# Development SOP pointer

For local preview on Windows, use
`powershell -ExecutionPolicy Bypass -File scripts/codex-tools.ps1 preview [PORT]`
after a full render exists. Other platforms can use
`bash scripts/preview-site.sh [PORT]`. For build and release behavior, follow
the existing `scripts/bms-build-and-publish.sh` contract and the root testing
SOP. This is a layout reservation, not a replacement workflow.
