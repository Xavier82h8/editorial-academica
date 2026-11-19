#!/usr/bin/env python3
"""Genera las plantillas <perfil>.docx (reference-doc de pandoc) con estilos APA 7 o IEEE.

Uso: python -I scripts/crear_plantillas.py [--destino DIR] [--forzar]
Base: pandoc --print-default-data-file reference.docx del pandoc del usuario; se ajustan estilos con python-docx.

Las plantillas NO se versionan ni se distribuyen (derivan del reference.docx de pandoc, GPL): se generan localmente.
Destino por defecto: <caché del usuario>/plantillas-docx (ver datos.py; EDITORIAL_CACHE lo redefine), para no escribir
en la carpeta del plugin. `asegurar_plantillas()` las crea si faltan o si este script cambió (marcador con su hash) y
devuelve el directorio; render.py y los generadores de pruebas la llaman antes de usarlas.
Salida: 0 si se generaron; 2 si falta pandoc o falla (cli.error).
"""
import argparse
import hashlib
import pathlib
import subprocess
import sys

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import cli  # noqa: E402
import datos  # noqa: E402
import render  # noqa: E402

PERFILES = ("apa7", "ieee", "apa7-base+ieee-citas", "ieee-base+apa7-citas", "apa7-profesional")
MARCADOR = ".generado"
NEGRO = RGBColor(0, 0, 0)
CUERPO = ("Normal", "Body Text", "First Paragraph", "Compact", "Block Text", "Bibliography",
          "Abstract", "Title", "Subtitle", "Author", "Date", "Table Caption", "Image Caption",
          "Caption", "Figure", "Captioned Figure", "Footnote Text")


def num_pagina_derecha(section):
    hdr = section.header
    p = hdr.paragraphs[0] if hdr.paragraphs else hdr.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r = p.add_run()
    for tag, val in (("w:fldChar", "begin"), ("w:instrText", " PAGE "), ("w:fldChar", "end")):
        el = OxmlElement(tag)
        if tag == "w:fldChar":
            el.set(qn("w:fldCharType"), val)
        else:
            el.set(qn("xml:space"), "preserve")
            el.text = val
        r._r.append(el)


def encabezado_profesional(section):
    """APA 7 profesional (2.18): running head a la izquierda (lo rellena render.postproceso_docx) y PAGE a la derecha."""
    p = section.header.paragraphs[0]
    for r in list(p.runs):
        r._r.getparent().remove(r._r)
    p.alignment = None
    ppr = p._p.get_or_add_pPr()
    tabs = OxmlElement("w:tabs")
    tab = OxmlElement("w:tab")
    tab.set(qn("w:val"), "right")
    tab.set(qn("w:pos"), "9360")
    tabs.append(tab)
    ppr.append(tabs)
    p.add_run("")  # marcador: texto del running head
    r = p.add_run()
    r._r.append(OxmlElement("w:tab"))
    r2 = p.add_run()
    for tag, val in (("w:fldChar", "begin"), ("w:instrText", " PAGE "), ("w:fldChar", "end")):
        el = OxmlElement(tag)
        if tag == "w:fldChar":
            el.set(qn("w:fldCharType"), val)
        else:
            el.set(qn("xml:space"), "preserve")
            el.text = val
        r2._r.append(el)


def estilo(d, nombre):
    try:
        return d.styles[nombre]
    except KeyError:
        return None


def fuente(st, nombre, tam):
    st.font.name = nombre
    st.font.size = Pt(tam)
    st.font.color.rgb = NEGRO
    rpr = st.element.get_or_add_rPr()
    rf = rpr.find(qn("w:rFonts"))
    if rf is None:
        rf = OxmlElement("w:rFonts")
        rpr.append(rf)
    for k in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rf.set(qn(k), nombre)
    for k in ("w:asciiTheme", "w:hAnsiTheme", "w:cstheme", "w:eastAsiaTheme"):
        rf.attrib.pop(qn(k), None)


def apa(d):
    for n in CUERPO:
        st = estilo(d, n)
        if st is None:
            continue
        fuente(st, "Times New Roman", 12)
        pf = st.paragraph_format
        pf.line_spacing = 2.0
        pf.space_before = pf.space_after = Pt(0)
        pf.alignment = WD_ALIGN_PARAGRAPH.LEFT
    for n in ("Body Text", "Normal"):
        estilo(d, n).paragraph_format.first_line_indent = Inches(0.5)
    estilo(d, "First Paragraph").paragraph_format.first_line_indent = Inches(0.5)
    bib = estilo(d, "Bibliography")
    if bib is not None:
        bib.paragraph_format.left_indent = Inches(0.5)
        bib.paragraph_format.first_line_indent = Inches(-0.5)
    # niveles de encabezado APA 7 (1-3 en párrafo propio; 4-5 en línea no los soporta pandoc)
    niveles = {1: (WD_ALIGN_PARAGRAPH.CENTER, True, False), 2: (WD_ALIGN_PARAGRAPH.LEFT, True, False),
               3: (WD_ALIGN_PARAGRAPH.LEFT, True, True), 4: (WD_ALIGN_PARAGRAPH.LEFT, True, False),
               5: (WD_ALIGN_PARAGRAPH.LEFT, True, True)}
    for lvl, (al, b, it) in niveles.items():
        st = estilo(d, f"Heading {lvl}")
        if st is None:
            continue
        fuente(st, "Times New Roman", 12)
        st.font.bold, st.font.italic = b, it
        pf = st.paragraph_format
        pf.alignment, pf.line_spacing = al, 2.0
        pf.space_before = pf.space_after = Pt(0)
        pf.first_line_indent = Inches(0.5) if lvl >= 4 else Inches(0)
        pf.keep_with_next = True
    t = estilo(d, "Title")
    if t is not None:
        t.font.bold = True
        t.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
        t.paragraph_format.first_line_indent = Inches(0)


def ieee(d):
    # IEEE no define maquetación de tesis/informe: valores de Transactions a una columna;
    # el perfil de equipo (.editorial.yaml) puede reemplazarlos.
    for n in CUERPO:
        st = estilo(d, n)
        if st is None:
            continue
        fuente(st, "Times New Roman", 10)
        pf = st.paragraph_format
        pf.line_spacing = 1.0
        pf.space_before = pf.space_after = Pt(0)
        pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    for n in ("Body Text", "Normal", "First Paragraph"):
        estilo(d, n).paragraph_format.first_line_indent = Inches(0.125)
    bib = estilo(d, "Bibliography")
    if bib is not None:
        fuente(bib, "Times New Roman", 8)
        bib.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
        bib.paragraph_format.left_indent = Inches(0.3)
        bib.paragraph_format.first_line_indent = Inches(-0.3)
    for lvl, (al, sc, it) in {1: (WD_ALIGN_PARAGRAPH.CENTER, True, False),
                               2: (WD_ALIGN_PARAGRAPH.LEFT, False, True),
                               3: (WD_ALIGN_PARAGRAPH.LEFT, False, True)}.items():
        st = estilo(d, f"Heading {lvl}")
        if st is None:
            continue
        fuente(st, "Times New Roman", 10)
        st.font.bold = False
        st.font.small_caps, st.font.italic = sc, it
        st.paragraph_format.alignment = al
        st.paragraph_format.space_before = Pt(6)
        st.paragraph_format.space_after = Pt(3)


def dir_plantillas():
    return datos.dir_cache() / "plantillas-docx"


def _huella():
    return hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()


def generar(out):
    out = pathlib.Path(out)
    out.mkdir(parents=True, exist_ok=True)
    exe = render.pandoc()  # error claro (exit 2) si falta pandoc
    base = out / "_pandoc-default.docx"
    r = subprocess.run([exe, "-o", str(base), "--print-default-data-file", "reference.docx"],
                       capture_output=True, text=True)
    if r.returncode != 0 or not base.exists():
        cli.error("pandoc no pudo entregar reference.docx: " + (r.stderr.strip() or f"código {r.returncode}"))
    fns = {"apa7": apa, "ieee": ieee, "apa7-base+ieee-citas": apa, "ieee-base+apa7-citas": ieee, "apa7-profesional": apa}
    for perfil in PERFILES:
        d = Document(base)
        fns[perfil](d)
        if perfil in ("ieee-base+apa7-citas", "apa7-base+ieee-citas"):  # lista APA: sangría francesa 0.5 in
            bib = estilo(d, "Bibliography")
            bib.paragraph_format.left_indent = Inches(0.5)
            bib.paragraph_format.first_line_indent = Inches(-0.5)
        for s in d.sections:
            s.top_margin = s.bottom_margin = s.left_margin = s.right_margin = Inches(1)
            if perfil == "apa7-profesional":
                encabezado_profesional(s)
            else:
                num_pagina_derecha(s)
        d.save(out / f"{perfil}.docx")
    base.unlink()
    (out / MARCADOR).write_text(_huella(), encoding="utf-8")


def asegurar_plantillas(forzar=False):
    """Devuelve el directorio con las plantillas, generándolas si faltan o están desactualizadas."""
    out = dir_plantillas()
    ok = (out / MARCADOR).is_file() and (out / MARCADOR).read_text(encoding="utf-8") == _huella()         and all((out / f"{p}.docx").is_file() for p in PERFILES)
    if forzar or not ok:
        generar(out)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--destino", help="directorio de salida (por defecto, el de la caché del usuario)")
    ap.add_argument("--forzar", action="store_true", help="regenera aunque estén al día")
    a = ap.parse_args()
    if a.destino:
        generar(a.destino)
        out = pathlib.Path(a.destino)
    else:
        out = asegurar_plantillas(a.forzar)
    print(out)


if __name__ == "__main__":
    main()
