from __future__ import annotations

import copy
import inspect
import json
import unittest

from scripts import glossary_source as source
from scripts import learn_glossary


class CanonicalGlossaryJsonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.entries = source.load_contract_json()
        cls.serialized, cls.report = source.build_production_source()
        cls.data = json.loads(cls.serialized)

    def test_canonical_json_is_the_only_production_input(self) -> None:
        self.assertEqual(
            source.GLOSSARY_SOURCE_PATH,
            learn_glossary.REPOSITORY_ROOT / "glossary" / "glossary.json",
        )
        implementation = inspect.getsource(source.build_production_source)
        self.assertIn("load_contract_json", implementation)
        self.assertNotIn("parse_markdown", implementation)
        self.assertNotIn("glossary_old", implementation)
        self.assertNotIn("staged", implementation)

    def test_only_published_entries_are_projected(self) -> None:
        self.assertEqual(len(self.entries), 12)
        self.assertEqual(self.report["canonical_entries"], 12)
        self.assertEqual(self.report["published_entries"], 12)
        self.assertEqual(self.report["aliases"], 3)
        self.assertEqual(len(self.data["entries"]), 12)
        self.assertEqual(
            {entry["slug"] for entry in self.data["entries"]},
            set(self.entries),
        )

    def test_contract_fields_map_without_rewriting_authoritative_json(self) -> None:
        source_entry = self.entries["10-in-the-zone"]
        generated = {
            entry["slug"]: entry for entry in self.data["entries"]
        }["10-in-the-zone"]
        self.assertEqual(generated["term"], source_entry["term"])
        self.assertEqual(generated["short_definition"], source_entry["short_definition"])
        self.assertEqual(generated["definition"], source_entry["long_definition"])
        self.assertEqual(generated["categories"], source_entry["categories"])
        self.assertEqual(generated["learning_tracks"], source_entry["tracks"])
        self.assertEqual(generated["date_added"], source_entry["added"])
        self.assertEqual(
            generated["definition_links"],
            [{"slug": "active-builder", "text": "active builders"}],
        )

    def test_unresolved_related_slugs_remain_plain_compatibility_labels(self) -> None:
        generated = {
            entry["slug"]: entry for entry in self.data["entries"]
        }["10-in-the-zone"]
        related = {item["term"]: item for item in generated["related_terms"]}
        self.assertEqual(related["Active Builder"]["slug"], "active-builder")
        self.assertNotIn("slug", related["Attack Zone"])
        self.assertGreater(self.report["unresolved_related_terms"], 0)

    def test_duplicate_raw_json_keys_fail_before_normal_parsing(self) -> None:
        with self.assertRaisesRegex(source.ValidationError, "Duplicate raw JSON key"):
            json.loads(
                '{"one":{"term":"One"},"one":{"term":"Other"}}',
                object_pairs_hook=source._reject_duplicate_keys,
            )

    def test_alias_collision_and_broken_inline_target_fail(self) -> None:
        collision = copy.deepcopy(self.entries)
        collision["abt"]["aliases"] = ["Ace"]
        with self.assertRaisesRegex(source.ValidationError, "conflicts with a canonical"):
            source.validate_contract_entries(collision)

        broken = copy.deepcopy(self.entries)
        broken["10-in-the-zone"]["inline_terms"] = {
            "active builders": "not-published"
        }
        with self.assertRaisesRegex(source.ValidationError, "broken inline target"):
            source.validate_contract_entries(broken)

    def test_generation_is_deterministic_and_tracked_output_is_current(self) -> None:
        first, _ = source.build_production_source()
        second, _ = source.build_production_source()
        self.assertEqual(first, second)
        self.assertEqual(
            learn_glossary.PUBLIC_DATA_PATH.read_text(encoding="utf-8"),
            first,
        )


if __name__ == "__main__":
    unittest.main()
