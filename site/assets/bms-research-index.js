(function () {
  "use strict";

  const CATEGORY_SELECTOR = "[data-bms-filter-category]";
  const TAG_SELECTOR = "[data-bms-filter-tag]";
  const ITEM_SELECTOR = "[data-bms-research-item]";

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

  function createTagButton(tag) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "bms-research-filter bms-research-filter--tag";
    button.dataset.bmsFilterTag = tag;
    button.setAttribute("aria-pressed", "false");

    const label = document.createElement("span");
    label.textContent = tag;

    const count = document.createElement("span");
    count.className = "bms-research-filter-count";
    count.setAttribute("aria-hidden", "true");
    count.textContent = "×0";

    button.append(label, count);
    return button;
  }

  function initializeResearchFilters() {
    const panel = document.querySelector("[data-bms-research-filters]");
    const list = document.querySelector("[data-bms-research-list]");

    if (!panel || !list) {
      return;
    }

    const items = Array.from(list.querySelectorAll(ITEM_SELECTOR)).map(function (element) {
      return {
        element: element,
        categories: parseList(element.dataset.bmsCategories),
        tags: parseList(element.dataset.bmsTags)
      };
    });

    const tagContainer = panel.querySelector("[data-bms-tag-filters]");
    const tagGroup = panel.querySelector("[data-bms-tag-group]");
    const resultCount = panel.querySelector("[data-bms-result-count]");
    const clearButton = panel.querySelector("[data-bms-clear-filters]");
    const emptyState = document.querySelector("[data-bms-empty-state]");

    const allTags = Array.from(
      new Set(items.flatMap(function (item) {
        return item.tags;
      }))
    ).sort(function (left, right) {
      return left.localeCompare(right);
    });

    if (tagContainer) {
      allTags.forEach(function (tag) {
        tagContainer.appendChild(createTagButton(tag));
      });
    }

    if (tagGroup && allTags.length === 0) {
      tagGroup.hidden = true;
    }

    let activeCategory = "";
    let activeTag = "";

    function itemMatches(item, category, tag) {
      const categoryMatch = !category || item.categories.includes(category);
      const tagMatch = !tag || item.tags.includes(tag);
      return categoryMatch && tagMatch;
    }

    function setPressed(buttons, activeValue, datasetKey) {
      buttons.forEach(function (button) {
        const isActive = button.dataset[datasetKey] === activeValue;
        button.setAttribute("aria-pressed", isActive ? "true" : "false");
        button.classList.toggle("is-active", isActive);
      });
    }

    function updateCounts() {
      const categoryButtons = Array.from(panel.querySelectorAll(CATEGORY_SELECTOR));
      const tagButtons = Array.from(panel.querySelectorAll(TAG_SELECTOR));

      categoryButtons.forEach(function (button) {
        const category = button.dataset.bmsFilterCategory || "";
        const count = items.filter(function (item) {
          return itemMatches(item, category, activeTag);
        }).length;
        const countElement = button.querySelector(".bms-research-filter-count");

        if (countElement) {
          countElement.textContent = "×" + count;
        }

        button.disabled = count === 0 && category !== activeCategory;
      });

      tagButtons.forEach(function (button) {
        const tag = button.dataset.bmsFilterTag || "";
        const count = items.filter(function (item) {
          return itemMatches(item, activeCategory, tag);
        }).length;
        const countElement = button.querySelector(".bms-research-filter-count");

        if (countElement) {
          countElement.textContent = "×" + count;
        }

        button.disabled = count === 0 && tag !== activeTag;
      });
    }

    function applyFilters() {
      let visibleCount = 0;

      items.forEach(function (item) {
        const visible = itemMatches(item, activeCategory, activeTag);
        item.element.hidden = !visible;
        if (visible) {
          visibleCount += 1;
        }
      });

      const categoryButtons = Array.from(panel.querySelectorAll(CATEGORY_SELECTOR));
      const tagButtons = Array.from(panel.querySelectorAll(TAG_SELECTOR));

      setPressed(categoryButtons, activeCategory, "bmsFilterCategory");
      setPressed(tagButtons, activeTag, "bmsFilterTag");
      updateCounts();

      if (resultCount) {
        resultCount.textContent =
          "Showing " +
          visibleCount +
          (visibleCount === 1 ? " article." : " articles.");
      }

      if (emptyState) {
        emptyState.hidden = visibleCount !== 0;
      }

      if (clearButton) {
        clearButton.hidden = !activeCategory && !activeTag;
      }
    }

    panel.addEventListener("click", function (event) {
      const categoryButton = event.target.closest(CATEGORY_SELECTOR);
      const tagButton = event.target.closest(TAG_SELECTOR);
      const clear = event.target.closest("[data-bms-clear-filters]");

      if (categoryButton) {
        const category = categoryButton.dataset.bmsFilterCategory || "";
        activeCategory = activeCategory === category ? "" : category;
        applyFilters();
        return;
      }

      if (tagButton) {
        const tag = tagButton.dataset.bmsFilterTag || "";
        activeTag = activeTag === tag ? "" : tag;
        applyFilters();
        return;
      }

      if (clear) {
        activeCategory = "";
        activeTag = "";
        applyFilters();
      }
    });

    list.addEventListener("click", function (event) {
      const categoryButton = event.target.closest("[data-bms-card-category]");
      const tagButton = event.target.closest("[data-bms-card-tag]");

      if (categoryButton) {
        activeCategory = categoryButton.dataset.bmsCardCategory || "";
        applyFilters();
        panel.scrollIntoView({ behavior: "smooth", block: "start" });
        return;
      }

      if (tagButton) {
        activeTag = tagButton.dataset.bmsCardTag || "";
        applyFilters();
        panel.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    });

    applyFilters();
  }

  document.addEventListener("DOMContentLoaded", initializeResearchFilters);
})();