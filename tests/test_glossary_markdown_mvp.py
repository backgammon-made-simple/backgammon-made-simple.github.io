from __future__ import annotations

import copy
import json
import shutil
import unittest
import uuid
from pathlib import Path

from scripts import glossary_markdown_mvp as mvp
from scripts import learn_glossary


ROOT = Path(__file__).resolve().parents[1]


def entry_block(
    term: str,
    slug: str,
    *,
    aliases: tuple[str, ...] = (),
    short_definition: str = "A short definition.",
    full_definition: str = "A full definition.",
    inline_terms: tuple[tuple[str, str], ...] = (("visible phrase", "ace"),),
    related_words: tuple[str, ...] = ("Ace",),
    categories: tuple[str, ...] = ("Language, rules, and culture",),
    learning_tracks: tuple[str, ...] = (),
    include_categories: bool = True,
) -> str:
    alias_lines = "\n".join(f"- {alias}" for alias in aliases) or "- None"
    inline_lines = (
        "\n".join(
            f'- "{visible}" -> `{target}`'
            for visible, target in inline_terms
        )
        or "- None selected yet."
    )
    related_lines = (
        "\n".join(f"- {related}" for related in related_words)
        or "- None selected yet."
    )
    category_section = ""
    if include_categories:
        category_lines = "\n".join(f"- {category}" for category in categories)
        category_section = f"\n## Categories\n\n{category_lines}\n"
    track_lines = (
        "\n".join(f"- {track}" for track in learning_tracks)
        or "- None"
    )
    return f"""# {term}

**Status:** Controlled test entry

**Slug:** `{slug}`

## AKA

{alias_lines}

## Short definition

{short_definition}

## Full definition

{full_definition}

## Inline terms

{inline_lines}

## Related words

{related_lines}
{category_section}
## Learning tracks

{track_lines}

## Generation notes

Test-only editorial note that must not be emitted.
"""


def mvp_document(
    *,
    ace: str | None = None,
    abt: str | None = None,
    active_builder: str | None = None,
) -> str:
    return "\n---\n---\n\n".join(
        (
            ace
            or entry_block(
                "Ace",
                "ace",
                full_definition=(
                    "In backgammon, ace means one. It can describe rolling a one."
                ),
                inline_terms=(("one-point", "one-point"),),
                related_words=("One-Point",),
            ),
            abt
            or entry_block(
                "ABT",
                "abt",
                aliases=("American Backgammon Tour",),
                full_definition=(
                    "The American Backgammon Tour is a series of tournaments."
                ),
                inline_terms=(("backgammon tournaments", "tournament"),),
                related_words=("Tournament",),
                categories=("Organizations and community",),
            ),
            active_builder
            or entry_block(
                "Active Builder",
                "active-builder",
                full_definition=(
                    'A builder\'s note: "make the point" on a future roll.'
                ),
                inline_terms=(
                    ("spare checker", "spare-checker"),
                    ("home board", "home-board"),
                ),
                related_words=("Builder", "Build One's Board"),
                categories=(
                    "Checker play and tactics",
                    "Strategy and position types",
                ),
            ),
        )
    )


class GlossaryMarkdownMvpTests(unittest.TestCase):
    def test_positive_contract_alias_categories_and_authoring_fields(self) -> None:
        parsed = mvp.parse_markdown(mvp_document())
        self.assertEqual([entry.term for entry in parsed], list(mvp.MVP_TERMS))
        self.assertEqual(
            parsed[1].aliases,
            ("American Backgammon Tour",),
        )
        self.assertEqual(
            parsed[2].inline_terms,
            (
                ("spare checker", "spare-checker"),
                ("home board", "home-board"),
            ),
        )
        self.assertEqual(
            parsed[2].related_words,
            ("Builder", "Build One's Board"),
        )

        data = mvp.build_public_data(parsed)
        self.assertEqual(data["schema_version"], "1.0")
        entries = data["entries"]
        self.assertEqual(
            [entry["term"] for entry in entries],
            ["ABT", "Ace", "Active Builder"],
        )
        by_term = {entry["term"]: entry for entry in entries}
        self.assertEqual(
            by_term["ABT"]["aliases"],
            [
                {
                    "slug": "american-backgammon-tour",
                    "term": "American Backgammon Tour",
                }
            ],
        )
        self.assertNotIn("categories", by_term["Ace"])
        self.assertEqual(
            by_term["Active Builder"]["categories"],
            [
                "checker play and tactics",
                "strategy and position types",
            ],
        )
        self.assertEqual(
            by_term["Active Builder"]["category"],
            "checker play and tactics",
        )
        for omitted in (
            "short_definition",
            "inline_terms",
            "related_words",
            "learning_tracks",
            "generation_notes",
            "status",
        ):
            self.assertNotIn(omitted, by_term["Active Builder"])

    def test_yaml_sensitive_text_is_preserved_in_json(self) -> None:
        full_definition = 'A builder\'s note: "make the point" — safely.'
        document = mvp_document(
            active_builder=entry_block(
                "Active Builder",
                "active-builder",
                full_definition=full_definition,
                categories=(
                    "Checker play and tactics",
                    "Strategy and position types",
                ),
            )
        )
        data = mvp.build_public_data(mvp.parse_markdown(document))
        entry = next(
            item for item in data["entries"] if item["term"] == "Active Builder"
        )
        self.assertEqual(entry["definition"], full_definition)
        serialized = learn_glossary.json_text(data)
        self.assertEqual(json.loads(serialized), data)
        self.assertIn("builder's note:", serialized)
        self.assertIn('\\"make the point\\"', serialized)
        self.assertIn("— safely.", serialized)

    def test_duplicate_canonical_terms_fail(self) -> None:
        document = "\n".join(
            (
                entry_block("Ace", "ace"),
                entry_block("Ace", "other-ace"),
            )
        )
        with self.assertRaisesRegex(
            learn_glossary.ValidationError,
            "Duplicate canonical term",
        ):
            mvp.parse_markdown(document)

    def test_duplicate_canonical_slugs_fail(self) -> None:
        document = "\n".join(
            (
                entry_block("Ace", "shared"),
                entry_block("ABT", "shared"),
            )
        )
        with self.assertRaisesRegex(
            learn_glossary.ValidationError,
            "Duplicate canonical slug",
        ):
            mvp.parse_markdown(document)

    def test_alias_assigned_to_different_entries_fails(self) -> None:
        document = "\n".join(
            (
                entry_block("Ace", "ace", aliases=("Shared Lookup",)),
                entry_block("ABT", "abt", aliases=("Shared Lookup",)),
            )
        )
        with self.assertRaisesRegex(
            learn_glossary.ValidationError,
            "assigned to both",
        ):
            mvp.parse_markdown(document)

    def test_canonical_alias_punctuation_normalization_conflict_fails(self) -> None:
        document = "\n".join(
            (
                entry_block("ABT", "abt", aliases=("active-builder",)),
                entry_block("Active Builder", "active-builder"),
            )
        )
        with self.assertRaisesRegex(
            learn_glossary.ValidationError,
            "Canonical and alias conflict after normalization",
        ):
            mvp.parse_markdown(document)
        self.assertEqual(
            mvp.normalize_lookup("  ACTIVE---Builder "),
            mvp.normalize_lookup("active builder"),
        )

    def test_missing_short_definition_fails(self) -> None:
        document = entry_block("Ace", "ace", short_definition="")
        with self.assertRaisesRegex(
            learn_glossary.ValidationError,
            "requires a short definition",
        ):
            mvp.parse_markdown(document)

    def test_missing_full_definition_fails(self) -> None:
        document = entry_block("Ace", "ace", full_definition="")
        with self.assertRaisesRegex(
            learn_glossary.ValidationError,
            "requires a full definition",
        ):
            mvp.parse_markdown(document)

    def test_missing_and_malformed_categories_fail(self) -> None:
        missing = entry_block(
            "Ace",
            "ace",
            include_categories=False,
        )
        with self.assertRaisesRegex(
            learn_glossary.ValidationError,
            "missing the Categories section",
        ):
            mvp.parse_markdown(missing)

        malformed = entry_block(
            "Ace",
            "ace",
            categories=("Language, rules, and culture",),
        ).replace(
            "- Language, rules, and culture",
            "Language, rules, and culture",
        )
        with self.assertRaisesRegex(
            learn_glossary.ValidationError,
            "must contain only Markdown list items",
        ):
            mvp.parse_markdown(malformed)

    def test_invalid_and_repeated_categories_fail(self) -> None:
        invalid = entry_block(
            "Ace",
            "ace",
            categories=("Not a controlled category",),
        )
        with self.assertRaisesRegex(
            learn_glossary.ValidationError,
            "Invalid glossary category",
        ):
            mvp.parse_markdown(invalid)

        repeated = entry_block(
            "Ace",
            "ace",
            categories=(
                "Checker play and tactics",
                "CHECKER PLAY AND TACTICS",
            ),
        )
        with self.assertRaisesRegex(
            learn_glossary.ValidationError,
            "repeats a category",
        ):
            mvp.parse_markdown(repeated)

    def test_multiword_alias_passes_and_malformed_alias_fails(self) -> None:
        parsed = mvp.parse_markdown(
            entry_block(
                "ABT",
                "abt",
                aliases=("American Backgammon Tour",),
            )
        )
        self.assertEqual(parsed[0].aliases, ("American Backgammon Tour",))
        self.assertEqual(
            mvp.alias_slug(parsed[0].aliases[0]),
            "american-backgammon-tour",
        )

        malformed = entry_block(
            "ABT",
            "abt",
            aliases=('"Quoted Alias"',),
        )
        with self.assertRaisesRegex(
            learn_glossary.ValidationError,
            "Malformed alias or lookup value",
        ):
            mvp.parse_markdown(malformed)

    def test_unstable_output_order_fails_current_validator(self) -> None:
        data = mvp.build_public_data(mvp.parse_markdown(mvp_document()))
        unstable = copy.deepcopy(data)
        unstable["entries"].reverse()
        with self.assertRaisesRegex(
            learn_glossary.ValidationError,
            "unstable output ordering",
        ):
            mvp.validate_current_build_compatibility(unstable)

    def test_generation_is_byte_deterministic_and_refuses_production(self) -> None:
        runtime_root = ROOT / "task-work" / "W3W-REGRESSION-01" / "runtime"
        root = runtime_root / f"glossary-mvp-{uuid.uuid4().hex}"
        root.mkdir(parents=True)
        try:
            source = root / "fixture.md"
            first = root / "first.json"
            second = root / "second.json"
            source.write_text(mvp_document(), encoding="utf-8", newline="\n")
            first_result = mvp.generate(source, first)
            second_result = mvp.generate(source, second)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            self.assertEqual(first_result, second_result)
            self.assertEqual(first_result["canonical_entries"], 3)
            self.assertEqual(first_result["alias_entries"], 1)
            self.assertEqual(first_result["page_definitions"], 3)
            self.assertEqual(first_result["lookup_entries"], 3)

            with self.assertRaisesRegex(
                learn_glossary.ValidationError,
                "Refusing to overwrite",
            ):
                mvp.generate(source, learn_glossary.PUBLIC_DATA_PATH)
        finally:
            shutil.rmtree(root)


if __name__ == "__main__":
    unittest.main()
