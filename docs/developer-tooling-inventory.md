# Developer-tooling inventory

Status labels: **active** is in current use; **relocate** is a future target;
**archive-candidate** needs a later retention decision; **delete** was proven
obsolete; **unresolved** needs investigation.

| Area | Current location | Status | Evidence / destination |
| --- | --- | --- | --- |
| Quarto site | `site/_quarto.yml` | active | Website project; invokes `scripts/bms_pre_render.py` and `bms_post_render.py`. |
| Build/publish | `scripts/bms-build-and-publish.sh` | active | Full render and `gh-pages` publication. |
| Preview | `scripts/preview-site.sh` | active | Static server plus Quarto watcher. |
| Server setup | `scripts/bms-setup-server-environment.sh` | active | Proven Linux setup source for Quarto 1.10.15, local environments, Playwright, and R yaml. |
| Browserless runners | `testing-scripts/` | active; relocate | Current short/long gates; future `scripts/testing/browserless/`. |
| Automated tests | `tests/` | active | Python, JS, and browser-helper contract checks. |
| Fixtures | `fixtures/`, `tests/fixtures/`, site data/assets | active | Inputs and retained analysis contracts; do not move. |
| Manual procedures | `testing-sop.md`, `manual-testing-plan.md`, `docs/ui-release-testing.md` | active | Release and browser checklists. |
| Social generation | `social_generator/` | active | Canonical implementation and pinned dependency manifests. |
| Developer directories | `scripts/testing/`, `scripts/dev/` | relocate | Reserved target layouts only; no active scripts moved. |
| Site templates | `site/templates/` | delete | No active path references; authoring-guide path reference removed. |
| Root `Advanced`, `App`, `Apps` | repository root | delete | Zero-byte accidental files. |
| Shiny dashboard | `shiny/` | unresolved | Separate R project; retain pending its own tooling inventory. |
| `task-work/` | repository root | archive-candidate | Not moved or deleted; needs ownership/retention review. |

## Dependency evidence

| Dependency | Source |
| --- | --- |
| Git, Bash, Python, Node | `testing-sop.md` and browserless runners |
| Quarto 1.10.15 | `scripts/bms-setup-server-environment.sh` |
| R / `Rscript` | server setup and benchmark/social scripts |
| Jinja2 3.1.6, PyYAML 6.0.2, playwright 1.54.0, Pillow 11.3.0, fonttools 4.63.0 | `social_generator/requirements-social.txt` |
| Playwright Chromium | server setup |
| R `yaml` | `social_generator/requirements-social.R` |

The foundation scripts deliberately make no claim to provision undeclared
system packages or the separate Shiny project.
