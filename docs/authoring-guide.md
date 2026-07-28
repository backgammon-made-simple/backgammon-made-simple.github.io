---

# Authoring Guide

This private guide explains where the site lives, how the navigation is wired, and how to copy the page components Marty wants to keep. The examples here are fixture-driven and intentionally editable.

## Where Things Live

| Area | Path | Notes |
|---|---|---|
| Homepage | `site/index.qmd` | Public landing page and homepage playground |
| Learn | `site/learn/index.qmd` | Curriculum landing page and lesson patterns |
| Glossary | `site/learn/glossary/index.qmd` | One searchable page containing every canonical term |
| Custom 404 | `site/404.qmd` | Root not-found page and recovery links |
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

## Learn Catalogue

The Learn index catalogue is a searchable view of the Learn sidebar, not a
second curriculum definition. Its groups, order, and parent/child hierarchy
come from the `learn` sidebar in `site/_quarto.yml`; titles, descriptions,
difficulties, and learning tracks come from each lesson's front matter. Add a
lesson to that sidebar and run the generator to update
`site/learn/_lesson-catalogue.html`.

## Learn Lesson Taxonomy

Every file under `site/learn/` that represents a lesson must declare `categories`, `tags`, and `terms`.

Allowed difficulty categories:

- `Beginner`
- `Intermediate`
- `Advanced`

Allowed learning-track tags:

- `Doubling Cube`
- `Checker Play`
- `Opening Play`
- `Match Play`
- `Endgames`
- `Engines and Analysis`

Use YAML lists even when selecting one value. Multiple difficulties or tracks mean the lesson is appropriate to each selected value. `terms` must contain canonical glossary slugs only; never use an alias slug. Related glossary links are generated only from this explicit metadata.

A complete lesson header looks like:

```yaml
---
title: "Why Is 25% the Basic Take Point When a Double Is Offered?"
description: "Learn the simplified comparison between taking and passing."
sidebar: learn
categories:
  - Beginner
  - Intermediate
tags:
  - Doubling Cube
terms:
  - take-point
  - equity
body-classes: bms-learn-article
---
```

The generated canonical-slug and stable-anchor reference is [learn-glossary-terms.md](learn-glossary-terms.md). Regenerate the Learn catalogue, glossary entries fragment, and that authoring reference with:

```powershell
python scripts/learn_glossary.py generate
python scripts/learn_glossary.py validate
```

Do not add glossary relationships by scanning lesson prose. A keyword scan may be used as an authoring warning, but the public relationship must remain explicit in `terms`.

Cube lessons also require one unique positive `cube-order` value. That metadata
is the authoritative automatic sequence for `/learn/cube/`; keep the Learn
sidebar as a validated mirror of the same order. Landing-page numbers are
generated from the resulting sequence and never belong in lesson titles.

## Single-Page Glossary

The glossary has one public route:

```text
/learn/glossary/
```

Do not create a directory or page for an individual term. Every canonical term
is an expandable entry in the initial HTML on the glossary page. Link to a term
with its stable canonical anchor:

```text
/learn/glossary/#prime
/learn/glossary/#take-point
```

Use canonical slugs in Learn and Research `terms` metadata. Aliases remain
inside their canonical data entry and search resolves them to the canonical
anchor; aliases never receive separate pages, redirects, or visible duplicate
entries. Related Learn and Research content is driven only by explicit
canonical `terms` metadata.

`site/404.qmd` is the source for the root `404.html` page. Keep its recovery
links to Home, Learn, Backgammon Glossary, and Research. It must
remain a normal content page without redirect code.

## Blog Discovery

The blog listing is driven by `listing:` metadata on `site/blog/index.qmd`, which points at `site/posts/**/*.qmd`. Add or remove posts by creating or deleting files under `site/posts/`.

## Updates RSS

`site/updates/index.qmd` produces the combined `/updates/index.xml` feed. An
eligible Learn article, Research article, study, or benchmark report must live
under its public section, have a real ISO publication `date`, and explicitly
set `published: true`. The feed sorts those sources in reverse chronological
order. Do not mark landings, templates, drafts, hidden or planned pages, or
private fixture posts as published feed items.

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

