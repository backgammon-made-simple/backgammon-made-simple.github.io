# Development layout

This directory reserves a clear home for future developer workflows. Existing
development and release scripts remain in `scripts/`, including
`preview-site.sh`, `bms-build-and-publish.sh`, and Windows helper scripts.

## Windows and fresh Codex chats

The repository-local launcher discovers installed tools without requiring an
inherited `PATH` or virtual-environment activation. Run it from the repository
root:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/codex-tools.ps1 verify
powershell -ExecutionPolicy Bypass -File scripts/codex-tools.ps1 browser-contract
powershell -ExecutionPolicy Bypass -File scripts/codex-tools.ps1 quick
powershell -ExecutionPolicy Bypass -File scripts/codex-tools.ps1 comprehensive
powershell -ExecutionPolicy Bypass -File scripts/codex-tools.ps1 preview 8765
powershell -ExecutionPolicy Bypass -File scripts/codex-tools.ps1 preview-smoke 8765
```

`preview` defaults to port `8765` when the port is omitted and serves
`http://127.0.0.1:8765/` through the existing `scripts/preview-site.sh`
workflow. The launcher changes `PATH` only in child processes and does not
persist environment settings.

Target layout: `scripts/dev/preview/`, `scripts/dev/build/`, and
`scripts/dev/release/`. Do not relocate an active script until its callers,
documentation, and release checks are migrated in one scoped change.
