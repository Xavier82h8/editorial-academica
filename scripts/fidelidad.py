#!/usr/bin/env python3
"""Certificado de fidelidad: compara el TEXTO de un .docx original con el de su versión corregida.

Compara párrafos del cuerpo, tablas (celda por celda), encabezados y pies (sin el campo de número de página) y notas al
pie/finales. Los espacios (normales, no separables, dobles) y los saltos de línea no cuentan como texto; los párrafos
vacíos tampoco. Cada cambio queda clasificado:
  - texto aprobado:   el usuario lo aprobó (propuesta aplicada con `corregir --aplicar-propuestas`)
  - texto NO aprobado: nadie lo aprobó (en modo fiel es un error y no se escribe la salida)
  - texto por reglas (modo completo): `corregir` sin --fiel corrige texto por regla; se lista, sin aprobación individual
  - formato-solo:     solo cambian espacios; se cuenta, no se lista

Uso suelto:  python scripts/editorial.py comparar original.docx corregido.docx [--json RUTA]
  imprime el certificado de texto y un resumen de los cambios de formato por grupo (con scripts/medir.py).
Salida: 0 texto idéntico, 1 con cambios de texto, 2 error de uso.
"""
import argparse
import collections
import difflib
import pathlib
import re
import sys
import unicodedata
import zipfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import cli  # noqa: E402

from lxml import etree  # noqa: E402

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def q(t):
    return "{%s}%s" % (W, t)


CAMPOS_NUMERO = ("PAGE", "NUMPAGES", "SECTIONPAGES")
CLASE_APROBADO, CLASE_NO_APROBADO, CLASE_REGLAS = "texto aprobado", "texto NO aprobado", "texto por reglas (modo completo)"


def norm(t):
    t = unicodedata.normalize("NFC", t).replace(" ", " ").replace(" ", " ")
    return " ".join(t.split())


def texto_parrafo(p):
    """Texto visible de un w:p; los campos PAGE/NUMPAGES (y su resultado en caché) no cuentan como texto."""
    out = []
    pila = []  # campos complejos abiertos: [instrucción, ya_separado]

    def omitir():
        return any(sep and instr.strip().upper().startswith(CAMPOS_NUMERO) for instr, sep in pila)

    def rec(el):
        for ch in el:
            tag = ch.tag
            if tag == q("fldSimple"):
                if (ch.get(q("instr")) or "").strip().upper().startswith(CAMPOS_NUMERO):
                    continue
                rec(ch)
            elif tag == q("fldChar"):
                t = ch.get(q("fldCharType"))
                if t == "begin":
                    pila.append(["", False])
                elif t == "separate" and pila:
                    pila[-1][1] = True
                elif t == "end" and pila:
                    pila.pop()
            elif tag == q("instrText"):
                if pila:
                    pila[-1][0] += ch.text or ""
            elif tag == q("t"):
                if not omitir():
                    out.append(ch.text or "")
            elif tag in (q("tab"), q("br"), q("cr")):
                out.append(" ")
            elif tag == q("noBreakHyphen"):
                out.append("-")
            elif tag in (q("delText"), q("pPr"), q("rPr")):
                continue
            else:
                rec(ch)

    rec(p)
    return "".join(out)


def _hijos_parrafos(el, ruta, salida, en_tabla, tablas):
    """Recorre cuerpo/celdas/sdt; `salida` recibe (etiqueta, texto) de párrafos fuera de tablas y `tablas` los de celdas."""
    for ch in el:
        if ch.tag == q("p"):
            salida.append((f"párrafo {len(salida) + 1}", texto_parrafo(ch)))
        elif ch.tag == q("tbl"):
            n = len(tablas) + 1
            celdas = []
            for i, tr in enumerate(ch.iterchildren(q("tr")), 1):
                for j, tc in enumerate(tr.iterchildren(q("tc")), 1):
                    sub = []
                    _hijos_parrafos(tc, ruta, sub, True, [])
                    celdas.append((f"tabla {n} fila {i} columna {j}", " ".join(t for _, t in sub if norm(t))))
            tablas.extend(celdas)
        elif ch.tag in (q("sdt"), q("customXml")):
            cont = ch.find(q("sdtContent"))
            _hijos_parrafos(ch if cont is None else cont, ruta, salida, en_tabla, tablas)
        elif ch.tag == q("ins"):
            _hijos_parrafos(ch, ruta, salida, en_tabla, tablas)


def _parte(z, nombre):
    try:
        return etree.fromstring(z.read(nombre))
    except KeyError:
        return None


def _partes_referenciadas(z, doc):
    """[(kind, nombre de parte)] de encabezados y pies referenciados por las secciones, en orden de sección."""
    rels = _parte(z, "word/_rels/document.xml.rels")
    destino = {}
    if rels is not None:
        for r in rels:
            destino[r.get("Id")] = r.get("Target")
    out = []
    for ref in doc.iter(q("headerReference"), q("footerReference")):
        rid = ref.get("{%s}id" % R)
        t = destino.get(rid)
        if t:
            out.append(("encabezado" if ref.tag == q("headerReference") else "pie", "word/" + t.lstrip("/").replace("word/", "")))
    return out


def extraer(path):
    """{'cuerpo': [(etiqueta, texto)], 'tablas': [...], 'encabezados': [...], 'notas': [...]} con el texto sin normalizar."""
    with zipfile.ZipFile(str(path)) as z:
        doc = _parte(z, "word/document.xml")
        if doc is None:
            raise ValueError(f"{path}: no es un .docx válido (falta word/document.xml)")
        cuerpo, tablas = [], []
        _hijos_parrafos(doc.find(q("body")), "cuerpo", cuerpo, False, tablas)
        enc, vistos = [], set()
        for kind, nombre in _partes_referenciadas(z, doc):
            if nombre in vistos:
                continue
            vistos.add(nombre)
            parte = _parte(z, nombre)
            if parte is None:
                continue
            txt = " ".join(t for t in (norm(texto_parrafo(p)) for p in parte.iter(q("p"))) if t)
            if txt:
                enc.append((f"{kind} ({nombre.split('/')[-1]})", txt))
        notas = []
        for nombre, tag in (("word/footnotes.xml", "footnote"), ("word/endnotes.xml", "endnote")):
            parte = _parte(z, nombre)
            if parte is None:
                continue
            for n in parte.iter(q(tag)):
                if n.get(q("type")) in ("separator", "continuationSeparator", "continuationNotice"):
                    continue
                txt = " ".join(t for t in (norm(texto_parrafo(p)) for p in n.iter(q("p"))) if t)
                if txt:
                    notas.append((f"{'nota al pie' if tag == 'footnote' else 'nota final'} {n.get(q('id'))}", txt))
    return {"cuerpo": cuerpo, "tablas": tablas, "encabezados": sorted(enc, key=lambda x: x[1]), "notas": notas}


def _comparar_listas(a, b, categoria):
    """Cambios entre dos listas [(etiqueta, texto)] ya normalizadas y sin vacíos. Devuelve (cambios, espacios_normalizados)."""
    ta, tb = [t for _, t in a], [t for _, t in b]
    cambios = []
    if ta == tb:
        return cambios
    if collections.Counter(ta) == collections.Counter(tb):  # mismos textos en otro orden
        movidos = [(i, ta[i], tb[i]) for i in range(len(ta)) if ta[i] != tb[i]]
        cambios.append({"categoria": categoria, "tipo": "reordenado", "ubicacion": f"{len(movidos)} elementos en otro orden",
                        "antes": [x[1] for x in movidos], "despues": [x[2] for x in movidos],
                        "etiquetas": [a[x[0]][0] for x in movidos]})
        return cambios
    if len(ta) == len(tb):  # mismo número de elementos: se comparan por posición (un orden distinto con ediciones no se confunde con altas y bajas)
        for i in range(len(ta)):
            if ta[i] != tb[i]:
                cambios.append({"categoria": categoria, "tipo": "modificado", "ubicacion": a[i][0], "antes": ta[i], "despues": tb[i]})
        return cambios
    sm = difflib.SequenceMatcher(None, ta, tb, autojunk=False)
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal":
            continue
        n = min(i2 - i1, j2 - j1) if op == "replace" else 0
        for k in range(n):
            cambios.append({"categoria": categoria, "tipo": "modificado", "ubicacion": a[i1 + k][0],
                            "antes": ta[i1 + k], "despues": tb[j1 + k]})
        for i in range(i1 + n, i2):
            cambios.append({"categoria": categoria, "tipo": "eliminado", "ubicacion": a[i][0], "antes": ta[i], "despues": ""})
        for j in range(j1 + n, j2):
            cambios.append({"categoria": categoria, "tipo": "agregado", "ubicacion": b[j][0], "antes": "", "despues": tb[j]})
    return cambios


def _prep(lista):
    out = [(e, norm(t)) for e, t in lista]
    return [x for x in out if x[1]]


def _textos_de(c):
    t = []
    for k in ("antes", "despues"):
        v = c[k]
        t += [norm(x) for x in v] if isinstance(v, list) else ([norm(v)] if v else [])
    return t


def comparar_texto(original, corregido, aprobados=None, modo="fiel"):
    """Certificado. `aprobados`: textos (antes y después, normalizados o no) de los cambios que el usuario aprobó.
    `modo`: «fiel» (todo cambio sin aprobar es NO aprobado) o «completo» (los cambios son por reglas, sin aprobación individual).
    Devuelve {estado, texto, cambios, resumen, aprobados_n, no_aprobados_n}."""
    A, B = extraer(original), extraer(corregido)
    aprob = {norm(t) for t in (aprobados or [])}
    cambios = []
    for cat in ("cuerpo", "tablas", "encabezados", "notas"):
        cambios += _comparar_listas(_prep(A[cat]), _prep(B[cat]), cat)
    for c in cambios:
        if modo == "completo":
            c["clase"] = CLASE_REGLAS
        else:
            c["clase"] = CLASE_APROBADO if _textos_de(c) and all(t in aprob for t in _textos_de(c)) else CLASE_NO_APROBADO
    espacios = sum(1 for (_, x), (_, y) in zip(A["cuerpo"], B["cuerpo"]) if x != y and norm(x) == norm(y)) \
        if len(A["cuerpo"]) == len(B["cuerpo"]) else 0
    vacios = max(0, sum(1 for _, t in A["cuerpo"] if not norm(t)) - sum(1 for _, t in B["cuerpo"] if not norm(t)))
    no_ap = sum(c["clase"] == CLASE_NO_APROBADO for c in cambios)
    ap = sum(c["clase"] == CLASE_APROBADO for c in cambios)
    return {"estado": "identico" if not cambios else "cambios",
            "texto": "fidelidad: texto idéntico" if not cambios else
            f"fidelidad: {len(cambios)} cambios de texto ({ap} aprobados, {no_ap} NO aprobados, {len(cambios) - ap - no_ap} por reglas)",
            "cambios": cambios,
            "resumen": {"parrafos_con_espacios_normalizados": espacios, "parrafos_vacios_quitados": vacios,
                        "parrafos": [len(A["cuerpo"]), len(B["cuerpo"])], "celdas": [len(A["tablas"]), len(B["tablas"])]},
            "aprobados_n": ap, "no_aprobados_n": no_ap}


def _corto(t, n=110):
    t = " ".join(t.split()) if isinstance(t, str) else " | ".join(" ".join(x.split())[:50] for x in t[:4])
    return t if len(t) <= n else t[:n - 1] + "…"


def imprimir(cert, log=print, max_cambios=40):
    log(cert["texto"])
    for c in cert["cambios"][:max_cambios]:
        log(f"  [{c['clase']}] {c['categoria']} {c['tipo']}: {c['ubicacion']}")
        log(f"      antes:   {_corto(c['antes'])}")
        log(f"      después: {_corto(c['despues'])}")
    if len(cert["cambios"]) > max_cambios:
        log(f"  … y {len(cert['cambios']) - max_cambios} cambios más (completos en el JSON)")
    r = cert["resumen"]
    if r["parrafos_vacios_quitados"] or r["parrafos_con_espacios_normalizados"]:
        log(f"  formato-solo: {r['parrafos_vacios_quitados']} párrafos vacíos quitados, "
            f"{r['parrafos_con_espacios_normalizados']} párrafos con espacios normalizados (no son texto)")


# ---------------------------------------------------------------- resumen de formato (medir.py)
def _vals(ficha):
    """{(grupo, atributo): valor dominante} de una ficha de medir."""
    out = {}
    for g in ficha["grupos"]:
        for attr, d in g["atributos"].items():
            out[(g["grupo"], attr)] = d["dominante"]
    for s in ficha["secciones"]:
        for k, v in (s.get("margenes") or {}).items():
            out[(f"sección {s['n']}", f"margen {k}")] = v
    return out


def _fmt_v(v):
    if isinstance(v, dict):
        if "texto" in v:
            return str(v["texto"])
        v = v.get("cm", v.get("pt", v))
        return f"{v:g} cm" if isinstance(v, (int, float)) else str(v)
    return str(v)


def cambios_formato(original, corregido):
    """Lista de {grupo, atributo, antes, despues} con lo que difiere en la ficha de medir (valor dominante por grupo)."""
    import medir
    fa, fb = medir.ficha_docx(str(original)), medir.ficha_docx(str(corregido))
    va, vb = _vals(fa), _vals(fb)
    out = []
    for k in sorted(set(va) | set(vb), key=lambda x: (str(x[0]), str(x[1]))):
        x, y = va.get(k), vb.get(k)
        if x != y:
            out.append({"grupo": k[0], "atributo": k[1], "antes": _fmt_v(x), "despues": _fmt_v(y)})
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(prog="editorial comparar", description="Compara el texto (y resume el formato) de un .docx original con su versión corregida.")
    ap.add_argument("original")
    ap.add_argument("corregido")
    ap.add_argument("--json", metavar="RUTA", help="escribe el certificado y los cambios de formato como JSON")
    ap.add_argument("--sin-formato", action="store_true", dest="sin_formato", help="solo el texto (sin la ficha de medir)")
    a = ap.parse_args(argv)
    cli.utf8()
    for r in (a.original, a.corregido):
        p = pathlib.Path(r)
        if not p.is_file() or p.suffix.lower() != ".docx":
            cli.error(f"no existe o no es .docx: {r}")
    try:
        cert = comparar_texto(a.original, a.corregido, modo="fiel")
    except (ValueError, zipfile.BadZipFile) as e:
        cli.error(str(e))
    imprimir(cert)
    fmt = []
    if not a.sin_formato:
        try:
            fmt = cambios_formato(a.original, a.corregido)
        except Exception as e:  # noqa: BLE001
            print(f"aviso: no se pudo medir el formato: {e}")
        print(f"formato: {len(fmt)} propiedades distintas por grupo" if fmt else "formato: sin diferencias medibles por grupo")
        por = collections.defaultdict(list)
        for c in fmt:
            por[c["grupo"]].append(c)
        for g, lista in por.items():
            print(f"  {g}: " + "; ".join(f"{c['atributo']} {c['antes']} -> {c['despues']}" for c in lista[:8]))
    cli.escribir_json(a.json, {"original": a.original, "corregido": a.corregido, "fidelidad": cert, "formato": fmt})
    sys.exit(cli.OK if cert["estado"] == "identico" else cli.HALLAZGOS)


if __name__ == "__main__":
    main()
