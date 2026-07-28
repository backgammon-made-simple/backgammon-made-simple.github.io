from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "site" / "_site"
SITEMAP_PATH = OUTPUT_ROOT / "sitemap.xml"
NOT_FOUND_PATH = OUTPUT_ROOT / "404.html"
FULL_BUILD_MARKER = OUTPUT_ROOT / ".bms-full-build.json"
FULL_BUILD_MARKER_SCHEMA = 1
GLOSSARY_INDEX_URL = (
    "https://backgammon-made-simple.github.io/learn/glossary/index.html"
)
NOT_FOUND_ROUTE_MAP = {
    "/.": "/",
    "/./": "/",
    "/./learn/": "/learn/",
    "/./learn/lesson-finder/": "/learn/lesson-finder/",
    "/./learn/glossary/": "/learn/glossary/",
    "/./research/": "/research/",
}
FOOTER_PATTERN = re.compile(r"<footer\b.*?</footer>", flags=re.DOTALL)
HREF_PATTERN = re.compile(r'(\bhref=")([^"]+)(")')
GLOSSARY_CANONICAL_URL = (
    "https://backgammon-made-simple.github.io/learn/glossary/"
)


def normalized_glossary_sitemap_text(text: str) -> tuple[str, bool]:
    dirty_location = f"<loc>{GLOSSARY_INDEX_URL}</loc>"
    clean_location = f"<loc>{GLOSSARY_CANONICAL_URL}</loc>"
    dirty_count = text.count(dirty_location)
    clean_count = text.count(clean_location)

    if dirty_count == 0 and clean_count == 1:
        return text, False
    if dirty_count != 1 or clean_count != 0:
        raise RuntimeError(
            "Glossary sitemap contract requires exactly one dirty or one clean "
            f"location; found dirty={dirty_count}, clean={clean_count}"
        )

    return text.replace(dirty_location, clean_location), True


def normalize_glossary_sitemap_url(path: Path = SITEMAP_PATH) -> bool:
    if not path.exists():
        print(f"Sitemap not present; clean-URL normalization skipped: {path}")
        return False

    text = path.read_text(encoding="utf-8")
    normalized, changed = normalized_glossary_sitemap_text(text)
    if not changed:
        return False
    path.write_text(
        normalized,
        encoding="utf-8",
        newline="\n",
    )
    return True


def normalized_404_text(text: str) -> tuple[str, bool]:
    def replace_href(match: re.Match[str]) -> str:
        href = match.group(2)
        clean_href = NOT_FOUND_ROUTE_MAP.get(href.replace("\\", "/"))
        if clean_href is None:
            return match.group(0)
        return f"{match.group(1)}{clean_href}{match.group(3)}"

    normalized = HREF_PATTERN.sub(replace_href, text)
    return normalized, normalized != text


def normalize_404_links(path: Path = NOT_FOUND_PATH) -> bool:
    if not path.exists():
        print(f"Rendered 404 not present; clean-link normalization skipped: {path}")
        return False
    text = path.read_text(encoding="utf-8")
    normalized, changed = normalized_404_text(text)
    if changed:
        path.write_text(normalized, encoding="utf-8", newline="\n")
    return changed


def normalized_footer_rss_text(text: str) -> tuple[str, bool]:
    def normalize_footer(match: re.Match[str]) -> str:
        footer = match.group(0)

        def replace_href(href_match: re.Match[str]) -> str:
            href = href_match.group(2).replace("\\", "/")
            if not re.fullmatch(r"(?:/|\./|\.\./)*updates/index\.xml", href):
                return href_match.group(0)
            return (
                f'{href_match.group(1)}/updates/index.xml'
                f"{href_match.group(3)}"
            )

        return HREF_PATTERN.sub(replace_href, footer)

    normalized = FOOTER_PATTERN.sub(normalize_footer, text)
    return normalized, normalized != text


def normalize_footer_rss_links(output_root: Path = OUTPUT_ROOT) -> int:
    if not output_root.exists():
        print(f"Rendered output not present; footer normalization skipped: {output_root}")
        return 0
    changed = 0
    for path in sorted(output_root.rglob("*.html")):
        text = path.read_text(encoding="utf-8")
        normalized, path_changed = normalized_footer_rss_text(text)
        if not path_changed:
            continue
        path.write_text(normalized, encoding="utf-8", newline="\n")
        changed += 1
    return changed


def write_full_build_marker(path: Path = FULL_BUILD_MARKER) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": FULL_BUILD_MARKER_SCHEMA,
        "complete_full_build": True,
    }
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def main() -> int:
    sitemap_changed = normalize_glossary_sitemap_url()
    print(
        "Glossary sitemap clean URL "
        + ("normalized." if sitemap_changed else "already current.")
    )
    not_found_changed = normalize_404_links()
    print(
        "Rendered 404 clean links "
        + ("normalized." if not_found_changed else "already current.")
    )
    footer_count = normalize_footer_rss_links()
    print(f"Normalized Updates RSS footer links in {footer_count} rendered pages.")

    if os.getenv("QUARTO_PROJECT_RENDER_ALL") == "1":
        write_full_build_marker()
        print(f"Recorded complete full build: {FULL_BUILD_MARKER}")
    else:
        print("Partial render: no full-build completion marker recorded.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
