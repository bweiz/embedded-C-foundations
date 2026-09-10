use std::collections::BTreeMap;
use std::env;
use std::fs::{self, File};
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::thread;
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};

type Result<T> = std::result::Result<T, Box<dyn std::error::Error>>;
const INPUTS: &[&str] = &[
    "fixture/image.c", "fixture/image.h", "fixture/test_image.c",
    "runner/Cargo.toml", "runner/Cargo.lock", "runner/src/main.rs",
];

fn quote(text: &str) -> String {
    let mut out = String::from("\"");
    for ch in text.chars() {
        match ch {
            '"' => out.push_str("\\\""), '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"), '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            c if c < ' ' => out.push_str(&format!("\\u{:04x}", c as u32)),
            c => out.push(c),
        }
    }
    out.push('"');
    out
}

struct Workspace(PathBuf);
impl Workspace {
    fn create() -> Result<Self> {
        let stamp = SystemTime::now().duration_since(UNIX_EPOCH)?.as_nanos();
        let path = env::temp_dir().join(format!("impactd-rust-{}-{stamp}", std::process::id()));
        fs::create_dir(&path)?;
        Ok(Self(path))
    }
}
impl Drop for Workspace {
    fn drop(&mut self) { let _ = fs::remove_dir_all(&self.0); }
}

struct Observation { stdout: String, json: String }

// File-backed capture prevents pipe-buffer deadlock. Commands are serialized.
// Timeouts reap the direct child; this is not a sandbox for arbitrary commands.
fn run(work: &Path, argv: &[String], timeout: Duration) -> Result<Observation> {
    let stdout_path = work.join("command.stdout");
    let stderr_path = work.join("command.stderr");
    let mut child = Command::new(&argv[0]).args(&argv[1..]).current_dir(work)
        .stdin(Stdio::null()).stdout(File::create(&stdout_path)?)
        .stderr(File::create(&stderr_path)?).spawn()?;
    let started = Instant::now();
    let status = loop {
        match child.try_wait() {
            Ok(Some(status)) => break status,
            Ok(None) => {},
            Err(error) => { let _ = child.kill(); let _ = child.wait(); return Err(error.into()); }
        }
        if started.elapsed() >= timeout {
            let _ = child.kill();
            let _ = child.wait();
            return Err(format!("Command timed out: {argv:?}").into());
        }
        thread::sleep(Duration::from_millis(5));
    };
    let stdout = fs::read_to_string(stdout_path)?;
    let stderr = fs::read_to_string(stderr_path)?;
    if !status.success() {
        return Err(format!("Command failed ({status}): {argv:?}\n{stderr}").into());
    }
    let args = argv.iter().map(|x| quote(x)).collect::<Vec<_>>().join(",");
    let json = format!("{{\"command\":[{args}],\"exit_code\":0,\"stdout\":{},\"stderr\":{}}}",
                       quote(&stdout), quote(&stderr));
    Ok(Observation { stdout, json })
}

fn call(work: &Path, argv: &[&str]) -> Result<Observation> {
    run(work, &argv.iter().map(|x| x.to_string()).collect::<Vec<_>>(), Duration::from_secs(30))
}

fn hash(work: &Path, path: &Path) -> Result<String> {
    let path = path.to_str().ok_or("Paths must be UTF-8")?;
    let output = call(work, &["sha256sum", "--", path])?;
    let hash = output.stdout.split_whitespace().next().ok_or("Missing SHA-256")?;
    if hash.len() != 64 || !hash.bytes().all(|x| x.is_ascii_hexdigit()) {
        return Err("Invalid sha256sum output".into());
    }
    Ok(hash.to_owned())
}

fn identities(work: &Path, root: &Path) -> Result<BTreeMap<String, String>> {
    INPUTS.iter().map(|name| Ok((name.to_string(), hash(work, &root.join(name))?))).collect()
}

fn remove_suffix(work: &Path, suffix: &str) -> Result<()> {
    for entry in fs::read_dir(work)? {
        let entry = entry?;
        if entry.file_name().to_string_lossy().ends_with(suffix) { fs::remove_file(entry.path())?; }
    }
    Ok(())
}

fn only_suffix(work: &Path, suffix: &str) -> Result<PathBuf> {
    let mut paths = Vec::new();
    for entry in fs::read_dir(work)? {
        let entry = entry?;
        if entry.file_name().to_string_lossy().ends_with(suffix) { paths.push(entry.path()); }
    }
    if paths.len() != 1 { return Err(format!("Expected one {suffix}, found {}", paths.len()).into()); }
    Ok(paths.remove(0))
}

fn collect(root: &Path) -> Result<()> {
    let root = root.canonicalize()?;
    fs::create_dir_all(root.join("build"))?;
    let report_path = root.join("build/rust-coverage.json");
    match fs::remove_file(&report_path) {
        Ok(()) => {},
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => {},
        Err(e) => return Err(e.into()),
    }
    // Explicit executable paths only; no shell evaluation or implicit argument splitting.
    let gcc = env::var("GCC").unwrap_or_else(|_| "gcc".into());
    let gcov = env::var("GCOV").unwrap_or_else(|_| "gcov".into());
    let workspace = Workspace::create()?;
    let work = &workspace.0;
    let before = identities(work, &root)?;
    for name in &INPUTS[..3] {
        fs::copy(root.join(name), work.join(Path::new(name).file_name().unwrap()))?;
    }
    let compiler = call(work, &[&gcc, "--version"])?;
    let gcov_version = call(work, &[&gcov, "--version"])?;
    let build = call(work, &[&gcc, "--coverage", "-O0", "-g", "-std=c11", "-Wall",
                             "-Wextra", "-Wpedantic", "-Werror", "image.c", "test_image.c", "-o", "test_image"])?;
    let executable_hash = hash(work, &work.join("test_image"))?;
    let listing = call(work, &["./test_image", "--list"])?;
    let names: Vec<_> = listing.stdout.lines().collect();
    let mut unique = names.clone(); unique.sort_unstable(); unique.dedup();
    if names.is_empty() || unique.len() != names.len() { return Err("Invalid test discovery".into()); }
    let mut tests = BTreeMap::new();
    for name in &names {
        remove_suffix(work, ".gcda")?;
        remove_suffix(work, ".gcov.json.gz")?;
        let execution = call(work, &["./test_image", "--test", name])?;
        if execution.stdout != format!("PASS {name}\n1 checks, 0 failures\n") {
            return Err(format!("Expected exactly one passing check: {name}").into());
        }
        let counters = only_suffix(work, "-image.gcda")?;
        let extraction = call(work, &[&gcov, "--json-format", counters.to_str().ok_or("Non-UTF-8 path")?])?;
        let compressed = only_suffix(work, ".gcov.json.gz")?;
        let raw = call(work, &["gzip", "-dc", "--", compressed.to_str().ok_or("Non-UTF-8 path")?])?;
        // Embed trusted gcov output; the Python parity gate parses and validates it.
        tests.insert(name.to_string(), format!("{{\"run\":{},\"gcov_run\":{},\"raw_gcov\":{}}}",
                                             execution.json, extraction.json, raw.stdout.trim()));
    }
    if identities(work, &root)? != before { return Err("Inputs changed during collection".into()); }
    let inputs_json = before.iter().map(|(k,v)| format!("{}:{}", quote(k),quote(v))).collect::<Vec<_>>().join(",");
    let tests_json = tests.iter().map(|(k,v)| format!("{}:{v}",quote(k))).collect::<Vec<_>>().join(",");
    let time = SystemTime::now().duration_since(UNIX_EPOCH)?.as_secs();
    let report = format!(concat!("{{\"schema_version\":1,\"evidence_kind\":\"observed_execution\",",
        "\"backend\":\"rust-gcov-raw\",\"recorded_at_unix\":{},\"source_sha256\":{{{}}},",
        "\"executable_sha256\":{},\"compiler\":{},\"gcov\":{},\"build\":{},\"tests\":{{{}}}}}\n"),
        time, inputs_json, quote(&executable_hash), compiler.json, gcov_version.json, build.json, tests_json);
    fs::write(&report_path, report)?;
    println!("Rust: recorded isolated coverage for {} tests: {}", names.len(), report_path.display());
    Ok(())
}

fn main() {
    let args: Vec<_> = env::args().collect();
    let result = if args.len() == 3 && args[1] == "collect" {
        collect(Path::new(&args[2]))
    } else { Err("usage: impactd-runner collect LAB_ROOT".into()) };
    if let Err(error) = result { eprintln!("impactd-runner: {error}"); std::process::exit(1); }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn json_escapes_controls_and_preserves_unicode() {
        assert_eq!(quote("a\"\\\n\t\r\u{0001}é"), "\"a\\\"\\\\\\n\\t\\r\\u0001é\"");
    }
    #[test]
    fn rejects_failed_children() {
        let dir = Workspace::create().unwrap();
        let result = call(&dir.0, &["python3", "-c", "import sys; sys.exit(7)"]);
        assert!(result.err().unwrap().to_string().contains("Command failed"));
    }
    #[test]
    fn times_out_and_reaps_direct_child() {
        let dir = Workspace::create().unwrap();
        let args = ["python3", "-c", "import time; time.sleep(10)"].map(String::from);
        let start = Instant::now();
        let error = run(&dir.0, &args, Duration::from_millis(30)).err().unwrap();
        assert!(error.to_string().contains("timed out"));
        assert!(start.elapsed() < Duration::from_secs(3));
    }
}
