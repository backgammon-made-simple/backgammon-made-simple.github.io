#!/usr/bin/env python3
"""Validate the canonical glossary JSON and generate website compatibility data."""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from dataclasses import dataclass
from datetime import date
from pathlib import Path

try:
    from scripts import learn_glossary
except ModuleNotFoundError:  # Direct execution sets sys.path to scripts/.
    import learn_glossary  # type: ignore[no-redef]


GLOSSARY_SOURCE_PATH = learn_glossary.REPOSITORY_ROOT / "glossary" / "glossary.json"
# Compatibility name for review tooling. It points to the one production source.
CONFIRMED_SOURCE_PATH = GLOSSARY_SOURCE_PATH
PRODUCTION_SOURCE_PATH = learn_glossary.PUBLIC_DATA_PATH
LEGACY_MARKDOWN_PATH = learn_glossary.REPOSITORY_ROOT / "glossary" / "glossary_old.md"
DOCUMENT_TITLE = "# BMS glossary"
ENTRY_HEADING = re.compile(r"^# ([^\r\n]+)$")
SECTION_HEADING = re.compile(r"^## ([^\r\n]+)$")
STATUS_FIELD = re.compile(r"^\*\*Status:\*\*\s+(.+?)\s*$")
SLUG_FIELD = re.compile(r"^\*\*Slug:\*\*\s+`([^`]+)`\s*$")
ADDED_FIELD = re.compile(r"^\*\*Added:\*\*\s+(\d{4}-\d{2}-\d{2})\s*$")
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
)
OPTIONAL_SECTIONS = ("Alias notes", "Usage note", "Editorial notes")
ALLOWED_STATUSES = ("Confirmed", "Legacy unconfirmed")
NONE_MARKERS = {"None", "None selected yet."}

PUBLIC_FIELD_ORDER = (
    "term",
    "aliases",
    "redirect_slugs",
    "short_definition",
    "long_definition",
    "categories",
    "tracks",
    "related_terms",
    "inline_terms",
    "status",
    "added",
    "updated",
)
PUBLIC_OPTIONAL_FIELDS = ("usage_note", "editorial_note")
REFERENCE_TYPES = {
    "book",
    "article",
    "manual",
    "website",
    "online_glossary",
    "forum",
    "reddit",
    "video",
    "software",
    "editorial",
    "unresolved",
}

ValidationError = learn_glossary.ValidationError


@dataclass(frozen=True)
class ParsedEntry:
    term: str
    slug: str
    status: str
    date_added: str | None
    aliases: tuple[str, ...]
    short_definition: str
    full_definition: str
    definition_links: tuple[tuple[str, str], ...]
    related_terms: tuple[str, ...]
    categories: tuple[str, ...]
    learning_tracks: tuple[str, ...]
    usage_note: str | None = None


def normalize_line_endings(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def normalize_lookup(value: str) -> str:
    """Normalize lookup text across punctuation, apostrophes, and hyphens."""
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


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValidationError(f"Duplicate raw JSON key: {key!r}")
        result[key] = value
    return result


def load_contract_json(path: Path = GLOSSARY_SOURCE_PATH) -> dict[str, dict[str, object]]:
    raw_bytes = path.read_bytes()
    try:
        raw_text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValidationError("Canonical glossary JSON must use UTF-8") from error
    raw_text = raw_text.replace("\r\n", "\n").replace("\r", "\n")
    if "\u2014" in raw_text:
        raise ValidationError("Canonical glossary JSON contains a prohibited em dash")
    try:
        parsed = json.loads(raw_text, object_pairs_hook=_reject_duplicate_keys)
    except json.JSONDecodeError as error:
        raise ValidationError(f"Malformed canonical glossary JSON: {error}") from error
    if not isinstance(parsed, dict) or not parsed:
        raise ValidationError("Canonical glossary JSON must be a non-empty object")
    return validate_contract_entries(parsed)


def _require_contract_string(entry: dict[str, object], field: str, slug: str) -> str:
    value = entry.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{slug} requires a non-empty {field}")
    if value != value.strip():
        raise ValidationError(f"{slug} {field} has unstable outer whitespace")
    return value


def _require_string_list(entry: dict[str, object], field: str, slug: str) -> list[str]:
    value = entry.get(field)
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item.strip() for item in value
    ):
        raise ValidationError(f"{slug} {field} must be a list of non-empty strings")
    return value


def _validate_reference(reference: object, slug: str, index: int) -> None:
    if not isinstance(reference, dict):
        raise ValidationError(f"{slug} reference {index} must be an object")
    reference_type = reference.get("type")
    if reference_type not in REFERENCE_TYPES:
        raise ValidationError(f"{slug} reference {index} has an invalid type")
    if reference_type == "book":
        for field in ("title", "author"):
            _require_contract_string(reference, field, f"{slug} reference {index}")
        if not reference.get("pages") and not reference.get("section"):
            raise ValidationError(
                f"{slug} reference {index} requires pages or a section"
            )
    elif reference_type in {"article", "manual", "website", "online_glossary"}:
        for field in ("title", "url"):
            _require_contract_string(reference, field, f"{slug} reference {index}")
    elif reference_type in {"forum", "reddit"}:
        for field in ("title", "url", "note"):
            _require_contract_string(reference, field, f"{slug} reference {index}")
    elif reference_type in {"editorial", "unresolved"}:
        _require_contract_string(reference, "note", f"{slug} reference {index}")


def validate_contract_entries(
    data: dict[str, object],
) -> dict[str, dict[str, object]]:
    if list(data) != sorted(data):
        raise ValidationError("Canonical glossary entries must be ordered by slug")

    entries: dict[str, dict[str, object]] = {}
    normalized_names: dict[str, str] = {}
    canonical_slugs = set(data)
    alias_owners: dict[str, str] = {}
    redirect_owners: dict[str, str] = {}
    category_rank = {
        value: index for index, value in enumerate(learn_glossary.GLOSSARY_CATEGORIES)
    }
    track_rank = {value: index for index, value in enumerate(learn_glossary.TRACKS)}

    for slug, raw_entry in data.items():
        if not SLUG_VALUE.fullmatch(slug):
            raise ValidationError(f"Malformed canonical glossary slug: {slug!r}")
        if not isinstance(raw_entry, dict):
            raise ValidationError(f"{slug} must be an object")
        keys = list(raw_entry)
        expected = list(PUBLIC_FIELD_ORDER)
        for optional in PUBLIC_OPTIONAL_FIELDS:
            if optional in raw_entry:
                expected.append(optional)
        expected.append("references")
        if keys != expected:
            raise ValidationError(
                f"{slug} fields are missing, unexpected, or out of contract order"
            )

        term = _require_contract_string(raw_entry, "term", slug)
        if "<" in term or ">" in term or "[" in term or "](" in term:
            raise ValidationError(f"{slug} term must not contain HTML or Markdown links")
        normalized_term = normalize_lookup(term)
        if normalized_term in normalized_names:
            raise ValidationError(
                f"Duplicate normalized canonical terms: {normalized_names[normalized_term]!r} and {term!r}"
            )
        normalized_names[normalized_term] = term

        aliases = _require_string_list(raw_entry, "aliases", slug)
        if aliases != sorted(aliases, key=str.casefold) or len(aliases) != len(set(aliases)):
            raise ValidationError(f"{slug} aliases must be unique and alphabetized")
        for alias in aliases:
            validate_alias(alias, term)

        redirects = _require_string_list(raw_entry, "redirect_slugs", slug)
        for redirect in redirects:
            if not SLUG_VALUE.fullmatch(redirect) or redirect == slug:
                raise ValidationError(f"{slug} has an invalid redirect slug: {redirect!r}")

        _require_contract_string(raw_entry, "short_definition", slug)
        _require_contract_string(raw_entry, "long_definition", slug)

        categories = _require_string_list(raw_entry, "categories", slug)
        if not categories:
            raise ValidationError(f"{slug} requires at least one category")
        if any(value not in category_rank for value in categories):
            raise ValidationError(f"{slug} contains an unknown category")
        if len(categories) != len(set(categories)) or categories != sorted(
            categories, key=category_rank.__getitem__
        ):
            raise ValidationError(f"{slug} categories are duplicated or out of order")

        tracks = _require_string_list(raw_entry, "tracks", slug)
        if any(value not in track_rank for value in tracks):
            raise ValidationError(f"{slug} contains an unknown learning track")
        if len(tracks) != len(set(tracks)) or tracks != sorted(
            tracks, key=track_rank.__getitem__
        ):
            raise ValidationError(f"{slug} tracks are duplicated or out of order")

        related = _require_string_list(raw_entry, "related_terms", slug)
        if slug in related or len(related) != len(set(related)):
            raise ValidationError(f"{slug} related terms contain a self-link or duplicate")
        if any(not SLUG_VALUE.fullmatch(value) for value in related):
            raise ValidationError(f"{slug} contains a malformed related-term slug")

        inline_terms = raw_entry.get("inline_terms")
        if not isinstance(inline_terms, dict):
            raise ValidationError(f"{slug} inline_terms must be an object")
        for phrase, target in inline_terms.items():
            if not isinstance(phrase, str) or not phrase.strip():
                raise ValidationError(f"{slug} has an invalid inline phrase")
            if not isinstance(target, str) or target not in canonical_slugs:
                raise ValidationError(f"{slug} has a broken inline target: {target!r}")
            if target == slug:
                raise ValidationError(f"{slug} has a self-referencing inline target")

        if raw_entry.get("status") != "published":
            raise ValidationError(f"{slug} public status must be published")
        added = _require_contract_string(raw_entry, "added", slug)
        updated = _require_contract_string(raw_entry, "updated", slug)
        try:
            added_date = date.fromisoformat(added)
            updated_date = date.fromisoformat(updated)
        except ValueError as error:
            raise ValidationError(f"{slug} has an invalid publication date") from error
        if updated_date < added_date:
            raise ValidationError(f"{slug} updated date is earlier than added")

        for optional in PUBLIC_OPTIONAL_FIELDS:
            if optional in raw_entry:
                _require_contract_string(raw_entry, optional, slug)
        references = raw_entry.get("references")
        if not isinstance(references, list):
            raise ValidationError(f"{slug} references must be a list")
        for index, reference in enumerate(references):
            _validate_reference(reference, slug, index)
        entries[slug] = raw_entry

    for slug, entry in entries.items():
        for alias in entry["aliases"]:
            normalized = normalize_lookup(str(alias))
            if normalized in normalized_names and normalized_names[normalized] != entry["term"]:
                raise ValidationError(f"Alias {alias!r} conflicts with a canonical term")
            if normalized in alias_owners:
                raise ValidationError(f"Alias {alias!r} has multiple owners")
            alias_owners[normalized] = slug
        for redirect in entry["redirect_slugs"]:
            redirect = str(redirect)
            if redirect in canonical_slugs or redirect in redirect_owners:
                raise ValidationError(f"Redirect slug {redirect!r} collides with another slug")
            redirect_owners[redirect] = slug
    return entries


def build_public_data_from_contract(
    entries: dict[str, dict[str, object]],
) -> dict[str, object]:
    public_entries: list[dict[str, object]] = []
    for slug, entry in entries.items():
        definition_links = [
            {"text": phrase, "slug": str(target)}
            for phrase, target in entry["inline_terms"].items()
        ]
        related_terms = []
        for target_slug in entry["related_terms"]:
            target = entries.get(str(target_slug))
            related: dict[str, str] = {
                "term": str(target["term"]) if target else str(target_slug).replace("-", " ").title()
            }
            if target:
                related["slug"] = str(target_slug)
            related_terms.append(related)
        public: dict[str, object] = {
            "aliases": [
                {"slug": alias_slug(str(alias)), "term": str(alias)}
                for alias in entry["aliases"]
            ],
            "categories": list(entry["categories"]),
            "category": entry["categories"][0],
            "date_added": entry["added"],
            "definition": entry["long_definition"],
            "definition_links": definition_links,
            "learning_tracks": list(entry["tracks"]),
            "redirect_slugs": list(entry["redirect_slugs"]),
            "references": list(entry["references"]),
            "related_terms": related_terms,
            "short_definition": entry["short_definition"],
            "slug": slug,
            "term": entry["term"],
        }
        if entry.get("usage_note"):
            public["usage_note"] = entry["usage_note"]
        public_entries.append(public)
    public_entries.sort(key=lambda item: (str(item["term"]).casefold(), str(item["slug"])))
    data: dict[str, object] = {"schema_version": "1.0", "entries": public_entries}
    validate_with_observed_counts(data)
    return data


def parse_list(content: str, *, section: str) -> list[str]:
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
    if any(value in NONE_MARKERS for value in values):
        if len(values) != 1 or values[0] not in NONE_MARKERS:
            raise ValidationError(
                f"{section} cannot mix a None marker with populated values"
            )
        return []
    return values


def canonical_category(value: str) -> str:
    normalized = " ".join(value.split()).casefold()
    by_normalized = {
        category.casefold(): category
        for category in learn_glossary.GLOSSARY_CATEGORIES
    }
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
    status: str | None = None
    slug: str | None = None
    date_added: str | None = None
    for line in lines[:first_section]:
        stripped = line.strip()
        if not stripped or stripped == "---" or stripped.startswith("<!--"):
            continue
        status_match = STATUS_FIELD.fullmatch(stripped)
        if status_match:
            if status is not None:
                raise ValidationError(f"{term} contains more than one Status field")
            status = status_match.group(1)
            continue
        slug_match = SLUG_FIELD.fullmatch(stripped)
        if slug_match:
            if slug is not None:
                raise ValidationError(f"{term} contains more than one Slug field")
            slug = slug_match.group(1)
            continue
        added_match = ADDED_FIELD.fullmatch(stripped)
        if added_match:
            if date_added is not None:
                raise ValidationError(f"{term} contains more than one Added field")
            date_added = added_match.group(1)
            try:
                date.fromisoformat(date_added)
            except ValueError as error:
                raise ValidationError(
                    f"{term} has an invalid Added date: {date_added!r}"
                ) from error
            continue
        raise ValidationError(f"Unexpected entry metadata under {term}: {line!r}")

    if status not in ALLOWED_STATUSES:
        raise ValidationError(
            f"{term} requires Status to be one of {list(ALLOWED_STATUSES)}"
        )
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
                raise ValidationError(f"{term} repeats the {current_section!r} section")
            sections[current_section] = []
            continue
        if current_section is None:
            if line.strip() and line.strip() != "---":
                raise ValidationError(f"Unexpected content before sections under {term}")
            continue
        sections[current_section].append(line)

    missing = [section for section in REQUIRED_SECTIONS if section not in sections]
    if missing:
        raise ValidationError(f"{term} is missing required sections: {missing}")
    unexpected = set(sections) - set(REQUIRED_SECTIONS) - set(OPTIONAL_SECTIONS)
    if unexpected:
        raise ValidationError(f"{term} has unexpected sections: {sorted(unexpected)}")

    def section_text(name: str) -> str:
        return "\n".join(sections.get(name, [])).strip().removesuffix("---").rstrip()

    short_definition = section_text("Short definition")
    full_definition = section_text("Full definition")
    if not short_definition:
        raise ValidationError(f"{term} requires a short definition")
    if not full_definition:
        raise ValidationError(f"{term} requires a full definition")

    aliases = tuple(
        validate_alias(value, term)
        for value in parse_list(section_text("AKA"), section=f"{term} AKA")
    )
    definition_links: list[tuple[str, str]] = []
    seen_link_phrases: set[str] = set()
    for value in parse_list(
        section_text("Inline terms"), section=f"{term} Inline terms"
    ):
        match = INLINE_TERM.fullmatch(f"- {value}")
        if not match:
            raise ValidationError(f"Malformed inline-term mapping under {term}: {value!r}")
        visible, target_slug = match.groups()
        normalized_visible = normalize_lookup(visible)
        if normalized_visible in seen_link_phrases:
            raise ValidationError(f"{term} repeats an inline-term phrase: {visible!r}")
        seen_link_phrases.add(normalized_visible)
        if normalized_visible not in normalize_lookup(full_definition):
            raise ValidationError(
                f"Inline-term phrase {visible!r} does not occur in {term}'s full definition"
            )
        definition_links.append((visible, target_slug))

    related_terms = tuple(
        parse_list(section_text("Related words"), section=f"{term} Related words")
    )
    categories = tuple(
        canonical_category(value)
        for value in parse_list(section_text("Categories"), section=f"{term} Categories")
    )
    if len(categories) != len(set(categories)):
        raise ValidationError(f"{term} repeats a category")
    # The supplied migration source predates the global display-order rule for 71
    # entries. Preserve that editorial source and canonicalize generated output.
    category_rank = {name: index for index, name in enumerate(learn_glossary.GLOSSARY_CATEGORIES)}
    categories = tuple(sorted(categories, key=category_rank.__getitem__))

    learning_tracks = tuple(
        parse_list(
            section_text("Learning tracks"), section=f"{term} Learning tracks"
        )
    )
    invalid_tracks = [track for track in learning_tracks if track not in learn_glossary.TRACKS]
    if invalid_tracks:
        raise ValidationError(f"{term} has invalid learning tracks: {invalid_tracks}")
    if len(learning_tracks) != len(set(learning_tracks)):
        raise ValidationError(f"{term} repeats a learning track")

    usage_note = section_text("Usage note") or None
    return ParsedEntry(
        term=term,
        slug=slug,
        status=status,
        date_added=date_added,
        aliases=aliases,
        short_definition=short_definition,
        full_definition=full_definition,
        definition_links=tuple(definition_links),
        related_terms=related_terms,
        categories=categories,
        learning_tracks=learning_tracks,
        usage_note=usage_note,
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
    if lines and lines[0].strip() == DOCUMENT_TITLE:
        lines = lines[1:]
        first_entry = next(
            (index for index, line in enumerate(lines) if ENTRY_HEADING.fullmatch(line)),
            None,
        )
        if first_entry is None:
            raise ValidationError("Glossary Markdown contains no canonical entries")
        lines = lines[first_entry:]
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


def parse_confirmed_markdown(text: str) -> list[ParsedEntry]:
    """Backward-compatible parser name for the unified document."""
    return parse_markdown(text)


def _reference_maps(
    entries: list[ParsedEntry],
) -> tuple[dict[str, ParsedEntry], dict[str, ParsedEntry], dict[str, ParsedEntry]]:
    by_slug = {entry.slug: entry for entry in entries}
    by_alias_slug: dict[str, ParsedEntry] = {}
    by_name: dict[str, ParsedEntry] = {}
    for entry in entries:
        by_name[normalize_lookup(entry.term)] = entry
        for alias in entry.aliases:
            by_alias_slug[alias_slug(alias)] = entry
            by_name[normalize_lookup(alias)] = entry
    return by_slug, by_alias_slug, by_name


def build_public_data(
    entries: list[ParsedEntry],
    reference_entries: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    del reference_entries  # Unified production references resolve within one document.
    by_slug, by_alias_slug, by_name = _reference_maps(entries)
    public_entries: list[dict[str, object]] = []
    for entry in entries:
        definition_links: list[dict[str, str]] = []
        for visible, authored_slug in entry.definition_links:
            target = by_slug.get(authored_slug) or by_alias_slug.get(authored_slug)
            if target is None:
                raise ValidationError(
                    f"{entry.term} has missing inline target: {authored_slug!r}"
                )
            definition_links.append({"slug": target.slug, "text": visible})

        related_terms: list[dict[str, str]] = []
        for label in entry.related_terms:
            related: dict[str, str] = {"term": label}
            target = by_name.get(normalize_lookup(label))
            if target is not None:
                related["slug"] = target.slug
            related_terms.append(related)

        public: dict[str, object] = {
            "aliases": [
                {"slug": alias_slug(alias), "term": alias}
                for alias in sorted(entry.aliases, key=str.casefold)
            ],
            "categories": list(entry.categories),
            "definition": entry.full_definition,
            "definition_links": definition_links,
            "learning_tracks": list(entry.learning_tracks),
            "related_terms": related_terms,
            "short_definition": entry.short_definition,
            "slug": entry.slug,
            "term": entry.term,
        }
        if entry.categories:
            public["category"] = entry.categories[0]
        if entry.date_added:
            public["date_added"] = entry.date_added
        if entry.usage_note:
            public["usage_note"] = entry.usage_note
        public_entries.append(public)

    public_entries.sort(key=lambda item: (str(item["term"]).casefold(), str(item["slug"])))
    data: dict[str, object] = {"schema_version": "1.0", "entries": public_entries}
    validate_with_observed_counts(data)
    return data


def validate_with_observed_counts(
    data: object,
    *,
    reference_entries: list[dict[str, object]] | None = None,
) -> list[dict[str, object]]:
    if not isinstance(data, dict) or not isinstance(data.get("entries"), list):
        raise ValidationError("Glossary source must contain an entries list")
    entries = data["entries"]
    alias_count = sum(
        len(entry.get("aliases", []))
        for entry in entries
        if isinstance(entry, dict) and isinstance(entry.get("aliases"), list)
    )
    return learn_glossary.validate_public_data(
        data,
        expected_canonical_entries=len(entries),
        expected_alias_entries=alias_count,
        reference_entries=reference_entries,
    )


def build_production_source() -> tuple[str, dict[str, object]]:
    entries = load_contract_json()
    data = build_public_data_from_contract(entries)
    serialized = learn_glossary.json_text(data)
    learn_glossary.assert_no_forbidden_text(
        serialized, "generated production glossary data"
    )
    report: dict[str, object] = {
        "aliases": sum(len(entry["aliases"]) for entry in entries.values()),
        "canonical_entries": len(entries),
        "published_entries": len(entries),
        "unresolved_related_terms": sum(
            target not in entries
            for entry in entries.values()
            for target in entry["related_terms"]
        ),
    }
    return serialized, report


def generate_production_source() -> dict[str, object]:
    serialized, report = build_production_source()
    changed = learn_glossary.write_if_changed(PRODUCTION_SOURCE_PATH, serialized)
    result = dict(report)
    result["bytes"] = len(serialized.encode("utf-8"))
    result["changed"] = changed
    result["sha256"] = learn_glossary.sha256_bytes(serialized.encode("utf-8"))
    return result


def assert_source_current(tracked: str, generated: str) -> None:
    if tracked != generated:
        raise ValidationError(
            "Generated production glossary is stale or manually edited; "
            "run `python scripts/glossary_source.py generate-source`"
        )


def check_production_source() -> dict[str, object]:
    serialized, report = build_production_source()
    if not PRODUCTION_SOURCE_PATH.exists():
        raise ValidationError(
            "Generated production glossary is missing; run generate-source"
        )
    assert_source_current(
        PRODUCTION_SOURCE_PATH.read_text(encoding="utf-8"), serialized
    )
    result = dict(report)
    result["bytes"] = len(serialized.encode("utf-8"))
    result["sha256"] = learn_glossary.sha256_bytes(serialized.encode("utf-8"))
    return result


def validate_current_build_compatibility(
    data: object,
    reference_entries: list[dict[str, object]] | None = None,
) -> dict[str, int]:
    entries = validate_with_observed_counts(
        data, reference_entries=reference_entries
    )
    entries_html = learn_glossary.build_entries_html(entries, {}, {})
    lookup = json.loads(learn_glossary.build_lookup_data(entries, {}))
    lookup_entries = lookup["entries"]
    return {
        "alias_entries": sum(len(entry["aliases"]) for entry in entries),
        "canonical_entries": len(entries),
        "definition_links": entries_html.count("data-bms-definition-link="),
        "lookup_entries": len(lookup_entries),
        "page_full_definitions": entries_html.count(
            'class="bms-glossary-definition"'
        ),
        "page_related_term_groups": entries_html.count(
            'class="bms-glossary-related-terms"'
        ),
        "page_short_definitions": entries_html.count(
            'class="bms-glossary-short-definition"'
        ),
    }


def generate_subset(input_path: Path, output_path: Path) -> dict[str, int]:
    if output_path.resolve() == PRODUCTION_SOURCE_PATH.resolve():
        raise ValidationError("Refusing to overwrite the production glossary JSON")
    parsed = parse_markdown(input_path.read_text(encoding="utf-8"))
    data = build_public_data(parsed)
    serialized = learn_glossary.json_text(data)
    learn_glossary.assert_no_forbidden_text(serialized, "Glossary subset JSON")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(serialized, encoding="utf-8", newline="\n")
    return validate_current_build_compatibility(data)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser(
        "generate-source",
        help="Generate website compatibility JSON from canonical glossary JSON",
    )
    commands.add_parser(
        "check-source",
        help="Fail when tracked production JSON differs from a fresh generation",
    )
    subset = commands.add_parser(
        "generate-subset", help="Generate isolated review JSON from Markdown"
    )
    subset.add_argument("--input", required=True, type=Path)
    subset.add_argument("--output", required=True, type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    try:
        if args.command == "generate-source":
            result = generate_production_source()
            print(
                "Generated production glossary source: "
                + json.dumps(result, sort_keys=True)
            )
            return 0
        if args.command == "check-source":
            result = check_production_source()
            print(
                "Production glossary source is current: "
                + json.dumps(result, sort_keys=True)
            )
            return 0
        result = generate_subset(args.input.resolve(), args.output.resolve())
    except (OSError, UnicodeError, ValidationError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(
        f"Glossary subset JSON written to {args.output.resolve()}: "
        + json.dumps(result, sort_keys=True)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
