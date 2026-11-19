#!/usr/bin/env python3
"""Genera tests/estructura/maquetacion.docx sembrado con defectos de maquetación (EST-010..EST-015).

- PAGE en el encabezado y en el pie (EST-010); pie «Página X de Y» con NUMPAGES (EST-011)
- «Tabla 1» + título + tabla corta sin keep_with_next ni cantSplit (EST-012), nota «Fuente: elaboración propia» (EST-015)
- «Tabla 2» con 30 filas sin tblHeader (EST-013)
- Encabezado Heading 1 pegado al final de la tabla 2 (EST-014)
"""
import pathlib
import sys

import docx
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt

SALIDA = pathlib.Path(__file__).resolve().parent / "maquetacion.docx"


def campo(par, instr):
    for tipo, txt in (("begin", None), (None, instr), ("separate", None), (None, "1"), ("end", None)):
        r = par.add_run()
        if tipo:
            fc = OxmlElement("w:fldChar")
            fc.set(qn("w:fldCharType"), tipo)
            r._r.append(fc)
        elif txt == instr:
            it = OxmlElement("w:instrText")
            it.set(qn("xml:space"), "preserve")
            it.text = f" {instr} "
            r._r.append(it)
        else:
            r.text = txt


def _ptab(par):
    r = par.add_run()
    pt = OxmlElement("w:ptab")
    pt.set(qn("w:relativeTo"), "margin")
    pt.set(qn("w:alignment"), "right")
    pt.set(qn("w:leader"), "none")
    r._r.append(pt)


def portada(destino, con_numero):
    """.docx de dos páginas para las pruebas de EST-016 (numeración de la portada), sin escribir nada en el repositorio.
    Encabezado general «TITULO ABREVIADO» + PAGE a la derecha. con_numero=True: la portada comparte ese encabezado;
    False: primera página distinta con el running head y sin PAGE. Pie con el texto «Pie institucional»."""
    d = docx.Document()
    s = d.sections[0]
    ph = s.header.paragraphs[0]
    ph.add_run("TITULO ABREVIADO")
    _ptab(ph)
    campo(ph, "PAGE")
    s.footer.paragraphs[0].add_run("Pie institucional")
    if not con_numero:
        s.different_first_page_header_footer = True
        s.first_page_header.paragraphs[0].add_run("TITULO ABREVIADO")
    d.add_paragraph("Título del protocolo")
    d.add_paragraph("Autor del protocolo")
    d.add_page_break()
    d.add_heading("Introducción", level=1)
    d.add_paragraph("Texto de la introducción.")
    d.save(destino)
    return destino


def main(salida=None):
    salida = pathlib.Path(salida) if salida else SALIDA
    d = docx.Document()
    for nombre in ("Heading 1", "Normal"):
        d.styles[nombre].paragraph_format.space_before = Pt(0)
        d.styles[nombre].paragraph_format.space_after = Pt(0)
    s = d.sections[0]
    ph = s.header.paragraphs[0]
    ph.add_run("Protocolo de prueba ")
    campo(ph, "PAGE")
    pf = s.footer.paragraphs[0]
    pf.add_run("Página ")
    campo(pf, "PAGE")
    pf.add_run(" de ")
    campo(pf, "NUMPAGES")

    d.add_heading("Introducción", level=1)
    d.add_paragraph("La Tabla 1 resume los estudios previos y la Tabla 2 el registro de pruebas.")
    d.add_paragraph("Tabla 1")
    d.add_paragraph("Estudios previos")
    t = d.add_table(rows=4, cols=3)
    t.style = "Table Grid"
    datos = [("Año", "Autores", "Aporte"), ("2017", "Vaswani et al.", "Transformer"),
             ("2018", "Devlin et al.", "BERT"), ("2020", "Brown et al.", "GPT-3")]
    for i, fila in enumerate(datos):
        for j, v in enumerate(fila):
            t.cell(i, j).text = v
    d.add_paragraph("Fuente: elaboración propia")
    d.add_paragraph("Texto intermedio del documento.")
    d.add_paragraph("Tabla 2")
    d.add_paragraph("Registro de pruebas")
    t2 = d.add_table(rows=30, cols=2)
    t2.style = "Table Grid"
    for i in range(30):
        t2.cell(i, 0).text = "Prueba" if i == 0 else f"P{i}"
        t2.cell(i, 1).text = "Resultado" if i == 0 else "ok"
    d.add_heading("Resultados", level=1)
    d.add_paragraph("Texto de los resultados.")
    d.save(salida)
    print("escrito", salida)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
