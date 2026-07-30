"use strict";

const assert = require("node:assert/strict");
const scroll = require("../site/assets/bms-learn-scroll.js");
const learn = require("../site/assets/bms-learn.js");

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

assert.equal(
  scroll.idPrefixForRoute("/learn/cube/what-the-cube-is-asking.html"),
  "bms-learn-scroll-what-the-cube-is-asking-"
);
assert.equal(
  scroll.idPrefixForRoute("/learn/game-plans/"),
  "bms-learn-scroll-game-plans-"
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
