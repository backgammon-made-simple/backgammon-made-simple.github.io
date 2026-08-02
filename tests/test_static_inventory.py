from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.testing.quality import static_inventory


class StaticInventoryTests(unittest.TestCase):
    def test_inventory_is_evidence_only_and_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "site" / "assets").mkdir(parents=True)
            (root / "site" / "_site").mkdir(parents=True)
            (root / "scripts").mkdir()
            (root / "tests").mkdir()
            (root / "docs").mkdir()
            (root / "site" / "index.qmd").write_text(
                '<img src="/assets/used.svg">', encoding="utf-8"
            )
            (root / "site" / "_quarto.yml").write_text(
                'resources:\n  - "assets/globbed/**"\n', encoding="utf-8"
            )
            (root / "site" / "assets" / "globbed").mkdir()
            (root / "site" / "assets" / "globbed" / "kept.svg").write_text(
                "<svg><circle/></svg>", encoding="utf-8"
            )
            (root / "site" / "assets" / "used.svg").write_text(
                "<svg></svg>", encoding="utf-8"
            )
            (root / "site" / "assets" / "unused.svg").write_text(
                "<svg><path/></svg>", encoding="utf-8"
            )
            (root / "scripts" / "one.js").write_text("same", encoding="utf-8")
            (root / "tests" / "two.js").write_text("same", encoding="utf-8")
            (root / "site" / "_site" / "index.html").write_text(
                '<img src="/assets/used.svg">', encoding="utf-8"
            )

            first = static_inventory.build_inventory(root, root / "site" / "_site")
            second = static_inventory.build_inventory(root, root / "site" / "_site")

            self.assertEqual(first, second)
            self.assertFalse(first["evidence_contract"]["reference_scanning_is_proof"])
            self.assertFalse(first["evidence_contract"]["files_moved_or_deleted"])
            self.assertEqual(
                [item["path"] for item in first["unreferenced_site_assets"]],
                ["site/assets/unused.svg"],
            )
            self.assertTrue(first["duplicate_files_by_sha256"])
            finding = next(
                item
                for item in first["findings"]
                if item["route_or_file"] == "site/assets/unused.svg"
            )
            self.assertEqual(finding["category"], "archive-candidate")
            self.assertFalse(finding["safe_for_automated_remediation"])
            self.assertTrue(finding["needs_review"])


if __name__ == "__main__":
    unittest.main()
