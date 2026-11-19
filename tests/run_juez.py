#!/usr/bin/env python3
"""Mide precisión y recall del juez determinista sobre tests/docs (errores sembrados).

Uso: python -I tests/run_juez.py [--dir tests/ciegos/docs]   (sin --dir regenera tests/docs)
Puerta fase 2: recall >= 0.95 y precisión >= 0.95; 0 hallazgos en *_correcto.docx.
"""
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import auditar  # noqa: E402

DOCS = ROOT / "tests" / "docs"


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    docs = DOCS
    if "--dir" in sys.argv:
        docs = pathlib.Path(sys.argv[sys.argv.index("--dir") + 1]).resolve()
    else:
        subprocess.run([sys.executable, "-I", str(ROOT / "tests" / "generar_docs.py")], check=True, capture_output=True)
    esperado = json.loads((docs / "esperado.json").read_text(encoding="utf-8"))
    tp = fp = fn = 0
    ok = True
    for nombre, info in esperado.items():
        r = auditar.auditar(str(docs / nombre), info["perfil"])
        got = sorted({h["id"] for h in r["hallazgos"]})
        exp = sorted({e["id"] for e in info["errores"]})
        t = len(set(got) & set(exp))
        f_p = sorted(set(got) - set(exp))
        f_n = sorted(set(exp) - set(got))
        tp, fp, fn = tp + t, fp + len(f_p), fn + len(f_n)
        estado = "OK" if not f_p and not f_n else "FALLA"
        ok &= estado == "OK"
        print(f"{nombre:<22} {estado:<5} esperados={len(exp)} detectados={t} falsos+={f_p} omitidos={f_n}")
        for h in r["hallazgos"]:
            if h["id"] in f_p:
                print(f"    FP {h['id']}: {h['evidencia']}")
        for e in info["errores"]:
            if e["id"] in f_n:
                print(f"    FN {e['id']}: {e['desc']}")
    prec = tp / (tp + fp) if tp + fp else 1.0
    rec = tp / (tp + fn) if tp + fn else 1.0
    print(f"\nprecisión={prec:.2f} recall={rec:.2f} (puerta: ambos >= 0.95)")
    sys.exit(0 if prec >= 0.95 and rec >= 0.95 else 1)


if __name__ == "__main__":
    main()
