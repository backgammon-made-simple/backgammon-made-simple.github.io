(function () {
  "use strict";

  const FIXTURE_SCHEMA = "bms-lesson-analysis-fixture-v1";
  const FIRST_ACTIONS = ["double", "roll"];
  const RESPONSES = ["pass", "take"];
  const fixtureRequests = new Map();
  let instanceCounter = 0;

  function cleanToken(value) {
    return String(value || "component")
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "") || "component";
  }

  function nextInstanceId(kind, fixtureId) {
    instanceCounter += 1;
    return [
      "bms-analysis",
      cleanToken(kind),
      cleanToken(fixtureId),
      String(instanceCounter)
    ].join("-");
  }

  function resetInstanceCounter() {
    instanceCounter = 0;
  }

  function optionalText(value, fallback) {
    if (value === null || value === undefined || value === "") {
      return fallback || "Not supplied";
    }
    return String(value);
  }

  function formatEquity(value) {
    if (value === null || value === undefined || Number.isNaN(Number(value))) {
      return "Not supplied";
    }
    const number = Number(value);
    return (number >= 0 ? "+" : "") + number.toFixed(3);
  }

  function formatProbability(value) {
    if (value === null || value === undefined || Number.isNaN(Number(value))) {
      return "Not supplied";
    }
    return (Number(value) * 100).toFixed(1) + "%";
  }

  function humanize(value) {
    return String(value || "")
      .replace(/_/g, " ")
      .replace(/\b\w/g, function (letter) {
        return letter.toUpperCase();
      });
  }

  function assetUrl(assetRoot, assetName) {
    const value = optionalText(assetName, "");
    if (!value) {
      throw new Error("Lesson analysis fixture is missing an SVG asset name.");
    }
    if (/^(?:https?:)?\//.test(value)) {
      return value;
    }
    const root = optionalText(assetRoot, "").replace(/\/?$/, "/");
    if (!root || value.includes("..")) {
      throw new Error("Lesson analysis fixture has an unsafe SVG asset path.");
    }
    return root + value.replace(/^\/+/, "");
  }

  function cubeDecisionState(fixture, action, response) {
    const normalizedAction = String(action || "").toLowerCase();
    if (!FIRST_ACTIONS.includes(normalizedAction)) {
      throw new Error("Cube action must be Double or Roll.");
    }
    if (!fixture || !fixture.actions || !fixture.actions[normalizedAction]) {
      throw new Error("Cube fixture does not define the selected action.");
    }
    const actionData = fixture.actions[normalizedAction];
    const accepted =
      String(fixture.correct_first_action || "").toLowerCase() ===
      normalizedAction;
    const responder =
      normalizedAction === "double" &&
      accepted &&
      actionData.responder
        ? actionData.responder
        : null;
    let responseData = null;
    let responseAccepted = null;

    if (response !== null && response !== undefined) {
      const normalizedResponse = String(response).toLowerCase();
      if (!RESPONSES.includes(normalizedResponse)) {
        throw new Error("Cube response must be Pass or Take.");
      }
      if (
        !responder ||
        !responder.responses ||
        !responder.responses[normalizedResponse]
      ) {
        throw new Error("Cube fixture does not define the selected response.");
      }
      responseData = responder.responses[normalizedResponse];
      responseAccepted =
        String(responder.correct_response || "").toLowerCase() ===
        normalizedResponse;
    }

    return {
      action: normalizedAction,
      actionAccepted: accepted,
      actionData: actionData,
      responder: responder,
      responseAccepted: responseAccepted,
      responseData: responseData
    };
  }

  function checkerCandidateState(fixture, candidateId) {
    if (!fixture || !Array.isArray(fixture.candidates)) {
      throw new Error("Checker fixture must define candidate moves.");
    }
    const candidate = fixture.candidates.find(function (item) {
      return item && item.id === candidateId;
    });
    if (!candidate) {
      throw new Error("Checker fixture does not define the selected candidate.");
    }
    return candidate;
  }

  function validateFixtureDocument(data) {
    if (!data || data.schema_version !== FIXTURE_SCHEMA) {
      throw new Error("Unsupported lesson analysis fixture schema.");
    }
    if (
      !data.fixture_status ||
      !data.fixture_status.message ||
      !data.asset_root
    ) {
      throw new Error("Lesson analysis fixture requires status and asset root.");
    }
    return data;
  }

  function loadFixtures(url) {
    if (!fixtureRequests.has(url)) {
      fixtureRequests.set(
        url,
        fetch(url, { credentials: "same-origin" }).then(function (response) {
          if (!response.ok) {
            throw new Error("Lesson analysis fixtures failed to load.");
          }
          return response.json();
        }).then(validateFixtureDocument)
      );
    }
    return fixtureRequests.get(url);
  }

  function element(tagName, className, text) {
    const node = document.createElement(tagName);
    if (className) {
      node.className = className;
    }
    if (text !== undefined && text !== null) {
      node.textContent = text;
    }
    return node;
  }

  function disclosure(id, summaryText, className) {
    const details = element("details", className || "bms-analysis-disclosure");
    const summary = element("summary", "", summaryText);
    const content = element("div", "bms-analysis-disclosure-content");
    details.id = id;
    content.id = id + "-content";
    summary.setAttribute("aria-controls", content.id);
    summary.setAttribute("aria-expanded", "false");
    details.addEventListener("toggle", function () {
      summary.setAttribute("aria-expanded", details.open ? "true" : "false");
    });
    details.append(summary, content);
    return {
      content: content,
      details: details,
      summary: summary
    };
  }

  function figureFor(image, assetRoot, className) {
    const figure = element("figure", className || "bms-analysis-position");
    const img = element("img", "bms-analysis-position-image");
    img.src = assetUrl(assetRoot, image.image);
    img.alt = optionalText(image.alt || image.image_alt, "Fixture position");
    img.width = 1200;
    img.height = 910;
    img.loading = "eager";
    img.decoding = "async";
    figure.appendChild(img);
    return { figure: figure, image: img };
  }

  function definitionList(rows, className) {
    const list = element("dl", className || "bms-analysis-metrics");
    rows.forEach(function (row) {
      list.append(
        element("dt", "", row[0]),
        element("dd", "", row[1])
      );
    });
    return list;
  }

  function analysisRows(analysis) {
    const rows = [
      ["Recommendation", optionalText(analysis && analysis.recommendation)]
    ];
    Object.entries((analysis && analysis.equities) || {}).forEach(
      function (entry) {
        rows.push(["Equity — " + humanize(entry[0]), formatEquity(entry[1])]);
      }
    );
    Object.entries((analysis && analysis.winning_probabilities) || {}).forEach(
      function (entry) {
        rows.push([
          "Probability — " + humanize(entry[0]),
          formatProbability(entry[1])
        ]);
      }
    );
    return rows;
  }

  function appendAnalysisDisclosure(
    parent,
    id,
    analysis,
    fixtureStatus,
    summaryText
  ) {
    const section = disclosure(
      id,
      summaryText || "Show fixture analysis",
      "bms-analysis-disclosure bms-analysis-disclosure--nested"
    );
    section.content.append(
      definitionList(analysisRows(analysis)),
      element(
        "p",
        "bms-analysis-explanation",
        optionalText(analysis && analysis.explanation)
      ),
      element(
        "p",
        "bms-analysis-fixture-note",
        fixtureStatus.message
      )
    );
    parent.appendChild(section.details);
    return section;
  }

  function choiceButton(label, value) {
    const button = element(
      "button",
      "bms-button-outline bms-analysis-choice",
      label
    );
    button.type = "button";
    button.dataset.bmsAnalysisChoice = value;
    button.setAttribute("aria-pressed", "false");
    return button;
  }

  function setPressed(group, selected) {
    group
      .querySelectorAll("[data-bms-analysis-choice]")
      .forEach(function (button) {
        button.setAttribute(
          "aria-pressed",
          button.dataset.bmsAnalysisChoice === selected ? "true" : "false"
        );
      });
  }

  function mountCube(host, fixtures, fixtureId) {
    const fixture = fixtures.cube_cases && fixtures.cube_cases[fixtureId];
    if (!fixture) {
      throw new Error("Unknown cube lesson fixture: " + fixtureId);
    }

    const instanceId = nextInstanceId("cube", fixtureId);
    const article = element("article", "bms-lesson-analysis bms-cube-analysis");
    const heading = element("h3", "bms-analysis-title", fixture.title);
    const initialFigure = figureFor(fixture.initial, fixtures.asset_root);
    const prompt = element("p", "bms-analysis-prompt", fixture.prompt);
    const group = element("div", "bms-analysis-choice-row");
    const status = element(
      "p",
      "bms-analysis-choice-status",
      "Choose Double or Roll to reveal the fixture answer."
    );
    const firstAnswer = disclosure(
      instanceId + "-first-answer",
      "Answer",
      "bms-analysis-disclosure bms-analysis-answer"
    );
    const doubleButton = choiceButton("Double", "double");
    const rollButton = choiceButton("Roll", "roll");

    heading.id = instanceId + "-title";
    article.setAttribute("aria-labelledby", heading.id);
    article.dataset.bmsAnalysisInstance = instanceId;
    group.setAttribute("role", "group");
    group.setAttribute("aria-label", fixture.prompt);
    group.append(doubleButton, rollButton);
    status.setAttribute("aria-live", "polite");
    firstAnswer.details.hidden = true;

    function renderResponse(responder, response) {
      const state = cubeDecisionState(fixture, "double", response);
      const responseAnswer = article.querySelector(
        "#" + instanceId + "-response-answer"
      );
      const responseGroup = article.querySelector(
        "[data-bms-cube-response-group]"
      );
      if (!responseAnswer || !responseGroup) {
        return;
      }
      setPressed(responseGroup, response);
      const responseSummary = responseAnswer.querySelector(":scope > summary");
      const responseContent = responseAnswer.querySelector(
        ":scope > .bms-analysis-disclosure-content"
      );
      responseSummary.textContent =
        humanize(response) +
        ": " +
        (state.responseAccepted ? "fixture answer" : "review the fixture answer");
      responseContent.replaceChildren(
        element(
          "p",
          "bms-analysis-answer-summary",
          state.responseData.summary
        )
      );
      appendAnalysisDisclosure(
        responseContent,
        instanceId + "-response-analysis",
        state.responseData.analysis,
        fixtures.fixture_status,
        "Show response analysis"
      );
      responseAnswer.hidden = false;
      responseAnswer.open = true;
      status.textContent =
        humanize(response) +
        " selected. " +
        (state.responseAccepted
          ? "This is the fixture response."
          : "Open the response analysis to compare it.");
    }

    function renderFirstAction(action) {
      const state = cubeDecisionState(fixture, action);
      setPressed(group, action);
      firstAnswer.summary.textContent =
        humanize(action) +
        ": " +
        (state.actionAccepted ? "fixture answer" : "review the fixture answer");
      firstAnswer.content.replaceChildren(
        element(
          "p",
          "bms-analysis-answer-summary",
          state.actionData.summary
        )
      );

      if (state.actionData.position) {
        firstAnswer.content.appendChild(
          figureFor(
            state.actionData.position,
            fixtures.asset_root,
            "bms-analysis-position bms-analysis-position--answer"
          ).figure
        );
      }

      if (state.actionData.analysis) {
        appendAnalysisDisclosure(
          firstAnswer.content,
          instanceId + "-first-analysis",
          state.actionData.analysis,
          fixtures.fixture_status,
          "Show first-decision analysis"
        );
      }

      if (state.responder) {
        const responderSection = element(
          "section",
          "bms-analysis-responder"
        );
        const responderHeading = element(
          "h4",
          "bms-analysis-responder-title",
          "Responder decision"
        );
        const responderFigure = figureFor(
          {
            image: state.responder.image,
            alt: state.responder.alt
          },
          fixtures.asset_root,
          "bms-analysis-position bms-analysis-position--responder"
        );
        const responderPrompt = element(
          "p",
          "bms-analysis-prompt",
          state.responder.prompt
        );
        const responseGroup = element(
          "div",
          "bms-analysis-choice-row"
        );
        const passButton = choiceButton("Pass", "pass");
        const takeButton = choiceButton("Take", "take");
        const responseAnswer = disclosure(
          instanceId + "-response-answer",
          "Response answer",
          "bms-analysis-disclosure bms-analysis-answer bms-analysis-answer--response"
        );

        responderHeading.id = instanceId + "-responder-title";
        responderSection.setAttribute(
          "aria-labelledby",
          responderHeading.id
        );
        responseGroup.dataset.bmsCubeResponseGroup = "";
        responseGroup.setAttribute("role", "group");
        responseGroup.setAttribute("aria-label", state.responder.prompt);
        responseGroup.append(passButton, takeButton);
        responseAnswer.details.hidden = true;
        passButton.addEventListener("click", function () {
          renderResponse(state.responder, "pass");
        });
        takeButton.addEventListener("click", function () {
          renderResponse(state.responder, "take");
        });
        responderSection.append(
          responderHeading,
          responderFigure.figure,
          responderPrompt,
          responseGroup,
          responseAnswer.details
        );
        firstAnswer.content.appendChild(responderSection);
      }

      firstAnswer.details.hidden = false;
      firstAnswer.details.open = true;
      status.textContent =
        humanize(action) +
        " selected. " +
        (state.actionAccepted
          ? "This is the fixture answer."
          : "Open the analysis to compare it.");
    }

    doubleButton.addEventListener("click", function () {
      renderFirstAction("double");
    });
    rollButton.addEventListener("click", function () {
      renderFirstAction("roll");
    });

    article.append(
      heading,
      initialFigure.figure,
      prompt,
      group,
      status,
      firstAnswer.details
    );
    host.replaceChildren(article);
  }

  function candidateMetricRows(candidate) {
    const rows = [
      ["Selected move", candidate.label],
      ["Equity", formatEquity(candidate.equity)],
      ["Equity loss", formatEquity(candidate.equity_loss)]
    ];
    Object.entries(candidate.winning_probabilities || {}).forEach(
      function (entry) {
        rows.push([
          "Probability — " + humanize(entry[0]),
          formatProbability(entry[1])
        ]);
      }
    );
    return rows;
  }

  function mountChecker(host, fixtures, fixtureId) {
    const fixture = fixtures.checker_cases && fixtures.checker_cases[fixtureId];
    if (!fixture) {
      throw new Error("Unknown checker lesson fixture: " + fixtureId);
    }

    const instanceId = nextInstanceId("checker", fixtureId);
    const article = element(
      "article",
      "bms-lesson-analysis bms-checker-analysis"
    );
    const heading = element("h3", "bms-analysis-title", fixture.title);
    const position = figureFor(fixture.initial, fixtures.asset_root);
    const prompt = element("p", "bms-analysis-prompt", fixture.prompt);
    const group = element("div", "bms-analysis-choice-row");
    const status = element(
      "p",
      "bms-analysis-choice-status",
      "Choose a supplied candidate to update the position and metrics."
    );
    const metrics = element("div", "bms-analysis-candidate-result");

    heading.id = instanceId + "-title";
    article.setAttribute("aria-labelledby", heading.id);
    article.dataset.bmsAnalysisInstance = instanceId;
    group.setAttribute("role", "group");
    group.setAttribute("aria-label", fixture.prompt);
    status.setAttribute("aria-live", "polite");
    metrics.appendChild(
      element(
        "p",
        "bms-analysis-empty",
        "No candidate selected. The shared starting SVG remains visible."
      )
    );

    fixture.candidates.forEach(function (candidate) {
      const button = choiceButton(candidate.label, candidate.id);
      button.addEventListener("click", function () {
        const selected = checkerCandidateState(fixture, candidate.id);
        setPressed(group, candidate.id);
        position.image.src = assetUrl(fixtures.asset_root, selected.image);
        position.image.alt = optionalText(
          selected.image_alt,
          selected.label + " fixture result"
        );
        metrics.replaceChildren(
          definitionList(candidateMetricRows(selected)),
          element(
            "p",
            "bms-analysis-explanation",
            optionalText(selected.explanation)
          )
        );
        status.textContent =
          selected.label +
          " selected. The supplied position and metrics are displayed.";
      });
      group.appendChild(button);
    });

    const engineAnalysis = disclosure(
      instanceId + "-engine-analysis",
      "Show engine-analysis fixture",
      "bms-analysis-disclosure"
    );
    engineAnalysis.content.append(
      definitionList([
        ["Recommendation", optionalText(fixture.recommendation)],
        [
          "Engine",
          optionalText(fixture.analysis && fixture.analysis.engine)
        ],
        [
          "Setting",
          optionalText(fixture.analysis && fixture.analysis.setting)
        ]
      ]),
      element(
        "p",
        "bms-analysis-explanation",
        optionalText(fixture.analysis && fixture.analysis.explanation)
      ),
      element(
        "p",
        "bms-analysis-fixture-note",
        fixtures.fixture_status.message
      )
    );

    article.append(
      heading,
      position.figure,
      prompt,
      group,
      status,
      metrics,
      engineAnalysis.details
    );
    host.replaceChildren(article);
  }

  function showMountError(host, error) {
    const message = element(
      "p",
      "bms-analysis-error",
      "This lesson analysis fixture could not be loaded."
    );
    message.setAttribute("role", "alert");
    message.title = String(error && error.message ? error.message : error);
    host.replaceChildren(message);
  }

  function mountHost(host) {
    if (!host || host.dataset.bmsAnalysisMounted === "true") {
      return Promise.resolve();
    }
    host.dataset.bmsAnalysisMounted = "true";
    const url = host.dataset.bmsFixtureSrc;
    const fixtureId = host.dataset.bmsFixtureId;
    if (!url || !fixtureId) {
      showMountError(host, new Error("Fixture source and ID are required."));
      return Promise.resolve();
    }
    host.setAttribute("aria-busy", "true");
    return loadFixtures(url)
      .then(function (fixtures) {
        if (host.hasAttribute("data-bms-cube-decision")) {
          mountCube(host, fixtures, fixtureId);
        } else if (host.hasAttribute("data-bms-checker-decision")) {
          mountChecker(host, fixtures, fixtureId);
        } else {
          throw new Error("Unknown lesson analysis component type.");
        }
      })
      .catch(function (error) {
        showMountError(host, error);
      })
      .finally(function () {
        host.removeAttribute("aria-busy");
      });
  }

  function hostsIn(rootElement) {
    if (!rootElement) {
      return [];
    }
    const selector =
      "[data-bms-cube-decision], [data-bms-checker-decision]";
    const hosts = [];
    if (
      typeof rootElement.matches === "function" &&
      rootElement.matches(selector)
    ) {
      hosts.push(rootElement);
    }
    if (typeof rootElement.querySelectorAll === "function") {
      rootElement.querySelectorAll(selector).forEach(function (host) {
        hosts.push(host);
      });
    }
    return hosts;
  }

  function mount(rootElement) {
    return Promise.all(hostsIn(rootElement).map(mountHost));
  }

  function hookContinuousLessons() {
    if (
      typeof window === "undefined" ||
      !window.BMSLearn ||
      typeof window.BMSLearn.mountLesson !== "function" ||
      window.BMSLearn.bmsLessonAnalysisHooked
    ) {
      return;
    }
    const originalMount = window.BMSLearn.mountLesson;
    window.BMSLearn.mountLesson = function (rootElement) {
      const result = originalMount(rootElement);
      mount(rootElement);
      return result;
    };
    window.BMSLearn.bmsLessonAnalysisHooked = true;
  }

  const publicApi = {
    assetUrl: assetUrl,
    checkerCandidateState: checkerCandidateState,
    cubeDecisionState: cubeDecisionState,
    formatEquity: formatEquity,
    formatProbability: formatProbability,
    mount: mount,
    nextInstanceId: nextInstanceId,
    resetInstanceCounter: resetInstanceCounter,
    validateFixtureDocument: validateFixtureDocument
  };

  if (typeof module !== "undefined" && module.exports) {
    module.exports = publicApi;
  }

  if (typeof window !== "undefined") {
    window.BMSLessonAnalysis = Object.assign(
      window.BMSLessonAnalysis || {},
      publicApi
    );
    hookContinuousLessons();
  }

  if (typeof document !== "undefined") {
    document.addEventListener("DOMContentLoaded", function () {
      hookContinuousLessons();
      mount(document);
    });
  }
})();
