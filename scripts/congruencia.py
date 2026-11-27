#!/usr/bin/env python3
"""Revisor determinista de congruencia interna de un documento académico (.md o .docx).

Uso: python -I scripts/congruencia.py <doc> [--json salida.json]
Salida: 0 sin hallazgos o solo menores; 1 con hallazgos críticos o mayores; 2 error de uso o de entrada (ver cli.py).
Función importable: revisar(path) -> {"documento","hallazgos","conteo","secciones_detectadas"}.

Reglas (IDs CON-xxx; salida con el mismo formato que auditar.py):
- CON-001 crítica: tamaño de muestra distinto entre Resumen / Método / Resultados / Discusión / Conclusiones.
- CON-002 mayor: porcentajes de una misma distribución que suman más de 100.5.
- CON-003 mayor: sigla definida más de una vez.
- CON-004 menor: sigla usada antes de su definición.
- CON-005 mayor: referencia cruzada rota (Tabla/Figura/Apéndice sin rótulo ni encabezado).
- CON-006 mayor: promesa incumplida («en la sección de X» sin encabezado X).
- CON-007 mayor: lenguaje causal en Discusión/Conclusiones con diseño no experimental.
- CON-008 menor: el texto repite la tabla. Un párrafo que menciona «Tabla N» (o está entre los 3 que siguen a la tabla
  y su nota) trae >= 4 cifras, autores o siglas de esa tabla, y ellos son >= 50 % de las cifras y nombres del párrafo.
  Solo .docx (el lector md no marca tablas). Práctica editorial: el snapshot APA no trae una regla de duplicación.
- CON-009 menor: redundancia. Oraciones (>= 12 palabras) casi duplicadas en párrafos distintos: shingles de 5 palabras
  normalizadas, Jaccard >= 0.6 (>= 0.85 si una está en el resumen). Excluye citas textuales, rótulos, notas, celdas, referencias.
- CON-018 menor: tras definir una sigla, la forma completa reaparece >= 2 veces sin la sigla al lado (APA 6.25: tras definirla,
  usar solo la abreviatura). Excluye encabezados, tablas, referencias y el resumen (APA: definirla en el resumen y en el texto).
- CON-019 mayor: numeración de tablas, figuras y apéndices: huecos (Tabla 1, 2, 4), rótulos duplicados o primera mención fuera
  de orden (Tabla 3 antes que Tabla 2). APA cap. 7 (tablas/figuras en orden de mención) y 2.14 (apéndices en orden).
- CON-020 mayor: objetivo o pregunta sin rastro: ningún término clave del objetivo (bajo un encabezado «Objetivos»/«Preguntas
  de investigación») aparece en método, resultados, discusión ni conclusiones (ni cronograma/plan de análisis). Práctica editorial.
- CON-021 menor: título y objetivo general no coinciden: el núcleo del título (objeto y propósito, sin sigla, método ni promesas) debe
  aparecer en el objetivo general (minúsculas, sin acentos, raíz de 5 letras); falla si falta el 30 % o más de ≥ 4 términos de núcleo.
  Necesita el título de la portada (o `title:` del YAML) y la sección «Objetivo general». Práctica editorial (receta en
  skills/editorial-academica/references/titulo.md; `editorial.py titulo` da el diagnóstico completo).
Las reglas 1 y 7 necesitan secciones identificadas por encabezado; sin ellas solo corren las reglas 2-6.
"""
import argparse
import json
import pathlib
import re
import sys
import unicodedata

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import auditar  # noqa: E402
import cli  # noqa: E402
import yaml  # noqa: E402

Hallazgo = auditar.Hallazgo
sin_acentos = auditar.sin_acentos

SECCIONES = {
    "resumen": ("resumen", "abstract", "resumen ejecutivo", "summary"),
    "metodo": ("metodo", "metodologia", "materiales y metodos", "metodos", "method", "methods", "methodology",
               "materials and methods", "diseno metodologico", "marco metodologico"),
    "resultados": ("resultados", "results", "resultados y discusion", "results and discussion"),
    "discusion": ("discusion", "discussion"),
    "conclusiones": ("conclusion", "conclusiones", "conclusions", "conclusiones y recomendaciones",
                     "consideraciones finales"),
}
ORDEN_SEC = ["resumen", "metodo", "resultados", "discusion", "conclusiones"]
RE_NUMERACION = re.compile(r"^\s*(?:\d+(?:\.\d+)*\.?|[IVXLC]+\.)\s+")


# ---------------------------------------------------------------- lectura
def norm_titulo(t):
    t = sin_acentos(t.lower())
    t = RE_NUMERACION.sub("", t.strip())
    t = re.sub(r"^[ivxlc]+\.\s+", "", t)
    t = re.sub(r"[^\w\s]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def clave_seccion(texto):
    n = norm_titulo(texto)
    for k, nombres in SECCIONES.items():
        if n in nombres:
            return k
    if n.startswith("resultados y discusion") or n.startswith("results and discussion"):
        return "resultados"
    return None


def leer_md(path):
    """Devuelve (pars, abstract_yaml): auditar.cargar_md sin el bloque YAML, con su `abstract` aparte."""
    pars, meta = auditar.cargar_md(path, frontmatter=True)
    return pars, (str(meta["abstract"]).strip() if meta.get("abstract") else None)


def cargar(path):
    abstract = None
    if str(path).lower().endswith(".docx"):
        pars, _ = auditar.cargar_docx(str(path))
    else:
        pars, abstract = leer_md(path)
    for p in pars:
        p["texto"] = unicodedata.normalize("NFC", p["texto"]).replace(" ", " ").replace(" ", " ")
    pars = [p for p in pars if not p.get("nota_pie")]
    return pars, abstract


def asignar_secciones(cuerpo):
    """Marca cada párrafo con p['sec']. Un encabezado conocido cambia de sección; uno desconocido mantiene la
    actual (subsección), salvo en el resumen, donde termina (APA repite el título tras el resumen)."""
    sec = None
    for p in cuerpo:
        if p.get("es_titulo"):
            k = clave_seccion(p["texto"])
            if k:
                sec = k
            elif sec == "resumen" or sec is None:
                sec = None
            p["sec"] = None
            p["encabezado"] = True
            continue
        if sec == "resumen" and re.match(r"\s*(palabras clave|keywords?|key words)\b", p["texto"], re.I):
            sec = None
        p["sec"] = sec
    return cuerpo


def ubicar(p):
    if p.get("yaml"):
        return f"YAML abstract: «{p['texto'][:50]}…»"
    return auditar.ubic(p)


# ---------------------------------------------------------------- utilidades de texto
RE_CITA_MD = re.compile(r"\[[^\]]*@[^\]]*\]")
RE_CITA_IEEE = re.compile(r"\[\d+(?:\s*[,–-]\s*\d+)*\]")
RE_CITA_PAR = re.compile(r"\([^()]*\b(?:1[5-9]|20)\d{2}[a-z]?\b[^()]*\)")


def sin_citas(t):
    t = RE_CITA_MD.sub(" ", t)
    t = RE_CITA_IEEE.sub(" ", t)
    return RE_CITA_PAR.sub(" ", t)


def oraciones(t):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+(?=[A-ZÁÉÍÓÚÑ¿¡\d«\"“])", t) if s.strip()]


def entero(s):
    s = s.strip()
    if re.fullmatch(r"\d{1,3}(?:[.,]\d{3})+", s):
        return int(re.sub(r"[.,]", "", s))
    return int(s) if s.isdigit() else None


# ---------------------------------------------------------------- CON-001
SUSTANTIVOS = (r"participantes|estudiantes|docentes|encuestados|personas|sujetos|profesores|alumnos|pacientes|"
               r"adultos|usuarios|trabajadores|empleados|participants|students|respondents|teachers|patients|subjects")
RE_N_IGUAL = re.compile(r"(?<![A-Za-z])[nN]\s*=\s*(\d{1,3}(?:[.,]\d{3})+|\d+)(?![\d.,]*\d)")
RE_N_SUST = re.compile(r"(?<![\d.,])(\d{1,3}(?:[.,]\d{3})+|\d+)\s+(?:[a-záéíóúñ]+\s+)?(?:" + SUSTANTIVOS + r")\b", re.I)


def valores_n(t):
    t = sin_citas(t)
    out = []
    for m in RE_N_IGUAL.finditer(t):
        v = entero(m.group(1))
        if v:
            out.append(v)
    for m in RE_N_SUST.finditer(t):
        v = entero(m.group(1))
        if v and not (1900 <= v <= 2100 and re.fullmatch(r"\d{4}", m.group(1))):
            out.append(v)
    return out


def n_total(valores):
    """El n más frecuente de la sección; en empate, el mayor (el total, no un subgrupo)."""
    if not valores:
        return None
    cuenta = {}
    for v in valores:
        cuenta[v] = cuenta.get(v, 0) + 1
    return max(cuenta, key=lambda v: (cuenta[v], v))


def regla_muestra(cuerpo):
    """Compara cada sección con el Método. Sin n en el Método no hay referencia y no se compara. Si el Método da
    3 o más n distintos (varios estudios o submuestras) la regla no aplica. Una cifra de la sección se acepta si
    coincide con algún n del Método o con su suma; si la sección solo da subgrupos menores que el total, se acepta."""
    por_sec = {}
    for p in cuerpo:
        if not p.get("sec") or (p.get("en_tabla") and p["sec"] != "metodo"):  # las tablas del Método también dan n
            continue
        for v in valores_n(p["texto"]):
            por_sec.setdefault(p["sec"], []).append((v, p))
    if "metodo" not in por_sec:
        return []
    M = {v for v, _ in por_sec["metodo"]}
    if len(M) >= 3:
        return []
    n_ref = n_total([v for v, _ in por_sec["metodo"]])
    p_ref = next(p for v, p in por_sec["metodo"] if v == n_ref)
    H = []
    for s in ORDEN_SEC:
        if s == "metodo" or s not in por_sec:
            continue
        vals = [v for v, _ in por_sec[s]]
        distintos = set(vals)
        if distintos & (M | {sum(M)}):
            continue
        if len(distintos) >= 2 and all(v < max(M) for v in distintos):  # solo subgrupos
            continue
        n_s = n_total(vals)
        p_s = next(p for v, p in por_sec[s] if v == n_s)
        H.append(Hallazgo("CON-001", "crítica", ubicar(p_s),
                          f"{s}: n = {n_s} frente a metodo: n = {n_ref} ({ubicar(p_ref)[:70]})",
                          f"unificar el tamaño de muestra: el método dice {n_ref} y {s} dice {n_s}"))
    return H


# ---------------------------------------------------------------- CON-002
RE_PORC = re.compile(r"(?<![\w.,])(\d+(?:[.,]\d+)?)\s*%")
RE_DISTRIB = re.compile(r"respectivamente|se distribuy|distribuci[oó]n\s+(?:de\s+(?:la|los|las)\s+)?(?:muestra|participantes|respuestas|encuestad)|se dividi|repart", re.I)
RE_RANGO_PORC = re.compile(r"\d+(?:[.,]\d+)?\s*%?\s*(?:a|al|y|–|-|to)\s*\d+(?:[.,]\d+)?\s*%")


def regla_porcentajes(cuerpo):
    H = []
    for p in cuerpo:
        if p.get("en_tabla") or p.get("encabezado"):
            continue
        for s in oraciones(p["texto"]):
            pc = [float(x.replace(",", ".")) for x in RE_PORC.findall(RE_RANGO_PORC.sub(" ", s))]  # «28 % a 40 %» es un rango
            if len(pc) >= 3 and RE_DISTRIB.search(s) and sum(pc) > 100.5:
                H.append(Hallazgo("CON-002", "mayor", ubicar(p), s,
                                  f"los porcentajes suman {sum(pc):g} %: revisar las cifras (deben sumar 100 %)"))
    return H


# ---------------------------------------------------------------- CON-003 / CON-004
RE_DEF = re.compile(r"((?:[\wáéíóúñÁÉÍÓÚÑ-]+\s+){1,8})\(([A-Z][A-Za-z0-9]{1,7})\)")


def coincide_sigla(palabras, sigla):
    """Las mayúsculas de la sigla aparecen, en orden, como iniciales de las palabras que la preceden."""
    letras = [c for c in sigla if c.isupper()]
    if len(letras) < 2:
        return False
    ini = [sin_acentos(w)[0].upper() for w in palabras if w]
    k = 0
    for c in ini:
        if k < len(letras) and c == letras[k]:
            k += 1
    return k == len(letras)


def definiciones(cuerpo):
    defs = {}
    for p in cuerpo:
        if p.get("en_tabla") or p.get("encabezado") or p.get("sec") == "resumen":
            continue
        for m in RE_DEF.finditer(sin_citas(p["texto"])):
            sigla = m.group(2)
            palabras = m.group(1).split()
            if coincide_sigla(palabras, sigla):
                defs.setdefault(sigla, []).append(p)
    return defs


def regla_siglas(cuerpo):
    H = []
    defs = definiciones(cuerpo)
    for sigla, ps in defs.items():
        if len(ps) >= 2:
            H.append(Hallazgo("CON-003", "mayor", ubicar(ps[1]), f"«{sigla}» definida otra vez (primera: {ubicar(ps[0])[:60]})",
                              f"definir «{sigla}» una sola vez y usar solo la sigla después"))
        primera = ps[0]
        antes = None
        for p in cuerpo:
            if p is primera:
                break
            if p.get("en_tabla") or p.get("encabezado") or p.get("sec") == "resumen" or len(p["texto"]) < 60:
                continue
            if re.search(r"(?<![\w-])" + re.escape(sigla) + r"(?![\w-])", sin_citas(p["texto"])):
                antes = p
                break
        if antes is not None:
            H.append(Hallazgo("CON-004", "menor", ubicar(antes), f"«{sigla}» aparece antes de su definición ({ubicar(primera)[:60]})",
                              f"definir «{sigla}» en su primer uso"))
    return H


# ---------------------------------------------------------------- CON-005
def es_rotulo(p):
    t = p["texto"].strip()
    t = re.sub(r"^[!\[*_\s]+", "", t)
    m = auditar.RE_ROTULO.match(t)
    if not m:
        return None
    es_pie = "caption" in p.get("estilo", "").lower() or "epígrafe" in p.get("estilo", "").lower()
    g4 = m.group(4).lstrip("*_ ")
    if not g4 or m.group(3) or es_pie or g4[:1].isupper() or g4[:1] in "¿¡«":
        return (auditar.tipo_rotulo(m.group(1)), auditar.numero(m.group(2)))
    return None


RE_DE_FUENTE = re.compile(r"\s*(?:\[\d|\(\s*[A-ZÁÉÍÓÚ][^)]{0,40}\d{4}|(?:de|del|of|from|en|in)\s+(?:[A-ZÁÉÍÓÚ][\w'’-]+[\s,&y]*){1,4}\(?\d{4})")
RE_APENDICE = re.compile(r"\b(Apéndices?|Apendices?|Anexos?|Appendix|Appendices)\s+(?-i:([A-Z]))\b(?!\w)")
RE_APENDICE_DEF = re.compile(r"^[!\[*_\s]*(apéndice|apendice|anexo|appendix)(?:\s+([A-Z])\b)?", re.I)


def regla_referencias(pars, cuerpo, extra, entradas):
    rotulos, apend = set(), set()
    apend_sin_letra = False
    for p in pars:
        r = es_rotulo(p)
        if r:
            rotulos.add(r)
        m = RE_APENDICE_DEF.match(p["texto"])
        if m and (p.get("es_titulo") or len(p["texto"]) < 90):
            if m.group(2):
                apend.add(m.group(2).upper())
            else:
                apend_sin_letra = True
    ids_ent = {id(e) for e in entradas}
    H, vistos = [], set()
    for p in list(cuerpo) + list(extra):
        if id(p) in ids_ent or p.get("en_tabla") or p.get("encabezado") or es_rotulo(p) or auditar.RE_NOTA.match(p["texto"].strip()):
            continue
        t = p["texto"]
        dentro = [m.span() for m in re.finditer(r"\[\d[^\]]*\]", t)] + [m.span() for m in RE_CITA_PAR.finditer(t)]
        for m in auditar.RE_MENCION.finditer(t):
            if any(a <= m.start() < b for a, b in dentro) or RE_DE_FUENTE.match(t[m.end():]):
                continue  # «[3, Fig. 2]», «Fig. 2 [1]», «Tabla 3 de García (2020)»: figura o tabla de la fuente citada
            tipo = auditar.tipo_rotulo(m.group(1))
            toks = re.findall(r"\d+|[IVXLC]+", m.group(2))
            nums = [auditar.numero(x) for x in toks]
            if re.search(r"\d\s*(?:a|to|–|-)\s*\d", m.group(2)) and len(nums) == 2:
                nums = list(range(nums[0], nums[1] + 1))
            for n in nums:
                if (tipo, n) not in rotulos and (tipo, n) not in vistos:
                    vistos.add((tipo, n))
                    H.append(Hallazgo("CON-005", "mayor", ubicar(p), m.group(0).strip(),
                                      f"no hay rótulo de {tipo} {n} en el documento: agregarlo o corregir la mención"))
        for m in RE_APENDICE.finditer(t):
            letra = m.group(2)
            if letra not in apend and not (apend_sin_letra and letra == "A") and ("ap", letra) not in vistos:
                vistos.add(("ap", letra))
                H.append(Hallazgo("CON-005", "mayor", ubicar(p), m.group(0), f"no hay apéndice o anexo {letra} en el documento"))
    return H


# ---------------------------------------------------------------- CON-006
IGNORAR_X = {"siguiente", "siguientes", "anterior", "anteriores", "previa", "previo", "posterior", "presente", "este",
             "esta", "estos", "estas", "correspondiente", "actual", "final", "inicial", "precedente", "otra", "otro",
             "misma", "mismo", "que", "donde", "cual", "cuales", "dedicada", "dedicado", "destinada", "destinado", "ya",
             "mas", "cada", "todo", "toda", "primera", "segunda", "tercera", "cuarta", "quinta", "ultima", "penultima",
             "posteriores", "de", "del", "la", "el", "un", "una", "tal", "ello"}
PARAR_X = {"y", "e", "o", "para", "donde", "que", "se", "con", "como", "es", "son", "cuando", "por", "al", "en", "a",
           "sobre", "si", "pero", "ya", "mas"}
RE_PROMESA_SEC = re.compile(
    r"\ben\s+(?:la\s+|el\s+|las\s+|los\s+)?(?:siguiente\s+|pr[oó]xima\s+)?(?:secci[oó]n(?:es)?|cap[ií]tulo|apartado|ep[ií]grafe)\s+"
    r"(?:de\s+|del\s+)?[«\"“]?(\d+(?:\.\d+)*|[^\n.,;:()«»\"“”]{1,60})", re.I)  # «sección 2.7.3» completo
RE_PROMESA_VERA = re.compile(
    r"\bcomo\s+se\s+(?:ver[aá]n?|discute|discutir[aá]|analiza|analizar[aá]|detalla|detallar[aá]|expone|expondr[aá]|presenta|"
    r"presentar[aá]|muestra|mostrar[aá])\s+(?:m[aá]s\s+adelante\s+|a\s+continuaci[oó]n\s+)?en\s+(?:la\s+secci[oó]n\s+(?:de\s+)?)?"
    r"([«\"“]?)([^\n.,;:()«»\"“”]{1,60})", re.I)
RE_PROMESA_EN = re.compile(r"\b(?:in|see)\s+(?:the\s+)?(?:section|chapter)\s+(\d+(?:\.\d+)*|[IVXLC]+)\b", re.I)


def stem(x):
    return x.rstrip("s")


def regla_promesas(pars, cuerpo, extra, entradas):
    encab = [p for p in pars if p.get("es_titulo")]
    if len(encab) < 2:
        return []
    nombres = [norm_titulo(p["texto"]) for p in encab]
    nums = {m.group(1) for p in encab if (m := re.match(r"\s*(\d+(?:\.\d+)*)\.?\s", p["texto"]))}
    romanos = {m.group(1) for p in encab if (m := re.match(r"\s*([IVXLC]+)\.\s", p["texto"]))}

    def existe(x, con_seccion):
        x = x.strip()
        if not x:
            return True
        if re.match(r"\d", x):
            n = re.match(r"\d+(?:\.\d+)*", x).group(0)
            return not nums or n in nums or any(k.startswith(n + ".") for k in nums)  # «sección 2» con 2.1, 2.2…
        if re.match(r"[IVXLC]+\b", x):
            return not romanos or re.match(r"[IVXLC]+", x).group(0) in romanos
        pal = [w for w in norm_titulo(x).split()]
        if not pal or pal[0] in IGNORAR_X:
            return True
        corte = []
        for w in pal:
            if w in PARAR_X and corte:
                break
            corte.append(w)
        for k in range(1, min(4, len(corte)) + 1):
            ps = stem(" ".join(corte[:k]))
            for h in nombres:
                hs = stem(h)
                if hs and (hs.startswith(ps) or (len(hs) >= 4 and ps.startswith(hs))):
                    return True
        return False

    ids_ent = {id(e) for e in entradas}
    H, vistos = [], set()
    for p in list(cuerpo) + list(extra):
        if id(p) in ids_ent or p.get("en_tabla") or p.get("encabezado"):
            continue
        t = p["texto"]
        for m in RE_PROMESA_SEC.finditer(t):
            if not existe(m.group(1), True) and (id(p), norm_titulo(m.group(1))) not in vistos:
                vistos.add((id(p), norm_titulo(m.group(1))))
                H.append(Hallazgo("CON-006", "mayor", ubicar(p), m.group(0).strip(),
                                  f"no hay encabezado «{m.group(1).strip()}»: crear la sección o corregir la remisión"))
        for m in RE_PROMESA_VERA.finditer(t):
            x = m.group(2)
            if "sección" not in m.group(0).lower() and "seccion" not in m.group(0).lower() and not (m.group(1) or x[:1].isupper()):
                continue
            if not existe(x, False) and (id(p), norm_titulo(x)) not in vistos:
                vistos.add((id(p), norm_titulo(x)))
                H.append(Hallazgo("CON-006", "mayor", ubicar(p), m.group(0).strip(),
                                  f"no hay encabezado «{x.strip()}»: crear la sección o corregir la remisión"))
        for m in RE_PROMESA_EN.finditer(t):
            if not existe(m.group(1), True):
                H.append(Hallazgo("CON-006", "mayor", ubicar(p), m.group(0).strip(),
                                  f"no hay sección {m.group(1)} en el documento"))
    return H


# ---------------------------------------------------------------- CON-007
RE_NOEXP = re.compile(r"(?:no|non|cuasi|quasi)[\s-]*experiment", re.I)
RE_DISENO_OBS = re.compile(r"correlacion|transversal|observacional|descriptiv|encuesta|cross-sectional|correlational|"
                           r"observational|survey", re.I)
RE_DISENO_EXP = re.compile(r"experiment|asign\w* aleatori|aleatori\w* asign|aleatoriz|randomi|random assign|ensayo controlado|"
                           r"randomized controlled", re.I)
RE_CAUSAL = re.compile(
    r"(?<![\wáéíóú])(?:(?:caus(?:a|ó|an|aron|ando|ar))|provoc(?:a|ó|an|aron)|produc(?:e|en)|produj(?:o|eron)|determin(?:a|ó|an|aron)|"
    r"causes? (?:an? )?(?:increase|decrease|reduction|decline|improvement|loss|drop))(?![\wáéíóú])|efecto de(?!l)\b|impacto causal|causal (?:effect|impact)|demuestra que[^.]*\b(?:aumenta|reduce|mejora|disminuye)\b",
    re.I)
RE_DETERMINANTE_ANTES = re.compile(r"(?:\b(?:la|una|esta|su|principal|posible|otra|cada|toda|de|por|sin|con|cuya|esa|dicha)\s+)$", re.I)
RE_DESCARGO = re.compile(r"\bno\b[^.]{0,50}\b(?:caus|inferir|afirmar|concluir|establecer|demostrar|implica|permite)|causalidad|"
                         r"no se (?:puede|pueden|debe)|correlaci[oó]n no implica|no es posible", re.I)


def regla_causal(cuerpo):
    metodo = " ".join(p["texto"] for p in cuerpo if p.get("sec") == "metodo" and not p.get("en_tabla"))
    if not metodo:
        return []
    m_sin = RE_NOEXP.sub(" ", sin_acentos(metodo))
    if not RE_DISENO_OBS.search(m_sin) or RE_DISENO_EXP.search(m_sin):
        return []
    H = []
    for p in cuerpo:
        if p.get("sec") not in ("discusion", "conclusiones") or p.get("en_tabla"):
            continue
        for s in oraciones(p["texto"]):
            if RE_DESCARGO.search(s):
                continue
            for m in RE_CAUSAL.finditer(s):
                if RE_DETERMINANTE_ANTES.search(s[:m.start()]) and m.group(0).lower().startswith(("causa", "produce", "determina")):
                    continue  # sustantivo («la causa de», «de determinación»), no verbo causal
                H.append(Hallazgo("CON-007", "mayor", ubicar(p), s,
                                  "el diseño es no experimental: usar lenguaje de asociación (se asocia con, se relaciona con)"))
                break
    return H


# ---------------------------------------------------------------- CON-008
RE_NUM_T = re.compile(r"(?<![\w.,])(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:[.,]\d+)?)(?!\w*\d)")
RE_SIGLA_T = re.compile(r"(?<![\w-])(?:[A-Z]{2,}[A-Za-z0-9]*(?:-[A-Za-z0-9]+)*|[A-Z][a-z]+[A-Z][A-Za-z0-9]*(?:-[A-Za-z0-9]+)*|"
                        r"[A-Z][A-Za-z]*-\d[\w-]*)(?![\w-])")
RE_CAP = re.compile(r"(?<![\w-])[A-ZÁÉÍÓÚÑ][a-záéíóúñü]{2,}(?![\w-])")
RE_NOMBRE = r"[A-ZÁÉÍÓÚÑ][\w'’-]+"
RE_ETAL = re.compile(r"((?:" + RE_NOMBRE + r"(?:,\s*|\s+(?:y|e|and|&)\s+))*" + RE_NOMBRE + r")\s+et\s+al\.?")
RE_AUTORES_CELDA = re.compile(RE_NOMBRE + r"(?:(?:,\s*|\s+(?:y|e|and|&)\s+)" + RE_NOMBRE + r"){0,5}")
NO_NOMBRE = {"tabla", "tablas", "figura", "figuras", "table", "tables", "figure", "figures", "nota", "note", "este", "esta",
             "estos", "estas", "los", "las", "una", "uno", "como", "para", "sobre", "entre", "desde", "segun", "tambien",
             "ademas", "asi", "pero", "cuando", "donde", "luego", "despues", "primero", "segundo", "tercero", "finalmente",
             "lectura", "the", "and", "for", "with", "from"}
UMBRAL_TOKENS = 4    # mínimo de cifras/nombres del párrafo que ya están en la tabla
UMBRAL_PORC = 0.5    # y su fracción de las cifras+nombres del párrafo
UMBRAL_FILAS = 3      # los repetidos vienen de >= 3 filas: destacar una fila (p. ej. el año atípico) es legítimo
UMBRAL_FUERTES = 3    # de ellos, >= 3 autores o cifras de 2+ dígitos (siglas y dígitos sueltos coinciden por azar)


def numeros_texto(t):
    """Cifras normalizadas (28.4; 10,000 -> 10000). Sin años, citas ni números de «Tabla N». Las cifras escritas en
    palabras (afirmaciones.palabras_a_numeros) cuentan solo si valen >= 10: «una» o «dos» no son cifras de tabla."""
    import afirmaciones
    t = sin_citas(auditar.RE_MENCION.sub(" ", t))
    vistos, out = set(), []

    def norm(v):
        v = v.replace(",", "") if re.fullmatch(r"\d{1,3}(?:,\d{3})+(?:\.\d+)?", v) else v.replace(",", ".")
        return v.rstrip("0").rstrip(".") if "." in v else v
    for m in RE_NUM_T.finditer(t):
        v = norm(m.group(1))
        vistos.add(v)
        if not re.fullmatch(r"(19|20)\d\d", v):
            out.append(v)
    for m in RE_NUM_T.finditer(afirmaciones.palabras_a_numeros(t)):
        v = norm(m.group(1))
        if v not in vistos and v.isdigit() and int(v) >= 10:
            out.append(v)
    return out


def nombres_texto(t, conocidos=()):
    """Autores y siglas de un texto: palabras antes de «et al.», siglas/modelos (MuPT, QLoRA, GPT-4) y mayúsculas a
    mitad de oración. Una mayúscula de inicio de oración solo cuenta si ya está en `conocidos` (la tabla)."""
    t = sin_citas(auditar.RE_MENCION.sub(" ", t))
    out = []
    for m in RE_ETAL.finditer(t):
        out += re.findall(RE_NOMBRE, m.group(1))
    out += RE_SIGLA_T.findall(t)
    for m in RE_CAP.finditer(t):
        previo = t[:m.start()].rstrip()
        inicio = not previo or previo[-1] in ".!?:¿¡«\"“("
        if not inicio or m.group(0) in conocidos:
            out.append(m.group(0))
    return [w for w in dict.fromkeys(out) if sin_acentos(w.lower()) not in NO_NOMBRE]


def tokens_tabla(celdas, filas=1):
    """Cifras, autores y siglas de las celdas, cada uno con el conjunto de filas donde aparece (`filas`: fila de cada
    celda, o celdas por fila si es un entero). Autor: celda «Apellido et al.» o solo apellidos (columna de autores). Devuelve (cifras, nombres)."""
    nums, nombres = {}, {}
    fila_de = lambda k: filas[k] if isinstance(filas, list) else k // filas  # noqa: E731
    con_cifra = {fila_de(k) for k, c in enumerate(celdas) if re.search(r"\d", c)}  # filas de encabezado no traen autores
    for k, c in enumerate(celdas):
        c, fila = c.strip(), fila_de(k)
        for v in numeros_texto(c):
            nums.setdefault(v, set()).add(fila)
        ws = RE_SIGLA_T.findall(c)
        m = RE_ETAL.search(c)
        if m:
            ws += re.findall(RE_NOMBRE, m.group(1))
        elif RE_AUTORES_CELDA.fullmatch(c) and not RE_SIGLA_T.fullmatch(c) and fila in con_cifra:
            ws += re.findall(RE_NOMBRE, c)
        for w in ws:
            if sin_acentos(w.lower()) not in NO_NOMBRE:
                nombres.setdefault(w, set()).add(fila)
    return nums, nombres


def numeros_mencion(m):
    nums = [auditar.numero(x) for x in re.findall(r"\d+|[IVXLC]+", m.group(2))]
    if re.search(r"\d\s*(?:a|to|–|-)\s*\d", m.group(2)) and len(nums) == 2:
        nums = list(range(nums[0], nums[1] + 1))
    return nums


def filas_de_tablas(path):
    """{n.º de tabla de nivel superior: [fila de cada párrafo de sus celdas, en orden de documento]}. Misma numeración
    que auditar.cargar_docx (orden de aparición)."""
    from docx.oxml.ns import qn
    d = auditar.abrir_docx(str(path))
    out = {}
    for tbl in d.element.body.iter(qn("w:tbl")):
        a = tbl.getparent()
        while a is not None and a.tag != qn("w:tbl"):
            a = a.getparent()
        if a is not None:
            continue  # anidada
        filas = []
        for r, tr in enumerate(tbl.iterchildren(qn("w:tr"))):
            for tc in tr.iterchildren(qn("w:tc")):
                filas += [r] * sum(1 for _ in tc.iter(qn("w:p")))
        out[len(out) + 1] = filas
    return out


def regla_repite_tabla(pars, filas_t=None):
    """CON-008. Solo .docx (el lector md no marca p['tabla'])."""
    ids = sorted({p["tabla"] for p in pars if p.get("tabla") and p.get("en_tabla")})
    H, marcados = [], set()
    for tid in ids:
        idx = [k for k, p in enumerate(pars) if p.get("tabla") == tid]
        a, b = idx[0], idx[-1]
        num = None
        for k in list(range(a - 1, max(a - 4, -1), -1)) + list(range(b + 1, min(b + 3, len(pars)))):
            r = None if pars[k].get("en_tabla") else es_rotulo(pars[k])
            if r and r[0] == "tabla":
                num = r[1]
                break
        if num is None:
            continue
        mapa = (filas_t or {}).get(tid)
        t_nums, t_nombres = tokens_tabla([pars[k]["texto"] for k in idx], mapa if mapa and len(mapa) == len(idx) else 1)
        if len(t_nums) + len(t_nombres) < UMBRAL_TOKENS:
            continue

        def texto_libre(p):
            return not (p.get("en_tabla") or p.get("es_titulo") or not p["texto"].strip() or es_rotulo(p)
                        or auditar.RE_NOTA.match(p["texto"].strip()))
        cand = {k: p for k, p in enumerate(pars) if texto_libre(p) and any(
            auditar.tipo_rotulo(m.group(1)) == "tabla" and num in numeros_mencion(m)
            for m in auditar.RE_MENCION.finditer(p["texto"]))}
        n = 0
        for k in range(b + 1, len(pars)):
            if pars[k].get("es_titulo"):
                break
            if texto_libre(pars[k]):
                cand[k] = pars[k]
                n += 1
                if n == 3:
                    break
        for k, p in sorted(cand.items()):
            if id(p) in marcados:
                continue
            p_nums = list(dict.fromkeys(numeros_texto(p["texto"])))
            p_nom = nombres_texto(p["texto"], t_nombres)
            rep_nom = [w for w in p_nom if w in t_nombres]
            rep_num = [v for v in p_nums if v in t_nums]
            rep, total = len(rep_nom) + len(rep_num), len(p_nums) + len(p_nom)
            fuertes = [w for w in rep_nom if not RE_SIGLA_T.fullmatch(w)] + [v for v in rep_num if len(v) > 1]
            filas_rep = set().union(*([t_nombres[w] for w in rep_nom if not RE_SIGLA_T.fullmatch(w)]
                                      + [t_nums[v] for v in rep_num if len(v) > 1]), set())
            if (rep >= UMBRAL_TOKENS and rep / total >= UMBRAL_PORC and len(fuertes) >= UMBRAL_FUERTES
                    and len(filas_rep) >= UMBRAL_FILAS):
                marcados.add(id(p))
                lista = rep_nom + rep_num
                ev = f"repite de la Tabla {num}: {', '.join(lista[:8])}{' …' if len(lista) > 8 else ''}"
                H.append(Hallazgo("CON-008", "menor", ubicar(p), ev,
                                  f"destaca la tendencia o lo que el lector debe ver en la Tabla {num}; no repitas sus filas "
                                  "(cifras y autores ya están en la tabla). Práctica editorial"))
    return H


# ---------------------------------------------------------------- CON-009
UMBRAL_SHINGLE = 5      # palabras por shingle
UMBRAL_PALABRAS = 15    # mínimo de palabras de la oración (sin citas ni texto entre comillas); 12 daba FP en la muestra
                        # oficial professional-paper.docx («No other factors … were statistically reliable.» repetida por diseño)
UMBRAL_JACCARD = 0.6
UMBRAL_JACCARD_RESUMEN = 0.85   # el resumen parafrasea el cuerpo: solo copia casi literal
RE_COMILLAS = re.compile(r"«[^»]*»|“[^”]*”|\"[^\"]*\"")


def palabras_norm(s):
    s = sin_citas(RE_COMILLAS.sub(" ", s))
    return re.findall(r"[a-z0-9ñ]+", sin_acentos(s.lower()))


def ubic_corta(p):
    return "el resumen (YAML)" if p.get("yaml") else f"el párrafo {p['i'] + 1}"


def elegible_texto(p):
    return not (p.get("en_tabla") or p.get("es_titulo") or p.get("encabezado") or not p["texto"].strip() or es_rotulo(p)
                or auditar.RE_NOTA.match(p["texto"].strip()))


def regla_redundancia(cuerpo):
    items = []   # (parrafo, oracion, shingles)
    for p in cuerpo:
        if not elegible_texto(p):
            continue
        for s in oraciones(p["texto"]):
            w = palabras_norm(s)
            if len(w) >= UMBRAL_PALABRAS and "\n" not in s.strip():  # bloques de autores/portada llevan saltos de línea
                sh = {" ".join(w[k:k + UMBRAL_SHINGLE]) for k in range(len(w) - UMBRAL_SHINGLE + 1)}
                items.append((p, s, sh))
    indice = {}
    for k, (_, _, sh) in enumerate(items):
        for g in sh:
            indice.setdefault(g, []).append(k)
    H, pares = [], set()
    for b, (pb, sb, shb) in enumerate(items):
        comunes = {}
        for g in shb:
            for a in indice[g]:
                if a < b:
                    comunes[a] = comunes.get(a, 0) + 1
        for a, c in sorted(comunes.items()):
            pa, sa, sha = items[a]
            if pa is pb or (id(pa), id(pb)) in pares:
                continue
            j = c / len(sha | shb)
            u = UMBRAL_JACCARD_RESUMEN if "resumen" in (pa.get("sec"), pb.get("sec")) else UMBRAL_JACCARD
            if j >= u:
                pares.add((id(pa), id(pb)))
                H.append(Hallazgo("CON-009", "menor", ubicar(pb),
                                  f"repite {ubicar(pa)[:70]} (similitud {j:.2f}): «{sb[:90]}»",
                                  f"la idea ya se dijo en {ubic_corta(pa)}; remite a ella o elimina la repetición"))
    return H


# ---------------------------------------------------------------- CON-018
def forma_completa(palabras, sigla):
    """Sufijo más corto de `palabras` cuyas iniciales contienen la sigla (lo anterior es relleno)."""
    primera = [c for c in sigla if c.isupper()][0]
    for k in range(len(palabras) - 1, -1, -1):
        if palabras[k] and sin_acentos(palabras[k][0]).upper() == primera and coincide_sigla(palabras[k:], sigla):
            return palabras[k:]
    return None


def regla_forma_repetida(cuerpo):
    H, formas = [], {}
    for p in cuerpo:
        if p.get("en_tabla") or p.get("encabezado") or p.get("sec") == "resumen":
            continue
        for m in RE_DEF.finditer(sin_citas(p["texto"])):
            sigla, palabras = m.group(2), m.group(1).split()
            if sigla in formas or not coincide_sigla(palabras, sigla):
                continue
            f = forma_completa([re.sub(r"[^\wáéíóúñÁÉÍÓÚÑ-]", "", w) for w in palabras], sigla)
            if f and len(f) >= 2:
                formas[sigla] = (p, " ".join(sin_acentos(w.lower()) for w in f))
    for sigla, (p0, forma) in formas.items():
        re_f = re.compile(r"(?<![\w-])" + r"\s+".join(map(re.escape, forma.split())) + r"(?![\w-])(?!\s*[(\[]\s*" +
                          re.escape(sin_acentos(sigla).lower()) + r"\b)")
        hits, desde, usos = [], False, 0
        for p in cuerpo:
            if p is p0:
                desde = True
                continue
            if not desde or not elegible_texto(p) or p.get("sec") == "resumen":
                continue
            t = sin_acentos(sin_citas(RE_COMILLAS.sub(" ", p["texto"])).lower())
            hits += [p] * len(re_f.findall(re.sub(r"\s+", " ", t)))
            usos += len(re.findall(r"(?<![\w-])" + re.escape(sigla) + r"(?![\w-])", sin_citas(p["texto"])))
        if len(hits) >= 2 and usos >= 1:  # sigla nunca usada tras definirla (p. ej. «focus group (FG) number»): no se adoptó
            H.append(Hallazgo("CON-018", "menor", ubicar(hits[1]),
                              f"«{forma}» reaparece {len(hits)} veces tras definir «{sigla}» ({ubicar(p0)[:60]})",
                              f"usa «{sigla}» tras definirla (APA 6.25: tras definir la abreviatura, usar solo la abreviatura)"))
    return H


# ---------------------------------------------------------------- CON-019
RE_INDICE = re.compile(r"(?:\.{3,}|\t)\s*\d+\s*$")


def es_entrada_indice(p):
    est = p.get("estilo", "").lower()
    return bool(RE_INDICE.search(p["texto"])) or any(k in est for k in ("toc", "table of figures", "tabla de ilus", "índice", "indice"))


def primeras_menciones(cuerpo):
    """Orden de primera mención por tipo (tabla/figura) y de letras de apéndice, en orden de documento."""
    orden, orden_ap = {}, []
    for p in cuerpo:
        celda = p.get("en_tabla") and not p.get("es_titulo") and p["texto"].strip() and not es_rotulo(p)
        if not (elegible_texto(p) or celda) or es_entrada_indice(p):
            continue   # una mención en una celda (matriz de consistencia) cuenta como mención, pero no se marca
        t = p["texto"]
        dentro = [m.span() for m in re.finditer(r"\[\d[^\]]*\]", t)] + [m.span() for m in RE_CITA_PAR.finditer(t)]
        hallados = []
        for m in auditar.RE_MENCION.finditer(t):
            if any(a <= m.start() < b for a, b in dentro) or RE_DE_FUENTE.match(t[m.end():]):
                continue
            for n in numeros_mencion(m):
                hallados.append((m.start(), auditar.tipo_rotulo(m.group(1)), n))
        for m in RE_APENDICE.finditer(t):
            hallados.append((m.start(), "ap", m.group(2)))
        for _, tipo, n in sorted(hallados, key=lambda x: x[0]):
            lst = orden_ap if tipo == "ap" else orden.setdefault(tipo, [])
            if n not in [x for x, _ in lst]:
                lst.append((n, p))
    return orden, orden_ap


def regla_numeracion(pars, cuerpo):
    H = []
    rot, letras = {}, []
    for p in pars:
        if p.get("en_tabla") or es_entrada_indice(p):
            continue
        r = es_rotulo(p)
        if r:
            rot.setdefault(r[0], []).append((r[1], p))
        m = RE_APENDICE_DEF.match(p["texto"])
        if m and m.group(2) and (p.get("es_titulo") or len(p["texto"]) < 90):
            letras.append((m.group(2).upper(), p))
    nombre = {"tabla": "Tabla", "figura": "Figura"}
    for tipo, lst in rot.items():
        vistos = {}
        for n, p in lst:
            if n in vistos:
                H.append(Hallazgo("CON-019", "mayor", ubicar(p),
                                  f"{nombre[tipo]} {n} rotulada dos veces (primera: {ubicar(vistos[n])[:60]})",
                                  f"numerar cada {tipo} una sola vez y en orden consecutivo (APA cap. 7)"))
            else:
                vistos[n] = p
        nums = sorted(vistos)
        for a, b in zip([0] + nums, nums):
            if b - a > 1:
                faltan = ", ".join(str(x) for x in range(a + 1, b))
                H.append(Hallazgo("CON-019", "mayor", ubicar(vistos[b]),
                                  f"hueco de numeración: falta {nombre[tipo]} {faltan} antes de {nombre[tipo]} {b}",
                                  f"numerar las {tipo}s de forma consecutiva (1, 2, 3…), en el orden de mención (APA cap. 7)"))
                break
    ls = [x for x, _ in letras]
    for k, (l, p) in enumerate(letras):
        if l in ls[:k]:
            H.append(Hallazgo("CON-019", "mayor", ubicar(p), f"Apéndice {l} rotulado dos veces", "rotular cada apéndice una sola vez (APA 2.14)"))
    esperado = [chr(65 + i) for i in range(len(set(ls)))]
    if ls and sorted(set(ls)) != esperado:
        faltan = sorted(set(chr(65 + i) for i in range(ord(max(ls)) - 64)) - set(ls))
        H.append(Hallazgo("CON-019", "mayor", ubicar(letras[0][1]), f"Apéndices {', '.join(sorted(set(ls)))}: falta {', '.join(faltan)}",
                          "rotular los apéndices en orden consecutivo A, B, C… (APA 2.14)"))
    orden, orden_ap = primeras_menciones(cuerpo)
    for tipo, lst in orden.items():
        existentes, vistos = {n for n, _ in rot.get(tipo, [])}, set()
        seq = [n for n, _ in lst]   # solo cuenta si la tabla menor sí se menciona, pero después (sin mención: APA-091)
        despues = {n: set(seq[k + 1:]) for k, n in enumerate(seq)}
        for n, p in lst:
            if n not in existentes:
                continue
            if p.get("en_tabla"):
                vistos.add(n)
                continue
            antes = sorted(m for m in existentes if m < n and m not in vistos and m in despues[n])
            if antes:
                H.append(Hallazgo("CON-019", "mayor", ubicar(p),
                                  f"{nombre[tipo]} {n} se menciona antes que {nombre[tipo]} {antes[0]}",
                                  f"mencionar las {tipo}s en el orden en que se numeran: {nombre[tipo]} {antes[0]} primero (APA cap. 7)"))
            vistos.add(n)
    existentes, vistos = set(ls), set()
    seq_ap = [l for l, _ in orden_ap]
    despues_ap = {l: set(seq_ap[k + 1:]) for k, l in enumerate(seq_ap)}
    for l, p in orden_ap:
        if l in existentes:
            antes = sorted(m for m in existentes if m < l and m not in vistos and m in despues_ap[l])
            if antes:
                H.append(Hallazgo("CON-019", "mayor", ubicar(p), f"Apéndice {l} se menciona antes que el Apéndice {antes[0]}",
                                  "mencionar los apéndices en el orden en que aparecen (APA 2.14)"))
            vistos.add(l)
    return H


# ---------------------------------------------------------------- CON-020
RE_SEC_OBJ = re.compile(r"^(?:objetivos?(?: general| generales| especificos?)*(?: y (?:objetivos )?especificos?)?"
                        r"(?: de (?:la )?investigacion| del estudio| del proyecto| del trabajo)?|"
                        r"preguntas? de (?:la )?investigacion|preguntas? (?:de investigacion )?y objetivos|objectives?|"
                        r"research questions?|specific objectives?)$")
RE_SEC_TRAZA = re.compile(r"cronograma|plan de analisis|analisis de datos|procedimiento|plan de trabajo|metodolog|\bmetodo|"
                          r"resultados|conclusion|discusion|schedule|analysis plan|procedure|method|results|discussion")
RE_ROTULO_OBJ = re.compile(r"^(?:objetivos?\s+(?:general|especifico)?\s*(?:n[.º°o]*\s*)?\d*|oe\s*\d*|o\d+|pregunta\s*\d*)\s*(?:\([^)]*\)\s*)?[:.\-–)]\s*")
RE_VINETA = re.compile(r"^\s*(?:[-•*·]|\(?[a-z0-9]{1,2}[.)])\s+")
VERBOS_GENERICOS = {"analizar", "evaluar", "determinar", "identificar", "disenar", "desarrollar", "describir", "establecer",
                    "conocer", "comparar", "explorar", "examinar", "estimar", "medir", "comprender", "elaborar", "proponer",
                    "valorar", "caracterizar", "implementar", "validar", "verificar", "demostrar", "indagar", "investigar",
                    "reconocer", "relacionar", "contrastar", "diagnosticar", "formular", "construir", "generar", "obtener",
                    "lograr", "explicar", "revisar", "aplicar", "realizar", "efectuar", "calcular", "cuantificar", "detectar"}
STOP_OBJ = {"entre", "sobre", "desde", "hasta", "mediante", "traves", "respecto", "dentro", "partir", "cuales", "donde",
            "cuando", "segun", "otros", "otras", "estos", "estas", "dicho", "dicha", "misma", "mismo", "tambien", "ademas",
            "cuanto", "forma", "manera", "nivel", "niveles", "proceso", "procesos", "caso", "casos", "aspectos", "aspecto",
            "diferentes", "distintos", "distintas", "principales", "principal", "general", "generales", "especifico",
            "especificos", "durante", "tiene", "tienen", "fuera", "mayor", "menor", "cual", "cada", "toda", "todos", "todas",
            "hacia", "ambos", "estudio", "trabajo", "investigacion", "objetivo", "objetivos", "propuesta", "actual",
            "actuales", "posibles", "posible", "resultados", "resultado", "datos", "informacion", "analisis"}
MIN_TERMINOS = 2
MAX_TERMINOS = 4
MIN_PALABRAS_TRAZA = 50


def raiz(w):
    w = stem(w)
    return w[:max(5, len(w) - 3)]


def objetivos_de(cuerpo):
    """([(p, texto)] de los objetivos o preguntas bajo encabezados de objetivos, ids de esos párrafos)."""
    objs, ids, dentro = [], set(), False
    for p in cuerpo:
        if p.get("es_titulo"):
            dentro = bool(RE_SEC_OBJ.match(norm_titulo(p["texto"])))
            continue
        if not dentro or p.get("en_tabla") or not p["texto"].strip():
            continue
        ids.add(id(p))
        partes = re.split(r"\n|;\s*|(?<=[.!?])\s+(?=[A-ZÁÉÍÓÚ¿])", p["texto"])
        for s in partes:
            s = RE_VINETA.sub("", s.strip())
            n = RE_ROTULO_OBJ.sub("", sin_acentos(s.lower())).strip(" .;¿")
            m = re.match(r"([a-zñ]+)\b", n)
            if not m or len(n.split()) < 4:
                continue
            w = m.group(1)
            sig = n.split()[1] if len(n.split()) > 1 else ""
            if sig in ("es", "son", "implica", "significa", "consiste", "requiere", "permite", "se", "fue", "era"):
                continue  # prosa que explica un verbo («Comprender es poder explicar…»), no un objetivo
            if (len(w) >= 5 and re.search(r"(ar|er|ir)(se)?$", w)) or s.lstrip().startswith("¿") or s.rstrip().endswith("?"):
                objs.append((p, s))
    return objs, ids


def terminos_clave(obj):
    n = RE_ROTULO_OBJ.sub("", RE_VINETA.sub("", sin_acentos(sin_citas(obj).lower()).strip())).strip()
    vistos, out = set(), []
    for w in re.findall(r"[a-zñ]{5,}", n):
        if w in VERBOS_GENERICOS or w in STOP_OBJ or w.endswith("mente") or raiz(w) in vistos:
            continue
        vistos.add(raiz(w))
        out.append(w)
    top = sorted(out, key=lambda w: -len(w))[:MAX_TERMINOS]
    return [w for w in out if w in top]


def regla_objetivos_sin_rastro(cuerpo):
    objs, ids = objetivos_de(cuerpo)
    if not objs:
        return []
    traza, pila = [], []   # pila de encabezados (nivel, título normalizado): un hijo de «Bosquejo del método» es método
    for p in cuerpo:
        if p.get("es_titulo"):
            nv = auditar.nivel_estilo(p) or 1
            while pila and pila[-1][0] >= nv:
                pila.pop()
            pila.append((nv, norm_titulo(p["texto"])))
            continue
        if id(p) in ids or not p["texto"].strip():
            continue
        if p.get("sec") in ("metodo", "resultados", "discusion", "conclusiones") or any(RE_SEC_TRAZA.search(t) for _, t in pila):
            traza.append(p["texto"])
    texto = sin_acentos(" ".join(traza).lower())
    if len(re.findall(r"\w+", texto)) < MIN_PALABRAS_TRAZA:
        return []
    palabras = set(re.findall(r"[a-zñ0-9]+", texto))
    H = []
    for p, obj in objs:
        ts = terminos_clave(obj)
        if len(ts) >= MIN_TERMINOS and not any(w.startswith(raiz(t)) for t in ts for w in palabras):
            H.append(Hallazgo("CON-020", "mayor", ubicar(p),
                              f"objetivo «{obj[:100]}»: ni {', '.join(ts)} aparecen en método, resultados ni conclusiones",
                              "el objetivo no tiene rastro: explica cómo se atiende en el método y qué se halló en "
                              "resultados o conclusiones, o ajústalo (práctica editorial)"))
    return H


# ---------------------------------------------------------------- CON-021
def regla_titulo_objetivo(path):
    """CON-021: el núcleo del título (objeto y propósito) aparece en el objetivo general. Sin título u objetivo no corre."""
    import titulo as T
    try:
        d = T.leer(path)
    except Exception:  # noqa: BLE001  (un documento sin portada reconocible no tiene título que comparar)
        return []
    if not d["titulo"] or not d["objetivo"]:
        return []
    _, cfg, _ = T.config_equipo(path)
    r = T.incoherencia(d["titulo"], d["objetivo"], cfg)
    if not r:
        return []
    faltan, nuc = r
    faltan = T._con_acentos(faltan, d["titulo"])
    pos = next((p for p in d["pars"] if T.RE_SEC_OBJ_GRAL.match(T._norm_encabezado(p["texto"])) and p.get("es_titulo")), None)
    return [Hallazgo("CON-021", "menor", ubicar(pos) if pos else "objetivo general",
                     f"el título «{d['titulo'][:90]}{'…' if len(d['titulo']) > 90 else ''}» usa {', '.join(faltan)}, que el objetivo general no usa "
                     f"({len(faltan)} de {len(nuc)} términos de núcleo)",
                     "alinear título y objetivo general: el título resume el objeto y el propósito del objetivo (ver `editorial.py titulo`)")]


# ---------------------------------------------------------------- principal
def revisar(path):
    auditar.validar_entrada(path)
    pars, abstract = cargar(path)
    cuerpo, titulo, entradas = auditar.partir(pars)
    ids = {id(p) for p in cuerpo} | {id(p) for p in entradas} | ({id(titulo)} if titulo else set())
    extra = [p for p in pars if id(p) not in ids and p["texto"].strip()]
    cuerpo = [p for p in cuerpo if p["texto"].strip()]
    asignar_secciones(cuerpo)
    if abstract:
        cuerpo.insert(0, {"i": -1, "texto": abstract, "es_titulo": False, "estilo": "", "sec": "resumen", "yaml": True})
    detectadas = [s for s in ORDEN_SEC if any(p.get("sec") == s or (p.get("es_titulo") and clave_seccion(p["texto"]) == s)
                                              for p in cuerpo)]
    H = []
    if detectadas:
        H += regla_muestra(cuerpo)
    H += regla_porcentajes(cuerpo)
    H += regla_siglas(cuerpo)
    H += regla_referencias(pars, cuerpo, extra, entradas)
    H += regla_promesas(pars, cuerpo, extra, entradas)
    H += regla_redundancia(cuerpo)
    H += regla_forma_repetida(cuerpo)
    H += regla_numeracion(pars, cuerpo)
    H += regla_objetivos_sin_rastro(cuerpo)
    H += regla_titulo_objetivo(path)
    if "metodo" in detectadas:
        H += regla_causal(cuerpo)
    if str(path).lower().endswith(".docx"):
        try:
            H += regla_repite_tabla(pars, filas_de_tablas(path))
        except Exception:  # noqa: BLE001  (sin filas, la regla pierde el criterio de filas y no corre)
            pass
    orden = {"crítica": 0, "mayor": 1, "menor": 2}
    H.sort(key=lambda h: (orden[h["severidad"]], h["id"]))
    conteo = {s: sum(h["severidad"] == s for h in H) for s in orden}
    return {"documento": str(path), "hallazgos": H, "conteo": conteo, "secciones_detectadas": detectadas}


def main():
    ap = argparse.ArgumentParser(description="Congruencia interna: objetivos, método, resultados, cifras, siglas, referencias cruzadas.")
    ap.add_argument("documento")
    ap.add_argument("--perfil", help="se acepta por uniformidad con los demás comandos; la congruencia no depende del perfil")
    ap.add_argument("--json", metavar="RUTA", help="escribe el resultado completo como JSON")
    a = ap.parse_args()
    cli.utf8()
    r = revisar(a.documento)
    cli.escribir_json(a.json, r)
    print(f"CONGRUENCIA: {r['conteo']}   secciones={r['secciones_detectadas']}")
    print("| # | ID | Severidad | Ubicación | Evidencia | Corrección |\n|---|---|---|---|---|---|")
    for i, h in enumerate(r["hallazgos"], 1):
        print(f"| {i} | {h['id']} | {h['severidad']} | {h['ubicacion']} | {h['evidencia']} | {h['correccion']} |")
    sys.exit(cli.codigo(r["hallazgos"]))


if __name__ == "__main__":
    main()
