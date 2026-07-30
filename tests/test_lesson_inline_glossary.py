from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "learn_glossary.py"
SPEC = importlib.util.spec_from_file_location("learn_glossary_iteration03", MODULE_PATH)
assert SPEC and SPEC.loader
learn_glossary = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(learn_glossary)

PANDOC = Path(r"C:\Program Files\Quarto\bin\tools\pandoc.exe")
FILTER = (
    ROOT
    / "site"
    / "_extensions"
    / "bms-inline-glossary"
    / "bms-inline-glossary.lua"
)
LOOKUP = ROOT / "site" / "assets" / "bms-glossary-lookup.json"
FIXTURES = ROOT / "tests" / "fixtures" / "iteration03"


class LessonInlineGlossaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not PANDOC.exists():
            raise unittest.SkipTest(f"Bundled Pandoc not found at {PANDOC}")
        data = json.loads(learn_glossary.PUBLIC_DATA_PATH.read_text(encoding="utf-8"))
        cls.entries = learn_glossary.validate_public_data(data)

    def render(
        self,
        source: str,
        *,
        lookup_path: Path = LOOKUP,
    ) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment["BMS_GLOSSARY_LOOKUP"] = str(lookup_path)
        return subprocess.run(
            [
                str(PANDOC),
                "--from",
                "markdown",
                "--to",
                "html",
                "--lua-filter",
                str(FILTER),
            ],
            cwd=ROOT,
            env=environment,
            input=source,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )

    def highlighted_source(self) -> str:
        return (FIXTURES / "highlighted-lesson.qmd").read_text(encoding="utf-8")

    def control_source(self) -> str:
        return (FIXTURES / "control-lesson.qmd").read_text(encoding="utf-8")

    def test_highlighted_fixture_uses_only_first_safe_canonical_occurrences(self) -> None:
        result = self.render(self.highlighted_source())
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.count('class="bms-inline-glossary"'), 2)
        self.assertIn('data-bms-glossary-slug="ace">Ace</a>', result.stdout)
        self.assertIn(
            'data-bms-glossary-slug="ahead-in-the-count">Ahead in the Race</a>',
            result.stdout,
        )
        self.assertIn('href="/learn/glossary/#ace"', result.stdout)
        self.assertIn('href="/learn/glossary/#ahead-in-the-count"', result.stdout)
        self.assertIn(
            "Ace appears again, and Ahead in the Count appears again",
            result.stdout,
        )

    def test_excluded_contexts_and_visible_wording_remain_unchanged(self) -> None:
        result = self.render(self.highlighted_source())
        self.assertEqual(result.returncode, 0, result.stderr)
        heading = result.stdout.split("</h1>", 1)[0]
        self.assertNotIn("bms-inline-glossary", heading)
        self.assertIn('href="https://example.com/ace"', result.stdout)
        self.assertIn("<code>ahead in the count in inline code</code>", result.stdout)
        self.assertIn("Ace and Ahead in the Race in a fenced code block.", result.stdout)
        self.assertIn('class="math inline"', result.stdout)
        self.assertRegex(
            result.stdout,
            r'class="fixture-raw">Ace and Ahead in the Race in raw\s+HTML\.</span>',
        )
        self.assertIn('alt="Ace and Ahead in the Race in a caption."', result.stdout)
        self.assertNotIn("data-bms-glossary-summary", result.stdout)
        self.assertNotIn("short_definition=", result.stdout)

    def test_control_lesson_has_no_inline_markup(self) -> None:
        result = self.render(self.control_source())
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("bms-inline-glossary", result.stdout)
        self.assertIn("Ace and Ahead in the Race appear in ordinary prose", result.stdout)

    def test_broad_terms_still_drive_all_backlinks(self) -> None:
        lesson = {
            "relative_path": "fixture.qmd",
            "categories": ["Beginner"],
            "tags": ["Checker Play"],
            "terms": ["ace", "active-builder", "ahead-in-the-count", "abt"],
            "highlighted_terms": ["ace", "ahead-in-the-count"],
            "title": "Fixture",
        }
        related = learn_glossary.validate_lessons([lesson], self.entries)
        self.assertEqual(
            set(related),
            {"ace", "active-builder", "ahead-in-the-count", "abt"},
        )
        self.assertEqual(
            lesson["terms"],
            ["ace", "active-builder", "ahead-in-the-count", "abt"],
        )
        self.assertEqual(
            lesson["highlighted_terms"],
            ["ace", "ahead-in-the-count"],
        )

    def test_absent_and_empty_highlighted_metadata_disable_highlighting(self) -> None:
        self.assertEqual(
            learn_glossary.highlighted_terms_from_metadata({}, "Fixture"),
            [],
        )
        self.assertEqual(
            learn_glossary.highlighted_terms_from_metadata(
                {"highlighted-terms": []},
                "Fixture",
            ),
            [],
        )

    def test_highlighted_metadata_must_be_a_list(self) -> None:
        with self.assertRaisesRegex(
            learn_glossary.ValidationError,
            "must be a YAML list",
        ):
            learn_glossary.highlighted_terms_from_metadata(
                {"highlighted-terms": "ace"},
                "Fixture",
            )

    def test_duplicate_normalized_values_fail(self) -> None:
        with self.assertRaisesRegex(
            learn_glossary.ValidationError,
            "duplicate normalized",
        ):
            learn_glossary.highlighted_terms_from_metadata(
                {"highlighted-terms": ["ace", "Ace"]},
                "Fixture",
            )

    def test_malformed_multi_word_slug_fails(self) -> None:
        with self.assertRaisesRegex(
            learn_glossary.ValidationError,
            "malformed",
        ):
            learn_glossary.highlighted_terms_from_metadata(
                {"highlighted-terms": ["active builder"]},
                "Fixture",
            )

    def test_unknown_alias_and_missing_broad_term_fail(self) -> None:
        base = {
            "relative_path": "fixture.qmd",
            "categories": ["Beginner"],
            "tags": ["Checker Play"],
            "terms": ["ace"],
            "title": "Fixture",
        }
        cases = (
            (
                {**base, "highlighted_terms": ["not-a-term"]},
                "unknown term slug",
            ),
            (
                {
                    **base,
                    "terms": ["ahead-in-the-count"],
                    "highlighted_terms": ["ahead-in-the-race"],
                },
                "uses alias slug",
            ),
            (
                {**base, "highlighted_terms": ["ahead-in-the-count"]},
                "missing from terms",
            ),
        )
        for lesson, message in cases:
            with self.subTest(message=message):
                with self.assertRaisesRegex(
                    learn_glossary.ValidationError,
                    message,
                ):
                    learn_glossary.validate_lessons([lesson], self.entries)

    def test_longest_valid_phrase_wins_without_partial_word_matches(self) -> None:
        source = """---
terms: [one-point, point]
highlighted-terms: [point, one-point]
---

Checkpoint is not a match. One Point comes first; point comes second.
"""
        result = self.render(
            source,
            lookup_path=FIXTURES / "longest-phrase-lookup.json",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn('>point</a> is not', result.stdout)
        first = result.stdout.index('data-bms-glossary-slug="one-point"')
        second = result.stdout.index('data-bms-glossary-slug="point"')
        self.assertLess(first, second)

    def test_ambiguous_canonical_alias_phrase_fails(self) -> None:
        source = """---
terms: [anchor, holding-point]
highlighted-terms: [anchor, holding-point]
---

Anchor and Holding Point.
"""
        result = self.render(
            source,
            lookup_path=FIXTURES / "ambiguous-phrase-lookup.json",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("ambiguous canonical or alias phrase", result.stderr)

    def test_existing_link_is_not_nested_and_missing_safe_match_warns(self) -> None:
        source = """---
terms: [ace]
highlighted-terms: [ace]
---

[Ace](https://example.com/ace)
"""
        result = self.render(source)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.count("<a "), 1)
        self.assertNotIn("bms-inline-glossary", result.stdout)
        self.assertIn("no safe prose occurrence for ace", result.stderr)

    def test_rendering_is_byte_deterministic_and_metadata_order_independent(self) -> None:
        first = self.render(self.highlighted_source())
        second_source = self.highlighted_source().replace(
            "  - ace\n  - ahead-in-the-count\n",
            "  - ahead-in-the-count\n  - ace\n",
        )
        second = self.render(second_source)
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(first.stdout.encode("utf-8"), second.stdout.encode("utf-8"))

    def test_generated_lookup_always_has_canonical_short_definitions(self) -> None:
        data = json.loads(LOOKUP.read_text(encoding="utf-8"))
        by_slug = {entry["slug"]: entry for entry in data["entries"]}
        for slug in ("ace", "active-builder", "ahead-in-the-count", "abt"):
            self.assertIsInstance(by_slug[slug]["short_definition"], str)
            self.assertTrue(by_slug[slug]["short_definition"])
        self.assertEqual(
            by_slug["ahead-in-the-count"]["aliases"],
            ["Ahead in the Race"],
        )
        self.assertEqual(
            by_slug["ahead-in-the-count"]["alias_slugs"],
            ["ahead-in-the-race"],
        )

    def test_client_hover_focus_and_slug_only_contract(self) -> None:
        javascript = (ROOT / "site" / "assets" / "bms-learn.js").read_text(
            encoding="utf-8"
        )
        self.assertIn("function canonicalShortDefinition(entries, slug)", javascript)
        self.assertIn("entry.short_definition", javascript)
        self.assertIn('link.addEventListener("mouseenter"', javascript)
        self.assertIn('link.addEventListener("focus"', javascript)
        self.assertIn('link.addEventListener("blur"', javascript)
        self.assertIn("link.dataset.bmsGlossarySlug", javascript)
        self.assertIn("inlineGlossaryTooltipPosition", javascript)
        self.assertIn('window.addEventListener("resize"', javascript)
        self.assertIn('window.addEventListener("scroll"', javascript)
        self.assertNotIn("dataset.bmsGlossarySummary", javascript)

    def test_real_lessons_do_not_highlight_unapproved_terms(self) -> None:
        lessons = learn_glossary.discover_lessons()
        highlighted = [
            lesson
            for lesson in lessons
            if lesson.get("highlighted_terms")
        ]
        self.assertEqual(highlighted, [])

    def test_real_lesson_has_no_unapproved_inline_glossary_links(self) -> None:
        source_path = (
            ROOT
            / "site"
            / "learn"
            / "cube"
            / "what-the-cube-is-asking.qmd"
        )
        result = self.render(source_path.read_text(encoding="utf-8"))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn('class="bms-inline-glossary"', result.stdout)
        self.assertIn("<code>Take point ~= risk / (risk + reward)</code>", result.stdout)
        self.assertNotIn("data-bms-glossary-summary", result.stdout)

    def test_real_lesson_unapproved_terms_do_not_create_public_backlinks(self) -> None:
        lessons = learn_glossary.discover_lessons()
        selected = next(
            lesson
            for lesson in lessons
            if lesson["relative_path"] == "cube/what-the-cube-is-asking.qmd"
        )
        related = learn_glossary.validate_lessons(lessons, self.entries)
        for slug in selected["terms"]:
            with self.subTest(slug=slug):
                self.assertNotIn(selected, related.get(slug, []))


if __name__ == "__main__":
    unittest.main()
