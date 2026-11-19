#!/usr/bin/env python3
"""Regresión de la salida en español (es-MX) y su contraparte en inglés de las referencias CSL.

Uso: python -I tests/run_es.py
Fechas con día/mes, rangos, estaciones, comillas/comas y términos de IEEE. Código de salida 0 solo si todo coincide.
"""
import json
import pathlib
import re
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import render  # noqa: E402


def web(i, titulo, fecha, **extra):
    return {"id": i, "type": "webpage", "title": titulo, "author": [{"family": "Pérez", "given": "Ana"}],
            "issued": {"date-parts": fecha}, "container-title": "Sitio", **extra}


FUENTES = [
    web("dia", "Dia", [[2019, 7, 24]], URL="https://e.org/x"),
    web("rango", "Rango", [[2019, 7, 24], [2019, 7, 26]]),
    web("meses", "Meses", [[2019, 7, 24], [2019, 8, 2]]),
    web("mes", "Mes", [[2019, 7]]),
    {"id": "art", "type": "article-journal", "title": "Art", "author": [{"family": "Gómez", "given": "Luis"}],
     "issued": {"date-parts": [[2020, 12]]}, "container-title": "Revista Uno", "volume": "5", "issue": "3", "page": "10-20"},
    {"id": "est", "type": "article-journal", "title": "Est", "author": [{"family": "Lee", "given": "Jo"}],
     "issued": {"season": "2", "date-parts": [[2018]]}, "container-title": "Rev", "volume": "1"},
    {"id": "ponencia", "type": "speech", "title": "Charla", "author": [{"family": "Ruiz", "given": "Eva"}],
     "issued": {"date-parts": [[2021, 3, 5]]}, "event-title": "Congreso"},
]
# (perfil, idioma, id) -> subcadena esperada
ESPERADO = [
    ("apa7", "es-MX", "dia", "(2019, 24 de julio)"),
    ("apa7", "es-MX", "rango", "(2019, 24–26 de julio)"),
    ("apa7", "es-MX", "meses", "(2019, 24 de julio–2 de agosto)"),
    ("apa7", "es-MX", "mes", "(2019, julio)"),
    ("apa7", "es-MX", "est", "(2018, verano)"),
    ("apa7", "es-MX", "art", "(2020). Art."),
    ("apa7", "es-MX", "ponencia", "(2021, 5 de marzo)"),
    ("apa7", "en-US", "dia", "(2019, July 24)"),
    ("apa7", "en-US", "rango", "(2019, July 24–26)"),
    ("apa7", "en-US", "meses", "(2019, July 24–August 2)"),
    ("apa7", "en-US", "mes", "(2019, July)"),
    ("apa7", "en-US", "est", "(2018, Summer)"),
    ("apa7", "en-US", "ponencia", "(2021, March 5)"),
    ("ieee", "es-MX", "dia", "“Dia,” Sitio, 24 jul. 2019."),
    ("ieee", "es-MX", "rango", "24–26 jul. 2019"),
    ("ieee", "es-MX", "meses", "24 jul.–2 ago. 2019"),
    ("ieee", "es-MX", "art", "“Art,” Revista Uno, vol. 5, no. 3, pp. 10–20, dic. 2020."),
    ("ieee", "es-MX", "est", "vol. 1, verano 2018."),
    ("ieee", "es-MX", "ponencia", "“Charla,” presentado en Congreso, 5 mar. 2021."),
    ("ieee", "es-MX", "dia", "[En línea]. Disponible en: https://e.org/x"),
    ("ieee", "en-US", "dia", "“Dia,” Sitio, Jul. 24, 2019. [Online]. Available: https://e.org/x"),
    ("ieee", "en-US", "rango", "Jul. 24–26, 2019"),
    ("ieee", "en-US", "art", "“Art,” Revista Uno, vol. 5, no. 3, pp. 10–20, Dec. 2020."),
    ("ieee", "en-US", "ponencia", "“Charla,” presented at the Congreso, Mar. 5, 2021."),
]
PROHIBIDO = [  # (perfil, idioma, regex): no debe aparecer nunca
    ("apa7", "es-MX", r"\b(julio|marzo|agosto) \d"),
    ("ieee", "es-MX", r"\b(jul|mar|ago|dic)\. \d{1,2},"),
    ("ieee", "es-MX", r"presented|núm\."),  # decisión 18-nov: «no.» como IEEE
]


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    tmp = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
    json.dump(FUENTES, tmp, ensure_ascii=False)
    tmp.close()
    salidas = {}
    for perfil in ("apa7", "ieee"):
        for idioma in ("es-MX", "en-US"):
            for f in FUENTES:
                one = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
                json.dump([f], one, ensure_ascii=False)
                one.close()
                salidas[(perfil, idioma, f["id"])] = " ".join(render.render_refs(one.name, perfil, idioma).split())
    fallas = 0
    for perfil, idioma, i, esp in ESPERADO:
        got = salidas[(perfil, idioma, i)]
        if esp not in got:
            fallas += 1
            print(f"FALLA {perfil} {idioma} {i}: esperado «{esp}» en «{got}»")
    for perfil, idioma, rx in PROHIBIDO:
        for (p, l, i), got in salidas.items():
            if (p, l) == (perfil, idioma) and re.search(rx, got):
                fallas += 1
                print(f"FALLA {p} {l} {i}: aparece /{rx}/ en «{got}»")
    print(f"== es-MX/en-US: {len(ESPERADO)} esperados, {len(PROHIBIDO)} prohibidos, {fallas} fallas")
    sys.exit(1 if fallas else 0)


if __name__ == "__main__":
    main()
