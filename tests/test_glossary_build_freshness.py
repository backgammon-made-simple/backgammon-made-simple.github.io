from __future__ import annotations

import copy
import hashlib
import json
import os
import subprocess
import unittest
from unittest import mock

from scripts import bms_pre_render
from scripts import glossary_source
from scripts import learn_glossary


class GlossaryBuildFreshnessTests(unittest.TestCase):
    def test_current_source_generates_current_public_data(self) -> None:
        result = glossary_source.check_production_source()
        source_entries = glossary_source.load_contract_json()

        self.assertEqual(result["canonical_entries"], len(source_entries))
        self.assertEqual(result["published_entries"], len(source_entries))

    def test_stale_public_data_fails_with_a_regeneration_instruction(self) -> None:
        generated, _ = glossary_source.build_production_source()

        with self.assertRaisesRegex(
            glossary_source.ValidationError,
            "Generated production glossary is stale or manually edited",
        ):
            glossary_source.assert_source_current("{}\n", generated)

    def test_source_generation_is_deterministic(self) -> None:
        first, _ = glossary_source.build_production_source()
        second, _ = glossary_source.build_production_source()

        self.assertEqual(first, second)
        self.assertEqual(
            hashlib.sha256(first.encode("utf-8")).hexdigest(),
            hashlib.sha256(second.encode("utf-8")).hexdigest(),
        )

    def test_changed_published_term_count_regenerates_glossary_outputs(self) -> None:
        entries = copy.deepcopy(glossary_source.load_contract_json())
        added = copy.deepcopy(entries["ace"])
        added.update(
            {
                "term": "Z Freshness Term",
                "aliases": [],
                "redirect_slugs": [],
                "short_definition": "A generated freshness test term.",
                "long_definition": "A generated freshness test term.",
                "categories": ["Checker Play"],
                "tracks": [],
                "related_terms": [],
                "inline_terms": {},
                "references": [],
            }
        )
        entries["z-freshness-term"] = added

        generated = glossary_source.build_public_data_from_contract(entries)
        public_entries = learn_glossary.validate_public_data(generated)
        html = learn_glossary.build_entries_html(public_entries, {}, {})
        lookup = json.loads(learn_glossary.build_lookup_data(public_entries, {}))

        self.assertEqual(len(public_entries), 13)
        self.assertEqual(html.count('class="bms-glossary-entry"'), 13)
        self.assertEqual(len(lookup["entries"]), 13)

    def test_partial_render_runs_the_freshness_check(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True), mock.patch.object(
            bms_pre_render, "invalidate_full_build_marker", return_value=False
        ), mock.patch.object(bms_pre_render, "run") as run:
            self.assertEqual(bms_pre_render.main(), 0)

        run.assert_called_once_with(
            [
                bms_pre_render.sys.executable,
                str(bms_pre_render.REPO_ROOT / "scripts" / "learn_glossary.py"),
                "validate",
            ]
        )

    def test_partial_render_propagates_a_stale_output_failure(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True), mock.patch.object(
            bms_pre_render, "invalidate_full_build_marker", return_value=False
        ), mock.patch.object(
            bms_pre_render,
            "run",
            side_effect=subprocess.CalledProcessError(1, ["glossary", "validate"]),
        ):
            with self.assertRaises(subprocess.CalledProcessError):
                bms_pre_render.main()


if __name__ == "__main__":
    unittest.main()
