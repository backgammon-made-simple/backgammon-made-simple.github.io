# Development layout

This directory reserves a clear home for future developer workflows. Existing
development and release scripts remain in `scripts/`, including
`preview-site.sh`, `bms-build-and-publish.sh`, and Windows helper scripts.

Target layout: `scripts/dev/preview/`, `scripts/dev/build/`, and
`scripts/dev/release/`. Do not relocate an active script until its callers,
documentation, and release checks are migrated in one scoped change.
