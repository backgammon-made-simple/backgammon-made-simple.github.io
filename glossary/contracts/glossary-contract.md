# BMS glossary contract

## Permanent repository structure

```text
glossary/
  glossary.md
  staged-terms.md
  comprehensive-list-of-terms.md
  contracts/
    glossary-contract.md
```

These are the only permanent editorial workflow files.

Generated website files may exist elsewhere, but they are build outputs and are not editorial sources.

## File roles

### `glossary/glossary.md`

The only production source of truth.

It contains every published canonical entry, including retained legacy entries. Each entry is marked `Confirmed` or `Legacy unconfirmed`.

The website build reads only this file.

Aliases never become separate canonical entries.

### `glossary/staged-terms.md`

The alphabetical mobile and car review queue.

It does not feed the website build.

A completed term is updated in `glossary.md` and removed from staging during the at-home reconciliation.

### `glossary/comprehensive-list-of-terms.md`

The raw vocabulary inbox.

It may contain duplicates, spelling variants, aliases, unresolved ideas, and research candidates.

It does not feed the website build.

### `glossary/contracts/glossary-contract.md`

The permanent authoring, taxonomy, page behaviour, build, and validation contract.

It does not feed the website build.

## Canonical entry format

```markdown
# Canonical Term

**Status:** Confirmed

**Slug:** `canonical-slug`

## AKA

- Approved Alias

## Short definition

One concise definition used for hover and keyboard focus.

## Full definition

The complete public definition.

## Inline terms

- "visible phrase" -> `canonical-target-slug`

## Related words

- Related Canonical Term

## Categories

- Checker Play
- Game Plans & Position Types

## Learning tracks

- Checker Play
```

Optional sections include `Added`, `Usage note`, `Alias notes`, and `Editorial notes`.

`AKA`, `Inline terms`, `Related words`, `Categories`, and `Learning tracks` may contain `None`.

## Allowed categories

Categories describe what a concept is. A canonical entry may have zero or more.

1. Checker Play
2. Cube Action
3. Match Score
4. Race & Bearoff
5. Game Plans & Position Types
6. Board, Equipment & Notation
7. Rules & Procedures
8. Analysis & Probability
9. Tournaments & Community
10. Chouette & Money Play
11. Variants & History
12. Software & Engines
13. Slang & Expressions

Aliases inherit their canonical entry's categories.

Category order follows the list above.

Learning tracks remain a separate teaching and curriculum relationship.

## Daily workflow

### Morning

Upload:

```text
glossary/glossary.md
glossary/staged-terms.md
glossary/comprehensive-list-of-terms.md
```

The next term comes from the first unresolved staged entry, never from conversation memory.

Confirmed entries are locked unless explicitly reopened.

### Mobile or car session

Finalize only:

- canonical wording when needed;
- obvious aliases when they arise;
- short definition;
- full definition.

Other ideas may be mentioned naturally without interrupting the definition review.

### At-home reconciliation

Once per day:

1. upload the current three workflow files;
2. identify completed, partial, alias, and newly mentioned terms;
3. review suggested categories and related terms;
4. update `glossary.md`;
5. remove completed staged sections;
6. append new raw vocabulary to the comprehensive list;
7. run validation and generation once.

## Search contract

All glossary search surfaces index:

- canonical term;
- every approved alias;
- short definition;
- full definition.

Searching an alias returns the canonical entry, not a separate alias result.

Normalization must handle case, whitespace, apostrophes, punctuation, and hyphens deterministically.

## Hover contract

Hover and keyboard focus always show:

1. canonical term;
2. canonical short definition;
3. `Click for full definition`.

Inline markup stores only the canonical target slug.

An alias uses its canonical entry's short definition.

## Learn and Research contract

Both page types support:

```yaml
terms:
  - broad glossary relationships

highlighted-terms:
  - explicit inline-highlight subset
```

Rules:

- `terms` controls search, backlinks, and relationships;
- only `highlighted-terms` receive inline markup;
- canonical terms and approved aliases may match prose;
- the longest valid phrase wins;
- only the first safe prose occurrence is highlighted;
- headings, existing links, code, mathematics, raw HTML, captions, metadata, and navigation are excluded;
- hover and focus show the canonical short definition;
- click opens the canonical full definition in the existing sidebar.

## Glossary page contract

The glossary page displays full definitions.

Inside definitions:

- canonical terms and aliases are matched automatically;
- the longest valid phrase wins;
- visible wording is preserved;
- self-links are prevented;
- explicit `Inline terms` override or supplement automatic matching;
- hover and focus show the canonical short definition;
- click opens the canonical full definition in the sidebar.

Related words are separate from inline definition links.

Clicking a resolved related word:

1. resolves the canonical slug;
2. clears incompatible search or category filters if needed;
3. reveals and expands the target entry;
4. scrolls to it;
5. updates the URL fragment;
6. preserves keyboard focus.

Unresolved related labels remain plain text.

## Sidebar contract

A canonical slug can open the existing sidebar directly.

The sidebar displays:

- canonical term;
- aliases;
- short definition;
- full definition;
- categories;
- resolved related terms;
- a link to the canonical glossary entry.

It must be keyboard accessible and usable on mobile.

## Build contract

The production build reads only:

```text
glossary/glossary.md
```

It validates and generates:

```text
site/data/glossary.json
site/assets/bms-glossary-lookup.json
generated glossary-page HTML
```

Generated files are deterministic and must not be edited manually.

`staged-terms.md` and `comprehensive-list-of-terms.md` must never be production inputs.

## Required validation

The build fails clearly for:

- duplicate canonical slugs;
- duplicate canonical normalized terms;
- alias collisions;
- aliases that duplicate another canonical term;
- unknown categories;
- repeated categories;
- categories in the wrong order;
- broken explicit inline targets;
- ambiguous explicit inline mappings;
- missing short or full definitions;
- staged or comprehensive files being used as production input;
- generated source drift.

Tests must cover:

- zero, one, and multiple categories;
- alias search;
- canonical hover text;
- sidebar full-definition opening;
- longest-match behaviour;
- explicit inline overrides;
- Learn highlighted terms;
- Research highlighted terms;
- related-term navigation;
- deterministic generated output.
