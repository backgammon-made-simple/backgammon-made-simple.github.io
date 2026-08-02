#!/usr/bin/env python3
"""Build a deterministic, evidence-only static bloat and archive inventory."""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Iterable


SCHEMA_VERSION = 1
EXCLUDED_PARTS = {
    ".git",
    ".pytest_cache",
    ".quarto",
    ".r-library",
    ".venv",
    "__pycache__",
    "node_modules",
    "task-work",
}
TEXT_EXTENSIONS = {
    ".css",
    ".csv",
    ".ejs",
    ".html",
    ".js",
    ".json",
    ".md",
    ".mjs",
    ".ps1",
    ".py",
    ".qmd",
    ".r",
    ".scss",
    ".sh",
    ".svg",
    ".toml",
    ".tsv",
    ".txt",
    ".yaml",
    ".yml",
}
MODULE_EXTENSIONS = {".js", ".mjs", ".ps1", ".py", ".r", ".sh"}
ASSET_EXTENSIONS = {
    ".avif",
    ".css",
    ".csv",
    ".eot",
    ".gif",
    ".ico",
    ".jpeg",
    ".jpg",
    ".js",
    ".json",
    ".mjs",
    ".otf",
    ".png",
    ".svg",
    ".tsv",
    ".ttf",
    ".webp",
    ".woff",
    ".woff2",
    ".yaml",
    ".yml",
}
GENERATED_SOURCE_HTML_ALLOWLIST = {
    "site/glossary/_entries.html",
    "site/includes/analyzer-form.html",
    "site/includes/bms-scripts.html",
    "site/includes/bot-arena-banner.html",
    "site/includes/report-problem.html",
    "site/includes/site-head.html",
    "site/includes/subscribe.html",
    "site/learn/_lesson-catalogue.html",
    "site/learn/cube/_lesson-index.html",
    "site/learn/opening-play/_lesson-index.html",
    "site/learn/start-here/_lesson-index.html",
}
REFERENCE_CATEGORIES = (
    "rendered",
    "source",
    "manifest",
    "script",
    "test",
    "documentation",
)


def relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def included(path: Path, root: Path) -> bool:
    parts = path.relative_to(root).parts
    return not any(part in EXCLUDED_PARTS for part in parts)


def files_under(root: Path) -> list[Path]:
    return sorted(
        (path for path in root.rglob("*") if path.is_file() and included(path, root)),
        key=lambda path: relative(path, root),
    )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def text_of(path: Path) -> str | None:
    if path.suffix.lower() not in TEXT_EXTENSIONS:
        return None
    try:
        return path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return None


def file_record(path: Path, root: Path) -> dict[str, object]:
    stat = path.stat()
    text = text_of(path)
    return {
        "path": relative(path, root),
        "bytes": stat.st_size,
        "lines": len(text.splitlines()) if text is not None else None,
        "sha256": sha256(path),
    }


def largest_files(paths: Iterable[Path], root: Path, limit: int = 30) -> list[dict[str, object]]:
    records = [file_record(path, root) for path in paths]
    return sorted(records, key=lambda item: (-int(item["bytes"]), str(item["path"])))[:limit]


def duplicate_groups(paths: Iterable[Path], root: Path) -> list[dict[str, object]]:
    groups: dict[tuple[str, int], list[str]] = defaultdict(list)
    for path in paths:
        size = path.stat().st_size
        if size:
            groups[(sha256(path), size)].append(relative(path, root))
    return [
        {"sha256": digest, "bytes": size, "paths": sorted(members)}
        for (digest, size), members in sorted(groups.items())
        if len(members) > 1
    ]


def repeated_implementations(paths: Iterable[Path], root: Path) -> list[dict[str, object]]:
    groups: dict[tuple[str, str], list[Path]] = defaultdict(list)
    for path in paths:
        suffix = path.suffix.lower()
        if suffix in {".css", ".js", ".json", ".mjs"}:
            groups[(path.name.lower(), suffix)].append(path)
    results = []
    for (name, kind), members in sorted(groups.items()):
        if len(members) < 2:
            continue
        hashes = sorted({sha256(path) for path in members})
        results.append(
            {
                "name": name,
                "kind": kind.lstrip("."),
                "exact_content_match": len(hashes) == 1,
                "distinct_hashes": len(hashes),
                "paths": sorted(relative(path, root) for path in members),
            }
        )
    return results


def module_review_candidates(paths: Iterable[Path], root: Path) -> list[dict[str, object]]:
    branch_pattern = re.compile(
        r"\b(?:if|elif|else|for|while|case|catch|except|switch|try)\b|&&|\|\|"
    )
    candidates = []
    for path in paths:
        if path.suffix.lower() not in MODULE_EXTENSIONS:
            continue
        text = text_of(path)
        if text is None:
            continue
        lines = len(text.splitlines())
        branch_tokens = len(branch_pattern.findall(text))
        if lines >= 400 or branch_tokens >= 50:
            candidates.append(
                {
                    "path": relative(path, root),
                    "lines": lines,
                    "approximate_branch_tokens": branch_tokens,
                    "evidence_only": True,
                }
            )
    return sorted(candidates, key=lambda item: (-int(item["lines"]), str(item["path"])))


def source_category(path: Path, root: Path, site_output: Path) -> str | None:
    rel = relative(path, root)
    if path.is_relative_to(site_output):
        return "rendered"
    if rel.startswith("scripts/"):
        return "script"
    if rel.startswith("tests/") or "/tests/" in f"/{rel}/":
        return "test"
    if path.suffix.lower() in {".md", ".txt"} or "docs" in path.parts:
        return "documentation"
    if path.name.lower().endswith(("manifest.json", "manifest.yml", "manifest.yaml")) or path.suffix.lower() in {".toml", ".yaml", ".yml"}:
        return "manifest"
    if rel.startswith("site/"):
        return "source"
    return None


def reference_corpus(paths: Iterable[Path], root: Path, site_output: Path) -> dict[str, list[tuple[str, str]]]:
    corpus = {category: [] for category in REFERENCE_CATEGORIES}
    for path in paths:
        category = source_category(path, root, site_output)
        if not category:
            continue
        text = text_of(path)
        if text is not None:
            corpus[category].append((relative(path, root), text))
    return corpus


def reference_counts(asset: Path, root: Path, corpus: dict[str, list[tuple[str, str]]]) -> dict[str, int]:
    rel = relative(asset, root)
    site_relative = asset.relative_to(root / "site").as_posix()
    route_token = f"/{site_relative}"
    tokens = {rel, site_relative, route_token, asset.name}
    counts = {}
    for category in REFERENCE_CATEGORIES:
        count = 0
        for source_path, text in corpus[category]:
            if source_path == rel:
                continue
            wildcard_match = False
            if category == "manifest":
                patterns = re.findall(r"[A-Za-z0-9_.\-/]*\*+[A-Za-z0-9_.*\-/]*", text)
                wildcard_match = any(
                    fnmatch.fnmatch(site_relative, pattern.lstrip("/"))
                    for pattern in patterns
                )
            if wildcard_match or any(token in text for token in tokens):
                count += 1
        counts[category] = count
    return counts


def asset_inventory(paths: Iterable[Path], root: Path, site_output: Path) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    all_paths = list(paths)
    corpus = reference_corpus(all_paths, root, site_output)
    assets = [
        path
        for path in all_paths
        if path.is_relative_to(root / "site")
        and not path.is_relative_to(site_output)
        and path.suffix.lower() in ASSET_EXTENSIONS
        and not path.name.startswith("_")
    ]
    records = []
    unreferenced = []
    for asset in assets:
        counts = reference_counts(asset, root, corpus)
        rel = relative(asset, root)
        status = "known" if sum(counts.values()) else "unresolved"
        if status == "unresolved" and re.search(
            r"(?:^|[-_/])(archive|backup|copy|legacy|old|temp|tmp)(?:[-_./]|$)", rel, re.I
        ):
            status = "archive-candidate"
        record = {
            "path": rel,
            "bytes": asset.stat().st_size,
            "purpose_status": status,
            "reference_counts": counts,
            "evidence_only": True,
        }
        records.append(record)
        if sum(counts.values()) == 0:
            unreferenced.append(record)
    return records, unreferenced


def generated_page_inventory(paths: Iterable[Path], root: Path, site_output: Path) -> dict[str, list[str]]:
    direct_sources = {
        relative(path, root)[: -len(path.suffix)]
        for path in paths
        if path.is_relative_to(root / "site")
        and not path.is_relative_to(site_output)
        and path.suffix.lower() in {".qmd", ".md"}
    }
    rendered_without_direct_source = []
    for path in paths:
        if path.is_relative_to(site_output) and path.suffix.lower() == ".html":
            output_rel = path.relative_to(site_output).as_posix()
            stem = output_rel[:-5]
            source_stem = f"site/{stem}"
            index_source_stem = f"site/{stem[:-6]}/index" if stem.endswith("/index") else None
            if source_stem not in direct_sources and index_source_stem not in direct_sources:
                rendered_without_direct_source.append(relative(path, root))
    source_adjacent_html = sorted(
        relative(path, root)
        for path in paths
        if path.is_relative_to(root / "site")
        and not path.is_relative_to(site_output)
        and path.suffix.lower() == ".html"
        and relative(path, root) not in GENERATED_SOURCE_HTML_ALLOWLIST
    )
    return {
        "rendered_html_without_direct_source": sorted(rendered_without_direct_source),
        "unexpected_source_adjacent_html": source_adjacent_html,
    }


def findings_for(
    duplicates: list[dict[str, object]],
    repeated: list[dict[str, object]],
    modules: list[dict[str, object]],
    pages: dict[str, list[str]],
    unreferenced: list[dict[str, object]],
) -> list[dict[str, object]]:
    findings = []
    for group in duplicates:
        if len(group["paths"]) < 2:
            continue
        normalized_paths = {
            f"site/{path.removeprefix('site/_site/')}"
            if path.startswith("site/_site/")
            else path
            for path in group["paths"]
        }
        if len(normalized_paths) == 1:
            continue
        findings.append(
            {
                "category": "simplification-opportunity",
                "severity": "minor",
                "route_or_file": group["paths"][0],
                "viewport": None,
                "evidence": f"Exact SHA-256 duplicate ({group['bytes']} bytes): {', '.join(group['paths'])}",
                "reproduction": "Run the canonical static inventory and inspect duplicate_files_by_sha256.",
                "safe_for_automated_remediation": False,
                "needs_review": True,
            }
        )
    for group in repeated:
        if group["exact_content_match"]:
            continue
        findings.append(
            {
                "category": "simplification-opportunity",
                "severity": "minor",
                "route_or_file": group["paths"][0],
                "viewport": None,
                "evidence": f"Repeated {group['kind']} basename with {group['distinct_hashes']} distinct hashes: {', '.join(group['paths'])}",
                "reproduction": "Run the canonical static inventory and inspect repeated_implementations.",
                "safe_for_automated_remediation": False,
                "needs_review": True,
            }
        )
    for module in modules:
        findings.append(
            {
                "category": "needs-review",
                "severity": "minor",
                "route_or_file": module["path"],
                "viewport": None,
                "evidence": f"{module['lines']} lines and {module['approximate_branch_tokens']} approximate branch tokens.",
                "reproduction": "Run the canonical static inventory and inspect module_review_candidates.",
                "safe_for_automated_remediation": False,
                "needs_review": True,
            }
        )
    for path in pages["unexpected_source_adjacent_html"]:
        findings.append(
            {
                "category": "archive-candidate",
                "severity": "minor",
                "route_or_file": path,
                "viewport": None,
                "evidence": "Source-adjacent HTML is not in the known generated-partial allowlist.",
                "reproduction": "Run the canonical static inventory and inspect generated_pages.unexpected_source_adjacent_html.",
                "safe_for_automated_remediation": False,
                "needs_review": True,
            }
        )
    for asset in unreferenced:
        findings.append(
            {
                "category": "archive-candidate",
                "severity": "minor",
                "route_or_file": asset["path"],
                "viewport": None,
                "evidence": "No reference was discovered in rendered output, source, manifests, scripts, tests, or documentation; scanning is evidence, not proof.",
                "reproduction": "Run the canonical static inventory and inspect unreferenced_site_assets.",
                "safe_for_automated_remediation": False,
                "needs_review": True,
            }
        )
    return sorted(
        findings,
        key=lambda item: (str(item["category"]), str(item["route_or_file"]), str(item["evidence"])),
    )


def build_inventory(root: Path, site_output: Path) -> dict[str, object]:
    paths = files_under(root)
    source_paths = [path for path in paths if not path.is_relative_to(site_output)]
    rendered_paths = [path for path in paths if path.is_relative_to(site_output)]
    duplicates = duplicate_groups(paths, root)
    repeated = repeated_implementations(paths, root)
    modules = module_review_candidates(source_paths, root)
    assets, unreferenced = asset_inventory(paths, root, site_output)
    pages = generated_page_inventory(paths, root, site_output)
    findings = findings_for(duplicates, repeated, modules, pages, unreferenced)
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "evidence_contract": {
            "reference_scanning_is_proof": False,
            "files_moved_or_deleted": False,
            "hash_algorithm": "sha256",
            "largest_file_limit_per_scope": 30,
            "reference_categories": list(REFERENCE_CATEGORIES),
        },
        "counts": {
            "source_files": len(source_paths),
            "rendered_files": len(rendered_paths),
            "duplicate_groups": len(duplicates),
            "module_review_candidates": len(modules),
            "unreferenced_site_assets": len(unreferenced),
        },
        "largest_source_files": largest_files(source_paths, root),
        "largest_rendered_files": largest_files(rendered_paths, root),
        "duplicate_files_by_sha256": duplicates,
        "repeated_implementations": repeated,
        "module_review_candidates": modules,
        "generated_pages": pages,
        "site_asset_classifications": assets,
        "unreferenced_site_assets": unreferenced,
        "findings": findings,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument("--site-dir", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.repo_root.resolve()
    site_output = (args.site_dir or root / "site" / "_site").resolve()
    inventory = build_inventory(root, site_output)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(inventory, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(
        "Static inventory: "
        f"{inventory['counts']['source_files']} source files, "
        f"{inventory['counts']['rendered_files']} rendered files, "
        f"{len(inventory['findings'])} findings."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
