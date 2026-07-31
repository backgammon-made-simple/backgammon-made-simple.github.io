# Lesson analysis SVG MVP handoff

## Checkpoint

- Branch: `codex/lesson-analysis-svg-mvp`
- Base: `a5c61d4a3ef76c8ffef13fe806afb967414c6233`
- Fixture commit: `2b52f18` (`prototype: add lesson fixtures and SVG generation`)
- Interaction commit: `4d0477b` (`feat: add cube and checker lesson interactions`)
- Test/release commit: this handoff is included in
  `test: cover scrolling and shared SVG reuse`
- No push, merge, or publication was performed.

## Website result

The cube lesson at
`/learn/cube/what-the-cube-is-asking.html` has two independent cube-decision
instances. The main path accepts Roll or Double, then Pass or Take when a
double is offered. The second instance is inside a disclosure and confirms
that repeated components retain independent state and unique runtime IDs.

The companion cube-track lesson at
`/learn/cube/why-is-25-percent-the-basic-take-point.html` has a reusable
three-candidate checker interaction. Selecting a candidate swaps only the
supplied SVG, metrics, and explanation. Missing probabilities are displayed
as `Not supplied`.

Both components load the same root-relative `starting.svg` through an `<img>`.
They do not inline SVG content, so repeated assets cannot duplicate SVG IDs.
The 1200-by-910 image dimensions are reserved before loading to prevent layout
shift.

All values and candidate positions are explicitly labelled fixture-only and
are not represented as verified engine output or legal move results.

## Library audit and SVG provenance

`backgammonboard` was inspected read-only at gallery commit
`a4b8188138506d5ca2cfc294092922a45cfe3b34`. The commit is labelled
`unfinished state`, but its existing `renderer_position()` and `ggboard()`
interfaces were sufficient to understand the contract. The gallery branch
was not modified because it did not block the website MVP.

The Engine Kit was inspected read-only at
`33409334c6f4d6fca0d798ba4a324673e72e86ce`. Its RendererPosition envelope
uses:

- `position` with schema `universal-position-v1`;
- `semantic_state_hash`;
- `view` with schema `backgammon-view-v1`;
- `view_hash`.

The board adapter accepts that envelope as a parsed R object, a JSON string,
or a JSON file. Dice come from `position.state.dice`; players remain
`player_0` and `player_1`; view metadata controls bottom/top player, home side,
cube placement, and point labels. The current learner policy fixes the learner
at the bottom and rejects flipping the responder to the bottom. Ghost
checkers and checker-move arrows are not implemented by the current adapter.

The exact retained-source mapping and semantic hash are stored in
`site/assets/positions/lesson-analysis-svg-mvp/opening-fixture/PROVENANCE.txt`.
It is plain text so Quarto does not render it as an extra page.

Two bounded R attempts were made:

1. `Rscript -e ...` failed because `Rscript` was not on `PATH`.
2. The absolute `Rscript.exe -e ...` attempt failed because native PowerShell
   argument handling stripped the embedded R path quotes.

The same inline method was not tried a third time. Existing retained gallery
SVGs were copied instead. No Sage or GNU Backgammon analysis was run.

## Validation completed

- `git diff --check`: passed.
- JavaScript syntax checks: passed.
- All six JavaScript test files: passed.
- Focused lesson/glossary Python tests: 73 passed.
- Full Python suite: 134 passed. The suite requires an unsandboxed run on this
  Windows host because two glossary tests use `TemporaryDirectory`.
- Full Quarto build with `BMS_SKIP_SOCIAL_CARDS=1`: passed, 65 pages.
- Rendered glossary check: passed, including 12 canonical glossary anchors and
  34 continuous lessons.
- Rendered static UI audit: 65 pages, zero findings.
- Dedicated lesson browser check: 56 checks, four page/viewport visits, zero
  failures.
- Full UI release browser sweep: 314 checks, 26 page/viewport visits, zero
  failures and zero console errors.

The browser checks covered 1440-by-1000 desktop and 390-by-844 mobile layouts,
Roll, Double, Pass, Take, all checker candidates, nested disclosures, repeated
instances, keyboard focus, scrolling down and up, continuous-page behavior,
missing values, SVG loading, duplicate IDs, horizontal overflow, and console
exceptions.

Local review screenshots are intentionally untracked under:

`task-work/lesson-analysis-svg-mvp/review/`

- `cube-initial.png`
- `cube-roll.png`
- `cube-double-take.png`
- `cube-repeated-instance.png`
- `checker-initial.png`
- `checker-candidate-3.png`
- `checker-mobile-candidate-3.png`

## Known limitations

- The responder SVG is an older retained rotated-view fixture. Production use
  needs an explicit board-contract decision for responder perspective.
- Checker candidate SVGs are representative supplied positions, not moves
  applied from the shared starting position.
- Analysis values are fixture data, not Engine Kit results.
- The browser does not parse notation, calculate legal moves, or invoke an
  engine.
- The current board adapter does not supply ghost checkers or checker-move
  arrows.

## Future Engine Kit fixture contract

A production cube fixture should add a stable case ID, input RendererPosition
and both hashes, decision player, correct first action, action equities,
winning/gammon/backgammon probabilities, responder RendererPosition and view
hash, correct Pass/Take response, engine name/version/settings, configuration
hash, and analysis provenance.

A production checker fixture should add the input RendererPosition and hashes,
dice, decision player, stable candidate IDs, normalized and source notation,
each resulting RendererPosition and hashes, rank, equity and equity loss,
nullable win/gammon/backgammon probabilities, explanation, engine
name/version/settings, configuration hash, and provenance.

The next iteration should generate those normalized records in Engine Kit,
render every resulting RendererPosition through a completed board gallery
workflow, and then replace the fixture-only JSON without changing the website
component API.
