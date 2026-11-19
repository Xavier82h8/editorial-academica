#!/usr/bin/env python3
"""Genera documentos de prueba .docx: uno correcto y uno con errores sembrados por perfil.

Uso: python -I tests/generar_docs.py   -> tests/docs/<perfil>_{correcto,errores}.docx + esperado.json
Cada error sembrado se etiqueta con el ID de regla que el juez debe reportar.
"""
import base64
import io
import json
import pathlib

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import RGBColor, Inches, Pt

OUT = pathlib.Path(__file__).resolve().parent / "docs"
LOREM = ("Los sistemas de tutoría inteligente han mostrado efectos positivos en el aprendizaje de la música, "
         "en particular cuando el estudiante explica lo aprendido a un agente que asume el rol de aprendiz. ")

APA_REFS = [
    ("Chen", "2022", "Chen, X., Wang, X., Zhang, K., & Qiu, Y. (2022). Recent advances and clinical applications of deep learning in medical image analysis. *Medical Image Analysis*, *79*, Article 102444. https://doi.org/10.1016/j.media.2022.102444"),
    ("Ker", "2018", "Ker, J., Wang, L., Rao, J., & Lim, T. (2018). Deep learning applications in medical image analysis. *IEEE Access*, *6*, 9375–9389. https://doi.org/10.1109/access.2017.2788044"),
    ("Litjens", "2017", "Litjens, G., Kooi, T., Bejnordi, B. E., Setio, A. A. A., Ciompi, F., Ghafoorian, M., van der Laak, J. A. W. M., van Ginneken, B., & Sánchez, C. I. (2017). A survey on deep learning in medical image analysis. *Medical Image Analysis*, *42*, 60–88. https://doi.org/10.1016/j.media.2017.07.005"),
    ("Shen", "2017", "Shen, D., Wu, G., & Suk, H.-I. (2017). Deep learning in medical image analysis. *Annual Review of Biomedical Engineering*, *19*, 221–248. https://doi.org/10.1146/annurev-bioeng-071516-044442"),
]
IEEE_REFS = [
    "G. Litjens et al., “A survey on deep learning in medical image analysis,” *Med. Image Anal.*, vol. 42, pp. 60–88, Dec. 2017, doi: 10.1016/j.media.2017.07.005.",
    "D. Shen, G. Wu, and H.-I. Suk, “Deep learning in medical image analysis,” *Annu. Rev. Biomed. Eng.*, vol. 19, pp. 221–248, Jun. 2017, doi: 10.1146/annurev-bioeng-071516-044442.",
    "J. Ker, L. Wang, J. Rao, and T. Lim, “Deep learning applications in medical image analysis,” *IEEE Access*, vol. 6, pp. 9375–9389, 2018, doi: 10.1109/ACCESS.2017.2788044.",
    "X. Chen et al., “Recent advances and clinical applications of deep learning in medical image analysis,” *Med. Image Anal.*, vol. 79, Jul. 2022, Art. no. 102444, doi: 10.1016/j.media.2022.102444.",
]


def runs_md(p, texto, font=None, size=None):
    for i, trozo in enumerate(texto.split("*")):
        if not trozo:
            continue
        r = p.add_run(trozo)
        r.italic = i % 2 == 1
        if font:
            r.font.name = font
        if size:
            r.font.size = Pt(size)


def num_pagina(section, derecha=True):
    p = section.header.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT if derecha else WD_ALIGN_PARAGRAPH.LEFT
    r = p.add_run()
    for tag, attr in (("w:fldChar", "begin"), ("w:instrText", None), ("w:fldChar", "end")):
        el = OxmlElement(tag)
        if attr:
            el.set(qn("w:fldCharType"), attr)
        else:
            el.set(qn("xml:space"), "preserve")
            el.text = " PAGE "
        r._r.append(el)


def base(margen=1.0, font="Times New Roman", size=12, interlineado=2.0, numpag=True, numder=True):
    d = Document()
    st = d.styles["Normal"]
    st.font.name, st.font.size = font, Pt(size)
    st.paragraph_format.line_spacing = interlineado
    st.paragraph_format.space_after = Pt(0)
    s = d.sections[0]
    s.top_margin = s.bottom_margin = s.left_margin = s.right_margin = Inches(margen)
    if numpag:
        num_pagina(s, numder)
    return d


def parrafo(d, texto, sangria=0.5, just=False):
    p = d.add_paragraph()
    p.paragraph_format.first_line_indent = Inches(sangria)
    if just:
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    runs_md(p, texto)
    return p


def titulo_refs(d, texto="Referencias", salto=True):
    if salto:
        d.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
    p = d.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run(texto).bold = True


def entrada(d, texto, francesa=True):
    p = d.add_paragraph()
    if francesa:
        p.paragraph_format.left_indent = Inches(0.5)
        p.paragraph_format.first_line_indent = Inches(-0.5)
    runs_md(p, texto)


# ------------------------------------------------------------------ APA
def apa(errores):
    E = []
    d = base(margen=1.25 if errores else 1.0, numder=not errores)
    if errores:
        E += [("APA-001", "márgenes 1.25"), ("APA-008", "número de página a la izquierda")]
    parrafo(d, LOREM + "La revisión de Litjens et al. (2017) es la referencia obligada del campo.")
    if errores:
        parrafo(d, LOREM + "Los modelos profundos superan a los clásicos (Shen and Wu, 2017).", sangria=0.0, just=True)
        E += [("APA-007", "párrafo sin sangría"), ("APA-006", "párrafo justificado"),
              ("APA-037", "«and» en parentética"), ("APA-035", "Shen 2017 citado como Shen and Wu: ok; año correcto")]
        E.pop()  # la última no es error: se deja documentado el intento
        parrafo(d, LOREM + "Otros estudios lo confirman (Chen et al., 2022; Ker et al., 2019).")
        E += [("APA-035", "Ker 2019 vs 2018 en la lista")]
        parrafo(d, LOREM + "También hay evidencia en contextos educativos (Gómez, 2021).")
        E += [("APA-034", "Gómez 2021 no está en la lista")]
    else:
        parrafo(d, LOREM + "Los modelos profundos superan a los clásicos (Shen et al., 2017).")
        parrafo(d, LOREM + "Otros estudios lo confirman (Chen et al., 2022; Ker et al., 2018).")
    titulo_refs(d, salto=not errores)
    if errores:
        E += [("APA-012", "referencias sin salto de página")]
    refs = [r[2] for r in APA_REFS]
    if errores:
        refs[1], refs[2] = refs[2], refs[1]
        E += [("APA-061", "orden alfabético roto")]
        refs[3] = refs[3].replace("https://doi.org/", "doi:")
        E += [("APA-076", "DOI con prefijo doi:")]
        refs[0] = refs[0] + "."
        E += [("APA-075", "punto después del DOI")]
    for i, r in enumerate(refs):
        entrada(d, r, francesa=not (errores and i == 0))
    if errores:
        E += [("APA-060", "primera entrada sin sangría francesa")]
    return d, E


# ------------------------------------------------------------------ IEEE
def ieee(errores):
    E = []
    d = base()
    if errores:
        parrafo(d, LOREM + "La revisión más citada del campo es [2].")
        parrafo(d, LOREM + "Varios trabajos lo confirman [1]–[3], y otros más recientes también.[4]")
        parrafo(d, LOREM + "Ver también [1, 2] y el estudio de 2023 [7].")
        parrafo(d, LOREM + "Este resultado coincide con (Shen, 2017).")
        E += [("IEEE-014", "primera cita es [2]"), ("IEEE-004", "rango [1]–[3]"), ("IEEE-002", "puntuación antes de [4]"),
              ("IEEE-003", "[1, 2]"), ("IEEE-012", "[7] no existe"), ("IEEE-001", "cita autor-año")]
    else:
        parrafo(d, LOREM + "La revisión más citada del campo es [1].")
        parrafo(d, LOREM + "Varios trabajos lo confirman [1], [2], [3], y otros más recientes también [4].")
    titulo_refs(d)
    refs = list(IEEE_REFS)
    if errores:
        refs[1] = refs[1].replace("doi: ", "DOI: ")
        E += [("IEEE-037", "DOI: en mayúscula")]
        refs[2] = refs[2].rstrip(".")
        E += [("IEEE-038", "sin punto final")]
    for i, r in enumerate(refs, 1):
        num = f"[{i}]" if not (errores and i == 4) else ""
        entrada(d, (num + "\t" if num else "") + r)
    if errores:
        E += [("IEEE-016", "entrada 4 sin [n]")]
    return d, E


# ------------------------------------------------------------------ APA: encabezados, tablas, figuras, citas finas
PNG_1X1 = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==")


def fmt(p, antes=0, despues=0, sangria=0.0, centro=False, linea=2.0):
    pf = p.paragraph_format
    pf.space_before, pf.space_after, pf.line_spacing = Pt(antes), Pt(despues), linea
    pf.first_line_indent = Inches(sangria)
    if centro:
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    return p


def enc(d, texto, nivel, antes=0, centro=None, negrita=True):
    p = d.add_paragraph(style=f"Heading {nivel}")
    fmt(p, antes=antes, centro=(nivel == 1) if centro is None else centro)
    r = p.add_run(texto)
    r.font.name, r.font.size, r.font.color.rgb = "Times New Roman", Pt(12), RGBColor(0, 0, 0)  # negro, no el azul del estilo
    r.bold, r.italic = negrita, nivel == 3
    return p


def rotulo(d, num, titulo, tabla=True):
    p = d.add_paragraph()
    fmt(p)
    p.add_run(("Tabla " if tabla else "Figura ") + str(num)).bold = True
    t = d.add_paragraph()
    fmt(t)
    t.add_run(titulo).italic = True


def nota(d, texto, italica=True, etiqueta="Nota."):
    p = d.add_paragraph()
    fmt(p)
    r = p.add_run(etiqueta)
    r.italic = italica
    p.add_run(" " + texto)
    return p


def tabla(d, bordes_verticales=False):
    t = d.add_table(rows=2, cols=2)
    for i, fila in enumerate((("Medida", "Valor"), ("Exactitud", "0.91"))):
        for j, v in enumerate(fila):
            t.cell(i, j).text = v
    if bordes_verticales:
        pr = t._tbl.tblPr
        b = OxmlElement("w:tblBorders")
        for lado in ("top", "left", "bottom", "right", "insideH", "insideV"):
            e = OxmlElement(f"w:{lado}")
            e.set(qn("w:val"), "single")
            e.set(qn("w:sz"), "4")
            b.append(e)
        pr.append(b)
    return t


def apa_fino(errores):
    """Documento APA con encabezados, tablas, figuras y citas finas (APA-005/025/028/030/033/036/043/060/065/072/089/091/093/094)."""
    E = []
    d = base()
    mid = LOREM + "La Tabla 1 resume los datos y la Figura 1 muestra el flujo del método."
    enc(d, "Método", 1, centro=False if errores else None, negrita=True)
    if errores:
        E += [("APA-025", "nivel 1 a la izquierda")]
    p = parrafo(d, mid + " Chen et al., 2022, propusieron un enfoque." if errores else
                mid + " Chen et al. (2022) propusieron un enfoque.")
    if errores:
        fmt(p, despues=12, sangria=0.5)
        E += [("APA-005", "espacio después de párrafo de 12 pt"), ("APA-036", "narrativa «Chen et al., 2022, propusieron»")]
    enc(d, "2.1 Participantes" if errores else "Participantes", 2, antes=12 if errores else 0)
    if errores:
        E += [("APA-030", "encabezado numerado"), ("APA-033", "encabezado con espacio antes de 12 pt")]
    p = d.add_paragraph()
    fmt(p, sangria=0.0 if errores else 0.5)
    p.add_run("Criterios de inclusión.").bold = True
    p.add_run(" " + LOREM)
    if errores:
        E += [("APA-028", "encabezado de nivel 4 en línea sin sangría"), ("APA-007", "ese párrafo tampoco tiene sangría de primera línea")]
    rotulo(d, 1, "Medidas de desempeño") if not errores else None
    if errores:
        t0 = d.add_paragraph()   # tabla sin número
        fmt(t0)
        t0.add_run("Medidas de desempeño").italic = True
        E += [("APA-089", "tabla sin número y figura con el título debajo")]
    tabla(d, bordes_verticales=errores)
    if errores:
        E += [("APA-093", "tabla con bordes verticales")]
    nota(d, "Elaboración propia. Ver también la Tabla 2." if errores else "Elaboración propia.", italica=not errores)
    if errores:
        E += [("APA-094", "«Nota.» sin cursiva y pie de figura sin «Nota.»")]
        rotulo(d, 2, "Resultados adicionales")
        tabla(d)
        E += [("APA-091", "Tabla 2 solo se menciona en una nota")]
    p = parrafo(d, LOREM + "Los estudios previos coinciden (Chen et al., 2022; Ker et al., 2018).")
    if errores:
        parrafo(d, LOREM + "Los modelos profundos superan a los clásicos (Shen et al., 2017; Litjens et al., 2017) y (Litjens, p. 4) lo ilustra.")
        E += [("APA-043", "Shen antes que Litjens"), ("APA-036", "(Litjens, p. 4) sin año")]
        parrafo(d, LOREM + "La salud mental es prioritaria (Organización Mundial de la Salud [OMS], 2021).")
    else:
        parrafo(d, LOREM + "Los modelos profundos superan a los clásicos (Litjens et al., 2017; Shen et al., 2017).")
        parrafo(d, LOREM + "La salud mental es prioritaria (Organización Mundial de la Salud [OMS], 2021).")
    rotulo(d, 1, "Flujo del método", tabla=False) if not errores else None
    if errores:
        r = d.add_paragraph().add_run("Figura 1")
        r.bold = True
    pf = d.add_paragraph()
    fmt(pf, centro=True)
    pf.add_run().add_picture(io.BytesIO(PNG_1X1), width=Inches(1))
    if errores:
        t = d.add_paragraph()
        fmt(t)
        t.add_run("Flujo del método. Elaboración propia.").italic = True
    else:
        nota(d, "Elaboración propia.")
    titulo_refs(d, salto=True)
    refs = [APA_REFS[0][2],
            APA_REFS[1][2].replace("*IEEE Access*, *6*", "IEEE Access, 6") if errores else APA_REFS[1][2],
            APA_REFS[2][2],
            "Organización Mundial de la Salud" + (" [OMS]" if errores else "") + ". (2021). *Informe mundial sobre la salud mental*. https://www.who.int/es",
            APA_REFS[3][2]]
    if errores:
        E += [("APA-072", "revista y volumen sin cursiva"), ("APA-065", "sigla [OMS] en la lista"),
              ("APA-060", "espacio entre entradas")]
    for r in refs:
        p = d.add_paragraph()
        p.paragraph_format.left_indent, p.paragraph_format.first_line_indent = Inches(0.5), Inches(-0.5)
        if errores:
            p.paragraph_format.space_after = Pt(9)
        runs_md(p, r)
    return d, E


def main():
    OUT.mkdir(exist_ok=True)
    esperado = {}
    for nombre, fn, perfil in (("apa7", apa, "apa7"), ("ieee", ieee, "ieee"), ("apa7_fino", apa_fino, "apa7")):
        for err in (False, True):
            d, E = fn(err)
            f = OUT / f"{nombre}_{'errores' if err else 'correcto'}.docx"
            d.save(f)
            esperado[f.name] = {"perfil": perfil, "errores": [{"id": i, "desc": s} for i, s in E]}
    (OUT / "esperado.json").write_text(json.dumps(esperado, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n".join(f"{k}: {len(v['errores'])} errores sembrados" for k, v in esperado.items()))


if __name__ == "__main__":
    main()
