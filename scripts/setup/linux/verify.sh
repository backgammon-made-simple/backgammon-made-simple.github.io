#!/usr/bin/env bash
set -Eeuo pipefail

REPO_ROOT="${1:?repository root is required}"
cd "$REPO_ROOT"
failed=0
check() { if "$@"; then printf 'PASS %s\n' "$*"; else printf 'FAIL %s\n' "$*" >&2; failed=1; fi; }
check test -f site/_quarto.yml
check test -f social_generator/requirements-social.txt
check test -f social_generator/requirements-social.R
for command_name in git bash python3 node Rscript; do check command -v "$command_name"; done
QUARTO_VERSION="${QUARTO_VERSION:-1.10.15}"
QUARTO_BIN="${QUARTO_BIN:-$HOME/opt/quarto-$QUARTO_VERSION/bin/quarto}"
check test -x "$QUARTO_BIN"
check test -x .venv/bin/python
check test -d .r-library
if [[ $failed -ne 0 ]]; then exit 1; fi
.venv/bin/python -m pip check
printf 'PASS: Linux developer-tooling verification.\n'
