#!/usr/bin/env python3
"""Pruebas sembradas de la versión 0.9.0 (sin red): herramientas de medida (`editorial.py medir`), reglas del usuario (INS-016) y exportación.

Uso: python -I tests/run_v09.py
  unidades      equivalencias (1.27 cm = 0.5 in = 36 pt, twips, EMU, medios puntos) y tolerancias por defecto
  herencia      valor efectivo como Word: docDefaults -> estilo -> estilo base -> párrafo directo -> run; francesa, centrado directo
  equivalencias lo equivalente NO es hallazgo (cm/in/pt, interlineado auto ×1.5 = exacto 18 pt con 12 pt, tolerancias) y lo que pasa
                de la tolerancia SÍ; la tolerancia de la regla se sobreescribe; excepciones legítimas (cita en bloque, centrado, nota)
  parser        frases en español e inglés -> reglas; lo ambiguo, incompleto o contradictorio vuelve como PREGUNTA; lo subjetivo, «no medible»
  pdf           PDF sintético (PyMuPDF): márgenes, sangría visible, paso de línea, fuentes, posición del número de página por página
  discrepancia  docx y PDF que no dicen lo mismo: AVISO, nunca violación; con LibreOffice, un render real sin avisos de margen ni de número
  no-medible    «al menos N pt», alcance inexistente, número con tabuladores sin PDF, frase subjetiva: «no medible» y nunca «cumple»
  auditar       `medidas:` en .editorial.yaml -> INS-016 con el origen del usuario; la excepción APA equivalente; entrada inválida = código 2
  perfilar      una guía con márgenes y sangría emite el bloque `medidas:` con su origen y el plugin lo acepta
  cli           editorial.py medir: --regla, --json, códigos de salida 0/1/2, despachador
  exportar      con remoto origin el commit nuevo lleva por padre origin/main (sin force, historial conservado); sin remoto, commit único
Código de salida 0 solo si todo pasa. Las pruebas que necesitan PyMuPDF o LibreOffice se saltan con «SALTADA: …» si no están.
"""
import contextlib
import io
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

import docx  # noqa: E402
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING  # noqa: E402
from docx.oxml import parse_xml  # noqa: E402
from docx.shared import Cm, Inches, Pt  # noqa: E402

import auditar  # noqa: E402
import libreoffice  # noqa: E402
import medidas as M  # noqa: E402
import medir  # noqa: E402
import unidades as U  # noqa: E402

PY = [sys.executable, "-I", str(ROOT / "scripts" / "editorial.py")]
NS = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
try:
    import fitz
    HAY_FITZ = True
except ImportError:
    HAY_FITZ = False
HAY_LO = libreoffice.buscar() is not None
LARGO = ("Este párrafo de prueba es lo bastante largo para contar como texto de cuerpo del documento, con más de ochenta caracteres "
         "en total y sin ser un título ni una nota.")


def correr(*args, cwd=None):
    r = subprocess.run(PY + [str(a) for a in args], capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=cwd,
                       env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    return r.returncode, r.stdout + r.stderr


# ---------------------------------------------------------------- constructores de documentos
def defaults(d, fuente="Times New Roman", pt=12, linea=360, regla="auto", despues=0):
    """docDefaults del documento: fuente, tamaño y espaciado (como los deja Word al guardar)."""
    st = d.styles.element
    dd = st.find(auditar.qn("w:docDefaults"))
    if dd is not None:
        st.remove(dd)
    el = parse_xml(f'<w:docDefaults {NS}><w:rPrDefault><w:rPr><w:rFonts w:ascii="{fuente}" w:hAnsi="{fuente}"/><w:sz w:val="{int(pt * 2)}"/></w:rPr></w:rPrDefault>'
                   f'<w:pPrDefault><w:pPr><w:spacing w:after="{int(despues * 20)}" w:line="{linea}" w:lineRule="{regla}"/></w:pPr></w:pPrDefault></w:docDefaults>')
    st.insert(0, el)
    # el Normal de la plantilla de python-docx trae sus propios valores: se quitan para que mande docDefaults
    normal = d.styles["Normal"].element
    for tag in ("w:pPr", "w:rPr"):
        e = normal.find(auditar.qn(tag))
        if e is not None:
            normal.remove(e)


def estilo(d, nombre, base, ppr="", rpr=""):
    from docx.enum.style import WD_STYLE_TYPE
    s = d.styles.add_style(nombre, WD_STYLE_TYPE.PARAGRAPH)
    s.base_style = d.styles[base]
    if ppr:
        s.element.append(parse_xml(f"<w:pPr {NS}>{ppr}</w:pPr>"))
    if rpr:
        s.element.append(parse_xml(f"<w:rPr {NS}>{rpr}</w:rPr>"))
    return s


def margenes(d, sup=2.54, inf=2.54, izq=2.54, der=2.54):
    for s in d.sections:
        s.page_width, s.page_height = Inches(8.5), Inches(11)
        s.top_margin, s.bottom_margin, s.left_margin, s.right_margin = Cm(sup), Cm(inf), Cm(izq), Cm(der)


def guardar(d, tmp, nombre):
    ruta = pathlib.Path(tmp) / nombre
    d.save(str(ruta))
    return str(ruta)


def doc_cuerpo(n=5, sangria_cm=1.27, linea=None, **kw):
    """Documento con n párrafos de cuerpo con sangría de primera línea."""
    d = docx.Document()
    defaults(d, **kw)
    margenes(d)
    for _ in range(n):
        p = d.add_paragraph(LARGO)
        if sangria_cm is not None:
            p.paragraph_format.first_line_indent = Cm(sangria_cm)
        if linea:
            p.paragraph_format.line_spacing = linea
    return d


def campo_pagina(parrafo, alinear=None, texto_antes="", tabs=0):
    if alinear is not None:
        parrafo.alignment = alinear
    if texto_antes:
        parrafo.add_run(texto_antes)
    for _ in range(tabs):
        parrafo.add_run().add_tab()
    parrafo._p.append(parse_xml(f'<w:fldSimple {NS} w:instr=" PAGE "><w:r><w:t>1</w:t></w:r></w:fldSimple>'))


def reglas(*frases):
    out = []
    for f in frases:
        r = M.parsear(f, "usuario prueba")
        out += [y for x in r["reglas"] for y in M.expandir(x)]
        assert not r["preguntas"], (f, r["preguntas"])
    return out


def veredicto(ruta, *frases, pdf=None):
    ficha = medir.ficha_docx(ruta)
    pdfm = medir.medir_pdf(pdf) if pdf else None
    return [M.evaluar_regla(r, ficha, pdfm) for r in reglas(*frases)], ficha, pdfm


# ---------------------------------------------------------------- pruebas
def prueba_unidades(tmp):
    f = []
    chk = lambda cond, msg: f.append(msg) if not cond else None  # noqa: E731
    chk(abs(U.a_pt(2.54, "cm") - 72) < 1e-6 and abs(U.a_pt(1, "in") - 72) < 1e-9, "2.54 cm = 1 in = 72 pt")
    chk(abs(U.a_pt(1.27, "cm") - U.a_pt(0.5, "in")) < 1e-6 and abs(U.a_pt(0.5, "in") - 36) < 1e-9, "1.27 cm = 0.5 in = 36 pt")
    chk(U.a_pt(1440, "twips") == 72 and abs(U.a_pt(914400, "emu") - 72) < 1e-9 and U.a_pt(24, "half") == 12, "twips, EMU y medios puntos")
    chk(U.unidad("pulgadas") == "in" and U.unidad("Centímetros") == "cm" and U.unidad("puntos") == "pt" and U.unidad("inches") == "in", "nombres de unidad es/en")
    chk(abs(U.de_pt(72, "cm") - 2.54) < 1e-9, "de_pt")
    chk(U.parsear_cantidad("0,5 pulgadas") == (0.5, "in") and U.parsear_cantidad("3 cm") == (3.0, "cm"), "parsear_cantidad")
    chk(U.tolerancia("margen") == U.a_pt(0.05, "cm") and U.tolerancia("espacio") == 0.5 and U.tolerancia("tamano") == 0.25, "tolerancias por defecto")
    chk(U.tolerancia("margen", "in", 0.1) == U.a_pt(0.1, "in"), "tolerancia de la regla en su unidad")
    chk(U.igual(72, 72 + U.a_pt(0.05, "cm"), U.a_pt(0.05, "cm")), "el borde de la tolerancia cuenta")
    # interlineado
    ic = U.interlineado_cumple
    chk(ic(U.interlineado_de_xml(360, "auto"), {"modo": "multiplo", "valor": 1.5}, 12)[0] == "igual", "auto 360 = ×1.5")
    chk(ic(U.interlineado_de_xml(360, "exact"), {"modo": "multiplo", "valor": 1.5}, 12)[0] == "equivalente", "exacto 18 pt = 1.5 con 12 pt")
    chk(ic(U.interlineado_de_xml(414, "exact"), {"modo": "multiplo", "valor": 1.5}, 12)[0] == "equivalente", "exacto 20.7 pt = 1.5 visual de Word")
    chk(ic(U.interlineado_de_xml(280, "exact"), {"modo": "multiplo", "valor": 1.5}, 12)[0] == "distinto", "exacto 14 pt no es 1.5")
    chk(ic(U.interlineado_de_xml(480, "auto"), {"modo": "multiplo", "valor": 2.0}, 11)[0] == "igual", "doble")
    chk(ic(U.interlineado_de_xml(360, "auto"), {"modo": "exacto", "pt": 18}, 12)[0] == "equivalente", "auto 1.5 = exacto 18 pt con 12 pt")
    chk(ic(U.interlineado_de_xml(360, "auto"), {"modo": "exacto", "pt": 24}, 12)[0] == "distinto", "auto 1.5 no es exacto 24 pt")
    chk(ic(U.interlineado_de_xml(360, "atLeast"), {"modo": "multiplo", "valor": 1.5}, 12)[0] == "indeterminado", "«al menos» no se afirma")
    return f


def prueba_herencia(tmp):
    f = []
    d = docx.Document()
    defaults(d, "Times New Roman", 12, 360, "auto", 0)
    margenes(d)
    estilo(d, "Cuerpo", "Normal", '<w:ind w:firstLine="720"/><w:jc w:val="both"/>')
    estilo(d, "Refs", "Cuerpo", '<w:ind w:left="720" w:hanging="720"/>')
    estilo(d, "Arial11", "Cuerpo", "", '<w:rFonts w:ascii="Arial" w:hAnsi="Arial"/><w:sz w:val="22"/><w:color w:val="1F3864"/>')
    p1 = d.add_paragraph(LARGO, style="Cuerpo")                                   # solo hereda
    p2 = d.add_paragraph(LARGO, style="Cuerpo")                                   # directo manda sobre el estilo
    p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p2.paragraph_format.line_spacing = 2.0
    p2.paragraph_format.space_before = Pt(6)
    p3 = d.add_paragraph(LARGO, style="Refs")                                     # basedOn: la francesa reemplaza la primera línea
    p4 = d.add_paragraph(LARGO, style="Arial11")                                  # fuente, tamaño y color del estilo
    p5 = d.add_paragraph()
    r = p5.add_run(LARGO)
    r.font.size = Pt(10)                                                          # run directo manda sobre el estilo y docDefaults
    ruta = guardar(d, tmp, "herencia.docx")
    ps = {p["i"]: p for p in medir.ficha_docx(ruta)["_parrafos"]}
    v = lambda i: ps[i]["v"]  # noqa: E731
    cond = [
        (v(0)["primera"] == 36 and v(0)["izq"] == 0 and v(0)["alineacion"] == "justificada", "p1: primera línea 36 pt y justificado heredados del estilo"),
        (v(0)["interlineado"] == {"regla": "auto", "multiplo": 1.5} and v(0)["fuente"] == "Times New Roman" and v(0)["tamano"] == 12, "p1: interlineado, fuente y tamaño de docDefaults"),
        (v(1)["alineacion"] == "centro" and v(1)["interlineado"]["multiplo"] == 2 and v(1)["antes"] == 6, "p2: lo directo manda sobre el estilo"),
        (v(1)["primera"] == 36, "p2: lo que no es directo se hereda (primera línea)"),
        (v(2)["izq"] == 36 and v(2)["primera"] == -36, "p3: francesa de un estilo basado en otro (reemplaza la primera línea de la base)"),
        (v(3)["fuente"] == "Arial" and v(3)["tamano"] == 11 and v(3)["color"] == "#1F3864", "p4: fuente, tamaño y color del estilo"),
        (v(4)["tamano"] == 10 and v(4)["fuente"] == "Times New Roman", "p5: el run directo cambia el tamaño; la fuente viene de docDefaults"),
    ]
    f += [m for ok, m in cond if not ok]
    # secciones: márgenes y página en las tres unidades
    s = medir.ficha_docx(ruta)["secciones"][0]
    if s["margenes"]["izquierdo"]["in"] != 1 or abs(s["margenes"]["izquierdo"]["cm"] - 2.54) > 0.001 or s["margenes"]["izquierdo"]["pt"] != 72:
        f.append(f"margen izquierdo en cm/pt/in: {s['margenes']['izquierdo']}")
    if s["pagina"]["ancho"]["in"] != 8.5 or s["pagina"]["alto"]["pt"] != 792:
        f.append(f"página: {s['pagina']}")
    # grupos: cuenta de valores y excepciones con índice y primeras palabras
    d2 = doc_cuerpo(5, 1.27)
    d2.paragraphs[3].paragraph_format.first_line_indent = Cm(0)
    fi = medir.ficha_docx(guardar(d2, tmp, "grupo.docx"))
    g = next(x for x in fi["grupos"] if x["grupo"] == "cuerpo")["atributos"]["primera"]
    if not (g["valores"][0]["n"] == 4 and g["valores"][1]["n"] == 1 and g["excepciones"][0]["i"] == 4 and g["excepciones"][0]["inicio"].startswith("Este párrafo")):
        f.append(f"grupo cuerpo, primera línea: {g}")
    return f


def prueba_equivalencias(tmp):
    f = []
    # márgenes: 0.5 in = 1.27 cm = 36 pt; la tolerancia por defecto es ±0.05 cm
    d = docx.Document()
    defaults(d)
    for s in d.sections:
        s.top_margin = s.bottom_margin = s.left_margin = s.right_margin = Inches(0.5)
    d.add_paragraph(LARGO)
    ruta = guardar(d, tmp, "m05.docx")
    for frase in ("márgenes 1.27 cm", "márgenes 36 pt", "márgenes 0.5 pulgadas", "margins 0.5 in", "márgenes de 12.7 mm"):
        r, _, _ = veredicto(ruta, frase)
        if any(x["estado"] != "cumple" for x in r):
            f.append(f"«{frase}» sobre márgenes de 0.5 in debía cumplir: {[x['estado'] for x in r]}")
    d = docx.Document()
    defaults(d)
    margenes(d, izq=2.54)
    d.add_paragraph(LARGO)
    ruta = guardar(d, tmp, "m254.docx")
    r, _, _ = veredicto(ruta, "márgenes 2.54 cm (1 pulgada)", "margen izquierdo 2.58 cm")      # 0.04 cm: dentro de la tolerancia
    if any(x["estado"] != "cumple" for x in r):
        f.append(f"2.58 cm sobre 2.54 cm está dentro de ±0.05 cm: {[(x['texto'], x['estado']) for x in r]}")
    r, _, _ = veredicto(ruta, "margen izquierdo 2.7 cm", "márgenes 3 cm izquierda")  # 0.16 y 0.46 cm: fuera
    if [x["estado"] for x in r] != ["no cumple", "no cumple"]:
        f.append(f"2.7 y 3 cm sobre 2.54 cm debían incumplir: {[x['estado'] for x in r]}")
    r = M.evaluar_regla(M.normalizar_regla({"que": "margen_izquierdo", "valor": 2.7, "unidad": "cm", "tolerancia": 0.2}), medir.ficha_docx(ruta))
    if r["estado"] != "cumple":
        f.append("la tolerancia de la regla (0.2 cm) debía aceptar 2.7 cm")
    # sangría: 0.5 in = 1.27 cm
    ruta = guardar(doc_cuerpo(5, 1.27), tmp, "s127.docx")
    r, _, _ = veredicto(ruta, "sangría de primera línea 0.5 in en el cuerpo", "sangría de primera línea 36 pt en el cuerpo", "sangría de primera línea 1.27 cm en el cuerpo")
    if any(x["estado"] != "cumple" for x in r):
        f.append(f"sangría equivalente: {[(x['texto'], x['estado']) for x in r]}")
    r, _, _ = veredicto(ruta, "sangría de primera línea 1.5 cm en el cuerpo", "sin sangría en el cuerpo")
    if [x["estado"] for x in r] != ["no cumple", "no cumple", "cumple"] or r[0]["n_mal"] != 5:
        f.append(f"sangría fuera de tolerancia: {[(x['texto'], x['estado'], x['n_mal']) for x in r]}")
    # interlineado: exacto 18 pt con letra de 12 pt es «1.5»; 14 pt no; auto ×1.5 cumple «exacto 18 pt» con aviso
    d = doc_cuerpo(4, 1.27)
    for p in d.paragraphs:
        p.paragraph_format.line_spacing = Pt(18)
        p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.EXACTLY
    ruta = guardar(d, tmp, "ex18.docx")
    r, _, _ = veredicto(ruta, "interlineado 1.5 en el cuerpo")
    if r[0]["estado"] != "cumple" or not any("equivalente" in a for a in r[0]["avisos"]):
        f.append(f"exacto 18 pt = 1.5 con 12 pt: {r[0]['estado']} {r[0]['avisos']}")
    r, _, _ = veredicto(ruta, "interlineado doble en el cuerpo")
    if r[0]["estado"] != "no cumple":
        f.append("exacto 18 pt no es doble")
    d = doc_cuerpo(4, 1.27)
    for p in d.paragraphs:
        p.paragraph_format.line_spacing = Pt(14)
        p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.EXACTLY
    r, _, _ = veredicto(guardar(d, tmp, "ex14.docx"), "interlineado 1.5 en el cuerpo")
    if r[0]["estado"] != "no cumple":
        f.append("exacto 14 pt no es 1.5 con 12 pt")
    r, _, _ = veredicto(guardar(doc_cuerpo(4, 1.27, linea=1.5), tmp, "a15.docx"), "interlineado exacto 18 pt en el cuerpo", "interlineado 1.5")
    if [x["estado"] for x in r] != ["cumple", "cumple"]:
        f.append(f"auto ×1.5 y exacto 18 pt con 12 pt: {[(x['texto'], x['estado']) for x in r]}")
    # tamaño y fuente: 12 pt = sz 24; 11.5 pt está fuera de ±0.25 pt; Times New Roman = «timesnewroman»
    r, _, _ = veredicto(ruta, "fuente Times New Roman 12 en el cuerpo")
    if any(x["estado"] != "cumple" for x in r):
        f.append(f"fuente y tamaño 12 pt: {[(x['texto'], x['estado']) for x in r]}")
    r, _, _ = veredicto(ruta, "tamaño 11.5 en el cuerpo", "tamaño 12.2 en el cuerpo", "fuente Arial en el cuerpo")
    if [x["estado"] for x in r] != ["no cumple", "cumple", "no cumple"]:
        f.append(f"tamaño 11.5 (fuera), 12.2 (dentro de ±0.25) y Arial (otra fuente): {[(x['texto'], x['estado']) for x in r]}")
    # excepciones legítimas: cita en bloque, párrafo centrado y nota no cuentan para la sangría de primera línea
    d = doc_cuerpo(4, 1.27)
    q = d.add_paragraph(LARGO + " (cita en bloque)")
    q.paragraph_format.left_indent = Inches(0.5)
    q.paragraph_format.first_line_indent = Cm(0)
    c = d.add_paragraph(LARGO + " (centrado)")
    c.alignment = WD_ALIGN_PARAGRAPH.CENTER
    n = d.add_paragraph("Nota. " + LARGO)
    ruta = guardar(d, tmp, "exentos.docx")
    r, _, _ = veredicto(ruta, "sangría de primera línea 1.27 cm en el cuerpo", "interlineado 1.5 en el cuerpo")
    if r[0]["estado"] != "cumple" or not r[0]["exentos"]:
        f.append(f"cita en bloque, centrado y nota no son incumplimiento: {r[0]['estado']} {r[0]['exentos']} {r[0]['detalle']}")
    return f


CASOS_PARSER = [
    # (frase, [(que, valor, unidad, alcance)…]) para lo que se entiende
    ("márgenes 3 cm izquierda", [("margen_izquierdo", 3.0, "cm", "documento")]),
    ("márgenes de 2.54 cm (1 pulgada)", [(f"margen_{l}", 2.54, "cm", "documento") for l in ("superior", "inferior", "izquierdo", "derecho")]),
    ("margen izquierdo 3 cm, derecho 2 cm, superior e inferior 2.5 cm", [("margen_izquierdo", 3.0, "cm", "documento"), ("margen_derecho", 2.0, "cm", "documento"),
                                                                       ("margen_superior", 2.5, "cm", "documento"), ("margen_inferior", 2.5, "cm", "documento")]),
    ("márgenes: 3 cm a la izquierda y 2.5 cm los demás", [("margen_izquierdo", 3.0, "cm", "documento"), ("margen_superior", 2.5, "cm", "documento"),
                                                          ("margen_inferior", 2.5, "cm", "documento"), ("margen_derecho", 2.5, "cm", "documento")]),
    ("margins 1 inch", [(f"margen_{l}", 1.0, "in", "documento") for l in ("superior", "inferior", "izquierdo", "derecho")]),
    ("left margin 3 cm", [("margen_izquierdo", 3.0, "cm", "documento")]),
    ("margen superior de 2.5 cm en la sección 2", [("margen_superior", 2.5, "cm", "seccion 2")]),
    ("sangría de primera línea 1.27 cm en el cuerpo", [("sangria_primera_linea", 1.27, "cm", "cuerpo")]),
    ("sangría francesa de 1.27 cm en las referencias", [("sangria_francesa", 1.27, "cm", "referencias")]),
    ("sin sangría en el resumen", [("sangria_primera_linea", 0.0, "cm", "resumen"), ("sangria_izquierda", 0.0, "cm", "resumen")]),
    ("first-line indent 0.5 in in the body", [("sangria_primera_linea", 0.5, "in", "cuerpo")]),
    ("hanging indent of 0.5 in in the references", [("sangria_francesa", 0.5, "in", "referencias")]),
    ("interlineado 1.5", [("interlineado", 1.5, "lineas", "documento")]),
    ("interlineado doble en el cuerpo", [("interlineado", 2.0, "lineas", "cuerpo")]),
    ("interlineado sencillo en las referencias", [("interlineado", 1.0, "lineas", "referencias")]),
    ("double spacing", [("interlineado", 2.0, "lineas", "documento")]),
    ("line spacing 1.5 in the body", [("interlineado", 1.5, "lineas", "cuerpo")]),
    ("interlineado exacto 18 pt", [("interlineado", 18.0, "pt", "documento")]),
    ("fuente Times New Roman 12", [("fuente", "Times New Roman", "", "documento"), ("tamano", 12.0, "pt", "documento")]),
    ("Arial 11 pt", [("fuente", "Arial", "", "documento"), ("tamano", 11.0, "pt", "documento")]),
    ("letra de 12 puntos", [("tamano", 12.0, "pt", "documento")]),
    ("font Calibri 11", [("fuente", "Calibri", "", "documento"), ("tamano", 11.0, "pt", "documento")]),
    ("tamaño de letra 14 en los títulos", [("tamano", 14.0, "pt", "titulos")]),
    ("espacio antes 0 pt en el cuerpo", [("espacio_antes", 0.0, "pt", "cuerpo")]),
    ("sin espacio entre párrafos en el cuerpo", [("espacio_antes", 0.0, "pt", "cuerpo"), ("espacio_despues", 0.0, "pt", "cuerpo")]),
    ("spacing after 6 pt in the body", [("espacio_despues", 6.0, "pt", "cuerpo")]),
    ("número de página arriba a la derecha", [("numero_pagina", "superior derecha", "", "documento")]),
    ("page number bottom center", [("numero_pagina", "inferior centro", "", "documento")]),
    ("número de página en el pie, centrado", [("numero_pagina", "inferior centro", "", "documento")]),
    ("sin número de página", [("numero_pagina", "ninguno", "", "documento")]),
    ("texto justificado en el cuerpo", [("alineacion", "justificada", "", "cuerpo")]),
    ("alineación izquierda en las referencias", [("alineacion", "izquierda", "", "referencias")]),
    ("fuente Times New Roman 12 pt e interlineado 1.5; márgenes 2.54 cm",
     [("fuente", "Times New Roman", "", "documento"), ("tamano", 12.0, "pt", "documento"), ("interlineado", 1.5, "lineas", "documento")]
     + [(f"margen_{l}", 2.54, "cm", "documento") for l in ("superior", "inferior", "izquierdo", "derecho")]),
]
CASOS_PREGUNTA = [  # lo que NO se adivina
    "márgenes 3",                              # falta la unidad
    "márgenes normales",                       # falta la medida
    "márgenes 2.5 o 3 cm",                     # dos medidas alternativas
    "sangría 1.27 cm",                         # ¿de qué tipo y dónde?
    "sangría 1.27 cm en el cuerpo",            # ¿primera línea, francesa o izquierda?
    "interlineado 1.5 o doble",                # contradictorio
    "interlineado 18 pt",                      # ¿exacto o al menos?
    "interlineado al menos 18 pt",             # no se puede afirmar
    "espacio entre párrafos 6 pt",             # ¿antes, después o ambos?
    "espacio antes 6",                         # falta unidad (y alcance)
    "número de página",                        # ¿dónde?
    "número de página arriba y abajo",         # contradictorio
    "justificado",                             # ¿en qué parte?
    "12 pt",                                   # ¿qué mide?
    "hola mundo",                              # no se entiende
    "fuente Arial o Times New Roman 12",       # dos fuentes
    "margin 2 cm left and 3 inch right",       # unidades mezcladas
    "text size 12 or 14",                      # dos tamaños
]


def prueba_indice(tmp):
    """Las entradas de un índice (estilo toc N, «TDC 3» localizado, table of figures, campo TOC) no son cuerpo."""
    f = []
    d = docx.Document()
    defaults(d, linea=360)
    margenes(d)
    estilo(d, "toc 3", "Normal", '<w:spacing w:line="240" w:lineRule="auto"/><w:ind w:left="480"/>')
    estilo(d, "TDC 3 ES", "Normal", '<w:spacing w:line="240" w:lineRule="auto"/>')
    d.styles["TDC 3 ES"].element.set(auditar.qn("w:styleId"), "TDC3")
    estilo(d, "Mi indice", "toc 3")                                     # estilo propio basado en toc 3
    estilo(d, "table of figures", "Normal", '<w:spacing w:line="240" w:lineRule="auto"/>')
    largo = LARGO + " 12"
    d.add_paragraph("4.3.10. " + largo, style="toc 3")
    d.add_paragraph("4.3.11. " + largo, style="TDC 3 ES")
    d.add_paragraph("4.3.12. " + largo, style="Mi indice")
    d.add_paragraph("TABLA I. " + largo, style="table of figures")
    # párrafo de Normal dentro de un campo TOC
    p = d.add_paragraph()
    p._p.append(parse_xml(f'<w:r {NS}><w:fldChar w:fldCharType="begin"/></w:r>'))
    p._p.append(parse_xml(f'<w:r {NS}><w:instrText> TOC \o "1-3" </w:instrText></w:r>'))
    p._p.append(parse_xml(f'<w:r {NS}><w:fldChar w:fldCharType="separate"/></w:r>'))
    p.add_run("5.1. " + largo)
    p.paragraph_format.line_spacing = 1.0
    p2 = d.add_paragraph("5.2. " + largo)
    p2.paragraph_format.line_spacing = 1.0
    p2._p.append(parse_xml(f'<w:r {NS}><w:fldChar w:fldCharType="end"/></w:r>'))
    for _ in range(4):
        d.add_paragraph(LARGO, style="Normal")                          # cuerpo a ×1.5 (docDefaults)
    ruta = guardar(d, tmp, "indice.docx")
    ficha = medir.ficha_docx(ruta)
    roles = [p["rol"] for p in ficha["_parrafos"]]
    if roles[:6] != ["indice"] * 6 or roles[6:].count("cuerpo") != 4 or roles[6:7] == ["indice"]:
        f.append(f"roles: {roles}")
    if not any(g["grupo"] == "indice" and g["n"] == 6 for g in ficha["grupos"]):
        f.append(f"grupo [indice]: {[(g['grupo'], g['n']) for g in ficha['grupos']]}")
    r, _, _ = veredicto(ruta, "interlineado 1.5 en el cuerpo", "interlineado 1.5")
    if [x["estado"] for x in r] != ["cumple", "cumple"]:
        f.append(f"el índice a ×1 no cuenta contra «interlineado 1.5»: {[(x['estado'], x['detalle']) for x in r]}")
    return f


def prueba_parser(tmp):
    f = []
    for frase, esp in CASOS_PARSER:
        r = M.parsear(frase, "usuario prueba")
        got = [(x["que"], x["valor"], x["unidad"], x["alcance"]) for y in r["reglas"] for x in M.expandir(y)]
        if r["preguntas"] or sorted(got, key=str) != sorted(esp, key=str):
            f.append(f"«{frase}»: esperado {esp}, salió {got} preguntas {[p['pregunta'][:50] for p in r['preguntas']]}")
        if any(x["origen"] != "usuario prueba" for x in r["reglas"]):
            f.append(f"«{frase}»: el origen no se conservó")
    for frase in CASOS_PREGUNTA:
        r = M.parsear(frase, "usuario prueba")
        if not r["preguntas"] or (r["reglas"] and frase not in ("margin 2 cm left and 3 inch right",)):
            f.append(f"«{frase}» debía volver como pregunta sin reglas: {[(x['que'], x['valor']) for x in r['reglas']]} {r['preguntas']}")
        if any(not p["pregunta"] for p in r["preguntas"]):
            f.append(f"«{frase}»: pregunta vacía")
    r = M.parsear("que se vea profesional")
    if r["reglas"] or not r["no_medibles"] or r["preguntas"]:
        f.append(f"«que se vea profesional» debía ser no medible: {r}")
    r = M.parsear("márgenes 3 cm y que se vea profesional")
    if len(r["reglas"]) != 4 or not r["no_medibles"]:
        f.append("la parte medible se conserva y la subjetiva sale aparte")
    r = M.parsear("márgenes 2.54 cm", None)
    if not r["reglas"][0]["origen"].startswith("usuario ") or "«márgenes 2.54 cm»" not in r["reglas"][0]["origen"]:
        f.append(f"origen por defecto: {r['reglas'][0]['origen']}")
    # entradas de `medidas:` validadas
    for malo in ({"que": "colores", "valor": 1}, {"que": "margenes", "valor": 3}, {"que": "margenes", "valor": "x", "unidad": "cm"},
                 {"que": "interlineado", "valor": 1.5, "alcance": "nunca"}, {"que": "margenes", "valor": 3, "unidad": "cm", "alcance": "cuerpo"},
                 {"que": "alineacion", "valor": "diagonal"}, {"valor": 1}):
        try:
            M.normalizar_medidas([malo])
            f.append(f"entrada inválida aceptada: {malo}")
        except M.ErrorMedidas:
            pass
    reglas_, _, _ = M.normalizar_medidas([{"que": "margenes", "valor": 3, "unidad": "cm", "tolerancia": 0.1, "alcance": "documento", "origen": "x"},
                                          {"frase": "interlineado 1.5 en el cuerpo", "origen": "usuario"}])
    if len(reglas_) != 5 or reglas_[0]["tolerancia"] != 0.1:
        f.append(f"normalizar_medidas: {reglas_}")
    try:
        M.normalizar_medidas([{"frase": "márgenes 3"}])
        f.append("una frase que no se entiende dentro de `medidas:` debe ser error")
    except M.ErrorMedidas:
        pass
    return f


def pdf_sintetico(ruta, paginas, numero=("inferior", "centro"), sangria_pt=36.0, cubierta=False, izq=72.0, base=84.0, paso=20.7):
    """PDF Letter con `paginas` páginas de 4 párrafos de 4 líneas (primera línea sangrada) y un número de página."""
    doc = fitz.open()
    for n in range(1, paginas + 1):
        pg = doc.new_page(width=612, height=792)
        if cubierta and n == 1:
            pg.insert_text((200, 300), "PORTADA DEL DOCUMENTO", fontname="tiro", fontsize=14)
            continue
        y = base
        for _p in range(4):
            for k in range(4):
                x = izq + (sangria_pt if k == 0 else 0)
                texto = "palabra " * 10 if k < 3 else "fin del párrafo"
                pg.insert_text((x, y), texto.strip(), fontname="tiro", fontsize=12)
                y += paso
        if numero:
            zona, lado = numero
            yy = 40.0 if zona == "superior" else 760.0
            xx = {"izquierda": 72.0, "centro": 303.0, "derecha": 530.0}[lado]
            pg.insert_text((xx, yy), str(n), fontname="tiro", fontsize=11)
    doc.save(str(ruta))
    doc.close()
    return str(ruta)


def prueba_pdf(tmp):
    if not HAY_FITZ:
        print("SALTADA: pdf (falta PyMuPDF)")
        return []
    f = []
    p1 = pdf_sintetico(pathlib.Path(tmp) / "pie_centro.pdf", 3, ("inferior", "centro"))
    m = medir.medir_pdf(p1)
    g = m["margenes"]
    if abs(g["izquierda"]["mediana"]["pt"] - 72) > 1.5:
        f.append(f"margen izquierdo del PDF: {g['izquierda']}")
    if not 70 <= g["superior"]["p10"]["pt"] <= 76:
        f.append(f"margen superior del PDF: {g['superior']}")
    der = g["derecha"]["p90"]["pt"]
    if not 100 < der < 400:
        f.append(f"margen derecho del PDF (texto no justificado): {der}")
    n = m["numero_pagina"]
    if n["predominante"] != {"zona": "inferior", "lado": "centro", "paginas": 3} or n["paginas_con_numero"] != 3:
        f.append(f"número de página inferior centro: {n['predominante']}")
    s = m["sangria_primera_linea"]
    if s["moda_cm"] != 1.27 or s["bloques"] < 6:
        f.append(f"sangría visible del PDF: {s}")
    pl = m["paso_linea"]
    if not pl or abs(pl["mediana_pt"] - 20.7) > 0.3 or abs(pl["razon"] - 1.725) > 0.03:
        f.append(f"paso de línea: {pl}")
    if not m["fuentes"] or m["fuentes"][0]["pt"] != 12.0 or "ti" not in m["fuentes"][0]["norm"].lower() and "times" not in m["fuentes"][0]["norm"].lower():
        f.append(f"fuentes del PDF: {m['fuentes'][:2]}")
    # posiciones del número: cada esquina
    for zona, lado in (("superior", "derecha"), ("superior", "izquierda"), ("inferior", "derecha"), ("superior", "centro")):
        mm = medir.medir_pdf(pdf_sintetico(pathlib.Path(tmp) / f"{zona}_{lado}.pdf", 3, (zona, lado)))
        if (mm["numero_pagina"]["predominante"] or {}).get("zona") != zona or mm["numero_pagina"]["predominante"]["lado"] != lado:
            f.append(f"número en {zona} {lado}: {mm['numero_pagina']['predominante']}")
    # por página: una portada sin número
    mc = medir.medir_pdf(pdf_sintetico(pathlib.Path(tmp) / "portada.pdf", 3, ("superior", "derecha"), cubierta=True))
    if mc["numero_pagina"]["paginas_sin_numero"] != [1] or mc["numero_pagina"]["paginas_con_numero"] != 2:
        f.append(f"portada sin número: {mc['numero_pagina']}")
    if [x["texto"] for x in mc["numero_pagina"]["por_pagina"]] != ["2", "3"]:
        f.append(f"números por página: {mc['numero_pagina']['por_pagina']}")
    # sin sangría y con margen izquierdo de 3 cm
    m3 = medir.medir_pdf(pdf_sintetico(pathlib.Path(tmp) / "izq3.pdf", 3, None, sangria_pt=0.0, izq=85.04))
    if abs(m3["margenes"]["izquierda"]["mediana"]["cm"] - 3.0) > 0.05 or m3["sangria_primera_linea"]["moda_cm"] not in (0.0, None):
        f.append(f"PDF con 3 cm y sin sangría: {m3['margenes']['izquierda']} {m3['sangria_primera_linea']}")
    if m3["numero_pagina"]["predominante"] is not None:
        f.append("un PDF sin número no debe inventar uno")
    return f


def docx_con_numero(tmp, nombre, alinear=WD_ALIGN_PARAGRAPH.RIGHT, en_pie=False, tabs=0, texto_antes=""):
    d = doc_cuerpo(6, 1.27)
    s = d.sections[0]
    parte = s.footer if en_pie else s.header
    parte.is_linked_to_previous = False
    campo_pagina(parte.paragraphs[0], alinear, texto_antes, tabs)
    return guardar(d, tmp, nombre)


def prueba_discrepancia(tmp):
    f = []
    ruta = docx_con_numero(tmp, "num_der.docx")
    ficha = medir.ficha_docx(ruta)
    if ficha["secciones"][0]["numero_pagina"]["donde"] != "encabezado derecha":
        f.append(f"posición del número en el .docx: {ficha['secciones'][0]['numero_pagina']['donde']}")
    if HAY_FITZ:
        # el PDF muestra el número abajo al centro: discrepancia = AVISO; la regla se juzga con el .docx
        pdf = pdf_sintetico(pathlib.Path(tmp) / "pie.pdf", 3, ("inferior", "centro"))
        pdfm = medir.medir_pdf(pdf)
        av = medir.discrepancias(ficha, pdfm)
        if not any(a.startswith("número de página") for a in av):
            f.append(f"docx con número arriba a la derecha y PDF abajo al centro: sin aviso ({av})")
        r = M.evaluar_regla(reglas("número de página arriba a la derecha")[0], ficha, pdfm)
        if r["estado"] != "cumple" or not any("discrepancia" in a for a in r["avisos"]):
            f.append(f"la discrepancia docx/PDF es aviso y no violación: {r['estado']} {r['avisos']}")
        # margen: el PDF con 3 cm de margen izquierdo contra un docx de 2.54 cm
        pdf3 = pdf_sintetico(pathlib.Path(tmp) / "izq3.pdf", 3, ("superior", "derecha"), izq=85.04)
        av = medir.discrepancias(ficha, medir.medir_pdf(pdf3))
        if not any(a.startswith("margen izquierdo") for a in av):
            f.append(f"margen izquierdo docx 2.54 cm frente a PDF 3 cm: {av}")
        # coinciden: sin avisos de margen ni de número
        pdf_ok = pdf_sintetico(pathlib.Path(tmp) / "ok.pdf", 3, ("superior", "derecha"))
        av = medir.discrepancias(ficha, medir.medir_pdf(pdf_ok))
        if any(a.startswith(("margen", "número", "tamaño de página")) for a in av):
            f.append(f"docx y PDF coinciden y sale aviso: {av}")
    else:
        print("SALTADA: discrepancia con PDF sintético (falta PyMuPDF)")
    if HAY_FITZ and HAY_LO:
        # render real: Word frente a LibreOffice no debe dar avisos de margen ni de número de página
        d = doc_cuerpo(40, 1.27, linea=1.5)
        d.sections[0].header.is_linked_to_previous = False
        campo_pagina(d.sections[0].header.paragraphs[0], WD_ALIGN_PARAGRAPH.RIGHT)
        real = guardar(d, tmp, "render.docx")
        pdf = libreoffice.a_pdf(real, pathlib.Path(tmp) / "lo")
        fi = medir.ficha_docx(real)
        pm = medir.medir_pdf(pdf)
        av = medir.discrepancias(fi, pm)
        if any(a.startswith(("margen", "número", "sangría", "tamaño de página")) for a in av):
            f.append(f"render de LibreOffice con avisos que no son reales: {av}")
        if (pm["numero_pagina"]["predominante"] or {}).get("lado") != "derecha":
            f.append(f"LibreOffice: número del encabezado derecho: {pm['numero_pagina']['predominante']}")
        if abs(pm["sangria_primera_linea"]["moda_cm"] - 1.27) > 0.05:
            f.append(f"sangría visible en el PDF de LibreOffice: {pm['sangria_primera_linea']}")
        if pm["paso_linea"] and not 1.5 <= pm["paso_linea"]["razon"] <= 2.0:
            f.append(f"paso de línea del PDF de LibreOffice con ×1.5: {pm['paso_linea']}")
    elif HAY_FITZ:
        print("SALTADA: discrepancia con render real (falta LibreOffice)")
    return f


def prueba_no_medible(tmp):
    f = []
    # «al menos 18 pt»: la línea puede crecer, no se afirma
    d = doc_cuerpo(4, 1.27)
    for p in d.paragraphs:
        p.paragraph_format.line_spacing = Pt(18)
        p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.AT_LEAST
    r, _, _ = veredicto(guardar(d, tmp, "atleast.docx"), "interlineado 1.5 en el cuerpo")
    if r[0]["estado"] != "no medible":
        f.append(f"interlineado «al menos» debía ser no medible: {r[0]['estado']}")
    # alcance que no existe en el documento
    r, _, _ = veredicto(guardar(doc_cuerpo(3), tmp, "sin_resumen.docx"), "sin sangría en el resumen", "alineación izquierda en las referencias")
    if any(x["estado"] != "no medible" for x in r) or "no hay párrafos" not in r[0]["detalle"][0]:
        f.append(f"alcance inexistente debía ser no medible: {[(x['texto'], x['estado']) for x in r]}")
    # número con tabuladores: el lado solo lo da el PDF
    ruta = docx_con_numero(tmp, "tabs.docx", alinear=None, tabs=2, texto_antes="Título corrido")
    r, _, _ = veredicto(ruta, "número de página arriba a la derecha")
    if r[0]["estado"] != "no medible" or "tabuladores" not in " ".join(r[0]["detalle"]):
        f.append(f"número con tabuladores sin PDF: {r[0]['estado']} {r[0]['detalle']}")
    if HAY_FITZ:
        pdf = pdf_sintetico(pathlib.Path(tmp) / "tabs.pdf", 3, ("superior", "derecha"))
        r, _, _ = veredicto(ruta, "número de página arriba a la derecha", pdf=pdf)
        if r[0]["estado"] != "cumple" or "PDF" not in " ".join(r[0]["avisos"] + [r[0]["real"]]):
            f.append(f"número con tabuladores y PDF debe juzgarse con el PDF: {r[0]['estado']} {r[0]['real']}")
    # la ficha lista lo no medible y nunca vacío
    ficha = medir.ficha_docx(ruta)
    if not ficha["no_medible"] or not any("tabuladores" in x["motivo"] or "lado" in x["que"] for x in ficha["no_medible"]):
        f.append(f"la ficha debe listar lo no medible: {ficha['no_medible']}")
    # la frase subjetiva sale por la CLI como «no medible»
    code, out = correr("medir", ruta, "--regla", "que se vea profesional", "--resumen")
    if code != 0 or "no medible:" not in out or "profesional" not in out:
        f.append(f"CLI con frase subjetiva: {code} {out[-200:]}")
    # un .docx sin pgMar completo: se mide con el valor por defecto y se avisa, no se calla
    d = docx.Document()
    d.add_paragraph(LARGO)
    sect = d.sections[0]._sectPr
    mg = sect.find(auditar.qn("w:pgMar"))
    if mg is not None:
        sect.remove(mg)
    r, ficha, _ = veredicto(guardar(d, tmp, "sinpgmar.docx"), "márgenes 2.54 cm")
    if not r[0]["avisos"] or not any("pgMar" in a for x in r for a in x["avisos"]):
        f.append(f"sin pgMar debe avisar: {[x['avisos'] for x in r]}")
    return f


def yaml_equipo(carpeta, texto):
    (pathlib.Path(carpeta) / ".editorial.yaml").write_text(texto, encoding="utf-8")


def prueba_auditar(tmp):
    f = []
    car = pathlib.Path(tmp) / "aud"
    car.mkdir()
    yaml_equipo(car, 'perfil: apa7\nmedidas:\n'
                     '  - {que: margenes, valor: 3, unidad: cm, alcance: documento, origen: "usuario 2026-11-27: «márgenes de 3 cm»"}\n'
                     '  - {frase: "sangría de primera línea 1.27 cm en el cuerpo", origen: "usuario 2026-11-27: «sangría de 1.27 cm»"}\n'
                     '  - {frase: "que se vea profesional", origen: "usuario 2026-11-27"}\n')
    d = doc_cuerpo(5, 1.27)  # márgenes de 2.54 cm: incumple los 3 cm pedidos
    ruta = guardar(d, car, "doc.docx")
    r = auditar.auditar(ruta, "apa7")
    h = [x for x in r["hallazgos"] if x["id"] == "INS-016"]
    if len(h) != 4 or any(x["severidad"] != "mayor" for x in h):
        f.append(f"INS-016 con márgenes de 2.54 cm y 3 cm pedidos: {[(x['id'], x['evidencia']) for x in r['hallazgos']]}")
    if h and "usuario 2026-11-27: «márgenes de 3 cm»" not in h[0]["correccion"]:
        f.append(f"INS-016 debe llevar el origen del usuario: {h[0]['correccion']}")
    if not any(a.startswith("no medible:") and "profesional" in a for a in r["avisos"]):
        f.append(f"la frase subjetiva debe salir como aviso «no medible»: {r['avisos']}")
    # con 3 cm de margen: sin INS-016 de márgenes
    d = doc_cuerpo(5, 1.27)
    margenes(d, 3, 3, 3, 3)
    r = auditar.auditar(guardar(d, car, "ok.docx"), "apa7")
    if not any(x["id"] == "EXC-APA-001" for x in r["excepciones"]):
        f.append("APA-001 (1 in) debe pasar a excepción cuando el usuario pide márgenes de 3 cm")
    if [x for x in r["hallazgos"] if x["id"] in ("INS-016", "APA-001")]:
        f.append(f"márgenes de 3 cm cumplen lo pedido: {[(x['id'], x['evidencia']) for x in r['hallazgos'] if x['id'] in ('INS-016', 'APA-001')]}")
    # sangría incumplida: un párrafo sin sangría
    d = doc_cuerpo(5, 1.27)
    margenes(d, 3, 3, 3, 3)
    d.paragraphs[2].paragraph_format.first_line_indent = Cm(0)
    r = auditar.auditar(guardar(d, car, "sang.docx"), "apa7")
    h = [x for x in r["hallazgos"] if x["id"] == "INS-016"]
    if len(h) != 1 or "1 de 5" not in h[0]["evidencia"] or "párrafo 3" not in h[0]["ubicacion"]:
        f.append(f"INS-016 de sangría: {[(x['ubicacion'], x['evidencia']) for x in h]}")
    # un .editorial.yaml sin `medidas:` no cambia nada
    yaml_equipo(car, "perfil: apa7\n")
    r = auditar.auditar(ruta, "apa7")
    if any(x["id"] == "INS-016" for x in r["hallazgos"]):
        f.append("sin `medidas:` no hay INS-016")
    # medidas inválidas: error de uso (código 2)
    yaml_equipo(car, "perfil: apa7\nmedidas:\n  - {que: colores, valor: 1}\n")
    try:
        with contextlib.redirect_stderr(io.StringIO()):
            auditar.auditar(ruta, "apa7")
        f.append("`medidas:` inválido debe salir con código 2")
    except SystemExit as e:
        if e.code != 2:
            f.append(f"`medidas:` inválido: código {e.code}")
    code, out = correr("auditar", ruta, "--perfil", "apa7")
    if code != 2 or "medidas[1]" not in out:
        f.append(f"CLI con `medidas:` inválido: {code} {out[-160:]}")
    yaml_equipo(car, "perfil: apa7\nmedidas:\n  - {que: interlineado, valor: 1.5, alcance: cuerpo, origen: usuario}\n")
    r = auditar.auditar(ruta, "apa7")
    if any(x["id"] in ("INS-016", "APA-004") for x in r["hallazgos"]) or not any(x["id"] == "EXC-APA-004" for x in r["excepciones"]):
        f.append("interlineado 1.5 pedido y cumplido: sin INS-016 y APA-004 (doble) como excepción")
    yaml_equipo(car, "perfil: apa7\nmedidas:\n  - {que: interlineado, valor: 2, alcance: cuerpo, origen: usuario}\n")
    r = auditar.auditar(ruta, "apa7")
    if not any(x["id"] == "INS-016" for x in r["hallazgos"]):
        f.append("interlineado doble pedido y documento a 1.5: INS-016")
    return f


def prueba_perfilar(tmp):
    f = []
    import yaml
    import run_perfilar as RP
    base = pathlib.Path(tmp) / "perf"
    base.mkdir()
    gd = base / "guia.docx"
    RP.guia_docx(gd, RP.GUIA_ES)
    code, out = correr("perfilar", gd, "--out", base / ".editorial.yaml", "--estructura-id", "t")
    if code != 0:
        return [f"perfilar salió {code}: {out[-200:]}"]
    cfg = yaml.safe_load((base / ".editorial.yaml").read_text(encoding="utf-8"))
    med = cfg.get("medidas") or []
    mg = next((m for m in med if m["que"] == "margenes"), None)
    if not mg or mg["valor"] != 3.0 or mg["unidad"] != "cm" or not mg["origen"].startswith("guía p."):
        f.append(f"perfilar debe emitir `medidas:` con los márgenes y su origen: {med}")
    sg = next((m for m in med if m["que"] == "sangria_primera_linea"), None)
    if not sg or sg["valor"] != 1.27:
        f.append(f"perfilar: sangría de primera línea en `medidas:`: {med}")
    try:
        reglas_, _, _ = M.normalizar_medidas(med)
        if len(reglas_) != 5:
            f.append(f"el plugin debe aceptar lo que emite perfilar: {len(reglas_)} reglas")
    except M.ErrorMedidas as e:
        f.append(f"el plugin rechaza lo que emite perfilar: {e}")
    return f


def prueba_cli(tmp):
    f = []
    ruta = guardar(doc_cuerpo(5, 1.27), tmp, "cli.docx")
    jr = pathlib.Path(tmp) / "ficha.json"
    code, out = correr("medir", ruta, "--json", jr)
    if code != 0 or "SECCIONES" not in out or "[cuerpo]" not in out or "cm (" not in out:
        f.append(f"medir sin reglas: {code} {out[-200:]}")
    j = json.loads(jr.read_text(encoding="utf-8"))
    if not {"secciones", "grupos", "estilos", "no_medible"} <= set(j) or "_parrafos" in j or j["secciones"][0]["margenes"]["izquierdo"]["cm"] != 2.54:
        f.append(f"JSON de la ficha: {sorted(j)}")
    code, out = correr("medir", ruta, "--regla", "márgenes 2.54 cm", "--regla", "sangría de primera línea 1.27 cm en el cuerpo", "--resumen")
    if code != 0 or out.count("CUMPLE") < 5 or "NO CUMPLE" in out:
        f.append(f"medir --regla que cumple: {code} {out[-300:]}")
    code, out = correr("medir", ruta, "--regla", "márgenes 3 cm izquierda", "--resumen", "--json", jr)
    if code != 1 or "NO CUMPLE" not in out or "origen: usuario" not in out:
        f.append(f"medir --regla que no cumple debe salir con 1: {code} {out[-300:]}")
    j = json.loads(jr.read_text(encoding="utf-8"))
    if j["reglas"]["resultados"][0]["estado"] != "no cumple":
        f.append("el JSON lleva el veredicto de las reglas")
    code, out = correr("medir", ruta, "--regla", "márgenes 3", "--resumen")
    if code != 0 or "PREGUNTA:" not in out or "NO CUMPLE" in out:
        f.append(f"una frase ambigua sale como pregunta, no como veredicto: {code} {out[-200:]}")
    code, out = correr("medir", pathlib.Path(tmp) / "no-existe.docx")
    if code != 2 or "no existe" not in out:
        f.append(f"archivo inexistente debe salir con 2: {code}")
    code, out = correr("medir", pathlib.Path(tmp) / "cli.docx.txt")
    if code != 2:
        f.append(f"extensión no soportada debe salir con 2: {code}")
    car = pathlib.Path(tmp) / "clicfg"
    car.mkdir()
    shutil.copy(ruta, car / "d.docx")
    yaml_equipo(car, "medidas:\n  - {que: margenes, valor: 3, unidad: cm, origen: usuario}\n")
    code, out = correr("medir", car / "d.docx", "--resumen")
    if code != 1 or "NO CUMPLE" not in out:
        f.append(f"medir evalúa solo el bloque `medidas:` del .editorial.yaml: {code} {out[-200:]}")
    code, out = correr("medir", car / "d.docx", "--contra", "perfil", "--resumen")
    if code not in (0, 1):
        f.append(f"--contra perfil: {code} {out[-200:]}")
    if HAY_FITZ:
        pdf = pdf_sintetico(pathlib.Path(tmp) / "solo.pdf", 3, ("superior", "derecha"))
        code, out = correr("medir", pdf)
        if code != 0 or "== PDF ==" not in out:
            f.append(f"medir de un PDF: {code} {out[-200:]}")
        code, out = correr("medir", ruta, "--pdf", pdf, "--resumen")
        if code != 0:
            f.append(f"medir --pdf: {code}")
    code, out = correr("--help")
    if "medir" not in out:
        f.append("editorial.py --help no lista medir")
    code, out = correr("medir", "--help")
    if "--regla" not in out or "--pdf" not in out:
        f.append("medir --help no lista --regla ni --pdf")
    return f


def git(*args, cwd):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")


def prueba_exportar(tmp):
    if not (ROOT / "scripts" / "exportar_publico.py").exists():
        print("SALTADA: exportar (el script no se distribuye en el repo público)")
        return []
    import exportar_publico as E
    f = []
    base = pathlib.Path(tmp) / "exp"
    base.mkdir()
    env = ["-c", "user.name=t", "-c", "user.email=t@e"]
    # «origen»: repo con dos commits
    semilla = base / "semilla"
    semilla.mkdir()
    git("init", "-q", "-b", "main", cwd=semilla)
    for i, t in enumerate(("uno", "dos"), 1):
        (semilla / "a.txt").write_text(t, encoding="utf-8")
        git("add", "-A", cwd=semilla)
        subprocess.run(["git", *env, "commit", "-q", "-m", f"c{i}"], cwd=semilla, capture_output=True)
    remoto = base / "remoto.git"
    git("clone", "-q", "--bare", str(semilla), str(remoto), cwd=base)
    # destino con origin (clon) marcado como exportado
    dest = base / "dest"
    git("clone", "-q", str(remoto), str(dest), cwd=base)
    (dest / E.MARCADOR).write_text("x", encoding="utf-8")
    git("config", "user.name", "t", cwd=dest)
    git("config", "user.email", "t@e", cwd=dest)
    padre_antes = git("rev-parse", "origin/main", cwd=dest).stdout.strip()
    if not E.tiene_origin(dest):
        f.append("tiene_origin debe ver el remoto")
    E.preparar_destino(dest, True)
    if not (dest / ".git").exists() or (dest / "a.txt").exists():
        f.append("con origin, preparar_destino conserva .git y vacía el árbol")
    (dest / "a.txt").write_text("nuevo contenido exportado", encoding="utf-8")
    (dest / "b.txt").write_text("otro", encoding="utf-8")
    msg = E.crear_commit_sobre_origen(dest, "editorial-academica 9.9.9")
    padres = git("log", "-1", "--format=%P", cwd=dest).stdout.split()
    n = git("rev-list", "--count", "HEAD", cwd=dest).stdout.strip()
    if padres != [padre_antes] or n != "3" or "sin push" not in msg:
        f.append(f"el commit nuevo debe tener por padre origin/main: padres {padres} (esperado {padre_antes}), commits {n}: {msg}")
    if git("status", "--porcelain", cwd=dest).stdout.strip():
        f.append(f"árbol sucio tras el commit: {git('status', '--porcelain', cwd=dest).stdout}")
    if (dest / "a.txt").read_text(encoding="utf-8") != "nuevo contenido exportado":
        f.append("el árbol de trabajo debe ser el exportado")
    if git("log", "-1", "--format=%s", cwd=dest).stdout.strip() != "editorial-academica 9.9.9":
        f.append("mensaje del commit")
    # avance rápido: el push posterior no necesita force
    ff = git("merge-base", "--is-ancestor", "origin/main", "HEAD", cwd=dest)
    if ff.returncode != 0:
        f.append("origin/main debe ser ancestro del commit nuevo (push sin force)")
    # repetir la exportación: el nuevo commit se apila sobre origin/main (lo único publicado), no sobre el commit local anterior
    E.crear_commit_sobre_origen(dest, "editorial-academica 9.9.9 (repetido)")
    padres2 = git("log", "-1", "--format=%P", cwd=dest).stdout.split()
    if padres2 != [padre_antes]:
        f.append(f"el padre siempre es origin/main, nunca el commit anterior local: {padres2}")
    # sin remoto: commit único (comportamiento de siempre)
    solo = base / "solo"
    solo.mkdir()
    (solo / E.MARCADOR).write_text("x", encoding="utf-8")
    (solo / "z.txt").write_text("z", encoding="utf-8")
    if E.tiene_origin(solo):
        f.append("sin .git no hay origin")
    # fetch que falla: error de uso, sin commit
    git("remote", "set-url", "origin", str(base / "no-existe.git"), cwd=dest)
    (dest / "c.txt").write_text("c", encoding="utf-8")
    try:
        with contextlib.redirect_stderr(io.StringIO()):
            E.crear_commit_sobre_origen(dest, "no debe crearse")
        f.append("un fetch que falla debe salir con error")
    except SystemExit as e:
        if e.code != 2:
            f.append(f"fetch fallido: código {e.code}")
    return f


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    tmp = tempfile.mkdtemp(prefix="v09")
    pruebas = [("unidades", prueba_unidades), ("herencia", prueba_herencia), ("equivalencias", prueba_equivalencias), ("indice", prueba_indice), ("parser", prueba_parser),
               ("pdf", prueba_pdf), ("discrepancia", prueba_discrepancia), ("no-medible", prueba_no_medible), ("auditar", prueba_auditar),
               ("perfilar", prueba_perfilar), ("cli", prueba_cli), ("exportar", prueba_exportar)]
    total = 0
    try:
        for nombre, fn in pruebas:
            sub = pathlib.Path(tmp) / nombre
            sub.mkdir()
            try:
                fallas = fn(str(sub))
            except Exception as ex:  # noqa: BLE001
                import traceback
                fallas = [f"EXCEPCIÓN {type(ex).__name__}: {ex}\n{traceback.format_exc()[-700:]}"]
            for m in fallas:
                print("FALLA", nombre, "-", m)
            total += len(fallas)
            print(("OK   " if not fallas else "FALLA"), nombre)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"== v0.9: {len(pruebas)} grupos, {total} fallas")
    sys.exit(1 if total else 0)


if __name__ == "__main__":
    main()
