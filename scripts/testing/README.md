# Testing

This directory is the single testing surface for Backgammon Made Simple. Tests
remain in `tests/`; source fixtures remain in `fixtures/` and `tests/fixtures/`.

Run from Git Bash, Linux, macOS, or another Bash environment at the repository
root:

```bash
bash scripts/testing/quick.sh
bash scripts/testing/comprehensive.sh
```

The root entrypoints delegate to two layers:

- `build/quick.sh` and `build/comprehensive.sh` run deterministic source,
  unit, render, and rendered-site checks.
- `ux/quick.sh` and `ux/comprehensive.sh` validate the browser helpers and then
  identify live-browser and human work as `NOT RUN` until somebody performs it.

Use [TESTING-SOP.md](TESTING-SOP.md) to select a gate. Browser and human
procedures are under [ux/](ux/README.md). Legacy commands in `testing-scripts/`
and `scripts/release-ui-check.sh` are compatibility wrappers.
