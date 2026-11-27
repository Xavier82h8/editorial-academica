"""Regenera las rondas ciegas que no se versionan (docs, docs2, docs3).

Sus .docx se construyen con las plantillas generadas desde el reference.docx de pandoc del usuario, que no se
distribuye con el repositorio (ver NOTICE); por eso se crean al vuelo la primera vez que una prueba las necesita."""
import pathlib
import subprocess
import sys

AQUI = pathlib.Path(__file__).resolve().parent
RONDAS = {"docs": "generar.py", "docs2": "generar2.py", "docs3": "generar3.py"}


def asegurar(*carpetas):
    for carpeta in carpetas or RONDAS:
        esperado = AQUI / carpeta / "esperado.json"
        # también si el generador cambió después de la última generación (esperado.json viejo = falsos fallos)
        if not esperado.exists() or (AQUI / RONDAS[carpeta]).stat().st_mtime > esperado.stat().st_mtime:
            subprocess.run([sys.executable, "-I", str(AQUI / RONDAS[carpeta])], check=True, capture_output=True,
                           cwd=AQUI.parent.parent)
    return AQUI


if __name__ == "__main__":
    asegurar(*sys.argv[1:])
