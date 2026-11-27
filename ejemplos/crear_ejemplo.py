#!/usr/bin/env python3
"""Genera ejemplos/informe-ejemplo.docx: un informe de estudiante con los errores que más se ven en una entrega real.

Los datos del estudio son FICTICIOS (se declara en la nota de autor de la portada). Las cuatro referencias son reales y
se verificaron contra Crossref con `python scripts/editorial.py fuentes --doi …` (ver ejemplos/fuentes.json).

Errores sembrados a propósito (lo que el juez debe encontrar):
- Formato: márgenes de 0.75 in, interlineado sencillo, encabezados con el estilo de Word por defecto (azules, sin el
  formato APA de nivel), sin sangría de primera línea.
- Paginación: número en el encabezado Y «Página X de Y» en el pie; la portada también lleva número.
- Tabla: título sin cursiva, nota «Fuente: elaboración propia», el párrafo siguiente repite sus cifras y el encabezado
  «Discusión» queda pegado a la tabla.
- Congruencia: el resumen dice n = 120 y el método n = 112; un objetivo (comparar por carrera) no vuelve a aparecer;
  la conclusión habla de causa con un diseño transversal; una sigla se usa antes de definirla.
- Citas y referencias: «&» en una cita narrativa, una cita sin referencia (Twenge, 2017), una referencia que nadie cita,
  lista sin orden alfabético, sin sangría francesa y con DOI en formato antiguo («doi:»).
- Un marcador del redactor que se quedó en el texto: [[FALTA FUENTE: dato de la OMS]].

Uso: python ejemplos/crear_ejemplo.py [SALIDA.docx]
"""
import pathlib
import sys

import docx
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt

AQUI = pathlib.Path(__file__).resolve().parent
SALIDA = AQUI / "informe-ejemplo.docx"


def campo(par, instr):
    for tipo, txt in (("begin", None), ("instr", instr), ("separate", None), (None, "1"), ("end", None)):
        r = par.add_run()
        if tipo == "instr":
            it = OxmlElement("w:instrText")
            it.set(qn("xml:space"), "preserve")
            it.text = f" {txt} "
            r._r.append(it)
        elif tipo:
            fc = OxmlElement("w:fldChar")
            fc.set(qn("w:fldCharType"), tipo)
            r._r.append(fc)
        else:
            r.text = txt


def parrafo(d, texto, **kw):
    p = d.add_paragraph(texto)
    if kw.get("centro"):
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    if kw.get("negrita"):
        for r in p.runs:
            r.bold = True
    return p


def main(salida=None):
    salida = pathlib.Path(salida) if salida else SALIDA
    d = docx.Document()
    normal = d.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(11)
    normal.paragraph_format.line_spacing = 1.0
    normal.paragraph_format.space_after = Pt(6)

    s = d.sections[0]
    s.page_width, s.page_height = Inches(8.5), Inches(11)
    for lado in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
        setattr(s, lado, Inches(0.75))
    ph = s.header.paragraphs[0]
    ph.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    campo(ph, "PAGE")
    pf = s.footer.paragraphs[0]
    pf.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pf.add_run("Página ")
    campo(pf, "PAGE")
    pf.add_run(" de ")
    campo(pf, "NUMPAGES")

    # --- Portada (lleva número de página: el encabezado no distingue la primera página)
    for _ in range(3):
        d.add_paragraph()
    parrafo(d, "Uso de redes sociales y calidad del sueño en estudiantes universitarios", centro=True, negrita=True)
    d.add_paragraph()
    for linea in ("Estudiante de Ejemplo", "Facultad de Psicología, Universidad de Ejemplo",
                  "Métodos de Investigación I", "Dra. Docente de Ejemplo", "15 de octubre de 2026"):
        parrafo(d, linea, centro=True)
    d.add_paragraph()
    parrafo(d, "Nota de autor: los datos de este informe son ficticios y se crearon para demostrar el editor; "
               "las referencias son reales.", centro=True)
    d.add_page_break()

    # --- Resumen
    d.add_heading("Resumen", level=1)
    d.add_paragraph(
        "Este informe describe la relación entre el tiempo diario en redes sociales y la calidad del sueño en una muestra "
        "de estudiantes universitarios. Participaron 120 estudiantes de primer año que respondieron un cuestionario en "
        "línea sobre sus hábitos de uso del teléfono y el Índice de Calidad de Sueño de Pittsburgh. Los estudiantes que "
        "usaron redes sociales más de tres horas al día reportaron peor calidad de sueño que quienes las usaron menos de "
        "una hora. Se concluye que conviene incluir la higiene digital en los programas de bienestar estudiantil.")

    # --- Introducción
    d.add_heading("Introducción", level=1)
    d.add_paragraph(
        "El sueño insuficiente afecta la memoria, la atención y el rendimiento académico de los estudiantes "
        "(Curcio et al., 2006). En la última década, el uso del teléfono antes de dormir se volvió casi universal entre "
        "los jóvenes, y la evidencia acumulada asocia el tiempo frente a pantallas con un sueño más corto y de peor "
        "calidad (Hale y Guan, 2015). Levenson & Shensa (2016) encontraron que los adultos jóvenes con mayor uso de "
        "redes sociales tenían más probabilidad de presentar alteraciones del sueño. Según la OMS, la mitad de los "
        "jóvenes duerme menos de lo recomendado [[FALTA FUENTE: dato de la OMS]]. Algunos autores señalan que la "
        "generación nacida con el teléfono inteligente duerme menos que las anteriores (Twenge, 2017).")
    d.add_heading("Objetivos", level=1)
    d.add_paragraph("1. Describir el tiempo diario que los estudiantes dedican a las redes sociales.")
    d.add_paragraph("2. Relacionar ese tiempo con la calidad del sueño autorreportada.")
    d.add_paragraph("3. Comparar los resultados entre carreras de ingeniería y de humanidades.")

    # --- Método
    d.add_heading("Método", level=1)
    d.add_paragraph(
        "Se empleó un diseño transversal y correlacional. La muestra estuvo formada por 112 estudiantes de primer año "
        "(n = 112) seleccionados por conveniencia. Cada participante respondió en línea un cuestionario sobre el tiempo "
        "diario en redes sociales y el PSQI, cuya versión completa es el Índice de Calidad de Sueño de Pittsburgh (PSQI). "
        "Las puntuaciones del PSQI van de 0 a 21; un valor mayor que 5 indica mala calidad de sueño.")

    # --- Resultados con tabla
    d.add_heading("Resultados", level=1)
    d.add_paragraph("La Tabla 1 resume la calidad del sueño según el tiempo diario de uso de redes sociales.")
    d.add_paragraph("Tabla 1")
    d.add_paragraph("Calidad del sueño según el tiempo diario en redes sociales")
    t = d.add_table(rows=4, cols=4)
    t.style = "Table Grid"
    filas = [("Tiempo diario", "Estudiantes", "PSQI medio", "Mala calidad (%)"),
             ("Menos de 1 h", "28", "4.1", "25.0"),
             ("De 1 a 3 h", "51", "6.3", "54.9"),
             ("Más de 3 h", "33", "8.2", "78.8")]
    for i, fila in enumerate(filas):
        for j, v in enumerate(fila):
            t.cell(i, j).text = v
    d.add_paragraph("Fuente: elaboración propia")
    d.add_paragraph(
        "Como se observa, 28 estudiantes usaron redes menos de 1 h con un PSQI medio de 4.1 y 25.0 % de mala calidad; "
        "51 estudiantes usaron de 1 a 3 h con un PSQI de 6.3 y 54.9 %; y 33 estudiantes usaron más de 3 h con un PSQI "
        "de 8.2 y 78.8 % de mala calidad.")
    t2 = d.add_table(rows=1, cols=1)
    t2.style = "Table Grid"
    t2.cell(0, 0).text = "Correlación de Spearman entre horas de uso y PSQI: rho = .41, p < .001"
    d.add_heading("Discusión", level=1)
    d.add_paragraph(
        "Los resultados coinciden con la revisión de Hale y Guan (2015) y con el estudio de Levenson et al. (2016): a "
        "más tiempo en redes sociales, peor calidad de sueño. Como el diseño fue transversal, no puede establecerse la "
        "dirección de la relación, y la muestra por conveniencia limita la generalización.")

    # --- Conclusiones
    d.add_heading("Conclusiones", level=1)
    d.add_paragraph(
        "El uso intensivo de redes sociales provoca una peor calidad del sueño en los estudiantes universitarios. Por "
        "ello, los programas de bienestar deberían incluir talleres de higiene digital desde el primer semestre.")

    # --- Referencias (desordenadas, sin sangría francesa, DOI antiguo; Hysing et al. no se cita)
    d.add_heading("Referencias", level=1)
    for ref in (
        "Levenson, J. C., Shensa, A., Sidani, J. E., Colditz, J. B., & Primack, B. A. (2016). The association between "
        "social media use and sleep disturbance among young adults. Preventive Medicine, 85, 36–41. "
        "doi:10.1016/j.ypmed.2016.01.001",
        "Hale, L., & Guan, S. (2015). Screen time and sleep among school-aged children and adolescents: A systematic "
        "literature review. Sleep Medicine Reviews, 21, 50–58. https://doi.org/10.1016/j.smrv.2014.07.007",
        "Curcio, G., Ferrara, M., & De Gennaro, L. (2006). Sleep loss, learning capacity and academic performance. "
        "Sleep Medicine Reviews, 10(5), 323–337. https://doi.org/10.1016/j.smrv.2005.11.001",
        "Hysing, M., Pallesen, S., Stormark, K. M., Jakobsen, R., Lundervold, A. J., & Sivertsen, B. (2015). Sleep and "
        "use of electronic devices in adolescence: Results from a large population-based study. BMJ Open, 5(1), "
        "e006748. https://doi.org/10.1136/bmjopen-2014-006748",
    ):
        d.add_paragraph(ref)

    d.core_properties.author = "Estudiante de Ejemplo"
    d.core_properties.title = "Uso de redes sociales y calidad del sueño"
    d.save(salida)
    print("escrito", salida)
    return salida


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
