# Developer setup SOP

## System prerequisites

Install system tools yourself, using the platform vendor instructions: Git,
Bash, Python 3, Node.js, Quarto 1.10.15, and R with `Rscript`. These are
system tools; this repository does not manage them. The short browserless gate
uses Git, Python, Node, and Bash. A full render additionally uses Quarto; the
social-card pipeline and benchmark scripts use R.

On Linux, the proven server convention is a Quarto 1.10.15 binary at
`$HOME/opt/quarto-1.10.15/bin/quarto`. On Windows, `quarto` must resolve on
`PATH` and report that version. Override either location with `QUARTO_BIN`.

## Project configuration

1. Run `bash scripts/setup/setup.sh`.
2. Run `bash scripts/setup/verify.sh`.
3. Run the appropriate existing test tier from `testing-scripts/`; setup does
   not move or replace those runners.

The configuration step is idempotent: it reuses `.venv` and `.r-library`, then
reconciles their declared dependencies. Network access is needed only when the
declared Python packages, Playwright Chromium, or R `yaml` package are not
already cached or installed.

## Dependency sources

- `social_generator/requirements-social.txt`: Jinja2, PyYAML, playwright,
  Pillow, and fonttools (pinned).
- `social_generator/requirements-social.R`: R `yaml`.
- `scripts/bms-setup-server-environment.sh`: Quarto 1.10.15 and Playwright
  Chromium, plus the established local-environment layout.

If verification reports a missing system tool, install that tool outside the
repository and rerun verification. Do not add a package merely to satisfy this
foundation unless repository evidence first names it.
