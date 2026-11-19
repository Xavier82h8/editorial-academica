#!/usr/bin/env python3
"""Compara la salida CSL (pandoc citeproc) con los ejemplos oficiales del corpus dorado.

Uso: python -I tests/run_csl.py [apa7|ieee ...] [--idioma en-US] [--detalle]
Reporta, por caso: IGUAL (con cursivas), IGUAL-TEXTO (solo difieren las cursivas) o DIFIERE (con diff).
Código de salida 0 solo si todos son IGUAL.
"""
import difflib
import json
import pathlib
import re
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import render  # noqa: E402

PERFIL = {"apa7": "apa7", "ieee": "ieee"}


def norm(s, cursivas=True):
    s = "\n".join(l for l in s.split("\n") if not l.lstrip().startswith(":::"))  # divs de pandoc
    s = s.replace("---", "—").replace("--", "–")  # guiones "smart"
    s = s.replace("\\", "").replace(" ", " ").replace(" ", " ")
    s = re.sub(r"<(/?)span[^>]*>", "", s)
    s = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", r"\1", s)  # enlaces markdown: queda el texto
    s = re.sub(r"\[\[\d+\]\s*\]\{\.csl-left-margin\}", "", s)  # numero IEEE en columna
    s = re.sub(r"\[(.*)\]\{\.csl-right-inline\}", lambda m: m.group(1), s, flags=re.S)  # envoltorio IEEE (puede contener [Online])
    previo = None
    while previo != s:  # spans de pandoc: [texto]{.nocase} {.csl-right-inline} {.smallcaps}
        previo, s = s, re.sub(r"\[([^\[\]]*)\]\{[^}]*\}", r"\1", s)
    s = re.sub(r"<(https?://[^>]+)>", r"\1", s)
    s = s.replace("_", "*") if cursivas else s.replace("*", "").replace("_", "")
    s = re.sub(r"^\[\d+\]\s*", "", s.strip())                  # número IEEE
    s = re.sub(r"[‘’'“”\"]", "'", s)  # comillas: pandoc "smart" las cambia
    s = s.replace("“", '"').replace("”", '"').replace("’", "'").replace("‘", "'")
    return re.sub(r"\s+", " ", s).strip()


def render_uno(item, perfil, idioma):
    tmp = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
    it = dict(item)
    it.setdefault("id", "x")
    json.dump([it], tmp, ensure_ascii=False)
    tmp.close()
    out = render.render_refs(tmp.name, perfil, idioma, fmt="markdown")
    return out.strip()


def correr(norma, idioma, detalle):
    casos = json.loads((ROOT / "tests/corpus" / norma / "referencias.json").read_text(encoding="utf-8"))
    res = {"IGUAL": 0, "IGUAL-TEXTO": 0, "DIFIERE": 0, "ERROR": 0}
    filas = []
    for c in casos:
        if c.get("alcance") or c.get("comparable") is False:
            continue  # plantillas parciales y ejemplos con formato antiguo de la guía: no comparables
        try:
            got = render_uno(c["csl"], PERFIL[norma], idioma)
        except Exception as e:  # noqa: BLE001
            res["ERROR"] += 1
            filas.append((c["id"], "ERROR", str(e)[:200]))
            continue
        esp = c.get("esperado_corregido", c["esperado"])  # erratas del ejemplo oficial
        if norm(got) == norm(esp):
            r = "IGUAL"
        elif norm(got, False) == norm(esp, False):
            r = "IGUAL-TEXTO"
        else:
            r = "DIFIERE"
        res[r] += 1
        d = ""
        if r != "IGUAL" and detalle:
            a, b = norm(esp, r == "IGUAL-TEXTO"), norm(got, r == "IGUAL-TEXTO")
            sm = difflib.SequenceMatcher(None, a, b)
            d = " | ".join(f"{op}: '{a[i1:i2]}' -> '{b[j1:j2]}'"
                           for op, i1, i2, j1, j2 in sm.get_opcodes() if op != "equal")[:400]
        filas.append((c["id"], r, d or c.get("tipo", "")))
    return res, filas


def main():
    args = [x for x in sys.argv[1:] if not x.startswith("--")]
    idioma = "en-US"
    if "--idioma" in sys.argv:
        idioma = sys.argv[sys.argv.index("--idioma") + 1]
        args = [x for x in args if x != idioma]
    detalle = "--detalle" in sys.argv
    sys.stdout.reconfigure(encoding="utf-8")
    ok = True
    reporte = []
    for norma in args or ["apa7", "ieee"]:
        res, filas = correr(norma, idioma, detalle)
        total = sum(res.values())
        print(f"\n== {norma} ({idioma}): {res}  exactos {res['IGUAL']}/{total}")
        for f in filas:
            if f[1] != "IGUAL":
                print(f"  {f[0]:<14} {f[1]:<12} {f[2]}")
        reporte.append({"norma": norma, "idioma": idioma, **res, "casos": filas})
        ok &= res["IGUAL"] == total
    (ROOT / "tests/resultados").mkdir(exist_ok=True)
    (ROOT / "tests/resultados/csl.json").write_text(json.dumps(reporte, ensure_ascii=False, indent=1), encoding="utf-8")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
