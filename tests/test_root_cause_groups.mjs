import assert from "node:assert/strict";

import {
  groupFindingsByRootCause,
  rootCauseRuleForFinding
} from "../scripts/testing/quality/browser/root_cause_groups.mjs";

const makeFinding = (overrides) => ({
  finding_id: "bms-finding-default",
  category: "product-defect",
  severity: "major",
  stability: "stable",
  component: "learn-lesson",
  selector: null,
  route_or_file: "/learn/cube/example.html",
  viewport: { name: "mobile-390" },
  evidence: "duplicate IDs after scrolling: example; screenshot: screenshots/example.png",
  reproduction: "Run the browser baseline.",
  ...overrides
});

assert.equal(
  rootCauseRuleForFinding(makeFinding({})).id,
  "bms-root-continuous-duplicate-ids"
);
assert.equal(
  rootCauseRuleForFinding(
    makeFinding({ evidence: "mobile navigation menu opens" })
  ).id,
  "bms-root-mobile-navigation"
);

const groups = groupFindingsByRootCause([
  makeFinding({ finding_id: "bms-finding-a", selector: "#TOC" }),
  makeFinding({
    finding_id: "bms-finding-b",
    route_or_file: "/research/example.html",
    viewport: { name: "desktop-1440" },
    evidence: "initial IDs are unique: TOC; screenshot: screenshots/research.png"
  })
]);

assert.equal(groups.length, 1);
assert.deepEqual(groups[0], {
  root_cause_id: "bms-root-continuous-duplicate-ids",
  category: "product-defect",
  severity: "major",
  affected_component: "continuous Learn/Research content",
  affected_routes: ["/learn/cube/example.html", "/research/example.html"],
  affected_viewports: ["desktop-1440", "mobile-390"],
  finding_instances: 2,
  representative_selectors: ["#TOC"],
  representative_screenshots: [
    "screenshots/example.png",
    "screenshots/research.png"
  ],
  likely_source_files: [
    "site/assets/bms-learn-scroll.js",
    "site/assets/bms-research-scroll.js"
  ],
  stability: "stable",
  confidence: "high",
  reproduction: ["Run the browser baseline."],
  recommended_future_task:
    "Correct duplicate IDs without excluding or suppressing appended content.",
  finding_ids: ["bms-finding-a", "bms-finding-b"]
});

const fallback = groupFindingsByRootCause([
  makeFinding({
    finding_id: "bms-finding-fallback",
    evidence: "an uncategorized product check failed"
  })
]);
assert.match(fallback[0].root_cause_id, /^bms-root-[a-f0-9]{12}$/);
assert.equal(fallback[0].confidence, "medium");

console.log("browser root-cause grouping contracts passed");
