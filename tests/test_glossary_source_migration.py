from __future__ import annotations

import inspect
import json
import unittest

from scripts import glossary_source as source
from scripts import learn_glossary


def entry_block(
    term: str = "Sample Term",
    *,
    slug: str = "sample-term",
    status: str = "Confirmed",
    aliases: tuple[str, ...] = (),
    categories: tuple[str, ...] = ("Checker Play",),
    inline: tuple[tuple[str, str], ...] = (),
    related: tuple[str, ...] = (),
    added: str | None = "2026-07-30",
    usage_note: str | None = None,
    editorial_note: str | None = None,
) -> str:
    alias_lines = "\n".join(f"- {alias}" for alias in aliases) or "- None"
    category_lines = "\n".join(f"- {category}" for category in categories) or "- None"
    inline_lines = (
        "\n".join(f'- "{text}" -> `{target}`' for text, target in inline)
        or "- None"
    )
    related_lines = "\n".join(f"- {term}" for term in related) or "- None"
    added_field = f"\n**Added:** {added}\n" if added else ""
    usage = f"\n## Usage note\n\n{usage_note}\n" if usage_note else ""
    editorial = (
        f"\n## Editorial notes\n\n{editorial_note}\n" if editorial_note else ""
    )
    return f"""# {term}

**Status:** {status}

**Slug:** `{slug}`
{added_field}
## AKA

{alias_lines}

## Short definition

Short definition for {term}.

## Full definition

Full definition for {term} with visible phrase.
{usage}
## Inline terms

{inline_lines}

## Related words

{related_lines}

## Categories

{category_lines}

## Learning tracks

- None
{editorial}
---
"""


class UnifiedGlossarySourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source_text = source.GLOSSARY_SOURCE_PATH.read_text(encoding="utf-8")
        cls.parsed = source.parse_markdown(cls.source_text)
        cls.serialized, cls.report = source.build_production_source()
        cls.data = json.loads(cls.serialized)

    def test_only_unified_markdown_is_a_production_input(self) -> None:
        self.assertEqual(
            source.GLOSSARY_SOURCE_PATH,
            learn_glossary.REPOSITORY_ROOT / "glossary" / "glossary.md",
        )
        implementation = inspect.getsource(source.build_production_source)
        self.assertIn("GLOSSARY_SOURCE_PATH", implementation)
        self.assertNotIn("staged-terms", implementation)
        self.assertNotIn("comprehensive-list", implementation)
        module_source = inspect.getsource(source)
        self.assertNotIn("legacy-unconfirmed-glossary.json", module_source)
        self.assertNotIn("glossary_wip", module_source)

    def test_complete_migration_counts_and_statuses(self) -> None:
        self.assertEqual(len(self.parsed), 625)
        self.assertEqual(self.report["canonical_entries"], 625)
        self.assertEqual(self.report["confirmed_entries"], 12)
        self.assertEqual(self.report["legacy_unconfirmed_entries"], 613)
        self.assertEqual(self.report["aliases"], 184)
        self.assertEqual(len(self.data["entries"]), 625)

    def test_status_and_editorial_sections_do_not_leak_publicly(self) -> None:
        serialized = self.serialized
        self.assertNotIn('"status"', serialized.casefold())
        self.assertNotIn("editorial notes", serialized.casefold())
        self.assertNotIn("alias notes", serialized.casefold())
        by_slug = {entry.slug: entry for entry in self.parsed}
        self.assertIsNotNone(by_slug["blue-game"].usage_note)
        public = {entry["slug"]: entry for entry in self.data["entries"]}
        self.assertIn("usage_note", public["blue-game"])

    def test_required_aliases_resolve_to_canonical_records(self) -> None:
        expected = {
            "American Backgammon Tour": "abt",
            "Ahead in the Race": "ahead-in-the-count",
            "Cube": "doubling-cube",
            "Ace-Point": "one-point",
        }
        resolved = {}
        for entry in self.data["entries"]:
            for alias in entry["aliases"]:
                resolved[alias["term"]] = entry["slug"]
        self.assertEqual({key: resolved[key] for key in expected}, expected)

    def test_zero_one_and_multiple_categories_survive(self) -> None:
        parsed = source.parse_markdown(
            entry_block("Zero", slug="zero", categories=())
            + entry_block("One", slug="one", categories=("Checker Play",))
            + entry_block(
                "Multiple",
                slug="multiple",
                categories=("Checker Play", "Cube Action"),
            )
        )
        by_slug = {
            entry["slug"]: entry for entry in source.build_public_data(parsed)["entries"]
        }
        zero, one, multiple = by_slug["zero"], by_slug["one"], by_slug["multiple"]
        self.assertNotIn("category", zero)
        self.assertEqual(one["category"], one["categories"][0])
        self.assertEqual(multiple["category"], multiple["categories"][0])

    def test_generated_categories_follow_contract_order(self) -> None:
        rank = {name: index for index, name in enumerate(learn_glossary.GLOSSARY_CATEGORIES)}
        for entry in self.data["entries"]:
            with self.subTest(slug=entry["slug"]):
                positions = [rank[value] for value in entry["categories"]]
                self.assertEqual(positions, sorted(positions))

    def test_duplicate_and_unknown_categories_fail(self) -> None:
        duplicate = entry_block(
            categories=("Checker Play", "Checker Play")
        )
        with self.assertRaisesRegex(source.ValidationError, "repeats a category"):
            source.parse_markdown(duplicate)
        unknown = entry_block(categories=("Unknown",))
        with self.assertRaisesRegex(source.ValidationError, "Invalid glossary category"):
            source.parse_markdown(unknown)

    def test_name_and_alias_collisions_fail(self) -> None:
        text = entry_block("Alpha", slug="alpha", aliases=("Beta",)) + entry_block(
            "Beta", slug="beta"
        )
        with self.assertRaisesRegex(source.ValidationError, "Canonical and alias conflict"):
            source.parse_markdown(text)

    def test_broken_inline_target_fails(self) -> None:
        parsed = source.parse_markdown(
            entry_block(inline=(("visible phrase", "missing-target"),))
        )
        with self.assertRaisesRegex(source.ValidationError, "missing inline target"):
            source.build_public_data(parsed)

    def test_optional_added_date_and_notes_are_supported(self) -> None:
        parsed = source.parse_markdown(
            entry_block(
                added=None,
                usage_note="Public usage guidance.",
                editorial_note="Private migration note.",
            )
        )
        data = source.build_public_data(parsed)
        entry = data["entries"][0]
        self.assertNotIn("date_added", entry)
        self.assertEqual(entry["usage_note"], "Public usage guidance.")
        self.assertNotIn("Private migration note.", json.dumps(data))

    def test_generation_is_deterministic_and_tracked_source_is_current(self) -> None:
        first, _ = source.build_production_source()
        second, _ = source.build_production_source()
        self.assertEqual(first, second)
        self.assertEqual(
            learn_glossary.PUBLIC_DATA_PATH.read_text(encoding="utf-8"),
            first,
        )


if __name__ == "__main__":
    unittest.main()
