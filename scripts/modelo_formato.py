#!/usr/bin/env python3
"""Modelos de formato vinculantes: mide un modelo (PDF o .docx) y lo compara con un documento (INS-015).

Un formato, modelo o instrucción que da el usuario es vinculante: se mide, se registra en `vinculante:` de .editorial.yaml
y se reproduce al pie de la letra. Este módulo hace lo medible.

Uso:
  python scripts/editorial.py modelo medir <modelo.pdf|docx> [--pagina N] [--ambito portada|documento|seccion:<nombre>]
                              [--fijo-todo] --out spec.json
  python scripts/editorial.py modelo comparar <documento.docx> <spec.json> [--ambito portada|documento|seccion:<nombre>]

`medir` escribe la spec JSON: por línea el texto, la fuente, el tamaño (pt), negrita, cursiva, color #RRGGBB, la alineación
(en PDF se deduce de la caja de la línea: centrada si su centro cae en el de la página), el espacio previo (pt) y las cajas
(rellenos y barras de borde con color y grosor, con las líneas a las que acompañan). PDF con PyMuPDF (`pip install pymupdf`;
sin él, error con código 2); .docx con python-docx. Cada línea puede marcarse a mano en la spec:
  "fijo": true        texto literal obligatorio (se compara tal cual, espacios colapsados)
  "campo": "nombre"   contenido variable (nombre del integrante, fecha…) que debe llevar el mismo estilo
  "y_fija": true      (solo `editorial.py portada`) la línea va en su posición absoluta de la página (bbox del modelo), no a una distancia de la
                      línea anterior: el pie de la portada, que no sube ni baja con el número de integrantes
  "nombre_negrita": true   línea con estilo mixto por diseño (nombre en negrita y el resto normal, p. ej. «Nombre — No. de control»):
                      `editorial.py portada` pone el nombre en negrita y la comparación no exige la negrita de la línea
Las líneas sin marca se tratan como campo: solo cuenta su lugar y su estilo (`--fijo-todo` marca todas como fijas).

`comparar` (y la regla INS-015) alinea las líneas del documento con las de la spec en orden y anota cada diferencia: línea fija
ausente o fuera de orden, fuente, tamaño (tolerancia 0.5 pt), negrita, cursiva, color, alineación, y cajas ausentes (relleno y
borde con color y grosor). El estilo de cada línea de un .docx se resuelve como Word: run > estilo de carácter > estilo de
párrafo (y sus bases) > docDefaults.
"""
import argparse
import json
import pathlib
import re
import sys
import unicodedata

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cli  # noqa: E402
import ooxml  # noqa: E402

from docx.oxml.ns import qn  # noqa: E402

TOL_PT = 0.5
LADOS = ("izquierda", "derecha", "superior", "inferior")
LADO_XML = {"izquierda": ("left", "start"), "derecha": ("right", "end"), "superior": ("top",), "inferior": ("bottom",)}
RE_HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")


class ErrorModelo(ValueError):
    """Spec o declaración `vinculante:` inválida; los llamadores la convierten en error de uso (código 2)."""


# ---------------------------------------------------------------- utilidades
def colapsar(t):
    return " ".join(unicodedata.normalize("NFC", t or "").replace("\xa0", " ").split())


def norm_fuente(n):
    """«TimesNewRomanPS-BoldMT», «Times New Roman» -> «timesnewroman» (sin prefijo de subconjunto, estilo ni sufijos PS/MT)."""
    s = re.sub(r"^[A-Z]{6}\+", "", n or "")
    s = re.split(r"[-,]", s, maxsplit=1)[0]
    s = re.sub(r"(?i)(?:mt|ps)+$", "", s)
    return re.sub(r"[\s_]", "", s).lower()


def _hex(rgb):
    if rgb is None:
        return "#000000"
    if isinstance(rgb, int):
        return "#%06X" % rgb
    return "#" + "".join("%02X" % int(round(max(0.0, min(1.0, c)) * 255)) for c in rgb[:3])


def clase_alin(a):
    a = (a or "").lower()
    if a.startswith(("cent", "center")):
        return "centro"
    if a.startswith(("der", "right", "end")):
        return "derecha"
    return "izquierda"  # izquierda y justificada (el PDF no distingue una línea justificada de una a la izquierda)


# ---------------------------------------------------------------- medir PDF
def medir_pdf(ruta, pagina=1):
    try:
        import fitz
    except ImportError:
        cli.error("medir un PDF necesita PyMuPDF: pip install pymupdf")
    try:
        doc = fitz.open(str(ruta))
    except Exception as e:  # noqa: BLE001
        cli.error(f"no se pudo abrir el PDF {ruta}: {e}")
    if not 1 <= pagina <= len(doc):
        cli.error(f"--pagina {pagina} fuera de rango (el PDF tiene {len(doc)} páginas)")
    pg = doc[pagina - 1]
    ancho, alto = pg.rect.width, pg.rect.height
    lineas = []
    for b in pg.get_text("dict")["blocks"]:
        if b.get("type") != 0:
            continue
        for ln in b["lines"]:
            spans = [s for s in ln["spans"] if s["text"].strip()]
            if not spans:
                continue
            dom = max(spans, key=lambda s: len(s["text"].strip()))
            f = dom["font"]
            lineas.append({
                "texto": colapsar("".join(s["text"] for s in ln["spans"])), "fuente": f, "pt": round(dom["size"], 2),
                "negrita": bool(dom["flags"] & 16) or "bold" in f.lower(),
                "cursiva": bool(dom["flags"] & 2) or bool(re.search(r"(?i)italic|oblique", f)),
                "color": _hex(dom["color"]), "bbox": [round(x, 1) for x in ln["bbox"]]})
    lineas.sort(key=lambda l: (round(l["bbox"][1]), l["bbox"][0]))
    if lineas:
        izq = min(l["bbox"][0] for l in lineas)
        der = max(l["bbox"][2] for l in lineas)
    prev = 0.0
    for l in lineas:
        x0, y0, x1, y1 = l["bbox"]
        cx = (x0 + x1) / 2
        if abs(cx - ancho / 2) <= 8:
            l["alineacion"] = "centro"
        elif abs(x1 - der) <= 6 and abs(x0 - izq) > 6:
            l["alineacion"] = "derecha"
        else:
            l["alineacion"] = "izquierda"
        l["espacio_antes"] = round(max(0.0, y0 - prev), 1)
        prev = y1
    cajas = []
    vistos = set()
    for dib in pg.get_drawings():
        r = dib["rect"]
        w, h = r.width, r.height
        if w >= ancho * 0.98 and h >= alto * 0.98:
            continue
        fill, trazo = dib.get("fill"), dib.get("color")
        if fill is not None and _hex(fill) != "#FFFFFF":
            col, grosor = _hex(fill), None
            tipo = "relleno" if min(w, h) > 4 else ("barra_v" if w <= h else "barra_h")
            if tipo != "relleno":
                grosor = round(min(w, h), 2)
        elif fill is None and trazo is not None:
            col, grosor = _hex(trazo), round(dib.get("width") or 0, 2)
            tipo = "barra_v" if (w <= 1 and h > 1) else "barra_h" if (h <= 1 and w > 1) else "marco"
        else:
            continue
        clave = (tipo, col, round(r.x0), round(r.y0), round(r.x1), round(r.y1))
        if clave in vistos:
            continue
        vistos.add(clave)
        caja = {"tipo": tipo, "color": col, "bbox": [round(r.x0, 1), round(r.y0, 1), round(r.x1, 1), round(r.y1, 1)]}
        if grosor:
            caja["grosor"] = grosor
        cajas.append(caja)
    _asociar_cajas(lineas, cajas)
    return {"origen": pathlib.Path(ruta).name, "pagina": [round(ancho, 1), round(alto, 1)], "lineas": lineas, "cajas": cajas}


def _asociar_cajas(lineas, cajas):
    """Cada caja guarda en `junto_a` los índices de las líneas a las que acompaña; barras: `lado` (izquierda, derecha…)."""
    for c in cajas:
        x0, y0, x1, y1 = c["bbox"]
        junto = []
        for i, l in enumerate(lineas):
            lx0, ly0, lx1, ly1 = l["bbox"]
            solapa_y = min(y1, ly1) - max(y0, ly0) > 0.5 * (ly1 - ly0)
            if c["tipo"] in ("relleno", "marco"):
                if lx0 >= x0 - 2 and lx1 <= x1 + 2 and ly0 >= y0 - 2 and ly1 <= y1 + 2:
                    junto.append(i)
            elif c["tipo"] == "barra_v":
                if solapa_y and (x1 - 2 <= lx0 <= x1 + 40 or x0 + 2 >= lx1 >= x0 - 40):
                    junto.append(i)
                    c["lado"] = "izquierda" if lx0 >= x0 else "derecha"
            else:
                if min(x1, lx1) - max(x0, lx0) > 0.3 * (lx1 - lx0) and (0 <= ly0 - y1 <= 30 or 0 <= y0 - ly1 <= 30):
                    junto.append(i)
                    c["lado"] = "superior" if ly0 >= y1 - 2 else "inferior"
        c["junto_a"] = junto
        if c["tipo"] == "barra_v" and "lado" not in c:
            c["lado"] = "izquierda"
        if c["tipo"] == "barra_h" and "lado" not in c:
            c["lado"] = "inferior"


# ---------------------------------------------------------------- resolver el estilo de un .docx
class Resolutor:
    """Estilo efectivo (fuente, tamaño, negrita, cursiva, color, alineación) de un run o párrafo de un .docx."""

    def __init__(self, d):
        self.d = d
        est = d.styles.element
        self.estilos = {s.get(qn("w:styleId")): s for s in est.findall(qn("w:style"))}
        self.def_par = next((s for s in est.findall(qn("w:style")) if s.get(qn("w:type")) == "paragraph" and s.get(qn("w:default")) in ("1", "true")), None)
        dd = est.find(qn("w:docDefaults"))
        self.rpr_def = dd.find(qn("w:rPrDefault") + "/" + qn("w:rPr")) if dd is not None else None
        self.tema = {"minor": None, "major": None}
        try:
            for parte in d.part.package.parts:
                if parte.partname.endswith("theme1.xml"):
                    for k in self.tema:
                        m = re.search(rb"<a:" + k.encode() + rb'Font>\s*<a:latin typeface="([^"]+)"', parte.blob)
                        self.tema[k] = m.group(1).decode() if m else None
        except Exception:  # noqa: BLE001
            pass

    def cadena(self, sid):
        out, vistos = [], set()
        while sid and sid in self.estilos and sid not in vistos:
            vistos.add(sid)
            out.append(self.estilos[sid])
            b = self.estilos[sid].find(qn("w:basedOn"))
            sid = b.get(qn("w:val")) if b is not None else None
        return out

    def _estilo_parrafo(self, p_el):
        ps = p_el.find(qn("w:pPr") + "/" + qn("w:pStyle"))
        if ps is not None:
            return self.cadena(ps.get(qn("w:val")))
        return self.cadena(self.def_par.get(qn("w:styleId"))) if self.def_par is not None else []

    def _rprs(self, r_el, p_el):
        """Elementos w:rPr por prioridad: run, estilo de carácter, estilo de párrafo (y bases), docDefaults."""
        out = []
        rpr = r_el.find(qn("w:rPr")) if r_el is not None else None
        if rpr is not None:
            out.append(rpr)
            rs = rpr.find(qn("w:rStyle"))
            if rs is not None:
                out += [s.find(qn("w:rPr")) for s in self.cadena(rs.get(qn("w:val")))]
        # la marca de párrafo (pPr/rPr) no formatea los runs: solo cuenta el estilo
        out += [s.find(qn("w:rPr")) for s in self._estilo_parrafo(p_el)]
        out.append(self.rpr_def)
        return [x for x in out if x is not None]

    def _nombre(self, rf):
        if rf is None:
            return None
        n = rf.get(qn("w:ascii")) or rf.get(qn("w:hAnsi"))
        if n:
            return n
        th = rf.get(qn("w:asciiTheme")) or rf.get(qn("w:hAnsiTheme"))
        return self.tema["major" if th and th.startswith("major") else "minor"] if th else None

    def run(self, r_el, p_el):
        rprs = self._rprs(r_el, p_el)
        fuente = next((n for n in (self._nombre(x.find(qn("w:rFonts"))) for x in rprs) if n), None)
        pt = next((int(x.find(qn("w:sz")).get(qn("w:val"))) / 2 for x in rprs if x.find(qn("w:sz")) is not None), None)

        def flag(tag):
            for x in rprs:
                e = x.find(qn(tag))
                if e is not None:
                    return (e.get(qn("w:val")) or "true").lower() not in ("0", "false", "off")
            return False
        color = None
        for x in rprs:
            c = x.find(qn("w:color"))
            if c is not None:
                color = c.get(qn("w:val"))
                break
        color = ("#" + color.upper()) if color and RE_HEX.match("#" + color) else "#000000"
        return {"fuente": fuente or "?", "pt": pt or 10.0, "negrita": flag("w:b"), "cursiva": flag("w:i"), "color": color}

    def alineacion(self, p_el):
        jc = p_el.find(qn("w:pPr") + "/" + qn("w:jc"))
        if jc is None:
            for s in self._estilo_parrafo(p_el):
                jc = s.find(qn("w:pPr") + "/" + qn("w:jc"))
                if jc is not None:
                    break
        v = jc.get(qn("w:val")) if jc is not None else "left"
        return {"center": "centro", "right": "derecha", "end": "derecha", "both": "justificada", "distribute": "justificada"}.get(v, "izquierda")


def _sin_fallback(el, raiz):
    a = el.getparent()
    while a is not None and a is not raiz:
        if a.tag == ooxml.FALLBACK:
            return False
        a = a.getparent()
    return True


def _borde(el):
    """(color #RRGGBB, grosor pt) de un w:left/w:top…; None si no hay borde."""
    if el is None or el.get(qn("w:val")) in ("nil", "none", None):
        return None
    c = el.get(qn("w:color")) or "auto"
    col = ("#" + c.upper()) if RE_HEX.match("#" + c) else "#000000"
    sz = el.get(qn("w:sz"))
    return col, (int(sz) / 8 if sz and sz.isdigit() else 0.5)


def _fondo(shd):
    f = shd.get(qn("w:fill")) if shd is not None else None
    return ("#" + f.upper()) if f and RE_HEX.match("#" + f) and f.upper() != "FFFFFF" else None


def parrafos_cuerpo(d, incluir_toc=False):
    """[(w:p, en_tabla)] en orden de documento (tablas y controles de contenido incluidos)."""
    out = []

    def rec(el, en_tabla):
        for ch in el:
            if ch.tag == qn("w:p"):
                out.append((ch, en_tabla))
            elif ch.tag == qn("w:tbl"):
                for tr in ch.iterchildren(qn("w:tr")):
                    for tc in tr.iterchildren(qn("w:tc")):
                        rec(tc, True)
            elif ch.tag in (qn("w:sdt"), qn("w:customXml")):
                gal = ch.find(".//" + qn("w:docPartGallery"))
                if gal is not None and "Contents" in (gal.get(qn("w:val")) or "") and not incluir_toc:
                    continue
                cont = ch.find(qn("w:sdtContent"))
                rec(ch if cont is None else cont, en_tabla)
    rec(d.element.body, False)
    return out


def _nivel_enc(p_el, res):
    for s in res._estilo_parrafo(p_el):
        m = re.match(r"(?:heading|t[ií]tulo)\s*(\d)", (s.find(qn("w:name")).get(qn("w:val")) if s.find(qn("w:name")) is not None else "").lower())
        if m:
            return int(m.group(1))
    return 0


def _titulo_limpio(t):
    t = unicodedata.normalize("NFD", t)
    t = "".join(c for c in t if unicodedata.category(c) != "Mn").lower()
    return re.sub(r"^\s*(?:[0-9]+(?:\.[0-9]+)*\.?|[ivxlc]+\.)\s+", "", t).strip().rstrip(":.")


def ambito_parrafos(d, res, ambito):
    """Párrafos (w:p, en_tabla) del ámbito: portada (hasta el primer salto de sección o de página, o el primer encabezado),
    documento (todo) o seccion:<nombre> (desde el encabezado con ese nombre hasta el siguiente de su nivel o superior)."""
    todos = parrafos_cuerpo(d)
    if ambito == "documento":
        return todos
    if ambito == "portada":
        out = []
        for p_el, tb in todos:
            texto = ooxml.texto_xml(p_el).strip()
            if _nivel_enc(p_el, res) and (out or texto):
                break
            salto = p_el.find(qn("w:pPr") + "/" + qn("w:pageBreakBefore")) is not None or any(
                b.get(qn("w:type")) == "page" for b in p_el.iter(qn("w:br")))
            if salto and out:
                break
            out.append((p_el, tb))
            if p_el.find(qn("w:pPr") + "/" + qn("w:sectPr")) is not None:
                break
        return out
    nombre = _titulo_limpio(ambito.split(":", 1)[1])
    out, nivel = [], None
    for p_el, tb in todos:
        n = _nivel_enc(p_el, res) if not tb else 0
        if nivel is None:
            if n and _titulo_limpio(ooxml.texto_xml(p_el)) == nombre:
                nivel = n
                out.append((p_el, tb))
        elif n and n <= nivel:
            break
        else:
            out.append((p_el, tb))
    return out


def lineas_docx(d, ambito="portada", res=None):
    """Líneas de un .docx en el ámbito: [{texto, fuente, pt, negrita, cursiva, color, alineacion, relleno, bordes}] más las cajas."""
    res = res or Resolutor(d)
    lineas = []
    for p_el, en_tabla in ambito_parrafos(d, res, ambito):
        ppr = p_el.find(qn("w:pPr"))
        relleno = _fondo(ppr.find(qn("w:shd"))) if ppr is not None else None
        bordes = {}
        if ppr is not None:
            pb = ppr.find(qn("w:pBdr"))
            for lado, tags in LADO_XML.items():
                for t in tags:
                    b = _borde(pb.find(qn("w:" + t))) if pb is not None else None
                    if b:
                        bordes[lado] = b
        if en_tabla:
            tc = next((a for a in p_el.iterancestors() if a.tag == qn("w:tc")), None)
            if tc is not None:
                tcpr = tc.find(qn("w:tcPr"))
                if tcpr is not None:
                    relleno = relleno or _fondo(tcpr.find(qn("w:shd")))
                    tb = tcpr.find(qn("w:tcBorders"))
                    for lado, tags in LADO_XML.items():
                        for t in tags:
                            b = _borde(tb.find(qn("w:" + t))) if tb is not None else None
                            if b and lado not in bordes:
                                bordes[lado] = b
        segs = [[]]  # líneas visuales: un w:br de línea abre una nueva
        for r_el in p_el.iter(qn("w:r")):
            if not _sin_fallback(r_el, p_el):
                continue
            est = None
            for n in r_el:
                if n.tag in (ooxml.W_T, ooxml.W_TAB):
                    est = est or res.run(r_el, p_el)
                    segs[-1].append(((n.text or "") if n.tag == ooxml.W_T else " ", est))
                elif n.tag == ooxml.W_BR and n.get(qn("w:type")) not in ("page", "column"):
                    segs.append([])
        alin = res.alineacion(p_el)
        for seg in segs:
            texto = colapsar("".join(t for t, _ in seg))
            if not texto:
                continue
            pesos = {}
            for t, e in seg:
                if t.strip():
                    k = (e["fuente"], e["pt"], e["negrita"], e["cursiva"], e["color"])
                    pesos[k] = pesos.get(k, 0) + len(t.strip())
            f, pt, neg, cur, col = max(pesos, key=pesos.get)
            lineas.append({"texto": texto, "fuente": f, "pt": pt, "negrita": neg, "cursiva": cur, "color": col,
                           "alineacion": alin, "relleno": relleno, "bordes": bordes, "_p": p_el})
    return lineas


def medir_docx(ruta, ambito="portada"):
    import auditar
    d = auditar.abrir_docx(str(ruta))
    lineas = lineas_docx(d, ambito)
    cajas = []
    for i, l in enumerate(lineas):
        if l["relleno"]:
            if cajas and cajas[-1]["tipo"] == "relleno" and cajas[-1]["color"] == l["relleno"] and cajas[-1]["junto_a"][-1] == i - 1:
                cajas[-1]["junto_a"].append(i)
            else:
                cajas.append({"tipo": "relleno", "color": l["relleno"], "junto_a": [i]})
        for lado, (col, gr) in l["bordes"].items():
            tipo = "barra_v" if lado in ("izquierda", "derecha") else "barra_h"
            previa = next((c for c in cajas if c["tipo"] == tipo and c.get("lado") == lado and c["color"] == col and c.get("grosor") == gr
                           and c["junto_a"][-1] == i - 1), None)
            if previa:
                previa["junto_a"].append(i)
            else:
                cajas.append({"tipo": tipo, "lado": lado, "color": col, "grosor": gr, "junto_a": [i]})
    salida = [{k: v for k, v in l.items() if k not in ("_p", "relleno", "bordes")} for l in lineas]
    return {"origen": pathlib.Path(ruta).name, "ambito": ambito, "lineas": salida, "cajas": cajas}


def medir(ruta, pagina=1, ambito="portada", fijo_todo=False):
    ruta = pathlib.Path(ruta)
    if not ruta.is_file():
        cli.error(f"no existe el modelo: {ruta}")
    ext = ruta.suffix.lower()
    if ext == ".pdf":
        spec = medir_pdf(ruta, pagina)
    elif ext == ".docx":
        spec = medir_docx(ruta, ambito)
    else:
        cli.error(f"modelo no soportado ({ext}): usa .pdf o .docx")
    if fijo_todo:
        for l in spec["lineas"]:
            l["fijo"] = True
    return spec


# ---------------------------------------------------------------- spec
def cargar_spec(ruta):
    """Lee y normaliza una spec JSON. Completa negrita/cursiva/alineación/color si faltan (se deducen del nombre de la fuente y la caja).
    ErrorModelo si no es una spec válida."""
    ruta = pathlib.Path(ruta)
    try:
        spec = json.loads(ruta.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as e:
        raise ErrorModelo(f"spec ilegible ({ruta}): {e}")
    if not isinstance(spec, dict) or not isinstance(spec.get("lineas"), list) or not spec["lineas"]:
        raise ErrorModelo(f"spec inválida ({ruta}): falta la lista `lineas`")
    ancho = (spec.get("pagina") or [None])[0]
    izq = min((l["bbox"][0] for l in spec["lineas"] if isinstance(l, dict) and l.get("bbox")), default=None)
    der = max((l["bbox"][2] for l in spec["lineas"] if isinstance(l, dict) and l.get("bbox")), default=None)
    for n, l in enumerate(spec["lineas"], 1):
        if not isinstance(l, dict) or not isinstance(l.get("texto"), str) or not l.get("fuente") or not isinstance(l.get("pt"), (int, float)):
            raise ErrorModelo(f"spec inválida ({ruta}): la línea {n} necesita texto, fuente y pt")
        f = l["fuente"]
        l.setdefault("negrita", "bold" in f.lower())
        l.setdefault("cursiva", bool(re.search(r"(?i)italic|oblique", f)))
        l["color"] = str(l.get("color") or "#000000").upper()
        if not RE_HEX.match(l["color"]):
            raise ErrorModelo(f"spec inválida ({ruta}): línea {n}, color {l['color']!r} no es #RRGGBB")
        if not l.get("alineacion"):
            b = l.get("bbox")
            if b and ancho and abs((b[0] + b[2]) / 2 - ancho / 2) <= 8:
                l["alineacion"] = "centro"
            elif b and der is not None and abs(b[2] - der) <= 6 and abs(b[0] - izq) > 6:
                l["alineacion"] = "derecha"
            else:
                l["alineacion"] = "izquierda"
    cajas = []
    for c in spec.get("cajas") or []:
        if isinstance(c, dict) and c.get("tipo"):
            cajas.append(c)
    # formato antiguo: `dibujos` = [{rect, fill, color, width}] sin asociación a líneas
    vistos_color = set()
    for dib in spec.get("dibujos") or []:
        if isinstance(dib, dict) and dib.get("rect") and dib.get("fill"):
            x0, y0, x1, y1 = dib["rect"]
            if min(x1 - x0, y1 - y0) > 4 and _hex(dib["fill"]) != "#FFFFFF" and _hex(dib["fill"]) not in vistos_color:
                vistos_color.add(_hex(dib["fill"]))
                cajas.append({"tipo": "relleno", "color": _hex(dib["fill"]), "bbox": dib["rect"], "junto_a": [], "aproximada": True})
    spec["cajas"] = cajas
    return spec


# ---------------------------------------------------------------- comparar
def comparar(spec, lineas):
    """Diferencias entre las líneas del documento y la spec: [{linea (n.º en la spec o None), texto, diferencias [str]}]."""
    difs = []
    j = 0
    mapa = {}  # índice de la spec -> índice de la línea del documento
    nlin = len(lineas)
    textos = [colapsar(l["texto"]) for l in lineas]
    sl = spec["lineas"]

    def proxima_fija(i):
        return next((colapsar(x["texto"]) for x in sl[i + 1:] if x.get("fijo")), None)

    for i, s in enumerate(sl):
        t = colapsar(s["texto"])
        if s.get("fijo"):
            k = next((k for k in range(j, nlin) if textos[k] == t), None)
            if k is None:
                antes = next((k for k in range(0, j) if textos[k] == t), None)
                difs.append({"linea": i + 1, "texto": t, "diferencias": [
                    "línea fija fuera de orden" if antes is not None else "línea fija ausente"]})
                continue
            j = k + 1
            mapa[i] = k
        else:
            if j >= nlin or textos[j] == proxima_fija(i):
                difs.append({"linea": i + 1, "texto": t, "diferencias": [f"falta el campo «{s.get('campo') or t[:30]}»"]})
                continue
            mapa[i] = j
            j += 1
        d = lineas[mapa[i]]
        dif = []
        if norm_fuente(d["fuente"]) != norm_fuente(s["fuente"]):
            dif.append(f"fuente {d['fuente']} (modelo {s['fuente']})")
        if abs(d["pt"] - s["pt"]) > TOL_PT:
            dif.append(f"tamaño {d['pt']:g} pt (modelo {s['pt']:g})")
        if bool(d["negrita"]) != bool(s["negrita"]) and not s.get("nombre_negrita"):
            dif.append("sin negrita" if s["negrita"] else "con negrita (el modelo no)")
        if bool(d["cursiva"]) != bool(s["cursiva"]):
            dif.append("sin cursiva" if s["cursiva"] else "con cursiva (el modelo no)")
        if d["color"].upper() != s["color"].upper():
            dif.append(f"color {d['color']} (modelo {s['color']})")
        if clase_alin(d["alineacion"]) != clase_alin(s["alineacion"]) or (
                s["alineacion"] == "justificada" and d["alineacion"] != "justificada"):
            dif.append(f"alineación {d['alineacion']} (modelo {s['alineacion']})")
        if dif:
            difs.append({"linea": i + 1, "texto": colapsar(d["texto"]), "diferencias": dif})
    # el orden de las líneas fijas ya se comprobó al avanzar j; una línea fija hallada antes de j quedó marcada como fuera de orden
    for c in spec["cajas"]:
        difs += _comparar_caja(c, lineas, mapa)
    return difs


def _comparar_caja(c, lineas, mapa):
    tipo = c["tipo"]
    idx = [mapa[i] for i in c.get("junto_a") or [] if i in mapa]
    a_donde = (" junto a «" + colapsar(lineas[idx[0]]["texto"])[:30] + "»") if idx else ""
    cand = [lineas[k] for k in idx] if idx else lineas
    col = c.get("color", "").upper()
    if tipo == "relleno":
        if idx and any(l["relleno"] and l["relleno"].upper() == col for l in cand):
            return []
        if not idx and any(l["relleno"] and l["relleno"].upper() == col for l in lineas):
            return []
        otro = next((l["relleno"] for l in cand if l["relleno"]), None)
        return [{"linea": None, "texto": a_donde.strip(), "diferencias": [
            f"caja de relleno {col} ausente{a_donde}" + (f" (hay relleno {otro})" if otro else "")]}]
    lados = [c.get("lado")] if c.get("lado") else (list(LADOS) if tipo == "marco" else ["izquierda"])
    out = []
    for lado in lados:
        mejor = None
        for l in cand:
            b = l["bordes"].get(lado)
            if b and b[0].upper() == col and (c.get("grosor") is None or abs(b[1] - c["grosor"]) <= TOL_PT):
                mejor = b
                break
            mejor = mejor or b
        if mejor and mejor[0].upper() == col and (c.get("grosor") is None or abs(mejor[1] - c["grosor"]) <= TOL_PT):
            continue
        gr = f" de {c['grosor']:g} pt" if c.get("grosor") else ""
        out.append({"linea": None, "texto": a_donde.strip(), "diferencias": [
            f"borde {lado} {col}{gr} ausente{a_donde}" + (f" (hay {mejor[0]} de {mejor[1]:g} pt)" if mejor else "")]})
    return out


def comparar_docx(ruta, spec, ambito="portada"):
    import auditar
    d = auditar.abrir_docx(str(ruta))
    return comparar(spec, lineas_docx(d, ambito))


# ---------------------------------------------------------------- CLI
def main(argv=None):
    ap = argparse.ArgumentParser(prog="editorial modelo", description="Mide un modelo de formato (PDF o .docx) y lo compara con un documento.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("medir", help="escribe la spec JSON de un modelo")
    m.add_argument("modelo")
    m.add_argument("--pagina", type=int, default=1, help="página del PDF (por defecto 1)")
    m.add_argument("--ambito", default="portada", help="portada | documento | seccion:<nombre> (solo .docx)")
    m.add_argument("--fijo-todo", action="store_true", dest="fijo_todo", help="marca todas las líneas como texto fijo")
    m.add_argument("--out", required=True, metavar="RUTA")
    c = sub.add_parser("comparar", help="compara un .docx con una spec (lo que hace INS-015)")
    c.add_argument("documento")
    c.add_argument("spec")
    c.add_argument("--ambito", default="portada")
    c.add_argument("--json", metavar="RUTA")
    a = ap.parse_args(argv)
    cli.utf8()
    if a.cmd == "medir":
        spec = medir(a.modelo, a.pagina, a.ambito, a.fijo_todo)
        cli.escribir_json(a.out, spec)
        print(f"escrito {a.out}: {len(spec['lineas'])} líneas, {len(spec['cajas'])} cajas")
        return 0
    try:
        spec = cargar_spec(a.spec)
    except ErrorModelo as e:
        cli.error(str(e))
    import auditar
    auditar.validar_entrada(a.documento, (".docx",))
    difs = comparar_docx(a.documento, spec, a.ambito)
    for x in difs:
        print(f"línea {x['linea'] or '-'} «{x['texto'][:50]}»: " + "; ".join(x["diferencias"]))
    print(f"{len(difs)} diferencias con el modelo" if difs else "el documento reproduce el modelo")
    cli.escribir_json(a.json, difs)
    return 1 if difs else 0


if __name__ == "__main__":
    sys.exit(main())
