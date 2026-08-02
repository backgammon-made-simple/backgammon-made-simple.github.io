import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";

const manifestUrl = new URL("./ui_release_manifest.json", import.meta.url);

export const DEFAULT_MANIFEST = JSON.parse(
  readFileSync(manifestUrl, "utf8")
);

const delay = (milliseconds) =>
  new Promise((resolve) => setTimeout(resolve, milliseconds));

const safeName = (value) => value.replace(/[^a-z0-9-]+/gi, "-").toLowerCase();

const accessibilitySnapshot = (tab) =>
  tab.playwright.locator("html").evaluate(() => {
    const visible = (element) => {
      const style = window.getComputedStyle(element);
      const rectangle = element.getBoundingClientRect();
      return (
        style.display !== "none" &&
        style.visibility !== "hidden" &&
        rectangle.width > 0 &&
        rectangle.height > 0
      );
    };
    const describe = (element) =>
      element.id ||
      element.getAttribute("name") ||
      element.getAttribute("aria-label") ||
      element.tagName.toLowerCase();
    const allIds = Array.from(document.querySelectorAll("[id]"), (item) => item.id);
    const duplicateIds = Array.from(
      new Set(allIds.filter((id, index) => allIds.indexOf(id) !== index))
    ).sort();
    const headings = Array.from(document.querySelectorAll("h1,h2,h3,h4,h5,h6"))
      .filter(visible)
      .map((heading) => Number(heading.tagName.slice(1)));
    const headingSkips = headings
      .map((level, index) => ({ from: headings[index - 1], to: level }))
      .filter((item, index) => index > 0 && item.to > item.from + 1);
    const controls = Array.from(
      document.querySelectorAll("a[href],button,input,select,textarea,[tabindex]")
    ).filter(visible);
    const clippedControls = controls
      .filter((element) => {
        const rectangle = element.getBoundingClientRect();
        const inVerticalViewport =
          rectangle.bottom > 0 && rectangle.top < window.innerHeight;
        return (
          inVerticalViewport &&
          (rectangle.left < -1 || rectangle.right > window.innerWidth + 1)
        );
      })
      .slice(0, 20)
      .map(describe);
    const unlabeledControls = Array.from(
      document.querySelectorAll("input:not([type='hidden']),select,textarea")
    )
      .filter(visible)
      .filter((element) => {
        const id = element.id;
        return !(
          element.getAttribute("aria-label") ||
          element.getAttribute("aria-labelledby") ||
          (id && document.querySelector(`label[for='${CSS.escape(id)}']`)) ||
          element.closest("label")
        );
      })
      .map(describe);
    const missingImageAlt = Array.from(document.querySelectorAll("img"))
      .filter((image) => !image.hasAttribute("alt"))
      .slice(0, 20)
      .map((image) => image.getAttribute("src") || "img");
    const failedImages = Array.from(document.images)
      .filter((image) => image.complete && image.naturalWidth === 0)
      .slice(0, 20)
      .map((image) => image.currentSrc || image.src);
    const failedStylesheets = Array.from(
      document.querySelectorAll("link[rel='stylesheet']")
    )
      .filter((link) => !link.sheet && new URL(link.href).origin === window.location.origin)
      .slice(0, 20)
      .map((link) => link.href);
    const resourceFailures = window.performance
      .getEntriesByType("resource")
      .filter((entry) => Number(entry.responseStatus || 0) >= 400)
      .slice(0, 20)
      .map((entry) => ({ name: entry.name, status: entry.responseStatus }));
    const fixedOrSticky = Array.from(document.querySelectorAll("body *"))
      .filter(visible)
      .filter((element) => {
        const position = window.getComputedStyle(element).position;
        return position === "fixed" || position === "sticky";
      });
    const coveredTargets = controls
      .concat(Array.from(document.querySelectorAll("h1,h2,h3")).filter(visible))
      .filter((element) => {
        const rectangle = element.getBoundingClientRect();
        if (
          rectangle.bottom <= 0 ||
          rectangle.top >= window.innerHeight ||
          rectangle.right <= 0 ||
          rectangle.left >= window.innerWidth
        ) {
          return false;
        }
        const x = Math.max(0, Math.min(window.innerWidth - 1, rectangle.left + rectangle.width / 2));
        const y = Math.max(0, Math.min(window.innerHeight - 1, rectangle.top + rectangle.height / 2));
        const covering = document.elementFromPoint(x, y);
        return fixedOrSticky.some(
          (overlay) => overlay !== element && overlay.contains(covering) && !overlay.contains(element)
        );
      })
      .slice(0, 20)
      .map(describe);
    return {
      duplicateIds,
      failedImages,
      failedStylesheets,
      resourceFailures,
      clippedControls,
      coveredTargets,
      focusableControls: controls.filter(
        (element) => !element.hasAttribute("disabled") && element.tabIndex >= 0
      ).length,
      headingSkips,
      h1Count: headings.filter((level) => level === 1).length,
      landmarks: {
        main: document.querySelectorAll("main,[role='main']").length,
        navigation: document.querySelectorAll("nav,[role='navigation']").length,
        footer: document.querySelectorAll("footer,[role='contentinfo']").length
      },
      missingImageAlt,
      unlabeledControls,
      viewport: {
        clientWidth: document.documentElement.clientWidth,
        scrollWidth: document.documentElement.scrollWidth
      }
    };
  });

const focusSnapshot = async (tab) => {
  const body = tab.playwright.locator("body");
  if ((await body.count()) !== 1) {
    return { distinct: 0, missingIndicators: ["body unavailable"] };
  }
  const identities = [];
  const missingIndicators = [];
  for (let index = 0; index < 8; index += 1) {
    await body.press("TAB");
    const state = await tab.playwright.locator("html").evaluate(() => {
      const active = document.activeElement;
      if (!active || active === document.body) {
        return { identity: "body", visibleIndicator: false };
      }
      const style = window.getComputedStyle(active);
      const identity =
        active.id ||
        active.getAttribute("data-bms-analysis-choice") ||
        active.getAttribute("aria-label") ||
        active.textContent.trim().slice(0, 80) ||
        active.tagName.toLowerCase();
      const visibleIndicator =
        (style.outlineStyle !== "none" && Number.parseFloat(style.outlineWidth) > 0) ||
        style.boxShadow !== "none" ||
        style.borderColor !== "rgba(0, 0, 0, 0)";
      return { identity, visibleIndicator };
    });
    identities.push(state.identity);
    if (!state.visibleIndicator) {
      missingIndicators.push(state.identity);
    }
  }
  return {
    distinct: new Set(identities.filter((identity) => identity !== "body")).size,
    missingIndicators: Array.from(new Set(missingIndicators)).sort()
  };
};

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

const duplicateIds = (tab, rootSelector = "html") =>
  tab.playwright.locator(rootSelector).evaluate((root) => {
    const counts = new Map();
    root.querySelectorAll("[id]").forEach((element) => {
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

const interactWithLookup = async (
  tab,
  check,
  context,
  desktop,
  openAtTopOnly = false
) => {
  if (desktop) {
    const openLookup = await visibleLocator(
      tab.playwright.locator("[data-bms-term-lookup]")
    );
    check(
      Boolean(openLookup),
      context,
      "desktop term lookup is open at the top of the page"
    );
    if (openAtTopOnly) {
      return;
    }
  }
  await scrollTo(tab, 1400);
  await delay(700);
  await scrollTo(tab, 900);
  await delay(700);
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
    tab.playwright.locator(".bms-term-lookup-close")
  );
  if (close) {
    await clickInPlace(tab, close);
    await delay(250);
  }
};

const interactWithMobileDrawer = async (tab, check, context) => {
  const edge = await visibleLocator(
    tab.playwright.locator("[data-bms-mobile-tools-edge]")
  );
  check(Boolean(edge), context, "mobile page-tools edge bar is visible");
  if (!edge) {
    return;
  }
  check(
    (await edge.textContent()).trim() === "",
    context,
    "mobile edge bar has no arrow or visible label"
  );
  await edge.click();
  const drawer = await visibleLocator(
    tab.playwright.locator("[data-bms-mobile-tools-drawer]")
  );
  check(Boolean(drawer), context, "mobile page-tools drawer opens");
  if (!drawer) {
    return;
  }
  check(
    (await drawer.locator("a[href]").count()) >= 1,
    context,
    "mobile drawer contains table-of-contents links"
  );
  check(
    (await drawer.locator("[data-bms-term-lookup]").count()) === 1,
    context,
    "mobile drawer contains term search beneath the TOC"
  );
  const close = drawer.locator("[data-bms-mobile-tools-close]");
  await close.click();
  check(
    (await edge.getAttribute("aria-expanded")) === "false",
    context,
    "mobile page-tools drawer closes"
  );
};

const interactWithMobileNavigation = async (tab, check, context) => {
  const toggle = tab.playwright.locator("button.navbar-toggler");
  const count = await toggle.count();
  check(count === 1, context, "mobile navigation has one menu toggle");
  if (count !== 1) {
    return;
  }
  await toggle.click();
  check(
    (await toggle.getAttribute("aria-expanded")) === "true",
    context,
    "mobile navigation menu opens"
  );
  const menu = tab.playwright.locator("#navbarCollapse");
  check(
    (await menu.count()) === 1 && (await menu.isVisible()),
    context,
    "mobile navigation links are visible"
  );
  await toggle.click();
  check(
    (await toggle.getAttribute("aria-expanded")) === "false",
    context,
    "mobile navigation menu closes"
  );
};

const interactWithGlossarySidebar = async (tab, check, context) => {
  const link = await visibleLocator(
    tab.playwright.locator("main .bms-inline-glossary[data-bms-glossary-slug]")
  );
  if (!link) {
    check(false, context, "inline glossary link is available for sidebar flow");
    return;
  }
  await link.click();
  const sidebar = tab.playwright.locator("[data-bms-glossary-sidebar]");
  check(
    (await sidebar.count()) === 1 && (await sidebar.isVisible()),
    context,
    "inline glossary link opens the definition sidebar"
  );
  const close = sidebar.locator("[data-bms-glossary-sidebar-close]");
  if ((await close.count()) === 1) {
    await close.click();
    check(!(await sidebar.isVisible()), context, "glossary definition sidebar closes");
  } else {
    check(false, context, "glossary definition sidebar has a close control");
  }
};

const interactWithToc = async (
  tab,
  check,
  context,
  desktop,
  collapseLessonTrack = false
) => {
  const toggleState = () =>
    tab.playwright.locator("html").evaluate(() => {
      const toggle = Array.from(
        document.querySelectorAll("[data-bms-toc-heading-toggle]")
      ).find((candidate) => {
        const rectangle = candidate.getBoundingClientRect();
        return rectangle.width > 0 && rectangle.height > 0;
      });
      return toggle
        ? {
            available: true,
            expanded: toggle.getAttribute("aria-expanded")
          }
        : { available: false, expanded: null };
    });
  const clickToggle = async () => {
    const toggle = await visibleLocator(
      tab.playwright.locator("[data-bms-toc-heading-toggle]")
    );
    if (!toggle) {
      return false;
    }
    await toggle.click();
    return true;
  };
  const initial = await toggleState();
  if (!desktop) {
    check(!initial.available, context, "desktop TOC heading control stays hidden");
    return;
  }
  check(initial.available, context, "compact TOC heading control is visible");
  if (!initial.available) {
    return;
  }
  const lessonTrack = collapseLessonTrack
    ? await visibleLocator(
        tab.playwright.locator(".bms-lesson-track-content")
      )
    : null;
  if (collapseLessonTrack) {
    check(
      Boolean(lessonTrack),
      context,
      "lesson track is visible before collapsing the TOC rail"
    );
  }
  await clickToggle();
  const collapsed = await toggleState();
  check(
    collapsed.expanded === "false",
    context,
    "TOC links collapse"
  );
  check(
    collapsed.available,
    context,
    "TOC restore control remains available"
  );
  if (lessonTrack) {
    check(
      !(await visibleLocator(lessonTrack)),
      context,
      "TOC rail collapse also hides the lesson track"
    );
  }
  if (!collapsed.available) {
    return;
  }
  await clickToggle();
  const restored = await toggleState();
  check(
    restored.expanded === "true",
    context,
    "TOC links restore"
  );
  if (lessonTrack) {
    check(
      Boolean(await visibleLocator(lessonTrack)),
      context,
      "restoring the TOC rail also restores the lesson track"
    );
  }
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

const interactWithLessonAnalysisFixture = async (tab, check, context) => {
  const fixture = tab.playwright.locator("[data-bms-cube-decision]").nth(0);
  check(
    (await fixture.count()) === 1,
    context,
    "cube lesson analysis mounts"
  );
  if ((await fixture.count()) !== 1) {
    return;
  }
  const double = fixture.locator(
    "button[data-bms-analysis-choice='double']"
  );
  await double.click();
  check(
    (await double.getAttribute("aria-pressed")) === "true",
    context,
    "Double records its pressed state"
  );
  const take = fixture.locator(
    "button[data-bms-analysis-choice='take']"
  );
  check((await take.count()) === 1, context, "Double reveals Pass and Take");
  if ((await take.count()) === 1) {
    await take.click();
    check(
      (await take.getAttribute("aria-pressed")) === "true",
      context,
      "Take records its pressed state"
    );
  }
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
  const trackFilter = tab.playwright.locator(
    "[data-bms-glossary-filter-track='Doubling Cube']"
  );
  check((await trackFilter.count()) === 1, context, "glossary track filter exists");
  if ((await trackFilter.count()) === 1) {
    await trackFilter.click();
    check(
      (await trackFilter.getAttribute("aria-pressed")) === "true" &&
        (await countVisible(entries)) < total,
      context,
      "glossary track filter narrows definitions"
    );
    await trackFilter.click();
  }
  await tab.goto(new URL("#active-builder", await tab.url()).href);
  check(
    (await tab.url()).endsWith("#active-builder") &&
      (await tab.playwright.locator("#active-builder").getAttribute("open")) !== null,
    context,
    "glossary anchor opens the requested definition"
  );
};

const runPageInteraction = async ({
  tab,
  page,
  viewport,
  check
}) => {
  const context = `${viewport.name}/${page.id}`;
  const desktop = viewport.width >= 992;
  if (!desktop) {
    await interactWithMobileNavigation(tab, check, context);
  }
  if (page.kind === "learn-index") {
    await interactWithLearnIndex(tab, check, context);
  }
  if (page.kind === "learn-lesson") {
    await interactWithToc(tab, check, context, desktop, true);
    if (desktop) {
      await interactWithLookup(tab, check, context, desktop);
    } else {
      await interactWithMobileDrawer(tab, check, context);
    }
    if ((page.required_markers || []).includes("data-bms-cube-decision")) {
      await interactWithLessonAnalysisFixture(tab, check, context);
    }
    await interactWithGlossarySidebar(tab, check, context);
  }
  if (page.kind === "rich-scroll-fixture") {
    await interactWithRichFixture(tab, check, context);
  }
  if (page.kind === "edge-scroll-fixture") {
    await interactWithEdgeFixture(tab, check, context);
  }
  if (page.kind === "research-article") {
    await interactWithToc(tab, check, context, desktop);
    if (desktop) {
      await interactWithLookup(tab, check, context, desktop, true);
    } else {
      await interactWithMobileDrawer(tab, check, context);
    }
    await interactWithGlossarySidebar(tab, check, context);
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
  manifest = DEFAULT_MANIFEST,
  screenshotDir = null
}) {
  if ((!browser && !tab) || !viewport || !baseUrl) {
    throw new Error("browser or tab, plus viewport and baseUrl, are required");
  }
  const started = Date.now();
  const failures = [];
  const consoleMessages = [];
  const screenshots = [];
  let failureScreenshots = 0;
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
  const saveScreenshot = async (activeTab, viewportCase, page, kind) => {
    if (!screenshotDir) {
      return;
    }
    if (
      kind === "failure" &&
      failureScreenshots >= (manifest.failure_screenshot_limit || 30)
    ) {
      return;
    }
    const fileName = `${safeName(viewportCase.name)}-${safeName(page.id)}${
      kind === "failure" ? `-failure-${failureScreenshots + 1}` : ""
    }.png`;
    const relativePath = `screenshots/browser/${fileName}`;
    try {
      mkdirSync(screenshotDir, { recursive: true });
      writeFileSync(join(screenshotDir, fileName), await activeTab.screenshot({ fullPage: false }));
      screenshots.push({ kind, page: page.id, route: page.route, viewport: viewportCase.name, path: relativePath });
      if (kind === "failure") {
        failureScreenshots += 1;
      }
    } catch (error) {
      failures.push({
        context: `${viewportCase.name}/${page.id}/screenshot`,
        message: `could not save ${kind} screenshot: ${String(error)}`,
        category: "test-infrastructure"
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
        const failureCountBeforePage = failures.length;
        let phase = "navigation";
        try {
          await viewport.set({
            width: viewportCase.width,
            height: viewportCase.height
          });
          await activeTab.goto(new URL(page.route, baseUrl).href);
          await scrollTo(activeTab, 0);
          await delay(500);

          phase = "landmarks and initial layout";
          const audit = await accessibilitySnapshot(activeTab);
          check(audit.landmarks.main === 1, context, "page has one main landmark");
          check(audit.landmarks.navigation >= 1, context, "page has a navigation landmark");
          check(audit.landmarks.footer >= 1, context, "page has a footer landmark");
          check(audit.h1Count === 1, context, "page has exactly one visible H1");
          check(audit.headingSkips.length === 0, context, "heading levels do not skip");
          check(audit.duplicateIds.length === 0, context, `initial IDs are unique${
            audit.duplicateIds.length ? `: ${audit.duplicateIds.join(", ")}` : ""
          }`);
          check(audit.unlabeledControls.length === 0, context, `form controls have labels${
            audit.unlabeledControls.length ? `: ${audit.unlabeledControls.join(", ")}` : ""
          }`);
          check(audit.missingImageAlt.length === 0, context, `images provide alt attributes${
            audit.missingImageAlt.length ? `: ${audit.missingImageAlt.join(", ")}` : ""
          }`);
          check(audit.failedImages.length === 0, context, `required images load${
            audit.failedImages.length ? `: ${audit.failedImages.join(", ")}` : ""
          }`);
          check(audit.failedStylesheets.length === 0, context, `required stylesheets load${
            audit.failedStylesheets.length ? `: ${audit.failedStylesheets.join(", ")}` : ""
          }`);
          check(audit.resourceFailures.length === 0, context, `required resources avoid HTTP failures${
            audit.resourceFailures.length ? `: ${JSON.stringify(audit.resourceFailures)}` : ""
          }`);
          check(audit.clippedControls.length === 0, context, `visible controls are not horizontally clipped${
            audit.clippedControls.length ? `: ${audit.clippedControls.join(", ")}` : ""
          }`);
          check(audit.coveredTargets.length === 0, context, `fixed or sticky elements do not cover controls or headings${
            audit.coveredTargets.length ? `: ${audit.coveredTargets.join(", ")}` : ""
          }`);
          const initialMetrics = await pagePosition(activeTab);
          check(
            initialMetrics.scrollWidth <= initialMetrics.clientWidth + 1,
            context,
            "page has no horizontal overflow"
          );
          for (const marker of page.required_markers || []) {
            const markerPresent = await activeTab.playwright.locator("html").evaluate(
              (root, requiredMarker) => {
                if (requiredMarker.startsWith("data-")) {
                  return Boolean(root.querySelector(`[${requiredMarker}]`));
                }
                if (requiredMarker.startsWith("bms-")) {
                  return Boolean(
                    root.querySelector(`.${requiredMarker}, #${requiredMarker}`)
                  );
                }
                return root.textContent.includes(requiredMarker);
              },
              marker
            );
            check(markerPresent, context, `required marker is present: ${marker}`);
          }
          if (page.kind === "analyzer") {
            check(
              (await activeTab.playwright.locator("#bms-position-preview-frame").count()) === 1,
              context,
              "analyzer iframe container is present without requiring iframe success"
            );
          }
          if (page.kind === "match-predictor") {
            check(
              (await activeTab.playwright.locator(".bms-dashboard-frame iframe").count()) === 1,
              context,
              "Match Predictor iframe container is present without requiring iframe success"
            );
          }
          const focus = await focusSnapshot(activeTab);
          check(
            audit.focusableControls < 2 || focus.distinct >= 2,
            context,
            "keyboard focus advances without an obvious focus trap"
          );
          check(
            focus.missingIndicators.length === 0,
            context,
            `sampled keyboard focus has a visible indicator${
              focus.missingIndicators.length ? `: ${focus.missingIndicators.join(", ")}` : ""
            }`
          );
          if (
            (manifest.baseline_screenshot_route_ids || []).includes(page.id) &&
            (manifest.baseline_screenshot_viewport_names || []).includes(viewportCase.name)
          ) {
            await saveScreenshot(activeTab, viewportCase, page, "baseline");
          }

          phase = "page interactions";
          await runPageInteraction({
            tab: activeTab,
            page,
            viewport: viewportCase,
            check
          });

          phase = "middle scroll";
          if (page.kind !== "research-article") {
            await scrollTo(
              activeTab,
              Math.floor(initialMetrics.scrollHeight / 2)
            );
          }
          const continuousPage =
            page.kind.includes("scroll-fixture") ||
            page.kind === "learn-lesson" ||
            page.kind === "research-article";
          const markerSelector =
            page.kind === "research-article"
              ? ".bms-research-scroll-marker"
              : ".bms-learn-scroll-lesson-marker";
          const markersBeforeScroll = continuousPage
            ? await activeTab.playwright.locator(markerSelector).count()
            : 0;
          phase = "bottom scroll and continuous loading";
          await scrollTo(activeTab, Number.MAX_SAFE_INTEGER);
          await delay(
            continuousPage ? 2500 : 180
          );
          let bottomMetrics = await pagePosition(activeTab);
          if (continuousPage) {
            const markersAfterScroll = await activeTab.playwright
              .locator(markerSelector)
              .count();
            check(
              markersAfterScroll > markersBeforeScroll,
              context,
              page.kind === "research-article"
                ? "continuous scrolling appends the next Research article"
                : "continuous scrolling appends the next lesson"
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
            if (page.kind.includes("scroll-fixture")) {
              check(
                navigationState.activeSidebarLinks >= 1,
                context,
                "continuous scrolling keeps an active lesson in the sidebar"
              );
            }
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
          phase = "duplicate ID audit";
          const duplicates = await duplicateIds(
            activeTab,
            page.kind === "research-article"
              ? "#quarto-document-content"
              : "html"
          );
          check(
            duplicates.length === 0,
            context,
            duplicates.length
              ? `duplicate IDs after scrolling: ${duplicates.join(", ")}`
              : "IDs remain unique after scrolling"
          );

          phase = "back-to-top control";
          const backToTop = await visibleLocator(
            activeTab.playwright.locator(
              "[data-bms-site-back-to-top], [data-bms-glossary-back-to-top]"
            )
          );
          if (
            backToTop &&
            bottomMetrics.scrollY > 0 &&
            page.kind !== "research-article"
          ) {
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
            message: `browser helper error during ${phase}: ${String(error)}`,
            category: "test-infrastructure"
          });
        } finally {
          await collectConsole(activeTab, `${context}/console`);
          if (failures.length > failureCountBeforePage) {
            await saveScreenshot(activeTab, viewportCase, page, "failure");
          }
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
    findings: failures.map((failure) => {
      const [viewportName, pageId] = failure.context.split("/");
      const page = manifest.pages.find((item) => item.id === pageId);
      const screenshot = screenshots.find(
        (item) =>
          item.kind === "failure" &&
          item.viewport === viewportName &&
          item.page === pageId
      );
      return {
        category: failure.category || "product-defect",
        severity: failure.category === "test-infrastructure" ? "blocking" : "major",
        route_or_file: page?.route || failure.context,
        viewport: manifest.viewports.find((item) => item.name === viewportName) || null,
        evidence: `${failure.message}${screenshot ? `; screenshot: ${screenshot.path}` : ""}`,
        reproduction: `Serve site/_site and run the comprehensive browser baseline for ${failure.context}.`,
        safe_for_automated_remediation: false,
        needs_review: true
      };
    }),
    consoleMessages,
    screenshots,
    durationMs: Date.now() - started
  };
  return {
    ...report,
    summary: summarizeReport(report)
  };
}
