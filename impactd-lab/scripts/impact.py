"""Compare tracked candidate files with hashed baseline snapshots; prioritize tests."""
import argparse
import difflib
import hashlib
import json
from pathlib import Path

import coverage

VALIDATOR = "fixture/image.c"


def validate_baseline(report):
    if report.get("schema_version") != 1 or report.get("evidence_kind") != "observed_execution":
        raise ValueError("Unsupported baseline evidence")
    hashes = report.get("source_sha256", {})
    snapshots = report.get("source_snapshots", {})
    if set(hashes) != set(coverage.INPUTS) or set(snapshots) != set(coverage.INPUTS):
        raise ValueError("Baseline requires all tracked snapshots; run make coverage before editing")
    for name in coverage.INPUTS:
        if not isinstance(snapshots[name], str) or hashlib.sha256(snapshots[name].encode()).hexdigest() != hashes[name]:
            raise ValueError(f"Baseline snapshot/hash mismatch: {name}")
    tests = report.get("tests")
    if not isinstance(tests, dict) or not tests:
        raise ValueError("Baseline has no named test observations")
    maximum = len(snapshots[VALIDATOR].splitlines())
    for name, item in tests.items():
        if not isinstance(name, str) or not isinstance(item, dict):
            raise ValueError("Malformed test observation")
        if item.get("file") != VALIDATOR or item.get("run", {}).get("exit_code") != 0:
            raise ValueError(f"Invalid baseline test result: {name}")
        counts = item.get("line_counts")
        if not isinstance(counts, dict) or not counts:
            raise ValueError(f"Missing coverage: {name}")
        for line, count in counts.items():
            if (not isinstance(line, str) or not line.isdecimal() or str(int(line)) != line
                    or not 1 <= int(line) <= maximum or type(count) is not int or count <= 0):
                raise ValueError(f"Invalid coverage count: {name}")
    return snapshots, tests


def analyze(report, candidate):
    snapshots, tests = validate_baseline(report)
    changes, gaps, reached = [], [], set()
    candidate_hashes = {}
    for name in coverage.INPUTS:
        path = candidate / name
        if not path.exists():
            candidate_hashes[name] = None
            changes.append({"file": name, "kind": "missing_file", "hunks": []})
            gaps.append(f"Tracked file is missing: {name}")
            if name == VALIDATOR:
                reached.update(tests)
            continue
        raw = path.read_bytes()
        candidate_hashes[name] = hashlib.sha256(raw).hexdigest()
        text = raw.decode("utf-8")
        if candidate_hashes[name] == report["source_sha256"][name]:
            continue
        old, new = snapshots[name].splitlines(keepends=True), text.splitlines(keepends=True)
        hunks = []
        for kind, start_old, end_old, start_new, end_new in difflib.SequenceMatcher(
                None, old, new, autojunk=False).get_opcodes():
            if kind == "equal":
                continue
            old_lines = list(range(start_old + 1, end_old + 1))
            observed = sorted(test for test, item in tests.items() if name == VALIDATOR
                              and any(str(line) in item["line_counts"] for line in old_lines))
            reached.update(observed)
            hunks.append({"kind": kind, "old_start": start_old + 1,
                          "old_count": end_old - start_old, "new_start": start_new + 1,
                          "new_count": end_new - start_new, "baseline_lines": old_lines,
                          "observed_tests": observed})
            if name == VALIDATOR:
                if kind == "insert":
                    gaps.append("Inserted validator code has no baseline execution evidence")
                elif not observed:
                    gaps.append("Changed validator lines have no observed baseline tests")
        if name != VALIDATOR:
            gaps.append(f"Change outside line-mapped validator: {name}")
        changes.append({"file": name, "kind": "modified", "hunks": hunks})
    return {
        "schema_version": 1,
        "status": "tracked_changes" if changes else "no_tracked_change",
        "baseline_source_sha256": report["source_sha256"],
        "candidate_source_sha256": candidate_hashes,
        "tracked_inputs": list(coverage.INPUTS),
        "changes": changes,
        "observed_candidates": sorted(reached),
        "evidence_gaps": sorted(set(gaps)),
        "verification_plan": {
            "prioritize": sorted(tests) if gaps else sorted(reached),
            "broad_fallback": bool(gaps),
            "required_gate": "make check",
            "may_skip_full_gate": False,
        },
        "limitations": ["Historical execution is not a complete impact set or assertion proof",
                        "Only listed inputs are compared; other files and environment changes are unobserved",
                        "Text alignment is not semantic change analysis; inserted code has no historical coverage",
                        "Hashes bind recorded bytes but do not authenticate the report's producer"],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, default=coverage.REPORT)
    parser.add_argument("--candidate", type=Path, default=coverage.ROOT)
    args = parser.parse_args()
    try:
        result = analyze(json.loads(args.baseline.read_text()), args.candidate)
        print(json.dumps(result, indent=2))
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
        parser.exit(1, f"impact: {error}\n")


if __name__ == "__main__":
    main()
