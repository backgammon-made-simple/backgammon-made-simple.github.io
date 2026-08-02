# Compatibility testing commands

These legacy paths delegate to the canonical build runners:

- `run-browserless-short.sh` -> `scripts/testing/build/quick.sh`
- `run-browserless-long.sh` -> `scripts/testing/build/comprehensive.sh`

New work should use the common entrypoints documented in
`scripts/testing/README.md`.
