#!/usr/bin/env python3
"""Despachador único de editorial-academica: una sola ruta para todos los comandos, en cualquier sistema operativo.

Uso:
  python scripts/editorial.py <subcomando> [argumentos…]
  python scripts/editorial.py --help | --version

Funciona desde cualquier directorio, con `python` o `python -I` (resuelve su propia carpeta; no depende del cwd).
Cada subcomando es el script correspondiente (`<subcomando> --help` muestra sus opciones). Convención común (ver cli.py):
`--perfil` (por defecto el de .editorial.yaml), `--json RUTA`, y códigos de salida 0 sin hallazgos, 1 con hallazgos
críticos o mayores, 2 error de uso o de entrada.
"""
import json
import pathlib
import runpy
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
FUENTES = ROOT / "skills" / "fuentes-academicas" / "scripts" / "fuentes.py"

# subcomando -> (script, descripción de una línea)
COMANDOS = {
    "auditar": (HERE / "auditar.py", "juez determinista de formato, citas y referencias (APA 7, IEEE o combinado)"),
    "corregir": (HERE / "corregir.py", "corrige el formato mecánico de un .docx sin tocar el original"),
    "puntuar": (HERE / "puntuar.py", "puntaje editorial 0-100 con las 5 correcciones de mayor impacto e historial"),
    "estructura": (HERE / "estructura.py", "secciones que exige el género (tesis, informe, IMRyD…) y maquetación EST-010..017"),
    "congruencia": (HERE / "congruencia.py", "congruencia interna: objetivos, método, resultados, cifras, siglas, referencias cruzadas"),
    "maquetacion": (HERE / "maquetacion.py", "paginación, portada, tablas y figuras de un .docx"),
    "afirmaciones": (HERE / "afirmaciones.py", "sustento V5: cifras de cada afirmación citada frente al resumen de su fuente"),
    "fuentes": (FUENTES, "busca y verifica fuentes académicas (OpenAlex, Crossref); genera fuentes.json"),
    "convertir": (HERE / "convertir.py", "convierte un .docx con citas a mano a otro perfil (APA 7, IEEE, combinado)"),
    "modelo": (HERE / "modelo_formato.py", "mide un modelo de formato (PDF o .docx) y lo compara con un documento (formato vinculante, INS-015)"),
    "titulo": (HERE / "titulo.py", "título concreto: diagnóstico del título de portada frente al objetivo general (CON-021, INS-010)"),
    "repasar": (HERE / "repasar.py", "modo de estudio por capítulo (qué pide la guía, qué tiene el documento, preguntas guía); no califica"),
    "portada": (HERE / "portada.py", "construye la portada institucional desde el perfil y el modelo vinculante (INS-010, INS-015)"),
    "indices": (HERE / "indices.py", "índice de contenido, de tablas y de figuras con páginas medidas en el PDF (LibreOffice)"),
    "entregar": (HERE / "entregar.py", "corregir, portada, índices, PDF, capturas y auditoría: deja .entrega.docx y .entrega.pdf juntos"),
    "medir": (HERE / "medir.py", "ficha técnica de medidas efectivas (márgenes, sangría, interlineado, fuente, número de página) en .docx y PDF; reglas del usuario medibles (INS-016)"),
    "comparar": (HERE / "fidelidad.py", "compara el texto (y resume el formato) de un original con su versión corregida: certificado de fidelidad"),
    "calificar": (HERE / "calificar.py", "califica sin tocar nada: auditar + estructura + congruencia + puntuar + medir en una corrida (solo lectura, con hash)"),
    "perfilar": (HERE / "perfilar.py", "la guía de tu escuela (PDF o .docx) se convierte en reglas: .editorial.yaml + estructura, cada valor con su cita de origen"),
    "render": (HERE / "render.py", "renderiza Markdown con marcas [@id] a docx, pdf, latex, html o md según un perfil"),
}


def version():
    try:
        return json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")).get("version", "desconocida")
    except (OSError, ValueError):
        return "desconocida"


def ayuda():
    filas = "\n".join(f"  {n:<14}{d}" for n, (_, d) in COMANDOS.items())
    return (f"editorial-academica {version()}: juez editorial APA 7 / IEEE\n\n"
            "Uso: python scripts/editorial.py <subcomando> [argumentos…]\n\n"
            f"Subcomandos:\n{filas}\n\n"
            "`<subcomando> --help` muestra las opciones de cada uno. `--version` imprime la versión.\n"
            "Salida: 0 sin hallazgos, 1 con hallazgos críticos o mayores, 2 error de uso o de entrada.")


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    for flujo in (sys.stdout, sys.stderr):
        try:
            flujo.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(ayuda())
        return 0 if argv else 2
    if argv[0] in ("--version", "-V"):
        print(f"editorial-academica {version()}")
        return 0
    cmd = argv[0]
    if cmd not in COMANDOS:
        print(f"subcomando desconocido: {cmd}. Subcomandos: {', '.join(COMANDOS)} (usa --help)", file=sys.stderr)
        return 2
    ruta = COMANDOS[cmd][0]
    sys.path.insert(0, str(HERE))
    sys.argv = [f"editorial {cmd}", *argv[1:]]
    runpy.run_path(str(ruta), run_name="__main__")  # SystemExit(código) del script se propaga tal cual
    return 0


if __name__ == "__main__":
    sys.exit(main())
