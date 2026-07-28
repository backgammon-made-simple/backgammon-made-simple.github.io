from __future__ import annotations

import importlib.util
import json
import os
import re
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "learn_glossary.py"
SPEC = importlib.util.spec_from_file_location("learn_glossary", MODULE_PATH)
assert SPEC and SPEC.loader
learn_glossary = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(learn_glossary)

PRE_RENDER_PATH = ROOT / "scripts" / "bms_pre_render.py"
PRE_RENDER_SPEC = importlib.util.spec_from_file_location(
    "bms_pre_render",
    PRE_RENDER_PATH,
)
assert PRE_RENDER_SPEC and PRE_RENDER_SPEC.loader
bms_pre_render = importlib.util.module_from_spec(PRE_RENDER_SPEC)
PRE_RENDER_SPEC.loader.exec_module(bms_pre_render)

POST_RENDER_PATH = ROOT / "scripts" / "bms_post_render.py"
POST_RENDER_SPEC = importlib.util.spec_from_file_location(
    "bms_post_render",
    POST_RENDER_PATH,
)
assert POST_RENDER_SPEC and POST_RENDER_SPEC.loader
bms_post_render = importlib.util.module_from_spec(POST_RENDER_SPEC)
POST_RENDER_SPEC.loader.exec_module(bms_post_render)


class LearnGlossaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data = json.loads(
            learn_glossary.PUBLIC_DATA_PATH.read_text(encoding="utf-8")
        )
        cls.entries = learn_glossary.validate_public_data(cls.data)
        cls.lessons = learn_glossary.discover_lessons()
        cls.related_lessons = learn_glossary.validate_lessons(
            cls.lessons,
            cls.entries,
        )
        cls.research_articles = learn_glossary.discover_research_articles()
        cls.related_research = learn_glossary.validate_research_articles(
            cls.research_articles,
            cls.entries,
        )
        cls.cube_lessons = learn_glossary.discover_cube_lessons()
        cls.update_publications = learn_glossary.discover_update_publications()
        cls.entries_html = learn_glossary.GENERATED_ENTRIES_PATH.read_text(
            encoding="utf-8"
        )

    def test_public_safe_counts_and_forbidden_guards(self) -> None:
        self.assertEqual(len(self.data["entries"]), 624)
        self.assertEqual(len(self.entries), 624)
        self.assertEqual(
            sum(len(entry["aliases"]) for entry in self.entries),
            181,
        )
        self.assertEqual(624 + 181, 805)
        learn_glossary.assert_no_forbidden_keys(self.data)
        learn_glossary.assert_no_forbidden_text(
            learn_glossary.PUBLIC_DATA_PATH.read_text(encoding="utf-8"),
            "tracked public glossary data",
        )
        learn_glossary.assert_no_forbidden_text(
            self.entries_html,
            "single-page glossary entries",
        )

    def test_generator_manages_only_single_page_outputs(self) -> None:
        outputs = learn_glossary.generated_outputs(
            self.entries,
            self.related_lessons,
            self.related_research,
        )
        self.assertEqual(
            set(outputs),
            {
                learn_glossary.GENERATED_ENTRIES_PATH,
                learn_glossary.AUTHORING_TERMS_PATH,
            },
        )
        self.assertEqual(len(outputs), 2)
        self.assertEqual(
            outputs,
            learn_glossary.generated_outputs(
                self.entries,
                self.related_lessons,
                self.related_research,
            ),
        )
        for path, expected in outputs.items():
            self.assertEqual(path.read_text(encoding="utf-8"), expected)

    def test_exactly_one_glossary_source_page_and_zero_term_pages(self) -> None:
        self.assertTrue((learn_glossary.GLOSSARY_ROOT / "index.qmd").exists())
        self.assertEqual(
            list(learn_glossary.GLOSSARY_ROOT.glob("*/index.qmd")),
            [],
        )
        self.assertFalse(learn_glossary.LEGACY_GENERATED_ROUTES_PATH.exists())
        self.assertEqual(
            [
                path
                for path in learn_glossary.GLOSSARY_ROOT.rglob("*.qmd")
                if path.name == "index.qmd"
            ],
            [learn_glossary.GLOSSARY_ROOT / "index.qmd"],
        )

    def test_single_page_has_unique_canonical_anchors_and_collapsed_terms(self) -> None:
        canonical = {str(entry["slug"]) for entry in self.entries}
        anchors = re.findall(
            r'<details class="bms-glossary-entry" id="([^"]+)"',
            self.entries_html,
        )
        self.assertEqual(len(anchors), 624)
        self.assertEqual(len(set(anchors)), 624)
        self.assertEqual(set(anchors), canonical)
        self.assertEqual(
            self.entries_html.count('class="bms-glossary-entry-summary"'),
            624,
        )
        entry_tags = re.findall(
            r'<details class="bms-glossary-entry"[^>]*>',
            self.entries_html,
        )
        self.assertEqual(len(entry_tags), 624)
        self.assertTrue(all(" open" not in tag for tag in entry_tags))

    def test_aliases_map_to_canonical_entries_without_visible_duplicates(self) -> None:
        canonical = {entry["slug"]: entry for entry in self.entries}
        alias_to_canonical = {
            alias["slug"]: entry["slug"]
            for entry in self.entries
            for alias in entry["aliases"]
        }
        self.assertEqual(len(alias_to_canonical), 181)
        self.assertEqual(alias_to_canonical["accept-a-double"], "take")
        self.assertEqual(alias_to_canonical["cube-ownership"], "own-the-cube")
        self.assertNotIn("accept-a-double", canonical)
        self.assertEqual(self.entries_html.count('data-bms-alias="'), 181)
        self.assertIn(
            'data-bms-aliases="[&quot;accept-a-double&quot;]"',
            self.entries_html,
        )
        self.assertNotIn('id="accept-a-double"', self.entries_html)

    def test_full_definitions_usage_and_related_links_are_initial_html(self) -> None:
        self.assertEqual(
            self.entries_html.count('class="bms-glossary-definition"'),
            624,
        )
        self.assertIn('class="bms-glossary-usage-note"', self.entries_html)
        self.assertIn("Learn more (", self.entries_html)
        self.assertIn("Research (", self.entries_html)
        self.assertIn(
            'href="/research/sage-vs-gnu-additional-details.html"',
            self.entries_html,
        )
        self.assertNotIn('target="_blank"', self.entries_html)
        self.assertNotIn("bms-learn-card-taxonomy", self.entries_html)
        self.assertNotIn("bms-research-post-taxonomy", self.entries_html)
        self.assertNotIn("Link to this term", self.entries_html)
        self.assertNotIn("bms-glossary-anchor", self.entries_html)
        self.assertEqual(
            sum(len(value) for value in self.related_lessons.values()),
            62,
        )
        self.assertEqual(
            sum(len(value) for value in self.related_research.values()),
            3,
        )

    def test_no_old_term_routes_metadata_or_navigation_remain(self) -> None:
        canonical = {str(entry["slug"]) for entry in self.entries}
        self.assertFalse(
            any(f"/learn/glossary/{slug}/" in self.entries_html for slug in canonical)
        )
        for forbidden in (
            "canonical-url:",
            "bms-glossary-term-navigation",
            'rel="prev"',
            'rel="next"',
            "bms-glossary-term-card",
        ):
            self.assertNotIn(forbidden, self.entries_html)

        script = MODULE_PATH.read_text(encoding="utf-8")
        self.assertNotIn("def build_term_qmd", script)
        self.assertNotIn("sampled_term_paths", script)
        self.assertNotIn("Expected 625 glossary HTML files", script)
        self.assertIn("sitemap_glossary_routes", script)
        self.assertIn('"standalone_term_pages": 0', script)

    def test_glossary_has_one_canonical_and_one_shared_social_image(self) -> None:
        source = (learn_glossary.GLOSSARY_ROOT / "index.qmd").read_text(
            encoding="utf-8"
        )
        self.assertEqual(source.count("canonical-url:"), 1)
        self.assertIn(
            'canonical-url: "https://backgammon-made-simple.github.io/learn/glossary/"',
            source,
        )
        self.assertEqual(source.count("social-card-slug: glossary"), 1)
        self.assertIn(
            "image: /assets/social/generated/social-glossary.png",
            source,
        )

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
        per_term_images = [
            path
            for path in (
                learn_glossary.SITE_ROOT / "assets" / "social" / "generated"
            ).glob("social-*.png")
            if path.stem.removeprefix("social-") in canonical_slugs
        ]
        self.assertEqual(per_term_images, [])

    def test_letter_sections_open_and_term_disclosures_do_not(self) -> None:
        letter_tags = re.findall(
            r'<details class="bms-glossary-letter-group"[^>]*>',
            self.entries_html,
        )
        self.assertGreater(len(letter_tags), 0)
        self.assertTrue(all(" open" in tag for tag in letter_tags))
        self.assertEqual(
            self.entries_html.count("data-bms-glossary-collapse-all"),
            1,
        )
        self.assertEqual(
            self.entries_html.count("data-bms-glossary-expand-all"),
            1,
        )
        self.assertRegex(
            self.entries_html,
            r"data-bms-glossary-expand-all[^>]*disabled",
        )
        self.assertIn('href="#letter-a"', self.entries_html)
        self.assertIn('id="letter-a"', self.entries_html)
        self.assertNotIn('id="letter-A"', self.entries_html)

    def test_fragment_search_and_letter_behavior_are_wired(self) -> None:
        javascript = (
            learn_glossary.SITE_ROOT / "assets" / "bms-glossary.js"
        ).read_text(encoding="utf-8")
        for required in (
            "function canonicalSlugForFragment",
            "function setExactlyOneExpandedTerm",
            "function closeTermEntries",
            "function openCurrentHash",
            "normalizedTermFragmentUrl(",
            "rankGlossaryItems(visibleItems, query).forEach",
            'searchInput.value = ""',
            "activeLetterBrowse =",
            "closeTermEntries(items)",
            "applyFilters({ updateUrl: false })",
            "letterNavigationUrl(",
        ):
            self.assertIn(required, javascript)
        self.assertNotIn("item.element.open = visible", javascript)
        self.assertNotIn("setAllGroupsExpanded(items", javascript)
        self.assertIn("group.open = expanded", javascript)

    def test_lookup_get_contract_and_link_policy_are_preserved(self) -> None:
        term_lookup = (
            learn_glossary.SITE_ROOT
            / "_extensions"
            / "bms-term-lookup"
            / "bms-term-lookup.lua"
        ).read_text(encoding="utf-8")
        self.assertRegex(
            term_lookup,
            r'<form action="/learn/glossary/" method="get" '
            r'target="_blank" rel="noopener"',
        )
        self.assertRegex(term_lookup, r'<input[^>]*name="q"')

        link_policy = (
            learn_glossary.SITE_ROOT
            / "_extensions"
            / "bms-link-policy"
            / "bms-link-policy.lua"
        ).read_text(encoding="utf-8")
        self.assertIn("is_same_document_fragment", link_policy)
        self.assertIn("is_glossary_target", link_policy)
        self.assertIn('link.attributes.target = "_blank"', link_policy)
        self.assertIn('"noopener"', link_policy)
        self.assertIn("opens in a new tab", link_policy)

    def test_learn_and_research_terms_metadata_is_canonical(self) -> None:
        canonical = {entry["slug"] for entry in self.entries}
        self.assertEqual(len(self.lessons), 7)
        for lesson in self.lessons:
            self.assertTrue(
                set(lesson["categories"]).issubset(learn_glossary.DIFFICULTIES)
            )
            self.assertTrue(set(lesson["tags"]).issubset(learn_glossary.TRACKS))
            self.assertTrue(set(lesson["terms"]).issubset(canonical))
        for article in self.research_articles:
            self.assertTrue(set(article["terms"]).issubset(canonical))

    def test_source_glossary_links_use_root_or_canonical_fragments(self) -> None:
        href_pattern = re.compile(r'href=["\'](/learn/glossary/[^"\']*)')
        source_paths = [
            *learn_glossary.LEARN_ROOT.rglob("*.qmd"),
            *learn_glossary.RESEARCH_ROOT.rglob("*.qmd"),
        ]
        for path in source_paths:
            for href in href_pattern.findall(path.read_text(encoding="utf-8")):
                suffix = href.removeprefix("/learn/glossary/")
                self.assertTrue(
                    suffix == "" or suffix.startswith(("#", "?")),
                    f"{path.relative_to(ROOT)} uses obsolete glossary route {href}",
                )

    def test_a5_cube_listing_is_preserved(self) -> None:
        self.assertEqual(
            [lesson["relative_path"] for lesson in self.cube_lessons],
            [
                "why-is-25-percent-the-basic-take-point.qmd",
                "what-the-cube-is-asking.qmd",
            ],
        )
        self.assertEqual(
            [lesson["cube-order"] for lesson in self.cube_lessons],
            [1, 2],
        )
        cube_index = (learn_glossary.CUBE_ROOT / "index.qmd").read_text(
            encoding="utf-8"
        )
        self.assertIn("template: ../_lesson-listing.ejs.md", cube_index)
        self.assertIn('sort: "cube-order"', cube_index)
        self.assertNotIn("**Planned", cube_index)
        self.assertFalse(
            (learn_glossary.CUBE_ROOT / "_cube-lesson-listing.ejs.md").exists()
        )

    def test_custom_404_source_contract(self) -> None:
        not_found_path = learn_glossary.SITE_ROOT / "404.qmd"
        self.assertTrue(not_found_path.exists())
        content = not_found_path.read_text(encoding="utf-8")
        self.assertIn('title: "Page closed out"', content)
        self.assertIn(
            "The page you're looking for doesn't exist, has moved, "
            "or suspiciously bounced off the board.",
            content,
        )
        for label, route in (
            ("Home", "/"),
            ("Learn", "/learn/"),
            ("Lesson Finder", "/learn/lesson-finder/"),
            ("Backgammon Glossary", "/learn/glossary/"),
            ("Research", "/research/"),
        ):
            self.assertIn(f"[{label}]({route})", content)
        self.assertIn("toc: false", content)
        self.assertIn("sidebar: false", content)
        self.assertIn("search: false", content)
        self.assertNotRegex(
            content,
            r"(?i)(http-equiv\s*=\s*[\"']?refresh|window\.location|"
            r"location\.replace|github pages)",
        )

    def test_native_toc_expansion_and_exclusions(self) -> None:
        learn_metadata = (
            learn_glossary.LEARN_ROOT / "_metadata.yml"
        ).read_text(encoding="utf-8")
        research_metadata = (
            learn_glossary.RESEARCH_ROOT / "_metadata.yml"
        ).read_text(encoding="utf-8")
        self.assertRegex(
            learn_metadata,
            r"format:\s+html:\s+toc-expand: true",
        )
        self.assertRegex(
            research_metadata,
            r"format:\s+html:\s+toc-expand: true",
        )
        excluded = [
            learn_glossary.LEARN_ROOT / "index.qmd",
            learn_glossary.LEARN_ROOT / "lesson-finder" / "index.qmd",
            learn_glossary.CUBE_ROOT / "index.qmd",
            learn_glossary.GLOSSARY_ROOT / "index.qmd",
            learn_glossary.RESEARCH_ROOT / "index.qmd",
            learn_glossary.SITE_ROOT / "404.qmd",
        ]
        for path in excluded:
            self.assertRegex(
                path.read_text(encoding="utf-8"),
                r"toc:\s*false",
                str(path.relative_to(ROOT)),
            )

        extension = (
            learn_glossary.SITE_ROOT
            / "_extensions"
            / "bms-research-taxonomy"
            / "bms-research-taxonomy.lua"
        ).read_text(encoding="utf-8")
        for forbidden in (
            "initializeResearchToc",
            "setResearchTocExpanded",
            "bms-research-toc-toggle",
            'classList.toggle("collapse"',
        ):
            self.assertNotIn(forbidden, extension)

    def test_authoring_docs_describe_single_page_anchors_and_404(self) -> None:
        guide = (ROOT / "docs" / "authoring-guide.md").read_text(
            encoding="utf-8"
        )
        terms = learn_glossary.AUTHORING_TERMS_PATH.read_text(
            encoding="utf-8"
        )
        for required in (
            "## Single-Page Glossary",
            "/learn/glossary/#prime",
            "Do not create a directory or page for an individual term",
            "site/404.qmd",
            "canonical `terms` metadata",
            "authoritative automatic sequence",
            "## Updates RSS",
            "published: true",
        ):
            self.assertIn(required, guide)
        self.assertIn("there are no standalone term routes", terms)
        self.assertEqual(terms.count("/learn/glossary/#"), 624)

    def test_moved_analyzer_include_and_all_cube_includes_resolve(self) -> None:
        include_copies = list(
            learn_glossary.SITE_ROOT.rglob("analyzer-form.html")
        )
        self.assertEqual(
            include_copies,
            [learn_glossary.SITE_ROOT / "includes" / "analyzer-form.html"],
        )
        lesson_path = learn_glossary.CUBE_ROOT / "what-the-cube-is-asking.qmd"
        source = lesson_path.read_text(encoding="utf-8")
        includes = re.findall(r"\{\{< include ([^ >]+) >\}\}", source)
        self.assertEqual(
            includes,
            [
                "../../includes/analyzer-form.html",
                "../../includes/subscribe.html",
                "../../includes/report-problem.html",
            ],
        )
        for include in includes:
            resolved = (lesson_path.parent / include).resolve()
            self.assertTrue(
                resolved.is_relative_to(learn_glossary.SITE_ROOT.resolve())
            )
            self.assertTrue(resolved.is_file(), resolved)
        self.assertNotRegex(source, r"[A-Za-z]:\\")
        self.assertIn("[Back to the cube overview](index.qmd)", source)
        self.assertNotIn("[Back to the cube overview](../index.qmd)", source)

    def test_cube_order_is_metadata_driven_and_consistent(self) -> None:
        expected_paths = [
            "why-is-25-percent-the-basic-take-point.qmd",
            "what-the-cube-is-asking.qmd",
        ]
        expected_titles = [
            "Why Is 25% the Basic Take Point When a Double Is Offered?",
            "What the Cube Is Really Asking",
        ]
        self.assertEqual(
            [lesson["relative_path"] for lesson in self.cube_lessons],
            expected_paths,
        )
        self.assertEqual(
            [lesson["title"] for lesson in self.cube_lessons],
            expected_titles,
        )
        self.assertEqual(
            [lesson["cube-order"] for lesson in self.cube_lessons],
            [1, 2],
        )

        config = (learn_glossary.SITE_ROOT / "_quarto.yml").read_text(
            encoding="utf-8"
        )
        sidebar_paths = [f"learn/cube/{path}" for path in expected_paths]
        self.assertTrue(
            config.index(sidebar_paths[0]) < config.index(sidebar_paths[1])
        )
        for path in sidebar_paths:
            self.assertEqual(config.count(path), 1)

        cube_index = (learn_glossary.CUBE_ROOT / "index.qmd").read_text(
            encoding="utf-8"
        )
        self.assertIn('sort: "cube-order"', cube_index)
        for lesson in self.cube_lessons:
            lesson_source = lesson["path"].read_text(encoding="utf-8")
            self.assertEqual(lesson_source.count("cube-order:"), 1)

        finder = (
            learn_glossary.LEARN_ROOT / "lesson-finder" / "index.qmd"
        ).read_text(encoding="utf-8")
        self.assertIn("../cube/what-the-cube-is-asking.qmd", finder)
        self.assertNotIn("../cube/what-the-cube-is-asking/index.qmd", finder)

    def test_cube_landing_uses_local_filters_and_excludes_lookup(self) -> None:
        cube_index = (learn_glossary.CUBE_ROOT / "index.qmd").read_text(
            encoding="utf-8"
        )
        self.assertIn("term-lookup: false", cube_index)
        self.assertIn("lesson-taxonomy: false", cube_index)
        self.assertNotIn("/learn/lesson-finder/", cube_index)
        self.assertNotIn("target=", cube_index)
        self.assertIn("data-bms-learn-filters", cube_index)
        self.assertIn("data-bms-learn-clear", cube_index)
        self.assertIn("data-bms-learn-empty", cube_index)

        difficulty_buttons = set(
            re.findall(r'data-bms-filter-difficulty="([^"]+)"', cube_index)
        )
        track_buttons = set(
            re.findall(r'data-bms-filter-track="([^"]+)"', cube_index)
        )
        expected_difficulties = {
            str(value)
            for lesson in self.cube_lessons
            for value in lesson["categories"]
        }
        expected_tracks = {
            str(value)
            for lesson in self.cube_lessons
            for value in lesson["tags"]
        }
        self.assertEqual(difficulty_buttons, expected_difficulties)
        self.assertEqual(track_buttons, expected_tracks)
        self.assertEqual(
            cube_index.count('aria-pressed="false"'),
            len(difficulty_buttons) + len(track_buttons),
        )

        taxonomy_filter = (
            learn_glossary.SITE_ROOT
            / "_extensions"
            / "bms-learn-taxonomy"
            / "bms-learn-taxonomy.lua"
        ).read_text(encoding="utf-8")
        self.assertIn('doc.meta["lesson-taxonomy"]', taxonomy_filter)
        self.assertIn("== false", taxonomy_filter)

        lesson_source = (
            learn_glossary.CUBE_ROOT
            / "why-is-25-percent-the-basic-take-point.qmd"
        ).read_text(encoding="utf-8")
        research_source = (
            learn_glossary.RESEARCH_ROOT / "what-we-are-building.qmd"
        ).read_text(encoding="utf-8")
        self.assertNotIn("term-lookup: false", lesson_source)
        self.assertNotIn("term-lookup: false", research_source)

    def test_cube_numbering_is_landing_only_and_sequence_generated(self) -> None:
        template = (
            learn_glossary.LEARN_ROOT / "_lesson-listing.ejs.md"
        ).read_text(encoding="utf-8")
        css = (
            learn_glossary.SITE_ROOT / "assets" / "bms-learn.css"
        ).read_text(encoding="utf-8")
        self.assertEqual(template.count("bms-cube-lesson-number"), 1)
        self.assertIn("#listing-cube-lessons .bms-cube-lesson-number", css)
        self.assertIn("counter-reset: bms-cube-lesson", css)
        self.assertIn("counter-increment: bms-cube-lesson", css)
        self.assertIn('content: counter(bms-cube-lesson) ". "', css)
        for lesson in self.cube_lessons:
            self.assertNotRegex(str(lesson["title"]), r"^\d+\.\s")

    def test_learn_home_cube_navigation_is_same_tab(self) -> None:
        source = (learn_glossary.LEARN_ROOT / "index.qmd").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            "[Start with the Cube Lessons](/learn/cube/){.bms-button-outline}",
            source,
        )
        cube_link = re.search(
            r"\[Start with the Cube Lessons\]\(/learn/cube/\)(\{[^}]*\})?",
            source,
        )
        self.assertIsNotNone(cube_link)
        attributes = cube_link.group(1) or ""
        self.assertNotIn("_blank", attributes)
        self.assertNotIn("noopener", attributes)
        self.assertNotIn("opens in a new tab", attributes)

    def test_clean_glossary_canonical_and_sitemap_contract(self) -> None:
        source = (learn_glossary.GLOSSARY_ROOT / "index.qmd").read_text(
            encoding="utf-8"
        )
        clean_url = "https://backgammon-made-simple.github.io/learn/glossary/"
        self.assertIn(f'canonical-url: "{clean_url}"', source)
        self.assertNotIn("/learn/glossary/index.html", source)
        generator = MODULE_PATH.read_text(encoding="utf-8")
        self.assertIn(f'"{clean_url}"', generator)
        self.assertNotIn(
            '"https://backgammon-made-simple.github.io/learn/glossary/index.html"',
            generator,
        )

    def test_combined_updates_feed_contract_and_footer(self) -> None:
        updates_path = learn_glossary.SITE_ROOT / "updates" / "index.qmd"
        self.assertTrue(updates_path.is_file())
        source = updates_path.read_text(encoding="utf-8")
        for required in (
            '"../learn/**/*.qmd"',
            '"../research/**/*.qmd"',
            '"../engine-benchmark/**/*.qmd"',
            "published: true",
            'sort: "date desc"',
            "feed:",
            'title: "Backgammon Made Simple Updates"',
        ):
            self.assertIn(required, source)
        self.assertNotIn("../posts/", source)
        self.assertNotIn("../templates/", source)
        self.assertEqual(self.update_publications, [])
        generator = MODULE_PATH.read_text(encoding="utf-8")
        for guard in (
            "excluded_landings",
            'metadata.get("draft"',
            'metadata.get("hidden"',
            '{"draft", "planned"}',
            "date.fromisoformat",
        ):
            self.assertIn(guard, generator)

        config = (learn_glossary.SITE_ROOT / "_quarto.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("href: /updates/index.xml", config)
        self.assertNotIn("href: research/index.xml", config)

        private_dated = list((learn_glossary.SITE_ROOT / "posts").rglob("*.qmd"))
        self.assertGreater(len(private_dated), 0)
        for path in private_dated:
            private_source = path.read_text(encoding="utf-8")
            self.assertRegex(private_source, r"(?i)(private|fixture)")

    def test_pre_render_wrapper_preserves_full_and_incremental_policy(self) -> None:
        config = (learn_glossary.SITE_ROOT / "_quarto.yml").read_text(
            encoding="utf-8"
        )
        self.assertRegex(
            config,
            r"pre-render:\s*\n\s*-\s+python ../scripts/bms_pre_render\.py",
        )

        with mock.patch.dict(os.environ, {}, clear=True):
            with mock.patch.object(bms_pre_render, "run") as run:
                self.assertEqual(bms_pre_render.main(), 0)
                run.assert_not_called()

        with mock.patch.dict(
            os.environ,
            {"QUARTO_PROJECT_RENDER_ALL": "1"},
            clear=True,
        ):
            with mock.patch.object(bms_pre_render, "run") as run:
                self.assertEqual(bms_pre_render.main(), 0)
                self.assertEqual(run.call_count, 2)
                commands = [call.args[0] for call in run.call_args_list]
                self.assertIn("learn_glossary.py", " ".join(commands[0]))
                self.assertIn("generate", commands[0])
                self.assertIn("run_social_pipeline.py", " ".join(commands[1]))

    def test_sitemap_clean_url_post_render_contract_is_narrow(self) -> None:
        config = (learn_glossary.SITE_ROOT / "_quarto.yml").read_text(
            encoding="utf-8"
        )
        self.assertRegex(
            config,
            r"post-render:\s*\n\s*-\s+python ../scripts/bms_post_render\.py",
        )
        unrelated = "https://backgammon-made-simple.github.io/research/index.html"
        dirty = bms_post_render.GLOSSARY_INDEX_URL
        clean = bms_post_render.GLOSSARY_CANONICAL_URL
        source = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            "<urlset>\n"
            f"  <url><loc>{unrelated}</loc></url>\n"
            f"  <url><loc>{dirty}</loc></url>\n"
            "</urlset>\n"
        )
        normalized, changed = bms_post_render.normalized_glossary_sitemap_text(
            source
        )
        self.assertTrue(changed)
        self.assertIn(f"<loc>{clean}</loc>", normalized)
        self.assertNotIn(f"<loc>{dirty}</loc>", normalized)
        self.assertIn(f"<loc>{unrelated}</loc>", normalized)
        current, changed_again = (
            bms_post_render.normalized_glossary_sitemap_text(normalized)
        )
        self.assertFalse(changed_again)
        self.assertEqual(current, normalized)

    def test_validation_reports_single_page_counts(self) -> None:
        result = learn_glossary.validate_generated()
        self.assertEqual(result["source_entries"], 805)
        self.assertEqual(result["canonical_entries"], 624)
        self.assertEqual(result["alias_entries"], 181)
        self.assertEqual(result["canonical_anchors"], 624)
        self.assertEqual(result["standalone_term_pages"], 0)
        self.assertEqual(result["generated_files"], 2)
        self.assertEqual(result["cube_lessons"], 2)
        self.assertEqual(result["updates_publications"], 0)
        self.assertEqual(result["related_lesson_links"], 62)
        self.assertEqual(result["related_research_links"], 3)


if __name__ == "__main__":
    unittest.main()
