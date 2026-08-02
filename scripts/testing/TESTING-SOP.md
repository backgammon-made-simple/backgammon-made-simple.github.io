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
