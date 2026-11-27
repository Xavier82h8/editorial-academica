#!/usr/bin/env python3
"""Niveles de evidencia de las fuentes (A-E), peso por nivel y «pirámide de fuentes».

  A  norma oficial (ISO/IEC/IEEE/NIST/NOM), artículo de revista arbitrada, actas IEEE/ACM con DOI          peso 1.00
  B  libro o capítulo académico, tesis                                                                      peso 0.80
  C  informe de organismo o gobierno (UNESCO, OCDE, INEGI, leyes y diarios oficiales)                       peso 0.60
  D  documentación de proveedor, software o datos (documentación técnica, repositorios, licencias, datos)    peso 0.30
  E  web, blog, wiki, preprint sin versión publicada                                                         peso 0.15

Se clasifica con, en este orden: (1) el tipo de Crossref (`_verificacion.crossref_type` o el `type` CSL), (2) el tipo de fuente de
OpenAlex (`_verificacion.openalex_source_type`: journal, conference, repository, book series…), (3) patrones del texto de la
referencia (autor organismo de normas, «Proceedings of», volumen(número), editorial de libros, «[Software]», «Recuperado de»),
(4) el dominio de la URL (listas de proveedores y documentación, de blogs y wikis y de organismos). Cada clasificación lleva su
`motivo`: lo que no se puede decidir queda en E con motivo «sin señales de nivel superior» (nunca se sube un nivel por
suposición). El nivel es del tipo de fuente, no de su calidad individual: V1-V3 siguen comprobando que exista y no esté retractada.

clasificar(item, texto=None) -> {"nivel", "motivo", "peso"};  piramide(lista de niveles) -> {"A": n, …};
hallazgos_nivel_bajo(...) -> [Hallazgo FUE-V4N] (afirmaciones sustantivas sostenidas solo por fuentes D/E).
"""
import re
import unicodedata

LIBROS_CR = ("book", "monograph", "book-chapter", "edited-book", "reference-book", "book-section", "book-part", "reference-entry")
PESOS = {"A": 1.0, "B": 0.8, "C": 0.6, "D": 0.3, "E": 0.15}
DESCRIPCION = {"A": "norma oficial o revista arbitrada", "B": "libro o capítulo académico", "C": "informe de organismo o gobierno",
               "D": "documentación de proveedor, software o datos", "E": "web, blog, wiki o preprint"}
BAJOS = ("D", "E")

DOMINIOS_D = ("docs.", "developer.", "developers.", "readthedocs.io", "github.com", "gitlab.com", "huggingface.co", "pypi.org",
              "npmjs.com", "ai.google.dev", "platform.openai.com", "learn.microsoft.com", "docs.aws.amazon.com", "cloud.google.com",
              "kaggle.com", "zenodo.org", "apache.org", "abcjs.net", "tensorflow.org", "pytorch.org", "ollama.com", "anthropic.com",
              "mathworks.com", "python.org", "scikit-learn.org", "numpy.org", "pandas.pydata.org", "unsloth.ai", "nvidia.com",
              "w3.org", "mozilla.org", "developer.mozilla.org", "openai.com", "meta.com", "mistral.ai", "gradio.app", "streamlit.io",
              "musescore.org", "lilypond.org", "abcnotation.com", "creativecommons.org", "opensource.org", "spdx.org")
DOMINIOS_E = ("wikipedia.org", "wikimedia.org", "medium.com", "wordpress.com", "blogspot.com", "substack.com", "towardsdatascience.com",
              "quora.com", "reddit.com", "stackoverflow.com", "stackexchange.com", "youtube.com", "youtu.be", "linkedin.com",
              "facebook.com", "x.com", "twitter.com", "tiktok.com", "instagram.com", "arxiv.org", "ssrn.com", "researchgate.net",
              "academia.edu", "techcrunch.com", "wired.com", "forbes.com", "xataka.com", "genbeta.com", "dev.to", "hackernoon.com",
              "analyticsvidhya.com", "geeksforgeeks.org", "w3schools.com", "tutorialspoint.com", "arc42.org", "blog.")
DOMINIOS_C = ("unesco.org", "oecd.org", "who.int", "worldbank.org", "un.org", "cepal.org", "europa.eu", "inegi.org.mx", "imco.org.mx",
              "conahcyt.mx", "sep.gob.mx", "dof.gob.mx", "diputados.gob.mx", "bunka.go.jp", "itu.int", "wipo.int", "iea.org", "imf.org",
              "ine.mx", "senado.gob.mx", "anuies.mx", "unicef.org", "ilo.org")
SUFIJOS_C = (".gob.mx", ".gov", ".gov.uk", ".gob.es", ".gob.cl", ".gob.ar", ".go.jp", ".gouv.fr", ".edu.mx")  # .edu.mx: informes institucionales

RE_AUTOR_NORMAS = re.compile(r"^(?:ISO|IEC|IEEE|International Organization for Standardization|International Electrotechnical|"
                             r"Institute of Electrical and Electronics Engineers|ANSI|ASTM|ETSI|BSI|CEN|AENOR|UNE|"
                             r"Secretar[ií]a de (?:Econom[ií]a|Salud|Gobernaci[oó]n|Energ[ií]a|Comunicaciones)|NIST|National Institute of Standards)", re.I)
RE_NORMA_TEXTO = re.compile(r"\b(?:ISO(?:/IEC)?(?:/IEEE)?|IEC|IEEE\s+Std\.?|NOM-\d{3}-[A-Z0-9\-]+|NMX-[A-Z]-[\w\-]+|NIST\s+(?:SP|AI|FIPS|IR)\s*[\d\-]+)\b", re.I)
RE_NOM = re.compile(r"\bNOM-\d{3}-[A-Z0-9\-]+|\bNMX-[A-Z]-[\w\-]+")
RE_ACTAS = re.compile(r"\b(?:In\s+)?Proceedings\b|\bActas\s+d[eé]l?\b|\bProc\.\s|\bConference\b|\bSymposium\b|\bWorkshop\b|\bCongreso\b|\bConferencia\b|\bSimposio\b", re.I)
RE_REVISTA = re.compile(r"\b\d{1,4}\s*\(\s*\d{1,4}\s*(?:[-–]\s*\d+)?\s*\)\s*,\s*(?:\d+[-–]\d+|\d{4,8}|e\d+|Article)|"
                        r"\bvol\.?\s*\d+.*\bno\.?\s*\d+.*\bpp\.", re.I)
RE_LIBRO = re.compile(r"\b(?:Wiley|Springer|Pearson|McGraw[- ]Hill|Elsevier|Routledge|Oxford University Press|Cambridge University Press|"
                      r"Longman|MIT Press|Addison[- ]Wesley|O.Reilly|Packt|Manning|Prentice[- ]Hall|CRC Press|Taylor (?:&|and) Francis|"
                      r"Sage|Morgan Kaufmann|Academic Press|Editorial|Ediciones|Alfaomega|Limusa|Paidós|Cengage|Wolters Kluwer|"
                      r"Penguin|Harvard University Press|Princeton University Press|Kogan Page|Apress|Wiley-IEEE Press|Guilford)\b", re.I)
RE_LIBRO_FORMA = re.compile(r"\((?:\d+(?:st|nd|rd|th|\.?\s*ª?)\s+ed\.|Eds?\.|ed\.|2\.?ª ed\.|3\.?ª ed\.)\)|\(\s*Eds?\.\s*\)", re.I)
RE_TESIS = re.compile(r"\[(?:Tesis|Thesis|Dissertation)[^\]]*\]|\b(?:tesis|thesis|dissertation)\s+(?:doctoral|de maestr|de licenciatura|de grado|de posgrado|master)", re.I)
RE_SOFTWARE = re.compile(r"\[(?:Software|Programa inform[aá]tico|Conjunto de datos|Data ?set|Aplicaci[oó]n|App|Biblioteca|Library|Modelo|Model|Directorio[^\]]*)[^\]]*\]|"
                         r"\b(?:documentation|documentaci[oó]n|API reference|user guide|model card|README|release notes|license|licencia)\b", re.I)
# Tipo de documento que pesa más que el dominio: una página de licencia, términos o conjunto de datos es documental (D) aunque
# viva en un foro, wiki o sitio de preguntas (p. ej. la página «Licensing» de Stack Exchange, SPDX, Apache, Creative Commons)
RE_DOC_LICENCIA = re.compile(r"\b(?:licen[cs]es?|licensing|licencias?|licenciamiento|terms\s+(?:of\s+(?:use|service)|and\s+conditions)|"
                             r"t[eé]rminos\s+(?:de\s+(?:uso|servicio)|y\s+condiciones)|condiciones\s+de\s+uso|"
                             r"conjuntos?\s+de\s+datos|data\s?sets?|source\s+code|c[oó]digo\s+fuente)\b|\[(?:software|conjunto de datos|data ?set)[^\]]*\]", re.I)
LICENCIA_DOMINIOS = ("spdx.org", "apache.org", "creativecommons.org", "opensource.org", "gnu.org", "choosealicense.com")
RE_LEY = re.compile(r"^(?:Ley|Reglamento|C[oó]digo|Constituci[oó]n|Decreto|Acuerdo|Diario Oficial)\b|\bDiario Oficial\b|\bBolet[ií]n Oficial\b", re.I)
RE_PREPRINT = re.compile(r"\barXiv\b|\bpreprint\b|\bSSRN\b|\bbioRxiv\b|\bmedRxiv\b|\bResearchGate\b", re.I)
RE_ORG_INFORME = re.compile(r"\b(?:UNESCO|OCDE|OECD|OMS|WHO|CEPAL|ECLAC|INEGI|Banco Mundial|World Bank|Naciones Unidas|United Nations|UNICEF|"
                            r"Secretar[ií]a de|Ministerio de|Instituto Nacional de|Gobierno de|Comisi[oó]n Europea|European Commission|"
                            r"Consejo Nacional|CONAHCYT|CONACYT|ANUIES|SEP\b|Departamento de|Department of)\b", re.I)
RE_INFORME = re.compile(r"\b(?:informe|report|white ?paper|reporte|panorama|estad[ií]sticas|statistics|policy brief|gu[ií]a)\b", re.I)


def _sin(t):
    return "".join(c for c in unicodedata.normalize("NFD", t or "") if unicodedata.category(c) != "Mn")


def _dominio(url):
    m = re.match(r"https?://([^/\s]+)", url or "", re.I)
    return (m.group(1).lower() if m else "")


def _coincide(dom, lista):
    """El dominio es uno de la lista, es subdominio de uno, o empieza por un prefijo terminado en punto («docs.»)."""
    return any(dom.startswith(x) if x.endswith(".") else dom == x or dom.endswith("." + x) for x in lista)


def _autor(it, texto):
    au = (it.get("author") or [{}])[0] if it else {}
    if au.get("literal"):
        return au["literal"]
    if texto:
        m = re.match(r"\s*(.+?)\s*\(\s*(?:\d{4}|s\.\s?f\.|n\.d\.|en prensa)", texto)
        if m:
            return m.group(1)
    return au.get("family") or ""


def _es_doc_licencia(titulo, texto, dom):
    """La referencia dice licencia, términos de uso, conjunto de datos o código (en el título o en el texto sin la URL), o es una
    página oficial de licencias (SPDX, Apache, Creative Commons…)."""
    sin_url = re.sub(r"https?://\S+", " ", f"{titulo} {texto}")
    return bool(RE_DOC_LICENCIA.search(sin_url)) or (bool(dom) and _coincide(dom, LICENCIA_DOMINIOS) and bool(re.search(r"licen|license|terms", (texto or "") + " " + (titulo or ""), re.I)))


def _res(nivel, motivo):
    return {"nivel": nivel, "motivo": motivo, "peso": PESOS[nivel]}


def clasificar(it=None, texto=None):
    """Nivel de evidencia de una fuente. `it`: item CSL (puede traer `_verificacion.crossref_type` y `openalex_source_type`);
    `texto`: la referencia tal cual está en el documento (opcional)."""
    it = it or {}
    texto = " ".join((texto or it.get("_original") or "").split())
    ver = it.get("_verificacion") or {}
    tipo_cr = (ver.get("crossref_type") or "").lower()
    tipo_oa = (ver.get("openalex_source_type") or "").lower()
    tipo = (it.get("type") or "").lower()
    doi = it.get("DOI") or (re.search(r"10\.\d{4,9}/\S+", texto) or [None])[0]
    url = it.get("URL") or (re.search(r"https?://\S+", texto) or [""])[0]
    dom = _dominio(url)
    autor = _autor(it, texto)
    titulo = it.get("title") or texto
    # 0. normas: el autor es el organismo de normas (una página que solo menciona la norma no lo es)
    if RE_NOM.search(texto + " " + str(it.get("number") or "")):
        return _res("A", "norma oficial mexicana (NOM/NMX)")
    if RE_AUTOR_NORMAS.match(autor) and (RE_NORMA_TEXTO.search(titulo + " " + texto + " " + str(it.get("number") or "")) or tipo == "standard"):
        return _res("A", f"norma de {autor.split(',')[0][:40]}")
    if tipo_cr == "standard" or tipo == "standard":
        return _res("A", "tipo de Crossref: norma")
    # 1. tipo de Crossref
    if tipo_cr in ("posted-content",) or ver.get("preprint") and not ver.get("version_publicada"):
        return _res("E", "preprint sin versión publicada" if tipo_cr else "preprint")
    # el tipo de Crossref manda; el de OpenAlex solo decide si Crossref no dio un libro o capítulo
    if tipo_cr == "journal-article" or (tipo_oa == "journal" and tipo_cr not in LIBROS_CR):
        return _res("A", "artículo de revista (Crossref/OpenAlex)")
    if tipo_cr == "proceedings-article" or (tipo_oa == "conference" and tipo_cr not in LIBROS_CR):
        return _res("A", "actas de congreso con DOI (Crossref/OpenAlex)")
    if tipo_cr in LIBROS_CR or (tipo_oa in ("book series", "ebook platform") and not tipo_cr):
        return _res("B", "libro o capítulo (Crossref/OpenAlex)")
    if tipo_cr in ("dissertation",):
        return _res("B", "tesis (Crossref)")
    if tipo_cr in ("report", "report-component", "report-series"):
        return _res("C", "informe (Crossref)")
    if tipo_cr in ("dataset", "database", "software"):
        return _res("D", f"{tipo_cr} (Crossref)")
    if tipo_oa == "repository" and not tipo_cr:
        return _res("E", "repositorio (OpenAlex): sin versión publicada")
    # 2. tipo CSL y patrones del texto
    if RE_PREPRINT.search(texto) or it.get("container-title", "").lower() in ("arxiv", "ssrn electronic journal"):
        return _res("E", "preprint (arXiv/SSRN) sin versión publicada comprobada")
    if tipo in ("software", "dataset") or RE_SOFTWARE.search(texto[:400]) and tipo not in ("article-journal", "book", "chapter"):
        if tipo in ("software", "dataset") or re.search(r"\[(?:Software|Programa|Conjunto|Data|Aplic|App|Bibliot|Library|Modelo|Model|Directorio)", texto, re.I) \
                or _coincide(dom, DOMINIOS_D):
            return _res("D", "software, conjunto de datos o documentación de proveedor")
    if tipo == "legislation" or RE_LEY.search(texto) or RE_LEY.search(titulo or ""):
        return _res("C", "norma jurídica o diario oficial (gobierno)")
    if tipo == "article-journal" or (RE_REVISTA.search(texto) and not RE_ACTAS.search(texto)):
        return _res("A", "artículo de revista (volumen y número)" if tipo != "article-journal" else "tipo de referencia: artículo de revista")
    if tipo == "paper-conference" or RE_ACTAS.search(texto) and (doi or RE_REVISTA.search(texto) or re.search(r"\bpp?\.\s*\d", texto)):
        return _res("A", "actas de congreso")
    if tipo == "thesis" or RE_TESIS.search(texto):
        return _res("B", "tesis")
    if tipo in ("book", "chapter") or RE_LIBRO_FORMA.search(texto[:200]) or (RE_LIBRO.search(texto) and not url):
        return _res("B", "libro o capítulo" + (" (editorial académica)" if RE_LIBRO.search(texto) else ""))
    if tipo == "report" or (_coincide(dom, DOMINIOS_C) or any(dom.endswith(s) for s in SUFIJOS_C)):
        return _res("C", "informe de organismo o gobierno" + (f" ({dom})" if dom else ""))
    if RE_ORG_INFORME.search(autor) and (RE_INFORME.search(texto[:250]) or tipo == "report"):
        return _res("C", f"informe de organismo ({autor[:40]})")
    # 2b. el tipo de documento (licencia, términos, conjunto de datos, código) gana sobre el dominio
    if _es_doc_licencia(titulo, texto, dom) and tipo not in ("article-journal", "book", "chapter", "paper-conference", "thesis"):
        return _res("D", f"documento de licencia, términos o datos: el tipo de documento pesa más que el dominio ({dom or 'sin URL'})")
    # 3. dominio de la URL
    if dom:
        if _coincide(dom, DOMINIOS_E):
            return _res("E", f"web, blog, wiki o preprint ({dom})")
        if _coincide(dom, DOMINIOS_D):
            return _res("D", f"documentación o repositorio de proveedor ({dom})")
        if dom.startswith("docs.") or "/docs" in url.lower() or "documentation" in url.lower():
            return _res("D", f"documentación ({dom})")
    if tipo in ("webpage", "post-weblog", "post", "entry-encyclopedia", "entry-dictionary", "article-newspaper", "article-magazine", "article"):
        return _res("E", "página web, blog, enciclopedia o nota de prensa")
    if doi and not url:
        return _res("E", "DOI sin tipo de obra reconocible: sin señales de nivel superior")
    return _res("E", "sin señales de nivel superior" + (f" ({dom})" if dom else ""))


def piramide(niveles):
    """{"A": n, …, "E": n} para una lista de niveles."""
    return {k: sum(1 for n in niveles if n == k) for k in "ABCDE"}


def texto_piramide(cuenta, total=None):
    total = total if total is not None else sum(cuenta.values())
    lineas = []
    for k in "ABCDE":
        n = cuenta.get(k, 0)
        pct = f"{100 * n / total:.0f} %" if total else "0 %"
        lineas.append(f"  {k} {'#' * n:<{max(1, min(40, max(cuenta.values() or [1])))}} {n:>3} ({pct}) {DESCRIPCION[k]}")
    return "\n".join(lineas)


def peso_medio(niveles):
    return round(sum(PESOS[n] for n in niveles) / len(niveles), 3) if niveles else 0.0


# ---------------------------------------------------------------- FUE-V4N: afirmación sustantiva solo con fuente D/E
RE_SUSTANTIVA = re.compile(
    r"\d+(?:[.,]\d+)?\s*%|\b(?!(?:19|20)\d{2}\b)\d{2,}(?:[.,]\d+)?\b|\b(?:demuestr\w+|muestr\w+|evidenci\w+|concluy\w+|confirm\w+|revel\w+|"
    r"mejor\w+|reduc\w+|aument\w+|increment\w+|supera\w*|super[oó]|logr\w+|eficaz|eficaces|eficiente|eficientes|significativ\w+|"
    r"causa\w*|provoca\w*|garantiz\w+|reportan?|reportó|estim\w+|encuentr\w+|encontr\w+|hall\w+|prueba\w*|"
    r"demonstrat\w+|shows?|showed|found|improv\w+|reduc\w+|increas\w+|outperform\w+)\b", re.I)
MAX_FUE_V4N = 8


def hallazgos_nivel_bajo(pars, cuerpo, entradas, Hallazgo, auditar):
    """FUE-V4N (menor): oraciones sustantivas (cifra, resultado, eficacia) cuyas citas son todas de nivel D/E. Se mide sobre la
    lista de referencias del documento, sin red. Devuelve (hallazgos, niveles por entrada o [])."""
    ents = [e for e in entradas if e["texto"].strip()]
    if not ents or not cuerpo:
        return [], []
    import refs_csl
    items = refs_csl.parsear_lista([e["texto"] for e in ents])
    niv = [clasificar(it, e["texto"]) for it, e in zip(items, ents)]
    por_ent = {id(e): niv[i] for i, e in enumerate(ents)}
    info = auditar.info_entradas(ents)
    H, vistos = [], 0
    for p in cuerpo:
        if p.get("es_titulo") or p.get("en_tabla") or len(p["texto"]) < 40:
            continue
        for o in re.split(r"(?<=[.!?])\s+(?=[A-ZÁÉÍÓÚÑ¿¡\d«\"“])", " ".join(p["texto"].split())):
            if len(o) < 40 or not RE_SUSTANTIVA.search(re.sub(r"\([^()]*\d{4}[a-z]?[^()]*\)", " ", o)):
                continue
            enl = auditar.entradas_citadas([{"texto": o}], info)
            citadas = {id(j["e"]) for ls in enl.values() for j, _ in ls}
            if not citadas:
                continue
            if all(por_ent[i]["nivel"] in BAJOS for i in citadas if i in por_ent) and any(i in por_ent for i in citadas):
                vistos += 1
                if len(H) < MAX_FUE_V4N:
                    niveles = sorted({por_ent[i]["nivel"] for i in citadas if i in por_ent})
                    H.append(Hallazgo("FUE-V4N", "menor", auditar.ubic(p),
                                      f"«{o[:110]}{'…' if len(o) > 110 else ''}» solo la sostiene una fuente de nivel {'/'.join(niveles)}",
                                      "respaldar la afirmación con una fuente de nivel A o B (/fuentes --reemplazar) o presentarla como descripción del proveedor, no como evidencia"))
    if vistos > MAX_FUE_V4N:
        H.append(Hallazgo("FUE-V4N", "menor", "documento", f"{vistos - MAX_FUE_V4N} afirmaciones más con el mismo problema (se muestran {MAX_FUE_V4N})",
                          "revisar todas las afirmaciones sustantivas sostenidas solo por documentación, web o preprint"))
    return H, [n["nivel"] for n in niv]


# ---------------------------------------------------------------- FUE-NIV: bloque `fuentes:` del perfil
ORDEN_NIVEL = "ABCDE"
EVITAR_DOMINIOS = {  # etiqueta -> dominios (o prefijos terminados en punto) y palabras que la delatan en el texto
    "wikipedia": (("wikipedia.org", "wikimedia.org"), ("wikipedia",)),
    "blog": (("medium.com", "wordpress.com", "blogspot.com", "substack.com", "dev.to", "hackernoon.com", "towardsdatascience.com", "blog."), ("blog",)),
    "foro": (("reddit.com", "quora.com", "stackoverflow.com", "stackexchange.com", "foro.", "forum.", "forums."), ("foro", "forum", "reddit", "quora")),
    "redes": (("facebook.com", "x.com", "twitter.com", "instagram.com", "tiktok.com", "linkedin.com"), ()),
    "video": (("youtube.com", "youtu.be"), ()),
}


def _evitar_motivo(texto, evitar):
    """Etiqueta de `evitar` que delata la referencia (dominio de la URL o palabra suelta en el texto), o None."""
    dom = _dominio((re.search(r"https?://\S+", texto) or [""])[0])
    bajo = _sin(texto).lower()
    for et in evitar:
        et = _sin(str(et)).strip().lower()
        doms, palabras = EVITAR_DOMINIOS.get(et, ((et,), (et,)))
        if dom and any(d in dom if not d.endswith(".") else dom.startswith(d) or ("." + d) in dom for d in doms):
            return et
        if any(re.search(r"\b" + re.escape(w) + r"\b", bajo) for w in palabras if len(w) >= 4):
            return et
    return None


def hallazgos_perfil(entradas, bloque, fr, Hallazgo, auditar):
    """FUE-NIV: evalúa `fuentes: {minimo_nivel: B, porcentaje_arbitradas: 70, evitar: [wikipedia, blog, foro]}` del perfil sobre la lista
    de referencias (sin red). Quedan fuera del cálculo las documentales (leyes, licencias, datos, software) y las obras fundacionales
    declaradas en `formato.fuentes_recientes` con su motivo.
      mayor  dominio o tipo de fuente a evitar (wikipedia, blog, foro…)
      menor  referencia bajo el nivel mínimo
      mayor  porcentaje de fuentes arbitradas (nivel A o B) por debajo del pedido
    Devuelve [Hallazgo]."""
    ents = [e for e in entradas if e["texto"].strip()]
    if not ents or not isinstance(bloque, dict):
        return []
    import institucional
    import refs_csl
    minimo = _sin(str(bloque.get("minimo_nivel") or "")).strip().upper()[:1]
    minimo = minimo if minimo in ORDEN_NIVEL else None
    try:
        pct = float(bloque["porcentaje_arbitradas"]) if bloque.get("porcentaje_arbitradas") is not None else None
    except (TypeError, ValueError):
        pct = None
    evitar = [str(x) for x in (bloque.get("evitar") or [])]
    if not (minimo or pct is not None or evitar):
        return []
    items = refs_csl.parsear_lista([e["texto"] for e in ents])
    niv = {id(e): clasificar(it, e["texto"]) for it, e in zip(items, ents)}
    items_titulo = {id(e): it.get("title") or "" for it, e in zip(items, ents)}
    fuera = institucional.clasificar_fuentes(ents, fr or {})
    H = []
    bajo = []
    for e in ents:
        t = " ".join(e["texto"].split())
        if evitar and not _es_doc_licencia(items_titulo.get(id(e), ""), t, _dominio((re.search(r"https?://\S+", t) or [""])[0])):
            et = _evitar_motivo(t, evitar)
            if et:
                H.append(Hallazgo("FUE-NIV", "mayor", auditar.ubic(e), f"«{t[:90]}…» es una fuente a evitar ({et}) según el perfil",
                                  "sustituir por una fuente de nivel A o B (/fuentes --reemplazar)"))
                continue
        if minimo and id(e) not in fuera and ORDEN_NIVEL.index(niv[id(e)]["nivel"]) > ORDEN_NIVEL.index(minimo):
            bajo.append((e, t))
    if bajo:
        ejemplos = "; ".join(f"[{niv[id(e)]['nivel']}] {t[:60]}…" for e, t in bajo[:4])
        H.append(Hallazgo("FUE-NIV", "menor", "lista de referencias",
                          f"{len(bajo)} de {len(ents)} referencias bajo el nivel mínimo {minimo} del perfil: {ejemplos}"
                          + (f" (y {len(bajo) - 4} más)" if len(bajo) > 4 else ""),
                          "reemplazarlas por fuentes de nivel " + minimo + " o mejor (/fuentes --reemplazar), o declararlas documentales o fundacionales con su motivo"))
    if pct is not None:
        info_fr = institucional.literatura_actualizable(ents, fr or {})  # MISMO denominador que INS-008
        base = [e for e, _ in info_fr["base"]]
        arb = [e for e in base if niv[id(e)]["nivel"] in ("A", "B")]
        if base and 100 * len(arb) / len(base) < pct:
            H.append(Hallazgo("FUE-NIV", "mayor", "lista de referencias",
                              f"{len(arb)} de {len(base)} referencias arbitradas (nivel A o B) = {100 * len(arb) / len(base):.0f} % de la literatura actualizable"
                              f"{institucional.texto_exclusion(info_fr)}: el perfil pide al menos {pct:g} %",
                              "sumar fuentes arbitradas o reemplazar las de nivel C, D o E"))
    return H

