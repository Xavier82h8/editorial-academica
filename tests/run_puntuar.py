#!/usr/bin/env python3
"""Regresión de /puntuar: estable (3 corridas, mismo total) y sensible (quitar Conclusiones baja el puntaje).

Uso: python -I tests/run_puntuar.py [--sin-red]   (o EDITORIAL_SIN_RED=1: solo la caché HTTP del usuario; run_todo --sin-red
la siembra desde tests/fixtures/http)

Usa tests/estructura/informe_ok.md e informe_sin_conclusiones.md con tests/estructura/fuentes.json.
"""
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import puntuar  # noqa: E402

D = ROOT / "tests" / "estructura"


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    fu = str(D / "fuentes.json")
    sin_red = "--sin-red" in sys.argv or os.environ.get("EDITORIAL_SIN_RED") == "1"
    tot = [puntuar.puntuar(str(D / "informe_ok.md"), "apa7-base+ieee-citas", "informe", fu, sin_red=sin_red)["total"] for _ in range(3)]
    peor = puntuar.puntuar(str(D / "informe_sin_conclusiones.md"), "apa7-base+ieee-citas", "informe", fu, sin_red=sin_red)["total"]
    ok = max(tot) - min(tot) <= 2 and peor < min(tot) and min(tot) >= 85
    print(("OK " if ok else "FALLA ") + f"== puntuar: corridas {tot}, sin conclusiones {peor}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
