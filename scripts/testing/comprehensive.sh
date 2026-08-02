#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../.." && pwd)"
cd "${REPO_ROOT}"

printf 'BMS comprehensive testing entrypoint\n\n'
bash scripts/testing/build/comprehensive.sh "$@"
bash scripts/testing/ux/comprehensive.sh

printf '\nCOMPLETE: automated comprehensive checks finished.\n'
printf 'NOT RUN: live-browser and human UX checks. Follow scripts/testing/ux/UX-TESTING-SOP.md.\n'
