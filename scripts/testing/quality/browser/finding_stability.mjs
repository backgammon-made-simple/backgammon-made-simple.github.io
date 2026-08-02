import { createHash } from "node:crypto";

export const STABILITY_CLASSIFICATIONS = [
  "stable",
  "volatile",
  "environment-dependent",
  "test-infrastructure"
];

const hashId = (prefix, value) =>
  `${prefix}-${createHash("sha256").update(value).digest("hex").slice(0, 16)}`;

export const normalizeFindingMessage = (message) =>
  String(message || "")
    .replace(/; screenshot: .+$/i, "")
    .replace(/within \d+ms/gi, "within <timeout>")
    .replace(/\b\d+(?:\.\d+)?ms\b/gi, "<duration>")
    .replace(/\s+/g, " ")
    .trim();

export const classifyFindingStability = (failure) => {
  if (STABILITY_CLASSIFICATIONS.includes(failure.stability)) {
    return failure.stability;
  }
  const message = normalizeFindingMessage(failure.message);
  if (
    failure.category === "test-infrastructure" ||
    failure.incomplete ||
    /browser helper error|could not (?:read console|save .*screenshot)|expected continuous state was not reached/i.test(
      message
    )
  ) {
    return "test-infrastructure";
  }
  if (
    /performance api unavailable|history state unavailable|browser controller/i.test(
      message
    )
  ) {
    return "environment-dependent";
  }
  if (failure.volatile === true) {
    return "volatile";
  }
  if (
    /initial IDs are unique/i.test(message) &&
    ["learn-lesson", "research-article"].includes(failure.component)
  ) {
    return "volatile";
  }
  return "stable";
};

export const findingIdentity = ({
  category,
  route,
  viewport,
  message,
  selector = null,
  state = null
}) => {
  const identity = JSON.stringify({
    category,
    route,
    viewport: viewport?.name || viewport || null,
    message: normalizeFindingMessage(message),
    selector,
    state
  });
  return hashId("bms-finding", identity);
};

export const classifyBrowserFinding = ({
  failure,
  page,
  viewport,
  screenshot
}) => {
  const stability = classifyFindingStability({
    ...failure,
    component: failure.component || page?.kind
  });
  const category = failure.category || "product-defect";
  const route = page?.route || failure.context;
  const selector = failure.selector || null;
  const state = failure.state || null;
  return {
    finding_id: findingIdentity({
      category,
      route,
      viewport,
      message: failure.message,
      selector,
      state
    }),
    category,
    severity: category === "test-infrastructure" ? "blocking" : "major",
    stability,
    component: failure.component || page?.kind || "browser-baseline",
    selector,
    state,
    route_or_file: route,
    viewport: viewport || null,
    evidence: `${failure.message}${
      screenshot ? `; screenshot: ${screenshot.path}` : ""
    }`,
    reproduction: `Serve site/_site and run the comprehensive browser baseline for ${failure.context}.`,
    safe_for_automated_remediation: false,
    needs_review: true
  };
};

export const summarizeStability = (findings) =>
  Object.fromEntries(
    STABILITY_CLASSIFICATIONS.map((classification) => [
      classification,
      findings.filter((finding) => finding.stability === classification).length
    ])
  );
