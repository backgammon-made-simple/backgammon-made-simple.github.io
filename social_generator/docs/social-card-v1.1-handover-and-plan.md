# Social Card v1.1 Handover and Remaining Integration Plan

## Completed in the renderer

The Python/Chromium renderer now implements the text-only v1.1 production
decision:

- closed nine-field manifest validation;
- exact kind dimensions;
- deterministic filenames;
- output-path and generated-directory symlink containment;
- local Source Sans 3 TrueType loading;
- local-font glyph coverage checks;
- no generic or operating-system font fallback;
- blocked HTTP and HTTPS requests;
- six typography/composition profiles;
- predefined title and subtitle size ladders;
- deterministic Chromium screenshots;
- post-render PNG readability and dimension checks;
- incremental rendering hashes;
- explicit orphan cleanup.

The renderer version is:

```text
1.1.0-text-only
```

## Work deliberately left for Left Brain / R / Quarto integration

### 1. Install the repository integration pipeline

The package supplies:

```text
scripts/social/validate_social_integration.R
scripts/social/run_social_pipeline.py
quarto-social-snippet.yml
```

These files do not prove that the real website repository is integrated. Left
Brain must merge the snippet into the existing `_quarto.yml`, preserve any
existing pre-render commands, and confirm this order:

```text
validate content metadata
generate QMD
generate social-cards.yml
run social-card contract and repository validation
render changed PNGs
run post-render checks
Quarto render
```

Acceptance requires the integration validator to pass against the real QMD
tree and the real `_quarto.yml`.

### 2. Keep the existing R generator as editorial owner

This package does not replace the website's R content generator. The existing
R layer must continue to own:

- card eligibility;
- publication status;
- page slugs;
- titles and descriptions;
- category derivation;
- social-title and social-subtitle fallbacks;
- QMD image metadata;
- generation of `site/assets/social/social-cards.yml`.

For contract v1.1, every generated card record must resolve to:

```yaml
visual: ""
```

Left Brain needs the location and command for the existing R generator when
performing the final repository integration.

## Deliberately retained stricter rejection rule

The renderer retains an implementation-level maximum of **three rendered
subtitle lines**.

A subtitle that would require four or more lines is rejected even when it might
physically fit inside the remaining card area. The failure appears as:

```text
Text fit failed for '<slug>': title/subtitle combination does not fit
```

This rule is intentionally stricter than the frozen v1.1 contract. It protects
social-preview readability and is not a renderer bug. Marty must shorten the
subtitle or revise the approved wording when this rejection occurs.

Titles are also limited to three rendered lines.

## Installation plan

1. Copy the replacement files into the website repository.
2. Put the pinned Source Sans 3 TrueType font files in
   `site/assets/social/fonts/`.
3. Ensure every manifest record has `visual: ""`.
4. Run the Python renderer validation.
5. Render and visually inspect one card from each of the six profiles.
6. Hand the R/Quarto integration work to Left Brain.
7. Run the complete repository pipeline.
8. Commit the manifest, PNGs, renderer files, dependency pins, and handover.

## Immediate renderer acceptance commands

```bash
python -m pip install -r requirements-social.txt
python -m playwright install chromium
python -u scripts/social/render_cards.py --validate-only
python -u scripts/social/render_cards.py --all
```

## Information needed by Left Brain later

No additional information is required to finish the standalone renderer.

For final R/Quarto integration, Left Brain will need:

- the actual R generator script or command;
- the current `_quarto.yml` pre-render sequence;
- any QMD pages intentionally exempt from social cards;
- the authoritative mapping for homepage and section slugs.
