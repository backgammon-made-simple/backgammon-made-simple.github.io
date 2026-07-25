# Legacy Website Comparison — 2026-07-22

The older `backgammon-made-simple` repository was inspected read-only. No files were copied from it.

| Old path | Classification | Reason |
|---|---|---|
| `scripts/run_analysis_dispatcher.py` | Keep only as reference | Worker-side dispatcher for the old `backgammon_lab` service; unrelated to static website asset/licence integration and depends on code absent from this repository. |
| `scripts/check_analyzer_worker.py` | Keep only as reference | Operational worker probe with token/endpoint handling; outside the public static build and current task boundary. |
| `tests/test_worker_contract.py` | Keep only as reference | Tests the old worker contract package, which is not present here. |
| `tests/test_sage_basic_schema.py` | Keep only as reference | Tests engine-kit and benchmark schemas outside this repository's current architecture. |
| `tests/test_request_hashing.py` | Keep only as reference | Depends on the absent `backgammon_lab` analysis package. |
| `tests/test_positions.py` | Keep only as reference | Depends on the absent `backgammon_lab` position package. |
| `tests/test_analysis_service.py` | Keep only as reference | Exercises fixture engine analysis, explicitly outside this infrastructure task. |
| `tests/test_analysis_dispatcher.py` | Keep only as reference | Couples to the old dispatcher and fixture analysis service. |
| `test-results/*.json` | Generated output | One prior test result artifact; not durable source or a current fixture, so it was deliberately not migrated. |
| `site/assets/bms-*.css` | Replace with newer equivalent | The current website has the accepted, newer theme/component/Learn styles. |
| `site/assets/logo.svg` | Keep only as reference | Its hash differs from the approved current project logo; it was not reused. |
| old `site/_quarto.yml` | Obsolete | It predates current navigation, Learn sidebar, asset integration, and accepted licensing. |

No old file was classified `migrate`: the durable current equivalents are already newer, while the remaining scripts/tests belong to an analyzer/worker architecture outside this task.
