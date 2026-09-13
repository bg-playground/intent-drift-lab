#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import drift_lab  # noqa: E402


FIXTURES = [
    (
        "TESLA-FSD-001",
        ROOT / "policies" / "TESLA-FSD-001.json",
        ROOT / "artifacts" / "tesla-fsd.baseline.yaml",
        ROOT / "mutations" / "tesla-fsd.occupant-may-rest.yaml",
    ),
    (
        "SPACEX-SL-001",
        ROOT / "policies" / "SPACEX-SL-001.json",
        ROOT / "artifacts" / "spacex-sl.baseline.yaml",
        ROOT / "mutations" / "spacex-sl.threshold-weakened.yaml",
    ),
    (
        "XAI-GROK-001",
        ROOT / "policies" / "XAI-GROK-001.json",
        ROOT / "artifacts" / "xai-grok.baseline.yaml",
        ROOT / "mutations" / "xai-grok.self-report.yaml",
    ),
]


class DriftLabTests(unittest.TestCase):
    def test_baselines_go_and_mutations_nogo(self) -> None:
        for req_id, contract, baseline, mutant in FIXTURES:
            with self.subTest(req_id=req_id, artifact="baseline"):
                report = drift_lab.analyze(baseline, contract)
                self.assertEqual(report["requirement_id"], req_id)
                self.assertEqual(report["release_decision"], "GO")
                self.assertTrue(report["aligned"])
                self.assertEqual(report["mismatch_count"], 0)
                self.assertTrue(report["happy_path_passed"])
                self.assertEqual(report["disclaimer"], drift_lab.DISCLAIMER)
                self.assertIn("phase_6_reporting", report["bgstm_trace"])
            with self.subTest(req_id=req_id, artifact="mutant"):
                report = drift_lab.analyze(mutant, contract)
                self.assertEqual(report["release_decision"], "NO-GO")
                self.assertFalse(report["aligned"])
                self.assertGreater(report["mismatch_count"], 0)
                self.assertTrue(report["happy_path_passed"])

    def test_exit_codes(self) -> None:
        for req_id, contract, baseline, mutant in FIXTURES:
            with self.subTest(req_id=req_id, code="baseline"):
                self.assertEqual(
                    drift_lab.main(["--artifact", str(baseline), "--contract", str(contract)]),
                    0,
                )
            with self.subTest(req_id=req_id, code="mutant"):
                self.assertEqual(
                    drift_lab.main(["--artifact", str(mutant), "--contract", str(contract)]),
                    2,
                )

    def test_missing_file_is_hard_failure(self) -> None:
        contract = ROOT / "policies" / "TESLA-FSD-001.json"
        self.assertEqual(
            drift_lab.main(
                ["--artifact", str(ROOT / "artifacts" / "missing.yaml"), "--contract", str(contract)]
            ),
            1,
        )

    def test_unknown_rule_kind_is_hard_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            contract = Path(tmp) / "bad.json"
            artifact = Path(tmp) / "ok.yaml"
            contract.write_text(
                json.dumps(
                    {
                        "requirement_id": "BAD-001",
                        "title": "bad",
                        "domain": "lab",
                        "risk": "low",
                        "rule": {"kind": "poetry", "path": "x", "expected": "y"},
                        "bgstm": {"planning_risk": "n/a", "traceability_id": "BAD-001"},
                    }
                ),
                encoding="utf-8",
            )
            artifact.write_text("x: y\n", encoding="utf-8")
            self.assertEqual(
                drift_lab.main(["--artifact", str(artifact), "--contract", str(contract)]),
                1,
            )

    def test_reports_include_required_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            json_out = Path(tmp) / "out.json"
            html_out = Path(tmp) / "out.html"
            code = drift_lab.main(
                [
                    "--artifact",
                    str(ROOT / "artifacts" / "tesla-fsd.baseline.yaml"),
                    "--contract",
                    str(ROOT / "policies" / "TESLA-FSD-001.json"),
                    "--json-out",
                    str(json_out),
                    "--html-out",
                    str(html_out),
                ]
            )
            self.assertEqual(code, 0)
            payload = json.loads(json_out.read_text(encoding="utf-8"))
            for key in (
                "schema_version",
                "requirement_id",
                "title",
                "domain",
                "risk",
                "contract_path",
                "artifact_path",
                "rule_kind",
                "path",
                "expected",
                "observed",
                "aligned",
                "happy_path_passed",
                "case_count",
                "mismatch_count",
                "cases",
                "release_decision",
                "decision_reason",
                "disclaimer",
                "bgstm_trace",
            ):
                self.assertIn(key, payload)
            html = html_out.read_text(encoding="utf-8")
            self.assertIn("GO", html)
            self.assertIn(drift_lab.DISCLAIMER, html)
            self.assertNotIn("artifact", payload)

    def test_html_reviewer_layout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mutant_html = Path(tmp) / "mutant.html"
            baseline_html = Path(tmp) / "baseline.html"
            self.assertEqual(
                drift_lab.main(
                    [
                        "--artifact",
                        str(ROOT / "mutations" / "tesla-fsd.occupant-may-rest.yaml"),
                        "--contract",
                        str(ROOT / "policies" / "TESLA-FSD-001.json"),
                        "--html-out",
                        str(mutant_html),
                    ]
                ),
                2,
            )
            self.assertEqual(
                drift_lab.main(
                    [
                        "--artifact",
                        str(ROOT / "artifacts" / "tesla-fsd.baseline.yaml"),
                        "--contract",
                        str(ROOT / "policies" / "TESLA-FSD-001.json"),
                        "--html-out",
                        str(baseline_html),
                    ]
                ),
                0,
            )
            mutant = mutant_html.read_text(encoding="utf-8")
            baseline = baseline_html.read_text(encoding="utf-8")
            self.assertIn("TESLA-FSD-001 · NO-GO · tesla-fsd.occupant-may-rest.yaml", mutant)
            self.assertIn("TESLA-FSD-001 · GO · tesla-fsd.baseline.yaml", baseline)
            self.assertIn("Observed artifact", mutant)
            self.assertIn("Boundary cases", mutant)
            self.assertIn("Happy path", mutant)
            self.assertIn("Supporting rule", mutant)
            self.assertIn("attention_required", mutant)
            self.assertIn("true", baseline.lower())
            self.assertNotIn("True", baseline)
            self.assertNotIn("False", mutant)
            self.assertIn('class="miss"', mutant)


if __name__ == "__main__":
    unittest.main()
