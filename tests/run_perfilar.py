#!/usr/bin/env python3
"""Pruebas de `/perfilar` (sin red): la guía de una escuela se convierte en reglas con su cita de origen.

Uso: python -I tests/run_perfilar.py
  extraccion     guía inventada en .docx y en PDF (reportlab): fuente, márgenes, interlineado, sangría, jerarquía de títulos, paginación
                 por partes, tablas, norma de citas, % y años de fuentes, título máximo, voz y tiempo, resumen, portada; cada valor con
                 `guía p. N: «cita literal»` y la cita está de verdad en el texto de la guía; el PDF y el .docx dan los mismos valores
  estructura     capítulos y subcapítulos numerados con su descripción y sus preguntas guía; preliminares; el perfil y la estructura
                 los acepta el propio plugin (sin «clave desconocida»)
  preguntas      lo que la guía no dice (alineación) y las preferencias (registro, extensión, citas, salida, fuentes a evitar) salen en
                 `preguntas:`; --responder las aplica con origen «respuesta del usuario»
  sin-sobrescribir  un .editorial.yaml existente no se toca: .editorial.propuesto.yaml y un diff legible
  modelo-portada --modelo-portada mide la portada y registra un `vinculante` tipo modelo con su spec
  ingles         guía en inglés: patrones en inglés (Level 1-5, margins, double-spaced, IEEE, one paragraph)
  errores        guía inexistente, formato no soportado y .docx vacío salen con código 2 y mensaje, sin traceback
  comparar       el comparador de perfiles: una guía con valores conocidos coincide al 100 % con su perfil esperado
La prueba dorada con una guía real es local y no se distribuye (tests/reales/privado/run_perfilar_dorada.py; se salta si falta el archivo).
"""
import hashlib
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import docx  # noqa: E402
import yaml  # noqa: E402

import perfilar  # noqa: E402

PY = [sys.executable, "-I", str(ROOT / "scripts" / "editorial.py")]

GUIA_ES = [
    [  # página 1
        "UNIVERSIDAD EJEMPLO DEL NORTE",
        "FACULTAD DE INGENIERÍA",
        "GUÍA DE FORMATO PARA TESINAS",
        "Asignatura: Seminario de Tesis (SEM-101)",
        "Lineamientos Oficiales — Ciclo 2027",
    ],
    [  # página 2
        "SECCIÓN I. FORMATO",
        "Toda tesina cumplirá las especificaciones de la TABLA I, basadas en APA (7.ª edición) para redacción y citación, e IEEE para tablas y figuras:",
        "Tipografía y tamaño: Arial a 11 puntos en todo el documento, incluidos los títulos.",
        "Márgenes: 3 cm en los cuatro lados.",
        "Interlineado doble en todo el documento.",
        "Sangría de primera línea de 0.5 pulgadas al inicio de cada párrafo normal.",
        "Jerarquía de títulos",
        "• Nivel 1: CENTRADO, MAYÚSCULAS, NEGRITAS (inicia en página nueva).",
        "• Nivel 2: Alineado a la izquierda, Negritas, Tipo Oración.",
        "• Nivel 3: Alineado a la izquierda, Negritas, Cursivas.",
        "• Nivel 4: Sangría 1.27 cm, Negritas, Tipo Oración, punto final.",
        "• Nivel 5: Sangría 1.27 cm, Negritas, Cursivas, punto final.",
        "Numeración de páginas",
        "• Portada: Sin número visible.",
        "• Páginas preliminares: números romanos en minúsculas (i, ii, iii).",
        "• Cuerpo: números arábigos (1, 2, 3...) en la esquina inferior derecha.",
        "Tablas (Estilo IEEE): centradas. Título en la parte SUPERIOR en MAYÚSCULAS, tamaño 9-10 pt, numeración romana (ej. TABLA I).",
        "Figuras (Estilo IEEE): centradas. Título en la parte INFERIOR en tipo oración, tamaño 9-10 pt, numeración arábiga (ej. Fig. 1.).",
        "Citas y referencias: estricto apego a APA 7.ª edición (Autor, Año) y lista alfabética con sangría francesa.",
        "Redacción en tercera persona (impersonal) y en tiempo pasado.",
        "Al menos el 60% de las referencias serán literatura arbitrada publicada en los últimos 10 años; al menos 8 fuentes en total.",
        "El título de la tesina no debe exceder 15 palabras.",
    ],
    [  # página 3
        "SECCIÓN II. ESTRUCTURA",
        "Portada: debe incluir el logotipo institucional (UEN), nombre de la institución, título del trabajo, nombre completo y número de control del autor, "
        "nombre del asesor, lugar (Monterrey, Nuevo León) y fecha (Mes y Año).",
        "Páginas preliminares",
        "• Resumen (página i): Síntesis de 200 a 300 palabras en un solo párrafo con sangría, seguido de 4 a 6 palabras clave.",
        "• Índice de contenido (página ii): Tabla de contenido automática con capítulos y páginas.",
        "1. INTRODUCCIÓN",
        "Presenta el tema y la razón del estudio.",
        "1.1. Contexto general",
        "Describe el entorno donde surge el problema.",
        "1.2. Objetivos del estudio",
        "Expone el objetivo general y los específicos.",
        "GUÍA RÁPIDA — CAPÍTULO 1",
        "Preguntas guía: ¿Qué problema se atiende? ¿Por qué importa ahora?",
        "2. MÉTODO",
        "Explica cómo se hará el estudio.",
        "2.1. Diseño de la investigación",
        "Define el enfoque y el alcance.",
        "2.2. Participantes y muestra",
        "Describe a quiénes se estudia (criterios de inclusión y exclusión).",
    ],
]
ENCABEZADO = "Universidad Ejemplo del Norte — Guía de formato 2027"

GUIA_EN = [
    ["EXAMPLE STATE UNIVERSITY", "SCHOOL OF COMPUTING", "THESIS FORMATTING GUIDE", "Course: Thesis Seminar (TS-200)", "Cycle 2027"],
    ["SECTION I. FORMAT",
     "All theses must follow these specifications, based on APA (7th edition) for writing and citation.",
     "Typeface: 12-point Times New Roman throughout, headings included.",
     "Margins: 1 inch on all four sides.",
     "The text is double-spaced and left-aligned alignment in paragraphs.",
     "First-line indent of 0.5 inches at the start of each normal paragraph.",
     "Level 1: Centered, Bold, Title Case Heading (starts on a new page).",
     "Level 2: Flush left, Bold, Title Case.",
     "Citations and references: strict adherence to APA 7th edition.",
     "At least 70% of the references must be peer-reviewed sources published in the last 5 years.",
     "The title must be no more than 12 words.",
     "Abstract: 150 to 250 words in one paragraph, no indent, followed by 3 to 5 keywords."],
    ["Cover page: must include the university logo (EXU), name of the institution, title of the thesis, full name and student ID of the author, "
     "name of the advisor, place (Austin, Texas) and date (Month and Year).",
     "Preliminary pages", "• Abstract (page i): Executive summary of 150 to 250 words.",
     "1. INTRODUCTION", "Introduces the topic.", "1.1. Background", "Describes the context.", "2. METHOD", "Explains the procedure."],
]


def guia_docx(ruta, paginas, saltar=True):
    d = docx.Document()
    for i, lineas in enumerate(paginas):
        if i and saltar:
            d.add_page_break()
        for l in lineas:
            d.add_paragraph(l)
    d.save(str(ruta))


def guia_pdf(ruta, paginas, encabezado=ENCABEZADO):
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    c = canvas.Canvas(str(ruta), pagesize=letter)
    for lineas in paginas:
        y = 750
        c.setFont("Helvetica", 9)
        c.drawString(72, 770, encabezado)  # encabezado repetido en cada página
        c.setFont("Helvetica", 10)
        for l in lineas:
            # parte la línea larga en renglones de ~95 caracteres
            partes = [l[i:i + 95] for i in range(0, len(l), 95)] if len(l) > 95 else [l]
            palabras = l.split(" ")
            partes, act = [], ""
            for w in palabras:
                if len(act) + len(w) + 1 > 95:
                    partes.append(act)
                    act = w
                else:
                    act = (act + " " + w).strip()
            partes.append(act)
            for r in partes:
                c.drawString(72, y, r)
                y -= 13
        c.showPage()
    c.save()


def correr(*args):
    r = subprocess.run(PY + [str(a) for a in args], capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.returncode, r.stdout + r.stderr


def sha(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


def cargar(p):
    return yaml.safe_load(pathlib.Path(p).read_text(encoding="utf-8"))


def aplanar_texto(paginas):
    return " ".join(" ".join(" ".join(l.split()) for l in p) for p in paginas)


def esperado_es(perfil):
    """Valores que la guía inventada dice; devuelve lista de fallas."""
    f = perfil.get("formato", {})
    fallas = []
    comprobar = [
        (f.get("fuente"), {"nombre": "Arial", "pt": 11}, "fuente"),
        (f.get("interlineado"), 2, "interlineado"),
        (perfil.get("reglas_guia", {}).get("margenes_cm"), 3, "márgenes"),
        (perfil.get("reglas_guia", {}).get("sangria_primera_linea_cm"), 1.27, "sangría"),
        (f.get("paginacion"), {"portada": "sin_numero", "preliminares": "romanos", "cuerpo": "arabigos", "posicion": "pie_derecha"}, "paginación"),
        (f.get("nivel1"), {"mayusculas": True, "numerado": True}, "nivel1"),
        (f.get("capitulo_pagina_nueva"), True, "capítulo en página nueva"),
        (perfil.get("tablas_figuras"), "ieee", "tablas_figuras"),
        (perfil.get("perfil"), "apa7", "perfil (citas)"),
        (f.get("fuentes_recientes"), {"anios": 10, "porcentaje": 60, "arbitradas": True}, "fuentes recientes"),
        (perfil.get("minimo_fuentes"), 8, "mínimo de fuentes"),
        (f.get("titulo_max_palabras"), 15, "título máximo"),
        (perfil.get("voz"), "impersonal", "voz"),
        (perfil.get("tiempo_verbal"), "pasado", "tiempo verbal"),
        (f.get("resumen"), {"palabras": [200, 300], "un_parrafo": True, "sangria": True, "palabras_clave": [4, 6]}, "resumen"),
        (f.get("rotulos_pt"), [9, 10], "rótulos pt"),
        (f.get("portada", {}).get("fecha"), "mes_anio", "fecha de portada"),
        (f.get("portada", {}).get("numero_control"), True, "número de control"),
        (f.get("portada", {}).get("logos"), ["UEN"], "logos"),
        (perfil.get("fuentes", {}).get("porcentaje_arbitradas"), 60, "fuentes.porcentaje_arbitradas"),
        (perfil.get("portada_numero"), False, "portada_numero"),
    ]
    for obt, esp, nombre in comprobar:
        if obt != esp:
            fallas.append(f"{nombre}: esperado {esp!r}, obtenido {obt!r}")
    jer = perfil.get("reglas_guia", {}).get("jerarquia_titulos", {})
    if jer.get("nivel1", {}).get("alineacion") != "centrado" or not jer.get("nivel4", {}).get("punto_final") or jer.get("nivel5", {}).get("sangria_cm") != 1.27 \
            or not jer.get("nivel3", {}).get("cursivas") or jer.get("nivel2", {}).get("tipo_texto") != "oracion":
        fallas.append(f"jerarquía de títulos 1-5: {jer}")
    campos = [c["nombre"] for c in f.get("portada", {}).get("campos", [])]
    if len(campos) < 6 or not any(c.startswith("lugar (Monterrey, Nuevo León)") for c in campos):
        fallas.append(f"campos de portada: {campos}")
    return fallas


def prueba_extraccion(tmp):
    fallas = []
    base = pathlib.Path(tmp) / "ext"
    base.mkdir()
    gd, gp = base / "guia.docx", base / "guia.pdf"
    guia_docx(gd, GUIA_ES)
    try:
        guia_pdf(gp, GUIA_ES)
    except ImportError:
        print("SALTADA: PDF sintético (falta reportlab)")
        gp = None
    perfiles = {}
    for nombre, ruta in (("docx", gd), ("pdf", gp)):
        if ruta is None:
            continue
        carpeta = base / nombre
        carpeta.mkdir()
        code, out = correr("perfilar", ruta, "--out", carpeta / ".editorial.yaml", "--estructura-id", "tesina-ejemplo")
        if code != 0:
            fallas.append(f"{nombre}: perfilar salió con {code}: {out[-300:]}")
            continue
        perfil = cargar(carpeta / ".editorial.yaml")
        perfiles[nombre] = perfil
        fallas += [f"{nombre}: {x}" for x in esperado_es(perfil)]
        # cada valor lleva su origen con la cita literal presente en la guía
        org = perfil.get("origenes", {})
        texto = aplanar_texto(GUIA_ES)
        sin_origen = [k for k in ("formato.fuente.nombre", "formato.interlineado", "reglas_guia.margenes_cm", "formato.paginacion.cuerpo", "perfil",
                                  "formato.resumen.palabras", "formato.titulo_max_palabras", "formato.fuentes_recientes.porcentaje") if k not in org]
        if sin_origen:
            fallas.append(f"{nombre}: sin origen: {sin_origen}")
        malas = []
        for k, o in org.items():
            m = re.match(r"guía p\. (\d+): «(.+)»$", o)
            if o.startswith("derivado de") or o.startswith("respuesta"):
                continue
            if not m:
                malas.append((k, o[:60]))
                continue
            for trozo in re.split(r" \[…\] |»\s*·\s*p\. \d+:\s*«", m.group(2)):
                if " ".join(trozo.split()) not in texto:
                    malas.append((k, trozo[:60]))
        if malas:
            fallas.append(f"{nombre}: orígenes con cita que no está en la guía: {malas[:3]}")
        if nombre == "docx" and not org.get("formato.fuente.nombre", "").startswith("guía p. 2:"):
            fallas.append(f"docx: la página de la fuente debe ser 2: {org.get('formato.fuente.nombre')}")
    if "docx" in perfiles and "pdf" in perfiles:
        for k in ("formato", "perfil", "voz", "minimo_fuentes"):
            if perfiles["docx"].get(k) != perfiles["pdf"].get(k):
                fallas.append(f"el .docx y el PDF dan distinto en {k}: {perfiles['docx'].get(k)} / {perfiles['pdf'].get(k)}")
    return fallas


def prueba_estructura(tmp):
    fallas = []
    base = pathlib.Path(tmp) / "est"
    base.mkdir()
    gd = base / "guia.docx"
    guia_docx(gd, GUIA_ES)
    code, out = correr("perfilar", gd, "--out", base / ".editorial.yaml", "--estructura-id", "tesina-ejemplo")
    if code != 0:
        return [f"perfilar: {code} {out[-300:]}"]
    ruta = base / "estructuras" / "tesina-ejemplo.yaml"
    if not ruta.exists():
        return ["no escribió estructuras/tesina-ejemplo.yaml"]
    e = cargar(ruta)
    nombres = [(s["nombre"], s["nivel"], s.get("numero")) for s in e["secciones"]]
    esperado = [("Resumen", 1, None), ("Índice de contenido", 1, None), ("Introducción", 1, "1"), ("Contexto general", 2, "1.1"), ("Objetivos del estudio", 2, "1.2"),
                ("Método", 1, "2"), ("Diseño de la investigación", 2, "2.1"), ("Participantes y muestra", 2, "2.2")]
    if nombres != esperado:
        fallas.append(f"secciones: {nombres}")
    por_nombre = {s["nombre"]: s for s in e["secciones"]}
    if por_nombre.get("Introducción", {}).get("preguntas") != ["¿Qué problema se atiende?", "¿Por qué importa ahora?"]:
        fallas.append(f"preguntas guía del capítulo 1: {por_nombre.get('Introducción', {}).get('preguntas')}")
    if "entorno donde surge el problema" not in por_nombre.get("Contexto general", {}).get("proposito", ""):
        fallas.append("la descripción del subcapítulo no quedó en `proposito`")
    if por_nombre.get("Resumen", {}).get("palabras") != "200-300" or por_nombre.get("Resumen", {}).get("palabras_clave") != "4-6":
        fallas.append(f"límites del resumen: {por_nombre.get('Resumen')}")
    if not all(s.get("origen", "").startswith("guía p. 3: «") for s in e["secciones"]):
        fallas.append("cada sección lleva su origen «guía p. 3: «…»»")
    # lo acepta el plugin: normalización del formato sin claves desconocidas ni avisos; la estructura la lee estructura.py
    import institucional
    perfil = cargar(base / ".editorial.yaml")
    f, avisos = institucional.normalizar(perfil.get("formato"), None, base)
    if avisos:
        fallas.append(f"el bloque formato: del perfil generado da avisos: {avisos}")
    if not f.get("portada") or f.get("fuente", {}).get("nombre") != "Arial":
        fallas.append("el formato generado no se normaliza (portada/fuente)")
    return fallas


def prueba_preguntas(tmp):
    fallas = []
    base = pathlib.Path(tmp) / "preg"
    base.mkdir()
    gd = base / "guia.docx"
    guia_docx(gd, GUIA_ES)
    code, out = correr("perfilar", gd, "--out", base / ".editorial.yaml", "--estructura-id", "t", "--json", base / "r.json")
    perfil = cargar(base / ".editorial.yaml")
    ids = [q["id"] for q in perfil.get("preguntas", [])]
    for esperado in ("P-alineacion", "P-registro", "P-extension", "P-citas-densidad", "P-salida", "P-evitar"):
        if esperado not in ids:
            fallas.append(f"falta la pregunta {esperado}: {ids}")
    if "alineacion" in perfil.get("formato", {}):
        fallas.append("la guía no dice la alineación: no debe inventarla")
    q = next((q for q in perfil.get("preguntas", []) if q["id"] == "P-alineacion"), None)
    if not q or len(q["opciones"]) < 2 or not q["opciones"][0].startswith("1) "):
        fallas.append(f"las preguntas llevan opciones numeradas: {q}")
    # responder
    resp = base / "respuestas.yaml"
    resp.write_text("P-alineacion: 2\nP-registro: tecnico\npreferencias.salida: 1\nP-evitar: [1]\nP-extension: 3\n", encoding="utf-8", newline="\n")
    out_dir = base / "r"
    out_dir.mkdir()
    code, out = correr("perfilar", gd, "--out", out_dir / ".editorial.yaml", "--estructura-id", "t", "--responder", resp)
    if code != 0:
        return fallas + [f"--responder: {code} {out[-300:]}"]
    p2 = cargar(out_dir / ".editorial.yaml")
    if p2["formato"].get("alineacion") != "justificada":
        fallas.append(f"P-alineacion: 2 -> justificada: {p2['formato'].get('alineacion')}")
    pref = p2.get("preferencias", {})
    if pref.get("registro") != "tecnico" or pref.get("salida") != ["docx", "pdf"] or pref.get("extension") != "media":
        fallas.append(f"preferencias aplicadas: {pref}")
    if p2.get("fuentes", {}).get("evitar") != ["wikipedia", "blog", "foro"]:
        fallas.append(f"P-evitar (lista [1]): {p2.get('fuentes')}")
    if not p2["origenes"].get("formato.alineacion", "").startswith("respuesta del usuario"):
        fallas.append("las respuestas llevan origen «respuesta del usuario»")
    restantes = [q["id"] for q in p2.get("preguntas", [])]
    if restantes != ["P-citas-densidad"]:
        fallas.append(f"quedan sin responder solo las no contestadas: {restantes}")
    return fallas


def prueba_no_sobrescribir(tmp):
    fallas = []
    base = pathlib.Path(tmp) / "nos"
    base.mkdir()
    gd = base / "guia.docx"
    guia_docx(gd, GUIA_ES)
    propio = base / ".editorial.yaml"
    propio.write_text("perfil: ieee\nformato:\n  interlineado: 1\n  fuente: {nombre: Calibri, pt: 10}\nmio: true\n", encoding="utf-8", newline="\n")
    antes = sha(propio)
    code, out = correr("perfilar", gd, "--out", propio, "--estructura-id", "t")
    if code != 0:
        return [f"perfilar: {code} {out[-300:]}"]
    if sha(propio) != antes:
        fallas.append("sobrescribió el .editorial.yaml existente")
    prop, diff = base / ".editorial.propuesto.yaml", base / ".editorial.propuesto.diff"
    if not prop.exists() or not diff.exists():
        return fallas + ["falta .editorial.propuesto.yaml o su diff"]
    t = diff.read_text(encoding="utf-8")
    if "~ formato.interlineado: 1 -> 2" not in t or "~ perfil: \"ieee\" -> \"apa7\"" not in t or "- mio: true" not in t or "+ formato.margenes" in t:
        pass
    if "~ formato.interlineado: 1 -> 2" not in t or '~ perfil: "ieee" -> "apa7"' not in t or "- mio: true" not in t:
        fallas.append(f"diff legible (~ cambia, + nuevo, - solo tuyo):\n{t[:400]}")
    if "no se sobrescribe" not in out.lower():
        fallas.append("el mensaje dice que no se sobrescribe")
    # segunda vez: la estructura existente tampoco se toca
    est = base / "estructuras" / "t.yaml"
    a = sha(est)
    code, out = correr("perfilar", gd, "--out", propio, "--estructura-id", "t")
    if sha(est) != a or not (base / "estructuras" / "t.propuesto.yaml").exists():
        fallas.append("la estructura existente no se sobrescribe (t.propuesto.yaml)")
    return fallas


def prueba_modelo_portada(tmp):
    fallas = []
    base = pathlib.Path(tmp) / "mod"
    base.mkdir()
    gd = base / "guia.docx"
    guia_docx(gd, GUIA_ES)
    modelo = base / "modelo.docx"
    d = docx.Document()
    for t in ("UNIVERSIDAD EJEMPLO DEL NORTE", "Título del trabajo de ejemplo", "Autor: Nombre Apellido", "Monterrey, Nuevo León — Mayo 2027"):
        p = d.add_paragraph()
        r = p.add_run(t)
        r.bold = t.isupper()
    d.save(str(modelo))
    code, out = correr("perfilar", gd, "--modelo-portada", modelo, "--out", base / ".editorial.yaml", "--estructura-id", "t")
    if code != 0:
        return [f"--modelo-portada: {code} {out[-400:]}"]
    perfil = cargar(base / ".editorial.yaml")
    v = perfil.get("vinculante")
    spec = base / "portada-modelo.json"
    if not v or v[0].get("tipo") != "modelo" or v[0].get("ambito") != "portada" or v[0].get("spec") != "portada-modelo.json" or not spec.exists():
        return [f"vinculante tipo modelo con su spec: {v}"]
    s = json.loads(spec.read_text(encoding="utf-8"))
    if len(s.get("lineas", [])) < 4:
        fallas.append(f"spec con las líneas del modelo: {len(s.get('lineas', []))}")
    # el plugin acepta el vinculante registrado
    import institucional
    try:
        vin = institucional.normalizar_vinculante(perfil["vinculante"], base)
        if vin[0]["tipo"] != "modelo" or not vin[0].get("spec"):
            fallas.append("normalizar_vinculante no cargó la spec")
    except institucional.ErrorPerfil as ex:
        fallas.append(f"el vinculante generado es inválido: {ex}")
    return fallas


def prueba_ingles(tmp):
    fallas = []
    base = pathlib.Path(tmp) / "en"
    base.mkdir()
    gd = base / "guide.docx"
    guia_docx(gd, GUIA_EN)
    code, out = correr("perfilar", gd, "--out", base / ".editorial.yaml", "--estructura-id", "thesis-example")
    if code != 0:
        return [f"guía en inglés: {code} {out[-300:]}"]
    p = cargar(base / ".editorial.yaml")
    f = p["formato"]
    esp = [(p.get("idioma"), "en"), (f.get("fuente"), {"nombre": "Times New Roman", "pt": 12}), (p.get("reglas_guia", {}).get("margenes_cm"), 2.54),
           (f.get("interlineado"), 2), (f.get("alineacion"), "izquierda"), (p.get("reglas_guia", {}).get("sangria_primera_linea_cm"), 1.27),
           (p.get("perfil"), "apa7"), (f.get("fuentes_recientes"), {"anios": 5, "porcentaje": 70, "arbitradas": True}), (f.get("titulo_max_palabras"), 12),
           (f.get("resumen", {}).get("palabras"), [150, 250]), (f.get("resumen", {}).get("un_parrafo"), True), (f.get("resumen", {}).get("sangria"), False),
           (f.get("resumen", {}).get("palabras_clave"), [3, 5]), (f.get("portada", {}).get("fecha"), "mes_anio"), (f.get("portada", {}).get("logos"), ["EXU"]),
           (f.get("portada", {}).get("numero_control"), True), (f.get("nivel1", {}).get("mayusculas"), False),
           (p.get("reglas_guia", {}).get("jerarquia_titulos", {}).get("nivel2", {}).get("tipo_texto"), "titulo")]
    for obt, e in esp:
        if obt != e:
            fallas.append(f"inglés: esperado {e!r}, obtenido {obt!r}")
    est = cargar(base / "estructuras" / "thesis-example.yaml")
    nombres = [s["nombre"] for s in est["secciones"]]
    if nombres != ["Abstract", "Introduction", "Background", "Method"]:
        fallas.append(f"estructura en inglés: {nombres}")
    return fallas


def prueba_errores(tmp):
    fallas = []
    base = pathlib.Path(tmp) / "err"
    base.mkdir()
    casos = [(["perfilar", base / "no-existe.pdf"], "no existe la guía"), ([ "perfilar", base / "x.txt"], "no soportada")]
    (base / "x.txt").write_text("hola", encoding="utf-8")
    vacio = base / "vacio.docx"
    docx.Document().save(str(vacio))
    casos.append((["perfilar", vacio], "no tiene texto"))
    for args, frag in casos:
        code, out = correr(*args, "--out", base / ".editorial.yaml")
        if code != 2 or frag not in out or "Traceback" in out:
            fallas.append(f"{args[1].name}: código {code} (esperado 2) {out[-160:]!r}")
    code, out = correr("perfilar")
    if code != 2:
        fallas.append(f"sin argumentos debe salir con 2, salió {code}")
    return fallas


def prueba_comparar(tmp):
    fallas = []
    base = pathlib.Path(tmp) / "cmp"
    base.mkdir()
    gd = base / "guia.docx"
    guia_docx(gd, GUIA_ES)
    code, out = correr("perfilar", gd, "--out", base / ".editorial.yaml", "--estructura-id", "tesina-ejemplo")
    gen = cargar(base / ".editorial.yaml")
    ref = {k: gen[k] for k in ("perfil", "voz", "tiempo_verbal", "minimo_fuentes", "tablas_figuras", "formato")}
    ref["formato"] = dict(gen["formato"])
    r = perfilar.comparar_perfil(gen, ref)
    if r["porcentaje"] != 100.0 or r["fallas"]:
        fallas.append(f"un perfil se compara al 100 % consigo mismo: {r['porcentaje']} {r['fallas'][:2]}")
    ref["formato"]["interlineado"] = 1.5
    ref["perfil"] = "ieee"
    r = perfilar.comparar_perfil(gen, ref)
    claves = {x[0] for x in r["fallas"]}
    if claves != {"formato.interlineado", "perfil"} or r["porcentaje"] >= 100:
        fallas.append(f"el comparador señala las claves distintas: {claves} {r['porcentaje']}")
    est = cargar(base / "estructuras" / "tesina-ejemplo.yaml")
    e = perfilar.comparar_estructura(est, est)
    if e["capitulos_referencia"] != 2 or e["subcapitulos_en_su_capitulo"] != 4 or e["perdidas"]:
        fallas.append(f"estructura contra sí misma: {e}")
    return fallas


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    tmp = tempfile.mkdtemp(prefix="perfilar")
    pruebas = [("extraccion", prueba_extraccion), ("estructura", prueba_estructura), ("preguntas", prueba_preguntas),
               ("sin-sobrescribir", prueba_no_sobrescribir), ("modelo-portada", prueba_modelo_portada), ("ingles", prueba_ingles),
               ("errores", prueba_errores), ("comparar", prueba_comparar)]
    solo = [a for a in sys.argv[1:] if not a.startswith("--")]
    if solo:
        pruebas = [x for x in pruebas if x[0] in solo]
    total = 0
    try:
        for nombre, fn in pruebas:
            try:
                fallas = fn(tmp)
            except Exception as ex:  # noqa: BLE001
                import traceback
                fallas = [f"EXCEPCIÓN {type(ex).__name__}: {ex}\n{traceback.format_exc()[-600:]}"]
            for f in fallas:
                print("FALLA", nombre, "-", f)
            total += len(fallas)
            print(("OK   " if not fallas else "FALLA"), nombre)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"== perfilar: {len(pruebas)} grupos, {total} fallas")
    sys.exit(1 if total else 0)


if __name__ == "__main__":
    main()
