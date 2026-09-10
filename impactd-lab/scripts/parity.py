"""Compare independently executed Rust and Python gcov observations."""
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

import coverage

ROOT = coverage.ROOT
RUST_INPUTS = ["fixture/image.c", "fixture/image.h", "fixture/test_image.c",
               "runner/Cargo.toml", "runner/Cargo.lock", "runner/src/main.rs"]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def compare(python, rust):
    require(python.get("source_sha256") == coverage.identities(), "Stale Python evidence")
    current = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in RUST_INPUTS}
    require(rust.get("source_sha256") == current, "Stale Rust evidence")
    require(rust.get("schema_version") == 1 and rust.get("backend") == "rust-gcov-raw"
            and rust.get("evidence_kind") == "observed_execution", "Unsupported Rust evidence")
    executable = rust.get("executable_sha256", "")
    require(len(executable) == 64 and all(c in "0123456789abcdef" for c in executable),
            "Missing executable identity")
    require(set(python["tests"]) == set(rust["tests"]) and len(rust["tests"]) == 40,
            "Test sets differ")
    for name, expected in python["tests"].items():
        actual = rust["tests"][name]
        require(actual["run"]["exit_code"] == 0 and actual["run"]["stdout"] == expected["run"]["stdout"],
                f"Execution differs: {name}")
        files = [f for f in actual["raw_gcov"]["files"] if Path(f["file"]).name == "image.c"]
        require(len(files) == 1, f"Ambiguous validator source: {name}")
        counts = {str(x["line_number"]): x["count"] for x in files[0]["lines"] if x["count"] > 0}
        require(counts == expected["line_counts"], f"Line counts differ: {name}")


def expect_rejection(python, rust, reason):
    try:
        compare(python, rust)
    except ValueError as error:
        require(reason in str(error), f"Wrong rejection: {error}")
    else:
        raise ValueError("Invalid evidence was accepted")


def main():
    summary_path = ROOT / "build/parity.json"
    summary_path.unlink(missing_ok=True)
    coverage.collect()
    python = json.loads(coverage.REPORT.read_text())
    rust = json.loads((ROOT / "build/rust-coverage.json").read_text())
    compare(python, rust)
    stale = copy.deepcopy(rust)
    stale["source_sha256"]["fixture/image.c"] = "0" * 64
    expect_rejection(python, stale, "Stale Rust")
    corrupted = copy.deepcopy(rust)
    first = next(iter(corrupted["tests"].values()))
    file = next(f for f in first["raw_gcov"]["files"] if Path(f["file"]).name == "image.c")
    line = next(x for x in file["lines"] if x["count"] > 0)
    line["count"] += 1
    expect_rejection(python, corrupted, "Line counts differ")
    # A failed new collection must remove an old report, not silently leave success.
    binary = ROOT / "build/rust-target/debug/impactd-runner"
    with tempfile.TemporaryDirectory(prefix="impactd-rust-failure-") as directory:
        clone = Path(directory)
        for name in RUST_INPUTS:
            dest = clone / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, dest)
        (clone / "build").mkdir()
        report = clone / "build/rust-coverage.json"
        report.write_text(json.dumps(rust))
        environment = dict(os.environ, GCC=str(clone / "missing-compiler"))
        result = subprocess.run([str(binary), "collect", str(clone)], env=environment,
                                capture_output=True, text=True, timeout=30)
        require(result.returncode != 0 and not report.exists(), "Failed collection retained old success")
    summary = {"status": "passed", "tests_compared": 40, "comparison": "all positive line counts per test",
               "negative_cases": ["stale input", "altered count", "failed recollection removes old report"],
               "python_source_sha256": python["source_sha256"], "rust_source_sha256": rust["source_sha256"]}
    summary_path.write_text(json.dumps(summary, indent=2) + "\n")
    print("Parity PASS: all line counts agree across 40 tests; 3 negative cases pass")


if __name__ == "__main__":
    main()
