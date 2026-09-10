"""Isolated GCC/gcov observations. No semantic dependency or safety claims."""
import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "build/coverage.json"
INPUTS = ["fixture/image.c", "fixture/image.h", "fixture/test_image.c", "scripts/coverage.py"]


def identities(root=ROOT):
    return {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in INPUTS}


def execute(command, cwd):
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True, timeout=30)
    if result.returncode:
        raise RuntimeError(f"Command failed ({result.returncode}): {command}\n{result.stderr}")
    return {"command": [str(x) for x in command], "exit_code": result.returncode,
            "stdout": result.stdout, "stderr": result.stderr}


def collect():
    REPORT.parent.mkdir(exist_ok=True)
    REPORT.unlink(missing_ok=True)  # a failed new collection must not leave an old success
    before = identities()
    gcc = shlex.split(os.environ.get("GCC", "gcc"))
    gcov = shlex.split(os.environ.get("GCOV", "gcov"))
    if not gcc or not gcov:
        raise RuntimeError("GCC and GCOV must name commands")
    report = {"schema_version": 1, "evidence_kind": "observed_execution",
              "recorded_at": datetime.now(timezone.utc).isoformat(),
              "source_sha256": before, "tests": {},
              "limitations": ["Executed lines do not prove assertions or dependency completeness",
                              "No observed test is not evidence that no test is needed",
                              "Freshness is file-level, not semantic or environment equivalence"]}
    with tempfile.TemporaryDirectory(prefix="impactd-coverage-") as directory:
        work = Path(directory)
        for name in INPUTS[:3]:
            (work / Path(name).name).write_bytes((ROOT / name).read_bytes())
        report["compiler"] = execute(gcc + ["--version"], work)
        report["gcov"] = execute(gcov + ["--version"], work)
        report["build"] = execute(gcc + ["--coverage", "-O0", "-g", "-std=c11",
                                         "-Wall", "-Wextra", "-Wpedantic", "-Werror",
                                         "image.c", "test_image.c", "-o", "test_image"], work)
        report["executable_sha256"] = hashlib.sha256((work / "test_image").read_bytes()).hexdigest()
        listing = execute([str(work / "test_image"), "--list"], work)
        names = listing["stdout"].splitlines()
        if not names or len(names) != len(set(names)):
            raise RuntimeError("Test discovery must return nonempty unique names")
        for name in names:
            for counters in work.glob("*.gcda"):
                counters.unlink()
            for previous in work.glob("*.gcov.json.gz"):
                previous.unlink()
            run = execute([str(work / "test_image"), "--test", name], work)
            if run["stdout"].splitlines() != [f"PASS {name}", "1 checks, 0 failures"]:
                raise RuntimeError(f"Named execution did not run exactly one passing check: {name}")
            counters = list(work.glob("*-image.gcda"))
            if len(counters) != 1:
                raise RuntimeError("Missing or ambiguous validator coverage counters")
            extraction = execute(gcov + ["--json-format", str(counters[0])], work)
            documents = list(work.glob("*.gcov.json.gz"))
            if len(documents) != 1:
                raise RuntimeError("Missing or ambiguous gcov JSON")
            with gzip.open(documents[0], "rt") as stream:
                raw = json.load(stream)
            files = [x for x in raw["files"] if Path(x["file"]).name == "image.c"]
            if len(files) != 1:
                raise RuntimeError("gcov did not identify exactly one validator source")
            lines = {str(x["line_number"]): x["count"] for x in files[0]["lines"]
                     if x["count"] > 0}
            if not lines:
                raise RuntimeError(f"No validator execution observed for {name}")
            report["tests"][name] = {"run": run, "gcov_run": extraction,
                                    "file": "fixture/image.c", "line_counts": lines}
    if identities() != before:
        raise RuntimeError("Sources changed during collection; discard this observation")
    REPORT.write_text(json.dumps(report, indent=2) + "\n")
    print(f"Recorded isolated coverage for {len(names)} tests: build/coverage.json")


def observed_tests(report, line, current):
    if report.get("schema_version") != 1 or report.get("evidence_kind") != "observed_execution":
        raise ValueError("Unsupported coverage evidence")
    if report.get("source_sha256") != current:
        raise ValueError("Stale coverage: recorded inputs differ; run make coverage again")
    if line < 1:
        raise ValueError("Line number must be positive")
    return sorted(name for name, item in report["tests"].items()
                  if item["line_counts"].get(str(line), 0) > 0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["collect", "explain"])
    parser.add_argument("line", type=int, nargs="?")
    args = parser.parse_args()
    try:
        if args.action == "collect":
            if args.line is not None:
                parser.error("collect takes no line number")
            collect()
        else:
            if args.line is None:
                parser.error("explain requires a source line number")
            if args.line > len((ROOT / "fixture/image.c").read_text().splitlines()):
                raise ValueError("Line is outside fixture/image.c")
            report = json.loads(REPORT.read_text())
            names = observed_tests(report, args.line, identities())
            print(json.dumps({"file": "fixture/image.c", "line": args.line,
                              "observed_tests": names,
                              "meaning": "These tests executed this line in the recorded build",
                              "limitation": "Not a complete impact set or a safety guarantee"}, indent=2))
    except (OSError, ValueError, KeyError, RuntimeError, subprocess.TimeoutExpired) as error:
        parser.exit(1, f"coverage: {error}\n")


if __name__ == "__main__":
    main()
