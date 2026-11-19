# -*- coding: utf-8 -*-
"""Genera tests/congruencia/tabla_repite.docx para la regla CON-008 (el texto repite la tabla).
Uso: python -I tests/congruencia/generar_con008.py

Tabla 1 (autor, año, cifra) + párrafo que repite sus filas  -> debe dar 1 CON-008 (Tabla 1).
Tabla 2 (autor, año, cifra) + párrafo que resume la tendencia -> no debe dar CON-008.
"""
import os
from pathlib import Path

from docx import Document

OUT = Path(os.path.abspath(__file__)).parent / "tabla_repite.docx"


def tabla(doc, rotulo, titulo, filas, nota):
    doc.add_paragraph(rotulo)
    doc.add_paragraph(titulo)
    t = doc.add_table(rows=1 + len(filas), cols=3)
    for j, h in enumerate(("Autores", "Año", "Parámetros (miles de millones)")):
        t.rows[0].cells[j].text = h
    for i, f in enumerate(filas, 1):
        for j, v in enumerate(f):
            t.rows[i].cells[j].text = v
    doc.add_paragraph(nota)


F1 = [("Vaswani et al.", "2017", "0.065"), ("Wei et al.", "2021", "137"), ("Ouyang et al.", "2022", "1.3"),
      ("Dettmers et al.", "2023", "65"), ("Zheng et al.", "2024", "48")]
F2 = [("Hernández et al.", "2018", "12"), ("Castro et al.", "2020", "27"), ("Ibarra et al.", "2021", "34"),
      ("Montes et al.", "2022", "58"), ("Paredes et al.", "2023", "71")]


def main():
    d = Document()
    d.add_heading("Antecedentes", level=1)
    d.add_paragraph("La Tabla 1 reúne los modelos de lenguaje que sustentan el proyecto.")
    tabla(d, "Tabla 1", "Modelos de lenguaje previos", F1, "Nota. Elaboración propia.")
    d.add_paragraph("Lectura de la tabla. Vaswani et al. (2017) abrieron el camino con 0.065 mil millones de parámetros; "
                    "después Wei et al. (2021) llegaron a 137 y Ouyang et al. (2022) a 1.3, mientras que Dettmers et al. (2023) "
                    "ajustaron un modelo de 65 y Zheng et al. (2024) uno de 48 mil millones.")
    d.add_paragraph("La Tabla 2 compara los trabajos que midieron el costo de adaptación.")
    tabla(d, "Tabla 2", "Trabajos sobre costo de adaptación", F2, "Nota. Elaboración propia.")
    d.add_paragraph("La tabla muestra que los métodos de adaptación reducen el costo con el tiempo, y que el tamaño de los "
                    "modelos adaptados crece de forma sostenida en todos los trabajos revisados.")
    d.save(OUT)
    print("escrito", OUT)


if __name__ == "__main__":
    main()
