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

local function has_terms(value)
  if value == nil then
    return false
  end
  if pandoc.utils.type(value) == "List" then
    return #value > 0
  end
  return pandoc.utils.stringify(value) ~= ""
end

local function lookup_html()
  return table.concat({
    '<aside class="bms-term-lookup" data-bms-term-lookup>',
    '  <form action="/learn/glossary/" method="get" target="_blank" rel="noopener" data-bms-term-lookup-form>',
    '    <label for="bms-term-lookup-input">Look Up a Term</label>',
    '    <div class="bms-term-lookup-controls">',
    '      <input id="bms-term-lookup-input" name="q" type="search" required autocomplete="off" spellcheck="false" placeholder="e.g. take point" aria-describedby="bms-term-lookup-new-tab">',
    '      <button type="submit">Look Up</button>',
    '    </div>',
    '    <span id="bms-term-lookup-new-tab" class="visually-hidden">Search results open in a new tab.</span>',
    '  </form>',
    '</aside>'
  }, "\n")
end

function Pandoc(doc)
  local enabled = metadata_boolean(doc.meta["term-lookup"])
  if enabled == nil then
    enabled = has_terms(doc.meta.terms)
  end

  if not enabled then
    return doc
  end

  table.insert(doc.blocks, 1, pandoc.RawBlock("html", lookup_html()))
  return doc
end
