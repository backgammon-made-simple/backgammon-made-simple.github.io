#!/usr/bin/env bash
set -Eeuo pipefail

trap 'printf "\nBuild or publish failed at line %s.\n" "$LINENO" >&2' ERR

QUARTO_VERSION="${QUARTO_VERSION:-1.10.15}"
EXPECTED_BRANCH="${BMS_BRANCH:-master}"
BMS_JOBS="${BMS_JOBS:-4}"

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || true)"
if [[ -z "$REPO_ROOT" ]]; then
    printf 'Run this script from inside the BMS website Git repository.\n' >&2
    exit 1
fi
cd "$REPO_ROOT"

PYTHON_BIN="$REPO_ROOT/.venv/bin/python"
QUARTO_BIN="${QUARTO_BIN:-$HOME/opt/quarto-$QUARTO_VERSION/bin/quarto}"
R_LIBRARY_DIR="$REPO_ROOT/.r-library"

if [[ ! -x "$PYTHON_BIN" ]]; then
    printf 'Missing Python environment: %s\n' "$PYTHON_BIN" >&2
    printf 'Run bms-setup-server-environment.sh first.\n' >&2
    exit 1
fi

if [[ ! -x "$QUARTO_BIN" ]]; then
    printf 'Missing Quarto executable: %s\n' "$QUARTO_BIN" >&2
    exit 1
fi

if [[ ! -d "$R_LIBRARY_DIR" ]]; then
    printf 'Missing R library: %s\n' "$R_LIBRARY_DIR" >&2
    printf 'Run bms-setup-server-environment.sh first.\n' >&2
    exit 1
fi

export PATH="$REPO_ROOT/.venv/bin:$HOME/opt/quarto-$QUARTO_VERSION/bin:$PATH"
export R_LIBS_USER="$R_LIBRARY_DIR"
export BMS_JOBS
export OMP_NUM_THREADS="1"
export OPENBLAS_NUM_THREADS="1"
export MKL_NUM_THREADS="1"
export NUMEXPR_NUM_THREADS="1"

CURRENT_BRANCH="$(git branch --show-current)"
if [[ "$CURRENT_BRANCH" != "$EXPECTED_BRANCH" ]]; then
    printf 'Expected branch %s, but current branch is %s.\n' \
        "$EXPECTED_BRANCH" "$CURRENT_BRANCH" >&2
    exit 1
fi

if [[ -n "$(git status --porcelain)" ]]; then
    printf 'The working tree is not clean. Review these files before deploying:\n' >&2
    git status --short >&2
    exit 1
fi

printf 'Fetching and fast-forwarding %s...\n' "$EXPECTED_BRANCH"
git fetch origin --prune
git pull --ff-only origin "$EXPECTED_BRANCH"

printf '\nTool versions:\n'
printf 'Python %s\n' "$($PYTHON_BIN --version 2>&1 | sed 's/^Python //')"
printf 'Rscript %s\n' "$(Rscript --version 2>&1 | sed 's/^Rscript (R) version //')"
printf 'Quarto %s\n' "$($QUARTO_BIN --version | head -n 1)"
printf 'Build workers %s\n' "$BMS_JOBS"

"$PYTHON_BIN" -m pip check

printf '\nBuilding the complete website...\n'
if [[ -f scripts/build_site.py ]]; then
    "$PYTHON_BIN" -u scripts/build_site.py
else
    "$QUARTO_BIN" render site
fi

if [[ ! -f site/_site/index.html ]]; then
    printf 'Build completed without producing site/_site/index.html.\n' >&2
    exit 1
fi

if [[ -f scripts/learn_glossary.py ]]; then
    printf '\nRunning rendered-site validation...\n'
    "$PYTHON_BIN" scripts/learn_glossary.py check-rendered \
        --output site/_site
fi

git diff --check

if [[ -n "$(git status --porcelain --untracked-files=no)" ]]; then
    printf 'The build changed tracked source or generated files.\n' >&2
    printf 'Review these changes instead of publishing them automatically:\n' >&2
    git status --short >&2
    exit 1
fi

printf '\nPublishing the existing render to gh-pages...\n'
(
    cd site
    "$QUARTO_BIN" publish gh-pages \
        --no-render \
        --no-browser \
        --no-prompt
)

printf '\nPublished gh-pages branch:\n'
git ls-remote --heads origin gh-pages

printf '\nSource checkout remains on:\n'
git status --short --branch

printf '\nDeployment submitted successfully.\n'
printf 'Site: https://backgammon-made-simple.github.io/\n'
