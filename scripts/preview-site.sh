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

Immediately serves the last rendered site while Quarto watches source files
and writes changed pages to site/_site. Social cards are not regenerated.

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

if command -v py >/dev/null 2>&1; then
  PYTHON_COMMAND=(py)
elif command -v python >/dev/null 2>&1; then
  PYTHON_COMMAND=(python)
else
  printf 'ERROR: Neither py nor python was found on PATH.\n' >&2
  exit 127
fi

cd "${REPO_ROOT}"
export BMS_SKIP_SOCIAL_CARDS=1

if [[ ! -f "site/_site/index.html" ]]; then
  printf 'ERROR: site/_site/index.html does not exist.\n' >&2
  printf 'Run a full build once before starting the development preview.\n' >&2
  exit 1
fi

STATIC_SERVER_PID=""

cleanup() {
  if [[ -n "${STATIC_SERVER_PID}" ]] && kill -0 "${STATIC_SERVER_PID}" 2>/dev/null; then
    kill "${STATIC_SERVER_PID}" 2>/dev/null || true
    wait "${STATIC_SERVER_PID}" 2>/dev/null || true
  fi
}

trap cleanup EXIT

printf 'BMS static preview + render watcher\n'
printf 'Repository: %s\n' "${REPO_ROOT}"
printf 'URL:        http://%s:%s/\n' "${HOST}" "${PORT}"
printf 'Serving:    existing site/_site output\n'
printf 'Watching:   Quarto source changes\n'
printf 'Social:     skipped\n'
printf 'Stop:       Ctrl-C\n\n'

"${PYTHON_COMMAND[@]}" -m http.server "${PORT}" \
  --bind "${HOST}" \
  --directory site/_site &
STATIC_SERVER_PID=$!

# Fail quickly if the static server could not bind (for example, if the port
# is already in use) instead of leaving only the render watcher running.
sleep 0.25
if ! kill -0 "${STATIC_SERVER_PID}" 2>/dev/null; then
  wait "${STATIC_SERVER_PID}"
  exit 1
fi

quarto preview site \
  --no-serve \
  --no-browser \
  --no-navigate
