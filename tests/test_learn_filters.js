"use strict";

const assert = require("node:assert/strict");
const learn = require("../site/assets/bms-learn.js");
const glossary = require("../site/assets/bms-glossary.js");

const lessons = [
  {
    difficulties: ["Beginner", "Intermediate"],
    tracks: ["Doubling Cube"]
  },
  {
    difficulties: ["Intermediate", "Advanced"],
    tracks: ["Engines and Analysis"]
  },
  {
    difficulties: ["Beginner"],
    tracks: ["Opening Play", "Checker Play"]
  }
];

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
