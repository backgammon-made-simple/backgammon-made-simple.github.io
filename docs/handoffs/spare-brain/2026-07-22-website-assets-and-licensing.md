# Handoff: Website Assets and Licensing

```text
handoff_id: spare-website-assets-licensing-2026-07-22
role: Spare Brain
task_id: stage-2-website-assets-and-licensing
repository: backgammon-made-simple.github.io
branch: spare-brain
implementation_commit: 8f6857b
base_commit: 5cfbed843afbbdf521bb8c521d3a2b4095343ec7
contains_prior_handoffs: no
merge_status: not-reviewed
```

## Summary

Stage 2 is complete. Stage 1 was not repeated because the accepted Learn checkpoint is already merged into `master`. The current implementation reuses the existing text-only social renderer, integrates approved brand assets, adds the accepted open licence split and global footer, and records reproducible asset/licence evidence.

## Changed files

Implementation commit `8f6857b` changes 40 files. The main groups are:

- build and metadata: `site/_quarto.yml`, `site/includes/site-head.html`, `README.md`;
- social pipeline: `social_generator/`, `site/assets/social/`;
- approved public icons: `site/assets/icons/`;
- licensing: `LICENSE.md`, `LICENSES/`, `THIRD_PARTY_NOTICES.md`, `site/licensing.qmd`;
- evidence: `docs/ASSET_PROVENANCE.md`, `docs/LEGACY_WEBSITE_COMPARISON.md`;
- accessibility metadata only: five existing post front matters and the Research fixture image.

## Intentionally unchanged / forbidden areas

No Learn curriculum prose or order, benchmark artifacts/results, predictor/analyzer behaviour, Shiny code, deployment configuration, old-site files, or coordination-reference files were changed. No branch was merged, rebased, pushed, deleted, or force-updated.

## Contracts or schemas touched

- Social Card Contract v1.1 remains a closed nine-field, text-only schema.
- The manifest is refreshed by R before the existing Python renderer runs.
- Homepage metadata generates `social-default`; other pages require explicit `social-card: true` plus kind/category metadata for a page-specific card.
- Website code/executable materials: `AGPL-3.0-only`.
- Original educational content: `CC-BY-SA-4.0`.
- Data: per release.
- Third-party materials: original licences.
- No trademark rights granted.

## Tests run

- full social pipeline with forced rendering: passed;
- manifest/page integration validator: passed (1 eligible page, 2 cards);
- generated PNG validation: passed (1200×630 default; 1280×640 GitHub);
- Quarto 1.10.15 full render: passed;
- local browser metadata/keyboard test: passed on `/`, nested Learn, `/research/`, and `/licensing.html`;
- desktop homepage at 1440×1000: visually sound;
- nested Learn and Licensing pages at 390×844: visually sound;
- icon/manifest/footer/OG/Twitter checks on root and nested output: passed;
- missing-alt check on tested pages: passed after focused metadata corrections;
- active and rendered obsolete-licence scans: no matches;
- public/private scan: passed, with safe false positives only in official AGPL language, vendored ClipboardJS, and Quarto's generated local-preview detection helper;
- `git diff --check`: passed;
- complete staged diff reviewed before commit.

## Tests not run

- No deployed social-platform crawler was run because this branch was not pushed or deployed.
- Old analyzer/worker tests were not run or migrated because their `backgammon_lab` implementation is absent and outside this task.
- No live Shiny or worker test was run because application behaviour was unchanged.

## Fixtures and generated artifacts

- `social-default.png`: 1200×630, SHA-256 `42444DD0C956F1B5BE2C0492F1BDF04B8DF92E10CC3651171818692199609BC2`;
- `github-backgammon-made-simple.png`: 1280×640, SHA-256 `5BEBE6FD66B12E8F375F5B59A65FBF19EBC9D3A9A436A7ED2263E90DCE1F334C`;
- screenshots used for visual review were temporary and were not committed;
- old `test-results` output was deliberately not migrated.

## Asset and licence evidence

`docs/ASSET_PROVENANCE.md` records every public icon's dimensions/hash, the approved logo hash, social generator commands/output dimensions, exact Source Sans 3 version, and authoritative licence sources/hashes. `THIRD_PARTY_NOTICES.md` records Source Sans 3 and build dependencies.

## Blockers and limitations

There is no completion blocker. The homepage social subtitle exceeds the renderer's recommended 140-character guidance, but browser text-fit validation passes. Pre-existing fenced-div warnings remain in unrelated page content. Pages without explicit page-card metadata use the global fallback or their existing Quarto image metadata.

## Exact next commands

```powershell
git show --stat 8f6857b
python social_generator/scripts/social/run_social_pipeline.py
quarto render site
git status --short --branch
```

## Requested acceptance

Review and accept implementation commit `8f6857b` on `spare-brain`. Do not push or merge until review is complete.
