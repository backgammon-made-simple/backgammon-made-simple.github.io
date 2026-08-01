# Unified glossary production source

`glossary/glossary.md` is the only production editorial source. It contains
every published canonical entry, including both `Confirmed` and
`Legacy unconfirmed` entries. Aliases live inside their canonical entry.

The other permanent workflow files have non-production roles:

- `glossary/staged-terms.md` is the review queue;
- `glossary/comprehensive-list-of-terms.md` is the raw vocabulary inbox;
- `glossary/contracts/glossary-contract.md` is the authoritative contract.

Production generation does not read those three files.

## Generation

From the repository root:

```powershell
python scripts\learn_glossary.py generate-source
python scripts\learn_glossary.py check-source
python scripts\learn_glossary.py generate
python scripts\learn_glossary.py validate
```

The generated chain is:

```text
glossary/glossary.md
  -> site/data/glossary.json
  -> site/assets/bms-glossary-lookup.json
  -> site/glossary/_entries.html
```

Generated files are deterministic and must not be edited manually.

## Public and editorial fields

The parser supports the exact entry shape in
`glossary/contracts/glossary-contract.md`, including status, slug, optional
Added date, AKA aliases, short and full definitions, explicit Inline terms,
Related words, Categories, Learning tracks, and optional Usage note, Alias
notes, and Editorial notes.

Status, Alias notes, and Editorial notes stay editorial and are not emitted.
Usage notes are public. `date_added` is emitted only when Added exists; only
dated entries enter the Updates feed, so retained legacy entries do not receive
invented publication dates.

The public compatibility field `category` is emitted only when categories are
non-empty and equals `categories[0]`.

## Validation and matching

Generation validates canonical and alias uniqueness after deterministic
Unicode, case, whitespace, apostrophe, punctuation, and hyphen normalization.
It also validates slugs, definitions, controlled categories, repeated
categories, learning tracks, inline mappings, and canonical targets.

The supplied migration document has 71 valid category lists written before the
global display-order rule. Their editorial order remains untouched in Markdown;
generated JSON canonicalizes all categories to the contract order. Unknown and
repeated categories still fail.

Search data includes canonical names, aliases, short definitions, and full
definitions. Alias matches resolve to their canonical entry. Hover and keyboard
focus use the canonical short definition; the glossary page and term sidebar
show the full definition.

Glossary definitions automatically link canonical terms and aliases using
longest-match-first recognition. Self-links are excluded. Explicit Inline terms
have priority over automatic matches. Resolved related words link to the
canonical fragment; unresolved labels remain plain text.

## Learn and Research metadata

Both page types support:

```yaml
terms:
  - broad relationship slugs

highlighted-terms:
  - explicit inline-highlight slugs
```

Only `highlighted-terms` are marked in prose. Matching accepts canonical names
and aliases, prefers the longest phrase, and marks only the first safe prose
occurrence. The filter excludes headings, links, code, math, raw HTML, captions,
metadata, and navigation.

## Isolated review subsets

The parser can still produce a non-production review file:

```powershell
python scripts\glossary_source.py generate-subset `
  --input C:\path\to\review-subset.md `
  --output C:\path\to\review-subset.json
```

The command refuses to overwrite `site/data/glossary.json` and is not part of
the production build.
