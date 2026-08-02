#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../../.." && pwd)"
cd "${REPO_ROOT}"

bash scripts/testing/ux/quick.sh

printf '\nUX comprehensive follow-up\n'
printf 'NOT RUN: live-browser release and lesson-analysis procedures.\n'
printf '  Helpers: scripts/testing/ux/browser/\n'
printf '  SOP:     scripts/testing/ux/UX-TESTING-SOP.md\n'
printf 'NOT RUN: comprehensive human review.\n'
printf '  Checklist: scripts/testing/ux/human-instructions/comprehensive.md\n'
