from __future__ import annotations

import hashlib
import importlib.util
import shutil
import sys
import unittest
import uuid
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
GENERATOR_PATH = ROOT / "scripts" / "generate_scrolling_test_lessons.py"
SPEC = importlib.util.spec_from_file_location(
    "generate_scrolling_test_lessons",
    GENERATOR_PATH,
)
assert SPEC and SPEC.loader
generator = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = generator
SPEC.loader.exec_module(generator)
learn_glossary = generator.learn_glossary


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ScrollingTestLessonGeneratorTests(unittest.TestCase):
    def setUp(self) -> None:
        runtime_root = (
            ROOT
            / "task-work"
            / "BMS-CONTINUOUS-LEARN-03"
            / "runtime"
        )
        runtime_root.mkdir(parents=True, exist_ok=True)
        self.test_root = runtime_root / f"generator-{uuid.uuid4().hex}"

    def tearDown(self) -> None:
        if self.test_root.exists():
            shutil.rmtree(self.test_root)

    def test_uses_existing_track_and_lesson_discovery(self) -> None:
        tracks, real_lessons = generator.discover_curriculum_inputs()
        self.assertEqual(
            [track["id"] for track in tracks],
            [track["id"] for track in learn_glossary.discover_tracks()],
        )
        self.assertEqual(
            [lesson["path"] for lesson in real_lessons],
            [
                lesson["path"]
                for lesson in learn_glossary.discover_lessons(
                    include_scrolling_tests=False
                )
            ],
        )
        self.assertFalse(
            any(
                "scrolling-test" in Path(str(lesson["relative_path"])).parts
                for lesson in real_lessons
            )
        )

    def test_ten_deterministic_lessons_are_built_for_every_track(self) -> None:
        tracks, real_lessons = generator.discover_curriculum_inputs()
        outputs = generator.build_expected_outputs(self.test_root)
        self.assertEqual(
            len(outputs),
            generator.LESSONS_PER_TRACK * len(tracks),
        )

        real_max = {
            str(track["id"]): max(
                (
                    int(lesson["order"])
                    for lesson in real_lessons
                    if lesson["track_id"] == track["id"]
                ),
                default=0,
            )
            for track in tracks
        }
        for track in tracks:
            track_id = str(track["id"])
            paths = sorted((self.test_root / track_id).glob("*.qmd"))
            self.assertEqual(paths, [])
            expected_paths = sorted(
                path for path in outputs if path.parent.name == track_id
            )
            self.assertEqual(len(expected_paths), 10)
            for index, path in enumerate(expected_paths, start=1):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(outputs[path], encoding="utf-8", newline="\n")
                metadata = learn_glossary.parse_complete_front_matter(path)
                self.assertEqual(metadata["learn-track"], track_id)
                self.assertEqual(
                    int(metadata["learn-order"]),
                    real_max[track_id] + index,
                )
                self.assertEqual(
                    metadata["categories"],
                    [generator.DIFFICULTY_CYCLE[index - 1]],
                )
                self.assertEqual(
                    metadata["title"],
                    f"Scrolling Test: {track['title']} {index:02d}",
                )
                self.assertIn(
                    generator.WARNING_TEXT,
                    path.read_text(encoding="utf-8"),
                )

    def test_first_two_cube_fixtures_include_rich_disclosure(self) -> None:
        outputs = generator.build_expected_outputs(self.test_root)
        rich_paths = {
            self.test_root / "doubling-cube" / "lesson-01.qmd",
            self.test_root / "doubling-cube" / "lesson-02.qmd",
        }
        included_paths = {
            path
            for path, content in outputs.items()
            if generator.RICH_DISCLOSURE_INCLUDE in content
        }
        self.assertEqual(included_paths, rich_paths)
        real_lesson = (
            ROOT / "site" / "learn" / "cube" / "what-the-cube-is-asking.qmd"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "{{< include ../../includes/scrolling-position-disclosure.html >}}",
            real_lesson,
        )

    def test_rich_disclosure_exercises_svg_ids_buttons_and_nesting(self) -> None:
        include_path = (
            ROOT / "site" / "includes" / "scrolling-position-disclosure.html"
        )
        content = include_path.read_text(encoding="utf-8")
        self.assertEqual(content.count("<svg"), 2)
        self.assertEqual(
            content.count('class="bms-button-outline bms-answer-choice"'),
            2,
        )
        self.assertEqual(content.count("<details"), 2)
        self.assertIn('data-answer-panel="bms-scroll-fixture-follow-up"', content)
        self.assertIn('id="bms-scroll-fixture-follow-up"', content)
        self.assertIn('fill="url(#bms-scroll-fixture-board-gradient)"', content)
        self.assertIn('clip-path="url(#bms-scroll-fixture-focus-clip)"', content)
        self.assertIn('aria-labelledby="bms-scroll-fixture-position-title ', content)
        self.assertIn('aria-labelledby="bms-scroll-fixture-follow-up-title ', content)

    def test_empty_track_receives_ten_lessons(self) -> None:
        tracks, real_lessons = generator.discover_curriculum_inputs()
        empty_track = next(
            track
            for track in tracks
            if not any(
                lesson["track_id"] == track["id"]
                for lesson in real_lessons
            )
        )
        outputs = generator.build_expected_outputs(self.test_root)
        empty_outputs = [
            path
            for path in outputs
            if path.parent.name == empty_track["id"]
        ]
        self.assertEqual(len(empty_outputs), 10)
        for index, path in enumerate(sorted(empty_outputs), start=1):
            metadata = yaml.safe_load(outputs[path].split("---", 2)[1])
            self.assertEqual(metadata["learn-order"], index)

    def test_generate_is_idempotent_and_preserves_real_lessons(self) -> None:
        real_paths = [
            Path(lesson["path"])
            for lesson in learn_glossary.discover_lessons(
                include_scrolling_tests=False
            )
        ]
        before = {path: digest(path) for path in real_paths}
        first = generator.generate(self.test_root)
        second = generator.generate(self.test_root)
        self.assertEqual(first.created, 30)
        self.assertEqual(first.unchanged, 0)
        self.assertEqual(second.created, 0)
        self.assertEqual(second.unchanged, 30)
        self.assertEqual(
            {path: digest(path) for path in real_paths},
            before,
        )

    def test_validate_detects_missing_and_modified_files(self) -> None:
        generator.generate(self.test_root)
        missing_path = self.test_root / "start-here" / "lesson-01.qmd"
        missing_path.unlink()
        with self.assertRaisesRegex(
            generator.FixtureValidationError,
            "missing=1",
        ):
            generator.validate(self.test_root)

        generator.generate(self.test_root)
        modified_path = self.test_root / "start-here" / "lesson-02.qmd"
        modified_path.write_text(
            modified_path.read_text(encoding="utf-8") + "\nModified.\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(
            generator.FixtureValidationError,
            "modified=1",
        ):
            generator.validate(self.test_root)

    def test_clean_removes_only_marked_generated_fixtures(self) -> None:
        generator.generate(self.test_root)
        preserved = self.test_root / "preserve-real-content.qmd"
        preserved.write_text(
            "---\ntitle: Preserve\n---\nNot generated.\n",
            encoding="utf-8",
        )
        result = generator.clean(self.test_root)
        self.assertEqual(result.removed, 30)
        self.assertEqual(result.invalid, 1)
        self.assertTrue(preserved.exists())
        self.assertEqual(
            list(self.test_root.rglob("lesson-*.qmd")),
            [],
        )


if __name__ == "__main__":
    unittest.main()
