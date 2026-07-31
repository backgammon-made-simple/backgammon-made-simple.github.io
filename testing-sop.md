# Backgammon Made Simple testing SOP

This is the concise release procedure for website, glossary, navigation,
responsive UI, lesson-analysis, SVG-renderer, RSS, and build changes. Choose the
smallest tier that covers the change; use the long tiers before a public release
or after shared JavaScript, CSS, templates, build hooks, or data contracts
change.

## Test tiers

| Tier | Typical time | Use it for |
| --- | ---: | --- |
| Short browserless | 1–5 minutes | Routine edits, fixture/data changes, pre-commit checks |
| Long browserless | 15–45 minutes | Shared UI/build changes and release candidates |
| Short Codex/Chrome | 5–15 minutes | One changed interaction at desktop and mobile widths |
| Long Codex/Chrome | 20–45 minutes | Full representative UI release pass |

Stop and report rather than repeatedly retrying when the same command or method
fails twice. Ask for direction if the combined work is likely to exceed 90
minutes.

## Preconditions

Record the exact state first:

```bash
pwd
git branch --show-current
git rev-parse --short HEAD
git status --short
git diff --stat
```

Required for browserless tests: Git, Python 3.11+, Node.js, and Bash. Long builds
also require Quarto and the project's Python/R dependencies. Browser testing
requires a current `site/_site` and either Codex Browser or the Codex Chrome
plugin.

Never commit generated `site/_site` files, source-adjacent rendered HTML,
screenshots, logs, or temporary reports unless they are explicitly requested.

## Short browserless test

Run from Git Bash, Linux, or a server shell:

```bash
bash testing-scripts/run-browserless-short.sh
```

This checks:

- whitespace and patch integrity with `git diff --check`;
- deterministic scrolling-test fixtures;
- syntax of Learn, continuous-scroll, lesson-analysis, and browser-helper JS;
- Learn filters/search ranking;
- continuous Learn and Research loading;
- cube/checker lesson state logic;
- retained checker identities, candidate mapping, probabilities, SVG presence,
  missing values, malformed data, and missing-asset failure;
- release-check source contracts;
- representative rendered HTML when `site/_site` already exists.

This tier does not render, start a server, or launch a browser.

## Long browserless and local/server full builds

Normal full development gate, with social-card generation skipped:

```bash
bash testing-scripts/run-browserless-long.sh
```

Canonical release build, including the social-card pipeline:

```bash
bash testing-scripts/run-browserless-long.sh --with-social-cards
```

The long runner adds:

- every Python `test_*.py` test;
- a complete Quarto render;
- full rendered glossary validation;
- all-route static checks for internal links, fragments, assets, duplicate IDs,
  raw source, landmarks, and viewport declarations;
- a second retained checker projection/asset-contract check.

The older equivalent UI-oriented runner remains available when a preview-port
check is useful:

```bash
bash scripts/release-ui-check.sh 8766 --render
```

For the cross-repository checker renderer, provide the checkout and R executable:

```bash
BACKGAMMONBOARD_REPO='C:/Users/andre/Documents/backgammonboard' \
RSCRIPT_BIN='C:/Program Files/R/R-4.6.1/bin/Rscript.exe' \
bash testing-scripts/run-browserless-long.sh
```

That optional gate covers ordinary moves, layered arrows, ghost origins, hits to
the bar, entries from the bar, bearing off, selected-result checker state,
unchanged plain rendering, and reversed/custom orientation. For a package
release, additionally run in `backgammonboard`:

```powershell
& 'C:\Program Files\R\R-4.6.1\bin\Rscript.exe' -e "devtools::test('.', reporter='summary'); devtools::check('.', args='--no-manual', cran=FALSE)"
```

## Serving the built site

For normal development, serve the last build immediately while a second process
watches and writes changed pages:

```bash
bash scripts/preview-site.sh 8766
```

Do not start another Quarto render while that watcher is rendering. For a fixed,
read-only release artifact, serve `site/_site` with any static server instead.

## Short Codex Browser or Chrome plugin test

Use Codex Browser for a clean isolated run. Use the Chrome plugin when the test
depends on the user's real Chrome session, extensions, or cache behavior. Test
at `1440 × 1000` and `390 × 844`, then reset the viewport.

- **Codex Browser:** ask Codex to use Browser against the local preview and run
  the short or long checklist below.
- **Chrome plugin:** open the same preview in Chrome, attach that tab to Codex,
  and request the same checklist. Prefer this for final cache, extension, and
  real-browser confirmation.

For a checker-analysis change, inspect only:

`/learn/cube/why-is-25-percent-the-basic-take-point.html`

Verify:

1. The starting SVG loads with nonzero natural dimensions.
2. Each of `8/4`, `13/10 11/10`, and `13/10 8/7` selects exactly one button.
3. Each selection changes the SVG, move, rank, equity, positive equity loss,
   and all supplied win/loss probabilities together.
4. `position_id`, `state_hash`, and `analysis_id` remain unchanged.
5. Missing explanation displays as `Not supplied`.
6. The retained-analysis disclosure opens and restores with correct
   `aria-expanded` state.
7. Keyboard focus is visible and native buttons activate with Enter/Space.
8. Desktop shows the board, arrows, ghost origins, metrics, TOC, and term tools
   without overlap.
9. Mobile buttons wrap, the SVG scales, and the TOC/term drawer opens and closes.
10. Page-level horizontal overflow is zero and the console has no errors.

For cube-lesson changes, also exercise Double/Roll, the responder view,
Pass/Take, and nested analysis disclosures on:

`/learn/cube/what-the-cube-is-asking.html`

The reusable browser logic is in `scripts/lesson_analysis_browser_check.mjs`.
Its Node source-contract test is
`tests/test_lesson_analysis_browser_check.mjs`.

## Long Codex Browser or Chrome plugin test

Start with a clean long browserless build and a fixed local server. Then run the
scripted browser procedure in `scripts/release_ui_browser_check.mjs`, using
`scripts/ui_release_manifest.json` as the authoritative route and viewport list.

The long pass covers:

- homepage regression only;
- Learn and Cube indexes, filter disclosure, metadata-first search, body-result
  fallback, title wrapping, and text width;
- Learn lesson track, left lesson index, right TOC, term search, Back to top,
  scroll-direction hiding/restoring, and continuous lesson loading;
- Research TOC, categories/tags rail, term search, and continuous articles;
- glossary full definitions, aliases, related-term links, hover/click behavior,
  search, clear, and absence of the Learn sidebar;
- rich/nested SVG disclosures, long labels, long text, wide tables, anchor
  navigation, and generated scrolling edge fixtures;
- Analyzer, About, Engine Benchmark, navbar routes, and ordinary-page isolation;
- duplicate IDs, console errors, broken resources, overlap, clipping, keyboard
  focus, and horizontal overflow at both viewports.

After automation, do a five-minute visual pass:

1. Scroll a Learn lesson from top to bottom and back up; observe both sidebars,
   active TOC state, Term Search, and Back to top.
2. Repeat on one Research article and confirm continuous loading preserves the
   TOC and unique anchors.
3. Open the mobile TOC/term drawer, use one anchor and one glossary lookup, then
   close it.
4. Select all checker candidates and one complete cube answer path.
5. Click the principal navbar routes once.

Take screenshots only for a real defect. The older detailed UI matrix remains in
`docs/ui-release-testing.md`.

## Specialized and post-deploy gates

Run these only when their subsystem changed:

```powershell
# Social-card manifest, generation, and dimensions
python social_generator/scripts/social/run_social_pipeline.py

# Metadata and keyboard smoke test against a served full build
python social_generator/scripts/social/check_rendered_site.py http://127.0.0.1:8766/

# Accepted Sage-vs-GNU website release data
Rscript scripts/engine-benchmark/sage-vs-gnu-stage1/validate_release.R
```

Regenerate real checker assets only when the retained JSON or renderer changes:

```powershell
& 'C:\Program Files\R\R-4.6.1\bin\Rscript.exe' scripts/render_real_checker_assets.R fixtures/real-analysis/checker-sage-gnu-disagreement-001 site/data/checker-sage-gnu-disagreement-001.json C:/Users/andre/Documents/backgammonboard site/assets/positions/real-analysis/checker-sage-gnu-disagreement-001
```

The generator must fail if a rendered candidate differs from the authoritative
resulting checker arrangement. After deployment, repeat the short browser pass
on the public URL and confirm the HTML, JSON, and four checker SVG requests all
return successfully. Do not use the post-deploy smoke test as a substitute for
the pre-deploy long gate.

## Tests accumulated during this implementation

The following have been run successfully during the sidebar, scrolling,
glossary, search, lesson-analysis, and renderer work:

- `git diff --check`, JS syntax checks, Bash syntax checks, and branch/status
  preflight checks;
- focused and complete Python unit suites for glossary Markdown/YAML migration,
  aliases, highlighting, lesson search/filtering, inline definitions, RSS data,
  scrolling fixtures, lesson analysis, and static release checks;
- Node tests for Learn filters, continuous Learn/Research loading, sidebar
  behavior, release-browser helpers, cube interactions, and checker selection;
- focused Quarto page renders and complete local site builds;
- rendered-site link, fragment, asset, duplicate-ID, raw-HTML, landmark,
  overflow, and glossary audits;
- desktop/mobile browser checks of Learn, Research, Glossary, Analyzer, About,
  indexes, continuous loading, TOC controls, Term Search, Back to top, navbar,
  nested disclosures, and console output;
- real checker projection/manifest identity validation and missing-data/asset
  failure tests;
- backgammonboard focused tests, full test suite, five-case SVG gallery, and
  `R CMD check` with zero errors, warnings, or notes;
- checker browser verification at both viewports: correct top-three SVG/metric
  mapping, visible focus, retained disclosure, mobile drawer, zero overflow,
  successful image loading, and a clean console.

## Pass/fail classification

- **Blocking:** page/build cannot load, initialization exception, broken local
  asset/link, horizontal overflow, unusable core control, duplicate IDs after
  continuous loading, or candidate/board mismatch.
- **Important:** page jumps, wrong active navigation, visible overlap/clipping,
  desktop control on mobile, inaccessible keyboard operation, or stale metrics.
- **Minor:** spacing or presentation inconsistency without functional impact.
- **Passed:** deterministic checks succeed and the representative UI behaves as
  specified at both viewports.

Do not merge or publish with Blocking findings. Fix in-scope Important findings;
otherwise document them and ask for approval.

## Release report template

Report:

1. branch and exact commit;
2. dirty/clean starting state;
3. tier and commands run;
4. render mode and social-card mode;
5. pages and viewports tested;
6. passed check/test counts;
7. Blocking, Important, Minor, and Passed findings;
8. console or network errors;
9. screenshots taken only for defects;
10. changed/generated/untracked files;
11. recommendation: merge, fix, or request direction.
