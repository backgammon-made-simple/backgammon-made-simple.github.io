#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../../.." && pwd)"
cd "${REPO_ROOT}"

printf '\nBMS quick UX automation contracts\n'
node --check scripts/testing/ux/browser/release_ui_browser_check.mjs
node --check scripts/testing/ux/browser/lesson_analysis_browser_check.mjs
node --check scripts/testing/ux/browser/comprehensive_quality_browser_check.mjs
node tests/test_release_ui_browser_check.mjs
node tests/test_lesson_analysis_browser_check.mjs
node tests/test_comprehensive_quality_browser_check.mjs

printf 'PASS: UX helper syntax and source contracts.\n'
printf 'NOT RUN: live-browser automation. A served site and browser controller are required.\n'
printf 'NOT RUN: human smoke instructions. See scripts/testing/ux/human-instructions/quick.md.\n'
