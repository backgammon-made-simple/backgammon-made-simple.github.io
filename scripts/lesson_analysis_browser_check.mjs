const VIEWPORTS = [
  { name: "desktop", width: 1440, height: 1000 },
  { name: "mobile", width: 390, height: 844 }
];

export const LESSON_ANALYSIS_ROUTES = {
  cube: "/learn/cube/what-the-cube-is-asking.html",
  checker: "/learn/cube/why-is-25-percent-the-basic-take-point.html"
};

const delay = (milliseconds) =>
  new Promise((resolve) => setTimeout(resolve, milliseconds));

const componentSnapshot = (tab) =>
  tab.playwright.locator("html").evaluate(() => {
    const ids = Array.from(
      document.querySelectorAll(".bms-lesson-analysis [id]")
    ).map((element) => element.id);
    return {
      componentErrors: document.querySelectorAll(".bms-analysis-error").length,
      duplicateComponentIds: Array.from(
        new Set(ids.filter((id, index) => ids.indexOf(id) !== index))
      ),
      innerWidth: window.innerWidth,
      overflow:
        document.documentElement.scrollWidth -
        document.documentElement.clientWidth
    };
  });

const consoleErrors = async (tab) => {
  const logs = await tab.dev.logs();
  return logs.filter((entry) =>
    /(TypeError|ReferenceError|Uncaught|console\.error)/i.test(
      typeof entry === "string" ? entry : JSON.stringify(entry)
    )
  );
};

const scrollAndRestore = (tab) =>
  tab.playwright.locator("html").evaluate(() => {
    window.scrollTo(0, document.documentElement.scrollHeight);
    window.scrollTo(0, 0);
  });

export const summarizeLessonAnalysisReport = (report) => ({
  passed: report.failures.length === 0,
  checks: report.checks,
  failures: report.failures.length,
  pages: report.pages,
  durationMs: report.durationMs
});

export async function runLessonAnalysisBrowserChecks({
  browser,
  viewport,
  baseUrl
}) {
  if (!browser || !viewport || !baseUrl) {
    throw new Error("browser, viewport, and baseUrl are required");
  }
  const started = Date.now();
  const failures = [];
  let checks = 0;
  let pages = 0;
  const check = (condition, context, message) => {
    checks += 1;
    if (!condition) {
      failures.push({ context, message });
    }
  };
  const freshTab = async (viewportCase, route) => {
    await browser.tabs.finalize();
    const tab = await browser.tabs.new();
    await viewport.set({
      width: viewportCase.width,
      height: viewportCase.height
    });
    await tab.goto(new URL(route, baseUrl).href);
    await delay(900);
    pages += 1;
    return tab;
  };

  try {
    for (const viewportCase of VIEWPORTS) {
      const cubeContext = `${viewportCase.name}/cube`;
      const cubeTab = await freshTab(
        viewportCase,
        LESSON_ANALYSIS_ROUTES.cube
      );
      try {
        const hosts = cubeTab.playwright.locator(
          "[data-bms-cube-decision]"
        );
        const first = hosts.nth(0);
        const second = hosts.nth(1);
        check((await hosts.count()) === 2, cubeContext, "two cube hosts mount");
        const initial = await cubeTab.playwright.locator("html").evaluate(() => {
          const instances = Array.from(
            document.querySelectorAll("[data-bms-analysis-instance]")
          );
          const starts = instances.map(
            (item) => item.querySelector("img")?.getAttribute("src") || ""
          );
          return {
            distinctInstances: new Set(
              instances.map((item) => item.dataset.bmsAnalysisInstance)
            ).size,
            primaryImageLoaded: Boolean(
              instances[0]?.querySelector(".bms-analysis-position-image")
                ?.complete &&
                instances[0]?.querySelector(".bms-analysis-position-image")
                  ?.naturalWidth > 0
            ),
            starts
          };
        });
        check(
          initial.distinctInstances === 2,
          cubeContext,
          "cube instances have unique IDs"
        );
        check(
          initial.starts.length === 2 &&
            initial.starts.every(
              (source) =>
                source ===
                "/assets/positions/lesson-analysis-svg-mvp/opening-fixture/starting.svg"
            ),
          cubeContext,
          "both instances reuse the shared starting SVG"
        );
        check(
          initial.primaryImageLoaded,
          cubeContext,
          "the visible primary cube SVG loads"
        );

        const rollButton = first.locator(
          "button[data-bms-analysis-choice='roll']"
        );
        await rollButton.press("ENTER");
        const rollFocused = await first.evaluate(
          () =>
            document.activeElement?.dataset.bmsAnalysisChoice === "roll"
        );
        check(
          rollFocused,
          cubeContext,
          "the native Roll button accepts keyboard focus"
        );
        await rollButton.evaluate((button) =>
          button.scrollIntoView({ block: "center" })
        );
        await delay(900);
        const beforeRoll = await first.evaluate(() => window.scrollY);
        await rollButton.click();
        const roll = await first.evaluate((element) => ({
          answerOpen: element.querySelector(".bms-analysis-answer")?.open,
          nested: element.querySelectorAll(
            ".bms-analysis-disclosure--nested"
          ).length,
          summary: element
            .querySelector(".bms-analysis-answer > summary")
            ?.textContent.trim(),
          scrollY: window.scrollY
        }));
        check(
          roll.answerOpen && roll.nested >= 1,
          cubeContext,
          "Roll reveals its nested analysis"
        );
        check(
          roll.summary === "Roll: review the fixture answer",
          cubeContext,
          "Roll path reports its fixture result"
        );
        check(
          Math.abs(roll.scrollY - beforeRoll) <= 32,
          cubeContext,
          "Roll reveal does not jump the page"
        );

        await first
          .locator("button[data-bms-analysis-choice='double']")
          .click();
        const double = await first.evaluate((element) => ({
          responder: Boolean(element.querySelector(".bms-analysis-responder")),
          responderImage: element
            .querySelector(".bms-analysis-responder img")
            ?.getAttribute("src")
        }));
        check(double.responder, cubeContext, "Double reveals responder choice");
        check(
          double.responderImage?.endsWith("/responder-flipped.svg"),
          cubeContext,
          "Double uses the supplied responder SVG"
        );

        await first
          .locator("button[data-bms-analysis-choice='pass']")
          .click();
        check(
          (await first
            .locator(".bms-analysis-answer--response > summary")
            .textContent()).trim() === "Pass: review the fixture answer",
          cubeContext,
          "Pass reveals response analysis"
        );
        await first
          .locator("button[data-bms-analysis-choice='take']")
          .click();
        check(
          (await first
            .locator(".bms-analysis-answer--response > summary")
            .textContent()).trim() === "Take: fixture answer",
          cubeContext,
          "Take reveals the accepted response"
        );

        await cubeTab.playwright
          .getByText("Open the component-isolation fixture", { exact: true })
          .click();
        await second
          .locator("button[data-bms-analysis-choice='double']")
          .click();
        check(
          (await second
            .locator(".bms-analysis-answer .bms-analysis-position--answer img")
            .getAttribute("src"))?.endsWith("/starting.svg"),
          cubeContext,
          "rejected Double answer reuses the same position render"
        );
        await second
          .locator("button[data-bms-analysis-choice='roll']")
          .click();
        const isolated = await cubeTab.playwright
          .locator("html")
          .evaluate(() => {
            const hosts = document.querySelectorAll(
              "[data-bms-cube-decision]"
            );
            return {
              firstTake: hosts[0]
                .querySelector("button[data-bms-analysis-choice='take']")
                ?.getAttribute("aria-pressed"),
              secondRoll: hosts[1]
                .querySelector("button[data-bms-analysis-choice='roll']")
                ?.getAttribute("aria-pressed")
            };
          });
        check(
          isolated.firstTake === "true" && isolated.secondRoll === "true",
          cubeContext,
          "two cube instances keep independent state"
        );
        await scrollAndRestore(cubeTab);
        check(
          (await first
            .locator("button[data-bms-analysis-choice='take']")
            .getAttribute("aria-pressed")) === "true",
          cubeContext,
          "cube state survives scrolling"
        );
        const cubePage = await componentSnapshot(cubeTab);
        check(cubePage.overflow <= 0, cubeContext, "cube page has no overflow");
        check(
          cubePage.duplicateComponentIds.length === 0,
          cubeContext,
          "cube component IDs remain unique"
        );
        check(
          cubePage.componentErrors === 0,
          cubeContext,
          "cube fixture has no mount errors"
        );
        check(
          (await consoleErrors(cubeTab)).length === 0,
          cubeContext,
          "cube page has no console exceptions"
        );
      } catch (error) {
        failures.push({
          context: cubeContext,
          message: `browser helper error: ${String(error)}`
        });
      }

      const checkerContext = `${viewportCase.name}/checker`;
      const checkerTab = await freshTab(
        viewportCase,
        LESSON_ANALYSIS_ROUTES.checker
      );
      try {
        const host = checkerTab.playwright.locator(
          "[data-bms-checker-decision]"
        );
        const startingSource = await host
          .locator(".bms-analysis-position-image")
          .getAttribute("src");
        check(
          startingSource?.endsWith("/starting.svg"),
          checkerContext,
          "checker lesson reuses the shared starting SVG"
        );
        for (const candidateId of [
          "candidate-1",
          "candidate-2",
          "candidate-3"
        ]) {
          await host
            .locator(
              `button[data-bms-analysis-choice='${candidateId}']`
            )
            .click();
          const selected = await host.evaluate((element, selectedId) => ({
            image: element
              .querySelector(".bms-analysis-position-image")
              ?.getAttribute("src"),
            pressed: element
              .querySelector(
                `button[data-bms-analysis-choice='${selectedId}']`
              )
              ?.getAttribute("aria-pressed"),
            status: element
              .querySelector(".bms-analysis-choice-status")
              ?.textContent.trim()
          }), candidateId);
          check(
            selected.image?.endsWith(`/${candidateId}.svg`) &&
              selected.pressed === "true" &&
              selected.status.includes("selected"),
            checkerContext,
            `${candidateId} updates its supplied image and state`
          );
        }
        const missing = await host.evaluate((element) =>
          Array.from(
            element.querySelectorAll(".bms-analysis-candidate-result dd")
          ).filter((item) => item.textContent.trim() === "Not supplied").length
        );
        check(
          missing === 2,
          checkerContext,
          "missing optional probabilities display clearly"
        );
        await scrollAndRestore(checkerTab);
        check(
          (await host
            .locator("button[data-bms-analysis-choice='candidate-3']")
            .getAttribute("aria-pressed")) === "true",
          checkerContext,
          "checker selection survives scrolling"
        );
        const checkerPage = await componentSnapshot(checkerTab);
        check(
          checkerPage.overflow <= 0,
          checkerContext,
          "checker page has no overflow"
        );
        check(
          checkerPage.duplicateComponentIds.length === 0,
          checkerContext,
          "checker component IDs remain unique"
        );
        check(
          checkerPage.componentErrors === 0,
          checkerContext,
          "checker fixture has no mount errors"
        );
        check(
          (await consoleErrors(checkerTab)).length === 0,
          checkerContext,
          "checker page has no console exceptions"
        );
      } catch (error) {
        failures.push({
          context: checkerContext,
          message: `browser helper error: ${String(error)}`
        });
      }
    }
  } finally {
    await viewport.reset();
    await browser.tabs.finalize();
  }

  const report = {
    checks,
    failures,
    pages,
    durationMs: Date.now() - started
  };
  return {
    ...report,
    summary: summarizeLessonAnalysisReport(report)
  };
}
