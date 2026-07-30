from __future__ import annotations

import copy
import json
import re
import tempfile
import unittest
from pathlib import Path

from scripts import glossary_source as mvp
from scripts import glossary_review_artifacts as artifacts
from scripts import learn_glossary


def entry_block(
    term: str,
    slug: str,
    *,
    aliases: tuple[str, ...] = (),
    short_definition: str = "A short definition.",
    full_definition: str = "A full definition with a visible phrase.",
    definition_links: tuple[tuple[str, str], ...] = (("visible phrase", "ace"),),
    related_terms: tuple[str, ...] = ("Ace",),
    categories: tuple[str, ...] = ("Language, rules, and culture",),
    learning_tracks: tuple[str, ...] = (),
    include_categories: bool = True,
) -> str:
    alias_lines = "\n".join(f"- {alias}" for alias in aliases) or "- None"
    link_lines = (
        "\n".join(
            f'- "{visible}" -> `{target}`'
            for visible, target in definition_links
        )
        or "- None selected yet."
    )
    related_lines = (
        "\n".join(f"- {related}" for related in related_terms)
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

**Added:** 2026-07-30

## AKA

{alias_lines}

## Short definition

{short_definition}

## Full definition

{full_definition}

## Inline terms

{link_lines}

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
                short_definition="Ace means one.",
                full_definition=(
                    "Ace means one: the one-point is also called the ace-point."
                ),
                definition_links=(
                    ("one-point", "one-point"),
                    ("ace-point", "one-point"),
                ),
                related_terms=("One-Point", "Ace-Point", "Unresolved Ace Term"),
            ),
            abt
            or entry_block(
                "ABT",
                "abt",
                aliases=("American Backgammon Tour",),
                short_definition="ABT is the American Backgammon Tour.",
                full_definition=(
                    "The American Backgammon Tour organizes "
                    "backgammon tournaments."
                ),
                definition_links=(("backgammon tournaments", "tournament"),),
                related_terms=("Tournament", "Match Play", "Standings"),
                categories=("Organizations and community",),
            ),
            active_builder
            or entry_block(
                "Active Builder",
                "active-builder",
                short_definition="An active builder can help make a point.",
                full_definition=(
                    'A builder\'s note: a spare checker in your outer board can '
                    '"make a point" in your home board.'
                ),
                definition_links=(
                    ("spare checker", "spare-checker"),
                    ("outer board", "outer-board"),
                    ("point", "point"),
                    ("home board", "home-board"),
                ),
                related_terms=("Builder", "Build One's Board", "Our Board"),
                categories=(
                    "Checker play and tactics",
                    "Strategy and position types",
                ),
                learning_tracks=("Checker Play", "Opening Play"),
            ),
        )
    )


class GlossaryMarkdownTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        review_data = learn_glossary.read_json(mvp.LEGACY_MIGRATION_PATH)
        cls.reference_entries = mvp.validate_with_observed_counts(review_data)

    def build_data(self, document: str | None = None) -> dict[str, object]:
        return mvp.build_public_data(
            mvp.parse_markdown(document or mvp_document()),
            self.reference_entries,
        )

    def test_positive_rich_contract_preserves_every_required_field(self) -> None:
        data = self.build_data()
        self.assertEqual(data["schema_version"], "1.0")
        entries = data["entries"]
        self.assertEqual(
            [entry["term"] for entry in entries],
            ["ABT", "Ace", "Active Builder"],
        )
        by_term = {entry["term"]: entry for entry in entries}
        self.assertEqual(
            set(by_term["Ace"]),
            {
                "aliases",
                "categories",
                "category",
                "date_added",
                "definition",
                "definition_links",
                "learning_tracks",
                "related_terms",
                "short_definition",
                "slug",
                "term",
            },
        )
        self.assertEqual(
            by_term["ABT"]["aliases"],
            [
                {
                    "slug": "american-backgammon-tour",
                    "term": "American Backgammon Tour",
                }
            ],
        )
        self.assertEqual(
            by_term["Ace"]["definition_links"],
            [
                {"slug": "one-point", "text": "one-point"},
                {"slug": "one-point", "text": "ace-point"},
            ],
        )
        self.assertEqual(
            by_term["Ace"]["related_terms"][1],
            {"slug": "one-point", "term": "Ace-Point"},
        )
        self.assertEqual(
            by_term["Ace"]["related_terms"][2],
            {"term": "Unresolved Ace Term"},
        )
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
        self.assertEqual(
            by_term["Active Builder"]["learning_tracks"],
            ["Checker Play", "Opening Play"],
        )

    def test_rich_fields_survive_html_and_lookup_generation(self) -> None:
        data = self.build_data()
        result = mvp.validate_current_build_compatibility(
            data,
            self.reference_entries,
        )
        self.assertEqual(result["canonical_entries"], 3)
        self.assertEqual(result["alias_entries"], 1)
        self.assertEqual(result["page_short_definitions"], 0)
        self.assertEqual(result["page_full_definitions"], 3)
        self.assertEqual(result["page_related_term_groups"], 3)
        self.assertEqual(result["definition_links"], 9)

        entries = data["entries"]
        html = learn_glossary.build_entries_html(entries, {}, {})
        self.assertIn('data-bms-definition-link="tournament"', html)
        self.assertIn(
            'data-bms-categories="[&quot;checker play and tactics&quot;, '
            '&quot;strategy and position types&quot;]"',
            html,
        )
        self.assertIn(
            'data-bms-tracks="[&quot;Checker Play&quot;, '
            '&quot;Opening Play&quot;]"',
            html,
        )
        self.assertIn("Unresolved Ace Term", html)

        lookup = json.loads(learn_glossary.build_lookup_data(entries, {}))
        active = next(
            entry for entry in lookup["entries"]
            if entry["term"] == "Active Builder"
        )
        self.assertEqual(
            active["learning_tracks"],
            ["Checker Play", "Opening Play"],
        )
        self.assertEqual(
            active["related_terms"][-1],
            {"term": "Our Board"},
        )
        self.assertIn("short_definition", active)
        self.assertIn("definition_links", active)

    def test_full_definitions_auto_link_canonical_terms_and_aliases(self) -> None:
        data = copy.deepcopy(self.build_data())
        ace = next(
            entry for entry in data["entries"]
            if entry["slug"] == "ace"
        )
        ace["definition"] = (
            "An Active Builder can appear on the American Backgammon Tour."
        )
        ace["definition_links"] = []
        rendered = learn_glossary.build_entries_html(data["entries"], {}, {})
        self.assertIn(
            '<a class="bms-inline-glossary" '
            'href="/learn/glossary/#active-builder" '
            'data-bms-glossary-slug="active-builder" '
            'data-bms-definition-link="active-builder">Active Builder</a>',
            rendered,
        )
        self.assertIn(
            '<a class="bms-inline-glossary" '
            'href="/learn/glossary/#abt" '
            'data-bms-glossary-slug="abt" '
            'data-bms-definition-link="abt">American Backgammon Tour</a>',
            rendered,
        )

    def test_auto_link_matching_does_not_link_inside_hyphenated_words(self) -> None:
        data = copy.deepcopy(self.build_data())
        ace = next(
            entry for entry in data["entries"]
            if entry["slug"] == "ace"
        )
        ace["definition"] = "Ace is distinct from ace-point terminology."
        ace["definition_links"] = []
        rendered = learn_glossary.build_entries_html(data["entries"], {}, {})
        self.assertEqual(
            rendered.count('data-bms-glossary-slug="ace"'),
            1,
        )
        self.assertNotIn(
            'data-bms-glossary-slug="ace">ace</a>-point',
            rendered,
        )

    def test_authored_definition_link_wins_over_longer_automatic_match(self) -> None:
        data = copy.deepcopy(self.build_data())
        ace = next(
            entry for entry in data["entries"]
            if entry["slug"] == "ace"
        )
        ace["definition"] = "American Backgammon Tour example."
        ace["definition_links"] = [
            {
                "slug": "active-builder",
                "text": "American Backgammon",
            }
        ]
        rendered = learn_glossary.build_entries_html(data["entries"], {}, {})
        self.assertIn(
            'data-bms-glossary-slug="active-builder" '
            'data-bms-definition-link="active-builder">'
            "American Backgammon</a> Tour",
            rendered,
        )

    def test_full_definition_paragraphs_stay_inside_the_glossary_wrapper(self) -> None:
        ace = entry_block(
            "Ace",
            "ace",
            full_definition="First full-definition paragraph.\n\nSecond paragraph.",
            definition_links=(),
        )
        data = self.build_data(mvp_document(ace=ace))
        rendered = learn_glossary.build_entries_html(data["entries"], {}, {})
        self.assertIn(
            '<div class="bms-glossary-definition">\n'
            "<p>First full-definition paragraph.</p>\n"
            "<p>Second paragraph.</p>\n"
            "</div>",
            rendered,
        )

    def test_zero_categories_are_valid_without_legacy_category(self) -> None:
        ace = entry_block(
            "Ace",
            "ace",
            full_definition="Ace has a visible phrase.",
            categories=(),
        )
        data = self.build_data(mvp_document(ace=ace))
        ace_entry = next(entry for entry in data["entries"] if entry["term"] == "Ace")
        self.assertEqual(ace_entry["categories"], [])
        self.assertNotIn("category", ace_entry)
        learn_glossary.validate_public_data(
            data,
            expected_canonical_entries=3,
            expected_alias_entries=1,
            reference_entries=self.reference_entries,
        )
        html = learn_glossary.build_entries_html(data["entries"], {}, {})
        ace_tag = next(
            tag for tag in html.splitlines()
            if 'id="ace"' in tag and "data-bms-glossary-entry" in tag
        )
        self.assertNotIn("data-bms-category=", ace_tag)
        self.assertIn('data-bms-categories="[]"', ace_tag)

    def test_yaml_sensitive_text_is_preserved_in_both_definitions(self) -> None:
        short = 'Builder\'s shorthand: "point" — safe.'
        full = 'Builder\'s note: "point" — safe, exact, and visible phrase.'
        active = entry_block(
            "Active Builder",
            "active-builder",
            short_definition=short,
            full_definition=full,
            definition_links=(("visible phrase", "ace"),),
            categories=(
                "Checker play and tactics",
                "Strategy and position types",
            ),
        )
        data = self.build_data(mvp_document(active_builder=active))
        entry = next(
            item for item in data["entries"] if item["term"] == "Active Builder"
        )
        self.assertEqual(entry["short_definition"], short)
        self.assertEqual(entry["definition"], full)
        self.assertEqual(json.loads(learn_glossary.json_text(data)), data)

    def test_duplicate_canonical_terms_and_slugs_fail(self) -> None:
        duplicate_term = "\n".join(
            (entry_block("Ace", "ace"), entry_block("Ace", "other-ace"))
        )
        with self.assertRaisesRegex(
            learn_glossary.ValidationError,
            "Duplicate canonical term",
        ):
            mvp.parse_markdown(duplicate_term)

        duplicate_slug = "\n".join(
            (entry_block("Ace", "shared"), entry_block("ABT", "shared"))
        )
        with self.assertRaisesRegex(
            learn_glossary.ValidationError,
            "Duplicate canonical slug",
        ):
            mvp.parse_markdown(duplicate_slug)

    def test_alias_collisions_and_punctuation_conflicts_fail(self) -> None:
        shared_alias = "\n".join(
            (
                entry_block("Ace", "ace", aliases=("Shared Lookup",)),
                entry_block("ABT", "abt", aliases=("Shared Lookup",)),
            )
        )
        with self.assertRaisesRegex(
            learn_glossary.ValidationError,
            "assigned to both",
        ):
            mvp.parse_markdown(shared_alias)

        canonical_conflict = "\n".join(
            (
                entry_block("ABT", "abt", aliases=("active-builder",)),
                entry_block("Active Builder", "active-builder"),
            )
        )
        with self.assertRaisesRegex(
            learn_glossary.ValidationError,
            "Canonical and alias conflict after normalization",
        ):
            mvp.parse_markdown(canonical_conflict)
        self.assertEqual(
            mvp.normalize_lookup(" ACTIVE---Builder "),
            mvp.normalize_lookup("active builder"),
        )

    def test_missing_short_and_full_definitions_fail(self) -> None:
        with self.assertRaisesRegex(
            learn_glossary.ValidationError,
            "requires a short definition",
        ):
            mvp.parse_markdown(
                entry_block("Ace", "ace", short_definition="")
            )
        with self.assertRaisesRegex(
            learn_glossary.ValidationError,
            "requires a full definition",
        ):
            mvp.parse_markdown(
                entry_block("Ace", "ace", full_definition="")
            )

    def test_missing_or_invalid_added_date_fails(self) -> None:
        missing = entry_block("Ace", "ace").replace(
            "**Added:** 2026-07-30\n\n",
            "",
        )
        with self.assertRaisesRegex(
            learn_glossary.ValidationError,
            "requires an Added field",
        ):
            mvp.parse_markdown(missing)

        invalid = entry_block("Ace", "ace").replace(
            "**Added:** 2026-07-30",
            "**Added:** 2026-02-30",
        )
        with self.assertRaisesRegex(
            learn_glossary.ValidationError,
            "invalid Added date",
        ):
            mvp.parse_markdown(invalid)

    def test_missing_malformed_invalid_and_repeated_categories_fail(self) -> None:
        with self.assertRaisesRegex(
            learn_glossary.ValidationError,
            "missing the Categories section",
        ):
            mvp.parse_markdown(
                entry_block("Ace", "ace", include_categories=False)
            )

        malformed = entry_block("Ace", "ace").replace(
            "- Language, rules, and culture",
            "Language, rules, and culture",
        )
        with self.assertRaisesRegex(
            learn_glossary.ValidationError,
            "must contain only Markdown list items",
        ):
            mvp.parse_markdown(malformed)

        with self.assertRaisesRegex(
            learn_glossary.ValidationError,
            "Invalid glossary category",
        ):
            mvp.parse_markdown(
                entry_block(
                    "Ace",
                    "ace",
                    categories=("Not a controlled category",),
                )
            )

        with self.assertRaisesRegex(
            learn_glossary.ValidationError,
            "repeats a category",
        ):
            mvp.parse_markdown(
                entry_block(
                    "Ace",
                    "ace",
                    categories=(
                        "Checker play and tactics",
                        "CHECKER PLAY AND TACTICS",
                    ),
                )
            )

    def test_malformed_alias_and_inline_mapping_fail(self) -> None:
        with self.assertRaisesRegex(
            learn_glossary.ValidationError,
            "Malformed alias or lookup value",
        ):
            mvp.parse_markdown(
                entry_block("ABT", "abt", aliases=('"Quoted Alias"',))
            )

        malformed_link = entry_block("Ace", "ace").replace(
            '- "visible phrase" -> `ace`',
            "- visible phrase -> ace",
        )
        with self.assertRaisesRegex(
            learn_glossary.ValidationError,
            "Malformed inline-term mapping",
        ):
            mvp.parse_markdown(malformed_link)

    def test_missing_or_absent_inline_link_targets_fail(self) -> None:
        absent_phrase = entry_block(
            "Ace",
            "ace",
            full_definition="No mapped words occur here.",
        )
        with self.assertRaisesRegex(
            learn_glossary.ValidationError,
            "does not occur",
        ):
            mvp.parse_markdown(absent_phrase)

        missing_target = entry_block(
            "Ace",
            "ace",
            full_definition="A visible phrase.",
            definition_links=(("visible phrase", "missing-target"),),
        )
        parsed = mvp.parse_markdown(mvp_document(ace=missing_target))
        with self.assertRaisesRegex(
            learn_glossary.ValidationError,
            "missing definition-link targets",
        ):
            mvp.build_public_data(parsed, self.reference_entries)

    def test_invalid_and_repeated_learning_tracks_fail(self) -> None:
        with self.assertRaisesRegex(
            learn_glossary.ValidationError,
            "invalid learning tracks",
        ):
            mvp.parse_markdown(
                entry_block(
                    "Ace",
                    "ace",
                    learning_tracks=("Unknown Track",),
                )
            )
        with self.assertRaisesRegex(
            learn_glossary.ValidationError,
            "repeats a learning track",
        ):
            mvp.parse_markdown(
                entry_block(
                    "Ace",
                    "ace",
                    learning_tracks=("Checker Play", "Checker Play"),
                )
            )

    def test_unstable_output_order_fails_reusable_validator(self) -> None:
        data = self.build_data()
        unstable = copy.deepcopy(data)
        unstable["entries"].reverse()
        with self.assertRaisesRegex(
            learn_glossary.ValidationError,
            "unstable output ordering",
        ):
            mvp.validate_current_build_compatibility(
                unstable,
                self.reference_entries,
            )

    def test_generation_is_byte_deterministic_and_refuses_production(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "fixture.md"
            first = root / "first.json"
            second = root / "second.json"
            source.write_text(mvp_document(), encoding="utf-8", newline="\n")
            first_result = mvp.generate_subset(source, first)
            second_result = mvp.generate_subset(source, second)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            self.assertEqual(first_result, second_result)
            self.assertEqual(first_result["canonical_entries"], 3)
            self.assertEqual(first_result["alias_entries"], 1)
            self.assertEqual(first_result["page_short_definitions"], 0)
            self.assertEqual(first_result["page_full_definitions"], 3)
            self.assertEqual(first_result["page_related_term_groups"], 3)
            self.assertEqual(first_result["lookup_entries"], 3)

            with self.assertRaisesRegex(
                learn_glossary.ValidationError,
                "Refusing to overwrite",
            ):
                mvp.generate_subset(source, learn_glossary.PUBLIC_DATA_PATH)

    def test_inspection_artifacts_preserve_rich_lookup_and_preview_contract(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            input_json = root / "mvp.json"
            lookup_path = root / "lookup.json"
            entries_path = root / "entries.html"
            preview_path = root / "preview.html"
            input_json.write_text(
                learn_glossary.json_text(self.build_data()),
                encoding="utf-8",
                newline="\n",
            )

            result = artifacts.generate_artifacts(
                input_json,
                lookup_path,
                entries_path,
                preview_path,
            )

            self.assertEqual(result["entries"], 3)
            self.assertGreater(result["canonical_targets"], 0)
            self.assertTrue(lookup_path.stat().st_size)
            self.assertTrue(entries_path.stat().st_size)
            self.assertTrue(preview_path.stat().st_size)

            lookup = json.loads(lookup_path.read_text(encoding="utf-8"))
            self.assertEqual(
                {entry["term"] for entry in lookup["entries"]},
                {"Ace", "ABT", "Active Builder"},
            )
            active = next(
                entry for entry in lookup["entries"]
                if entry["term"] == "Active Builder"
            )
            self.assertEqual(
                active["categories"],
                ["checker play and tactics", "strategy and position types"],
            )
            for field in (
                "aliases",
                "short_definition",
                "definition",
                "categories",
                "definition_links",
                "related_terms",
                "learning_tracks",
            ):
                self.assertIn(field, active)

            entries_html = entries_path.read_text(encoding="utf-8")
            self.assertEqual(entries_html.count("<h4>See also</h4>"), 3)
            self.assertEqual(
                entries_html.count('class="bms-glossary-short-definition"'),
                0,
            )
            self.assertEqual(
                entries_html.count('class="bms-glossary-definition"'),
                3,
            )
            self.assertIn("American Backgammon Tour", entries_html)
            self.assertIn("Strategy and Position Types", entries_html)

            preview_html = preview_path.read_text(encoding="utf-8")
            self.assertIn("<style>", preview_html)
            self.assertIn("<script>", preview_html)
            self.assertIn('id="bms-search-input"', preview_html)
            self.assertIn(
                'input.addEventListener("input", updateSearch)',
                preview_html,
            )
            self.assertIn("American Backgammon Tour", preview_html)
            self.assertEqual(
                preview_html.count('class="bms-inline-tooltip"'),
                1,
            )
            self.assertIn(
                'document.addEventListener("pointerover"',
                preview_html,
            )
            self.assertIn(
                'document.addEventListener("focusin"',
                preview_html,
            )
            self.assertIn(
                "tooltipSummary.textContent = target.short_definition",
                preview_html,
            )
            self.assertIn('href="#one-point"', preview_html)
            target_slugs = re.findall(
                r'data-bms-definition-link="([^"]+)"',
                preview_html,
            )
            for target_slug in target_slugs:
                self.assertIn(f'href="#{target_slug}"', preview_html)
                self.assertIn(f'id="{target_slug}"', preview_html)
            self.assertEqual(preview_html.count("<h4>See also</h4>"), 3)
            self.assertNotIn('src="', preview_html)
            self.assertNotIn('href="http', preview_html)

    def test_clicking_either_active_builder_category_returns_active_builder(
        self,
    ) -> None:
        data = self.build_data()
        lookup = artifacts.build_preview_lookup(
            data["entries"],
            self.reference_entries,
        )
        self.assertEqual(
            lookup["category_index"]["checker play and tactics"],
            ["active-builder"],
        )
        self.assertEqual(
            lookup["category_index"]["strategy and position types"],
            ["active-builder"],
        )

        preview = artifacts.build_preview_html(
            data["entries"],
            learn_glossary.build_entries_html(data["entries"], {}, {}),
            lookup,
        )
        self.assertIn(
            'const chip = event.target.closest("[data-bms-card-category]")',
            preview,
        )
        self.assertIn(
            "if (chip) applyCategory(chip.dataset.bmsCardCategory)",
            preview,
        )
        self.assertIn('button[aria-pressed="true"]', preview)

    def test_category_filter_expands_all_matching_entries(self) -> None:
        data = copy.deepcopy(self.build_data())
        ace = next(
            entry for entry in data["entries"] if entry["slug"] == "ace"
        )
        ace["categories"] = [
            "checker play and tactics",
            "language, rules, and culture",
        ]
        ace["category"] = "checker play and tactics"

        lookup = artifacts.build_preview_lookup(
            data["entries"],
            self.reference_entries,
        )
        self.assertEqual(
            lookup["category_index"]["checker play and tactics"],
            ["ace", "active-builder"],
        )
        preview = artifacts.build_preview_html(
            data["entries"],
            learn_glossary.build_entries_html(data["entries"], {}, {}),
            lookup,
        )
        self.assertIn("showEntries(matchingSlugs, true)", preview)
        self.assertIn("if (expand) entry.open = true", preview)

    def test_inline_hover_summary_uses_canonical_short_definition(self) -> None:
        data = self.build_data()
        reference_entries = copy.deepcopy(self.reference_entries)
        one_point = next(
            entry for entry in reference_entries
            if entry["slug"] == "one-point"
        )
        one_point["short_definition"] = "Canonical one-point summary."
        lookup = artifacts.build_preview_lookup(
            data["entries"],
            reference_entries,
        )
        target = next(
            entry for entry in lookup["canonical_targets"]
            if entry["slug"] == "one-point"
        )
        self.assertEqual(
            target["short_definition"],
            "Canonical one-point summary.",
        )

        preview = artifacts.build_preview_html(
            data["entries"],
            learn_glossary.build_entries_html(data["entries"], {}, {}),
            lookup,
        )
        link = re.search(
            r'<a class="bms-inline-term"[^>]+'
            r'data-bms-definition-link="one-point"[^>]*>[^<]+</a>',
            preview,
        )
        self.assertIsNotNone(link)
        self.assertNotIn("Canonical one-point summary.", link.group(0))
        self.assertEqual(preview.count("Canonical one-point summary."), 1)
        self.assertIn(
            "tooltipSummary.textContent = target.short_definition",
            preview,
        )

    def test_canonical_short_definition_change_updates_hover_without_link_edit(
        self,
    ) -> None:
        data = self.build_data()
        linking_entry_before = copy.deepcopy(
            next(entry for entry in data["entries"] if entry["slug"] == "ace")
        )
        first_reference = copy.deepcopy(self.reference_entries)
        second_reference = copy.deepcopy(self.reference_entries)
        next(
            entry for entry in first_reference
            if entry["slug"] == "one-point"
        )["short_definition"] = "First canonical summary."
        next(
            entry for entry in second_reference
            if entry["slug"] == "one-point"
        )["short_definition"] = "Revised canonical summary."

        first_lookup = artifacts.build_preview_lookup(
            data["entries"],
            first_reference,
        )
        second_lookup = artifacts.build_preview_lookup(
            data["entries"],
            second_reference,
        )
        first_target = next(
            entry for entry in first_lookup["canonical_targets"]
            if entry["slug"] == "one-point"
        )
        second_target = next(
            entry for entry in second_lookup["canonical_targets"]
            if entry["slug"] == "one-point"
        )
        self.assertEqual(
            first_target["short_definition"],
            "First canonical summary.",
        )
        self.assertEqual(
            second_target["short_definition"],
            "Revised canonical summary.",
        )
        self.assertEqual(
            next(entry for entry in data["entries"] if entry["slug"] == "ace"),
            linking_entry_before,
        )
        fragment = artifacts.preview_fragment(
            learn_glossary.build_entries_html(data["entries"], {}, {})
        )
        self.assertNotIn(
            "First canonical summary.",
            fragment,
        )
        self.assertNotIn(
            "Revised canonical summary.",
            fragment,
        )

    def test_alias_resolves_to_canonical_entry_and_short_definition(self) -> None:
        data = self.build_data()
        lookup = artifacts.build_preview_lookup(
            data["entries"],
            self.reference_entries,
        )
        canonical = artifacts.resolve_lookup_entry(lookup, "ABT")
        alias = artifacts.resolve_lookup_entry(
            lookup,
            "American Backgammon Tour",
        )
        self.assertIsNotNone(canonical)
        self.assertIsNotNone(alias)
        self.assertEqual(alias["slug"], "abt")
        self.assertEqual(alias["term"], "ABT")
        self.assertEqual(
            alias["short_definition"],
            canonical["short_definition"],
        )


if __name__ == "__main__":
    unittest.main()
