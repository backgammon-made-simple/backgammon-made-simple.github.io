# UI release testing moved

Use the canonical UX SOP at `scripts/testing/ux/UX-TESTING-SOP.md` and its
browser helpers and human instructions. The source/render gate is
`scripts/testing/build/release-ui-check.sh` and a complete render uses
`site/_site`; stop if the work is likely to exceed 90 minutes.

Compatibility paths remain available: `scripts/release-ui-check.sh`,
`scripts/release_ui_browser_check.mjs`, and
`scripts/ui_release_manifest.json`.
