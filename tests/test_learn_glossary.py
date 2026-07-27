from __future__ import annotations

import importlib.util
import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "learn_glossary.py"
SPEC = importlib.util.spec_from_file_location("learn_glossary", MODULE_PATH)
assert SPEC and SPEC.loader
learn_glossary = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(learn_glossary)


class LearnGlossaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data = json.loads(
            learn_glossary.PUBLIC_DATA_PATH.read_text(encoding="utf-8")
        )
        cls.entries = learn_glossary.validate_public_data(cls.data)
        cls.lessons = learn_glossary.discover_lessons()
        cls.related = learn_glossary.validate_lessons(cls.lessons, cls.entries)
        cls.research_articles = learn_glossary.discover_research_articles()
        cls.related_research = learn_glossary.validate_research_articles(
            cls.research_articles,
            cls.entries,
        )

    def test_public_safe_integrity_and_expected_counts(self) -> None:
        self.assertEqual(len(self.entries), 624)
        self.assertEqual(
            sum(len(entry["aliases"]) for entry in self.entries),
            181,
        )
        self.assertEqual(
            set(self.data),
            {"schema_version", "entries"},
        )

    def test_forbidden_fields_do_not_leak(self) -> None:
        learn_glossary.assert_no_forbidden_keys(self.data)
        learn_glossary.assert_no_forbidden_text(
            learn_glossary.PUBLIC_DATA_PATH.read_text(encoding="utf-8"),
            "test public data",
        )
        for path in [
            learn_glossary.GENERATED_ENTRIES_PATH,
            *learn_glossary.GLOSSARY_ROOT.glob("*/index.qmd"),
        ]:
            learn_glossary.assert_no_forbidden_text(
                path.read_text(encoding="utf-8"),
                str(path.relative_to(ROOT)),
            )

    def test_canonical_and_alias_mapping(self) -> None:
        canonical = {entry["slug"]: entry for entry in self.entries}
        alias_to_canonical = {
            alias["slug"]: entry["slug"]
            for entry in self.entries
            for alias in entry["aliases"]
        }
        self.assertNotIn("accept-a-double", canonical)
        self.assertEqual(alias_to_canonical["accept-a-double"], "take")
        self.assertEqual(alias_to_canonical["cube-ownership"], "own-the-cube")
        self.assertEqual(len(alias_to_canonical), 181)

    def test_lesson_metadata_uses_frozen_taxonomy_and_canonical_terms(self) -> None:
        self.assertEqual(len(self.lessons), 7)
        canonical = {entry["slug"] for entry in self.entries}
        for lesson in self.lessons:
            self.assertTrue(set(lesson["categories"]).issubset(learn_glossary.DIFFICULTIES))
            self.assertTrue(set(lesson["tags"]).issubset(learn_glossary.TRACKS))
            self.assertTrue(set(lesson["terms"]).issubset(canonical))

    def test_related_lessons_come_only_from_explicit_metadata(self) -> None:
        expected = {
            slug: sorted(
                lesson["relative_path"]
                for lesson in self.lessons
                if slug in lesson["terms"]
            )
            for slug in {term for lesson in self.lessons for term in lesson["terms"]}
        }
        actual = {
            slug: sorted(lesson["relative_path"] for lesson in lessons)
            for slug, lessons in self.related.items()
        }
        self.assertEqual(actual, expected)

    def test_related_research_comes_only_from_explicit_metadata(self) -> None:
        expected = {
            "equity": ["research/sage-vs-gnu-additional-details.qmd"],
            "error-rate": ["research/sage-vs-gnu-additional-details.qmd"],
            "rollout": ["research/sage-vs-gnu-additional-details.qmd"],
        }
        actual = {
            slug: sorted(
                str(article["relative_path"]) for article in articles
            )
            for slug, articles in self.related_research.items()
        }
        self.assertEqual(actual, expected)

    def test_routes_are_unique_and_alias_routes_are_absent(self) -> None:
        canonical_routes = {
            f"/learn/glossary/{entry['slug']}/" for entry in self.entries
        }
        self.assertEqual(len(canonical_routes), 624)
        alias_slugs = {
            alias["slug"]
            for entry in self.entries
            for alias in entry["aliases"]
        }
        self.assertFalse(
            any(
                (learn_glossary.GLOSSARY_ROOT / slug / "index.qmd").exists()
                for slug in alias_slugs
            )
        )

    def test_generated_internal_learn_links_have_targets(self) -> None:
        lesson_routes = {lesson["route"] for lesson in self.lessons}
        valid_routes = (
            {"/learn/", "/learn/lesson-finder/", "/learn/glossary/"}
            | lesson_routes
            | {f"/learn/glossary/{entry['slug']}/" for entry in self.entries}
        )
        href_pattern = re.compile(r'href="([^"]+)"')
        paths = [
            learn_glossary.GENERATED_ENTRIES_PATH,
            *learn_glossary.GLOSSARY_ROOT.glob("*/index.qmd"),
        ]
        for path in paths:
            for href in href_pattern.findall(path.read_text(encoding="utf-8")):
                if not href.startswith("/learn/"):
                    continue
                route = href.split("?", 1)[0].split("#", 1)[0]
                self.assertIn(
                    route,
                    valid_routes,
                    f"{path.relative_to(ROOT)} contains broken route {route}",
                )

    def test_generation_is_deterministic_and_current(self) -> None:
        first = learn_glossary.generated_outputs(
            self.entries,
            self.related,
            self.related_research,
        )
        second = learn_glossary.generated_outputs(
            self.entries,
            self.related,
            self.related_research,
        )
        self.assertEqual(first, second)
        for path, expected in first.items():
            self.assertEqual(path.read_text(encoding="utf-8"), expected)

    def test_amendment_page_structure_and_shared_social_metadata(self) -> None:
        learn_landing = (learn_glossary.LEARN_ROOT / "index.qmd").read_text(
            encoding="utf-8"
        )
        lesson_finder = (
            learn_glossary.LEARN_ROOT / "lesson-finder" / "index.qmd"
        ).read_text(encoding="utf-8")
        listing_template = (
            learn_glossary.LEARN_ROOT / "_lesson-listing.ejs.md"
        ).read_text(encoding="utf-8")
        entries_html = learn_glossary.GENERATED_ENTRIES_PATH.read_text(
            encoding="utf-8"
        )

        self.assertNotIn("data-bms-learn-filters", learn_landing)
        self.assertNotIn("listing:", learn_landing)
        self.assertIn("lesson-finder/", learn_landing)
        self.assertIn("data-bms-learn-filters", lesson_finder)
        self.assertIn("listing:", lesson_finder)
        self.assertNotIn("bms-learn-card-taxonomy", listing_template)
        self.assertEqual(
            entries_html.count('data-bms-letter-group open'),
            len(
                re.findall(
                    r'<details class="bms-glossary-letter-group"',
                    entries_html,
                )
            ),
        )

        sample = (
            learn_glossary.GLOSSARY_ROOT / "take-point" / "index.qmd"
        ).read_text(encoding="utf-8")
        self.assertIn("description:", sample)
        self.assertIn("canonical-url:", sample)
        self.assertIn(
            "image: /assets/social/generated/social-glossary.png",
            sample,
        )
        self.assertNotIn("bms-glossary-canonical", sample)
        self.assertNotIn("Canonical URL:", sample)

        glossary_landing = (
            learn_glossary.GLOSSARY_ROOT / "index.qmd"
        ).read_text(encoding="utf-8")
        self.assertIn("social-card-slug: glossary", glossary_landing)
        self.assertIn(
            "image: /assets/social/generated/social-glossary.png",
            glossary_landing,
        )
        self.assertNotIn("undergoing editorial review", glossary_landing)

        learn_css = (
            learn_glossary.SITE_ROOT / "assets" / "bms-learn.css"
        ).read_text(encoding="utf-8")
        self.assertRegex(
            learn_css,
            r"\.bms-learn-list\s*\{[^}]*grid-template-columns:\s*1fr;",
        )
        self.assertRegex(
            learn_css,
            r"body\.bms-glossary-term #title-block-header \.description\s*"
            r"\{[^}]*display:\s*none;",
        )
        self.assertNotIn(
            '.sidebar-link[href$="learn/glossary/index.html"]',
            learn_css,
        )

    def test_a2_sidebar_order_and_static_glossary_link(self) -> None:
        quarto = (learn_glossary.SITE_ROOT / "_quarto.yml").read_text(
            encoding="utf-8"
        )
        learn_sidebar = quarto.split("  page-footer:", 1)[0].split(
            "  sidebar:", 1
        )[1]
        finder = learn_sidebar.rfind('text: "Lesson Finder"')
        glossary = learn_sidebar.rfind('text: "Backgammon Glossary')
        self.assertIn('text: "Learn Home"', learn_sidebar)
        self.assertGreater(finder, learn_sidebar.rfind('section: "Opening Play Lab"'))
        self.assertGreater(glossary, finder)
        self.assertIn(
            "href: learn/lesson-finder/index.qmd",
            learn_sidebar,
        )
        glossary_block = learn_sidebar[glossary:]
        self.assertIn("target: _blank", glossary_block)
        self.assertIn("rel: noopener", glossary_block)
        self.assertIn("opens in a new tab", glossary_block)

    def test_a2_content_controls_lookup_and_link_policy_sources(self) -> None:
        learn_landing = (learn_glossary.LEARN_ROOT / "index.qmd").read_text(
            encoding="utf-8"
        )
        finder = (
            learn_glossary.LEARN_ROOT / "lesson-finder" / "index.qmd"
        ).read_text(encoding="utf-8")
        glossary = (
            learn_glossary.GLOSSARY_ROOT / "index.qmd"
        ).read_text(encoding="utf-8")
        entries = learn_glossary.GENERATED_ENTRIES_PATH.read_text(
            encoding="utf-8"
        )
        term_lookup = (
            learn_glossary.SITE_ROOT
            / "_extensions"
            / "bms-term-lookup"
            / "bms-term-lookup.lua"
        ).read_text(encoding="utf-8")
        link_policy = (
            learn_glossary.SITE_ROOT
            / "_extensions"
            / "bms-link-policy"
            / "bms-link-policy.lua"
        ).read_text(encoding="utf-8")

        self.assertNotIn("Why We Are Starting With the Doubling Cube", learn_landing)
        self.assertIn("## Start with The Doubling Cube", learn_landing)
        self.assertIn(
            "We first wrote lessons for the doubling cube. More lesson topics are coming.",
            learn_landing,
        )
        self.assertIn("Find Lessons by Difficulty", learn_landing)
        self.assertIn("Look Up a Term", learn_landing)
        self.assertNotIn("combined with **or**", finder)

        self.assertIn("data-bms-glossary-category-disclosure", glossary)
        self.assertIn("data-bms-glossary-track-disclosure", glossary)
        self.assertNotIn("data-bms-glossary-section-control", glossary)
        self.assertIn("data-bms-glossary-section-control", entries)
        self.assertIn("bms-glossary-alphabet-links", entries)
        self.assertIn("data-bms-glossary-back-to-top", glossary)

        self.assertIn('action="/learn/glossary/"', term_lookup)
        self.assertIn('target="_blank"', term_lookup)
        self.assertIn('rel="noopener"', term_lookup)
        self.assertIn('name="q"', term_lookup)
        self.assertIn("has_download(link)", link_policy)
        self.assertIn('link.attributes.target = "_blank"', link_policy)
        self.assertIn('"noopener"', link_policy)

    def test_a2_generated_related_research_is_compact_and_same_tab(self) -> None:
        equity = (
            learn_glossary.GLOSSARY_ROOT / "equity" / "index.qmd"
        ).read_text(encoding="utf-8")
        self.assertIn("Related research (1)", equity)
        self.assertIn(
            'href="/research/sage-vs-gnu-additional-details.html"',
            equity,
        )
        related_link = re.search(
            r'<a[^>]*href="/research/sage-vs-gnu-additional-details\.html"[^>]*>',
            equity,
        )
        self.assertIsNotNone(related_link)
        self.assertNotIn('target="_blank"', related_link.group(0))
        self.assertIn("bms-glossary-related--research", equity)

    def test_one_shared_glossary_social_card_is_configured(self) -> None:
        shared_image = "/assets/social/generated/social-glossary.png"
        term_pages = list(learn_glossary.GLOSSARY_ROOT.glob("*/index.qmd"))
        self.assertEqual(len(term_pages), 624)
        for path in term_pages:
            content = path.read_text(encoding="utf-8")
            self.assertIn(f"image: {shared_image}", content)
            self.assertNotIn("social-card: true", content)

        manifest = (
            learn_glossary.SITE_ROOT / "assets" / "social" / "social-cards.yml"
        ).read_text(encoding="utf-8")
        self.assertEqual(manifest.count("- slug: glossary"), 1)
        self.assertEqual(
            manifest.count(
                "output: site/assets/social/generated/social-glossary.png"
            ),
            1,
        )

        canonical_slugs = {entry["slug"] for entry in self.entries}
        generated_social = (
            learn_glossary.SITE_ROOT / "assets" / "social" / "generated"
        )
        per_term_images = [
            path
            for path in generated_social.glob("social-*.png")
            if path.stem.removeprefix("social-") in canonical_slugs
        ]
        self.assertEqual(per_term_images, [])


if __name__ == "__main__":
    unittest.main()
