#!/usr/bin/env bash
set -Eeuo pipefail

# Compatibility command: bash scripts/release-ui-check.sh
# The canonical runner performs git diff --check, unittest discover,
# release_ui_static_check.py, and test_continuous_research.js checks.
REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
exec bash "${REPO_ROOT}/scripts/testing/build/release-ui-check.sh" "$@"
