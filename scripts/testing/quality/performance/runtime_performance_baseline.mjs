import { DEFAULT_MANIFEST } from "../../ux/browser/comprehensive_quality_browser_check.mjs";

export const PERFORMANCE_CONTRACT = {
  version: 1,
  warmup_loads: 1,
  measured_loads: 3,
  route_ids: [
    "home",
    "cube-lesson",
    "research-article",
    "glossary",
    "analyze",
    "match-predictor"
  ],
  viewport_names: ["desktop-1440", "mobile-390"],
  metric_names: [
    "navigation.dns_ms",
    "navigation.connect_ms",
    "navigation.request_ms",
    "navigation.response_ms",
    "navigation.dom_interactive_ms",
    "navigation.dom_content_loaded_ms",
    "navigation.load_event_ms",
    "navigation.duration_ms",
    "paint.first_paint_ms",
    "paint.first_contentful_paint_ms",
    "paint.largest_contentful_paint_ms",
    "layout.cumulative_layout_shift",
    "dom.node_count",
    "requests.count",
    "requests.failure_count",
    "bytes.total.transfer",
    "bytes.total.encoded_body",
    "bytes.total.decoded_body",
    "bytes.html.transfer",
    "bytes.javascript.transfer",
    "bytes.css.transfer",
    "bytes.image.transfer",
    "bytes.font.transfer",
    "bytes.json.transfer",
    "interactions.glossary_search_ms",
    "interactions.glossary_filter_ms",
    "interactions.glossary_anchor_ms",
    "interactions.glossary_sidebar_ms"
  ]
};

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

export const median = (values) => {
  const numeric = values
    .filter((value) => typeof value === "number" && Number.isFinite(value))
    .sort((left, right) => left - right);
  if (!numeric.length) {
    return null;
  }
  const middle = Math.floor(numeric.length / 2);
  return numeric.length % 2
    ? numeric[middle]
    : (numeric[middle - 1] + numeric[middle]) / 2;
};

const roundMetric = (value, digits = 3) =>
  typeof value === "number" && Number.isFinite(value)
    ? Number(value.toFixed(digits))
    : null;

const collectPageMetrics = (tab) =>
  tab.playwright.locator("html").evaluate(() => {
    const navigation = window.performance.getEntriesByType("navigation")[0];
    const resources = window.performance.getEntriesByType("resource");
    const paints = Object.fromEntries(
      window.performance
        .getEntriesByType("paint")
        .map((entry) => [entry.name, entry.startTime])
    );
    const lcpEntries = window.performance.getEntriesByType(
      "largest-contentful-paint"
    );
    const layoutShifts = window.performance
      .getEntriesByType("layout-shift")
      .filter((entry) => !entry.hadRecentInput);
    const categoryFor = (entry) => {
      const pathname = new URL(entry.name).pathname.toLowerCase();
      if (entry.entryType === "navigation") return "html";
      if (entry.initiatorType === "script" || /\.(?:js|mjs)$/.test(pathname)) return "javascript";
      if (entry.initiatorType === "css" || /\.css$/.test(pathname)) return "css";
      if (entry.initiatorType === "img" || /\.(?:avif|gif|jpe?g|png|svg|webp)$/.test(pathname)) return "image";
      if (/\.(?:eot|otf|ttf|woff2?)$/.test(pathname)) return "font";
      if (/\.json$/.test(pathname)) return "json";
      return "other";
    };
    const byteTemplate = () => ({ transfer: 0, encoded_body: 0, decoded_body: 0 });
    const bytes = {
      total: byteTemplate(),
      html: byteTemplate(),
      javascript: byteTemplate(),
      css: byteTemplate(),
      image: byteTemplate(),
      font: byteTemplate(),
      json: byteTemplate(),
      other: byteTemplate()
    };
    const entries = navigation ? [navigation, ...resources] : resources;
    for (const entry of entries) {
      const category = categoryFor(entry);
      for (const key of ["transfer", "encoded_body", "decoded_body"]) {
        const source =
          key === "transfer"
            ? "transferSize"
            : key === "encoded_body"
              ? "encodedBodySize"
              : "decodedBodySize";
        const value = Number(entry[source] || 0);
        bytes.total[key] += value;
        bytes[category][key] += value;
      }
    }
    return {
      navigation: navigation
        ? {
            dns_ms: navigation.domainLookupEnd - navigation.domainLookupStart,
            connect_ms: navigation.connectEnd - navigation.connectStart,
            request_ms: navigation.responseStart - navigation.requestStart,
            response_ms: navigation.responseEnd - navigation.responseStart,
            dom_interactive_ms: navigation.domInteractive,
            dom_content_loaded_ms: navigation.domContentLoadedEventEnd,
            load_event_ms: navigation.loadEventEnd,
            duration_ms: navigation.duration
          }
        : null,
      paint: {
        first_paint_ms: paints["first-paint"] ?? null,
        first_contentful_paint_ms: paints["first-contentful-paint"] ?? null,
        largest_contentful_paint_ms: lcpEntries.length
          ? lcpEntries[lcpEntries.length - 1].startTime
          : null
      },
      layout: {
        cumulative_layout_shift: layoutShifts.reduce(
          (total, entry) => total + entry.value,
          0
        )
      },
      dom: { node_count: document.querySelectorAll("*").length },
      requests: {
        count: resources.length + (navigation ? 1 : 0),
        failure_count: resources.filter(
          (entry) => Number(entry.responseStatus || 0) >= 400
        ).length
      },
      bytes
    };
  });

const flattenMetrics = (value, prefix = "", output = {}) => {
  for (const [key, child] of Object.entries(value || {})) {
    const name = prefix ? `${prefix}.${key}` : key;
    if (child && typeof child === "object" && !Array.isArray(child)) {
      flattenMetrics(child, name, output);
    } else {
      output[name] = child;
    }
  }
  return output;
};

const medianMetrics = (samples) => {
  const flattened = samples.map((sample) => flattenMetrics(sample));
  const names = Array.from(
    new Set(flattened.flatMap((sample) => Object.keys(sample)))
  ).sort();
  const result = {};
  for (const name of names) {
    result[name] = roundMetric(median(flattened.map((sample) => sample[name])));
  }
  return result;
};

const measureGlossaryInteractions = async ({ tab, baseUrl }) => {
  const measurements = {};
  await tab.goto(new URL("/glossary/", baseUrl).href);
  const search = tab.playwright.locator("[data-bms-glossary-search]");
  if ((await search.count()) === 1) {
    let started = Date.now();
    await search.fill("active builder");
    await tab.playwright.locator("[data-bms-glossary-result-count]").textContent();
    measurements.glossary_search_ms = Date.now() - started;
    const clear = await visibleLocator(
      tab.playwright.locator("[data-bms-glossary-clear]")
    );
    if (clear) await clear.click();
  }
  const filter = tab.playwright.locator(
    "[data-bms-glossary-filter-track='Doubling Cube']"
  );
  if ((await filter.count()) === 1) {
    const started = Date.now();
    await filter.click();
    await filter.getAttribute("aria-pressed");
    measurements.glossary_filter_ms = Date.now() - started;
  }
  let started = Date.now();
  await tab.goto(new URL("/glossary/#active-builder", baseUrl).href);
  await tab.playwright.locator("#active-builder").getAttribute("open");
  measurements.glossary_anchor_ms = Date.now() - started;

  await tab.goto(
    new URL("/learn/cube/what-the-cube-is-asking.html", baseUrl).href
  );
  const inlineLink = await visibleLocator(
    tab.playwright.locator("main .bms-inline-glossary[data-bms-glossary-slug]")
  );
  if (inlineLink) {
    started = Date.now();
    await inlineLink.click();
    const sidebar = tab.playwright.locator("[data-bms-glossary-sidebar]");
    await sidebar.waitFor({ state: "visible", timeoutMs: 3000 });
    measurements.glossary_sidebar_ms = Date.now() - started;
  }
  return measurements;
};

export async function runRuntimePerformanceBaseline({
  tab,
  viewport,
  baseUrl,
  manifest = DEFAULT_MANIFEST,
  contract = PERFORMANCE_CONTRACT
}) {
  if (!tab || !viewport || !baseUrl) {
    throw new Error("tab, viewport, and baseUrl are required");
  }
  const started = Date.now();
  const measurements = [];
  const errors = [];
  const interactions = [];
  try {
    for (const viewportName of contract.viewport_names) {
      const viewportCase = manifest.viewports.find(
        (item) => item.name === viewportName
      );
      if (!viewportCase) throw new Error(`Unknown viewport: ${viewportName}`);
      await viewport.set({ width: viewportCase.width, height: viewportCase.height });
      for (const routeId of contract.route_ids) {
        const page = manifest.pages.find((item) => item.id === routeId);
        if (!page) throw new Error(`Unknown route: ${routeId}`);
        for (let warmup = 0; warmup < contract.warmup_loads; warmup += 1) {
          await tab.goto(new URL(page.route, baseUrl).href);
          await tab.playwright.waitForLoadState({ state: "load", timeoutMs: 30000 });
        }
        const samples = [];
        for (let repetition = 1; repetition <= contract.measured_loads; repetition += 1) {
          await tab.goto(new URL(page.route, baseUrl).href);
          await tab.playwright.waitForLoadState({ state: "load", timeoutMs: 30000 });
          await delay(350);
          try {
            samples.push(await collectPageMetrics(tab));
          } catch (error) {
            errors.push({ viewport: viewportName, route: page.route, repetition, error: String(error) });
          }
        }
        measurements.push({
          viewport: viewportCase,
          route_id: routeId,
          route: page.route,
          samples,
          medians: medianMetrics(samples)
        });
      }
      try {
        interactions.push({
          viewport: viewportCase,
          metrics: await measureGlossaryInteractions({ tab, baseUrl })
        });
      } catch (error) {
        errors.push({ viewport: viewportName, route: "/glossary/", repetition: null, error: String(error) });
      }
    }
  } finally {
    await viewport.reset();
  }
  const reliability = {
    largest_contentful_paint: measurements.some(
      (item) => item.medians["paint.largest_contentful_paint_ms"] !== null
    )
      ? "measured"
      : "not exposed by browser controller",
    cumulative_layout_shift: measurements.some(
      (item) => item.medians["layout.cumulative_layout_shift"] !== null
    )
      ? "measured"
      : "not exposed by browser controller",
    transfer_sizes:
      "Resource Timing values; zero can indicate a cached or restricted cross-origin response"
  };
  return {
    schema_version: 1,
    status: errors.length ? "FAIL" : "PASS",
    base_url: baseUrl,
    contract,
    measurements,
    interactions,
    reliability,
    errors,
    findings: errors.map((error) => ({
      category: "test-infrastructure",
      severity: "major",
      route_or_file: error.route,
      viewport: manifest.viewports.find((item) => item.name === error.viewport) || null,
      evidence: error.error,
      reproduction: "Run the canonical runtime performance baseline against the served site.",
      safe_for_automated_remediation: false,
      needs_review: true
    })),
    duration_ms: Date.now() - started
  };
}
