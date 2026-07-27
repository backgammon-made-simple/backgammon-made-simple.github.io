(function () {
  "use strict";

  const ENTRY_SELECTOR = "[data-bms-glossary-entry]";
  const CATEGORY_SELECTOR = "[data-bms-glossary-filter-category]";
  const TRACK_SELECTOR = "[data-bms-glossary-filter-track]";

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

  function normalizeSearch(value) {
    return String(value || "")
      .normalize("NFKD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLocaleLowerCase()
      .replace(/['’‘`]/g, "")
      .replace(/[^\p{L}\p{N}]+/gu, " ")
      .replace(/\s+/g, " ")
      .trim();
  }

  function normalizeCompact(value) {
    return normalizeSearch(value).replace(/\s+/g, "");
  }

  function matchesAny(values, selected) {
    return selected.length === 0 || selected.some(function (value) {
      return values.includes(value);
    });
  }

  function allGroupsExpanded(groups) {
    return groups.length > 0 && groups.every(function (group) {
      return Boolean(group.open);
    });
  }

  function setAllGroupsExpanded(groups, expanded) {
    groups.forEach(function (group) {
      group.open = expanded;
    });
  }

  function itemMatchesGlossary(item, query, categories, tracks) {
    const normalizedWords = normalizeSearch(query);
    const normalizedCompact = normalizeCompact(query);
    const searchMatch =
      !normalizedWords ||
      item.searchValues.some(function (value) {
        return (
          normalizeSearch(value).includes(normalizedWords) ||
          normalizeCompact(value).includes(normalizedCompact)
        );
      });
    return (
      searchMatch &&
      matchesAny([item.category], categories) &&
      matchesAny(item.tracks, tracks)
    );
  }

  function displayCategory(value) {
    return value
      .replace(/\b\w/g, function (letter) {
        return letter.toLocaleUpperCase();
      })
      .replace(/\bAnd\b/g, "and");
  }

  function createCategoryButton(category) {
    const button = document.createElement("button");
    button.type = "button";
    button.className =
      "bms-glossary-filter bms-glossary-filter--category";
    button.dataset.bmsGlossaryFilterCategory = category;
    button.setAttribute("aria-pressed", "false");
    button.textContent = displayCategory(category);
    return button;
  }

  function sortedValues(values) {
    return Array.from(values).sort(function (left, right) {
      return left.localeCompare(right);
    });
  }

  function openHashTarget() {
    if (!window.location.hash) {
      return;
    }
    const target = document.getElementById(
      decodeURIComponent(window.location.hash.slice(1))
    );
    if (!target) {
      return;
    }
    const group = target.closest("[data-bms-letter-group]");
    if (group instanceof HTMLDetailsElement) {
      group.open = true;
    }
  }

  function initializeGlossary() {
    const panel = document.querySelector("[data-bms-glossary-filters]");
    const groupContainer = document.querySelector(
      "[data-bms-glossary-groups]"
    );

    if (!panel || !groupContainer) {
      return;
    }

    const items = Array.from(
      groupContainer.querySelectorAll(ENTRY_SELECTOR)
    ).map(function (element) {
      return {
        element: element,
        category: element.dataset.bmsCategory || "",
        tracks: parseList(element.dataset.bmsTracks),
        searchValues: parseList(element.dataset.bmsSearch)
      };
    });
    const groups = Array.from(
      groupContainer.querySelectorAll("[data-bms-letter-group]")
    );
    const searchInput = panel.querySelector("[data-bms-glossary-search]");
    const categoryContainer = panel.querySelector(
      "[data-bms-glossary-category-filters]"
    );
    const resultCount = panel.querySelector(
      "[data-bms-glossary-result-count]"
    );
    const clearButton = panel.querySelector("[data-bms-glossary-clear]");
    const categoryDisclosure = panel.querySelector(
      "[data-bms-glossary-category-disclosure]"
    );
    const trackDisclosure = panel.querySelector(
      "[data-bms-glossary-track-disclosure]"
    );
    const sectionControl = document.querySelector(
      "[data-bms-glossary-section-control]"
    );
    const emptyState = document.querySelector("[data-bms-glossary-empty]");
    const selectedCategories = new Set();
    const selectedTracks = new Set();

    const categories = Array.from(
      new Set(items.map(function (item) {
        return item.category;
      }))
    ).sort(function (left, right) {
      return left.localeCompare(right);
    });
    categories.forEach(function (category) {
      categoryContainer.appendChild(createCategoryButton(category));
    });

    const parameters = new URLSearchParams(window.location.search);
    if (searchInput) {
      searchInput.value = parameters.get("q") || "";
    }
    parameters.getAll("category").forEach(function (value) {
      if (categories.includes(value)) {
        selectedCategories.add(value);
      }
    });
    const trackButtons = Array.from(panel.querySelectorAll(TRACK_SELECTOR));
    parameters.getAll("track").forEach(function (value) {
      if (
        trackButtons.some(function (button) {
          return button.dataset.bmsGlossaryFilterTrack === value;
        })
      ) {
        selectedTracks.add(value);
      }
    });
    if (categoryDisclosure instanceof HTMLDetailsElement) {
      categoryDisclosure.open = selectedCategories.size > 0;
    }
    if (trackDisclosure instanceof HTMLDetailsElement) {
      trackDisclosure.open = selectedTracks.size > 0;
    }

    function currentQuery() {
      return searchInput ? searchInput.value : "";
    }

    function hasActiveFilters() {
      return Boolean(
        normalizeSearch(currentQuery()) ||
          selectedCategories.size ||
          selectedTracks.size
      );
    }

    function updateSectionControl() {
      if (!sectionControl) {
        return;
      }
      const expanded = allGroupsExpanded(groups);
      sectionControl.textContent = expanded ? "Collapse all" : "Expand all";
      sectionControl.setAttribute("aria-expanded", expanded ? "true" : "false");
    }

    function setPressed(buttons, selected, datasetKey) {
      buttons.forEach(function (button) {
        const active = selected.has(button.dataset[datasetKey] || "");
        button.setAttribute("aria-pressed", active ? "true" : "false");
        button.classList.toggle("is-active", active);
      });
    }

    function updateUrl() {
      const next = new URL(window.location.href);
      next.searchParams.delete("q");
      next.searchParams.delete("category");
      next.searchParams.delete("track");
      if (normalizeSearch(currentQuery())) {
        next.searchParams.set("q", currentQuery().trim());
      }
      sortedValues(selectedCategories).forEach(function (value) {
        next.searchParams.append("category", value);
      });
      sortedValues(selectedTracks).forEach(function (value) {
        next.searchParams.append("track", value);
      });
      window.history.replaceState({}, "", next);
    }

    function updateAvailability() {
      const categoryButtons = Array.from(
        panel.querySelectorAll(CATEGORY_SELECTOR)
      );
      const tracks = sortedValues(selectedTracks);
      const selectedCategoryValues = sortedValues(selectedCategories);
      const query = currentQuery();

      categoryButtons.forEach(function (button) {
        const category =
          button.dataset.bmsGlossaryFilterCategory || "";
        const count = items.filter(function (item) {
          return itemMatchesGlossary(item, query, [category], tracks);
        }).length;
        button.disabled =
          count === 0 && !selectedCategories.has(category);
        button.title = count + (count === 1 ? " matching term" : " matching terms");
      });
      trackButtons.forEach(function (button) {
        const track = button.dataset.bmsGlossaryFilterTrack || "";
        const count = items.filter(function (item) {
          return itemMatchesGlossary(
            item,
            query,
            selectedCategoryValues,
            [track]
          );
        }).length;
        button.disabled = count === 0 && !selectedTracks.has(track);
        button.title = count + (count === 1 ? " matching term" : " matching terms");
      });
    }

    function applyFilters(options) {
      const shouldUpdateUrl = !options || options.updateUrl !== false;
      const categoriesToMatch = sortedValues(selectedCategories);
      const tracksToMatch = sortedValues(selectedTracks);
      const query = currentQuery();
      const active = hasActiveFilters();
      let visibleCount = 0;

      items.forEach(function (item) {
        const visible = itemMatchesGlossary(
          item,
          query,
          categoriesToMatch,
          tracksToMatch
        );
        item.element.hidden = !visible;
        if (visible) {
          visibleCount += 1;
        }
      });

      groups.forEach(function (group) {
        const hasVisible = Array.from(
          group.querySelectorAll(ENTRY_SELECTOR)
        ).some(function (entry) {
          return !entry.hidden;
        });
        group.hidden = !hasVisible;
        if (active && hasVisible) {
          group.open = true;
        }
      });

      setPressed(
        Array.from(panel.querySelectorAll(CATEGORY_SELECTOR)),
        selectedCategories,
        "bmsGlossaryFilterCategory"
      );
      setPressed(
        trackButtons,
        selectedTracks,
        "bmsGlossaryFilterTrack"
      );
      updateAvailability();

      if (resultCount) {
        resultCount.textContent =
          "Showing " +
          visibleCount +
          (visibleCount === 1 ? " canonical term." : " canonical terms.");
      }
      if (emptyState) {
        emptyState.hidden = visibleCount !== 0;
      }
      if (clearButton) {
        clearButton.hidden = !active;
      }
      if (shouldUpdateUrl) {
        updateUrl();
      }
      updateSectionControl();
    }

    function toggleSelection(set, value) {
      if (set.has(value)) {
        set.delete(value);
      } else {
        set.add(value);
      }
    }

    panel.addEventListener("click", function (event) {
      const categoryButton = event.target.closest(CATEGORY_SELECTOR);
      const trackButton = event.target.closest(TRACK_SELECTOR);
      const clear = event.target.closest("[data-bms-glossary-clear]");

      if (categoryButton) {
        if (categoryDisclosure instanceof HTMLDetailsElement) {
          categoryDisclosure.open = true;
        }
        toggleSelection(
          selectedCategories,
          categoryButton.dataset.bmsGlossaryFilterCategory || ""
        );
        applyFilters();
        return;
      }
      if (trackButton) {
        if (trackDisclosure instanceof HTMLDetailsElement) {
          trackDisclosure.open = true;
        }
        toggleSelection(
          selectedTracks,
          trackButton.dataset.bmsGlossaryFilterTrack || ""
        );
        applyFilters();
        return;
      }
      if (clear) {
        selectedCategories.clear();
        selectedTracks.clear();
        if (searchInput) {
          searchInput.value = "";
        }
        if (categoryDisclosure instanceof HTMLDetailsElement) {
          categoryDisclosure.open = false;
        }
        if (trackDisclosure instanceof HTMLDetailsElement) {
          trackDisclosure.open = false;
        }
        setAllGroupsExpanded(groups, true);
        applyFilters();
      }
    });

    if (sectionControl) {
      sectionControl.addEventListener("click", function () {
        setAllGroupsExpanded(groups, !allGroupsExpanded(groups));
        updateSectionControl();
      });
    }

    groups.forEach(function (group) {
      group.addEventListener("toggle", updateSectionControl);
    });

    groupContainer.addEventListener("click", function (event) {
      const categoryButton = event.target.closest("[data-bms-card-category]");
      if (!categoryButton) {
        return;
      }
      selectedCategories.clear();
      selectedCategories.add(categoryButton.dataset.bmsCardCategory || "");
      if (categoryDisclosure instanceof HTMLDetailsElement) {
        categoryDisclosure.open = true;
      }
      applyFilters();
      panel.scrollIntoView({ behavior: "smooth", block: "start" });
    });

    if (searchInput) {
      searchInput.addEventListener("input", function () {
        applyFilters();
      });
    }
    document
      .querySelectorAll("[data-bms-letter-link]")
      .forEach(function (link) {
        link.addEventListener("click", function () {
          window.setTimeout(openHashTarget, 0);
        });
      });
    window.addEventListener("hashchange", openHashTarget);

    applyFilters({ updateUrl: false });
    openHashTarget();
    updateSectionControl();
  }

  function initializeBackToTop() {
    const control = document.querySelector(
      "[data-bms-glossary-back-to-top]"
    );
    const target = document.getElementById("bms-glossary-top");
    if (!control || !target) {
      return;
    }

    function updateVisibility() {
      control.hidden = window.scrollY < 600;
    }

    control.addEventListener("click", function (event) {
      event.preventDefault();
      target.focus({ preventScroll: true });
      const reducedMotion = window.matchMedia(
        "(prefers-reduced-motion: reduce)"
      ).matches;
      window.scrollTo({
        top: 0,
        behavior: reducedMotion ? "auto" : "smooth"
      });
    });
    window.addEventListener("scroll", updateVisibility, { passive: true });
    updateVisibility();
  }

  const publicApi = {
    allGroupsExpanded: allGroupsExpanded,
    itemMatchesGlossary: itemMatchesGlossary,
    matchesAny: matchesAny,
    normalizeCompact: normalizeCompact,
    normalizeSearch: normalizeSearch,
    parseList: parseList,
    setAllGroupsExpanded: setAllGroupsExpanded
  };

  if (typeof module !== "undefined" && module.exports) {
    module.exports = publicApi;
  }

  if (typeof document !== "undefined") {
    document.addEventListener("DOMContentLoaded", function () {
      initializeGlossary();
      initializeBackToTop();
    });
  }
})();
