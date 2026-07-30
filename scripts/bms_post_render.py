from __future__ import annotations

import html
import json
import os
import re
import sys
from datetime import date, datetime, time, timezone
from email.utils import format_datetime, parsedate_to_datetime
from pathlib import Path
from xml.etree import ElementTree


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "site" / "_site"
SITEMAP_PATH = OUTPUT_ROOT / "sitemap.xml"
NOT_FOUND_PATH = OUTPUT_ROOT / "404.html"
FULL_BUILD_MARKER = OUTPUT_ROOT / ".bms-full-build.json"
UPDATES_FEED_PATH = OUTPUT_ROOT / "updates" / "index.xml"
GLOSSARY_DATA_PATH = REPO_ROOT / "site" / "data" / "glossary.json"
FULL_BUILD_MARKER_SCHEMA = 1
GLOSSARY_INDEX_URL = (
    "https://backgammon-made-simple.github.io/learn/glossary/index.html"
)
NOT_FOUND_ROUTE_MAP = {
    "/.": "/",
    "/./": "/",
    "/./learn/": "/learn/",
    "/./learn/glossary/": "/learn/glossary/",
    "/./research/": "/research/",
}
FOOTER_PATTERN = re.compile(r"<footer\b.*?</footer>", flags=re.DOTALL)
HREF_PATTERN = re.compile(r'(\bhref=")([^"]+)(")')
GLOSSARY_CANONICAL_URL = (
    "https://backgammon-made-simple.github.io/learn/glossary/"
)
GLOSSARY_FEED_URL_PREFIX = GLOSSARY_CANONICAL_URL + "#"
RSS_NAMESPACES = {
    "atom": "http://www.w3.org/2005/Atom",
    "content": "http://purl.org/rss/1.0/modules/content/",
    "dc": "http://purl.org/dc/elements/1.1/",
    "media": "http://search.yahoo.com/mrss/",
}


def glossary_feed_records(data: object) -> list[dict[str, str]]:
    if not isinstance(data, dict) or not isinstance(data.get("entries"), list):
        raise RuntimeError("Glossary RSS source must contain an entries list")
    records: list[dict[str, str]] = []
    for index, entry in enumerate(data["entries"]):
        if not isinstance(entry, dict):
            raise RuntimeError(f"Glossary RSS entry {index} must be an object")
        required: dict[str, str] = {}
        for field in ("date_added", "definition", "slug", "term"):
            value = entry.get(field)
            if not isinstance(value, str) or not value.strip():
                raise RuntimeError(
                    f"Glossary RSS entry {index} requires non-empty {field}"
                )
            required[field] = value.strip()
        try:
            date.fromisoformat(required["date_added"])
        except ValueError as error:
            raise RuntimeError(
                f"Glossary RSS entry {required['slug']} has invalid date_added"
            ) from error
        records.append({
            "date": required["date_added"],
            "definition": required["definition"],
            "link": GLOSSARY_FEED_URL_PREFIX + required["slug"],
            "title": f"Glossary: {required['term']}",
        })
    records.sort(
        key=lambda record: (
            -date.fromisoformat(record["date"]).toordinal(),
            record["title"].casefold(),
            record["link"],
        )
    )
    return records


def rss_publication_date(value: str) -> str:
    published = datetime.combine(
        date.fromisoformat(value),
        time.min,
        tzinfo=timezone.utc,
    )
    return format_datetime(published, usegmt=True)


def glossary_feed_item(record: dict[str, str]) -> ElementTree.Element:
    item = ElementTree.Element("item")
    ElementTree.SubElement(item, "title").text = record["title"]
    ElementTree.SubElement(item, "link").text = record["link"]
    guid = ElementTree.SubElement(item, "guid", {"isPermaLink": "true"})
    guid.text = record["link"]
    ElementTree.SubElement(item, "pubDate").text = rss_publication_date(
        record["date"]
    )
    ElementTree.SubElement(item, "category").text = "Glossary"
    ElementTree.SubElement(item, "description").text = record["definition"]
    paragraphs = [
        paragraph.strip()
        for paragraph in re.split(r"\n\s*\n", record["definition"])
        if paragraph.strip()
    ]
    encoded = ElementTree.SubElement(
        item,
        f"{{{RSS_NAMESPACES['content']}}}encoded",
    )
    encoded.text = "".join(
        f"<p>{html.escape(paragraph)}</p>"
        for paragraph in paragraphs
    )
    return item


def feed_item_sort_key(item: ElementTree.Element) -> tuple[float, str, str]:
    raw_date = item.findtext("pubDate", "")
    try:
        parsed_date = parsedate_to_datetime(raw_date)
        if parsed_date.tzinfo is None:
            parsed_date = parsed_date.replace(tzinfo=timezone.utc)
        timestamp = parsed_date.timestamp()
    except (TypeError, ValueError):
        timestamp = float("-inf")
    return (
        -timestamp,
        item.findtext("title", "").casefold(),
        item.findtext("link", ""),
    )


def augmented_updates_feed_text(
    text: str,
    glossary_records: list[dict[str, str]],
) -> tuple[str, bool]:
    for prefix, namespace in RSS_NAMESPACES.items():
        ElementTree.register_namespace(prefix, namespace)
    try:
        root = ElementTree.fromstring(text)
    except ElementTree.ParseError as error:
        raise RuntimeError("Updates RSS feed is invalid XML") from error
    channel = root.find("channel")
    if channel is None:
        raise RuntimeError("Updates RSS feed has no channel")

    for item in list(channel.findall("item")):
        if item.findtext("link", "").startswith(GLOSSARY_FEED_URL_PREFIX):
            channel.remove(item)
    for record in glossary_records:
        channel.append(glossary_feed_item(record))

    items = list(channel.findall("item"))
    for item in items:
        channel.remove(item)
    for item in sorted(items, key=feed_item_sort_key):
        channel.append(item)

    ElementTree.indent(root, space="  ")
    updated = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        + ElementTree.tostring(root, encoding="unicode", short_empty_elements=True)
        + "\n"
    )
    return updated, updated != text


def augment_updates_rss_feed(
    feed_path: Path = UPDATES_FEED_PATH,
    data_path: Path = GLOSSARY_DATA_PATH,
) -> int:
    if not feed_path.exists():
        print(f"Updates RSS feed not present; glossary items skipped: {feed_path}")
        return 0
    data = json.loads(data_path.read_text(encoding="utf-8"))
    records = glossary_feed_records(data)
    current = feed_path.read_text(encoding="utf-8")
    updated, changed = augmented_updates_feed_text(current, records)
    if changed:
        feed_path.write_text(updated, encoding="utf-8", newline="\n")
    return len(records)


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
    glossary_feed_count = augment_updates_rss_feed()
    print(
        f"Updates RSS includes {glossary_feed_count} approved glossary definitions."
    )
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
