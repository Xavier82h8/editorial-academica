#!/usr/bin/env python3
"""Juez determinista: revisa las reglas MECÁNICAS de un .docx/.md según un perfil.

Uso: python -I auditar.py documento.docx [--perfil apa7] [--json salida.json] [--equipo .editorial.yaml]
`--perfil` por defecto: el de `.editorial.yaml`. Salida: 0 sin hallazgos o solo menores; 1 con hallazgos críticos o
mayores; 2 error de uso o de entrada (ver cli.py).

Las reglas que requieren juicio (contenido, tono, sesgo, tipo de fuente…) las evalúa el
agente juez-formato; este script cubre lo medible y reproducible. Cada hallazgo usa el ID
del checklist oficial (skills/<norma>/references/checklist.md).
"""
import argparse
import difflib
import json
import pathlib
import re
import sys
import unicodedata

import yaml
from docx.oxml.ns import qn

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import cli  # noqa: E402
import ooxml  # noqa: E402
TITULOS_REF = {"references", "referencias", "bibliografía", "bibliografia", "reference list",
               "lista de referencias", "fuentes consultadas", "referencias bibliográficas",
               "referencias bibliograficas", "obras citadas", "works cited", "bibliography", "fuentes",
               "fuentes de consulta", "reference", "referencia", "fuentes de información", "fuentes de informacion"}


EXTS_ENTRADA = (".docx", ".md", ".markdown", ".txt")


def _error(msg):
    """Mensaje de uso/entrada a stderr (UTF-8 aunque la consola de Windows use otra página de códigos) y exit 2."""
    try:
        sys.stderr.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    print(msg, file=sys.stderr)
    sys.exit(2)


def validar_entrada(path, exts=EXTS_ENTRADA):
    """Aborta con mensaje claro (stderr) y código 2 si `path` no existe o su extensión no está soportada."""
    p = pathlib.Path(path)
    if not p.is_file():
        _error(f"no existe el archivo: {path}")
    ext = p.suffix.lower()
    if ext not in exts:
        if exts == EXTS_ENTRADA:
            _error(f"formato no soportado: {ext or '(sin extensión)'}; convierte a .docx o .md (p. ej. con pandoc)")
        _error(f"formato no soportado: {ext or '(sin extensión)'}; este comando solo acepta {', '.join(exts)} "
               "(convierte con pandoc)")
    return p


def perfiles_validos():
    return sorted(f.stem for f in (ROOT / "perfiles").glob("*.yaml") if ".editorial" not in f.stem)


def cargar_perfil(perfil_id):
    """Lee perfiles/<id>.yaml; si no existe, lista los válidos en stderr y sale con código 2."""
    ruta = ROOT / "perfiles" / f"{perfil_id}.yaml"
    if not re.fullmatch(r"[\w.+-]+", str(perfil_id)) or not ruta.is_file():
        _error(f"perfil desconocido: {perfil_id}. Perfiles válidos: {', '.join(perfiles_validos())}")
    return yaml.safe_load(ruta.read_text(encoding="utf-8"))


def titulo_limpio(t):
    """«2.10 Fuentes consultadas», «IV. Referencias», «Referencias:» -> «fuentes consultadas» / «referencias»."""
    return re.sub(r"^\s*(?:[0-9]+(?:\.[0-9]+)*\.?|[IVXLC]+\.)\s+", "", t).strip().lower().rstrip(":")
APA_FUENTES = {("aptos", 12), ("aptos", 11), ("calibri", 11), ("arial", 11), ("lucida sans unicode", 10),
               ("times new roman", 12), ("georgia", 11), ("computer modern", 10),
               ("latin modern roman", 10)}
EMU_IN = 914400
TOL = 0.03  # pulgadas


class Hallazgo(dict):
    def __init__(self, id_, sev, ubic, evid, corr):
        super().__init__(id=id_, severidad=sev, ubicacion=ubic, evidencia=evid[:160], correccion=corr)


# ---------------------------------------------------------------- lectura .docx
STRICT_NS = [(r"http://purl\.oclc\.org/ooxml/officeDocument/relationships", "http://schemas.openxmlformats.org/officeDocument/2006/relationships"),
             (r"http://purl\.oclc\.org/ooxml/officeDocument/", "http://schemas.openxmlformats.org/officeDocument/2006/"),
             (r"http://purl\.oclc\.org/ooxml/wordprocessingml/main", "http://schemas.openxmlformats.org/wordprocessingml/2006/main"),
             (r"http://purl\.oclc\.org/ooxml/drawingml/", "http://schemas.openxmlformats.org/drawingml/2006/"),
             (r"http://purl\.oclc\.org/ooxml/", "http://schemas.openxmlformats.org/")]


def abrir_docx(path):
    """Abre con python-docx. Los .docx «Strict Open XML» (espacios de nombres purl.oclc.org, p. ej. las plantillas
    de IEEE) se reescriben en memoria al espacio Transitional equivalente, que es el que entiende python-docx."""
    import docx
    import io
    import zipfile
    validar_entrada(path, (".docx",))
    with zipfile.ZipFile(path) as z:
        strict = b"purl.oclc.org/ooxml" in z.read("_rels/.rels")
        if not strict:
            return docx.Document(path)
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as out:
            for info in z.infolist():
                data = z.read(info.filename)
                if info.filename.endswith((".xml", ".rels")):
                    t = data.decode("utf-8")
                    for a, b in STRICT_NS:
                        t = re.sub(a, b, t)
                    t = t.replace('<w:jc w:val="start"', '<w:jc w:val="left"')  # Strict: start/end; Transitional: left/right
                    t = t.replace('<w:jc w:val="end"', '<w:jc w:val="right"')
                    data = t.encode("utf-8")
                out.writestr(info, data)
    buf.seek(0)
    return docx.Document(buf)


def cargar_docx(path):
    from docx.oxml.ns import qn
    d = abrir_docx(path)

    def estilo_attr(style, getter):
        s = style
        while s is not None:
            v = getter(s)
            if v is not None:
                return v
            s = s.base_style
        return None

    # valores por defecto del documento
    defaults = d.styles.element.find(qn("w:docDefaults"))
    rf_def = None
    def_font, def_size, def_line = None, None, None
    if defaults is not None:
        rpr = defaults.find(qn("w:rPrDefault") + "/" + qn("w:rPr"))
        if rpr is not None:
            rf_def = rpr.find(qn("w:rFonts"))
            sz = rpr.find(qn("w:sz"))
            if sz is not None:
                def_size = int(sz.get(qn("w:val"))) / 2
        ppr = defaults.find(qn("w:pPrDefault") + "/" + qn("w:pPr"))
        if ppr is not None:
            sp = ppr.find(qn("w:spacing"))
            if sp is not None and sp.get(qn("w:line")) and sp.get(qn("w:lineRule"), "auto") == "auto":
                def_line = int(sp.get(qn("w:line"))) / 240
    tema = {"minor": None, "major": None}
    try:
        for rel in d.part.package.parts:
            if rel.partname.endswith("theme1.xml"):
                for k in tema:
                    m = re.search(rb"<a:" + k.encode() + rb'Font>\s*<a:latin typeface="([^"]+)"', rel.blob)
                    tema[k] = m.group(1).decode() if m else None
    except Exception:  # noqa: BLE001
        pass

    def nombre_fuente(rf):
        """Nombre de fuente de un w:rFonts: explícita (ascii/hAnsi) o la fuente del tema (minor/major) que nombra."""
        if rf is None:
            return None
        n = rf.get(qn("w:ascii")) or rf.get(qn("w:hAnsi"))
        if n:
            return n
        th = rf.get(qn("w:asciiTheme")) or rf.get(qn("w:hAnsiTheme"))
        return tema["major" if th and th.startswith("major") else "minor"] if th else None

    def_font = nombre_fuente(rf_def)

    from docx.text.paragraph import Paragraph

    tablas = {}  # n -> elemento w:tbl de las tablas de nivel superior

    def en_orden(el=None, en_tabla=False, tid=None):
        """Párrafos en orden de documento, incluidos tablas (también anidadas) y controles de contenido
        (w:sdt), que python-docx no recorre. Los de tablas van marcados: cuentan para citas, no para maquetación.
        Rinde (párrafo, en_tabla, n.º de tabla de nivel superior, es el primer párrafo de esa tabla)."""
        for ch in (d.element.body if el is None else el):
            if ch.tag == qn("w:p"):
                yield Paragraph(ch, d._body), en_tabla, tid, False
            elif ch.tag == qn("w:tbl"):
                if en_tabla:
                    mi, ini = tid, False
                else:
                    mi, ini = len(tablas) + 1, True
                    tablas[mi] = ch
                for tr in ch.iterchildren(qn("w:tr")):
                    for tc in tr.iterchildren(qn("w:tc")):
                        for p_, et, ti, _ in en_orden(tc, True, mi):
                            yield p_, et, ti, ini
                            ini = False
            elif ch.tag in (qn("w:sdt"), qn("w:customXml")):
                gal = ch.find(".//" + qn("w:docPartGallery"))
                if gal is not None and "Contents" in (gal.get(qn("w:val")) or ""):
                    continue  # índice (TOC): repite encabezados, no es cuerpo
                cont = ch.find(qn("w:sdtContent"))
                yield from en_orden(ch if cont is None else cont, en_tabla, tid)

    def estilos_por_id():
        return {s.get(qn("w:styleId")): s for s in d.styles.element.findall(qn("w:style"))}
    est_xml = estilos_por_id()

    def cadena_estilo(sid):
        """Elementos w:style desde el estilo dado hasta su base (basedOn)."""
        out, vistos = [], set()
        while sid and sid in est_xml and sid not in vistos:
            vistos.add(sid)
            out.append(est_xml[sid])
            b = est_xml[sid].find(qn("w:basedOn"))
            sid = b.get(qn("w:val")) if b is not None else None
        return out

    def bordes_tabla(tbl):
        """True si la tabla tiene bordes verticales (left/right/insideV) en tblBorders, estilo de tabla o celdas."""
        def vacio(b):
            return b is None or b.get(qn("w:val")) in ("nil", "none") or b.get(qn("w:sz")) == "0"
        lados = {}  # el estilo más cercano manda; lo directo sobreescribe
        pr = tbl.find(qn("w:tblPr"))
        fuentes = []
        if pr is not None:
            ts = pr.find(qn("w:tblStyle"))
            if ts is not None:
                fuentes += [s.find(qn("w:tblPr")) for s in reversed(cadena_estilo(ts.get(qn("w:val"))))]
            fuentes.append(pr)
        for f in fuentes:
            tb = f.find(qn("w:tblBorders")) if f is not None else None
            if tb is not None:
                for lado in ("left", "right", "start", "end", "insideV"):
                    b = tb.find(qn("w:" + lado))
                    if b is not None:
                        lados[lado] = b
        if any(not vacio(b) for b in lados.values()):
            return True
        for tc in tbl.iter(qn("w:tcBorders")):
            for lado in ("left", "right", "start", "end"):
                b = tc.find(qn("w:" + lado))
                if b is not None and not vacio(b):
                    return True
        return False

    nivel_cache = {}

    def nivel_base(style):
        """Nivel N si el estilo, o alguno de sus basedOn, es «Heading N» / «Título N» (estilo propio basado en un encabezado)."""
        s, k = style, style.style_id
        if k in nivel_cache:
            return nivel_cache[k]
        niv, vistos = 0, set()
        while s is not None and s.style_id not in vistos:
            vistos.add(s.style_id)
            m = re.match(r"(?:heading|t[ií]tulo)\s*(\d)\b", (s.name or "").lower())
            if m:
                niv = int(m.group(1))
                break
            s = s.base_style
        nivel_cache[k] = niv
        return niv

    def num_en_estilo(sid):
        for s in cadena_estilo(sid):
            n = s.find(qn("w:pPr") + "/" + qn("w:numPr") + "/" + qn("w:numId"))
            if n is not None:
                return n.get(qn("w:val")) != "0"
        return False

    T, TAB, BR, FALLBACK = ooxml.W_T, ooxml.W_TAB, ooxml.W_BR, ooxml.FALLBACK
    texto_xml = ooxml.texto_xml

    from docx.text.run import Run

    def sp_def(attr):
        if defaults is None:
            return 0.0
        sp = defaults.find(qn("w:pPrDefault") + "/" + qn("w:pPr") + "/" + qn("w:spacing"))
        return int(sp.get(qn(attr))) / 20 if sp is not None and sp.get(qn(attr)) else 0.0

    def flag_run(r_el, p, st, attr):
        """Negrita/cursiva efectiva de un run: directa, de su estilo de carácter o del estilo del párrafo."""
        r = Run(r_el, p)
        v = getattr(r.font, attr)
        if v is None and r_el.find(qn("w:rPr") + "/" + qn("w:rStyle")) is not None and r.style is not None:  # sin rStyle, el estilo es el predeterminado (y buscarlo es lento)
            v = estilo_attr(r.style, lambda s: getattr(s.font, attr))
        if v is None:
            v = estilo_attr(st, lambda s: getattr(s.font, attr))
        return bool(v)

    def fuente_efectiva(r_el, st):
        """Fuente de un run: directa, de su estilo de carácter, del estilo del párrafo (y sus bases) o docDefaults;
        las fuentes de tema (asciiTheme) se resuelven con el tema del documento."""
        rpr = r_el.find(qn("w:rPr"))
        if rpr is not None:
            n = nombre_fuente(rpr.find(qn("w:rFonts")))
            if n:
                return n
            rs = rpr.find(qn("w:rStyle"))
            for s_ in cadena_estilo(rs.get(qn("w:val"))) if rs is not None else ():
                n = nombre_fuente(s_.find(qn("w:rPr") + "/" + qn("w:rFonts")))
                if n:
                    return n
        for s_ in cadena_estilo(st.style_id) if st is not None else ():
            n = nombre_fuente(s_.find(qn("w:rPr") + "/" + qn("w:rFonts")))
            if n:
                return n
        return def_font

    def color_efectivo(r_el, st):
        """Color del texto de un run (hex en mayúsculas) salvo negro o automático: directo, de su estilo de carácter o
        del estilo del párrafo y sus bases. None = negro/automático."""
        def de(rpr):
            c = rpr.find(qn("w:color")) if rpr is not None else None
            return c.get(qn("w:val")) if c is not None else None
        rpr = r_el.find(qn("w:rPr"))
        v = de(rpr)
        if v is None and rpr is not None and rpr.find(qn("w:rStyle")) is not None:
            for s_ in cadena_estilo(rpr.find(qn("w:rStyle")).get(qn("w:val"))):
                v = de(s_.find(qn("w:rPr")))
                if v:
                    break
        if v is None:
            for s_ in cadena_estilo(st.style_id) if st is not None else ():
                v = de(s_.find(qn("w:rPr")))
                if v:
                    break
        v = (v or "").upper()
        if v in ("", "AUTO") or not re.fullmatch(r"[0-9A-F]{6}", v):
            return None
        return None if max(int(v[k:k + 2], 16) for k in (0, 2, 4)) < 0x40 else v  # casi negro (#231F20) cuenta como negro

    pars = []
    for i, (p, en_tabla, tid, inicio_tabla) in enumerate(en_orden()):
        pf, st = p.paragraph_format, p.style
        ls = pf.line_spacing if pf.line_spacing is not None else estilo_attr(st, lambda s: s.paragraph_format.line_spacing)
        if ls is None:
            ls = def_line or 1.0
        if hasattr(ls, "pt"):  # interlineado exacto en puntos
            ls = ("exacto", ls.pt)
        fi = pf.first_line_indent if pf.first_line_indent is not None else estilo_attr(st, lambda s: s.paragraph_format.first_line_indent)
        li = pf.left_indent if pf.left_indent is not None else estilo_attr(st, lambda s: s.paragraph_format.left_indent)
        al = pf.alignment if pf.alignment is not None else estilo_attr(st, lambda s: s.paragraph_format.alignment)
        fuentes, colores = set(), set()
        for r in p.runs:
            if not r.text.strip():
                continue
            fn = fuente_efectiva(r._r, st)
            fz = r.font.size.pt if r.font.size else (estilo_attr(st, lambda s: s.font.size.pt if s.font.size else None) or def_size)
            fuentes.add(((fn or "?").lower(), fz))
            col = color_efectivo(r._r, st)
            if col:
                colores.add(col)
        salto = any(b.get(qn("w:type")) == "page" for b in p._p.iter(qn("w:br")))  # sin serializar el XML de cada párrafo
        salto_est = bool(pf.page_break_before) or bool(estilo_attr(st, lambda s: s.paragraph_format.page_break_before))  # directo o del estilo
        es_sect = p._p.find(qn("w:pPr") + "/" + qn("w:sectPr")) is not None
        sb = pf.space_before if pf.space_before is not None else estilo_attr(st, lambda s: s.paragraph_format.space_before)
        sa = pf.space_after if pf.space_after is not None else estilo_attr(st, lambda s: s.paragraph_format.space_after)
        # tramos (texto, cursiva, negrita) de cada run, incluidos los de w:sdt e hipervínculos
        tramos = []
        for r_el in p._p.iter(qn("w:r")):
            a = r_el.getparent()
            while a is not None and a is not p._p and a.tag != FALLBACK:
                a = a.getparent()
            if a is not None and a.tag == FALLBACK:
                continue
            tx = "".join((n.text or "") if n.tag == T else ("\t" if n.tag == TAB else "\n") for n in r_el.iter(T, TAB, BR))
            if tx:
                tramos.append((tx, flag_run(r_el, p, st, "italic"), flag_run(r_el, p, st, "bold")))
        imagen = any(True for _ in p._p.iter("{http://schemas.openxmlformats.org/drawingml/2006/main}blip",
                                              "{urn:schemas-microsoft-com:vml}imagedata",
                                              "{http://schemas.openxmlformats.org/drawingml/2006/chart}chart"))
        npr = p._p.find(qn("w:pPr") + "/" + qn("w:numPr") + "/" + qn("w:numId"))
        numerado = (npr.get(qn("w:val")) != "0") if npr is not None else (st is not None and num_en_estilo(st.style_id))
        pars.append({
            "esp_antes": sb.pt if sb is not None else sp_def("w:before"),
            "esp_despues": sa.pt if sa is not None else sp_def("w:after"),
            "tramos": tramos, "imagen": imagen, "numerado": numerado, "tabla": tid,
            "tabla_inicio": inicio_tabla,
            "tabla_info": ({"vertical": bordes_tabla(tablas[tid]), "filas": len(tablas[tid].findall(qn("w:tr"))),
                            "columnas": len(tablas[tid].findall(qn("w:tr") + "/" + qn("w:tc")))} if inicio_tabla else None),
            "i": i, "texto": texto_xml(p._p), "estilo": st.name if st is not None else "",
            "interlineado": ls, "sangria1": fi / EMU_IN if fi is not None else 0.0,
            "sangria_izq": li / EMU_IN if li is not None else 0.0,
            "alineacion": str(al) if al is not None else "LEFT", "fuentes": fuentes, "colores": colores,
            "salto_antes": bool(pf.page_break_before) or salto, "salto_estilo": salto_est,
            "es_titulo": ((st.name if st is not None else "").lower().startswith(("heading", "título", "titulo", "title"))
                          or (st is not None and nivel_base(st) > 0)) and not en_tabla,
            "nivel_base": nivel_base(st) if st is not None else 0,
            "en_tabla": en_tabla, "sect": es_sect,
        })
    def tabuladores(p_el):
        """Paradas de tabulación (posición en twips, alineación) del párrafo: las del estilo y las directas."""
        stops = {}
        sid = p_el.find(qn("w:pPr") + "/" + qn("w:pStyle"))
        fuentes = [s_.find(qn("w:pPr")) for s_ in reversed(cadena_estilo(sid.get(qn("w:val")) if sid is not None else None))]
        fuentes.append(p_el.find(qn("w:pPr")))
        for pr in fuentes:
            if pr is None:
                continue
            for t in pr.findall(qn("w:tabs") + "/" + qn("w:tab")):
                pos, val = int(t.get(qn("w:pos"), "0")), t.get(qn("w:val"), "left")
                if val == "clear":
                    stops.pop(pos, None)
                else:
                    stops[pos] = "right" if val in ("right", "end") else val
        return sorted(stops.items())

    def pagina_en_encabezado(hdr_el):
        """Del párrafo del encabezado que lleva el campo PAGE: (alineado a la derecha, texto a su izquierda).
        Si el número va tras tabuladores se simula dónde cae cada uno: un texto largo (running head) pasa de la
        parada central y el tabulador siguiente llega a la derecha."""
        for p_el in hdr_el.iter(qn("w:p")):
            if not ooxml.tiene_pagina(p_el):  # \bPAGE\b: NUMPAGES y SECTIONPAGES no cuentan como número de página
                continue
            jc = p_el.find(qn("w:pPr") + "/" + qn("w:jc"))
            alineado_der = jc is not None and jc.get(qn("w:val")) in ("right", "end")
            stops = tabuladores(p_el)
            texto, pos, ultima, tabs, antes = "", 0.0, None, 0, ""
            for n in p_el.iter(T, TAB, qn("w:instrText"), qn("w:ptab")):
                if n.tag == qn("w:instrText"):
                    if re.search(r"\bPAGE\b", n.text or ""):
                        break
                    continue
                if n.tag == qn("w:ptab"):
                    return alineado_der or n.get(qn("w:alignment")) == "right", antes
                if n.tag == T:
                    t_ = n.text or ""
                    antes += t_
                    pos += sum((0.68 if c.isupper() else 0.5) * 11 * 20 for c in t_)  # twips, a 11 pt
                    continue
                tabs += 1
                sig = next(((x, v) for x, v in stops if x > pos + 1), None)
                if sig is None:
                    if ultima != "right":  # tras la parada derecha, otro tabulador no la deshace
                        pos = (int(pos // 720) + 1) * 720  # parada predeterminada (izquierda)
                        ultima = "predeterminada"
                else:
                    pos, ultima = sig[0], sig[1]
            # número empujado con tabuladores predeterminados: vale si queda en el lado derecho de la línea
            return alineado_der or ultima == "right" or (ultima == "predeterminada" and pos >= 5600), antes.strip()
        return None, ""

    secciones = []
    for s in d.sections:
        hdr = s.header._element.xml if s.header is not None else ""
        der, izq = pagina_en_encabezado(s.header._element) if s.header is not None else (None, "")
        secciones.append({
            # sectPr sin pgMar: python-docx da None; Word usa sus márgenes por defecto (1 in) y se avisa
            "margenes": [round((m if m is not None else EMU_IN) / EMU_IN, 2) for m in (s.top_margin, s.bottom_margin, s.left_margin, s.right_margin)],
            "sin_margenes": any(m is None for m in (s.top_margin, s.bottom_margin, s.left_margin, s.right_margin)),
            "num_pagina": ooxml.tiene_pagina(s.header._element) if s.header is not None else False,
            "num_derecha": bool(re.search(r'w:jc w:val="(right|end)"', hdr)) or 'PTab' in hdr or "w:ptab" in hdr or bool(der),
            "running_head": izq,
        })
    # notas al pie y notas finales: llevan citas, pero no forman parte de la maquetación del cuerpo
    try:
        from lxml import etree
        for parte in d.part.package.iter_parts():
            if str(parte.partname).endswith(("/footnotes.xml", "/endnotes.xml")):
                raiz = etree.fromstring(parte.blob)
                for nota in raiz:
                    if nota.get(qn("w:type")) in ("separator", "continuationSeparator", "continuationNotice"):
                        continue
                    for p_el in nota.iter(qn("w:p")):
                        tx = texto_xml(p_el)
                        if tx.strip():
                            pars.append({"i": len(pars), "texto": tx, "estilo": "Footnote Text", "nota_pie": True, "en_tabla": True,
                                         "es_titulo": False, "salto_antes": False, "sect": False, "tabla": None, "tramos": []})
    except Exception:  # noqa: BLE001
        pass
    return pars, secciones


RE_FRONTMATTER = re.compile(r"\ufeff?---\s*\n(.*?)\n---[ \t]*\n?", re.S)


def cargar_md(path, frontmatter=False):
    """Único cargador de Markdown/texto: (pars, []) con un párrafo por bloque separado por línea en blanco.

    Lee UTF-8 con BOM opcional y normaliza CRLF. Cada párrafo lleva texto sin «#», es_titulo y nivel (nº de «#»).
    Con frontmatter=True quita el bloque YAML inicial y devuelve (pars, meta) con meta como dict ({} si no hay o no
    se puede leer); sin él, el bloque YAML queda como párrafo (lo que ve el juez)."""
    validar_entrada(path)
    txt = pathlib.Path(path).read_text(encoding="utf-8-sig").replace("\r\n", "\n")
    meta = {}
    if frontmatter:
        m = RE_FRONTMATTER.match(txt)
        if m:
            try:
                meta = yaml.safe_load(m.group(1)) or {}
            except yaml.YAMLError:
                meta = {}
            if not isinstance(meta, dict):
                meta = {}
            txt = txt[m.end():]
    pars = []
    for i, bloque in enumerate(re.split(r"\n\s*\n", txt)):
        t = bloque.strip()
        m = re.match(r"^(#+)\s*", t)
        pars.append({"i": i, "texto": t[m.end():] if m else t, "es_titulo": bool(m), "nivel": len(m.group(1)) if m else 0,
                     "salto_antes": False, "estilo": ""})
    return pars, (meta if frontmatter else [])


# ---------------------------------------------------------------- utilidades
def sin_acentos(s):
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


RE_ETIQUETA_ESTILO = re.compile(r"\s*\((?:use style:\s*)?([^()]{3,40})\)\s*$", re.I)


def es_plantilla(pars):
    """Plantilla con texto de instrucción: al menos 3 párrafos terminan con el nombre de su propio estilo entre
    paréntesis, p. ej. «Introduction (Heading 1)» o «Paper Title (use style: paper title)». Su lista de referencias
    es de ejemplo y su texto no cita de verdad."""
    n = 0
    for p in pars:
        m = RE_ETIQUETA_ESTILO.search(p["texto"])
        if m and (m.group(1).strip().lower() == p.get("estilo", "").lower() or "use style" in m.group(0).lower()):
            n += 1
    return n >= 3


def partir(pars):
    """Devuelve (cuerpo, titulo_refs, entradas_refs)."""
    k = next((p["i"] for p in reversed(pars) if titulo_limpio(p["texto"]) in TITULOS_REF), None)  # la última
    if k is None:
        # bibliografía anotada (APA 9.51): sin sección «Referencias»; cada entrada con sangría francesa va seguida de su
        # anotación y esas entradas forman la lista
        ent = [p for p in pars if not p.get("en_tabla") and p.get("sangria1", 0) <= -0.3 and p["texto"][:1].strip()
               and re.match(r"[^()]{2,300}\((?:\d{4}[a-z]?|n\.d\.|s\.\s?f\.)(?:,[^)]*)?\)\.", p["texto"])]
        if len(ent) >= 2:
            ids = {id(e) for e in ent}
            return [p for p in pars if id(p) not in ids], None, ent
        return pars, None, []
    fin = len(pars)
    for p in pars[k + 1:]:
        if p.get("es_titulo") or re.match(r"^(appendix|apéndice|anexo)\b", p["texto"].strip(), re.I):
            fin = p["i"]
            break
    for p in pars[k + 1:fin]:  # tablas y figuras tras la lista (APA 2.17) no son entradas
        if re.match(r"^\s*(tabla|table|figura|figure)\s+\d+\s*$", p["texto"], re.I):
            fin = p["i"]
            break
    entradas = [p for p in pars[k + 1:fin] if p["texto"].strip()]
    return pars[:k], pars[k], entradas


def ubic(p):
    return f"{'tabla, ' if p.get('en_tabla') else ''}párrafo {p['i'] + 1}: «{p['texto'][:50]}…»"


# ---------------------------------------------------------------- base APA (maquetación)
def sin_sangria_legitima(todos, p):
    """APA-007: párrafos que APA 7 no sangra en la primera línea: cita en bloque (sangría izquierda de 0.5 in, APA 8.27)
    y el párrafo que la continúa, resumen (APA 2.9), notas de tabla o figura («Nota.»), líneas centradas y
    líneas de palabras clave."""
    if "CENTER" in p["alineacion"] or es_nota(todos, p) or re.match(r"\s*(keywords?|palabras clave)\s*:", p["texto"], re.I):
        return True
    if p["sangria_izq"] >= 0.4 and p["sangria1"] < 0.4:
        return True  # cita en bloque (o sangría francesa)
    if RE_ROT_NUM.match(p["texto"].strip()):
        return True  # rótulo «Tabla N» / «Figure N»
    k = p["i"]
    for _ in range(2):  # título bajo el rótulo (APA 7.10) o texto de la figura (cuadros de un diagrama) bajo el título
        k -= 1
        while k >= 0 and es_vacio(todos[k]) and not todos[k].get("en_tabla"):
            k -= 1
        if k < 0 or todos[k].get("en_tabla") or todos[k].get("es_titulo") or nivel_estilo(todos[k]):
            break
        if RE_ROT_NUM.match(todos[k]["texto"].strip()):
            return True
    j = p["i"] - 1
    while j >= 0 and (todos[j].get("en_tabla") or es_vacio(todos[j])):
        j -= 1
    if j >= 0 and todos[j]["sangria_izq"] >= 0.4 and todos[j]["sangria1"] < 0.4 and not todos[j].get("es_titulo") and p["sangria1"] < 0.4:
        return True  # continuación de una cita en bloque
    while j >= 0 and not nivel_estilo(todos[j]) and not todos[j].get("salto_antes"):
        j -= 1
    return j >= 0 and bool(re.match(r"\s*(abstract|resumen)\s*$", todos[j]["texto"], re.I)) and p["sangria1"] < 0.4  # resumen


def base_apa(pars, secciones, refs_titulo, entradas, tipo_trabajo="estudiante", interlineado_enc=2.0):
    H = []
    todos, pars = pars, [p for p in pars if not p.get("en_tabla")]  # tablas: interlineado y sangría propios (APA 7.13)
    for n, s in enumerate(secciones, 1):
        if any(abs(m - 1.0) > TOL for m in s["margenes"]):
            H.append(Hallazgo("APA-001", "mayor", f"sección {n}", f"márgenes (sup, inf, izq, der) = {s['margenes']} in",
                              "1 in en los cuatro lados (salvo margen institucional declarado en el perfil)"))
        if not s["num_pagina"]:
            H.append(Hallazgo("APA-008", "crítica", f"sección {n}", "el encabezado no tiene campo PAGE",
                              "insertar número de página en la esquina superior derecha"))
        elif not s["num_derecha"]:
            H.append(Hallazgo("APA-008", "crítica", f"sección {n}", "número de página no alineado a la derecha",
                              "alinear el número de página a la derecha"))
        if tipo_trabajo == "profesional":  # APA 2.18: running head en mayúsculas, ≤ 50 caracteres, sin «Running head:»
            rh = s.get("running_head", "")
            if not rh:
                H.append(Hallazgo("APA-009", "mayor", f"sección {n}", "el encabezado no tiene running head",
                                  "título abreviado en mayúsculas (máx. 50 caracteres) en el encabezado, junto al número de página"))
            else:
                if re.match(r"\s*running head\s*:", rh, re.I):
                    H.append(Hallazgo("APA-010", "menor", f"sección {n}", rh[:60], "quitar la etiqueta «Running head:»"))
                if len(rh) > 50 or rh != rh.upper():
                    H.append(Hallazgo("APA-009", "mayor", f"sección {n}", f"running head «{rh[:60]}» ({len(rh)} caracteres)",
                                      "running head en mayúsculas y de máximo 50 caracteres"))
    ids_lista = {id(e) for e in entradas}  # la lista tiene sus propias reglas (APA-060)
    fin_p = fin_portada(todos)  # la portada (APA 2.3) tiene su propia maquetación: centrada, sin sangría
    cuerpo = [p for p in pars if len(p["texto"]) > 80 and not p.get("es_titulo") and id(p) not in ids_lista and p["i"] >= fin_p]
    fuentes = {}
    for p in pars:
        for f in p.get("fuentes", ()):
            fuentes[f] = fuentes.get(f, 0) + 1
    en_cuerpo = {}  # APA-003: cualquier párrafo de texto con otra fuente (salvo monoespaciada: código)
    for p in cuerpo:
        for f in p.get("fuentes", ()):
            en_cuerpo[f] = en_cuerpo.get(f, 0) + 1
    principales = sorted(fuentes, key=fuentes.get, reverse=True)
    if principales:
        fn, fz = principales[0]
        if (fn, fz) not in APA_FUENTES:
            H.append(Hallazgo("APA-002", "mayor", "documento", f"fuente principal {fn} {fz} pt",
                              "usar una fuente permitida con su tamaño (p. ej. Times New Roman 12, Calibri 11)"))
        mono = ("courier", "consolas", "cascadia", "menlo", "monaco", "lucida console", "source code")
        otras = [f"{a} {b}" for a, b in principales[1:] if a != fn and not a.startswith(mono)
                 and (fuentes[(a, b)] > 2 or en_cuerpo.get((a, b)))]
        if otras:
            H.append(Hallazgo("APA-003", "menor", "documento", "fuentes adicionales: " + ", ".join(otras[:4]),
                              "una sola fuente en todo el texto"))
        # encabezados con el aspecto del estilo «Heading» de Word: otro tamaño o fuente que el texto, o en color
        distintos = []
        for p in pars:
            if not p.get("es_titulo") or p["i"] < fin_portada(todos) or not p["texto"].strip():
                continue
            otro = sorted({f"{a} {b:g} pt" for a, b in p.get("fuentes", ()) if b and (abs(b - fz) > 0.5 or a != fn)})
            col = sorted(p.get("colores", ()))
            if otro or col:
                distintos.append((p, ", ".join(otro + [f"color #{c}" for c in col])))
        if distintos:
            p0, que = distintos[0]
            H.append(Hallazgo("APA-003", "menor", ubic(p0),
                              f"{len(distintos)} encabezados con otro tamaño, fuente o color que el texto ({fn} {fz:g} pt); "
                              f"p. ej. «{p0['texto'][:40]}»: {que}",
                              f"encabezados en {fn} {fz:g} pt y en negro, como el texto; solo cambian negrita, cursiva y "
                              "alineación según el nivel (APA 2.19 y 2.27; el estilo «Título»/«Heading» de Word trae otro "
                              "tamaño y color)"))
    for p in cuerpo:
        ls = p["interlineado"]
        if not (isinstance(ls, (int, float)) and abs(ls - 2.0) < 0.05):
            H.append(Hallazgo("APA-004", "mayor", ubic(p), f"interlineado {ls}", "interlineado doble"))
            break
    for p in cuerpo:
        if "JUSTIFY" in p["alineacion"]:
            H.append(Hallazgo("APA-006", "mayor", ubic(p), "texto justificado", "alinear a la izquierda"))
            break
    malos = [p for p in cuerpo if abs(p["sangria1"] - 0.5) > TOL and not p["texto"].startswith((" ", "\t"))
             and p["sangria1"] >= 0 and not sin_sangria_legitima(todos, p)]
    if malos:
        H.append(Hallazgo("APA-007", "mayor", ubic(malos[0]),
                          f"{len(malos)} párrafos sin sangría de 0.5 in en la primera línea (p. ej. {malos[0]['sangria1']:.2f} in)",
                          "sangría de primera línea de 0.5 in por formato de párrafo"))
    if any(p["texto"].startswith("     ") for p in cuerpo):
        H.append(Hallazgo("APA-007", "mayor", "documento", "sangría hecha con espacios", "usar formato de párrafo"))
    if refs_titulo and secciones and not refs_titulo["salto_antes"]:
        prev = todos[refs_titulo["i"] - 1] if refs_titulo["i"] else None
        # el salto puede ir en un párrafo vacío o al final del último párrafo del texto («…made.<salto>»)
        if not (prev and prev["salto_antes"] is True and (not prev["texto"].strip() or prev["texto"].endswith("\n"))):
            H.append(Hallazgo("APA-012", "menor", ubic(refs_titulo), "la lista de referencias no empieza en página nueva",
                              "insertar salto de página antes de «Referencias»"))
    H += espaciado_apa(todos, cuerpo, fin_p)
    H += encabezados_apa(todos, fin_p, refs_titulo, entradas, interlineado_enc)
    H += tablas_figuras_apa(todos, fin_p)
    return H


# ---------------------------------------------------------------- base APA: espaciado, encabezados, tablas y figuras
TOL_PT = 0.5   # tolerancia de espacio entre párrafos (pt)
GRANDE = 10 ** 9
RE_NUM_ENC = re.compile(r"^\s*(?:\d{1,2}(?:\.\d{1,2})*\.?|[A-Z]\.|[IVXL]+\.)\s+\S")


def rotulo_re(apendice):
    """Única gramática de rótulo de tabla/figura: «Tabla 1», «Figure 2», «Fig. 3», «TABLE IV». Grupos: 1 palabra,
    2 número, 3 puntuación, 4 resto. Dos variantes, porque los consumidores no pueden compartir los bordes:
    - apendice=True (RE_ROT_NUM; reglas APA de espaciado y tablas/figuras de auditar y corregir): admite «Tabla A1» (apéndice),
      exige espacio tras la palabra y no admite «Fig.» ni exige borde tras el número.
    - apendice=False (RE_ROTULO; congruencia, maquetación y APA-091/IEEE-093): admite «Fig.», solo números arábigos o
      romanos (numero() no sabe leer «A1») y el número debe terminar en borde de palabra."""
    if apendice:
        return re.compile(r"^\s*(tabla|table|figura|figure)\s+(\d+|(?-i:[IVXLC]+)|(?-i:[A-Z]\d+))\s*([.:—–-]?)\s*(.*)$", re.I | re.S)
    return re.compile(r"^\s*(tabla|table|figura|figure|fig\.)\s*(\d+|(?-i:[IVXLC]+))\b\s*([.:—–-]?)\s*(.*)$", re.I | re.S)


RE_ROT_NUM = rotulo_re(True)  # «Tabla 1», «Tabla A1» (apéndice)
RE_NOTA = re.compile(r"^\s*(nota|note)\s*([.:])", re.I)
RE_NOTA_SIGUE = re.compile(r"^\s*(?:[a-z]\s|[*\u2020\u2021\u2022]|p\s*[<>=])")  # nota específica o de probabilidad
RE_PIE = re.compile(r"\b(elaboración propia|fuente:|source:|adaptado de|tomado de|adapted from)", re.I)


def es_vacio(p):
    """Párrafo sin texto que no lleva imagen, salto de página ni salto de sección (espaciador)."""
    return not p["texto"].strip() and not p.get("imagen") and not p.get("salto_antes") and not p.get("sect")


def nivel_estilo(p):
    """Nivel 1-5 de un párrafo con estilo «Heading N»/«Título N»; 0 si no es encabezado (Title no cuenta)."""
    m = re.match(r"(?:heading|t[ií]tulo)\s*(\d)\b", p.get("estilo", "").lower())
    if m:
        return int(m.group(1)) if not p.get("en_tabla") else 0
    return p.get("nivel_base", 0) if not p.get("en_tabla") else 0  # estilo propio basado en un encabezado (basedOn)


RE_NOTA_AUTOR = re.compile(r"(?:author(?:s)?(?:['’]s?)?\s+note|nota\s+(?:del|de\s+la|de\s+los)\s+autor\w*)\s*$", re.I)


def fin_portada(pars):
    """Índice donde termina la portada. Si hay un salto de página antes de cualquier párrafo largo de cuerpo
    (la nota del autor de los trabajos profesionales va en la portada y sí puede ser larga), la portada llega hasta
    ese salto: incluye el título aunque lleve estilo de encabezado. Si no, vale el primer encabezado o salto;
    0 si no hay portada (un párrafo largo de cuerpo antes de ellos significa que el documento no tiene portada)."""
    nota = False
    for k, p in enumerate(pars):
        if p.get("en_tabla"):
            continue
        if p.get("salto_antes"):
            return k
        if nivel_estilo(p) and RE_NOTA_AUTOR.match(p["texto"].strip()):
            nota = True
        if len(p["texto"]) > 80 and not nota and "CENTER" not in p["alineacion"]:
            break  # (un título largo centrado no es cuerpo)
    for k, p in enumerate(pars):
        if p.get("en_tabla"):
            continue
        if p.get("salto_antes") or nivel_estilo(p):
            return k
        if len(p["texto"]) > 80 and "CENTER" not in p["alineacion"]:
            return 0  # (igual que arriba: un título largo centrado de la portada no es cuerpo)
    return 0


def marca(p, k, a=0, b=GRANDE, solo_alnum=False):
    """True si todos los caracteres no blancos de [a, b) del texto de los runs tienen la marca k (1 cursiva, 2 negrita).
    Con solo_alnum se ignora la puntuación (una coma dentro de un título en cursiva no se ve como error)."""
    pos, algun = 0, False
    for t in p.get("tramos", ()):
        for ch in t[0]:
            if a <= pos < b and not ch.isspace() and (ch.isalnum() or not solo_alnum):
                algun = True
                if not t[k]:
                    return False
            pos += 1
    return algun


def plano(p):
    return "".join(t[0] for t in p.get("tramos", ())) or p["texto"]


def es_nota(todos, p, prof=0):
    """Nota de tabla o figura: «Nota.»/«Note.», o párrafo sin sangría que sigue a una tabla o a otra nota
    (las notas generales, de nota específica «a …» y de probabilidad «* p < .05» van una por párrafo)."""
    if RE_NOTA.match(p["texto"]):
        return True
    if prof > 3 or p["sangria1"] > 0.4 or p.get("es_titulo") or nivel_estilo(p):
        return False  # un encabezado nunca es nota y corta la cadena (el texto bajo él no hereda la exención)
    j = p["i"] - 1
    while j >= 0 and es_vacio(todos[j]) and not todos[j].get("en_tabla"):
        j -= 1
    if j < 0:
        return False
    q = todos[j]
    if q.get("en_tabla"):
        return True
    # tras otra nota solo siguen notas específicas («a …», «b …») o de probabilidad («* p < .05»), una por párrafo
    return bool(RE_NOTA_SIGUE.match(p["texto"])) and es_nota(todos, q, prof + 1)


def vacio_legitimo(todos, p):
    """Párrafo vacío que no es un espaciador entre párrafos de texto: los que cierran una página (antes de un salto de
    página o al final del documento) y la línea en blanco que separa una tabla o figura del texto (APA 7.4/7.5)."""
    a = p["i"]
    while a > 0 and es_vacio(todos[a - 1]) and not todos[a - 1].get("en_tabla"):
        a -= 1
    b = p["i"]
    while b + 1 < len(todos) and es_vacio(todos[b + 1]) and not todos[b + 1].get("en_tabla"):
        b += 1
    ant = todos[a - 1] if a > 0 else None
    sig = todos[b + 1] if b + 1 < len(todos) else None
    if sig is None or sig.get("salto_antes") or sig.get("sect"):
        return True
    if ant is not None and abs(ant["sangria1"] - 0.5) > TOL:
        return True  # no separa párrafos de texto corrido (listas, entradas con sangría francesa, líneas sueltas)
    for q in (ant, sig):
        if q is None:
            continue
        if q.get("en_tabla") or q.get("imagen") or RE_ROT_NUM.match(q["texto"].strip()) or RE_NOTA.match(q["texto"]):
            return True
    return False


def espaciado_apa(todos, cuerpo, fin_p):
    """APA-005: sin espacio antes/después de párrafos ni párrafos vacíos como espaciadores."""
    H = []
    ult = next((p for p in reversed(todos) if p["texto"].strip() and not p.get("en_tabla")), None)
    con = [p for p in cuerpo if (p.get("esp_antes", 0) > TOL_PT or (p.get("esp_despues", 0) > TOL_PT and p is not ult))
           and not es_nota(todos, p)]  # el espacio tras el último párrafo no separa nada; las notas de tabla/figura tienen el suyo
    if con:
        p = con[0]
        H.append(Hallazgo("APA-005", "menor", ubic(p),
                          f"{len(con)} de {len(cuerpo)} párrafos de cuerpo con espacio antes/después "
                          f"(p. ej. antes {p['esp_antes']:.0f} pt, después {p['esp_despues']:.0f} pt)",
                          "espacio 0 pt antes y después de cada párrafo; el interlineado doble separa los párrafos"))
    vacios = [p for p in todos[fin_p:] if not p.get("en_tabla") and es_vacio(p) and not vacio_legitimo(todos, p)]
    if vacios:
        H.append(Hallazgo("APA-005", "menor", ubic(vacios[0]), f"{len(vacios)} párrafos vacíos usados como espaciador",
                          "quitar los párrafos vacíos; usar saltos de página o formato de párrafo"))
    return H


# «Introducción» en español es una extensión por convención, no regla APA (checklist APA-031): el corpus de pruebas, el ejemplo
# y /estructura la usan, así que solo se juzga el «Introduction» oficial de APA 2.26.
INTRO_PROHIBIDA = ("introduction",)
RESUMENES = {"resumen", "abstract", "resumen ejecutivo", "palabras clave", "keywords", "key words", "summary", "sumario"}


def encabezados_apa(todos, fin_p, refs_titulo, entradas, interlineado_enc=2.0):
    """APA-025..029 (formato por nivel), APA-030 (sin numeración), APA-033 (doble espacio, sin líneas en blanco).
    interlineado_enc: el que exige APA-033 (2.0; el de `formato.interlineado` si el perfil de equipo lo declara)."""
    H = []
    ids_ent = {id(e) for e in entradas}
    heads = []
    for p in todos[fin_p:]:
        n = nivel_estilo(p)
        if not n or not p["texto"].strip() or id(p) in ids_ent or p is refs_titulo:
            continue
        if titulo_limpio(p["texto"]) in TITULOS_REF:
            continue  # el rótulo de la lista lo cubren APA-059 / APA-013
        heads.append((n, p))
    ids = {1: "APA-025", 2: "APA-026", 3: "APA-027", 4: "APA-028", 5: "APA-029"}
    mal = {k: [] for k in ids}
    for n, p in heads:
        al = p["alineacion"]
        centro = "CENTER" in al
        izq = not any(x in al for x in ("CENTER", "RIGHT", "JUSTIFY", "DISTRIBUTE"))
        neg, cur = marca(p, 2), marca(p, 1)
        f = []
        if n == 1:
            f += (["no centrado"] if not centro else []) + (["sin negrita"] if not neg else [])
        elif n in (2, 3):
            f += (["no alineado a la izquierda"] if not izq else []) + (["sin negrita"] if not neg else [])
            f += ["sin cursiva"] if n == 3 and not cur else []
        else:
            f += ["sin negrita"] if not neg else []
            f += ["sin cursiva"] if n == 5 and not cur else []
            f += ["sin sangría"] if max(p["sangria1"], p["sangria_izq"]) < 0.4 else []
            f += ["sin punto final"] if not p["texto"].rstrip().endswith(".") else []
            f += ["en párrafo aparte: el texto debe seguir en la misma línea"]
        if f:
            mal[n].append((p, f))
    for p in todos[fin_p:]:  # encabezados «en línea»: negrita (y cursiva) terminada en punto, texto a continuación
        tr = p.get("tramos")
        if (not tr or p.get("en_tabla") or id(p) in ids_ent or nivel_estilo(p) or p.get("numerado") or p is refs_titulo):
            continue
        k, pre = 0, ""
        while k < len(tr) and (tr[k][2] or not tr[k][0].strip()):
            pre += tr[k][0]
            k += 1
        pr, resto = pre.strip(), "".join(t[0] for t in tr[k:]).strip()
        if (len(pr) < 3 or len(pr.split()) > 12 or not pr.endswith(".") or ". " in pr[:-1] or len(resto) < 15
                or re.match(r"(tabla|figura|table|figure|nota|note)\b", pr, re.I) or not marca(p, 2, 0, len(pre))):
            continue
        n = 5 if marca(p, 1, 0, len(pre)) else 4
        if max(p["sangria1"], p["sangria_izq"]) < 0.4:
            mal[n].append((p, ["encabezado en línea sin sangría"]))
    for n, lst in mal.items():
        if lst:
            p, f = lst[0]
            H.append(Hallazgo(ids[n], "mayor", ubic(p), f"{len(lst)} encabezados de nivel {n} mal formados; p. ej. «{p['texto'][:40]}»: {', '.join(f)}",
                              {1: "nivel 1: centrado, negrita, title case", 2: "nivel 2: izquierda, negrita, title case",
                               3: "nivel 3: izquierda, negrita cursiva, title case",
                               4: "nivel 4: con sangría, negrita, termina en punto y el texto sigue en la misma línea",
                               5: "nivel 5: con sangría, negrita cursiva, termina en punto y el texto sigue en la misma línea"}[n]))
    num = [p for n, p in heads if p.get("numerado") or RE_NUM_ENC.match(p["texto"])]
    if num:
        H.append(Hallazgo("APA-030", "mayor", ubic(num[0]), f"{len(num)} de {len(heads)} encabezados numerados o con letra; p. ej. «{num[0]['texto'][:40]}»",
                          "quitar numeración y letras de los encabezados"))
    feos = []
    for n, p in heads:
        k, f = p["i"], []
        # El espacio antes de un encabezado que sigue a una tabla, imagen o nota es el que propone EST-014
        # (maquetacion.py, APA tablas-figuras opción 1: línea en blanco a doble espacio tras la tabla o figura): no se marca.
        tras_obj = k > 0 and (todos[k - 1].get("en_tabla") or todos[k - 1].get("imagen") or es_nota(todos, todos[k - 1]))
        if (p.get("esp_antes", 0) > TOL_PT and not tras_obj) or p.get("esp_despues", 0) > TOL_PT:
            f.append(f"espacio antes {p['esp_antes']:.0f} pt / después {p['esp_despues']:.0f} pt")
        ls = p["interlineado"]
        if not (isinstance(ls, (int, float)) and abs(ls - interlineado_enc) < 0.05):
            f.append(f"interlineado {ls}")
        if (k > 0 and not todos[k - 1].get("en_tabla") and es_vacio(todos[k - 1]) and not vacio_legitimo(todos, todos[k - 1])) or \
                (k + 1 < len(todos) and not todos[k + 1].get("en_tabla") and es_vacio(todos[k + 1]) and not vacio_legitimo(todos, todos[k + 1])):
            f.append("línea en blanco adyacente")
        if f:
            feos.append((p, f))
    if feos:
        p, f = feos[0]
        H.append(Hallazgo("APA-033", "menor", ubic(p), f"{len(feos)} de {len(heads)} encabezados; p. ej.: {', '.join(f)}",
                          "encabezados a doble espacio, sin espacio extra ni líneas en blanco antes o después"))
    prev = 0  # APA-024: cada nivel subdivide al anterior sin saltar niveles (1 -> 3 salta el 2)
    for n, p in heads:
        if prev and n > prev + 1:
            H.append(Hallazgo("APA-024", "mayor", ubic(p), f"encabezado de nivel {n} tras uno de nivel {prev}: «{p['texto'][:40]}»",
                              f"usar el nivel {prev + 1}: los niveles no se saltan"))
            break
        prev = n
    unicos = []  # APA-032: un encabezado con exactamente un subencabezado del nivel siguiente
    for k, (n, p) in enumerate(heads):
        hijos = []
        for m_, q in heads[k + 1:]:
            if m_ <= n:
                break
            if m_ == n + 1:
                hijos.append(q)
        if len(hijos) == 1:
            unicos.append((p, hijos[0]))
    if unicos:
        p, q = unicos[0]
        H.append(Hallazgo("APA-032", "menor", ubic(p), f"{len(unicos)} secciones con un solo subencabezado; p. ej. «{p['texto'][:30]}» solo tiene «{q['texto'][:30]}»",
                          "una sección con subencabezados lleva al menos dos: agregar otro o quitar el subencabezado"))
    # APA-031: el texto no empieza con «Introducción» (APA 2.26; en español es convención, no regla oficial)
    cuerpo_h = [p for n, p in heads if titulo_limpio(p["texto"]) not in RESUMENES]
    if cuerpo_h and titulo_limpio(cuerpo_h[0]["texto"]) in INTRO_PROHIBIDA:
        H.append(Hallazgo("APA-031", "mayor", ubic(cuerpo_h[0]), f"el primer encabezado del texto es «{cuerpo_h[0]['texto'][:40]}»",
                          "quitar el encabezado: el texto empieza sin rótulo (el título del trabajo hace de encabezado)"))
    return H


def previos(todos, k, n=2):
    """Hasta n párrafos no vacíos de cuerpo justo antes del índice k (se detiene en una tabla)."""
    out, j = [], k - 1
    while j >= 0 and len(out) < n:
        q = todos[j]
        if q.get("en_tabla"):
            break
        if not es_vacio(q) and (q["texto"].strip() or q.get("imagen")):
            out.append(q)
        j -= 1
    return out


def siguiente(todos, k):
    j = k + 1
    while j < len(todos):
        q = todos[j]
        if q.get("en_tabla"):
            return None
        if q["texto"].strip():
            return q
        j += 1
    return None


def tablas_figuras_apa(todos, fin_p):
    """APA-089 (número en negrita sobre el título, ambos encima), APA-093 (sin bordes verticales), APA-094 («Nota.» en cursiva)."""
    H = []
    sin_num, sin_neg, sin_titulo, mismo_renglon, bajo_img, notas_mal, pies = [], [], [], [], [], [], []
    verticales, total_tab = [], 0
    objetos = []  # (tipo, párrafo de arranque, párrafo de fin)
    ultimo = {}
    for p in todos:
        if p.get("tabla") is not None:
            ultimo[p["tabla"]] = p
    for p in todos[fin_p:]:
        if p.get("tabla_inicio"):
            objetos.append(("tabla", p, ultimo[p["tabla"]]))
            total_tab += 1
            if p["tabla_info"]["vertical"]:
                verticales.append(p)
        elif p.get("imagen") and not p.get("en_tabla") and (not p["texto"].strip() or RE_ROT_NUM.match(p["texto"])):
            objetos.append(("figura", p, p))
    for tipo, ini, fin in objetos:
        pref = "tab" if tipo == "tabla" else "fig"
        nombre = f"figura ({ini['texto'][:30] or 'imagen'})" if tipo == "figura" else f"tabla {ini['tabla']}"
        rot, pos, mm = None, 0, None
        m0 = RE_ROT_NUM.match(ini["texto"].strip()) if tipo == "figura" else None
        if m0 and m0.group(1).lower().startswith(pref):
            rot, mm = ini, m0   # el número comparte párrafo con la imagen: el título no puede ir entre ambos
        else:
            for pos, q in enumerate(previos(todos, ini["i"], 2)):
                m1 = RE_ROT_NUM.match(plano(q).strip().split("\n")[0].strip())  # el salto de página puede ir antes del rótulo
                if m1 and m1.group(1).lower().startswith(pref):
                    rot, mm = q, m1
                    break
        if rot is None:
            sin_num.append((tipo, ini, nombre))
            continue
        linea1 = plano(rot).split("\n")[0].strip()
        if not marca(rot, 2, 0, len(plano(rot)) - len(plano(rot).lstrip()) + mm.end(2)):
            sin_neg.append((tipo, rot, nombre))
        if mm.group(4):
            mismo_renglon.append((tipo, rot, nombre))
        elif "\n" in plano(rot).strip() and plano(rot).strip().split("\n", 1)[1].strip():
            pass  # número y título en dos líneas del mismo párrafo
        elif rot is ini or pos == 0:
            (bajo_img if tipo == "figura" else sin_titulo).append((tipo, rot, nombre))
        sig = siguiente(todos, fin["i"])
        if sig is not None:
            m = RE_NOTA.match(sig["texto"])
            if m:
                if not marca(sig, 1, 0, m.end(1)):
                    notas_mal.append((tipo, sig, nombre))
            elif RE_PIE.search(sig["texto"][:200]) and not RE_ROT_NUM.match(sig["texto"]):
                pies.append((tipo, sig, nombre))
    def una(id_, sev, lst, evid, corr):
        if lst:
            t, q, n = lst[0]
            H.append(Hallazgo(id_, sev, ubic(q), f"{len(lst)} casos; p. ej. {n}: {evid}", corr))
    una("APA-089", "mayor", sin_num, "sin «Tabla N»/«Figura N» encima", "añadir el número («Tabla 1»/«Figura 1») en negrita sobre el título")
    una("APA-089", "mayor", sin_neg, "el número no está en negrita", "poner el número en negrita")
    una("APA-089", "mayor", mismo_renglon, "número y título en el mismo renglón", "número en una línea y el título en la línea siguiente")
    una("APA-089", "mayor", sin_titulo, "falta el título entre el número y la tabla", "título en cursiva en la línea siguiente al número, encima de la tabla")
    una("APA-089", "mayor", bajo_img, "el título no está entre el número y la figura (va debajo o falta)", "número y título encima de la figura")
    if verticales:
        p = verticales[0]
        H.append(Hallazgo("APA-093", "mayor", ubic(p), f"{len(verticales)} de {total_tab} tablas con bordes verticales/rejilla",
                          "solo líneas horizontales: arriba, bajo el encabezado y abajo; sin bordes verticales"))
    una("APA-094", "menor", notas_mal, "la etiqueta «Nota.» no está en cursiva", "«Nota.» en cursiva")
    una("APA-094", "menor", pies, "pie de tabla/figura sin «Nota.»", "empezar la nota con «Nota.» en cursiva (p. ej. «Nota. Elaboración propia…»)")
    return H


# ---------------------------------------------------------------- citas APA
RE_PAR =re.compile(r"\(([^()]*?\b(?:(?:1[5-9]\d{2}|20\d{2})[a-z]?|n\.d\.(?:-[a-z])?|s\.f\.(?:-[a-z])?)(?:,[^()]*)?)\)")  # admite localizador: (Autor, 2016, p. 4)
RE_NARR = re.compile(r"([A-ZÁÉÍÓÚÑ][\w'’\-]+(?:\s(?:&|and|y)\s[A-ZÁÉÍÓÚÑ][\w'’\-]+(?:\s[A-ZÁÉÍÓÚÑ][\w'’\-]+)*|\set al\.)?)\s\((\d{4}[a-z]?(?!\d)|n\.d\.|s\.f\.)")  # (?!\d): «Ana Pérez (21330001)» (número de control) no es un año
_AP = r"[A-ZÁÉÍÓÚÑ][\w'’\-]+(?:\s(?:de la|de|del|van der|van|von)?\s?[A-ZÁÉÍÓÚÑ][\w'’\-]+)*"
RE_VARIOS = re.compile(rf"({_AP})((?:,\s{_AP})+),?\s(?:&|y|and)\s{_AP},\s(\d{{4}}[a-z]?|n\.d\.|s\.f\.)")
RE_AUTOR_AÑO = re.compile(r"([A-ZÁÉÍÓÚÑ][\w'’\-]+(?:\s[A-ZÁÉÍÓÚÑ][\w'’\-]+)*)(?:\set al\.|\s(?:&|and|y)\s[A-ZÁÉÍÓÚÑ][\w'’\-]+(?:\s[A-ZÁÉÍÓÚÑ][\w'’\-]+)*)?,\s(\d{4}[a-z]?|n\.d\.|s\.f\.)")


def sin_sigla(autor):
    m = re.match(r"(.*?)\s*\[([^\]]+)\]\s*$", autor.strip())
    return (m.group(1), m.group(2)) if m else (autor.strip(), None)


def grupos_apa(cuerpo, entradas):
    """Autores grupales: nombre completo -> última palabra (la clave de la lista) y sus abreviaturas
    (APA 8.21: «(Organización Mundial de la Salud [OMS], 2021)» y luego «(OMS, 2021)»)."""
    mapa = {}
    for e in entradas:
        m = re.match(r"\s*([^,(]+?)\.\s*\((?:\d{4}|n\.d\.|s\.f\.)", e["texto"])
        if m and len(m.group(1).split()) >= 2:
            nombre, sigla = sin_sigla(m.group(1))
            mapa[nombre] = nombre.split()[-1]
            if sigla:  # «Suprema Corte de Justicia de la Nación [SCJN]. (2024)»: la sigla no va en la lista (APA 9.11), pero cuenta
                mapa[sigla] = nombre.split()[-1]
    texto = " ".join(p["texto"] for p in cuerpo)
    for nombre, clave_ in list(mapa.items()):
        for m in re.finditer(re.escape(nombre) + r"\s*(?:\[|\()([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ0-9/&\-]+)[\],]", texto):
            mapa[m.group(1)] = clave_
    return mapa


def normalizar_grupos(t, mapa):
    for nombre in sorted(mapa, key=len, reverse=True):
        clave_ = mapa[nombre]
        t = re.sub(re.escape(nombre) + r"\s*\[[A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ0-9/&\-]+\]", clave_, t)            # (Nombre [SIGLA], 2020)
        t = re.sub(re.escape(nombre) + r"\s*\(([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ0-9/&\-]+), ", clave_ + " (", t)  # Nombre (SIGLA, 2020)
        t = re.sub(r"\b" + re.escape(nombre) + r"\b", clave_, t)
    return t


RE_VEASE_TAMBIEN = re.compile(r";\s*(?:see also|v[ée]ase tambi[ée]n|v[ée]ase adem[áa]s)\s", re.I)
RE_REVISTA = re.compile(r"(?:^|[.?!]\s)([^.?!]+?),\s(\d{1,4})(\([^)]*\))?,\s(?:\d+\s?[–-]\s?\d+|Article\b|Art\.|e\d)")
RE_PREFIJO = re.compile(r"^\s*(?:(?:véase|ver|see|cf\.|p\.\s?ej\.|e\.\s?g\.|por ejemplo)[,\s]+)+", re.I)
RE_NARR_DOS = re.compile(r"\b([A-ZÁÉÍÓÚÑ][\w'’\-]+)\s(&|y|and)\s([A-ZÁÉÍÓÚÑ][\w'’\-]+)\s\((\d{4}[a-z]?)")
RE_AUTOR_LISTA = re.compile(r"[A-ZÁÉÍÓÚÑ][\w'’\-]+(?:\s[A-ZÁÉÍÓÚÑ][\w'’\-]+)*,\s(?:[A-ZÁÉÍÓÚÑ]\.(?:\s?-?[A-ZÁÉÍÓÚÑ]\.)*)")
RE_NARR_COMA = re.compile(r"\b([A-ZÁÉÍÓÚÑ][\w'’\-]+(?:\s(?:et al\.|(?:&|y|and)\s[A-ZÁÉÍÓÚÑ][\w'’\-]+))?),\s(\d{4}[a-z]?),\s+(?=[a-záéíóúñ]{3,}\b(?!\.))")
RE_SIN_AÑO = re.compile(r"\b(?:1[5-9]\d{2}|20\d{2})[a-z]?\b|n\.d\.|s\.\s?f\.")
RE_LOCALIZADOR = re.compile(r"([A-ZÁÉÍÓÚÑ][\w'’\-]*(?:\s+et al\.)?),\s*((?:arts?\.|artículos?|caps?\.|capítulos?|pp?\.|párr\.|secc?\.|fr\.|fracc\.)\s*[^;]*)$")


def hay_marca(p, k, a, b):
    """True si algún carácter no blanco de [a, b) tiene la marca k (1 cursiva, 2 negrita)."""
    pos = 0
    for t in p.get("tramos", ()):
        for ch in t[0]:
            if a <= pos < b and not ch.isspace() and t[k]:
                return True
            pos += 1
    return False


def revistas_cursiva(entradas):
    """APA-072: en artículos de revista («Revista, 7(4), 1–10» / «Revista, 10, Article e5») la revista y el volumen
    van en cursiva y el número entre paréntesis no."""
    mal = []
    for e in entradas:
        if not e.get("tramos"):
            continue
        s = plano(e)
        m = RE_REVISTA.search(s)
        if not m:
            continue
        f = []
        if not marca(e, 1, *m.span(1), solo_alnum=True):
            f.append("revista sin cursiva")
        if not marca(e, 1, *m.span(2), solo_alnum=True):
            f.append("volumen sin cursiva")
        if m.group(3) and hay_marca(e, 1, *m.span(3)):
            f.append("número entre paréntesis en cursiva")
        if f:
            mal.append((e, f, m.group(0).strip(". ")))
    if not mal:
        return []
    e, f, ev = mal[0]
    return [Hallazgo("APA-072", "mayor", ubic(e), f"{len(mal)} entradas de revista; p. ej. «{ev[:70]}»: {', '.join(f)}",
                     "revista y volumen en cursiva; número entre paréntesis en redonda")]


def orden_alfabetico(dentro, grupos):
    """APA-043: devuelve (anterior, actual) si dos obras de un paréntesis múltiple no están en orden alfabético
    (letra por letra, por apellido del primer autor; mismo autor: por año). Ignora prefijos («véase», «p. ej.») y siglas."""
    claves_grupo = set(grupos.values())
    previa = None
    for parte in dentro.split(";"):
        m = RE_AUTOR_AÑO.match(RE_PREFIJO.sub("", parte).strip())
        if not m:
            continue
        a = m.group(1)
        if (a.isupper() and len(a) >= 2) or a in claves_grupo:
            continue  # siglas y autores grupales: se ordenan por su nombre completo, no verificable aquí
        k = (re.sub(r"[^a-z]", "", sin_acentos(a).lower()), m.group(2), m.group(0)[:m.start(2)].strip())
        if previa:
            if k[0] < previa[0]:
                return previa, k, a
            if k[0] == previa[0] and k[2] == previa[2] and k[1][:4].isdigit() and previa[1][:4].isdigit() and k[1][:4] < previa[1][:4]:
                return previa, k, a
        previa = k
    return None


TOK_AÑO = r"(?:1[5-9]\d{2}|20\d{2})[a-z]?|n\.d\.(?:-[a-z])?|s\.\s?f\.(?:-[a-z])?"
RE_TOK_AÑO = re.compile(r"(?<![\w.])(" + TOK_AÑO + r")(?![\w])")
RE_CITADO_EN = re.compile(r"([A-ZÁÉÍÓÚÑ][\w'’\-]+(?:\s[A-ZÁÉÍÓÚÑ][\w'’\-]+)*)\s*\((?:" + TOK_AÑO + r")\s*[;,]\s*(?:as cited in|citado en)\s+([^()]*)\)")
RE_CITADO_EN_PAR = re.compile(r"\((?:[^()]*?[;,]\s*)?(?:as cited in|citado en)\s+")


def fuente_secundaria(t):
    """Fuente secundaria (APA 8.6): «Wolpe (1960; as cited in Peterson et al., 2011)» y «(Wolpe, 1960, as cited in …)».
    Solo la fuente que se leyó entra en la lista; la obra original no, así que no cuenta como cita."""
    t = RE_CITADO_EN.sub(r"\1 (\2)", t)
    t = RE_CITADO_EN_PAR.sub("(", t)
    return re.sub(r"\b(?:1[5-9]\d{2}|20\d{2})/((?:1[5-9]\d{2}|20\d{2})[a-z]?)\b", r"\1", t)  # «Dewey (1894/1971)»: cuenta la edición consultada


def palabras(s):
    return re.findall(r"[a-z0-9]+", sin_acentos(s).lower())


def contiene(ventana, nombre):
    """True si las palabras de «nombre» aparecen seguidas dentro de las de «ventana»."""
    n = len(nombre)
    return n > 0 and any(ventana[i:i + n] == nombre for i in range(len(ventana) - n + 1))


def base_año(tok):
    return re.sub(r"-[a-z]$", "", tok.lower().replace(" ", ""))


def info_entradas(entradas):
    """Por entrada: nombre del primer autor (apellido, o nombre completo de un autor grupal) y año con sufijo."""
    out = []
    for e in entradas:
        m = re.match(r"\s*(.+?)\s*\(\s*(" + TOK_AÑO + r")\s*[,)]", e["texto"])
        if not m:
            continue
        seg = re.sub(r"\s*\[[^\]]*\]", "", m.group(1)).strip()
        persona = bool(re.search(r",\s*[A-ZÁÉÍÓÚÑ]\.", seg))
        seg = seg.strip(" .,")
        out.append({"e": e, "nombre": palabras(seg.split(",")[0] if persona else seg), "año": m.group(2).lower().replace(" ", "")})
    return out


def entradas_citadas(cuerpo, info):
    """Emparejamiento por contexto, además de las regex de cita: cada año del texto (entre paréntesis, tras el nombre
    o suelto en la prosa: «In 1973, Bernstein and Borkovec created…», APA 8.11) se enlaza con la entrada cuyo año
    coincide y cuyo autor aparece justo antes (o, para el año en prosa, justo después). Rinde {id(párrafo): [(entrada,
    ventana de palabras)]}: sirve para dar por buenas las citas con posesivo («Dewey’s (1920)»), partículas
    («van der Linden»), autor grupal de varias palabras («Pew Research Center») o sufijo n.d.-a."""
    res = {}
    for p in cuerpo:
        t = fuente_secundaria(p["texto"])
        for m in RE_TOK_AÑO.finditer(t):
            tok = m.group(1).lower().replace(" ", "")
            antes = t[max(0, m.start() - 100):m.start()]
            narrativa = antes.rstrip().endswith("(")  # «Nombre (año)»: el autor va antes del paréntesis
            if narrativa:
                antes = antes.rstrip()[:-1]
            antes = re.split(r";|\)|(?<=[a-záéíóúñ0-9]{2})(?<!\bal)\.\s" + ("" if narrativa else r"|\("), antes)[-1]  # solo la cita o la oración propia
            despues = "" if narrativa else re.split(r"\)|(?<=[a-záéíóúñ0-9]{2})(?<!\bal)\.\s", t[m.end():m.end() + 100])[0]
            win = palabras(antes + " " + despues)
            for j in info:
                if (tok == j["año"] or ("-" not in tok and tok == base_año(j["año"]))) and contiene(win, j["nombre"]):
                    res.setdefault(id(p), []).append((j, win))
    return res


def citas_apa(cuerpo, entradas, con_layout, base_es_apa=True, anotada=False):
    H = []
    citas = []  # (apellido, año, párrafo)
    grupos = grupos_apa(cuerpo, entradas)
    primeros = {}  # (primer apellido, año) -> n.º de entradas: si se repite, «et al.» no distingue las obras
    for e in entradas:
        m = re.match(r"\s*([^,(]+?),.*?\((\d{4})[a-z]?[,)]", e["texto"])
        if m:
            k = (sin_acentos(m.group(1).split()[-1]).lower(), m.group(2))
            primeros[k] = primeros.get(k, 0) + 1
    ambiguas = {k for k, n in primeros.items() if n > 1}
    autores_entrada = {}  # (primer apellido, año) -> n.º de autores de la entrada (para «A y B (año)» con 3+ autores)
    for e in entradas:
        m = re.match(r"\s*(.+?)\s*\((\d{4})[a-z]?[,)]", e["texto"])
        if m:
            n = len(RE_AUTOR_LISTA.findall(m.group(1)))
            primero = re.match(r"\s*([^,(]+?),", m.group(1))
            if n and primero:
                autores_entrada[(sin_acentos(primero.group(1).split()[-1]).lower(), m.group(2))] = n
    info = info_entradas(entradas)
    enlaces = entradas_citadas(cuerpo, info)
    cubiertas = {id(j["e"]) for ls in enlaces.values() for j, _ in ls}
    for p in cuerpo:
        t = normalizar_grupos(fuente_secundaria(p["texto"]), grupos)
        for m in re.finditer(r"\bib[ií]d\b\.?", t, re.I):
            H.append(Hallazgo("APA-042", "mayor", ubic(p), t[max(0, m.start() - 15):m.end() + 5], "repetir la cita completa"))
            break
        for m in RE_PAR.finditer(t):
            dentro = m.group(1)
            if re.search(r"personal communication|comunicación personal", dentro, re.I):
                continue
            # tras «see also» / «véase también» las obras se ordenan aparte (APA 8.12)
            if ";" in dentro and any(orden_alfabetico(g, grupos) for g in RE_VEASE_TAMBIEN.split(dentro)):
                H.append(Hallazgo("APA-043", "mayor", ubic(p), "(" + dentro[:90] + ")",
                                  "ordenar las obras alfabéticamente por apellido del primer autor (mismo autor: por año)"))
            for parte in dentro.split(";"):
                mv = RE_VARIOS.search(parte)  # 3+ apellidos: debe ser «Primero et al.»
                if mv and (sin_acentos(mv.group(1).split()[-1]).lower(), mv.group(3).lower()) in ambiguas:
                    mv = None  # «Reschke, Walle, & Dukes, 2017»: et al. sería ambiguo; se listan los autores necesarios (APA 8.18)
                    continue
                if mv:
                    H.append(Hallazgo("APA-038", "mayor", ubic(p), mv.group(0), f"{mv.group(1)} et al., {mv.group(3)}"))
                    citas.append((mv.group(1).split()[-1], mv.group(3), p))
                    continue
                for a, y in RE_AUTOR_AÑO.findall(parte):
                    citas.append((a.split()[-1] if " " in a and not a.isupper() else a, y, p))
        for a, y in RE_NARR.findall(t):
            citas.append((a.split()[0], y, p))
        for m in RE_NARR_COMA.finditer(t):  # «Vaswani et al., 2017, propusieron»: narrativa mal formada
            antes = t[:m.start()]
            if antes.count("(") > antes.count(")") and re.search(r"(?:\(|;|véase|ver|see|e\.\s?g\.,|p\.\s?ej\.,)\s*$", antes, re.I):
                continue  # cita parentética legítima: «(Autor, 2020, capítulo 3)»
            if re.match(r"(?:cap[ií]tulo|secci[oó]n|section|chapter|tablas?|figuras?|p[aá]rrafo|p[aá]ginas?|apartado|ecuaci[oó]n)\b", t[m.end():]):
                continue
            H.append(Hallazgo("APA-036", "mayor", ubic(p), t[m.start():m.end() + 12],
                              f"cita narrativa: «{m.group(1)} ({m.group(2)}) …» (año entre paréntesis, sin comas)"))
        # «and» entre apellidos de una cita parentética («(Smith and Jones, 2020)»); no «(2012, 2013, and 2014)»
        RE_AND = r"\(\w[^()]*\band\s+[A-ZÁÉÍÓÚÑ][\w'’\-]+(?:\s+[A-ZÁÉÍÓÚÑ][\w'’\-]+)*(?:\s+et al\.)?,\s*(?:\d{4}[a-z]?|n\.d\.)[^()]*\)"
        if re.search(RE_AND, t):
            m = re.search(RE_AND, t)
            H.append(Hallazgo("APA-037", "mayor", ubic(p), m.group(0), "en cita parentética usar «&»"))
        else:  # decisión del usuario (18-nov): también en español la parentética lleva «&», no «y»
            m = re.search(r"\((?:[^()]*;\s*)?[A-ZÁÉÍÓÚÑ][\w'’-]+\s+y\s+[A-ZÁÉÍÓÚÑ][\w'’-]+,\s*(?:\d{4}[a-z]?|s\.\s?f\.|n\.d\.)", t)
            if m:
                H.append(Hallazgo("APA-037", "mayor", ubic(p), m.group(0) + ")", "en cita parentética usar «&» (también en español)"))
        for m in RE_NARR_DOS.finditer(t):  # «Levenson & Shensa (2016)» fuera de paréntesis
            antes = t[:m.start()]
            if antes.count("(") > antes.count(")"):
                continue
            a1, conj, a2, año = m.groups()
            if conj == "&":
                H.append(Hallazgo("APA-037", "mayor", ubic(p), m.group(0) + ")",
                                  f"en cita narrativa la conjunción va escrita: «{a1} y {a2} ({año})» («and» en inglés), no «&»"))
            n = autores_entrada.get((sin_acentos(a1).lower(), año[:4]))
            if n and n >= 3:
                H.append(Hallazgo("APA-038", "mayor", ubic(p), m.group(0) + ")",
                                  f"la obra tiene {n} autores: «{a1} et al. ({año})» (APA 8.17)"))

    lista = []
    doble_lista = False
    con_espacio, con_sigla = [], []
    for e in entradas:
        m = re.match(r"\s*([^,(]+?),.*?\((\d{4}[a-z]?|n\.d\.|s\.f\.)", e["texto"]) or \
            re.match(r"\s*([^.(]+?)\.\s*\((\d{4}[a-z]?|n\.d\.|s\.f\.)", e["texto"])
        if m:
            lista.append((sin_sigla(m.group(1))[0], m.group(2), e))
        ls = e.get("interlineado")
        if con_layout and base_es_apa and "fuentes" in e and not doble_lista and isinstance(ls, (int, float)) and abs(ls - 2.0) >= 0.05:
            H.append(Hallazgo("APA-004", "mayor", ubic(e), f"lista de referencias con interlineado {ls}", "interlineado doble"))
            doble_lista = True
        if con_layout and "fuentes" in e:
            if not e.get("numerado") and not (abs(e["sangria1"] + 0.5) < TOL and abs(e["sangria_izq"] - 0.5) < TOL):
                H.append(Hallazgo("APA-060", "mayor", ubic(e), f"sangría izq {e['sangria_izq']:.2f} in, primera línea {e['sangria1']:.2f} in",
                                  "sangría francesa de 0.5 in"))
                con_layout = False
            if e.get("esp_antes", 0) > TOL_PT or e.get("esp_despues", 0) > TOL_PT:
                con_espacio.append(e)  # APA-060: sin espacio extra entre entradas
        if re.search(r"^[^()]*?\[([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ0-9/&.\-]{1,14})\]\.?\s*\(", e["texto"]):
            con_sigla.append(e)  # APA-065: la sigla del autor grupal va solo en el texto (APA 9.11)
        if re.search(r"https?://(dx\.)?doi\.org/", e["texto"]) is None and re.search(r"\bdoi:\s*10\.", e["texto"], re.I):
            H.append(Hallazgo("APA-076", "mayor", ubic(e), re.search(r"doi:\s*\S+", e["texto"], re.I).group(0),
                              "DOI como https://doi.org/10.xxxx"))
        if re.search(r"\b(Retrieved from|Recuperado de|Accessed from)\b", e["texto"]):
            H.append(Hallazgo("APA-079", "mayor", ubic(e), "contiene «Retrieved from/Recuperado de»", "eliminar la frase"))
        if re.search(r"(https?://\S+|10\.\d{4,}/\S+)\.\s*$", e["texto"]):
            H.append(Hallazgo("APA-075", "mayor", ubic(e), e["texto"][-40:], "sin punto después de DOI o URL"))

    if con_espacio:
        e = con_espacio[0]
        H.append(Hallazgo("APA-060", "mayor", ubic(e),
                          f"{len(con_espacio)} de {len(entradas)} entradas con espacio entre párrafos (antes {e['esp_antes']:.0f} pt, después {e['esp_despues']:.0f} pt)",
                          "sin espacio extra entre entradas: 0 pt antes y después"))
    if con_sigla:
        e = con_sigla[0]
        H.append(Hallazgo("APA-065", "mayor", ubic(e),
                          f"{len(con_sigla)} entradas con sigla entre corchetes en el autor grupal; p. ej. «{e['texto'][:60]}»",
                          "nombre completo del grupo sin sigla en la lista; la sigla solo va en el texto"))
    H += revistas_cursiva(entradas)

    claves = [re.sub(r"^(?:the|an?|el|la|los|las)\s+", "", sin_acentos(x[0]).lower()) for x in lista]  # se ignora el artículo inicial (APA 9.44)
    for i in range(1, len(claves)):
        if claves[i] < claves[i - 1]:
            H.append(Hallazgo("APA-061", "mayor", ubic(lista[i][2]), f"«{lista[i][0]}» después de «{lista[i - 1][0]}»",
                              "ordenar alfabéticamente por la primera palabra"))
            break

    idx = {(sin_acentos(a.split(",")[0].split()[-1] if a else "").lower(), y.lower()) for a, y, _ in lista}
    idx_ap = {k[0] for k in idx}
    # APA-036: cita sin año de una obra que está en la lista con año: «(LFDA, art. 16)», «(Autor, p. 4)»
    texto_cuerpo = " ".join(p["texto"] for p in cuerpo)
    siglas = {sin_acentos(s).lower() for s in re.findall(r"\(([A-ZÁÉÍÓÚÑ]{2,}[A-Z0-9/\-]*),\s*(?:\d{4}|n\.d\.|s\.\s?f\.)", texto_cuerpo)}
    siglas |= {sin_acentos(s).lower() for s in grupos if s.isupper()}
    conocidas = idx_ap | siglas
    hay_ley = any(re.match(r"(Ley|Código|Constitución|Reglamento|Decreto)\b", a) for a, _, _ in lista)
    vistos_036 = set()
    for p in cuerpo:
        t = p["texto"]
        for m in re.finditer(r"\(([^()]*)\)", t):
            c = m.group(1)
            if RE_SIN_AÑO.search(c):
                continue
            ml = RE_LOCALIZADOR.match(c)
            sin_autor = hay_ley and re.match(r"arts?\.\s*\d", c)
            if ml and sin_sigla(ml.group(1))[0] and sin_acentos(ml.group(1).split()[0]).lower() in conocidas or sin_autor:
                if m.group(0) not in vistos_036:
                    vistos_036.add(m.group(0))
                    H.append(Hallazgo("APA-036", "mayor", ubic(p), m.group(0),
                                      "cita autor-fecha completa: (Autor, año, localizador)"))
    vistos = set()
    for a, y, p in citas:
        k = (sin_acentos(a).lower(), y.lower())
        if k in vistos:
            continue
        vistos.add(k)
        if k not in idx and any(base_año(j["año"]) == base_año(y) and set(palabras(a)) <= set(w) for j, w in enlaces.get(id(p), ())):
            continue  # el contexto enlaza la cita con una entrada (posesivo, partícula, autor grupal…)
        if k not in idx:
            parecido = [ap for ap, yy in idx if yy == k[1] and difflib.SequenceMatcher(None, ap, k[0]).ratio() >= 0.8]
            if k[0] in idx_ap:
                H.append(Hallazgo("APA-035", "crítica", ubic(p), f"{a}, {y}", "el año no coincide con el de la lista"))
            elif parecido:
                H.append(Hallazgo("APA-035", "crítica", ubic(p), f"{a}, {y}",
                                  f"el apellido no coincide con la lista («{parecido[0]}»)"))
            else:
                H.append(Hallazgo("APA-034", "crítica", ubic(p), f"{a}, {y}", "agregar la entrada a la lista o corregir la cita"))
    citadas = {k[0] for k in vistos}
    for a, y, e in lista:
        ap = sin_acentos(a.split(",")[0].split()[-1] if a else "").lower()
        if ap and ap not in citadas and id(e) not in cubiertas and not anotada:  # en una bibliografía anotada la entrada es la obra
            H.append(Hallazgo("APA-034", "crítica", ubic(e), f"{a} ({y}) no se cita en el texto",
                              "citarla o quitarla de la lista"))
    return H


# ---------------------------------------------------------------- APA: reglas finas de la lista, fechas en citas, apéndices
_MES = (r"(?:[Ee]nero|[Ff]ebrero|[Mm]arzo|[Aa]bril|[Mm]ayo|[Jj]unio|[Jj]ulio|[Aa]gosto|[Ss]e[p]?tiembre|[Oo]ctubre|[Nn]oviembre|"
        r"[Dd]iciembre|January|February|March|April|May|June|July|August|September|October|November|December)")
_AÑO4 = r"(?:1[5-9]\d{2}|20\d{2})"
_DIA_MES = rf"(?:\d{{1,2}}\s+(?:de\s+)?{_MES}|{_MES}\s+\d{{1,2}})"                 # «24 de julio», «July 24»
_FECHA_COMPLETA = rf"(?:{_MES}\s+\d{{1,2}},?\s+{_AÑO4}|\d{{1,2}}\s+(?:de\s+)?{_MES}(?:\s+de)?\s+{_AÑO4})"  # «March 3, 2020», «24 de julio de 2020»
_NOMBRE_CITA = r"[A-ZÁÉÍÓÚÑ][\w'’\-]+(?:\s+et al\.)?"
RE_FECHA_PAR = re.compile(r"\(\s*(?:" + _AÑO4 + r"[a-z]?|n\.\s?d\.(?:-[a-z])?|s\.\s?f\.(?:-[a-z])?|en prensa|in press)(?:[,–-][^()]*)?\)", re.I)
RE_FECHA_INVERTIDA = re.compile(rf"\(\s*(?:{_FECHA_COMPLETA}|\d{{1,2}}[/.\-]\d{{1,2}}[/.\-](?:19|20)?\d{{2}})\s*\)")
RE_AÑO_SIN_PAR = re.compile(rf"^[^()]{{2,160}}?(?:[A-ZÁÉÍÓÚÑ]\.|&)\s*,?\s+{_AÑO4}[a-z]?[.,]\s")
RE_CITA_FECHA_COMPLETA = [
    re.compile(rf"{_NOMBRE_CITA},\s*{_AÑO4}[a-z]?,\s*{_DIA_MES}"),             # (Pérez, 2020, 24 de julio)
    re.compile(rf"{_NOMBRE_CITA},\s*{_FECHA_COMPLETA}"),                        # (Smith, March 3, 2020)
]
RE_NARR_FECHA_COMPLETA = re.compile(rf"{_NOMBRE_CITA}\s*\(\s*(?:{_AÑO4}[a-z]?,\s*{_DIA_MES}|{_FECHA_COMPLETA})\s*\)")  # Pérez (2020, 24 de julio)
RE_SIN_FECHA_MAL = re.compile(rf"{_NOMBRE_CITA}(?:,|\s\()\s*(?:sin fecha|sin año|S/F|s/f|no date|undated)\s*[),;]")
RE_PERSONAL = re.compile(r"personal communication|comunicación personal", re.I)


def autores_y_fecha(texto):
    """(segmento de autores, token de fecha) de una entrada APA «Autores. (fecha). …»; None si no tiene la forma."""
    m = re.match(r"\s*(.+?)\s*\(\s*(" + TOK_AÑO + r"|en prensa|in press)\s*[,)]", texto, re.I)
    if not m:
        return None
    return re.sub(r"\s*\((?:[^()]*\bEds?\.|[^()]*\bHosts?|[^()]*\bTrads?\.|with\s[^()]*)[^()]*\)\.?", "", m.group(1)).strip(" ,"), m.group(2).lower().replace(" ", "")


def referencias_apa(entradas):
    """APA-066 (fecha entre paréntesis con punto, año primero), APA-063 (autores invertidos con «&»/«y» antes del último) y
    APA-044 (misma autoría y año: letras a, b)."""
    H = []
    sin_punto, sin_paren, invertida, sin_conj, iniciales_antes = [], [], [], [], []
    grupos = {}
    for e in entradas:
        t = e["texto"]
        ini = t[:260]
        m = RE_FECHA_PAR.search(ini)
        if m:
            if t[m.end():m.end() + 1] != ".":
                sin_punto.append((e, t[max(0, m.start() - 12):m.end() + 12]))
        elif RE_AÑO_SIN_PAR.match(ini):
            sin_paren.append((e, ini[:60]))
        mi = RE_FECHA_INVERTIDA.search(ini)
        if mi:
            invertida.append((e, mi.group(0)))
        af = autores_y_fecha(t)
        if not af:
            continue
        seg, tok = af
        if re.search(r",\s*[A-ZÁÉÍÓÚÑ]\.", seg):  # autores personas (no grupales)
            lista = list(RE_AUTOR_LISTA.finditer(seg))
            if len(lista) >= 2:
                if not re.search(r"(?:,\s*|\s)(?:&|y|and|e)\s|\.\s?\.\s?\.|…", seg):
                    sin_conj.append((e, seg[-60:]))
            if re.match(r"(?:[A-ZÁÉÍÓÚÑ]\.\s?){1,3}[A-ZÁÉÍÓÚÑ][\w'’\-]{2,}\s*(?:,|&|$)", seg) or \
                    re.search(r"(?:,|&)\s+(?:[A-ZÁÉÍÓÚÑ]\.\s?){1,3}[A-ZÁÉÍÓÚÑ][\w'’\-]{2,}\s*(?:,|&|$)", seg):
                iniciales_antes.append((e, seg[:60]))
        base = re.sub(r"-?[a-z]$", "", tok) if not tok.endswith(".") else tok
        grupos.setdefault((tuple(palabras(seg)), base), []).append((e, tok))
    if sin_punto:
        e, ev = sin_punto[0]
        H.append(Hallazgo("APA-066", "mayor", ubic(e), f"{len(sin_punto)} entradas sin punto tras la fecha; p. ej. «…{ev}…»",
                          "la fecha va entre paréntesis y seguida de punto: «(2020).»"))
    if sin_paren:
        e, ev = sin_paren[0]
        H.append(Hallazgo("APA-066", "mayor", ubic(e), f"{len(sin_paren)} entradas con la fecha sin paréntesis; p. ej. «{ev}»",
                          "fecha entre paréntesis y con punto después de los autores: «Autor, A. (2020).»"))
    if invertida:
        e, ev = invertida[0]
        H.append(Hallazgo("APA-066", "mayor", ubic(e), f"{len(invertida)} entradas con la fecha en otro orden; p. ej. {ev}",
                          "año primero: «(2020, 24 de julio)» o «(2020, July 24)»"))
    if sin_conj:
        e, ev = sin_conj[0]
        H.append(Hallazgo("APA-063", "mayor", ubic(e), f"{len(sin_conj)} entradas sin «&» ni «y» antes del último autor; p. ej. «…{ev}»",
                          "separar los autores con comas y poner «&» («y» en español) antes del último"))
    if iniciales_antes:
        e, ev = iniciales_antes[0]
        H.append(Hallazgo("APA-063", "mayor", ubic(e), f"{len(iniciales_antes)} entradas con las iniciales antes del apellido; p. ej. «{ev}»",
                          "autores invertidos: «Apellido, I. I.»"))
    for (_, base), lst in grupos.items():
        if len(lst) >= 2 and any(not re.search(r"(?:\d|\.-?)[a-z]$", tok) for _, tok in lst):
            e = next(e for e, tok in lst if not re.search(r"(?:\d|\.-?)[a-z]$", tok))
            H.append(Hallazgo("APA-044", "mayor", ubic(e), f"{len(lst)} entradas de la misma autoría y año ({base}) sin letra: «{e['texto'][:60]}»",
                              "añadir a, b, c tras el año (2020a, 2020b; n.d.-a) en la lista y en las citas, en el orden alfabético de los títulos"))
            break
    return H


def citas_fecha_apa(cuerpo):
    """APA-041: la cita lleva solo el año (no la fecha completa); sin fecha se escribe «n.d.» («s. f.»), no «sin fecha» ni «S/F»."""
    H = []
    for p in cuerpo:
        t = fuente_secundaria(p["texto"])
        hallado = None
        for m in re.finditer(r"\(([^()]*)\)", t):
            if RE_PERSONAL.search(m.group(1)):
                continue
            for rx in RE_CITA_FECHA_COMPLETA:
                mm = rx.search(m.group(1))
                if mm:
                    hallado = (mm.group(0), "en la cita solo el año: «(Autor, 2020)»; la fecha completa va en la lista de referencias")
                    break
            if hallado:
                break
        if not hallado:
            mm = RE_NARR_FECHA_COMPLETA.search(t)
            if mm and not RE_PERSONAL.search(mm.group(0)):
                hallado = (mm.group(0), "en la cita solo el año: «Autor (2020)»; la fecha completa va en la lista de referencias")
        if not hallado:
            mm = RE_SIN_FECHA_MAL.search(t)
            if mm:
                hallado = (mm.group(0), "sin fecha se escribe «n.d.» («s. f.» en español): «(Autor, s. f.)»")
        if hallado:
            H.append(Hallazgo("APA-041", "mayor", ubic(p), hallado[0], hallado[1]))
    return H


def citas_et_al_apa(cuerpo, entradas):
    """APA-039: una obra de uno o dos autores se cita con todos los nombres, no con «et al.» (se contrasta con su entrada)."""
    H = []
    n_aut, cuenta = {}, {}
    for e in entradas:
        af = autores_y_fecha(e["texto"])
        if not af or not re.search(r",\s*[A-ZÁÉÍÓÚÑ]\.", af[0]):
            continue
        seg = af[0]
        primero = re.match(r"\s*([^,(]+?),", seg)
        año = re.match(r"\d{4}", af[1])
        if not primero or not año:
            continue
        k = (sin_acentos(primero.group(1).split()[-1]).lower(), año.group(0))
        cuenta[k] = cuenta.get(k, 0) + 1
        n = max(len(RE_AUTOR_LISTA.findall(seg)), (seg.count(",") + 1) // 2)  # el recuento por comas no resta: un nombre mal escrito no cuenta como menos autores
        n_aut[k] = n
    ya = set()
    for p in cuerpo:
        t = fuente_secundaria(p["texto"])
        for m in re.finditer(r"(" + _NOMBRE_CITA.replace(r"(?:\s+et al\.)?", "") + r")\s+et al\.(?:,\s*|\s*\(\s*)(" + _AÑO4 + r")[a-z]?", t):
            k = (sin_acentos(m.group(1).split()[-1]).lower(), m.group(2))
            if n_aut.get(k, 9) <= 2 and cuenta.get(k) == 1 and k not in ya:
                ya.add(k)
                H.append(Hallazgo("APA-039", "mayor", ubic(p), m.group(0),
                                  f"la obra tiene {n_aut[k]} autor{'es' if n_aut[k] > 1 else ''} en la lista: nombrarlos todos en cada cita (no «et al.»)"))
    return H


RE_APENDICE = re.compile(r"^\s*(ap[ée]ndice|appendix)(?:\s+((?-i:[A-Z]|\d{1,2})))?\s*(?:[.:—–-].{0,80})?$", re.I)
RE_MENCION_APENDICE = re.compile(r"\b(ap[ée]ndices?|appendi(?:x|ces))(?:\s+((?-i:[A-Z]|\d{1,2})\b(?:\s*(?:,|y|e|and|&|a|to|–|-)\s*(?-i:[A-Z]|\d{1,2})\b)*))?", re.I)


def apendices_mencionados(pars, cuerpo, refs_titulo):
    """APA-015: cada apéndice (rótulo «Apéndice A» tras la lista de referencias) se menciona en el texto y en el orden en que aparecen."""
    if refs_titulo is None:
        return []
    rotulos = []
    for p in pars:
        if p["i"] <= refs_titulo["i"] or p.get("en_tabla"):
            continue
        t = p["texto"].strip()
        m = RE_APENDICE.match(t)
        if m and (len(t) <= 14 or nivel_estilo(p) or p.get("es_titulo") or marca(p, 2, 0, len(m.group(0)))):
            rotulos.append(((m.group(2) or "").upper(), p))
    if not rotulos:
        return []
    primera = {}
    for orden, p in enumerate(cuerpo):
        for m in RE_MENCION_APENDICE.finditer(p["texto"]):
            letras = re.findall(r"(?-i:[A-Z]|\d{1,2})\b", m.group(2) or "")
            if re.search(r"\s(?:a|to|–|-)\s", m.group(2) or "") and len(letras) == 2 and letras[0].isalpha() and letras[1].isalpha():
                letras = [chr(c) for c in range(ord(letras[0]), ord(letras[1]) + 1)]
            for x in letras or [""]:
                primera.setdefault(x.upper(), (orden, m.start()))
    H = []
    previo = None
    for letra, p in rotulos:
        pos = primera.get(letra, primera.get("") if len(rotulos) == 1 else None)
        if pos is None:
            H.append(Hallazgo("APA-015", "mayor", ubic(p), f"«{p['texto'].strip()[:40]}» no se menciona en el texto",
                              "mencionar cada apéndice en el texto («véase el Apéndice A»)"))
        elif previo and pos < previo[0]:
            H.append(Hallazgo("APA-015", "mayor", ubic(p), f"«{p['texto'].strip()[:40]}» se menciona antes que el «Apéndice {previo[1]}»",
                              "ordenar y rotular los apéndices en el orden en que se mencionan"))
        else:
            previo = (pos, letra)
    return H


# ---------------------------------------------------------------- citas IEEE
ABREV_IEEE = {"Ref", "Refs", "al", "Fig", "Figs", "Eq", "Eqs", "Sec", "Sect", "Secc", "Ch", "Cap", "Tab",
              "No", "Nos", "Vol", "Thm", "Ej", "ej", "cf", "vs", "pp", "p"}


def citas_ieee(cuerpo, entradas):
    H = []
    orden = []
    for p in cuerpo:
        t = p["texto"]
        for m in re.finditer(r"\]\s*[–—-]\s*\[", t):
            ini = re.search(r"\[(\d+)\]\s*$", t[:m.start() + 1])
            fin = re.match(r"\[(\d+)\]", t[m.end() - 1:])
            if ini and fin and int(ini.group(1)) < int(fin.group(1)) <= int(ini.group(1)) + 50:
                corr = ", ".join(f"[{n}]" for n in range(int(ini.group(1)), int(fin.group(1)) + 1))
            else:
                corr = "[1], [2], [3], [4]"
            H.append(Hallazgo("IEEE-004", "mayor", ubic(p), t[max(0, m.start() - 4):m.end() + 4],
                              "escribir todos los números: " + corr))
        for m in re.finditer(r"\[(\d+)\s*[,;–-]\s*(\d+)[^\]]*\]", t):
            nums = re.findall(r"\d+", m.group(0)) if re.fullmatch(r"\[[\d\s,;]+\]", m.group(0)) else []
            corr = ", ".join(f"[{n}]" for n in nums) if nums else "[1], [2]"
            H.append(Hallazgo("IEEE-003", "mayor", ubic(p), m.group(0), "un número por corchete: " + corr))
        for m in re.finditer(r"(?:[.;]\s?|[,:])\[\d+", t):  # ", [2]" y ": [2]" son válidos
            previa = re.search(r"(\w+)\.\s?$", t[max(0, m.start() - 12):m.start() + 1])
            if previa and previa.group(1) in ABREV_IEEE:  # «Ref. [1]», «et al. [4]», «Fig. [2]»
                continue
            H.append(Hallazgo("IEEE-002", "menor", ubic(p), t[max(0, m.start() - 10):m.end() + 2],
                              "el corchete va antes de la puntuación: … [n]."))
        for m in re.finditer(r"\[(\d+)(?:,\s*([^\]]+))?\]", t):
            orden.append((int(m.group(1)), p))
            if m.group(2) and re.fullmatch(r"[\d\s,;–-]+", m.group(2)):  # «[1, 2]» (IEEE-003): ambos cuentan para el orden
                orden += [(int(n), p) for n in re.findall(r"\d+", m.group(2))]
        for m in re.finditer(r"\(\s*[A-Z][\w\-]+(?: et al\.)?,\s*\d{4}\s*\)", t):
            H.append(Hallazgo("IEEE-001", "crítica", ubic(p), m.group(0), "usar cita numérica [n]"))
    nums_lista = []
    if any(e.get("numerado") for e in entradas):
        # lista numerada por Word ([1], [2]… generados por la numeración): solo los párrafos numerados son
        # entradas; el resto (texto de apoyo, párrafos vacíos) no lo es
        entradas = [e for e in entradas if e.get("numerado")]
    for pos, e in enumerate(entradas, 1):
        m = re.match(r"\s*\[(\d+)\]", e["texto"])
        if e.get("numerado") and not m:
            nums_lista.append(pos)  # número automático de Word
        elif not m:  # la entrada existe: cuenta por su posición para no duplicar como IEEE-012
            H.append(Hallazgo("IEEE-016", "menor", ubic(e), e["texto"][:30], "empezar la entrada con [n]"))
            nums_lista.append(pos)
        else:
            nums_lista.append(int(m.group(1)))
        tx = e["texto"]
        if re.search(r"https?://(dx\.)?doi\.org/10\.", tx) and "Available:" not in tx or re.search(r"\bDOI:\s", tx):
            H.append(Hallazgo("IEEE-037", "menor", ubic(e), re.search(r"(https?://(dx\.)?doi\.org/\S+|DOI:\s\S+)", tx).group(0),
                              "escribir «doi: 10.xxxx/…»"))
        if not re.search(r"https?://\S+$", tx.strip()) and not tx.strip().endswith("."):
            H.append(Hallazgo("IEEE-038", "menor", ubic(e), tx[-30:], "terminar la referencia en punto"))
        if re.search(r"Available:\s*\S+\.?\s*,?\s*doi:", tx):
            H.append(Hallazgo("IEEE-040", "mayor", ubic(e), tx[-60:], "DOI antes de «[Online]. Available: URL»"))
    if nums_lista and nums_lista != list(range(1, len(nums_lista) + 1)):
        H.append(Hallazgo("IEEE-017", "crítica", "lista de referencias", f"numeración {nums_lista[:12]}",
                          "numerar 1..n sin huecos ni repetidos (renumerar exige corregir las citas)"))
    existentes = set(nums_lista)
    primera = []
    faltantes = set()
    for n, p in orden:
        if n not in primera:
            primera.append(n)
        if existentes and n not in existentes and n not in faltantes:
            faltantes.add(n)
            H.append(Hallazgo("IEEE-012", "crítica", ubic(p), f"[{n}]", "la cita no tiene entrada en la lista"))
    if primera and primera != sorted(primera):
        k = next(i for i in range(len(primera)) if primera[i] != sorted(primera)[i])
        H.append(Hallazgo("IEEE-014", "menor", "texto", f"orden de primera aparición {primera[:12]} (primer desvío en posición {k + 1})",
                          "renumerar por orden de primera aparición"))
    sin_citar = existentes - set(primera)
    if sin_citar:
        H.append(Hallazgo("IEEE-013", "menor", "lista de referencias", f"no citadas: {sorted(sin_citar)[:10]}",
                          "citarlas o quitarlas"))
    return H


ROMANOS = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100}


def romano(s):
    n = 0
    for a, b in zip(s, s[1:] + " "):
        v = ROMANOS[a]
        n += -v if ROMANOS.get(b, 0) > v else v
    return n


RE_ROTULO = rotulo_re(False)
RE_MENCION = re.compile(r"\b(tablas?|tables?|figuras?|figures?|figs?\.)\s*((?:\d+|(?-i:[IVXLC]+))\b(?:\(\w\))?"
                        r"(?:\s*(?:,|y|e|and|a|to|–|-)\s*(?:\d+|(?-i:[IVXLC]+))\b(?:\(\w\))?)*)", re.I)


def tipo_rotulo(palabra):
    return "tabla" if palabra.lower().startswith("tab") else "figura"


def numero(tok):
    tok = re.sub(r"\(\w\)$", "", tok)
    return int(tok) if tok.isdigit() else romano(tok.upper())


def separar_rotulos(pars):
    """Reparte los párrafos en rótulos de tabla/figura [(tipo, número, párrafo, token del número, palabra)] y en
    párrafos de texto (str) donde cuentan las menciones. Una mención dentro de otra tabla o de una nota
    («Nota. …») no cuenta como mención en el texto."""
    rotulos, otros = [], []
    for p in pars:
        t = p["texto"].strip()
        m = None if p.get("en_tabla") else RE_ROTULO.match(t)
        es_pie = "caption" in p.get("estilo", "").lower() or "epígrafe" in p.get("estilo", "").lower()
        if m and (not m.group(4) or es_pie or (m.group(3) and len(t) < 250 and m.group(1).lower() == "fig.")
                  or (m.group(2).isupper() and not m.group(2).isdigit() and not m.group(3) and len(t) < 250)):
            rotulos.append((tipo_rotulo(m.group(1)), numero(m.group(2)), p, m.group(2), m.group(1)))
        elif p.get("en_tabla") or RE_NOTA.match(t):
            continue
        else:
            otros.append(t)
    return rotulos, otros


def numeros_mencion(m):
    """Números que nombra una mención de RE_MENCION («Tablas 2 a 4» -> 2, 3, 4), en orden de aparición."""
    nums = [numero(x) for x in re.findall(r"\d+|[IVXLC]+", m.group(2))]
    if re.search(r"\d\s*(?:a|to|–|-)\s*\d", m.group(2)) and len(nums) == 2:
        nums = list(range(nums[0], nums[1] + 1))
    return nums


def figuras_mencionadas(pars, textos_extra, base):
    """APA-091 / IEEE-093 (decisión del usuario, 18-nov: es regla): cada tabla y figura se menciona en el texto.
    Rótulo = párrafo «Tabla 1» / «Figura 1» solo (APA), o «Fig. 1. Texto» / «TABLE I» (IEEE), o estilo de pie.
    Las menciones cuentan en cualquier otro párrafo de texto; no cuentan las de celdas de tabla ni las de notas
    («Nota. …» / «Note. …»)."""
    rotulos, otros = separar_rotulos(pars)
    mencion = set()
    for t in otros + list(textos_extra):
        for m in RE_MENCION.finditer(t):
            tipo = tipo_rotulo(m.group(1))
            mencion |= {(tipo, n) for n in numeros_mencion(m)}
    H = []
    regla = "APA-091" if base == "apa7" else "IEEE-093"
    for tipo, n, p, _, _ in rotulos:
        if (tipo, n) not in mencion:
            H.append(Hallazgo(regla, "mayor", ubic(p), p["texto"][:60],
                              f"mencionar y explicar la {tipo} {n} en el texto antes o cerca de ella"))
    return H


def textos_tablas(path):
    if not path.lower().endswith(".docx"):
        return []
    return [c.text for t in abrir_docx(path).tables for r in t.rows for c in r.cells]


def decimales_ieee(cuerpo):
    """IEEE-119 (decisión del usuario, 18-nov): decimal siempre con cero inicial («0.25», no «.25»).
    Se reporta una vez por párrafo; no toca «.NET», versiones «v1.2», rangos «1..n» ni puntos suspensivos."""
    H = []
    for p in cuerpo:
        m = re.search(r"(?:^|(?<=[\s(=<>≤≥±+−\-–/]))\.\d+\b", p["texto"])
        if m:
            t = p["texto"]
            H.append(Hallazgo("IEEE-119", "mayor", ubic(p), t[max(0, m.start() - 12):m.end() + 6],
                              f"escribir el cero inicial: 0{m.group(0).lstrip()}"))
    return H


RE_INICIALES_ANTES = r"(?:[A-ZÁÉÍÓÚÑ]\.(?:-[A-ZÁÉÍÓÚÑ]\.)?\s?)+"
RE_APELLIDO_COMA = re.compile(r"[A-ZÁÉÍÓÚÑ][\w'’\-áéíóúñü]+,\s+(?:[A-ZÁÉÍÓÚÑ]\.(?:-[A-ZÁÉÍÓÚÑ]\.)?\s?)+(?=,|\s+and\b|\s+&|\s+y\s|\s*$)")
RE_Y_AUTORES = re.compile(r"(?<=[\w.,])(?:\s+&\s+(?=\S)|\s+y\s+(?=[A-ZÁÉÍÓÚÑ]))")  # «A, B & C», «A y B» entre autores
RE_COMILLA = re.compile("[“\"„«]")
RE_IBID = re.compile(r"\b(?:ibid(?:em)?|op\.\s?cit|loc\.\s?cit)\b", re.I)
RE_FIGURE_EN = re.compile(r"\b(Figures?)\s+(?=\d)")
RE_URL_ACCESO = re.compile(r"https?://(?!(?:dx\.)?doi\.org)\S+")
RE_ABSTRACT_CORRIDO = re.compile(r"^\s*(?:abstract|resumen)\s*(?:[—–:-]|\.\s)\s*", re.I)
RE_FIN_ABSTRACT = re.compile(r"^\s*(?:index terms|keywords?|palabras clave|términos de indización)\b", re.I)
RE_NUM_ENC_IEEE = re.compile(r"^\s*(?:[IVXL]+\.|\d{1,2}(?:\.\d{1,2})*\.?)\s+\S")


def segmento_autores(tx):
    """Texto de una entrada IEEE antes de la primera comilla (los autores), sin el «[n]» inicial; None si no hay título entre comillas."""
    tx = re.sub(r"^\s*\[\d+\]\s*", "", tx)
    m = RE_COMILLA.search(tx)
    return tx[:m.start()] if m else None


def autores_ieee(entradas):
    """IEEE-020 / IEEE-022 / IEEE-023 sobre el segmento de autores de cada entrada (solo las que tienen título entre comillas)."""
    H = []
    for e in entradas:
        seg = segmento_autores(e["texto"])
        if not seg or not seg.strip():
            continue
        m = RE_Y_AUTORES.search(seg)
        if m:
            H.append(Hallazgo("IEEE-023", "mayor", ubic(e), seg[max(0, m.start() - 20):m.end() + 12].strip(),
                              "escribir «and» antes del último autor, no «&» ni «y»"))
        if RE_APELLIDO_COMA.search(seg):
            H.append(Hallazgo("IEEE-020", "crítica", ubic(e), seg[:80].strip(),
                              "iniciales antes del apellido: «J. K. Apellido», no «Apellido, I.»"))
        elif not re.search(r"\bet al\b", seg):
            piezas = [x.strip() for x in re.split(r",|\band\b|&", seg) if x.strip()]
            n = sum(bool(re.match(RE_INICIALES_ANTES + r"\S", x)) for x in piezas)
            if n > 6:
                H.append(Hallazgo("IEEE-022", "mayor", ubic(e), seg[:80].strip(),
                                  f"{n} autores: escribir solo el primero seguido de «et al.»"))
    return H


def lista_ieee(entradas):
    """IEEE-034 (año o n.d.), IEEE-041 (URL con «[Online]. Available:») e IEEE-019 (obra repetida con dos números)."""
    H = []
    vistas = {}
    for e in entradas:
        tx = re.sub(r"^\s*\[\d+\]\s*", "", e["texto"])
        sin_enlaces = re.sub(r"https?://\S+|\bdoi:\s*\S+", " ", tx, flags=re.I)
        if not re.search(r"(?<![\d.])(?:19|20)\d{2}(?!\d)|\bn\.\s?d\.|\bs\.\s?f\.|to be published|submitted for publication"
                         r"|\bunpublished\b|\bin press\b|\bforthcoming\b|\ben prensa\b|\bno publicad", sin_enlaces, re.I):
            H.append(Hallazgo("IEEE-034", "mayor", ubic(e), tx[-60:], "agregar el año o «(n.d.)» si no tiene fecha"))
        url = RE_URL_ACCESO.search(tx)
        if url and not re.search(r"\[(?:online|en línea|en linea)[^\]]*\]|\b(?:available|disponible)\s*:", tx, re.I):
            H.append(Hallazgo("IEEE-041", "mayor", ubic(e), url.group(0), "agregar «[Online]. Available: URL»"))
        claves = []
        m = re.search(r"\b10\.\d{4,9}/[^\s,;]+", tx)
        if m:
            claves.append("doi:" + m.group(0).rstrip(".").lower())
        m = RE_COMILLA.search(tx)
        if m:
            t = re.split("[”\"“]", tx[m.end():])[0]
            t = re.sub(r"[^a-z0-9áéíóúñ]+", " ", t.lower()).strip()
            if len(t) >= 15:
                claves.append("t:" + t)
        if any(c in vistas for c in claves):
            H.append(Hallazgo("IEEE-019", "mayor", ubic(e), tx[:60], "la misma obra ya está en otra entrada: usar un solo número"))
        for c in claves:
            vistas.setdefault(c, e)
    return H


def abstract_ieee(cuerpo):
    """IEEE-061: el Abstract/Resumen tiene entre 150 y 250 palabras. Solo si existe el encabezado «Abstract»/«Resumen»
    (título solo o párrafo corrido «Abstract—…»); el texto llega hasta el siguiente encabezado o «Index Terms»."""
    for k, p in enumerate(cuerpo):
        t = p["texto"].strip()
        if titulo_limpio(t) in ("abstract", "resumen"):
            partes = []
            for q in cuerpo[k + 1:]:
                u = q["texto"].strip()
                if not u:
                    continue
                if q.get("es_titulo") or nivel_estilo(q) or RE_FIN_ABSTRACT.match(u) or (RE_NUM_ENC_IEEE.match(u) and len(u.split()) < 8):
                    break
                partes.append(u)
            texto = " ".join(partes)
        elif RE_ABSTRACT_CORRIDO.match(t) and len(t.split()) > 12:
            texto = re.split(r"\s(?:Index Terms|Keywords?|Palabras clave)\s*[—–:-]", RE_ABSTRACT_CORRIDO.sub("", t, count=1))[0]
        else:
            continue
        n = len(texto.split())
        if n and not 150 <= n <= 250:
            return [Hallazgo("IEEE-061", "mayor", ubic(p), f"{n} palabras", "el Abstract debe tener entre 150 y 250 palabras")]
        return []
    return []


def romano_a_texto(n):
    out = ""
    for v, s in ((100, "C"), (90, "XC"), (50, "L"), (40, "XL"), (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")):
        while n >= v:
            out, n = out + s, n - v
    return out


def figure_en_texto(p):
    """Menciones «Figure N» / «Figures N» del cuerpo de un párrafo (IEEE-084); no cuentan las del pie de figura
    («Figure 1. …»), las de tablas ni las de notas."""
    t = p["texto"]
    es_pie = RE_ROTULO.match(t.strip()) and len(t) < 250 and re.match(r"\s*Figures?\s+\d+\s*[.:—–-]", t)
    if p.get("en_tabla") or RE_NOTA.match(t) or es_pie:
        return []
    return list(RE_FIGURE_EN.finditer(t))


def figuras_ieee(cuerpo):
    """IEEE-084 («Figure N» en el texto -> «Fig. N»; «Figura N» es válido en español), IEEE-089 (rótulo de tabla con
    número arábigo), IEEE-091 (numeración consecutiva de figuras y de tablas) e IEEE-092 (primeras menciones en orden)."""
    H = []
    rotulos, otros = separar_rotulos(cuerpo)
    for tipo, n, p, tok, palabra in rotulos:
        if tipo == "tabla" and tok.isdigit():
            H.append(Hallazgo("IEEE-089", "mayor", ubic(p), p["texto"][:40], f"rotular «{'TABLA' if palabra.lower().startswith('tabla') else 'TABLE'} {romano_a_texto(n)}» (numeral romano)"))
    for tipo in ("figura", "tabla"):
        nombre = "figuras" if tipo == "figura" else "tablas"
        nums = [n for t_, n, _, _, _ in rotulos if t_ == tipo]
        if nums and nums != list(range(1, len(nums) + 1)):
            H.append(Hallazgo("IEEE-091", "mayor", "texto", f"{nombre}: {nums[:12]}",
                              "numerar de forma consecutiva, sin saltos ni repetidos"))
        vistas = []
        for t in otros:
            for m in RE_MENCION.finditer(t):
                if tipo_rotulo(m.group(1)) == tipo:
                    vistas += [x for x in numeros_mencion(m) if x not in vistas]
        if vistas != sorted(vistas):
            k = next(i for i in range(len(vistas)) if vistas[i] != sorted(vistas)[i])
            H.append(Hallazgo("IEEE-092", "mayor", "texto", f"primeras menciones de {nombre}: {vistas[:12]} (primer desvío en posición {k + 1})",
                              "mencionar en orden numérico"))
    for p in cuerpo:
        ms = figure_en_texto(p)
        if ms:
            t, m = p["texto"], ms[0]
            H.append(Hallazgo("IEEE-084", "mayor", ubic(p), t[max(0, m.start() - 15):m.end() + 12],
                              "en el texto se escribe «Fig. N» («Figs. N y M» en plural)"))
    return H


def rotulos_ieee_equipo(cuerpo):
    """`tablas_figuras: ieee` de .editorial.yaml (norma base APA): rótulos de tabla y figura al estilo IEEE, que la
    institución impone sobre APA 7. Reutiliza separar_rotulos / RE_MENCION; las reglas ya existentes (IEEE-089 romano,
    IEEE-091, IEEE-092) las corre figuras_ieee. Aquí:
      IEEE-089  «TABLA» en mayúsculas y rótulo encima de la tabla
      IEEE-085  figura rotulada «Fig. N.» (no «Figura N») y con el pie debajo de la imagen
      APA-091   tabla o figura mencionada en el texto antes de aparecer (APA-091 pide menciones; aquí además van antes)"""
    H = []
    rotulos, _ = separar_rotulos(cuerpo)
    rot = {id(r[2]): r for r in rotulos}
    vistas = set()
    sin_mencion = []
    visibles = [p for p in cuerpo if p["texto"].strip() or p.get("imagen") or p.get("tabla_inicio")]
    for k, p in enumerate(visibles):
        r = rot.get(id(p))
        if r is None:
            if not (p.get("en_tabla") or RE_NOTA.match(p["texto"].strip())):
                for m in RE_MENCION.finditer(p["texto"]):
                    vistas |= {(tipo_rotulo(m.group(1)), n) for n in numeros_mencion(m)}
            continue
        tipo, n, _, tok, palabra = r
        if (tipo, n) not in vistas:
            sin_mencion.append((p, (tipo, n)))
        prev = visibles[k - 1] if k else None
        sig = visibles[k + 1:k + 3]
        if tipo == "tabla":
            if palabra != palabra.upper() and not tok.isdigit():  # con número arábigo, IEEE-089 (romano) ya pide «TABLA I»
                H.append(Hallazgo("IEEE-089", "mayor", ubic(p), p["texto"][:40], f"rotular «{palabra.upper()} {tok}» en mayúsculas"))
            if prev is not None and prev.get("en_tabla") and not any(q.get("en_tabla") for q in sig):
                H.append(Hallazgo("IEEE-089", "mayor", ubic(p), p["texto"][:40], "el rótulo de la tabla va centrado encima de ella"))
        else:
            if palabra.lower() != "fig." or not re.match(r"\s*fig\.\s*\d+\s*\.\s*\S", p["texto"], re.I):
                H.append(Hallazgo("IEEE-085", "mayor", ubic(p), p["texto"][:40], f"rotular «Fig. {n}. Texto del pie» (con punto tras el número)"))
            if sig and sig[0].get("imagen") and not (prev is not None and prev.get("imagen")):
                H.append(Hallazgo("IEEE-085", "mayor", ubic(p), p["texto"][:40], "el pie de la figura va debajo de la imagen, no encima"))
    sin_mencion = [p for p, k_ in sin_mencion if k_ in vistas]  # las nunca mencionadas ya las marca figuras_mencionadas (APA-091)
    if sin_mencion:
        p = sin_mencion[0]
        H.append(Hallazgo("APA-091", "mayor", ubic(p), f"{len(sin_mencion)} tablas/figuras aparecen antes de su primera mención; p. ej. «{p['texto'][:30]}»",
                          "mencionar y explicar cada tabla o figura en el texto antes de que aparezca"))
    return H


TITULOS_INDICE = {"indice de contenido", "indice general", "indice", "tabla de contenido", "tabla de contenidos", "contenido",
                  "indice de tablas", "lista de tablas", "indice de figuras", "lista de figuras", "table of contents", "list of tables",
                  "list of figures"}
RE_PAGINA_FINAL = re.compile(r"(?:[\t.…]|\s{2,})\s*(?:\d+|[ivxlc]+)\s*$", re.I)


def sin_indices(cuerpo):
    """Quita los índices de contenido, de tablas y de figuras (preliminares): sus entradas («TABLA I. Cronograma … 12») no
    son rótulos ni menciones. Un índice empieza en su título y acaba en el siguiente encabezado o salto de página; también se
    quitan las líneas de estilo TOC / «Tabla de ilustraciones» y los rótulos que terminan en puntos guía + página."""
    out, dentro = [], False
    for p in cuerpo:
        t = sin_acentos(p["texto"]).strip().lower().rstrip(":")
        t = re.sub(r"^[0-9ivxlc]+[.)]\s+", "", t)
        if t in TITULOS_INDICE and len(p["texto"]) < 40:
            dentro = True
            continue
        if dentro and (p.get("es_titulo") or p.get("salto_antes")):
            dentro = False
        est = p.get("estilo", "").lower()
        if dentro or est.startswith(("toc", "tdc", "table of", "tabla de ilustra", "índice", "indice")) \
                or (RE_ROTULO.match(p["texto"].strip()) and RE_PAGINA_FINAL.search(p["texto"]) and not p.get("imagen")):
            continue
        out.append(p)
    return out


def tablas_figuras_equipo(path, equipo=None):
    """`tablas_figuras:` de .editorial.yaml: «ieee» | None."""
    ruta = buscar_equipo(path, equipo)
    if not ruta or not ruta.exists():
        return None
    try:
        v = (yaml.safe_load(ruta.read_text(encoding="utf-8")) or {}).get("tablas_figuras")
    except yaml.YAMLError:
        return None
    return "ieee" if isinstance(v, str) and v.strip().lower() == "ieee" else None


def reglas_base_ieee(cuerpo, plantilla):
    """Reglas deterministas de la base IEEE (maquetación del texto): IEEE-061, 084, 089, 091, 092 (tanda 1 de
    docs/PRIORIDAD-REGLAS.md). La plantilla oficial (texto de ejemplo) no se juzga en el abstract."""
    return figuras_ieee(cuerpo) + ([] if plantilla else abstract_ieee(cuerpo))


def reglas_citas_ieee(cuerpo, entradas, plantilla):
    """Reglas deterministas de citas y lista IEEE: IEEE-009, 019, 020, 022, 023, 034, 041 (tanda 1). Solo con
    `citas: ieee`; la lista de ejemplo de una plantilla oficial no se juzga."""
    H = []
    if any(e.get("numerado") for e in entradas):
        entradas = [e for e in entradas if e.get("numerado")]
    for p in list(cuerpo) + list(entradas):
        m = RE_IBID.search(p["texto"])
        if m:
            H.append(Hallazgo("IEEE-009", "mayor", ubic(p), p["texto"][max(0, m.start() - 20):m.end() + 12],
                              "citar de nuevo el número de la referencia en vez de «ibid.» / «op. cit.»"))
    if not plantilla:
        H += autores_ieee(entradas) + lista_ieee(entradas) + lista_ieee_tanda2(entradas) + nombres_en_cita_ieee(cuerpo, entradas)
    return H


RE_PUNT_DOBLE = re.compile(r"(?<![.\d])\.\.(?![.\w])|,,|;;|(?<!\w)::|::(?!\w)")


def puntuacion(cuerpo, entradas, base):
    """APA-145 / IEEE-140 (petición del usuario, 18-nov): sin puntuación duplicada («aplica.. La»)
    ni espacios dobles dentro del párrafo. En APA, el doble espacio tras punto es APA-115.
    No toca puntos suspensivos «...», rangos «1..n» ni «std::». Los espacios dobles no se revisan
    dentro de tablas (alineación manual)."""
    H = []
    id_p = "APA-145" if base == "apa7" else "IEEE-140"
    for p in list(cuerpo) + list(entradas):
        t = p["texto"]
        for m in RE_PUNT_DOBLE.finditer(t):
            H.append(Hallazgo(id_p, "menor", ubic(p), t[max(0, m.start() - 20):m.end() + 12].strip(),
                              f"puntuación duplicada «{m.group(0)}»: dejar un solo signo"))
        if p.get("en_tabla"):
            continue
        dobles = [m for m in re.finditer(r"(?<=\S) {2,}(?=\S)", t)
                  if not (p.get("imagen") and t[m.end():].startswith("https://orcid.org"))]  # hueco del icono ORCID
        tras_punto = [m for m in dobles if t[m.start() - 1] in ".?!:"] if base == "apa7" else []
        otros = [m for m in dobles if m not in tras_punto]
        if base != "apa7":  # IEEE no regula el espacio tras signo de fin de oración (su plantilla oficial usa dos)
            otros = [m for m in otros if t[m.start() - 1] not in ".?!:;"]
        for ms, id_, que in ((tras_punto, "APA-115", "tras punto"), (otros, id_p, "")):
            if ms:
                m = ms[0]
                H.append(Hallazgo(id_, "menor", ubic(p), t[max(0, m.start() - 20):m.end() + 12].strip(),
                                  f"{len(ms)} espacio(s) doble(s) {que}: dejar uno".replace("  ", " ")))
    return H


# ---------------------------------------------------------------- tanda 2 (docs/PRIORIDAD-REGLAS.md)
# Referencias APA: APA-064 (21+ autores), APA-074 (rango de páginas con raya en), APA-080 (DOI y URL), APA-081 (URL de bases de datos)
RE_RANGO_PAGINAS = re.compile(
    r"(?:\bpp?\.\s*|\)\s*,\s*\*?|\d\*?,\s*\*?)([A-Za-z]?\d+)\s*([-‐‑‒—−])\s*([A-Za-z]?\d+)(?=\*?(?:\.|,|\)|\s*$|\s+(?:https?://|doi:)))")
RE_ENLACE = re.compile(r"https?://\S+|\bdoi:\s*\S+", re.I)
RE_DOI_APA = re.compile(r"https?://(?:dx\.)?doi\.org/10\.\S+|\bdoi:\s*10\.\S+", re.I)
RE_URL_NO_DOI = re.compile(r"https?://(?!(?:dx\.)?doi\.org)[^\s)>\]]+", re.I)
RE_URL_BASE_DATOS = re.compile(
    r"https?://(?:[\w\-]+\.)*(?:ebscohost\.com|proquest\.com|ovid\.com|ovidsp\.[\w.]+|webofscience\.com|webofknowledge\.com"
    r"|scopus\.com|psycnet\.apa\.org|gale\.com|galegroup\.com|nexisuni\.com)[^\s)>\]]*", re.I)  # sin jstor.org/stable: las muestras oficiales de APA lo usan como enlace estable de un artículo sin DOI
RE_PUNTOS_SUSP = re.compile(r"\s*(?:\.\s?\.\s?\.|…)\s*")


def rangos_guion(t):
    """Posiciones del guion (o raya) de los rangos de páginas de una entrada de referencia, escritos con «-» en vez de «–»
    (APA-074). Solo rangos tras «pp.», tras el volumen y número («12(3), 45-67») o tras el volumen («12, 45-67»); no toca
    URL ni DOI ni fechas «(2019, 24-26 de julio)»."""
    t2 = RE_ENLACE.sub(lambda m: " " * len(m.group(0)), t)
    out = []
    for m in RE_RANGO_PAGINAS.finditer(t2):
        if re.search(r"\(\s*(?:1[5-9]|20)\d{2}[a-z]?,\s*\*?$", t2[:m.start(1)]):
            continue
        out.append(m.start(2))
    return out


def referencias_apa_tanda2(entradas):
    """APA-064 (de 2 a 20 autores todos; con 21 o más: 19, «…» y el último, sin «&»), APA-074, APA-080 (con DOI y URL se deja
    solo el DOI) y APA-081 (URL de bases de datos académicas comunes)."""
    H = []
    guion, ambos, base_datos, largos = [], [], [], []
    for e in entradas:
        t = e["texto"]
        pos = rangos_guion(t)
        if pos:
            guion.append((e, t[max(0, pos[0] - 8):pos[0] + 8]))
        url = RE_URL_NO_DOI.search(t)
        if RE_DOI_APA.search(t) and url:
            ambos.append((e, url.group(0)))
        bd = RE_URL_BASE_DATOS.search(t)
        if bd and not (re.search(r"proquest", bd.group(0), re.I) and re.search(r"dissertation|thesis|tesis", t, re.I)):
            base_datos.append((e, bd.group(0)))
        af = autores_y_fecha(t)
        if af and re.search(r",\s*[A-ZÁÉÍÓÚÑ]\.", af[0]):
            seg = af[0]
            partes = RE_PUNTOS_SUSP.split(seg, 1)
            if len(partes) == 2:
                antes, despues = len(RE_AUTOR_LISTA.findall(partes[0])), len(RE_AUTOR_LISTA.findall(partes[1]))
                if antes != 19 or despues != 1 or re.search(r"(?:^|[\s,])(?:&|y|and)\s", partes[1]):
                    largos.append((e, f"{antes} autores antes de los puntos suspensivos y {despues} después"))
            elif len(RE_AUTOR_LISTA.findall(seg)) >= 21:
                largos.append((e, f"{len(RE_AUTOR_LISTA.findall(seg))} autores sin puntos suspensivos"))
    if largos:
        e, ev = largos[0]
        H.append(Hallazgo("APA-064", "mayor", ubic(e), f"{len(largos)} entradas con 21 o más autores mal escritos; p. ej. {ev}",
                          "con 21 o más autores: los 19 primeros, puntos suspensivos (sin «&») y el último autor"))
    if guion:
        e, ev = guion[0]
        H.append(Hallazgo("APA-074", "menor", ubic(e), f"{len(guion)} entradas con rango de páginas con guion; p. ej. «…{ev}…»",
                          "rango de páginas con raya en (–): «249–260»"))
    if ambos:
        e, ev = ambos[0]
        H.append(Hallazgo("APA-080", "menor", ubic(e), f"{len(ambos)} entradas con DOI y URL; p. ej. {ev}",
                          "con DOI se deja solo el DOI (https://doi.org/…) y se quita la URL"))
    if base_datos:
        e, ev = base_datos[0]
        H.append(Hallazgo("APA-081", "mayor", ubic(e), f"{len(base_datos)} entradas con URL de una base de datos; p. ej. {ev}",
                          "quitar el nombre y la URL de la base de datos (EBSCOhost, ProQuest, JSTOR…); usar el DOI o la URL de la obra"))
    return H


# Citas textuales sin ubicación (APA-048) y siglas con puntos (APA-103)
RE_COMILLADO = re.compile("“([^“”]*)”|«([^«»]*)»|\"([^\"]*)\"")
RE_UBICACION = re.compile(r"\bpp?\.|\bp[áa]gs?\.|\bp[áa]ginas?\b|\bpages?\b|\bp[áa]rr(?:afo)?s?\.|\bparas?\.|\bparagraphs?\b|\bcaps?\.|\bchap\.|\bch\."
                          r"|\bsecc?\.|\bsect\.|\bsection\b|\bsecci[óo]n\b|\bdiap\.|\bslides?\b|\bmin\.|\bfig\.|\btabla\b|\btable\b|\bl[íi]neas?\b|\blines?\b"
                          r"|\bart\.|\bvers\.|§|\bp\s?\d", re.I)
RE_PISTA_TITULO = re.compile(r"(?:art[íi]culos?|cap[íi]tulos?|articles?|chapters?|titulad[oa]s?|titled|entitled|t[íi]tulo|title|poemas?|poems?"
                             r"|canci[óo]n|songs?|episod\w+|p[áa]gina|webpage|libros?|books?|obras?|informes?|reports?|ensayos?|essays?)\W+(?:\S+\W+){0,3}$", re.I)
RE_AÑO_PAR = re.compile(r"(?:1[5-9]|20)\d{2}[a-z]?|\bn\.\s?d\.|\bs\.\s?f\.", re.I)
MIN_PALABRAS_CITA = 6


def cita_textual_apa(cuerpo):
    """APA-048: una cita textual entre comillas de MIN_PALABRAS_CITA o más palabras, seguida de una cita autor-fecha, lleva
    página u otra ubicación (p., pp., párr., cap., sec.…). Las comillas cortas (ironía) y los títulos de artículos entre
    comillas no cuentan; tampoco la cita de comunicación personal."""
    H = []
    for p in cuerpo:
        t = fuente_secundaria(p["texto"])
        if p.get("en_tabla"):
            continue
        for m in RE_COMILLADO.finditer(t):
            inner = next(g for g in m.groups() if g is not None)
            if len([w for w in inner.split() if re.search(r"\w", w)]) < MIN_PALABRAS_CITA:
                continue
            if RE_PISTA_TITULO.search(t[max(0, m.start() - 40):m.start()]):
                continue
            sig = re.match(r"\s*\(([^()]*)\)", t[m.end():])
            if not sig:
                continue
            c = sig.group(1)
            if RE_AÑO_PAR.search(c) and not RE_UBICACION.search(c) and not RE_PERSONAL.search(c):
                H.append(Hallazgo("APA-048", "mayor", ubic(p), f"«{inner[:40]}…» ({c})",
                                  "la cita textual lleva página u otra ubicación: «(Autor, 2020, p. 5)» o «(Autor, 2020, párr. 3)»"))
                break
    return H


RE_SIGLA_PUNTOS = re.compile(r"(?<![\w.])(?:[A-ZÁÉÍÓÚÑ]\.){3,}(?!\w)|(?<![\w.])Ph\.\s?D\.(?!\w)")
SIGLAS_LEGALES = {"SAB", "SAPI", "SAS", "SRL", "SAPIB", "SCP", "SPR"}


def siglas_puntos_apa(cuerpo):
    """APA-103: siglas sin puntos («FBI», «PhD», no «F.B.I.», «Ph.D.»). Se evalúan las de tres o más letras (las de dos se
    confunden con iniciales de nombre); no cuentan las iniciales seguidas de un apellido («J.R.R. Tolkien»), las razones
    sociales («S.A.P.I.») ni lo que va entre comillas."""
    H = []
    n, primero = 0, None
    for p in cuerpo:
        t = RE_COMILLADO.sub(lambda m: " " * len(m.group(0)), p["texto"])
        for m in RE_SIGLA_PUNTOS.finditer(t):
            if re.sub(r"\W", "", m.group(0)) in SIGLAS_LEGALES or re.match(r"\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñü]", t[m.end():]):
                continue
            n += 1
            primero = primero or (p, m.group(0))
    if primero:
        p, s = primero
        H.append(Hallazgo("APA-103", "menor", ubic(p), f"{n} siglas con puntos; p. ej. «{s}»",
                          "escribir las siglas sin puntos: «FBI», «PhD»"))
    return H


# IEEE-007 (nombres en la cita), IEEE-031 (vol., no., pp.) e IEEE-032 (mes abreviado)
RE_MENCION_AUTOR_IEEE = re.compile(
    r"(?<![\w'’\-])([A-ZÁÉÍÓÚÑ][\w'’\-áéíóúñü]+(?:(?:,\s+[A-ZÁÉÍÓÚÑ][\w'’\-áéíóúñü]+)*,?\s+(?:and|y|&)\s+[A-ZÁÉÍÓÚÑ][\w'’\-áéíóúñü]+|\s+et al\.?)?)\s+$")
RE_NOMBRE_PROPIO = re.compile(r"[A-ZÁÉÍÓÚÑ][\w'’\-áéíóúñü]+")
RE_ROMPE_MENCION = re.compile(r"^(?:In|See|Ref|Refs|Fig|Figs|Eq|Table|Section|Sec|The|As|And|Of|By|From|For|With)$")


def autores_entrada_ieee(tx):
    """(n.º de autores, apellidos) de una entrada IEEE con el título entre comillas; «et al.» cuenta como 3 o más. None si no se puede."""
    seg = segmento_autores(tx)
    if not seg or not seg.strip():
        return None
    et_al = bool(re.search(r"\bet al\b", seg))
    seg = re.sub(r",?\s*et al\.?", "", seg)
    piezas = [x.strip() for x in re.split(r",\s*(?:and\s+)?|\s+and\s+|\s*&\s*", seg) if x.strip()]
    apellidos = []
    for x in piezas:
        if re.match(RE_INICIALES_ANTES + r"\S", x):
            apellidos.append(sin_acentos(re.sub(r"^" + RE_INICIALES_ANTES, "", x).strip()).lower())
    if not apellidos:
        return None
    return (max(len(apellidos), 3) if et_al else len(apellidos)), apellidos


def nombres_en_cita_ieee(cuerpo, entradas):
    """IEEE-007: «Wood et al. [7]» si la obra tiene 3 o más autores; «Brown and Jones [5]» (todos los nombres) con 1 o 2. Se cruza
    el número del corchete con su entrada y solo se juzga la mención cuyo primer apellido es el de esa entrada."""
    H = []
    info = {}
    for pos, e in enumerate(entradas, 1):
        m = re.match(r"\s*\[(\d+)\]", e["texto"])
        a = autores_entrada_ieee(e["texto"])
        if a:
            info[int(m.group(1)) if m else pos] = a
    ya = set()
    for p in cuerpo:
        t = p["texto"]
        for m in re.finditer(r"\[(\d+)\]", t):
            n = int(m.group(1))
            if n not in info or n in ya:
                continue
            mm = RE_MENCION_AUTOR_IEEE.search(t[max(0, m.start() - 90):m.start()] + " ")
            if not mm:
                continue
            nombres = [x for x in RE_NOMBRE_PROPIO.findall(re.sub(r"\bet al\b", "", mm.group(1))) if x not in ("and", "y")]
            if not nombres or RE_ROMPE_MENCION.match(nombres[0]):
                continue
            n_aut, apellidos = info[n]
            nombres_n = [sin_acentos(x).lower() for x in nombres]
            if not any(a.split()[-1] == nombres_n[0] or a == nombres_n[0] for a in apellidos[:1]):
                continue
            if len(nombres_n) > 1 and not all(any(a.split()[-1] == x for a in apellidos) for x in nombres_n):
                continue
            et_al = bool(re.search(r"\bet al\b", mm.group(1)))
            if n_aut >= 3:
                ok = et_al and len(nombres_n) == 1
                esperado = f"«{nombres[0]} et al. [{n}]»"
            else:
                ok = not et_al and len(nombres_n) == n_aut
                esperado = f"nombrar a todos: «{' and '.join(x.capitalize() for x in apellidos)} [{n}]»"
            if not ok:
                ya.add(n)
                H.append(Hallazgo("IEEE-007", "mayor", ubic(p), f"«{mm.group(1)} [{n}]»: la obra tiene {n_aut if n_aut < 3 else '3 o más'} autor{'es' if n_aut > 1 else ''}",
                                  "con 3 o más autores: primer apellido y «et al.»; con 1 o 2: todos los apellidos, sin «et al.» — " + esperado))
    return H


MESES_COMPLETOS = "January|February|March|April|June|July|August|September|October|November|December|Sept"
RE_MES_COMPLETO = re.compile(r"(?<![\w.])(?:\d{1,2}\s+)?(" + MESES_COMPLETOS + r")\.?(?:\s+\d{1,2})?,?\s+(?:19|20)\d{2}(?!\d)")
RE_MES_SIN_PUNTO = re.compile(r"(?<![\w.])(Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Oct|Nov|Dec)(?![\w.])(?:\s+\d{1,2},)?\s+(?:19|20)\d{2}(?!\d)")
RE_VOL_NO_PP = [re.compile(x) for x in (
    r"\bVol\b\.?\s?\d", r"\bvol(?!\.)\s?\d", r"(?<!Law )\bNo\.\s?\d", r",\s*no(?!\.)\s?\d", r"\bPP?\.\s?\d|\bPp\.\s?\d", r",\s*pp?(?!\.)\s\d",
    r"\bpp\.\s*[A-Za-z]?\d+\s*[-‐‑‒—−]\s*[A-Za-z]?\d+", r"\bp\.\s*[A-Za-z]?\d+\s*[-‐‑‒—–−]\s*[A-Za-z]?\d+",
    r"\bpp\.\s*\d+(?!\d|\.\d|\s*[-‐‑‒–—−,]\s*[A-Za-z]?\d)")]


def lista_ieee_tanda2(entradas):
    """IEEE-031 (`vol.`, `no.`, `pp.`/`p.` en minúscula con punto, páginas con raya en) e IEEE-032 (mes abreviado). Se ignoran el título
    entre comillas, lo que va en cursiva marcada con «*», las URL y los DOI; no se juzga el mes en datasets ni en software."""
    H = []
    for e in entradas:
        tx = re.sub(r"^\s*\[\d+\]\s*", "", e["texto"])
        lim = RE_ENLACE.sub(lambda m: " " * len(m.group(0)), tx)
        lim = re.sub("[“\"«][^”\"»“«]*[”\"»]", lambda m: " " * len(m.group(0)), lim)
        lim = re.sub(r"\*[^*]*\*", lambda m: " " * len(m.group(0)), lim)
        falla = next((m for m in (rx.search(lim) for rx in RE_VOL_NO_PP) if m), None)
        if falla:
            H.append(Hallazgo("IEEE-031", "menor", ubic(e), lim[max(0, falla.start() - 10):falla.end() + 10].strip(),
                              "«vol.», «no.», «pp.» en minúscula con punto; «pp. 12–34» con raya en y «p. 12» para una sola página"))
        if re.search(r"distributed by|\bdataset\b|\bsoftware\b|\(\d{4}\)\.\s+\S", lim, re.I):
            continue
        m = RE_MES_COMPLETO.search(lim) or RE_MES_SIN_PUNTO.search(lim)
        if m:
            H.append(Hallazgo("IEEE-032", "menor", ubic(e), lim[max(0, m.start() - 10):m.end() + 6].strip(),
                              "mes abreviado: Jan., Feb., Mar., Apr., May, Jun., Jul., Aug., Sep., Oct., Nov., Dec."))
    return H


# Encabezados y símbolos de la base IEEE: IEEE-015, IEEE-070, IEEE-129
RE_PREFIJO_ENC_IEEE = re.compile(r"^\s*(?:[IVXLC]+\.|\d{1,2}(?:\.\d{1,2})*\.?|[A-Z][.)])\s+(?=\S)")
RE_ENC_ROMANO = re.compile(r"^\s*[IVXL]+\.\s+[A-Z][A-Z \-:,]{3,}$")
RE_ACK_IEEE = re.compile(r"^(?:acknowledg(?:e)?ments?|agradecimientos?)$", re.I)


def encabezados_ieee(pars, titulo):
    """IEEE-015 (la lista se rotula `REFERENCES`/`REFERENCIAS` sin numeral ni letra) e IEEE-070 (con los demás encabezados
    numerados, `REFERENCES` y `ACKNOWLEDGMENT` tampoco llevan numeral; si los demás no se numeran, solo cuenta IEEE-015)."""
    H = []
    ref_num = bool(titulo and (RE_PREFIJO_ENC_IEEE.match(titulo["texto"]) or titulo.get("numerado")))
    ack = []
    otros = 0
    for p in pars:
        t = p["texto"].strip()
        if not t or p.get("en_tabla") or len(t) > 80 or p is titulo:
            continue
        sin = RE_PREFIJO_ENC_IEEE.sub("", t, count=1).strip().rstrip(":")
        enc = p.get("es_titulo") or nivel_estilo(p) or RE_ENC_ROMANO.match(t)
        if RE_ACK_IEEE.match(sin) and (RE_PREFIJO_ENC_IEEE.match(t) or p.get("numerado")) and (enc or sin.isupper()):
            ack.append(p)
        elif enc and (RE_PREFIJO_ENC_IEEE.match(t) or p.get("numerado")) and titulo_limpio(t) not in TITULOS_REF:
            otros += 1
    numeran = otros >= 2
    if ref_num and numeran:
        H.append(Hallazgo("IEEE-070", "mayor", ubic(titulo), f"«{titulo['texto'].strip()[:40]}» numerado con los demás encabezados",
                          "`REFERENCES` va sin numeral ni letra aunque los demás encabezados se numeren"))
    elif ref_num:
        H.append(Hallazgo("IEEE-015", "menor", ubic(titulo), f"«{titulo['texto'].strip()[:40]}»",
                          "rotular la lista `REFERENCES` (`REFERENCIAS`) sin numeral romano ni letra"))
    if numeran:
        for p in ack[:1]:
            H.append(Hallazgo("IEEE-070", "mayor", ubic(p), f"«{p['texto'].strip()[:40]}» numerado con los demás encabezados",
                              "`ACKNOWLEDGMENT` va sin numeral ni letra aunque los demás encabezados se numeren"))
    return H


def simbolos_ieee(cuerpo):
    """IEEE-129: sin ™ ni ® en el texto corrido."""
    H = []
    for p in cuerpo:
        m = re.search("[™®]", p["texto"])
        if m:
            t = p["texto"]
            H.append(Hallazgo("IEEE-129", "menor", ubic(p), t[max(0, m.start() - 20):m.end() + 6],
                              "quitar el símbolo ™/®: el nombre comercial se escribe sin él"))
    return H


# ---------------------------------------------------------------- principal
def auditar(path, perfil_id, equipo=None):
    validar_entrada(path)
    cfg = cargar_perfil(perfil_id)
    pars, secciones = (cargar_docx if path.lower().endswith(".docx") else cargar_md)(path)
    for p in pars:
        p["texto"] = unicodedata.normalize("NFC", p["texto"]).replace(" ", " ").replace(" ", " ")
    notas = [p for p in pars if p.get("nota_pie")]
    pars = [p for p in pars if not p.get("nota_pie")]
    plantilla = es_plantilla(pars)
    if plantilla:  # las etiquetas «(Heading 1)» que la plantilla añade a su texto de ejemplo no son parte del texto
        for p in pars:
            m = RE_ETIQUETA_ESTILO.search(p["texto"])
            if m and (m.group(1).strip().lower() == p.get("estilo", "").lower() or "use style" in m.group(0).lower()):
                p["texto"] = p["texto"][:m.start()]
    cuerpo, titulo, entradas = partir(pars)
    ids_antes = {id(p) for p in cuerpo} | {id(p) for p in entradas} | {id(titulo)}
    # texto citable fuera del cuerpo: notas al pie y lo que sigue a la lista (tablas, figuras y apéndices, APA 2.17)
    extra = [p for p in pars if id(p) not in ids_antes and p["texto"].strip()] + notas
    H = []
    avisos = []
    if titulo is None and not entradas:
        H.append(Hallazgo("APA-034" if cfg["citas"] == "apa7" else "IEEE-012", "crítica", "documento",
                          "no se encontró la sección de referencias", "agregar «Referencias»"))
    if titulo is not None and cfg["citas"] == "apa7" and titulo_limpio(titulo["texto"]) not in ("referencias", "references", "referencia", "reference"):
        H.append(Hallazgo("APA-059", "mayor", ubic(titulo), titulo["texto"], "rotular la lista «Referencias» (sin numeración ni otro nombre)"))
    fmt, av_fmt = formato_equipo(path, equipo)
    if secciones and any(x.get("sin_margenes") for x in secciones):
        avisos.append("Sección sin márgenes declarados (sectPr sin pgMar): se usan los valores por defecto de Word (1 in en los cuatro lados); declara los márgenes del documento.")
    if cfg["base"] == "apa7" and secciones:
        H += base_apa(pars, secciones, titulo, entradas, (cfg.get("opciones") or {}).get("tipo_trabajo", "estudiante"),
                      (fmt or {}).get("interlineado") or 2.0)
    elif cfg["base"] == "ieee":
        H += decimales_ieee(cuerpo)
        H += reglas_base_ieee(cuerpo, plantilla)
        H += encabezados_ieee(pars, titulo) + simbolos_ieee(cuerpo)
        avisos.append("IEEE no define maquetación de tesis/informe: márgenes, fuente y portada se evalúan con el perfil de equipo.")
    if cfg["base"] == "apa7" and tablas_figuras_equipo(path, equipo) == "ieee":  # perfil de equipo: rótulos IEEE sobre base APA
        H += figuras_ieee(sin_indices(cuerpo)) + rotulos_ieee_equipo(sin_indices(cuerpo))
    for p in pars:  # EA-001: marcadores del redactor que no pueden llegar a la entrega
        for m in re.finditer(r"\[\[\s*(FALTA FUENTE|TODO|PENDIENTE)[^\]]*\]\]", p["texto"]):
            H.append(Hallazgo("EA-001", "crítica", ubic(p), m.group(0)[:80],
                              "aportar una fuente verificada o reescribir la afirmación sin ella"))
    H += puntuacion(cuerpo, entradas, cfg["base"])
    H += figuras_mencionadas(cuerpo, [] if path.lower().endswith(".docx") else textos_tablas(path), cfg["base"])
    if cfg["citas"] == "apa7":
        H += citas_apa(cuerpo + extra, entradas, con_layout=bool(secciones), base_es_apa=cfg["base"] == "apa7",
                       anotada=titulo is None and bool(entradas))
        H += referencias_apa(entradas) + citas_fecha_apa(cuerpo + extra) + citas_et_al_apa(cuerpo + extra, entradas)
        H += referencias_apa_tanda2(entradas) + cita_textual_apa(cuerpo + extra) + siglas_puntos_apa(cuerpo)
        H += apendices_mencionados(pars, cuerpo, titulo)
    else:
        H += citas_ieee(cuerpo + extra, entradas)
        H += reglas_citas_ieee(cuerpo, entradas, plantilla)
    if entradas and not plantilla and fuentes_niveles_equipo(path, equipo):  # FUE-V4N (scripts/niveles.py)
        import niveles
        H += niveles.hallazgos_nivel_bajo(pars, cuerpo, entradas, Hallazgo, sys.modules[__name__])[0]
    bloque_fuentes = fuentes_bloque_equipo(path, equipo)
    if entradas and not plantilla and any(bloque_fuentes.get(k) for k in ("minimo_nivel", "porcentaje_arbitradas", "evitar")):
        import niveles  # FUE-NIV: bloque `fuentes:` del perfil (minimo_nivel, porcentaje_arbitradas, evitar)
        H += niveles.hallazgos_perfil(entradas, bloque_fuentes, (fmt or {}).get("fuentes_recientes"), Hallazgo, sys.modules[__name__])
    if plantilla:
        avisos.append("Plantilla con texto de ejemplo: no se compara lo citado con la lista de referencias (son ejemplos).")
        H = [h for h in H if h["id"] not in ("APA-034", "APA-035", "IEEE-012", "IEEE-013", "IEEE-014")]
    if fmt:  # INS-001..015 (INS-016 va aparte, más abajo): formato institucional (`formato:`) y modelos vinculantes (`vinculante:`) (solo .docx)
        avisos += av_fmt
        if path.lower().endswith(".docx"):
            import institucional
            H += institucional.reglas(path, pars, cuerpo, titulo, entradas, fmt)
            avisos += institucional.avisos_fuentes(entradas, fmt)
            avisos += institucional.avisos_extra(path, pars, cuerpo, titulo, entradas, fmt)
        else:
            avisos.append("formato: las reglas INS solo se evalúan en .docx")
    if path.lower().endswith(".docx"):  # INS-016: medidas pedidas por el usuario (bloque `medidas:` de .editorial.yaml; scripts/medidas.py)
        import medidas as _M
        reglas_m, no_med_m, _ = _M.leer_medidas_yaml(path, equipo)
        if reglas_m:
            h_m, av_m = _M.hallazgos(path, [dict(p) for p in pars], reglas_m, no_med_m, Hallazgo)
            H += h_m
            avisos += av_m
    H, excepciones, equipo_ruta = aplicar_equipo(H, path, equipo)
    if equipo_ruta:
        avisos.append(f"Perfil de equipo: {equipo_ruta} ({len(excepciones)} hallazgos pasan a excepción institucional)")
    orden = {"crítica": 0, "mayor": 1, "menor": 2}
    H.sort(key=lambda h: (orden[h["severidad"]], h["id"]))
    c = {s: sum(h["severidad"] == s for h in H) for s in orden}
    if c["crítica"]:
        dict_ = "Rechazado"
    elif c["mayor"] > 5:
        dict_ = "Correcciones mayores"
    elif c["mayor"] or c["menor"]:
        dict_ = "Correcciones menores"
    else:
        dict_ = "Aprobado (reglas mecánicas)"
    return {"documento": str(path), "perfil": perfil_id, "dictamen_mecanico": dict_, "conteo": c,
            "hallazgos": H, "avisos": avisos, "entradas_lista": len(entradas), "excepciones": excepciones}


def fuentes_niveles_equipo(path, equipo=None):
    """`fuentes: {niveles: true}` en .editorial.yaml: el juez añade FUE-V4N (afirmación sustantiva sostenida solo por fuentes de nivel D/E).
    /puntuar lo calcula siempre."""
    ruta = buscar_equipo(path, equipo)
    if not ruta or not ruta.exists():
        return False
    try:
        f = (yaml.safe_load(ruta.read_text(encoding="utf-8")) or {}).get("fuentes")
    except yaml.YAMLError:
        return False
    return isinstance(f, dict) and f.get("niveles") is True


def fuentes_bloque_equipo(path, equipo=None):
    """Bloque `fuentes:` de .editorial.yaml (dict; vacío si no hay): niveles, minimo_nivel, porcentaje_arbitradas, evitar."""
    ruta = buscar_equipo(path, equipo)
    if not ruta or not ruta.exists():
        return {}
    try:
        f = (yaml.safe_load(ruta.read_text(encoding="utf-8")) or {}).get("fuentes")
    except yaml.YAMLError:
        return {}
    return f if isinstance(f, dict) else {}


EQUIPO_EXPLICITO = None  # ruta de `--equipo` (cli.perfil_por_defecto): vale para todas las búsquedas de este proceso
IGNORADOS = set()  # rutas resueltas de .editorial.yaml que `--perfil` explícito desautoriza (cli.perfil_por_defecto)


def buscar_equipo(path, equipo=None, ignorados=True):
    """`.editorial.yaml` explícito, o el primero hacia arriba desde la carpeta del documento (máx. 6 niveles). Un archivo que
    `--perfil` explícito desautorizó (declara otro perfil) no se devuelve, salvo con `ignorados=False`."""
    equipo = equipo or EQUIPO_EXPLICITO
    if equipo:
        return pathlib.Path(equipo)
    d = pathlib.Path(path).resolve().parent
    for _ in range(6):
        if (d / ".editorial.yaml").exists():
            if ignorados and (d / ".editorial.yaml").resolve() in IGNORADOS:
                return None
            return d / ".editorial.yaml"
        if d.parent == d:
            break
        d = d.parent
    return None


def _si_no(v):
    """YAML 1.1 lee `no` como False y `si` como texto: normaliza a «si» | «no» | None."""
    if v is True:
        return "si"
    if v is False:
        return "no"
    if isinstance(v, str):
        s = sin_acentos(v).strip().lower()
        if s in ("si", "yes", "true", "1"):
            return "si"
        if s in ("no", "false", "0"):
            return "no"
    return None


def formato_equipo(path, equipo=None):
    """`formato:` de .editorial.yaml normalizado (institucional.normalizar): (dict, avisos). ({}, []) sin bloque."""
    ruta = buscar_equipo(path, equipo)
    if not ruta or not ruta.exists():
        return {}, []
    try:
        cfg = yaml.safe_load(ruta.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError:
        return {}, []
    raw, vinc, fijo = cfg.get("formato"), cfg.get("vinculante"), cfg.get("titulo")
    if raw is None and vinc is None and not fijo:
        return {}, []
    import institucional
    try:  # `vinculante:` inválido es un error de uso (código 2), no un aviso
        f, av = institucional.normalizar(raw, vinc, ruta.parent)
    except institucional.ErrorPerfil as e:
        _error(f"{ruta}: {e}")
    if fijo:  # `titulo:` fijado por el usuario (vinculante): la portada debe coincidir (INS-010)
        f["titulo_fijo"] = " ".join(str(fijo).split())
    return f, av


def _portada_cfg(cfg):
    """`portada_numero:` o, sin él, `formato.paginacion.portada: sin_numero` (= «no»)."""
    v = _si_no(cfg.get("portada_numero"))
    if v is None and isinstance(cfg.get("formato"), dict) and isinstance(cfg["formato"].get("paginacion"), dict):
        p = str(cfg["formato"]["paginacion"].get("portada") or "")
        if p:
            v = "no" if "sin" in sin_acentos(p).lower() else "si"
    return v


def portada_numero_equipo(path, equipo=None):
    """`portada_numero:` de .editorial.yaml: «si» | «no» | None (sin declarar)."""
    ruta = buscar_equipo(path, equipo)
    if not ruta or not ruta.exists():
        return None
    try:
        return _portada_cfg(yaml.safe_load(ruta.read_text(encoding="utf-8")) or {})
    except yaml.YAMLError:
        return None


def estado_portada(d):
    """Numeración de la portada (primera página de la sección 0): («encabezado» | «pie» | «ninguno», primera página distinta).
    Con `different_first_page_header_footer` mira first_page_header/footer; si no, header/footer. Una parte sin
    definición propia en la sección 0 está vacía."""
    if not d.sections:
        return "ninguno", False
    s = d.sections[0]
    dif = bool(s.different_first_page_header_footer)
    h, f = (s.first_page_header, s.first_page_footer) if dif else (s.header, s.footer)
    if not h.is_linked_to_previous and ooxml.tiene_pagina(h._element):
        return "encabezado", dif
    if not f.is_linked_to_previous and ooxml.tiene_pagina(f._element):
        return "pie", dif
    return "ninguno", dif


def aplicar_equipo(H, path, equipo=None):
    """Perfil de equipo (precedencia: equipo > norma). Cada `excepciones[].regla` que coincide con un hallazgo
    (y con `si_contiene`, si se da, en su evidencia) lo convierte en excepción institucional: sale de los
    hallazgos y queda registrada con su motivo. Devuelve (hallazgos, excepciones, ruta del perfil)."""
    ruta = buscar_equipo(path, equipo)
    if not ruta or not ruta.exists():
        return H, [], None
    cfg = yaml.safe_load(ruta.read_text(encoding="utf-8")) or {}
    reglas = list(cfg.get("excepciones") or [])
    if cfg.get("tablas_figuras") == "ieee":  # el rótulo APA (número en negrita, título encima de figuras) lo sustituye el IEEE
        reglas += [{"regla": r, "motivo": "la institución rotula tablas y figuras en estilo IEEE (tablas_figuras: ieee)"}
                   for r in ("APA-089", "APA-090")]
    if cfg.get("medidas"):  # lo pedido en `medidas:` sustituye la exigencia APA equivalente (margen, interlineado, sangría…)
        import medidas as _M
        try:
            reglas += _M.excepciones_derivadas(_M.normalizar_medidas(cfg["medidas"])[0])
        except _M.ErrorMedidas as e:
            _error(f"{ruta}: {e}")
    if isinstance(cfg.get("formato"), dict):  # excepciones que se derivan solas de `formato:`
        import institucional
        reglas += institucional.excepciones_derivadas(institucional.normalizar(cfg["formato"])[0])
    quedan, exc = [], []
    for h in H:
        r = next((x for x in reglas if x.get("regla") == h["id"]
                  and (not x.get("si_contiene") or str(x["si_contiene"]).lower() in h["evidencia"].lower())), None)
        if r:
            exc.append({**h, "id": "EXC-" + h["id"], "motivo": r.get("motivo", cfg.get("institucion", "perfil de equipo"))})
        else:
            quedan.append(h)
    if _portada_cfg(cfg) == "no" and str(path).lower().endswith(".docx"):
        # la portada sin número es lo que pide la institución: APA-008 (APA §2.18 pide el 1) pasa a excepción
        try:
            estado, dif = estado_portada(abrir_docx(str(path)))
        except Exception:  # noqa: BLE001
            estado, dif = "encabezado", False
        if dif and estado == "ninguno":
            exc.append({**Hallazgo("APA-008", "crítica", "portada", "la portada (primera página) no lleva número de página",
                                   "APA §2.18: la portada lleva el número 1"),
                        "id": "EXC-APA-008", "motivo": "la institución pide portada sin número"})
    return quedan, exc, str(ruta)


def main():
    ap = argparse.ArgumentParser(description="Juez determinista de formato, citas y referencias.")
    ap.add_argument("documento")
    ap.add_argument("--perfil", help="id de perfil (apa7, ieee, …); por defecto el `perfil:` de .editorial.yaml")
    ap.add_argument("--json", metavar="RUTA", help="escribe el resultado completo como JSON")
    ap.add_argument("--equipo", help="ruta de .editorial.yaml (si no, se busca hacia arriba desde el documento)")
    a = ap.parse_args()
    cli.utf8()
    perfil = cli.perfil_por_defecto(ap, a.perfil, a.documento, a.equipo)
    r = auditar(a.documento, perfil, a.equipo)
    cli.escribir_json(a.json, r)
    print(f"DICTAMEN MECÁNICO: {r['dictamen_mecanico']}   Perfil: {r['perfil']}   {r['conteo']}   entradas={r['entradas_lista']}")
    for av in r["avisos"]:
        print("AVISO:", av)
    print("| # | ID | Severidad | Ubicación | Evidencia | Corrección |\n|---|---|---|---|---|---|")
    for i, h in enumerate(r["hallazgos"], 1):
        print(f"| {i} | {h['id']} | {h['severidad']} | {h['ubicacion']} | {h['evidencia']} | {h['correccion']} |")
    for h in r.get("excepciones", []):
        print(f"EXCEPCIÓN INSTITUCIONAL: {h['id']} | {h['ubicacion']} | {h['evidencia']} | motivo: {h['motivo']}")
    sys.exit(cli.codigo(r["hallazgos"]))


if __name__ == "__main__":
    main()
