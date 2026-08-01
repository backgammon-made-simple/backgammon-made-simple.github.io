#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(git rev-parse --show-toplevel)"
PORT="${1:-8765}"
cd "$ROOT"

[[ "$PORT" =~ ^[0-9]+$ ]] && (( PORT >= 1 && PORT <= 65535 )) || {
  printf 'Usage: bash scripts/windows-clean-build-and-test.sh [PORT]\n' >&2
  exit 2
}

printf 'Clean build and test on %s\n' "$(git branch --show-current)"
rm -rf -- site/_site site/.quarto
bash testing-scripts/run-browserless-long.sh --with-social-cards

if [[ "${BMS_NO_PREVIEW:-0}" != "1" ]]; then
  exec bash scripts/preview-site.sh "$PORT"
fi
