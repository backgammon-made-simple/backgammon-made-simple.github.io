from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.testing.quality import quality_reports


class QualityReportTests(unittest.TestCase):
    def test_assemble_preserves_independent_statuses_and_human_not_run(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            values = {
                "contract": {"schema_version": 1, "routes": [], "viewports": [], "metric_names": {}, "commands": {}, "report_schema": {}},
                "build": {"status": "PASS", "duration_ms": 123, "rendered_file_count": 10, "findings": []},
                "browser": {"summary": {"passed": True, "pages": 2, "checks": 4, "failures": 0, "consoleMessages": 0, "durationMs": 20}, "screenshots": [], "findings": []},
                "performance": {"status": "PASS", "measurements": [], "interactions": [], "findings": []},
                "static": {"status": "PASS", "counts": {"source_files": 2, "rendered_files": 1, "duplicate_groups": 0, "module_review_candidates": 0, "unreferenced_site_assets": 0}, "findings": []},
            }
            paths = {}
            for name, value in values.items():
                path = root / f"{name}.json"
                path.write_text(json.dumps(value), encoding="utf-8")
                paths[name] = path
            baseline = quality_reports.assemble(
                output_dir=root / "output",
                contract_path=paths["contract"],
                build_path=paths["build"],
                browser_path=paths["browser"],
                performance_path=paths["performance"],
                static_path=paths["static"],
            )
            self.assertEqual(baseline["overall_status"], "PASS")
            self.assertEqual(baseline["components"]["human_ux_review"]["status"], "NOT RUN")
            self.assertEqual(
                baseline["components"]["clean_build_and_browserless_tests"]["evidence"],
                "../build.json",
            )
            for name in ("baseline-summary.md", "baseline.json", "findings.json"):
                self.assertTrue((root / "output" / name).is_file())

    def test_comparison_contract_matches_canonical_sources(self) -> None:
        repository_root = Path(__file__).resolve().parents[1]
        contract = json.loads((repository_root / "scripts/testing/quality/comparison-contract.json").read_text(encoding="utf-8"))
        manifest = json.loads((repository_root / "scripts/testing/ux/browser/ui_release_manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(contract["routes"], [{"id": page["id"], "route": page["route"]} for page in manifest["pages"]])
        self.assertEqual(contract["viewports"], [{"height": item["height"], "name": item["name"], "width": item["width"]} for item in manifest["viewports"]])
        self.assertEqual(contract["performance"]["warmup_loads"], 1)
        self.assertEqual(contract["performance"]["measured_loads"], 3)
        self.assertEqual(contract["screenshots"]["failure_limit"], 30)


if __name__ == "__main__":
    unittest.main()
