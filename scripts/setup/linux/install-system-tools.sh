#!/usr/bin/env bash
set -Eeuo pipefail

cat <<'EOF'
Install these system tools with your distribution/vendor guidance; this script does not install anything:
 - git, bash, python3, node, Rscript
 - Quarto 1.10.15 at $HOME/opt/quarto-1.10.15/bin/quarto (or set QUARTO_BIN)
Then run: bash scripts/setup/setup.sh
EOF
