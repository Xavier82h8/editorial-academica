#!/usr/bin/env python3
"""V5 (sustento), parte determinista: extrae cada oración que cita una fuente y la empareja con el resumen.

Uso:
  python -I afirmaciones.py doc.md --fuentes fuentes.json [--json afirmaciones.json]

Para cada oración con `[@id…]` o `@id` narrativo produce {n, seccion, oracion, ids, resumenes, cifras_sin_respaldo}.
`cifras_sin_respaldo`: números de la oración (salvo años y localizadores) que no aparecen en el resumen de
ninguna fuente citada en ella. Es la señal mecánica de V5; el agente `verificador-afirmaciones` juzga el resto
(¿el resumen respalda, respalda en parte, contradice o no permite verificar la afirmación?).
Salida: 0 sin cifras sin respaldo; 1 con cifras que no aparecen en el resumen citado; 2 error de uso o de entrada.
"""
import argparse
import json
import pathlib
import re
import sys
import unicodedata

RE_CITA = re.compile(r"\[[^\[\]]*@[\w:.#$%&+?<>~/-]+[^\[\]]*\]|(?<![\w\[])-?@([\w][\w:.#$%&+?<>~/-]*[\w])")
RE_ID = re.compile(r"@([\w][\w:.#$%&+?<>~/-]*[\w])")
RE_NUM = re.compile(r"(?<![\w.])(\d+(?:[.,]\d+)?)\s*(%|por ciento)?")


def oraciones(texto):
    """Divide en oraciones sin cortar dentro de corchetes ni en abreviaturas comunes."""
    out, buf, prof = [], [], 0
    for i, c in enumerate(texto):
        buf.append(c)
        prof += (c == "[") - (c == "]")
        if c in ".?!" and prof == 0:
            sig = texto[i + 1:i + 3]
            previa = "".join(buf[-6:])
            if (sig[:1] in (" ", "\n", "") and not re.search(r"\b(al|p|pp|e\.g|i\.e|vs|Fig|cf|núm|vol|ed|eds|Dr|Dra|EE\.UU)\.$", previa)
                    and not (sig[1:2].islower())):
                out.append("".join(buf).strip())
                buf = []
    if "".join(buf).strip():
        out.append("".join(buf).strip())
    return out


def numeros(s):
    s = RE_CITA.sub(" ", s)
    res = []
    for m in RE_NUM.finditer(s):
        v = m.group(1).replace(",", ".")
        if re.fullmatch(r"(19|20)\d\d", v):
            continue  # años
        res.append(v.rstrip("0").rstrip(".") if "." in v else v)
    return res


UNIDADES = {"zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
            "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
            "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19,
            "uno": 1, "una": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5, "seis": 6, "siete": 7, "ocho": 8,
            "nueve": 9, "diez": 10, "once": 11, "doce": 12, "trece": 13, "catorce": 14, "quince": 15}
DECENAS = {"twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80,
           "ninety": 90, "veinte": 20, "treinta": 30, "cuarenta": 40, "cincuenta": 50, "sesenta": 60,
           "setenta": 70, "ochenta": 80, "noventa": 90}


def palabras_a_numeros(t):
    """«Sixty-one faculty» -> «61 faculty»; «twelve tools» -> «12 tools» (inglés y español, 0-99)."""
    dec = "|".join(DECENAS)
    uni = "|".join(sorted(UNIDADES, key=len, reverse=True))

    def comp(m):
        d, u = m.group(1).lower(), (m.group(2) or "").lower()
        return str(DECENAS[d] + UNIDADES.get(u, 0))
    t = re.sub(rf"\b({dec})(?:[- ]|\s+y\s+)?({uni})?\b", comp, t, flags=re.I)
    return re.sub(rf"\b({uni})\b", lambda m: str(UNIDADES[m.group(1).lower()]), t, flags=re.I)


def en_resumen(num, resumen):
    r = palabras_a_numeros(resumen).replace(",", ".")
    variantes = {num, num + ".0", num.replace(".", ",")}
    return any(re.search(r"(?<![\d.])" + re.escape(v) + r"(?![\d])", r) for v in variantes)


def extraer(md, fuentes):
    por_id = {f["id"]: f for f in fuentes}
    texto = md
    if texto.startswith("---"):
        fin = texto.find("\n---", 3)
        texto = texto[fin + 4:] if fin > 0 else texto
    seccion, res = "Introducción", []
    for bloque in texto.split("\n\n"):
        b = bloque.strip()
        if not b:
            continue
        if b.startswith("#"):
            seccion = b.lstrip("#").strip()
            continue
        for o in oraciones(unicodedata.normalize("NFC", " ".join(b.split()))):
            ids = []
            for m in RE_CITA.finditer(o):
                for i in RE_ID.findall(m.group(0)):
                    if i in por_id and i not in ids:
                        ids.append(i)
            if not ids:
                continue
            resumenes = {i: por_id[i].get("abstract", "") for i in ids}
            todos = " ".join(resumenes.values())
            sin = [n for n in numeros(o) if todos and not en_resumen(n, todos)]
            res.append({"n": len(res) + 1, "seccion": seccion, "oracion": o, "ids": ids,
                        "sin_resumen": [i for i in ids if not resumenes[i]],
                        "cifras_sin_respaldo": sin, "resumenes": resumenes})
    return res


def _fuentes_mod():
    """skills/fuentes-academicas/scripts/fuentes.py (import normal; se añade su carpeta a sys.path)."""
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "skills" / "fuentes-academicas" / "scripts"))
    import fuentes
    return fuentes


def extraer_docx(path, red=True, fuentes=None):
    """V5 sobre un documento ya maquetado (.docx o .md sin [@id]): empareja cada oración con las entradas de su
    lista de referencias por autor-año (APA, con el mismo emparejamiento que usa el juez) o por número [n] (IEEE),
    y toma el resumen de cada entrada con DOI (Crossref u OpenAlex). Con `fuentes` (la lista de `fuentes.json` generada por
    `editorial.py fuentes --desde-docx`) cada entrada toma su `id`, su `abstract` y su nivel de ese archivo (se empareja por `_ref_n`,
    o por posición si la lista tiene la misma longitud): no se vuelve a consultar la red."""
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
    import auditar
    import refs_csl
    pars, _ = (auditar.cargar_docx if str(path).lower().endswith(".docx") else auditar.cargar_md)(str(path))
    for p in pars:
        p["texto"] = unicodedata.normalize("NFC", p["texto"])
    cuerpo, _, entradas = auditar.partir(pars)
    entradas = [e for e in entradas if e["texto"].strip()]
    items = refs_csl.parsear_lista([e["texto"] for e in entradas])
    bus = _fuentes_mod()
    bus.SIN_RED = not red
    resumen = {}
    fallos = {}   # id -> motivo: el resumen no se pudo consultar (distinto de «la fuente no tiene resumen»)
    por_n = {}
    if fuentes:
        por_n = {f.get("_ref_n", k + 1): f for k, f in enumerate(fuentes)} if len(fuentes) == len(items) or any("_ref_n" in f for f in fuentes) else {}
    for i, it in enumerate(items):
        it["id"] = f"ref{i + 1}"
        f = por_n.get(i + 1)
        if f is not None:
            it["id"] = f.get("id") or it["id"]
            if f.get("abstract"):
                resumen[it["id"]] = f["abstract"]
            elif f.get("DOI") or it.get("DOI"):
                resumen[it["id"]] = ""
            continue
        if it.get("DOI"):
            try:
                resumen[it["id"]] = bus.resumen_por_doi(it["DOI"], estricto=True) or ""
            except Exception as ex:  # noqa: BLE001
                resumen[it["id"]] = ""
                fallos[it["id"]] = f"no_verificado: {type(ex).__name__} al consultar el resumen"
    por_entrada = {id(e): items[i]["id"] for i, e in enumerate(entradas)}
    etiqueta = {items[i]["id"]: e["texto"][:60] for i, e in enumerate(entradas)}
    info = auditar.info_entradas(entradas)
    seccion, res = "Introducción", []
    for p in cuerpo:
        if p.get("es_titulo"):
            seccion = p["texto"].strip()
            continue
        if p.get("en_tabla") or len(p["texto"]) < 40:
            continue
        for o in oraciones(" ".join(p["texto"].split())):
            ids = []
            enl = auditar.entradas_citadas([{"texto": o}], info)
            for ls in enl.values():
                for j, _ in ls:
                    k = por_entrada.get(id(j["e"]))
                    if k and k not in ids:
                        ids.append(k)
            for n in re.findall(r"\[(\d+)\]", o):  # IEEE: el número es la posición en la lista
                k = items[int(n) - 1]["id"] if 0 < int(n) <= len(items) else None
                if k in etiqueta and k not in ids:
                    ids.append(k)
            if not ids:
                continue
            rs = {i: resumen.get(i, "") for i in ids}
            todos = " ".join(rs.values())
            sin = [n for n in numeros(re.sub(r"\(([^()]*\d{4}[^()]*)\)", " ", o)) if todos and not en_resumen(n, todos)]
            res.append({"n": len(res) + 1, "seccion": seccion, "oracion": o, "ids": ids,
                        "fuentes": {i: etiqueta[i] for i in ids}, "sin_resumen": [i for i in ids if not rs[i]],
                        "no_verificado": {i: fallos[i] for i in ids if i in fallos},
                        "cifras_sin_respaldo": sin, "resumenes": rs})
    return res


def main():
    p = argparse.ArgumentParser(description="Sustento V5 mecánico: cifras de cada afirmación citada frente al resumen de su fuente.")
    p.add_argument("doc")
    p.add_argument("--perfil", help="se acepta por uniformidad con los demás comandos; el sustento no depende del perfil")
    p.add_argument("--fuentes", help="fuentes.json: con Markdown y [@id] son las fuentes citadas; con un .docx (o .md sin [@id]) debe venir de "
                   "`editorial.py fuentes --desde-docx` y evita consultar la red; sin él se usa la lista de referencias del documento")
    p.add_argument("--json", metavar="RUTA", help="escribe las afirmaciones como JSON")
    p.add_argument("--sin-red", action="store_true")
    a = p.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
    import auditar
    auditar.validar_entrada(a.doc)
    texto = "" if a.doc.lower().endswith(".docx") else pathlib.Path(a.doc).read_text(encoding="utf-8-sig")
    fu = json.loads(pathlib.Path(a.fuentes).read_text(encoding="utf-8")) if a.fuentes else None
    if fu is not None and "[@" in texto:
        res = extraer(texto, fu)
    else:
        res = extraer_docx(a.doc, red=not a.sin_red, fuentes=fu)
    if a.json:
        pathlib.Path(a.json).write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    sin = [r for r in res if r["cifras_sin_respaldo"]]
    print(f"{len(res)} afirmaciones con cita; {len(sin)} con cifras que no aparecen en el resumen citado")
    for r in sin:
        print(f"  #{r['n']} [{r['seccion']}] {', '.join(r['cifras_sin_respaldo'])} | {r['oracion'][:110]}")
    nores = sorted({i for r in res for i in r["sin_resumen"]})
    if nores:
        print("fuentes sin resumen (sustento no verificable):", ", ".join(nores))
    nov = sorted({i for r in res for i in r.get("no_verificado", {})})
    if nov:
        print("fuentes no verificadas (fallo de consulta, no ausencia de resumen):", ", ".join(nov))
    sys.exit(1 if sin else 0)  # cifras sin respaldo = hallazgo mayor; 2 = error de uso o de entrada


if __name__ == "__main__":
    main()
