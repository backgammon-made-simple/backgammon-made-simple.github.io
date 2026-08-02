import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

import {
  DEFAULT_MANIFEST,
  runComprehensiveBrowserBaseline
} from "../scripts/testing/ux/browser/comprehensive_quality_browser_check.mjs";

const helperSource = readFileSync(
  new URL(
    "../scripts/testing/ux/browser/release_ui_browser_check.mjs",
    import.meta.url
  ),
  "utf8"
);

assert.equal(DEFAULT_MANIFEST.version, 2);
assert.deepEqual(
  DEFAULT_MANIFEST.viewports.map(({ width, height }) => [width, height]),
  [
    [1440, 900],
    [1280, 800],
    [1024, 768],
    [390, 844],
    [320, 568]
  ]
);
assert.equal(DEFAULT_MANIFEST.baseline_screenshot_route_ids.length, 6);
assert.equal(DEFAULT_MANIFEST.baseline_screenshot_viewport_names.length, 2);
assert.equal(DEFAULT_MANIFEST.failure_screenshot_limit, 30);

const requiredPageIds = [
  "home",
  "learn-index",
  "cube-index",
  "cube-lesson",
  "take-point-lesson",
  "research-index",
  "research-article",
  "engine-benchmark",
  "sage-vs-gnu",
  "analyze",
  "match-predictor",
  "glossary",
  "about",
  "licensing",
  "updates",
  "404"
];
assert.deepEqual(
  DEFAULT_MANIFEST.pages.map((page) => page.id),
  requiredPageIds
);

for (const requiredSourceContract of [
  "accessibilitySnapshot",
  "focusSnapshot",
  "interactWithMobileNavigation",
  "interactWithGlossarySidebar",
  "failure_screenshot_limit",
  "safe_for_automated_remediation",
  "needs_review"
]) {
  assert.ok(helperSource.includes(requiredSourceContract), requiredSourceContract);
}

await assert.rejects(
  runComprehensiveBrowserBaseline({ manifest: { version: 1 } }),
  /manifest version 2/
);

console.log("comprehensive quality browser helper contracts passed");
