import assert from "node:assert/strict";

import { compareBrowserBaselines } from "../scripts/testing/quality/browser/compare_browser_baselines.mjs";

const report = (overrides = {}) => ({
  comparisonContractVersion: 2,
  checks: 2000,
  coverage: {
    routeIds: ["home", "learn"],
    viewportNames: ["desktop", "mobile"],
    complete: true
  },
  findings: [
    { finding_id: "stable-a", stability: "stable" },
    { finding_id: "volatile-a", stability: "volatile" },
    { finding_id: "environment-a", stability: "environment-dependent" }
  ],
  rootCauseGroups: [
    { root_cause_id: "root-a", stability: "stable" }
  ],
  ...overrides
});

const identical = compareBrowserBaselines([report(), report()], ["a", "b"]);
assert.equal(identical.schema_version, 2);
assert.equal(identical.deterministicStableEvidence, true);
assert.equal(identical.comparisons[0].retentionAllowed, true);
assert.deepEqual(identical.comparisons[0].retentionBlockers, []);

const volatileOnly = compareBrowserBaselines([
  report(),
  report({
    findings: [
      { finding_id: "stable-a", stability: "stable" },
      { finding_id: "volatile-b", stability: "volatile" },
      { finding_id: "environment-b", stability: "environment-dependent" }
    ]
  })
]);
assert.equal(volatileOnly.comparisons[0].retentionAllowed, true);
assert.deepEqual(volatileOnly.comparisons[0].volatileVariation.added, [
  "volatile-b"
]);

const relatedVolatile = compareBrowserBaselines(
  [
    report(),
    report({
      findings: [
        { finding_id: "stable-a", stability: "stable" },
        {
          finding_id: "volatile-b",
          stability: "volatile",
          route_or_file: "/learn/"
        }
      ]
    })
  ],
  [],
  { affectedScopes: [{ route: "/learn/" }] }
);
assert.deepEqual(relatedVolatile.comparisons[0].retentionBlockers, [
  "related-volatile-variation"
]);

const blocked = compareBrowserBaselines([
  report(),
  report({
    checks: 1999,
    coverage: {
      routeIds: ["home"],
      viewportNames: ["desktop"],
      complete: false
    },
    findings: [
      { finding_id: "stable-new", stability: "stable" },
      { finding_id: "infra-a", stability: "test-infrastructure" }
    ],
    rootCauseGroups: [
      { root_cause_id: "root-new", stability: "stable" }
    ]
  })
]);
assert.deepEqual(blocked.comparisons[0].retentionBlockers, [
  "changed-check-count",
  "changed-route-coverage",
  "changed-viewport-coverage",
  "incomplete-browser-execution",
  "new-stable-findings",
  "new-stable-root-cause-groups",
  "test-infrastructure-failures"
]);
assert.equal(blocked.comparisons[0].retentionAllowed, false);

console.log("deterministic browser comparison gate contracts passed");
