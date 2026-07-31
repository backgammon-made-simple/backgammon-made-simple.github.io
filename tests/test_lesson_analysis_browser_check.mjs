import assert from "node:assert/strict";

import {
  LESSON_ANALYSIS_ROUTES,
  summarizeLessonAnalysisReport
} from "../scripts/lesson_analysis_browser_check.mjs";

assert.deepEqual(LESSON_ANALYSIS_ROUTES, {
  cube: "/learn/cube/what-the-cube-is-asking.html",
  checker: "/learn/cube/why-is-25-percent-the-basic-take-point.html"
});

assert.deepEqual(
  summarizeLessonAnalysisReport({
    checks: 12,
    failures: [],
    pages: 4,
    durationMs: 250
  }),
  {
    passed: true,
    checks: 12,
    failures: 0,
    pages: 4,
    durationMs: 250
  }
);

assert.equal(
  summarizeLessonAnalysisReport({
    checks: 1,
    failures: [{ context: "mobile/cube", message: "overflow" }],
    pages: 1,
    durationMs: 50
  }).passed,
  false
);

console.log("lesson analysis browser helper tests passed");
