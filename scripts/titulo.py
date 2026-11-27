#!/usr/bin/env python3
"""Título concreto: diagnóstico determinista del título de portada frente al objetivo general.

Uso:
  python -I scripts/titulo.py <doc.docx|doc.md> [--max-palabras N] [--opcion "título candidato" ...] [--json RUTA]

Extrae el título de la portada (.docx: las líneas contiguas de la portada que no son etiquetas, o los párrafos de estilo
Título; .md: `title:` del YAML) y el objetivo general (sección «Objetivo general» o párrafo «Objetivo general: …») y emite un
diagnóstico: palabras, sigla o nombre del proyecto, detalles de método o tecnología que sobran en un título (LoRA, ABC,
Gemma, prompting, «comparando», «mediante», «basado en», nombres de modelos y versiones, pila tecnológica), promesas de
resultado («mejorar», «garantizar», «optimizar», «encargado de»), cifras, términos clave del objetivo que el título no recoge y
términos del título que el objetivo no usa (CON-021). Con `--opcion` evalúa además títulos candidatos con el mismo diagnóstico.

El título lo elige el usuario (receta y opciones en skills/editorial-academica/references/titulo.md); una vez elegido se fija en
`.editorial.yaml` (`titulo:`), pasa a ser vinculante y la portada debe coincidir (INS-010). Ajustes opcionales en `.editorial.yaml`:
  titulo_config: {max_palabras: 15, sobran: ["texto o regex", …], promesas: ["…"]}   (se suman a las listas por defecto)
Salida: 0 (el diagnóstico informa, no califica; los hallazgos reglados son CON-021 e INS-010); 2 error de uso o de entrada.
Funciones importables: leer(path) y diagnosticar(titulo, objetivo, cfg=None).
"""
import argparse
import pathlib
import re
import sys
import unicodedata

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import auditar  # noqa: E402
import cli  # noqa: E402

sin_acentos = auditar.sin_acentos
MAX_PALABRAS = 15
MIN_PALABRAS = 8

# detalles de método o tecnología que no van en un título (se buscan sin acentos y en minúsculas)
SOBRAN_DEFECTO = [
    (r"\bq?lora\b", "técnica de ajuste (LoRA)"), (r"\bfine[- ]?tuning\b|\bajuste fino\b", "ajuste fino"),
    (r"\bprompt(?:ing|s)?\b", "prompting"), (r"\brag\b", "RAG"), (r"\babc\b", "formato de notación (ABC)"),
    (r"\bcomparando\b|\bcomparacion de\b|\bcomparativ[oa]\b", "comparación (diseño del estudio)"),
    (r"\bmediante\b|\bpor medio de\b|\ba traves de\b|\butilizando\b|\busando\b|\baplicando\b", "método («mediante», «utilizando»…)"),
    (r"\bbasad[oa]s? en\b", "«basado en»"),
    (r"\b(?:gpt|gemma|llama|qwen|mistral|bert|claude|gemini|phi|deepseek|falcon|whisper|t5)[- ]?v?\d*(?:[.\-]\d+)*[a-z]{0,3}\b",
     "nombre de modelo"),
    (r"\bv\d+(?:\.\d+)+\b|\b\d+\.\d+(?:\.\d+)*\b", "versión"),
    (r"\b(?:python|java|javascript|typescript|react|angular|vue|tensorflow|pytorch|mysql|postgresql|mongodb|django|flask|"
     r"node\.?js|docker|arduino|raspberry|android|laravel|spring|kubernetes|firebase)\b", "tecnología concreta"),
]
# promesas de resultado que el protocolo no evalúa (cámbialas por «apoyar», «explorar», «contribuir a»…)
PROMESAS_DEFECTO = [
    r"\bmejor(?:ar|a|as|ando|amiento|ara|ando)\b", r"\bgarantiz\w+", r"\boptimiz\w+", r"\bmaximiz\w+", r"\bminimiz\w+",
    r"\basegur(?:ar|a|ando|amiento)\b", r"\belimin(?:ar|a|ando)\b", r"\brevolucion\w+", r"\bencargad[oa]s? de\b",
    r"\bresolv(?:er|iendo)\b", r"\bgarantia\b",
]
STOP = {"para", "como", "desde", "entre", "sobre", "hacia", "ante", "bajo", "tras", "segun", "contra", "durante", "mediante",
        "esta", "este", "estos", "estas", "esos", "esas", "aquel", "cada", "otro", "otra", "otros", "otras", "tambien",
        "pero", "sino", "aunque", "donde", "cuando", "tiene", "tienen", "puede", "pueden", "debe", "deben", "sera", "seran",
        "sistema", "proyecto", "estudio", "trabajo", "propuesta", "desarrollo", "prototipo", "protocolo", "investigacion"}
RE_HONORIFICO = re.compile(r"^\s*(?:MC|M\.?C|Dra?|Mtr[oa]|Ing|Lic|Prof|Profa|Mtra)\.?\s+\S", re.I)
RE_TITULO_ESTILO = ("title", "título", "titulo")
RE_SEC_OBJ_GRAL = re.compile(r"^objetivos? general(?:es)?$")
RE_PARRAFO_OBJ = re.compile(r"^\s*objetivos? general(?:es)?\s*[:.\-–—]\s*(\S.*)$", re.I | re.S)


def palabras(t):
    return [w for w in t.split() if re.search(r"\w", w)]


def norm(t):
    """Minúsculas, sin acentos ni signos: para comparar títulos."""
    return " ".join(re.sub(r"[^a-z0-9ñ]+", " ", sin_acentos(t.lower())).split())


def raiz5(w):
    return sin_acentos(w.lower())[:5]


# ---------------------------------------------------------------- lectura
def titulo_de_portada(pars, fin_p, buscadores=()):
    """Título de la portada: párrafos contiguos de estilo Título o, si no hay, la línea más larga que no es una etiqueta ni un
    docente, con las líneas contiguas del mismo tipo de letra (el título puede ocupar varias líneas). None si no se reconoce."""
    import institucional as INS
    lineas = INS.lineas_portada(pars, fin_p)
    if not lineas:
        return None
    est = [k for k, (_, p) in enumerate(lineas) if p.get("estilo", "").lower() in RE_TITULO_ESTILO]
    if est:
        a = b = est[0]
        while b + 1 < len(lineas) and (b + 1) in est:
            b += 1
        return " ".join(t for t, _ in lineas[a:b + 1])
    otros = list(buscadores)
    textos = [t for t, _ in lineas]
    excl = set()   # lista de integrantes: desde su etiqueta hasta la siguiente etiqueta o línea de lugar y fecha
    for k, t in enumerate(textos):
        if INS.RE_INTEGRANTES.match(t):
            excl.add(k)
            for j in range(k + 1, len(textos)):
                if INS.RE_ETIQUETA_PORTADA.match(textos[j]) or INS.RE_MES_ANIO.search(sin_acentos(textos[j].lower())):
                    break
                excl.add(j)

    def candidata(k, min_pal):
        t = textos[k]
        return (k not in excl and INS._candidato_titulo(t, otros, min_pal) and not RE_HONORIFICO.match(t) and "@" not in t
                and "[[" not in t and not re.search(r"\bcontrol\b|\bgrupo\b|\bsemestre\b", sin_acentos(t.lower())))

    def mayus(t):
        letras = [c for c in t if c.isalpha()]
        return bool(letras) and all(c.isupper() for c in letras)

    mejor = None   # (palabras, a, b): el bloque contiguo de líneas candidatas del mismo tipo de letra con más palabras
    k = 0
    while k < len(textos):
        if not candidata(k, 2):
            k += 1
            continue
        a = b = k
        while b + 1 < len(textos) and candidata(b + 1, 2) and mayus(textos[b + 1]) == mayus(textos[k]):
            b += 1
        n = sum(len(palabras(x)) for x in textos[a:b + 1])
        if any(candidata(j, 4) for j in range(a, b + 1)) and (mejor is None or n > mejor[0]):
            mejor = (n, a, b)
        k = b + 1
    return " ".join(textos[mejor[1]:mejor[2] + 1]) if mejor else None


def objetivo_general(pars):
    """Texto del objetivo general: párrafos bajo el encabezado «Objetivo general» (hasta el siguiente encabezado) o un
    párrafo «Objetivo general: …». None si no hay."""
    for k, p in enumerate(pars):
        if p.get("es_titulo") and RE_SEC_OBJ_GRAL.match(_norm_encabezado(p["texto"])):
            partes = []
            for q in pars[k + 1:]:
                if q.get("es_titulo"):
                    break
                if q.get("en_tabla") or not q["texto"].strip() or q.get("estilo", "").lower().startswith("toc"):
                    continue
                partes.append(" ".join(q["texto"].split()))
            if partes:
                return " ".join(partes)
    for p in pars:
        if p.get("es_titulo") or p.get("estilo", "").lower().startswith("toc"):
            continue
        m = RE_PARRAFO_OBJ.match(p["texto"].strip())
        if m:
            return " ".join(m.group(1).split())
    return None


def _norm_encabezado(t):
    t = sin_acentos(t.lower()).strip()
    t = re.sub(r"^(?:\d+(?:\.\d+)*\.?|[ivxlc]+\.)\s+", "", t)
    return " ".join(re.sub(r"[^\w\s]", " ", t).split())


def config_equipo(path):
    """`.editorial.yaml` del documento: (titulo fijo o None, titulo_config dict, formato.titulo_max_palabras o None)."""
    ruta = auditar.buscar_equipo(str(path))
    if not ruta or not ruta.exists():
        return None, {}, None
    try:
        cfg = auditar.yaml.safe_load(ruta.read_text(encoding="utf-8")) or {}
    except auditar.yaml.YAMLError:
        return None, {}, None
    fijo = cfg.get("titulo")
    tc = cfg.get("titulo_config") if isinstance(cfg.get("titulo_config"), dict) else {}
    lim = (cfg.get("formato") or {}).get("titulo_max_palabras") if isinstance(cfg.get("formato"), dict) else None
    return (" ".join(str(fijo).split()) if fijo else None), tc, lim


def leer(path):
    """{titulo, objetivo, pars} del documento. `titulo` None si no se reconoce la portada (o `title:` en md)."""
    auditar.validar_entrada(path)
    if str(path).lower().endswith(".docx"):
        pars, _ = auditar.cargar_docx(str(path))
        cuerpo, tit, entradas = auditar.partir(pars)
        fin_p = auditar.fin_portada(pars)
        titulo = titulo_de_portada(pars, fin_p) if fin_p else None
    else:
        pars, meta = auditar.cargar_md(str(path), frontmatter=True)
        titulo = " ".join(str(meta.get("title")).split()) if meta.get("title") else None
        if not titulo:
            h1 = next((p for p in pars if p.get("es_titulo") and p.get("nivel", 1) == 1), None)
            titulo = " ".join(h1["texto"].split()) if h1 else None
    return {"titulo": titulo, "objetivo": objetivo_general(pars), "pars": pars}


# ---------------------------------------------------------------- diagnóstico
def _patrones(cfg):
    sobran = [(re.compile(rx), et) for rx, et in SOBRAN_DEFECTO]
    for x in (cfg or {}).get("sobran") or []:
        x = sin_acentos(str(x).lower())
        try:
            sobran.append((re.compile(r"\b" + x + r"\b" if re.fullmatch(r"[\w\- ]+", x) else x), "detalle declarado en titulo_config"))
        except re.error:
            pass
    promesas = [re.compile(rx) for rx in PROMESAS_DEFECTO]
    for x in (cfg or {}).get("promesas") or []:
        x = sin_acentos(str(x).lower())
        try:
            promesas.append(re.compile(r"\b" + x + r"\b" if re.fullmatch(r"[\w\- ]+", x) else x))
        except re.error:
            pass
    return sobran, promesas


def nombre_proyecto(titulo, cfg=None):
    """(nombre o sigla, está_antes_de_dos_puntos). «TUTOR-AI: tutor…» -> («TUTOR-AI», True); sin ellos, la primera sigla en mayúsculas
    (TUTOR-AI, SIPROD) que no sea un detalle de método (ABC, RAG) y que no sea todo el título en mayúsculas."""
    m = re.match(r"^\s*([^:]{1,30}):\s*\S", titulo)
    if m and len(m.group(1).split()) <= 3:
        return m.group(1).strip(), True
    if titulo.upper() != titulo:
        sobran = _patrones(cfg)[0]
        for w in titulo.split():
            w = w.strip(",.;:()")
            if re.fullmatch(r"[A-ZÁÉÍÓÚÑ0-9]{2,}(?:-[A-Za-z0-9]+)*", w) and not any(rx.search(sin_acentos(w.lower())) for rx, _ in sobran):
                return w, False
    return None, False


def nucleo(titulo, cfg=None):
    """Palabras de contenido del título (objeto y propósito): sin sigla, sin detalles que sobran, sin promesas, sin
    infinitivos de propósito ni palabras vacías. Devuelve [palabra sin acentos]."""
    sobran, promesas = _patrones(cfg)
    nombre, _ = nombre_proyecto(titulo, cfg)
    t = sin_acentos(titulo.lower())
    if nombre:
        t = t.replace(sin_acentos(nombre.lower()), " ")
    for rx, _ in sobran:
        t = rx.sub(" ", t)
    for rx in promesas:
        t = rx.sub(" ", t)
    out = []
    for w in re.findall(r"[a-zñ]{4,}", t):
        if w in STOP or re.search(r"(?:ar|er|ir)(?:se)?$", w) and len(w) >= 5 or w.endswith("mente"):
            continue
        if raiz5(w) not in {raiz5(x) for x in out}:
            out.append(w)
    return out


def terminos_objetivo(objetivo, cfg=None, maximo=8):
    """Palabras de contenido del objetivo (sin verbos genéricos, sin detalles de método), en orden de aparición."""
    import congruencia
    sobran, _ = _patrones(cfg)
    t = sin_acentos(congruencia.sin_citas(objetivo).lower())
    for rx, _ in sobran:
        t = rx.sub(" ", t)
    out, vistos = [], set()
    for w in re.findall(r"[a-zñ]{5,}", t):
        if w in congruencia.VERBOS_GENERICOS or w in congruencia.STOP_OBJ or w in STOP or w.endswith("mente"):
            continue
        if re.search(r"(?:ar|er|ir)(?:se)?$", w) or raiz5(w) in vistos:
            continue
        vistos.add(raiz5(w))
        out.append(w)
    return out[:maximo]


def _con_acentos(palabras_, texto):
    """Cada palabra (sin acentos) como aparece en `texto` (con sus acentos)."""
    mapa = {sin_acentos(w.lower()): w.lower() for w in re.findall(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+", texto)}
    return [mapa.get(w, w) for w in palabras_]


def cobertura(titulo, objetivo, cfg=None):
    """(términos del núcleo del título que el objetivo no usa, núcleo). Coincidencia por prefijo de 5 letras."""
    nuc = nucleo(titulo, cfg)
    raices_obj = {raiz5(w) for w in re.findall(r"[a-zñ]{4,}", sin_acentos(objetivo.lower()))}
    return [w for w in nuc if raiz5(w) not in raices_obj], nuc


def diagnosticar(titulo, objetivo=None, cfg=None, max_palabras=None):
    cfg = cfg or {}
    mx = max_palabras or cfg.get("max_palabras") or MAX_PALABRAS
    sobran_rx, promesas_rx = _patrones(cfg)
    t = sin_acentos(titulo.lower())
    n = len(palabras(titulo))
    nombre, antes = nombre_proyecto(titulo, cfg)
    sobran, vistos = [], set()
    for rx, et in sobran_rx:
        for m in rx.finditer(t):
            k = (m.start(), m.group(0))
            if k not in vistos:
                vistos.add(k)
                sobran.append({"texto": titulo[m.start():m.end()] if len(titulo) == len(t) else m.group(0), "motivo": et})
    promesas = []
    for rx in promesas_rx:
        for m in rx.finditer(t):
            promesas.append(titulo[m.start():m.end()] if len(titulo) == len(t) else m.group(0))
    cifras = re.findall(r"\d+(?:[.,]\d+)*\s*%?", re.sub(r"\b[a-z]+-?\d+[a-z]*\b|\b\w*\d\w*-\w+", " ", titulo))
    cifras = [c.strip() for c in cifras if c.strip() and not any(c.strip() in s["texto"] for s in sobran)]
    obs = []
    if n > mx:
        obs.append(f"{n} palabras: el máximo recomendado es {mx} (receta de 8 a 15); quita detalle")
    elif n < MIN_PALABRAS:
        obs.append(f"{n} palabras: demasiado corto para identificar objeto y propósito (receta de 8 a 15)")
    if not nombre:
        obs.append("sin sigla ni nombre del proyecto al inicio («Nombre: objeto + para qué»)")
    elif not antes:
        obs.append(f"la sigla «{nombre}» no encabeza el título: «{nombre}: objeto + para qué»")
    if sobran:
        obs.append("detalle de método o tecnología que sobra: " + ", ".join(f"«{s['texto']}»" for s in sobran))
    if promesas:
        obs.append("promesa de resultado que el protocolo no evalúa: " + ", ".join(f"«{p}»" for p in promesas)
                   + " (usa «apoyar», «contribuir a» o «explorar» si solo se evalúa)")
    if cifras:
        obs.append("cifras en el título: " + ", ".join(f"«{c}»" for c in cifras))
    r = {"titulo": titulo, "palabras": n, "max_palabras": mx, "nombre_proyecto": nombre, "sigla_al_inicio": antes,
         "sobran": sobran, "promesas": promesas, "cifras": cifras, "nucleo": nucleo(titulo, cfg)}
    if objetivo:
        faltan_obj, nuc = cobertura(titulo, objetivo, cfg)
        raices_tit = {raiz5(w) for w in re.findall(r"[a-zñ]{4,}", t)}
        no_recoge = [w for w in terminos_objetivo(objetivo, cfg) if raiz5(w) not in raices_tit]
        r["objetivo"] = objetivo
        r["objetivo_no_recoge"] = no_recoge
        faltan_obj = _con_acentos(faltan_obj, titulo)
        no_recoge = _con_acentos(no_recoge, objetivo)
        r["objetivo_no_recoge"] = no_recoge
        r["titulo_no_en_objetivo"] = faltan_obj
        if no_recoge:
            obs.append("términos clave del objetivo que el título no recoge: " + ", ".join(no_recoge))
        if faltan_obj:
            obs.append("términos del título que el objetivo general no usa: " + ", ".join(faltan_obj) + " (CON-021)")
    r["observaciones"] = obs
    r["limpio"] = not obs
    return r


def incoherencia(titulo, objetivo, cfg=None):
    """CON-021: núcleo del título ausente del objetivo general. (faltan, núcleo) o None si es coherente o no hay base:
    hacen falta >= 4 términos de núcleo y que falte al menos el 30 %."""
    faltan, nuc = cobertura(titulo, objetivo, cfg)
    if len(nuc) >= 4 and len(palabras(objetivo)) >= 8 and len(faltan) * 10 >= 3 * len(nuc):
        return faltan, nuc
    return None


# ---------------------------------------------------------------- CLI
def imprimir(r, etiqueta):
    print(f"{etiqueta}: {r['titulo']}")
    print(f"  palabras: {r['palabras']} (máximo recomendado {r['max_palabras']})   sigla o nombre: {r['nombre_proyecto'] or 'no'}")
    if r["sobran"]:
        print("  sobran: " + "; ".join(f"«{s['texto']}» ({s['motivo']})" for s in r["sobran"]))
    if r["promesas"]:
        print("  promesas: " + ", ".join(f"«{p}»" for p in r["promesas"]))
    if r["cifras"]:
        print("  cifras: " + ", ".join(r["cifras"]))
    if "objetivo_no_recoge" in r:
        print("  objetivo no recogido en el título: " + (", ".join(r["objetivo_no_recoge"]) or "nada"))
        print("  título no usado en el objetivo: " + (", ".join(r["titulo_no_en_objetivo"]) or "nada"))
    if r["observaciones"]:
        print("  observaciones:")
        for o in r["observaciones"]:
            print("   - " + o)
    else:
        print("  sin observaciones")


def main():
    ap = argparse.ArgumentParser(description="Título concreto: diagnóstico del título de portada frente al objetivo general.")
    ap.add_argument("documento")
    ap.add_argument("--max-palabras", type=int, help=f"máximo recomendado (por defecto titulo_config.max_palabras o {MAX_PALABRAS})")
    ap.add_argument("--opcion", action="append", default=[], metavar="TÍTULO", help="título candidato a evaluar (repetible)")
    ap.add_argument("--perfil", help="se acepta por uniformidad; el diagnóstico no depende del perfil")
    ap.add_argument("--json", metavar="RUTA", help="escribe el diagnóstico completo como JSON")
    a = ap.parse_args()
    cli.utf8()
    d = leer(a.documento)
    fijo, cfg, lim = config_equipo(a.documento)
    out = {"documento": a.documento, "titulo_fijo": fijo, "limite_institucional": lim, "opciones": []}
    if not d["titulo"]:
        print("No se reconoce el título de la portada" + (" (se usa `titulo:` de .editorial.yaml)" if fijo else "") + ".")
    base = d["titulo"] or fijo
    if base:
        r = diagnosticar(base, d["objetivo"], cfg, a.max_palabras)
        out["actual"] = r
        imprimir(r, "Título de la portada" if d["titulo"] else "Título fijado")
    if d["objetivo"] is None:
        print("Objetivo general: no se encontró la sección «Objetivo general».")
    else:
        print("Objetivo general: " + d["objetivo"][:300] + ("…" if len(d["objetivo"]) > 300 else ""))
    if lim and d["titulo"] and len(palabras(d["titulo"])) > lim:
        print(f"Límite institucional: {lim} palabras (INS-007) superado.")
    if fijo:
        coincide = bool(d["titulo"]) and norm(fijo) == norm(d["titulo"])
        out["coincide_fijo"] = coincide
        print(f"Título fijado en .editorial.yaml: {fijo} -> " + ("la portada coincide" if coincide else "la portada NO coincide (INS-010)"))
    for k, op in enumerate(a.opcion, 1):
        r = diagnosticar(" ".join(op.split()), d["objetivo"], cfg, a.max_palabras)
        out["opciones"].append(r)
        imprimir(r, f"Opción {k}")
    cli.escribir_json(a.json, out)
    sys.exit(cli.OK)


if __name__ == "__main__":
    main()
