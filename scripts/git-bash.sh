#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
PORT="${1:-8765}"
HOST="127.0.0.1"

usage() {
  cat <<'EOF'
Usage:
  ./scripts/git-bash.sh [PORT]

Serves the already-rendered site/_site directory locally.

Examples:
  ./scripts/git-bash.sh
  ./scripts/git-bash.sh 9000

Default port:
  8765

Open:
  http://127.0.0.1:PORT/

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

if command -v py >/dev/null 2>&1; then
  PYTHON_COMMAND=(py)
elif command -v python >/dev/null 2>&1; then
  PYTHON_COMMAND=(python)
else
  printf 'ERROR: Neither py nor python was found on PATH.\n' >&2
  exit 127
fi

cd "${REPO_ROOT}"

if [[ ! -f "site/_site/index.html" ]]; then
  printf 'ERROR: site/_site/index.html does not exist.\n' >&2
  printf 'Start the render watcher first:\n' >&2
  printf '  ./scripts/vs-code.sh\n' >&2
  printf 'Or run the full-build script if available:\n' >&2
  printf '  ./scripts/bms-full-build.sh\n' >&2
  exit 1
fi

printf 'BMS local static server\n'
printf 'Repository: %s\n' "${REPO_ROOT}"
printf 'Serving:    %s/site/_site\n' "${REPO_ROOT}"
printf 'URL:        http://%s:%s/\n' "${HOST}" "${PORT}"
printf 'Stop:       Ctrl-C\n\n'

exec "${PYTHON_COMMAND[@]}" -m http.server "${PORT}" \
  --bind "${HOST}" \
  --directory site/_site
