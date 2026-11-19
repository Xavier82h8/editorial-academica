#!/usr/bin/env python3
"""Compara las citas en el texto (pandoc citeproc) con los ejemplos oficiales de tests/corpus/*/citas.json.

Uso: python -I tests/run_citas.py [apa7|ieee ...]
Resultados: IGUAL, DIFIERE, ERROR o MANUAL (casos que CSL no puede generar: abreviatura de autor
grupal, comunicación personal; los escribe el redactor a mano y los revisa el juez).
Código de salida 0 si no hay DIFIERE ni ERROR.
"""
import json
import pathlib
import re
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))
import render  # noqa: E402
from run_csl import norm  # noqa: E402

A, B = "QQINI", "QQFIN"


def pandoc_plain(md, items, perfil):
    cfg = render.perfil(perfil)
    tmp = pathlib.Path(tempfile.mkdtemp())
    (tmp / "f.json").write_text(json.dumps(items, ensure_ascii=False), encoding="utf-8")
    fuentes = render.limpiar_fuentes(str(tmp / "f.json"))
    (tmp / "d.md").write_text(md, encoding="utf-8")
    args = [render.pandoc(), str(tmp / "d.md"), "-t", "plain", "--wrap=none",
            *render.args_comunes(cfg, fuentes, "en-US"), "-M", "suppress-bibliography=true"]
    return subprocess.run(args, capture_output=True, text=True, encoding="utf-8", check=True).stdout


def extraer(salida):
    m = re.findall(A + r"\s*(.*?)\s*" + B, salida, flags=re.S)
    return m[-1].strip() if m else salida.strip()


ETIQUETAS = {"page": "p. ", "paragraph": "para. ", "chapter": "chapter ", "figure": "fig. "}


def clave(it):
    """Item del corpus -> (prefijo, resto) en sintaxis pandoc. Convención del redactor:
    etiquetas CSL reconocidas (p., para., chapter, fig.); cualquier otro localizador entre llaves
    ({Table 3}, {2:12}, {Thm. 1}) para que pandoc no lo convierta en "p."."""
    loc, lab = it.get("locator") or "", it.get("label") or ""
    suf = it.get("suffix") or ""
    pre = (it.get("prefix") or "").replace(";", r"\;")
    if loc:
        resto = ", " + (ETIQUETAS[lab] + loc if lab in ETIQUETAS else "{" + (lab.capitalize() + " " if lab else "") + loc + "}")
    elif suf[:2] == ", " and suf[2:3].isdigit():
        resto, suf = ", {" + suf[2:] + "}", ""
    else:
        resto = ""
    if suf and not suf.startswith(","):
        suf = "," + suf
    return pre, resto + suf


def resolver_apa(c, refs):
    for it in c["items"]:
        if "ref" in it and "csl" not in it:
            it["csl"] = dict(refs[it["ref"]], id=it["ref"])


def cita_apa(c):
    if not c["items"] or c.get("abreviatura"):
        return None
    partes = []
    for it in c["items"]:
        pre, suf = clave(it)
        partes.append(f"{pre}@{it['csl']['id']}{suf}")
    if c["modo"] == "parentetica":
        return "[" + "; ".join(partes) + "]"
    if len(c["items"]) == 1:
        pre, suf = clave(c["items"][0])
        return f"@{c['items'][0]['csl']['id']}" + (f" [{suf.lstrip(', ')}]" if suf else "")
    if c["esperado"].count("(") > 1:  # narrativa de varios autores: "A (2019), B (2025), and C (2022)"
        ids = ["@" + it["csl"]["id"] for it in c["items"]]
        return ", ".join(ids[:-1]) + ", and " + ids[-1]
    # narrativa con varias obras del mismo autor: "Autor ([-@a; -@b])"
    autor = c["esperado"].split(" (")[0]
    return autor + " [" + "; ".join("-@" + it["csl"]["id"] for it in c["items"]) + "]"


def correr_apa():
    casos = json.loads((ROOT / "tests/corpus/apa7/citas.json").read_text(encoding="utf-8"))
    refs = {r["id"]: r["csl"] for r in json.loads((ROOT / "tests/corpus/apa7/referencias.json").read_text(encoding="utf-8"))}
    todos = {}
    for c in casos:
        resolver_apa(c, refs)  # todas las obras del corpus juntas: la desambiguación depende del conjunto
        for it in c["items"]:
            if "csl" in it:
                todos[it["csl"]["id"]] = it["csl"]
    filas = []
    for c in casos:
        cit = cita_apa(c)
        if cit is None:
            filas.append((c["id"], "MANUAL", c["esperado"]))
            continue
        md = "---\nnocite: '@*'\n---\n\n" + f"{A} {cit} {B}\n"
        try:
            got = extraer(pandoc_plain(md, list(todos.values()), "apa7"))
        except subprocess.CalledProcessError as e:
            filas.append((c["id"], "ERROR", e.stderr[:200]))
            continue
        filas.append((c["id"], "IGUAL" if norm(got) == norm(c["esperado"]) else "DIFIERE",
                      f"esperado={c['esperado']!r} obtenido={got!r}"))
    return filas


def correr_ieee():
    casos = json.loads((ROOT / "tests/corpus/ieee/citas.json").read_text(encoding="utf-8"))
    refs = {r["id"]: r["csl"] for r in json.loads((ROOT / "tests/corpus/ieee/referencias.json").read_text(encoding="utf-8"))}
    filas = []
    for c in casos:
        items = []
        for rid in c["lista"]:
            it = dict(refs[rid])
            it["id"] = rid
            items.append(it)
        orden = " ".join(f"[@{r}]" for r in c["lista"])  # fija la numeración por orden de aparición
        partes = []
        for it in c["items"]:
            pre, resto = clave(it)
            partes.append(f"{pre}@{it['ref']}{resto}")
        md = f"{orden}\n\n{A} [{'; '.join(partes)}] {B}\n"
        try:
            got = extraer(pandoc_plain(md, items, "ieee"))
        except subprocess.CalledProcessError as e:
            filas.append((c["id"], "ERROR", e.stderr[:200]))
            continue
        filas.append((c["id"], "IGUAL" if norm(got) == norm(c["esperado"]) else "DIFIERE",
                      f"esperado={c['esperado']!r} obtenido={got!r}"))
    return filas


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    normas = [x for x in sys.argv[1:] if not x.startswith("--")] or ["apa7", "ieee"]
    ok = True
    for n in normas:
        filas = correr_apa() if n == "apa7" else correr_ieee()
        cuenta = {k: sum(f[1] == k for f in filas) for k in ("IGUAL", "DIFIERE", "ERROR", "MANUAL")}
        print(f"\n== citas {n}: {cuenta}")
        for f in filas:
            if f[1] != "IGUAL":
                print(f"  {f[0]:<16} {f[1]:<8} {f[2]}")
        ok &= not cuenta["DIFIERE"] and not cuenta["ERROR"]
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
