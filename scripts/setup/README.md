# Setup entrypoints

Run these from Git Bash (Windows) or a Linux shell at any location:

```bash
bash scripts/setup/setup.sh
bash scripts/setup/verify.sh
```

`setup.sh` first validates the repository evidence and then dispatches to the
current platform. It creates only repository-local environments (`.venv` and
`.r-library`) and installs the exact Python and R dependencies declared in the
repository. It never installs system packages. Run the platform
`install-system-tools` script first to see the required system tools and their
official installation locations.

`verify.sh` is non-mutating. On Windows it invokes `windows/verify.ps1`; on
Linux it invokes `linux/verify.sh`.

Platform files:

- `windows/install-system-tools.ps1` — reports required Windows tools; it does
  not run a package manager.
- `windows/configure-project.ps1` — creates/reuses `.venv`, installs
  `social_generator/requirements-social.txt`, and provisions the local R
  library from `requirements-social.R`.
- `windows/verify.ps1` — checks tool availability, repository contracts, and
  local-environment state.
- `linux/install-system-tools.sh`, `linux/configure-project.sh`, and
  `linux/verify.sh` provide the same responsibilities, retaining the proven
  server Quarto location convention.

See [SETUP-SOP.md](SETUP-SOP.md) for prerequisites and recovery guidance.
