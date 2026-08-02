#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"

if [[ -x "${REPO_ROOT}/.venv/Scripts/python.exe" ]]; then
  PYTHON_COMMAND=("${REPO_ROOT}/.venv/Scripts/python.exe")
elif command -v py >/dev/null 2>&1; then
  PYTHON_COMMAND=(py)
elif command -v python >/dev/null 2>&1; then
  PYTHON_COMMAND=(python)
else
  printf 'ERROR: Neither py nor python was found on PATH.\n' >&2
  exit 127
fi

for command_name in git node; do
  if ! command -v "${command_name}" >/dev/null 2>&1; then
    printf 'ERROR: %s was not found on PATH.\n' "${command_name}" >&2
    exit 127
  fi
done

cd "${REPO_ROOT}"

printf 'BMS short browserless gate\n'
printf 'Repository: %s\n\n' "${REPO_ROOT}"

printf '[1/5] Diff and deterministic fixture checks\n'
git diff --check

printf '\n[2/5] JavaScript syntax\n'
node --check site/assets/bms-learn.js
node --check site/assets/bms-learn-scroll.js
node --check site/assets/bms-lesson-analysis.js
node --check scripts/release_ui_browser_check.mjs
node --check scripts/lesson_analysis_browser_check.mjs

printf '\n[3/5] Focused JavaScript behavior\n'
node tests/test_learn_filters.js
node tests/test_continuous_learn.js
node tests/test_continuous_research.js
node tests/test_lesson_analysis.js
node tests/test_release_ui_browser_check.mjs
node tests/test_lesson_analysis_browser_check.mjs

printf '\n[4/5] Focused Python contracts\n'
"${PYTHON_COMMAND[@]}" -m unittest \
  tests.test_release_ui_checks \
  tests.test_lesson_analysis \
  tests.test_real_checker_analysis \
  -v

printf '\n[5/5] Existing rendered-site representative audit\n'
if [[ -f site/_site/index.html ]]; then
  "${PYTHON_COMMAND[@]}" scripts/release_ui_static_check.py \
    --representative-only
else
  printf 'Skipped: site/_site/index.html does not exist.\n'
fi

printf '\nPASS: short browserless gate.\n'
