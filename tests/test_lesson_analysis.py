import hashlib
import json
import re
import unittest
from pathlib import Path
from xml.etree import ElementTree


ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
FIXTURE_PATH = SITE / "data" / "lesson-analysis-svg-mvp.json"
ASSET_ROOT = (
    SITE
    / "assets"
    / "positions"
    / "lesson-analysis-svg-mvp"
    / "opening-fixture"
)
CUBE_LESSON = SITE / "learn" / "cube" / "what-the-cube-is-asking.qmd"
CHECKER_LESSON = (
    SITE
    / "learn"
    / "cube"
    / "why-is-25-percent-the-basic-take-point.qmd"
)


class LessonAnalysisFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        cls.cube_source = CUBE_LESSON.read_text(encoding="utf-8")
        cls.checker_source = CHECKER_LESSON.read_text(encoding="utf-8")

    def test_fixture_contract_and_explicit_status(self):
        self.assertEqual(
            self.data["schema_version"],
            "bms-lesson-analysis-fixture-v1",
        )
        self.assertEqual(self.data["fixture_status"]["kind"], "fixture-only")
        message = self.data["fixture_status"]["message"].casefold()
        self.assertIn("test fixtures", message)
        self.assertIn("not verified engine output", message)

    def test_cube_fixture_supports_all_requested_answer_shapes(self):
        cube_cases = self.data["cube_cases"]
        self.assertEqual(
            cube_cases["cube-roll"]["correct_first_action"],
            "roll",
        )
        self.assertEqual(
            cube_cases["cube-double-take"]["actions"]["double"]["responder"][
                "correct_response"
            ],
            "take",
        )
        self.assertEqual(
            cube_cases["cube-double-pass"]["actions"]["double"]["responder"][
                "correct_response"
            ],
            "pass",
        )

    def test_every_referenced_svg_exists_and_parses(self):
        names = set()
        for cube in self.data["cube_cases"].values():
            names.add(cube["initial"]["image"])
            for action in cube["actions"].values():
                if action.get("position"):
                    names.add(action["position"]["image"])
            responder = cube["actions"]["double"].get("responder")
            if responder:
                names.add(responder["image"])
        for checker in self.data["checker_cases"].values():
            names.add(checker["initial"]["image"])
            names.update(candidate["image"] for candidate in checker["candidates"])

        self.assertEqual(
            names,
            {
                "starting.svg",
                "responder-flipped.svg",
                "candidate-1.svg",
                "candidate-2.svg",
                "candidate-3.svg",
            },
        )
        for name in names:
            path = ASSET_ROOT / name
            self.assertTrue(path.is_file(), name)
            root = ElementTree.parse(path).getroot()
            self.assertTrue(root.tag.endswith("svg"), name)

    def test_shared_start_is_one_asset_used_by_both_component_types(self):
        cube_start = self.data["cube_cases"]["cube-double-take"]["initial"][
            "image"
        ]
        checker_start = self.data["checker_cases"][
            "checker-three-candidates"
        ]["initial"]["image"]
        self.assertEqual(cube_start, checker_start)
        starts = list(
            (SITE / "assets" / "positions").rglob("starting.svg")
        )
        self.assertEqual(starts, [ASSET_ROOT / "starting.svg"])

    def test_rejected_double_reuses_the_same_position_in_its_answer(self):
        fixture = self.data["cube_cases"]["cube-roll"]
        self.assertEqual(
            fixture["actions"]["double"]["position"]["image"],
            fixture["initial"]["image"],
        )

    def test_two_lessons_use_root_relative_fixture_loading(self):
        expected = 'data-bms-fixture-src="/data/lesson-analysis-svg-mvp.json"'
        self.assertIn(expected, self.cube_source)
        self.assertIn(expected, self.checker_source)
        self.assertEqual(
            self.cube_source.count("data-bms-cube-decision"),
            2,
        )
        self.assertEqual(
            self.checker_source.count("data-bms-checker-decision"),
            1,
        )
        self.assertNotIn("<svg", self.cube_source.casefold())
        self.assertNotIn("<svg", self.checker_source.casefold())

    def test_qmd_hosts_do_not_hard_code_component_ids(self):
        for source in (self.cube_source, self.checker_source):
            host_blocks = re.findall(
                r"<div\s+.*?data-bms-(?:cube|checker)-decision.*?</div>",
                source,
                flags=re.DOTALL,
            )
            self.assertTrue(host_blocks)
            for block in host_blocks:
                self.assertNotRegex(block, r'(?:^|\s)id="')

    def test_script_is_loaded_before_continuous_lesson_loader(self):
        scripts = (SITE / "includes" / "bms-scripts.html").read_text(
            encoding="utf-8"
        )
        analysis_index = scripts.index("bms-lesson-analysis.js")
        scroll_index = scripts.index("bms-learn-scroll.js")
        self.assertLess(analysis_index, scroll_index)
        implementation = (
            SITE / "assets" / "bms-lesson-analysis.js"
        ).read_text(encoding="utf-8")
        self.assertIn("window.BMSLearn.mountLesson", implementation)
        self.assertIn("mount(rootElement)", implementation)
        self.assertIn("dataset.bmsAnalysisMounted", implementation)

    def test_svg_reuse_cannot_duplicate_inline_ids(self):
        implementation = (
            SITE / "assets" / "bms-lesson-analysis.js"
        ).read_text(encoding="utf-8")
        self.assertIn('element("img", "bms-analysis-position-image")', implementation)
        self.assertIn("img.width = 1200", implementation)
        self.assertIn("img.height = 910", implementation)
        self.assertIn('img.loading = "eager"', implementation)
        self.assertNotIn("fetchSvg", implementation)
        start_hash = hashlib.sha256(
            (ASSET_ROOT / "starting.svg").read_bytes()
        ).hexdigest()
        self.assertEqual(len(start_hash), 64)

    def test_missing_optional_values_are_retained(self):
        candidate = self.data["checker_cases"]["checker-three-candidates"][
            "candidates"
        ][2]
        self.assertIsNone(candidate["winning_probabilities"]["win_gammon"])
        self.assertIsNone(candidate["winning_probabilities"]["lose_gammon"])

    def test_resource_contract_copies_dynamic_assets(self):
        config = (SITE / "_quarto.yml").read_text(encoding="utf-8")
        self.assertIn('"assets/positions/**"', config)
        self.assertIn("data/lesson-analysis-svg-mvp.json", config)
        self.assertIn("assets/bms-lesson-analysis.css", config)
        provenance = ASSET_ROOT / "PROVENANCE.txt"
        self.assertTrue(provenance.is_file())
        self.assertFalse((ASSET_ROOT / "PROVENANCE.md").exists())


if __name__ == "__main__":
    unittest.main()
