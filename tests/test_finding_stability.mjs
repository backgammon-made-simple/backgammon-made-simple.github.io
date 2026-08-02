import assert from "node:assert/strict";

import {
  STABILITY_CLASSIFICATIONS,
  classifyBrowserFinding,
  classifyFindingStability,
  findingIdentity,
  normalizeFindingMessage,
  summarizeStability
} from "../scripts/testing/quality/browser/finding_stability.mjs";

assert.deepEqual(STABILITY_CLASSIFICATIONS, [
  "stable",
  "volatile",
  "environment-dependent",
  "test-infrastructure"
]);
assert.equal(
  normalizeFindingMessage("timeout within 10000ms; screenshot: run/a.png"),
  "timeout within <timeout>"
);
assert.equal(
  classifyFindingStability({ category: "product-defect", message: "clipped" }),
  "stable"
);
assert.equal(
  classifyFindingStability({ category: "test-infrastructure", message: "failed" }),
  "test-infrastructure"
);
assert.equal(
  classifyFindingStability({ message: "performance API unavailable" }),
  "environment-dependent"
);
assert.equal(
  classifyFindingStability({ message: "sampled", volatile: true }),
  "volatile"
);
assert.equal(
  classifyFindingStability({
    message: "initial IDs are unique: TOC",
    component: "research-article"
  }),
  "volatile"
);
assert.equal(
  classifyFindingStability({
    message: "duplicate IDs after scrolling: TOC",
    component: "research-article"
  }),
  "stable"
);

const identityInput = {
  category: "product-defect",
  route: "/learn/",
  viewport: { name: "mobile-390" },
  message: "control is clipped",
  selector: "button",
  state: "open"
};
assert.equal(findingIdentity(identityInput), findingIdentity(identityInput));

const finding = classifyBrowserFinding({
  failure: {
    context: "mobile-390/learn-index",
    message: "control is clipped",
    selector: "button"
  },
  page: { kind: "learn-index", route: "/learn/" },
  viewport: { name: "mobile-390", width: 390, height: 844 },
  screenshot: { path: "screenshots/browser/failure.png" }
});
assert.match(finding.finding_id, /^bms-finding-[a-f0-9]{16}$/);
assert.equal(finding.stability, "stable");
assert.equal(finding.component, "learn-index");
assert.equal(finding.selector, "button");
assert.match(finding.evidence, /screenshot/);

assert.deepEqual(summarizeStability([finding]), {
  stable: 1,
  volatile: 0,
  "environment-dependent": 0,
  "test-infrastructure": 0
});

console.log("browser finding stability contracts passed");
