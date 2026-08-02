#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../../.." && pwd)"
WITH_SOCIAL_CARDS=0

usage() {
  cat <<'EOF'
Usage:
  bash scripts/testing/build/comprehensive.sh [--with-social-cards]

Options:
  --with-social-cards  Run the canonical full social-card pipeline during the
                       Quarto build. The default skips social-card generation.
  -h, --help           Show this help.

Optional cross-repository renderer gate:
  Set BACKGAMMONBOARD_REPO to the backgammonboard checkout.
  Set RSCRIPT_BIN when Rscript is not on PATH.
EOF
}

for argument in "$@"; do
  case "${argument}" in
    --with-social-cards)
      WITH_SOCIAL_CARDS=1
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      printf 'ERROR: Unrecognized argument: %s\n\n' "${argument}" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if command -v py >/dev/null 2>&1; then
  PYTHON_COMMAND=(py)
elif command -v python >/dev/null 2>&1; then
  PYTHON_COMMAND=(python)
else
  printf 'ERROR: Neither py nor python was found on PATH.\n' >&2
  exit 127
fi

for command_name in git node quarto; do
  if ! command -v "${command_name}" >/dev/null 2>&1; then
    printf 'ERROR: %s was not found on PATH.\n' "${command_name}" >&2
    exit 127
  fi
done

cd "${REPO_ROOT}"

printf 'BMS comprehensive build gate\n'
printf 'Repository:   %s\n' "${REPO_ROOT}"
printf 'Social cards: %s\n\n' "$([[ ${WITH_SOCIAL_CARDS} -eq 1 ]] && printf yes || printf no)"

printf '[1/6] Quick build gate\n'
bash scripts/testing/build/quick.sh

printf '\n[2/6] Complete Python suite\n'
"${PYTHON_COMMAND[@]}" -m unittest discover -s tests -p 'test_*.py'

printf '\n[3/6] Full Quarto build\n'
if [[ ${WITH_SOCIAL_CARDS} -eq 1 ]]; then
  unset BMS_SKIP_SOCIAL_CARDS || true
else
  export BMS_SKIP_SOCIAL_CARDS=1
fi
quarto render site

printf '\n[4/6] Full rendered glossary and HTML audit\n'
"${PYTHON_COMMAND[@]}" scripts/learn_glossary.py check-rendered \
  --output site/_site
"${PYTHON_COMMAND[@]}" scripts/testing/build/release_ui_static_check.py

printf '\n[5/6] Real checker projection and asset contract\n'
"${PYTHON_COMMAND[@]}" -m unittest tests.test_real_checker_analysis -v

printf '\n[6/6] Optional backgammonboard renderer gate\n'
if [[ -n "${BACKGAMMONBOARD_REPO:-}" ]]; then
  RSCRIPT_COMMAND="${RSCRIPT_BIN:-Rscript}"
  "${RSCRIPT_COMMAND}" -e \
    "devtools::load_all('${BACKGAMMONBOARD_REPO}', quiet=TRUE); testthat::test_file(file.path('${BACKGAMMONBOARD_REPO}', 'tests/testthat/test-move-overlay.R')); testthat::test_file(file.path('${BACKGAMMONBOARD_REPO}', 'tests/testthat/test-ggboard.R'))"
else
  printf 'Skipped: BACKGAMMONBOARD_REPO is not set.\n'
fi

git diff --check
printf '\nPASS: comprehensive build gate.\n'
