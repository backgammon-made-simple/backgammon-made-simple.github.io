#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../.." && pwd)"
cd "${REPO_ROOT}"

printf 'BMS quick testing entrypoint\n\n'
bash scripts/testing/build/quick.sh
bash scripts/testing/ux/quick.sh

printf '\nCOMPLETE: automated quick checks finished.\n'
printf 'NOT RUN: live-browser and human UX checks.\n'
