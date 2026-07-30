# Glossary Markdown-to-JSON MVP

This bounded authoring path accepts exactly three canonical entries: Ace, ABT,
and Active Builder. It is an MVP compatibility proof, not the full glossary
conversion path.

Run it explicitly from the repository root:

```powershell
.venv\Scripts\python.exe scripts\glossary_markdown_mvp.py `
  --input C:\path\to\artifacts\<timestamp>-mvp-confirmed-terms.md `
  --output C:\path\to\artifacts\<timestamp>-mvp-glossary.json
```

The command refuses to overwrite `site/data/glossary.json`. It validates the
Markdown and exercises the existing JSON validator, glossary-page generator,
and compact search-lookup generator before writing output.

## Accepted MVP entry format

Each entry begins with one level-one canonical term heading. `Status` is
optional, and `Slug` is required.

```markdown
# Canonical Term

**Status:** Optional editorial text

**Slug:** `canonical-slug`

## AKA

- Alias or lookup phrase
- None

## Short definition

One required short definition.

## Full definition

One required full definition. Multiple paragraphs and punctuation are
preserved with LF line endings.

## Inline terms

- "visible phrase" -> `target-slug`
- None selected yet.

## Related words

- Related Term
- None selected yet.

## Categories

- One or more controlled categories

## Learning tracks

- One or more existing learning-track names
- None

## Generation notes

Editorial-only notes.
```

`Editorial notes` may follow the required sections. Generation and editorial
notes, status, short definition, inline-term mappings, related words, and
learning tracks are validated as authoring data but are not emitted because
JSON schema v1.0 has no equivalent public fields. The required full definition
maps to the existing public `definition` field without rewriting.

## JSON v1.0 compatibility

Canonical entries retain the existing fields used by the website:

- `aliases`: existing objects with `slug` and `term`;
- `category`: the required legacy primary category;
- `definition`: the full definition;
- `slug`;
- `term`.

For a multi-category entry only, `categories` is added as the ordered complete
list. `category` must equal `categories[0]`. Single-category entries omit
`categories`, so their shape is unchanged. Existing page and search consumers
continue using `category`; the validator derives a one-item category list when
the extension is absent.

The MVP accepts the controlled category names already present in the production
glossary, case-insensitively, and emits their existing lowercase JSON values.
Repeated or unknown categories fail validation.

For current JSON v1.0 compatibility, every MVP entry must have at least one
category even though the broader editorial format may eventually support zero.

## Determinism and collision rules

Output uses UTF-8, LF line endings, sorted object keys, deterministic canonical
term ordering, and deterministic alias ordering. Lookup names are checked for
conflicts after Unicode normalization, case folding, whitespace collapse, and
punctuation removal. Duplicate canonical terms or slugs, shared aliases,
canonical/alias conflicts, and alias-slug conflicts fail before output.
