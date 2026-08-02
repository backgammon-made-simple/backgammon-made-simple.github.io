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
| Build runners | `scripts/testing/build/` | active | Quick/comprehensive gates; legacy wrappers remain in `testing-scripts/`. |
| Automated tests | `tests/` | active | Python, JS, and browser-helper contract checks. |
| Fixtures | `fixtures/`, `tests/fixtures/`, site data/assets | active | Inputs and retained analysis contracts; do not move. |
| Testing procedures | `scripts/testing/` | active | Canonical build, browser, and human procedures; old docs are pointers. |
| Social generation | `social_generator/` | active | Canonical implementation and pinned dependency manifests. |
| Developer directories | `scripts/testing/`, `scripts/dev/` | active | Consolidated testing and development surfaces. |
| Site templates | `site/templates/` | delete | No active path references; authoring-guide path reference removed. |
| Root `Advanced`, `App`, `Apps` | repository root | delete | Zero-byte accidental files. |
| Shiny dashboard | `shiny/` | unresolved | Separate R project; retain pending its own tooling inventory. |
| `task-work/` | repository root | archive-candidate | Not moved or deleted; needs ownership/retention review. |

## Dependency evidence

| Dependency | Source |
| --- | --- |
| Git, Bash, Python, Node | `scripts/testing/TESTING-SOP.md` and build runners |
| Quarto 1.10.15 | `scripts/bms-setup-server-environment.sh` |
| R / `Rscript` | server setup and benchmark/social scripts |
| Jinja2 3.1.6, PyYAML 6.0.2, playwright 1.54.0, Pillow 11.3.0, fonttools 4.63.0 | `social_generator/requirements-social.txt` |
| Playwright Chromium | server setup |
| R `yaml` | `social_generator/requirements-social.R` |

The foundation scripts deliberately make no claim to provision undeclared
system packages or the separate Shiny project.
