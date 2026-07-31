# Testing scripts

- `run-browserless-short.sh` is the fast source and representative-render gate.
- `run-browserless-long.sh` runs the complete Python suite, a full Quarto build,
  full rendered-site checks, and an optional backgammonboard renderer gate.

Run both scripts from any directory with `bash`. See
[`../testing-sop.md`](../testing-sop.md) for prerequisites, browser procedures,
failure classifications, and reporting requirements.
