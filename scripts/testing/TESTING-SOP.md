# Backgammon Made Simple testing SOP

## Choose a gate

Use the smallest gate that covers the change:

| Gate | Command | Use |
| --- | --- | --- |
| Quick | `bash scripts/testing/quick.sh` | Routine source, fixture, and focused behavior changes |
| Comprehensive | `bash scripts/testing/comprehensive.sh` | Shared UI/build changes and release candidates |
| Comprehensive with social cards | `bash scripts/testing/comprehensive.sh --with-social-cards` | Authorized release preparation |
| Comprehensive quality baseline | `bash scripts/testing/comprehensive-quality.sh --output-dir <OUTPUT_DIR>` | Reproducible build, browser, performance, bloat, and human-status baseline |

Stop after the same approach fails twice. Record both attempts instead of
repeating them. Do not run two Quarto renders concurrently.

## Preflight

Record `git branch --show-current`, `git rev-parse --short HEAD`, and
`git status --short`. The quick gate requires Git, Bash, Python 3.11+, and
Node.js. The comprehensive build also requires Quarto and project dependencies.

The quick entrypoint runs the focused build gate and UX helper contracts. The
comprehensive entrypoint adds all Python tests, a full Quarto render, glossary
and HTML audits, checker contracts, and the comprehensive UX handoff.

`PASS` applies only to the named automated layer. Live-browser and human work
must remain `NOT RUN` until actually completed; it is never implied by a build
result. Follow [ux/UX-TESTING-SOP.md](ux/UX-TESTING-SOP.md) for those phases.

For the comprehensive quality baseline, start a fixed server on port 8766 and
run the controller helpers documented in `ux/UX-TESTING-SOP.md`. Supply their
JSON reports to the final entrypoint with `--browser-report` and
`--performance-report`. Missing controller reports remain `NOT RUN`; human UX
review is never inferred from them.

## Canonical quality workflow

Run commands from the repository root. Choose an ignored output directory,
record the current commit, and do not change the rendered output or server
between repeated browser runs.

```bash
# Complete build and browserless automation.
bash scripts/testing/comprehensive.sh

# Create clean build/static evidence; controller and human components are
# initially NOT RUN.
bash scripts/testing/comprehensive-quality.sh --output-dir <OUTPUT_DIR>

# Serve that fixed output while browser evidence is collected.
python -m http.server 8766 --bind 127.0.0.1 --directory site/_site

# Static inventory alone.
python scripts/testing/quality/static_inventory.py \
  --repo-root . --site-dir site/_site \
  --output <OUTPUT_DIR>/static/static-inventory.json

# Compare two or more unchanged browser reports under contract v2.
node scripts/testing/quality/browser/compare_browser_baselines.mjs \
  <RUN_1_BROWSER_JSON> <RUN_2_BROWSER_JSON> <RUN_3_BROWSER_JSON> \
  --output <OUTPUT_DIR>/browser-comparison.json

# Reassemble all automated components without rebuilding the tested output.
bash scripts/testing/comprehensive-quality.sh \
  --output-dir <OUTPUT_DIR> --skip-build \
  --browser-report <OUTPUT_DIR>/browser/browser-baseline.json \
  --performance-report <OUTPUT_DIR>/performance/runtime-performance.json
```

The browser controller calls `runComprehensiveBrowserBaseline()` from
`ux/browser/comprehensive_quality_browser_check.mjs`; the performance phase
calls `runRuntimePerformanceBaseline()` from
`quality/performance/runtime_performance_baseline.mjs`. Use their
`WithIsolation` variants when the controller requires a fresh tab for explicit
navigations. Exact call signatures, routes, viewports, repetitions, metrics,
and screenshot bounds are versioned in `quality/comparison-contract.json`.
See [ux/UX-TESTING-SOP.md](ux/UX-TESTING-SOP.md) for state control, two-shard
execution, focus testing, and report-writing requirements.

## Deterministic comparison contract v2

Every automated browser finding remains visible and is classified as:

- `stable`: repeatable product evidence used for strict regression comparison;
- `volatile`: timing/state sampling that can vary and must retain scope data;
- `environment-dependent`: controller or host capability variation;
- `test-infrastructure`: the test could not produce trustworthy evidence.

Stable findings are also grouped by deterministic root-cause ID. A valid
unchanged comparison requires identical route coverage, viewport coverage,
complete route/viewport contexts, aggregate check count, per-context check
counts, stable finding IDs, and stable root-cause IDs. The automatic comparator
checks coverage, aggregate checks, findings, infrastructure classifications,
and root groups. For sharded runs, also compare the complete
`checksByContext` maps exactly; an equal aggregate must not hide a lost check in
one context and an extra check in another.

### Retaining a future change

A new stable product finding, new stable root-cause group, changed route or
viewport coverage, missing context/check, incomplete execution, or
test-infrastructure failure blocks retention. Unrelated volatile variation
remains in the comparison but does not independently reject a change. Volatile
variation related by route, component, state, selector, or root-cause group
must be investigated before retention.

Performance claims require comparable repeated measurements under the same
contract and environment. A simplification may be retained without a speed
improvement only when complexity or duplication clearly decreases and there is
no stable regression.

## Interpreting and retaining evidence

A completed browser baseline can report `FAIL` because it successfully found
product defects; that is different from a `test-infrastructure` finding.
Build, browser, runtime performance, static inventory, and human UX statuses
remain independent. Human UX stays `NOT RUN` until a person performs and
records it.

Raw local reports, screenshots, and interrupted attempts belong in ignored
`.quarto/` output. Mark the accepted comparison and every superseded attempt
unambiguously; do not silently overwrite or reinterpret them. Deterministic
summaries belong in milestone evidence. Repository SOPs describe this reusable
workflow and must not become copies of a particular milestone report.

## Optional gates

Set `BACKGAMMONBOARD_REPO` and optionally `RSCRIPT_BIN` before the comprehensive
command to run the cross-repository renderer checks. Use `--with-social-cards`
only when the social-card pipeline is intentionally in scope.

For a fixed release-style source/render check with a preview availability
probe, use:

```bash
bash scripts/testing/build/release-ui-check.sh 8766 --render
```

Serve the last build with `bash scripts/preview-site.sh 8766`. Never commit
generated `site/_site`, source-adjacent HTML, screenshots, logs, or reports
unless explicitly requested.

## Reporting

Record the branch and commit, exact commands, build/social-card mode, automated
results, browser viewports actually tested, human checks actually performed,
skips, findings by severity, generated files, and the next recommendation.
