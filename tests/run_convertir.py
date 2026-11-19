#!/usr/bin/env python3
"""Pruebas de /convertir (sin red).

Uso: python -I tests/run_convertir.py [parser|citas] [--detalle]

a) Ida y vuelta del parser de referencias: cada referencia del corpus (APA 83, IEEE 138) se
   renderiza desde su CSL-JSON con la norma y se parsea de vuelta con scripts/refs_csl.py; se
   comparan apellidos, año, título, contenedor, volumen, número, páginas, DOI, URL y tipo.
   Puerta: apellidos, año y título >= 0.95 en ambas normas; el resto >= 0.85.
b) Ida y vuelta de citas: las citas del corpus se renderizan a .docx (APA e IEEE), se convierten con
   convertir.py (mismo perfil y cruzado APA->IEEE->APA e IEEE->APA->IEEE) y se comprueban claves y
   localizadores. Puerta >= 0.95.
Código de salida 0 solo si todas las puertas pasan.
"""
import difflib
import json
import pathlib
import re
import sys
import tempfile
import unicodedata

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))
import refs_csl  # noqa: E402
import render  # noqa: E402

CAMPOS = ["apellidos", "año", "título", "contenedor", "volumen", "número", "páginas", "doi", "url", "tipo"]
PUERTA = {"apellidos": 0.95, "año": 0.95, "título": 0.95}
PUERTA_RESTO = 0.85

# grupos de tipos CSL que la norma renderiza igual (o que no se pueden distinguir leyendo solo el texto)
GRUPOS_TIPO = {
    "article-journal": "articulo", "article-magazine": "articulo", "article-newspaper": "articulo",
    "article": "preprint", "post-weblog": "web", "post": "web", "webpage": "web",
    "paper-conference": "ponencia", "speech": "ponencia", "chapter": "capitulo",
    "entry-encyclopedia": "entrada", "entry-dictionary": "entrada",
    "book": "libro", "report": "informe", "thesis": "tesis", "standard": "norma", "dataset": "datos",
    "software": "software", "motion_picture": "audiovisual", "broadcast": "audiovisual",
    "patent": "patente", "legislation": "ley", "legal_case": "caso", "bill": "ley",
    "manuscript": "manuscrito", "personal_communication": "comunicacion",
}


def slug(s):
    return re.sub(r"[^a-z0-9]", "", "".join(c for c in unicodedata.normalize("NFD", str(s or "").lower()) if unicodedata.category(c) != "Mn"))


def nombres(it):
    out = []
    for k in ("author", "host", "editor"):
        if it.get(k):
            out = it[k]
            break
    return [slug(p.get("family") or p.get("literal") or "") for p in out]


def pag(p):
    return re.sub(r"[^0-9a-z-]", "", str(p or "").lower().replace("–", "-").replace("—", "-"))


def cmp_nombres(o, p, it_p):
    if not o and not p:
        return True
    v = it_p.get("_verificacion") or {}
    if o == p:
        return True
    if v.get("etal") and p and o[:len(p)] == p:
        return True
    if v.get("omitidos") and len(p) >= 2 and o[:len(p) - 1] == p[:-1] and o[-1] == p[-1]:
        return True
    if len(o) == len(p) == 1 and (o[0] in p[0] or p[0] in o[0]):
        return True
    return False


def cmp_titulo(a, b):
    a, b = slug(a), slug(b)
    return bool(a) and (a == b or difflib.SequenceMatcher(None, a, b).ratio() >= 0.97)


def comparar(orig, par):
    """-> dict campo -> True/False/None (None = no aplica: el original no tiene el campo)."""
    r = {}
    r["apellidos"] = cmp_nombres(nombres(orig), nombres(par), par)

    def anio(it):
        return refs_csl.anio_de(it)
    r["año"] = anio(orig) == anio(par)
    r["título"] = cmp_titulo(orig.get("title"), par.get("title"))
    r["contenedor"] = (slug(orig.get("container-title")) == slug(par.get("container-title"))
                       or cmp_titulo(orig.get("container-title"), par.get("container-title"))) if orig.get("container-title") else None
    r["volumen"] = (slug(orig.get("volume")) == slug(par.get("volume"))) if orig.get("volume") else None
    r["número"] = (slug(orig.get("issue") or orig.get("number")) in (slug(par.get("issue")), slug(par.get("number")))) if (orig.get("issue") or orig.get("number")) else None
    r["páginas"] = (pag(orig.get("page")) == pag(par.get("page"))) if orig.get("page") else None
    r["doi"] = (str(orig.get("DOI", "")).lower() == str(par.get("DOI", "")).lower()) if orig.get("DOI") else None
    r["url"] = (str(orig.get("URL", "")).rstrip("/").lower() == str(par.get("URL", "")).rstrip("/").lower()) if orig.get("URL") else None
    r["tipo"] = GRUPOS_TIPO.get(orig.get("type"), orig.get("type")) == GRUPOS_TIPO.get(par.get("type"), par.get("type"))
    return r


def render_corpus(norma, tmp):
    refs = json.loads((ROOT / "tests/corpus" / norma / "referencias.json").read_text(encoding="utf-8"))
    items = [dict(x["csl"], id=x["id"]) for x in refs]
    f = pathlib.Path(tmp) / f"{norma}.json"
    f.write_text(json.dumps(items, ensure_ascii=False), encoding="utf-8")
    out = render.render_refs(str(f), norma, "en-US", fmt="markdown-smart")
    entradas = re.findall(r"::: \{#ref-(\S+) \.csl-entry\}\n(.*?)\n:::", out, re.S)
    return {x["id"]: x["csl"] for x in refs}, dict(entradas)


def ida_vuelta_parser(detalle=False):
    ok_total = True
    res = {}
    for norma in ("apa7", "ieee"):
        with tempfile.TemporaryDirectory() as tmp:
            originales, textos = render_corpus(norma, tmp)
        ids = list(textos)
        parsed = refs_csl.parsear_lista([textos[i] for i in ids], norma, red=False)
        cuenta = {c: [0, 0] for c in CAMPOS}
        fallos = {c: [] for c in CAMPOS}
        for i, par in zip(ids, parsed):
            r = comparar(originales[i], par)
            for c, v in r.items():
                if v is None:
                    continue
                cuenta[c][1] += 1
                cuenta[c][0] += bool(v)
                if not v:
                    fallos[c].append((i, originales[i], par, textos[i]))
        res[norma] = {c: (a / b if b else 1.0) for c, (a, b) in cuenta.items()}
        print(f"\n== parser {norma} ({len(ids)} referencias)")
        for c in CAMPOS:
            a, b = cuenta[c]
            meta = PUERTA.get(c, PUERTA_RESTO)
            marca = "OK " if (a / b if b else 1) >= meta else "BAJO"
            print(f"  {c:<11} {a:>3}/{b:<3} = {a / b if b else 1:.3f}  [{marca}, puerta {meta}]")
            ok_total &= (a / b if b else 1) >= meta
        if detalle:
            for c in CAMPOS:
                for i, o, p, t in fallos[c][:40]:
                    print(f"   - {c} {i}: orig={_resumen(o, c)!r} parser={_resumen(p, c)!r}\n       {t[:200]}")
    return ok_total, res


def _resumen(it, c):
    if c == "apellidos":
        return nombres(it)
    if c == "año":
        return refs_csl.anio_de(it)
    clave = {"título": "title", "contenedor": "container-title", "volumen": "volume", "número": "issue", "páginas": "page",
             "doi": "DOI", "url": "URL", "tipo": "type"}[c]
    return it.get(clave) if c != "número" else (it.get("issue"), it.get("number"))


# ------------------------------------------------------------------ b) ida y vuelta de citas
PUERTA_CITAS = 0.95
ETIQ_LOC = re.compile(r"^(?:pp?\.|págs?\.|chapters?|chap\.|cap\.|paras?\.|paragraphs?|párr\.|figs?\.|figures?|table|secs?\.|sect\.|ch\.|sections?|eqs?\.|arts?\.|vols?\.|pages?)\s*", re.I)


def norm_loc(s):
    s = re.sub(r"[{}]", "", s or "").strip().lower()
    s = ETIQ_LOC.sub("", s)
    return re.sub(r"[\s.]+", "", s.replace("–", "-").replace("—", "-"))


def clave_obra(csl):
    fam = ""
    au = csl.get("author") or csl.get("editor") or []
    if au:
        fam = slug(au[0].get("family") or au[0].get("literal"))
    return (fam, refs_csl.anio_de(csl), slug(csl.get("title")))


def emparejar(parsed, originales):
    """item parseado -> id del original (por título y primer autor)."""
    out = {}
    for it in parsed:
        f, y, t = clave_obra(it)
        mejor, mejor_r = None, 0.0
        for oid, o in originales.items():
            of, oy, ot = clave_obra(o)
            r = difflib.SequenceMatcher(None, t, ot).ratio() if t and ot else 0.0
            if f and f == of:
                r += 0.15
            if y and y == oy:
                r += 0.1
            if r > mejor_r:
                mejor, mejor_r = oid, r
        out[it["id"]] = mejor if mejor_r >= 0.8 else None
    return out


def casos_apa():
    import run_citas  # noqa: PLC0415
    casos = json.loads((ROOT / "tests/corpus/apa7/citas.json").read_text(encoding="utf-8"))
    refs = {r["id"]: r["csl"] for r in json.loads((ROOT / "tests/corpus/apa7/referencias.json").read_text(encoding="utf-8"))}
    todos = {}
    for c in casos:
        run_citas.resolver_apa(c, refs)
        for it in c["items"]:
            if "csl" in it:
                todos[it["csl"]["id"]] = it["csl"]
    out = []
    for c in casos:
        cit = run_citas.cita_apa(c)
        if cit is None:
            continue
        def _loc(it):
            suf = it.get("suffix") or ""
            return it.get("locator") or (suf[2:] if suf[:2] == ", " and suf[2:3].isdigit() else "")
        items = [(it["csl"]["id"], _loc(it)) for it in c["items"]]
        out.append({"id": c["id"], "md": cit, "items": items, "modo": c["modo"],
                    "prefijo": any((it.get("prefix") or "").strip() for it in c["items"])})
    return out, todos


def casos_ieee():
    import run_citas  # noqa: PLC0415
    casos = json.loads((ROOT / "tests/corpus/ieee/citas.json").read_text(encoding="utf-8"))
    refs = {r["id"]: dict(r["csl"], id=r["id"]) for r in json.loads((ROOT / "tests/corpus/ieee/referencias.json").read_text(encoding="utf-8"))}
    out, usados = [], {}
    for c in casos:
        partes = []
        for it in c["items"]:
            pre, resto = run_citas.clave(it)
            partes.append(f"{pre}@{it['ref']}{resto}")
            usados[it["ref"]] = refs[it["ref"]]
        out.append({"id": c["id"], "md": "[" + "; ".join(partes) + "]", "items": [(it["ref"], it.get("locator") or "") for it in c["items"]],
                    "modo": "bracket", "prefijo": False})
    return out, usados


def construir_docx(casos, items, perfil, tmp, nombre):
    """Markdown con un caso por párrafo -> .docx con render.py."""
    tmp = pathlib.Path(tmp)
    lineas = ["---", "title: Prueba de citas", "---", "", "# Introduction", ""]
    for i, c in enumerate(casos, 1):
        lineas += [f"Caso {i:02d} — {c['md']}.", ""]
    lineas += ["# References", "", "::: {#refs}", ":::", ""]
    md = tmp / f"{nombre}.md"
    md.write_text("\n".join(lineas), encoding="utf-8")
    fu = tmp / f"{nombre}.json"
    fu.write_text(json.dumps(list(items.values()), ensure_ascii=False), encoding="utf-8")
    out = tmp / f"{nombre}.docx"
    import types
    import contextlib
    import io
    ns = types.SimpleNamespace(doc=str(md), perfil=perfil, fuentes=str(fu), salida="docx", out=str(out), idioma="en-US")
    with contextlib.redirect_stdout(io.StringIO()):
        render.render_doc(ns)
    return out


def recuperado_por_caso(res, casos, originales):
    mapa = emparejar(res["items"], originales)
    por_caso = {i: [] for i in range(1, len(casos) + 1)}
    for c in res["citas"]:
        m = re.search(r"Caso (\d\d)", c.get("contexto", ""))
        if not m:
            continue
        i = int(m.group(1))
        for k, loc in zip(c["claves"], c["localizadores"]):
            por_caso.setdefault(i, []).append((mapa.get(k), norm_loc(loc)))
    return por_caso


def puntuar(casos, por_caso, detalle, titulo):
    ok = 0
    for i, c in enumerate(casos, 1):
        esp = sorted((k, norm_loc(l)) for k, l in c["items"])
        rec = sorted((k or "?", l) for k, l in por_caso.get(i, []))
        if esp == rec:
            ok += 1
        elif detalle:
            print(f"   - {titulo} caso {i:02d} ({c['id']}): esperado={esp} recuperado={rec} md={c['md']}")
    return ok, len(casos)


def ida_vuelta_citas(detalle=False):
    import convertir  # noqa: PLC0415
    resumen = {}
    ok_total = True
    with tempfile.TemporaryDirectory() as tmp:
        tmp = pathlib.Path(tmp)
        datos = {"apa7": casos_apa(), "ieee": casos_ieee()}
        for norma, (casos, items) in datos.items():
            otra = "ieee" if norma == "apa7" else "apa7"
            docx = construir_docx(casos, items, norma, tmp, f"orig_{norma}")
            # 1) mismo perfil
            r1 = convertir.convertir(docx, norma, out=tmp / f"{norma}_a_{norma}.docx", sin_red=True, auditar_salida=False,
                                     idioma="en-US", verbose=False)
            ok, n = puntuar(casos, recuperado_por_caso(r1, casos, items), detalle, f"{norma}->{norma}")
            resumen[f"{norma} -> {norma}"] = (ok, n)
            # 2) cruzado: norma -> otra -> norma (las citas se leen del documento intermedio)
            r2 = convertir.convertir(docx, otra, out=tmp / f"{norma}_a_{otra}.docx", sin_red=True, auditar_salida=False,
                                     idioma="en-US", verbose=False)
            ok2, n2 = puntuar(casos, recuperado_por_caso(r2, casos, items), detalle, f"{norma}->{otra}")
            resumen[f"{norma} -> {otra} (claves leídas del original)"] = (ok2, n2)
            inter = tmp / f"{norma}_a_{otra}.docx"
            # el intermedio no tiene los marcadores "Caso NN": se compara por orden de aparición
            r3 = convertir.convertir(inter, norma, out=tmp / f"{norma}_a_{otra}_a_{norma}.docx", sin_red=True, auditar_salida=False,
                                     idioma="en-US", verbose=False)
            mapa = emparejar(r3["items"], items)
            rec = []
            for c in r3["citas"]:
                rec.append(sorted((mapa.get(k) or "?", norm_loc(l)) for k, l in zip(c["claves"], c["localizadores"])))
            esperado = []
            for c in casos:
                esperado.append(sorted((k, norm_loc(l)) for k, l in c["items"]))
            # alinea: cada caso aporta 1 cita (parentética/bracket) o varias (narrativa con varios autores)
            plano_rec = [x for grupo in rec for x in grupo]
            plano_esp = [x for grupo in esperado for x in grupo]
            hits = sum(1 for e in plano_esp if e in plano_rec)
            # puntaje por casos: todas las citas del caso están en lo recuperado
            pool = list(plano_rec)
            ok3 = 0
            for g in esperado:
                tmp_pool = list(pool)
                if all((e in tmp_pool and (tmp_pool.remove(e) or True)) for e in g):
                    ok3 += 1
                    pool = tmp_pool
                elif detalle:
                    print(f"   - {norma}->{otra}->{norma}: falta {g}")
            resumen[f"{norma} -> {otra} -> {norma} (cadena)"] = (ok3, len(esperado))
    print("\n== citas: ida y vuelta por convertir.py")
    for k, (a, b) in resumen.items():
        p = a / b if b else 1.0
        marca = "OK " if p >= PUERTA_CITAS else "BAJO"
        print(f"  {k:<48} {a:>3}/{b:<3} = {p:.3f}  [{marca}, puerta {PUERTA_CITAS}]")
        ok_total &= p >= PUERTA_CITAS
    return ok_total


def prueba_rutas():
    """Las salidas nunca pisan la entrada ni un archivo del usuario; render no deja temporales."""
    import shutil
    import subprocess
    import tempfile as tf
    import convertir  # noqa: PLC0415
    fallas = []
    N = convertir.nombres_salida(pathlib.Path("d") / "doc.ieee.docx")
    esperado = {"md": "doc.ieee.md", "json": "doc.ieee.ast.json", "fuentes": "doc.ieee.fuentes.json",
                "informe": "doc.ieee.informe.md", "media": "doc.ieee_media"}
    for k, v in esperado.items():
        if N[k].name != v:
            fallas.append(f"nombres_salida[{k}] = {N[k].name} (esperado {v})")
    py = [sys.executable, "-I"]
    with tf.TemporaryDirectory() as tmp:
        tmp = pathlib.Path(tmp)
        from docx import Document
        d = Document()
        d.add_paragraph("Texto.")
        doc = tmp / "doc.docx"
        d.save(str(doc))
        usuario = tmp / "doc.md"
        usuario.write_text("MIO", encoding="utf-8")
        for nombre, extra in (("--out igual a la entrada", ["--out", str(doc)]),
                              ("--informe igual a la entrada", ["--informe", str(doc)]),
                              ("--informe sobre un archivo del usuario", ["--informe", str(usuario)]),
                              ("entrada .pdf", None), ("entrada inexistente", None)):
            if extra is None:
                ent = tmp / ("x.pdf" if "pdf" in nombre else "no_existe.docx")
                ent.write_bytes(b"%PDF") if "pdf" in nombre else None
                cmd = py + [str(ROOT / "scripts" / "convertir.py"), str(ent), "--a", "ieee"]
            else:
                cmd = py + [str(ROOT / "scripts" / "convertir.py"), str(doc), "--a", "ieee", *extra]
            r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
            if r.returncode != 2 or not r.stderr.strip():
                fallas.append(f"convertir {nombre}: exit {r.returncode}, stderr {r.stderr[:80]!r} (esperado exit 2 con mensaje)")
        if usuario.read_text(encoding="utf-8") != "MIO":
            fallas.append("convertir pisó doc.md del usuario")
        # render: sin --out no sobrescribe la entrada .md; --out igual a la entrada aborta; sin temporales
        try:
            render.pandoc()
        except SystemExit:
            return fallas
        fu = tmp / "fuentes.json"
        fu.write_text("[]", encoding="utf-8")
        antes = set(pathlib.Path(tf.gettempdir()).glob("tmp*.json"))
        base = py + [str(ROOT / "scripts" / "render.py"), str(usuario), "--perfil", "apa7", "--fuentes", str(fu), "--salida", "md"]
        r = subprocess.run(base, capture_output=True, text=True, encoding="utf-8")
        if r.returncode != 0 or usuario.read_text(encoding="utf-8") != "MIO" or not (tmp / "doc.salida.md").exists():
            fallas.append(f"render --salida md sin --out: exit {r.returncode}, {r.stderr[:100]!r}")
        r = subprocess.run(base + ["--out", str(usuario)], capture_output=True, text=True, encoding="utf-8")
        if r.returncode != 2 or usuario.read_text(encoding="utf-8") != "MIO":
            fallas.append(f"render --out igual a la entrada: exit {r.returncode}")
        if set(pathlib.Path(tf.gettempdir()).glob("tmp*.json")) - antes:
            fallas.append("render dejó temporales tmp*.json")
        shutil.rmtree(tmp / "doc.ieee_media", ignore_errors=True)
    return fallas


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    detalle = "--detalle" in sys.argv
    quien = args or ["parser", "citas", "rutas"]
    ok = True
    if "rutas" in quien:
        f = prueba_rutas()
        for x in f:
            print("FALLA rutas:", x)
        print(f"rutas de salida: {'OK' if not f else 'FALLAS'}")
        ok &= not f
    if "parser" in quien:
        o, _ = ida_vuelta_parser(detalle)
        ok &= o
    if "citas" in quien:
        ok &= ida_vuelta_citas(detalle)
    print("\nCONVERTIR OK" if ok else "\nCONVERTIR CON FALLAS")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
