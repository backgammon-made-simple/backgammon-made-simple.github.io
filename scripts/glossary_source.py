#!/usr/bin/env python3
"""Parse confirmed glossary Markdown and generate the production JSON v1.0 source."""

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


CONFIRMED_SOURCE_PATH = (
    learn_glossary.REPOSITORY_ROOT / "glossary_wip" / "confirmed-terms.md"
)
LEGACY_MIGRATION_PATH = (
    learn_glossary.REPOSITORY_ROOT
    / "glossary_wip"
    / "legacy-unconfirmed-glossary.json"
)
PRODUCTION_SOURCE_PATH = learn_glossary.PUBLIC_DATA_PATH
ENTRY_HEADING = re.compile(r"^# ([^\r\n]+)$")
SECTION_HEADING = re.compile(r"^## ([^\r\n]+)$")
SLUG_FIELD = re.compile(r"^\*\*Slug:\*\*\s+`([^`]+)`\s*$")
ADDED_FIELD = re.compile(r"^\*\*Added:\*\*\s+(\d{4}-\d{2}-\d{2})\s*$")
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
NONE_MARKERS = {"None", "None selected yet."}

ValidationError = learn_glossary.ValidationError


@dataclass(frozen=True)
class ParsedEntry:
    term: str
    slug: str
    date_added: str
    aliases: tuple[str, ...]
    short_definition: str
    full_definition: str
    definition_links: tuple[tuple[str, str], ...]
    related_terms: tuple[str, ...]
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
    slug: str | None = None
    date_added: str | None = None
    for line in lines[:first_section]:
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

    if slug is None:
        raise ValidationError(f"{term} requires a Slug field")
    if not SLUG_VALUE.fullmatch(slug):
        raise ValidationError(f"{term} has a malformed canonical slug: {slug!r}")
    if date_added is None:
        raise ValidationError(f"{term} requires an Added field")

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
        return "\n".join(sections[name]).strip()

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

    definition_links: list[tuple[str, str]] = []
    for value in parse_list(
        section_text("Inline terms"),
        section=f"{term} Inline terms",
    ):
        match = INLINE_TERM.fullmatch(f"- {value}")
        if not match:
            raise ValidationError(f"Malformed inline-term mapping under {term}: {value!r}")
        visible, target_slug = match.groups()
        if visible.casefold() not in full_definition.casefold():
            raise ValidationError(
                f"Inline-term phrase {visible!r} does not occur in {term}'s "
                "full definition"
            )
        definition_links.append((visible, target_slug))

    related_terms = tuple(
        parse_list(section_text("Related words"), section=f"{term} Related words")
    )
    raw_categories = parse_list(
        section_text("Categories"),
        section=f"{term} Categories",
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
    if len(learning_tracks) != len(set(learning_tracks)):
        raise ValidationError(f"{term} repeats a learning track")

    return ParsedEntry(
        term=term,
        slug=slug,
        date_added=date_added,
        aliases=aliases,
        short_definition=short_definition,
        full_definition=full_definition,
        definition_links=tuple(definition_links),
        related_terms=related_terms,
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


def parse_confirmed_markdown(text: str) -> list[ParsedEntry]:
    """Parse the complete maintained document without treating its title as an entry."""
    normalized = normalize_line_endings(text).lstrip("\ufeff")
    title = "# Confirmed glossary terms"
    lines = normalized.split("\n")
    if not lines or lines[0].strip() != title:
        raise ValidationError(
            "Confirmed glossary source must begin with '# Confirmed glossary terms'"
        )
    return parse_markdown("\n".join(lines[1:]))


def reference_maps(
    entries: list[dict[str, object]],
) -> tuple[set[str], dict[str, tuple[str, str]]]:
    canonical_slugs = {str(entry["slug"]) for entry in entries}
    names: dict[str, tuple[str, str]] = {}
    for entry in entries:
        slug = str(entry["slug"])
        canonical_term = str(entry["term"])
        for name in (
            canonical_term,
            *(
                str(alias["term"])
                for alias in entry["aliases"]  # type: ignore[index]
            ),
        ):
            normalized = normalize_lookup(name)
            existing = names.get(normalized)
            if existing and existing[0] != slug:
                raise ValidationError(
                    f"Ambiguous production lookup name {name!r}: "
                    f"{existing[0]!r} and {slug!r}"
                )
            names[normalized] = (slug, canonical_term)
    return canonical_slugs, names


def build_public_data(
    entries: list[ParsedEntry],
    reference_entries: list[dict[str, object]],
) -> dict[str, object]:
    reference_slugs, reference_names = reference_maps(reference_entries)
    public_entries: list[dict[str, object]] = []
    for entry in entries:
        definition_links = [
            {"slug": slug, "text": text}
            for text, slug in entry.definition_links
        ]
        missing_links = [
            link["slug"]
            for link in definition_links
            if link["slug"] not in reference_slugs
            and link["slug"] not in {candidate.slug for candidate in entries}
        ]
        if missing_links:
            raise ValidationError(
                f"{entry.term} has missing definition-link targets: {missing_links}"
            )

        related_terms: list[dict[str, str]] = []
        for related_term in entry.related_terms:
            related: dict[str, str] = {"term": related_term}
            resolved = reference_names.get(normalize_lookup(related_term))
            if resolved:
                related["slug"] = resolved[0]
            related_terms.append(related)

        aliases = [
            {"slug": alias_slug(alias), "term": alias}
            for alias in entry.aliases
        ]
        aliases.sort(key=lambda item: (item["term"].casefold(), item["slug"]))
        public_entry: dict[str, object] = {
            "aliases": aliases,
            "categories": list(entry.categories),
            "date_added": entry.date_added,
            "definition": entry.full_definition,
            "definition_links": definition_links,
            "learning_tracks": list(entry.learning_tracks),
            "related_terms": related_terms,
            "short_definition": entry.short_definition,
            "slug": entry.slug,
            "term": entry.term,
        }
        if entry.categories:
            public_entry["category"] = entry.categories[0]
        public_entries.append(public_entry)

    public_entries.sort(
        key=lambda item: (str(item["term"]).casefold(), str(item["slug"]))
    )
    data: dict[str, object] = {
        "schema_version": "1.0",
        "entries": public_entries,
    }
    validate_current_build_compatibility(data, reference_entries)
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


def rich_legacy_entry(entry: dict[str, object]) -> dict[str, object]:
    """Add deliberate rich compatibility fields without changing legacy meaning."""
    copied = json.loads(json.dumps(entry, ensure_ascii=False))
    label = f"legacy entry {copied.get('slug')}"
    categories = learn_glossary.glossary_categories(copied, label)
    copied["categories"] = categories
    copied["short_definition"] = str(copied["definition"])
    copied.setdefault("definition_links", [])
    copied.setdefault("related_terms", [])
    copied.setdefault("learning_tracks", [])
    copied["aliases"] = sorted(
        copied["aliases"],
        key=lambda item: (
            str(item["term"]).casefold(),
            str(item["slug"]),
        ),
    )
    return copied


def confirmed_entry_shell(entry: ParsedEntry) -> dict[str, object]:
    aliases = sorted(
        (
            {"slug": alias_slug(alias), "term": alias}
            for alias in entry.aliases
        ),
        key=lambda item: (item["term"].casefold(), item["slug"]),
    )
    public: dict[str, object] = {
        "aliases": aliases,
        "categories": list(entry.categories),
        "date_added": entry.date_added,
        "definition": entry.full_definition,
        "definition_links": [],
        "learning_tracks": list(entry.learning_tracks),
        "related_terms": [],
        "short_definition": entry.short_definition,
        "slug": entry.slug,
        "term": entry.term,
    }
    if entry.categories:
        public["category"] = entry.categories[0]
    return public


def combined_reference_maps(
    entries: list[dict[str, object]],
) -> tuple[
    dict[str, dict[str, object]],
    dict[str, str],
    dict[str, tuple[str, str]],
]:
    canonical_by_slug: dict[str, dict[str, object]] = {}
    alias_slug_to_canonical: dict[str, str] = {}
    normalized_name_to_canonical: dict[str, tuple[str, str]] = {}

    for entry in entries:
        slug = str(entry["slug"])
        term = str(entry["term"])
        if slug in canonical_by_slug:
            raise ValidationError(f"Duplicate combined canonical slug {slug!r}")
        normalized = normalize_lookup(term)
        existing = normalized_name_to_canonical.get(normalized)
        if existing:
            raise ValidationError(
                f"Duplicate combined canonical term after normalization: "
                f"{existing[1]!r} and {term!r}"
            )
        canonical_by_slug[slug] = entry
        normalized_name_to_canonical[normalized] = (slug, term)

    for entry in entries:
        owner_slug = str(entry["slug"])
        for alias in entry["aliases"]:  # type: ignore[index]
            alias_term = str(alias["term"])
            alias_value_slug = str(alias["slug"])
            normalized = normalize_lookup(alias_term)
            existing = normalized_name_to_canonical.get(normalized)
            if existing:
                raise ValidationError(
                    f"Duplicate alias ownership after normalization: "
                    f"{alias_term!r} belongs to {owner_slug!r}, but "
                    f"{existing[1]!r} belongs to {existing[0]!r}"
                )
            if alias_value_slug in canonical_by_slug:
                raise ValidationError(
                    f"Combined alias slug {alias_value_slug!r} conflicts with "
                    "a canonical slug"
                )
            if alias_value_slug in alias_slug_to_canonical:
                raise ValidationError(
                    f"Duplicate combined alias slug {alias_value_slug!r}"
                )
            alias_slug_to_canonical[alias_value_slug] = owner_slug
            normalized_name_to_canonical[normalized] = (
                owner_slug,
                alias_term,
            )
    return (
        canonical_by_slug,
        alias_slug_to_canonical,
        normalized_name_to_canonical,
    )


def merge_confirmed_and_legacy(
    confirmed_entries: list[ParsedEntry],
    legacy_data: object,
) -> tuple[dict[str, object], dict[str, object]]:
    legacy_entries = validate_with_observed_counts(legacy_data)
    confirmed_slugs = {entry.slug for entry in confirmed_entries}
    confirmed_alias_exact = {
        alias: entry.slug
        for entry in confirmed_entries
        for alias in entry.aliases
    }
    confirmed_claims: dict[str, tuple[str, str, str]] = {}
    confirmed_claim_slugs: dict[str, tuple[str, str, str]] = {}
    for entry in confirmed_entries:
        claims = (("canonical", entry.term, entry.slug),) + tuple(
            ("alias", alias, alias_slug(alias))
            for alias in entry.aliases
        )
        for kind, term, slug_value in claims:
            normalized = normalize_lookup(term)
            existing = confirmed_claims.get(normalized)
            if existing and existing[0] != entry.slug:
                raise ValidationError(
                    f"Confirmed name {term!r} has conflicting ownership"
                )
            confirmed_claims[normalized] = (entry.slug, kind, term)
            existing_slug = confirmed_claim_slugs.get(slug_value)
            if existing_slug and existing_slug[0] != entry.slug:
                raise ValidationError(
                    f"Confirmed slug {slug_value!r} has conflicting ownership"
                )
            confirmed_claim_slugs[slug_value] = (entry.slug, kind, term)

    replaced_slugs: list[str] = []
    alias_takeovers: list[dict[str, str]] = []
    retained_candidates: list[dict[str, object]] = []
    for legacy in legacy_entries:
        slug = str(legacy["slug"])
        term = str(legacy["term"])
        if slug in confirmed_slugs:
            replaced_slugs.append(slug)
            continue
        alias_owner = confirmed_alias_exact.get(term)
        if alias_owner:
            alias_takeovers.append(
                {
                    "confirmed_slug": alias_owner,
                    "legacy_slug": slug,
                    "term": term,
                }
            )
            continue
        retained_candidates.append(legacy)

    removed_legacy_aliases: list[dict[str, str]] = []
    retained_entries: list[dict[str, object]] = []
    for legacy in retained_candidates:
        legacy_slug = str(legacy["slug"])
        legacy_term = str(legacy["term"])
        normalized = normalize_lookup(legacy_term)
        claim = confirmed_claims.get(normalized)
        if claim:
            raise ValidationError(
                f"Confirmed {claim[1]} {claim[2]!r} conflicts with retained "
                f"legacy canonical {legacy_term!r}"
            )
        slug_claim = confirmed_claim_slugs.get(legacy_slug)
        if slug_claim:
            raise ValidationError(
                f"Confirmed {slug_claim[1]} slug {legacy_slug!r} conflicts "
                f"with retained legacy canonical {legacy_term!r}"
            )

        copied = json.loads(json.dumps(legacy, ensure_ascii=False))
        filtered_aliases: list[dict[str, object]] = []
        for alias in copied["aliases"]:
            alias_term = str(alias["term"])
            alias_value_slug = str(alias["slug"])
            normalized_alias = normalize_lookup(alias_term)
            name_claim = confirmed_claims.get(normalized_alias)
            slug_claim = confirmed_claim_slugs.get(alias_value_slug)
            claim = name_claim or slug_claim
            if claim:
                if alias_term != claim[2]:
                    raise ValidationError(
                        f"Normalized confirmed/legacy alias conflict: "
                        f"{claim[2]!r} versus {alias_term!r}"
                    )
                removed_legacy_aliases.append(
                    {
                        "alias_slug": alias_value_slug,
                        "alias_term": alias_term,
                        "confirmed_slug": claim[0],
                        "legacy_owner_slug": legacy_slug,
                    }
                )
                continue
            filtered_aliases.append(alias)
        copied["aliases"] = filtered_aliases
        retained_entries.append(rich_legacy_entry(copied))

    confirmed_public = [
        confirmed_entry_shell(entry)
        for entry in confirmed_entries
    ]
    # Legacy entries remain available only as migration/review input. Production
    # publishes the entries that have completed the confirmed Markdown workflow.
    combined = confirmed_public
    (
        canonical_by_slug,
        alias_slug_to_canonical,
        normalized_name_to_canonical,
    ) = combined_reference_maps(combined)

    parsed_by_slug = {entry.slug: entry for entry in confirmed_entries}
    canonicalized_inline_targets: list[dict[str, str]] = []
    unresolved_inline_targets: list[dict[str, str]] = []
    unresolved_related: list[dict[str, str]] = []
    for public in confirmed_public:
        slug = str(public["slug"])
        parsed = parsed_by_slug[slug]
        links: list[dict[str, str]] = []
        for visible, target_slug in parsed.definition_links:
            canonical_target = target_slug
            if canonical_target not in canonical_by_slug:
                canonical_target = alias_slug_to_canonical.get(target_slug, "")
            if not canonical_target:
                unresolved_inline_targets.append(
                    {
                        "entry_slug": slug,
                        "target_slug": target_slug,
                        "visible": visible,
                    }
                )
                continue
            if canonical_target != target_slug:
                canonicalized_inline_targets.append(
                    {
                        "entry_slug": slug,
                        "authored_target": target_slug,
                        "canonical_target": canonical_target,
                        "visible": visible,
                    }
                )
            links.append({"slug": canonical_target, "text": visible})
        public["definition_links"] = links

        related_values: list[dict[str, str]] = []
        for related_term in parsed.related_terms:
            related: dict[str, str] = {"term": related_term}
            resolved = normalized_name_to_canonical.get(
                normalize_lookup(related_term)
            )
            if resolved:
                related["slug"] = resolved[0]
            else:
                unresolved_related.append(
                    {"entry_slug": slug, "term": related_term}
                )
            related_values.append(related)
        public["related_terms"] = related_values

    combined.sort(
        key=lambda item: (
            str(item["term"]).casefold(),
            str(item["slug"]),
        )
    )
    data: dict[str, object] = {
        "entries": combined,
        "schema_version": "1.0",
    }
    validate_with_observed_counts(data)
    report: dict[str, object] = {
        "canonicalized_inline_targets": sorted(
            canonicalized_inline_targets,
            key=lambda item: (
                item["entry_slug"],
                item["visible"].casefold(),
            ),
        ),
        "confirmed_aliases": sum(
            len(entry.aliases) for entry in confirmed_entries
        ),
        "confirmed_entries": len(confirmed_entries),
        "confirmed_new_slugs": sorted(confirmed_slugs - set(replaced_slugs)),
        "confirmed_replaced_slugs": sorted(replaced_slugs),
        "final_aliases": sum(
            len(entry["aliases"])  # type: ignore[arg-type]
            for entry in combined
        ),
        "final_entries": len(combined),
        "legacy_aliases_removed": sorted(
            removed_legacy_aliases,
            key=lambda item: (
                item["legacy_owner_slug"],
                item["alias_term"].casefold(),
            ),
        ),
        "legacy_canonicals_absorbed_as_confirmed_aliases": sorted(
            alias_takeovers,
            key=lambda item: item["legacy_slug"],
        ),
        "retained_legacy_aliases": 0,
        "retained_legacy_entries": 0,
        "review_only_legacy_aliases": sum(
            len(entry["aliases"])  # type: ignore[arg-type]
            for entry in retained_entries
        ),
        "review_only_legacy_entries": len(retained_entries),
        "unresolved_inline_targets": sorted(
            unresolved_inline_targets,
            key=lambda item: (
                item["entry_slug"],
                item["visible"].casefold(),
            ),
        ),
        "unresolved_related_terms": sorted(
            unresolved_related,
            key=lambda item: (
                item["entry_slug"],
                item["term"].casefold(),
            ),
        ),
    }
    return data, report


def build_production_source() -> tuple[str, dict[str, object]]:
    confirmed_entries = parse_confirmed_markdown(
        CONFIRMED_SOURCE_PATH.read_text(encoding="utf-8")
    )
    legacy_data = learn_glossary.read_json(LEGACY_MIGRATION_PATH)
    data, report = merge_confirmed_and_legacy(confirmed_entries, legacy_data)
    serialized = learn_glossary.json_text(data)
    learn_glossary.assert_no_forbidden_text(
        serialized,
        "generated production glossary data",
    )
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
    tracked = PRODUCTION_SOURCE_PATH.read_text(encoding="utf-8")
    assert_source_current(tracked, serialized)
    result = dict(report)
    result["bytes"] = len(serialized.encode("utf-8"))
    result["sha256"] = learn_glossary.sha256_bytes(serialized.encode("utf-8"))
    return result


def validate_current_build_compatibility(
    data: object,
    reference_entries: list[dict[str, object]],
) -> dict[str, int]:
    if not isinstance(data, dict):
        raise ValidationError("Glossary output must be a JSON object")
    entries_value = data.get("entries")
    if not isinstance(entries_value, list):
        raise ValidationError("Glossary output entries must be a list")
    alias_count = sum(
        len(entry.get("aliases", []))
        for entry in entries_value
        if isinstance(entry, dict)
    )
    entries = learn_glossary.validate_public_data(
        data,
        expected_canonical_entries=len(entries_value),
        expected_alias_entries=alias_count,
        reference_entries=reference_entries,
    )

    entries_html = learn_glossary.build_entries_html(entries, {}, {})
    definition_link_count = entries_html.count("data-bms-definition-link=")
    if entries_html.count('class="bms-glossary-short-definition"') != 0:
        raise ValidationError(
            "Current page generator exposed short definitions on the "
            "full-definition glossary page"
        )
    if entries_html.count('class="bms-glossary-definition"') != len(entries):
        raise ValidationError("Current page generator dropped a full definition")
    authored_link_count = sum(
        1
        for entry in entries
        for link in entry.get("definition_links", [])
        if str(link["slug"]) != str(entry["slug"])
    )
    if definition_link_count < authored_link_count:
        raise ValidationError("Current page generator dropped definition links")
    expected_related_groups = sum(
        bool(entry.get("related_terms")) for entry in entries
    )
    if (
        entries_html.count('class="bms-glossary-related-terms"')
        != expected_related_groups
    ):
        raise ValidationError("Current page generator dropped related terms")

    lookup_text = learn_glossary.build_lookup_data(entries, {})
    lookup = json.loads(lookup_text)
    lookup_entries = lookup.get("entries")
    if not isinstance(lookup_entries, list) or len(lookup_entries) != len(entries):
        raise ValidationError("Current lookup generator rejected glossary entries")
    for lookup_entry in lookup_entries:
        for field in (
            "categories",
            "definition_links",
            "learning_tracks",
            "related_terms",
            "short_definition",
        ):
            if field not in lookup_entry:
                raise ValidationError(
                    f"Current lookup generator dropped {field} from "
                    f"{lookup_entry.get('term')}"
                )

    return {
        "alias_entries": alias_count,
        "canonical_entries": len(entries),
        "definition_links": definition_link_count,
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
    if output_path.resolve() == learn_glossary.PUBLIC_DATA_PATH.resolve():
        raise ValidationError("Refusing to overwrite the production glossary JSON")
    review_data = learn_glossary.read_json(LEGACY_MIGRATION_PATH)
    reference_entries = validate_with_observed_counts(review_data)
    parsed_entries = parse_markdown(input_path.read_text(encoding="utf-8"))
    data = build_public_data(parsed_entries, reference_entries)
    serialized = learn_glossary.json_text(data)
    learn_glossary.assert_no_forbidden_text(serialized, "Glossary subset JSON")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(serialized, encoding="utf-8", newline="\n")
    return validate_current_build_compatibility(data, reference_entries)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser(
        "generate-source",
        help="Generate production JSON from confirmed Markdown and legacy migration data",
    )
    commands.add_parser(
        "check-source",
        help="Fail when tracked production JSON differs from a fresh generation",
    )
    subset = commands.add_parser(
        "generate-subset",
        help="Generate an isolated review JSON from a Markdown subset",
    )
    subset.add_argument(
        "--input",
        required=True,
        type=Path,
        help="Markdown subset",
    )
    subset.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Review JSON output (production glossary.json is refused)",
    )
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
        if args.command != "generate-subset":
            raise AssertionError(f"Unhandled command: {args.command}")
        result = generate_subset(args.input.resolve(), args.output.resolve())
    except (OSError, UnicodeError, ValidationError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(
        f"Rich-field glossary subset JSON written to {args.output.resolve()}: "
        + json.dumps(result, sort_keys=True)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
