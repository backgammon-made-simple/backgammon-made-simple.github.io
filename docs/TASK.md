# TASK — Stage 2 Website Assets and Licensing

```text
role: Spare Brain
repository: backgammon-made-simple.github.io
working_path: repository root
branch: spare-brain
base_commit: 5cfbed843afbbdf521bb8c521d3a2b4095343ec7
implementation_commit: 8f6857b
status: complete; awaiting review
```

## Stage decision

The accepted Learn curriculum-shell checkpoint was already present on `master`: `master` commit `5cfbed8` is the merge of local Learn source commit `5c75b59`. The remote Learn ref (`a8dd863`) is older and is also an ancestor of `master`. There was no Learn diff to integrate, so this task completed Stage 2 only.

## Scope and boundaries

Allowed work covered the existing social-card generator, approved favicon/logo/icon sources, Quarto metadata and footer configuration, licence files/page/notices, asset provenance, accessibility metadata for existing Research images, build documentation, and the focused old-site scripts/tests comparison.

Learn curriculum content, benchmark data/results, Match Predictor or analyzer behaviour, Shiny code, deployment configuration, and all reference repositories remained unchanged.

## Deliverables completed

- integrated the existing text-only social renderer into the canonical Quarto pre-render;
- added an R manifest generator using homepage metadata and explicit page-card opt-in;
- generated and validated the default and GitHub social previews;
- published approved favicon, touch-icon, and web-app assets without visual modification;
- added Open Graph, Twitter card, favicon, touch-icon, and manifest metadata;
- replaced active obsolete non-open wording with the accepted licence split;
- added official AGPL-3.0-only, CC-BY-SA-4.0, and Source Sans OFL texts;
- added the global licence footer and public licensing page;
- recorded asset sources, hashes, dimensions, commands, and licences;
- classified old scripts/tests and deliberately did not migrate generated test results;
- added a reproducible rendered-site metadata/keyboard smoke test.

## Validation

- `python social_generator/scripts/social/run_social_pipeline.py --all` — passed;
- `quarto render site` with Quarto 1.10.15 — passed;
- rendered-page browser smoke test on home, nested Learn, Research, and Licensing — passed;
- desktop 1440×1000 and mobile 390×844 visual checks — passed;
- Open Graph/Twitter/icon/footer output checks — passed;
- PNG format and dimension validation — passed;
- active/rendered obsolete-licence scan — no matches;
- public/private scan — no private paths, credentials, worker URLs, or coordination-repository references; only authoritative licence language and Quarto's generated local-preview detection code matched broad terms;
- `git diff --check` — passed.

## Stop conditions / remaining review

Stop before push, merge, rebasing, or any reference-repository update. Reviewer should inspect commit `8f6857b`. The social renderer reports a non-fatal warning that the homepage description exceeds its recommended 140-character subtitle length; Chromium fit validation still passes without truncation or clipping. Existing Quarto fenced-div warnings in Learn, Match Predictor, and Research remain outside this task.
