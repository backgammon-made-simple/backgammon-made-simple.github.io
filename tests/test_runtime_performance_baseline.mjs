import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

import {
  PERFORMANCE_CONTRACT,
  median,
  runRuntimePerformanceBaseline
} from "../scripts/testing/quality/performance/runtime_performance_baseline.mjs";

assert.equal(PERFORMANCE_CONTRACT.warmup_loads, 1);
assert.equal(PERFORMANCE_CONTRACT.measured_loads, 3);
assert.deepEqual(PERFORMANCE_CONTRACT.viewport_names, [
  "desktop-1440",
  "mobile-390"
]);
assert.equal(PERFORMANCE_CONTRACT.route_ids.length, 6);
assert.equal(median([9, 1, 5]), 5);
assert.equal(median([1, 3]), 2);
assert.equal(median([null, Number.NaN]), null);

for (const metric of [
  "paint.largest_contentful_paint_ms",
  "layout.cumulative_layout_shift",
  "bytes.total.transfer",
  "bytes.javascript.transfer",
  "interactions.glossary_sidebar_ms"
]) {
  assert.ok(PERFORMANCE_CONTRACT.metric_names.includes(metric), metric);
}

const source = readFileSync(
  new URL(
    "../scripts/testing/quality/performance/runtime_performance_baseline.mjs",
    import.meta.url
  ),
  "utf8"
);
assert.ok(source.includes("Resource Timing values"));
assert.ok(source.includes("safe_for_automated_remediation"));

await assert.rejects(
  runRuntimePerformanceBaseline({}),
  /tab, viewport, and baseUrl are required/
);

console.log("runtime performance baseline contracts passed");
