(function () {
  "use strict";

  const DIFFICULTY_SELECTOR = "[data-bms-filter-difficulty]";
  const TRACK_SELECTOR = "[data-bms-filter-track]";
  const LESSON_SELECTOR = "[data-bms-learn-item]";

  function parseList(value) {
    if (!value) {
      return [];
    }

    try {
      const parsed = JSON.parse(value);
      return Array.isArray(parsed) ? parsed.map(String) : [];
    } catch (_error) {
      return [];
    }
  }

  function matchesAny(values, selected) {
    return selected.length === 0 || selected.some(function (value) {
      return values.includes(value);
    });
  }

  function itemMatchesTaxonomy(item, difficulties, tracks) {
    return (
      matchesAny(item.difficulties, difficulties) &&
      matchesAny(item.tracks, tracks)
    );
  }

  function sortedValues(values) {
    return Array.from(values).sort(function (left, right) {
      return left.localeCompare(right);
    });
  }

  function normalizeLookupQuery(value) {
    return String(value || "").trim();
  }

  function initializeLearnFilters() {
    const panel = document.querySelector("[data-bms-learn-filters]");
    const list = document.querySelector("[data-bms-learn-list]");

    if (!panel || !list) {
      return;
    }

    const items = Array.from(list.querySelectorAll(LESSON_SELECTOR)).map(
      function (element) {
        return {
          element: element,
          difficulties: parseList(element.dataset.bmsDifficulties),
          tracks: parseList(element.dataset.bmsTracks)
        };
      }
    );
    const difficultyButtons = Array.from(
      panel.querySelectorAll(DIFFICULTY_SELECTOR)
    );
    const trackButtons = Array.from(panel.querySelectorAll(TRACK_SELECTOR));
    const resultCount = panel.querySelector("[data-bms-learn-result-count]");
    const clearButton = panel.querySelector("[data-bms-learn-clear]");
    const emptyState = document.querySelector("[data-bms-learn-empty]");
    const selectedDifficulties = new Set();
    const selectedTracks = new Set();
    const parameters = new URLSearchParams(window.location.search);

    parameters.getAll("difficulty").forEach(function (value) {
      if (
        difficultyButtons.some(function (button) {
          return button.dataset.bmsFilterDifficulty === value;
        })
      ) {
        selectedDifficulties.add(value);
      }
    });
    parameters.getAll("track").forEach(function (value) {
      if (
        trackButtons.some(function (button) {
          return button.dataset.bmsFilterTrack === value;
        })
      ) {
        selectedTracks.add(value);
      }
    });

    function setPressed(buttons, selected, datasetKey) {
      buttons.forEach(function (button) {
        const active = selected.has(button.dataset[datasetKey] || "");
        button.setAttribute("aria-pressed", active ? "true" : "false");
        button.classList.toggle("is-active", active);
      });
    }

    function updateUrl() {
      const next = new URL(window.location.href);
      next.searchParams.delete("difficulty");
      next.searchParams.delete("track");
      sortedValues(selectedDifficulties).forEach(function (value) {
        next.searchParams.append("difficulty", value);
      });
      sortedValues(selectedTracks).forEach(function (value) {
        next.searchParams.append("track", value);
      });
      window.history.replaceState({}, "", next);
    }

    function updateCounts() {
      difficultyButtons.forEach(function (button) {
        const value = button.dataset.bmsFilterDifficulty || "";
        const count = items.filter(function (item) {
          return (
            item.difficulties.includes(value) &&
            matchesAny(item.tracks, sortedValues(selectedTracks))
          );
        }).length;
        const countElement = button.querySelector(".bms-learn-filter-count");
        if (countElement) {
          countElement.textContent = "×" + count;
        }
        button.disabled =
          count === 0 && !selectedDifficulties.has(value);
      });

      trackButtons.forEach(function (button) {
        const value = button.dataset.bmsFilterTrack || "";
        const count = items.filter(function (item) {
          return (
            item.tracks.includes(value) &&
            matchesAny(item.difficulties, sortedValues(selectedDifficulties))
          );
        }).length;
        const countElement = button.querySelector(".bms-learn-filter-count");
        if (countElement) {
          countElement.textContent = "×" + count;
        }
        button.disabled = count === 0 && !selectedTracks.has(value);
      });
    }

    function applyFilters(options) {
      const shouldUpdateUrl = !options || options.updateUrl !== false;
      const difficulties = sortedValues(selectedDifficulties);
      const tracks = sortedValues(selectedTracks);
      let visibleCount = 0;

      items.forEach(function (item) {
        const visible = itemMatchesTaxonomy(item, difficulties, tracks);
        item.element.hidden = !visible;
        if (visible) {
          visibleCount += 1;
        }
      });

      setPressed(
        difficultyButtons,
        selectedDifficulties,
        "bmsFilterDifficulty"
      );
      setPressed(trackButtons, selectedTracks, "bmsFilterTrack");
      updateCounts();

      if (resultCount) {
        resultCount.textContent =
          "Showing " +
          visibleCount +
          (visibleCount === 1 ? " lesson." : " lessons.");
      }
      if (emptyState) {
        emptyState.hidden = visibleCount !== 0;
      }
      if (clearButton) {
        clearButton.hidden =
          selectedDifficulties.size === 0 && selectedTracks.size === 0;
      }
      if (shouldUpdateUrl) {
        updateUrl();
      }
    }

    function toggleSelection(set, value) {
      if (set.has(value)) {
        set.delete(value);
      } else {
        set.add(value);
      }
    }

    panel.addEventListener("click", function (event) {
      const difficultyButton = event.target.closest(DIFFICULTY_SELECTOR);
      const trackButton = event.target.closest(TRACK_SELECTOR);
      const clear = event.target.closest("[data-bms-learn-clear]");

      if (difficultyButton) {
        toggleSelection(
          selectedDifficulties,
          difficultyButton.dataset.bmsFilterDifficulty || ""
        );
        applyFilters();
        return;
      }
      if (trackButton) {
        toggleSelection(
          selectedTracks,
          trackButton.dataset.bmsFilterTrack || ""
        );
        applyFilters();
        return;
      }
      if (clear) {
        selectedDifficulties.clear();
        selectedTracks.clear();
        applyFilters();
      }
    });

    list.addEventListener("click", function (event) {
      const difficultyButton = event.target.closest(
        "[data-bms-card-difficulty]"
      );
      const trackButton = event.target.closest("[data-bms-card-track]");

      if (difficultyButton) {
        toggleSelection(
          selectedDifficulties,
          difficultyButton.dataset.bmsCardDifficulty || ""
        );
        applyFilters();
        panel.scrollIntoView({ behavior: "smooth", block: "start" });
        return;
      }
      if (trackButton) {
        toggleSelection(
          selectedTracks,
          trackButton.dataset.bmsCardTrack || ""
        );
        applyFilters();
        panel.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    });

    applyFilters({ updateUrl: false });
  }

  function placeLessonTrackLinks() {
    document
      .querySelectorAll("[data-bms-lesson-taxonomy]")
      .forEach(function (taxonomy) {
        const trackNav = taxonomy.querySelector(
          "[data-bms-lesson-track-nav]"
        );

        if (!trackNav) {
          return;
        }

        function place() {
          const wide = window.matchMedia("(min-width: 992px)").matches;
          const sidebar = document.getElementById("quarto-margin-sidebar");
          const toc = sidebar ? sidebar.querySelector("#TOC") : null;

          if (wide && sidebar) {
            let anchor = toc;
            while (
              anchor &&
              anchor.parentElement &&
              anchor.parentElement !== sidebar
            ) {
              anchor = anchor.parentElement;
            }
            if (anchor) {
              sidebar.insertBefore(trackNav, anchor);
            } else {
              sidebar.prepend(trackNav);
            }
          } else {
            taxonomy.appendChild(trackNav);
          }
        }

        place();
        window
          .matchMedia("(min-width: 992px)")
          .addEventListener("change", place);
      });
  }

  function initializeTermLookup() {
    document.querySelectorAll("[data-bms-term-lookup]").forEach(function (lookup) {
      const sourceParent = lookup.parentElement;
      const sourceNextSibling = lookup.nextSibling;
      const form = lookup.querySelector("[data-bms-term-lookup-form]");
      const input = form ? form.querySelector('input[name="q"]') : null;

      if (form && input) {
        form.addEventListener("submit", function (event) {
          const query = normalizeLookupQuery(input.value);
          if (!query) {
            event.preventDefault();
            input.focus();
            return;
          }
          input.value = query;
        });
      }

      function place() {
        const wide = window.matchMedia("(min-width: 992px)").matches;
        const sidebar = document.getElementById("quarto-margin-sidebar");
        const toc = sidebar ? sidebar.querySelector("#TOC") : null;

        if (wide && sidebar) {
          let anchor = toc;
          while (
            anchor &&
            anchor.parentElement &&
            anchor.parentElement !== sidebar
          ) {
            anchor = anchor.parentElement;
          }
          if (anchor) {
            sidebar.insertBefore(lookup, anchor);
          } else {
            sidebar.prepend(lookup);
          }
        } else if (sourceParent) {
          if (
            sourceNextSibling &&
            sourceNextSibling.parentNode === sourceParent
          ) {
            sourceParent.insertBefore(lookup, sourceNextSibling);
          } else {
            sourceParent.appendChild(lookup);
          }
        }
      }

      place();
      window
        .matchMedia("(min-width: 992px)")
        .addEventListener("change", place);
    });
  }

  function initializeAnswerChoices() {
    document.querySelectorAll(".bms-decision-prompt").forEach(function (prompt) {
      const panelId = prompt.dataset.answerPanel;
      const panel = panelId ? document.getElementById(panelId) : null;
      const buttons = Array.from(
        prompt.querySelectorAll(".bms-answer-choice")
      );
      const status = prompt.querySelector(".bms-choice-status");

      buttons.forEach(function (button) {
        button.addEventListener("click", function () {
          buttons.forEach(function (candidate) {
            candidate.setAttribute("aria-pressed", "false");
            candidate.classList.remove("is-selected");
          });

          button.setAttribute("aria-pressed", "true");
          button.classList.add("is-selected");

          if (status) {
            status.textContent =
              "Selected: " +
              button.textContent.trim() +
              ". The working answer is open below; correctness remains unverified.";
          }

          if (panel instanceof HTMLDetailsElement) {
            panel.open = true;
          }
        });
      });
    });
  }

  function initializeLazyAnalyzerFrames() {
    document
      .querySelectorAll("details.bms-analyzer-embed")
      .forEach(function (details) {
        details.addEventListener("toggle", function () {
          if (!details.open) {
            return;
          }

          const iframe = details.querySelector("iframe[data-src]");

          if (!iframe || iframe.getAttribute("src")) {
            return;
          }

          const source = iframe.dataset.src;

          if (!source) {
            return;
          }

          const status = details.querySelector(".bms-analyzer-status");

          if (status) {
            status.textContent = "Loading the analyzer…";
          }

          iframe.addEventListener(
            "load",
            function () {
              if (status) {
                status.textContent = "Analyzer loaded.";
              }
            },
            { once: true }
          );

          iframe.setAttribute("src", source);
          iframe.removeAttribute("data-src");
        });
      });
  }

  const publicApi = {
    itemMatchesTaxonomy: itemMatchesTaxonomy,
    matchesAny: matchesAny,
    normalizeLookupQuery: normalizeLookupQuery,
    parseList: parseList
  };

  if (typeof module !== "undefined" && module.exports) {
    module.exports = publicApi;
  }

  if (typeof document !== "undefined") {
    document.addEventListener("DOMContentLoaded", function () {
      initializeLearnFilters();
      initializeTermLookup();
      placeLessonTrackLinks();
      initializeAnswerChoices();
      initializeLazyAnalyzerFrames();
    });
  }
})();
