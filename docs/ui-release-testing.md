# UI release testing

This is the standard bounded release procedure for new Backgammon Made Simple
UI features. It combines deterministic source tests, a rendered-site audit,
scripted desktop/mobile browser checks, and a short human sanity pass.

The target duration is 20–45 minutes. Stop and ask for direction if the work
will exceed 90 minutes, requires testing every content page, or uncovers a
change outside the UI feature's intended scope.

## Release gate

### 1. Pre-flight

From the repository root, record:

```bash
pwd
git branch --show-current
git rev-parse --short HEAD
git status --short
git diff --stat
```

Do not discard an intentionally dirty working tree. Identify generated output
before staging. In particular, never commit:

- anything under `site/_site`;
- rendered `.html` files beside `.qmd` lesson sources;
- a source-tree `site/site_libs` directory;
- screenshots, logs, or test reports unless they are requested artifacts.

### 2. Run the automated source and render gate

Use the full release form:

```bash
bash scripts/release-ui-check.sh 8766 --render
```

For a fast iteration against an already current render:

```bash
bash scripts/release-ui-check.sh 8766 --representative-only
```

The script runs:

- `git diff --check`;
- deterministic scrolling-fixture validation;
- JavaScript syntax and focused JavaScript tests;
- the complete Python test suite;
- an optional full Quarto render with social cards skipped;
- rendered glossary validation;
- internal-link, fragment, asset, duplicate-ID, raw-source, landmark, and
  viewport checks;
- a local-preview availability check.

### 3. Start the preview

If it is not already running:

```bash
bash scripts/preview-site.sh 8766
```

The preview serves the last render immediately while Quarto writes changed
pages in the background. Do not run another Quarto render at the same time.

### 4. Run the scripted browser phase

Use Codex Browser to run
`scripts/release_ui_browser_check.mjs` against
`http://127.0.0.1:8766/`. The helper reads
`scripts/ui_release_manifest.json` and covers both `1440 × 1000` desktop and
`390 × 844` mobile viewports.

The browser phase must:

- visit every manifest route;
- confirm one main landmark and at least one H1;
- detect page-level horizontal overflow before and after interactions;
- scroll to the middle and bottom;
- use Back to top when available;
- detect duplicate IDs after continuous loading;
- expand, collapse, and restore Learn filters;
- search and clear the Learn catalogue;
- independently toggle the desktop lesson track and TOC;
- open and close Look Up a Term without moving the reading position;
- open both SVG worked-position disclosures and use the Take choice;
- exercise long text, long button labels, wide tables, anchors, nested details,
  and responsive SVGs on the generated edge pages;
- search and clear the glossary;
- click from About to Learn and then to the Cube track;
- report obvious console exceptions;
- reset the viewport when finished.

The manifest deliberately includes the homepage for regression detection, but
the edge fixtures are confined to generated non-home pages:

- `/learn/scrolling-test/start-here/lesson-01.html`;
- `/learn/scrolling-test/doubling-cube/lesson-03.html`;
- `/learn/scrolling-test/opening-play/lesson-01.html`.

The rich nested SVG fixture is also checked on:

- `/learn/cube/what-the-cube-is-asking.html`;
- `/learn/scrolling-test/doubling-cube/lesson-01.html`.

### 5. Five-minute human sanity pass

Use only enough manual clicking to confirm what automation can miss:

1. On desktop, open the cube lesson, scroll through the worked position, and
   watch the active TOC state as another lesson loads.
2. Collapse and restore the lesson track and TOC independently.
3. Open and close Look Up a Term at mid-page and confirm the page does not jump.
4. On mobile, repeat the worked-position and edge-fixture interactions and
   swipe the wide comparison table horizontally.
5. Click the main navbar routes once and confirm there is no overlap, clipped
   text, or unusable control.

Take screenshots only for an actual visual defect.

## Coverage matrix

| Surface | Representative pages | Primary risks |
|---|---|---|
| Homepage | `/` | Unintended global regression only |
| Learn indexes | `/learn/`, `/learn/cube/` | Narrow text, filters, wrapping |
| Learn lesson | Cube lesson | Independent rail controls, lookup, SVG disclosure |
| Continuous Learn | Three generated edge fixtures | Appending, rewritten IDs, active TOC, overflow |
| Research | What We Are Building | Desktop TOC and lookup |
| Glossary | `/learn/glossary/` | Full definitions, search, clear, anchors |
| Ordinary pages | Analyze, About, Engine Benchmark | Global layout and navigation regression |

## Pass and fail rules

Blocking:

- a representative page cannot load;
- a browser exception prevents initialization;
- page-level horizontal overflow at either viewport;
- a core control cannot be reached or restored;
- continuous loading creates duplicate IDs or loses the TOC;
- an internal link, fragment, or local asset is broken.

Important:

- opening a control moves the reading position;
- active navigation becomes incorrect;
- visible controls overlap or clip;
- mobile receives desktop-only controls.

Minor:

- small spacing inconsistencies;
- non-blocking console noise with a documented external cause.

Do not merge or publish with Blocking findings. Fix Important findings when
they are in scope; otherwise record and obtain approval. Minor findings may be
deferred with a written note.

## Reporting template

Report:

1. branch and tested commit;
2. render command and result;
3. pages and viewports tested;
4. source, static, and browser check counts;
5. Blocking, Important, Minor, and Passed findings;
6. console errors;
7. screenshots or reports created;
8. files changed to fix test findings;
9. remaining generated or untracked artifacts;
10. recommendation: merge, fix, or ask for direction.
