const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const analysis = require("../site/assets/bms-lesson-analysis.js");

const root = path.resolve(__dirname, "..");
const fixtures = JSON.parse(
  fs.readFileSync(
    path.join(root, "site/data/lesson-analysis-svg-mvp.json"),
    "utf8"
  )
);

assert.equal(
  analysis.validateFixtureDocument(fixtures),
  fixtures,
  "the checked-in fixture document is accepted"
);

const doubleTake = fixtures.cube_cases["cube-double-take"];
const rollReview = analysis.cubeDecisionState(doubleTake, "roll");
assert.equal(rollReview.actionAccepted, false);
assert.equal(rollReview.responder, null);
assert.equal(rollReview.actionData.analysis.recommendation, "Double");

const doubleChoice = analysis.cubeDecisionState(doubleTake, "double");
assert.equal(doubleChoice.actionAccepted, true);
assert.equal(doubleChoice.responder.correct_response, "take");
assert.equal(doubleChoice.actionData.analysis.recommendation, "Double");

const passReview = analysis.cubeDecisionState(doubleTake, "double", "pass");
assert.equal(passReview.responseAccepted, false);
assert.equal(passReview.responseData.analysis.recommendation, "Take");

const takeAnswer = analysis.cubeDecisionState(doubleTake, "double", "take");
assert.equal(takeAnswer.responseAccepted, true);
assert.equal(takeAnswer.responseData.analysis.recommendation, "Take");

const rollFixture = fixtures.cube_cases["cube-roll"];
assert.equal(
  analysis.cubeDecisionState(rollFixture, "roll").actionAccepted,
  true,
  "the component supports Roll as the accepted first action"
);
assert.equal(
  analysis.cubeDecisionState(rollFixture, "double").responder,
  null,
  "a rejected Double does not invent a responder decision"
);

const doublePass = fixtures.cube_cases["cube-double-pass"];
assert.equal(
  analysis.cubeDecisionState(doublePass, "double", "pass").responseAccepted,
  true,
  "the component supports Pass as the accepted cube response"
);
assert.equal(
  analysis.cubeDecisionState(doublePass, "double", "take").responseAccepted,
  false
);

assert.throws(
  () => analysis.cubeDecisionState(doubleTake, "beaver"),
  /Double or Roll/
);
assert.throws(
  () => analysis.cubeDecisionState(doubleTake, "double", "beaver"),
  /Pass or Take/
);

const checker = fixtures.checker_cases["checker-three-candidates"];
const candidate1 = analysis.checkerCandidateState(checker, "candidate-1");
const candidate2 = analysis.checkerCandidateState(checker, "candidate-2");
const candidate3 = analysis.checkerCandidateState(checker, "candidate-3");
assert.equal(candidate1.image, "candidate-1.svg");
assert.equal(candidate2.equity_loss, 0);
assert.equal(candidate3.winning_probabilities.win_gammon, null);
assert.throws(
  () => analysis.checkerCandidateState(checker, "candidate-4"),
  /does not define/
);

assert.equal(analysis.formatEquity(0.093), "+0.093");
assert.equal(analysis.formatEquity(-1), "-1.000");
assert.equal(analysis.formatEquity(null), "Not supplied");
assert.equal(analysis.formatProbability(0.58), "58.0%");
assert.equal(analysis.formatProbability(null), "Not supplied");

assert.equal(
  analysis.assetUrl(fixtures.asset_root, fixtures.cube_cases["cube-roll"].initial.image),
  "/assets/positions/lesson-analysis-svg-mvp/opening-fixture/starting.svg"
);
assert.throws(
  () => analysis.assetUrl(fixtures.asset_root, "../outside.svg"),
  /unsafe/
);

analysis.resetInstanceCounter();
const instanceIds = [
  analysis.nextInstanceId("cube", "cube-double-take"),
  analysis.nextInstanceId("cube", "cube-double-take"),
  analysis.nextInstanceId("checker", "checker-three-candidates")
];
assert.equal(new Set(instanceIds).size, instanceIds.length);
assert.match(instanceIds[0], /^bms-analysis-cube-cube-double-take-1$/);
assert.match(instanceIds[2], /^bms-analysis-checker-checker-three-candidates-3$/);

console.log("lesson analysis fixture logic passed");
