from __future__ import annotations

import importlib.util
import json
import shutil
import sys
import unittest
import uuid
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "release_ui_static_check.py"
SPEC = importlib.util.spec_from_file_location("release_ui_static_check", SCRIPT_PATH)
assert SPEC and SPEC.loader
release_check = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = release_check
SPEC.loader.exec_module(release_check)


def page_html(body: str, *, head: str = "") -> str:
    return (
        "<!doctype html><html><head>"
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"{head}</head><body><main><h1>Fixture</h1>{body}</main></body></html>"
    )


class ReleaseUiStaticCheckTests(unittest.TestCase):
    def setUp(self) -> None:
        runtime_root = ROOT / "task-work" / "BMS-UI-RELEASE" / "runtime"
        runtime_root.mkdir(parents=True, exist_ok=True)
        self.site_dir = runtime_root / f"site-{uuid.uuid4().hex}"
        self.site_dir.mkdir()

    def tearDown(self) -> None:
        if self.site_dir.exists():
            shutil.rmtree(self.site_dir)

    def write(self, relative: str, content: str) -> Path:
        path = self.site_dir / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def test_clean_representative_page_passes(self) -> None:
        self.write("assets/test.svg", "<svg></svg>")
        self.write(
            "learn/index.html",
            page_html(
                '<section id="target">Required marker</section>'
                '<a href="#target">Jump</a>'
                '<img src="/assets/test.svg" alt="">'
            ),
        )
        findings = release_check.audit_page(
            site_dir=self.site_dir,
            route="/learn/",
            required_markers=["Required marker"],
        )
        self.assertEqual(findings, [])

    def test_duplicate_id_broken_link_and_missing_anchor_fail(self) -> None:
        self.write(
            "index.html",
            page_html(
                '<div id="duplicate"></div><div id="duplicate"></div>'
                '<a href="#missing">Missing anchor</a>'
                '<a href="/not-rendered/">Broken page</a>'
            ),
        )
        messages = [
            finding.message
            for finding in release_check.audit_page(
                site_dir=self.site_dir,
                route="/",
            )
        ]
        self.assertTrue(any("duplicate IDs" in message for message in messages))
        self.assertTrue(
            any("missing same-page anchor" in message for message in messages)
        )
        self.assertTrue(any("broken internal link" in message for message in messages))

    def test_intentional_redirect_skips_content_landmarks_but_checks_target(
        self,
    ) -> None:
        self.write("glossary/index.html", page_html("Glossary"))
        redirect = (
            "<!doctype html><html><head>"
            '<meta http-equiv="refresh" content="0; url=/glossary/">'
            "</head><body>Moved</body></html>"
        )
        self.write("learn/glossary/index.html", redirect)
        self.assertEqual(
            release_check.audit_page(
                site_dir=self.site_dir,
                route="/learn/glossary/",
            ),
            [],
        )

        self.write(
            "learn/glossary/index.html",
            redirect.replace("/glossary/", "/missing-glossary/"),
        )
        messages = [
            finding.message
            for finding in release_check.audit_page(
                site_dir=self.site_dir,
                route="/learn/glossary/",
            )
        ]
        self.assertEqual(
            messages,
            ["broken redirect target: /missing-glossary/"],
        )

    def test_manifest_uses_only_current_public_pages(self) -> None:
        manifest = json.loads(
            (ROOT / "scripts" / "ui_release_manifest.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertFalse(
            any("/scrolling-test/" in page["route"] for page in manifest["pages"])
        )

    def test_release_procedure_references_all_automation_layers(self) -> None:
        procedure = (ROOT / "docs" / "ui-release-testing.md").read_text(
            encoding="utf-8"
        )
        shell_runner = (ROOT / "scripts" / "release-ui-check.sh").read_text(
            encoding="utf-8"
        )
        for expected in (
            "scripts/release-ui-check.sh",
            "scripts/release_ui_browser_check.mjs",
            "scripts/ui_release_manifest.json",
            "90 minutes",
            "site/_site",
        ):
            self.assertIn(expected, procedure)
        for expected in (
            "git diff --check",
            "unittest discover",
            "release_ui_static_check.py",
            "test_continuous_research.js",
        ):
            self.assertIn(expected, shell_runner)

    def test_preview_prefers_usable_project_python(self) -> None:
        preview = (ROOT / "scripts" / "preview-site.sh").read_text(
            encoding="utf-8"
        )
        project_python = (
            'PROJECT_PYTHON="${REPO_ROOT}/.venv/Scripts/python.exe"'
        )
        project_selection = 'PYTHON_COMMAND=("${PROJECT_PYTHON}")'
        project_path = 'export PATH="$(dirname "${PROJECT_PYTHON}"):${PATH}"'
        fallback_selection = "elif command -v py"

        self.assertIn(project_python, preview)
        self.assertIn('"${PROJECT_PYTHON}" -c \'import sys\'', preview)
        self.assertIn(project_selection, preview)
        self.assertIn(project_path, preview)
        self.assertLess(preview.index(project_selection), preview.index(fallback_selection))
        self.assertLess(preview.index(project_path), preview.index("quarto preview site"))


if __name__ == "__main__":
    unittest.main()
