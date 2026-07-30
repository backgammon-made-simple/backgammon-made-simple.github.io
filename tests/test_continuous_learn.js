"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const scroll = require("../site/assets/bms-learn-scroll.js");
const learn = require("../site/assets/bms-learn.js");
const scrollSource = fs.readFileSync(
  path.join(__dirname, "../site/assets/bms-learn-scroll.js"),
  "utf8"
);

assert.match(
  scrollSource,
  /querySelector\(\s*"\[data-bms-toc-heading-toggle\]"\s*\)/
);
assert.match(scrollSource, /tocLinks\.id = controlledLinksId/);
assert.match(scrollSource, /tocTitle\.appendChild\(headingToggle\)/);
assert.match(
  scrollSource,
  /!document\.body\.classList\.contains\("bms-learn-article"\)/
);
assert.match(
  scrollSource,
  /document\.body\.classList\.contains\("bms-learn-track-index"\)/
);
assert.match(scrollSource, /findPrimaryToc\(document\)/);
assert.match(scrollSource, /findPrimaryToc\(nextDocument\)/);
assert.match(scrollSource, /new ResizeObserver/);
assert.match(
  scrollSource,
  /main\.addEventListener\(\s*"toggle"[\s\S]*?scheduleActiveLessonUpdate\(0\)/
);

const manifest = {
  schema_version: 1,
  lessons: [
    {
      sequence_index: 0,
      route: "/learn/first/",
      previous_route: null,
      next_route: "/learn/middle.html",
      track_id: "one",
      next_starts_new_track: false
    },
    {
      sequence_index: 1,
      route: "/learn/middle.html",
      previous_route: "/learn/first/",
      next_route: "/learn/second-track/",
      track_id: "one",
      next_starts_new_track: true
    },
    {
      sequence_index: 2,
      route: "/learn/second-track/",
      previous_route: "/learn/middle.html",
      next_route: null,
      track_id: "two",
      next_starts_new_track: false
    }
  ]
};

assert.equal(scroll.normalizeRoute("/learn/first"), "/learn/first/");
assert.equal(scroll.normalizeRoute("/learn/first/index.html"), "/learn/first/");
assert.equal(scroll.normalizeRoute("/learn/middle.html/"), "/learn/middle.html");
assert.equal(
  scroll.normalizeRoute("https://example.test/learn/middle.html?x=1#part"),
  "/learn/middle.html"
);

const first = scroll.findCurrentLesson(manifest, "/learn/first/index.html");
const middle = scroll.findCurrentLesson(manifest, "/learn/middle.html");
const finalLesson = scroll.findCurrentLesson(manifest, "/learn/second-track/");
assert.equal(first.sequence_index, 0);
assert.equal(scroll.nextLesson(manifest, first), middle);
assert.equal(scroll.nextLesson(manifest, middle), finalLesson);
assert.equal(scroll.nextLesson(manifest, finalLesson), null);
assert.equal(scroll.isFinalLesson(manifest, first), false);
assert.equal(scroll.isFinalLesson(manifest, finalLesson), true);
assert.equal(scroll.findCurrentLesson(manifest, "/learn/not-a-lesson/"), null);
assert.deepEqual(
  scroll.laterLessonRoutes(manifest, "/learn/middle.html"),
  ["/learn/second-track/"],
  "direct middle entry exposes only later lessons"
);
assert.deepEqual(
  scroll.laterLessonRoutes(manifest, "/learn/second-track/"),
  [],
  "final entry has no forward routes"
);
assert.equal(scroll.startsNewTrack(middle), true);
assert.equal(scroll.startsNewTrack(first), false);

const visibleMarginToc = { location: "margin" };
const fallbackToc = { location: "fallback" };
const documentWithDuplicateTocs = {
  getElementById(id) {
    if (id === "quarto-margin-sidebar") {
      return {
        querySelector(selector) {
          return selector === "#TOC" ? visibleMarginToc : null;
        }
      };
    }
    return id === "TOC" ? fallbackToc : null;
  }
};
assert.equal(
  scroll.findPrimaryToc(documentWithDuplicateTocs),
  visibleMarginToc,
  "the visible margin TOC wins when Quarto emits duplicate TOC IDs"
);
assert.equal(
  scroll.findPrimaryToc({
    getElementById(id) {
      return id === "TOC" ? fallbackToc : null;
    }
  }),
  fallbackToc,
  "ordinary pages keep the document-level TOC fallback"
);
assert.equal(scroll.findPrimaryToc(null), null);

assert.equal(
  scroll.idPrefixForRoute("/learn/cube/what-the-cube-is-asking.html"),
  "bms-learn-scroll-cube-what-the-cube-is-asking-"
);
assert.equal(
  scroll.idPrefixForRoute("/learn/game-plans/"),
  "bms-learn-scroll-game-plans-"
);
assert.notEqual(
  scroll.idPrefixForRoute(
    "/learn/scrolling-test/start-here/lesson-01.html"
  ),
  scroll.idPrefixForRoute(
    "/learn/scrolling-test/doubling-cube/lesson-01.html"
  ),
  "the full route keeps repeated generated filenames collision-free"
);
const generatedPrefixes = ["start-here", "doubling-cube", "opening-play"]
  .flatMap((track) =>
    Array.from({ length: 10 }, (_, index) =>
      scroll.idPrefixForRoute(
        `/learn/scrolling-test/${track}/lesson-${String(index + 1).padStart(2, "0")}.html`
      )
    )
  );
assert.equal(new Set(generatedPrefixes).size, 30);
assert.equal(
  new Set(generatedPrefixes.map((prefixValue) => prefixValue + "overview")).size,
  30,
  "repeated heading IDs remain unique across the long fixture sequence"
);

class FakeElement {
  constructor(attributes = {}) {
    this.values = new Map(Object.entries(attributes));
  }

  get id() {
    return this.getAttribute("id") || "";
  }

  set id(value) {
    this.setAttribute("id", value);
  }

  get attributes() {
    return Array.from(this.values, ([name, value]) => ({ name, value }));
  }

  getAttribute(name) {
    return this.values.has(name) ? this.values.get(name) : null;
  }

  setAttribute(name, value) {
    this.values.set(name, String(value));
  }
}

class FakeRoot {
  constructor(elements) {
    this.elements = elements;
  }

  querySelectorAll(selector) {
    if (selector === "[id]") {
      return this.elements.filter((element) => element.id);
    }
    if (selector === "*") {
      return this.elements;
    }
    return [];
  }
}

const panel = new FakeElement({ id: "answer-panel" });
const label = new FakeElement({ id: "choice-label" });
const references = new FakeElement({
  for: "answer-panel",
  "aria-labelledby": "choice-label answer-panel",
  "aria-describedby": "answer-panel",
  "aria-controls": "answer-panel",
  "aria-owns": "answer-panel",
  "data-answer-panel": "answer-panel",
  "data-bs-target": "#answer-panel",
  "data-target": "#answer-panel",
  href: "#answer-panel",
  style: "filter: url(#answer-panel)"
});
const otherPageLink = new FakeElement({
  href: "/learn/other.html#answer-panel"
});
const root = new FakeRoot([panel, label, references, otherPageLink]);
const prefix = "bms-learn-scroll-example-";
scroll.rewriteIdReferences(root, prefix);
assert.equal(panel.id, prefix + "answer-panel");
assert.equal(label.id, prefix + "choice-label");
assert.equal(references.getAttribute("for"), prefix + "answer-panel");
assert.equal(
  references.getAttribute("aria-labelledby"),
  prefix + "choice-label " + prefix + "answer-panel"
);
assert.equal(references.getAttribute("aria-describedby"), prefix + "answer-panel");
assert.equal(references.getAttribute("aria-controls"), prefix + "answer-panel");
assert.equal(references.getAttribute("aria-owns"), prefix + "answer-panel");
assert.equal(references.getAttribute("data-answer-panel"), prefix + "answer-panel");
assert.equal(references.getAttribute("data-bs-target"), "#" + prefix + "answer-panel");
assert.equal(references.getAttribute("data-target"), "#" + prefix + "answer-panel");
assert.equal(references.getAttribute("href"), "#" + prefix + "answer-panel");
assert.equal(
  references.getAttribute("style"),
  "filter: url(#" + prefix + "answer-panel)"
);
assert.equal(
  otherPageLink.getAttribute("href"),
  "/learn/other.html#answer-panel",
  "another page's fragment is not rewritten"
);

const base = "https://example.test/learn/deep/lesson.html";
assert.equal(
  scroll.resolveUrlValue("image.png", base),
  "https://example.test/learn/deep/image.png"
);
assert.equal(
  scroll.resolveUrlValue("../image.png", base),
  "https://example.test/learn/image.png"
);
assert.equal(
  scroll.resolveUrlValue("../../assets/image.png", base),
  "https://example.test/assets/image.png"
);
assert.equal(
  scroll.resolveUrlValue("/assets/image.png", base),
  "/assets/image.png"
);
assert.equal(
  scroll.resolveUrlValue("https://cdn.example/image.png", base),
  "https://cdn.example/image.png"
);
assert.equal(scroll.resolveUrlValue("mailto:test@example.com", base), "mailto:test@example.com");
assert.equal(scroll.resolveUrlValue("tel:+15551234567", base), "tel:+15551234567");
assert.equal(scroll.resolveUrlValue("#local", base), "#local");
assert.equal(scroll.resolveUrlValue("javascript:alert(1)", base), null);
assert.equal(
  scroll.resolveUrlValue("data:image/png;base64,AAAA", base),
  "data:image/png;base64,AAAA"
);
assert.equal(scroll.resolveUrlValue("data:text/html;base64,AAAA", base), null);
assert.equal(
  scroll.resolveSrcset("../one.png 1x, ../../two.png 2x", base),
  "https://example.test/learn/one.png 1x, https://example.test/two.png 2x"
);

assert.equal(
  scroll.sameOriginUrl("/learn/first/", "https://example.test").href,
  "https://example.test/learn/first/"
);
assert.equal(
  scroll.sameOriginUrl("https://example.test/learn/first/", "https://example.test")
    .pathname,
  "/learn/first/"
);
assert.equal(
  scroll.sameOriginUrl("https://other.test/learn/first/", "https://example.test"),
  null
);

const tracker = scroll.createLoadedRouteTracker("/learn/first/");
assert.equal(tracker.isLoaded("/learn/first/index.html"), true);
assert.equal(tracker.canFetch("/learn/middle.html"), true);
assert.equal(tracker.start("/learn/middle.html"), true);
assert.equal(tracker.start("/learn/middle.html"), false);
assert.equal(tracker.canFetch("/learn/second-track/"), false);
tracker.complete("/learn/middle.html");
assert.equal(tracker.isLoaded("/learn/middle.html"), true);
assert.equal(tracker.start("/learn/middle.html"), false);
assert.equal(tracker.start("/learn/second-track/"), true);
tracker.fail("/learn/second-track/");
assert.equal(
  tracker.canFetch("/learn/second-track/"),
  true,
  "a failed route can be retried only by the caller"
);

assert.deepEqual(scroll.errorStateForLesson(middle), {
  message: "The next lesson could not be loaded.",
  route: "/learn/middle.html"
});

assert.equal(scroll.readingLineForViewport(1000), 140);
assert.equal(scroll.readingLineForViewport(390), 72);
assert.equal(
  scroll.selectActiveLessonIndex([0, 80, 500], 100, 0, 1, 28),
  0,
  "downward hysteresis retains the current lesson near a boundary"
);
assert.equal(
  scroll.selectActiveLessonIndex([0, 70, 500], 100, 0, 1, 28),
  1,
  "scrolling downward selects a lesson after it clears the stable band"
);
assert.equal(
  scroll.selectActiveLessonIndex([-500, 120, 500], 100, 1, -1, 28),
  1,
  "upward hysteresis avoids boundary flicker"
);
assert.equal(
  scroll.selectActiveLessonIndex([-500, 130, 500], 100, 1, -1, 28),
  0,
  "scrolling upward restores the preceding loaded lesson"
);
assert.equal(
  scroll.selectActiveLessonIndex([-1000, -500, 20], 100, 0, 1, 28),
  2,
  "large downward jumps remain deterministic"
);
assert.equal(scroll.selectActiveHeadingIndex([20, 90, 180], 100), 1);
assert.equal(scroll.selectActiveHeadingIndex([], 100), -1);

assert.equal(
  scroll.sidebarRouteMatches(
    "../../learn/first/index.html",
    "/learn/first/",
    "https://example.test/learn/deep/current.html"
  ),
  true
);
assert.equal(
  scroll.sidebarRouteMatches(
    "../../learn/first/index.html",
    "/learn/middle.html",
    "https://example.test/learn/deep/current.html"
  ),
  false
);
assert.equal(scroll.shouldExpandTrack(false, true), true);
assert.equal(scroll.shouldExpandTrack(true, true), false);
assert.equal(scroll.shouldExpandTrack(false, false), false);

function fakeClassList(initial = []) {
  const values = new Set(initial);
  return {
    add(value) {
      values.add(value);
    },
    remove(value) {
      values.delete(value);
    },
    contains(value) {
      return values.has(value);
    }
  };
}

const sidebarToggle = {
  attributes: new Map([["aria-expanded", "false"]]),
  clickCount: 0,
  getAttribute(name) {
    return this.attributes.get(name) || null;
  },
  click() {
    this.clickCount += 1;
    this.attributes.set("aria-expanded", "true");
  }
};
const sidebarSection = {
  querySelector() {
    return sidebarToggle;
  }
};
const sidebarSectionList = {
  closest() {
    return sidebarSection;
  }
};
function fakeSidebarLink(href, classes, top) {
  return {
    attributes: new Map([["href", href], ["aria-current", "page"]]),
    classList: fakeClassList(classes),
    getAttribute(name) {
      return this.attributes.has(name) ? this.attributes.get(name) : null;
    },
    setAttribute(name, value) {
      this.attributes.set(name, value);
    },
    removeAttribute(name) {
      this.attributes.delete(name);
    },
    closest(selector) {
      return selector === ".sidebar-section" ? sidebarSectionList : null;
    },
    getBoundingClientRect() {
      return { top, bottom: top + 30 };
    }
  };
}
const oldSidebarLink = fakeSidebarLink(
  "../../learn/first/index.html",
  ["sidebar-link", "active"],
  20
);
const newSidebarLink = fakeSidebarLink(
  "../../learn/middle.html",
  ["sidebar-link"],
  240
);
newSidebarLink.removeAttribute("aria-current");
const fakeSidebar = {
  scrollTop: 0,
  querySelectorAll() {
    return [oldSidebarLink, newSidebarLink];
  },
  getBoundingClientRect() {
    return { top: 0, bottom: 200 };
  }
};
assert.equal(
  scroll.setActiveSidebar(
    fakeSidebar,
    "/learn/middle.html",
    "https://example.test/learn/deep/current.html"
  ),
  newSidebarLink
);
assert.equal(oldSidebarLink.classList.contains("active"), false);
assert.equal(oldSidebarLink.getAttribute("aria-current"), null);
assert.equal(newSidebarLink.classList.contains("active"), true);
assert.equal(newSidebarLink.getAttribute("aria-current"), "page");
assert.equal(sidebarToggle.clickCount, 1);
assert.equal(fakeSidebar.scrollTop, 78);

const tocHeadingMap = new Map([
  ["overview", "bms-learn-scroll-test-overview"]
]);
const tocLinkElement = new FakeElement({
  id: "toc-overview",
  href: "#overview",
  "data-scroll-target": "#overview"
});
scroll.rewriteIdReferences(
  new FakeRoot([tocLinkElement]),
  "bms-learn-scroll-test-",
  tocHeadingMap
);
assert.equal(
  tocLinkElement.getAttribute("href"),
  "#bms-learn-scroll-test-overview"
);
assert.equal(
  tocLinkElement.getAttribute("data-scroll-target"),
  "#bms-learn-scroll-test-overview"
);
assert.equal(
  tocLinkElement.id,
  "bms-learn-scroll-test-toc-overview"
);

function fakeTocLink(href, active) {
  return {
    href,
    classList: fakeClassList(active ? ["active"] : []),
    getAttribute(name) {
      return name === "href" ? this.href : null;
    },
    cloneNode() {
      return fakeTocLink(this.href, this.classList.contains("active"));
    }
  };
}
function fakeToc(links) {
  return {
    links,
    childNodes: links,
    hidden: false,
    attributes: new Map(),
    querySelector(selector) {
      return selector === 'a[href^="#"]' ? this.links[0] || null : null;
    },
    querySelectorAll(selector) {
      if (selector === 'a[href^="#"]') {
        return this.links;
      }
      if (selector === ".active") {
        return this.links.filter((link) => link.classList.contains("active"));
      }
      return [];
    },
    cloneNode() {
      return fakeToc(this.links.map((link) => link.cloneNode(true)));
    },
    replaceChildren(...children) {
      this.childNodes = children;
      this.links = children;
    },
    setAttribute(name, value) {
      this.attributes.set(name, value);
    },
    removeAttribute(name) {
      this.attributes.delete(name);
    }
  };
}
const sourceToc = fakeToc([
  fakeTocLink("#overview", true),
  fakeTocLink("#details", false)
]);
const storedToc = scroll.captureToc(sourceToc);
assert.deepEqual(scroll.tocHashTargets(storedToc), [
  "#overview",
  "#details"
]);
assert.equal(storedToc.links[0].classList.contains("active"), false);
const globalToc = fakeToc([]);
assert.equal(scroll.replaceTocContents(globalToc, storedToc), true);
assert.equal(globalToc.hidden, false);
assert.deepEqual(
  globalToc.links.map((link) => link.getAttribute("href")),
  ["#overview", "#details"]
);
assert.equal(scroll.replaceTocContents(globalToc, null), false);
assert.equal(globalToc.hidden, true);
assert.equal(globalToc.attributes.get("aria-hidden"), "true");

const lessonRecord = scroll.createLessonRecord(
  {
    route: "/learn/middle.html",
    title: "Middle",
    track_id: "one",
    track_title: "Track One",
    sequence_index: 1
  },
  { marker: true },
  ["overview", "details"],
  storedToc
);
assert.deepEqual(
  {
    route: lessonRecord.route,
    title: lessonRecord.title,
    trackId: lessonRecord.trackId,
    trackTitle: lessonRecord.trackTitle,
    headingIds: lessonRecord.headingIds,
    sequencePosition: lessonRecord.sequencePosition
  },
  {
    route: "/learn/middle.html",
    title: "Middle",
    trackId: "one",
    trackTitle: "Track One",
    headingIds: ["overview", "details"],
    sequencePosition: 1
  }
);

const mountedButton = {
  listenerCount: 0,
  addEventListener() {
    this.listenerCount += 1;
  }
};
const mountedPrompt = {
  dataset: {},
  querySelectorAll(selector) {
    return selector === ".bms-answer-choice" ? [mountedButton] : [];
  },
  querySelector() {
    return null;
  }
};
const mountedAnalyzer = {
  dataset: {},
  listenerCount: 0,
  addEventListener() {
    this.listenerCount += 1;
  }
};
const mountRoot = {
  querySelectorAll(selector) {
    if (selector === ".bms-decision-prompt") {
      return [mountedPrompt];
    }
    if (selector === "details.bms-analyzer-embed") {
      return [mountedAnalyzer];
    }
    if (selector === "[id]") {
      return [];
    }
    return [];
  }
};
learn.mountLesson(mountRoot);
learn.mountLesson(mountRoot);
assert.equal(mountedButton.listenerCount, 1);
assert.equal(mountedAnalyzer.listenerCount, 1);
assert.equal(mountedPrompt.dataset.bmsAnswerChoicesMounted, "true");
assert.equal(mountedAnalyzer.dataset.bmsLazyAnalyzerMounted, "true");

console.log("continuous Learn helper tests passed");
