local function remove_new_window_rel(link)
  local values = {}
  for value in (link.attributes.rel or ""):gmatch("%S+") do
    if value ~= "noopener" and value ~= "noreferrer" then
      table.insert(values, value)
    end
  end
  if #values == 0 then
    link.attributes.rel = nil
  else
    link.attributes.rel = table.concat(values, " ")
  end
end

function Link(link)
  link.attributes.target = nil
  remove_new_window_rel(link)
  return link
end
