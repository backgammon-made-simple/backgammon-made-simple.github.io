#!/usr/bin/env python3
"""Parse the bounded glossary Markdown MVP and emit JSON v1.0 data."""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path

try:
    from scripts import learn_glossary
except ModuleNotFoundError:  # Direct execution sets sys.path to scripts/.
    import learn_glossary  # type: ignore[no-redef]


MVP_TERMS = ("Ace", "ABT", "Active Builder")
ENTRY_HEADING = re.compile(r"^# ([^\r\n]+)$")
SECTION_HEADING = re.compile(r"^## ([^\r\n]+)$")
SLUG_FIELD = re.compile(r"^\*\*Slug:\*\*\s+`([^`]+)`\s*$")
STATUS_FIELD = re.compile(r"^\*\*Status:\*\*(?:\s+.*)?$")
SLUG_VALUE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
INLINE_TERM = re.compile(
    r'^-\s+"([^"\r\n]+)"\s+->\s+`([a-z0-9]+(?:-[a-z0-9]+)*)`\s*$'
)
REQUIRED_SECTIONS = (
    "AKA",
    "Short definition",
    "Full definition",
    "Inline terms",
    "Related words",
    "Categories",
    "Learning tracks",
    "Generation notes",
)
NONE_MARKERS = {
    "None",
    "None selected yet.",
}

ValidationError = learn_glossary.ValidationError


@dataclass(frozen=True)
class ParsedEntry:
    term: str
    slug: str
    aliases: tuple[str, ...]
    short_definition: str
    full_definition: str
    inline_terms: tuple[tuple[str, str], ...]
    related_words: tuple[str, ...]
    categories: tuple[str, ...]
    learning_tracks: tuple[str, ...]


def normalize_line_endings(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def normalize_lookup(value: str) -> str:
    """Normalize names for collision checks across case, space, and punctuation."""
    normalized = unicodedata.normalize("NFKC", value).casefold()
    words: list[str] = []
    current: list[str] = []
    for character in normalized:
        if character.isalnum():
            current.append(character)
        elif current:
            words.append("".join(current))
            current = []
    if current:
        words.append("".join(current))
    return " ".join(words)


def alias_slug(value: str) -> str:
    ascii_value = (
        unicodedata.normalize("NFKD", value)
        .encode("ascii", "ignore")
        .decode("ascii")
        .casefold()
    )
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_value).strip("-")
    if not SLUG_VALUE.fullmatch(slug):
        raise ValidationError(f"Alias cannot form a valid lookup slug: {value!r}")
    return slug


def parse_list(
    content: str,
    *,
    section: str,
    allow_none: bool = True,
) -> list[str]:
    values: list[str] = []
    for raw_line in content.splitlines():
        if not raw_line.strip():
            continue
        if not raw_line.startswith("- "):
            raise ValidationError(
                f"{section} must contain only Markdown list items beginning '- '"
            )
        value = raw_line[2:].strip()
        if not value:
            raise ValidationError(f"{section} contains an empty list item")
        values.append(value)

    if not values:
        return []
    none_values = [value for value in values if value in NONE_MARKERS]
    if none_values:
        if not allow_none:
            raise ValidationError(f"{section} cannot use a None marker")
        if len(values) != 1:
            raise ValidationError(
                f"{section} cannot mix a None marker with populated values"
            )
        return []
    return values


def canonical_category(value: str) -> str:
    by_normalized = {
        category.casefold(): category
        for category in learn_glossary.GLOSSARY_CATEGORIES
    }
    normalized = " ".join(value.split()).casefold()
    category = by_normalized.get(normalized)
    if category is None:
        raise ValidationError(f"Invalid glossary category: {value!r}")
    return category


def validate_alias(value: str, term: str) -> str:
    if value != " ".join(value.split()):
        raise ValidationError(f"Alias under {term} has unstable whitespace: {value!r}")
    if (
        not normalize_lookup(value)
        or "`" in value
        or "->" in value
        or value.startswith(('"', "'"))
        or value.endswith(('"', "'"))
    ):
        raise ValidationError(f"Malformed alias or lookup value under {term}: {value!r}")
    alias_slug(value)
    return value


def parse_entry(term: str, lines: list[str]) -> ParsedEntry:
    if term != term.strip() or not normalize_lookup(term):
        raise ValidationError(f"Malformed canonical term heading: {term!r}")

    first_section = next(
        (index for index, line in enumerate(lines) if SECTION_HEADING.fullmatch(line)),
        len(lines),
    )
    preamble = lines[:first_section]
    slug: str | None = None
    for line in preamble:
        stripped = line.strip()
        if (
            not stripped
            or stripped == "---"
            or stripped.startswith("<!--")
            or STATUS_FIELD.fullmatch(stripped)
        ):
            continue
        slug_match = SLUG_FIELD.fullmatch(stripped)
        if slug_match:
            if slug is not None:
                raise ValidationError(f"{term} contains more than one Slug field")
            slug = slug_match.group(1)
            continue
        raise ValidationError(f"Unexpected entry metadata under {term}: {line!r}")

    if slug is None:
        raise ValidationError(f"{term} requires a Slug field")
    if not SLUG_VALUE.fullmatch(slug):
        raise ValidationError(f"{term} has a malformed canonical slug: {slug!r}")

    sections: dict[str, list[str]] = {}
    current_section: str | None = None
    for line in lines[first_section:]:
        section_match = SECTION_HEADING.fullmatch(line)
        if section_match:
            current_section = section_match.group(1).strip()
            if current_section in sections:
                raise ValidationError(
                    f"{term} repeats the {current_section!r} section"
                )
            sections[current_section] = []
            continue
        if current_section is None:
            if line.strip() and line.strip() != "---":
                raise ValidationError(f"Unexpected content before sections under {term}")
            continue
        sections[current_section].append(line)

    missing = [section for section in REQUIRED_SECTIONS if section not in sections]
    if missing:
        if "Categories" in missing:
            raise ValidationError(f"{term} is missing the Categories section")
        raise ValidationError(f"{term} is missing required sections: {missing}")

    def section_text(name: str) -> str:
        content = "\n".join(sections[name]).strip()
        return content

    short_definition = section_text("Short definition")
    if not short_definition:
        raise ValidationError(f"{term} requires a short definition")
    full_definition = section_text("Full definition")
    if not full_definition:
        raise ValidationError(f"{term} requires a full definition")

    aliases = tuple(
        validate_alias(value, term)
        for value in parse_list(section_text("AKA"), section=f"{term} AKA")
    )

    inline_terms: list[tuple[str, str]] = []
    inline_content = section_text("Inline terms")
    inline_values = parse_list(inline_content, section=f"{term} Inline terms")
    for value in inline_values:
        match = INLINE_TERM.fullmatch(f"- {value}")
        if not match:
            raise ValidationError(f"Malformed inline-term mapping under {term}: {value!r}")
        inline_terms.append((match.group(1), match.group(2)))

    related_words = tuple(
        parse_list(section_text("Related words"), section=f"{term} Related words")
    )
    raw_categories = parse_list(
        section_text("Categories"),
        section=f"{term} Categories",
        allow_none=False,
    )
    if not raw_categories:
        raise ValidationError(
            f"{term} requires at least one category for JSON v1.0 compatibility"
        )
    categories = tuple(canonical_category(value) for value in raw_categories)
    if len(categories) != len(set(categories)):
        raise ValidationError(f"{term} repeats a category")

    learning_tracks = tuple(
        parse_list(
            section_text("Learning tracks"),
            section=f"{term} Learning tracks",
        )
    )
    invalid_tracks = [
        track for track in learning_tracks if track not in learn_glossary.TRACKS
    ]
    if invalid_tracks:
        raise ValidationError(
            f"{term} has invalid learning tracks: {invalid_tracks}"
        )

    return ParsedEntry(
        term=term,
        slug=slug,
        aliases=aliases,
        short_definition=short_definition,
        full_definition=full_definition,
        inline_terms=tuple(inline_terms),
        related_words=related_words,
        categories=categories,
        learning_tracks=learning_tracks,
    )


def validate_name_conflicts(entries: list[ParsedEntry]) -> None:
    canonical_slugs: dict[str, str] = {}
    names: dict[str, tuple[str, str]] = {}
    alias_slugs: dict[str, str] = {}

    for entry in entries:
        if entry.slug in canonical_slugs:
            raise ValidationError(
                f"Duplicate canonical slug {entry.slug!r}: "
                f"{canonical_slugs[entry.slug]!r} and {entry.term!r}"
            )
        canonical_slugs[entry.slug] = entry.term

        normalized = normalize_lookup(entry.term)
        if normalized in names:
            raise ValidationError(
                f"Duplicate canonical term after normalization: {entry.term!r}"
            )
        names[normalized] = ("canonical", entry.term)

    for entry in entries:
        for alias in entry.aliases:
            normalized = normalize_lookup(alias)
            existing = names.get(normalized)
            if existing:
                kind, owner = existing
                if kind == "canonical":
                    raise ValidationError(
                        f"Canonical and alias conflict after normalization: "
                        f"{owner!r} and {alias!r}"
                    )
                raise ValidationError(
                    f"Alias {alias!r} is assigned to both {owner!r} and {entry.term!r}"
                )
            names[normalized] = ("alias", entry.term)

            slug = alias_slug(alias)
            if slug in canonical_slugs:
                raise ValidationError(
                    f"Alias slug {slug!r} conflicts with canonical "
                    f"{canonical_slugs[slug]!r}"
                )
            if slug in alias_slugs:
                raise ValidationError(
                    f"Duplicate alias slug {slug!r} under "
                    f"{alias_slugs[slug]!r} and {entry.term!r}"
                )
            alias_slugs[slug] = entry.term


def parse_markdown(text: str) -> list[ParsedEntry]:
    normalized = normalize_line_endings(text).lstrip("\ufeff")
    lines = normalized.split("\n")
    headings = [
        (index, match.group(1))
        for index, line in enumerate(lines)
        if (match := ENTRY_HEADING.fullmatch(line))
    ]
    if not headings:
        raise ValidationError("Glossary Markdown contains no canonical entries")

    entries = [
        parse_entry(
            term,
            lines[index + 1 : headings[position + 1][0]]
            if position + 1 < len(headings)
            else lines[index + 1 :],
        )
        for position, (index, term) in enumerate(headings)
    ]
    validate_name_conflicts(entries)
    return entries


def build_public_data(entries: list[ParsedEntry]) -> dict[str, object]:
    terms = [entry.term for entry in entries]
    if len(entries) != len(MVP_TERMS) or set(terms) != set(MVP_TERMS):
        raise ValidationError(
            "This bounded MVP requires exactly Ace, ABT, and Active Builder; "
            f"found {terms}"
        )

    public_entries: list[dict[str, object]] = []
    for entry in entries:
        aliases = [
            {"slug": alias_slug(alias), "term": alias}
            for alias in entry.aliases
        ]
        aliases.sort(key=lambda item: (item["term"].casefold(), item["slug"]))
        public_entry: dict[str, object] = {
            "aliases": aliases,
            "category": entry.categories[0],
            "definition": entry.full_definition,
            "slug": entry.slug,
            "term": entry.term,
        }
        if len(entry.categories) > 1:
            public_entry["categories"] = list(entry.categories)
        public_entries.append(public_entry)

    public_entries.sort(
        key=lambda item: (str(item["term"]).casefold(), str(item["slug"]))
    )
    data: dict[str, object] = {
        "schema_version": "1.0",
        "entries": public_entries,
    }
    validate_current_build_compatibility(data)
    return data


def validate_current_build_compatibility(data: object) -> dict[str, int]:
    if not isinstance(data, dict):
        raise ValidationError("MVP output must be a JSON object")
    entries_value = data.get("entries")
    if not isinstance(entries_value, list):
        raise ValidationError("MVP output entries must be a list")
    alias_count = sum(
        len(entry.get("aliases", []))
        for entry in entries_value
        if isinstance(entry, dict)
    )
    entries = learn_glossary.validate_public_data(
        data,
        expected_canonical_entries=len(MVP_TERMS),
        expected_alias_entries=alias_count,
    )

    entries_html = learn_glossary.build_entries_html(entries, {}, {})
    if entries_html.count('class="bms-glossary-definition"') != len(MVP_TERMS):
        raise ValidationError("Current page generator dropped an MVP definition")
    if "American Backgammon Tour" not in entries_html:
        raise ValidationError("Current page generator dropped the ABT alias")

    lookup_text = learn_glossary.build_lookup_data(entries, {})
    lookup = json.loads(lookup_text)
    lookup_entries = lookup.get("entries")
    if not isinstance(lookup_entries, list) or len(lookup_entries) != len(MVP_TERMS):
        raise ValidationError("Current lookup generator rejected the MVP entries")
    abt = next((entry for entry in lookup_entries if entry.get("term") == "ABT"), None)
    if not isinstance(abt, dict) or abt.get("aliases") != [
        "American Backgammon Tour"
    ]:
        raise ValidationError("Current lookup generator dropped the ABT alias")

    return {
        "alias_entries": alias_count,
        "canonical_entries": len(entries),
        "page_definitions": entries_html.count(
            'class="bms-glossary-definition"'
        ),
        "lookup_entries": len(lookup_entries),
    }


def generate(input_path: Path, output_path: Path) -> dict[str, int]:
    if output_path.resolve() == learn_glossary.PUBLIC_DATA_PATH.resolve():
        raise ValidationError("Refusing to overwrite the production glossary JSON")
    entries = parse_markdown(input_path.read_text(encoding="utf-8"))
    data = build_public_data(entries)
    serialized = learn_glossary.json_text(data)
    learn_glossary.assert_no_forbidden_text(serialized, "MVP glossary JSON")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(serialized, encoding="utf-8", newline="\n")
    return validate_current_build_compatibility(data)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        required=True,
        type=Path,
        help="Three-entry MVP Markdown fixture",
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Task-folder JSON artifact (production glossary.json is refused)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    try:
        result = generate(args.input.resolve(), args.output.resolve())
    except (OSError, UnicodeError, ValidationError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(
        f"MVP glossary JSON written to {args.output.resolve()}: "
        + json.dumps(result, sort_keys=True)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
