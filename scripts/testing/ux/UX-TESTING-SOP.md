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

Using the same fixed server and controller, run
`runRuntimePerformanceBaseline()` from
`../quality/performance/runtime_performance_baseline.mjs`. It performs one
warm-up plus three measured loads on the contract subset at desktop and mobile,
then records medians and glossary interaction timings.

When lesson-analysis changed, also run `runLessonAnalysisBrowserChecks()` from
`browser/lesson_analysis_browser_check.mjs`. It exercises cube paths, nested
disclosures, independent instances, checker candidates, missing values, image
loads, state retention, and overflow at both viewports.

Record helper summaries, failures, console messages, URL, and viewports. If a
browser controller is unavailable, record this phase as `NOT RUN`, never passed.

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
