import { readFileSync, writeFileSync } from "node:fs";
import { pathToFileURL } from "node:url";

const sorted = (values) => Array.from(new Set(values)).sort();
const findingIds = (report, stability) =>
  sorted(
    (report.findings || [])
      .filter((finding) => finding.stability === stability)
      .map((finding) => finding.finding_id)
  );
const rootCauseIds = (report, stability = null) =>
  sorted(
    (report.rootCauseGroups || [])
      .filter((group) => !stability || group.stability === stability)
      .map((group) => group.root_cause_id)
  );
const difference = (left, right) => left.filter((item) => !right.includes(item));

const compareSet = (reference, candidate) => ({
  added: difference(candidate, reference),
  removed: difference(reference, candidate),
  unchanged: reference.filter((item) => candidate.includes(item))
});

const overlapsAffectedScope = (finding, scopes, rootCauseGroups) =>
  scopes.some(
    (scope) =>
      (scope.route && scope.route === finding.route_or_file) ||
      (scope.component && scope.component === finding.component) ||
      (scope.state && scope.state === finding.state) ||
      (scope.selector && scope.selector === finding.selector) ||
      (scope.rootCauseId &&
        rootCauseGroups.some(
          (group) =>
            group.root_cause_id === scope.rootCauseId &&
            group.finding_ids?.includes(finding.finding_id)
        ))
  );

export const compareBrowserBaselines = (
  reports,
  labels = [],
  { affectedScopes = [] } = {}
) => {
  if (!Array.isArray(reports) || reports.length < 2) {
    throw new Error("At least two browser reports are required.");
  }
  const reference = reports[0];
  const referenceStable = findingIds(reference, "stable");
  const referenceVolatile = findingIds(reference, "volatile");
  const referenceEnvironment = findingIds(reference, "environment-dependent");
  const referenceRootCauses = rootCauseIds(reference, "stable");
  const comparisons = reports.slice(1).map((candidate, index) => {
    const stable = compareSet(referenceStable, findingIds(candidate, "stable"));
    const volatile = compareSet(
      referenceVolatile,
      findingIds(candidate, "volatile")
    );
    const environment = compareSet(
      referenceEnvironment,
      findingIds(candidate, "environment-dependent")
    );
    const rootCauses = compareSet(
      referenceRootCauses,
      rootCauseIds(candidate, "stable")
    );
    const routeCoverage = compareSet(
      sorted(reference.coverage?.routeIds || []),
      sorted(candidate.coverage?.routeIds || [])
    );
    const viewportCoverage = compareSet(
      sorted(reference.coverage?.viewportNames || []),
      sorted(candidate.coverage?.viewportNames || [])
    );
    const infrastructureFailures = (candidate.findings || []).filter(
      (finding) => finding.stability === "test-infrastructure"
    );
    const relatedVolatileVariation = (candidate.findings || []).filter(
      (finding) =>
        finding.stability === "volatile" &&
        volatile.added.includes(finding.finding_id) &&
        overlapsAffectedScope(
          finding,
          affectedScopes,
          candidate.rootCauseGroups || []
        )
    );
    const blockers = [];
    if (candidate.comparisonContractVersion !== 2) {
      blockers.push("changed-or-missing-comparison-contract-version");
    }
    if (!candidate.coverage?.complete) {
      blockers.push("incomplete-browser-execution");
    }
    if (routeCoverage.added.length || routeCoverage.removed.length) {
      blockers.push("changed-route-coverage");
    }
    if (viewportCoverage.added.length || viewportCoverage.removed.length) {
      blockers.push("changed-viewport-coverage");
    }
    if (candidate.checks !== reference.checks) {
      blockers.push("changed-check-count");
    }
    if (stable.added.length) {
      blockers.push("new-stable-findings");
    }
    if (rootCauses.added.length) {
      blockers.push("new-stable-root-cause-groups");
    }
    if (infrastructureFailures.length) {
      blockers.push("test-infrastructure-failures");
    }
    if (relatedVolatileVariation.length) {
      blockers.push("related-volatile-variation");
    }
    return {
      reference: labels[0] || "run-1",
      candidate: labels[index + 1] || `run-${index + 2}`,
      routeCoverage,
      viewportCoverage,
      expectedCheckCount: reference.checks,
      actualCheckCount: candidate.checks,
      stableFindings: stable,
      volatileVariation: volatile,
      environmentDependentVariation: environment,
      testInfrastructureFailureIds: infrastructureFailures.map(
        (finding) => finding.finding_id
      ),
      relatedVolatileVariationIds: relatedVolatileVariation.map(
        (finding) => finding.finding_id
      ),
      stableRootCauseGroups: rootCauses,
      retentionBlockers: sorted(blockers),
      retentionAllowed: blockers.length === 0
    };
  });
  return {
    schema_version: 2,
    comparison_contract_version: 2,
    reference: labels[0] || "run-1",
    runs: reports.map((report, index) => ({
      label: labels[index] || `run-${index + 1}`,
      routeIds: sorted(report.coverage?.routeIds || []),
      viewportNames: sorted(report.coverage?.viewportNames || []),
      checks: report.checks,
      stableFindingIds: findingIds(report, "stable"),
      volatileFindingIds: findingIds(report, "volatile"),
      environmentDependentFindingIds: findingIds(
        report,
        "environment-dependent"
      ),
      testInfrastructureFindingIds: findingIds(
        report,
        "test-infrastructure"
      ),
      stableRootCauseGroupIds: rootCauseIds(report, "stable"),
      coverageComplete: Boolean(report.coverage?.complete)
    })),
    comparisons,
    deterministicStableEvidence: comparisons.every(
      (comparison) =>
        comparison.stableFindings.added.length === 0 &&
        comparison.stableFindings.removed.length === 0 &&
        comparison.stableRootCauseGroups.added.length === 0 &&
        comparison.stableRootCauseGroups.removed.length === 0 &&
        comparison.routeCoverage.added.length === 0 &&
        comparison.routeCoverage.removed.length === 0 &&
        comparison.viewportCoverage.added.length === 0 &&
        comparison.viewportCoverage.removed.length === 0 &&
        comparison.actualCheckCount === comparison.expectedCheckCount
    )
  };
};

const isCli =
  typeof process !== "undefined" &&
  process.argv?.[1] &&
  import.meta.url === pathToFileURL(process.argv[1]).href;
if (isCli) {
  const argumentsAfterScript = process.argv.slice(2);
  const outputIndex = argumentsAfterScript.indexOf("--output");
  const output =
    outputIndex >= 0 ? argumentsAfterScript[outputIndex + 1] : null;
  const paths = argumentsAfterScript.filter(
    (value, index) =>
      value !== "--output" && index !== outputIndex + 1
  );
  if (!output || paths.length < 2) {
    throw new Error(
      "Usage: node compare_browser_baselines.mjs <report> <report> [...] --output <comparison.json>"
    );
  }
  const result = compareBrowserBaselines(
    paths.map((path) => JSON.parse(readFileSync(path, "utf8"))),
    paths
  );
  writeFileSync(output, `${JSON.stringify(result, null, 2)}\n`);
}
