# -*- coding: utf-8 -*-
"""Genera tests/congruencia/hilo.docx y hilo_orden.docx para CON-009, CON-018, CON-019 y CON-020.
Uso: python -I tests/congruencia/generar_hilo.py

hilo.docx (cada regla exactamente 1 vez salvo CON-019 que da 1 hueco):
- CON-009: una oración casi idéntica en la Introducción y en la Discusión.
- CON-018: «Organización Mundial de la Salud (OMS)» definida; la forma completa vuelve 2 veces sin sigla.
- CON-019: rótulos Tabla 1, 2 y 4 (hueco: falta la 3).
- CON-020: dos objetivos específicos; el segundo (mecanismos de compensación fiscal municipal) no tiene rastro, el primero
  (prevalencia del insomnio) sí lo tiene en Resultados y NO debe disparar.
hilo_orden.docx: Tabla 3 se menciona antes que la Tabla 2 (CON-019 por orden de mención).
"""
import os
from pathlib import Path

from docx import Document

DIR = Path(os.path.abspath(__file__)).parent

DUP_A = ("El insomnio crónico en adultos jóvenes se asocia con peor rendimiento laboral, mayor ausentismo y una "
         "percepción deteriorada de la calidad de vida en las ciudades grandes de la región.")
DUP_B = ("El insomnio crónico en adultos jóvenes se asocia con peor rendimiento laboral, mayor ausentismo y una "
         "percepción deteriorada de la calidad de vida en las ciudades grandes del país.")


def tabla(d, num, titulo, filas):
    d.add_paragraph(f"Tabla {num}")
    d.add_paragraph(titulo)
    t = d.add_table(rows=len(filas), cols=2)
    for i, (a, b) in enumerate(filas):
        t.rows[i].cells[0].text, t.rows[i].cells[1].text = a, b
    d.add_paragraph("Nota. Elaboración propia.")


FILAS = [("Grupo", "Porcentaje"), ("A", "40"), ("B", "60")]


def hilo():
    d = Document()
    d.add_heading("Insomnio y desempeño en adultos jóvenes", level=1)
    d.add_heading("Introducción", level=1)
    d.add_paragraph(DUP_A + " Este trabajo estudia el fenómeno en una muestra urbana.")
    d.add_paragraph("La Organización Mundial de la Salud (OMS) reconoce los trastornos del sueño como un problema de salud "
                    "pública creciente en todas las regiones.")
    d.add_heading("Objetivos específicos", level=1)
    d.add_paragraph("Estimar la prevalencia del insomnio en adultos jóvenes.")
    d.add_paragraph("Caracterizar los mecanismos de compensación fiscal municipal.")
    d.add_heading("Método", level=1)
    d.add_paragraph("Se aplicó un cuestionario autoadministrado a una muestra de adultos de entre 18 y 35 años, seleccionados "
                    "en centros de trabajo de tres ciudades. El instrumento midió horas de sueño, latencia y somnolencia "
                    "diurna durante dos semanas consecutivas, con consentimiento informado de cada participante.")
    d.add_paragraph("La Tabla 1 resume la composición de la muestra.")
    tabla(d, 1, "Composición de la muestra", FILAS)
    d.add_heading("Resultados", level=1)
    d.add_paragraph("La prevalencia del insomnio fue elevada entre los adultos jóvenes evaluados y se concentró en quienes "
                    "dormían menos de seis horas. La Tabla 2 presenta la distribución por grupo de edad.")
    tabla(d, 2, "Distribución por grupo de edad", FILAS)
    d.add_paragraph("Según la Organización Mundial de la Salud, la relación es consistente con lo esperado. La Tabla 4 "
                    "detalla la latencia del sueño.")
    tabla(d, 4, "Latencia del sueño", FILAS)
    d.add_paragraph("Los datos de la Organización Mundial de la Salud coinciden con la tendencia observada, y la OMS "
                    "recomienda vigilar el sueño.")
    d.add_heading("Discusión", level=1)
    d.add_paragraph(DUP_B + " Por ello conviene vigilar el sueño en el trabajo.")
    d.add_heading("Conclusiones", level=1)
    d.add_paragraph("El insomnio resultó frecuente en la muestra y se asoció con menor descanso nocturno.")
    d.add_heading("Referencias", level=1)
    d.add_paragraph("Ejemplo, A. (2023). Sueño y trabajo. Editorial Académica.")
    d.save(DIR / "hilo.docx")


def orden():
    d = Document()
    d.add_heading("Sueño y trabajo", level=1)
    d.add_heading("Introducción", level=1)
    d.add_paragraph("Este estudio analiza el sueño de trabajadores en tres centros urbanos. La Tabla 1 describe la muestra.")
    d.add_paragraph("Los promedios finales aparecen en la Tabla 3, y las horas de sueño en la Tabla 2.")
    tabla(d, 1, "Muestra", FILAS)
    tabla(d, 2, "Horas de sueño", FILAS)
    tabla(d, 3, "Promedios finales", FILAS)
    d.add_heading("Referencias", level=1)
    d.add_paragraph("Ejemplo, A. (2023). Sueño y trabajo. Editorial Académica.")
    d.save(DIR / "hilo_orden.docx")


if __name__ == "__main__":
    hilo()
    orden()
    print("escritos", DIR / "hilo.docx", DIR / "hilo_orden.docx")
