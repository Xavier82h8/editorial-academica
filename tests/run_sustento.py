#!/usr/bin/env python3
"""Regresión de V5 determinista (scripts/afirmaciones.py) sobre tests/sustento/sembrado.md.

Las 3 oraciones con cifra falsa deben marcarse (cifras_sin_respaldo) y ninguna otra.
Si existe tests/sustento/evidencias.json (salida del agente verificador-afirmaciones), informa además
cuántos veredictos coinciden con esperado.json (respaldada frente a no respaldada); puerta del agente: >= 8/10.
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import afirmaciones  # noqa: E402

D = ROOT / "tests" / "sustento"


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    fu = json.loads((D / "fuentes.json").read_text(encoding="utf-8"))
    esp = json.loads((D / "esperado.json").read_text(encoding="utf-8"))
    res = afirmaciones.extraer((D / "sembrado.md").read_text(encoding="utf-8"), fu)
    marcadas = {r["n"] for r in res if r["cifras_sin_respaldo"]}
    deben = {e["n"] for e in esp if e["cifra_falsa"]}
    ok = len(res) == len(esp) and marcadas == deben
    det = f"cifras: {len(marcadas & deben)}/{len(deben)} detectadas, {len(marcadas - deben)} falsos positivos"
    ev = D / "evidencias.json"
    if ev.exists():
        v = {e["n"]: e["veredicto"] for e in json.loads(ev.read_text(encoding="utf-8"))}
        aciertos = sum((v.get(e["n"]) == "respaldada") == (e["esperado"] == "respaldada") for e in esp)
        det += f"; agente: {aciertos}/{len(esp)}"
        ok &= aciertos >= 8
    print(("OK " if ok else "FALLA ") + det)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
