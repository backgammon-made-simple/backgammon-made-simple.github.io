#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
PORT="${1:-8765}"
HOST="127.0.0.1"

usage() {
  cat <<'EOF'
Usage:
  bash preview-site.sh [PORT]

Starts the Quarto development preview without regenerating social cards.

Examples:
  bash preview-site.sh
  bash preview-site.sh 8765

Stop with Ctrl-C.
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ $# -gt 1 ]]; then
  printf 'ERROR: Provide zero or one port number.\n\n' >&2
  usage >&2
  exit 2
fi

if [[ ! "${PORT}" =~ ^[0-9]+$ ]] || (( PORT < 1 || PORT > 65535 )); then
  printf 'ERROR: Port must be an integer from 1 to 65535. Received: %s\n' "${PORT}" >&2
  exit 2
fi

if ! command -v quarto >/dev/null 2>&1; then
  printf 'ERROR: quarto was not found on PATH.\n' >&2
  exit 127
fi

cd "${REPO_ROOT}"
export BMS_SKIP_SOCIAL_CARDS=1

printf 'BMS development preview\n'
printf 'Repository: %s\n' "${REPO_ROOT}"
printf 'URL:        http://%s:%s/\n' "${HOST}" "${PORT}"
printf 'Social:     skipped\n'
printf 'Stop:       Ctrl-C\n\n'

exec quarto preview site \
  --host "${HOST}" \
  --port "${PORT}" \
  --no-browser
