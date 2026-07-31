"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const learn = require("../site/assets/bms-learn.js");
const glossary = require("../site/assets/bms-glossary.js");

const lessons = [
  {
    difficulties: ["Beginner", "Intermediate"],
    tracks: ["Doubling Cube"],
    terms: ["doubling-cube", "take-point"],
    searchValues: ["The Doubling Cube", "A question-led learning path"]
  },
  {
    difficulties: ["Intermediate", "Advanced"],
    tracks: ["Engines and Analysis"],
    terms: ["equity", "rollout"],
    searchValues: ["Reading Positions", "Understand engine output"]
  },
  {
    difficulties: ["Beginner"],
    tracks: ["Opening Play", "Checker Play"],
    terms: ["opening-roll"],
    searchValues: ["Opening Play Lab", "Opening rolls and replies"]
  }
];

const inlineLookup = [
  {
    slug: "anchor",
    term: "Anchor",
    aliases: ["Holding Point"],
    short_definition: "The canonical anchor summary."
  }
];

assert.equal(
  learn.isMobileDrawerSwipe(20, 100, 48, 103),
  true,
  "a horizontal gesture from the left edge opens mobile page tools"
);
assert.equal(
  learn.isMobileDrawerSwipe(20, 100, 2, 101),
  false,
  "a very short edge gesture is ignored"
);
assert.equal(
  learn.isMobileDrawerSwipe(80, 100, 20, 102),
  false,
  "a gesture away from the left edge is ignored"
);
assert.equal(
  learn.isMobileDrawerSwipe(20, 100, 25, 155),
  false,
  "vertical scrolling does not open mobile page tools"
);

[
  ["#section", "https://example.test/research/article.html", true],
  [
    "https://example.test/research/article.html#section",
    "https://example.test/research/article.html",
    true
  ],
  [
    "https://example.test/research/article.html#section",
    "https://example.test/research/article.html?preview=1",
    true
  ],
  [
    "https://example.test/research/other.html#section",
    "https://example.test/research/article.html",
    false
  ],
  [
    "https://example.test/research/article.html",
    "https://example.test/research/article.html",
    false
  ]
].forEach(([href, currentHref, expected]) => {
  assert.equal(
    learn.isSamePageTocHref(href, currentHref),
    expected,
    href + " has expected same-page TOC classification"
  );
});

assert.equal(
  learn.canonicalEntryBySlug(inlineLookup, "anchor"),
  inlineLookup[0],
  "canonical slugs resolve to the canonical generated record"
);
assert.equal(
  learn.canonicalShortDefinition(inlineLookup, "anchor"),
  "The canonical anchor summary.",
  "inline summaries come from canonical short_definition"
);
assert.equal(
  learn.bestLookupEntry(inlineLookup, "Holding Point"),
  inlineLookup[0],
  "aliases resolve to the same canonical record"
);
assert.equal(
  learn.canonicalShortDefinition(
    inlineLookup,
    learn.bestLookupEntry(inlineLookup, "Holding Point").slug
  ),
  "The canonical anchor summary.",
  "alias lookup uses the canonical record's short definition"
);
assert.equal(
  learn.canonicalShortDefinition(
    [{ ...inlineLookup[0], short_definition: "A changed canonical summary." }],
    "anchor"
  ),
  "A changed canonical summary.",
  "changing the canonical short definition changes the inline summary"
);

assert.equal(
  learn.itemMatchesTaxonomy(
    lessons[0],
    ["Beginner", "Advanced"],
    ["Doubling Cube"]
  ),
  true,
  "difficulty selections are ORed within their group"
);
assert.equal(
  learn.itemMatchesTaxonomy(
    lessons[1],
    ["Beginner", "Advanced"],
    ["Doubling Cube"]
  ),
  false,
  "difficulty and track groups are ANDed"
);
assert.equal(
  learn.itemMatchesTaxonomy(lessons[2], [], []),
  true,
  "no selections show all lessons"
);
assert.equal(
  learn.itemMatchesLesson(
    lessons[1],
    "engine output",
    ["Advanced"],
    ["rollout"]
  ),
  true,
  "lesson search combines with difficulty and track filters"
);
assert.equal(
  learn.itemMatchesLesson(
    lessons[1],
    "opening",
    ["Advanced"],
    ["rollout"]
  ),
  false,
  "lesson search excludes nonmatching titles and descriptions"
);
assert.equal(
  learn.itemMatchesLesson(lessons[0], "cube", ["Beginner"], ["take-point"]),
  true,
  "term selections combine with search and difficulty"
);
assert.equal(
  learn.itemMatchesLesson(lessons[0], "cube", ["Beginner"], ["rollout"]),
  false,
  "a nonmatching term excludes the lesson"
);

const learnGroups = [
  { open: true, hidden: false },
  { open: true, hidden: false },
  { open: true, hidden: false }
];
assert.deepEqual(
  learn.groupControlState(learnGroups),
  { collapseDisabled: false, expandDisabled: true },
  "all lesson tracks begin expanded"
);
learn.setAllGroupsExpanded(learnGroups, false);
assert.deepEqual(
  learnGroups.map((group) => group.open),
  [false, false, false],
  "Collapse all closes every lesson track"
);
assert.deepEqual(
  learn.groupControlState(learnGroups),
  { collapseDisabled: true, expandDisabled: false }
);
assert.equal(
  learn.normalizeLearnSearch("  Doubling-Cubé  "),
  "doubling cube",
  "lesson search normalizes punctuation, whitespace, and accents"
);

const canonicalTerm = {
  category: "cube and scoring",
  tracks: ["Doubling Cube"],
  searchValues: ["Take", "Accept a Double"]
};

assert.equal(
  glossary.itemMatchesGlossary(
    canonicalTerm,
    "accept a double",
    [],
    []
  ),
  true,
  "an alias search matches its canonical entry"
);
assert.equal(
  glossary.itemMatchesGlossary(
    canonicalTerm,
    "take",
    ["cube and scoring"],
    ["Doubling Cube"]
  ),
  true,
  "search, category, and track filters combine"
);
assert.equal(
  glossary.itemMatchesGlossary(
    canonicalTerm,
    "take",
    ["checker play and tactics"],
    ["Doubling Cube"]
  ),
  false,
  "glossary filter groups are ANDed"
);
assert.equal(glossary.normalizeSearch("\u00c9quity"), "equity");
assert.equal(glossary.normalizeSearch("Take-Point"), "take point");
assert.equal(glossary.normalizeCompact("Take Point"), "takepoint");

const spellingVariants = {
  category: "strategy and position types",
  tracks: [],
  searchValues: ["Outfield"]
};
["outfield", "out field", "Outfield", "out-field"].forEach((query) => {
  assert.equal(
    glossary.itemMatchesGlossary(spellingVariants, query, [], []),
    true,
    query + " matches the canonical Outfield term"
  );
});

["take point", "take-point", "Take Point", "take.po"].forEach((query) => {
  assert.equal(
    glossary.itemMatchesGlossary(
      {
        category: "cube and scoring",
        tracks: ["Doubling Cube"],
        searchValues: ["Take Point"]
      },
      query,
      [],
      []
    ),
    true,
    query + " matches Take Point after normalized partial search"
  );
});

const rankingCandidates = [
  {
    canonical: "Take Point Formula",
    aliases: [],
    searchValues: ["Take Point Formula"]
  },
  {
    canonical: "Take Point",
    aliases: [],
    searchValues: ["Take Point"]
  },
  {
    canonical: "Take",
    aliases: ["Accept a Double"],
    searchValues: ["Take", "Accept a Double"]
  },
  {
    canonical: "Accepting Cube Action",
    aliases: ["Accept a Double Position"],
    searchValues: ["Accepting Cube Action", "Accept a Double Position"]
  },
  {
    canonical: "Outfield Strategy",
    aliases: [],
    searchValues: ["Outfield Strategy"]
  },
  {
    canonical: "Outfield",
    aliases: [],
    searchValues: ["Outfield"]
  },
  {
    canonical: "Beta Take Example",
    aliases: [],
    searchValues: ["Beta Take Example"]
  },
  {
    canonical: "Alpha Take Example",
    aliases: [],
    searchValues: ["Alpha Take Example"]
  }
];

assert.equal(
  glossary.rankGlossaryItems(rankingCandidates, "take point")[0].canonical,
  "Take Point",
  "an exact canonical match ranks ahead of canonical-prefix matches"
);
assert.equal(
  glossary.rankGlossaryItems(
    rankingCandidates,
    "accept a double"
  )[0].canonical,
  "Take",
  "an exact alias match ranks ahead of alias-prefix matches"
);
assert.equal(
  glossary.rankGlossaryItems(rankingCandidates, "out field")[0].canonical,
  "Outfield",
  "a compact exact match ranks ahead of other compact partial matches"
);
assert.deepEqual(
  glossary
    .rankGlossaryItems(rankingCandidates, "take")
    .filter((item) => item.canonical.endsWith("Take Example"))
    .map((item) => item.canonical),
  ["Alpha Take Example", "Beta Take Example"],
  "results at the same rank are ordered alphabetically by canonical term"
);
assert.equal(
  glossary.glossaryMatchRank(
    { canonical: "Take Point", aliases: [] },
    "take point"
  ),
  1
);
assert.equal(
  glossary.glossaryMatchRank(
    { canonical: "Take", aliases: ["Accept a Double"] },
    "accept a double"
  ),
  2
);
assert.equal(
  glossary.glossaryMatchRank(
    { canonical: "Outfield", aliases: [] },
    "out field"
  ),
  3
);
assert.equal(
  glossary.glossaryMatchRank(
    {
      canonical: "Take Point",
      aliases: [],
      searchValues: [
        "Take Point",
        "The minimum winning chance needed to accept a double."
      ]
    },
    "minimum winning chance"
  ),
  9,
  "glossary filtering indexes definition text after canonical names and aliases"
);

function decodeHtmlAttribute(value) {
  return value
    .replaceAll("&quot;", '"')
    .replaceAll("&#39;", "'")
    .replaceAll("&amp;", "&");
}

function attributeValue(tag, name) {
  const match = tag.match(new RegExp(name + '="([^"]*)"'));
  return match ? decodeHtmlAttribute(match[1]) : "";
}

const generatedGlossaryMarkup = fs.readFileSync(
  path.join(__dirname, "../site/learn/glossary/_entries.html"),
  "utf8"
);
const generatedGlossaryItems = Array.from(
  generatedGlossaryMarkup.matchAll(
    /<details class="bms-glossary-entry"[^>]*>/g
  ),
  (match) => {
    const tag = match[0];
    const searchValues = JSON.parse(attributeValue(tag, "data-bms-search"));
    const categoriesAttribute = attributeValue(tag, "data-bms-categories");
    const primaryCategory = attributeValue(tag, "data-bms-category");
    return {
      slug: attributeValue(tag, "data-bms-slug"),
      aliasSlugs: JSON.parse(attributeValue(tag, "data-bms-aliases")),
      canonical: searchValues[0],
      aliases: JSON.parse(attributeValue(tag, "data-bms-alias-names")),
      categories: categoriesAttribute
        ? JSON.parse(categoriesAttribute)
        : primaryCategory
          ? [primaryCategory]
          : [],
      searchValues,
      element: { open: false }
    };
  }
);

const multiCategoryItems = [
  {
    categories: ["Checker Play", "Game Plans & Position Types"],
    element: { hidden: false, open: false },
    canonical: "Active Builder",
    aliases: [],
    tracks: []
  },
  {
    categories: ["Checker Play"],
    element: { hidden: false, open: false },
    canonical: "Ace",
    aliases: [],
    tracks: []
  }
];
assert.equal(
  glossary.itemMatchesGlossary(
    multiCategoryItems[0],
    "",
    ["Game Plans & Position Types"],
    []
  ),
  true,
  "a secondary category matches a multi-category entry"
);
assert.equal(
  glossary.expandCategoryMatches(
    multiCategoryItems,
    "Game Plans & Position Types"
  )[0].canonical,
  "Active Builder",
  "either Active Builder category resolves to the canonical entry"
);
multiCategoryItems.forEach((item) => {
  item.element.open = false;
});
assert.equal(
  glossary.expandCategoryMatches(
    multiCategoryItems,
    "Checker Play"
  ).length,
  2,
  "category filtering expands every matching entry"
);
assert.equal(
  multiCategoryItems.every((item) => item.element.open),
  true,
  "all category matches are expanded"
);
assert.equal(
  generatedGlossaryItems.length,
  625,
  "the JavaScript integration fixture uses every canonical entry"
);
assert.equal(
  generatedGlossaryItems.reduce(
    (count, item) => count + item.aliasSlugs.length,
    0
  ),
  184,
  "the JavaScript integration fixture uses every canonical alias"
);

[
  ["10 in the zone", "10 in the Zone"],
  ["Ten in the Zone", "10 in the Zone"],
  ["American Backgammon Tour", "ABT"],
  ["Ahead in the Race", "Ahead in the Count"]
].forEach(([query, expectedCanonical]) => {
  const matchingItems = generatedGlossaryItems.filter((item) =>
    glossary.itemMatchesGlossary(item, query, [], [])
  );
  const expanded = glossary.expandBestGlossaryMatch(
    generatedGlossaryItems,
    matchingItems,
    query
  );
  assert.equal(expanded.canonical, expectedCanonical);
  assert.equal(expanded.element.open, true);
  assert.equal(
    matchingItems.filter((item) => item.element.open).length,
    1,
    query + " expands exactly its best generated canonical match"
  );
});
const previouslyOpened = generatedGlossaryItems.find(
  (item) => item.canonical === "Ahead in the Count"
);
assert.equal(
  previouslyOpened.element.open,
  true,
  "an alias query expands its canonical target"
);
glossary.expandBestGlossaryMatch(
  generatedGlossaryItems,
  generatedGlossaryItems.filter((item) =>
    glossary.itemMatchesGlossary(item, "American Backgammon Tour", [], [])
  ),
  "American Backgammon Tour"
);
assert.equal(
  previouslyOpened.element.open,
  false,
  "a different active query closes the previously auto-opened result"
);
glossary.closeTermEntries(generatedGlossaryItems);
assert.equal(
  generatedGlossaryItems.some((item) => item.element.open),
  false,
  "clearing search restores collapsed generated term definitions"
);

assert.equal(
  glossary.itemMatchesGlossary(
    {
      category: "language, rules, and culture",
      tracks: [],
      searchValues: ["Player's Own Dice"]
    },
    "players-own dice",
    [],
    []
  ),
  true,
  "apostrophes and basic punctuation do not change search matching"
);

const letterGroups = [{ open: true }, { open: true }, { open: true }];
assert.equal(
  glossary.allGroupsExpanded(letterGroups),
  true,
  "all alphabetical sections initially report expanded"
);
assert.deepEqual(
  glossary.sectionControlState(letterGroups),
  { collapseDisabled: false, expandDisabled: true },
  "Expand all starts disabled when every letter is open"
);
glossary.setAllGroupsExpanded(letterGroups, false);
assert.equal(
  glossary.allGroupsExpanded(letterGroups),
  false,
  "Collapse all closes every alphabetical section"
);
assert.deepEqual(
  letterGroups.map((group) => group.open),
  [false, false, false]
);
assert.deepEqual(
  glossary.sectionControlState(letterGroups),
  { collapseDisabled: true, expandDisabled: false },
  "Collapse all is disabled when every letter is closed"
);
letterGroups[0].open = true;
assert.deepEqual(
  glossary.sectionControlState(letterGroups),
  { collapseDisabled: false, expandDisabled: false },
  "both controls are enabled for a mixed letter state"
);
glossary.setAllGroupsExpanded(letterGroups, true);
assert.equal(
  glossary.allGroupsExpanded(letterGroups),
  true,
  "Expand all opens every alphabetical section"
);

assert.equal(
  learn.normalizeLookupQuery("  take point  "),
  "take point",
  "the normal GET form submits a trimmed lookup query"
);
assert.equal(
  learn.normalizeLookupQuery("   "),
  "",
  "blank lookup submissions remain a no-op"
);

assert.deepEqual(
  learn.inlineGlossaryTooltipPosition(
    { left: 52, top: 780, bottom: 800 },
    { width: 320, height: 183 },
    390,
    844
  ),
  { left: 52, top: 589 },
  "a mobile tooltip flips above a term when it would overflow below"
);
assert.deepEqual(
  learn.inlineGlossaryTooltipPosition(
    { left: 1300, top: 100, bottom: 120 },
    { width: 320, height: 180 },
    1440,
    1000
  ),
  { left: 1108, top: 128 },
  "a desktop tooltip remains inside the right viewport edge"
);

const lookupCandidates = [
  {
    term: "Take Point",
    aliases: ["Point of Last Take"],
    short_definition: "The minimum winning chance needed to accept a double.",
    definition: "A full cube decision definition.",
    slug: "take-point"
  },
  {
    term: "Outfield",
    aliases: ["Out Field"],
    short_definition: "The outer board.",
    definition: "A full board definition.",
    slug: "outfield"
  }
];
assert.equal(
  learn.bestLookupEntry(lookupCandidates, "take point").slug,
  "take-point",
  "a direct canonical match wins"
);
assert.equal(
  learn.bestLookupEntry(lookupCandidates, "point of last take").slug,
  "take-point",
  "a direct alias match resolves to its canonical term"
);
assert.equal(
  learn.bestLookupEntry(lookupCandidates, "take poi").slug,
  "take-point",
  "a partial canonical match resolves to the best term"
);
assert.equal(
  learn.bestLookupEntry(lookupCandidates, "last ta").slug,
  "take-point",
  "a partial alias match resolves to the best canonical term"
);
assert.equal(
  learn.bestLookupEntry(lookupCandidates, "minimum winning chance").slug,
  "take-point",
  "short-definition search resolves to the canonical term"
);
assert.equal(
  learn.bestLookupEntry(lookupCandidates, "cube decision").slug,
  "take-point",
  "full-definition search resolves to the canonical term"
);
assert.equal(
  learn.bestLookupEntry(lookupCandidates, "no matching concept"),
  null,
  "an unrelated query does not invent a glossary result"
);

const lookupData = JSON.parse(
  fs.readFileSync(
    path.join(__dirname, "..", "site", "assets", "bms-glossary-lookup.json"),
    "utf8"
  )
);
assert.equal(lookupData.entries.length, 625);
assert.equal(
  lookupData.entries.reduce(
    (total, entry) => total + entry.aliases.length,
    0
  ),
  184
);
assert.equal(
  learn.bestLookupEntry(lookupData.entries, "Ahead in the Race").term,
  "Ahead in the Count",
  "generated lookup data supports approved alias search"
);

[
  ["?q=out%20field", "out field"],
  ["?q=take-point", "take-point"],
  ["?q=Accept%20a%20Double", "Accept a Double"]
].forEach(([search, expected]) => {
  assert.equal(
    glossary.glossaryStateFromSearch(search).query,
    expected,
    search + " is available before initial filtering"
  );
});

const combinedState = glossary.glossaryStateFromSearch(
  "?q=take+point&category=cube%20and%20scoring&track=Doubling%20Cube"
);
assert.deepEqual(combinedState, {
  query: "take point",
  categories: ["cube and scoring"],
  tracks: ["Doubling Cube"]
});
assert.equal(
  glossary.itemMatchesGlossary(
    {
      category: "cube and scoring",
      tracks: ["Doubling Cube"],
      searchValues: ["Take Point", "Accept a Double"]
    },
    combinedState.query,
    combinedState.categories,
    combinedState.tracks
  ),
  true,
  "initial q, category, and track state is applied together"
);

assert.deepEqual(
  glossary.glossaryStateFromSearch(
    "?category=cube%20and%20scoring&track=Doubling%20Cube",
    "take point"
  ),
  {
    query: "take point",
    categories: ["cube and scoring"],
    tracks: ["Doubling Cube"]
  },
  "Quarto's captured q is restored after Quarto Search cleans the live URL"
);

const clearedUrl = new URL(
  glossary.urlWithoutGlossaryQuery(
    "https://backgammon-made-simple.github.io/learn/glossary/" +
      "?q=take+point&category=cube%20and%20scoring&track=Doubling%20Cube"
  )
);
assert.equal(clearedUrl.searchParams.has("q"), false);
assert.deepEqual(
  clearedUrl.searchParams.getAll("category"),
  ["cube and scoring"],
  "global section actions preserve category filters"
);
assert.deepEqual(
  clearedUrl.searchParams.getAll("track"),
  ["Doubling Cube"],
  "global section actions preserve learning-track filters"
);
assert.equal(
  glossary.urlWithoutGlossaryFilters(
    "https://backgammon-made-simple.github.io/learn/glossary/" +
      "?q=take&category=Cube%20Action&track=Doubling%20Cube#take"
  ),
  "https://backgammon-made-simple.github.io/learn/glossary/#take",
  "related-term navigation clears all incompatible filters"
);

const currentGlossaryUrl =
  "https://backgammon-made-simple.github.io/learn/glossary/" +
  "?q=take-point&category=cube%20and%20scoring&track=Doubling%20Cube";
const letterUrl = new URL(
  glossary.letterNavigationUrl(currentGlossaryUrl, "#letter-t")
);
assert.equal(letterUrl.pathname, "/learn/glossary/");
assert.equal(letterUrl.searchParams.has("q"), false);
assert.deepEqual(
  letterUrl.searchParams.getAll("category"),
  ["cube and scoring"],
  "A-Z navigation preserves category filters"
);
assert.deepEqual(letterUrl.searchParams.getAll("track"), ["Doubling Cube"]);
assert.equal(letterUrl.hash, "#letter-t");
assert.equal(
  glossary.letterNavigationUrl(
    currentGlossaryUrl,
    "./#letter-a"
  ).endsWith(
    "?category=cube+and+scoring&track=Doubling+Cube#letter-a"
  ),
  true,
  "explicit A-Z navigation clears only q on the current glossary page"
);

const fragmentItems = [
  {
    slug: "take",
    aliasSlugs: ["accept-a-double"],
    letter: "T",
    element: { open: false }
  },
  {
    slug: "prime",
    aliasSlugs: [],
    letter: "P",
    element: { open: false }
  }
];
assert.equal(
  glossary.canonicalSlugForFragment(fragmentItems, "#take"),
  "take",
  "canonical fragments resolve directly"
);
assert.equal(
  glossary.canonicalSlugForFragment(
    fragmentItems,
    "#accept-a-double"
  ),
  "take",
  "alias fragments resolve to their canonical entry"
);
assert.equal(
  new URL(
    glossary.normalizedTermFragmentUrl(
      "https://backgammon-made-simple.github.io/learn/glossary/" +
        "?track=Doubling%20Cube#accept-a-double",
      "take"
    )
  ).hash,
  "#take",
  "alias fragments normalize without changing the glossary route"
);
glossary.setExactlyOneExpandedTerm(fragmentItems, fragmentItems[1]);
assert.deepEqual(
  glossary.termDisclosureState(fragmentItems),
  [false, true],
  "direct term navigation expands exactly one canonical entry"
);
assert.equal(glossary.hasAtMostOneExpandedTerm(fragmentItems), true);
glossary.closeTermEntries(fragmentItems);
assert.deepEqual(
  glossary.termDisclosureState(fragmentItems),
  [false, false],
  "letter browsing restores collapsed term definitions"
);
assert.equal(
  glossary.itemMatchesLetter(fragmentItems[0], "T"),
  true,
  "letter browsing can show every term summary for its selected letter"
);
assert.equal(
  glossary.samePageFragmentUrl(
    currentGlossaryUrl,
    "/learn/cube/#take-point"
  ),
  "",
  "a fragment on another page is not treated as glossary navigation"
);
assert.equal(
  glossary.samePageFragmentUrl(currentGlossaryUrl, "https://example.com/#A"),
  "",
  "external fragments are not treated as same-page navigation"
);

console.log("Learn and glossary filter logic passed.");
