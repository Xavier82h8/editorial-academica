#!/usr/bin/env python3
"""Reglas APA finas de la tanda 1 (APA-015/039/041/044/063/066): casos que deben saltar y casos que no.

Uso: python -I tests/run_reglas_apa.py
- 0 hallazgos de estas reglas en las 83 referencias oficiales de tests/corpus/apa7 (formas de fecha, autores grupales, 20+ autores).
- Cada caso sembrado dispara exactamente su regla; cada caso limpio, ninguna (formas en español incluidas).
APA-024 y APA-031 (encabezados) se prueban en tests/generar_docs.py (necesitan estilos de Word).
"""
import json
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import auditar  # noqa: E402

REGLAS = {"APA-015", "APA-039", "APA-041", "APA-044", "APA-063", "APA-066"}

REFS_OK = [
    "Pérez, A., & Gil, B. (2020, 24 de julio). Título. *Revista*, *3*(2), 1–2.",
    "Reyes, T. (2020, July 24). Title. Publisher.",
    "Reyes, T. (n.d.). Title. Publisher.",
    "García, L. (s. f.). Título. Editorial.",
    "García, L. (en prensa). Título. Editorial.",
    "Lee, K. (in press). Title. *Journal*.",
    "Mera, P. (2019, 24–26 de julio). Título. Sitio.",
    "Ríos, A., Soto, M., & Vera, L. (2021). Título. Editorial.",
    "Ríos, A., Soto, M. y Vera, L. (2021). Título. Editorial.",
    "Organización Mundial de la Salud. (2021). *Informe*. https://who.int",
    "U.S. Census Bureau. (2020). *Population*. Department.",
    "Smith, J. (2020a). Uno. Editorial.", "Smith, J. (2020b). Dos. Editorial.",
    "Smith, J. (n.d.-a). Uno. Editorial.", "Smith, J. (n.d.-b). Dos. Editorial.",
    "Smith, J., & Lee, K. (2020). Uno. Editorial.", "Smith, J., & Wu, T. (2020). Dos. Editorial.",
    "Kübler-Ross, E. (with Byock, I.). (2014). *On death*. Scribner.",
]
# (regla, entrada o entradas que deben dispararla)
REFS_MAL = [
    ("APA-066", ["Pérez, A. (2020) Título. Editorial."]),
    ("APA-066", ["Pérez, A. (2020), Título. Editorial."]),
    ("APA-066", ["Pérez, A. 2020. Título. Editorial."]),
    ("APA-066", ["Pérez, A. (24 de julio de 2020). Título. Editorial."]),
    ("APA-066", ["Smith, J. (July 24, 2020). Title. Publisher."]),
    ("APA-063", ["Ríos, A., Soto, M., Vera, L. (2021). Título. Editorial."]),
    ("APA-063", ["Ríos, A., Soto, M. (2021). Título. Editorial."]),
    ("APA-063", ["A. Ríos, M. Soto, & L. Vera. (2021). Título. Editorial."]),
    ("APA-044", ["Smith, J. (2020). Uno. Editorial.", "Smith, J. (2020). Dos. Editorial."]),
    ("APA-044", ["Smith, J. (n.d.). Uno. Editorial.", "Smith, J. (n.d.). Dos. Editorial."]),
    ("APA-044", ["Smith, J. (2020a). Uno. Editorial.", "Smith, J. (2020). Dos. Editorial."]),
]
CITAS_OK = [
    "Según Pérez (2020), el efecto es claro (Gil & Soto, 2019; Ríos et al., 2021).",
    "El efecto es claro (Gil, s. f.) y confirmado (Gil, n.d.).",
    "El efecto es claro (J. Pérez, comunicación personal, 3 de marzo de 2020) y (J. Smith, personal communication, March 3, 2020).",
    "Según Ríos et al. (2021) y Smith y Lee (2020), el efecto es claro.",
    "El 24 de julio de 2020, Pérez (2020) publicó el estudio (Pérez, 2020, p. 4).",
]
CITAS_MAL = [
    ("APA-041", "El efecto es claro (Pérez, 2020, 24 de julio) en la muestra."),
    ("APA-041", "El efecto es claro (Smith, March 3, 2020) en la muestra."),
    ("APA-041", "El efecto es claro (Pérez, 24 de julio de 2020) en la muestra."),
    ("APA-041", "Según Pérez (2020, 24 de julio) el efecto es claro."),
    ("APA-041", "Según Pérez (24 de julio de 2020) el efecto es claro."),
    ("APA-041", "El efecto es claro (Pérez, sin fecha) en la muestra."),
    ("APA-041", "El efecto es claro (Pérez, S/F) en la muestra."),
    ("APA-039", "Según Smith et al. (2020) el efecto es claro."),
    ("APA-039", "El efecto es claro (Smith et al., 2020)."),
]
LISTA_CITAS = ["Smith, J., & Lee, K. (2020). Uno. Editorial.", "Ríos, A., Soto, M., & Vera, L. (2021). Dos. Editorial.",
               "Pérez, A. (2020, July 24). Tres. Editorial.", "Gil, B., & Soto, C. (2019). Cuatro. Editorial.",
               "Gil, B. (n.d.). Cinco. Editorial."]
APENDICES = [  # (regla esperada o None, documento md)
    (None, "Texto (véase el Apéndice A y el Apéndice B).\n\n# Referencias\n\nSmith, J. (2020). Uno. Editorial.\n\n# Apéndice A\n\nx\n\n# Apéndice B\n\ny"),
    (None, "Texto (véanse los Apéndices A y B).\n\n# Referencias\n\nSmith, J. (2020). Uno. Editorial.\n\n# Apéndice A\n\nx\n\n# Apéndice B\n\ny"),
    (None, "Texto (véase el Apéndice).\n\n# Referencias\n\nSmith, J. (2020). Uno. Editorial.\n\n# Apéndice\n\nx"),
    ("APA-015", "Texto (véase el Apéndice A).\n\n# Referencias\n\nSmith, J. (2020). Uno. Editorial.\n\n# Apéndice A\n\nx\n\n# Apéndice B\n\ny"),
    ("APA-015", "Texto sin menciones.\n\n# Referencias\n\nSmith, J. (2020). Uno. Editorial.\n\n# Apéndice\n\nx"),
    ("APA-015", "Véase el Apéndice B y luego el Apéndice A.\n\n# Referencias\n\nSmith, J. (2020). Uno. Editorial.\n\n# Apéndice A\n\nx\n\n# Apéndice B\n\ny"),
]


def ids(h):
    return {x["id"] for x in h} & REGLAS


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    fallas = []
    corpus = json.loads((ROOT / "tests/corpus/apa7/referencias.json").read_text(encoding="utf-8"))
    ents = [{"texto": c["esperado"].replace("*", ""), "i": i} for i, c in enumerate(corpus)]
    for h in auditar.referencias_apa(ents):
        fallas.append(f"FP corpus {h['id']}: {h['evidencia']}")
    for t in REFS_OK:
        got = ids(auditar.referencias_apa([{"texto": t, "i": 0}]))
        if got:
            fallas.append(f"FP {sorted(got)} en «{t}»")
    ok_juntas = [{"texto": t, "i": i} for i, t in enumerate(REFS_OK)]
    if ids(auditar.referencias_apa(ok_juntas)):
        fallas.append(f"FP en el conjunto limpio: {ids(auditar.referencias_apa(ok_juntas))}")
    for regla, lista in REFS_MAL:
        got = ids(auditar.referencias_apa([{"texto": t, "i": i} for i, t in enumerate(lista)]))
        if got != {regla}:
            fallas.append(f"{regla}: se esperaba solo {regla}, salió {sorted(got)} para «{lista[0]}»")
    entradas = [{"texto": t, "i": i} for i, t in enumerate(LISTA_CITAS)]
    for t in CITAS_OK:
        p = [{"texto": t, "i": 0}]
        got = ids(auditar.citas_fecha_apa(p) + auditar.citas_et_al_apa(p, entradas))
        if got:
            fallas.append(f"FP {sorted(got)} en «{t}»")
    for regla, t in CITAS_MAL:
        p = [{"texto": t, "i": 0}]
        got = ids(auditar.citas_fecha_apa(p) + auditar.citas_et_al_apa(p, entradas))
        if got != {regla}:
            fallas.append(f"{regla}: salió {sorted(got)} para «{t}»")
    with tempfile.TemporaryDirectory() as tmp:
        for k, (regla, md) in enumerate(APENDICES):
            f = pathlib.Path(tmp) / f"ap{k}.md"
            f.write_text(md, encoding="utf-8")
            got = ids(auditar.auditar(str(f), "apa7")["hallazgos"])
            if got != ({regla} if regla else set()):
                fallas.append(f"apéndices caso {k}: se esperaba {regla}, salió {sorted(got)}")
    for f in fallas:
        print("FALLA", f)
    n = len(corpus) + len(REFS_OK) + len(REFS_MAL) + len(CITAS_OK) + len(CITAS_MAL) + len(APENDICES)
    print(f"== reglas APA tanda 1: {n} casos, {len(fallas)} fallas")
    sys.exit(1 if fallas else 0)


if __name__ == "__main__":
    main()
