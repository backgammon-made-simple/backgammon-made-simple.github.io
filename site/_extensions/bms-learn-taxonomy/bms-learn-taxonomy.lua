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

local function metadata_boolean(value)
  if value == nil then
    return nil
  end

  if pandoc.utils.type(value) == "MetaBool" then
    return value
  end

  local text = pandoc.utils.stringify(value):lower()
  if text == "true" then
    return true
  end
  if text == "false" then
    return false
  end
  return nil
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

local function difficulty_badges(values)
  if #values == 0 then
    return ""
  end

  local lines = {
    '<div class="bms-lesson-difficulties" role="list" aria-label="Lesson difficulty">'
  }

  for _, value in ipairs(values) do
    table.insert(
      lines,
      '  <span class="bms-lesson-difficulty" role="listitem">'
        .. escape_html(value)
        .. '</span>'
    )
  end

  table.insert(lines, "</div>")
  return table.concat(lines, "\n")
end

local function track_links(values)
  if #values == 0 then
    return ""
  end

  local lines = {
    '<nav class="bms-lesson-track-nav" data-bms-lesson-track-nav aria-label="Learning tracks">',
    '  <p class="bms-lesson-track-label">Learning tracks</p>',
    '  <div class="bms-lesson-track-links">'
  }

  for _, value in ipairs(values) do
    table.insert(
      lines,
      '    <a href="/learn/lesson-finder/?track='
        .. url_encode(value)
        .. '">'
        .. escape_html(value)
        .. '</a>'
    )
  end

  table.insert(lines, "  </div>")
  table.insert(lines, "</nav>")
  return table.concat(lines, "\n")
end

function Pandoc(doc)
  if not tostring(FORMAT):match("html") then
    return doc
  end

  if metadata_boolean(doc.meta["lesson-taxonomy"]) == false then
    return doc
  end

  local difficulties = metadata_values(doc.meta.categories)
  local tracks = metadata_values(doc.meta.tags)

  if #difficulties == 0 and #tracks == 0 then
    return doc
  end

  local html = table.concat({
    '<div class="bms-lesson-taxonomy" data-bms-lesson-taxonomy>',
    difficulty_badges(difficulties),
    track_links(tracks),
    '</div>'
  }, "\n")

  table.insert(doc.blocks, 1, pandoc.RawBlock("html", html))
  return doc
end
