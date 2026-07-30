import { readFileSync } from "node:fs";

const manifestUrl = new URL("./ui_release_manifest.json", import.meta.url);

export const DEFAULT_MANIFEST = JSON.parse(
  readFileSync(manifestUrl, "utf8")
);

const delay = (milliseconds) =>
  new Promise((resolve) => setTimeout(resolve, milliseconds));

const visibleLocator = async (locator) => {
  const count = await locator.count();
  for (let index = 0; index < count; index += 1) {
    const candidate = locator.nth(index);
    if (await candidate.isVisible()) {
      return candidate;
    }
  }
  return null;
};

const clickInPlace = async (tab, locator) => {
  const point = await locator.evaluate((element) => {
    const rectangle = element.getBoundingClientRect();
    return {
      x: rectangle.left + rectangle.width / 2,
      y: rectangle.top + rectangle.height / 2
    };
  });
  await tab.cua.click(point);
};

const pagePosition = (tab) =>
  tab.playwright.locator("html").evaluate(() => ({
    clientHeight: document.documentElement.clientHeight,
    clientWidth: document.documentElement.clientWidth,
    scrollHeight: document.documentElement.scrollHeight,
    scrollWidth: document.documentElement.scrollWidth,
    scrollY: window.scrollY
  }));

const scrollTo = async (tab, position) => {
  await tab.playwright.locator("html").evaluate(
    (_element, target) => {
      window.scrollTo(0, target);
    },
    position
  );
  await delay(120);
};

const countVisible = async (locator) => {
  const count = await locator.count();
  let visible = 0;
  for (let index = 0; index < count; index += 1) {
    if (await locator.nth(index).isVisible()) {
      visible += 1;
    }
  }
  return visible;
};

const duplicateIds = (tab) =>
  tab.playwright.locator("html").evaluate(() => {
    const counts = new Map();
    document.querySelectorAll("[id]").forEach((element) => {
      if (element.closest(".quarto-sidebar-toggle-contents")) {
        return;
      }
      counts.set(element.id, (counts.get(element.id) || 0) + 1);
    });
    return Array.from(counts)
      .filter((entry) => entry[1] > 1)
      .map((entry) => entry[0])
      .sort();
  });

const interactWithLookup = async (tab, check, context) => {
  await scrollTo(tab, 320);
  const toggle = await visibleLocator(
    tab.playwright.locator(
      "[data-bms-site-term-toggle], [data-bms-mobile-term-toggle]"
    )
  );
  if (!toggle) {
    check(false, context, "term lookup reveal control is missing");
    return;
  }
  check(
    (await toggle.getAttribute("aria-expanded")) === "false",
    context,
    "term lookup is initially collapsed"
  );
  const before = (await pagePosition(tab)).scrollY;
  await clickInPlace(tab, toggle);
  await delay(250);
  const afterOpen = (await pagePosition(tab)).scrollY;
  check(
    Math.abs(afterOpen - before) <= 32,
    context,
    "opening term lookup preserves scroll position " +
      `(before=${before}, after=${afterOpen})`
  );
  const close = await visibleLocator(
    tab.playwright.locator("[data-bms-term-lookup-close]")
  );
  check(Boolean(close), context, "term lookup close control is available");
  if (close) {
    await clickInPlace(tab, close);
    await delay(250);
    const afterClose = (await pagePosition(tab)).scrollY;
    check(
      Math.abs(afterClose - before) <= 32,
      context,
      "closing term lookup preserves scroll position " +
        `(before=${before}, after=${afterClose})`
    );
  }
};

const interactWithToc = async (tab, check, context, desktop) => {
  const toggle = await visibleLocator(
    tab.playwright.locator("[data-bms-toc-heading-toggle]")
  );
  if (!desktop) {
    check(!toggle, context, "desktop TOC heading control stays hidden");
    return;
  }
  check(Boolean(toggle), context, "compact TOC heading control is visible");
  if (!toggle) {
    return;
  }
  await toggle.click();
  check(
    (await toggle.getAttribute("aria-expanded")) === "false",
    context,
    "TOC links collapse"
  );
  await toggle.click();
  check(
    (await toggle.getAttribute("aria-expanded")) === "true",
    context,
    "TOC links restore"
  );
};

const interactWithLessonTrack = async (tab, check, context, desktop) => {
  const toggle = await visibleLocator(
    tab.playwright.locator("[data-bms-lesson-track-toggle]")
  );
  if (!desktop) {
    check(!toggle, context, "desktop lesson-track control stays hidden");
    return;
  }
  check(Boolean(toggle), context, "lesson-track sideways control is visible");
  if (!toggle) {
    return;
  }
  const initiallyExpanded =
    (await toggle.getAttribute("aria-expanded")) === "true";
  await toggle.click();
  check(
    (await toggle.getAttribute("aria-expanded")) !==
      String(initiallyExpanded),
    context,
    "lesson track changes state"
  );
  await toggle.click();
  check(
    (await toggle.getAttribute("aria-expanded")) ===
      String(initiallyExpanded),
    context,
    "lesson track restores independently"
  );
};

const interactWithLearnIndex = async (tab, check, context) => {
  const filters = tab.playwright.locator("[data-bms-learn-filters]");
  check((await filters.count()) === 1, context, "lesson filters exist");
  if ((await filters.count()) !== 1) {
    return;
  }
  check(
    (await filters.getAttribute("open")) === null,
    context,
    "lesson filters default collapsed"
  );
  await filters.locator(":scope > summary").click();
  check(
    (await filters.getAttribute("open")) !== null,
    context,
    "lesson filters expand"
  );
  const input = filters.locator("[data-bms-learn-search]");
  const items = tab.playwright.locator("[data-bms-learn-item]");
  const total = await items.count();
  await input.fill("What the Cube Is Really Asking");
  await delay(80);
  const visible = await countVisible(items);
  check(
    visible >= 1 && visible < total,
    context,
    "lesson search narrows the catalogue"
  );
  const clear = await visibleLocator(
    filters.locator("[data-bms-learn-clear]")
  );
  check(Boolean(clear), context, "lesson search exposes its clear control");
  if (clear) {
    await clear.click();
    check(
      (await countVisible(items)) === total,
      context,
      "clearing search restores lessons"
    );
  }
};

const interactWithRichFixture = async (tab, check, context) => {
  const summary = tab.playwright.locator(
    "details.bms-scroll-fixture-disclosure > summary"
  );
  check((await summary.count()) === 1, context, "rich disclosure exists");
  if ((await summary.count()) !== 1) {
    return;
  }
  await summary.click();
  check(
    (await tab.playwright.locator(".bms-scroll-fixture-svg").count()) === 2,
    context,
    "two SVG positions render"
  );
  const choices = tab.playwright.locator(
    ".bms-scroll-fixture-disclosure .bms-answer-choice"
  );
  check((await choices.count()) === 4, context, "four position choices render");
  const take = tab.playwright.getByRole("button", {
    name: "Take",
    exact: true
  });
  await take.click();
  check(
    (await take.getAttribute("aria-pressed")) === "true",
    context,
    "Take records its pressed state"
  );
  check(
    (await tab.playwright
      .locator("#bms-scroll-fixture-follow-up")
      .getAttribute("open")) !== null,
    context,
    "choice opens the nested explanation"
  );
};

const interactWithEdgeFixture = async (tab, check, context) => {
  const fixture = tab.playwright.locator("[data-bms-ui-edge-fixture]");
  check((await fixture.count()) === 1, context, "edge fixture renders once");
  if ((await fixture.count()) !== 1) {
    return;
  }
  const longChoice = tab.playwright.getByRole("button", {
    name: "Keep playing with this unusually long choice label",
    exact: true
  });
  await longChoice.click();
  check(
    (await longChoice.getAttribute("aria-pressed")) === "true",
    context,
    "long action label remains clickable"
  );
  const panel = tab.playwright.locator("#bms-ui-edge-response");
  check(
    (await panel.getAttribute("open")) !== null,
    context,
    "edge layout panel opens"
  );
  const region = tab.playwright.locator(".bms-ui-edge-scroll-region");
  const regionMetrics = await region.evaluate((element) => ({
    clientWidth: element.clientWidth,
    scrollWidth: element.scrollWidth
  }));
  check(
    regionMetrics.scrollWidth > regionMetrics.clientWidth,
    context,
    "wide table is contained in its own scroll region"
  );
  await tab.playwright
    .locator('a[href="#bms-ui-edge-anchor"]')
    .click();
  check(
    (await tab.url()).endsWith("#bms-ui-edge-anchor"),
    context,
    "fixture anchor navigation works"
  );
};

const interactWithGlossary = async (tab, check, context) => {
  const input = tab.playwright.locator("[data-bms-glossary-search]");
  check((await input.count()) === 1, context, "glossary search exists");
  if ((await input.count()) !== 1) {
    return;
  }
  const entries = tab.playwright.locator("[data-bms-glossary-entry]");
  const total = await entries.count();
  await input.fill("active builder");
  await delay(100);
  const visible = await countVisible(entries);
  check(
    visible >= 1 && visible < total,
    context,
    "glossary search narrows full definitions"
  );
  const clear = await visibleLocator(
    tab.playwright.locator("[data-bms-glossary-clear]")
  );
  if (clear) {
    await clear.click();
    check(
      (await countVisible(entries)) === total,
      context,
      "glossary clear restores full definitions"
    );
  } else {
    check(false, context, "glossary clear control is missing");
  }
};

const runPageInteraction = async ({
  tab,
  page,
  viewport,
  check
}) => {
  const context = `${viewport.name}/${page.id}`;
  const desktop = viewport.width >= 992;
  if (page.kind === "learn-index") {
    await interactWithLearnIndex(tab, check, context);
  }
  if (page.kind === "learn-lesson") {
    await interactWithLessonTrack(tab, check, context, desktop);
    await interactWithToc(tab, check, context, desktop);
    await interactWithLookup(tab, check, context);
    await interactWithRichFixture(tab, check, context);
  }
  if (page.kind === "rich-scroll-fixture") {
    await interactWithRichFixture(tab, check, context);
  }
  if (page.kind === "edge-scroll-fixture") {
    await interactWithEdgeFixture(tab, check, context);
  }
  if (page.kind === "research-article") {
    await interactWithToc(tab, check, context, desktop);
    await interactWithLookup(tab, check, context);
  }
  if (page.kind === "glossary") {
    await interactWithGlossary(tab, check, context);
  }
};

const clickThroughNavigation = async ({
  tab,
  browser,
  viewport,
  desktop,
  baseUrl,
  check
}) => {
  await tab.goto(new URL("/about.html", baseUrl).href);
  await delay(250);
  const learnLink = await visibleLocator(
    tab.playwright.getByRole("link", { name: "Learn", exact: true })
  );
  check(Boolean(learnLink), "desktop/click-through", "Learn nav link is visible");
  if (!learnLink) {
    return;
  }
  await learnLink.click();
  await delay(300);
  check(
    new URL(await tab.url()).pathname === "/learn/",
    "desktop/click-through",
    "navbar click reaches Learn"
  );
  let cubeTab = tab;
  if (browser) {
    cubeTab = await browser.tabs.new();
    await viewport.set({ width: desktop.width, height: desktop.height });
    await cubeTab.goto(new URL("/learn/", baseUrl).href);
    await delay(300);
  }
  const cubeLink = await visibleLocator(
    cubeTab.playwright.getByRole("link", {
      name: "The Doubling Cube",
      exact: true
    })
  );
  check(Boolean(cubeLink), "desktop/click-through", "Cube track link is visible");
  if (!cubeLink) {
    return cubeTab;
  }
  await cubeLink.click();
  await delay(300);
  check(
    new URL(await cubeTab.url()).pathname === "/learn/cube/",
    "desktop/click-through",
    "Learn click reaches the Cube track"
  );
  return cubeTab;
};

export const summarizeReport = (report) => ({
  passed: report.failures.length === 0,
  pages: report.pages,
  checks: report.checks,
  failures: report.failures.length,
  consoleMessages: report.consoleMessages.length,
  durationMs: report.durationMs
});

export async function runReleaseUiChecks({
  browser,
  tab,
  viewport,
  baseUrl,
  manifest = DEFAULT_MANIFEST
}) {
  if ((!browser && !tab) || !viewport || !baseUrl) {
    throw new Error("browser or tab, plus viewport and baseUrl, are required");
  }
  const started = Date.now();
  const failures = [];
  const consoleMessages = [];
  let checks = 0;
  let pages = 0;
  const check = (condition, context, message) => {
    checks += 1;
    if (!condition) {
      failures.push({ context, message });
    }
  };
  const acquireTab = async () => {
    if (!browser) {
      return tab;
    }
    await browser.tabs.finalize();
    return browser.tabs.new();
  };
  const collectConsole = async (activeTab, context) => {
    try {
      const logs = await activeTab.dev.logs();
      for (const entry of logs) {
        const text =
          typeof entry === "string" ? entry : JSON.stringify(entry);
        consoleMessages.push(text);
        if (/(TypeError|ReferenceError|Uncaught|console\.error)/i.test(text)) {
          failures.push({ context, message: text });
        }
      }
    } catch (error) {
      failures.push({
        context,
        message: `could not read console logs: ${String(error)}`
      });
    }
  };

  try {
    for (const viewportCase of manifest.viewports) {
      await viewport.set({
        width: viewportCase.width,
        height: viewportCase.height
      });
      for (const page of manifest.pages) {
        const context = `${viewportCase.name}/${page.id}`;
        pages += 1;
        const activeTab = await acquireTab();
        try {
          await viewport.set({
            width: viewportCase.width,
            height: viewportCase.height
          });
          await activeTab.goto(new URL(page.route, baseUrl).href);
          await delay(500);

          check(
            (await activeTab.playwright.locator("main").count()) === 1,
            context,
            "page has one main landmark"
          );
          check(
            (await activeTab.playwright.locator("h1").count()) >= 1,
            context,
            "page has an H1"
          );
          const initialMetrics = await pagePosition(activeTab);
          check(
            initialMetrics.scrollWidth <= initialMetrics.clientWidth + 1,
            context,
            "page has no horizontal overflow"
          );

          await runPageInteraction({
            tab: activeTab,
            page,
            viewport: viewportCase,
            check
          });

          await scrollTo(
            activeTab,
            Math.floor(initialMetrics.scrollHeight / 2)
          );
          const markersBeforeScroll = page.kind.includes("scroll-fixture")
            ? await activeTab.playwright
                .locator(".bms-learn-scroll-lesson-marker")
                .count()
            : 0;
          await scrollTo(activeTab, Number.MAX_SAFE_INTEGER);
          await delay(
            page.kind.includes("scroll-fixture") ? 2500 : 180
          );
          let bottomMetrics = await pagePosition(activeTab);
          if (page.kind.includes("scroll-fixture")) {
            const markersAfterScroll = await activeTab.playwright
              .locator(".bms-learn-scroll-lesson-marker")
              .count();
            check(
              markersAfterScroll > markersBeforeScroll,
              context,
              "continuous scrolling appends the next lesson"
            );
            await scrollTo(activeTab, Number.MAX_SAFE_INTEGER);
            await delay(500);
            const navigationState = await activeTab.playwright
              .locator("html")
              .evaluate(() => ({
                activeSidebarLinks: document.querySelectorAll(
                  "#quarto-sidebar a.active[href]"
                ).length,
                activeTocLinks: document.querySelectorAll(
                  "#TOC a.nav-link.active"
                ).length,
                tocLinks: document.querySelectorAll("#TOC a[href]").length
              }));
            check(
              navigationState.activeSidebarLinks >= 1,
              context,
              "continuous scrolling keeps an active lesson in the sidebar"
            );
            check(
              navigationState.tocLinks >= 1 &&
                navigationState.activeTocLinks >= 1,
              context,
              "continuous scrolling keeps an active populated TOC"
            );
            bottomMetrics = await pagePosition(activeTab);
          }
          if (bottomMetrics.scrollHeight > bottomMetrics.clientHeight + 1) {
            check(
              bottomMetrics.scrollY > 0,
              context,
              "page scrolls toward the bottom"
            );
          }
          check(
            bottomMetrics.scrollWidth <= bottomMetrics.clientWidth + 1,
            context,
            "page remains free of horizontal overflow after interactions"
          );
          const duplicates = await duplicateIds(activeTab);
          check(
            duplicates.length === 0,
            context,
            duplicates.length
              ? `duplicate IDs after scrolling: ${duplicates.join(", ")}`
              : "IDs remain unique after scrolling"
          );

          const backToTop = await visibleLocator(
            activeTab.playwright.locator(
              "[data-bms-site-back-to-top], [data-bms-glossary-back-to-top]"
            )
          );
          if (backToTop && bottomMetrics.scrollY > 0) {
            await backToTop.click();
            await delay(1200);
            check(
              (await pagePosition(activeTab)).scrollY <= 80,
              context,
              "back-to-top returns near the page start"
            );
          }
        } catch (error) {
          failures.push({
            context,
            message: `browser helper error: ${String(error)}`
          });
        } finally {
          await collectConsole(activeTab, `${context}/console`);
        }
      }
    }

    const desktop = manifest.viewports.find(
      (item) => item.width >= 992
    );
    if (desktop) {
      const clickTab = await acquireTab();
      let finalClickTab = clickTab;
      try {
        await viewport.set({ width: desktop.width, height: desktop.height });
        finalClickTab =
          (await clickThroughNavigation({
            tab: clickTab,
            browser,
            viewport,
            desktop,
            baseUrl,
            check
          })) || clickTab;
      } catch (error) {
        failures.push({
          context: "desktop/click-through",
          message: `browser helper error: ${String(error)}`
        });
      } finally {
        await collectConsole(clickTab, "desktop/click-through/console");
        if (finalClickTab !== clickTab) {
          await collectConsole(
            finalClickTab,
            "desktop/click-through-cube/console"
          );
        }
      }
    }
  } finally {
    await viewport.reset();
    if (browser) {
      await browser.tabs.finalize();
    }
  }

  const report = {
    version: manifest.version,
    baseUrl,
    pages,
    checks,
    failures,
    consoleMessages,
    durationMs: Date.now() - started
  };
  return {
    ...report,
    summary: summarizeReport(report)
  };
}
