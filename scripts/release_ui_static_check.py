#!/usr/bin/env python3
"""Audit rendered UI pages, anchors, assets, and internal links."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SITE_DIR = REPOSITORY_ROOT / "site" / "_site"
DEFAULT_MANIFEST = Path(__file__).with_name("ui_release_manifest.json")
SKIPPED_SCHEMES = {"data", "http", "https", "mailto", "tel"}
RAW_LEAK_MARKERS = ("{{<", "::: {", "```{=html}")


@dataclass
class PageDocument:
    ids: list[str] = field(default_factory=list)
    links: list[str] = field(default_factory=list)
    assets: list[str] = field(default_factory=list)
    main_count: int = 0
    h1_count: int = 0
    viewport_meta: bool = False


@dataclass(frozen=True)
class Finding:
    page: str
    message: str


class RenderedPageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.document = PageDocument()

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        attributes = dict(attrs)
        element_id = attributes.get("id")
        if element_id:
            self.document.ids.append(element_id)
        if tag == "a" and attributes.get("href"):
            self.document.links.append(str(attributes["href"]))
        if tag in {"img", "script", "source"} and attributes.get("src"):
            self.document.assets.append(str(attributes["src"]))
        if tag == "link" and attributes.get("href"):
            relation = str(attributes.get("rel") or "").casefold()
            if any(
                token in relation
                for token in ("stylesheet", "icon", "manifest")
            ):
                self.document.assets.append(str(attributes["href"]))
        if tag == "main":
            self.document.main_count += 1
        if tag == "h1":
            self.document.h1_count += 1
        if (
            tag == "meta"
            and str(attributes.get("name") or "").casefold() == "viewport"
            and attributes.get("content")
        ):
            self.document.viewport_meta = True


def load_manifest(path: Path = DEFAULT_MANIFEST) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def route_to_file(site_dir: Path, route: str) -> Path:
    path = unquote(urlsplit(route).path)
    relative = path.lstrip("/")
    if not relative:
        return site_dir / "index.html"
    candidate = site_dir / relative
    if path.endswith("/"):
        return candidate / "index.html"
    if candidate.suffix:
        return candidate
    html_candidate = candidate.with_suffix(".html")
    if html_candidate.exists():
        return html_candidate
    return candidate / "index.html"


def parse_page(path: Path) -> tuple[str, PageDocument]:
    source = path.read_text(encoding="utf-8")
    parser = RenderedPageParser()
    parser.feed(source)
    parser.close()
    return source, parser.document


def public_route_for_file(site_dir: Path, path: Path) -> str:
    relative = path.relative_to(site_dir).as_posix()
    if relative == "index.html":
        return "/"
    if relative.endswith("/index.html"):
        return "/" + relative[: -len("index.html")]
    return "/" + relative


def resolve_public_target(
    site_dir: Path,
    current_route: str,
    reference: str,
) -> tuple[Path | None, str]:
    parsed = urlsplit(reference)
    if parsed.scheme.casefold() in SKIPPED_SCHEMES or parsed.netloc:
        return None, ""
    absolute = urlsplit(
        urljoin("https://bms.invalid" + current_route, reference)
    )
    return route_to_file(site_dir, absolute.path), unquote(absolute.fragment)


def audit_page(
    *,
    site_dir: Path,
    route: str,
    required_markers: list[str] | None = None,
    forbidden_markers: list[str] | None = None,
) -> list[Finding]:
    findings: list[Finding] = []
    page_path = route_to_file(site_dir, route)
    if not page_path.is_file():
        return [Finding(route, f"rendered page is missing: {page_path}")]

    source, document = parse_page(page_path)
    if document.main_count != 1:
        findings.append(
            Finding(route, f"expected one <main>; found {document.main_count}")
        )
    if document.h1_count < 1:
        findings.append(Finding(route, "page has no <h1>"))
    if not document.viewport_meta:
        findings.append(Finding(route, "viewport meta tag is missing"))

    duplicate_ids = sorted(
        item for item, count in Counter(document.ids).items() if count > 1
    )
    if duplicate_ids:
        findings.append(
            Finding(route, "duplicate IDs: " + ", ".join(duplicate_ids))
        )

    for marker in required_markers or []:
        if marker not in source:
            findings.append(Finding(route, f"required marker is missing: {marker}"))
    for marker in forbidden_markers or []:
        if marker in source:
            findings.append(Finding(route, f"forbidden marker is present: {marker}"))
    for marker in RAW_LEAK_MARKERS:
        if marker in source:
            findings.append(Finding(route, f"raw source marker leaked: {marker}"))

    available_ids = set(document.ids)
    for reference in document.links:
        if reference.startswith("#"):
            fragment = unquote(urlsplit(reference).fragment)
            if fragment and fragment not in available_ids:
                findings.append(
                    Finding(route, f"missing same-page anchor target: {reference}")
                )
            continue
        target, fragment = resolve_public_target(
            site_dir,
            route,
            reference,
        )
        if target is None:
            continue
        if target.suffix.casefold() == ".qmd":
            findings.append(Finding(route, f"source link leaked: {reference}"))
            continue
        if not target.exists():
            findings.append(Finding(route, f"broken internal link: {reference}"))
            continue
        if fragment and target.suffix.casefold() == ".html":
            _target_source, target_document = parse_page(target)
            if fragment not in set(target_document.ids):
                findings.append(
                    Finding(
                        route,
                        f"missing target fragment: {reference}",
                    )
                )

    for reference in document.assets:
        target, _fragment = resolve_public_target(
            site_dir,
            route,
            reference,
        )
        if target is not None and not target.exists():
            findings.append(Finding(route, f"missing local asset: {reference}"))
    return findings


def rendered_pages(site_dir: Path) -> list[Path]:
    return sorted(
        path
        for path in site_dir.rglob("*.html")
        if "site_libs" not in path.relative_to(site_dir).parts
    )


def audit_site(
    site_dir: Path,
    manifest: dict[str, object],
    *,
    all_pages: bool,
) -> tuple[list[Finding], int]:
    findings: list[Finding] = []
    checked_routes: set[str] = set()
    pages = manifest.get("pages")
    if not isinstance(pages, list):
        raise ValueError("manifest pages must be a list")

    for page in pages:
        if not isinstance(page, dict):
            raise ValueError("each manifest page must be an object")
        route = str(page["route"])
        checked_routes.add(route)
        findings.extend(
            audit_page(
                site_dir=site_dir,
                route=route,
                required_markers=[
                    str(item) for item in page.get("required_markers", [])
                ],
                forbidden_markers=[
                    str(item) for item in page.get("forbidden_markers", [])
                ],
            )
        )

    if all_pages:
        for page_path in rendered_pages(site_dir):
            route = public_route_for_file(site_dir, page_path)
            if route in checked_routes:
                continue
            findings.extend(audit_page(site_dir=site_dir, route=route))
            checked_routes.add(route)
    return findings, len(checked_routes)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--site-dir",
        type=Path,
        default=DEFAULT_SITE_DIR,
        help="Rendered site directory (default: site/_site).",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
        help="UI release manifest JSON.",
    )
    parser.add_argument(
        "--representative-only",
        action="store_true",
        help="Skip the full rendered HTML sweep.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    site_dir = args.site_dir.resolve()
    if not site_dir.is_dir():
        print(f"ERROR: rendered site directory is missing: {site_dir}", file=sys.stderr)
        return 2
    manifest = load_manifest(args.manifest)
    findings, checked = audit_site(
        site_dir,
        manifest,
        all_pages=not args.representative_only,
    )
    if findings:
        print(f"Rendered UI audit failed: pages={checked}, findings={len(findings)}")
        for finding in findings:
            print(f"- {finding.page}: {finding.message}")
        return 1
    print(f"Rendered UI audit passed: pages={checked}, findings=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
