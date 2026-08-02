# Testing

This directory is the single testing surface for Backgammon Made Simple. Tests
remain in `tests/`; source fixtures remain in `fixtures/` and `tests/fixtures/`.

Run from Git Bash, Linux, macOS, or another Bash environment at the repository
root:

```bash
bash scripts/testing/quick.sh
bash scripts/testing/comprehensive.sh
bash scripts/testing/comprehensive-quality.sh --output-dir <OUTPUT_DIR>
```

The root entrypoints delegate to two layers:

- `build/quick.sh` and `build/comprehensive.sh` run deterministic source,
  unit, render, and rendered-site checks.
- `ux/quick.sh` and `ux/comprehensive.sh` validate the browser helpers and then
  identify live-browser and human work as `NOT RUN` until somebody performs it.

`comprehensive-quality.sh` is the canonical baseline/comparison entrypoint. It
performs a clean comprehensive build, records build duration and rendered-file
count, runs the static inventory, consumes controller-produced browser and
performance JSON when supplied, and generates `baseline-summary.md`,
`baseline.json`, and `findings.json`. Its five component statuses are
independent. Human UX review always remains `NOT RUN` in automation.

The exact routes, viewports, repetitions, metrics, commands, screenshot bounds,
and schemas that later comparisons must reuse are versioned in
`quality/comparison-contract.json`.

The reusable deterministic comparison process, retention rules, status
interpretation, and evidence policy are in [TESTING-SOP.md](TESTING-SOP.md).
Controller operation, two-shard logical browser runs, continuous-loading state,
and keyboard-focus procedure are in
[ux/UX-TESTING-SOP.md](ux/UX-TESTING-SOP.md).

Use [TESTING-SOP.md](TESTING-SOP.md) to select a gate. Browser and human
procedures are under [ux/](ux/README.md). Legacy commands in `testing-scripts/`
and `scripts/release-ui-check.sh` are compatibility wrappers.
