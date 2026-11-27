#!/usr/bin/env python3
"""Índices con páginas medidas: contenido (campo TOC real con resultado precalculado), tablas y figuras.

Uso:
  python scripts/editorial.py indices <doc.docx> [--out RUTA] [--equipo .editorial.yaml] [--max-vueltas 4] [--json RUTA]
  python scripts/editorial.py indices <doc.docx> --comprobar [--pdf RUTA]     (solo mide y compara con lo escrito; no escribe)

Qué hace: localiza los títulos «ÍNDICE DE CONTENIDO» (o «Tabla de contenido»), «ÍNDICE/LISTA DE TABLAS» y «ÍNDICE/LISTA DE FIGURAS»
y reescribe lo que sigue a cada uno (si el documento no los tiene, inserta los que correspondan tras los preliminares):
  contenido  campo `TOC \\o "1-3" \\h \\z \\u` con su resultado ya calculado (una entrada por encabezado de nivel 1 a 3, enlazada a un
             marcador `_Toc…` del encabezado) y `updateFields` activo, para que Word lo actualice al abrir
  tablas     «TABLA I. Título» con los rótulos exactos del documento (rótulo «TABLA N» y el título de la línea siguiente, o rótulo con título)
  figuras    «Fig. N. Título» (también «Figura N.») con el texto exacto del pie
Tipografía: la de `formato: fuente:` de .editorial.yaml (Times New Roman 12 por defecto), tabulador de puntos a la derecha.
Páginas: se miden, no se calculan a ojo. Convierte el documento a PDF con LibreOffice, localiza cada encabezado y rótulo con PyMuPDF y
calcula el número VISIBLE según las secciones del documento (`w:pgNumType`: romanos minúsculos en los preliminares, arábigos que
reinician en 1 en el cuerpo, o lo que declare cada sección); reescribe los números y repite hasta que no cambie nada (máximo 4 vueltas:
cambiar un número de una cifra a dos puede mover una página). Sin LibreOffice o sin PyMuPDF: código 2 con el mensaje de instalación.
La salida es `<doc>.indices.docx` (o --out); nunca escribe sobre el original. Límite conocido: el número de un encabezado con numeración
automática de Word no entra en el texto de su entrada (se copia el texto del párrafo).
Salida: 0 convergió; 1 no convergió en las vueltas dadas o (con --comprobar) hay números que no coinciden con el PDF; 2 error de uso o herramienta ausente.
"""
import argparse
import copy
import pathlib
import re
import sys
import tempfile
import unicodedata
from xml.sax.saxutils import escape

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import auditar  # noqa: E402
import cli  # noqa: E402
import institucional  # noqa: E402
import libreoffice  # noqa: E402
from docx import Document  # noqa: E402
from docx.oxml import parse_xml  # noqa: E402
from docx.oxml.ns import nsdecls, qn  # noqa: E402

RE_T_CONTENIDO = re.compile(r"^(?:indice(?:\s+general|\s+de\s+contenidos?)?|tabla\s+de\s+contenidos?|contenidos?)$")
RE_T_TABLAS = re.compile(r"^(?:indice|lista)\s+de\s+tablas$")
RE_T_FIGURAS = re.compile(r"^(?:indice|lista)\s+de\s+(?:figuras|ilustraciones)$")
RE_ROT_TABLA = re.compile(r"^(TABLA|Tabla|Table)\s+([IVXLCDM]+|\d+)\s*$")
RE_ROT_TABLA_LINEA = re.compile(r"^(TABLA|Tabla|Table)\s+([IVXLCDM]+|\d+)\s*[.:]\s*(\S.*)$")
RE_ROT_FIG = re.compile(r"^(Fig\.|Figura|Figure)\s*(\d+)\s*[.:]\s+(\S.*)$")
RE_ROT_FIG_SOLO = re.compile(r"^(Figura|Figure)\s+(\d+)\s*$")
ROMANOS = ((1000, "m"), (900, "cm"), (500, "d"), (400, "cd"), (100, "c"), (90, "xc"), (50, "l"), (40, "xl"), (10, "x"), (9, "ix"), (5, "v"), (4, "iv"), (1, "i"))


def _sin(t):
    return institucional._sin(t)


def norm(t):
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", t or "")).strip()


def formato_numero(n, fmt):
    """Número de página visible según `w:pgNumType/@w:fmt`."""
    fmt = fmt or "decimal"
    if fmt in ("lowerRoman", "upperRoman"):
        out, x = "", n
        for v, s in ROMANOS:
            while x >= v:
                out += s
                x -= v
        return out.upper() if fmt == "upperRoman" else out
    if fmt in ("lowerLetter", "upperLetter"):
        c = chr(ord("a") + (n - 1) % 26) * (1 + (n - 1) // 26)
        return c.upper() if fmt == "upperLetter" else c
    return str(n)


def texto_el(el):
    return "".join(t.text or "" for t in el.iter(qn("w:t")))


def estilo_nombre(p_el, doc):
    ps = p_el.find(qn("w:pPr") + "/" + qn("w:pStyle"))
    if ps is None:
        return ""
    st = doc.styles.element.find(f'.//{qn("w:style")}[@{qn("w:styleId")}="{ps.get(qn("w:val"))}"]')
    n = st.find(qn("w:name")) if st is not None else None
    return (n.get(qn("w:val")) if n is not None else ps.get(qn("w:val"))).lower()


def nivel_encabezado(p_el, doc):
    n = estilo_nombre(p_el, doc)
    m = re.match(r"(?:heading|t[ií]tulo)\s*(\d)\b", n)
    return int(m.group(1)) if m and "prelim" not in n else 0


def texto_con_tab(el):
    """Texto del párrafo con un tabulador por cada w:tab de un run (las entradas de índice separan el título del número con uno)."""
    out = []
    for n in el.iter(qn("w:t"), qn("w:tab")):
        if n.tag == qn("w:tab"):
            if n.getparent().tag == qn("w:r"):
                out.append(chr(9))
        else:
            out.append(n.text or "")
    return "".join(out)


def es_entrada_indice(p_el, doc):
    n = estilo_nombre(p_el, doc)
    if n.startswith(("toc", "table of figures", "tabla de ilustraciones", "índice", "indice")) and not n.startswith(("título", "titulo")):
        return True
    t = texto_con_tab(p_el)
    return bool(re.search(r"\t\s*[0-9ivxlcdm]+\s*$", t) or re.search(r"\.{4,}\s*[0-9ivxlcdm]+\s*$", t))


# ---------------------------------------------------------------- recolectar lo que el documento tiene
def recolectar(doc):
    """(encabezados, tablas, figuras, zonas). encabezados: [{p, nivel, texto}], tablas/figuras: [{p, clave, texto}]; zonas: {tipo: (título p, [elementos])}."""
    body = doc.element.body
    hijos = list(body)
    zonas, en_zona = {}, set()
    for i, el in enumerate(hijos):
        if el.tag != qn("w:p"):
            continue
        t = _sin(texto_el(el)).strip().rstrip(".:")
        tipo = "contenido" if RE_T_CONTENIDO.match(t) else "tablas" if RE_T_TABLAS.match(t) else "figuras" if RE_T_FIGURAS.match(t) else None
        if tipo is None or tipo in zonas or es_entrada_indice(el, doc):
            continue
        resto = []
        for sig in hijos[i + 1:]:
            if sig.tag != qn("w:p") or sig.find(qn("w:pPr") + "/" + qn("w:sectPr")) is not None:
                break
            if not texto_el(sig).strip() and not list(sig.iter(qn("w:fldChar"))):
                break
            if not es_entrada_indice(sig, doc) and not list(sig.iter(qn("w:fldChar"), qn("w:instrText"))):
                break
            resto.append(sig)
        zonas[tipo] = (el, resto)
        en_zona.add(id(el))
        en_zona.update(id(x) for x in resto)
    enc, tablas, figs = [], [], []
    ps = [el for el in hijos if el.tag == qn("w:p")]
    for k, el in enumerate(ps):
        if id(el) in en_zona:
            continue
        t = norm(texto_el(el))
        if not t:
            continue
        n = nivel_encabezado(el, doc)
        if n and n <= 3 and not institucional.RE_PRELIM.match(_sin(t)):
            enc.append({"p": el, "nivel": n, "texto": t})
            continue
        if es_entrada_indice(el, doc):
            continue
        m = RE_ROT_TABLA_LINEA.match(t)
        if m:
            tablas.append({"p": el, "clave": f"{m.group(1)} {m.group(2)}", "texto": f"{m.group(1)} {m.group(2)}. {m.group(3)}"})
            continue
        m = RE_ROT_TABLA.match(t)
        if m:
            titulo = ""
            for sig in ps[k + 1:k + 3]:
                s = norm(texto_el(sig))
                if s:
                    titulo = s
                    break
            tablas.append({"p": el, "clave": f"{m.group(1)} {m.group(2)}", "texto": f"{m.group(1)} {m.group(2)}" + (f". {titulo}" if titulo else "")})
            continue
        m = RE_ROT_FIG.match(t)
        if m and len(t) < 400:
            figs.append({"p": el, "clave": f"{m.group(1)} {m.group(2)}.", "texto": t})
            continue
        m = RE_ROT_FIG_SOLO.match(t)
        if m:
            titulo = next((norm(texto_el(s)) for s in ps[k + 1:k + 3] if norm(texto_el(s))), "")
            figs.append({"p": el, "clave": f"{m.group(1)} {m.group(2)}.", "texto": f"{m.group(1)} {m.group(2)}." + (f" {titulo}" if titulo else "")})
    return enc, tablas, figs, zonas


# ---------------------------------------------------------------- secciones y páginas visibles
def secciones(doc):
    """[{fmt, start, primero}] en orden: formato y reinicio de numeración de cada sección y el primer texto de la sección."""
    body = doc.element.body
    out, primero = [], None

    def info(sect):
        pg = sect.find(qn("w:pgNumType")) if sect is not None else None
        st = pg.get(qn("w:start")) if pg is not None else None
        return (pg.get(qn("w:fmt")) if pg is not None else None) or "decimal", int(st) if st and st.lstrip("-").isdigit() else None

    for el in body:
        if el.tag == qn("w:sectPr"):
            fmt, st = info(el)
            out.append({"fmt": fmt, "start": st, "primero": primero})
            primero = None
            continue
        t = norm(texto_el(el))
        if t and primero is None:
            primero = t
        s = el.find(qn("w:pPr") + "/" + qn("w:sectPr")) if el.tag == qn("w:p") else None
        if s is not None:
            fmt, st = info(s)
            out.append({"fmt": fmt, "start": st, "primero": primero})
            primero = None
    return out


def paginas_pdf(pdf):
    """[[línea, …] por hoja] en orden de lectura (una línea de texto cada una)."""
    fitz = libreoffice.requerir_pymupdf()
    paginas = []
    with fitz.open(str(pdf)) as d:
        for pg in d:
            ls = []
            for b in pg.get_text("dict")["blocks"]:
                for ln in b.get("lines", []):
                    t = norm("".join(s["text"] for s in ln["spans"]))
                    if t:
                        ls.append((round(ln["bbox"][1]), ln["bbox"][0], t))
            paginas.append([t for _, _, t in sorted(ls)])
    return paginas


def visibles(pgs, secs, avisos):
    """Número visible de cada hoja física: lista de textos, según el inicio y el formato de cada sección."""
    n = len(pgs)
    inicio, ultimo = [], 0
    for k, s in enumerate(secs):
        if k == 0:
            inicio.append(0)
            continue
        prim = s["primero"] or ""
        # una línea del PDF que sea el principio del primer texto de la sección (una entrada de índice lleva puntos y número: no coincide)
        hit = next((j for j in range(ultimo, n) if prim and any(l == prim or (len(l) >= 12 and prim.startswith(l)) for l in pgs[j])), None)
        if hit is None:
            hit = min(n - 1, ultimo + 1)
            avisos.append(f"sección {k + 1}: no se halló su primer texto en el PDF; se supone que empieza en la hoja {hit + 1}")
        inicio.append(hit)
        ultimo = hit
    vis, cont = [], 0
    for j in range(n):
        k = max(i for i, st in enumerate(inicio) if st <= j)
        s = secs[k]
        if j == inicio[k]:
            cont = s["start"] if s["start"] is not None else (cont + 1 if j else 1)
        else:
            cont += 1
        vis.append(formato_numero(cont, s["fmt"]))
    return vis


def _regex_titulo(texto):
    t = re.escape(norm(texto))
    return re.compile(r"^(?:[0-9ivxlcIVXLC]+(?:\.[0-9]+)*\.?\s+)?" + t + r"$", re.I)


def medir(pdf, doc, enc, tablas, figs, avisos):
    """{("enc"|"tab"|"fig", posición): página visible}. Búsqueda monótona (los elementos aparecen en el orden del documento) tras el último índice."""
    pgs = paginas_pdf(pdf)
    vis = visibles(pgs, secciones(doc), avisos)
    ult_indice = -1
    for j, pg in enumerate(pgs):
        if any(RE_T_CONTENIDO.match(_sin(l).strip().rstrip(".:")) or RE_T_TABLAS.match(_sin(l).strip().rstrip(".:"))
               or RE_T_FIGURAS.match(_sin(l).strip().rstrip(".:")) for l in pg):
            ult_indice = max(ult_indice, j)
    res = {}
    desde = ult_indice + 1

    def hallar(pred, empezar):
        for j in range(empezar, len(pgs)):
            pg = pgs[j]
            for i in range(len(pg)):
                for n in (1, 2, 3):
                    if pred(" ".join(pg[i:i + n])):
                        return j
        return None

    # los encabezados avanzan de forma monótona; las tablas y las figuras tienen su propia secuencia
    j = desde
    for i_h, h in enumerate(enc):
        rx = _regex_titulo(h["texto"])
        k = hallar(lambda s: bool(rx.match(s)), j)
        if k is None:
            k = hallar(lambda s: bool(rx.match(s)), desde)
        if k is None:
            avisos.append(f"encabezado «{h['texto'][:50]}» no hallado en el PDF")
            continue
        res[("enc", i_h)] = vis[k]
        j = k
    for nombre_l, lista, ini in (("tab", tablas, desde), ("fig", figs, desde)):
        j = ini
        for i_l, it in enumerate(lista):
            rx = re.compile(r"^" + re.escape(it["clave"]) + (r"(?:\s|$)" if it["clave"].endswith(".") else r"(?:[.:]\s|\s*$)"))
            k = hallar(lambda s: bool(rx.match(s)), j) or hallar(lambda s: bool(rx.match(s)), ini)
            if k is None:
                avisos.append(f"rótulo «{it['clave']}» no hallado en el PDF")
                continue
            res[(nombre_l, i_l)] = vis[k]
            j = k
    return res, vis


# ---------------------------------------------------------------- escribir
def _rpr(f, negrita=False):
    nom = escape(f["nombre"])
    sz = int(round(f["pt"] * 2))
    return (f'<w:rPr><w:rFonts w:ascii="{nom}" w:hAnsi="{nom}" w:cs="{nom}" w:eastAsia="{nom}"/>' + ("<w:b/><w:bCs/>" if negrita else "")
            + f'<w:color w:val="000000"/><w:sz w:val="{sz}"/><w:szCs w:val="{sz}"/></w:rPr>')


def id_estilo(doc, *nombres):
    """styleId del primer estilo cuyo nombre (sin mayúsculas) está en `nombres`, o None."""
    for st in doc.styles.element.findall(qn("w:style")):
        n = st.find(qn("w:name"))
        if n is not None and n.get(qn("w:val")).lower() in nombres:
            return st.get(qn("w:styleId"))
    return None


def parrafo_entrada(doc, f, texto, pagina, nivel, ancho_tw, anchor=None, campo=None, estilo=None):
    """Una línea de índice: texto, tabulador de puntos a la derecha y número. `campo`: 'inicio' | 'fin' | None para el campo TOC."""
    izq = {1: 0, 2: 360, 3: 720}.get(nivel, 0)
    antes = 80 if nivel == 1 else 0
    r = _rpr(f, negrita=(nivel == 1 and anchor is not None))
    ps = f'<w:pStyle w:val="{estilo}"/>' if estilo else ""
    xml = (f'<w:p {nsdecls("w")}><w:pPr>{ps}<w:tabs><w:tab w:val="right" w:leader="dot" w:pos="{ancho_tw}"/></w:tabs>'
           f'<w:spacing w:before="{antes}" w:after="0" w:line="240" w:lineRule="auto"/><w:ind w:left="{izq}" w:right="720" w:firstLine="0"/><w:jc w:val="left"/></w:pPr>')
    if campo == "inicio":
        xml += (f'<w:r>{r}<w:fldChar w:fldCharType="begin"/></w:r><w:r>{r}<w:instrText xml:space="preserve"> TOC \\o "1-3" \\h \\z \\u </w:instrText></w:r>'
                f'<w:r>{r}<w:fldChar w:fldCharType="separate"/></w:r>')
    cuerpo = (f'<w:r>{r}<w:t xml:space="preserve">{escape(texto)}</w:t></w:r><w:r>{r}<w:tab/></w:r><w:r>{r}<w:t>{escape(pagina)}</w:t></w:r>')
    xml += f'<w:hyperlink w:anchor="{anchor}" w:history="1">{cuerpo}</w:hyperlink>' if anchor else cuerpo
    if campo == "fin":
        xml += f'<w:r>{r}<w:fldChar w:fldCharType="end"/></w:r>'
    return parse_xml(xml + "</w:p>")


def marcador_toc(doc, p_el, usados):
    """Nombre del marcador `_Toc…` del encabezado (reutiliza el que tenga; si no, lo crea)."""
    for b in p_el.iter(qn("w:bookmarkStart")):
        n = b.get(qn("w:name")) or ""
        if n.startswith("_Toc"):
            return n
    ids = [int(b.get(qn("w:id"))) for b in doc.element.body.iter(qn("w:bookmarkStart")) if (b.get(qn("w:id")) or "").isdigit()]
    nuevo = max(ids + [9000]) + 1
    nombre = f"_Toc{202600000 + nuevo}"
    while nombre in usados:
        nuevo += 1
        nombre = f"_Toc{202600000 + nuevo}"
    usados.add(nombre)
    ini = parse_xml(f'<w:bookmarkStart {nsdecls("w")} w:id="{nuevo}" w:name="{nombre}"/>')
    fin = parse_xml(f'<w:bookmarkEnd {nsdecls("w")} w:id="{nuevo}"/>')
    ppr = p_el.find(qn("w:pPr"))
    if ppr is not None:
        ppr.addnext(ini)
    else:
        p_el.insert(0, ini)
    p_el.append(fin)
    return nombre


def poner_update_fields(doc):
    st = doc.settings.element
    if st.find(qn("w:updateFields")) is not None:
        st.find(qn("w:updateFields")).set(qn("w:val"), "true")
        return
    nuevo = parse_xml(f'<w:updateFields {nsdecls("w")} w:val="true"/>')
    for tag in ("hdrShapeDefaults", "footnotePr", "endnotePr", "compat", "docVars", "rsids"):
        e = st.find(qn("w:" + tag))
        if e is not None:
            e.addprevious(nuevo)
            return
    st.append(nuevo)


def escribir(doc, f, enc, tablas, figs, zonas, paginas, ancho_tw, crear_si_falta=True, avisos=None):
    """Reescribe las tres zonas con las páginas dadas ({clave: texto}). Devuelve cuántos números cambiaron."""
    usados = {b.get(qn("w:name")) for b in doc.element.body.iter(qn("w:bookmarkStart"))}
    estilos = {1: id_estilo(doc, "toc 1"), 2: id_estilo(doc, "toc 2"), 3: id_estilo(doc, "toc 3"), "fig": id_estilo(doc, "table of figures", "tabla de ilustraciones")}
    cambios = 0

    def pag(nombre_l, i):
        return paginas.get((nombre_l, i), "0")

    for tipo, lista in (("contenido", enc), ("tablas", tablas), ("figuras", figs)):
        if not lista:
            continue
        if tipo not in zonas:
            if not crear_si_falta:
                continue
            ref = zonas.get("figuras") or zonas.get("tablas") or zonas.get("contenido")
            titulo_txt = {"contenido": "ÍNDICE DE CONTENIDO", "tablas": "ÍNDICE DE TABLAS", "figuras": "ÍNDICE DE FIGURAS"}[tipo]
            t_el = parse_xml(f'<w:p {nsdecls("w")}><w:pPr><w:pageBreakBefore/><w:spacing w:before="0" w:after="0" w:line="360" w:lineRule="auto"/><w:jc w:val="center"/></w:pPr>'
                             f'<w:r>{_rpr(f, True)}<w:t>{titulo_txt}</w:t></w:r></w:p>')
            if ref is not None:
                (ref[1][-1] if ref[1] else ref[0]).addnext(t_el)
            else:
                prim = next((h["p"] for h in enc), None) or next(iter(doc.element.body))
                prim.addprevious(t_el)
            zonas[tipo] = (t_el, [])
            if avisos is not None:
                avisos.append(f"el documento no tenía «{titulo_txt}»: se insertó (revisa su lugar y su numeración de sección)")
        t_el, viejos = zonas[tipo]
        nuevos = []
        if tipo == "contenido":
            for k, h in enumerate(enc):
                nombre = marcador_toc(doc, h["p"], usados)
                nuevos.append(parrafo_entrada(doc, f, h["texto"], pag("enc", k), h["nivel"], ancho_tw, anchor=nombre,
                                              campo="inicio" if k == 0 else ("fin" if k == len(enc) - 1 else None), estilo=estilos[h["nivel"]]))
            if len(enc) == 1:  # un solo encabezado: inicio y fin en el mismo párrafo
                nuevos[0] = parrafo_entrada(doc, f, enc[0]["texto"], pag("enc", 0), 1, ancho_tw,
                                            anchor=marcador_toc(doc, enc[0]["p"], usados), campo="inicio", estilo=estilos[1])
                nuevos[0].append(parse_xml(f'<w:r {nsdecls("w")}>{_rpr(f)}<w:fldChar w:fldCharType="end"/></w:r>'))
        else:
            for i_l, it in enumerate(lista):
                nuevos.append(parrafo_entrada(doc, f, it["texto"], pag("tab" if tipo == "tablas" else "fig", i_l), 0, ancho_tw, estilo=estilos["fig"]))
        viejo_txt = [norm(texto_el(x)) for x in viejos]
        ancla = t_el
        for n in nuevos:
            ancla.addnext(n)
            ancla = n
        for v in viejos:
            v.getparent().remove(v)
        nuevo_txt = [norm(texto_el(x)) for x in nuevos]
        cambios += sum(1 for a, b in zip(viejo_txt, nuevo_txt) if a != b) + abs(len(viejo_txt) - len(nuevo_txt))
    poner_update_fields(doc)
    return cambios


def fuente_cfg(documento, equipo):
    f, _ = auditar.formato_equipo(documento, equipo)
    fu = (f or {}).get("fuente") or {}
    return {"nombre": fu.get("nombre") or "Times New Roman", "pt": fu.get("pt") or 12}


def ancho_texto_tw(doc):
    sect = doc.element.body.find(qn("w:sectPr"))
    mar, sz = (sect.find(qn("w:pgMar")), sect.find(qn("w:pgSz"))) if sect is not None else (None, None)
    w = int(sz.get(qn("w:w"), 12240)) if sz is not None else 12240
    return w - (int(mar.get(qn("w:left"), 1440)) + int(mar.get(qn("w:right"), 1440)) if mar is not None else 2880)


def construir(documento, salida=None, equipo=None, max_vueltas=4):
    """Escribe `<doc>.indices.docx` con los índices y sus páginas medidas. Devuelve el resultado."""
    auditar.validar_entrada(documento, (".docx",))
    libreoffice.requerir()
    libreoffice.requerir_pymupdf()
    entrada = pathlib.Path(documento).resolve()
    out = pathlib.Path(salida).resolve() if salida else entrada.with_name(entrada.stem + ".indices.docx")
    if out == entrada:
        cli.error("la salida coincide con el original: los índices nunca se escriben sobre el original (usa --out distinto)")
    f = fuente_cfg(documento, equipo)
    avisos = []
    paginas, convergio, vueltas = {}, False, 0
    import shutil
    with tempfile.TemporaryDirectory(prefix="indices-") as tmp:
        ruta = pathlib.Path(tmp) / "i.docx"
        for v in range(1, max_vueltas + 1):
            doc = Document(str(entrada))
            enc, tablas, figs, zonas = recolectar(doc)
            if not (enc or tablas or figs):
                cli.error("el documento no tiene encabezados de nivel 1 a 3 (estilo Heading/Título), tablas ni figuras rotuladas que indexar")
            escribir(doc, f, enc, tablas, figs, zonas, paginas, ancho_texto_tw(doc), avisos=avisos if v == 1 else None)
            doc.save(str(ruta))
            vueltas = v
            d2 = Document(str(ruta))
            enc2, tablas2, figs2, _z = recolectar(d2)
            av = []
            medidas, _vis = medir(libreoffice.a_pdf(ruta, tmp), d2, enc2, tablas2, figs2, av)
            if v == 1:
                avisos += av
            if medidas == paginas:  # lo escrito es lo que mide el PDF de lo escrito
                convergio = True
                break
            paginas = medidas
        if not convergio:  # se escribe lo último medido y se informa
            doc = Document(str(entrada))
            enc, tablas, figs, zonas = recolectar(doc)
            escribir(doc, f, enc, tablas, figs, zonas, paginas, ancho_texto_tw(doc), avisos=None)
            doc.save(str(ruta))
        shutil.copyfile(str(ruta), str(out))
    return {"salida": str(out), "vueltas": vueltas, "convergio": convergio, "avisos": avisos,
            "encabezados": len(enc), "tablas": len(tablas), "figuras": len(figs),
            "paginas": {f"{k_[0]}{k_[1] + 1}": val for k_, val in paginas.items()}}


# ---------------------------------------------------------------- comprobar un documento ya indexado contra su PDF
def leer_escrito(doc):
    """{texto de la entrada: número escrito} de los tres índices del documento."""
    _e, _t, _f, zonas = recolectar(doc)
    out = {}
    for tipo, (t_el, resto) in zonas.items():
        for p in resto:
            ts = [t.text or "" for t in p.iter(qn("w:t"))]
            if len(ts) >= 2:
                out[(tipo, norm("".join(ts[:-1])))] = norm(ts[-1])
    return out


def comprobar(docx, pdf=None):
    """[(índice, entrada, escrito, medido)] de los números del índice que no coinciden con el PDF."""
    libreoffice.requerir_pymupdf()
    docx = pathlib.Path(docx)
    doc = Document(str(docx))
    enc, tablas, figs, zonas = recolectar(doc)
    with tempfile.TemporaryDirectory(prefix="indices-") as tmp:
        pdf = pathlib.Path(pdf) if pdf else libreoffice.a_pdf(docx, tmp)
        av = []
        medidos, _vis = medir(pdf, doc, enc, tablas, figs, av)
    escrito = leer_escrito(doc)
    por_texto = {}
    for i, h in enumerate(enc):
        por_texto[("contenido", h["texto"])] = medidos.get(("enc", i))
    for i, it in enumerate(tablas):
        por_texto[("tablas", it["texto"])] = medidos.get(("tab", i))
    for i, it in enumerate(figs):
        por_texto[("figuras", it["texto"])] = medidos.get(("fig", i))
    dif = []
    for k, medido in por_texto.items():
        e = escrito.get(k)
        if e is None or medido is None:
            continue
        if e != medido:
            dif.append((k[0], k[1], e, medido))
    return dif, av, len(por_texto)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="editorial indices", description="Índices de contenido, tablas y figuras con páginas medidas en el PDF.")
    ap.add_argument("documento")
    ap.add_argument("--out", metavar="RUTA", help="salida (por defecto <doc>.indices.docx)")
    ap.add_argument("--equipo", help="ruta de .editorial.yaml (si no, se busca hacia arriba desde el documento)")
    ap.add_argument("--max-vueltas", type=int, default=4, dest="max_vueltas")
    ap.add_argument("--comprobar", action="store_true", help="no escribe: mide y compara los números escritos con el PDF")
    ap.add_argument("--pdf", metavar="RUTA", help="con --comprobar: PDF ya hecho del documento")
    ap.add_argument("--json", metavar="RUTA")
    a = ap.parse_args(argv)
    cli.utf8()
    auditar.validar_entrada(a.documento, (".docx",))
    if a.comprobar:
        libreoffice.requerir() if not a.pdf else None
        dif, av, n = comprobar(a.documento, a.pdf)
        for k, e, esc, med in dif:
            print(f"{k}: «{e[:60]}» dice {esc}, el PDF da {med}")
        for x in av:
            print("aviso:", x)
        print(f"{len(dif)} números distintos de {n} entradas" if dif else f"los {n} números de los índices coinciden con el PDF")
        cli.escribir_json(a.json, {"diferencias": dif, "entradas": n})
        return cli.HALLAZGOS if dif else cli.OK
    r = construir(a.documento, a.out, a.equipo, a.max_vueltas)
    print(f"índices escritos en {r['salida']}: {r['encabezados']} encabezados, {r['tablas']} tablas, {r['figuras']} figuras; "
          f"{r['vueltas']} vueltas, {'convergió' if r['convergio'] else 'NO convergió'}")
    for x in r["avisos"]:
        print("aviso:", x)
    cli.escribir_json(a.json, r)
    return cli.OK if r["convergio"] else cli.HALLAZGOS


if __name__ == "__main__":
    sys.exit(main())
