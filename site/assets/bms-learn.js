(function () {
  "use strict";

  const DIFFICULTY_SELECTOR = "[data-bms-filter-difficulty]";
  const TRACK_SELECTOR = "[data-bms-filter-track]";
  const TERM_SELECTOR = "[data-bms-filter-term]";
  const LESSON_SELECTOR = "[data-bms-learn-item]";
  const GROUP_SELECTOR = "[data-bms-learn-group]";

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

  function normalizeLearnSearch(value) {
    return String(value || "")
      .normalize("NFKD")
      .replace(/[\u0300-\u036f]/g, "")
      .replace(/[^\p{L}\p{N}]+/gu, " ")
      .trim()
      .toLocaleLowerCase();
  }

  function itemMatchesLesson(item, query, difficulties, terms) {
    const normalizedQuery = normalizeLearnSearch(query);
    const matchesSearch =
      normalizedQuery.length === 0 ||
      item.searchValues.some(function (value) {
        return normalizeLearnSearch(value).includes(normalizedQuery);
      });
    return (
      matchesSearch &&
      matchesAny(item.difficulties, difficulties) &&
      matchesAny(item.terms, terms)
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

  function setAllGroupsExpanded(groups, expanded) {
    groups.forEach(function (group) {
      group.open = expanded;
    });
  }

  function groupControlState(groups) {
    const visibleGroups = groups.filter(function (group) {
      return !group.hidden;
    });
    return {
      collapseDisabled:
        visibleGroups.length === 0 ||
        visibleGroups.every(function (group) {
          return !group.open;
        }),
      expandDisabled:
        visibleGroups.length === 0 ||
        visibleGroups.every(function (group) {
          return group.open;
        })
    };
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
          track: element.dataset.bmsTrack || "",
          terms: parseList(element.dataset.bmsTerms),
          searchValues: parseList(element.dataset.bmsSearch)
        };
      }
    );
    const groups = Array.from(list.querySelectorAll(GROUP_SELECTOR));
    const difficultyButtons = Array.from(
      panel.querySelectorAll(DIFFICULTY_SELECTOR)
    );
    const trackButtons = Array.from(panel.querySelectorAll(TRACK_SELECTOR));
    const termButtons = Array.from(panel.querySelectorAll(TERM_SELECTOR));
    const searchInput = panel.querySelector("[data-bms-learn-search]");
    const resultCount = panel.querySelector("[data-bms-learn-result-count]");
    const clearButton = panel.querySelector("[data-bms-learn-clear]");
    const emptyState = document.querySelector("[data-bms-learn-empty]");
    const collapseAll = document.querySelector("[data-bms-learn-collapse-all]");
    const expandAll = document.querySelector("[data-bms-learn-expand-all]");
    const selectedDifficulties = new Set();
    const selectedTerms = new Set();
    let selectedTrack = "";
    const parameters = new URLSearchParams(window.location.search);
    if (searchInput) {
      searchInput.value = parameters.get("search") || "";
    }

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
        selectedTrack = value;
      }
    });
    parameters.getAll("term").forEach(function (value) {
      if (
        termButtons.some(function (button) {
          return button.dataset.bmsFilterTerm === value;
        })
      ) {
        selectedTerms.add(value);
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
      next.searchParams.delete("term");
      next.searchParams.delete("search");
      const query = searchInput ? searchInput.value.trim() : "";
      if (query) {
        next.searchParams.set("search", query);
      }
      sortedValues(selectedDifficulties).forEach(function (value) {
        next.searchParams.append("difficulty", value);
      });
      if (selectedTrack) {
        next.searchParams.set("track", selectedTrack);
      }
      sortedValues(selectedTerms).forEach(function (value) {
        next.searchParams.append("term", value);
      });
      window.history.replaceState({}, "", next);
    }

    function updateGroupControls() {
      const state = groupControlState(groups);
      if (collapseAll) {
        collapseAll.disabled = state.collapseDisabled;
      }
      if (expandAll) {
        expandAll.disabled = state.expandDisabled;
      }
    }

    function updateCounts() {
      const query = searchInput ? searchInput.value : "";
      const difficulties = sortedValues(selectedDifficulties);
      const terms = sortedValues(selectedTerms);
      difficultyButtons.forEach(function (button) {
        const value = button.dataset.bmsFilterDifficulty || "";
        const count = items.filter(function (item) {
          return (
            item.difficulties.includes(value) &&
            itemMatchesLesson(item, query, [], terms)
          );
        }).length;
        const countElement = button.querySelector(".bms-learn-filter-count");
        if (countElement) {
          countElement.textContent = "\u00d7" + count;
        }
        button.disabled =
          count === 0 && !selectedDifficulties.has(value);
      });

      trackButtons.forEach(function (button) {
        const value = button.dataset.bmsFilterTrack || "";
        const count = items.filter(function (item) {
          return (
            item.track === value &&
            itemMatchesLesson(item, query, difficulties, terms)
          );
        }).length;
        const countElement = button.querySelector(".bms-learn-filter-count");
        if (countElement) {
          countElement.textContent = "\u00d7" + count;
        }
        button.disabled = false;
      });

      termButtons.forEach(function (button) {
        const value = button.dataset.bmsFilterTerm || "";
        const count = items.filter(function (item) {
          return (
            item.terms.includes(value) &&
            itemMatchesLesson(item, query, difficulties, [])
          );
        }).length;
        const countElement = button.querySelector(".bms-learn-filter-count");
        if (countElement) {
          countElement.textContent = "\u00d7" + count;
        }
        button.disabled = count === 0 && !selectedTerms.has(value);
      });
    }

    function applyFilters(options) {
      const shouldUpdateUrl = !options || options.updateUrl !== false;
      const difficulties = sortedValues(selectedDifficulties);
      const terms = sortedValues(selectedTerms);
      const query = searchInput ? searchInput.value : "";
      let visibleCount = 0;

      items.forEach(function (item) {
        const visible = itemMatchesLesson(
          item,
          query,
          difficulties,
          terms
        );
        item.element.hidden = !visible;
        if (visible) {
          visibleCount += 1;
        }
      });

      groups.forEach(function (group) {
        const groupItems = Array.from(
          group.querySelectorAll(LESSON_SELECTOR)
        );
        const groupVisibleCount = groupItems.filter(function (element) {
          return !element.hidden;
        }).length;
        const totalCount = Number(group.dataset.bmsTotalLessons || "0");
        group.hidden =
          totalCount > 0 && groupVisibleCount === 0;
        const groupCount = group.querySelector(
          "[data-bms-learn-group-count]"
        );
        if (groupCount) {
          groupCount.textContent =
            groupVisibleCount +
            (groupVisibleCount === 1 ? " lesson" : " lessons");
        }
      });

      setPressed(
        difficultyButtons,
        selectedDifficulties,
        "bmsFilterDifficulty"
      );
      setPressed(
        trackButtons,
        new Set(selectedTrack ? [selectedTrack] : []),
        "bmsFilterTrack"
      );
      setPressed(termButtons, selectedTerms, "bmsFilterTerm");
      updateCounts();

      if (selectedTrack) {
        groups.forEach(function (group) {
          group.open = group.dataset.bmsTrackId === selectedTrack;
        });
      }
      updateGroupControls();

      if (resultCount) {
        resultCount.textContent =
          "Showing " +
          visibleCount +
          (visibleCount === 1 ? " lesson." : " lessons.");
      }
      if (emptyState) {
        emptyState.hidden = visibleCount !== 0 || items.length === 0;
      }
      if (clearButton) {
        clearButton.hidden =
          selectedDifficulties.size === 0 &&
          selectedTrack === "" &&
          selectedTerms.size === 0 &&
          normalizeLearnSearch(query).length === 0;
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
      const termButton = event.target.closest(TERM_SELECTOR);
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
        const value = trackButton.dataset.bmsFilterTrack || "";
        selectedTrack = selectedTrack === value ? "" : value;
        if (!selectedTrack) {
          setAllGroupsExpanded(groups, true);
        }
        applyFilters();
        return;
      }
      if (termButton) {
        toggleSelection(
          selectedTerms,
          termButton.dataset.bmsFilterTerm || ""
        );
        applyFilters();
        return;
      }
      if (clear) {
        selectedDifficulties.clear();
        selectedTerms.clear();
        selectedTrack = "";
        setAllGroupsExpanded(groups, true);
        if (searchInput) {
          searchInput.value = "";
        }
        applyFilters();
      }
    });

    if (searchInput) {
      searchInput.addEventListener("input", function () {
        applyFilters();
      });
    }

    list.addEventListener("click", function (event) {
      if (event.target.closest(".bms-learn-catalogue-link")) {
        event.stopPropagation();
      }
    });

    if (collapseAll) {
      collapseAll.addEventListener("click", function () {
        selectedTrack = "";
        setAllGroupsExpanded(groups, false);
        setPressed(trackButtons, new Set(), "bmsFilterTrack");
        updateGroupControls();
        updateUrl();
      });
    }
    if (expandAll) {
      expandAll.addEventListener("click", function () {
        selectedTrack = "";
        setAllGroupsExpanded(groups, true);
        setPressed(trackButtons, new Set(), "bmsFilterTrack");
        updateGroupControls();
        updateUrl();
      });
    }
    groups.forEach(function (group) {
      group.addEventListener("toggle", updateGroupControls);
    });

    applyFilters({ updateUrl: false });
  }

  function initializeLearnSidebarControls() {
    const sidebar = document.getElementById("quarto-sidebar");
    const menu = sidebar
      ? sidebar.querySelector(".sidebar-menu-container")
      : null;
    const sections = sidebar
      ? Array.from(sidebar.querySelectorAll(".sidebar-item-section"))
      : [];
    if (!menu || sections.length === 0) {
      return;
    }

    const controls = document.createElement("div");
    controls.className = "bms-learn-sidebar-actions";
    controls.setAttribute("role", "group");
    controls.setAttribute("aria-label", "Learn sidebar sections");
    controls.innerHTML =
      '<button type="button" data-bms-sidebar-collapse-all>Collapse all</button>' +
      '<button type="button" data-bms-sidebar-expand-all>Expand all</button>';
    menu.prepend(controls);
    const collapse = controls.querySelector("[data-bms-sidebar-collapse-all]");
    const expand = controls.querySelector("[data-bms-sidebar-expand-all]");

    function toggles() {
      return sections
        .map(function (section) {
          return section.querySelector(
            ":scope > .sidebar-item-container .sidebar-item-toggle"
          );
        })
        .filter(Boolean);
    }

    function setExpanded(expanded) {
      toggles().forEach(function (toggle) {
        const isExpanded = toggle.getAttribute("aria-expanded") === "true";
        if (isExpanded !== expanded) {
          toggle.click();
        }
      });
      update();
    }

    function update() {
      const states = toggles().map(function (toggle) {
        return toggle.getAttribute("aria-expanded") === "true";
      });
      if (collapse) {
        collapse.disabled = states.every(function (state) {
          return !state;
        });
      }
      if (expand) {
        expand.disabled = states.every(Boolean);
      }
    }

    if (collapse) {
      collapse.addEventListener("click", function () {
        setExpanded(false);
      });
    }
    if (expand) {
      expand.addEventListener("click", function () {
        setExpanded(true);
      });
    }
    toggles().forEach(function (toggle) {
      toggle.addEventListener("click", function () {
        window.setTimeout(update, 0);
      });
    });
    update();
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
    groupControlState: groupControlState,
    itemMatchesLesson: itemMatchesLesson,
    itemMatchesTaxonomy: itemMatchesTaxonomy,
    matchesAny: matchesAny,
    normalizeLearnSearch: normalizeLearnSearch,
    normalizeLookupQuery: normalizeLookupQuery,
    parseList: parseList,
    setAllGroupsExpanded: setAllGroupsExpanded
  };

  if (typeof module !== "undefined" && module.exports) {
    module.exports = publicApi;
  }

  if (typeof document !== "undefined") {
    document.addEventListener("DOMContentLoaded", function () {
      initializeLearnFilters();
      initializeLearnSidebarControls();
      initializeTermLookup();
      placeLessonTrackLinks();
      initializeAnswerChoices();
      initializeLazyAnalyzerFrames();
    });
  }
})();
