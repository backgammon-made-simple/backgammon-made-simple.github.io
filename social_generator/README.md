# Backgammon Made Simple Social Cards — Contract v1.1

This package implements the frozen contract v1.1 text-only renderer. It uses deterministic local assets and six typography/composition profiles.

## Live repository integration

This directory is the canonical live implementation. Do not copy it into a second `scripts/social` or `templates/social` tree.

From the repository root, run:

```text
python social_generator/scripts/social/run_social_pipeline.py
```

The Quarto project in `site/_quarto.yml` runs that same pipeline as a pre-render hook. The implementation paths are:

```text
social_generator/scripts/social/
social_generator/templates/social/
social_generator/requirements-social.txt
social_generator/requirements-social.R
```

Do not overwrite the real manifest with the example unless that is intentional:

```text
examples/social-cards.yml
```

## Font location

The renderer supports either the original Google Fonts variable TrueType file:

```text
social_generator/site/assets/social/fonts/SourceSans3-VariableFont_wght.ttf
```

or the two static TrueType files:

```text
social_generator/site/assets/social/fonts/SourceSans3-Regular.ttf
social_generator/site/assets/social/fonts/SourceSans3-SemiBold.ttf
```

The variable file is the simplest option. The capitalization in `SemiBold`
matters on case-sensitive systems.

The transparent S-only logo belongs at:

```text
site/assets/logo.svg
```


## Font and path guarantees

The renderer uses no generic CSS font fallback. Before rendering, it checks
that every visible character in the manifest exists in the pinned local
Source Sans 3 font files. A missing glyph is a fatal error rather than a silent
operating-system font substitution.

The generated output directory and every output path are resolved through
existing symlinks. Their final locations must remain inside the repository.

## Text-only manifest rule

The nine-field schema remains closed. Every record must still include `visual`,
but it must now be:

```yaml
visual: ""
```

For a one-time migration of the generated manifest:

```bash
python social_generator/scripts/social/clear_visuals.py
```

Then update the R content generator so future manifests continue to emit an
empty string.

## Python installation

From the website repository root:

```bash
python -m pip install -r social_generator/requirements-social.txt
python -m playwright install chromium
```

## R installation

The repository integration validator needs the R package `yaml`:

```bash
Rscript social_generator/requirements-social.R
```

## QMD metadata convention

The homepage always maps to `social-default`. Other pages opt into a page-specific card with `social-card: true`; opted-in pages are generated and validated against their image metadata.

Use one of these front-matter slug fields:

```yaml
slug: when-should-you-offer-the-cube
```

The validator also accepts `social-card-slug`, `social_card_slug`,
`social-slug`, and `social_slug`.

The generated image metadata must match the card output:

```yaml
image: /assets/social/generated/social-when-should-you-offer-the-cube.png
```

An opted-in page also declares `social-card-kind` and, when needed, `social-card-category`. Pages with `draft: true` or status `planned`, `draft`, `private`, `archived`, or `unpublished` are excluded.

Pages that do not opt in use the global `social-default` metadata. Section `index.qmd` pages infer their slug from the parent directory when no explicit slug is present.

## Quarto

The accepted entries from `quarto-social-snippet.yml` are integrated into `site/_quarto.yml`.

The pre-render order is:

```text
generate social-cards.yml
validate the manifest and page relationships
render changed social PNGs and validate their dimensions
Quarto renders the site
```

The pipeline performs:

```text
Python contract and browser text-fit validation
R page-to-card and Quarto metadata validation
Python changed-card rendering and PNG post-render checks
```

## Commands

Renderer only:

```bash
python -u social_generator/scripts/social/render_cards.py --validate-only
python -u social_generator/scripts/social/render_cards.py --all
python -u social_generator/scripts/social/render_cards.py --changed
python -u social_generator/scripts/social/render_cards.py --slug social-default
python -u social_generator/scripts/social/render_cards.py --clean-orphans
```

Complete repository pipeline:

```bash
python -u social_generator/scripts/social/run_social_pipeline.py
```

Force all cards through the complete pipeline:

```bash
python -u social_generator/scripts/social/run_social_pipeline.py --all
```

## Card-profile differences

All profiles are text-only:

- `default`: broad site-level statement;
- `github`: concise technical repository framing;
- `section`: curriculum-oriented landing-page composition;
- `article`: largest question-led title treatment;
- `tool`: tighter technical composition;
- `benchmark`: stronger rule and semibold evidence-oriented subtitle.

There are no generated illustrations or decorative background images.

## Planning and handover

See `docs/social-card-v1.1-handover-and-plan.md` for the remaining R/Quarto integration work and the deliberate three-line subtitle rejection policy.
