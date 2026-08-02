# UX testing SOP

## Prepare

Run the clean phase of `bash scripts/testing/comprehensive-quality.sh` for a
baseline, then serve the fixed output at `http://127.0.0.1:8766/`. The canonical
matrix is `1440 x 900`, `1280 x 800`, `1024 x 768`, `390 x 844`, and
`320 x 568`; reset the viewport afterward.

## Automated browser phase

With the supported browser controller, run `runComprehensiveBrowserBaseline()`
from `browser/comprehensive_quality_browser_check.mjs`. It reads
`browser/ui_release_manifest.json` and covers routes, landmarks, overflow,
clipped controls, fixed/sticky overlap, duplicate IDs, headings, labels, alt
text, sampled focus behavior, navigation, Learn filters/rails, continuous
loading, glossary flows, iframe containers, console exceptions, and responsive
behavior. Write its JSON result and bounded screenshots to the baseline output
directory.

The canonical controller calls are:

```js
const browserReport = await runComprehensiveBrowserBaseline({
  tab,
  viewport,
  baseUrl: "http://127.0.0.1:8766/",
  screenshotDir: "<OUTPUT_DIR>/screenshots/browser"
});

const performanceReport = await runRuntimePerformanceBaseline({
  tab,
  viewport,
  baseUrl: "http://127.0.0.1:8766/"
});
```

Write the returned JSON to
`<OUTPUT_DIR>/browser/browser-baseline.json` and
`<OUTPUT_DIR>/performance/runtime-performance.json` respectively. Do not infer
a passed result from the function returning; interpret each report's component
status and findings.

Controllers that invalidate selector evaluation after a second explicit
navigation must use `runComprehensiveBrowserBaselineWithIsolation()` from the
same module. It applies a fresh controller page to each explicit navigation
while preserving the manifest, checks, screenshots, and report schema.

### Deterministic logical runs

The browser bridge has a five-minute control-call ceiling. One logical baseline
therefore consists of two sequential 40-context shards against the same commit,
rendered output, server, controller, route manifest, and viewport manifest.
Partition the 16 routes deterministically into two eight-route sets (the
established process uses alternating manifest indexes); each shard runs all
five viewports. Do not run shards concurrently.

Merge the two shard reports without dropping findings or contexts. Recompute
the stability summary and root-cause groups from the combined findings, retain
all 80 `coverage.executedPageContexts`, and record the shard limitation. The
merged `coverage.complete` must be true. Retain every executed assertion and
the complete `checksByContext` map. Repeated logical runs must have identical
route coverage, viewport coverage, aggregate checks, and per-context checks.
An equal total does not excuse a context-level difference.

Write each merged logical run to a distinct ignored evidence directory. After
at least two unchanged runs (three for a retention baseline), compare them with:

```bash
node scripts/testing/quality/browser/compare_browser_baselines.mjs \
  <RUN_1_BROWSER_JSON> <RUN_2_BROWSER_JSON> <RUN_3_BROWSER_JSON> \
  --output <BROWSER_COMPARISON_JSON>
```

Accept only the reports named in the comparison. Label partial, diagnostic,
and pre-contract reports as superseded rather than treating the newest file as
implicitly accepted.

### Continuous-loading state

Learn and Research checks must start from a freshly loaded canonical route,
not from state left by a preceding interaction. Before product assertions,
record the initial document/route identity and wait for the initial marker,
ready completion sentinel, and unloaded append state.

Drive the documented scroll or trigger until the expected state is reached,
then record and assert the appended-page count, identities and order,
completion sentinel, loaded-page order, namespaced container IDs, scroll/trigger
state, final URL, and available history evidence. Record a bounded timeout
reason when the expected state is not reached. Never suppress a real duplicate
ID to make repeated results agree.

### Keyboard-focus procedure

Exercise actual keyboard traversal before evaluating focus. Seed focus with a
keyboard action, traverse with Tab/Shift+Tab, and record the focused elements
in order. Check visible focus indication, meaningful order, obvious traps, skip
links, mobile navigation, drawers/modals where present, and focus return after
closing an interaction.

If no focusable element was exercised, the focus phase is incomplete or failed;
it must never pass because focus remained on `body` or no traversal occurred.

Using the same fixed server and controller, run
`runRuntimePerformanceBaseline()` from
`../quality/performance/runtime_performance_baseline.mjs`. It performs one
warm-up plus three measured loads on the contract subset at desktop and mobile,
then records medians and glossary interaction timings.

Use `runRuntimePerformanceBaselineWithIsolation()` when the controller needs
the same fresh-page navigation isolation. The performance contract, measured
loads, medians, interaction names, and report schema remain unchanged.

When lesson-analysis changed, also run `runLessonAnalysisBrowserChecks()` from
`browser/lesson_analysis_browser_check.mjs`. It exercises cube paths, nested
disclosures, independent instances, checker candidates, missing values, image
loads, state retention, and overflow at both viewports.

Record helper summaries, failures, console messages, URL, and viewports. If a
browser controller is unavailable, record this phase as `NOT RUN`, never passed.

The browser report may finish with `FAIL` because stable product defects were
observed. Treat that as completed product evidence, not an infrastructure
failure. A `test-infrastructure` classification means the evidence itself is
untrustworthy and blocks retention. Keep browser, runtime-performance, build,
static, and human statuses separate.

## Human phase

Use [human-instructions/quick.md](human-instructions/quick.md) during
development or [human-instructions/comprehensive.md](human-instructions/comprehensive.md)
before release. Section checklists provide focused coverage. Record each
section as passed, failed, or `NOT RUN`; take screenshots only for defects.

Blocking findings include a page/build that cannot load, initialization errors,
broken local routes/assets, wrong checker mapping, duplicate IDs, horizontal
page overflow, or an unusable core control. Important findings include jumps,
wrong active navigation, overlap/clipping, desktop controls on mobile,
inaccessible keyboard operation, or stale metrics. Do not release with blocking
findings.
