local SLUG_PATTERN = "^[a-z0-9]+%-?[a-z0-9%-]*$"

local function fail(message)
  error("bms-inline-glossary: " .. message)
end

local function meta_list(value, label)
  if value == nil then
    return nil
  end
  if pandoc.utils.type(value) ~= "List" then
    fail(label .. " must be a YAML list")
  end
  local values = {}
  for _, item in ipairs(value) do
    table.insert(values, pandoc.utils.stringify(item):match("^%s*(.-)%s*$"))
  end
  return values
end

local function normalized_slug(value)
  local normalized = value:lower():gsub("[^a-z0-9]+", "-")
  return normalized:gsub("^%-+", ""):gsub("%-+$", "")
end

local function normalized_phrase(value)
  local words = {}
  for word in value:lower():gmatch("[a-z0-9]+") do
    table.insert(words, word)
  end
  return table.concat(words, " ")
end

local function lookup_paths()
  local paths = {}
  local configured = os.getenv("BMS_GLOSSARY_LOOKUP")
  if configured and configured ~= "" then
    table.insert(paths, configured)
  end
  if quarto and quarto.project and quarto.project.directory then
    table.insert(
      paths,
      quarto.project.directory .. "/assets/bms-glossary-lookup.json"
    )
  end
  table.insert(paths, "assets/bms-glossary-lookup.json")
  table.insert(paths, "site/assets/bms-glossary-lookup.json")
  table.insert(paths, "../site/assets/bms-glossary-lookup.json")
  return paths
end

local function decode_json(text)
  if quarto and quarto.json and quarto.json.decode then
    return quarto.json.decode(text)
  end
  if pandoc.json and pandoc.json.decode then
    return pandoc.json.decode(text)
  end
  fail("this Quarto/Pandoc runtime has no JSON decoder")
end

local function load_lookup()
  local attempted = {}
  for _, path in ipairs(lookup_paths()) do
    table.insert(attempted, path)
    local handle = io.open(path, "r")
    if handle then
      local text = handle:read("*a")
      handle:close()
      local ok, data = pcall(decode_json, text)
      if not ok or type(data) ~= "table" or type(data.entries) ~= "table" then
        fail("generated lookup is malformed: " .. path)
      end
      return data.entries
    end
  end
  fail("generated lookup was not found; tried " .. table.concat(attempted, ", "))
end

local function validate_metadata(doc, entries)
  local highlighted = meta_list(doc.meta["highlighted-terms"], "highlighted-terms")
  if highlighted == nil or #highlighted == 0 then
    return {}
  end
  local terms = meta_list(doc.meta.terms, "terms")
  if terms == nil then
    fail("highlighted-terms requires a terms list")
  end

  local canonical = {}
  local alias_slugs = {}
  for _, entry in ipairs(entries) do
    canonical[tostring(entry.slug)] = entry
    for _, alias_slug in ipairs(entry.alias_slugs or {}) do
      alias_slugs[tostring(alias_slug)] = tostring(entry.slug)
    end
  end
  local term_set = {}
  for _, slug in ipairs(terms) do
    term_set[slug] = true
  end
  local normalized_seen = {}
  for _, slug in ipairs(highlighted) do
    local normalized = normalized_slug(slug)
    if normalized_seen[normalized] then
      fail("duplicate normalized highlighted-terms value " .. slug)
    end
    normalized_seen[normalized] = true
    if not slug:match(SLUG_PATTERN) or normalized ~= slug then
      fail("malformed highlighted-terms slug " .. slug)
    end
    if alias_slugs[slug] then
      fail(
        "highlighted-terms uses alias slug "
          .. slug
          .. "; use canonical slug "
          .. alias_slugs[slug]
      )
    end
    if not canonical[slug] then
      fail("highlighted-terms uses unknown canonical slug " .. slug)
    end
    if not term_set[slug] then
      fail("highlighted term " .. slug .. " is missing from terms")
    end
  end
  table.sort(highlighted)

  local phrases = {}
  local phrase_owners = {}
  for _, slug in ipairs(highlighted) do
    local entry = canonical[slug]
    local values = { tostring(entry.term) }
    for _, alias in ipairs(entry.aliases or {}) do
      table.insert(values, tostring(alias))
    end
    for _, phrase in ipairs(values) do
      local normalized = normalized_phrase(phrase)
      local owner = phrase_owners[normalized]
      if owner and owner ~= slug then
        fail(
          "ambiguous canonical or alias phrase "
            .. phrase
            .. " resolves to both "
            .. owner
            .. " and "
            .. slug
        )
      end
      phrase_owners[normalized] = slug
      local pattern_words = {}
      for word in normalized:gmatch("[a-z0-9]+") do
        table.insert(pattern_words, word)
      end
      table.insert(phrases, {
        slug = slug,
        phrase = phrase,
        normalized = normalized,
        pattern = table.concat(pattern_words, "%W+"),
        length = #normalized,
      })
    end
  end
  table.sort(phrases, function(left, right)
    if left.length ~= right.length then
      return left.length > right.length
    end
    if left.normalized ~= right.normalized then
      return left.normalized < right.normalized
    end
    return left.slug < right.slug
  end)
  return phrases, highlighted
end

local function is_word_character(character)
  return character ~= nil and character:match("[A-Za-z0-9]") ~= nil
end

local function next_match(text, start_at, phrases, found)
  local lowered = text:lower()
  local best = nil
  for _, candidate in ipairs(phrases) do
    if not found[candidate.slug] then
      local search_at = start_at
      while search_at <= #text do
        local first, last = lowered:find(candidate.pattern, search_at)
        if not first then
          break
        end
        local before = first > 1 and text:sub(first - 1, first - 1) or nil
        local after = last < #text and text:sub(last + 1, last + 1) or nil
        if not is_word_character(before) and not is_word_character(after) then
          if
            best == nil
            or first < best.first
            or (
              first == best.first
              and candidate.length > best.candidate.length
            )
          then
            best = {
              first = first,
              last = last,
              candidate = candidate,
            }
          end
          break
        end
        search_at = first + 1
      end
    end
  end
  return best
end

local function text_inlines(text)
  local inlines = pandoc.List()
  local position = 1
  while position <= #text do
    local first, last = text:find("%s+", position)
    if not first then
      if position <= #text then
        inlines:insert(pandoc.Str(text:sub(position)))
      end
      break
    end
    if first > position then
      inlines:insert(pandoc.Str(text:sub(position, first - 1)))
    end
    inlines:insert(pandoc.Space())
    position = last + 1
  end
  return inlines
end

local function transformed_run(text, phrases, found)
  local output = pandoc.List()
  local position = 1
  while position <= #text do
    local match = next_match(text, position, phrases, found)
    if not match then
      output:extend(text_inlines(text:sub(position)))
      break
    end
    if match.first > position then
      output:extend(text_inlines(text:sub(position, match.first - 1)))
    end
    local visible = text:sub(match.first, match.last)
    output:insert(
      pandoc.Link(
        text_inlines(visible),
        "/learn/glossary/#" .. match.candidate.slug,
        "",
        pandoc.Attr(
          "",
          { "bms-inline-glossary" },
          { { "data-bms-glossary-slug", match.candidate.slug } }
        )
      )
    )
    found[match.candidate.slug] = true
    position = match.last + 1
  end
  return output
end

local function transform_paragraph(block, phrases, found)
  local output = pandoc.List()
  local run = {}
  local function flush()
    if #run > 0 then
      output:extend(transformed_run(table.concat(run), phrases, found))
      run = {}
    end
  end

  for _, inline in ipairs(block.content) do
    if inline.t == "Str" then
      table.insert(run, inline.text)
    elseif inline.t == "Space" then
      table.insert(run, " ")
    elseif inline.t == "SoftBreak" or inline.t == "LineBreak" then
      table.insert(run, "\n")
    else
      flush()
      output:insert(inline)
    end
  end
  flush()
  block.content = output
  return block
end

function Pandoc(doc)
  local is_html = FORMAT and FORMAT:match("html") ~= nil
  if quarto and quarto.doc and quarto.doc.is_format then
    is_html = quarto.doc.is_format("html")
  end
  if not is_html then
    return doc
  end
  if doc.meta["highlighted-terms"] == nil then
    return doc
  end

  local entries = load_lookup()
  local phrases, highlighted = validate_metadata(doc, entries)
  if #phrases == 0 then
    return doc
  end
  local found = {}

  -- Only top-level prose paragraphs are transformed. This deliberate safety
  -- boundary excludes headings, links, code, math, raw HTML, captions,
  -- navigation, metadata, and generated UI structurally.
  for index, block in ipairs(doc.blocks) do
    if block.t == "Para" or block.t == "Plain" then
      doc.blocks[index] = transform_paragraph(block, phrases, found)
    end
  end

  for _, slug in ipairs(highlighted) do
    if not found[slug] then
      io.stderr:write(
        "bms-inline-glossary warning: no safe prose occurrence for "
          .. slug
          .. "\n"
      )
    end
  end
  return doc
end
