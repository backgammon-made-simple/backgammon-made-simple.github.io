# UX testing SOP

## Prepare

Run `bash scripts/testing/comprehensive.sh` for a release candidate, then serve
the fixed output at `http://127.0.0.1:8766/`. Use desktop `1440 x 1000` and
mobile `390 x 844`; reset the viewport afterward.

## Automated browser phase

With Codex Browser or an attached Chrome session, run
`runReleaseUiChecks()` from `browser/release_ui_browser_check.mjs`. It reads
`browser/ui_release_manifest.json` and covers routes, landmarks, overflow,
duplicate IDs, navigation, Learn filters/rails, continuous loading, glossary,
worked positions, console exceptions, and responsive behavior.

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
