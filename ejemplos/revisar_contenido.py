#!/usr/bin/env python3
"""Etapa 3 del ejemplo: aplica sobre la copia corregida las correcciones de contenido que `corregir` no hace solo.

Es lo que el agente (o tú) hace leyendo los hallazgos que quedan; cada edición cita el ID que la motiva. Ninguna
inventa datos ni fuentes: se quita lo que no tiene respaldo y se unifica con lo que el propio documento dice.

Uso: python ejemplos/revisar_contenido.py ENTRADA.corregido.docx SALIDA.final.docx
"""
import sys

import docx
import docx.shared
import docx.text.paragraph

TEXTO = {  # inicio del párrafo -> texto nuevo
    # CON-001: el método (112) manda; el resumen decía 120
    "Este informe describe": (
        "Este informe describe la relación entre el tiempo diario en redes sociales y la calidad del sueño en 112 "
        "estudiantes universitarios de primer año. Los participantes respondieron en línea un cuestionario sobre el uso "
        "del teléfono y el Índice de Calidad de Sueño de Pittsburgh. Quienes usaron redes sociales más de tres horas al "
        "día reportaron peor calidad de sueño que quienes las usaron menos de una hora. Se concluye que conviene incluir "
        "la higiene digital en los programas de bienestar estudiantil."),
    # RED-001: oraciones de más de 40 palabras divididas en dos
    # EA-001 y APA-034: se quitan la afirmación sin fuente (OMS) y la cita sin referencia (Twenge, 2017);
    # APA-038: la obra de Levenson tiene cinco autores
    "El sueño insuficiente": (
        "El sueño insuficiente afecta la memoria, la atención y el rendimiento académico de los estudiantes "
        "(Curcio et al., 2006). En la última década, el uso del teléfono antes de dormir se volvió casi universal entre "
        "los jóvenes. La evidencia acumulada asocia el tiempo frente a pantallas con un sueño más corto y de peor "
        "calidad (Hale & Guan, 2015). Levenson et al. (2016) encontraron que los adultos jóvenes con mayor uso de redes "
        "sociales tenían más probabilidad de presentar alteraciones del sueño."),
    # CON-020: el objetivo 3 no tenía método ni resultado; se sustituye por el que sí atienden las conclusiones
    "3. Comparar": "3. Proponer recomendaciones de higiene digital para los programas de bienestar estudiantil.",
    # CON-004: la sigla se define en su primera aparición
    "Se empleó un diseño": (
        "Se empleó un diseño transversal y correlacional. La muestra estuvo formada por 112 estudiantes de primer año "
        "seleccionados por conveniencia. Cada participante respondió en línea un cuestionario sobre el tiempo diario en "
        "redes sociales y el Índice de Calidad de Sueño de Pittsburgh (PSQI). Las puntuaciones del PSQI van de 0 a 21; "
        "un valor mayor que 5 indica mala calidad de sueño."),
    # CON-008: el párrafo repetía la tabla; ahora dice qué debe ver el lector y añade la correlación (antes en una
    # tabla de una celda sin rótulo, APA-089)
    "Como se observa": (
        "La proporción de estudiantes con mala calidad de sueño se triplica entre quienes usan redes menos de una hora "
        "y quienes las usan más de tres. La correlación de Spearman entre las horas de uso y el PSQI fue moderada y "
        "positiva, rho = .41, p < .001."),
    # APA-034 (Hysing no se citaba) y discusión que la usa con lo que su resumen respalda
    "Los resultados coinciden": (
        "Los resultados coinciden con la revisión de Hale y Guan (2015), con el estudio de Levenson et al. (2016) y con "
        "el de Hysing et al. (2015) en adolescentes: a más tiempo frente a pantallas, peor sueño. Como el diseño fue "
        "transversal, no puede establecerse la dirección de la relación, y la muestra por conveniencia limita la "
        "generalización."),
    # CON-007: diseño no experimental, lenguaje de asociación
    "El uso intensivo": (
        "En esta muestra, el uso intensivo de redes sociales se asoció con una peor calidad del sueño. Por ello, los "
        "programas de bienestar deberían incluir talleres de higiene digital desde el primer semestre."),
}
# APA-072: revista y volumen en cursiva. (antes del título de la revista, revista, resto)
REFS = {
    "Curcio": ("Curcio, G., Ferrara, M., & De Gennaro, L. (2006). Sleep loss, learning capacity and academic "
               "performance. ", "Sleep Medicine Reviews, 10", "(5), 323-337. https://doi.org/10.1016/j.smrv.2005.11.001"),
    "Hale": ("Hale, L., & Guan, S. (2015). Screen time and sleep among school-aged children and adolescents: A "
             "systematic literature review. ", "Sleep Medicine Reviews, 21", ", 50-58. https://doi.org/10.1016/j.smrv.2014.07.007"),
    "Hysing": ("Hysing, M., Pallesen, S., Stormark, K. M., Jakobsen, R., Lundervold, A. J., & Sivertsen, B. (2015). "
               "Sleep and use of electronic devices in adolescence: Results from a large population-based study. ",
               "BMJ Open, 5", "(1), Artículo e006748. https://doi.org/10.1136/bmjopen-2014-006748"),
    "Levenson": ("Levenson, J. C., Shensa, A., Sidani, J. E., Colditz, J. B., & Primack, B. A. (2016). The association "
                 "between social media use and sleep disturbance among young adults. ", "Preventive Medicine, 85",
                 ", 36-41. https://doi.org/10.1016/j.ypmed.2016.01.001"),
}


def poner(p, texto):
    runs = p.runs
    runs[0].text = texto
    for r in runs[1:]:
        r.text = ""


def main(src, dst):
    d = docx.Document(src)
    hechos = set()
    pars = d.paragraphs
    for i, p in enumerate(pars):
        t = p.text.strip()
        for ini, nuevo in TEXTO.items():
            if t.startswith(ini):
                poner(p, nuevo)
                hechos.add(ini)
        if t == "Tabla 1":  # APA-089: número en negrita; título en cursiva
            for r in p.runs:
                r.bold = True
            for r in pars[i + 1].runs:
                r.italic = True
            hechos.add("rótulo")
        if t.startswith("Fuente: elaboración propia"):  # APA-094 / EST-015: nota con «Nota.» en cursiva
            poner(p, "")
            p.runs[0].text = "Nota."
            p.runs[0].italic = True
            p.add_run(" Datos ficticios del estudio piloto; PSQI = Índice de Calidad de Sueño de Pittsburgh.")
            hechos.add("nota")
        for clave, (antes, cursiva, despues) in REFS.items():
            if t.startswith(clave + ","):
                poner(p, antes)
                r = p.add_run(cursiva)
                r.italic = True
                p.add_run(despues)
                hechos.add(clave)
    for t in d.tables:  # la tabla de una celda (correlación) pasa al texto
        if len(t.rows) == 1 and len(t.columns) == 1:
            sig = t._tbl.getnext()
            t._tbl.getparent().remove(t._tbl)
            if sig is not None and sig.tag.endswith('}p'):  # ya no hay tabla encima: sin el espacio de EST-014 (APA-033)
                docx.text.paragraph.Paragraph(sig, d._body).paragraph_format.space_before = docx.shared.Pt(0)
            hechos.add("tabla suelta")
    faltan = set(TEXTO) | set(REFS) | {"rótulo", "nota", "tabla suelta"}
    if faltan - hechos:
        raise SystemExit(f"no se encontró: {sorted(faltan - hechos)}")
    d.save(dst)
    print(f"{len(hechos)} ediciones de contenido aplicadas -> {dst}")


if __name__ == "__main__":
    main(*sys.argv[1:3])
