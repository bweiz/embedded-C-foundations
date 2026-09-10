"""Executable harness gate. Run from any working directory."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile

import coverage as observations

ROOT = Path(__file__).resolve().parents[1]


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def command(argv):
    result = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, timeout=120)
    return {"command": argv, "exit_code": result.returncode,
            "stdout": result.stdout, "stderr": result.stderr}


def doctor():
    for variable, default in [("CC", "cc"), ("GCC", "gcc"), ("GCOV", "gcov")]:
        words = shlex.split(os.environ.get(variable, default))
        require(bool(words) and shutil.which(words[0]), f"Missing prerequisite: {variable}")
    require(shutil.which("make"), "Missing prerequisite: make")
    gcc = command(shlex.split(os.environ.get("GCC", "gcc")) + ["-dumpfullversion"])
    gcov = command(shlex.split(os.environ.get("GCOV", "gcov")) + ["--version"])
    require(gcc["exit_code"] == gcov["exit_code"] == 0, "Cannot inspect GCC/gcov versions")
    require(gcc["stdout"].strip() in gcov["stdout"].splitlines()[0], "GCC/gcov versions must match")
    print("Doctor: C compiler, Make, Python, GCC and matching gcov available")


def acceptance():
    binary = str(ROOT / "build/test_image")
    listing = command([binary, "--list"])
    names = listing["stdout"].splitlines()
    require(listing["exit_code"] == 0 and len(names) == len(set(names)) == 40,
            "Expected 40 unique named checks")
    unknown = command([binary, "--test", "not_a_test"])
    require(unknown["exit_code"] == 2 and "Unknown test" in unknown["stderr"],
            "Unknown test must fail with exit 2")
    report = json.loads(observations.REPORT.read_text())
    require(set(report["tests"]) == set(names), "Coverage must include every named test")
    lines = (ROOT / "fixture/image.c").read_text().splitlines()
    matches = [i for i, text in enumerate(lines, 1) if "if (entry < load" in text]
    require(len(matches) == 1, "Review entry-guard acceptance case after source changes")
    guard = matches[0]
    observed = observations.observed_tests(report, guard, observations.identities())
    require("entry_at_payload_end" in observed, "Entry-boundary test must reach guard")
    require("bad_magic" not in observed and "null" not in observed,
            "Coverage contamination: early returns must not reach entry guard")
    query = command([sys.executable, "scripts/coverage.py", "explain", str(guard)])
    require(query["exit_code"] == 0 and json.loads(query["stdout"])["observed_tests"] == observed,
            "CLI must explain observed tests")
    # Exercise real file identity changes in an isolated copy, including CLI rejection.
    with tempfile.TemporaryDirectory(prefix="impactd-freshness-") as directory:
        clone = Path(directory)
        for name in observations.INPUTS:
            destination = clone / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, destination)
        (clone / "build").mkdir()
        shutil.copyfile(observations.REPORT, clone / "build/coverage.json")
        for name in observations.INPUTS:
            path = clone / name
            original = path.read_bytes()
            path.write_bytes(original + b"\n")
            result = command([sys.executable, str(clone / "scripts/coverage.py"), "explain", str(guard)])
            require(result["exit_code"] != 0 and "Stale coverage" in result["stderr"],
                    f"Modified {name} must invalidate CLI evidence")
            path.write_bytes(original)
    print("Acceptance: 40 isolated tests, early-return separation, query and 4 stale-input rejections pass")


def main():
    if sys.argv[1:] == ["--doctor"]:
        doctor()
        return
    require(not sys.argv[1:], "usage: check.py [--doctor]")
    report = {"schema_version": 1, "started_at": datetime.now(timezone.utc).isoformat(),
              "status": "running", "steps": [], "sanitizers": "separate make sanitize gate"}
    output = ROOT / "build/check.json"
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    try:
        doctor()
        # -B forces recompilation; a previous binary cannot make this gate green.
        for argv in [["make", "-B", "test"], ["make", "demo"], ["make", "coverage"],
                     [sys.executable, "scripts/test_impact.py"]]:
            result = command(argv)
            report["steps"].append(result)
            require(result["exit_code"] == 0, f"Failed {argv}: {result['stderr']}")
            print(f"PASS {' '.join(argv)}")
        acceptance()
        report["source_sha256"] = observations.identities()
        report["status"] = "passed"
    except Exception as error:
        report["status"] = "failed"
        report["error"] = str(error)
        raise
    finally:
        report["finished_at"] = datetime.now(timezone.utc).isoformat()
        output.write_text(json.dumps(report, indent=2) + "\n")
    print("Harness passed. Summary: build/check.json")


if __name__ == "__main__":
    main()
