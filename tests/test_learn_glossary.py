from __future__ import annotations

import importlib.util
import json
import os
import re
import shutil
import unittest
import uuid
from contextlib import contextmanager
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


@contextmanager
def writable_test_directory():
    runtime_root = ROOT / "task-work" / "W3W-REGRESSION-01" / "runtime"
    path = runtime_root / f"validator-fixture-{uuid.uuid4().hex}"
    path.mkdir(parents=True)
    try:
        yield path
    finally:
        shutil.rmtree(path)


class LearnGlossaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data = json.loads(
            learn_glossary.PUBLIC_DATA_PATH.read_text(encoding="utf-8")
        )
        cls.entries = learn_glossary.validate_public_data(cls.data)
        cls.tracks = learn_glossary.discover_tracks()
        cls.lessons = learn_glossary.discover_lessons()
        cls.lesson_sections = learn_glossary.build_curriculum(
            cls.tracks,
            cls.lessons,
        )
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

    def test_generator_manages_glossary_and_sidebar_driven_learn_outputs(self) -> None:
        outputs = learn_glossary.generated_outputs(
            self.entries,
            self.lesson_sections,
            self.related_lessons,
            self.related_research,
        )
        track_outputs = {
            track["path"].parent / "_lesson-index.html"
            for track in self.lesson_sections
        }
        self.assertEqual(
            set(outputs),
            {
                learn_glossary.GENERATED_LESSON_CATALOGUE_PATH,
                learn_glossary.GENERATED_NAVIGATION_PATH,
                learn_glossary.GENERATED_ENTRIES_PATH,
                learn_glossary.GENERATED_LOOKUP_DATA_PATH,
                learn_glossary.AUTHORING_TERMS_PATH,
                *track_outputs,
            }
        )
        self.assertEqual(len(outputs), 8)
        self.assertEqual(
            outputs,
            learn_glossary.generated_outputs(
                self.entries,
                self.lesson_sections,
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
            40,
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
            "const rankedItems = rankGlossaryItems(visibleItems, query)",
            "expandBestGlossaryMatch(",
            "autoOpenedSearchItem",
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

    def test_lookup_get_contract_and_same_tab_link_policy_are_preserved(self) -> None:
        term_lookup = (
            learn_glossary.SITE_ROOT
            / "_extensions"
            / "bms-term-lookup"
            / "bms-term-lookup.lua"
        ).read_text(encoding="utf-8")
        self.assertRegex(
            term_lookup,
            r'<form action="/learn/glossary/" method="get" '
            r"data-bms-term-lookup-form",
        )
        self.assertRegex(term_lookup, r'<input[^>]*name="q"')
        self.assertNotIn("target=", term_lookup)
        self.assertNotRegex(term_lookup, r"(?i)opens? in (?:a )?new tab")

        link_policy = (
            learn_glossary.SITE_ROOT
            / "_extensions"
            / "bms-link-policy"
            / "bms-link-policy.lua"
        ).read_text(encoding="utf-8")
        self.assertIn("function Link(link)", link_policy)
        self.assertIn("link.attributes.target = nil", link_policy)
        self.assertNotIn("link.attributes.download =", link_policy)
        self.assertNotIn("_blank", link_policy)
        self.assertNotRegex(link_policy, r"(?i)opens? in (?:a )?new tab")

    def test_temporary_site_wide_same_tab_source_contract(self) -> None:
        source_paths = [
            path
            for path in learn_glossary.SITE_ROOT.rglob("*")
            if path.is_file()
            and path.suffix in {".qmd", ".html", ".yml", ".yaml", ".lua", ".js"}
            and "_site" not in path.parts
            and "_freeze" not in path.parts
        ]
        for path in source_paths:
            content = path.read_text(encoding="utf-8", errors="replace")
            self.assertNotIn("_blank", content, str(path.relative_to(ROOT)))
            self.assertNotRegex(
                content,
                r"(?i)opens? in (?:a )?new tab",
                str(path.relative_to(ROOT)),
            )

        config = (learn_glossary.SITE_ROOT / "_quarto.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("link-external-newwindow: false", config)
        self.assertNotRegex(config, r"(?m)^\s+target:")
        self.assertIn("href: /updates/index.xml", config)

        about = (learn_glossary.SITE_ROOT / "about.qmd").read_text(
            encoding="utf-8"
        )
        self.assertIn("[Read what I am building ->](/research/)", about)

        learn_home = (learn_glossary.LEARN_ROOT / "index.qmd").read_text(
            encoding="utf-8"
        )
        self.assertEqual(
            learn_home.split("---", 2)[-1].strip(),
            "{{< include _lesson-catalogue.html >}}",
        )
        self.assertIn('href="#letter-a"', self.entries_html)
        self.assertIn('href="/learn/', self.entries_html)

        analyze = (learn_glossary.SITE_ROOT / "analyze" / "index.qmd").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            "](https://backgammon-made-simple.shinyapps.io/",
            analyze,
        )
        self.assertIn("bms-analyze-page", analyze)

        engine_benchmark = (
            learn_glossary.SITE_ROOT / "engine-benchmark" / "index.qmd"
        ).read_text(encoding="utf-8")
        self.assertIn("bms-engine-benchmark-page", engine_benchmark)

        research_index = (
            learn_glossary.SITE_ROOT / "research" / "index.qmd"
        ).read_text(encoding="utf-8")
        self.assertIn("bms-research-index", research_index)
        self.assertNotIn("term-lookup: false", research_index)

        link_policy = (
            learn_glossary.SITE_ROOT
            / "_extensions"
            / "bms-link-policy"
            / "bms-link-policy.lua"
        ).read_text(encoding="utf-8")
        self.assertIn("link.attributes.target = nil", link_policy)
        self.assertNotIn("link.attributes.download =", link_policy)
        self.assertNotIn("link.target =", link_policy)

    def test_learn_and_research_terms_metadata_is_canonical(self) -> None:
        canonical = {entry["slug"] for entry in self.entries}
        self.assertEqual(len(self.tracks), 3)
        self.assertEqual(len(self.lessons), 4)
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

    def test_cube_sequence_is_preserved_in_generated_track_index(self) -> None:
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
        self.assertIn("learn-track-index: doubling-cube", cube_index)
        self.assertIn("{{< include _lesson-index.html >}}", cube_index)
        generated = (learn_glossary.CUBE_ROOT / "_lesson-index.html").read_text(
            encoding="utf-8"
        )
        self.assertTrue(
            generated.index(str(self.cube_lessons[0]["title"]))
            < generated.index(str(self.cube_lessons[1]["title"]))
        )
        self.assertNotIn("data-bms-filter-track", generated)
        self.assertIn("data-bms-filter-term", generated)

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
            "single curriculum sequence",
            "learn-track-index",
            "learn-order",
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

        navigation = learn_glossary.GENERATED_NAVIGATION_PATH.read_text(
            encoding="utf-8"
        )
        sidebar_paths = [f"learn/cube/{path}" for path in expected_paths]
        self.assertTrue(
            navigation.index(sidebar_paths[0]) < navigation.index(sidebar_paths[1])
        )
        for path in sidebar_paths:
            self.assertEqual(navigation.count(path), 1)

        cube_index = (learn_glossary.CUBE_ROOT / "index.qmd").read_text(
            encoding="utf-8"
        )
        self.assertIn("learn-track-order: 2", cube_index)
        for lesson in self.cube_lessons:
            lesson_source = lesson["path"].read_text(encoding="utf-8")
            self.assertEqual(lesson_source.count("cube-order:"), 0)
            self.assertEqual(lesson_source.count("learn-order:"), 1)

    def test_learn_catalogue_uses_sidebar_hierarchy_and_lesson_metadata(self) -> None:
        self.assertEqual(
            [section["title"] for section in self.lesson_sections],
            ["Start Here", "The Doubling Cube", "Opening Play Lab"],
        )
        catalogue = (
            learn_glossary.GENERATED_LESSON_CATALOGUE_PATH.read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(catalogue.count("data-bms-learn-item"), len(self.lessons))
        self.assertEqual(
            catalogue.count('class="bms-learn-catalogue-description"'),
            len(self.lessons),
        )
        self.assertNotRegex(
            catalogue,
            r'<details class="bms-learn-catalogue-description"[^>]*\sopen',
        )
        self.assertEqual(
            catalogue.count(
                '<details class="bms-learn-catalogue-section" '
                "data-bms-learn-group"
            ),
            3,
        )
        self.assertEqual(
            re.findall(
                r'<span class="bms-learn-track-number"[^>]*>([^<]+)</span>',
                catalogue,
            ),
            ["I", "II", "III"],
        )
        self.assertEqual(
            re.findall(
                r'<span class="bms-learn-lesson-number"[^>]*>([^<]+)</span>',
                catalogue,
            ),
            ["1", "2", "1", "2"],
        )
        self.assertNotIn("bms-learn-catalogue-tag", catalogue)
        self.assertNotIn(">Description<", catalogue)
        self.assertIn("Difficulty Filter", catalogue)
        self.assertIn("Learning Track Filter", catalogue)
        self.assertIn("Term Filter", catalogue)
        self.assertIn("data-bms-filter-term", catalogue)
        self.assertEqual(catalogue.count("data-bms-learn-collapse-all"), 1)
        self.assertEqual(catalogue.count("data-bms-learn-expand-all"), 1)
        for lesson in self.lessons:
            self.assertIn(
                f'href="{lesson["route"]}">{lesson["title"]}</a>',
                catalogue,
            )
            self.assertIn(str(lesson["description"]), catalogue)

        learn_index = (learn_glossary.LEARN_ROOT / "index.qmd").read_text(
            encoding="utf-8"
        )
        self.assertIn("{{< include _lesson-catalogue.html >}}", learn_index)
        for lesson in self.lessons:
            self.assertNotIn(str(lesson["relative_path"]), learn_index)

        navigation = learn_glossary.GENERATED_NAVIGATION_PATH.read_text(
            encoding="utf-8"
        )
        self.assertIn("Generated by scripts/learn_glossary.py", navigation)
        for track in self.lesson_sections:
            self.assertIn(
                f'{learn_glossary.roman_number(int(track["order"]))} '
                f'{track["title"]}',
                navigation,
            )
            track_page = track["path"].read_text(encoding="utf-8")
            self.assertIn("{{< include _lesson-index.html >}}", track_page)
            generated_track = (
                track["path"].parent / "_lesson-index.html"
            ).read_text(encoding="utf-8")
            self.assertIn('data-bms-learn-mode="track"', generated_track)
            self.assertIn("Term Filter", generated_track)
            self.assertNotIn("Learning Track Filter", generated_track)

    def test_lesson_finder_is_removed_and_track_links_target_learn(self) -> None:
        self.assertFalse(
            (learn_glossary.LEARN_ROOT / "lesson-finder" / "index.qmd").exists()
        )
        public_sources = [
            learn_glossary.SITE_ROOT / "_quarto.yml",
            learn_glossary.SITE_ROOT / "404.qmd",
            learn_glossary.LEARN_ROOT / "index.qmd",
            ROOT / "scripts" / "bms_post_render.py",
        ]
        for path in public_sources:
            self.assertNotIn(
                "lesson-finder",
                path.read_text(encoding="utf-8"),
                str(path.relative_to(ROOT)),
            )
        taxonomy_filter = (
            learn_glossary.SITE_ROOT
            / "_extensions"
            / "bms-learn-taxonomy"
            / "bms-learn-taxonomy.lua"
        ).read_text(encoding="utf-8")
        self.assertIn('href="/learn/?track=', taxonomy_filter)

    def test_track_landings_use_generated_difficulty_and_term_filters(self) -> None:
        cube_index = (learn_glossary.CUBE_ROOT / "index.qmd").read_text(
            encoding="utf-8"
        )
        self.assertIn("term-lookup: false", cube_index)
        self.assertIn("lesson-taxonomy: false", cube_index)
        self.assertIn("{{< include _lesson-index.html >}}", cube_index)

        generated = (learn_glossary.CUBE_ROOT / "_lesson-index.html").read_text(
            encoding="utf-8"
        )
        difficulty_buttons = set(
            re.findall(r'data-bms-filter-difficulty="([^"]+)"', generated)
        )
        term_buttons = set(
            re.findall(r'data-bms-filter-term="([^"]+)"', generated)
        )
        expected_difficulties = {
            str(value)
            for lesson in self.cube_lessons
            for value in lesson["categories"]
        }
        cube_curriculum_lessons = [
            lesson
            for lesson in self.lessons
            if lesson["track_id"] == "doubling-cube"
        ]
        expected_terms = {
            str(value)
            for lesson in cube_curriculum_lessons
            for value in lesson["terms"]
        }
        self.assertEqual(difficulty_buttons, expected_difficulties)
        self.assertEqual(term_buttons, expected_terms)
        self.assertNotIn("data-bms-filter-track", generated)
        self.assertEqual(
            generated.count('aria-pressed="false"'),
            len(difficulty_buttons) + len(term_buttons),
        )

        taxonomy_filter = (
            learn_glossary.SITE_ROOT
            / "_extensions"
            / "bms-learn-taxonomy"
            / "bms-learn-taxonomy.lua"
        ).read_text(encoding="utf-8")
        self.assertIn('doc.meta["lesson-taxonomy"]', taxonomy_filter)
        self.assertIn('doc.meta["learn-track"]', taxonomy_filter)
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

    def test_track_roman_and_lesson_arabic_numbering_is_generated(self) -> None:
        css = (
            learn_glossary.SITE_ROOT / "assets" / "bms-learn.css"
        ).read_text(encoding="utf-8")
        self.assertFalse(
            (learn_glossary.LEARN_ROOT / "_lesson-listing.ejs.md").exists()
        )
        self.assertEqual(learn_glossary.roman_number(1), "I")
        self.assertEqual(learn_glossary.roman_number(3), "III")
        self.assertIn(".bms-learn-track-number", css)
        self.assertIn(".bms-learn-lesson-number", css)
        self.assertNotIn(
            ".bms-learn-catalogue-item + .bms-learn-catalogue-item",
            css,
        )
        for lesson in self.cube_lessons:
            self.assertNotRegex(str(lesson["title"]), r"^\d+\.\s")

    def test_compact_site_lookup_data_is_public_safe_and_complete(self) -> None:
        lookup = json.loads(
            learn_glossary.GENERATED_LOOKUP_DATA_PATH.read_text(
                encoding="utf-8"
            )
        )
        entries = lookup["entries"]
        self.assertEqual(len(entries), 624)
        self.assertEqual(
            sum(len(entry["aliases"]) for entry in entries),
            181,
        )
        self.assertEqual(
            sum(len(entry["related_lessons"]) for entry in entries),
            40,
        )
        self.assertTrue(all(entry["definition"] for entry in entries))
        learn_glossary.assert_no_forbidden_keys(lookup)
        learn_glossary.assert_no_forbidden_text(
            learn_glossary.GENERATED_LOOKUP_DATA_PATH.read_text(
                encoding="utf-8"
            ),
            "compact site lookup data",
        )

    def test_site_navigation_and_lookup_controls_contract(self) -> None:
        config = (learn_glossary.SITE_ROOT / "_quarto.yml").read_text(
            encoding="utf-8"
        )
        research = config.index("text: Research")
        glossary = config.index("text: Glossary")
        about = config.index("text: About")
        self.assertLess(research, glossary)
        self.assertLess(glossary, about)
        self.assertIn("assets/bms-glossary-lookup.json", config)

        javascript = (
            learn_glossary.SITE_ROOT / "assets" / "bms-learn.js"
        ).read_text(encoding="utf-8")
        for required in (
            "initializeMobileLessonBar",
            r"\u2190 Expand Lesson Index",
            r"Look Up a Term \u2192",
            "data-bms-site-back-to-top",
            "data-bms-toc-toggle",
            "data-bms-margin-sidebar-toggle",
            "bms-site-tools--sidebar",
            "bms-site-tools--editorial-dock",
            "bms-site-tools--floating",
            'aria-controls="bms-term-lookup-panel"',
            'aria-controls="quarto-margin-sidebar"',
            "Collapse term lookup to the right",
            "Collapse TOC",
            "Expand TOC",
            "Collapse all right sidebar content",
            "Expand all right sidebar content",
            "bms-toc-collapsed",
            "bms-margin-sidebar-collapsed",
            "marginSidebar.appendChild(tools)",
            "inEditorialDock",
            "bms-research-index",
            "desktopCollapsed",
            "tocCollapsed",
            "marginSidebarCollapsed",
            "/assets/bms-glossary-lookup.json",
            "renderLookupResult",
            "related_lessons",
            r"Full Glossary Lookup \u2192",
            "isMainSiteIndex",
        ):
            self.assertIn(required, javascript)

        css = (
            learn_glossary.SITE_ROOT / "assets" / "bms-learn.css"
        ).read_text(encoding="utf-8")
        catalogue_section_css = re.search(
            r"\.bms-learn-catalogue-section \{([^}]*)\}",
            css,
        )
        self.assertIsNotNone(catalogue_section_css)
        self.assertNotIn("border-top:", catalogue_section_css.group(1))
        self.assertNotIn("border-bottom:", catalogue_section_css.group(1))
        self.assertIn(
            ".bms-learn-filter[aria-pressed=\"true\"]:hover",
            css,
        )
        self.assertIn("color: var(--bms-ivory)", css)
        self.assertIn(
            "body:is(.bms-learn-index, .bms-learn-track-index)"
            " .bms-learn-clear",
            css,
        )
        self.assertRegex(
            css,
            r"body:is\(\.bms-learn-index, \.bms-learn-track-index\)"
            r"\s+\.bms-learn-filter-disclosure \{\s+border-top: 0;",
        )
        self.assertRegex(
            css,
            r"body\.bms-learn-article #quarto-margin-sidebar \{[^}]*"
            r"width: clamp\(10rem, 16vw, 18rem\);[^}]*"
            r"min-width: clamp\(10rem, 16vw, 18rem\);",
        )
        self.assertRegex(
            css,
            r"body\.bms-engine-benchmark-page #quarto-margin-sidebar \{[^}]*"
            r"width: clamp\(10rem, 16vw, 18rem\);[^}]*"
            r"min-width: clamp\(10rem, 16vw, 18rem\);",
        )
        self.assertRegex(
            css,
            r"\.bms-site-tools--sidebar \.bms-term-lookup-reveal \{[^}]*"
            r"white-space: nowrap;",
        )
        self.assertRegex(
            css,
            r"body\.bms-analyze-page \.bms-site-tools--floating,[^}]*"
            r"left: calc\(50% \+ 26\.625rem\);",
        )
        self.assertRegex(
            css,
            r"\.bms-term-lookup-controls button \{[^}]*"
            r"background: var\(--bms-surface\);[^}]*"
            r"color: var\(--bms-link\);",
        )
        for required in (
            "#quarto-margin-sidebar > *",
            "opacity: 1 !important",
            "#quarto-margin-sidebar #TOC[data-toc-expanded] ul.collapse",
            "#quarto-toc-toggle",
            "display: none !important",
            "#quarto-margin-sidebar .bms-site-tools",
            ".bms-site-tools--sidebar .bms-term-lookup-reveal",
            ".bms-site-tools--sidebar .bms-toc-toggle",
            ".bms-site-tools--sidebar .bms-margin-sidebar-toggle",
            ".bms-site-tools--sidebar .bms-site-back-to-top",
            "#quarto-margin-sidebar.bms-margin-sidebar-collapsed",
            "#quarto-margin-sidebar.bms-toc-collapsed #TOC",
            "> :not(.bms-margin-sidebar-toggle)",
            ".bms-site-tools--floating",
            ".bms-site-tools--editorial-dock",
            ".bms-term-lookup--floating",
            "z-index: 1060",
        ):
            self.assertIn(required, css)

    def test_mobile_brand_wraps_and_has_a_narrow_screen_fallback(self) -> None:
        css = (
            learn_glossary.SITE_ROOT / "assets" / "bms-shared.css"
        ).read_text(encoding="utf-8")
        for required in (
            ".navbar-brand-container > .navbar-brand-logo",
            "white-space: normal",
            ".quarto-secondary-nav .quarto-page-breadcrumbs",
            "@media (max-width: 350px)",
            'content: "BMS"',
        ):
            self.assertIn(required, css)

    def test_learn_home_contains_only_generated_catalogue(self) -> None:
        source = (learn_glossary.LEARN_ROOT / "index.qmd").read_text(
            encoding="utf-8"
        )
        body = source.split("---", 2)[-1].strip()
        self.assertEqual(body, "{{< include _lesson-catalogue.html >}}")
        for removed in (
            "Come with a question",
            "Start with the Cube Lessons",
            "Look Up a Term",
            "How Each Lesson Works",
            "A Real Question",
            "A Board Position",
            "A Reusable Idea",
        ):
            self.assertNotIn(removed, source)

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
            with (
                mock.patch.object(
                    bms_pre_render,
                    "invalidate_full_build_marker",
                    return_value=False,
                ),
                mock.patch.object(bms_pre_render, "run") as run,
            ):
                self.assertEqual(bms_pre_render.main(), 0)
                run.assert_not_called()

        with mock.patch.dict(
            os.environ,
            {"QUARTO_PROJECT_RENDER_ALL": "1"},
            clear=True,
        ):
            with (
                mock.patch.object(
                    bms_pre_render,
                    "invalidate_full_build_marker",
                    return_value=False,
                ),
                mock.patch.object(bms_pre_render, "run") as run,
            ):
                self.assertEqual(bms_pre_render.main(), 0)
                self.assertEqual(run.call_count, 2)
                commands = [call.args[0] for call in run.call_args_list]
                self.assertIn("learn_glossary.py", " ".join(commands[0]))
                self.assertIn("generate", commands[0])
                self.assertIn("run_social_pipeline.py", " ".join(commands[1]))

        with writable_test_directory() as runtime:
            marker = runtime / ".bms-full-build.json"
            marker.write_text("stale", encoding="utf-8")
            self.assertTrue(bms_pre_render.invalidate_full_build_marker(marker))
            self.assertFalse(marker.exists())

    def test_same_tab_policy_preserves_download_mailto_and_tel_destinations(
        self,
    ) -> None:
        link_policy = (
            learn_glossary.SITE_ROOT
            / "_extensions"
            / "bms-link-policy"
            / "bms-link-policy.lua"
        ).read_text(encoding="utf-8")
        self.assertNotIn("link.target =", link_policy)
        self.assertNotIn("link.attributes.download =", link_policy)
        self.assertNotIn("link.attributes.href =", link_policy)
        self.assertNotIn("link.attributes.action =", link_policy)
        for representative in (
            '<a href="/files/guide.pdf" download>Download</a>',
            '<a href="mailto:hello@example.com">Email</a>',
            '<a href="tel:+14165550123">Call</a>',
        ):
            self.assertNotIn("target=", representative)

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

    def test_post_render_404_and_footer_routes_are_clean_and_narrow(self) -> None:
        dirty_404 = (
            '<a href="/.">Home</a>'
            '<a href="/.\\learn/">Learn</a>'
            '<a href="/./learn/glossary/">Glossary</a>'
            '<a href="/.\\research/">Research</a>'
            '<a href="/unrelated/">Unrelated</a>'
        )
        normalized_404, changed = bms_post_render.normalized_404_text(dirty_404)
        self.assertTrue(changed)
        for route in learn_glossary.NOT_FOUND_ROUTES:
            self.assertIn(f'href="{route}"', normalized_404)
        self.assertIn('href="/unrelated/"', normalized_404)

        dirty_footer = (
            '<main><a href="../../updates/index.xml">Body link</a></main>'
            '<footer><a href="..\\..\\updates/index.xml">RSS</a></footer>'
        )
        normalized_footer, footer_changed = (
            bms_post_render.normalized_footer_rss_text(dirty_footer)
        )
        self.assertTrue(footer_changed)
        self.assertIn(
            '<main><a href="../../updates/index.xml">Body link</a></main>',
            normalized_footer,
        )
        self.assertIn(
            '<footer><a href="/updates/index.xml">RSS</a></footer>',
            normalized_footer,
        )

    def test_rendered_validator_distinguishes_partial_and_missing_artifacts(
        self,
    ) -> None:
        with writable_test_directory() as output_root:
            with self.assertRaisesRegex(
                learn_glossary.ValidationError,
                "partial or has not completed a full site build",
            ):
                learn_glossary.validate_full_build_output(output_root)

            marker = output_root / learn_glossary.FULL_BUILD_MARKER_NAME
            bms_post_render.write_full_build_marker(marker)
            with self.assertRaisesRegex(
                learn_glossary.ValidationError,
                "site output is incomplete",
            ):
                learn_glossary.validate_full_build_output(output_root)

            for relative in learn_glossary.RENDERED_CORE_PATHS:
                path = output_root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("", encoding="utf-8")
            learn_glossary.validate_full_build_output(output_root)

            with self.assertRaisesRegex(
                learn_glossary.ValidationError,
                "root 404.html is missing",
            ):
                learn_glossary.check_rendered(output_root)

            not_found = output_root / "404.html"
            not_found.write_text(
                "Page closed out suspiciously bounced off the board "
                + " ".join(
                    f'<a href="{route}">{route}</a>'
                    for route in learn_glossary.NOT_FOUND_ROUTES
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                learn_glossary.ValidationError,
                "Updates RSS feed is missing",
            ):
                learn_glossary.check_rendered(output_root)

            feed = output_root / "updates" / "index.xml"
            feed.write_text("<rss><channel /></rss>", encoding="utf-8")
            with self.assertRaisesRegex(
                learn_glossary.ValidationError,
                "sitemap.xml is missing",
            ):
                learn_glossary.check_rendered(output_root)

    def test_rendered_404_and_footer_diagnostics_are_specific(self) -> None:
        with self.assertRaisesRegex(
            learn_glossary.ValidationError,
            "404 links are malformed",
        ):
            learn_glossary.validate_rendered_404(
                "Page closed out suspiciously bounced off the board"
            )

        with writable_test_directory() as output_root:
            for relative in learn_glossary.RSS_FOOTER_REPRESENTATIVE_PATHS:
                path = output_root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(
                    '<footer><a href="../updates/index.xml">RSS</a></footer>',
                    encoding="utf-8",
                )
            with self.assertRaisesRegex(
                learn_glossary.ValidationError,
                "footer RSS mismatch",
            ):
                learn_glossary.validate_representative_rss_footers(output_root)

    def test_social_render_state_includes_os_identity_without_layout_changes(
        self,
    ) -> None:
        renderer = (
            ROOT
            / "social_generator"
            / "scripts"
            / "social"
            / "render_cards.py"
        ).read_text(encoding="utf-8")
        self.assertIn("import platform", renderer)
        self.assertIn('"render_platform": {', renderer)
        self.assertIn('"system": platform.system()', renderer)
        self.assertIn('"machine": platform.machine()', renderer)

    def test_validation_reports_single_page_counts(self) -> None:
        result = learn_glossary.validate_generated()
        self.assertEqual(result["source_entries"], 805)
        self.assertEqual(result["canonical_entries"], 624)
        self.assertEqual(result["alias_entries"], 181)
        self.assertEqual(result["canonical_anchors"], 624)
        self.assertEqual(result["standalone_term_pages"], 0)
        self.assertEqual(result["generated_files"], 8)
        self.assertEqual(result["lesson_catalogue_sections"], 3)
        self.assertEqual(result["learn_tracks"], 3)
        self.assertEqual(result["lessons"], 4)
        self.assertEqual(result["cube_lessons"], 2)
        self.assertEqual(result["updates_publications"], 0)
        self.assertEqual(result["related_lesson_links"], 40)
        self.assertEqual(result["related_research_links"], 3)


if __name__ == "__main__":
    unittest.main()
