#!/usr/bin/env python3
"""Build inspectable lookup, fragment, and offline preview artifacts for a review subset."""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import unicodedata
from pathlib import Path

try:
    from scripts import learn_glossary
except ModuleNotFoundError:  # Direct execution sets sys.path to scripts/.
    import learn_glossary  # type: ignore[no-redef]


REVIEW_TERMS = {"ABT", "Ace", "Active Builder"}
INLINE_LINK = re.compile(
    r'<a href="/learn/glossary/#(?P<slug>[^"]+)" '
    r'data-bms-definition-link="(?P=slug)">(?P<text>[^<]+)</a>'
)

ValidationError = learn_glossary.ValidationError


def validate_review_data(
    data: object,
    reference_entries: list[dict[str, object]],
) -> list[dict[str, object]]:
    if not isinstance(data, dict):
        raise ValidationError("Review artifact input must be a JSON object")
    raw_entries = data.get("entries")
    if not isinstance(raw_entries, list):
        raise ValidationError("Review artifact input must contain an entries list")
    alias_count = sum(
        len(entry.get("aliases", []))
        for entry in raw_entries
        if isinstance(entry, dict)
    )
    entries = learn_glossary.validate_public_data(
        data,
        expected_canonical_entries=3,
        expected_alias_entries=alias_count,
        reference_entries=reference_entries,
    )
    terms = {str(entry["term"]) for entry in entries}
    if terms != REVIEW_TERMS:
        raise ValidationError(
            "Artifact export requires exactly Ace, ABT, and Active Builder; "
            f"found {sorted(terms)}"
        )
    return entries


def normalize_lookup_value(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).casefold()
    normalized = "".join(
        character
        for character in normalized
        if not unicodedata.combining(character)
    )
    return " ".join(re.sub(r"[^a-z0-9]+", " ", normalized).split())


def referenced_target_slugs(entries: list[dict[str, object]]) -> set[str]:
    target_slugs: set[str] = set()
    for entry in entries:
        for link in entry.get("definition_links", []):
            if isinstance(link, dict):
                target_slugs.add(str(link["slug"]))
        for related in entry.get("related_terms", []):
            if isinstance(related, dict) and related.get("slug"):
                target_slugs.add(str(related["slug"]))
    return target_slugs


def canonical_target_entries(
    entries: list[dict[str, object]],
    reference_entries: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Generate canonical lookup records for targets outside the review subset."""
    by_slug = {
        str(entry["slug"]): entry
        for entry in (*reference_entries, *entries)
    }
    review_slugs = {str(entry["slug"]) for entry in entries}
    targets: list[dict[str, object]] = []
    for slug in sorted(referenced_target_slugs(entries) - review_slugs):
        target = by_slug.get(slug)
        if target is None:
            raise ValidationError(f"Missing preview target for canonical slug: {slug}")
        short_definition = target.get("short_definition")
        if short_definition is None:
            # JSON v1.0 legacy entries have only one canonical definition.
            # Generate the richer compatibility field on the canonical record.
            short_definition = target.get("definition")
        if not isinstance(short_definition, str) or not short_definition.strip():
            raise ValidationError(f"Preview target {slug} has no definition")
        aliases = target.get("aliases", [])
        if not isinstance(aliases, list):
            raise ValidationError(f"Preview target {slug} aliases must be a list")
        targets.append({
            "aliases": aliases,
            "short_definition": short_definition.strip(),
            "slug": slug,
            "term": str(target["term"]),
        })
    return targets


def category_index(entries: list[dict[str, object]]) -> dict[str, list[str]]:
    index: dict[str, list[str]] = {}
    for entry in entries:
        slug = str(entry["slug"])
        for category in learn_glossary.glossary_categories(entry, f"entry {slug}"):
            index.setdefault(category, []).append(slug)
    return index


def build_preview_lookup(
    entries: list[dict[str, object]],
    reference_entries: list[dict[str, object]],
) -> dict[str, object]:
    lookup = json.loads(learn_glossary.build_lookup_data(entries, {}))
    lookup["canonical_targets"] = canonical_target_entries(
        entries,
        reference_entries,
    )
    lookup["category_index"] = category_index(entries)
    return lookup


def resolve_lookup_entry(
    lookup: dict[str, object],
    value: str,
) -> dict[str, object] | None:
    records = [
        *lookup.get("entries", []),  # type: ignore[misc]
        *lookup.get("canonical_targets", []),  # type: ignore[misc]
    ]
    normalized = normalize_lookup_value(value)
    matches: list[dict[str, object]] = []
    for record in records:
        if not isinstance(record, dict):
            continue
        names = [str(record["term"])] + [
            str(alias["term"]) if isinstance(alias, dict) else str(alias)
            for alias in record.get("aliases", [])
        ]
        if any(normalize_lookup_value(name) == normalized for name in names):
            matches.append(record)
    if len(matches) > 1:
        raise ValidationError(f"Ambiguous generated lookup value: {value!r}")
    return matches[0] if matches else None


def preview_fragment(
    entries_html: str,
) -> str:
    def replace_inline_link(match: re.Match[str]) -> str:
        slug = match.group("slug")
        visible = html.unescape(match.group("text"))
        return (
            f'<a class="bms-inline-term" href="#{html.escape(slug, quote=True)}" '
            f'data-bms-definition-link="{html.escape(slug, quote=True)}" '
            'aria-describedby="bms-inline-tooltip">'
            f"{html.escape(visible)}</a>"
        )

    fragment = INLINE_LINK.sub(replace_inline_link, entries_html)
    fragment = fragment.replace('href="/learn/glossary/#', 'href="#')
    fragment = fragment.replace(
        '<button type="button" data-bms-card-category=',
        '<button type="button" aria-pressed="false" data-bms-card-category=',
    )
    fragment = fragment.replace(
        '<details class="bms-glossary-entry"',
        '<details open class="bms-glossary-entry"',
    )
    return fragment


def target_registry_html(lookup: dict[str, object]) -> str:
    lines = [
        '<section class="bms-target-registry" aria-label="Inline-link target anchors">',
        "<h2>Inline-link target anchors</h2>",
        (
            "<p>These local anchors let the offline preview demonstrate the same "
            "fragment navigation used by the website.</p>"
        ),
    ]
    for target in lookup["canonical_targets"]:  # type: ignore[index]
        slug = str(target["slug"])  # type: ignore[index]
        term = str(target["term"])  # type: ignore[index]
        lines.append(
            f'<span id="{html.escape(slug, quote=True)}" '
            f'class="bms-target-summary" tabindex="-1" '
            f'aria-label="{html.escape(term, quote=True)}"></span>'
        )
    lines.append("</section>")
    return "\n".join(lines)


def build_preview_html(
    entries: list[dict[str, object]],
    entries_html: str,
    lookup: dict[str, object],
) -> str:
    fragment = preview_fragment(entries_html)
    registry = target_registry_html(lookup)
    embedded_lookup = learn_glossary.json_text(lookup).replace("<", "\\u003c")
    expected_count = len(entries)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Glossary iteration 02R offline preview</title>
<style>
:root {{
  color-scheme: light;
  --ink: #17212b;
  --muted: #5a6772;
  --paper: #f5f1e8;
  --card: #fffdf8;
  --line: #cfc6b5;
  --accent: #8b2f26;
  --accent-soft: #f6dfd9;
  --focus: #155eef;
}}
* {{ box-sizing: border-box; }}
body {{
  margin: 0;
  color: var(--ink);
  background: var(--paper);
  font: 16px/1.55 system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}}
main {{ width: min(72rem, calc(100% - 2rem)); margin: 0 auto; padding: 2.5rem 0 5rem; }}
h1, h2, h3, h4 {{ line-height: 1.2; }}
.bms-intro {{ max-width: 48rem; color: var(--muted); }}
.bms-search {{
  position: sticky;
  top: 0;
  z-index: 20;
  display: grid;
  gap: .5rem;
  margin: 1.5rem 0;
  padding: 1rem;
  border: 1px solid var(--line);
  border-radius: .75rem;
  background: color-mix(in srgb, var(--paper) 94%, transparent);
  backdrop-filter: blur(8px);
}}
.bms-search label {{ font-weight: 700; }}
.bms-search input {{
  width: 100%;
  padding: .75rem .9rem;
  border: 2px solid var(--line);
  border-radius: .5rem;
  font: inherit;
}}
.bms-search input:focus {{ outline: 3px solid color-mix(in srgb, var(--focus) 30%, transparent); border-color: var(--focus); }}
.bms-search-status {{ margin: 0; color: var(--muted); }}
.bms-glossary-letter-group {{ margin: 1.5rem 0; }}
.bms-glossary-entry {{
  margin: .8rem 0;
  border: 1px solid var(--line);
  border-radius: .75rem;
  background: var(--card);
  box-shadow: 0 8px 24px rgb(40 32 21 / 7%);
}}
.bms-glossary-entry > summary {{ cursor: pointer; padding: 1rem 1.15rem; font-size: 1.15rem; font-weight: 800; }}
.bms-glossary-entry-body {{ padding: 0 1.15rem 1.15rem; }}
.bms-glossary-short-definition {{ font-size: 1.08rem; font-weight: 650; }}
.bms-glossary-definition {{ max-width: 68ch; }}
.bms-glossary-category button {{
  margin: .15rem .25rem .15rem 0;
  padding: .25rem .55rem;
  border: 2px solid transparent;
  border-radius: 99rem;
  color: #5e211a;
  background: var(--accent-soft);
  cursor: pointer;
}}
.bms-glossary-category button:hover,
.bms-glossary-category button:focus-visible {{
  border-color: var(--accent);
  outline: none;
}}
.bms-glossary-category button[aria-pressed="true"] {{
  border-color: #5e211a;
  color: white;
  background: var(--accent);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--accent) 24%, transparent);
}}
.bms-category-filter-status {{
  display: flex;
  align-items: center;
  gap: .75rem;
  min-height: 2rem;
}}
.bms-category-filter-status button {{
  padding: .3rem .65rem;
  border: 1px solid var(--line);
  border-radius: .4rem;
  background: var(--card);
  cursor: pointer;
}}
.bms-glossary-related-terms {{
  margin-top: 1.25rem;
  padding-top: .75rem;
  border-top: 1px solid var(--line);
}}
.bms-inline-term {{
  position: relative;
  color: var(--accent);
  font-weight: 750;
  text-decoration: underline 2px dotted;
  text-underline-offset: .2em;
}}
.bms-inline-term:focus {{ outline: 3px solid var(--focus); outline-offset: 3px; border-radius: .15rem; }}
.bms-inline-tooltip {{
  position: fixed;
  left: 1rem;
  top: 1rem;
  z-index: 50;
  width: min(24rem, 78vw);
  padding: .7rem .8rem;
  border-radius: .55rem;
  color: white;
  background: #17212b;
  box-shadow: 0 8px 28px rgb(0 0 0 / 25%);
  pointer-events: none;
}}
.bms-inline-tooltip strong, .bms-inline-tooltip span {{ display: block; }}
.bms-inline-tooltip strong {{ margin-bottom: .25rem; color: #ffd8cf; }}
.bms-target-registry {{ margin-top: 3rem; padding-top: 1.5rem; border-top: 3px double var(--line); }}
.bms-target-summary {{ display: block; height: 1px; scroll-margin-top: 8rem; }}
.bms-target-summary:target {{ outline: 4px solid #fff1ad; }}
[hidden] {{ display: none !important; }}
</style>
</head>
<body>
<main>
<header>
  <p><strong>Iteration 02R artifact</strong></p>
  <h1>Rich-field glossary preview</h1>
  <p class="bms-intro">A self-contained, offline compatibility preview for Ace,
  ABT, and Active Builder. Inline summaries resolve the canonical target slug
  through the generated lookup and read that canonical record's
  <code>short_definition</code>.</p>
</header>
<section class="bms-search" aria-label="Glossary search">
  <label for="bms-search-input">Search canonical terms or AKA values</label>
  <input id="bms-search-input" type="search"
    placeholder="Try ABT or American Backgammon Tour" autocomplete="off">
  <p id="bms-search-status" class="bms-search-status" role="status"
    aria-live="polite">{expected_count} results</p>
  <div class="bms-category-filter-status">
    <span id="bms-category-status">All categories</span>
    <button id="bms-clear-category" type="button" hidden>
      Clear category filter
    </button>
  </div>
</section>
<div id="bms-entry-list">
{fragment}
</div>
{registry}
</main>
<div id="bms-inline-tooltip" class="bms-inline-tooltip" role="tooltip" hidden>
  <strong id="bms-inline-tooltip-term"></strong>
  <span id="bms-inline-tooltip-summary"></span>
</div>
<script id="bms-preview-lookup" type="application/json">
{embedded_lookup}</script>
<script>
(() => {{
  "use strict";
  const input = document.getElementById("bms-search-input");
  const status = document.getElementById("bms-search-status");
  const categoryStatus = document.getElementById("bms-category-status");
  const clearCategory = document.getElementById("bms-clear-category");
  const tooltip = document.getElementById("bms-inline-tooltip");
  const tooltipTerm = document.getElementById("bms-inline-tooltip-term");
  const tooltipSummary = document.getElementById("bms-inline-tooltip-summary");
  const lookup = JSON.parse(
    document.getElementById("bms-preview-lookup").textContent
  );
  const entries = [...document.querySelectorAll("[data-bms-glossary-entry]")];
  const chips = [...document.querySelectorAll("[data-bms-card-category]")];
  const normalize = value => value
    .normalize("NFKD")
    .replace(/[\\u0300-\\u036f]/g, "")
    .toLocaleLowerCase("en")
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
  const canonicalRecords = [...lookup.entries, ...lookup.canonical_targets];
  const bySlug = new Map(canonicalRecords.map(record => [record.slug, record]));
  const byLookupValue = new Map();
  for (const record of canonicalRecords) {{
    for (const value of [
      record.term,
      ...(record.aliases || []).map(
        alias => typeof alias === "string" ? alias : alias.term
      )
    ]) {{
      byLookupValue.set(normalize(value), record);
    }}
  }}
  const showEntries = (matchingSlugs, expand) => {{
    const matches = new Set(matchingSlugs);
    let visible = 0;
    for (const entry of entries) {{
      const matchesFilter = matches.has(entry.dataset.bmsSlug);
      entry.hidden = !matchesFilter;
      if (matchesFilter) {{
        visible += 1;
        if (expand) entry.open = true;
      }}
    }}
    status.textContent = `${{visible}} ${{visible === 1 ? "result" : "results"}}`;
  }};
  const resetCategorySelection = () => {{
    for (const chip of chips) chip.setAttribute("aria-pressed", "false");
    categoryStatus.textContent = "All categories";
    clearCategory.hidden = true;
  }};
  const updateSearch = () => {{
    resetCategorySelection();
    const query = normalize(input.value);
    const exactCanonical = byLookupValue.get(query);
    const matchingSlugs = entries
      .filter(entry => {{
        if (!query) return true;
        if (exactCanonical) return entry.dataset.bmsSlug === exactCanonical.slug;
        const values = JSON.parse(entry.dataset.bmsSearch || "[]");
        return values.some(value => normalize(value).includes(query));
      }})
      .map(entry => entry.dataset.bmsSlug);
    showEntries(matchingSlugs, Boolean(query));
  }};
  const applyCategory = category => {{
    input.value = "";
    const matchingSlugs = lookup.category_index[category] || [];
    for (const chip of chips) {{
      chip.setAttribute(
        "aria-pressed",
        String(chip.dataset.bmsCardCategory === category)
      );
    }}
    categoryStatus.textContent = `Category: ${{category}}`;
    clearCategory.hidden = false;
    showEntries(matchingSlugs, true);
  }};
  const showInlineSummary = link => {{
    const target = bySlug.get(link.dataset.bmsDefinitionLink);
    if (!target || !target.short_definition) {{
      throw new Error(
        `Missing canonical short_definition for ${{link.dataset.bmsDefinitionLink}}`
      );
    }}
    tooltipTerm.textContent = target.term;
    tooltipSummary.textContent = target.short_definition;
    const bounds = link.getBoundingClientRect();
    tooltip.style.left = `${{Math.max(12, Math.min(bounds.left, window.innerWidth - 400))}}px`;
    tooltip.style.top = `${{Math.max(12, bounds.top - 120)}}px`;
    tooltip.hidden = false;
  }};
  const hideInlineSummary = () => {{
    tooltip.hidden = true;
    tooltipTerm.textContent = "";
    tooltipSummary.textContent = "";
  }};
  document.addEventListener("click", event => {{
    const chip = event.target.closest("[data-bms-card-category]");
    if (chip) applyCategory(chip.dataset.bmsCardCategory);
  }});
  document.addEventListener("pointerover", event => {{
    const link = event.target.closest("[data-bms-definition-link]");
    if (link) showInlineSummary(link);
  }});
  document.addEventListener("pointerout", event => {{
    if (event.target.closest("[data-bms-definition-link]")) hideInlineSummary();
  }});
  document.addEventListener("focusin", event => {{
    const link = event.target.closest("[data-bms-definition-link]");
    if (link) showInlineSummary(link);
  }});
  document.addEventListener("focusout", event => {{
    if (event.target.closest("[data-bms-definition-link]")) hideInlineSummary();
  }});
  clearCategory.addEventListener("click", () => {{
    input.value = "";
    resetCategorySelection();
    showEntries(entries.map(entry => entry.dataset.bmsSlug), false);
  }});
  input.addEventListener("input", updateSearch);
  resetCategorySelection();
  updateSearch();
}})();
</script>
</body>
</html>
"""


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")
    if path.stat().st_size == 0:
        raise ValidationError(f"Artifact output is empty: {path}")


def generate_artifacts(
    input_path: Path,
    lookup_output: Path,
    entries_output: Path,
    preview_output: Path,
) -> dict[str, int]:
    output_paths = (lookup_output, entries_output, preview_output)
    if len({path.resolve() for path in output_paths}) != len(output_paths):
        raise ValidationError("Artifact output paths must be distinct")
    if any(
        path.resolve() == learn_glossary.PUBLIC_DATA_PATH.resolve()
        for path in output_paths
    ):
        raise ValidationError("Refusing to overwrite the production glossary JSON")

    production = learn_glossary.read_json(learn_glossary.PUBLIC_DATA_PATH)
    reference_entries = learn_glossary.validate_public_data(production)
    data = learn_glossary.read_json(input_path)
    entries = validate_review_data(data, reference_entries)

    lookup = build_preview_lookup(entries, reference_entries)
    lookup_entries = lookup.get("entries")
    if not isinstance(lookup_entries, list) or len(lookup_entries) != 3:
        raise ValidationError("Lookup builder did not emit the three review entries")
    required_lookup_fields = {
        "aliases",
        "categories",
        "definition",
        "definition_links",
        "learning_tracks",
        "related_terms",
        "short_definition",
        "slug",
        "term",
    }
    for entry in lookup_entries:
        missing = required_lookup_fields - set(entry)
        if missing:
            raise ValidationError(
                f"Lookup entry {entry.get('term')} lost fields: {sorted(missing)}"
            )
    canonical_targets = lookup.get("canonical_targets")
    if not isinstance(canonical_targets, list) or not canonical_targets:
        raise ValidationError("Preview lookup has no canonical target records")
    for target in canonical_targets:
        if (
            not isinstance(target, dict)
            or not isinstance(target.get("short_definition"), str)
            or not str(target["short_definition"]).strip()
        ):
            raise ValidationError(
                "Every canonical preview target requires a generated "
                "short_definition"
            )
    for entry in entries:
        for link in entry.get("definition_links", []):
            if not isinstance(link, dict):
                continue
            target = resolve_lookup_entry(lookup, str(link["slug"]))
            if target is None:
                target = next(
                    (
                        record
                        for record in [*lookup_entries, *canonical_targets]
                        if isinstance(record, dict)
                        and record.get("slug") == link["slug"]
                    ),
                    None,
                )
            if target is None or not target.get("short_definition"):
                raise ValidationError(
                    f"Inline target {link['slug']} has no canonical "
                    "short_definition in generated lookup"
                )

    entries_html = learn_glossary.build_entries_html(entries, {}, {})
    if entries_html.count('data-bms-glossary-entry') != 3:
        raise ValidationError("HTML builder did not emit the three review entries")
    if entries_html.count("<h4>See also</h4>") != 3:
        raise ValidationError("HTML builder did not emit separate See also sections")

    preview_html = build_preview_html(entries, entries_html, lookup)
    if "<style>" not in preview_html or "<script>" not in preview_html:
        raise ValidationError("Standalone preview must embed CSS and JavaScript")

    write_text(lookup_output, learn_glossary.json_text(lookup))
    write_text(entries_output, entries_html + "\n")
    write_text(preview_output, preview_html)
    return {
        "entries": len(entries),
        "inline_links": sum(
            len(entry.get("definition_links", [])) for entry in entries
        ),
        "lookup_bytes": lookup_output.stat().st_size,
        "entries_html_bytes": entries_output.stat().st_size,
        "preview_html_bytes": preview_output.stat().st_size,
        "canonical_targets": len(canonical_targets),
        "categories": len(lookup["category_index"]),  # type: ignore[arg-type]
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-json", required=True, type=Path)
    parser.add_argument("--lookup-output", required=True, type=Path)
    parser.add_argument("--entries-output", required=True, type=Path)
    parser.add_argument("--preview-output", required=True, type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    try:
        result = generate_artifacts(
            args.input_json.resolve(),
            args.lookup_output.resolve(),
            args.entries_output.resolve(),
            args.preview_output.resolve(),
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ValidationError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(
        "Iteration 02R compatibility artifacts written: "
        + json.dumps(result, sort_keys=True)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
