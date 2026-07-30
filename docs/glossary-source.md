# Glossary Markdown production source

`glossary_wip/confirmed-terms.md` is the only production source for reviewed
glossary entries. The temporary migration inventory in
`glossary_wip/legacy-unconfirmed-glossary.json` is used for review and conflict
reporting, but its unconfirmed entries are never published.

Run production generation and drift checks from the repository root:

```powershell
python scripts\learn_glossary.py generate-source
python scripts\learn_glossary.py check-source
```

`site/data/glossary.json` is generated. Do not edit it manually.

The normal glossary command regenerates production data before building any
consumer:

```powershell
python scripts\learn_glossary.py generate
python scripts\learn_glossary.py validate
```

Production code never reads `staged-terms.md`,
`comprehensive-list-of-terms.md`, or the permanent task folder.

## Accepted entry format

```markdown
# Canonical Term

**Status:** Optional editorial text

**Slug:** `canonical-slug`

**Added:** 2026-07-30

## AKA

- Alias or lookup phrase
- None

## Short definition

One required short definition.

## Full definition

One required full definition. Multiple paragraphs and punctuation are
preserved with LF line endings.

The public glossary page displays this full definition. Compact term lookup
results and inline lesson hover cards use the separate short definition.

## Inline terms

- "visible phrase" -> `target-slug`
- None selected yet.

## Related words

- Related Term
- None selected yet.

## Categories

- Zero or more controlled categories
- None

## Learning tracks

- Zero or more existing learning-track names
- None

## Generation notes

Editorial-only notes.
```

Additional editorial sections may follow Generation notes. Status, generation
notes, and other editorial-only sections are never emitted.

## Rich JSON v1.0 shape

Every confirmed entry emits:

- `term`;
- `slug`;
- stable ISO `date_added`, used for its RSS publication date;
- `aliases` using the existing objects with `slug` and `term`;
- `short_definition`;
- full `definition`;
- `definition_links`;
- `related_terms`;
- ordered `categories`;
- `learning_tracks`.

`definition_links` preserves each authored visible phrase and canonical target:

```json
{"text": "one-point", "slug": "one-point"}
```

The visible phrase must occur in the full definition, and its target must be a
canonical slug in the final approved production glossary.

The generated glossary also detects approved canonical terms and aliases in
each full definition automatically. Matches receive the same keyboard-focus
and pointer-hover treatment as highlighted lesson terms, and the hover card
always reads the target's canonical `short_definition`. Explicit Inline terms
remain available as higher-priority mappings when editorial wording needs a
specific target.

`related_terms` preserves authored order and spelling. When the term resolves
through a current canonical or alias name, its canonical slug is added:

```json
{"term": "Ace-Point", "slug": "one-point"}
```

An unresolved editorial related term remains explicit without a slug:

```json
{"term": "Our Board"}
```

This preserves the confirmed editorial decision without incorrectly treating a
staged or pending term as a production target.

## Compatibility fields

When `categories` is non-empty, legacy `category` is emitted and must equal
`categories[0]`. When `categories` is empty, `category` is omitted; no
misleading fallback category is invented.

The existing HTML builder conditionally:

- renders full definitions on the glossary page;
- links explicit and automatically matched inline phrases to glossary
  fragments;
- preserves all categories in a data attribute and visible buttons;
- merges author-supplied learning tracks into its track data;
- renders resolved related terms as links and unresolved terms as text.

Related terms are presented in a separate **See also** section.

The compact lookup builder carries the rich fields required by glossary and
lesson consumers.

## Determinism and conflicts

Output uses UTF-8, LF line endings, sorted object keys, deterministic
canonical-term ordering, and deterministic alias ordering.

Canonical and alias names are checked after Unicode normalization, case
folding, whitespace collapse, and punctuation removal. Duplicate terms or
slugs, shared aliases, canonical-versus-alias conflicts, malformed mappings,
missing definitions, invalid/repeated categories, invalid/repeated learning
tracks, and unstable output order fail before output.

## Production generation and migration

```text
glossary_wip/confirmed-terms.md
  -> site/data/glossary.json

glossary_wip/legacy-unconfirmed-glossary.json
  -> migration and conflict report only
```

Run:

```powershell
python scripts\learn_glossary.py generate-source
python scripts\learn_glossary.py check-source
```

`generate-source` parses all confirmed entry blocks, validates the temporary
legacy migration input, compares it for migration reporting, validates the
approved-only JSON v1.0 result, and writes `site/data/glossary.json`.

`check-source` regenerates in memory and fails with a clear stale/manual-edit
message if the tracked production JSON differs. `site/data/glossary.json` is a
generated file and must not be edited manually.

The normal `python scripts\learn_glossary.py generate` command now runs source
generation before page, lookup, catalogue, and backlink generation. Full
Quarto pre-render already calls that command, so the generated JSON is current
before any consumer reads it.

Only confirmed entries and their approved aliases are emitted. Matching legacy
entries and aliases are recorded in the migration report. An exact confirmed
AKA may absorb an exact same-spelling legacy canonical for compatibility
reporting. Any case-only, punctuation-only, whitespace-only, hyphen-only, or
otherwise normalized near-match is ambiguous and fails instead of being
silently accepted.

The temporary migration file exists only until every review-only legacy term has
been promoted into `confirmed-terms.md`, deliberately rejected, or recorded as
an approved alias of a confirmed term. It is not an ongoing editorial source.
Staged and comprehensive workflow files are never read by production
generation.

Confirmed entries use only the confirmed Markdown values. An authored inline
target that names an existing alias slug is canonicalized to that alias's
canonical owner. An inline target that has not been approved remains ordinary
definition text and is listed in the migration report.

Unresolved confirmed related-word labels follow one explicit temporary rule:
they remain term-only, non-clickable related records and are listed in the
migration report. The generator does not use staged terms to resolve them and
does not invent a canonical target. Once a canonical or approved alias enters
the final glossary, regeneration adds its canonical slug.

## Isolated review-subset utility

The production parser can generate an isolated review JSON without writing the
production file:

```powershell
python scripts\glossary_source.py generate-subset `
  --input C:\path\to\review-subset.md `
  --output C:\path\to\review-subset.json
```

The command refuses `site/data/glossary.json`. The accepted Ace, ABT, and
Active Builder compatibility artifacts can be regenerated with the separate,
review-only utility:

```powershell
python scripts\glossary_review_artifacts.py `
  --input-json C:\path\to\review-subset.json `
  --lookup-output C:\path\to\review-lookup.json `
  --entries-output C:\path\to\review-entries.html `
  --preview-output C:\path\to\review-preview.html
```

Neither review command participates in the production build.
Review-subset validation may use the legacy migration inventory to resolve
candidate links, but only the explicitly supplied subset is written to the
review artifact.
