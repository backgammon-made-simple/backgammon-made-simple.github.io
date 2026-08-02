#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../.." && pwd)"

require_file() {
  [[ -f "$1" ]] || { printf 'Missing repository dependency source: %s\n' "$1" >&2; exit 1; }
}

require_file "${REPO_ROOT}/social_generator/requirements-social.txt"
require_file "${REPO_ROOT}/social_generator/requirements-social.R"
require_file "${REPO_ROOT}/site/_quarto.yml"

case "$(uname -s)" in
  MINGW*|MSYS*|CYGWIN*)
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File \
      "${SCRIPT_DIR}/windows/configure-project.ps1" -RepoRoot "${REPO_ROOT}"
    ;;
  Linux)
    bash "${SCRIPT_DIR}/linux/configure-project.sh" "${REPO_ROOT}"
    ;;
  *)
    printf 'Unsupported platform: %s\n' "$(uname -s)" >&2
    exit 2
    ;;
esac
