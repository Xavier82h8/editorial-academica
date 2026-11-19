-- Filtro para salidas LaTeX/PDF (plantillas/latex/*.latex). Requiere -M perfil-base=apa7|ieee.
--  * define etiquetas segun idioma (kwlabel) y la linea de autores APA (authorsline: "A, B y C")
--  * apa7: lista de referencias (encabezado nivel 1 "Referencias"/"References") en pagina nueva
--  * ieee: ese encabezado sin numerar (IEEEtran lo compone centrado en versalitas)
local stringify = pandoc.utils.stringify

local REFS = { ["referencias"] = true, ["references"] = true, ["bibliografia"] = true,
               ["bibliografía"] = true, ["bibliography"] = true }

local function nombre(a)
  if type(a) == "table" and a.name then return stringify(a.name) end
  return stringify(a)
end

-- Figuras. apa7: "Figura 1" (negrita) y titulo (cursiva) ARRIBA de la imagen y la nota ("Nota."/"Note.") que
-- sigue a la figura, DENTRO del flotante (debajo de la imagen); [H] la deja donde se cita.
-- ieee: IEEEtran pone "Fig. 1." debajo, tal cual lo genera pandoc (no se toca).
local function es_nota(b)
  if b.t ~= "Para" and b.t ~= "Plain" then return false end
  local f = b.content[1]
  return f ~= nil and f.t == "Emph" and stringify(f):match("^%s*[Nn]ot[ae]%s*%.") ~= nil
end

local function sin_sangria(inlines)  -- las notas de tabla/figura van sin sangria de primera linea (APA 7.14)
  local r = { pandoc.RawInline("latex", "{\\raggedright\\noindent ") }  -- en grupo: el flotante centra
  for _, x in ipairs(inlines) do r[#r + 1] = x end
  r[#r + 1] = pandoc.RawInline("latex", "\\par}")
  return r
end

function figuras(blocks, base)
  if base ~= "apa7" then return blocks end
  local out, i = {}, 1
  while i <= #blocks do
    local b = blocks[i]
    if b.t == "Figure" then
      local cap = {}
      for _, cb in ipairs(b.caption.long) do
        if cb.content then for _, x in ipairs(cb.content) do cap[#cap + 1] = x end end
      end
      out[#out + 1] = pandoc.RawBlock("latex", "\\begin{figure}[H]")
      local lab = b.identifier ~= "" and ("\\label{" .. b.identifier .. "}") or ""
      local c = { pandoc.RawInline("latex", "\\caption{") }
      for _, x in ipairs(cap) do c[#c + 1] = x end
      c[#c + 1] = pandoc.RawInline("latex", "}" .. lab)
      out[#out + 1] = pandoc.Plain(c)
      out[#out + 1] = pandoc.RawBlock("latex", "\\centering")
      for _, cb in ipairs(b.content) do out[#out + 1] = cb end
      local nxt = blocks[i + 1]
      if nxt and es_nota(nxt) then
        out[#out + 1] = pandoc.Para(sin_sangria(nxt.content))
        i = i + 1
      end
      out[#out + 1] = pandoc.RawBlock("latex", "\\end{figure}")
    elseif b.t == "Table" and blocks[i + 1] and es_nota(blocks[i + 1]) then
      out[#out + 1] = b
      out[#out + 1] = pandoc.Para(sin_sangria(blocks[i + 1].content))
      i = i + 1
    else
      out[#out + 1] = b
    end
    i = i + 1
  end
  return out
end

function Pandoc(doc)
  if FORMAT ~= "latex" then return nil end
  local meta = doc.meta
  local base = meta["perfil-base"] and stringify(meta["perfil-base"]) or "apa7"
  local lang = meta.lang and stringify(meta.lang) or "es"
  local es = lang:sub(1, 2) == "es"

  if base == "ieee" then
    meta.kwlabel = pandoc.MetaInlines { pandoc.Str(es and "Palabras clave" or "Index Terms") }
  else
    meta.kwlabel = pandoc.MetaInlines { pandoc.Str(es and "Palabras clave" or "Keywords") }
  end

  -- autores APA: "A", "A y B", "A, B y C"
  if meta.author then
    local lista = {}
    if pandoc.utils.type(meta.author) == "List" then
      for _, a in ipairs(meta.author) do lista[#lista + 1] = nombre(a) end
    else
      lista[1] = nombre(meta.author)
    end
    local conj = es and " y " or " and "
    local s
    if #lista <= 1 then s = lista[1] or ""
    elseif #lista == 2 then s = lista[1] .. conj .. lista[2]
    else
      s = table.concat(lista, ", ", 1, #lista - 1) .. (es and " y " or ", and ") .. lista[#lista]
    end
    meta.authorsline = pandoc.MetaInlines { pandoc.Str(s) }
  end

  doc.blocks = figuras(doc.blocks, base)

  local out = {}
  for _, b in ipairs(doc.blocks) do
    if b.t == "Header" and b.level == 1 and REFS[stringify(b):lower()] then
      if base == "apa7" then
        out[#out + 1] = pandoc.RawBlock("latex", "\\clearpage")
      else
        b.classes:insert("unnumbered")
      end
    end
    out[#out + 1] = b
  end
  doc.blocks = out
  return doc
end
