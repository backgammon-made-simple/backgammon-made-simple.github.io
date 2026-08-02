# Backgammon Made Simple manual testing plan

This document is the human verification plan for the website functionality
added or refined during the Learn, Research, glossary, scrolling, sidebar,
lesson-analysis, build, and release work. It complements, rather than replaces,
the automated procedures in `testing-sop.md` and
`docs/ui-release-testing.md`.

Use the quick smoke pass while developing. Use the complete pass before merging
shared JavaScript or CSS, changing glossary data or generation, changing
continuous loading, changing lesson fixtures, or publishing to `gh-pages`.

## 1. Test record and environment

Record these before testing:

```text
Tester:
Date and time:
Branch:
Commit:
Working-tree status:
Preview or public URL:
Browser and version:
Desktop viewport:
Mobile device or viewport:
Build command used:
```

Recommended viewports:

- Desktop: 1440 x 1000 at 100% browser zoom.
- Narrow desktop: 1024 x 768.
- Mobile: 390 x 844 in portrait orientation.
- Optional real-phone check: Safari on iPhone or Chrome on Android.
- Optional phone desktop-mode check: confirm the desktop rails do not obscure
  the article.

Before a release, start from a clean full build. During development, a current
focused render is sufficient for the affected representative pages.

```bash
# Development preview of the last build plus source watching
bash scripts/preview-site.sh 8766

# Full local clean build and test, then preview
bash scripts/windows-clean-build-and-test.sh 8766

# Release workflow; use only when a release is authorized
bash scripts/windows-clean-release.sh
```

Do not run a second Quarto render while the preview watcher is rendering.
During every browser pass, keep the browser console open and note red errors,
failed local requests, or repeated warnings.

## 2. Representative routes

Use these pages to cover the site without testing every article:

| Surface | Route |
| --- | --- |
| Homepage | `/` |
| Learn index | `/learn/` |
| Cube track index | `/learn/cube/` |
| Learn lesson and rich cube fixture | `/learn/cube/what-the-cube-is-asking.html` |
| Real checker fixture | `/learn/cube/why-is-25-percent-the-basic-take-point.html` |
| Research article | `/research/what-we-are-building.html` |
| Long Research article | `/research/sage-vs-gnu-additional-details.html` |
| Glossary | `/glossary/` |
| Analyzer | `/analyze/` |
| Match Predictor | `/match-predictor/` |
| Engine Benchmark | `/engine-benchmark/` |
| About | `/about.html` |
| Updates and RSS landing | `/updates/` |
| Missing route | `/this-page-does-not-exist` |

## 3. Fifteen-minute smoke pass

Run this after a focused UI change.

1. Open `/` at desktop width. Use every primary navbar link once. Confirm the
   homepage has not inherited Learn, Research, glossary, or sidebar controls.
2. Open `/learn/`. Expand **Click to search and filter lessons**, search for
   `cube`, clear it, and open the Cube track.
3. On `/learn/cube/`, confirm lesson titles are readable, track title and lesson
   count are close together, and the displayed count matches the visible
   lessons.
4. Open `/learn/cube/what-the-cube-is-asking.html`. At the top, confirm Lessons,
   On This Page, and Term Search are usable and do not overlap.
5. Scroll down and then up. Confirm the navbar and lesson controls respond to
   direction correctly. Open Lessons and confirm **Hide** remains inside the
   left divider.
6. Confirm Term Search is approximately half the tools rail width, is open only
   at the page top, and collapses after either upward or downward scrolling.
7. Hover and click **10 in the Zone** and **active builder**. Confirm the short
   definition appears on hover and the full definition appears in the lookup.
8. Exercise one Double/Roll choice and one nested disclosure on the worked cube
   position.
9. Open the checker fixture page and select all three candidate moves. Confirm
   the SVG and metrics change together.
10. Open one Research article. Exercise its TOC, Term Search, scrolling rails,
    and one anchor.
11. Open `/glossary/`. Confirm its Term Search starts collapsed at the top,
    opens after desktop scrolling, and clicking **active builders** displays
    **Active Builder** in place without jumping to the top.
12. Confirm `/analyze/` and `/match-predictor/` have no Term Search control.
13. Repeat steps 4, 7, 9, 10, and 11 at mobile width. Confirm there is no page-
    level horizontal overflow.
14. Confirm the browser console contains no application errors.

## 4. Global shell, scale, and navigation

Run at desktop and mobile widths.

### 4.1 Visual scale and readable width

- Text, navigation, cards, controls, and sidebars should use the site's enlarged
  visual scale consistently.
- Body text must remain comfortably wide on Learn index and track index pages.
- Headings must wrap without clipping.
- No content should be hidden behind the fixed navbar.
- The main reading column must widen when side rails collapse.
- No page should have horizontal document overflow. Deliberately scroll a wide
  table inside its own container to distinguish local scrolling from page
  overflow.

### 4.2 Navbar and ordinary links

- Click Home, Learn, Research, Glossary, Analyze, Match Predictor, Engine
  Benchmark, Updates, and About when present in navigation.
- Each link must open in the same tab unless it is explicitly external.
- Browser Back and Forward must restore the expected page and approximate scroll
  position.
- Internal article links, fragment links, footer links, and logo links must not
  lead to `/.`, duplicate slashes, or obsolete `/learn/glossary/` routes.
- External links should be visibly identifiable and should not break the local
  navigation state.

### 4.3 Navbar scroll behavior

- Scroll down far enough to unpin the navbar.
- Scroll upward and confirm it returns smoothly without covering headings.
- Controls designed to sit below the navbar must slide down with it.
- Controls designed to remain available while the navbar is hidden must move to
  the top rather than leaving an empty navbar-height gap.

### 4.4 Back to top

- The control must remain hidden near the top.
- It should appear only after more than approximately one viewport of scrolling.
- On Learn and Research articles it should be right-aligned beneath Term Search
  and close to the bottom of the viewport.
- Its font, muted-grey color, and visual weight should match Term Search.
- Activating it should return to the top, restore the expected rails, and place
  focus sensibly without a console error.

### 4.5 Ordinary-page isolation

On About, Engine Benchmark, Analyzer, Match Predictor, Updates, and the
homepage, confirm that Learn-only lesson rails and Research-only controls are
absent. Analyzer and Match Predictor must also have no Term Search button or
panel.

## 5. Learn index and track indexes

Test both `/learn/` and `/learn/cube/`.

### 5.1 Layout and typography

- The central content must not be unusually narrow at desktop or mobile width.
- Lesson titles should use the larger readable lesson-title size.
- Titles, descriptions, badges, and metadata must not overlap.
- Track titles and lesson counts should sit on the same baseline with compact
  spacing, not a large tab-sized gap.
- The lesson count shown beside each track title must match the visible lesson
  cards after clearing all filters.
- Collapse/expand controls should sit to the left and remain compact.
- Ordered lesson numbers should appear as `1.`, `2.`, `3.` using the surrounding
  font, immediately before the text. Roman numerals must not appear.
- Article and lesson descriptions should use normal body weight, not dark bold
  text.

### 5.2 Collapsible filters

- Filters start collapsed.
- The summary reads **Click to search and filter lessons** and uses a small
  disclosure triangle rather than a prominent button.
- Click, Enter, and Space should expand and collapse the disclosure.
- The disclosure must remain slim when closed.
- Opening it must not shift the page horizontally.
- Filter labels, inputs, and buttons must have visible keyboard focus.

### 5.3 Search ordering

Run separate searches that match:

1. a lesson title;
2. a description;
3. a category;
4. a tag or approved glossary term;
5. only prose in the lesson body.

Expected result:

- Title, description, category, tag, and approved highlighted-term matches rank
  before body-only matches.
- Search is case-insensitive and tolerates ordinary surrounding whitespace.
- A phrase match behaves as a phrase and does not require manually searching
  each word.
- A lesson appears only once even if several primary fields match.
- The visible count updates correctly.
- A no-result state is clear and does not leave stale cards visible.
- Clearing the query restores the original metadata-defined lesson order.

### 5.4 Filter combinations

- Select one difficulty, then combine it with a search query.
- Select a track or term filter where available.
- Confirm AND/OR behavior matches the labels and no disabled option can be
  activated.
- Clear filters and confirm every lesson returns in its original track.
- Refresh with filters open and confirm the page remains usable even if the
  disclosure resets.
- Term Search must be absent on the Learn index and all Learn track index pages.

## 6. Learn lesson desktop behavior

Use `/learn/cube/what-the-cube-is-asking.html` at 1440 x 1000 and 1024 x 768.

### 6.1 Learning Track rail

- The Learning Track rail is proportionally readable and larger than its old
  compact form without crowding the article.
- Lesson labels use ordinary decimal numbering; no Roman numerals remain.
- Active lesson highlighting identifies the current lesson.
- Every lesson link opens the correct lesson.
- The control is a sideways **Show Lessons/Hide** control, not a full-width
  collapse bar.
- Collapsing Lessons must not collapse the right TOC or Term Search.
- When Lessons are collapsed and the page scrolls down, **Show Lessons** moves
  close to the top of the viewport.
- When scrolling upward and the navbar returns, **Show Lessons** slides below
  the navbar.
- Click **Show Lessons**, then scroll upward. **Hide** must remain to the left of
  the left-sidebar divider, never centered over or to the right of the line.
- Repeated open/close and scroll cycles must not make the control drift.
- The article widens when the rail is hidden and returns without clipping when
  restored.

### 6.2 On This Page rail

- The heading and active-section state are visible at the page top.
- The compact collapse control is at the bottom of the TOC links and visually
  blends with the off-white page background.
- The page must not show a separate full-width **Collapse TOC**, **Collapse
  All**, X, or Distraction Free Mode control.
- Collapsing the TOC collapses its links and the Learning Track as currently
  designed, but Term Search remains independent.
- The collapsed state reads **Contents** with a centered disclosure glyph.
- Restoring it reveals links and Learning Track without moving the reader to
  the page top.
- Click three TOC anchors. Confirm the correct heading is reached and active
  highlighting updates.
- Scroll down and up. The right rail should hide and restore with scroll
  direction; its compact restoration control must continue to work after it
  reappears.

### 6.3 Term Search on a Learn lesson

- At the exact page top, the expanded lookup is visible beneath the page tools.
- It is right-aligned beside the article and approximately half the width of the
  available tools rail.
- The background matches the page rather than a contrasting cream panel.
- The collapsed control reads **Term Search** with a proper left arrow and uses
  muted grey.
- Scroll down: the expanded lookup collapses.
- Open it at mid-page, then scroll downward: it collapses.
- Open it again and scroll upward while remaining away from the top: it
  collapses.
- Return to the page top: it automatically opens.
- Opening or closing it must preserve the current reading position.
- Search a canonical term and an alias. Both should return the canonical term,
  full definition, aliases when present, related terms, and the glossary-entry
  link.
- Search an unknown term. The result should explain that no definition was
  found and offer the full Glossary search without throwing an error.
- Close and reopen it. Controls and keyboard focus should remain usable.

### 6.4 Continuous/infinite Learn loading

- Start on a lesson that has a following lesson in its generated track/order.
- Scroll to the continuation boundary and allow the next lesson to append.
- A loading operation should occur once, not repeatedly.
- The appended lesson must contain its title, body, rendered SVGs, disclosures,
  lesson navigation, highlighted terms, and working anchors.
- Continue until at least three lessons have been observed when the track has
  three available lessons.
- The address bar/history behavior must be understandable when crossing lesson
  boundaries; Back should not trap the user.
- The active Lessons item and On This Page state should follow the currently
  viewed article.
- IDs must remain unique after appending. Test an anchor and a disclosure in the
  appended article rather than only the initially loaded article.
- Term Search and sidebar controls must not be duplicated.
- No raw QMD/Markdown syntax, unprocessed shortcode, or source HTML should
  appear.
- Images and SVGs should lazy-load without causing large layout jumps.
- Reaching the final lesson must stop cleanly without a spinner or repeated
  network requests.

## 7. Learn lesson mobile behavior

Use 390 x 844 and a real phone if available.

- Desktop left and right rails and their fixed desktop buttons must be hidden.
- Article text must use the available width and remain readable.
- The narrow left-edge tools bar is present without covering text.
- Tap the bar and swipe from the left edge to open the mobile drawer.
- A mostly horizontal left-to-right swipe should open it; a vertical page swipe
  should not.
- The drawer contains the page TOC and Term Search beneath it.
- Use a TOC anchor; the drawer should close and the heading should be visible.
- Search a glossary term in the drawer and close it with Escape or the visible
  close control where available.
- The mobile navbar remains usable while the drawer is closed.
- Repeated opening, orientation changes, and continuous loading must not create
  duplicate drawers or freeze body scrolling.
- Wide tables scroll inside their container. SVGs scale to the article width.
- No desktop arrow or floating desktop lookup should appear over the article.

## 8. Cube worked-position component

Use `/learn/cube/what-the-cube-is-asking.html`.

- The first-level worked-position disclosure opens and closes with mouse and
  keyboard.
- Its initial SVG loads, has nonzero natural dimensions, and is not the wrong
  fixture answer.
- The explanatory sentence and second SVG render in the expected order.
- The available response buttons include the intended cube choices, including
  Take and Pass where specified.
- Selecting a button gives exactly one button selected/pressed state.
- Double/Roll and Pass/Take paths show the correct corresponding board and
  explanation.
- The nested disclosure opens independently and contains its SVG and two
  sentences.
- Repeated component instances receive independent controls and unique IDs.
- Opening or selecting one instance must not alter another instance.
- Collapse the outer disclosure while the nested disclosure is open, restore
  it, and confirm the component remains coherent.
- Repeat on mobile: buttons wrap, SVGs scale, and focus remains visible.

## 9. Real checker candidate fixture

Use `/learn/cube/why-is-25-percent-the-basic-take-point.html`.

### 9.1 Initial and candidate mapping

- The initial position SVG loads successfully.
- Record the displayed `position_id`, `state_hash`, and `analysis_id` if exposed
  by diagnostics; they must remain constant through selection.
- Select each of the three candidate buttons:
  - `8/4`;
  - `13/10 11/10`;
  - `13/10 8/7`.
- For each candidate confirm the move label, rank, SVG, equity, equity loss,
  supplied winning probabilities, and explanation or missing-value state change
  as one coherent set.
- The selected SVG must visibly match that candidate, not merely change its URL.
- The best-ranked candidate should have the appropriate best-play loss state.
- Missing optional probabilities and missing explanations should display a
  deliberate `Not supplied`-style state, never `undefined`, `NaN`, or an empty
  broken row.

### 9.2 Interaction contract

- Exactly one candidate button has `aria-pressed="true"`.
- Tab reaches each button in visual order.
- Enter and Space select candidates.
- Focus remains visible on buttons and disclosures.
- Selecting a candidate does not alter or reinterpret move notation in the
  browser; the rendered asset is selected from the fixture mapping.
- The retained-engine-analysis disclosure opens and restores with the correct
  expanded state.
- Reload the page and confirm the deterministic initial candidate and SVG.

### 9.3 Failure states

Use DevTools request blocking only in a disposable local test; do not edit the
authoritative fixture.

- Block one candidate SVG request and reload. The component should show a clear
  failure rather than silently displaying the previous candidate.
- Block the fixture JSON request and reload. A controlled fixture-load error
  should appear and the rest of the lesson must remain usable.
- Confirm the console error identifies the missing resource without causing a
  site-wide JavaScript initialization failure.
- Remove request blocking and reload; normal behavior must return.

## 10. Research articles

Test both representative Research routes at desktop and mobile widths.

### 10.1 Desktop rail

- Categories and tags appear at the top of the article in the intended rail.
- The compact rail control uses the same off-white background and muted color as
  the Learn controls.
- Scrolling down hides the right rail; scrolling up restores it.
- The restored control must remain usable and must not overlap the article.
- On This Page collapses to a compact **Contents** state and restores its links.
- TOC anchors and active-section highlighting work before and after restoration.
- Term Search is positioned beside the body, not at the far browser edge.
- Its width, scroll-collapse behavior, definitions, related terms, and page-
  position preservation match the Learn lesson behavior.
- Back to top sits beneath Term Search and works near the end of the page.

### 10.2 Continuous Research loading

- Scroll through a Research article until the next article is appended.
- Confirm only the expected next article loads and the request is not repeated.
- Titles, categories, tags, anchors, figures, citations, and related links remain
  correct in appended content.
- The TOC reflects the current article and does not become inert after the rail
  has auto-collapsed.
- Term Search, Back to top, and rail toggles are not duplicated.
- All appended IDs are unique.
- Reaching the final Research article stops cleanly.
- Browser Back/Forward remains understandable after article transitions.

### 10.3 Mobile Research

- Desktop rails are absent.
- The mobile edge drawer contains TOC plus Term Search.
- Tap and swipe opening both work; vertical scrolling does not trigger a false
  open.
- An anchor closes the drawer and reaches the correct heading.
- Appending the next article does not create a second drawer or horizontal
  overflow.

## 11. Glossary page

Use `/glossary/`. The approved public contract currently contains 12 canonical
entries and 3 aliases; if the approved source changes, update these expected
counts before using this plan.

### 11.1 Initial page and generated content

- The canonical route is `/glossary/`; `/learn/glossary/` is not used as the
  live source page.
- No Learn lesson sidebar appears.
- One canonical card/disclosure exists for each approved term; aliases do not
  create duplicate visible entries.
- Letter counts and the total result count agree with visible approved entries.
- Entries start collapsed while letter groups are usable.
- Each entry displays its canonical name, aliases when present, short
  definition, full definition, categories, available related terms, and related
  lessons.
- Full definitions—not short tooltip definitions—appear on the Glossary page.
- Collapse all and Expand all affect the letter sections consistently.
- No `glossary_old`, `glossary_wip`, internal-only, candidate-only, or
  unapproved definition appears in the rendered public page.

### 11.2 Main Glossary search and filters

- Search a canonical term, an alias, a phrase from a short definition, and a
  phrase from a full definition.
- The best canonical/alias/name match should appear before definition-only
  matches.
- Searching `Ten in the Zone` should resolve to `10 in the Zone` without a
  duplicate alias card.
- The best matching disclosure should open and show its full definition.
- Combine a category with a search query, then add a learning-track filter.
- Counts, enabled/disabled filters, and the no-result state must remain correct.
- Reset restores alphabetical order, clears the query-string filters, and
  restores all approved entries.
- Refresh a `?q=` URL and confirm the search state is reconstructed.
- A canonical `#term-slug` link opens the intended entry.

### 11.3 Glossary Term Search behavior

Desktop expectations:

- On first arrival at scroll position zero, the floating Term Search is
  collapsed and positioned near the top-right rather than the bottom.
- Scroll more than 32 pixels: Term Search opens near the top.
- Return to the exact page top: it collapses again.
- Its opening and closing must not obscure the main Glossary search on common
  desktop widths.
- Search for `active builder`; the lookup input, heading, and full definition
  must all show Active Builder.
- The old separate Glossary definition sidebar must remain hidden when the Term
  Search lookup is available.

Related-term expectations:

1. Open `10 in the Zone`.
2. Click the inline **active builders** phrase in its full definition.
3. Confirm the Term Search input becomes `Active Builder`.
4. Confirm the full Active Builder definition appears in that lookup.
5. Confirm the page does not jump to the main Glossary search at the top.
6. Repeat using **Active Builder** under **See also**.
7. Click another related term from the lookup; it should replace the result in
   place.
8. Click **Go to glossary entry**; only this explicit action should navigate to
   or scroll to the canonical entry.

On mobile, confirm the page remains usable and the desktop scroll-triggered
auto-open does not cover the content. The main search, filters, term entries,
and related links must remain keyboard/touch accessible.

## 12. Inline glossary highlighting on Learn and Research

Use the cube lesson for known highlighted phrases, then one Research article
that declares highlighted terms.

- Only terms listed in approved `highlighted-terms` metadata are marked inline.
- The first safe occurrence is highlighted; headings, existing links, code,
  scripts, styles, and the term's own definition are not incorrectly nested or
  re-highlighted.
- When phrases overlap, the longest approved phrase wins.
- Matching is case-insensitive but does not match inside a larger word.
- Hover or keyboard focus shows the canonical short definition.
- Leaving hover or focus closes the tooltip.
- The tooltip stays inside the viewport near all four window edges.
- Clicking the phrase opens the full definition in Term Search without moving
  the reading position to the top.
- The lookup input receives the canonical term even when an alias or inflected
  approved phrase was clicked.
- The selected term or one of its aliases must not be hover-linked inside its
  own displayed definition; other approved glossary phrases may remain
  interactive.
- Repeat after a lesson or Research article has loaded continuously to ensure
  appended content is initialized exactly once.
- On touch devices, tapping a highlighted term must provide an understandable
  route to the definition without requiring hover.

## 13. Analyzer, Match Predictor, and ordinary pages

### 13.1 Analyzer

- `/analyze/` loads the board/analyzer interface and its help text.
- Pasting a valid XGID produces the expected position preview.
- Invalid or empty input produces a controlled message.
- The analyzer card is beside the body at desktop width and does not force the
  article narrow.
- Term Search and its arrow/toggle are completely absent.
- Learn/Research rail auto-collapse code must not affect the analyzer.

### 13.2 Match Predictor

- `/match-predictor/` loads its dashboard/embedded content or documented
  fallback.
- Primary dashboard links are visibly clickable and keyboard reachable.
- The full-width layout has no horizontal page overflow.
- Term Search and its arrow/toggle are completely absent.
- Learn/Research rail behavior must not appear.

### 13.3 Engine Benchmark and other ordinary content

- Engine Benchmark and Research landing pages retain their expected article
  width and cards.
- If a page legitimately uses a shared Term Search, it appears beside the body,
  not at the far viewport edge.
- Homepage, landing pages, About, and Updates do not acquire lesson numbering,
  continuous-loading sentinels, mobile drawers, or sidebar controls.

## 14. Accessibility and input methods

Perform this section without a mouse.

- Tab order follows the visual order and does not enter hidden rails, drawers,
  disclosures, or lookup panels.
- Every custom button has visible focus.
- Enter and Space activate buttons and summaries as expected.
- Escape closes open mobile drawers, tooltips, and dismissible lookup panels
  where supported.
- Sidebar, TOC, disclosure, and drawer buttons expose accurate `aria-expanded`
  and `aria-controls` states.
- The selected checker/cube choice exposes its pressed state.
- Search result and lookup updates are announced through their live regions
  without repeatedly announcing unrelated content.
- Headings remain hierarchical and each page has one useful main landmark and
  one H1.
- Muted-grey text and controls remain legible against the off-white page
  background.
- Links can be distinguished without relying only on color.
- At 200% browser zoom, essential controls remain reachable and text does not
  overlap.
- With reduced-motion enabled, the interface remains usable even if transitions
  are shortened or removed.

## 15. Browser history, anchors, and direct URLs

- Directly open a Learn heading fragment, Research heading fragment, and
  Glossary canonical term fragment.
- Each target should be visible below the navbar and should receive the expected
  expanded state.
- Use a Glossary `?q=` URL, then follow a related term and use Back.
- Use Back after a continuously appended lesson or Research transition.
- Reload at mid-page and confirm controls initialize without null-reference
  errors or duplicate toggles.
- Open a route with and without trailing slash where supported; canonical links
  should remain consistent.
- Visit the deliberate missing route and confirm the custom 404 page has working
  Home, Learn, Research, and Glossary links.

## 16. Build-generated Glossary, RSS, and social output

Run after a full build that includes glossary generation and social cards.

### 16.1 Glossary source contract

- Compare the approved source entry count with `/glossary/`, the generated
  lookup JSON, and the generated glossary data JSON.
- Confirm aliases resolve to one canonical slug.
- Confirm short definitions power hover/lookup summaries where intended and
  full definitions power Glossary cards and expanded lookup results.
- Confirm related lesson/research backlinks use approved metadata only.
- Confirm no private notes, candidate-only terms, source paths, or validation
  annotations appear publicly.

### 16.2 RSS/Updates

- Open `/updates/index.xml` directly and validate that it is well-formed XML.
- Confirm newly approved or changed Glossary definitions appear in the Updates
  feed after the build.
- Confirm each Glossary update links to `/glossary/#canonical-slug` rather than
  an obsolete standalone term page.
- Confirm titles, descriptions, publication dates, and links contain no raw HTML
  escaping errors.
- Confirm existing non-Glossary update items remain present and correctly
  ordered.

### 16.3 Sitemap, redirects, and social cards

- Search the sitemap for every approved canonical Glossary anchor/route policy
  required by the build contract and confirm obsolete dirty URLs are absent.
- Confirm the legacy Glossary redirect reaches `/glossary/` without a loop.
- Open representative social images for Home, Learn, Research, Glossary, and one
  article. Images must load at the expected dimensions with unclipped text.
- Inspect the rendered page metadata for canonical URL, Open Graph image, title,
  and description.
- Confirm a partial development render did not accidentally mark a full release
  build as complete.

## 17. Performance and resilience

- Reload representative pages with cache disabled. Local JavaScript, CSS, JSON,
  fonts, and SVGs should return successfully.
- Reload again with cache enabled. Navigation and controls should initialize
  normally from cache.
- Throttle to a slow connection and confirm continuous loading displays a stable
  state and does not fire duplicate requests.
- Scroll quickly up/down across navbar and sidebar thresholds. Controls should
  settle into one correct state without flicker, drift, or overlap.
- Resize repeatedly across the 992px desktop boundary. Desktop rails and the
  mobile drawer should never be visible simultaneously.
- Open, close, and reopen each major disclosure at least five times. Event
  handlers should not duplicate.
- Leave a lesson or Research page open through several appended articles and
  confirm memory symptoms, repeated console messages, or ever-growing duplicate
  controls are not obvious.
- Print preview one article and confirm fixed navigation/tools do not cover the
  printed content.

## 18. Public-site post-deploy pass

After `gh-pages` is published, repeat the smoke pass against the public URL.
Also verify:

- The deployed commit corresponds to the approved `master` commit.
- Home, Learn, one lesson, one Research article, Glossary, Analyzer, Match
  Predictor, Updates XML, checker JSON, and all checker SVG assets return 200.
- A hard refresh and private/incognito window do not show stale CSS or
  JavaScript.
- GitHub Pages base-path handling does not break root-relative links.
- Glossary related-term clicks and inline highlighted terms use the deployed
  lookup JSON successfully.
- Continuous loading requests deployed HTML rather than local-only paths.
- Social-card URLs are public and cacheable.
- The browser console and network panel contain no unexpected 404/500 responses.

## 19. Pass/fail severity

- **Blocking:** build/page failure, initialization exception, wrong checker SVG
  for a candidate, inaccessible core content, broken public JSON/SVG, duplicate
  IDs after continuous loading, page-level horizontal overflow, or a broken
  internal route.
- **Important:** unexpected jump to the top, inactive TOC control, incorrect
  scroll-direction behavior, sidebar overlap, desktop controls on mobile,
  missing keyboard operation, wrong full/short definition, or stale search
  ordering.
- **Minor:** small spacing, color, or alignment issue that does not impede use.
- **Passed:** expected result is reproducible at the required viewports and no
  relevant console/network error appears.

Do not release with Blocking findings. Resolve in-scope Important findings or
record and obtain explicit approval before release.

## 20. Manual test report template

```text
Branch and commit:
Build and preview command:
Browsers/devices/viewports:
Routes tested:

Passed:
-

Blocking findings:
- None

Important findings:
- None

Minor findings:
- None

Console errors:
- None

Network/resource failures:
- None

Screenshots taken for defects:
- None

Generated/untracked artifacts:
-

Recommendation: Release / Fix and retest / Ask for direction
```
