#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"

usage() {
  cat <<'EOF'
Usage:
  ./scripts/vs-code.sh

Watches the Quarto website for source changes and rerenders changed inputs.
It does not start a web server.

Run ./scripts/git-bash.sh in a second Git Bash terminal to view the site.
Stop with Ctrl-C.
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ $# -gt 0 ]]; then
  printf 'ERROR: vs-code.sh does not accept arguments.\n\n' >&2
  usage >&2
  exit 2
fi

if ! command -v quarto >/dev/null 2>&1; then
  printf 'ERROR: quarto was not found on PATH.\n' >&2
  exit 127
fi

cd "${REPO_ROOT}"

if [[ ! -f "site/_quarto.yml" ]]; then
  printf 'ERROR: Expected Quarto project not found: %s/site/_quarto.yml\n' "${REPO_ROOT}" >&2
  exit 1
fi

printf 'BMS live-render watcher\n'
printf 'Repository: %s\n' "${REPO_ROOT}"
printf 'Project:    %s/site\n' "${REPO_ROOT}"
printf 'Serving:    disabled\n'
printf 'Stop:       Ctrl-C\n\n'
printf 'Open a second Git Bash terminal and run:\n'
printf '  ./scripts/git-bash.sh\n\n'

exec quarto preview site \
  --no-serve \
  --no-browser \
  --no-navigate
