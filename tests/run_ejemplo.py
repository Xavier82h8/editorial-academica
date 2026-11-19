#!/usr/bin/env python3
"""El ejemplo del README no miente: regenera ejemplos/ en una carpeta temporal y comprueba, sin red, las cifras que
ejemplos/README.md y README.md publican.

- original: auditar 3 críticas / 16 mayores / 5 menores; congruencia 4 (CON-001, 007, 008, 020); maquetación 4
- corregir: 28 -> 9 hallazgos, sin hallazgos nuevos
- final (tras revisar_contenido.py): 0 hallazgos en auditar, congruencia y maquetación
- los .docx versionados en ejemplos/ coinciden con los regenerados (mismo texto)
Salida: 0 todo cuadra; 1 alguna cifra cambió (actualiza los README o corrige la regresión).
"""
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
EJ = ROOT / "ejemplos"
sys.path.insert(0, str(ROOT / "scripts"))


def correr(*args):
    r = subprocess.run([sys.executable, *map(str, args)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.returncode, r.stdout + r.stderr


def conteo(salida):
    import ast
    import re
    m = re.search(r"\{'crítica': \d+, 'mayor': \d+, 'menor': \d+\}", salida)
    return ast.literal_eval(m.group(0)) if m else None


def texto(path):
    import docx
    d = docx.Document(str(path))
    return [p.text for p in d.paragraphs] + [c.text for t in d.tables for r in t.rows for c in r.cells]


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    fallas = []
    ed = ROOT / "scripts" / "editorial.py"
    with tempfile.TemporaryDirectory() as tmp:
        tmp = pathlib.Path(tmp)
        orig, corr, fin = tmp / "informe-ejemplo.docx", tmp / "informe-ejemplo.corregido.docx", tmp / "informe-ejemplo.final.docx"
        correr(EJ / "crear_ejemplo.py", orig)
        _, out = correr(ed, "auditar", orig, "--perfil", "apa7")
        if conteo(out) != {"crítica": 3, "mayor": 16, "menor": 5}:
            fallas.append(f"auditar original: {conteo(out)} (README: 3/16/5)")
        _, out = correr(ed, "congruencia", orig)
        ids = sorted(set(__import__("re").findall(r"\| (CON-\d+) \|", out)))
        if ids != ["CON-001", "CON-007", "CON-008", "CON-020"]:
            fallas.append(f"congruencia original: {ids}")
        _, out = correr(ed, "estructura", orig, "--estructura", "informe", "--perfil", "apa7")
        if "MAQUETACIÓN: 4 hallazgos" not in out:
            fallas.append("maquetación original: no son 4 hallazgos")
        _, out = correr(ed, "corregir", orig, "--perfil", "apa7", "--paginacion", "encabezado", "--portada-numero", "si")
        if "TOTAL: 28 -> 9" not in out:
            fallas.append("corregir: " + next((l.strip() for l in out.splitlines() if "TOTAL" in l), "sin TOTAL"))
        correr(EJ / "revisar_contenido.py", corr, fin)
        for sub, extra in (("auditar", ["--perfil", "apa7"]), ("congruencia", []),
                           ("estructura", ["--estructura", "informe", "--perfil", "apa7"])):
            _, out = correr(ed, sub, fin, *extra)
            c = conteo(out)
            if (c is not None and any(c.values())) or (sub == "estructura" and "MAQUETACIÓN: 0 hallazgos" not in out):
                fallas.append(f"final {sub}: {c}")
        for f in (orig, corr, fin):
            versionado = EJ / f.name
            if not versionado.exists():
                fallas.append(f"falta {versionado.relative_to(ROOT)}")
            elif texto(versionado) != texto(f):
                fallas.append(f"{versionado.relative_to(ROOT)} no coincide con lo regenerado: python ejemplos/crear_ejemplo.py y la cadena de ejemplos/README.md")
    print("== ejemplo: original 3/16/5, congruencia 4, maquetación 4, corregir 28 -> 9, final 0 hallazgos")
    for f in fallas:
        print("FALLO:", f)
    print("OK: 0 fallas" if not fallas else f"{len(fallas)} fallas")
    sys.exit(1 if fallas else 0)


if __name__ == "__main__":
    main()
