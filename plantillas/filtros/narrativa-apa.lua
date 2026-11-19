-- editorial-academica: citas narrativas APA (AuthorInText) con "and"/"y" en vez de "&" (APA 8.17).
-- citeproc de pandoc no implementa <intext> (CSL 1.1): reutiliza los nombres de la cita parentética.
-- Se aplica después de --citeproc y solo a la parte previa al primer "(" (los autores).
local conj = "and"

function Meta(m)
  local l = m.lang and pandoc.utils.stringify(m.lang) or "en"
  if l:sub(1, 2) == "es" then conj = "y" end
end

function Cite(c)
  if c.citations[1].mode ~= "AuthorInText" then return nil end
  local antes = true
  c.content = c.content:walk({
    Str = function(s)
      if not antes then return nil end
      if s.text:find("%(") then antes = false end
      if s.text == "&" then return pandoc.Str(conj) end
    end
  })
  return c
end

return {{Meta = Meta}, {Cite = Cite}}
