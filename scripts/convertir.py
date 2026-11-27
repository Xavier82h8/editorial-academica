#!/usr/bin/env python3
"""Convierte un .docx con citas escritas a mano (sin marcas [@id]) a otro perfil de formato.

Uso:
  python -I convertir.py doc.docx --a ieee [--de apa7|ieee] [--out salida.docx] [--sin-red] [--informe ruta.md] [--json res.json]
  (`--perfil` es alias de `--a`; sin ninguno se usa el `perfil:` de .editorial.yaml)

Pasos: pandoc docx -> AST (conserva tablas e imágenes) -> lista de referencias a CSL-JSON (refs_csl.py,
con verificación por DOI en Crossref) -> citas del texto a citas de pandoc -> render.py con el perfil
destino -> auditar.py. Nunca sobrescribe el original ni inventa metadatos.
Salidas junto a --out: <nombre>.docx, <nombre>.md (Markdown con [@id], para revisar), <nombre>.fuentes.json,
<nombre>.informe.md y la carpeta <nombre>_media/.
Salida: 0 si el juez no halla críticos ni mayores en el documento convertido; 1 si los halla; 2 error de uso o de entrada
(archivo inexistente o que no es .docx, sin lista de referencias, perfil desconocido, pandoc ausente).
"""
import argparse
import contextlib
import io
import json
import pathlib
import re
import subprocess
import sys
import types

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import auditar  # noqa: E402
import cli  # noqa: E402
import refs_csl  # noqa: E402
import render  # noqa: E402

INLINE_TYPES = {"Str", "Space", "SoftBreak", "LineBreak", "Emph", "Strong", "Strikeout", "Superscript", "Subscript",
                "SmallCaps", "Quoted", "Cite", "Code", "Math", "RawInline", "Link", "Image", "Note", "Span", "Underline"}
FORMATO = {"Emph", "Strong", "Strikeout", "Superscript", "Subscript", "SmallCaps", "Underline", "Span"}
OPACO = ""
YEAR = r"(?:\d{4}[a-z]?|s\. ?f\.(?:-[a-z])?|s/f(?:-[a-z])?|n\.d\.(?:-[a-z])?|in press|en prensa)"
PREFIJOS = (r"(?:véase(?: también| además)?|véanse|ver(?: también)?|vea|cf\.|cfr\.|por ejemplo,|p\. ?ej\.,?|e\. ?g\.,?|"
            r"see(?: also)?|compárese con|también|según)")
LOCALIZADOR = (r"(?:pp?\.|págs?\.|caps?\.|capítulos?|párrs?\.|parrs?\.|arts?\.|artículos?|secc?\.|sección|figs?\.|figura|tabla|"
               r"tbl\.|fr\.|vols?\.|núms?\.|n\.º|ch\.|paras?\.|§|ff?\.|líneas?|ll?\.|inciso|fracc?\.|apdo\.|ap\.|"
               r"Table|Fig\.|Sec\.|sects?\.|chapters?|chap\.|figures?|sections?|paragraphs?|pages?|appendix|slides?|minutes?|"
               r"theorem|thm\.|lemma|algorithm|eqs?\.|equations?|\d+:\d{2}(?::\d{2})?)")
ES_LOC = re.compile(r"^" + LOCALIZADOR, re.I)
ETIQUETAS_PAG = {"p.": "p.", "pp.": "pp.", "pág.": "p.", "págs.": "pp."}


# ------------------------------------------------------------------ utilidades AST
def texto_de(x):
    """Texto plano de un inline, bloque o lista (sin marcas)."""
    if isinstance(x, list):
        return "".join(texto_de(i) for i in x)
    if not isinstance(x, dict):
        return ""
    t, c = x.get("t"), x.get("c")
    if t == "Str":
        return c
    if t in ("Space", "SoftBreak"):
        return " "
    if t == "LineBreak":
        return "\n"
    if t == "Quoted":
        a, b = ("“", "”") if c[0]["t"] == "DoubleQuote" else ("‘", "’")
        return a + texto_de(c[1]) + b
    if t in ("Code", "Math"):
        return c[1]
    if t in ("Emph", "Strong", "Strikeout", "Superscript", "Subscript", "SmallCaps", "Underline"):
        return texto_de(c)
    if t == "Span":
        return texto_de(c[1])
    if t == "Link":
        return texto_de(c[1])
    if t == "Image":
        return texto_de(c[1])
    if t == "Cite":
        return texto_de(c[1])
    if t in ("Para", "Plain"):
        return texto_de(c)
    if t == "Header":
        return texto_de(c[2])
    return ""


def a_md(inls):
    """Inlines -> texto con *cursivas* (lo que espera refs_csl)."""
    out = []
    for x in inls:
        t, c = x["t"], x.get("c")
        if t == "Str":
            out.append(c.replace("*", refs_csl.ESCAPE))
        elif t in ("Space", "SoftBreak", "LineBreak"):
            out.append(" ")
        elif t == "Emph":
            inner = a_md(c)
            out.append("*" + inner + "*" if inner.strip() else inner)
        elif t in ("Strong", "Strikeout", "Superscript", "Subscript", "SmallCaps", "Underline"):
            out.append(a_md(c))
        elif t == "Span":
            out.append(a_md(c[1]))
        elif t == "Quoted":
            a, b = ("“", "”") if c[0]["t"] == "DoubleQuote" else ("‘", "’")
            out.append(a + a_md(c[1]) + b)
        elif t == "Link":
            txt = texto_de(c[1])
            url = c[2][0]
            out.append(url if (not txt.strip() or txt.strip().startswith(("http", "www")) or txt.strip() == url) else txt)
        elif t in ("Code", "Math"):
            out.append(c[1])
    s = "".join(out)
    s = re.sub(r"\*\s*\*", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def es_lista_inlines(x):
    return isinstance(x, list) and x and all(isinstance(i, dict) and i.get("t") in INLINE_TYPES for i in x)


def str_(s):
    return {"t": "Str", "c": s}


ESPACIO = {"t": "Space"}


def partir_palabras(s):
    out = []
    for i, w in enumerate(s.split(" ")):
        if i:
            out.append(ESPACIO)
        if w:
            out.append(str_(w))
    return out


def citation(id_, modo="NormalCitation", prefijo="", sufijo=""):
    return {"citationId": id_, "citationPrefix": partir_palabras(prefijo) if prefijo else [],
            "citationSuffix": partir_palabras(sufijo) if sufijo else [], "citationMode": {"t": modo},
            "citationNoteNum": 0, "citationHash": 0}


def cite(citas, visible):
    return {"t": "Cite", "c": [citas, [str_(visible)]]}


# ------------------------------------------------------------------ índice de etiquetas
def clave_anio(it):
    v = it.get("_verificacion", {})
    if v.get("clave_anio"):
        return v["clave_anio"]
    return refs_csl._clave_anio(it, v.get("sufijo", ""))


def norm_anio(t):
    t = t.strip()
    if re.fullmatch(r"in press|en prensa", t):
        return "ip"
    m = re.match(r"^(?:s\. ?f\.|s/f|n\.d\.)(?:-([a-z]))?$", t)
    if m:
        return "sf" + ("-" + m.group(1) if m.group(1) else "")
    return t


def apellidos(it):
    v = it.get("_verificacion", {})
    if v.get("apellidos_texto") is not None:
        return list(v["apellidos_texto"])
    au = it.get("author") or it.get("editor") or it.get("host") or []
    return [p.get("family") or p.get("literal") or "" for p in au]


class Indice:
    """Etiquetas de autor (como se escriben en el texto) -> items."""

    def __init__(self, items):
        self.items = items
        self.por_id = {i["id"]: i for i in items}
        self.etq = {}       # (etiqueta, clave_anio) -> [items]
        self.etiquetas = set()
        for it in items:
            self.agregar(it)

    def _reg(self, et, it, alias=False):
        et = et.strip()
        if not et or len(et) < 2:
            return
        self.etiquetas.add(et)
        self.etq.setdefault((et, clave_anio(it)), [])
        if it not in self.etq[(et, clave_anio(it))]:
            self.etq[(et, clave_anio(it))].append(it)

    def agregar(self, it):
        fams = apellidos(it)
        v = it.get("_verificacion", {})
        sig = v.get("sigla")
        n = len(fams)
        if it.get("type") == "legislation" and not fams:
            self._reg(it.get("title", ""), it)
            if sig:
                self._reg(sig, it)
            return
        if not fams:
            return
        if n == 1:
            self._reg(fams[0], it)
            if sig:
                self._reg(sig, it)
            pal = fams[0].split()
            if len(pal) >= 2 and "literal" not in (it.get("author") or [{}])[0]:
                for k in range(1, len(pal)):
                    self._reg(" ".join(pal[:k]), it, True)
                    self._reg(" ".join(pal[k:]), it, True)
        elif n == 2:
            for conj in (" & ", " y ", " and ", " e "):
                self._reg(fams[0] + conj + fams[1], it)
            for a in (fams[0], fams[1]):
                pass
        if n >= 3 or v.get("etal") or v.get("omitidos"):
            self._reg(fams[0] + " et al.", it)
            self._reg(fams[0] + " et al", it)
            for k in range(1, len(fams[0].split())):
                self._reg(" ".join(fams[0].split()[k:]) + " et al.", it, True)
        # desambiguación APA: «J. M. Taylor & Neimeyer», «Kapoor, Bloom, et al.»
        aus = it.get("author") or it.get("editor") or []
        dados = [(pp.get("given") or "") for pp in aus] if len(aus) == n else []
        if dados and dados[0] and re.fullmatch(r"(?:[A-ZÀ-ÝŁ][a-zà-ÿ]?\.[\s-]*)+", dados[0].strip()):
            f0 = dados[0].strip() + " " + fams[0]
            if n == 1:
                self._reg(f0, it, True)
            elif n == 2:
                for conj in (" & ", " y ", " and "):
                    self._reg(f0 + conj + fams[1], it, True)
                    if dados[1]:
                        self._reg(f0 + conj + dados[1].strip() + " " + fams[1], it, True)
            else:
                self._reg(f0 + " et al.", it, True)
        for k in range(2, n):
            self._reg(", ".join(fams[:k]) + ", et al.", it, True)
        if n == 2:
            # abreviaturas de apellidos compuestos: "Hernández-Sampieri & Mendoza"
            pa = [fams[0].split(), fams[1].split()]
            for i in range(len(pa[0]) + 1):
                for j in range(len(pa[1]) + 1):
                    a = " ".join(pa[0][i:] if i < len(pa[0]) else pa[0])
                    for conj in (" & ", " y "):
                        for x in {" ".join(pa[0][:max(1, len(pa[0]) - i)]), " ".join(pa[0])}:
                            for y in {" ".join(pa[1][:max(1, len(pa[1]) - j)]), " ".join(pa[1])}:
                                self._reg(x + conj + y, it, True)

    def regex_etiquetas(self):
        et = sorted(self.etiquetas, key=len, reverse=True)
        return "|".join(re.escape(e) for e in et) or "(?!)"

    def buscar(self, etiqueta, anio):
        """-> (item|None, motivo)"""
        yk = norm_anio(anio)
        c = self.etq.get((etiqueta, yk))
        if not c and re.search(r"[a-z]$", yk) is None:
            # año sin letra: aceptar si hay un único item con ese año
            c = [i for (e, k), lst in self.etq.items() if e == etiqueta and re.sub(r"[a-z]$", "", k.replace("-", "")) == yk.replace("-", "") for i in lst]
            c = list({id(i): i for i in c}.values())
        if not c:
            return None, "sin entrada en la lista de referencias"
        if len(c) > 1:
            return None, "ambigua: " + ", ".join(i["id"] for i in c)
        return c[0], None


# ------------------------------------------------------------------ flujo de texto
class Flujo:
    """Texto plano de una lista de inlines con el mapa a sus tokens."""

    def __init__(self, inls):
        self.inls = inls
        self.tok = []   # (inicio, fin, inline, divisible)
        buf = []
        pos = 0
        for x in inls:
            t = x["t"]
            if t == "Str":
                s = re.sub("[\u00a0\u202f\u2009]", " ", x["c"])
                div = True
            elif t in ("Space", "SoftBreak"):
                s, div = " ", False
            elif t == "LineBreak":
                s, div = "\n", False
            elif t in FORMATO or t == "Quoted":
                s, div = re.sub("[\u00a0\u202f\u2009]", " ", texto_de(x)), False
            else:
                s, div = OPACO * max(1, len(texto_de(x))), False
            self.tok.append((pos, pos + len(s), x, div))
            buf.append(s)
            pos += len(s)
        self.texto = "".join(buf)

    def reemplazar(self, spans):
        """spans: [(a, b, [inlines])] sin solapes -> nueva lista de inlines; omite los que caen dentro de un formato."""
        spans = sorted(spans, key=lambda s: s[0])
        validos = []
        rechazados = []
        internos = []
        for sp in spans:
            a, b, nuevo = sp[0], sp[1], sp[2]
            ok = True
            for ini, fin, x, div in self.tok:
                for lim in (a, b):
                    if ini < lim < fin and not div:
                        ok = False
            if ok:
                validos.append(sp)
            elif any(ini <= a and b <= fin and (x["t"] in FORMATO or x["t"] == "Quoted") for ini, fin, x, div in self.tok):
                internos.append(sp)     # cae dentro de una cursiva/negrita: se procesa al recursar en ella
            else:
                rechazados.append(sp)
        out = []
        for ini, fin, x, div in self.tok:
            piezas = [(ini, fin, x)]
            if div:
                cortes = sorted({lim for a, b, *_ in validos for lim in (a, b) if ini < lim < fin})
                if cortes:
                    s = x["c"]
                    piezas = []
                    prev = ini
                    for c in cortes + [fin]:
                        piezas.append((prev, c, str_(s[prev - ini:c - ini])))
                        prev = c
            for pa, pb, px in piezas:
                dentro = next((v for v in validos if v[0] <= pa and pb <= v[1]), None)
                if dentro is None:
                    out.append(px)
                elif dentro[0] == pa:
                    out.extend(dentro[2])
        return out, validos, rechazados, internos


def contexto(texto, a, b, n=70):
    return re.sub(r"\s+", " ", texto[max(0, a - n):a] + "⟦" + texto[a:b] + "⟧" + texto[b:b + n]).replace(OPACO, "·")


# ------------------------------------------------------------------ mapeo de citas
class Loc(str):
    """Localizador (puede ir vacío) que recuerda la etiqueta de autor tal como estaba escrita (p. ej. «SCJN»)."""
    etq = None


def _con_etq(loc, etq):
    r = Loc(loc or "")
    r.etq = etq
    return r


def es_sigla(etq):
    return bool(etq) and ("[" in etq or re.fullmatch(r"[A-ZÁÉÍÓÚÑ0-9/&\-]{2,12}", etq) is not None)


def _texto_loc(l):
    return (l or "").strip().lstrip(",").strip()


def _solo_loc(l):
    t = _texto_loc(l)
    return t if ES_LOC.match(t) else ""


class Mapeador:
    def __init__(self, indice, origen, destino, numeros=None):
        self.ix = indice
        self.origen = origen
        self.destino = destino
        self.numeros = numeros or {}        # IEEE de origen: n -> item
        self.citas = []                     # citas mapeadas (para el informe y las pruebas)
        self.no_mapeadas = []               # (motivo, texto, contexto)
        self.silencio = 0
        self.usados = set()
        self.siglas_vistas = set()          # APA 8.21: la sigla se define en la primera cita
        self.rx_et = indice.regex_etiquetas()
        self.parte = re.compile(
            r"^(?P<pre>" + PREFIJOS + r"\s+|[^;]+?,\s*(?:as cited in|citado en)\s+)?(?P<lab>" + self.rx_et + r")(?:\s*\[(?P<sig>[^\]]+)\])?,\s*"
            r"(?P<anios>" + YEAR + r"(?:\s*,\s*" + YEAR + r")*)(?P<loc>\s*,\s*[^;]+)?\s*$")
        self.sin_anio = re.compile(r"^(?:" + PREFIJOS + r"\s+)?(?:" + self.rx_et + r")\s*,\s*" + LOCALIZADOR, re.I)
        self.narr = re.compile(
            r"(?<![\w\[])(?P<lab>" + self.rx_et + r")(?:\s*\[(?P<sig>[^\]]+)\])?\s*\((?P<anios>" + YEAR +
            r"(?:\s*,\s*" + YEAR + r")*)(?P<loc>\s*,\s*" + LOCALIZADOR + r"[^()]*)?\)")
        self.generica = re.compile(r"^(?:" + PREFIJOS + r"\s+)?(?P<lab>[A-ZÁÉÍÓÚÑ][^,;()]*?)(?:\s*\[[^\]]+\])?,\s*" + YEAR + r"\b")
        self.generica_narr = re.compile(r"(?<![\w\[])(?P<lab>[A-ZÁÉÍÓÚÑ][\w\-’']+(?: et al\.|(?: y| &| and) [A-ZÁÉÍÓÚÑ][\w\-’']+)?)\s*\((?P<anios>" + YEAR + r")(?:[,)])")

    # --- construcción de inlines de cita
    def sufijo_loc(self, loc, primera=True):
        """Localizador original -> texto de sufijo para pandoc (', p. 14' o ', {arts. 27 y 78}')."""
        loc = (loc or "").strip().lstrip(",").strip()
        if not loc:
            return ""
        m = re.match(r"^(págs?\.|pp?\.)\s*(.+)$", loc)
        if m:
            return ", " + ETIQUETAS_PAG[m.group(1)] + " " + m.group(2).strip()
        if not ES_LOC.match(loc):
            return ", " + loc          # texto libre («for more detail»): sufijo, no localizador
        return ", {" + loc + "}"

    def registrar(self, modo, items_loc, original, prefijo="", ctx=""):
        self.citas.append({"modo": modo, "claves": [i["id"] for i, _ in items_loc],
                           "localizadores": [(_texto_loc(l) if self.origen == "ieee" else _solo_loc(l)) for _, l in items_loc],
                           "sufijos": [_texto_loc(l) for _, l in items_loc if _texto_loc(l) and not ES_LOC.match(_texto_loc(l))],
                           "prefijo": prefijo.strip(), "original": original, "contexto": ctx})
        for i, _ in items_loc:
            self.usados.add(i["id"])

    def nombre_sigla(self, it, etq):
        """Si `etq` es la sigla de un autor grupal que aún no se ha definido en el texto (APA 8.21),
        devuelve el nombre completo; si ya se definió (o la cita trae «Nombre [SIGLA]»), None."""
        sig = (it.get("_verificacion") or {}).get("sigla")
        if not sig:
            return None
        if "[" in (etq or ""):
            self.siglas_vistas.add(sig)
            return None
        if etq != sig or sig in self.siglas_vistas:
            return None
        self.siglas_vistas.add(sig)
        au = (it.get("author") or [{}])[0]
        return au.get("literal")

    def inlines_parentetica(self, items_loc, prefijo, original):
        citas = []
        envolver = self.destino == "ieee" and prefijo.endswith(";")   # «SUS;» no es una cita: (SUS [57])
        for k, (it, loc) in enumerate(items_loc):
            pre_k = prefijo if k == 0 and not envolver else ""
            etq = getattr(loc, "etq", None)
            if self.destino == "apa7" and es_sigla(etq):
                # «Nombre [SIGLA], año» la 1.ª vez y «SIGLA, año» después (APA 8.21)
                completo = self.nombre_sigla(it, etq)
                etq_v = f"{completo} [{etq}]" if completo else etq
                citas.append(citation(it["id"], "SuppressAuthor", (pre_k + " " if pre_k else "") + etq_v + ",", self.sufijo_loc(loc)))
            else:
                citas.append(citation(it["id"], "NormalCitation", pre_k, self.sufijo_loc(loc)))
        if envolver:
            return partir_palabras("(" + prefijo.rstrip(";") + " ") + [cite(citas, original), str_(")")]
        return [cite(citas, original)]

    def inlines_narrativa(self, items_loc, etiqueta_texto, original):
        if self.destino.endswith("ieee") or self.destino == "ieee":
            citas = [citation(it["id"], "NormalCitation", "", self.sufijo_loc(loc)) for it, loc in items_loc]
            return partir_palabras(etiqueta_texto + " ") + [cite(citas, original)]
        citas = []
        sigla = es_sigla(items_loc[0][1].etq if items_loc and hasattr(items_loc[0][1], "etq") else None)
        for k, (it, loc) in enumerate(items_loc):
            suf = self.sufijo_loc(loc).lstrip(", ").strip() if k == 0 else ""
            modo = "AuthorInText" if (k == 0 and not sigla) else "SuppressAuthor"
            citas.append(citation(it["id"], modo, "", suf))
        if sigla:
            etq = items_loc[0][1].etq
            completo = self.nombre_sigla(items_loc[0][0], etq)
            if completo:  # «Nombre (SIGLA, año)» la 1.ª vez (APA 8.21)
                citas[0] = citation(items_loc[0][0]["id"], "SuppressAuthor", etq + ",",
                                    self.sufijo_loc(items_loc[0][1]))
                return partir_palabras(completo + " ") + [cite(citas, original)]
            return partir_palabras(etq + " ") + [cite(citas, original)]
        return [cite(citas, original)]

    # --- APA
    def separar_anios(self, anios):
        return [a.strip() for a in re.split(r",\s*", anios)]

    def analizar_parte_apa(self, parte, nota=None):
        m = self.parte.match(parte.strip())
        if not m:
            return None, "formato de cita no reconocido"
        res = []
        for a in self.separar_anios(m.group("anios")):
            it, motivo = self.ix.buscar(m.group("lab"), a)
            if it is None:
                return None, f"{m.group('lab')}, {a}: {motivo}"
            res.append((it, _con_etq("", m.group("lab") + (f" [{m.group('sig')}]" if m.group("sig") else ""))))
        if m.group("loc"):
            res[-1] = (res[-1][0], _con_etq(m.group("loc"), res[-1][1].etq))
        return (res, (m.group("pre") or "").strip()), None

    def paren_apa(self, texto):
        """Devuelve spans de citas parentéticas APA."""
        spans = []
        pares = []
        pila = []
        for i, ch in enumerate(texto):
            if ch == "(":
                pila.append(i)
            elif ch == ")" and pila:
                pares.append((pila.pop(), i))
        pares.sort(key=lambda p: p[1] - p[0])
        ocupado = []
        for a, b in pares:
            if any(not (b < x or a > y) for x, y in ocupado):
                continue
            cont = texto[a + 1:b]
            if not re.search(YEAR, cont):
                if self.sin_anio.match(cont.strip()) and not any(not (b < x or a > y) for x, y in ocupado):
                    self.nm(("cita sin año (el autor está en la lista, pero falta el año): no se completa para no alterar lo escrito",
                             texto[a:b + 1], contexto(texto, a, b + 1)))
                    ocupado.append((a, b))
                continue
            partes = [p.strip() for p in cont.split(";")]
            items_loc = []
            prefijo = ""
            fallo = None
            for k, p in enumerate(partes):
                r, motivo = self.analizar_parte_apa(p)
                if r is None:
                    # primera parte sin año, corta: texto previo ("SUS;") que se conserva como prefijo
                    if k == 0 and len(partes) > 1 and not re.search(YEAR, p) and len(p) <= 60 and not items_loc:
                        prefijo = p + ";"
                        continue
                    fallo = (p, motivo)
                    break
                its, pre = r
                if pre:
                    prefijo = (prefijo + " " + pre).strip() if k == 0 or not prefijo else prefijo
                    if k > 0:
                        fallo = (p, "prefijo en una cita que no es la primera del grupo")
                        break
                items_loc += its
            if fallo is None and items_loc:
                spans.append((a, b + 1, items_loc, prefijo, texto[a:b + 1], "parentetica"))
                ocupado.append((a, b))
                continue
            if fallo is None:
                continue
            # texto corrido entre paréntesis con «Autor, año» dentro: en IEEE se puede escribir «Autor [n]»
            if self.destino == "ieee":
                internas = []
                for m in re.finditer(r"(?<![\w])(?P<lab>" + self.rx_et + r")(?:\s*\[[^\]]+\])?,\s*(?P<an>" + YEAR + r")(?P<loc>\s*,\s*" + LOCALIZADOR + r"[^,;)]*)?", cont):
                    it, _ = self.ix.buscar(m.group("lab"), m.group("an"))
                    if it is not None:
                        internas.append((a + 1 + m.start(), a + 1 + m.end(), [(it, m.group("loc"))], m.group("lab"), m.group(0), "narrativa"))
                n_pares = len(re.findall(r"[A-ZÁÉÍÓÚÑ][^,;()]*?,\s*" + YEAR + r"\b", cont))
                if internas and len(internas) >= n_pares:
                    spans += internas
                    ocupado.append((a, b))
                    continue
            if self.generica.match(fallo[0]) is not None and fallo[1] != "formato de cita no reconocido":
                self.nm((fallo[1], texto[a:b + 1], contexto(texto, a, b + 1)))
                ocupado.append((a, b))
            elif re.search(r"[A-ZÁÉÍÓÚÑ][^,;()]*?,\s*" + YEAR + r"\b", cont) and not re.search(r"\d\.\d|versión|version", cont):
                self.nm((f"no se pudo representar con la sintaxis de pandoc (autor y año dentro de texto corrido entre paréntesis): {fallo[1]}", texto[a:b + 1],
                         contexto(texto, a, b + 1)))
                ocupado.append((a, b))
        return spans, ocupado

    def narrativas_apa(self, texto, ocupado):
        spans = []
        for m in self.narr.finditer(texto):
            a, b = m.span()
            if any(not (b <= x or a > y) for x, y in ocupado):
                continue
            res = []
            for an in self.separar_anios(m.group("anios")):
                it, motivo = self.ix.buscar(m.group("lab"), an)
                if it is None:
                    res = None
                    self.nm((f"{m.group('lab')} ({an}): {motivo}", m.group(0), contexto(texto, a, b)))
                    break
                res.append((it, _con_etq("", m.group("lab") + (f" [{m.group('sig')}]" if m.group("sig") else ""))))
            if not res:
                continue
            if m.group("loc"):
                res[-1] = (res[-1][0], _con_etq(m.group("loc"), res[-1][1].etq))
            etiqueta = m.group("lab") + (f" [{m.group('sig')}]" if m.group("sig") else "")
            spans.append((a, b, res, etiqueta, m.group(0)))
            ocupado.append((a, b - 1))
        # narrativas desconocidas (autor + año entre paréntesis sin entrada en la lista)
        for m in self.generica_narr.finditer(texto):
            a, b = m.span()
            if any(not (b <= x or a > y) for x, y in ocupado):
                continue
            if m.group("lab") in self.ix.etiquetas:
                continue
            self.nm(("sin entrada en la lista de referencias", m.group(0), contexto(texto, a, b)))
        return spans

    # --- IEEE
    def grupos_ieee(self, texto):
        corchete = r"\[\s*[^\[\]]+?\s*\]"
        rx = re.compile(r"(?:(?P<nom>[A-ZÁÉÍÓÚÑ][\w\-’']+(?: et al\.|(?: y| and| &) [A-ZÁÉÍÓÚÑ][\w\-’']+)?)\s+)?(?P<g>" + corchete + r"(?:\s*(?:,|–|—|-)\s*" + corchete + r")*)")
        spans = []
        for m in rx.finditer(texto):
            g = m.group("g")
            a, b = m.start("g"), m.end("g")
            lista = self.parse_grupo_ieee(g)
            if lista is None:
                continue
            if isinstance(lista, str):
                self.nm((lista, g, contexto(texto, a, b)))
                continue
            nom = m.group("nom")
            narr = False
            if nom and self.origen == "ieee":
                autor = {nom, nom.replace(" et al.", ""), }
                primero = lista[0][0]
                ets = {e for (e, k), lst in self.ix.etq.items() if primero in lst}
                narr = nom in ets or nom.split(" ")[0] in {e.split(" ")[0] for e in ets}
            if narr:
                a = m.start("nom")
            spans.append((a, b, lista, nom if narr else "", texto[a:b], narr))
        return spans

    def parse_grupo_ieee(self, g):
        """'[1], [2]–[4]' / '[1, Fig. 2]' -> [(item, loc)] | str (motivo) | None (no es una cita)."""
        brs = re.findall(r"\[\s*([^\[\]]+?)\s*\]", g)
        seps = re.findall(r"\]\s*([^\[\]]*?)\s*\[", g)
        out = []
        for k, c in enumerate(brs):
            toks = [t.strip() for t in re.split(r",\s*(?=\d|[A-Za-z])", c) if t.strip()]
            nums = []
            for t in toks:
                mr = re.fullmatch(r"(\d+)\s*[–—-]\s*(\d+)", t)
                mn = re.fullmatch(r"(\d+)", t)
                ml = re.match(r"^[A-Za-z][\w.]*\s*.+$", t) or re.fullmatch(r"\d+:\d{2}(?::\d{2})?", t)
                if mr:
                    lo, hi = int(mr.group(1)), int(mr.group(2))
                    if lo > hi:
                        return None
                    nums += [[n, None] for n in range(lo, hi + 1)]
                elif mn:
                    nums.append([int(t), None])
                elif ml and nums:
                    nums[-1][1] = (nums[-1][1] + ", " + t) if nums[-1][1] else t
                else:
                    return None
            if not nums:
                return None
            if k > 0 and seps[k - 1] in ("–", "—", "-") and out and nums:
                ini = out[-1][0]
                fin = nums[0][0]
                if fin > ini + 1:
                    out += [[n, None] for n in range(ini + 1, fin)]
            out += nums
        res = []
        for n, loc in out:
            it = self.numeros.get(n)
            if it is None:
                return f"[{n}] no existe en la lista de referencias"
            res.append((it, loc))
        return res

    # --- API
    def nm(self, *a):
        t = a[0] if len(a) == 1 else a
        if not self.silencio:
            self.no_mapeadas.append(tuple(t))

    def procesar(self, inls):
        fl = Flujo(inls)
        texto = fl.texto
        spans = []   # (a, b, inlines nuevos, meta)
        if self.origen == "ieee":
            for a, b, lista, nom, orig, narr in self.grupos_ieee(texto):
                if narr and self.destino != "ieee":
                    nuevo = self.inlines_narrativa(lista, nom, orig)
                    modo = "narrativa"
                elif narr:
                    nuevo = partir_palabras(nom + " ") + self.inlines_parentetica(lista, "", orig)
                    modo = "narrativa"
                else:
                    nuevo = self.inlines_parentetica(lista, "", orig)
                    modo = "parentetica"
                spans.append((a, b, nuevo, (modo, lista, "", orig)))
        else:
            ps, ocupado = self.paren_apa(texto)
            for a, b, lista, pre, orig, modo in ps:
                if modo == "narrativa":
                    spans.append((a, b, self.inlines_narrativa(lista, pre, orig), ("narrativa", lista, "", orig)))
                else:
                    spans.append((a, b, self.inlines_parentetica(lista, pre, orig), ("parentetica", lista, pre, orig)))
            for a, b, lista, etq, orig in self.narrativas_apa(texto, ocupado):
                spans.append((a, b, self.inlines_narrativa(lista, etq, orig), ("narrativa", lista, "", orig)))
        nuevo = inls
        if spans:
            spans.sort(key=lambda s: s[0])
            limpio = []
            for s in spans:
                if limpio and s[0] < limpio[-1][1]:
                    continue
                limpio.append(s)
            nuevo, validos, rechazados, internos = fl.reemplazar(limpio)
            for sp in validos:
                modo, lista, pre, orig = sp[3]
                self.registrar(modo, lista, orig, pre, contexto(texto, sp[0], sp[1]))
            for sp in rechazados:
                self.nm("la cita cruza el borde de un formato (cursiva, negrita) y no se pudo reemplazar", sp[3][3],
                        contexto(texto, sp[0], sp[1]))
        # recursión dentro de cursivas, negritas y comillas
        res = []
        self.silencio += 1
        try:
            for x in nuevo:
                t = x.get("t")
                if t in FORMATO and t != "Span" and es_lista_inlines(x["c"]):
                    x = {"t": t, "c": self.procesar(x["c"])}
                elif t == "Span" and es_lista_inlines(x["c"][1]):
                    x = {"t": t, "c": [x["c"][0], self.procesar(x["c"][1])]}
                elif t == "Quoted" and es_lista_inlines(x["c"][1]):
                    x = {"t": t, "c": [x["c"][0], self.procesar(x["c"][1])]}
                res.append(x)
        finally:
            self.silencio -= 1
        return res


def caminar(nodo, f):
    """Recorre el AST y aplica f a cada lista de inlines."""
    if isinstance(nodo, list):
        if es_lista_inlines(nodo):
            return f(nodo)
        return [caminar(x, f) for x in nodo]
    if isinstance(nodo, dict):
        if nodo.get("t") == "Cite":
            return nodo
        if "c" in nodo:
            r = dict(nodo)
            r["c"] = caminar(nodo["c"], f)
            return r
    return nodo


# ------------------------------------------------------------------ lista de referencias en el AST
def encontrar_lista(bloques):
    """-> (indice_titulo, [indices de bloques de entradas], nivel) usando los mismos títulos que auditar.py."""
    k = None
    for i, b in enumerate(bloques):
        if b["t"] == "Header" and auditar.titulo_limpio(texto_de(b)) in auditar.TITULOS_REF:
            k = i
    if k is None:
        for i, b in enumerate(bloques):
            if b["t"] in ("Para", "Plain") and len(texto_de(b)) < 40 and auditar.titulo_limpio(texto_de(b)) in auditar.TITULOS_REF:
                k = i
    if k is None:
        return None, [], 1
    nivel = bloques[k]["c"][0] if bloques[k]["t"] == "Header" else 1
    fin = len(bloques)
    for i in range(k + 1, len(bloques)):
        b = bloques[i]
        if b["t"] == "Header" or (b["t"] in ("Para", "Plain") and re.match(r"^(appendix|apéndice|anexo)\b", texto_de(b).strip(), re.I)):
            fin = i
            break
    return k, list(range(k + 1, fin)), nivel


def entradas_de(bloques, idx):
    """Cada párrafo (o ítem de lista) no vacío es una entrada. -> [(indice_bloque, inlines)]"""
    out = []
    for i in idx:
        b = bloques[i]
        if b["t"] in ("Para", "Plain"):
            if texto_de(b).strip():
                out.append((i, b["c"]))
        elif b["t"] in ("OrderedList", "BulletList"):
            items = b["c"][1] if b["t"] == "OrderedList" else b["c"]
            for it in items:
                for bb in it:
                    if bb["t"] in ("Para", "Plain") and texto_de(bb).strip():
                        out.append((i, bb["c"]))
    return out


def detectar_idioma(texto):
    t = " " + texto.lower() + " "
    es = sum(t.count(w) for w in (" de ", " la ", " el ", " que ", " los ", " en ", " y ", " una "))
    en = sum(t.count(w) for w in (" the ", " of ", " and ", " to ", " is ", " in ", " that ", " with "))
    return "es-MX" if es >= en else "en-US"


def adaptar_leyes(items, norma_dest="apa7"):
    """CSL 'legislation' de APA/IEEE imprime «Título, Gaceta (año)». El formato escrito en el documento, «Ley X. (fecha).
    Gaceta.», sale con un 'document' cuyo autor es el nombre de la ley y cuyo título es la gaceta."""
    out = []
    for it in items:
        if it.get("type") == "legislation" and not it.get("author"):
            c = dict(it)
            c["type"] = "document"
            c["author"] = [{"literal": c.pop("title")}]
            gaceta = c.pop("container-title", None)
            if gaceta:
                c["title"] = gaceta
            out.append(c)
        # «Autor [SIGLA].» no se reescribe en la lista: APA-065 pide nombre completo sin sigla;
        # la sigla vive solo en las citas («Autor [SIGLA], año» la primera vez y «SIGLA, año» después).
        else:
            out.append(it)
    return out


def nombres_salida(out):
    """Rutas de salida y auxiliares; todas derivan del nombre completo (doc.ieee.docx -> doc.ieee.md)."""
    out = pathlib.Path(out)
    base = str(out.with_suffix(""))
    return {"docx": out, "md": pathlib.Path(base + ".md"), "fuentes": pathlib.Path(base + ".fuentes.json"),
            "json": pathlib.Path(base + ".ast.json"), "media": pathlib.Path(base + "_media"),
            "informe": pathlib.Path(base + ".informe.md")}


def verificar_rutas(docx, N, informe_propio=None):
    """Aborta (exit 2) si alguna salida coincide con la entrada, entre sí o con un archivo ajeno ya existente."""
    entrada = pathlib.Path(docx).resolve()
    vistas = {}
    for clave, ruta in N.items():
        r = ruta.resolve()
        if r == entrada:
            print(f"la ruta de {clave} ({ruta}) coincide con la entrada: no se sobrescribe", file=sys.stderr)
            sys.exit(2)
        if r in vistas:
            print(f"las rutas de {clave} y {vistas[r]} coinciden ({ruta}); usa otra --out/--informe", file=sys.stderr)
            sys.exit(2)
        vistas[r] = clave
    if informe_propio is not None:  # --informe elegido por el usuario: no pisa un archivo que el script no creó
        r = informe_propio.resolve()
        if r.exists() and not r.name.endswith(".informe.md"):
            print(f"--informe apunta a un archivo existente que no es un informe previo: {informe_propio}", file=sys.stderr)
            sys.exit(2)


def pandoc_docx_a_json(docx, media):
    r = subprocess.run([render.pandoc(), str(docx), "-t", "json", "--extract-media=" + str(media)],
                       capture_output=True, text=True, encoding="utf-8")
    if r.returncode:
        cli.error("pandoc no pudo leer el .docx: " + r.stderr)
    return json.loads(r.stdout)


def convertir(docx, destino, de=None, out=None, sin_red=False, informe=None, idioma=None, auditar_salida=True, verbose=True):
    docx = pathlib.Path(docx).resolve()
    if not docx.exists():
        print(f"no existe {docx}", file=sys.stderr)
        sys.exit(2)
    if docx.suffix.lower() != ".docx":
        print(f"formato no soportado: {docx.suffix or '(sin extensión)'}; convertir.py necesita un .docx", file=sys.stderr)
        sys.exit(2)
    out = pathlib.Path(out) if out else docx.with_name(f"{docx.stem}.{destino}.docx")
    if out.resolve() == docx:
        print("la salida no puede ser el original: no se sobrescribe", file=sys.stderr)
        sys.exit(2)
    out.parent.mkdir(parents=True, exist_ok=True)
    N = nombres_salida(out)
    if informe:
        N["informe"] = pathlib.Path(informe)
    verificar_rutas(docx, N, pathlib.Path(informe) if informe else None)
    cfg_dest = render.perfil(destino)
    norma_dest = cfg_dest["citas"]

    ast = pandoc_docx_a_json(docx, N["media"].resolve())
    bloques = ast["blocks"]
    k, idx, nivel = encontrar_lista(bloques)
    if k is None:
        cli.error("no se encontró la lista de referencias (título como «Referencias», «Fuentes consultadas», etc.)")
    ents = entradas_de(bloques, idx)
    textos = [a_md(inl) for _, inl in ents]
    # numeración IEEE de origen
    norma_origen = de or refs_csl.detectar_norma([refs_csl.limpiar(t) for t in textos])
    if verbose:
        print(f"origen: {norma_origen} | entradas: {len(textos)} | destino: {destino}", flush=True)
    import doi_csl  # noqa: PLC0415
    items = refs_csl.parsear_lista(textos, norma_origen, red=True, solo_cache=sin_red,
                                   buscar_doi=lambda d: doi_csl.csl_por_doi(d, sin_red=sin_red))
    numeros = {}
    if norma_origen == "ieee":
        for n, (t, it) in enumerate(zip(textos, items), 1):
            m = re.match(r"^\[(\d+)\]", t)
            numeros[int(m.group(1)) if m else n] = it
    ix = Indice(items)
    # siglas introducidas en el texto: «Ley Federal del Derecho de Autor (LFDA)»
    todo = " ".join(texto_de(b) for i, b in enumerate(bloques) if i not in set(idx) and i != k)
    for it in items:
        nombre = it.get("title") if it.get("type") == "legislation" and not apellidos(it) else (apellidos(it) or [None])[0]
        if not nombre or len(nombre) < 6:
            continue
        for m in re.finditer(re.escape(nombre) + r"\s*[\(\[]([A-ZÁÉÍÓÚÑ][A-Za-z0-9ÁÉÍÓÚÑ/&\-]{1,12})[\)\]]", todo):
            if not re.fullmatch(r"\d+", m.group(1)):
                ix._reg(m.group(1), it, True)

    mp = Mapeador(ix, norma_origen, norma_dest, numeros)
    mp.destino = norma_dest
    resto = [b for i, b in enumerate(bloques) if i not in set(idx) and i != k]
    nuevos = []
    for i, b in enumerate(bloques):
        if i == k:
            nuevos.append("__REFS__")
        elif i in set(idx):
            continue
        else:
            nuevos.append(caminar(b, mp.procesar))
    # encabezado y contenedor de referencias del perfil destino
    idioma = idioma or detectar_idioma(" ".join(texto_de(b) for b in resto))
    titulo = "Referencias" if idioma.startswith("es") else "References"
    orig_h = bloques[k]
    cont = [str_(titulo)]
    if orig_h["t"] == "Header" and len(orig_h["c"][2]) == 1 and orig_h["c"][2][0]["t"] == "Strong":
        cont = [{"t": "Strong", "c": cont}]
    if orig_h["t"] == "Header":
        encabezado = {"t": "Header", "c": [nivel, ["referencias", [], []], cont]}
    else:
        encabezado = {"t": "Header", "c": [1, ["referencias", [], []], cont]}
    div = {"t": "Div", "c": [["refs", [], []], []]}
    final = []
    for b in nuevos:
        if b == "__REFS__":
            final += [encabezado, div]
        else:
            final.append(b)
    ast["blocks"] = final
    usados = mp.usados
    no_citadas = [i for i in items if i["id"] not in usados]
    ids = [i["id"] for i in no_citadas]
    if ids:
        ast.setdefault("meta", {})["nocite"] = {"t": "MetaInlines", "c": [cite([citation(i) for i in ids], "[@" + "; @".join(ids) + "]")]}
    N["json"].write_text(json.dumps(ast, ensure_ascii=False), encoding="utf-8")
    N["fuentes"].write_text(json.dumps(adaptar_leyes(items, norma_dest), ensure_ascii=False, indent=1), encoding="utf-8")
    # Markdown para revisar
    r = subprocess.run([render.pandoc(), str(N["json"]), "-f", "json", "-t", "markdown-smart", "--wrap=none"],
                       capture_output=True, text=True, encoding="utf-8")
    if r.returncode == 0:
        N["md"].write_text(r.stdout, encoding="utf-8")
    # render con el perfil destino
    ns = types.SimpleNamespace(doc=str(N["json"]), perfil=destino, fuentes=str(N["fuentes"]), salida="docx",
                               out=str(out), idioma=idioma)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        render.render_doc(ns)
    resultado_juez = None
    if auditar_salida:
        try:
            resultado_juez = auditar.auditar(str(out), destino)
        except Exception as ex:  # noqa: BLE001 - el juez no debe tumbar la conversión
            resultado_juez = {"dictamen_mecanico": f"no disponible (error del juez: {type(ex).__name__}: {ex})",
                              "conteo": {"crítica": 0, "mayor": 0, "menor": 0}, "hallazgos": [], "avisos": []}
    res = {"salida": str(out), "origen": norma_origen, "destino": destino, "idioma": idioma, "items": items,
           "citas": mp.citas, "no_mapeadas": mp.no_mapeadas, "no_citadas": no_citadas, "juez": resultado_juez,
           "rutas": {k_: str(v) for k_, v in N.items()}, "titulo_original": texto_de(bloques[k]),
           "titulo_nuevo": titulo, "n_bloques_lista": len(ents)}
    informe_md = redactar_informe(res, docx, ast)
    N["informe"].write_text(informe_md, encoding="utf-8")
    if verbose:
        v = [i["_verificacion"]["estado"] for i in items]
        print(f"entradas {len(items)}: verificadas {v.count('verificada')}, discrepancias {v.count('discrepancia')}, "
              f"no verificadas {v.count('no-verificada')} | citas mapeadas {len(mp.citas)}, no mapeadas {len(mp.no_mapeadas)} | "
              f"no citadas {len(no_citadas)}", flush=True)
        if resultado_juez:
            print("juez:", resultado_juez["dictamen_mecanico"], resultado_juez["conteo"], flush=True)
        print("salida:", out, "\ninforme:", N["informe"], flush=True)
    return res


def redactar_informe(r, docx, ast):
    items = r["items"]
    est = {"verificada": [], "discrepancia": [], "no-verificada": []}
    for it in items:
        est[it["_verificacion"]["estado"]].append(it)
    L = []
    L.append(f"# Informe de conversión: {pathlib.Path(docx).name} a {r['destino']}")
    L.append("")
    L.append(f"- Origen detectado: **{r['origen']}** | Destino: **{r['destino']}** | Idioma: {r['idioma']}")
    L.append(f"- Salida: `{r['salida']}` (el original no se modifica)")
    L.append(f"- Fuentes en CSL-JSON: `{r['rutas']['fuentes']}`; Markdown intermedio: `{r['rutas']['md']}`")
    L.append("")
    L.append("## Referencias")
    L.append(f"- Entradas en la lista original: **{len(items)}**")
    L.append(f"- Verificadas contra Crossref (DOI coincide en título, año y primer autor): **{len(est['verificada'])}**")
    L.append(f"- Con discrepancia (se conservó lo escrito en el documento): **{len(est['discrepancia'])}**")
    L.append(f"- No verificadas (sin DOI o sin respuesta): **{len(est['no-verificada'])}**. No se inventó ningún metadato: solo se usó lo que dice el documento.")
    L.append("")
    if est["discrepancia"]:
        L.append("### Discrepancias con Crossref")
        for it in est["discrepancia"]:
            L.append(f"- `{it['id']}`: {it['_verificacion']['original'][:110]}")
            for n in it["_verificacion"]["notas"]:
                if "Crossref" in n or "distinto" in n or "DOI" in n:
                    L.append(f"  - {n}")
        L.append("")
    L.append("### Entradas no verificadas")
    sin_doi = [i for i in est["no-verificada"]]
    for it in sin_doi:
        motivo = "sin DOI" if not it.get("DOI") else "; ".join(n for n in it["_verificacion"]["notas"] if "DOI" in n or "Crossref" in n)
        L.append(f"- `{it['id']}` ({motivo}): {it['_verificacion']['original'][:100]}")
    L.append("")
    avis = [(it, n) for it in items for n in it["_verificacion"]["notas"] if "no se pudo" in n or "no reconocido" in n or "error del parser" in n or "se omitió" in n]
    if avis:
        L.append("### Avisos del parser de referencias")
        for it, n in avis:
            L.append(f"- `{it['id']}`: {n}")
        L.append("")
    L.append("## Citas en el texto")
    mc = r["citas"]
    nm = r["no_mapeadas"]
    tot = len(mc) + len(nm)
    L.append(f"- Citas detectadas: **{tot}**; convertidas a citas de pandoc: **{len(mc)}** ({100 * len(mc) / tot:.0f} %); no mapeadas: **{len(nm)}**" if tot else "- No se detectaron citas.")
    por_modo = {}
    for c in mc:
        por_modo[c["modo"]] = por_modo.get(c["modo"], 0) + 1
    if por_modo:
        L.append("- Por tipo: " + ", ".join(f"{k} {v}" for k, v in por_modo.items()))
    L.append("")
    if nm:
        L.append("### Citas no mapeadas (el texto original queda intacto)")
        for motivo, texto, ctx in nm:
            L.append(f"- «{texto}»: {motivo}. Contexto: …{ctx}…")
        L.append("")
    L.append("## Entradas no citadas en el texto")
    nc = r["no_citadas"]
    if nc:
        L.append("Se conservan en la lista con `nocite` (no se borran):")
        for it in nc:
            L.append(f"- `{it['id']}`: {it['_verificacion']['original'][:110]}")
    else:
        L.append("Ninguna: todas las entradas se citan en el texto.")
    L.append("")
    L.append("## Dictamen del juez determinista (`auditar.py`, perfil destino)")
    j = r.get("juez")
    if j:
        L.append(f"- Dictamen: **{j['dictamen_mecanico']}**; hallazgos: crítica {j['conteo']['crítica']}, mayor {j['conteo']['mayor']}, menor {j['conteo']['menor']}")
        for h in j["hallazgos"][:40]:
            L.append(f"  - {h['id']} ({h['severidad']}): {h['ubicacion']} | {h['evidencia']} | corregir: {h['correccion']}")
        for a in j.get("avisos", []):
            L.append(f"  - aviso: {a}")
    L.append("")
    L.append("## Qué se pierde o cambia en la conversión")
    L.append(f"- El encabezado de la lista pasa de «{r['titulo_original']}» a «{r['titulo_nuevo']}» (sin numeración, como exige APA-059).")
    L.append("- Se rehacen con la plantilla del perfil destino: portada, encabezados y pies de página, estilos personalizados, saltos de sección, márgenes y fuentes locales.")
    L.append("- Una tabla de contenido escrita a mano queda como texto; los campos de Word (TOC, referencias cruzadas) no se conservan.")
    L.append("- Tablas e imágenes se conservan, pero el ancho de columnas y el formato fino de celdas pueden cambiar.")
    L.append("- Las citas de autor-fecha dentro de texto corrido entre paréntesis (por ejemplo «(por ejemplo, que Vaswani et al., 2017, propusieron…)») no tienen representación en pandoc y se dejan como estaban.")
    L.append("- Los contenedores en IEEE van abreviados según la norma; esta herramienta no abrevia los nombres de revista, así que quedan como estaban en el original.")
    L.append("- Al pasar de APA a IEEE (o al revés) cambia la capitalización esperada de los títulos: no se reescribe.")
    return "\n".join(L) + "\n"


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("doc")
    p.add_argument("--a", "--perfil", dest="a", help="perfil destino (apa7, ieee, apa7-base+ieee-citas, ieee-base+apa7-citas); "
                   "`--perfil` es alias; por defecto el `perfil:` de .editorial.yaml")
    p.add_argument("--de", choices=["apa7", "ieee"], help="norma de origen (por defecto, autodetecta)")
    p.add_argument("--out", help="ruta del .docx de salida (por defecto <doc>.<perfil>.docx junto al original)")
    p.add_argument("--sin-red", action="store_true", help="no consultar Crossref (usa solo la caché)")
    p.add_argument("--informe", help="ruta del informe .md")
    p.add_argument("--idioma", help="es-MX | en-US (por defecto, autodetecta)")
    p.add_argument("--json", metavar="RUTA", help="escribe un resumen del resultado (salida, conteos, dictamen del juez) como JSON")
    a = p.parse_args()
    cli.utf8()
    perfil = cli.perfil_por_defecto(p, a.a, a.doc, ignorar_equipo=False)  # `--a` es el perfil de DESTINO: no desautoriza al .editorial.yaml
    res = convertir(a.doc, perfil, a.de, a.out, a.sin_red, a.informe, a.idioma)
    estados = [i["_verificacion"]["estado"] for i in res["items"]]
    juez = res.get("juez") or {}
    cli.escribir_json(a.json, {
        "salida": res["salida"], "origen": res["origen"], "destino": res["destino"], "idioma": res["idioma"],
        "referencias": {e: estados.count(e) for e in ("verificada", "discrepancia", "no-verificada")},
        "citas": {"mapeadas": len(res["citas"]), "no_mapeadas": len(res["no_mapeadas"])},
        "no_citadas": [i["id"] for i in res["no_citadas"]], "rutas": res["rutas"],
        "dictamen": juez.get("dictamen_mecanico"), "conteo": juez.get("conteo"), "hallazgos": juez.get("hallazgos", [])})
    sys.exit(cli.codigo(juez.get("hallazgos", [])))


if __name__ == "__main__":
    main()
