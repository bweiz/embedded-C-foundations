"""One bounded mutation experiment, not an automatic impact-analysis engine."""
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import tempfile
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
FLAGS = ["-std=c11", "-Wall", "-Wextra", "-Wpedantic", "-Werror", "-O0", "-g"]
GUARD = "    if (entry < load || entry - load >= size) return IMAGE_ERR_ENTRY_RANGE;"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def run(command):
    result = subprocess.run(command, capture_output=True, text=True, timeout=30)
    return {"command": [str(x) for x in command], "exit_code": result.returncode,
            "stdout": result.stdout, "stderr": result.stderr}


def main():
    compiler = shlex.split(os.environ.get("CC", "cc"))
    if not compiler:
        raise RuntimeError("CC must specify a compiler")
    source = (ROOT / "fixture/image.c").read_text()
    if source.count(GUARD) != 1:
        raise RuntimeError("Expected exactly one entry guard; review mutation for this source")
    # Mutate a temporary copy only; keep entry referenced with strict warnings.
    mutated = source.replace(GUARD, "    (void)entry; /* EXPERIMENT: entry check removed */")
    report = {
        "schema_version": 1,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "experiment": "remove_entry_rejection",
        "requirement": "load_addr <= entry_addr < load_addr + image_size",
        "scope": "one manually selected C guard and two explicit probes",
        "compiler": run(compiler + ["--version"]),
        "source_sha256": {
            p.name: digest(p.read_bytes()) for p in sorted((ROOT / "fixture").glob("*.[ch]"))
        },
        "mutant_source_sha256": digest(mutated.encode()),
        "mutation": {"removed": GUARD.strip(), "replacement": "(void)entry;"},
        "builds": {}, "runs": {},
        "limitations": ["No coverage collection or automatic test selection yet",
                        "A detected mutation is not proof of correctness",
                        "Command paths in temporary directories expire after this run",
                        "Source identity detects changes, not semantic impact"]
    }
    with tempfile.TemporaryDirectory(prefix="impactd-lab-") as directory:
        work = Path(directory)
        for variant, text in [("baseline", source), ("mutant", mutated)]:
            unit = work / (variant + ".c")
            binary = work / variant
            unit.write_text(text)
            command = compiler + FLAGS + ["-I", str(ROOT / "fixture"), str(unit),
                       str(ROOT / "fixture/test_image.c"), "-o", str(binary)]
            build = run(command)
            report["builds"][variant] = build
            if build["exit_code"] != 0:
                raise RuntimeError("Compilation failed: " + build["stderr"])
            build["executable_sha256"] = digest(binary.read_bytes())
            for probe, arguments in [("suite", []), ("weak", ["--weak-entry"]),
                                     ("strong", ["--strong-entry"])]:
                report["runs"][variant + ":" + probe] = run([str(binary)] + arguments)

    expected = {"baseline:suite": 0, "baseline:weak": 0, "baseline:strong": 0,
                "mutant:suite": 1, "mutant:weak": 0, "mutant:strong": 1}
    for name, code in expected.items():
        actual = report["runs"][name]
        if actual["exit_code"] != code:
            raise RuntimeError(f"Unexpected {name}: {actual}")
    if "FAIL reject_entry_outside_image" not in report["runs"]["mutant:strong"]["stderr"]:
        raise RuntimeError("Strong probe did not fail through its intended assertion")
    report["finding"] = {
        "weak_probe": "does not detect removal of entry-address rejection",
        "strong_probe": "detects removal of entry-address rejection",
        "baseline_evidence": "applies to baseline hashes; cannot be relabeled as mutant evidence"
    }
    output = ROOT / "build/evidence.json"
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    print("Baseline: complete suite and both probes pass.")
    print("Injected fault: entry-address rejection removed in a temporary copy.")
    print("Weak probe: PASS — verification gap demonstrated.")
    print("Strong probe: FAIL through rejection assertion — fault detected.")
    print("Experiment successful. Evidence: build/evidence.json")


if __name__ == "__main__":
    main()
