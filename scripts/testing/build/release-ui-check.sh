#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../../.." && pwd)"
PORT="8766"
RENDER=0
REPRESENTATIVE_ONLY=0

usage() {
  cat <<'EOF'
Usage:
  bash scripts/testing/build/release-ui-check.sh [PORT] [--render] [--representative-only]

Runs the repeatable source and rendered-site portion of the BMS UI release
gate. The browser phase uses scripts/testing/ux/browser/
release_ui_browser_check.mjs and is documented in scripts/testing/ux/.

Options:
  --render               Run a full Quarto render with social cards skipped.
  --representative-only  Limit rendered HTML validation to manifest pages.
  -h, --help             Show this help.

Examples:
  bash scripts/testing/build/release-ui-check.sh
  bash scripts/testing/build/release-ui-check.sh 8766 --render
EOF
}

for argument in "$@"; do
  case "${argument}" in
    --render)
      RENDER=1
      ;;
    --representative-only)
      REPRESENTATIVE_ONLY=1
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      if [[ "${argument}" =~ ^[0-9]+$ ]]; then
        PORT="${argument}"
      else
        printf 'ERROR: Unrecognized argument: %s\n\n' "${argument}" >&2
        usage >&2
        exit 2
      fi
      ;;
  esac
done

if (( PORT < 1 || PORT > 65535 )); then
  printf 'ERROR: Port must be from 1 to 65535. Received: %s\n' "${PORT}" >&2
  exit 2
fi

if [[ -x "${REPO_ROOT}/.venv/Scripts/python.exe" ]] &&
  "${REPO_ROOT}/.venv/Scripts/python.exe" -c 'import sys' >/dev/null 2>&1; then
  PYTHON_COMMAND=("${REPO_ROOT}/.venv/Scripts/python.exe")
  export PATH="${REPO_ROOT}/.venv/Scripts:${PATH}"
elif command -v py >/dev/null 2>&1; then
  PYTHON_COMMAND=(py)
elif command -v python >/dev/null 2>&1; then
  PYTHON_COMMAND=(python)
else
  printf 'ERROR: Neither py nor python was found on PATH.\n' >&2
  exit 127
fi

if ! command -v node >/dev/null 2>&1; then
  printf 'ERROR: node was not found on PATH.\n' >&2
  exit 127
fi

cd "${REPO_ROOT}"

printf 'BMS UI release checks\n'
printf 'Repository: %s\n' "${REPO_ROOT}"
printf 'Preview:    http://127.0.0.1:%s/\n' "${PORT}"
printf 'Render:     %s\n\n' "$([[ ${RENDER} -eq 1 ]] && printf yes || printf no)"

printf '[1/6] Source diff and deterministic fixture validation\n'
git diff --check

printf '\n[2/6] JavaScript syntax and focused logic tests\n'
node --check site/assets/bms-learn.js
node --check site/assets/bms-learn-scroll.js
node --check scripts/testing/ux/browser/release_ui_browser_check.mjs
node tests/test_learn_filters.js
node tests/test_continuous_learn.js
node tests/test_continuous_research.js
node tests/test_release_ui_browser_check.mjs

printf '\n[3/6] Python test suite\n'
"${PYTHON_COMMAND[@]}" -m unittest discover -s tests -p 'test_*.py'

printf '\n[4/6] Optional full render\n'
if [[ ${RENDER} -eq 1 ]]; then
  if ! command -v quarto >/dev/null 2>&1; then
    printf 'ERROR: quarto was not found on PATH.\n' >&2
    exit 127
  fi
  export BMS_SKIP_SOCIAL_CARDS=1
  quarto render site
else
  printf 'Skipped. Use --render for the release gate.\n'
fi

printf '\n[5/6] Rendered glossary and HTML audit\n'
STATIC_ARGUMENTS=()
if [[ ${REPRESENTATIVE_ONLY} -eq 1 ]]; then
  printf 'Full-build glossary validation skipped in representative-only mode.\n'
  STATIC_ARGUMENTS+=(--representative-only)
else
  "${PYTHON_COMMAND[@]}" scripts/learn_glossary.py check-rendered --output site/_site
fi
"${PYTHON_COMMAND[@]}" scripts/testing/build/release_ui_static_check.py "${STATIC_ARGUMENTS[@]}"

printf '\n[6/6] Preview availability\n'
if "${PYTHON_COMMAND[@]}" -c \
  'import sys, urllib.request; urllib.request.urlopen(sys.argv[1], timeout=2).read(1)' \
  "http://127.0.0.1:${PORT}/" 2>/dev/null; then
  printf 'Preview is reachable. Run the scripted browser phase now.\n'
else
  printf 'Preview is not reachable. Start it with:\n'
  printf '  bash scripts/preview-site.sh %s\n' "${PORT}"
fi

printf '\nSource/render UI gate passed.\n'
printf 'Browser procedure: scripts/testing/ux/UX-TESTING-SOP.md\n'
