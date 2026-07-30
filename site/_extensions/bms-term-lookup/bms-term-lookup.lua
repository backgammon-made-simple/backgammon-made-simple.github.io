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
    '<aside id="bms-term-lookup-panel" class="bms-term-lookup" data-bms-term-lookup hidden>',
    '  <div class="bms-term-lookup-heading">',
    '    <strong>Look Up a Term</strong>',
    '    <button type="button" class="bms-term-lookup-close" data-bms-term-lookup-close aria-controls="bms-term-lookup-panel" aria-expanded="true" aria-label="Collapse term lookup to the right"><span aria-hidden="true">&rarr;</span></button>',
    '  </div>',
    '  <form action="/learn/glossary/" method="get" data-bms-term-lookup-form>',
    '    <label class="visually-hidden" for="bms-term-lookup-input">Term or alias</label>',
    '    <div class="bms-term-lookup-controls">',
    '      <input id="bms-term-lookup-input" name="q" type="search" required autocomplete="off" spellcheck="false" placeholder="Enter Term">',
    '      <button type="submit">Search</button>',
    '    </div>',
    '  </form>',
    '  <div class="bms-term-lookup-result" data-bms-term-lookup-result aria-live="polite" hidden></div>',
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
