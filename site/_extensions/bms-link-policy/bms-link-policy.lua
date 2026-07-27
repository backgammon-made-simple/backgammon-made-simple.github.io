local function metadata_boolean(value)
  if value == nil then
    return false
  end
  if pandoc.utils.type(value) == "MetaBool" then
    return value
  end
  return pandoc.utils.stringify(value):lower() == "true"
end

local function has_download(link)
  return link.attributes.download ~= nil
end

local function is_external(target)
  return target:match("^https?://") ~= nil
end

local function is_glossary_target(target)
  local path = target:match("^[^?#]*") or ""
  return path:match("^/learn/glossary/?") ~= nil
    or path:match("^%.?%.?/learn/glossary/?") ~= nil
    or path:match("^glossary/?") ~= nil
end

local function contains_indicator(link)
  return pandoc.utils.stringify(link.content):lower():find(
    "opens in a new tab",
    1,
    true
  ) ~= nil
end

local function add_noopener(link)
  local values = {}
  local seen = {}
  for value in (link.attributes.rel or ""):gmatch("%S+") do
    if not seen[value] then
      table.insert(values, value)
      seen[value] = true
    end
  end
  if not seen.noopener then
    table.insert(values, "noopener")
  end
  link.attributes.rel = table.concat(values, " ")
end

function Pandoc(doc)
  local glossary_links_new_tab = metadata_boolean(
    doc.meta["glossary-links-new-tab"]
  )
  local body_classes = pandoc.utils.stringify(doc.meta["body-classes"] or "")
  local is_glossary_page = body_classes:find("bms%-glossary%-") ~= nil

  doc.blocks = pandoc.walk_block(
    pandoc.Div(doc.blocks),
    {
      Link = function(link)
        local target = link.target or ""
        if has_download(link) then
          return link
        end

        local new_tab = is_external(target)
          or (
            glossary_links_new_tab
            and not is_glossary_page
            and is_glossary_target(target)
          )
        if not new_tab then
          return link
        end

        link.attributes.target = "_blank"
        add_noopener(link)
        if not contains_indicator(link) then
          table.insert(
            link.content,
            pandoc.Span(
              { pandoc.Str(" (opens in a new tab)") },
              pandoc.Attr("", { "visually-hidden" })
            )
          )
        end
        return link
      end
    }
  ).content

  return doc
end
