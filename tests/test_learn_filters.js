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
glossary.setAllGroupsExpanded(letterGroups, true);
assert.equal(
  glossary.allGroupsExpanded(letterGroups),
  true,
  "Expand all opens every alphabetical section"
);

console.log("Learn and glossary filter logic passed.");
