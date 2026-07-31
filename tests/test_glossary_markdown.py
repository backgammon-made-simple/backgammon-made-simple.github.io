from __future__ import annotations

import html
import json
import re
import unittest

from scripts import glossary_source
from scripts import learn_glossary


def public_entry(
    term: str,
    slug: str,
    *,
    aliases: tuple[str, ...] = (),
    short: str | None = None,
    definition: str | None = None,
    categories: tuple[str, ...] = ("Checker Play",),
    links: tuple[tuple[str, str], ...] = (),
    related: tuple[tuple[str, str | None], ...] = (),
) -> dict[str, object]:
    entry: dict[str, object] = {
        "aliases": [
            {"slug": glossary_source.alias_slug(alias), "term": alias}
            for alias in aliases
        ],
        "categories": list(categories),
        "definition": definition or f"Full definition for {term}.",
        "definition_links": [
            {"slug": target, "text": visible} for visible, target in links
        ],
        "learning_tracks": [],
        "related_terms": [
            {"term": label, **({"slug": target} if target else {})}
            for label, target in related
        ],
        "short_definition": short or f"Short definition for {term}.",
        "slug": slug,
        "term": term,
    }
    if categories:
        entry["category"] = categories[0]
    return entry


class GlossaryPageGenerationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.ace = public_entry("Ace", "ace")
        self.one_point = public_entry(
            "One-Point",
            "one-point",
            aliases=("Ace-Point",),
            short="The opponent's one-point.",
        )
        self.sample = public_entry(
            "Sample",
            "sample",
            definition=(
                "The ace point matters. Ace can also matter. "
                "A special phrase appears here."
            ),
            categories=("Checker Play", "Cube Action"),
            links=(("special phrase", "one-point"),),
            related=(("Ace-Point", "one-point"), ("Pending idea", None)),
        )
        self.entries = [self.ace, self.one_point, self.sample]

    def test_full_definitions_are_visible_and_short_definitions_are_not(self) -> None:
        output = learn_glossary.build_entries_html(self.entries, {}, {})
        self.assertEqual(
            output.count('class="bms-glossary-definition"'), len(self.entries)
        )
        self.assertNotIn("bms-glossary-short-definition", output)
        self.assertIn("The ace point matters.", output)

    def test_automatic_longest_alias_match_wins(self) -> None:
        output = learn_glossary.linked_definition_html(self.sample, self.entries)
        self.assertRegex(
            output,
            r'data-bms-glossary-slug="one-point"[^>]*>ace point</a>',
        )
        first_link = re.search(r'data-bms-glossary-slug="([^"]+)"', output)
        self.assertIsNotNone(first_link)
        self.assertEqual(first_link.group(1), "one-point")

    def test_self_links_are_prevented(self) -> None:
        entry = public_entry(
            "Ace",
            "ace",
            aliases=("Single",),
            definition="Ace and Single describe this entry.",
        )
        output = learn_glossary.linked_definition_html(entry, [entry])
        self.assertNotIn("data-bms-definition-link", output)

    def test_explicit_inline_mapping_overrides_automatic_matching(self) -> None:
        automatic = public_entry("Special Phrase", "special-phrase")
        sample = public_entry(
            "Sample",
            "sample",
            definition="A special phrase appears here.",
            links=(("special phrase", "one-point"),),
        )
        output = learn_glossary.linked_definition_html(
            sample, [automatic, self.one_point, sample]
        )
        self.assertIn('data-bms-glossary-slug="one-point"', output)
        self.assertNotIn('data-bms-glossary-slug="special-phrase"', output)

    def test_related_terms_are_links_only_when_resolved(self) -> None:
        output = learn_glossary.related_terms_html(self.sample)
        self.assertIn('href="/learn/glossary/#one-point"', output)
        self.assertIn(">Ace-Point</a>", output)
        self.assertIn("<li>Pending idea</li>", output)

    def test_multi_category_data_supports_each_filter(self) -> None:
        output = learn_glossary.build_entries_html([self.sample], {}, {})
        encoded = html.escape(
            json.dumps(["Checker Play", "Cube Action"], ensure_ascii=False),
            quote=True,
        )
        self.assertIn(f'data-bms-categories="{encoded}"', output)
        self.assertEqual(output.count("data-bms-card-category="), 2)

    def test_glossary_search_payload_includes_names_and_both_definitions(self) -> None:
        output = learn_glossary.build_entries_html([self.one_point], {}, {})
        self.assertIn("Ace-Point", output)
        self.assertIn("The opponent&#x27;s one-point.", output)
        self.assertIn("Full definition for One-Point.", output)
        self.assertIn("data-bms-alias-names=", output)

    def test_lookup_contains_canonical_short_and_full_definitions(self) -> None:
        lookup = json.loads(learn_glossary.build_lookup_data(self.entries, {}))
        one_point = next(
            entry for entry in lookup["entries"] if entry["slug"] == "one-point"
        )
        self.assertEqual(one_point["aliases"], ["Ace-Point"])
        self.assertEqual(one_point["short_definition"], "The opponent's one-point.")
        self.assertEqual(one_point["definition"], "Full definition for One-Point.")

    def test_generated_html_and_lookup_are_deterministic(self) -> None:
        first_html = learn_glossary.build_entries_html(self.entries, {}, {})
        second_html = learn_glossary.build_entries_html(self.entries, {}, {})
        self.assertEqual(first_html, second_html)
        self.assertEqual(
            learn_glossary.build_lookup_data(self.entries, {}),
            learn_glossary.build_lookup_data(self.entries, {}),
        )


if __name__ == "__main__":
    unittest.main()
