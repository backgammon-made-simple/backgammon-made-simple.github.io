from __future__ import annotations

import inspect
import json
import unittest
from unittest import mock

from scripts import glossary_source as source
from scripts import learn_glossary


def parsed_entry(
    term: str,
    slug: str,
    *,
    aliases: tuple[str, ...] = (),
    categories: tuple[str, ...] = ("checker play and tactics",),
    definition_links: tuple[tuple[str, str], ...] = (),
    related_terms: tuple[str, ...] = (),
    learning_tracks: tuple[str, ...] = (),
    full_definition: str | None = None,
) -> source.ParsedEntry:
    return source.ParsedEntry(
        term=term,
        slug=slug,
        aliases=aliases,
        short_definition=f"Short definition for {term}.",
        full_definition=full_definition or f"Full definition for {term}.",
        definition_links=definition_links,
        related_terms=related_terms,
        categories=categories,
        learning_tracks=learning_tracks,
    )


def legacy_entry(
    term: str,
    slug: str,
    *,
    aliases: tuple[tuple[str, str], ...] = (),
) -> dict[str, object]:
    return {
        "aliases": [
            {"slug": alias_slug, "term": alias_term}
            for alias_slug, alias_term in aliases
        ],
        "category": "language, rules, and culture",
        "definition": f"Legacy definition for {term}.",
        "slug": slug,
        "term": term,
    }


def legacy_data(*entries: dict[str, object]) -> dict[str, object]:
    return {
        "entries": sorted(
            entries,
            key=lambda item: (
                str(item["term"]).casefold(),
                str(item["slug"]),
            ),
        ),
        "schema_version": "1.0",
    }


class GlossarySourceMigrationTests(unittest.TestCase):
    def test_production_source_contract_excludes_workflow_and_task_files(self) -> None:
        self.assertEqual(
            source.CONFIRMED_SOURCE_PATH,
            learn_glossary.REPOSITORY_ROOT
            / "glossary_wip"
            / "confirmed-terms.md",
        )
        self.assertEqual(
            source.LEGACY_MIGRATION_PATH,
            learn_glossary.REPOSITORY_ROOT
            / "glossary_wip"
            / "legacy-unconfirmed-glossary.json",
        )
        self.assertEqual(source.PRODUCTION_SOURCE_PATH, learn_glossary.PUBLIC_DATA_PATH)
        implementation = inspect.getsource(source)
        self.assertNotIn("staged-terms.md", implementation)
        self.assertNotIn("comprehensive-list-of-terms.md", implementation)
        self.assertNotIn("task-management", implementation)
        source_runner = inspect.getsource(learn_glossary.run_glossary_source_command)
        self.assertIn('"glossary_source.py"', source_runner)

    def test_confirmed_entry_and_aliases_replace_same_slug_legacy_data(self) -> None:
        confirmed = parsed_entry(
            "Alpha",
            "alpha",
            aliases=("Approved Alpha",),
            categories=("analysis and probability",),
            full_definition="Confirmed full definition for Alpha.",
        )
        data, report = source.merge_confirmed_and_legacy(
            [confirmed],
            legacy_data(
                legacy_entry(
                    "Alpha",
                    "alpha",
                    aliases=(("old-alpha", "Old Alpha"),),
                ),
                legacy_entry("Beta", "beta"),
            ),
        )
        by_slug = {entry["slug"]: entry for entry in data["entries"]}
        self.assertEqual(set(by_slug), {"alpha"})
        self.assertEqual(
            by_slug["alpha"]["definition"],
            "Confirmed full definition for Alpha.",
        )
        self.assertEqual(
            by_slug["alpha"]["aliases"],
            [{"slug": "approved-alpha", "term": "Approved Alpha"}],
        )
        self.assertNotIn("old-alpha", json.dumps(by_slug["alpha"]))
        self.assertEqual(by_slug["alpha"]["category"], "analysis and probability")
        self.assertEqual(by_slug["alpha"]["categories"], ["analysis and probability"])
        self.assertEqual(report["confirmed_replaced_slugs"], ["alpha"])
        self.assertEqual(report["retained_legacy_entries"], 0)
        self.assertEqual(report["review_only_legacy_entries"], 1)

    def test_exact_confirmed_aka_absorbs_same_spelling_legacy_canonical(self) -> None:
        confirmed = parsed_entry(
            "Ahead in the Count",
            "ahead-in-the-count",
            aliases=("Ahead in the Race",),
        )
        data, report = source.merge_confirmed_and_legacy(
            [confirmed],
            legacy_data(
                legacy_entry("Ahead in the Count", "ahead-in-the-count"),
                legacy_entry("Ahead in the Race", "ahead-in-the-race"),
                legacy_entry("Beta", "beta"),
            ),
        )
        by_slug = {entry["slug"]: entry for entry in data["entries"]}
        self.assertNotIn("ahead-in-the-race", by_slug)
        self.assertEqual(
            by_slug["ahead-in-the-count"]["aliases"],
            [{"slug": "ahead-in-the-race", "term": "Ahead in the Race"}],
        )
        self.assertEqual(
            report["legacy_canonicals_absorbed_as_confirmed_aliases"],
            [
                {
                    "confirmed_slug": "ahead-in-the-count",
                    "legacy_slug": "ahead-in-the-race",
                    "term": "Ahead in the Race",
                }
            ],
        )

    def test_exact_confirmed_name_removes_matching_legacy_alias(self) -> None:
        confirmed = parsed_entry("Alpha", "alpha")
        data, report = source.merge_confirmed_and_legacy(
            [confirmed],
            legacy_data(
                legacy_entry("Alpha", "alpha"),
                legacy_entry(
                    "Beta",
                    "beta",
                    aliases=(("alpha-name", "Alpha"),),
                ),
            ),
        )
        self.assertEqual(
            [entry["slug"] for entry in data["entries"]],
            ["alpha"],
        )
        self.assertEqual(len(report["legacy_aliases_removed"]), 1)

    def test_normalized_confirmed_canonical_vs_legacy_alias_conflict_fails(self) -> None:
        confirmed = parsed_entry("Alpha Term", "alpha-term")
        with self.assertRaisesRegex(
            learn_glossary.ValidationError,
            "Normalized confirmed/legacy alias conflict",
        ):
            source.merge_confirmed_and_legacy(
                [confirmed],
                legacy_data(
                    legacy_entry("Alpha Term", "alpha-term"),
                    legacy_entry(
                        "Beta",
                        "beta",
                        aliases=(("alpha-term-alias", "Alpha-Term"),),
                    ),
                ),
            )

    def test_normalized_confirmed_alias_vs_legacy_canonical_conflict_fails(self) -> None:
        confirmed = parsed_entry(
            "Alpha",
            "alpha",
            aliases=("Legacy Term",),
        )
        with self.assertRaisesRegex(
            learn_glossary.ValidationError,
            "conflicts with retained legacy canonical",
        ):
            source.merge_confirmed_and_legacy(
                [confirmed],
                legacy_data(
                    legacy_entry("Alpha", "alpha"),
                    legacy_entry("Legacy-Term", "legacy-term"),
                ),
            )

    def test_duplicate_canonical_terms_slugs_and_alias_ownership_fail(self) -> None:
        cases = (
            (
                [parsed_entry("Alpha", "alpha"), parsed_entry("Alpha", "other")],
                "Duplicate canonical term",
            ),
            (
                [parsed_entry("Alpha", "alpha"), parsed_entry("Beta", "alpha")],
                "Duplicate canonical slug",
            ),
            (
                [
                    parsed_entry("Alpha", "alpha", aliases=("Shared",)),
                    parsed_entry("Beta", "beta", aliases=("Shared",)),
                ],
                "assigned to both",
            ),
        )
        for entries, message in cases:
            with self.subTest(message=message):
                with self.assertRaisesRegex(
                    learn_glossary.ValidationError,
                    message,
                ):
                    source.validate_name_conflicts(entries)

    def test_rich_fields_targets_multiple_and_zero_categories_survive(self) -> None:
        target = legacy_entry(
            "Target Term",
            "target-term",
            aliases=(("target-alias", "Target Alias"),),
        )
        confirmed_target = parsed_entry(
            "Target Term",
            "target-term",
            aliases=("Target Alias",),
        )
        rich = parsed_entry(
            "Rich Term",
            "rich-term",
            aliases=("Rich Alias",),
            categories=(
                "checker play and tactics",
                "strategy and position types",
            ),
            definition_links=(("Target Alias", "target-alias"),),
            related_terms=("Target Term", "Pending Related"),
            learning_tracks=("Checker Play",),
            full_definition="Target Alias appears in this full definition.",
        )
        uncategorized = parsed_entry(
            "Uncategorized",
            "uncategorized",
            categories=(),
        )
        data, report = source.merge_confirmed_and_legacy(
            [rich, uncategorized, confirmed_target],
            legacy_data(target),
        )
        by_slug = {entry["slug"]: entry for entry in data["entries"]}
        self.assertEqual(
            by_slug["rich-term"]["categories"],
            ["checker play and tactics", "strategy and position types"],
        )
        self.assertEqual(
            by_slug["rich-term"]["category"],
            "checker play and tactics",
        )
        self.assertEqual(by_slug["rich-term"]["learning_tracks"], ["Checker Play"])
        self.assertEqual(
            by_slug["rich-term"]["definition_links"],
            [{"slug": "target-term", "text": "Target Alias"}],
        )
        self.assertEqual(
            by_slug["rich-term"]["related_terms"],
            [
                {"slug": "target-term", "term": "Target Term"},
                {"term": "Pending Related"},
            ],
        )
        self.assertEqual(by_slug["uncategorized"]["categories"], [])
        self.assertNotIn("category", by_slug["uncategorized"])
        self.assertEqual(
            report["canonicalized_inline_targets"],
            [
                {
                    "authored_target": "target-alias",
                    "canonical_target": "target-term",
                    "entry_slug": "rich-term",
                    "visible": "Target Alias",
                }
            ],
        )
        self.assertEqual(
            report["unresolved_related_terms"],
            [{"entry_slug": "rich-term", "term": "Pending Related"}],
        )

    def test_unapproved_inline_target_remains_plain_text(self) -> None:
        confirmed = parsed_entry(
            "Alpha",
            "alpha",
            definition_links=(("Missing", "missing"),),
            full_definition="Missing is referenced.",
        )
        data, report = source.merge_confirmed_and_legacy(
            [confirmed],
            legacy_data(),
        )
        self.assertEqual(data["entries"][0]["definition_links"], [])
        self.assertEqual(
            report["unresolved_inline_targets"],
            [
                {
                    "entry_slug": "alpha",
                    "target_slug": "missing",
                    "visible": "Missing",
                }
            ],
        )

    def test_production_generation_matches_tracked_file_and_is_deterministic(self) -> None:
        first, first_report = source.build_production_source()
        second, second_report = source.build_production_source()
        self.assertEqual(first.encode("utf-8"), second.encode("utf-8"))
        self.assertEqual(first_report, second_report)
        self.assertEqual(
            source.PRODUCTION_SOURCE_PATH.read_text(encoding="utf-8"),
            first,
        )
        self.assertEqual(first_report["confirmed_entries"], 12)
        self.assertEqual(first_report["confirmed_aliases"], 4)
        self.assertEqual(first_report["retained_legacy_entries"], 0)
        self.assertEqual(first_report["retained_legacy_aliases"], 0)
        self.assertEqual(first_report["review_only_legacy_entries"], 613)
        self.assertEqual(first_report["review_only_legacy_aliases"], 181)
        self.assertEqual(first_report["final_entries"], 12)
        self.assertEqual(first_report["final_aliases"], 4)
        self.assertTrue(first_report["unresolved_inline_targets"])

    def test_manual_edit_drift_message_is_clear(self) -> None:
        generated, _report = source.build_production_source()
        fake_path = mock.Mock()
        fake_path.exists.return_value = True
        fake_path.read_text.return_value = generated + " "
        with mock.patch.object(source, "PRODUCTION_SOURCE_PATH", fake_path):
            with self.assertRaisesRegex(
                learn_glossary.ValidationError,
                "stale or manually edited",
            ):
                source.check_production_source()

    def test_multi_category_html_chips_are_pressable_and_complete(self) -> None:
        rich = parsed_entry(
            "Rich Term",
            "rich-term",
            categories=(
                "checker play and tactics",
                "strategy and position types",
            ),
        )
        data, _report = source.merge_confirmed_and_legacy(
            [rich],
            legacy_data(),
        )
        entries = source.validate_with_observed_counts(data)
        html = learn_glossary.build_entries_html(entries, {}, {})
        self.assertIn(
            'data-bms-categories="[&quot;checker play and tactics&quot;, '
            '&quot;strategy and position types&quot;]"',
            html,
        )
        self.assertEqual(html.count('data-bms-card-category="'), 2)
        self.assertEqual(html.count('aria-pressed="false"'), 2)

    def test_confirmed_values_replace_legacy_values_exactly(self) -> None:
        confirmed = {
            entry.slug: entry
            for entry in source.parse_confirmed_markdown(
                source.CONFIRMED_SOURCE_PATH.read_text(encoding="utf-8")
            )
        }
        production = json.loads(
            source.PRODUCTION_SOURCE_PATH.read_text(encoding="utf-8")
        )
        by_slug = {entry["slug"]: entry for entry in production["entries"]}
        for slug, parsed in confirmed.items():
            with self.subTest(slug=slug):
                generated = by_slug[slug]
                self.assertEqual(generated["term"], parsed.term)
                self.assertEqual(generated["short_definition"], parsed.short_definition)
                self.assertEqual(generated["definition"], parsed.full_definition)
                self.assertEqual(generated["categories"], list(parsed.categories))
                self.assertEqual(generated["learning_tracks"], list(parsed.learning_tracks))
                self.assertEqual(
                    [alias["term"] for alias in generated["aliases"]],
                    sorted(parsed.aliases, key=str.casefold),
                )

    def test_legacy_input_remains_separate_and_unmodified(self) -> None:
        legacy = json.loads(source.LEGACY_MIGRATION_PATH.read_text(encoding="utf-8"))
        production = json.loads(source.PRODUCTION_SOURCE_PATH.read_text(encoding="utf-8"))
        self.assertEqual(len(legacy["entries"]), 624)
        self.assertEqual(len(production["entries"]), 12)
        self.assertNotEqual(legacy, production)
        self.assertFalse(
            source.CONFIRMED_SOURCE_PATH.samefile(
                source.LEGACY_MIGRATION_PATH
            )
        )


if __name__ == "__main__":
    unittest.main()
