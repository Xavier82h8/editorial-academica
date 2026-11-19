#!/usr/bin/env python3
"""Genera el «borrador de estudiante» sintético que sustituye al boceto real (privado) en tests/run_real.py.

Todo es inventado: tema (monitoreo acústico de colmenas), autores, institución, fuentes y cifras. Imita los vicios
mecánicos típicos de un borrador de estudiante: fuentes decorativas mezcladas, interlineado 1.25, espacio posterior,
párrafos vacíos y justificados sin sangría, número de página solo en el pie, encabezados numerados a la izquierda,
citas fuera de orden alfabético, lista de referencias desordenada con siglas entre corchetes y revista sin cursiva,
tabla con todos los bordes y sin «Tabla N» ni título encima.

Uso: python -I tests/reales/crear_boceto_sintetico.py RUTA.docx   (run_real.py lo genera en un temporal)
La verdad esperada está en tests/reales/boceto_sintetico.json.
"""
import pathlib
import sys

import docx
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt

CUERPO, TITULOS, OTRA, MONO = "Lexend", "Montserrat", "Oswald", "Cardo"
LINEA = 1.25          # APA-004: debería ser doble
DESPUES = Pt(10)      # APA-005: debería ser 0


def fuente(run, nombre, tam, negrita=None, cursiva=None):
    run.font.name = nombre
    rpr = run._element.get_or_add_rPr()
    rpr.rFonts.set(qn("w:eastAsia"), nombre)
    run.font.size = Pt(tam)
    if negrita is not None:
        run.bold = negrita
    if cursiva is not None:
        run.italic = cursiva


def campo(par, instr, nombre, tam):
    for tipo, texto in (("begin", None), (None, instr), ("separate", None), (None, "1"), ("end", None)):
        r = par.add_run()
        fuente(r, nombre, tam)
        if tipo:
            c = OxmlElement("w:fldChar")
            c.set(qn("w:fldCharType"), tipo)
            r._r.append(c)
        elif texto == instr:
            it = OxmlElement("w:instrText")
            it.set(qn("xml:space"), "preserve")
            it.text = f" {instr} "
            r._r.append(it)
        else:
            r.text = texto


def parrafo(d, texto, nombre=CUERPO, tam=11, justificado=True, vacios_antes=0):
    for _ in range(vacios_antes):
        d.add_paragraph("")
    p = d.add_paragraph()
    pf = p.paragraph_format
    pf.line_spacing = LINEA
    pf.space_after = DESPUES
    if justificado:
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    fuente(p.add_run(texto), nombre, tam)
    return p


def encabezado(d, texto, nivel=1):
    p = d.add_heading(level=nivel)
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.space_before = Pt(24)
    p.paragraph_format.space_after = Pt(12)
    fuente(p.add_run(texto), TITULOS, 15 if nivel == 1 else 12.5, negrita=True)
    return p


def bordes(tabla):
    tbl_pr = tabla._tbl.tblPr
    b = OxmlElement("w:tblBorders")
    for lado in ("top", "left", "bottom", "right", "insideH", "insideV"):
        e = OxmlElement(f"w:{lado}")
        e.set(qn("w:val"), "single")
        e.set(qn("w:sz"), "4")
        e.set(qn("w:color"), "000000")
        b.append(e)
    tbl_pr.append(b)


def referencia(d, partes):
    """partes: [(texto, cursiva)]; sangría francesa de 0,5 in, 1.15 y 9 pt después (vicio: ni doble ni sin espacio)."""
    p = d.add_paragraph()
    pf = p.paragraph_format
    pf.left_indent = Inches(0.5)
    pf.first_line_indent = Inches(-0.5)
    pf.line_spacing = 1.15
    pf.space_after = Pt(9)
    for texto, cursiva in partes:
        fuente(p.add_run(texto), CUERPO, 10.5, cursiva=cursiva)
    return p


def crear(destino):
    d = docx.Document()
    for nombre in ("Normal", "Heading 1", "Heading 2"):
        d.styles[nombre].font.name = CUERPO
    s = d.sections[0]
    for m in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
        setattr(s, m, Inches(1))
    s.header.paragraphs[0].text = ""
    fuente(s.header.paragraphs[0].add_run("Borrador ficticio · Colmenas sonoras"), CUERPO, 9)
    pie = s.footer.paragraphs[0]
    pie.alignment = WD_ALIGN_PARAGRAPH.CENTER
    fuente(pie.add_run("Página "), CUERPO, 9)
    campo(pie, "PAGE", CUERPO, 9)
    fuente(pie.add_run(" de "), CUERPO, 9)
    campo(pie, "NUMPAGES", CUERPO, 9)

    # portada
    p = d.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    fuente(p.add_run("Actividad: Proyecto de investigación (Unidad 2)"), OTRA, 14)
    for linea in ("Quiroga Lemus Ana", "Mateo Brisa Ortega", "INSTITUTO TECNOLÓGICO FICTICIO DEL VALLE",
                  "MATERIA: Taller de Investigación", "Profesora: Dra. Elena Vidal Rojas · 03/11/2026"):
        q = d.add_paragraph()
        q.alignment = WD_ALIGN_PARAGRAPH.CENTER
        fuente(q.add_run(linea), CUERPO, 11)
    d.add_page_break()

    encabezado(d, "1. Introducción")
    parrafo(d, "El monitoreo acústico de colmenas permite estimar la salud de una colonia sin abrirla. Este proyecto "
               "propone un sensor de bajo costo y un modelo de clasificación para detectar la pérdida de reina.")
    parrafo(d, "La literatura reporta que Marlow et al., 2019, propusieron el análisis espectral de zumbidos y que "
               "Sato et al., 2021, lo extendieron a redes ligeras (Sato et al., 2021; Marlow et al., 2019).",
            vacios_antes=3)
    parrafo(d, "La Figura 1 resume el montaje del sensor; la tabla de grabaciones se incluye en el método sin remitir a ella.", vacios_antes=2)

    encabezado(d, "2. Método")
    encabezado(d, "2.1 Diseño del sensor", nivel=2)
    parrafo(d, "Se usó un micrófono MEMS con un microcontrolador de 32 bits y una tarjeta de memoria. Cada colmena "
               "se grabó durante 20 semanas en ventanas de diez minutos (Okonkwo, 2020).")
    parrafo(d, "El Centro Nacional de Apicultura [CNA] (2023) recomienda calibrar el micrófono cada mes.")
    t = d.add_table(rows=3, cols=3)
    bordes(t)
    for i, fila in enumerate((("Colmena", "Estado", "Grabaciones"), ("A1", "con reina", "120"), ("A2", "sin reina", "118"))):
        for j, v in enumerate(fila):
            t.cell(i, j).text = v
    d.add_paragraph("")
    p = d.add_paragraph()
    fuente(p.add_run("Figura 1. Montaje del sensor dentro de la colmena (elaboración propia)."), CUERPO, 10, cursiva=True)

    encabezado(d, "3. Resultados")
    parrafo(d, "El clasificador alcanzó una exactitud de 0.91 con 238 grabaciones (n = 238), frente a 0.84 del modelo base.")

    encabezado(d, "4. Fuentes consultadas")
    referencia(d, [("Sato, K., Ibarra, L., & Nwosu, C. (2021). Redes ligeras para zumbidos de abeja. ", None),
                   ("Journal of Hive Sensing, 4(2), 55-70.", None)])
    referencia(d, [("Centro Nacional de Apicultura [CNA]. (2023). ", None), ("Guía de calibración de sensores", True),
                   (". https://ejemplo.invalid/guia", None)])
    referencia(d, [("Marlow, D., Ito, H., & Pérez, R. (2019). Análisis espectral de colmenas. ", None),
                   ("Acoustics of Bees", True), (", 12(1), 1-18.", None)])
    referencia(d, [("Okonkwo, T. (2020). ", None), ("Sensores MEMS para apicultura", True), (". Editorial Ficticia.", None)])
    d.save(destino)
    return destino


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("uso: crear_boceto_sintetico.py RUTA.docx")
    crear(pathlib.Path(sys.argv[1]))
    print("escrito", sys.argv[1])
