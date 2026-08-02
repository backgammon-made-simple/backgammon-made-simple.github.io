import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

import {
  DEFAULT_MANIFEST,
  runComprehensiveBrowserBaseline,
  runComprehensiveBrowserBaselineWithIsolation
} from "../scripts/testing/ux/browser/comprehensive_quality_browser_check.mjs";
import {
  EXPECTED_CONTINUOUS_APPEND_COUNT,
  continuousConfigForPage
} from "../scripts/testing/ux/browser/release_ui_browser_check.mjs";

const helperSource = readFileSync(
  new URL(
    "../scripts/testing/ux/browser/release_ui_browser_check.mjs",
    import.meta.url
  ),
  "utf8"
);
const findingSource = readFileSync(
  new URL(
    "../scripts/testing/quality/browser/finding_stability.mjs",
    import.meta.url
  ),
  "utf8"
);
const browserContractSource = `${helperSource}\n${findingSource}`;

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
assert.equal(EXPECTED_CONTINUOUS_APPEND_COUNT, 1);
assert.deepEqual(continuousConfigForPage({ kind: "learn-lesson" }), {
  markerSelector: ".bms-learn-scroll-lesson-marker",
  routeAttribute: "data-bms-learn-scroll-lesson-route",
  sentinelSelector: ".bms-learn-scroll-sentinel",
  endSelector: "[data-bms-learn-scroll-end]",
  namespace: "bms-learn-scroll-"
});
assert.equal(continuousConfigForPage({ kind: "ordinary" }), null);

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
  "locator(\":focus\")",
  "pressFocused(\"Tab\")",
  "focusTraversal",
  "keyboard traversal incomplete",
  "mobileNavigation",
  "mobileDrawer",
  "skipLink",
  "interactWithMobileNavigation",
  "interactWithGlossarySidebar",
  "failure_screenshot_limit",
  "limitations",
  "domcontentloaded",
  "safe_for_automated_remediation",
  "needs_review",
  "continuousLoading",
  "expectedAppendedPageCount",
  "browserHistoryState",
  "timeoutReason",
  "timeoutMs: 10000",
  "clickInPlace(activeTab, backToTop)"
]) {
  assert.ok(
    browserContractSource.includes(requiredSourceContract),
    requiredSourceContract
  );
}

await assert.rejects(
  runComprehensiveBrowserBaseline({ manifest: { version: 1 } }),
  /manifest version 2/
);

await assert.rejects(
  runComprehensiveBrowserBaselineWithIsolation({}),
  /tab isolation support/
);

console.log("comprehensive quality browser helper contracts passed");
