const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const research = require("../site/assets/bms-research-scroll.js");

const manifest = {
  schema_version: 1,
  articles: [
    {
      sequence_index: 0,
      route: "/research/alpha.html",
      title: "Alpha",
      previous_route: null,
      next_route: "/research/beta.html"
    },
    {
      sequence_index: 1,
      route: "/research/beta.html",
      title: "Beta",
      previous_route: "/research/alpha.html",
      next_route: null
    }
  ]
};

assert.equal(
  research.findCurrentArticle(manifest, "/research/alpha.html?x=1").title,
  "Alpha"
);
assert.equal(
  research.nextArticle(
    manifest,
    research.findCurrentArticle(manifest, "/research/alpha.html")
  ).title,
  "Beta"
);
assert.equal(
  research.nextArticle(
    manifest,
    research.findCurrentArticle(manifest, "/research/beta.html")
  ),
  null
);
assert.equal(
  research.idPrefixForArticle("/research/Article One.html"),
  "bms-research-scroll-article-one-"
);

const source = fs.readFileSync(
  path.join(__dirname, "../site/assets/bms-research-scroll.js"),
  "utf8"
);
for (const required of [
  "bms-research-scroll-sentinel",
  "IntersectionObserver",
  "rewriteIdReferences",
  "rewriteResourceUrls",
  "captureArticleToc",
  "replaceTocContents",
  "dataset.bmsResearchScrollMarker"
]) {
  assert.ok(source.includes(required), `Research scroll includes ${required}`);
}
assert.ok(
  source.includes("!nextDocument.body.classList.contains(\"bms-research-article\")"),
  "fetched pages must remain Research articles"
);

console.log("continuous Research helper tests passed");
