#!/usr/bin/env bash
set -Eeuo pipefail

REPO_ROOT="${1:?repository root is required}"
cd "$REPO_ROOT"
QUARTO_VERSION="${QUARTO_VERSION:-1.10.15}"
QUARTO_BIN="${QUARTO_BIN:-$HOME/opt/quarto-$QUARTO_VERSION/bin/quarto}"

for command_name in git python3 Rscript; do command -v "$command_name" >/dev/null || { printf 'Required system tool is missing: %s\n' "$command_name" >&2; exit 1; }; done
python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)' || { printf 'Python 3.11+ is required by testing-sop.md.\n' >&2; exit 1; }
[[ -x "$QUARTO_BIN" ]] || { printf 'Missing Quarto executable: %s\n' "$QUARTO_BIN" >&2; exit 1; }
[[ "$($QUARTO_BIN --version | head -n 1)" == "$QUARTO_VERSION" ]] || { printf 'Expected Quarto %s.\n' "$QUARTO_VERSION" >&2; exit 1; }

if [[ ! -x .venv/bin/python ]]; then python3 -m venv .venv; fi
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r social_generator/requirements-social.txt
.venv/bin/python -m pip check
.venv/bin/python -m playwright install chromium
mkdir -p .r-library
R_LIBS_USER="$REPO_ROOT/.r-library" Rscript --vanilla -e 'source("social_generator/requirements-social.R"); stopifnot(requireNamespace("yaml", quietly = TRUE))'
printf 'Project configuration completed.\n'
