#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../.." && pwd)"

for required_file in site/_quarto.yml social_generator/requirements-social.txt social_generator/requirements-social.R; do
  [[ -f "${REPO_ROOT}/${required_file}" ]] || { printf 'Missing: %s\n' "$required_file" >&2; exit 1; }
done

case "$(uname -s)" in
  MINGW*|MSYS*|CYGWIN*)
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File \
      "${SCRIPT_DIR}/windows/verify.ps1" -RepoRoot "${REPO_ROOT}"
    ;;
  Linux)
    bash "${SCRIPT_DIR}/linux/verify.sh" "${REPO_ROOT}"
    ;;
  *)
    printf 'Unsupported platform: %s\n' "$(uname -s)" >&2
    exit 2
    ;;
esac
