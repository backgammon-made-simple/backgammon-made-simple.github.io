# Lesson inline glossary metadata

Learn pages use two separate glossary metadata fields.

## `terms`: broad relationships

`terms` is the complete list of canonical glossary concepts substantially covered by a page. It continues to drive:

- glossary-to-lesson backlinks;
- lesson search and term filters;
- lesson and Research relationships;
- existing metadata validation.

Do not reduce `terms` to control inline presentation.

## `highlighted-terms`: inline presentation

`highlighted-terms` is an optional list containing only the canonical slugs that should receive inline glossary markup.

```yaml
terms:
  - take-point
  - doubling-cube
  - pass
  - recube-vigorish-vig

highlighted-terms:
  - take-point
  - doubling-cube
```

The field name is exactly `highlighted-terms`. Its rules are:

- absent or `[]` disables inline highlighting;
- every value must also occur in `terms`;
- only canonical glossary slugs are valid; alias slugs are rejected;
- duplicate or duplicate-normalized values fail validation;
- malformed and unknown slugs fail validation;
- internal processing is sorted for deterministic output.

The generator validates this metadata before a full render. The Learn-only Quarto filter repeats the render-critical checks against the generated glossary lookup.

## Rendering behavior

For each selected canonical concept, the filter considers the canonical term and its approved aliases. It marks only the first safe top-level prose occurrence. Matching is case-insensitive, requires whole words, tolerates punctuation between words, and gives the longest valid phrase priority.

The filter does not descend into:

- headings;
- existing links;
- inline or fenced code;
- mathematics;
- raw HTML;
- image captions;
- navigation, metadata, or generated glossary UI.

The generated link retains the visible lesson wording and stores only the canonical target slug:

```html
<a
  class="bms-inline-glossary"
  href="/learn/glossary/#anchor"
  data-bms-glossary-slug="anchor"
>Holding Point</a>
```

The lesson markup never contains a copied definition. On pointer hover or keyboard focus, `bms-learn.js` loads the generated canonical lookup, resolves `data-bms-glossary-slug`, and displays that record's `short_definition`. Activating the ordinary link navigates to `/learn/glossary/#canonical-slug`.

The generated lookup always supplies `short_definition`. During the legacy JSON migration, an entry without a separately authored short definition receives its canonical full `definition` as the deterministic compatibility value. The lookup also supplies `alias_slugs` for canonical-only metadata validation. Neither compatibility field modifies `site/data/glossary.json`.

If a selected concept has no safe prose occurrence, rendering succeeds with one deterministic warning per canonical slug. The current rollout treats that situation as an authoring warning rather than a build failure.

## Separate from glossary definition links

Glossary-entry `definition_links` are authored inside confirmed glossary definitions and connect glossary entries to one another.

Lesson `highlighted-terms` is page metadata that selects a subset of lesson prose for inline markup. The two features share canonical lookup records but have separate authoring purposes and validation.

## Current rollout boundary

Iteration 03 deliberately transforms only top-level prose paragraphs. Nested prose in lists, block quotes, tables, and other containers is not highlighted. This keeps the exclusion behavior structural and predictable while the authoring convention is evaluated.
