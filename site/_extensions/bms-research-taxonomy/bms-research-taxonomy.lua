local function metadata_values(value)
  local values = {}

  if value == nil then
    return values
  end

  if pandoc.utils.type(value) == "List" then
    for _, item in ipairs(value) do
      local text = pandoc.utils.stringify(item)
      if text ~= "" then
        table.insert(values, text)
      end
    end
  else
    local text = pandoc.utils.stringify(value)
    if text ~= "" then
      table.insert(values, text)
    end
  end

  return values
end

local function escape_html(value)
  return value
    :gsub("&", "&amp;")
    :gsub("<", "&lt;")
    :gsub(">", "&gt;")
    :gsub('"', "&quot;")
    :gsub("'", "&#39;")
end

local function url_encode(value)
  return (value:gsub("([^%w%-%.%_%~])", function(character)
    return string.format("%%%02X", string.byte(character))
  end))
end

local function taxonomy_group(label, values, query_name, css_class)
  if #values == 0 then
    return ""
  end

  local lines = {
    '  <div class="bms-post-taxonomy-group">',
    '    <p class="bms-post-taxonomy-label">' .. escape_html(label) .. '</p>',
    '    <div class="bms-post-taxonomy-links">'
  }

  for _, value in ipairs(values) do
    local href = "index.html?" .. query_name .. "=" .. url_encode(value)

    table.insert(
      lines,
      '      <a class="bms-post-taxonomy-link '
        .. css_class
        .. '" href="'
        .. escape_html(href)
        .. '">'
        .. escape_html(value)
        .. '</a>'
    )
  end

  table.insert(lines, "    </div>")
  table.insert(lines, "  </div>")

  return table.concat(lines, "\n")
end

local css = [==[
<style id="bms-research-taxonomy-styles">
#title-block-header .quarto-categories {
  display: none;
}

.bms-post-taxonomy {
  position: relative;
  margin: 0 0 1.2rem;
  padding: 0 1.8rem 1.1rem 0;
  border-bottom: 1px solid var(--bms-border, #d9d3c7);
}

.bms-post-taxonomy-toggle {
  position: absolute;
  top: 0;
  right: 0;
  display: inline-flex;
  width: 1.45rem;
  min-height: 1.45rem;
  align-items: center;
  justify-content: center;
  padding: 0;
  border: 1px solid var(--bms-border, #d9d3c7);
  border-radius: 5px;
  background: var(--bms-page-background, #faf7f2);
  color: var(--bms-text-muted, #68625a);
  cursor: pointer;
  font-size: 1rem;
  line-height: 1;
}

.bms-post-taxonomy-toggle:focus-visible {
  outline: 2px solid var(--bms-link-hover, #6d3f27);
  outline-offset: 2px;
}

.bms-post-taxonomy--collapsed {
  min-height: 1.55rem;
  margin-bottom: 0.4rem;
  padding-bottom: 0.2rem;
}

.bms-post-taxonomy--collapsed .bms-post-taxonomy-content {
  display: none;
}

.bms-post-taxonomy-group + .bms-post-taxonomy-group {
  margin-top: 0.9rem;
}

.bms-post-taxonomy-label {
  margin: 0 0 0.45rem;
  color: var(--bms-text-muted, #68625a);
  font-family:
    "Source Code Pro",
    ui-monospace,
    SFMono-Regular,
    Menlo,
    Monaco,
    Consolas,
    monospace;
  font-size: 0.68rem;
  font-weight: 680;
  letter-spacing: 0.065em;
  line-height: 1.35;
  text-transform: uppercase;
}

.bms-post-taxonomy-links {
  display: flex;
  flex-wrap: wrap;
  gap: 0.38rem;
}

.bms-post-taxonomy-link {
  display: inline-flex;
  align-items: center;
  min-height: 1.9rem;
  padding: 0.3rem 0.52rem;
  border: 1px solid var(--bms-border-strong, #bcb4a7);
  background: var(--bms-surface, #fff);
  color: var(--bms-text-secondary, #4c4841);
  font-size: 0.72rem;
  font-weight: 680;
  line-height: 1.15;
  text-decoration: none;
}

.bms-post-taxonomy-link--category {
  border-radius: 4px;
}

.bms-post-taxonomy-link--tag {
  border-color: var(--bms-border, #d9d3c7);
  border-radius: 999px;
  background: var(--bms-ivory, #f7f3ea);
  color: var(--bms-copper-dark, #7a482d);
}

.bms-post-taxonomy-link:hover,
.bms-post-taxonomy-link:focus-visible {
  border-color: var(--bms-link-hover, #6d3f27);
  color: var(--bms-link-hover, #6d3f27);
  text-decoration: underline;
  text-underline-offset: 0.14em;
}

@media (max-width: 991.98px) {
  .bms-post-taxonomy {
    display: none;
  }
}
</style>
]==]

local javascript = [==[
<script id="bms-research-taxonomy-script">
(function () {
  "use strict";

  function moveResearchTaxonomy() {
    var source = document.getElementById("bms-research-taxonomy-source");

    if (!source) {
      return;
    }

    var taxonomy = source.querySelector(".bms-post-taxonomy");

    if (!taxonomy) {
      source.remove();
      return;
    }

    var sidebar = document.getElementById("quarto-margin-sidebar");
    var toc = sidebar ? sidebar.querySelector("#TOC") : null;

    if (sidebar && toc) {
      var anchor = toc;

      while (anchor.parentElement && anchor.parentElement !== sidebar) {
        anchor = anchor.parentElement;
      }

      sidebar.insertBefore(taxonomy, anchor);
    } else if (sidebar) {
      sidebar.prepend(taxonomy);
    } else {
      var titleBlock = document.getElementById("title-block-header");

      if (titleBlock) {
        titleBlock.insertAdjacentElement("afterend", taxonomy);
      }
    }

    initializeResearchTaxonomyToggle(taxonomy);
    source.remove();
  }

  function initializeResearchTaxonomyToggle(taxonomy) {
    if (!taxonomy || taxonomy.querySelector("[data-bms-research-taxonomy-toggle]")) {
      return;
    }

    var collapsed = false;
    var toggle = document.createElement("button");
    var contentId = "bms-research-taxonomy-content";
    var groups = Array.from(
      taxonomy.querySelectorAll(".bms-post-taxonomy-group")
    );
    var content = document.createElement("div");

    content.id = contentId;
    content.className = "bms-post-taxonomy-content";
    groups.forEach(function (group) {
      content.appendChild(group);
    });
    taxonomy.appendChild(content);
    toggle.type = "button";
    toggle.className = "bms-post-taxonomy-toggle";
    toggle.dataset.bmsResearchTaxonomyToggle = "";
    toggle.setAttribute("aria-controls", contentId);

    function update() {
      taxonomy.classList.toggle("bms-post-taxonomy--collapsed", collapsed);
      toggle.setAttribute("aria-expanded", collapsed ? "false" : "true");
      toggle.setAttribute(
        "aria-label",
        collapsed
          ? "Show article categories and tags"
          : "Hide article categories and tags"
      );
      toggle.textContent = collapsed ? "\u25be" : "\u25b4";
    }

    toggle.addEventListener("click", function () {
      collapsed = !collapsed;
      update();
    });
    window.addEventListener(
      "scroll",
      function () {
        if (!collapsed && window.scrollY > 32) {
          collapsed = true;
          update();
        }
      },
      { passive: true }
    );
    taxonomy.prepend(toggle);
    update();
  }

  function matchingButton(selector, datasetKey, value) {
    return Array.from(document.querySelectorAll(selector)).find(
      function (button) {
        return button.dataset[datasetKey] === value;
      }
    );
  }

  function applyRequestedResearchFilters() {
    var parameters = new URLSearchParams(window.location.search);
    var category = parameters.get("category") || "";
    var tag = parameters.get("tag") || "";

    if (!category && !tag) {
      return;
    }

    window.setTimeout(function () {
      if (category) {
        var categoryButton = matchingButton(
          "[data-bms-filter-category]",
          "bmsFilterCategory",
          category
        );

        if (
          categoryButton &&
          categoryButton.getAttribute("aria-pressed") !== "true"
        ) {
          categoryButton.click();
        }
      }

      if (tag) {
        var tagButton = matchingButton(
          "[data-bms-filter-tag]",
          "bmsFilterTag",
          tag
        );

        if (
          tagButton &&
          tagButton.getAttribute("aria-pressed") !== "true"
        ) {
          tagButton.click();
        }
      }
    }, 0);
  }

  function initialize() {
    moveResearchTaxonomy();
    applyRequestedResearchFilters();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initialize);
  } else {
    initialize();
  }
})();
</script>
]==]

function Pandoc(doc)
  if not tostring(FORMAT):match("html") then
    return doc
  end

  if quarto ~= nil and quarto.doc ~= nil then
    quarto.doc.include_text("in-header", css)
    quarto.doc.include_text("after-body", javascript)
  end

  local categories = metadata_values(doc.meta.categories)
  local tags = metadata_values(doc.meta.tags)

  if #categories == 0 and #tags == 0 then
    return doc
  end

  local groups = {}

  local categories_html = taxonomy_group(
    "Categories",
    categories,
    "category",
    "bms-post-taxonomy-link--category"
  )

  local tags_html = taxonomy_group(
    "Tags",
    tags,
    "tag",
    "bms-post-taxonomy-link--tag"
  )

  if categories_html ~= "" then
    table.insert(groups, categories_html)
  end

  if tags_html ~= "" then
    table.insert(groups, tags_html)
  end

  local html = table.concat({
    '<div id="bms-research-taxonomy-source" hidden>',
    '<nav class="bms-post-taxonomy" aria-label="Article categories and tags">',
    table.concat(groups, "\n"),
    '</nav>',
    '</div>'
  }, "\n")

  table.insert(doc.blocks, 1, pandoc.RawBlock("html", html))

  return doc
end
