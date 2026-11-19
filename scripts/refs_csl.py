#!/usr/bin/env python3
"""Parser de entradas de lista de referencias (APA 7 o IEEE) a CSL-JSON.

Uso:
  python -I refs_csl.py "Autor, A. (2020). Título. *Revista*, *3*(2), 1-9."          # imprime el CSL-JSON
  python -I refs_csl.py --lista entradas.txt [--norma apa7|ieee] [--sin-red]            # una entrada por párrafo

Importable:
  parsear_entrada(texto, norma=None) -> dict CSL (sin id)
  parsear_lista(entradas, norma=None, red=False) -> list[dict CSL con id y _verificacion]
  detectar_norma(entradas) -> "apa7" | "ieee"

El texto de entrada es Markdown ligero: las cursivas se marcan con *...* (son la pista principal
para distinguir título y contenedor). No inventa metadatos: lo que no reconoce no se rellena y se
anota en _verificacion.notas.
"""
import argparse
import json
import re
import sys
import unicodedata

ESCAPE = ""  # marcador de asterisco literal

MESES = {"enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
         "septiembre": 9, "setiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
         "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6, "july": 7, "august": 8,
         "september": 9, "october": 10, "november": 11, "december": 12,
         "ene": 1, "feb": 2, "mar": 3, "abr": 4, "may.": 5, "jun": 6, "jul": 7, "ago": 8, "sep": 9, "sept": 9,
         "oct": 10, "nov": 11, "dic": 12, "jan": 1, "apr": 4, "aug": 8, "dec": 12}
ESTACIONES = {"winter", "spring", "summer", "fall", "autumn", "invierno", "primavera", "verano", "otoño"}
SIN_FECHA = r"(?:s\.\s?f\.|s/f|n\.\s?d\.|sin fecha|no date)"
INICIAL = r"[A-ZÀ-ÝŁØÅ][a-zà-ÿ]?\."
INICIALES = INICIAL + r"(?:[\s-]*" + INICIAL + r")*"
SUFIJOS = r"(?:Jr\.|Sr\.|II|III|IV)"
CLAVES_CONF = re.compile(r"proceedings|proc\.|conference|conf\.|congreso|conferencia|symposium|symp\.|workshop|"
                         r"actas|annual meeting|convention|international (?:conf|symp)|int\. (?:conf|symp)|"
                         r"coloquio|simposio|jornadas|tech\. dig|preprints|conf\. rec", re.I)
EDITORIALES = re.compile(r"\b(?:press|publish\w*|forlag|editorial\w*|verlag|books|springer|wiley|routledge|sage|longman|"
                         r"mcgraw|elsevier|academic|taylor|harper|penguin|scribner|guilford|oxford|cambridge|"
                         r"pearson|prentice|norton|plenum|basic|hill|ediciones|siglo|fondo de cultura|"
                         r"createspace|bond|house|mit|ltd|inc)\b", re.I)
SERVIDORES_PREPRINT = re.compile(r"^(?:arXiv|PsyArXiv|SSRN|OSF Preprints|bioRxiv|medRxiv|ChemRxiv|SocArXiv|"
                                 r"Research Square|PubMed Central|HAL|Preprints\.org|EdArXiv|engrXiv)\b", re.I)


# ------------------------------------------------------------------ utilidades de texto
def sin_acentos(s):
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def slug(s):
    return re.sub(r"[^a-z0-9]", "", sin_acentos(s).lower())


def limpiar(t):
    """Markdown de pandoc (o de render) -> texto con *cursivas* y signos normales."""
    t = unicodedata.normalize("NFC", re.sub("[\u00a0\u202f\u2009\u200b]", " ", t))
    t = re.sub(r"\[\\?\[(\d+)\\?\]\s*\]\{\.csl-left-margin\}\[(.*)\]\{\.csl-right-inline\}",
               lambda m: f"[{m.group(1)}] " + m.group(2), t, flags=re.S)
    prev = None
    while prev != t:  # spans de pandoc: [txt]{.nocase}
        prev, t = t, re.sub(r"\[([^\[\]]*)\]\{[^}]*\}", r"\1", t)
    t = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", lambda m: m.group(2) if m.group(1).startswith(("http", "www")) else m.group(1), t)
    t = re.sub(r"<(https?://[^>]+)>", r"\1", t)
    t = t.replace("\\*", ESCAPE)
    t = re.sub(r"\\([\\`_{}\[\]()#+\-.!|<>~\"'@$&%:;,=/?^])", r"\1", t)
    t = re.sub(r"\\\s*$", "", t)
    t = t.replace("---", "—").replace("--", "–")
    t = re.sub(r"(?<!\*)\b_([^_]+)_\b", r"*\1*", t)           # _cursiva_ -> *cursiva*
    t = re.sub(r"\*\*([^*]+)\*\*", r"\1", t)                  # negritas fuera
    t = re.sub(r"\*\s+\*", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def sin_marcas(s):
    return s.replace("*", "").replace(ESCAPE, "*")


def restaurar(s):
    return s.replace(ESCAPE, "*")


def parse_fecha(s):
    """Fecha en texto -> CSL date. Devuelve (dict|None, sufijo_anio). Entiende 2026, 14 de octubre / March 22 / Sep. 23, 2024."""
    if not s:
        return None, ""
    s0 = s.strip()
    if re.fullmatch(r"(?:in press|en prensa)", s0, re.I):
        return {"literal": s0}, "ip"
    if re.fullmatch(SIN_FECHA + r"(?:-[a-z])?", s0, re.I):
        m = re.search(r"-([a-z])$", s0)
        return None, ("sf" + (m.group(1) if m else ""))
    my = re.search(r"\b(1[0-9]{3}|20[0-9]{2})([a-z])?\b", s0)
    if not my:
        return {"literal": s0}, ""
    if re.search(r"(?:–|-)\s*(?:present|presente|actualidad)", s0, re.I):
        return {"literal": s0}, ""
    y = int(my.group(1))
    suf = my.group(2) or ""
    rest = s0[:my.start()] + " " + s0[my.end():]
    parts = [y]
    mes = None
    for w in re.findall(r"[A-Za-záéíóúñ\.]+", rest):
        k = w.lower().rstrip(".")
        if k in MESES:
            mes = MESES[k]
            break
        if k in ESTACIONES:
            return {"date-parts": [[y]], "season": w.capitalize()}, suf
    if mes:
        parts.append(mes)
        d = re.search(r"\b(\d{1,2})\b", rest)
        if d and 1 <= int(d.group(1)) <= 31:
            parts.append(int(d.group(1)))
    return {"date-parts": [parts]}, suf


def anio_de(item):
    d = (item.get("issued") or {})
    try:
        return d["date-parts"][0][0]
    except (KeyError, IndexError, TypeError):
        m = re.search(r"\d{4}", d.get("literal", "")) if isinstance(d, dict) else None
        return int(m.group()) if m else None


# ------------------------------------------------------------------ autores
def _persona_dado_primero(tok):
    tok = tok.strip().strip(",")
    if not tok:
        return None
    m = re.match(r"^(" + INICIALES + r")\s*(.+)$", tok)
    if m:
        given, fam = m.group(1).strip(), m.group(2).strip()
    else:
        w = tok.split()
        if len(w) < 2:
            return {"literal": tok}
        part = []
        i = len(w) - 1
        fam = w[i]
        while i > 0 and w[i - 1].lower() in {"de", "la", "del", "van", "von", "der", "da", "di", "le", "du", "y"}:
            i -= 1
            fam = w[i] + " " + fam
        given = " ".join(w[:i])
    ms = re.search(r"\s+(" + SUFIJOS + r")$", fam)
    out = {"family": fam, "given": given}
    if ms:
        out["family"] = fam[:ms.start()]
        out["suffix"] = ms.group(1)
    return out


def personas_dado_primero(s):
    """'R. F. Subotnik, P. Olszewski-Kubilius, & F. C. Worrell' / 'A. B and C. D' -> lista CSL."""
    s = re.sub(r"\s*\bet al\.?\s*$", "", s.strip())
    toks = re.split(r",\s*(?:&|y|and)\s+|\s+&\s+|\s+y\s+|\s+and\s+|,\s+", s)
    out = [p for p in (_persona_dado_primero(t) for t in toks) if p]
    return out


RE_PERSONA_APA = (r"(?P<f>[^,&\[\]()]+?),\s*(?P<g>" + INICIALES + r")(?:,\s*(?P<s>" + SUFIJOS + r"))?")


def autores_apa(a):
    """Bloque de autores APA -> (lista CSL, rol, sigla, omitidos, handle).  Grupo si no encaja en 'Apellido, I.'."""
    a = a.strip()
    rol = None
    sigla = None
    handle = None
    omit = False
    m = re.search(r"\s*\((Eds?\.|Hosts?|Hosted by|Dirs?\.|Directors?|Coords?\.|Coordinadore?s?|Comps?\.|Hosts)\)\.?$", a)
    if m:
        rol = m.group(1).lower()
        a = a[:m.start()].strip()
    a = re.sub(r"\s*\((?:with|con) [^)]*\)\.?$", "", a)
    m = re.search(r"\s*\[(@[^\]]+)\]\.?$", a)
    if m:
        handle = m.group(1)
        a = a[:m.start()].strip()
    m = re.search(r"\s*\[([^\]@]+)\]\.?$", a)
    if m and not re.fullmatch(r"\d+", m.group(1)):
        sigla = m.group(1)
        a = a[:m.start()].strip()
    # personas
    pos, out = 0, []
    s = a if a.endswith(".") else a + "."
    s_ini = s
    while pos < len(s):
        sep = re.match(r"(?:,\s*(?:&|y|and)\s+|\s+&\s+|\s+y\s+|,\s*|\s*)", s[pos:]) if pos else None
        if pos and sep:
            elip = re.match(r",?\s*(?:\.\s?\.\s?\.|…)\s*", s[pos:])
            if elip:
                omit = True
                pos += elip.end()
                sep = None
            else:
                pos += sep.end()
        m = re.compile(RE_PERSONA_APA).match(s, pos)
        if not m:
            out = None
            break
        d = {"family": m.group("f").strip(), "given": m.group("g").strip()}
        if m.group("s"):
            d["suffix"] = m.group("s")
        out.append(d)
        pos = m.end()
        if s[pos:pos + 1] == "." and pos + 1 == len(s):
            pos += 1
    if out:
        return out, rol, sigla, omit, handle
    lit = re.sub(r"\.$", "", a).strip()
    return [{"literal": lit}], rol, sigla, False, handle


# ------------------------------------------------------------------ APA
RE_FECHA_APA = re.compile(
    r"^(?P<au>.+?)\s*\((?P<f>(?:\d{4}[a-z]?|in press|en prensa|" + SIN_FECHA + r")(?:-[a-z])?(?:\s*[–-]\s*(?:\d{4}|present|presente|actualidad))?"
    r"(?:,\s*[^()]+)?)\)\.?\s*(?P<rest>.*)$", re.S | re.I)
RE_ED = r"(?:\d+(?:st|nd|rd|th|\.ª|ª|a|\.ᵃ|º)?\s+(?:digital |anniversary |rev\. |revised |nueva |new )?ed\.|(?:rev\.|revised|nueva|new|\w+)\s+ed\.)"
RE_REVISTA_A1 = re.compile(r"^\*(?P<c>[^*]+)\*,\s*\*(?P<v>[^*]+)\*(?:\((?P<i>[^)]+)\))?(?:,\s*(?P<p>.+?))?\.?$")
RE_REVISTA_A2 = re.compile(r"^\*(?P<c>[^*]+?),\s*(?P<v>[^,*]+)\*(?:\((?P<i>[^)]+)\))?(?:,\s*(?P<p>.+?))?\.?$")
RE_REVISTA_A1B = re.compile(r"^\*(?P<c>[^*]+)\*,\s*\((?P<i>[^)]+)\)(?:,\s*(?P<p>.+?))?\.?$")
RE_PAGINAS = r"(?:Article\s+\S+|Artículo\s+\S+|[A-Za-z]?\d+[\w.]*\s*[–-]\s*[A-Za-z]?[\w.]+|[A-Za-z]?\d+[A-Za-z]?(?:,\s*[A-Za-z]?\d+[A-Za-z]?)*)"


def _pag(p):
    if not p:
        return None
    p = re.sub(r"^(?:pp?\.|págs?\.)\s*", "", p.strip())
    return p.replace("–", "-").replace("—", "-").replace(" - ", "-")


def _es_articulo_num(p):
    return bool(p and re.match(r"^(?:Article|Artículo)\s+", p))


def _poner_pag(it, p):
    p = (p or "").strip().rstrip(".")
    if not p:
        return
    m = re.match(r"^(?:Article|Artículo)\s+(\S+)$", p)
    if m:
        it["number"] = m.group(1)           # CSL: Article eNNN se renderiza con 'number' en artículos
        it["_articulo"] = True
    else:
        it["page"] = _pag(p)


def _parentesis(s):
    """Extrae paréntesis y corchetes consecutivos del inicio de s. -> (parens, brackets, resto)."""
    parens, brackets = [], []
    while True:
        s2 = s.lstrip()
        m = re.match(r"\(((?:[^()]|\([^()]*\))*)\)", s2)
        if m:
            parens.append(m.group(1))
            s = s2[m.end():]
            continue
        m = re.match(r"\[((?:[^\[\]]|\[[^\[\]]*\])*)\]", s2)
        if m:
            brackets.append(m.group(1))
            s = s2[m.end():]
            continue
        break
    return parens, brackets, s.lstrip().lstrip(".").strip()


def _aplicar_parens(it, parens, tipo_pref=None):
    """Interpreta paréntesis tras el título: edición, volúmenes, páginas, editores, número."""
    nums = []
    for p in parens:
        pl = p.strip()
        m = re.fullmatch(r"(?:(\d+)\.?ª|(\d+)(?:st|nd|rd|th|a|ª|º)?|\w+)?\s*(?:digital |anniversary |rev\. |revised )?ed\.", pl, re.I)
        if re.fullmatch(r"(?:\w+\s+)?(?:\d+(?:st|nd|rd|th|\.ª|ª|a|º)?\s+)?(?:digital |anniversary |revised )?ed\.", pl, re.I) or re.fullmatch(r"\d+\S*\s+(?:\w+\s+)?ed\.", pl):
            it["edition"] = re.sub(r"\s*ed\.$", "", pl).strip().replace(".ª", "").replace("ª", "")
            continue
        m = re.fullmatch(r"(?:Vols?\.|Tomos?|Vol\.)\s*(.+)", pl)
        if m:
            it["volume"] = m.group(1)
            continue
        m = re.match(r"^(?P<eds>.+?),\s*(?:Eds?\.|Trads?\.|Trans\.)$", pl)
        if m:
            it["editor"] = personas_dado_primero(m.group("eds"))
            continue
        m = re.fullmatch(r"(?:(?:Original work|Obra original) published\s*)?(\d{4})", pl)
        if m:
            continue
        nums.append(pl)
    if nums:
        raw = "; ".join(nums)
        it["_num_raw"] = raw
        partes = [x.strip() for x in raw.split(";")]
        for x in partes[1:]:
            mv = re.match(r"^(?:Version|Versión)\s+(.+)$", x)
            if mv:
                it["version"] = mv.group(1)
        it["number"] = re.sub(r"^(?:[A-Z][A-Za-z]*\s+)*?(?:Publication|Report|Standard|Informe|Number|Accession)?\s*No\.\s*", "", partes[0])
    return it


def _tipo_por_descriptor(desc):
    d = desc.lower()
    tabla = [
        (r"conjunto de datos|data ?set|^datos$|base de datos|^data$", "dataset"),
        (r"doctoral dissertation|master'?s thesis|tesis|dissertation|thesis", "thesis"),
        (r"conference (?:presentation|paper|session)|ponencia|presentaci[oó]n (?:en|de) congreso|keynote|symposium", "speech"),
        (r"audio podcast|podcast|video|película|film|webinar", "motion_picture"),
        (r"large language model|software|app|aplicaci[oó]n|código|source code|computer program|mobile app", "software"),
        (r"^post$|publicaci[oó]n|\btweet\b|^status update$", "post"),
        (r"profile|perfil|channel|canal", "webpage"),
        (r"generative ai chat|chat", "post"),
    ]
    for pat, t in tabla:
        if re.search(pat, d):
            return t
    return None


def _resto_tras_titulo(rest_after, it):
    """Interpreta el texto tras un título cursivo; decide tipo, editorial, sitio, etc."""
    parens, brackets, rem = _parentesis(rest_after)
    _aplicar_parens(it, parens)
    desc = None
    for b in brackets:
        t = _tipo_por_descriptor(b)
        if t and not desc:
            desc = b
            it["type"] = t
            if t == "thesis":
                m = re.match(r"^(?P<g>[^,]+?),\s*(?P<u>.+)$", b)
                it["genre"] = m.group("g") if m else b
                if m:
                    it["publisher"] = m.group("u")
            else:
                it["genre"] = b
        elif not desc:
            it["genre"] = b
        else:
            it["genre"] = (it.get("genre", "") + "; " + b).strip("; ")
    rem = rem.strip().rstrip(".").strip()
    return rem, desc


def parse_apa(t):
    notas = []
    it = {}
    t = t.strip()
    # colas: obra original / reimpresión / retractación
    for _ in range(3):
        m = re.search(r"\s*\((?:Original work published|Reprinted from|Retraction published|Obra original|Reimpreso de|Retractaci[oó]n)[^\n]*\)\.?$", t)
        if not m:
            break
        cola = m.group(0).strip()
        mo = re.search(r"(?:Original work published|Obra original publicada(?: en)?)\s+(\d{4})", cola)
        if mo:
            it["original-date"] = {"date-parts": [[int(mo.group(1))]]}
        else:
            notas.append("se omitió la nota final: " + sin_marcas(cola)[:80])
        t = t[:m.start()].rstrip()
    # recuperado + url / url / doi
    acc = None
    m = re.search(r"\s*(?:Recuperado(?: el)?\s+(?P<d1>.+?),?\s+de|Retrieved\s+(?P<d2>.+?),?\s+from)\s+(?P<u>\S+)\s*$", t)
    url = None
    if m:
        acc = m.group("d1") or m.group("d2")
        url = m.group("u")
        t = t[:m.start()].rstrip()
    else:
        m = re.search(r"\s*(?P<u>(?:https?://|www\.)\S+)\s*$", t)
        if m:
            url = m.group("u")
            t = t[:m.start()].rstrip()
        else:
            m = re.search(r"\s*doi:\s*(?P<u>10\.\S+)\s*$", t, re.I)
            if m:
                url = "https://doi.org/" + m.group("u")
                t = t[:m.start()].rstrip()
    if url:
        url = sin_marcas(url).rstrip(".,;")
        if url.endswith(")") and url.count("(") < url.count(")"):
            url = url[:-1]
        md = re.match(r"https?://(?:dx\.)?doi\.org/(10\..+)$", url, re.I)
        if md:
            it["DOI"] = md.group(1)
        else:
            it["URL"] = url
    if acc:
        f, _ = parse_fecha(sin_marcas(acc))
        if f:
            it["accessed"] = f
    t = t.rstrip()
    m = RE_FECHA_APA.match(t)
    if not m:
        it.update({"type": "document", "title": sin_marcas(t)})
        notas.append("formato APA no reconocido (sin '(año).'): se conservó el texto como título")
        return it, notas, ""
    au, f, rest = m.group("au"), m.group("f"), m.group("rest").strip()
    fecha, suf = parse_fecha(f)
    if fecha:
        it["issued"] = fecha
    sufijo_anio = suf
    es_ley = bool(re.match(r"^(?:Ley|Código|Constitución|Decreto|Reglamento|Acuerdo|Norma Oficial|Estatuto|Law\b|Act\b|U\.S\. Code|Constitution)", au.strip()))
    autores = None
    if es_ley:
        it["type"] = "legislation"
        titulo = re.sub(r"\.$", "", au.strip())
        ms = re.search(r"\s*\[([^\]]+)\]$", titulo)
        sig = None
        if ms:
            sig = ms.group(1)
            titulo = titulo[:ms.start()]
        it["title"] = restaurar(titulo)
        it["_sigla"] = sig
        rem = sin_marcas_ital = rest
        mi = re.match(r"^\*([^*]+)\*\.?\s*(.*)$", rest)
        if mi:
            it["container-title"] = mi.group(1)
            if mi.group(2).strip().rstrip("."):
                it["publisher"] = mi.group(2).strip().rstrip(".")
        elif rest:
            rr = rest.rstrip(".")
            if re.match(r"^Diario Oficial|^Gaceta|^Boletín|^Periódico Oficial|^Federal Register|^Official Journal", rr):
                it["container-title"] = rr
            else:
                it["publisher"] = rr
        return it, notas, sufijo_anio
    autores, rol, sigla, omit, handle = autores_apa(au)
    if autores:
        if rol and rol.startswith(("ed", "coord")):
            it["editor"] = autores
        elif rol and rol.startswith(("host", "hosted")):
            it["author"] = autores
            it["_rol"] = "host"
        else:
            it["author"] = autores
    if sigla:
        it["_sigla"] = sigla
    if handle:
        it["_handle"] = handle
    if omit:
        it["_omitidos"] = True
    # sin autor: el título ocupa su lugar ("Oil painting. (2019, December 8). In *Wikipedia*.")
    if re.match(r"^(?:In|En)\s+\*", rest) and autores and len(autores) == 1 and "literal" in autores[0] and not rol:
        it.pop("author", None)
        it["title"] = autores[0]["literal"]
        it["_sin_autor"] = True
    parse_apa_resto(rest, it, notas)
    return it, notas, sufijo_anio


def _dividir_coleccion(c):
    m = re.match(r"^(?P<col>.+?):\s*Vol\.\s*(?P<n>\S+?)\.\s+(?P<c>.+)$", c)
    if m:
        return m.group("c"), m.group("col"), m.group("n")
    return c, None, None


def parse_apa_resto(rest, it, notas):
    rest = rest.strip()
    # --- artículo con cursiva de revista: "Título. *Revista*, *3*(2), 1-9."
    m = re.match(r"^(?P<t>.+?)\s+(?P<ital>\*[^*].*)$", rest)
    if m and not re.match(r"^(?:In|En)\s+\*", rest) and not re.search(r"(?<![\w])(?:In|En)$", m.group("t")):
        ti, resto = m.group("t"), m.group("ital")
        # el título termina antes de la cursiva; si la cursiva es "In *..." ya se trató
        for rx in (RE_REVISTA_A1, RE_REVISTA_A1B, RE_REVISTA_A2):
            mm = rx.match(resto)
            if mm:
                gd = mm.groupdict()
                it["type"] = "article-journal"
                it["container-title"] = gd["c"]
                if gd.get("v"):
                    it["volume"] = gd["v"].strip()
                if gd.get("i"):
                    it["issue"] = gd["i"].strip()
                _poner_pag(it, gd.get("p"))
                _titulo_articulo(it, ti)
                return
        mm = re.match(r"^\*(?P<c>[^*]+)\*(?:,\s*(?P<p>[^*]+?))?\.?\s*$", resto)
        if mm and not it.get("title"):
            it["type"] = "article-newspaper" if not it.get("DOI") else "article-journal"
            it["container-title"] = mm.group("c")
            _poner_pag(it, mm.group("p")) if mm.group("p") and re.match(r"^[A-Za-z]?\d", mm.group("p")) else None
            _titulo_articulo(it, ti)
            return
    # --- capítulo / ponencia / entrada: "Título. In Eds (Eds.), *Libro* (pp. 1-2). Editorial."
    m = re.match(r"^(?P<t>.*?)\.?\s*\b(?:In|En)\s+(?:(?P<eds>[^*]+?)\s+\((?:Eds?\.|Coords?\.)\),\s+)?\*(?P<c>[^*]+)\*(?P<resto>.*)$", rest)
    if m and (not it.get("title") or it.get("_sin_autor")):
        ti = m.group("t").strip().rstrip(".")
        if it.get("_sin_autor") and not ti:
            ti = it.pop("title")
        parens, brackets, rem = _parentesis(m.group("resto"))
        c, col, num = _dividir_coleccion(m.group("c"))
        it["container-title"] = c
        if col:
            it["collection-title"] = col
            it["collection-number"] = num
        for p in parens:
            mp = re.match(r"^(?:(?P<ed>.+?),\s*)?(?:pp?\.|págs?\.)\s*(?P<pg>.+)$", p.strip())
            if mp:
                if mp.group("ed"):
                    _aplicar_parens(it, [mp.group("ed")])
                it["page"] = _pag(mp.group("pg"))
                continue
            _aplicar_parens(it, [p])
        if m.group("eds"):
            it["editor"] = personas_dado_primero(m.group("eds"))
        rem = rem.strip().rstrip(".")
        if rem:
            it["publisher"] = rem
        pa, br, rr = _parentesis_final_titulo(ti)
        it["title"] = rr
        generos = list(brackets) + list(br)
        if generos:
            it["genre"] = "; ".join(generos)
        ty = _tipo_por_descriptor(generos[0]) if generos else None
        if pa:
            _aplicar_parens(it, pa)
        cl = c.lower()
        if ty == "motion_picture":
            it["type"] = "broadcast"
            it["medium"] = it.pop("genre", None)
        elif re.search(r"dictionary|diccionario", cl):
            it["type"] = "entry-dictionary"
        elif re.search(r"wikipedia|encyclop|enciclopedia", cl):
            it["type"] = "entry-encyclopedia"
        elif CLAVES_CONF.search(c):
            it["type"] = "paper-conference"
        else:
            it["type"] = "chapter"
        return
    # --- título en cursiva tras la fecha
    m = re.match(r"^\*(?P<t>[^*]+)\*\s*(?P<post>.*)$", rest)
    if m:
        it["title"] = m.group("t").strip().rstrip(".").strip() if not m.group("t").strip().endswith("?") else m.group("t").strip()
        rem, desc = _resto_tras_titulo(m.group("post"), it)
        _clasificar_obra(it, rem, desc)
        return
    # --- título en cursiva con descriptores dentro: "Título *[desc]"
    # --- sin cursivas: artículo plano "Título. Revista, 7(4), Article e21161."
    m = re.match(r"^(?P<t>.+)\.\s+(?P<c>[^.]+?),\s*(?P<v>\d+)(?:\((?P<i>[^)]+)\))?,\s*(?P<p>" + RE_PAGINAS + r")\.?$", rest)
    if m:
        it["type"] = "article-journal"
        it["container-title"] = m.group("c").strip()
        it["volume"] = m.group("v")
        if m.group("i"):
            it["issue"] = m.group("i")
        _poner_pag(it, m.group("p"))
        _titulo_articulo(it, m.group("t"))
        return
    # --- sin cursivas: título + sitio
    pa, br, rr = _parentesis_final_titulo(rest) if False else (None, None, None)
    mt = re.match(r"^(?P<t>.+?)(?P<d>(?:\s*\[[^\]]+\])*)\s*(?:[.?!])\s+(?P<s>[^\[].*)$", rest) or re.match(r"^(?P<t>.+?)(?P<d>(?:\s*\[[^\]]+\])*)\s*\.?$", rest)
    if mt:
        titulo = mt.group("t").strip()
        sitio = (mt.groupdict().get("s") or "").strip().rstrip(".")
        if mt.group("d").strip():
            it["genre"] = "; ".join(re.findall(r"\[([^\]]+)\]", mt.group("d")))
            ty = _tipo_por_descriptor(it["genre"])
            if ty:
                it["type"] = ty
        pa, br, tt = _parentesis_final_titulo(titulo)
        it["title"] = tt
        if pa:
            _aplicar_parens(it, pa)
        if re.search(r"[?!]$", rest.split(".")[0]) and False:
            pass
        _clasificar_obra(it, sitio, it.get("genre"))
        return
    it["title"] = sin_marcas(rest)
    it.setdefault("type", "document")
    notas.append("no se pudo separar título y contenedor")


def _parentesis_final_titulo(ti):
    """Separa '(Accession No. 1)' y '[Monograph]' al final de un título plano -> (parens, brackets, titulo)."""
    pa, br = [], []
    ti = ti.strip()
    if not ti.endswith(("?.", "!.")):
        ti = re.sub(r"(?<=[\]\)])\.$", "", ti)
    while True:
        m = re.search(r"\s*\[([^\[\]]+)\]\s*$", ti)
        if m:
            br.insert(0, m.group(1))
            ti = ti[:m.start()]
            continue
        m = re.search(r"\s*\(((?:[^()]|\([^()]*\))*)\)\s*$", ti)
        if m and re.search(r"No\.|ISO|ICPSR|ED\d|Accession|Report|Publication|Vol|ed\.|Eds?\.|[A-Z]{2,}[ -]\d", m.group(1)):
            pa.insert(0, m.group(1))
            ti = ti[:m.start()]
            continue
        break
    return pa, br, sin_marcas(ti).strip().rstrip(".") if not ti.rstrip().endswith(("?", "!", "”", '"')) else sin_marcas(ti).strip()


def _titulo_articulo(it, ti):
    pa, br, tt = _parentesis_final_titulo(ti)
    it["title"] = tt
    if br:
        it["genre"] = "; ".join(br)
    if pa:
        it["number"] = it.get("number") or "; ".join(pa)
        it.pop("_articulo", None) if False else None
    if it.get("_articulo") and pa:
        it["_numero_extra"] = "; ".join(pa)
        it.pop("number", None)
        it["number"] = it.pop("_numero_extra")


def _clasificar_obra(it, resto, desc):
    """Con título (cursiva) y lo que sigue ('resto' = editorial/sitio) decide el tipo."""
    resto = (resto or "").strip().rstrip(".").strip()
    num = it.get("_num_raw") or it.get("number") or ""
    ty = it.get("type")
    if ty in ("thesis", "dataset", "speech", "motion_picture", "software", "post"):
        if ty == "thesis":
            if resto:
                it["archive"] = resto if it.get("publisher") else it.get("archive")
                if not it.get("publisher"):
                    it["publisher"] = resto
        elif ty == "speech":
            if resto:
                it["event-title"] = resto
        elif resto:
            it["publisher" if ty in ("dataset", "software", "motion_picture") else "container-title"] = resto
        if ty == "post" and resto:
            it["container-title"] = it.pop("container-title", resto)
        return
    if ty == "webpage":
        if resto:
            it["container-title"] = resto
        return
    if resto and SERVIDORES_PREPRINT.match(resto):
        it["type"] = "article"
        it["publisher"] = resto
        return
    if re.search(r"ISO|IEC|IEEE Std|Standard No|OSHA|ANSI|NIST SP|Norma|NOM-|UNE", num) and re.search(r"Standard|ISO|IEC|Norma|NOM", num):
        it["type"] = "standard"
        if resto:
            it["publisher"] = resto
        return
    if re.search(r"Report|Informe|Publication|Technical|Working Paper|White Paper|NIST|ED\d{4,}|^[A-Z]+[ -]\d", num):
        it["type"] = "report"
        if resto:
            it["publisher"] = resto
        return
    if it.get("edition") or it.get("number-of-volumes") or it.get("volume"):
        it["type"] = "book"
        if resto:
            it["publisher"] = resto
        return
    url = it.get("URL")
    fecha = it.get("issued") or {}
    dp = (fecha.get("date-parts") or [[]])[0] if isinstance(fecha, dict) else []
    detallada = len(dp) >= 2 or bool(it.get("accessed")) or (isinstance(fecha, dict) and "season" in fecha)
    if not resto:
        it["type"] = "webpage" if url else "book"
        return
    if EDITORIALES.search(resto) and not url or (EDITORIALES.search(resto) and it.get("DOI")):
        it["type"] = "book"
        it["publisher"] = resto
        return
    if url and not EDITORIALES.search(resto):
        if detallada or not fecha or "issued" not in it:
            it["type"] = "webpage"
            it["container-title"] = resto
        else:
            it["type"] = "report"
            it["publisher"] = resto
        return
    if it.get("DOI") and not EDITORIALES.search(resto):
        it["type"] = "book"
        it["publisher"] = resto
        return
    it["type"] = "book"
    it["publisher"] = resto


# ------------------------------------------------------------------ IEEE
RE_ONLINE = re.compile(r"\s*\[(?:Online|En línea)(?: Video)?\.?\]\.?\s*(?:(?:Available|Disponible en)\s*:?\s*)?(?P<u>\S*)\s*$", re.I)
RE_DISP = re.compile(r"\s*(?:Available|Disponible en)\s*:\s*(?P<u>\S+)\s*$", re.I)
RE_ACC = re.compile(r"\s*(?:Accessed|Consultado|Accedido|Visitado)\s*:?\s+(?P<d>[A-Za-zñáéíóú]+\.?\s+\d{1,2},\s+\d{4}|\d{1,2}\s+[A-Za-z]+\.?\s+\d{4}|[A-Za-z]+\.?\s+\d{4})\.?")
MESES_ABR = r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec|ene|abr|ago|dic)\.?"
RE_FECHA_IEEE = re.compile(r"(?:(?P<mes>" + MESES_ABR + r"|January|February|March|April|June|July|August|September|October|November|December|[A-Za-z]{4,9})\s+)?(?:(?P<d>\d{1,2})(?:[–-]\d{1,2})?,\s+)?(?P<y>(?:1[5-9]|20)\d{2})\b")


def _fecha_ieee(s):
    m = RE_FECHA_IEEE.search(s)
    if not m:
        return None
    mes = m.group("mes")
    if mes and mes.lower().rstrip(".") not in MESES and mes.lower() not in ESTACIONES:
        mes = None
    parts = [int(m.group("y"))]
    if mes and mes.lower().rstrip(".") in MESES:
        parts.append(MESES[mes.lower().rstrip(".")])
        if m.group("d"):
            parts.append(int(m.group("d")))
    return {"date-parts": [parts]}


def _cierre_comillas(s):
    """Índice del cierre del título entrecomillado que empieza en s[0]."""
    if s[0] == "“":
        d = 0
        for i, ch in enumerate(s):
            if ch == "“":
                d += 1
            elif ch == "”":
                d -= 1
                if d == 0:
                    return i
        return -1
    for m in re.finditer(r'"', s[1:]):
        i = m.start() + 1
        if re.match(r'(?:[,.]|\s|$)', s[i + 1:i + 2] or " ") and s[i - 1] not in " ":
            return i
    return -1


def autores_ieee(a):
    a = a.strip().rstrip(",").strip()
    rol = None
    etal = False
    m = re.search(r",?\s*\b(Eds?\.|Ed\.)$", a)
    if m:
        rol = "editor"
        a = a[:m.start()].strip().rstrip(",")
    m = re.search(r",?\s*(?:\*et al\.\*|et al\.)\s*$", a)
    if m:
        etal = True
        a = a[:m.start()].strip().rstrip(",")
    a = sin_marcas(a)
    if not a:
        return [], rol, etal
    toks = re.split(r",\s*(?:and|y)\s+|\s+(?:and|y)\s+|,\s+", a)
    if all(re.match(r"^(?:" + INICIALES + r")\s*\S", t.strip()) for t in toks):
        return personas_dado_primero(a), rol, etal
    return [{"literal": a}], rol, etal


def parse_ieee(t):
    notas = []
    it = {}
    t = re.sub(r"^\[\d+\]\s*", "", t.strip())
    t = re.sub(r"\*et al\.?\*", "et al.", t)
    # DOI, URL, accedido
    md = re.search(r",?\s*doi:\s*(?P<d>10\.[^\s,]+?)[.,]?(?=\s|$)", t, re.I)
    if md:
        it["DOI"] = md.group("d").rstrip(".")
        t = t[:md.start()] + t[md.end():]
    mo = RE_ONLINE.search(t) or RE_DISP.search(t)
    if mo:
        u = sin_marcas(mo.group("u")).rstrip(".,")
        if u:
            mdoi = re.match(r"https?://(?:dx\.)?doi\.org/(10\..+)$", u)
            if mdoi and "DOI" not in it:
                it["DOI"] = mdoi.group(1)
            elif not mdoi:
                it["URL"] = u
        medio = re.search(r"\[((?:Online|En línea) Video)\]", mo.group(0), re.I)
        if medio:
            it["medium"] = "Online Video"
        t = t[:mo.start()].rstrip()
    ma = RE_ACC.search(t)
    if ma:
        f = _fecha_ieee(ma.group("d")) or parse_fecha(ma.group("d"))[0]
        if f:
            it["accessed"] = f
        t = (t[:ma.start()] + t[ma.end():]).strip()
    t = t.strip().rstrip(".").strip()
    # comunicación personal
    mc = re.match(r"^(?P<a>.+?),\s*(?:private|personal) communication(?:,\s*(?P<d>.+))?$", t, re.I)
    if mc:
        it["type"] = "personal_communication"
        autores, rol, etal = autores_ieee(mc.group("a"))
        it["author"] = autores
        f = _fecha_ieee(mc.group("d") or "")
        if f:
            it["issued"] = f
        return it, notas, ""
    # autores y título
    iq = min([i for i in (t.find("“"), t.find('"')) if i >= 0], default=-1)
    au, ti, tail = "", None, ""
    termina_punto = False
    if iq >= 0:
        j = _cierre_comillas(t[iq:])
        if j > 0:
            au = t[:iq].rstrip(" ,")
            ti_raw = t[iq + 1:iq + j]
            tail = t[iq + j + 1:].lstrip(" ,.")
            termina_punto = ti_raw.rstrip().endswith(".")
            ti = ti_raw.rstrip(" ")
            if not ti.endswith(("?", "!")):
                ti = ti.rstrip(",.")
    cursiva_titulo = False
    if ti is None:
        m = re.match(r"^(?P<a>.*?)(?:,\s*|\.\s+|\s+)?\*(?P<t>[^*]+)\*(?P<tail>.*)$", t)
        if m:
            au, ti, tail = m.group("a").strip().rstrip(","), m.group("t").strip(), m.group("tail").lstrip(" ,.")
            cursiva_titulo = True
        else:
            it.update({"type": "document", "title": sin_marcas(t.rstrip("."))})
            notas.append("formato IEEE no reconocido")
            return it, notas, ""
    if au:
        autores, rol, etal = autores_ieee(au)
        if autores:
            it["editor" if rol == "editor" else "author"] = autores
        if etal:
            it["_etal"] = True
    it["title"] = sin_marcas(ti)
    parse_ieee_cola(it, tail, notas, cursiva_titulo, termina_punto)
    return it, notas, ""


def _quitar(rx, s, it=None, key=None, grupo=1):
    m = rx.search(s)
    if not m:
        return s, None
    val = m.group(grupo)
    return (s[:m.start()] + s[m.end():]), val


RE_FIN_FECHA = r"(?:" + MESES_ABR + r"\s+)?(?:\d{1,2}(?:[–-]\d{1,2})?,\s+)?(?:1[5-9]|20)\d{2}\.?"


def parse_ieee_cola(it, tail, notas, cursiva_titulo=False, termina_punto=False):
    s = tail.strip()
    # campos sueltos
    s, vol = _quitar(re.compile(r",?\s*\bvol\.\s*([A-Za-z]*-?\d+[\w-]*)"), s)
    s, num = _quitar(re.compile(r",?\s*\bno\.\s*(\d+[\w-]*)"), s)
    s, art = _quitar(re.compile(r",?\s*\bArt(?:\.|icle)?\s*no\.?\s*(\S+?)(?=,|\s|$)", re.I), s)
    s, pt = _quitar(re.compile(r",?\s*\bpt\.\s*(\w+)"), s)
    s, cap = _quitar(re.compile(r",?\s*\bch\.\s*(\w+)"), s)
    s, pag = _quitar(re.compile(r",?\s*(?<![A-Za-z])pp?\.\s*(?=[A-Za-z]?\d)([A-Za-z]?[\d.]+(?:\s*[–-]\s*[A-Za-z]?[\d.]+)*[\w-]*)"), s)
    s, ed = _quitar(re.compile(r",?\s*\b(\d+(?:st|nd|rd|th)\s+ed\.)"), s)
    if not ed:
        s, ed = _quitar(re.compile(r",?\s*\b(\d+\.ª\s+ed\.|\d+a\s+ed\.)"), s)
    s, publicar = _quitar(re.compile(r",?\s*(to be published|early access|submitted for publication|unpublished|in press)\b", re.I), s)
    if vol:
        it["volume"] = vol
    if num:
        it["issue"] = num
    if art:
        it["number"] = art.rstrip(".,")
        it["_articulo"] = True
    if pt:
        it["_parte"] = pt
    if cap:
        it["chapter-number"] = cap
    if pag:
        it["page"] = _pag(pag)
    if ed:
        it["edition"] = re.sub(r"\s*ed\.$", "", ed).replace(".ª", "").replace("ª", "")
    if publicar:
        it["status"] = publicar.lower()
    s = s.strip().strip(",.").strip()
    sin_url = re.sub(r"https?://\S+", "", s)

    # --- patente
    if not cursiva_titulo and re.search(r"\bPatent\b", s):
        mpat = re.search(r"Patent\s*(?P<n>(?:Appl\.\s|Utility Model\s)?(?:[A-Z]{1,2}\s)?\d[\d ]*(?:,\d{3})*(?:\s?[A-Z]\d)?)", s)
        it["type"] = "patent"
        if mpat:
            it["number"] = mpat.group("n").strip()
        f = _fecha_ieee(s[mpat.end():] if mpat else s)
        if f:
            it["issued"] = f
        return

    # --- contenedor en cursiva: revista, capítulo, ponencia, blog, periódico
    mc = re.match(r"^(?:(?P<in>in|en)\s+)?\*(?P<c>[^*]+)\*[,.]?\s*(?P<r>.*)$", s, re.I)
    if mc and not cursiva_titulo:
        cont = mc.group("c").strip().rstrip(",.")
        resto = mc.group("r").strip()
        en = bool(mc.group("in"))
        it["container-title"] = cont
        me = re.match(r"^(?P<e>[^:]+?),\s*Eds?\.,?\s*(?P<r>.*)$", resto)
        if me and re.match(r"^(?:" + INICIALES + r")", me.group("e").strip()):
            it["editor"] = personas_dado_primero(me.group("e"))
            resto = me.group("r").strip()
        resto_sin_url = re.sub(r"https?://\S+", "", resto)
        f = _fecha_ieee(resto_sin_url) if resto_sin_url else None
        mp = re.match(r"^(?P<lug>[^:]+?):\s*(?P<pub>[^,]+?)(?:,\s*(?P<f>.*))?$", resto_sin_url)
        if mp and not re.match(r"^\d", resto_sin_url):
            it["publisher-place"] = mp.group("lug").strip()
            it["publisher"] = mp.group("pub").strip()
            f = _fecha_ieee(mp.group("f") or "") or f
        elif en and resto_sin_url:
            # "Hiroshima, Japan, 2013" / "Noordwijk, ..., Oct. 2014": lugar antes de la fecha
            mlug = re.match(r"^(?P<lug>.+?),\s*" + RE_FIN_FECHA + r"$", resto_sin_url)
            if mlug and not re.match(r"^" + RE_FIN_FECHA, resto_sin_url):
                it["event-place"] = mlug.group("lug").strip()
        if f:
            it["issued"] = f
        if en:
            it["type"] = "paper-conference" if CLAVES_CONF.search(cont) else "chapter"
        elif it.get("volume") or it.get("page") or it.get("number") or it.get("status") or it.get("DOI") or it.get("issue"):
            it["type"] = "article-journal"
        elif re.search(r"blog", cont, re.I):
            it["type"] = "post-weblog"
        elif not f and (it.get("URL") or it.get("accessed")):
            it["type"] = "webpage"
        else:
            it["type"] = "article-newspaper"
        return

    # --- ponencia presentada
    mp = re.match(r"^(?:presented at the|presentado en)\s+(?P<ev>.*)$", s, re.I)
    if mp:
        it["type"] = "speech"
        r = mp.group("ev")
        mpaper = re.search(r",?\s*Paper\s+(\S.*)$", r)
        if mpaper:
            it["number"] = mpaper.group(1).strip(" .")
            r = r[:mpaper.start()]
        f = _fecha_ieee(r)
        if f:
            it["issued"] = f
        partes = [x.strip() for x in re.split(r",\s*", r)]
        ev = []
        for x in partes:
            if ev and (re.match(r"^(?:" + MESES_ABR + r")\s*\d|^(?:1[5-9]|20)\d{2}$|^(?:" + MESES_ABR + r")\s+\d", x)):
                break
            ev.append(x)
        it["event-title"] = ev[0] if ev else r
        if len(ev) > 1:
            it["event-place"] = ", ".join(ev[1:])
        return

    # --- tesis
    mt = re.match(r"^(?P<g>Ph\.D\. (?:dissertation|thesis)|M\.S\. thesis|M\.Sc\. thesis|Master’s thesis|Master's thesis|Tesis[^,]*)(?:,\s*)?(?P<r>.*)$", s)
    if mt:
        it["type"] = "thesis"
        it["genre"] = mt.group("g")
        r = mt.group("r").strip()
        f = _fecha_ieee(r)
        if f:
            it["issued"] = f
        piezas = [x.strip() for x in re.split(r",\s*", re.sub(RE_FIN_FECHA + "$", "", r)) if x.strip()]
        univ = next((x for x in piezas if re.search(r"Univ|Inst|College|School|Tech", x)), None)
        if univ:
            it["publisher"] = univ
        return

    # --- arXiv y documentos de repositorio
    marx = re.search(r"arXiv:\s*(\S+?)\*?$", s)
    if marx:
        it["type"] = "article"
        it["number"] = marx.group(1)
        it["publisher"] = "arXiv"
        f = _fecha_ieee(s[:marx.start()])
        if f:
            it["issued"] = f
        return
    mrep = re.search(r"(?:^|,\s*)(?P<p>[^,]+?),\s*(?P<n>Paper\s+\S+)$", s)
    if mrep and not cursiva_titulo:
        it["type"] = "report"
        it["publisher"] = mrep.group("p")
        it["number"] = mrep.group("n")
        return
    # --- informe técnico: "Empresa, Ciudad, Tech. Rep. N, fecha"
    mr = re.search(r"(?:^|,\s*)(?P<g>(?:Tech\.|Sci\.|Final|Interim)?\s*(?:Rep\.|Memo\.|Report)|White Paper|Tech\. Ser\.|R Package Version)\s*(?P<n>[^,]*)", s)
    if mr and not cursiva_titulo:
        it["type"] = "report"
        it["genre"] = mr.group("g").strip()
        it["number"] = mr.group("n").strip()
        pre = s[:mr.start()].strip(" ,")
        f = _fecha_ieee(s[mr.end():])
        if f:
            it["issued"] = f
        piezas = [x.strip() for x in re.split(r",\s*", pre) if x.strip()]
        if piezas:
            it["publisher"] = piezas[0]
            if len(piezas) > 1:
                it["publisher-place"] = ", ".join(piezas[1:])
        return

    # --- título en cursiva (libro, norma, software, ley) o título entrecomillado sin contenedor
    if cursiva_titulo:
        msw = re.match(r"^\((?P<y>(?:1[5-9]|20)\d{2})\)\.?\s*(?P<p>[^.]*)\.?$", sin_url.strip())
        if msw:
            it["type"] = "software"
            it["issued"] = {"date-parts": [[int(msw.group("y"))]]}
            if msw.group("p").strip():
                it["publisher"] = msw.group("p").strip()
            return
        mestb = re.search(r"(Rec\. ITU[\w .-]+|IEEE Standard \S+|ANSI Standard \S+|NERC Reliability Standard \S+)", sin_url)
        if mestb:
            it["type"] = "standard"
            it["number"] = mestb.group(1).strip(" ,.")
            resto = sin_url.replace(mestb.group(1), "")
            f = _fecha_ieee(resto)
            if f:
                it["issued"] = f
            piezas = [x.strip(" .") for x in resto.split(",") if x.strip(" .") and not re.match(r"^" + RE_FIN_FECHA + r"$", x.strip())]
            if piezas:
                it["publisher"] = piezas[0]
            return
        mpb = re.match(r"^(?P<lug>[^:]+?):\s*(?P<pub>[^,]+?)(?:,\s*(?P<r>.*))?$", sin_url)
        if mpb and re.search(r"[A-Z]{2}|USA|U\.K\.|Japan|Canada|Germany|Australia|Croatia|India|China|France|Mexico", mpb.group("lug")):
            it["type"] = "book"
            it["publisher-place"] = mpb.group("lug").strip()
            it["publisher"] = mpb.group("pub").strip()
            f = _fecha_ieee(mpb.group("r") or "")
            if f:
                it["issued"] = f
            return
        f = _fecha_ieee(sin_url)
        if f:
            it["issued"] = f
        if it.get("medium") == "Online Video":
            it["type"] = "motion_picture"
            return
        if re.search(r"\bvol\.", tail) or it.get("volume") or (re.search(r"\b(?:Code|Act)\b", it.get("title", "")) and not it.get("author")):
            it["type"] = "legal_case" if re.search(r"\bv\.\s", it.get("title", "")) else "legislation"
            return
        piezas = [x.strip() for x in re.split(r",\s*", re.sub(RE_FIN_FECHA + "$", "", sin_url.strip().rstrip("."))) if x.strip()]
        it["type"] = "book"
        if piezas:
            if not it.get("author"):
                it["author"] = [{"literal": piezas[0]}]
                piezas = piezas[1:]
            if piezas:
                it["publisher"] = piezas[0] if not re.search(r"[A-Z]{2}$|USA|U\.K\.", piezas[0]) else it["author"][0].get("literal", piezas[0])
        return
    f = _fecha_ieee(sin_url)
    if f:
        it["issued"] = f
    resto_pub = re.sub(RE_FIN_FECHA + "$", "", sin_url.strip().rstrip(".")).strip(" ,.")
    if termina_punto and resto_pub and resto_pub[0].isupper():
        it["type"] = "dataset"
        piezas = [x.strip() for x in re.split(r",\s*", resto_pub) if x.strip()]
        it["publisher"] = piezas[0]
        return
    if it.get("URL") or it.get("accessed"):
        it["type"] = "webpage"
        if resto_pub:
            it["container-title"] = re.split(r"[.,]\s+", resto_pub)[0]
    elif resto_pub:
        it["type"] = "report"
        it["publisher"] = resto_pub.split(",")[0]
    else:
        it["type"] = "manuscript" if it.get("status") in ("unpublished", "submitted for publication") else "webpage"
    if it.get("type") == "document":
        notas.append("tipo no determinado")


# ------------------------------------------------------------------ detección y API
def detectar_norma(entradas):
    n_ieee = n_apa = 0
    for e in entradas:
        e = e.strip()
        if re.match(r"^\[\\?\[?\d+\\?\]", e) or re.match(r"^\[\d+\]", e):
            n_ieee += 1
        elif RE_FECHA_APA.match(re.sub(r"\s*https?://\S+\s*$", "", e)):
            n_apa += 1
        elif "“" in e and "vol." in e:
            n_ieee += 1
    return "ieee" if n_ieee > n_apa else "apa7"


def parsear_entrada(texto, norma=None):
    t = limpiar(texto)
    norma = norma or detectar_norma([t])
    if norma == "ieee":
        it, notas, suf = parse_ieee(t)
    else:
        it, notas, suf = parse_apa(t)
    it = {k: v for k, v in it.items() if v not in (None, "", [], {})}
    it["_notas"] = notas
    it["_sufijo"] = suf
    it["_original"] = restaurar(re.sub(r"^\[\d+\]\s*", "", sin_marcas_cursiva(t)))
    return _finalizar(it, norma)


def sin_marcas_cursiva(t):
    return t.replace("*", "")


def _finalizar(it, norma):
    for k in ("title", "container-title", "publisher", "genre", "event-title", "collection-title"):
        if k in it and isinstance(it[k], str):
            it[k] = restaurar(it[k])
    it["_articulo_no"] = it.pop("_articulo", False)
    if it["_articulo_no"] and it.get("type") == "article-journal":
        pass
    return it


def _base_id(it):
    au = (it.get("author") or it.get("editor") or [])
    sig = it.get("_sigla")
    if au:
        a = au[0]
        base = slug(sig) if sig and "literal" in a else slug(a.get("family") or " ".join(a.get("literal", "").split()[:3]))
        if "literal" in a and not sig:
            base = slug("".join(w[:8] for w in a["literal"].split()[:3]))
    else:
        base = slug("".join(w[:8] for w in it.get("title", "ref").split()[:2]))
    a_ = anio_de(it)
    suf = it.get("_sufijo", "")
    return (base or "ref") + (str(a_) if a_ else (suf[:2] if suf.startswith("sf") else "sf")) + (suf[2:] if suf.startswith("sf") else suf)


def asignar_ids(items):
    usados = set()
    for it in items:
        b = _base_id(it)
        i, cand = 0, b
        while cand in usados:
            i += 1
            cand = b + chr(ord("a") + (i - 1) % 26) + (str(i // 26) if i > 25 else "")
        usados.add(cand)
        it["id"] = cand
    return items


def parsear_lista(entradas, norma=None, red=False, buscar_doi=None, solo_cache=False):
    """entradas: lista de textos (markdown ligero). Devuelve items CSL con id y _verificacion."""
    limpias = [limpiar(e) for e in entradas]
    norma = norma or detectar_norma(limpias)
    items = []
    for e in entradas:
        try:
            it = parsear_entrada(e, norma)
        except Exception as ex:  # noqa: BLE001 - un fallo de una entrada no tumba la lista
            it = {"type": "document", "title": sin_marcas(limpiar(e)), "_notas": [f"error del parser: {ex}"], "_sufijo": "",
                  "_original": limpiar(e)}
        it["_norma"] = norma
        items.append(it)
    asignar_ids(items)
    for it in items:
        verificar(it, red=red, buscar_doi=buscar_doi, solo_cache=solo_cache)
    return items


# ------------------------------------------------------------------ verificación
def _norm_titulo(s):
    return re.sub(r"[^a-z0-9]", "", sin_acentos(s or "").lower())


def _primer_apellido(it):
    au = it.get("author") or it.get("editor") or []
    if not au:
        return ""
    return slug(au[0].get("family") or au[0].get("literal") or "")


def coincide(a, b):
    """Compara parser (a) con Crossref (b): título, año, primer autor. -> (ok, motivos)"""
    import difflib
    motivos = []
    ta, tb = _norm_titulo(a.get("title")), _norm_titulo(re.sub(r"<[^>]+>", "", b.get("title") if isinstance(b.get("title"), str) else (b.get("title") or [""])[0]))
    if ta and tb:
        r = difflib.SequenceMatcher(None, ta, tb).ratio()
        if not (r >= 0.85 or (len(ta) > 15 and (ta in tb or tb in ta))):
            motivos.append(f"título distinto (similitud {r:.2f}): «{a.get('title')}» vs Crossref «{b.get('title')}»")
    ya, yb = anio_de(a), anio_de(b)
    if ya and yb and abs(ya - yb) > 1:
        motivos.append(f"año distinto: {ya} vs Crossref {yb}")
    fa, fb = _primer_apellido(a), _primer_apellido(b)
    if fa and fb and fa != fb and not (fa in fb or fb in fa):
        motivos.append(f"primer autor distinto: {fa} vs Crossref {fb}")
    return not motivos, motivos


TIPOS_CROSSREF = {"journal-article": "article-journal", "proceedings-article": "paper-conference", "book-chapter": "chapter",
                  "posted-content": "article", "monograph": "book", "edited-book": "book", "book": "book",
                  "report": "report", "dataset": "dataset", "dissertation": "thesis", "reference-entry": "entry-encyclopedia",
                  "standard": "standard", "reference-book": "book", "book-section": "chapter", "peer-review": "review"}


def normalizar_crossref(d):
    """Respuesta de doi.org (CSL o JSON nativo de Crossref) -> CSL-JSON limpio."""
    out = {}
    for k, v in d.items():
        if k in ("title", "container-title", "publisher", "volume", "issue", "page", "edition", "number") and isinstance(v, list):
            v = v[0] if v else None
        out[k] = v
    out["type"] = TIPOS_CROSSREF.get(out.get("type"), out.get("type"))
    for k in ("author", "editor"):
        if isinstance(out.get(k), list):
            out[k] = [{kk: vv for kk, vv in p.items() if kk in ("family", "given", "literal", "suffix", "dropping-particle", "non-dropping-particle")} for p in out[k]]
    if not out.get("issued"):
        for k in ("published", "published-print", "published-online", "created"):
            if isinstance(out.get(k), dict) and out[k].get("date-parts"):
                out["issued"] = out[k]
                break
    if isinstance(out.get("title"), str):
        out["title"] = re.sub(r"<[^>]+>", "", out["title"]).strip()
    return out


CLAVES_CROSSREF = {"type", "title", "author", "editor", "issued", "container-title", "volume", "issue", "page",
                   "publisher", "DOI", "URL", "edition", "number", "ISBN", "ISSN", "event-title", "publisher-place",
                   "collection-title", "collection-number", "genre", "language", "accessed"}


def _clave_anio(it, suf):
    if suf == "ip":
        return "ip"
    if suf.startswith("sf"):
        return "sf" + ("-" + suf[2:] if suf[2:] else "")
    y = anio_de(it)
    return f"{y}{suf}" if y else "sf"


def verificar(it, red=False, buscar_doi=None, solo_cache=False):
    v = {"metodo": "parser", "estado": "no-verificada", "notas": list(it.pop("_notas", []))}
    v["sigla"] = it.pop("_sigla", None)
    v["sufijo"] = it.pop("_sufijo", "")
    v["original"] = it.pop("_original", "")
    v["norma"] = it.pop("_norma", None)
    v["etal"] = it.pop("_etal", False)
    for k in [k for k in it if k.startswith("_") and k != "_verificacion"]:
        v[k.lstrip("_")] = it.pop(k)
    # nombres tal como se escriben en el documento (las citas del texto se buscan con ellos, no con los de Crossref)
    v["apellidos_texto"] = [pp.get("family") or pp.get("literal") or "" for pp in (it.get("author") or it.get("editor") or it.get("host") or [])]
    v["clave_anio"] = _clave_anio(it, v["sufijo"])
    doi = it.get("DOI")
    if doi and red:
        try:
            if buscar_doi is None:
                from doi_csl import csl_por_doi as buscar_doi  # noqa: PLC0415
            cr = buscar_doi(doi)
            cr = normalizar_crossref(cr) if cr else None
        except Exception as ex:  # noqa: BLE001
            cr = None
            v["notas"].append(f"Crossref no respondió ({type(ex).__name__}); sin verificar")
        if cr:
            ok, motivos = coincide(it, cr)
            if ok:
                # El documento manda en título, contenedor, año y tipo (capitalización APA, abreviaturas); Crossref completa
                # lo que falta (volumen, número, páginas, editorial, autores truncados con "et al.", etc.).
                limpio = {k: val for k, val in cr.items() if k in CLAVES_CROSSREF and val not in (None, "", [], {})}
                if "doi.org" in str(limpio.get("URL", "")):
                    limpio.pop("URL")
                base = {k: val for k, val in it.items() if not k.startswith("_")}
                aus_cr = limpio.get("author") or []
                aus_it = base.get("author") or []
                if aus_cr and (not aus_it or v.get("etal") or v.get("omitidos") or len(aus_it) < len(aus_cr)):
                    if all((x.get("family") or x.get("literal") or "").isupper() for x in aus_cr):
                        aus_cr = [{**x, **{k2: x[k2].title() for k2 in ("family", "given") if x.get(k2) and x[k2].isupper()}} for x in aus_cr]
                    base["author"] = aus_cr
                    v["notas"].append("autores completados con Crossref")
                for k, val in limpio.items():
                    if k in base or k in ("author", "type", "issued") and (k in base):
                        continue
                    if k == "page" and (base.get("number") or v.get("articulo_no")):
                        continue
                    if k == "publisher" and (base.get("author") or [{}])[0].get("literal"):
                        continue        # autor institucional: la editorial suele ser la misma y Crossref la escribe distinto
                    if k == "title" and isinstance(val, str) and val.isupper():
                        continue
                    base[k] = val
                if base.get("type") in (None, "document"):
                    base["type"] = limpio.get("type", "document")
                for campo in ("issued", "accessed"):
                    if isinstance(base.get(campo), dict) and base[campo].get("date-parts"):
                        base[campo] = {**base[campo], "date-parts": [[x for x in dp if x is not None] for dp in base[campo]["date-parts"]]}
                it.clear()
                it.update(base)
                v.update(metodo="doi-crossref", estado="verificada")
            else:
                v.update(metodo="doi-crossref", estado="discrepancia")
                v["notas"] += motivos
                v["notas"].append("se conservó el texto del documento; revisar el DOI " + doi)
        elif not any("Crossref no respondió" in n for n in v["notas"]):
            v.update(metodo="doi-crossref", estado="no-verificada")
            v["notas"].append(f"el DOI {doi} no está en la caché (modo --sin-red)" if solo_cache else f"el DOI {doi} no se resolvió en Crossref")
    elif doi:
        v["notas"].append("con DOI pero sin consulta a Crossref (--sin-red o caché vacía)")
    else:
        v["notas"].append("sin DOI: no se pueden verificar los metadatos")
    it["_verificacion"] = v
    return it


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("entrada", nargs="?", help="texto de una entrada")
    p.add_argument("--lista", help="archivo con una entrada por línea")
    p.add_argument("--norma", choices=["apa7", "ieee"])
    p.add_argument("--sin-red", action="store_true")
    a = p.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    ent = []
    if a.lista:
        import pathlib
        ent = [l for l in pathlib.Path(a.lista).read_text(encoding="utf-8").splitlines() if l.strip()]
    elif a.entrada:
        ent = [a.entrada]
    else:
        p.error("falta la entrada o --lista")
    print(json.dumps(parsear_lista(ent, a.norma, red=not a.sin_red), ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
