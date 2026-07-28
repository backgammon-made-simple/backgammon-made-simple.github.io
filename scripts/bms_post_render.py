from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SITEMAP_PATH = REPO_ROOT / "site" / "_site" / "sitemap.xml"
GLOSSARY_INDEX_URL = (
    "https://backgammon-made-simple.github.io/learn/glossary/index.html"
)
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


def main() -> int:
    changed = normalize_glossary_sitemap_url()
    print(
        "Glossary sitemap clean URL "
        + ("normalized." if changed else "already current.")
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
