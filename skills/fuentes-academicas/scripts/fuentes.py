#!/usr/bin/env python3
"""Busca, rankea y verifica fuentes académicas. Salida: CSL-JSON verificado.

Uso:
  python fuentes.py "consulta" [--n 15] [--desde 2016] [--clasicos 3] [--idioma es|en] [--oa] [--out fuentes.json]
  python fuentes.py --verificar fuentes.json [--json res.json]  # re-verifica cada DOI contra Crossref
  python fuentes.py --doi 10.1109/5.771073 [--out f.json --append]
  python fuentes.py --resumenes fuentes.json          # añade resúmenes a las fuentes que no lo tengan
  python fuentes.py --desde-docx doc.docx --out fuentes.json [--sin-red]   # fuentes.json desde la lista de referencias de un Word

`--desde-docx`: lee la lista de referencias del documento, extrae DOI y URL de cada entrada, resuelve el DOI (Crossref; OpenAlex
para resumen y tipo de fuente) y, a las que no tienen DOI, les busca uno por título + primer autor + año (solo coincidencia alta; si
no, queda sin DOI con el motivo en `_verificacion.sin_doi_motivo`). Cada entrada guarda `_original` (el texto del documento), `_ref_n`
(posición en la lista) y `_nivel` (A-E, ver scripts/niveles.py); la salida resume DOI resueltos, sin DOI con motivo y la
pirámide de fuentes. Con `--verificar`, las normas ISO/IEC se comprueban con la vista previa oficial cuando iso.org no responde
(scripts/normas_iso.py).

Solo stdlib. Sin claves. OpenAlex (búsqueda/citas), Crossref (metadatos canónicos),
Semantic Scholar (citas influyentes, opcional: falla en silencio por límite de tasa).
Caché HTTP en el directorio de caché del usuario (scripts/datos.py: EDITORIAL_CACHE o el del sistema), 7 días.

Salida: 0 sin hallazgos (--verificar: todas las fuentes verificadas o no verificables sin bloqueo); 1 con fuentes que
fallan (DOI inexistente, metadatos que no coinciden, retractada); 2 error de uso o de entrada (falta consulta,
archivo ilegible, DOI que no resuelve o preprint con versión publicada).
"""
import argparse
import datetime as dt
import json
import hashlib
import math
import pathlib
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
import cli  # noqa: E402
import datos  # noqa: E402
import niveles  # noqa: E402
import normas_iso  # noqa: E402

UA = "editorial-academica/0.1 (academic citation plugin)"
TIPOS_REVISADOS = {"journal-article", "proceedings-article", "book-chapter", "book", "monograph",
                   "report", "dissertation", "posted-content", "dataset", "standard", "reference-entry"}


CACHE_HTTP = datos.dir_cache() / "http"
SIN_RED = False          # --sin-red: solo caché (regresión sin red)
TTL_CACHE = 7 * 86400    # retractaciones y versiones cambian: la caché caduca en una semana


def get(url, tries=3):
    """GET JSON con caché en disco (<dir de caché>/http). Un 404 se cachea como null."""
    ruta = CACHE_HTTP / (hashlib.sha1(url.encode()).hexdigest() + ".json")
    if ruta.exists() and (SIN_RED or time.time() - ruta.stat().st_mtime < TTL_CACHE):
        return json.loads(ruta.read_text(encoding="utf-8"))
    if SIN_RED:
        raise urllib.error.URLError("sin red y sin caché: " + url)
    d = _get_red(url, tries)
    CACHE_HTTP.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    return d


def _get_red(url, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if e.code in (429, 503) and i < tries - 1:
                time.sleep(2 * (i + 1))
                continue
            raise
        except urllib.error.URLError:
            if i < tries - 1:
                time.sleep(2)
                continue
            raise


def get_texto(url, tries=2):
    """GET de texto (p. ej. la ficha Atom de arXiv) con la misma caché en disco que `get`; sin red y sin caché lanza URLError."""
    ruta = CACHE_HTTP / (hashlib.sha1(("txt:" + url).encode()).hexdigest() + ".txt")
    if ruta.exists() and (SIN_RED or time.time() - ruta.stat().st_mtime < TTL_CACHE):
        return ruta.read_text(encoding="utf-8")
    if SIN_RED:
        raise urllib.error.URLError("sin red y sin caché: " + url)
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                t = r.read().decode("utf-8", "replace")
            CACHE_HTTP.mkdir(parents=True, exist_ok=True)
            ruta.write_text(t, encoding="utf-8")
            return t
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return ""
            if i == tries - 1:
                raise
        except urllib.error.URLError:
            if i == tries - 1:
                raise
        time.sleep(2)
    return ""


def openalex_buscar(q, n, desde, idioma, oa, orden=None):
    filtros = [f"from_publication_date:{desde}-01-01", "is_retracted:false",
               "type:article|book|book-chapter|review|dissertation|report|dataset|standard|preprint"]
    if idioma:
        filtros.append(f"language:{idioma}")
    if oa:
        filtros.append("is_oa:true")
    params = {"search": q, "filter": ",".join(filtros), "per-page": str(min(max(n * 3, 25), 100)),
              "select": "id,doi,title,publication_year,cited_by_count,type,primary_location,"
                        "relevance_score,open_access,authorships,language,abstract_inverted_index"}
    if orden:
        params["sort"] = orden
    d = get("https://api.openalex.org/works?" + urllib.parse.urlencode(params))
    return (d or {}).get("results", [])


def resumen_openalex(inv):
    """abstract_inverted_index de OpenAlex -> texto plano."""
    if not inv:
        return ""
    pos = sorted((i, w) for w, idx in inv.items() for i in idx)
    return " ".join(w for _, w in pos)


def resumen_por_doi(doi, estricto=False):
    """Resumen de OpenAlex. Con estricto=True un fallo de red/parseo se propaga (el llamador lo informa
    como no_verificado); si no, devuelve «» (sin resumen)."""
    try:
        w = get("https://api.openalex.org/works/doi:" + urllib.parse.quote(doi, safe="/")
                + "?select=abstract_inverted_index", tries=2)
    except Exception:
        if estricto:
            raise
        return ""
    return resumen_openalex((w or {}).get("abstract_inverted_index"))


def openalex_info(doi, estricto=False):
    """(resumen, tipo de fuente de OpenAlex: journal, conference, repository, book series…) de un DOI. Un fallo de red/parseo se
    propaga con estricto=True; si no, devuelve ("", None)."""
    try:
        w = get("https://api.openalex.org/works/doi:" + urllib.parse.quote(doi, safe="/")
                + "?select=abstract_inverted_index,primary_location,type", tries=2)
    except Exception:
        if estricto:
            raise
        return "", None
    w = w or {}
    src = ((w.get("primary_location") or {}).get("source") or {})
    return resumen_openalex(w.get("abstract_inverted_index")), src.get("type")


def crossref(doi):
    d = get("https://api.crossref.org/works/" + urllib.parse.quote(doi, safe="/"))
    return d.get("message") if d else None


def s2(doi):
    try:
        return get(f"https://api.semanticscholar.org/graph/v1/paper/DOI:{urllib.parse.quote(doi, safe='/')}"
                   "?fields=citationCount,influentialCitationCount", tries=1)
    except Exception:
        return None


def puntaje(w, anio_actual):
    rel = w.get("relevance_score") or 0
    edad = max(1, anio_actual - (w.get("publication_year") or anio_actual) + 1)
    citas_anio = (w.get("cited_by_count") or 0) / edad
    src = ((w.get("primary_location") or {}).get("source") or {})
    venue = 1.0 if src.get("type") in ("journal", "conference") else 0.6
    return round((math.log1p(rel) * 2 + math.log1p(citas_anio)) * venue, 3)


MENORES = {"a", "an", "the", "and", "or", "but", "nor", "for", "of", "in", "on", "at", "to", "by", "with",
           "from", "as", "via", "into", "over", "per", "vs", "y", "e", "o", "u", "de", "del", "la", "el",
           "los", "las", "en", "con", "para", "por", "un", "una"}


def a_oracion(titulo):
    """Title Case -> sentence case (convención CSL; APA lo exige en títulos de obra).

    Conserva: primera palabra, palabra tras ':' / '?' / '!', siglas (2+ mayúsculas), palabras con
    mayúsculas internas (MusicScaffold, iPhone) y palabras con dígitos. Los nombres propios comunes
    (países, personas) no se pueden detectar: se marca para revisión.
    Devuelve (titulo, cambiado).
    """
    palabras = titulo.split(" ")
    capitalizadas = [w for w in palabras if w[:1].isupper()]
    candidatas = [w for w in palabras if w.lower() not in MENORES and w[:1].isalpha()]
    if not candidatas or len(capitalizadas) / len(candidatas) < 0.8:
        return titulo, False  # ya está en sentence case
    out, inicio = [], True
    def conservar(parte, es_inicio):
        n = parte.strip("()[]\"'“”‘’,.;:?!")
        return (es_inicio or len(n) <= 1 or sum(c.isupper() for c in n) >= 2 or any(c.isdigit() for c in n)
                or n[1:] != n[1:].lower() or not n[:1].isalpha())

    for w in palabras:
        partes = w.split("-")
        w = "-".join(p if conservar(p, inicio and i == 0) else p.lower() for i, p in enumerate(partes))
        out.append(w)
        inicio = w.endswith((":", "?", "!", "—"))
    return " ".join(out), True


def limpiar_titulo(t):
    """Quita marcado JATS/HTML de Crossref (<scp>, <i>, <sub>…) y colapsa espacios y saltos de línea."""
    import unicodedata
    return unicodedata.normalize("NFC", re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", t or ""))).strip()


def titulo_cmp(t):
    """Clave de comparación de títulos: sin marcado, sin mayúsculas ni puntuación final."""
    return limpiar_titulo(t).lower().rstrip(" .")[:40]


def titulos_equivalentes(a, b):
    """Mismo título salvo puntuación, mayúsculas, marcado y subtítulo omitido en uno de los dos
    («Does Gamification Work? -- A Literature…» = «Does gamification work? A literature…»;
    «Fundamentals of Music Processing» = «Fundamentals of music processing: Audio, analysis…»)."""
    import unicodedata

    def k(t):
        t = unicodedata.normalize("NFKD", limpiar_titulo(t)).lower()
        return "".join(c for c in t if c.isalnum())
    x, y = k(a), k(b)
    if not x or not y:
        return x == y
    corto, largo = sorted((x, y), key=len)
    return largo.startswith(corto[:40]) and (len(corto) >= 12 or corto == largo)


def clave_legible(it):
    """apellidoAño sin acentos ni espacios (p. ej. «weberwulff2023»); el DOI sigue en `DOI`."""
    import unicodedata
    au = (it.get("author") or [{}])[0]
    ap = au.get("family") or au.get("literal") or (it.get("container-title") or "anon").split()[0]
    ap = "".join(c for c in unicodedata.normalize("NFKD", ap) if c.isalnum() and not unicodedata.combining(c)).lower()
    y = ((it.get("issued") or {}).get("date-parts") or [[None]])[0][0]
    return f"{ap or 'anon'}{y or 'sf'}"


def asignar_ids(previos, nuevos):
    """Une listas sin duplicar por DOI y da a los nuevos un id legible único (sufijo a, b… si choca)."""
    usados = {i["id"] for i in previos}
    dois = {(i.get("DOI") or "").lower() for i in previos} - {""}
    salida = list(previos)
    for it in nuevos:
        doi = (it.get("DOI") or "").lower()
        if doi and doi in dois:
            continue
        base = clave_legible(it)
        cand, k = base, 0
        while cand in usados:
            cand = base + "abcdefghijklmnopqrstuvwxyz"[k]
            k += 1
        it["id"] = cand
        usados.add(cand)
        dois.add(doi)
        salida.append(it)
    return salida


def a_csl(m, extra=None, resumen=""):
    """Crossref message -> CSL-JSON item (Crossref ya usa nombres compatibles con CSL).
    `abstract`: el de Crossref (JATS limpio) o, si falta, el de OpenAlex. El redactor lo usa para no
    afirmar nada que la fuente no diga; ningún CSL lo imprime."""
    tipo = m.get("type", "article")
    mapa = {"journal-article": "article-journal", "proceedings-article": "paper-conference",
            "book-chapter": "chapter", "posted-content": "article", "monograph": "book",
            "dissertation": "thesis", "reference-entry": "entry"}
    item = {
        "id": m.get("DOI", "").lower(),
        "type": mapa.get(tipo, tipo),
        "title": limpiar_titulo((m.get("title") or [""])[0]),
        "author": [{k: a[k] for k in ("family", "given", "literal") if k in a} for a in m.get("author", [])],
        "editor": [{k: a[k] for k in ("family", "given") if k in a} for a in m.get("editor", [])],
        "container-title": (m.get("container-title") or [""])[0],
        "publisher": m.get("publisher"),
        "volume": m.get("volume"), "issue": m.get("issue"), "page": m.get("page"),
        "DOI": m.get("DOI"), "URL": m.get("URL"),
        "issued": m.get("issued") or m.get("published"),
        "ISSN": ", ".join(m.get("ISSN") or []), "ISBN": ", ".join(m.get("ISBN") or []),
        "language": m.get("language"),
        "abstract": limpiar_titulo(m.get("abstract") or "") or resumen,
    }
    if m.get("article-number"):
        item["number"] = m["article-number"]
        if item.get("page") == item["number"]:
            item.pop("page")  # Crossref repite el eLocator como página
    item = {k: v for k, v in item.items() if v not in (None, "", [], {})}
    titulo_original = item.get("title", "")
    item["title"], cambiado = a_oracion(titulo_original)
    item["_verificacion"] = {"fuente": "crossref", "fecha": dt.date.today().isoformat(),
                             "doi_resuelve": True, **(extra or {})}
    if cambiado:
        item["_verificacion"]["titulo_original"] = titulo_original
        item["_verificacion"]["revisar_nombres_propios"] = True
    return item


def buscar(a):
    anio = dt.date.today().year
    obras = openalex_buscar(a.consulta, a.n, a.desde, a.idioma, a.oa)
    obras.sort(key=lambda w: puntaje(w, anio), reverse=True)
    if a.clasicos:
        # obras más citadas del tema sin límite de antigüedad; van primero
        top = openalex_buscar(a.consulta, a.clasicos, 1900, a.idioma, a.oa, "cited_by_count:desc")[:a.clasicos]
        vistos = {w["id"] for w in top}
        obras = top + [w for w in obras if w["id"] not in vistos]
        a.n += a.clasicos
    salida, descartadas = [], []
    for w in obras:
        if len(salida) >= a.n:
            break
        doi = (w.get("doi") or "").replace("https://doi.org/", "")
        if not doi:
            descartadas.append({"titulo": w.get("title"), "motivo": "sin DOI (verificar manualmente)"})
            continue
        m = crossref(doi)
        if not m:
            descartadas.append({"titulo": w.get("title"), "doi": doi, "motivo": "DOI no resuelve en Crossref"})
            continue
        sc = s2(doi) or {}
        salida.append(a_csl(m, resumen=resumen_openalex(w.get("abstract_inverted_index")), extra={
            "openalex": w.get("id"), "citas": w.get("cited_by_count"),
            "citas_influyentes": sc.get("influentialCitationCount"),
            "acceso_abierto": (w.get("open_access") or {}).get("oa_url"),
            "puntaje": puntaje(w, anio)}))
        time.sleep(0.15)
    return salida, descartadas


def _norm(t):
    import unicodedata
    t = unicodedata.normalize("NFKD", limpiar_titulo(str(t or ""))).lower()
    return "".join(c for c in t if c.isalnum())


def _motivo_red(ex, que):
    """Motivo legible de un fallo de consulta: «sin red» si es de red/caché vacía, si no el tipo de error."""
    if SIN_RED or isinstance(ex, (urllib.error.URLError, OSError, TimeoutError)):
        return f"sin red: {que}"
    return f"error de respuesta ({type(ex).__name__}): {que}"


def metadatos_doi(doi):
    """Metadatos canónicos: Crossref; si no está (p. ej. arXiv/Zenodo en DataCite), CSL de doi.org."""
    return metadatos_doi_estado(doi)[0]


def metadatos_doi_estado(doi):
    """(meta, error). error es None si la consulta se pudo hacer (meta None = el DOI no existe) o un motivo
    «sin red: …» si un fallo de red/parseo impidió comprobarlo (entonces no hay veredicto)."""
    error = None
    try:
        m = crossref(doi)
    except Exception as ex:  # noqa: BLE001 - se informa como no verificado, no se traga
        m = None
        error = _motivo_red(ex, "DOI no comprobado en Crossref")
    if m:
        return {"title": (m.get("title") or [""])[0], "author": m.get("author") or [],
                "year": ((m.get("issued") or m.get("published") or {}).get("date-parts") or [[None]])[0][0],
                "container": (m.get("container-title") or [""])[0], "type": m.get("type"),
                "relation": m.get("relation") or {}, "updated-by": m.get("updated-by") or [],
                "registro": "crossref"}, None
    ruta = CACHE_HTTP / (hashlib.sha1(("csl:" + doi).encode()).hexdigest() + ".json")
    c = None
    if ruta.exists() and (SIN_RED or time.time() - ruta.stat().st_mtime < TTL_CACHE):
        c = json.loads(ruta.read_text(encoding="utf-8"))
        error = None
    elif not SIN_RED:
        try:
            req = urllib.request.Request("https://doi.org/" + urllib.parse.quote(doi, safe="/"),
                                         headers={"User-Agent": UA, "Accept": "application/vnd.citationstyles.csl+json"})
            with urllib.request.urlopen(req, timeout=30) as r:
                c = json.load(r)
        except urllib.error.HTTPError as e:
            c = {} if e.code == 404 else None
            error = None if e.code == 404 else _motivo_red(e, "DOI no comprobado en doi.org")
        except Exception as ex:  # noqa: BLE001
            c = None
            error = _motivo_red(ex, "DOI no comprobado en doi.org")
        else:
            error = None
        if c is not None:
            CACHE_HTTP.mkdir(parents=True, exist_ok=True)
            ruta.write_text(json.dumps(c, ensure_ascii=False), encoding="utf-8")
    if not c:
        return None, error
    return {"title": c.get("title", ""), "author": c.get("author") or [],
            "year": ((c.get("issued") or {}).get("date-parts") or [[None]])[0][0],
            "container": c.get("container-title", ""), "type": c.get("type"), "relation": {}, "updated-by": [],
            "registro": "doi.org"}, None


AVISOS_EDITORIALES = {"retraction": "retractado", "withdrawal": "retirado", "removal": "eliminado",
                      "expression_of_concern": "expresión de preocupación",
                      "expression-of-concern": "expresión de preocupación"}
GRAVES = {"retractado", "retirado", "eliminado"}
PREFIJOS_PREPRINT = ("10.48550/", "10.31234/", "10.1101/", "10.20944/", "10.21203/", "10.2139/ssrn")


def integridad(doi, meta):
    """V3: avisos editoriales (Crossref + Retraction Watch, OpenAlex is_retracted) y versión publicada de un preprint."""
    out = {"avisos": [], "version_publicada": None, "preprint": False, "estado": "verificado", "motivo": None}
    sin = []   # consultas que fallaron: sin ellas no se puede afirmar «no retractada»
    for u in meta.get("updated-by", []):
        a = {"tipo": AVISOS_EDITORIALES.get(u.get("type")), "aviso": u.get("DOI")}
        if a["tipo"] and a not in out["avisos"]:
            out["avisos"].append(a)
    try:
        r = get("https://api.crossref.org/works?rows=20&select=DOI,update-to&filter=updates:"
                + urllib.parse.quote(doi, safe="/"), tries=2)
        for it in ((r or {}).get("message") or {}).get("items", []):
            for u in it.get("update-to", []):
                if (u.get("DOI") or "").lower() == doi.lower() and u.get("type") in AVISOS_EDITORIALES:
                    a = {"tipo": AVISOS_EDITORIALES[u["type"]], "aviso": it["DOI"]}
                    if a not in out["avisos"]:
                        out["avisos"].append(a)
    except Exception as ex:  # noqa: BLE001
        sin.append(_motivo_red(ex, "retractación no comprobada (Crossref)"))
    w = None
    try:
        w = get("https://api.openalex.org/works/doi:" + urllib.parse.quote(doi, safe="/")
                + "?select=doi,is_retracted,locations,type", tries=2)
    except Exception as ex:  # noqa: BLE001
        sin.append(_motivo_red(ex, "retractación no comprobada (OpenAlex)"))
    if w and w.get("is_retracted") and not any(a["tipo"] == "retractado" for a in out["avisos"]):
        out["avisos"].append({"tipo": "retractado", "aviso": "OpenAlex is_retracted"})
    out["preprint"] = meta.get("type") == "posted-content" or doi.lower().startswith(PREFIJOS_PREPRINT)
    if out["preprint"]:
        pub = [x.get("id") for x in (meta.get("relation") or {}).get("is-preprint-of", []) if x.get("id-type") == "doi"]
        if not pub and w:
            for loc in w.get("locations") or []:
                url = loc.get("landing_page_url") or ""
                if loc.get("version") == "publishedVersion" and "doi.org/10." in url:
                    cand = url.split("doi.org/", 1)[1]
                    if cand.lower() != doi.lower() and not cand.lower().startswith(PREFIJOS_PREPRINT):
                        pub.append(cand)
        out["version_publicada"] = pub[0] if pub else None
    if sin:
        out["estado"], out["motivo"] = "no_verificado", "; ".join(sin)
    return out


def url_resuelve(url):
    """V1 para fuentes sin DOI: «ok» (2xx/3xx), «roto» (404/410 o dominio inexistente) o «no verificable»
    (401/403/429/5xx, tiempo agotado: el sitio existe pero no deja comprobarlo). Caché como get()."""
    ruta = CACHE_HTTP / (hashlib.sha1(("url:" + url).encode()).hexdigest() + ".json")
    if ruta.exists() and (SIN_RED or time.time() - ruta.stat().st_mtime < TTL_CACHE):
        return json.loads(ruta.read_text(encoding="utf-8"))
    if SIN_RED:
        return "no verificable"
    estado = "no verificable"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; " + UA + ")"}, method="GET")
        with urllib.request.urlopen(req, timeout=20) as r:
            estado = "ok" if r.status < 400 else "no verificable"
    except urllib.error.HTTPError as e:
        estado = "roto" if e.code in (404, 410) else "no verificable"
    except urllib.error.URLError as e:
        estado = "roto" if "getaddrinfo" in str(e.reason) or "Name or service" in str(e.reason) else "no verificable"
    except Exception:
        estado = "no verificable"
    if estado != "no verificable":  # un fallo transitorio no se cachea: se reintenta en la próxima corrida
        CACHE_HTTP.mkdir(parents=True, exist_ok=True)
        ruta.write_text(json.dumps(estado), encoding="utf-8")
    return estado


def comparar(it, meta):
    """V2: campos que no coinciden entre la entrada y el registro (título, primer autor, año, revista)."""
    dif = []
    if not titulos_equivalentes(meta["title"], it.get("title", "")):
        dif.append("título")
    a1 = (it.get("author") or [{}])[0]
    m1 = (meta["author"] or [{}])[0]
    fa = _norm(a1.get("family") or a1.get("literal"))
    fm = _norm(m1.get("family") or m1.get("literal") or m1.get("name"))
    grupal = bool(a1.get("literal")) and not a1.get("family")  # «National Institute…» frente al editor personal del registro
    if fa and fm and fa != fm and fa not in fm and fm not in fa and not grupal:
        dif.append("primer autor")
    ya = ((it.get("issued") or {}).get("date-parts") or [[None]])[0][0]
    try:
        if ya and meta["year"] and abs(int(ya) - int(meta["year"])) > 1:  # ±1: publicación en línea anticipada
            dif.append("año")
    except (TypeError, ValueError):
        pass
    ca, cm = _norm(it.get("container-title"))[:20], _norm(meta.get("container"))[:20]
    if ca and cm and ca != cm and ca not in cm and cm not in ca:
        dif.append("revista (aviso)")
    return dif


def calidad(it, meta, v3, desde=None):
    """V4: señales de calidad (avisos, no bloquean): revista sin ISSN, preprint sin versión publicada,
    expresión de preocupación, antigüedad fuera del rango pedido."""
    av = []
    if it.get("type") == "article-journal" and not it.get("ISSN"):
        av.append("revista sin ISSN registrado")
    if v3.get("preprint") and not v3.get("version_publicada"):
        av.append("preprint sin revisión por pares")
    if any(a["tipo"] == "expresión de preocupación" for a in v3.get("avisos", [])):
        av.append("expresión de preocupación editorial")
    y = meta.get("year")
    if desde and y and int(y) < desde:
        av.append(f"anterior a {desde}")
    return av


def autocitas(items):
    """Proporción de entradas cuyo primer autor encabeza también otra entrada (concentración, V4)."""
    fam = [_norm(((i.get("author") or [{}])[0]).get("family")) for i in items]
    fam = [f for f in fam if f]
    return sum(fam.count(f) > 1 for f in fam) / len(fam) if fam else 0.0


def doi_por_metadatos(it):
    """DOI de la obra con el mismo título, primer autor y año (±1) en Crossref, o None (ver doi_por_metadatos_motivo)."""
    return doi_por_metadatos_motivo(it)[0]


def doi_por_metadatos_motivo(it):
    """Busca en Crossref (query.bibliographic) una obra con el mismo título, primer autor y año (±1).
    Devuelve (DOI o None, motivo si no hay). Solo se envían título, apellido y año (metadatos públicos de la obra).
    Coincidencia alta: título equivalente (titulos_equivalentes) Y primer autor Y año; si no, no se acepta."""
    titulo = limpiar_titulo(it.get("title", ""))
    if len(titulo) < 12:
        return None, "título demasiado corto para buscar por título"
    if it.get("type") in ("webpage", "post-weblog", "software", "legislation", "personal_communication", "dataset"):
        return None, f"obra de tipo «{it.get('type')}»: no suele tener DOI (no se buscó)"
    a1 = (it.get("author") or [{}])[0]
    ap = a1.get("family") or a1.get("literal") or ""
    y = ((it.get("issued") or {}).get("date-parts") or [[None]])[0][0]
    q = urllib.parse.urlencode({"query.bibliographic": f"{titulo} {ap} {y or ''}".strip(), "rows": "3",
                                "select": "DOI,title,author,issued,type"})
    try:
        d = get("https://api.crossref.org/works?" + q, tries=2)
    except Exception as ex:  # noqa: BLE001
        return None, _motivo_red(ex, "búsqueda por título en Crossref")
    candidatas = ((d or {}).get("message") or {}).get("items", [])
    if not candidatas:
        return None, "Crossref no devuelve obras para ese título"
    motivo = "ninguna candidata de Crossref coincide en título"
    for m in candidatas:
        if not titulos_equivalentes((m.get("title") or [""])[0], titulo):
            continue
        fm = _norm(((m.get("author") or [{}])[0]).get("family") or ((m.get("author") or [{}])[0]).get("name"))
        fa = _norm(ap)
        if fa and fm and fa not in fm and fm not in fa and not a1.get("literal"):
            motivo = "el título coincide pero el primer autor no"
            continue
        ym = ((m.get("issued") or {}).get("date-parts") or [[None]])[0][0]
        try:
            if y and ym and abs(int(y) - int(ym)) > 1:
                motivo = "el título y el autor coinciden pero el año no"
                continue
        except (TypeError, ValueError):
            pass
        return m.get("DOI"), None
    return None, motivo


def verificar_item(it):
    """V1-V3 de una entrada. ok = existe, metadatos esenciales coinciden y sin retractación ni retiro."""
    doi = it.get("DOI")
    r = {"id": it.get("id"), "doi": doi, "v1": False, "v2": [], "v3": {}, "ok": False,
         "estado": "verificado", "motivo": None}
    if not doi:
        url = it.get("URL")
        norma = normas_iso.detectar(it)
        rn = normas_iso.verificar(norma, SIN_RED) if norma else None
        if rn:
            r["_verificacion"] = {k: rn[k] for k in ("estado", "motivo", "fuente_verificacion", "norma", "edicion", "titulo_oficial") if rn.get(k)}
            if isinstance(it.get("_verificacion"), dict) or "_verificacion" not in it:
                it.setdefault("_verificacion", {}).update(r["_verificacion"])
            if rn["estado"] == "verificado":
                r.update(url="ok", v1=True, ok=True, estado="verificado",
                         nota=f"norma {rn['norma']} verificada con {rn['fuente_verificacion']}" + (f" ({rn['edicion']})" if rn.get("edicion") else ""))
                r["fuente_verificacion"] = rn["fuente_verificacion"]
                return r
            if rn["estado"] == "difiere":
                r.update(url="ok", v1=True, ok=False, v2=rn["diferencias"], nota=rn["motivo"])
                r["fuente_verificacion"] = rn["fuente_verificacion"]
                return r
        sug = None if norma else doi_por_metadatos(it)
        if sug:
            r["doi_sugerido"] = sug  # APA 9.34: si la obra tiene DOI, la referencia lo incluye
        if not url:  # libro impreso, ley, comunicación: existe pero no se comprueba en línea
            r["url"] = "registro" if sug else None
            r["v1"] = bool(sug)
            r["ok"] = True
            r["nota"] = (f"existe en Crossref con DOI {sug}: añadirlo" if sug
                         else "sin DOI ni URL: no verificable en línea")
            if rn and not sug:
                r["nota"] += "; norma ISO/IEC: " + (rn.get("motivo") or "no verificada")
            if not sug:
                r["estado"], r["motivo"] = "no_verificado", r["nota"]
            return r
        r["url"] = url_resuelve(url)
        r["v1"] = r["url"] == "ok"
        r["ok"] = r["url"] != "roto"
        r["nota"] = {"ok": "URL responde", "roto": "URL rota (404/410 o dominio inexistente)",
                     "no verificable": "el sitio no permite comprobar la URL"}[r["url"]]
        if rn and rn["estado"] == "no_verificado":  # la URL responde, pero la norma no se pudo comprobar contra una portada oficial
            r["nota"] += "; norma ISO/IEC: " + (rn.get("motivo") or "no verificada")
            r["estado"], r["motivo"] = "no_verificado", rn.get("motivo") or r["nota"]
        if r["url"] == "no verificable":
            r["estado"], r["motivo"] = "no_verificado", r["nota"]
        return r
    meta, error = metadatos_doi_estado(doi)
    if not meta and error:
        # fallo de red/parseo: no hay veredicto. No bloquea, pero V1 y V3 quedan sin comprobar.
        r["ok"] = True
        r["estado"], r["motivo"] = "no_verificado", error
        r["v3"] = {"avisos": [], "version_publicada": None, "preprint": False,
                   "estado": "no_verificado", "motivo": error}
        r["nota"] = error
        return r
    if not meta:
        r["nota"] = "el DOI no resuelve"
        return r
    r["v1"] = True
    r["v2"] = comparar(it, meta)
    r["v3"] = integridad(doi, meta)
    r["v4"] = calidad(it, meta, r["v3"])
    if r["v3"].get("estado") == "no_verificado":
        r["estado"], r["motivo"] = "no_verificado", r["v3"]["motivo"]
    r["ok"] = (not [d for d in r["v2"] if "aviso" not in d]
               and not any(a["tipo"] in GRAVES for a in r["v3"]["avisos"]))
    return r


def cargar_json(path):
    """Lista de fuentes de un .json; archivo inexistente o JSON inválido = error de entrada (código 2)."""
    try:
        return json.load(open(path, encoding="utf-8"))
    except FileNotFoundError:
        cli.error(f"no existe el archivo: {path}")
    except ValueError as ex:
        cli.error(f"JSON inválido en {path}: {ex}")


RE_DOI = re.compile(r"10\.\d{4,9}/[^\s\"<>]+")


def _limpiar_doi(d):
    return d.rstrip(".,;:)]}»”’'").lower() if d else d


def _ids_unicos(items):
    """Da a cada item un id apellidoAño único (sufijo a, b… si choca) sin fusionar duplicados: conserva el orden de la lista."""
    usados = set()
    for it in items:
        base = clave_legible(it)
        m = re.match(r"^(.*?)(\d{4}|sf)$", base)
        if m and len(m.group(1)) > 20:  # autor institucional largo: solo el comienzo («agenciadeasuntosculturales2024»)
            base = m.group(1)[:20] + m.group(2)
        cand, k = base, 0
        while cand in usados:
            cand = base + "abcdefghijklmnopqrstuvwxyz"[k % 26] + (str(k // 26) if k >= 26 else "")
            k += 1
        it["id"] = cand
        usados.add(cand)


def desde_docx(doc, out, resolver=True):
    """fuentes.json desde la lista de referencias de un .docx/.md (ver el docstring del módulo). Devuelve (items, resumen)."""
    import auditar
    import refs_csl
    auditar.validar_entrada(doc)
    pars, _ = (auditar.cargar_docx if str(doc).lower().endswith(".docx") else auditar.cargar_md)(str(doc))
    _, _, entradas = auditar.partir(pars)
    textos = [" ".join(e["texto"].split()) for e in entradas if e["texto"].strip()]
    if not textos:
        cli.error(f"{doc}: no se encontró la lista de referencias")
    parseadas = refs_csl.parsear_lista(textos)
    items = []
    cuenta = {"referencias": len(textos), "doi_en_documento": 0, "doi_resuelto": 0, "doi_no_resuelve": 0, "doi_por_titulo": 0,
              "sin_doi": 0, "con_resumen": 0, "sin_red": 0}
    sin_doi_motivos = []
    for n, (it, texto) in enumerate(zip(parseadas, textos), 1):
        doi = _limpiar_doi(it.get("DOI") or (RE_DOI.search(texto) or [None])[0])
        encontrado_por = None
        if doi:
            cuenta["doi_en_documento"] += 1
        elif resolver:
            sug, motivo = doi_por_metadatos_motivo(it)
            if sug:
                doi, encontrado_por = sug.lower(), "título + primer autor + año"
                cuenta["doi_por_titulo"] += 1
            else:
                it.setdefault("_verificacion", {})["sin_doi_motivo"] = motivo
        if doi and resolver:
            try:
                m = crossref(doi)
                err = None
            except Exception as ex:  # noqa: BLE001
                m, err = None, _motivo_red(ex, "DOI no comprobado en Crossref")
            if m:
                resumen, tipo_oa = openalex_info(doi)
                base = a_csl(m, resumen=resumen, extra={"crossref_type": m.get("type"), "openalex_source_type": tipo_oa})
                dif = comparar(it, {"title": (m.get("title") or [""])[0], "author": m.get("author") or [],
                                    "year": ((m.get("issued") or m.get("published") or {}).get("date-parts") or [[None]])[0][0],
                                    "container": (m.get("container-title") or [""])[0]})
                base["_verificacion"]["coincide_documento"] = not [d for d in dif if "aviso" not in d]
                if dif:
                    base["_verificacion"]["diferencias_con_documento"] = dif
                if encontrado_por:
                    base["_verificacion"]["doi_encontrado_por"] = encontrado_por
                if it.get("URL") and not base.get("URL"):
                    base["URL"] = it["URL"]
                it = base
                cuenta["doi_resuelto"] += 1
                cuenta["con_resumen"] += bool(base.get("abstract"))
            elif err:
                it["DOI"] = doi
                it.setdefault("_verificacion", {}).update({"fuente": "documento", "estado": "no_verificado", "motivo": err})
                cuenta["sin_red"] += 1
            else:
                it["DOI"] = doi
                it.setdefault("_verificacion", {}).update({"fuente": "documento", "estado": "falla", "motivo": "el DOI no resuelve en Crossref"})
                cuenta["doi_no_resuelve"] += 1
        elif doi:
            it["DOI"] = doi
        if not it.get("DOI"):
            cuenta["sin_doi"] += 1
            sin_doi_motivos.append((n, (it.get("_verificacion") or {}).get("sin_doi_motivo") or "sin DOI ni búsqueda (--sin-red)"))
        it["_original"] = texto
        it["_ref_n"] = n
        it["_nivel"] = niveles.clasificar(it, texto)
        for k in ("_norma", "_sufijo"):
            it.pop(k, None)
        items.append(it)
        time.sleep(0 if SIN_RED else 0.1)
    _ids_unicos(items)
    niv = [i["_nivel"]["nivel"] for i in items]
    resumen = {**cuenta, "piramide": niveles.piramide(niv), "peso_medio": niveles.peso_medio(niv), "sin_doi_motivos": sin_doi_motivos}
    if out:
        pathlib.Path(out).write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    return items, resumen


def verificar(path, json_out=None, guardar=False):
    items = cargar_json(path)
    res = []
    for it in items:
        r = verificar_item(it)
        res.append(r)
        r["nivel"] = niveles.clasificar(it)["nivel"]
        nota = []
        if not r["v1"]:
            nota.append(r.get("nota", "no resuelve"))
        if r["v2"]:
            nota.append("difiere: " + ", ".join(r["v2"]))
        for a in r["v3"].get("avisos", []):
            nota.append(f"{a['tipo'].upper()} ({a['aviso']})")
        for a in r.get("v4", []):
            nota.append("aviso: " + a)
        if r["v3"].get("preprint"):
            vp = r["v3"].get("version_publicada")
            nota.append("preprint" + (f"; versión publicada: {vp}" if vp else " sin versión publicada"))
        if r["ok"] and r["estado"] == "no_verificado" and r["doi"]:
            nota.append("NO VERIFICADO: " + r["motivo"])
        etiqueta = "FALLA" if not r["ok"] else "NO VERIFICADO" if (r["doi"] and r["estado"] == "no_verificado") else "OK   "
        print(etiqueta, r["doi"] or r["id"], ("| " + "; ".join(nota)) if nota else "")
        time.sleep(0 if SIN_RED else 0.1)
    malos = sum(not r["ok"] for r in res)
    nover = sum(bool(r["ok"] and r["doi"] and r["estado"] == "no_verificado") for r in res)
    print(f"\n{len(items) - malos - nover}/{len(items)} verificadas"
          + (f"; {nover} no verificadas (sin red o error de consulta)" if nover else ""))
    conc = autocitas(items)
    if conc > 0.3:
        print(f"aviso V4: {conc:.0%} de las fuentes comparten primer autor con otra (concentración de autores)")
    print("\nPirámide de fuentes (nivel de evidencia):")
    print(niveles.texto_piramide(niveles.piramide([r["nivel"] for r in res]), len(res)))
    if json_out:
        json.dump(res, open(json_out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    if guardar:
        for it, r in zip(items, res):
            if r.get("_verificacion"):
                it.setdefault("_verificacion", {}).update(r["_verificacion"])
        pathlib.Path(path).write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    return 1 if malos else 0

def main():
    p = argparse.ArgumentParser()
    p.add_argument("consulta", nargs="?")
    p.add_argument("--n", type=int, default=15)
    p.add_argument("--desde", type=int, default=dt.date.today().year - 10)
    p.add_argument("--idioma")
    p.add_argument("--oa", action="store_true")
    p.add_argument("--clasicos", type=int, default=0, help="añade las k obras más citadas del tema")
    p.add_argument("--out", default="fuentes.json")
    p.add_argument("--append", action="store_true")
    p.add_argument("--verificar")
    p.add_argument("--json", help="con --verificar: guarda el resultado V1-V3 por fuente en este JSON")
    p.add_argument("--sin-red", action="store_true", help="solo caché HTTP (regresión sin red)")
    p.add_argument("--doi")
    p.add_argument("--desde-docx", metavar="DOC", help="genera fuentes.json (--out) desde la lista de referencias de este .docx o .md")
    p.add_argument("--guardar", action="store_true", help="con --verificar: escribe `_verificacion` (p. ej. fuente_verificacion de las normas ISO) en el mismo fuentes.json")
    p.add_argument("--resumenes", help="añade el resumen (Crossref/OpenAlex) a las fuentes de este JSON que no lo tengan")
    p.add_argument("--reemplazar", metavar="ORACION", help="propone (sin aplicar) cómo respaldar esta oración: versión publicada de la misma obra y candidatas A/B; con --cita")
    p.add_argument("--cita", metavar="REFERENCIA", help="con --reemplazar: texto de la referencia citada o su DOI")
    p.add_argument("--contexto", "--doc", dest="contexto", metavar="DOC.docx",
                   help="con --reemplazar: .docx del que se extraen 5-8 términos de dominio (título, palabras clave, frecuencia); se exigen en la consulta y en el filtrado")
    a = p.parse_args()
    cli.utf8()

    global SIN_RED
    SIN_RED = a.sin_red
    if a.reemplazar:
        if not a.cita:
            p.error("--reemplazar necesita --cita \"<texto de la referencia o DOI>\"")
        import reemplazo_fuentes
        try:
            res = reemplazo_fuentes.proponer(sys.modules[__name__], a.reemplazar, a.cita, n=a.n if a.n != 15 else 5, contexto=a.contexto)
        except (urllib.error.URLError, OSError) as ex:
            cli.error(f"sin red o la consulta falló ({type(ex).__name__}): {ex}")
        reemplazo_fuentes.imprimir(res)
        if a.out != "fuentes.json":
            cli.escribir_json(a.out, res, indent=2)
            print(f"propuesta escrita en {a.out}")
        sys.exit(0)
    if a.verificar:
        sys.exit(verificar(a.verificar, a.json, a.guardar))
    if a.desde_docx:
        items, rs = desde_docx(a.desde_docx, a.out)
        print(f"{rs['referencias']} referencias en {a.desde_docx}")
        print(f"  DOI en el documento: {rs['doi_en_documento']}; encontrados por título + autor + año: {rs['doi_por_titulo']}; "
              f"resueltos en Crossref: {rs['doi_resuelto']}; no resuelven: {rs['doi_no_resuelve']}; sin comprobar (sin red): {rs['sin_red']}")
        print(f"  sin DOI: {rs['sin_doi']}; con resumen: {rs['con_resumen']}")
        for n, motivo in rs["sin_doi_motivos"][:12]:
            print(f"    ref {n}: {motivo}")
        if len(rs["sin_doi_motivos"]) > 12:
            print(f"    … y {len(rs['sin_doi_motivos']) - 12} más (en `_verificacion.sin_doi_motivo` de cada entrada)")
        print("Pirámide de fuentes (nivel de evidencia):")
        print(niveles.texto_piramide(rs["piramide"], rs["referencias"]))
        print(f"  peso medio: {rs['peso_medio']}\n{len(items)} entradas en {a.out}")
        sys.exit(1 if rs["doi_no_resuelve"] else 0)
    if a.resumenes:
        items = cargar_json(a.resumenes)
        n = 0
        for it in items:
            if not it.get("abstract") and it.get("DOI"):
                m = crossref(it["DOI"]) or {}
                it["abstract"] = limpiar_titulo(m.get("abstract") or "") or resumen_por_doi(it["DOI"])
                n += bool(it["abstract"])
                if not it["abstract"]:
                    it.pop("abstract")
                time.sleep(0.15)
        json.dump(items, open(a.resumenes, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        print(f"{n} resúmenes añadidos; {sum(bool(i.get('abstract')) for i in items)}/{len(items)} fuentes con resumen")
        sys.exit(0)
    if a.doi:
        try:
            m = crossref(a.doi)
        except (urllib.error.URLError, OSError, ValueError) as ex:
            cli.error(f"sin red o la consulta falló ({type(ex).__name__}): {ex}")
        if not m:
            meta = metadatos_doi(a.doi)  # DataCite (arXiv, Zenodo…)
            vp = integridad(a.doi, meta).get("version_publicada") if meta else None
            if vp:
                cli.error(f"{a.doi} es un preprint con versión publicada: usa --doi {vp}")
            cli.error(f"DOI no resuelve en Crossref: {a.doi}" + (" (existe en DataCite: añádelo a mano con URL y fecha de consulta)" if meta else ""))
        nuevos, desc = [a_csl(m, resumen=resumen_por_doi(a.doi))], []
        v3 = integridad(a.doi, metadatos_doi(a.doi) or {})
        if any(x["tipo"] in GRAVES for x in v3["avisos"]):
            print(f"NO SE AGREGA: {a.doi} está {v3['avisos'][0]['tipo']} (aviso {v3['avisos'][0]['aviso']})", file=sys.stderr)
            sys.exit(cli.HALLAZGOS)
        if v3.get("estado") == "no_verificado":
            print(f"aviso: NO VERIFICADO: {v3['motivo']}")
        if v3.get("version_publicada"):
            print(f"aviso: {a.doi} es un preprint; cita la versión publicada: --doi {v3['version_publicada']}")
    elif a.consulta:
        try:
            nuevos, desc = buscar(a)
        except (urllib.error.URLError, OSError, ValueError) as ex:
            cli.error(f"sin red o la consulta falló ({type(ex).__name__}): {ex}")
    else:
        p.error("falta consulta, --doi o --verificar")

    previos = []
    if a.append:
        try:
            previos = json.load(open(a.out, encoding="utf-8"))
        except FileNotFoundError:
            pass
    todos = asignar_ids(previos, nuevos)
    json.dump(todos, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    for i, it in enumerate(nuevos, 1):
        v = it["_verificacion"]
        au = (it.get("author") or [{}])[0].get("family", "s.a.")
        y = (it.get("issued", {}).get("date-parts") or [[None]])[0][0]
        print(f"{i:>2}. [{v.get('puntaje', '-')}] {au} ({y}) {it['title'][:90]} | citas={v.get('citas')} | {it.get('DOI')}")
    if desc:
        print(f"\nDescartadas ({len(desc)}):")
        for d in desc[:10]:
            print(" -", (d.get("titulo") or "")[:80], "|", d["motivo"])
    print(f"\n{len(todos)} fuentes verificadas en {a.out}")


if __name__ == "__main__":
    main()
