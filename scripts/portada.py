#!/usr/bin/env python3
"""Portada institucional como función propia: la construye desde el perfil y el modelo vinculante, y la comprueba.

Uso:
  python scripts/editorial.py portada <doc.docx> [--out RUTA] [--campo nombre=valor ...] [--perfil ID] [--equipo .editorial.yaml]
                              [--sin-ajuste] [--json RUTA]

Qué hace: lee `formato: portada:` de .editorial.yaml (campos en orden y sus textos) y el `vinculante` tipo `modelo` con ámbito
`portada` (la spec que mide `editorial.py modelo medir`: fuente, tamaño, negrita, cursiva, color, alineación, espacio previo y cajas
con relleno y borde izquierdo) y construye la portada. Reemplaza la portada del documento (la que detecta `auditar.fin_portada`)
conservando su `w:sectPr` (numeración y márgenes); nunca escribe sobre el original: la salida es `<doc>.portada.docx` o `--out`.

Contenido de cada campo, en este orden de prioridad: `--campo nombre=valor` (el nombre es una parte del nombre del campo, sin
acentos ni mayúsculas: `--campo docente="MC. Ana Pérez"`); el `literal` del perfil; el título fijado con `titulo:` o el que ya tiene
la portada; la línea de la portada actual que corresponde al campo. Un campo sin valor queda `[[PENDIENTE]]` (EA-001 lo bloquea en
la entrega). Integrantes: `--campo "integrantes=Ana Pérez:21330001; Luis Gómez"` (sin número queda pendiente) o, para rellenar los
números después, `--campo "control.Ana=21330001"` (parte del nombre del integrante). El título admite `|` para forzar el salto de línea.

Modelo: las líneas de la spec se asocian a los campos por su marca `"campo": "<nombre>"` (recomendado: edita la spec medida) o, sin
marca, por su contenido (el literal o el patrón del campo). Las líneas sin campo (p. ej. la asignatura o la carrera) toman, en orden,
las líneas de la portada actual que no son de ningún campo: nunca se inventa texto. Las líneas de una caja (`cajas` de la spec con
`junto_a`) van en una tabla de una celda con el relleno y la barra de borde del modelo. Sin spec, sale una portada centrada en
Times New Roman 12 pt.

Una línea con `"y_fija": true` en la spec (el pie con el lugar y la fecha) se ancla a su posición absoluta en la página; las demás se
colocan a la distancia del modelo respecto de la línea anterior.

Espaciado: se calcula desde las cajas de texto del modelo (espacio entre líneas, múltiplo de interlineado, sangría negativa si una
línea mide más que la caja de texto) y se afina midiendo la portada con LibreOffice (hasta 5 vueltas, error final en el resultado);
sin LibreOffice o con `--sin-ajuste` queda la estimación inicial. Con una fila de logos las posiciones solo se desplazan lo que ocupa
la fila.

Logos: `formato: portada: logos: [{nombre: ITE, ruta: logos/ith.png, alto_cm: 2}, ...]` (rutas relativas al .editorial.yaml) pone una
tabla sin bordes arriba de la portada con las imágenes centradas a la misma altura; si falta un archivo queda el hueco y se avisa.

Después de construir corre INS-010 e INS-015 sobre el resultado: código 1 si hay diferencias (incluidos los números de control
pendientes de INS-010), 2 si falta el perfil de portada, el archivo o la herramienta.
"""
import argparse
import copy
import os
import pathlib
import re
import sys
import tempfile
from xml.sax.saxutils import escape

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import auditar  # noqa: E402
import cli  # noqa: E402
import institucional  # noqa: E402
import libreoffice  # noqa: E402
import modelo_formato as MF  # noqa: E402
from docx import Document  # noqa: E402
from docx.oxml import parse_xml  # noqa: E402
from docx.oxml.ns import nsdecls, qn  # noqa: E402
from docx.shared import Cm  # noqa: E402

PENDIENTE = "[[PENDIENTE]]"
RAZON_LINEA = 1.149      # paso de línea sencillo de Times New Roman en LibreOffice, en múltiplos del cuerpo
PAD_ARRIBA = PAD_ABAJO = 6.0
RE_FILA_PERSONA = re.compile(r"^(.*?)\s*(?:[—–]|\s-\s)\s*(.*)$")
EMPIEZA_INTEGRANTES = ("integrant", "autor", "alumn", "estudiant", "equipo")


def _sin(t):
    return institucional._sin(t)


def tw(pt):
    return int(round(pt * 20))


def nombre_fuente(f):
    """«TimesNewRomanPS-BoldMT» -> «Times New Roman»; «Calibri» se queda igual."""
    n = re.sub(r"^[A-Z]{6}\+", "", f or "")
    n = re.split(r"[-,]", n, maxsplit=1)[0]
    n = re.sub(r"(?i)(?:mt|ps)+$", "", n)
    return n if " " in n else re.sub(r"(?<=[a-z])(?=[A-Z])", " ", n) or "Times New Roman"


def _fuente_fitz(nombre, negrita, cursiva):
    base = "he" if re.search(r"(?i)arial|helvet|calibri|verdana", nombre) else "co" if re.search(r"(?i)courier|mono|consol", nombre) else "ti"
    if base == "ti":
        return "tibi" if negrita and cursiva else "tibo" if negrita else "tiit" if cursiva else "tiro"
    if base == "he":
        return "hebi" if negrita and cursiva else "hebo" if negrita else "heit" if cursiva else "helv"
    return "cobi" if negrita and cursiva else "cobo" if negrita else "coit" if cursiva else "cour"


# Anchos de Helvetica en milésimas del cuerpo (métricas AFM estándar de Adobe); respaldo cuando no hay PyMuPDF.
_HELV = dict(zip("ABCDEFGHIJKLMNOPQRSTUVWXYZ", (667, 667, 722, 722, 667, 611, 778, 722, 278, 500, 667, 556, 833,
                                                722, 778, 667, 778, 722, 667, 611, 722, 667, 944, 667, 667, 611)))
_HELV.update(zip("abcdefghijklmnopqrstuvwxyz", (556, 556, 500, 556, 556, 278, 556, 556, 222, 222, 500, 222, 833,
                                                556, 556, 556, 556, 333, 500, 278, 556, 500, 722, 500, 500, 500)))
_HELV.update({c: 556 for c in "0123456789"})
_HELV.update({" ": 278, ".": 278, ",": 278, ":": 278, ";": 278, "-": 333, "—": 1000, "–": 556, "(": 333, ")": 333,
              "/": 278, "'": 191, '"': 355, "«": 556, "»": 556})


# Factor sobre Helvetica por familia y peso: (mayúsculas, resto), medido con PyMuPDF sobre texto en español.
_FACTOR = {("he", False): (1.0, 1.0), ("he", True): (1.02, 1.08), ("ti", False): (0.99, 0.89), ("ti", True): (1.04, 0.95)}


def _ancho_aprox(texto, nombre, pt, negrita):
    """Ancho en pt con las métricas de Helvetica y un factor por familia y peso (Courier: 0.6 fijo)."""
    import unicodedata
    fam = _fuente_fitz(nombre, negrita, False)[:2]
    if fam == "co":
        return 0.6 * pt * len(texto)
    f_may, f_resto = _FACTOR[(fam, bool(negrita))]
    total = 0.0
    for c in texto:
        b = unicodedata.normalize("NFD", c)[0]
        total += _HELV.get(b, 556 if b.isalpha() else 500) * (f_may if b.isupper() else f_resto)
    return total / 1000 * pt


def ancho_texto(texto, nombre, pt, negrita, cursiva):
    """Ancho aproximado en pt de `texto` (métricas de PyMuPDF); sin PyMuPDF, métricas AFM de Helvetica (_ancho_aprox)."""
    try:
        import fitz
        return fitz.Font(_fuente_fitz(nombre, negrita, cursiva)).text_length(texto, fontsize=pt)
    except Exception:  # noqa: BLE001
        return _ancho_aprox(texto, nombre, pt, negrita)


# ---------------------------------------------------------------- XML
def _rpr(est, negrita=None):
    f = escape(est["fuente_docx"])
    neg = est["negrita"] if negrita is None else negrita
    sz = int(round(est["pt"] * 2))
    return (f'<w:rPr><w:rFonts w:ascii="{f}" w:hAnsi="{f}" w:cs="{f}" w:eastAsia="{f}"/>'
            + ("<w:b/><w:bCs/>" if neg else "") + ("<w:i/><w:iCs/>" if est["cursiva"] else "")
            + f'<w:color w:val="{est["color"].lstrip("#")}"/><w:sz w:val="{sz}"/><w:szCs w:val="{sz}"/></w:rPr>')


def parrafo_xml(runs, est, antes_pt, mult=1.0, sangria_neg_tw=0, despues_pt=0.0):
    """w:p con los `runs` [(texto, negrita|None)], el estilo `est` y el espaciado dado."""
    jc = {"centro": "center", "derecha": "right", "justificada": "both"}.get(est["alineacion"], "left")
    line = int(round(240 * mult))
    xml = (f'<w:p {nsdecls("w")}><w:pPr><w:spacing w:before="{tw(antes_pt)}" w:after="{tw(despues_pt)}" w:line="{line}" w:lineRule="auto"/>'
           f'<w:ind w:left="{-sangria_neg_tw}" w:right="{-sangria_neg_tw}" w:firstLine="0"/><w:jc w:val="{jc}"/></w:pPr>')
    for texto, neg in runs:
        xml += f'<w:r>{_rpr(est, neg)}<w:t xml:space="preserve">{escape(texto)}</w:t></w:r>'
    return parse_xml(xml + "</w:p>")


def caja_xml(parrafos, caja, ancho_tw, ind_tw, margen_izq_tw, pad_arriba_pt, pad_abajo_pt):
    """Tabla de una celda con el relleno y la barra de borde del modelo (`caja`: {relleno, barra: (color, grosor, lado)})."""
    bordes = {"top": "nil", "bottom": "nil", "right": "nil", "left": "nil"}
    celda_b = ""
    for lado in ("top", "left", "bottom", "right"):
        b = caja.get("bordes", {}).get(lado)
        if b:
            celda_b += f'<w:{lado} w:val="single" w:sz="{max(2, int(round(b[1] * 8)))}" w:space="0" w:color="{b[0].lstrip("#")}"/>'
        else:
            celda_b += f'<w:{lado} w:val="nil"/>'
    shd = f'<w:shd w:val="clear" w:color="auto" w:fill="{caja["relleno"].lstrip("#")}"/>' if caja.get("relleno") else ""
    xml = (f'<w:tbl {nsdecls("w")}><w:tblPr><w:tblW w:w="{ancho_tw}" w:type="dxa"/><w:tblInd w:w="{ind_tw}" w:type="dxa"/>'
           '<w:tblBorders><w:top w:val="nil"/><w:left w:val="nil"/><w:bottom w:val="nil"/><w:right w:val="nil"/><w:insideH w:val="nil"/><w:insideV w:val="nil"/></w:tblBorders>'
           f'<w:tblLayout w:type="fixed"/><w:tblCellMar><w:top w:w="{tw(pad_arriba_pt)}" w:type="dxa"/><w:left w:w="{margen_izq_tw}" w:type="dxa"/>'
           f'<w:bottom w:w="{tw(pad_abajo_pt)}" w:type="dxa"/><w:right w:w="150" w:type="dxa"/></w:tblCellMar></w:tblPr>'
           f'<w:tblGrid><w:gridCol w:w="{ancho_tw}"/></w:tblGrid><w:tr><w:trPr><w:cantSplit/></w:trPr><w:tc><w:tcPr><w:tcW w:w="{ancho_tw}" w:type="dxa"/>'
           f'<w:tcBorders>{celda_b}</w:tcBorders>{shd}</w:tcPr></w:tc></w:tr></w:tbl>')
    tbl = parse_xml(xml)
    tc = tbl.find(".//" + qn("w:tc"))
    for p in parrafos:
        tc.append(p)
    return tbl


# ---------------------------------------------------------------- perfil y modelo
def cargar_config(doc, equipo):
    """(formato normalizado, ruta de .editorial.yaml). Error de uso si no hay `formato: portada:`."""
    ruta = auditar.buscar_equipo(doc, equipo)
    if not ruta or not ruta.exists():
        cli.error("no hay .editorial.yaml (pásalo con --equipo o ponlo junto al documento): la portada se declara en `formato: portada:`")
    f, _av = auditar.formato_equipo(doc, equipo)
    if not (f.get("portada") or {}).get("campos"):
        cli.error(f"{ruta}: falta `formato: portada: campos:`; la portada se construye desde ese bloque (ver docs/PERFILES-INSTITUCIONALES.md)")
    return f, ruta


def normalizar_logos(logos, base):
    """[{nombre, ruta (Path|None), alto_cm}] de `portada: logos:`; los nombres sueltos (formato antiguo) no llevan imagen."""
    out = []
    for x in logos or []:
        if isinstance(x, dict):
            r = pathlib.Path(str(x["ruta"])) if x.get("ruta") else None
            if r is not None and not r.is_absolute():
                r = pathlib.Path(base) / r
            try:
                alto = float(x.get("alto_cm") or 2.0)
            except (TypeError, ValueError):
                alto = 2.0
            out.append({"nombre": str(x.get("nombre") or (r.stem if r else "logo")), "ruta": r, "alto_cm": alto})
    return out


def spec_portada(f):
    for v in f.get("vinculante") or []:
        if v["tipo"] == "modelo" and v["ambito"] == "portada":
            return v["spec"], v
    return None, None


def estilo_de(l):
    f = l.get("fuente") or "Times New Roman"
    return {"fuente_docx": nombre_fuente(f), "pt": float(l.get("pt") or 12), "negrita": bool(l.get("negrita")),
            "cursiva": bool(l.get("cursiva")), "color": (l.get("color") or "#000000").upper(),
            "alineacion": l.get("alineacion") or "centro"}


# ---------------------------------------------------------------- lo que ya tiene la portada
def raices_portada(d, pars_aud):
    """Elementos de primer nivel de la portada actual (vacío si `auditar.fin_portada` no detecta portada)."""
    if auditar.fin_portada(pars_aud) == 0:
        return []
    out, vistos = [], set()
    for p_el, _tb in MF.ambito_parrafos(d, MF.Resolutor(d), "portada"):
        t = p_el
        while t.getparent() is not None and t.getparent().tag != qn("w:body"):
            t = t.getparent()
        if id(t) not in vistos:
            vistos.add(id(t))
            out.append(t)
    return out


def es_integrantes(c):
    return _sin(c["nombre"]).startswith(EMPIEZA_INTEGRANTES)


def persona_de_linea(t):
    """(nombre, número de control o None) de una línea «Nombre — No. de control: NNN»."""
    t = " ".join(t.split())
    m = RE_FILA_PERSONA.match(t)
    nombre = (m.group(1) if m else t).strip()
    resto = m.group(2) if m else t
    c = institucional.RE_CONTROL.search(resto)
    return nombre, (c.group(0) if c else None)


def leer_existente(d, raices, campos, titulo_fijo):
    """{nombre del campo: texto o lista de personas} y extras (líneas de la portada sin campo) de la portada actual."""
    lineas = MF.lineas_docx(d, "portada")
    textos = [l["texto"] for l in lineas]
    bus = {c["nombre"]: institucional._buscador(c) for c in campos if "titulo" not in c}
    uso = [None] * len(textos)
    valores = {}
    ultimo = -1
    for c in campos:
        if "titulo" in c or es_integrantes(c):
            continue
        k = next((k for k, t in enumerate(textos) if uso[k] is None and bus[c["nombre"]](t)), None)
        if k is not None:
            uso[k] = c["nombre"]
            if not c.get("literal"):  # el literal del perfil manda sobre lo que haya en la portada actual
                valores[c["nombre"]] = textos[k]
    for c in campos:
        if es_integrantes(c):
            k = next((k for k, t in enumerate(textos) if uso[k] is None and (bus[c["nombre"]](t) or institucional.RE_INTEGRANTES.match(t))), None)
            if k is None:
                continue
            uso[k] = c["nombre"]
            personas, tc0 = [], next((a for a in lineas[k]["_p"].iterancestors(qn("w:tc"))), None)
            inline = institucional.RE_INTEGRANTES.match(textos[k])
            if inline and inline.group(2).strip():
                for x in institucional.RE_PERSONAS.split(inline.group(2)):
                    if x.strip():
                        personas.append(persona_de_linea(x))
            j = k + 1
            while j < len(textos) and uso[j] is None:
                mismo = tc0 is not None and next((a for a in lineas[j]["_p"].iterancestors(qn("w:tc"))), None) is tc0
                if not mismo and (tc0 is not None or any(f(textos[j]) for f in bus.values())):
                    break
                if tc0 is None and (textos[j].rstrip().endswith(":") or institucional.RE_ETIQUETA_PORTADA.match(textos[j])):
                    break
                uso[j] = c["nombre"]
                personas.append(persona_de_linea(textos[j]))
                j += 1
            valores[c["nombre"]] = personas
    tit = next((c for c in campos if "titulo" in c), None)
    if tit is not None:
        otros = [f for n, f in bus.items()]
        ini = next((k for k, t in enumerate(textos) if uso[k] is None and institucional._candidato_titulo(t, otros)), None)
        if ini is not None:
            fin = ini
            def mismo_estilo(k):
                return lineas[k]["pt"] == lineas[ini]["pt"] and lineas[k]["negrita"] == lineas[ini]["negrita"] and lineas[k]["color"] == lineas[ini]["color"]
            # las líneas siguientes con el estilo de la primera son del mismo título aunque sean cortas («SUPERIOR»)
            while fin + 1 < len(textos) and uso[fin + 1] is None and not any(f(textos[fin + 1]) for f in otros) and (
                    institucional._candidato_titulo(textos[fin + 1], otros) or (mismo_estilo(fin + 1) and not textos[fin + 1].rstrip().endswith(":"))):
                fin += 1
            for k in range(ini, fin + 1):
                uso[k] = tit["nombre"]
            valores[tit["nombre"]] = " ".join(textos[ini:fin + 1])
    extras = [(textos[k], lineas[k]) for k in range(len(textos)) if uso[k] is None]
    return valores, extras


def aplicar_campos_cli(campos, valores, cli_campos, avisos):
    """Mezcla `--campo` en `valores`; devuelve el dict de personas con controles por rellenar [(fragmento, número)]."""
    controles = []
    for clave, val in cli_campos:
        k = _sin(clave).strip()
        if k.startswith("control"):
            frag = k[len("control"):].lstrip(".: ").strip()
            controles.append((frag, val.strip()))
            continue
        c = next((c for c in campos if k == _sin(c["nombre"]) or k in _sin(c["nombre"]) or _sin(c["nombre"]).startswith(k)), None)
        if c is None:
            avisos.append(f"--campo {clave}: ningún campo del perfil se llama así ({', '.join(c['nombre'][:25] for c in campos)})")
            continue
        if es_integrantes(c):
            personas = []
            for x in re.split(r"\s*;\s*", val):
                if not x.strip():
                    continue
                m = institucional.RE_CONTROL.search(x)
                nombre = re.sub(r"\s*(?:[:(—–-]\s*)?(?:No\.? de control:?\s*)?\(?" + re.escape(m.group(0)) + r"\)?", "", x).strip(" :—–-") if m else x.strip()
                personas.append((nombre, m.group(0) if m else None))
            valores[c["nombre"]] = personas
        else:
            valores[c["nombre"]] = val
    return controles


def rellenar_controles(valores, campos, controles, avisos):
    ints = next((c for c in campos if es_integrantes(c)), None)
    if not controles or ints is None:
        return
    personas = [list(p) for p in valores.get(ints["nombre"], [])]
    libres = [x for x in controles if not x[0]]
    for frag, num in controles:
        if not frag:
            continue
        hit = [p for p in personas if _sin(frag) in _sin(p[0])]
        if len(hit) != 1:
            avisos.append(f"--campo control.{frag}: {'ningún integrante' if not hit else 'varios integrantes'} coincide con «{frag}»")
            continue
        hit[0][1] = num
    nums = [n for _, n in libres for n in re.split(r"\s*[,;]\s*", n) if n]
    for p, n in zip([p for p in personas if not p[1]], nums):
        p[1] = n
    valores[ints["nombre"]] = [tuple(p) for p in personas]


# ---------------------------------------------------------------- asociación spec -> campos
def reclamar(spec_lineas, campos):
    """Grupos [{campo, idx}] de líneas consecutivas de la spec; `campo` es el nombre del campo del perfil o None (libre)."""
    nombres = [c["nombre"] for c in campos]
    bus = {c["nombre"]: institucional._buscador(c) for c in campos if "titulo" not in c}
    dueno = []
    for l in spec_lineas:
        m = _sin(str(l.get("campo") or "")).strip()
        hit = None
        if m:
            hit = next((n for n in nombres if _sin(n) == m), None) or next((n for n in nombres if m in _sin(n) or _sin(n).startswith(m)), None)
        elif not l.get("_libre"):
            hit = next((n for n in nombres if n in bus and bus[n](l["texto"])), None)
        dueno.append(hit)
    tit = next((c["nombre"] for c in campos if "titulo" in c), None)
    if tit and tit not in dueno:
        libres = [i for i, d_ in enumerate(dueno) if d_ is None and not spec_lineas[i].get("campo")]
        if libres:
            mayor = max(spec_lineas[i]["pt"] for i in libres)
            ini = next(i for i in libres if abs(spec_lineas[i]["pt"] - mayor) < 0.5)
            fin = ini
            while fin + 1 < len(dueno) and dueno[fin + 1] is None and abs(spec_lineas[fin + 1]["pt"] - mayor) < 0.5:
                fin += 1
            for i in range(ini, fin + 1):
                dueno[i] = tit
    grupos = []
    for i, dn in enumerate(dueno):
        if grupos and grupos[-1]["campo"] == dn and dn is not None:
            grupos[-1]["idx"].append(i)
        else:
            grupos.append({"campo": dn, "idx": [i]})
    vistos, final = set(), []
    for g in grupos:  # un campo reclamado en dos sitios: el segundo grupo pasa a libre
        if g["campo"] is not None and g["campo"] in vistos:
            g = {"campo": None, "idx": g["idx"]}
        if g["campo"] is not None:
            vistos.add(g["campo"])
        final.append(g)
    return final


def espacio_antes(spec_lineas, i):
    l = spec_lineas[i]
    if l.get("espacio_antes") is not None:
        return float(l["espacio_antes"])
    if i > 0 and l.get("bbox") and spec_lineas[i - 1].get("bbox"):
        return max(0.0, l["bbox"][1] - spec_lineas[i - 1]["bbox"][3])
    return 12.0 if i else 0.0


def multiplo(spec_lineas, i):
    """Interlineado de una línea que continúa a la anterior del mismo campo (paso entre líneas / paso sencillo)."""
    if i == 0 or not (spec_lineas[i].get("bbox") and spec_lineas[i - 1].get("bbox")):
        return 1.0
    paso = spec_lineas[i]["bbox"][1] - spec_lineas[i - 1]["bbox"][1]
    r = paso / (RAZON_LINEA * spec_lineas[i]["pt"])
    return next((m for m in (1.0, 1.15, 1.5, 2.0) if abs(r - m) < 0.12), 1.0)


def caja_de(spec, idxs):
    """{relleno, bordes{lado: (color, grosor)}, bbox} de las cajas de la spec que acompañan a alguna de las líneas `idxs`."""
    out = {"relleno": None, "bordes": {}, "bbox": None}
    for c in spec.get("cajas") or []:
        if not set(c.get("junto_a") or []) & set(idxs):
            continue
        if c["tipo"] == "relleno":
            out["relleno"] = c["color"]
            out["bbox"] = c.get("bbox") or out["bbox"]
        elif c["tipo"] == "barra_v":
            out["bordes"]["left" if c.get("lado", "izquierda") == "izquierda" else "right"] = (c["color"], c.get("grosor") or 3.0)
            out["bbox_barra"] = c.get("bbox")
        elif c["tipo"] == "barra_h":
            out["bordes"]["bottom" if c.get("lado") == "inferior" else "top"] = (c["color"], c.get("grosor") or 1.0)
        elif c["tipo"] == "marco":
            for lado in ("top", "left", "bottom", "right"):
                out["bordes"][lado] = (c["color"], c.get("grosor") or 1.0)
    return out if (out["relleno"] or out["bordes"]) else None


# ---------------------------------------------------------------- plan de la portada
def spec_por_defecto(campos):
    """Spec mínima sin modelo: centrada, Times New Roman 12 pt, el título en 16 pt negrita, 12 pt entre líneas."""
    lineas = []
    for c in campos:
        pt, neg = (16.0, True) if "titulo" in c else (12.0, False)
        lineas.append({"texto": c.get("literal") or c["nombre"], "fuente": "Times New Roman", "pt": pt, "negrita": neg, "cursiva": False,
                       "color": "#000000", "alineacion": "izquierda" if es_integrantes(c) else "centro", "espacio_antes": 0.0 if not lineas else 18.0,
                       "campo": c["nombre"]})
    return {"lineas": lineas, "cajas": []}


def planificar(campos, spec, valores, extras, f, avisos):
    """Lista de bloques de la portada (párrafos y cajas) con su texto, estilo y espaciado inicial."""
    sl = spec["lineas"]
    grupos = reclamar(sl, campos)
    pendientes_extra = list(extras)
    claimed = {g["campo"] for g in grupos if g["campo"]}
    # campos sin línea en la spec: se insertan tras el campo anterior del perfil con el estilo de la línea anterior
    orden = [c["nombre"] for c in campos]
    for c in campos:
        if c["nombre"] in claimed:
            continue
        avisos.append(f"el modelo no tiene línea para «{c['nombre']}»: se usó el estilo de la línea anterior")
        k = orden.index(c["nombre"])
        pos = next((i for i in range(len(grupos) - 1, -1, -1) if grupos[i]["campo"] in orden[:k]), -1)
        ref = grupos[pos]["idx"][-1] if pos >= 0 else 0
        grupos.insert(pos + 1, {"campo": c["nombre"], "idx": [ref], "sintetico": True})
    bloques, n_por_campo = [], {}
    por_nombre = {c["nombre"]: c for c in campos}
    ancho_texto_pt = f["_ancho_texto_pt"]
    for g in grupos:
        idx = g["idx"]
        if g["campo"] is None:  # líneas libres: las del documento que no son de ningún campo, en orden
            for i in idx:
                if not pendientes_extra:
                    continue
                texto, lin = pendientes_extra.pop(0)
                est = estilo_de(sl[i])
                bloques.append({"tipo": "p", "runs": [(texto, None)], "est": est, "objetivo": espacio_antes(sl, i), "mult": 1.0,
                                "antes": espacio_antes(sl, i), "campo": None, "texto": texto})
            continue
        c = por_nombre[g["campo"]]
        val = valores.get(c["nombre"])
        if es_integrantes(c):
            personas = val if isinstance(val, list) and val else []
            if not personas:
                personas = [("", None)]
            etiqueta = next((sl[i]["texto"] for i in idx if institucional.RE_INTEGRANTES.match(sl[i]["texto"])), None)
            ests = [estilo_de(sl[i]) for i in idx]
            caja = caja_de(spec, idx)
            filas = []
            if etiqueta is not None or len(idx) > 1:
                filas.append(("etiqueta", (etiqueta or "INTEGRANTES").strip(), ests[0], idx[0]))
                est_p, i_p = (ests[1], idx[1]) if len(idx) > 1 else (ests[0], idx[0])
                i_gap = idx[2] if len(idx) > 2 else idx[1] if len(idx) > 1 else idx[0]
            else:
                est_p, i_p, i_gap = ests[0], idx[0], idx[0]
            for k, (nombre, ctrl) in enumerate(personas):
                filas.append(("persona", (nombre or PENDIENTE, ctrl), est_p, i_p if k == 0 else i_gap))
            ps = []
            for k, (tipo, dato, est, i) in enumerate(filas):
                if tipo == "etiqueta":
                    runs = [(dato, None)]
                else:
                    nombre, ctrl = dato
                    resto = f" — No. de control: {ctrl or PENDIENTE}" if f["portada"].get("numero_control", True) else ""
                    negrita_nombre = bool(sl[i].get("nombre_negrita"))
                    runs = [(nombre, negrita_nombre or None), (resto, False)] if resto else [(nombre, negrita_nombre or None)]
                ps.append({"tipo": "p", "runs": runs, "est": est, "antes": 0.0 if k == 0 else espacio_antes(sl, i), "objetivo": 0.0 if k == 0 else espacio_antes(sl, i),
                           "mult": 1.0, "campo": c["nombre"], "texto": "".join(t for t, _ in runs), "en_caja": True})
            ps[0]["objetivo"] = espacio_antes(sl, idx[0])
            ps[0]["ref_bloque"] = True
            bloques.append({"tipo": "caja", "parrafos": ps, "caja": caja, "campo": c["nombre"], "idx": idx,
                            "antes": espacio_antes(sl, idx[0]), "objetivo": espacio_antes(sl, idx[0])})
            continue
        # campo de texto: una o varias líneas
        texto = val if isinstance(val, str) and val.strip() else (c.get("literal") or "")
        if not texto.strip():
            texto = PENDIENTE
        est0 = estilo_de(sl[idx[0]])
        mayus = sl[idx[0]]["texto"].isupper() and "titulo" in c
        partes = [x.strip() for x in texto.split("|")] if "|" in texto else None
        if "titulo" in c:
            texto_t = texto.replace("|", " ") if partes else texto
            if mayus:
                texto_t = texto_t.upper()
            if partes:
                lins = [x.upper() if mayus else x for x in partes]
            else:
                lins = []
                actual = ""
                tope = ancho_texto_pt + 2 * 10  # la sangría negativa deja hasta 10 pt a cada lado
                for w in texto_t.split():
                    prueba = (actual + " " + w).strip()
                    if actual and ancho_texto(prueba, est0["fuente_docx"], est0["pt"], est0["negrita"], est0["cursiva"]) > tope:
                        lins.append(actual)
                        actual = w
                    else:
                        actual = prueba
                if actual:
                    lins.append(actual)
            if len(lins) != len(idx):
                avisos.append(f"el título ocupa {len(lins)} líneas y el modelo trae {len(idx)}: INS-015 compara las líneas en orden; ajusta la spec "
                              "(una línea de título por línea final) o acorta el título")
            mult = multiplo(sl, idx[1]) if len(idx) > 1 else (multiplo(sl, idx[0]) if False else 1.0)
            for j, lin in enumerate(lins):
                i = idx[min(j, len(idx) - 1)]
                w = ancho_texto(lin, est0["fuente_docx"], est0["pt"], est0["negrita"], est0["cursiva"])
                neg = max(0, int(round(((w - ancho_texto_pt) / 2 + 2) * 20))) if est0["alineacion"] == "centro" and w > ancho_texto_pt else 0
                gap = espacio_antes(sl, idx[0]) if j == 0 else espacio_antes(sl, idx[min(j, len(idx) - 1)])
                bloques.append({"tipo": "p", "runs": [(lin, None)], "est": est0, "antes": gap, "objetivo": gap, "mult": mult, "campo": c["nombre"],
                                "texto": lin, "sangria": neg})
        else:
            lins = partes or [texto]
            for j, lin in enumerate(lins):
                i = idx[min(j, len(idx) - 1)]
                est = estilo_de(sl[i])
                w = ancho_texto(lin, est["fuente_docx"], est["pt"], est["negrita"], est["cursiva"])
                neg = max(0, int(round(((w - ancho_texto_pt) / 2 + 2) * 20))) if est["alineacion"] == "centro" and w > ancho_texto_pt else 0
                bloques.append({"tipo": "p", "runs": [(lin, None)], "est": est, "antes": espacio_antes(sl, i), "objetivo": espacio_antes(sl, i), "mult": 1.0,
                                "campo": c["nombre"], "texto": lin, "sangria": neg, "spec_i": i})
    if pendientes_extra:
        avisos.append(f"{len(pendientes_extra)} líneas de la portada actual no tienen sitio en el modelo y se agregaron al final: "
                      + "; ".join(t[:40] for t, _ in pendientes_extra[:3]))
        for texto, lin in pendientes_extra:
            ref = next((b for b in reversed(bloques) if b["tipo"] == "p"), None)
            est = dict(ref["est"]) if ref else estilo_de({"fuente": lin.get("fuente"), "pt": lin.get("pt"), "negrita": lin.get("negrita"),
                                                         "cursiva": lin.get("cursiva"), "color": lin.get("color"), "alineacion": lin.get("alineacion")})
            bloques.append({"tipo": "p", "runs": [(texto, None)], "est": est, "antes": 6.0, "objetivo": None, "mult": 1.0, "campo": None, "texto": texto})
    return bloques


def objetivos_x(b, spec):
    """(borde izquierdo de la caja, x del texto) del modelo, en pt; None donde la spec no los trae."""
    caja = b["caja"] or {}
    barra = caja.get("bbox_barra") or caja.get("bbox")
    borde = barra[0] if barra else None
    bb = spec["lineas"][b["idx"][0]].get("bbox")
    return borde, (bb[0] if bb else None)


def horizontal_inicial(b, spec, geom):
    """{ind, izq, pad_a, pad_b}: tblInd y margen izquierdo de celda en twips. Con compatibilidad de Word 2013+ (modo 15) tblInd mide
    hasta el borde de la tabla; en modos anteriores hasta el texto. Sin posiciones en el modelo: -30 y 212 (la caja de la guía ITE)."""
    borde, texto = objetivos_x(b, spec)
    aj = {"ind": -30, "izq": 212, "pad_a": None, "pad_b": None}
    if borde is not None and texto is not None:
        aj["izq"] = max(0, tw(texto - borde))
        aj["ind"] = tw((borde if geom.get("modo_nuevo") else texto) - geom["izq"])
    return aj


def pad_caja(caja, spec, idxs):
    """(arriba, abajo) en pt del relleno de la caja alrededor de sus líneas, desde los bbox de la spec; 6 pt si no hay."""
    sl = spec["lineas"]
    if caja and caja.get("bbox") and all(sl[i].get("bbox") for i in idxs):
        b = caja["bbox"]
        return max(0.0, sl[idxs[0]]["bbox"][1] - b[1]), max(0.0, b[3] - sl[idxs[-1]]["bbox"][3])
    return PAD_ARRIBA, PAD_ABAJO


# ---------------------------------------------------------------- construcción en el documento
def construir_xml(bloques, spec, geom, cajas_ajuste):
    """Elementos lxml de la portada (sin sectPr)."""
    els = []
    for b in bloques:
        if b["tipo"] == "p":
            els.append(parrafo_xml(b["runs"], b["est"], b["antes"], b.get("mult", 1.0), b.get("sangria", 0)))
        else:
            ps = [parrafo_xml(p["runs"], p["est"], p["antes"], 1.0, 0, 0.0) for p in b["parrafos"]]
            cajas_ajuste["_geom"] = geom
            aj = cajas_ajuste.setdefault(b["campo"], horizontal_inicial(b, spec, geom))
            pa, pb = pad_caja(b["caja"], spec, b["idx"])
            aj["pad_a"] = pa if aj["pad_a"] is None else aj["pad_a"]
            aj["pad_b"] = pb if aj["pad_b"] is None else aj["pad_b"]
            # espacio previo de la caja: párrafo vacío mínimo no; se usa el espaciado del primer párrafo de la celda (antes) desplazado
            tbl = caja_xml(ps, b["caja"] or {}, geom["ancho_tw"], aj["ind"], aj["izq"], aj["pad_a"], aj["pad_b"])
            antes_caja = max(0.0, b["antes"] - aj["pad_a"])
            if antes_caja > 0.0:  # separación previa: un párrafo diminuto sin texto que solo aporta espacio
                els.append(parse_xml(f'<w:p {nsdecls("w")}><w:pPr><w:spacing w:before="{tw(antes_caja)}" w:after="0" w:line="20" w:lineRule="exact"/></w:pPr></w:p>'))
            els.append(tbl)
    return els


def fila_logos(d, logos, geom, avisos):
    """Tabla sin bordes con los logos centrados (o None si no hay logos declarados con imagen)."""
    if not logos:
        return None
    n = len(logos)
    t = d.add_table(rows=1, cols=n)
    tbl = t._tbl
    tbl.getparent().remove(tbl)
    pr = tbl.tblPr
    for x in list(pr):
        if x.tag in (qn("w:tblStyle"), qn("w:tblW"), qn("w:tblLook"), qn("w:tblBorders")):
            pr.remove(x)
    pr.append(parse_xml(f'<w:tblW {nsdecls("w")} w:w="{geom["ancho_tw"]}" w:type="dxa"/>'))
    pr.append(parse_xml(f'<w:tblBorders {nsdecls("w")}><w:top w:val="nil"/><w:left w:val="nil"/><w:bottom w:val="nil"/><w:right w:val="nil"/>'
                        '<w:insideH w:val="nil"/><w:insideV w:val="nil"/></w:tblBorders>'))
    pr.append(parse_xml(f'<w:tblLayout {nsdecls("w")} w:type="fixed"/>'))
    for col, g in zip(tbl.tblGrid.findall(qn("w:gridCol")), logos):
        col.set(qn("w:w"), str(geom["ancho_tw"] // n))
    for celda, lg in zip(t.rows[0].cells, logos):
        celda.width = int(geom["ancho_tw"] // n * 635)
        p = celda.paragraphs[0]
        p.alignment = 1
        p.paragraph_format.space_before = p.paragraph_format.space_after = 0
        if lg["ruta"] and lg["ruta"].is_file():
            p.add_run().add_picture(str(lg["ruta"]), height=Cm(lg["alto_cm"]))
        else:
            avisos.append(f"logo «{lg['nombre']}»: no existe {lg['ruta'] or '(sin ruta)'}; queda el hueco")
    return tbl


def geometria(d, raices):
    """Márgenes y ancho de texto (pt, twips) de la sección de la portada."""
    sect = None
    for r in raices:
        sect = r.find(qn("w:pPr") + "/" + qn("w:sectPr")) if r.tag == qn("w:p") else None
        if sect is not None:
            break
    if sect is None:
        sect = d.element.body.find(qn("w:sectPr"))
    g = {"izq": 72.0, "der": 72.0, "arriba": 72.0, "ancho_pagina": 612.0}
    if sect is not None:
        mar, sz = sect.find(qn("w:pgMar")), sect.find(qn("w:pgSz"))
        if mar is not None:
            g["izq"] = int(mar.get(qn("w:left"), 1440)) / 20
            g["der"] = int(mar.get(qn("w:right"), 1440)) / 20
            g["arriba"] = int(mar.get(qn("w:top"), 1440)) / 20
        if sz is not None:
            g["ancho_pagina"] = int(sz.get(qn("w:w"), 12240)) / 20
    modo = 12
    for x in d.settings.element.iter(qn("w:compatSetting")):
        if x.get(qn("w:name")) == "compatibilityMode" and (x.get(qn("w:val")) or "").isdigit():
            modo = int(x.get(qn("w:val")))
    g["modo_nuevo"] = modo >= 15
    g["ancho_texto"] = g["ancho_pagina"] - g["izq"] - g["der"]
    g["ancho_tw"] = tw(g["ancho_texto"])
    return g


def aplicar(entrada, bloques, spec, logos, cajas_ajuste, avisos):
    """Abre `entrada`, reemplaza su portada por los bloques y devuelve (Document, número de elementos nuevos al inicio del cuerpo)."""
    d = Document(str(entrada))
    pars, _ = auditar.cargar_docx(str(entrada))
    raices = raices_portada(d, pars)
    geom = geometria(d, raices)
    body = d.element.body
    sect = None
    salto_pagina = False
    for r in raices:
        s = r.find(qn("w:pPr") + "/" + qn("w:sectPr")) if r.tag == qn("w:p") else None
        if s is not None:
            sect = copy.deepcopy(s)
        if any(b.get(qn("w:type")) == "page" for b in r.iter(qn("w:br"))):
            salto_pagina = True
    nuevos = []
    fl = fila_logos(d, logos, geom, avisos) if logos else None
    if fl is not None:
        nuevos.append(fl)
    nuevos += construir_xml(bloques, spec, geom, cajas_ajuste)
    # la portada termina en un párrafo: lleva el sectPr de la original o el salto de página
    if sect is not None or salto_pagina or not raices:
        if sect is not None and nuevos and nuevos[-1].tag == qn("w:p"):
            cierre = nuevos.pop()
        else:
            cierre = parse_xml(f'<w:p {nsdecls("w")}><w:pPr><w:spacing w:before="0" w:after="0" w:line="20" w:lineRule="exact"/></w:pPr></w:p>')
        if sect is not None:
            cierre.find(qn("w:pPr")).append(sect)
        else:
            cierre.append(parse_xml(f'<w:r {nsdecls("w")}><w:br w:type="page"/></w:r>'))
        nuevos.append(cierre)
    ancla = raices[0] if raices else next(iter(body), None)
    for el in nuevos:
        ancla.addprevious(el)
    for r in raices:
        body.remove(r)
    return d, len(nuevos)


# ---------------------------------------------------------------- medición y ajuste
def norm_t(t):
    return re.sub(r"\s+", " ", t or "").strip().lower()


def medir_portada(d, k_nuevos, tmpdir):
    """(líneas [(texto, x0, y0, y1)], rellenos [(color, x0, y0, x1, y1)]) de la primera página del documento recortado a la portada."""
    ruta = pathlib.Path(tmpdir) / "mini.docx"
    d.save(str(ruta))
    m = Document(str(ruta))
    hijos = list(m.element.body)
    for el in hijos[k_nuevos:-1]:
        m.element.body.remove(el)
    m.save(str(ruta))
    pdf = libreoffice.a_pdf(ruta, tmpdir)
    fitz = libreoffice.requerir_pymupdf()
    with fitz.open(str(pdf)) as doc:
        pg = doc[0]
        lineas = []
        for b in pg.get_text("dict")["blocks"]:
            for ln in b.get("lines", []):
                t = "".join(s["text"] for s in ln["spans"]).strip()
                if t:
                    lineas.append((t, ln["bbox"][0], ln["bbox"][1], ln["bbox"][3]))
        lineas.sort(key=lambda x: (round(x[2]), x[1]))
        rell = []
        for dib in pg.get_drawings():
            if dib.get("fill") is not None:
                r = dib["rect"]
                rell.append((MF._hex(dib["fill"]), r.x0, r.y0, r.x1, r.y1))
    return lineas, rell


def ajustar(entrada, bloques, spec, logos, avisos, max_vueltas=5, tol=0.35):
    """Afina el espaciado midiendo en LibreOffice. Devuelve (Document final, informe)."""
    cajas_ajuste = {}
    info = {"vueltas": 0, "error_max_pt": None, "ajustado": False}
    with tempfile.TemporaryDirectory(prefix="portada-") as tmp:
        for v in range(max_vueltas + 1):
            av = []
            d, k = aplicar(entrada, bloques, spec, logos, cajas_ajuste, av)
            if v == 0:
                avisos.extend(av)
            if v == max_vueltas:
                break
            try:
                lineas, rell = medir_portada(d, k, tmp)
            except SystemExit:
                raise
            planos = []
            for b in bloques:
                planos += b["parrafos"] if b["tipo"] == "caja" else [b]
            usados, pos = set(), []
            for p in planos:
                clave = norm_t(p["texto"])[:22]
                j = next((j for j, l in enumerate(lineas) if j not in usados and norm_t(l[0]).startswith(clave)), None)
                if j is None:
                    pos.append(None)
                    continue
                usados.add(j)
                pos.append(lineas[j])
            errores = []
            prev = None
            dueno = {id(p): b for b in bloques if b["tipo"] == "caja" for p in b["parrafos"]}
            for p, l in zip(planos, pos):
                if l is None:
                    prev = None
                    continue
                destino = dueno[id(p)] if p.get("ref_bloque") else p
                sp_i = spec["lineas"][p["spec_i"]] if p.get("spec_i") is not None else None
                if sp_i is not None and sp_i.get("y_fija") and sp_i.get("bbox") and not logos:
                    err = sp_i["bbox"][1] - l[2]   # línea anclada a su posición absoluta en la página (pie de la portada)
                elif prev is not None and p.get("objetivo") is not None:
                    err = p["objetivo"] - (l[2] - prev[3])
                elif prev is None and p is planos[0] and spec["lineas"][0].get("bbox") and not logos and p.get("objetivo") is not None:
                    err = spec["lineas"][0]["bbox"][1] - l[2]
                else:
                    err = None
                if err is not None:
                    errores.append(abs(err))
                    destino["antes"] = max(0.0, destino["antes"] + err)
                prev = l
            # caja: separación previa (objetivo) y pad inferior
            for b in bloques:
                if b["tipo"] != "caja":
                    continue
                aj = cajas_ajuste.get(b["campo"])
                if aj is None:
                    continue
                primero = next((l for p, l in zip(planos, pos) if p is b["parrafos"][0]), None)
                ultimo = next((l for p, l in zip(planos, pos) if p is b["parrafos"][-1]), None)
                color = (b["caja"] or {}).get("relleno")
                rr = [r for r in rell if color and r[0] == color and (r[3] - r[1]) > 100]
                if primero and rr:
                    caja_pdf = (min(r[1] for r in rr), min(r[2] for r in rr), max(r[3] for r in rr), max(r[4] for r in rr))
                    pa_obj, pb_obj = pad_caja(b["caja"], spec, b["idx"])
                    err_a = (primero[2] - caja_pdf[1]) - pa_obj
                    aj["pad_a"] = max(0.0, aj["pad_a"] - err_a)
                    errores.append(abs(err_a))
                    if os.environ.get("EDITORIAL_DEBUG"):
                        print("  dbg caja_pdf", [round(x, 1) for x in caja_pdf], "aj", aj, "rell", [(r[0], round(r[1]), round(r[2]), round(r[3]), round(r[4])) for r in rell], file=sys.stderr)
                    if ultimo:
                        err_b = (caja_pdf[3] - ultimo[3]) - pb_obj
                        aj["pad_b"] = max(0.0, aj["pad_b"] - err_b)
                        errores.append(abs(err_b))
                # posición horizontal: borde de la caja y texto (el modo de compatibilidad decide qué mueve tblInd)
                borde_t, texto_t = objetivos_x(b, spec)
                geom = cajas_ajuste.get("_geom") or {}
                colores = {c for c in ((b["caja"] or {}).get("relleno"), *((v[0] for v in (b["caja"] or {}).get("bordes", {}).values()))) if c}
                bordes_pdf = [r[1] for r in rell if r[0] in colores]
                if primero and texto_t is not None and borde_t is not None and bordes_pdf:
                    err_borde, err_texto = borde_t - min(bordes_pdf), texto_t - primero[1]
                    errores += [abs(err_borde), abs(err_texto)]
                    aj["ind"] += tw(err_borde if geom.get("modo_nuevo") else err_texto)
                    aj["izq"] = max(0, aj["izq"] + tw(err_texto - err_borde))
            if os.environ.get("EDITORIAL_DEBUG"):
                for p_, l_ in zip(planos, pos):
                    print("  dbg", v, repr(p_["texto"][:28]), "antes", round(p_["antes"], 1), "obj", p_.get("objetivo"), "y0", l_ and round(l_[2], 1), "y1", l_ and round(l_[3], 1), "x0", l_ and round(l_[1], 1), file=sys.stderr)
                print("  dbg errores", [round(e, 1) for e in errores], file=sys.stderr)
            info["vueltas"] = v + 1
            info["error_max_pt"] = round(max(errores), 2) if errores else None
            info["ajustado"] = True
            if errores and max(errores) <= tol:
                d, k = aplicar(entrada, bloques, spec, logos, cajas_ajuste, [])
                break
    return d, info


# ---------------------------------------------------------------- CLI
def construir(documento, salida=None, cli_campos=(), equipo=None, ajuste=True, perfil=None):
    """Construye la portada. Devuelve el resultado (dict) o termina con código 2."""
    auditar.validar_entrada(documento, (".docx",))
    f, ruta_eq = cargar_config(documento, equipo)
    cfg = f["portada"]
    campos = cfg["campos"]
    entrada = pathlib.Path(documento).resolve()
    out = pathlib.Path(salida).resolve() if salida else entrada.with_name(entrada.stem + ".portada.docx")
    if out == entrada:
        cli.error("la salida coincide con el original: la portada nunca se escribe sobre el original (usa --out distinto)")
    avisos = []
    d0 = auditar.abrir_docx(str(entrada))
    pars, _ = auditar.cargar_docx(str(entrada))
    raices0 = raices_portada(d0, pars)
    existe = bool(raices0)
    if not existe:
        avisos.append("el documento no tiene portada detectable (auditar.fin_portada = 0): se inserta una nueva al inicio")
    valores, extras = leer_existente(d0, raices0, campos, f.get("titulo_fijo")) if existe else ({}, [])
    if f.get("titulo_fijo"):
        t = next((c for c in campos if "titulo" in c), None)
        if t:
            valores[t["nombre"]] = f["titulo_fijo"]
    controles = aplicar_campos_cli(campos, valores, [tuple(x.split("=", 1)) if "=" in x else (x, "") for x in cli_campos], avisos)
    rellenar_controles(valores, campos, controles, avisos)
    spec, vinc = spec_portada(f)
    if spec is None:
        avisos.append("sin `vinculante` tipo modelo con ámbito portada: se usa una portada centrada en Times New Roman 12 pt")
        spec = spec_por_defecto(campos)
    geom = geometria(d0, raices0)
    f["_ancho_texto_pt"] = geom["ancho_texto"]
    logos = normalizar_logos(cfg.get("logos") if any(isinstance(x, dict) for x in cfg.get("logos") or []) else None, ruta_eq.parent)
    for lin in spec["lineas"]:
        lin["fuente_docx"] = nombre_fuente(lin.get("fuente"))
    bloques = planificar(campos, spec, valores, extras, f, avisos)
    info = {"vueltas": 0, "error_max_pt": None, "ajustado": False}
    if ajuste and libreoffice.buscar() and spec.get("lineas") and any(l.get("bbox") for l in spec["lineas"]):
        d, info = ajustar(entrada, bloques, spec, logos, avisos)
    else:
        if ajuste and not libreoffice.buscar():
            avisos.append("sin LibreOffice: espaciado estimado desde el modelo, sin medir (" + libreoffice.INSTALAR + ")")
        d, _k = aplicar(entrada, bloques, spec, logos, {}, avisos)
    d.save(str(out))
    pend = sum(1 for b in bloques for p in (b["parrafos"] if b["tipo"] == "caja" else [b]) if PENDIENTE in "".join(t for t, _ in p["runs"]))
    texto_campo = {}
    for b in bloques:
        for p in (b["parrafos"] if b["tipo"] == "caja" else [b]):
            if p.get("campo") and not p.get("en_caja"):
                texto_campo[p["campo"]] = (texto_campo.get(p["campo"]) + " " if p["campo"] in texto_campo else "") + p["texto"]
    campos_res = {c["nombre"]: valores.get(c["nombre"]) if es_integrantes(c) else texto_campo.get(c["nombre"]) for c in campos}
    return {"salida": str(out), "campos": campos_res, "pendientes": pend, "avisos": avisos,
            "ajuste": info, "perfil_equipo": str(ruta_eq), "modelo": vinc["id"] if vinc else None}


def comprobar(salida, perfil, equipo):
    """Hallazgos INS-010 e INS-015 sobre la salida."""
    r = auditar.auditar(str(salida), perfil, equipo)
    return [h for h in r["hallazgos"] if h["id"] in ("INS-010", "INS-015")]


def main(argv=None):
    ap = argparse.ArgumentParser(prog="editorial portada", description="Construye la portada institucional desde el perfil y el modelo vinculante.")
    ap.add_argument("documento")
    ap.add_argument("--out", metavar="RUTA", help="salida (por defecto <doc>.portada.docx)")
    ap.add_argument("--campo", action="append", default=[], metavar="NOMBRE=VALOR", help="valor de un campo (repetible); control.<integrante>=NNNNNNNN rellena un número de control")
    ap.add_argument("--perfil", help="id de perfil; por defecto el `perfil:` de .editorial.yaml")
    ap.add_argument("--equipo", help="ruta de .editorial.yaml (si no, se busca hacia arriba desde el documento)")
    ap.add_argument("--sin-ajuste", action="store_true", dest="sin_ajuste", help="no medir con LibreOffice: espaciado estimado desde el modelo")
    ap.add_argument("--json", metavar="RUTA")
    a = ap.parse_args(argv)
    cli.utf8()
    perfil = cli.perfil_por_defecto(ap, a.perfil, a.documento, a.equipo)
    r = construir(a.documento, a.out, a.campo, a.equipo, not a.sin_ajuste, perfil)
    hall = comprobar(r["salida"], perfil, a.equipo)
    r["hallazgos"] = hall
    print(f"portada escrita en {r['salida']}")
    if r["ajuste"]["ajustado"]:
        print(f"  espaciado medido en LibreOffice: {r['ajuste']['vueltas']} vueltas, error máximo {r['ajuste']['error_max_pt']} pt")
    for k, v in r["campos"].items():
        txt = "; ".join(f"{n}{' (' + c + ')' if c else ' [[PENDIENTE]]'}" for n, c in v) if isinstance(v, list) else (v or "[[PENDIENTE]]")
        print(f"  {k}: {txt}")
    for av in r["avisos"]:
        print("aviso:", av)
    if r["pendientes"]:
        print(f"{r['pendientes']} campos con [[PENDIENTE]] (los bloquea EA-001 en la entrega)")
    for h in hall:
        print(f"{h['id']} {h['severidad']}: {h['ubicacion']}: {h['evidencia']}")
    print(f"INS-010 e INS-015: {len(hall)} diferencias" if hall else "INS-010 e INS-015: la portada reproduce el perfil y el modelo")
    cli.escribir_json(a.json, r)
    return cli.HALLAZGOS if hall else cli.OK


if __name__ == "__main__":
    sys.exit(main())
