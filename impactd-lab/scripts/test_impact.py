"""Acceptance cases for baseline-to-candidate change analysis."""
import copy
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import unittest

import coverage
import impact


class ImpactAcceptance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.baseline = json.loads(coverage.REPORT.read_text())
        cls.source = cls.baseline["source_snapshots"][impact.VALIDATOR]
        cls.guard = next(line for line in cls.source.splitlines() if "if (entry < load" in line)
        cls.guard_line = cls.source.splitlines().index(cls.guard) + 1
        cls.expected = sorted(name for name, item in cls.baseline["tests"].items()
                              if str(cls.guard_line) in item["line_counts"])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="impactd-candidate-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name, text in self.baseline["source_snapshots"].items():
            p = self.root / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(text.encode())

    def change(self, text):
        (self.root / impact.VALIDATOR).write_bytes(text.encode())
        return impact.analyze(self.baseline, self.root)

    def test_unchanged(self):
        report = impact.analyze(self.baseline, self.root)
        self.assertEqual(report["status"], "no_tracked_change")
        self.assertEqual(report["observed_candidates"], [])
        self.assertFalse(report["verification_plan"]["may_skip_full_gate"])

    def test_guard_replacement(self):
        report = self.change(self.source.replace("entry - load >= size", "entry - load > size"))
        self.assertEqual(len(self.expected), 8)
        self.assertEqual(report["observed_candidates"], self.expected)
        self.assertEqual(report["changes"][0]["hunks"][0]["baseline_lines"], [self.guard_line])
        self.assertFalse(report["verification_plan"]["may_skip_full_gate"])

    def test_shifted_guard_retains_baseline_coordinates(self):
        report = self.change("/* new prefix */\n\n" + self.source.replace("entry - load >= size", "entry - load > size"))
        hunk = next(h for h in report["changes"][0]["hunks"] if h["kind"] == "replace")
        self.assertEqual(hunk["old_start"], self.guard_line)
        self.assertEqual(hunk["new_start"], self.guard_line + 2)
        self.assertEqual(hunk["observed_tests"], self.expected)
        self.assertTrue(report["verification_plan"]["broad_fallback"])

    def test_insertion_is_unknown(self):
        report = self.change(self.source.replace(self.guard, "    if (entry == load) return IMAGE_OK;\n" + self.guard))
        self.assertTrue(report["verification_plan"]["broad_fallback"])
        self.assertEqual(len(report["verification_plan"]["prioritize"]), 40)
        self.assertTrue(any("Inserted" in gap for gap in report["evidence_gaps"]))

    def test_deletion_uses_old_coverage(self):
        report = self.change(self.source.replace(self.guard + "\n", ""))
        self.assertEqual(report["observed_candidates"], self.expected)
        self.assertEqual(report["changes"][0]["hunks"][0]["kind"], "delete")

    def test_no_coverage_never_means_safe(self):
        report = self.change(self.source.replace("/* Subtract only", "/* Safely subtract only"))
        self.assertEqual(report["observed_candidates"], [])
        self.assertTrue(report["verification_plan"]["broad_fallback"])
        self.assertFalse(report["verification_plan"]["may_skip_full_gate"])

    def test_unmapped_inputs_request_full_verification(self):
        for name in coverage.INPUTS:
            if name == impact.VALIDATOR:
                continue
            with self.subTest(name=name):
                path = self.root / name
                before = path.read_bytes()
                path.write_bytes(before + b"\n")
                report = impact.analyze(self.baseline, self.root)
                self.assertTrue(report["verification_plan"]["broad_fallback"])
                self.assertEqual(len(report["verification_plan"]["prioritize"]), 40)
                path.write_bytes(before)

    def test_missing_file_requests_full_verification(self):
        (self.root / impact.VALIDATOR).unlink()
        report = impact.analyze(self.baseline, self.root)
        self.assertTrue(report["verification_plan"]["broad_fallback"])
        self.assertEqual(report["changes"][0]["kind"], "missing_file")

    def test_snapshot_mismatch_rejected(self):
        bad = copy.deepcopy(self.baseline)
        bad["source_snapshots"][impact.VALIDATOR] += "\n"
        with self.assertRaisesRegex(ValueError, "snapshot/hash mismatch"):
            impact.analyze(bad, self.root)

    def test_old_report_without_snapshots_rejected(self):
        bad = copy.deepcopy(self.baseline)
        del bad["source_snapshots"]
        with self.assertRaisesRegex(ValueError, "requires all tracked snapshots"):
            impact.analyze(bad, self.root)

    def test_malformed_counts_rejected(self):
        for count in [-1, True, "3"]:
            bad = copy.deepcopy(self.baseline)
            next(iter(bad["tests"].values()))["line_counts"]["11"] = count
            with self.subTest(count=count), self.assertRaisesRegex(ValueError, "Invalid coverage count"):
                impact.analyze(bad, self.root)

    def test_cli_and_selected_tests_detect_real_defect(self):
        expected = self.change(self.source.replace("entry - load >= size", "entry - load > size"))
        result = subprocess.run([sys.executable, str(coverage.ROOT / "scripts/impact.py"),
                                 "--baseline", str(coverage.REPORT), "--candidate", str(self.root)],
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), expected)
        binary = self.root / "candidate"
        compile_command = shlex.split(os.environ.get("CC", "cc")) + [
            "-std=c11", "-Wall", "-Wextra", "-Werror", "-O0",
            str(self.root / "fixture/image.c"), str(self.root / "fixture/test_image.c"), "-o", str(binary)]
        subprocess.run(compile_command, check=True, capture_output=True, text=True, timeout=30)
        runs = {}
        for name in expected["observed_candidates"]:
            run = subprocess.run([str(binary), "--test", name], capture_output=True, text=True, timeout=30)
            runs[name] = {"exit_code": run.returncode, "stdout": run.stdout, "stderr": run.stderr}
        failure = runs["entry_at_payload_end"]
        self.assertEqual(failure["exit_code"], 1)
        self.assertIn("FAIL entry_at_payload_end", failure["stderr"])
        (coverage.ROOT / "build/impact-demo.json").write_text(json.dumps(
            {"analysis": expected, "candidate_build_command": compile_command, "candidate_test_runs": runs,
             "finding": "A test prioritized from old-line coverage detects the injected boundary defect"}, indent=2) + "\n")


if __name__ == "__main__":
    unittest.main()
