#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

if [[ -n "$(git status --porcelain)" ]]; then
  printf 'ERROR: Commit or remove working-tree changes before release.\n' >&2
  git status --short >&2
  exit 1
fi

git switch master
git pull --ff-only origin master
BMS_NO_PREVIEW=1 bash scripts/windows-clean-build-and-test.sh

if [[ -n "$(git status --porcelain --untracked-files=no)" ]]; then
  printf 'ERROR: The build changed tracked files; review them before release.\n' >&2
  git status --short >&2
  exit 1
fi

(cd site && quarto publish gh-pages --no-render --no-browser --no-prompt)
printf 'Released master to gh-pages.\n'
