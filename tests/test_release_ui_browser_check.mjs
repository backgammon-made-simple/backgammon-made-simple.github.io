import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

import {
  DEFAULT_MANIFEST,
  summarizeReport
} from "../scripts/release_ui_browser_check.mjs";

const helperSource = readFileSync(
  new URL("../scripts/release_ui_browser_check.mjs", import.meta.url),
  "utf8"
);

assert.equal(DEFAULT_MANIFEST.version, 1);
assert.deepEqual(
  DEFAULT_MANIFEST.viewports.map((item) => item.name),
  ["desktop", "mobile"]
);
assert.ok(DEFAULT_MANIFEST.pages.some((page) => page.id === "home"));
assert.deepEqual(
  DEFAULT_MANIFEST.pages.find((page) => page.id === "cube-lesson")
    .required_markers,
  ["data-bms-cube-decision"]
);
assert.equal(
  DEFAULT_MANIFEST.pages.filter(
    (page) => page.kind === "edge-scroll-fixture"
  ).length,
  3
);

assert.deepEqual(
  summarizeReport({
    pages: 4,
    checks: 20,
    failures: [],
    consoleMessages: [],
    durationMs: 100
  }),
  {
    passed: true,
    pages: 4,
    checks: 20,
    failures: 0,
    consoleMessages: 0,
    durationMs: 100
  }
);

assert.equal(
  summarizeReport({
    pages: 1,
    checks: 2,
    failures: [{ context: "mobile/home", message: "overflow" }],
    consoleMessages: ["error"],
    durationMs: 50
  }).passed,
  false
);

assert.ok(
  helperSource.includes("TOC rail collapse also hides the lesson track")
);
assert.ok(
  helperSource.includes("restoring the TOC rail also restores the lesson track")
);
assert.ok(!helperSource.includes("[data-bms-lesson-track-toggle]"));
assert.match(
  helperSource,
  /await scrollTo\(tab, 420\);\s+await scrollTo\(tab, 280\);/
);
assert.ok(
  helperSource.includes("term lookup closes without reloading the page")
);

console.log("UI release browser helper tests passed");
