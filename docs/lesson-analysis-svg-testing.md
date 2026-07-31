# Lesson analysis SVG MVP testing

This is the bounded release procedure for the fixture-driven cube and checker
lesson components. It tests supplied SVG selection and disclosure behavior; it
does not verify that fixture positions are legal moves or that placeholder
analysis values are real engine output.

## Source checks

From the repository root:

```powershell
git diff --check
node --check site/assets/bms-lesson-analysis.js
node --check scripts/lesson_analysis_browser_check.mjs
node tests/test_lesson_analysis.js
node tests/test_lesson_analysis_browser_check.mjs
py -m unittest tests.test_lesson_analysis
py -m unittest tests.test_learn_glossary tests.test_scrolling_test_lessons
```

The focused tests cover:

- fixture loading and explicit fixture status;
- Roll and Double as accepted first actions;
- Pass and Take as accepted responses;
- checker image and metric selection;
- missing optional values;
- unique IDs returned for repeated component instances;
- shared root-relative SVG paths across both lessons;
- use of image files rather than embedded SVG content;
- mounting after continuous Learn appends a lesson.

## Local render

For a fast iteration:

```powershell
quarto render site/learn/cube/what-the-cube-is-asking.qmd
quarto render site/learn/cube/why-is-25-percent-the-basic-take-point.qmd
```

Before handoff, run the complete local build with social cards skipped:

```powershell
$env:BMS_SKIP_SOCIAL_CARDS = "1"
quarto render site
```

Serve the completed output on a free local port:

```powershell
python -m http.server 8766 --bind 127.0.0.1 --directory site/_site
```

## Scripted browser check

Use Codex Browser to call
`runLessonAnalysisBrowserChecks()` from
`scripts/lesson_analysis_browser_check.mjs` against
`http://127.0.0.1:8766/`.

The helper opens each lesson in a fresh tab at `1440 × 1000` and `390 × 844`
and checks:

- keyboard focus on the native Roll button;
- Double, Pass, and Take paths;
- nested analysis disclosures;
- no page jump when the first answer opens;
- two cube instances retaining independent state;
- unique component IDs;
- the shared start asset on both lessons;
- all three checker candidate images and metrics;
- deliberate missing-value display;
- state after scrolling down and back up;
- image loading, horizontal overflow, mount errors, and console exceptions.

## Five-minute visual review

1. Open the cube lesson and inspect the initial card.
2. Tab to Roll, press Enter once in a normal browser, then inspect and close
   its nested analysis.
3. Choose Double, then Pass and Take; open both nested analysis sections.
4. Open the component-isolation fixture and confirm its Roll choice does not
   change the first component.
5. Open the checker lesson and choose all three candidates.
6. Confirm Candidate 3 displays missing probabilities without breaking layout.
7. Repeat steps 2–5 at a narrow viewport.
8. Scroll down and back up after a selection; confirm state remains intact.
9. Reload each page and confirm a clean initial state is reasonable.
10. Use browser Back and Forward once between the two lessons.

Capture only these review artifacts:

- cube initial state;
- cube Double then Take or Pass;
- cube Roll;
- checker initial and selected states;
- one narrow layout;
- the repeated component section.
