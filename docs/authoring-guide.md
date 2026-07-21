---

# Authoring Guide

This private guide explains where the site lives, how the navigation is wired, and how to copy the page components Marty wants to keep. The examples here are fixture-driven and intentionally editable.

## Where Things Live

| Area | Path | Notes |
|---|---|---|
| Homepage | `site/index.qmd` | Public landing page and homepage playground |
| Learn | `site/learn/index.qmd` | Curriculum landing page and lesson patterns |
| Analyze | `site/analyze/index.qmd` | Static analyzer entry page and Shiny companion |
| Sage vs GNU | `site/engine-benchmark/sage-vs-gnu-stage1/index.qmd` | Study overview and status page |
| Blog | `site/blog/index.qmd` | Chronological listing that discovers `site/posts/**` |
| About | `site/about.qmd` | Project purpose and site-level identity |
| Posts | `site/posts/**/index.qmd` | Individual blog entries |
| Shared CSS | `site/assets/` | Layout, color, and component styling |
| Templates | `site/templates/` | Copyable page skeletons |

## Navigation

Edit `site/_quarto.yml` to change the navbar. The current public navigation is:

`Learn | Analyze | Sage vs GNU | Blog | About | Search`

`Practice` and `Positions` stay out of the Phase 1 navbar. The old `Articles` label is replaced by `Blog`.

## Learn Sidebar

The Learn sidebar also lives in `site/_quarto.yml`. It is the place to reorder lessons, move sections, and expose or hide learning tracks.

## Blog Discovery

The blog listing is driven by `listing:` metadata on `site/blog/index.qmd`, which points at `site/posts/**/*.qmd`. Add or remove posts by creating or deleting files under `site/posts/`.

## Recently Added

The homepage `Recently Added` section is hand-curated. Update it when a new lesson, post, or status page should be surfaced.

## Copying A Component

Each primary page has a `Component Playground` section. Marty can copy a rendered component and then copy the code source directly below it. The main pages that need this treatment are:

- Homepage
- Learn
- Analyze
- Sage vs GNU
- Blog
- About

## Removing Playground Sections

Before public release, search for `Component Playground` and delete or rewrite every section under that boundary. The visible boundary is deliberate so the private material is easy to remove.

## Render And Preview

Render the full site from `site/` with:

```bash
quarto render
```

Preview one page by rendering the page file directly, for example:

```bash
quarto render learn/index.qmd
```

## Shiny

Run the analyzer app from `shiny/position-dashboard/` with the local R environment. The site and Shiny app are separate, and the Shiny app still keeps worker-backed polling unwired until the contract is finalized next week.

## Generated Directories

Do not edit `_site/`, rendered HTML output, or other generated artifacts. Use the source files under `site/` instead.

## References

This guide uses fixture citation examples only, consistent with the private playground approach [@bms-fixture-methodology].
:::::

