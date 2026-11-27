#!/usr/bin/env python3
"""Cierre de fuentes: propone el reemplazo o respaldo de una cita para una oración concreta (`editorial.py fuentes --reemplazar`).

Uso (a través de fuentes.py):
  python scripts/editorial.py fuentes --reemplazar "<oración>" --cita "<texto de la referencia o DOI>" [--n 5] [--out cand.json]
                                      [--contexto <doc.docx>]    (o --doc: contexto del documento)

Nunca aplica cambios: solo propone. Dos pasos:
 1. Si la referencia es un preprint o una página web, busca la versión publicada de la MISMA obra y la propone primero:
    la relación `is-preprint-of` de Crossref, las `locations` de OpenAlex (versión publicada con DOI propio), la búsqueda por
    título y primer autor en Crossref y en OpenAlex, y la ficha de arXiv (`journal_ref`, `doi`). Solo cuenta como misma obra un
    título equivalente con el mismo primer autor.
 2. Busca candidatas de nivel A o B (norma, revista arbitrada, actas, libro; scripts/niveles.py) con consultas derivadas de los
    términos clave de la oración, en español y en inglés (glosario de términos académicos frecuentes; lo que no está en el
    glosario pasa tal cual). Cada candidata trae título, DOI, nivel, año, resumen y el fragmento del resumen que más se parece a la
    oración, con una puntuación de solapamiento simple (0 a 1: términos clave de la oración hallados en título y resumen).
Con `--contexto <doc.docx>` (o `--doc`) se extraen de una copia local del documento 5 a 8 términos de dominio (título de la portada,
palabras clave del resumen y frecuencia en el cuerpo): se exigen en la consulta, se descartan las candidatas cuyo título + resumen
comparta menos de 2 de ellos (sin contexto, una oración suelta trae candidatas de dominios ajenos: genómica, materiales) y la
puntuación es solapamiento con la oración x solapamiento con el dominio. Solo viajan los términos, nunca el texto del documento.
La sustentación real (V5) sigue siendo un juicio: el solapamiento solo ordena y señala dónde mirar. Solo viajan a los servicios
externos términos de la oración, el título y el primer autor de la referencia, nunca el texto del documento.
"""
import datetime as dt
import re
import unicodedata
import urllib.parse

PREFIJOS_PREPRINT = ("10.48550/", "10.31234/", "10.1101/", "10.20944/", "10.21203/", "10.2139/ssrn")
RE_DOI = re.compile(r"10\.\d{4,9}/[^\s\"<>]+")
RE_ARXIV = re.compile(r"arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,5}|[a-z\-]+(?:\.[A-Z]{2})?/\d{7})(?:v\d+)?", re.I)
RE_ARXIV_DOI = re.compile(r"10\.48550/arxiv\.(\S+)", re.I)

STOP = set("""a al algo algunos ante antes aporta aquel aqui as asi aun aunque bajo cada como con contra cual cuales cuando de del desde
donde dos el ella ellos en entre era es esa ese eso esta estas este esto estos fue ha han hay la las le les lo los mas me mi mucho muy
no nos o os otra otro para pero poco por porque que quien se sea segun ser si sido sin sobre solo su sus tambien tanto te todo tras
tu un una uno unos y ya ademas sin embargo asimismo tal vez puede pueden podria muestra mostro reporta reporto estudio
the of and or to in on for with by from as at is are was were be been this that these those it its not no can may might also an a
however moreover thus therefore study studies et al""".split())

# Glosario español -> inglés de términos frecuentes en protocolos de investigación (raíz sin acentos -> equivalentes)
GLOSARIO = {
    "ajust": ["fine-tuning", "fine-tune", "adjust"], "asegur": ["ensure", "guarantee"], "garantiz": ["guarantee", "ensure"],
    "mejor": ["improve", "improvement", "better"], "dato": ["data"], "entren": ["training", "train"], "error": ["errors", "noise", "noisy labels"],
    "ruido": ["noise", "noisy"], "contien": ["contain"], "modelo": ["model", "models"], "lenguaj": ["language"],
    "aprend": ["learning", "learn"], "ensen": ["teaching", "education"], "educa": ["education", "educational"],
    "estudiant": ["students", "student"], "musica": ["music", "musical"], "music": ["music", "musical"],
    "tutor": ["tutor", "tutoring"], "inteligen": ["intelligence", "intelligent"], "artific": ["artificial"],
    "generativ": ["generative"], "evalu": ["evaluation", "evaluate", "assessment"], "rendim": ["performance"],
    "desempen": ["performance"], "usabil": ["usability"], "calidad": ["quality"], "fiabil": ["reliability"],
    "confiab": ["reliability", "trustworthy"], "sesgo": ["bias"], "alucin": ["hallucination", "hallucinations"],
    "retroaliment": ["feedback"], "motiv": ["motivation"], "gamific": ["gamification"], "ludic": ["gamified", "game-based"],
    "adaptativ": ["adaptive"], "personaliz": ["personalized", "personalization"], "carga": ["load"], "cognitiv": ["cognitive"],
    "prueba": ["test", "evaluation"], "resultado": ["results", "outcomes"], "eficac": ["effectiveness", "effective"],
    "eficien": ["efficiency", "efficient"], "riesgo": ["risk"], "seguridad": ["security", "safety"], "privacidad": ["privacy"],
    "derecho": ["copyright", "rights"], "licenc": ["license", "licensing"], "notacion": ["notation"], "partitur": ["score", "sheet music"],
    "interfaz": ["interface"], "usuario": ["user", "users"], "experienc": ["experience"], "sistema": ["system", "systems"],
    "arquitect": ["architecture"], "software": ["software"], "requisit": ["requirements"], "metodolog": ["methodology"],
    "analisis": ["analysis"], "muestra": ["sample"], "encuest": ["survey", "questionnaire"], "entrevist": ["interview", "interviews"],
    "docent": ["teacher", "instructor"], "profesor": ["teacher", "instructor"], "escuela": ["school"], "universit": ["university"],
    "estudio": ["study"], "revision": ["review"], "sistematic": ["systematic"], "escalab": ["scalability"], "latenc": ["latency"],
    "memoria": ["memory"], "red": ["network"], "neuron": ["neural"], "transform": ["transformer"], "corpus": ["corpus", "dataset"],
    "etiquet": ["labels", "annotation"], "anotac": ["annotation"], "sintetic": ["synthetic"], "pequen": ["small"], "gran": ["large"],
    "texto": ["text"], "voz": ["speech", "voice"], "audio": ["audio"], "imagen": ["image"], "video": ["video"],
    "asesor": ["advisor", "advising"], "orient": ["guidance", "advising"], "recomend": ["recommendation", "recommender"],
}


def _sin(t):
    return "".join(c for c in unicodedata.normalize("NFD", t or "") if unicodedata.category(c) != "Mn")


def _fold(t):
    return _sin(t).lower()


def _palabras(t):
    return re.findall(r"[a-zñ0-9][a-zñ0-9\-]+", _fold(t))


def _raiz(w):
    return w[:5]


def terminos_clave(oracion, max_n=8):
    """Términos clave de la oración (sin citas entre paréntesis, sin palabras vacías), por orden de aparición; largos primero si sobran."""
    sin_citas = re.sub(r"\([^()]*\d{4}[a-z]?[^()]*\)", " ", oracion or "")
    sin_citas = re.sub(r"\b[A-ZÁÉÍÓÚ][\wáéíóú\-]+(?: et al\.?)?\s*\(\s*\d{4}[a-z]?\s*\)", " ", sin_citas)
    vistos, out = set(), []
    for w in _palabras(sin_citas):
        if w in STOP or len(w) < 4 or w.isdigit() or w in vistos:
            continue
        vistos.add(w)
        out.append(w)
    if len(out) > max_n:
        mantener = set(sorted(out, key=lambda x: (-len(x), out.index(x)))[:max_n])
        out = [w for w in out if w in mantener]
    return out


def a_ingles(terminos, formas=1):
    """Equivalentes en inglés por glosario (la primera forma de cada término en la consulta); los términos sin entrada pasan tal cual
    (cognados)."""
    out = []
    for t in terminos:
        eq = next((v for k, v in GLOSARIO.items() if t.startswith(k)), None)
        for x in (eq[:formas] if eq else [t]):
            if x not in out:
                out.append(x)
    return out


def es_ingles(oracion):
    pal = _palabras(oracion)
    en = sum(w in ("the", "of", "and", "with", "that", "is", "are", "was", "for", "to", "in") for w in pal)
    es = sum(w in ("el", "la", "los", "las", "de", "del", "que", "con", "por", "para", "una", "un", "se", "no", "y", "en") for w in pal)
    return en > es


# ---------------------------------------------------------------- contexto del documento
PORTADA_STOP = set("""tecnologico nacional mexico instituto departamento sistemas computacion asignatura protocolo investigacion taller
docente grupo ingenieria Ciudad Ejemplo Estado universidad facultad escuela licenciatura maestria doctorado tesis tesina informe reporte
resumen indice contenido abstract keywords introduccion conclusiones referencias bibliografia apendice anexo capitulo seccion tabla figura
noviembre diciembre enero febrero marzo abril mayo junio julio agosto septiembre octubre""".split())
ACADEMICAS = set("""proyecto sistema sistemas estudio estudios objetivo objetivos desarrollo resultados resultado metodologia metodo metodos
documento trabajo marco teorico problema analisis propuesta presente mediante forma manera parte partes tipo tipos nivel niveles
general generales especifico especificos describe descripcion definicion proceso procesos uso usos usar usado principal principales
puede pueden debe deben tambien ademas entre sobre desde hasta cada otros otras todos todas misma mismo mismos mismas lugar tiempo
etapa etapas fase fases ejemplo ejemplos caso casos aspectos aspecto elementos elemento contexto actual actuales siguiente siguientes
parrafo pagina paginas autor autores anio anios fuente fuentes citas cita datos informacion herramienta herramientas""".split())


def _lineas_documento(ruta):
    """(portada, palabras_clave, cuerpo) de un .docx: líneas de la portada (antes del resumen), la línea de palabras clave y el texto
    del cuerpo. Solo lectura de una copia local; nada de esto sale de la máquina salvo los términos elegidos."""
    import docx
    d = docx.Document(str(ruta))
    pars = [" ".join(p.text.split()) for p in d.paragraphs if p.text.strip()]
    i_res = len(pars)
    for i, t in enumerate(pars):
        if re.match(r"(?i)^(?:\d+\.?\s*)?(?:resumen|abstract)\s*$", t):
            i_res = i
            break
    portada = pars[:i_res][:14]
    clave = ""
    for t in pars:
        m = re.match(r"(?i)^(?:palabras\s+clave|keywords?)\s*[:.]\s*(.+)$", t)
        if m:
            clave = m.group(1)
            break
    cuerpo = [t for t in pars[i_res:] if len(t) > 40]
    return portada, clave, cuerpo


def terminos_dominio(ruta, max_n=8, min_n=5):
    """5-8 términos de dominio del documento, por puntuación: palabras clave del resumen (3), título de la portada (2) y frecuencia en el
    cuerpo (hasta 3 por frecuencia relativa). Quita palabras vacías, de portada y académicas genéricas. Devuelve la lista de términos
    (formas del documento, sin acentos, en minúsculas) de mayor a menor puntuación."""
    portada, clave, cuerpo = _lineas_documento(ruta)
    vacias = STOP | PORTADA_STOP | ACADEMICAS
    pts, forma = {}, {}

    def contar(texto, peso=None, cont=None):
        for w in _palabras(texto):
            if w in vacias or len(w) < 5 or w.isdigit() or re.match(r"^[a-z]+-[a-z]{1,3}$", w):  # sin nombres propios tipo «XXXX-AI»
                continue
            r = _raiz(w)
            if peso is not None:
                pts[r] = pts.get(r, 0.0) + peso
            if cont is not None:
                cont[r] = cont.get(r, 0) + 1
            forma.setdefault(r, {}).setdefault(w, 0)
            forma[r][w] += 1

    # el título es la línea de la portada con más palabras de contenido y sin institución (se aceptan dos líneas seguidas)
    titulos = [t for t in portada if len([w for w in _palabras(t) if w not in vacias and len(w) >= 5]) >= 2
               and not re.match(r"(?i)^(?:docente|profesor|asesor|mc\.|dra?\.|ing\.|lic\.|integrantes?)", t)]
    for t in titulos[:2]:
        contar(t, peso=2.0)
    contar(clave, peso=3.0)
    cont = {}
    for t in cuerpo:
        contar(t, cont=cont)
    if cont:
        top = max(cont.values())
        for r, n in cont.items():
            pts[r] = pts.get(r, 0.0) + 3.0 * n / top
    out = []
    for r in sorted(pts, key=lambda r: (-pts[r], r)):
        w = max(forma[r], key=lambda x: (forma[r][x], -len(x)))
        if w not in out:
            out.append(w)
        if len(out) >= max_n:
            break
    return out


def _grupos_dominio(terminos):
    """[(término, formas raíz con equivalentes en inglés)] para medir el solapamiento con el dominio."""
    grupos = []
    for t in terminos:
        formas = {_raiz(t)}
        eq = next((v for k, v in GLOSARIO.items() if t.startswith(k)), None)
        for e in eq or []:
            for w in _palabras(e):
                if len(w) >= 4:
                    formas.add(_raiz(w))
        grupos.append((t, formas))
    return grupos


def solapamiento_dominio(terminos, titulo, resumen):
    """(fracción 0-1 de términos de dominio hallados en título + resumen, lista de hallados)."""
    if not terminos:
        return 1.0, []
    raices = {_raiz(w) for w in _palabras((titulo or "") + " " + (resumen or ""))}
    hallados = [t for t, formas in _grupos_dominio(terminos) if formas & raices]
    return round(len(hallados) / len(terminos), 3), hallados


MIN_DOMINIO = 2  # una candidata debe compartir al menos 2 términos de dominio con el documento


def consultas(oracion, dominio=None):
    """[(idioma, consulta)]: español (términos clave) e inglés (glosario). Una oración en inglés solo da la consulta en inglés.
    Con `dominio` (términos del documento) se exigen en la consulta: hasta 3 términos de dominio que la oración no trae."""
    claves = terminos_clave(oracion)
    dom = [t for t in (dominio or []) if t not in claves]
    if not dom:
        if es_ingles(oracion):
            return [("en", " ".join(claves))] if claves else []
        out = []
        if claves:
            out.append(("es", " ".join(claves[:7])))
        if a_ingles(claves):
            out.append(("en", " ".join(a_ingles(claves)[:8])))
        return out
    # los términos de dominio se exigen en cada consulta, de dos en dos (rotando) para que un solo término no arrastre el tema
    cortes = [dom[i:i + 2] for i in range(0, min(len(dom), 6), 2)] or [dom[:2]]
    out = []
    if es_ingles(oracion):
        return [("en", " ".join(claves[:6] + c)) for c in cortes]
    out.append(("es", " ".join(claves[:5] + cortes[0])))
    for c in cortes:
        out.append(("en", " ".join(a_ingles(claves[:5] + c)[:8])))
    return out


def _conjunto_oracion(oracion):
    """Términos clave de la oración con sus equivalentes en inglés: cada término cuenta una vez si alguna forma aparece."""
    claves = terminos_clave(oracion, max_n=12)
    grupos = []
    for t in claves:
        formas = {_raiz(t)}
        eq = next((v for k, v in GLOSARIO.items() if t.startswith(k)), None)
        for e in eq or []:
            for w in _palabras(e):
                if len(w) >= 4:
                    formas.add(_raiz(w))
        grupos.append((t, formas))
    return grupos


def solapamiento(oracion, titulo, resumen):
    """(puntuación 0-1, términos coincidentes, fragmento del resumen que más se parece a la oración)."""
    grupos = _conjunto_oracion(oracion)
    if not grupos:
        return 0.0, [], ""
    texto = _palabras((titulo or "") + " " + (resumen or ""))
    raices = {_raiz(w) for w in texto}
    hallados = [t for t, formas in grupos if formas & raices]
    punt = round(len(hallados) / len(grupos), 3)
    frag, mejor = "", 0
    for s in re.split(r"(?<=[.!?])\s+", (resumen or "").strip()):
        rs = {_raiz(w) for w in _palabras(s)}
        n = sum(1 for _, formas in grupos if formas & rs)
        if n > mejor:
            mejor, frag = n, s.strip()
    return punt, hallados, frag[:400]


# ---------------------------------------------------------------- la referencia original
def analizar_cita(F, cita):
    """{doi, titulo, apellido, anio, texto, arxiv, tipo_obra, preprint, web} de la referencia dada (DOI suelto o texto APA)."""
    cita = " ".join((cita or "").split())
    m = RE_DOI.search(cita)
    doi = m.group(0).rstrip(".,;)") if m else None
    arx = RE_ARXIV.search(cita)
    arxiv_id = arx.group(1) if arx else None
    ma = RE_ARXIV_DOI.search(cita)
    if ma and not arxiv_id:
        arxiv_id = re.sub(r"v\d+$", "", ma.group(1))
    if arxiv_id and not doi:
        doi = "10.48550/arXiv." + arxiv_id
    info = {"doi": doi, "titulo": "", "apellido": "", "anio": None, "texto": cita, "arxiv": arxiv_id, "tipo_crossref": None, "origen_meta": None}
    meta = None
    if doi:
        try:
            meta = F.metadatos_doi(doi)
        except Exception:  # noqa: BLE001
            meta = None
    if meta:
        a1 = (meta.get("author") or [{}])[0]
        info.update(titulo=F.limpiar_titulo(meta.get("title") if isinstance(meta.get("title"), str) else (meta.get("title") or [""])[0]),
                    apellido=a1.get("family") or a1.get("name") or a1.get("literal") or "", anio=meta.get("year"),
                    tipo_crossref=meta.get("type"), origen_meta=meta.get("registro"))
    if not info["titulo"] and cita:
        try:
            import refs_csl
            it = refs_csl.parsear_lista([cita])[0]
        except Exception:  # noqa: BLE001
            it = {}
        a1 = (it.get("author") or [{}])[0]
        info.update(titulo=F.limpiar_titulo(it.get("title") or ""), apellido=a1.get("family") or a1.get("literal") or "",
                    anio=((it.get("issued") or {}).get("date-parts") or [[None]])[0][0], origen_meta="texto")
        if not doi and it.get("DOI"):
            info["doi"] = it["DOI"]
    if not info["anio"]:
        y = re.search(r"\((\d{4})[a-z]?[,)]", cita)
        info["anio"] = int(y.group(1)) if y else None
    return info


def es_preprint_o_web(info):
    doi = (info.get("doi") or "").lower()
    texto = info.get("texto") or ""
    if info.get("tipo_crossref") == "posted-content" or doi.startswith(PREFIJOS_PREPRINT) or info.get("arxiv"):
        return "preprint"
    if re.search(r"\bpreprint\b|\bSSRN\b|\bbioRxiv\b|\bmedRxiv\b", texto, re.I):
        return "preprint"
    import niveles
    nivel = niveles.clasificar({"title": info.get("titulo")}, texto)
    if nivel["nivel"] in ("D", "E"):
        return "web" if not doi else "preprint" if "preprint" in nivel["motivo"] else "web"
    return None


# ---------------------------------------------------------------- paso 1: versión publicada de la misma obra
def _misma_obra(F, info, titulo, autores):
    """Título equivalente y primer autor (apellido) que coincide."""
    if not F.titulos_equivalentes(titulo, info["titulo"]):
        return False
    fa = F._norm(info["apellido"])
    if not fa:
        return True
    a1 = (autores or [{}])[0]
    fm = F._norm(a1.get("family") or a1.get("name") or a1.get("literal") or "")
    return bool(fm) and (fa in fm or fm in fa)


def _no_preprint(doi):
    return bool(doi) and not doi.lower().startswith(PREFIJOS_PREPRINT)


def versiones_publicadas(F, info, avisos):
    """[(doi, origen)] de la versión publicada de la misma obra, sin repetir y sin el propio preprint."""
    out, vistos = [], set()

    def agregar(doi, origen):
        doi = (doi or "").replace("https://doi.org/", "").strip().rstrip("/")
        k = doi.lower()
        if _no_preprint(doi) and k != (info.get("doi") or "").lower() and k not in vistos:
            vistos.add(k)
            out.append((doi, origen))

    doi = info.get("doi")
    if doi and (doi.lower().startswith(PREFIJOS_PREPRINT) or info.get("tipo_crossref") == "posted-content"):
        try:
            meta = F.metadatos_doi(doi) or {}
            pub = F.integridad(doi, meta).get("version_publicada")
            if pub:
                agregar(pub, "Crossref (is-preprint-of) / OpenAlex (versión publicada de la obra)")
        except Exception as ex:  # noqa: BLE001
            avisos.append(F._motivo_red(ex, "relación preprint -> versión publicada"))
    if info.get("arxiv"):
        try:
            xml = F.get_texto("http://export.arxiv.org/api/query?id_list=" + urllib.parse.quote(info["arxiv"]))
            for tag in ("arxiv:doi",):
                m = re.search(r"<" + tag + r"[^>]*>([^<]+)</" + tag + ">", xml or "")
                if m:
                    agregar(m.group(1).strip(), "ficha de arXiv (doi declarado por los autores)")
        except Exception as ex:  # noqa: BLE001
            avisos.append(F._motivo_red(ex, "ficha de arXiv"))
    titulo = info.get("titulo") or ""
    if len(titulo) >= 12:
        try:
            doi_t, _motivo = F.doi_por_metadatos_motivo({"title": titulo, "type": "article-journal",
                                                         "author": [{"family": info.get("apellido") or ""}],
                                                         "issued": {"date-parts": [[info.get("anio")]]} if info.get("anio") else {}})
            if doi_t:
                agregar(doi_t, "Crossref: mismo título y primer autor")
        except Exception as ex:  # noqa: BLE001
            avisos.append(F._motivo_red(ex, "búsqueda por título en Crossref"))
        try:
            q = urllib.parse.urlencode({"search": titulo, "per-page": "5", "select": "doi,title,authorships,publication_year,locations,type"})
            d = F.get("https://api.openalex.org/works?" + q) or {}
            for w in d.get("results", []):
                autores = [{"name": (a.get("author") or {}).get("display_name", "").split()[-1] if (a.get("author") or {}).get("display_name") else ""}
                           for a in w.get("authorships") or []]
                if not _misma_obra(F, info, w.get("title") or "", autores):
                    continue
                cands = [(w.get("doi") or "")]
                cands += [loc.get("landing_page_url") or "" for loc in w.get("locations") or [] if loc.get("version") == "publishedVersion"]
                for c in cands:
                    c = c.replace("https://doi.org/", "")
                    if c.startswith("10."):
                        agregar(c, "OpenAlex: misma obra con versión publicada")
        except Exception as ex:  # noqa: BLE001
            avisos.append(F._motivo_red(ex, "búsqueda por título en OpenAlex"))
    return out


# ---------------------------------------------------------------- candidatas
def _item(F, m, w=None):
    """Crossref message -> CSL con resumen y tipo de fuente de OpenAlex (para el nivel)."""
    resumen = F.resumen_openalex((w or {}).get("abstract_inverted_index")) if w else ""
    src_tipo = (((w or {}).get("primary_location") or {}).get("source") or {}).get("type")
    extra = {"crossref_type": m.get("type")}
    if src_tipo:
        extra["openalex_source_type"] = src_tipo
    return F.a_csl(m, resumen=resumen, extra=extra)


def _ficha(F, it, oracion, origen=None, misma_obra=False, dominio=None):
    import niveles
    nv = niveles.clasificar(it)
    punt, hallados, frag = solapamiento(oracion, it.get("title", ""), it.get("abstract", ""))
    anio = ((it.get("issued") or {}).get("date-parts") or [[None]])[0][0]
    a1 = (it.get("author") or [{}])[0]
    pd, td = solapamiento_dominio(dominio, it.get("title", ""), it.get("abstract", "")) if dominio else (None, [])
    return {"titulo": it.get("title"), "doi": it.get("DOI"), "primer_autor": a1.get("family") or a1.get("literal"), "anio": anio,
            "nivel": nv["nivel"], "nivel_motivo": nv["motivo"], "revista": it.get("container-title"),
            "resumen": it.get("abstract") or "", "fragmento": frag, "coincidencia": punt, "terminos": hallados,
            **({"dominio": pd, "terminos_dominio": td, "puntuacion": round(punt * pd, 3)} if dominio else {}),
            **({"origen": origen} if origen else {}), **({"misma_obra": True} if misma_obra else {})}


def proponer(F, oracion, cita, n=5, desde=None, contexto=None):
    """Resultado completo: {oracion, cita, tipo_original, version_publicada, candidatas, consultas, avisos, dominio}. Solo propone.
    `contexto`: ruta de un .docx (se extraen los términos de dominio) o lista de términos ya elegidos."""
    oracion = " ".join((oracion or "").split())
    avisos = []
    dominio = None
    if contexto:
        dominio = list(contexto) if isinstance(contexto, (list, tuple)) else terminos_dominio(contexto)
        if len(dominio) < MIN_DOMINIO:
            avisos.append("el contexto dio menos de 2 términos de dominio: no se filtra por dominio")
            dominio = None
    info = analizar_cita(F, cita)
    tipo = es_preprint_o_web(info)
    res = {"oracion": oracion, "cita": {k: v for k, v in info.items() if k != "texto"} | {"texto": info["texto"][:300]},
           "tipo_original": tipo, "version_publicada": [], "candidatas": [], "consultas": [], "avisos": avisos,
           "dominio": dominio or [], "descartadas_por_dominio": 0}
    propios = {(info.get("doi") or "").lower()}
    if tipo:
        for doi, origen in versiones_publicadas(F, info, avisos):
            try:
                m = F.crossref(doi)
            except Exception as ex:  # noqa: BLE001
                avisos.append(F._motivo_red(ex, f"DOI {doi} sin comprobar en Crossref"))
                continue
            if not m:
                avisos.append(f"{doi}: no resuelve en Crossref, no se propone")
                continue
            w = None
            try:
                w = F.get("https://api.openalex.org/works/doi:" + urllib.parse.quote(doi, safe="/")
                          + "?select=abstract_inverted_index,primary_location,type")
            except Exception:  # noqa: BLE001
                pass
            it = _item(F, m, w)
            res["version_publicada"].append(_ficha(F, it, oracion, origen, misma_obra=True, dominio=dominio))
            propios.add(doi.lower())
        if not res["version_publicada"]:
            avisos.append("no se halló versión publicada de la misma obra: sigue siendo preprint/web; conviene una fuente A o B que respalde la oración")
    hasta = dt.date.today().year
    desde = desde or hasta - 10
    vistos = set(propios)
    cand = []
    for idioma, q in consultas(oracion, dominio):
        res["consultas"].append({"idioma": idioma, "consulta": q})
        try:
            obras = F.openalex_buscar(q, max(n, 5), desde, None, False)
        except Exception as ex:  # noqa: BLE001
            avisos.append(F._motivo_red(ex, f"búsqueda «{q[:40]}»"))
            continue
        for w in obras:
            doi = (w.get("doi") or "").replace("https://doi.org/", "")
            if not doi or doi.lower() in vistos or doi.lower().startswith(PREFIJOS_PREPRINT):
                continue
            vistos.add(doi.lower())
            try:
                m = F.crossref(doi)
            except Exception as ex:  # noqa: BLE001
                avisos.append(F._motivo_red(ex, f"DOI {doi} sin comprobar"))
                continue
            if not m:
                continue
            it = _item(F, m, w)
            ficha = _ficha(F, it, oracion, dominio=dominio)
            if ficha["nivel"] not in ("A", "B"):
                continue
            if dominio and len(ficha["terminos_dominio"]) < MIN_DOMINIO:
                res["descartadas_por_dominio"] += 1  # dominio ajeno al documento: título + resumen sin 2 términos de dominio
                continue
            cand.append(ficha)
    if dominio:
        cand.sort(key=lambda c: (-c["puntuacion"], -c["coincidencia"], -(c["anio"] or 0)))
    else:
        cand.sort(key=lambda c: (-c["coincidencia"], -(c["anio"] or 0)))
    res["candidatas"] = cand[:n]
    if not res["consultas"]:
        avisos.append("la oración no tiene términos clave suficientes para buscar")
    return res


def imprimir(res):
    print(f"Oración: {res['oracion'][:160]}")
    c = res["cita"]
    print(f"Referencia: {c.get('titulo') or c.get('texto', '')[:100]} ({c.get('anio') or 's. f.'}), DOI {c.get('doi') or '-'}"
          + (f" [{res['tipo_original']}]" if res["tipo_original"] else ""))
    if res["version_publicada"]:
        print("Versión publicada de la misma obra (propuesta primero):")
        for v in res["version_publicada"]:
            print(f"  * {v['primer_autor']} ({v['anio']}) {v['titulo'][:100]} | {v['doi']} | nivel {v['nivel']} | {v['origen']}")
    if res.get("dominio"):
        print(f"Contexto del documento: {', '.join(res['dominio'])} (candidatas con menos de 2 términos de dominio descartadas: {res['descartadas_por_dominio']})")
    print(f"Candidatas A/B por la oración ({len(res['candidatas'])}) con consultas "
          + "; ".join(f"[{q['idioma']}] {q['consulta']}" for q in res["consultas"]) + ":")
    for i, v in enumerate(res["candidatas"], 1):
        punt = f"{v['puntuacion']:.2f} = {v['coincidencia']:.2f} x {v['dominio']:.2f}" if "puntuacion" in v else f"{v['coincidencia']:.2f}"
        print(f"{i:>2}. [{punt}] nivel {v['nivel']} {v['primer_autor']} ({v['anio']}) {v['titulo'][:90]} | {v['doi']}")
        if v["fragmento"]:
            print(f"      resumen: «{v['fragmento'][:220]}»")
    for a in res["avisos"]:
        print("aviso:", a)
    print("Solo se propone: no se cambió ningún documento. Comprueba el resumen contra la oración antes de citar (V5).")
