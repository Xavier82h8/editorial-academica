#!/usr/bin/env python3
"""Compara el juez determinista con una verdad esperada de un borrador de estudiante.

Uso: python -I tests/run_real.py
Por defecto usa el borrador SINTÉTICO (tests/reales/boceto_sintetico.json + crear_boceto_sintetico.py, que genera el
.docx en un temporal: tema, autores y fuentes inventados). Si existe tests/reales/privado/ (ignorada por git) con
`*.json` de revisión experta de un documento real, los evalúa además (cada json declara la ruta de su .docx; si el
documento no está en esta máquina, se omite con aviso).

Mide:
- recall sobre los IDs «seguro» y mecánicos de la verdad esperada (puerta: >= 0.90);
- recall sobre todos los IDs «seguro» (informativo: incluye reglas de juicio que el script no cubre);
- falsos positivos: IDs que el juez reporta y que la verdad marca como CUMPLE (puerta: 0).
Salida 0 si se cumplen ambas puertas; 1 si alguna falla.
"""
import json
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests" / "reales"))
import auditar  # noqa: E402
import crear_boceto_sintetico  # noqa: E402

REALES = ROOT / "tests" / "reales"
SINTETICO = REALES / "boceto_sintetico.json"
UMBRAL_RECALL = 0.90


def evaluar(exp, doc, etiqueta):
    """Imprime el informe de un documento frente a su verdad esperada; devuelve True si pasa las dos puertas."""
    r = auditar.auditar(str(doc), exp["perfil"])
    got = {h["id"] for h in r["hallazgos"]}
    seguro = {h["id"] for h in exp["hallazgos"] if h["certeza"] == "seguro"}
    seguro_mec = {h["id"] for h in exp["hallazgos"] if h["certeza"] == "seguro" and h["mecanica"]}
    cumple = set(exp["cumple"])
    fp = sorted(got & cumple)
    nuevos = sorted(got - {h["id"] for h in exp["hallazgos"]} - cumple)
    rec_mec = len(got & seguro_mec) / len(seguro_mec) if seguro_mec else 1.0
    rec_seg = len(got & seguro) / len(seguro) if seguro else 1.0
    print(f"{etiqueta}documento: {doc.name}   hallazgos del juez: {len(r['hallazgos'])} ({len(got)} IDs distintos)")
    print(f"recall seguro+mecánico = {rec_mec:.2f} ({len(got & seguro_mec)}/{len(seguro_mec)})   omitidos: {sorted(seguro_mec - got)}")
    print(f"recall seguro (todos)  = {rec_seg:.2f} ({len(got & seguro)}/{len(seguro)})   omitidos (juicio, no mecánicos): {sorted(seguro - got)}")
    print(f"falsos positivos sobre IDs que cumplen = {len(fp)} {fp}")
    print(f"IDs del juez que la verdad no lista (revisar a mano): {nuevos}")
    ok = rec_mec >= UMBRAL_RECALL and not fp
    print(f"recall mecánico seguro >= {UMBRAL_RECALL:.2f} y 0 falsos positivos: {'OK' if ok else 'FALLA'}")
    return ok


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    exp = json.loads(SINTETICO.read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory() as tmp:
        doc = crear_boceto_sintetico.crear(pathlib.Path(tmp) / "boceto_sintetico.docx")
        ok = evaluar(exp, doc, "")
    privado = REALES / "privado"
    for f in sorted(privado.glob("*.json")) if privado.is_dir() else []:
        exp_p = json.loads(f.read_text(encoding="utf-8"))
        doc_p = pathlib.Path(exp_p["documento"])
        print(f"\n[privado] {f.name}")
        if not doc_p.exists():
            print(f"AVISO: no existe {doc_p}; prueba privada omitida")
            continue
        ok &= evaluar(exp_p, doc_p, "[privado] ")
    print(f"\n{'OK' if ok else 'FALLA'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
