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

  function glossaryNames(item) {
    const values = Array.isArray(item.searchValues)
      ? item.searchValues.map(String)
      : [];
    return {
      canonical: String(item.canonical || values[0] || ""),
      aliases: Array.isArray(item.aliases)
        ? item.aliases.map(String)
        : values.slice(1)
    };
  }

  function glossaryMatchRank(item, query) {
    const normalizedQuery = normalizeSearch(query);
    if (!normalizedQuery) {
      return 0;
    }

    const compactQuery = normalizeCompact(query);
    const names = glossaryNames(item);
    const canonical = normalizeSearch(names.canonical);
    const compactCanonical = normalizeCompact(names.canonical);
    const aliases = names.aliases.map(normalizeSearch);
    const compactAliases = names.aliases.map(normalizeCompact);

    if (canonical === normalizedQuery) {
      return 1;
    }
    if (aliases.includes(normalizedQuery)) {
      return 2;
    }
    if (
      compactCanonical === compactQuery ||
      compactAliases.includes(compactQuery)
    ) {
      return 3;
    }
    if (canonical.startsWith(normalizedQuery)) {
      return 4;
    }
    if (aliases.some(function (alias) {
      return alias.startsWith(normalizedQuery);
    })) {
      return 5;
    }
    if (canonical.includes(normalizedQuery)) {
      return 6;
    }
    if (aliases.some(function (alias) {
      return alias.includes(normalizedQuery);
    })) {
      return 7;
    }
    if (
      compactCanonical.includes(compactQuery) ||
      compactAliases.some(function (alias) {
        return alias.includes(compactQuery);
      })
    ) {
      return 8;
    }
    return Number.POSITIVE_INFINITY;
  }

  function rankGlossaryItems(items, query) {
    return Array.from(items).sort(function (left, right) {
      const leftRank = glossaryMatchRank(left, query);
      const rightRank = glossaryMatchRank(right, query);
      if (leftRank !== rightRank) {
        return leftRank - rightRank;
      }
      return glossaryNames(left).canonical.localeCompare(
        glossaryNames(right).canonical
      );
    });
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

  function allGroupsCollapsed(groups) {
    return groups.length > 0 && groups.every(function (group) {
      return !group.open;
    });
  }

  function sectionControlState(groups) {
    return {
      collapseDisabled: allGroupsCollapsed(groups),
      expandDisabled: allGroupsExpanded(groups)
    };
  }

  function setAllGroupsExpanded(groups, expanded) {
    groups.forEach(function (group) {
      group.open = expanded;
    });
  }

  function itemMatchesGlossary(item, query, categories, tracks) {
    const searchMatch = Number.isFinite(glossaryMatchRank(item, query));
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

  function queryValueFromSearch(search) {
    return new URLSearchParams(String(search || "")).get("q") || "";
  }

  function glossaryStateFromSearch(search, capturedQuery) {
    const parameters = new URLSearchParams(String(search || ""));
    return {
      query: parameters.get("q") || String(capturedQuery || ""),
      categories: parameters.getAll("category"),
      tracks: parameters.getAll("track")
    };
  }

  function quartoCapturedQuery() {
    if (typeof kQuery !== "undefined" && kQuery) {
      return String(kQuery);
    }
    return "";
  }

  function samePageFragmentUrl(currentUrl, fragment) {
    const current = new URL(currentUrl);
    const target = new URL(fragment, current);
    if (
      target.origin !== current.origin ||
      target.pathname !== current.pathname ||
      !target.hash
    ) {
      return "";
    }
    current.hash = target.hash;
    return current.toString();
  }

  function urlWithoutGlossaryQuery(value) {
    const next = new URL(value);
    next.searchParams.delete("q");
    return next.toString();
  }

  function letterNavigationUrl(currentUrl, fragment) {
    return samePageFragmentUrl(
      urlWithoutGlossaryQuery(currentUrl),
      fragment
    );
  }

  function fragmentSlug(fragment) {
    return decodeURIComponent(
      String(fragment || "").replace(/^.*#/, "")
    ).trim();
  }

  function canonicalSlugForFragment(items, fragment) {
    const slug = fragmentSlug(fragment);
    const match = items.find(function (item) {
      return (
        item.slug === slug ||
        (Array.isArray(item.aliasSlugs) && item.aliasSlugs.includes(slug))
      );
    });
    return match ? match.slug : "";
  }

  function closeTermEntries(items) {
    items.forEach(function (item) {
      item.element.open = false;
    });
  }

  function itemMatchesLetter(item, letter) {
    return item.letter === letter;
  }

  function termDisclosureState(items) {
    return items.map(function (item) {
      return Boolean(item.element.open);
    });
  }

  function hasAtMostOneExpandedTerm(items) {
    return termDisclosureState(items).filter(Boolean).length <= 1;
  }

  function setExactlyOneExpandedTerm(items, selectedItem) {
    items.forEach(function (item) {
      item.element.open = item === selectedItem;
    });
  }

  function normalizedTermFragmentUrl(currentUrl, canonicalSlug) {
    const next = new URL(currentUrl);
    next.hash = canonicalSlug;
    return next.toString();
  }

  function groupForItem(item) {
    if (!item || !item.originalParent) {
      return null;
    }
    return item.originalParent.closest("[data-bms-letter-group]");
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
    ).map(function (element, originalIndex) {
      const searchValues = parseList(element.dataset.bmsSearch);
      return {
        element: element,
        slug: element.dataset.bmsSlug || "",
        aliasSlugs: parseList(element.dataset.bmsAliases),
        letter: element.dataset.bmsLetter || "",
        category: element.dataset.bmsCategory || "",
        tracks: parseList(element.dataset.bmsTracks),
        searchValues: searchValues,
        canonical: searchValues[0] || "",
        aliases: searchValues.slice(1),
        originalParent: element.parentElement,
        originalIndex: originalIndex
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
    const collapseControl = document.querySelector(
      "[data-bms-glossary-collapse-all]"
    );
    const expandControl = document.querySelector(
      "[data-bms-glossary-expand-all]"
    );
    const emptyState = document.querySelector("[data-bms-glossary-empty]");
    const selectedCategories = new Set();
    const selectedTracks = new Set();
    let activeLetterBrowse = "";
    const rankedResults = document.createElement("div");
    rankedResults.className = "bms-glossary-ranked-results";
    rankedResults.dataset.bmsGlossaryRankedResults = "";
    rankedResults.hidden = true;
    groupContainer.prepend(rankedResults);

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

    const initialState = glossaryStateFromSearch(
      window.location.search,
      quartoCapturedQuery()
    );
    if (searchInput) {
      searchInput.value = initialState.query;
    }
    initialState.categories.forEach(function (value) {
      if (categories.includes(value)) {
        selectedCategories.add(value);
      }
    });
    const trackButtons = Array.from(panel.querySelectorAll(TRACK_SELECTOR));
    initialState.tracks.forEach(function (value) {
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

    function updateSectionControls() {
      const state = sectionControlState(groups);
      if (collapseControl) {
        collapseControl.disabled = state.collapseDisabled;
      }
      if (expandControl) {
        expandControl.disabled = state.expandDisabled;
      }
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

    function restoreAlphabeticalOrder() {
      const parents = Array.from(
        new Set(items.map(function (item) {
          return item.originalParent;
        }))
      );
      parents.forEach(function (parent) {
        if (!parent) {
          return;
        }
        items
          .filter(function (item) {
            return item.originalParent === parent;
          })
          .sort(function (left, right) {
            return left.originalIndex - right.originalIndex;
          })
          .forEach(function (item) {
            parent.appendChild(item.element);
          });
      });
      rankedResults.replaceChildren();
      rankedResults.hidden = true;
    }

    function arrangeSearchResults(query) {
      restoreAlphabeticalOrder();
      if (!normalizeSearch(query)) {
        return false;
      }
      const visibleItems = items.filter(function (item) {
        return !item.element.hidden;
      });
      rankGlossaryItems(visibleItems, query).forEach(function (item) {
        rankedResults.appendChild(item.element);
      });
      rankedResults.hidden = visibleItems.length === 0;
      return true;
    }

    function applyFilters(options) {
      const shouldUpdateUrl = !options || options.updateUrl !== false;
      const categoriesToMatch = sortedValues(selectedCategories);
      const tracksToMatch = sortedValues(selectedTracks);
      const query = currentQuery();
      const active = hasActiveFilters();
      let visibleCount = 0;

      items.forEach(function (item) {
        const visible = activeLetterBrowse
          ? itemMatchesLetter(item, activeLetterBrowse)
          : itemMatchesGlossary(
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

      const queryActive =
        !activeLetterBrowse && arrangeSearchResults(query);
      if (activeLetterBrowse) {
        restoreAlphabeticalOrder();
      }
      groups.forEach(function (group) {
        if (queryActive) {
          group.hidden = true;
          return;
        }
        if (activeLetterBrowse) {
          const selected =
            group.dataset.bmsLetter === activeLetterBrowse;
          group.hidden = !selected;
          if (selected) {
            group.open = true;
          }
          return;
        }
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
      updateSectionControls();
    }

    function focusAndScroll(target) {
      window.requestAnimationFrame(function () {
        const reducedMotion = window.matchMedia(
          "(prefers-reduced-motion: reduce)"
        ).matches;
        target.scrollIntoView({
          behavior: reducedMotion ? "auto" : "smooth",
          block: "start"
        });
        const focusTarget =
          target.querySelector(":scope > summary") || target;
        focusTarget.focus({ preventScroll: true });
      });
    }

    function openCurrentHash(options) {
      const hash = fragmentSlug(window.location.hash);
      if (!hash) {
        return;
      }
      if (hash.startsWith("letter-")) {
        const letterGroup = document.getElementById(hash);
        if (letterGroup instanceof HTMLDetailsElement) {
          letterGroup.hidden = false;
          letterGroup.open = true;
          if (!options || options.focus !== false) {
            focusAndScroll(letterGroup);
          }
        }
        return;
      }

      const canonicalSlug = canonicalSlugForFragment(items, hash);
      if (!canonicalSlug) {
        return;
      }
      const selectedItem = items.find(function (item) {
        return item.slug === canonicalSlug;
      });
      if (!selectedItem) {
        return;
      }

      setExactlyOneExpandedTerm(items, selectedItem);
      selectedItem.element.hidden = false;
      const group = groupForItem(selectedItem);
      if (group instanceof HTMLDetailsElement) {
        group.hidden = false;
        group.open = true;
      }
      if (hash !== canonicalSlug) {
        window.history.replaceState(
          {},
          "",
          normalizedTermFragmentUrl(
            window.location.href,
            canonicalSlug
          )
        );
      }
      if (!options || options.focus !== false) {
        focusAndScroll(selectedItem.element);
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
      const categoryButton = event.target.closest(CATEGORY_SELECTOR);
      const trackButton = event.target.closest(TRACK_SELECTOR);
      const clear = event.target.closest("[data-bms-glossary-clear]");

      if (categoryButton) {
        activeLetterBrowse = "";
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
        activeLetterBrowse = "";
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
        activeLetterBrowse = "";
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

    function applySectionAction(expanded) {
      activeLetterBrowse = "";
      if (searchInput) {
        searchInput.value = "";
      }
      applyFilters({ updateUrl: false });
      window.history.replaceState(
        {},
        "",
        urlWithoutGlossaryQuery(window.location.href)
      );
      setAllGroupsExpanded(groups, expanded);
      updateSectionControls();
    }

    if (collapseControl) {
      collapseControl.addEventListener("click", function () {
        applySectionAction(false);
      });
    }
    if (expandControl) {
      expandControl.addEventListener("click", function () {
        applySectionAction(true);
      });
    }

    groups.forEach(function (group) {
      group.addEventListener("toggle", updateSectionControls);
    });

    groupContainer.addEventListener("click", function (event) {
      const categoryButton = event.target.closest("[data-bms-card-category]");
      if (!categoryButton) {
        return;
      }
      selectedCategories.clear();
      selectedCategories.add(categoryButton.dataset.bmsCardCategory || "");
      activeLetterBrowse = "";
      if (categoryDisclosure instanceof HTMLDetailsElement) {
        categoryDisclosure.open = true;
      }
      applyFilters();
      panel.scrollIntoView({ behavior: "smooth", block: "start" });
    });

    if (searchInput) {
      searchInput.addEventListener("input", function () {
        activeLetterBrowse = "";
        applyFilters();
      });
    }
    document
      .querySelectorAll("[data-bms-letter-link]")
      .forEach(function (link) {
        link.removeAttribute("target");
        link.removeAttribute("rel");
        link.addEventListener("click", function (event) {
          const destination = letterNavigationUrl(
            window.location.href,
            link.getAttribute("href") || ""
          );
          if (!destination) {
            return;
          }
          event.preventDefault();
          if (searchInput) {
            searchInput.value = "";
          }
          activeLetterBrowse =
            link.dataset.bmsLetterLink || "";
          closeTermEntries(items);
          applyFilters({ updateUrl: false });
          const target = document.getElementById(
            decodeURIComponent(new URL(destination).hash.slice(1))
          );
          if (!target) {
            return;
          }
          if (target instanceof HTMLDetailsElement) {
            target.open = true;
          }
          window.history.pushState({}, "", destination);
          focusAndScroll(target);
        });
      });
    window.addEventListener("hashchange", function () {
      openCurrentHash();
    });

    closeTermEntries(items);
    applyFilters({ updateUrl: false });
    openCurrentHash();
    updateSectionControls();
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
    allGroupsCollapsed: allGroupsCollapsed,
    allGroupsExpanded: allGroupsExpanded,
    canonicalSlugForFragment: canonicalSlugForFragment,
    closeTermEntries: closeTermEntries,
    fragmentSlug: fragmentSlug,
    glossaryMatchRank: glossaryMatchRank,
    glossaryStateFromSearch: glossaryStateFromSearch,
    itemMatchesGlossary: itemMatchesGlossary,
    itemMatchesLetter: itemMatchesLetter,
    letterNavigationUrl: letterNavigationUrl,
    matchesAny: matchesAny,
    normalizeCompact: normalizeCompact,
    normalizeSearch: normalizeSearch,
    normalizedTermFragmentUrl: normalizedTermFragmentUrl,
    parseList: parseList,
    quartoCapturedQuery: quartoCapturedQuery,
    queryValueFromSearch: queryValueFromSearch,
    rankGlossaryItems: rankGlossaryItems,
    samePageFragmentUrl: samePageFragmentUrl,
    sectionControlState: sectionControlState,
    setAllGroupsExpanded: setAllGroupsExpanded,
    setExactlyOneExpandedTerm: setExactlyOneExpandedTerm,
    termDisclosureState: termDisclosureState,
    hasAtMostOneExpandedTerm: hasAtMostOneExpandedTerm,
    urlWithoutGlossaryQuery: urlWithoutGlossaryQuery
  };

  if (typeof module !== "undefined" && module.exports) {
    module.exports = publicApi;
  }

  if (typeof document !== "undefined") {
    const initialize = function () {
      initializeGlossary();
      initializeBackToTop();
    };
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", initialize);
    } else {
      initialize();
    }
  }
})();
