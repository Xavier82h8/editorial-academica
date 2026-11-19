#!/usr/bin/env python3
"""Corrector determinista de .docx para las reglas mecánicas con «Fix auto: sí» del checklist APA 7.

Uso: python -I corregir.py documento.docx [--perfil apa7] [--out salida.docx] [--solo APA-002,APA-004] [--json res.json]
`--perfil` por defecto: el de `.editorial.yaml`. Salida: 0 si no quedan hallazgos críticos ni mayores tras corregir;
1 si quedan; 2 error de uso o de entrada (ver cli.py).

Se guía por los hallazgos de auditar.py y reutiliza sus lectores (cargar_docx, partir, fin_portada, ...) para
tocar exactamente los párrafos que el juez evalúa. Nunca sobrescribe el original: por defecto escribe
<nombre>.corregido.docx. Al final re-audita la salida y muestra el conteo de hallazgos antes/después.
"""
import argparse
import copy
import pathlib
import re
import sys
import unicodedata

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import auditar  # noqa: E402
import cli  # noqa: E402
import maquetacion  # noqa: E402
import ooxml  # noqa: E402

from docx.enum.text import WD_ALIGN_PARAGRAPH  # noqa: E402
from docx.oxml import OxmlElement  # noqa: E402
from docx.oxml.ns import qn  # noqa: E402
from docx.shared import Inches, Pt  # noqa: E402
from docx.text.paragraph import Paragraph  # noqa: E402
from docx.text.run import Run  # noqa: E402

TNR = "Times New Roman"
MONO = ("courier", "consolas", "cascadia", "menlo", "monaco", "lucida console", "source code", "mono")
SIMBOLO = ("symbol", "wingdings", "webdings", "cambria math")
ESTILOS_FUENTE_OMITIDOS = ("footnote", "endnote", "header", "footer")
ESTILOS_TAMANO = ("normal", "body text", "first paragraph", "heading 1", "heading 2", "heading 3", "heading 4",
                  "heading 5", "title", "bibliography", "subtitle", "block text", "quote", "text body", "compact",
                  "título 1", "título 2", "título 3", "título 4", "título 5", "título", "texto independiente")
RE_PREFIJO_NUM = re.compile(r"^\s*(?:\d{1,2}(?:\.\d{1,2})*\.?|[A-Z]\.|[IVXL]+\.)\s+")
# regla -> grupo de corrección
REGLAS = {"APA-001": "margenes", "APA-002": "fuente", "APA-003": "fuente", "APA-004": "interlineado",
          "APA-005": "espaciado", "APA-006": "alineacion", "APA-007": "sangria", "APA-008": "pagina",
          "APA-025": "encabezados", "APA-026": "encabezados", "APA-027": "encabezados", "APA-030": "numeracion",
          "APA-059": "rotulo", "APA-012": "rotulo", "APA-060": "refs_formato", "APA-061": "refs_orden",
          "APA-028": "enc_linea", "APA-029": "enc_linea", "APA-036": "narrativa", "APA-037": "conjuncion", "APA-043": "orden_cita", "APA-076": "doi",
          "APA-065": "sigla", "APA-093": "tablas", "APA-145": "puntuacion", "APA-115": "puntuacion",
          "IEEE-140": "puntuacion", "EST-010": "paginacion", "EST-011": "paginacion", "EST-012": "maqueta",
          "EST-013": "maqueta", "EST-014": "maqueta"}
# reglas que solo se corrigen en parte: lo que sobra se informa como no automático
NO_AUTO = {"APA-028": "encabezados de nivel 4 con estilo «Heading 4»: requieren fusionar el encabezado con el párrafo siguiente",
           "APA-029": "encabezados de nivel 5 con estilo «Heading 5»: requieren fusionar el encabezado con el párrafo siguiente",
           "APA-036": "citas legales sin año, p. ej. «(art. 16, fr. VI)» o «(LFDA, art. 27)»: decidir la obra y el año a mano"}
NO_AUTO["EST-015"] = "nota de tabla/figura sin formato APA: elegir la obra; plantilla propuesta en /estructura"
NO_AUTO["EST-016"] = "numeración de la portada: decisión del usuario o de la institución; --portada-numero si|no o `portada_numero:` en .editorial.yaml"
PARCIALES = set(NO_AUTO)
MODOS_PAGINACION = ("encabezado", "pie", "ninguna")


# ---------------------------------------------------------------- utilidades XML
def elementos(d):
    """Elementos w:p en el mismo orden que auditar.cargar_docx (cuerpo, tablas, w:sdt; sin índice TOC)."""
    out = []

    def rec(el):
        for ch in el:
            if ch.tag == qn("w:p"):
                out.append(ch)
            elif ch.tag == qn("w:tbl"):
                for tr in ch.iterchildren(qn("w:tr")):
                    for tc in tr.iterchildren(qn("w:tc")):
                        rec(tc)
            elif ch.tag in (qn("w:sdt"), qn("w:customXml")):
                gal = ch.find(".//" + qn("w:docPartGallery"))
                if gal is not None and "Contents" in (gal.get(qn("w:val")) or ""):
                    continue
                cont = ch.find(qn("w:sdtContent"))
                rec(ch if cont is None else cont)
    rec(d.element.body)
    return out


def es_mono(nombre):
    n = (nombre or "").lower()
    return n.startswith(MONO) or "mono" in n or any(n.startswith(s) for s in SIMBOLO)


def nombre_rfonts(rf):
    if rf is None:
        return None
    return rf.get(qn("w:ascii")) or rf.get(qn("w:hAnsi"))


def poner_tnr(rf):
    for a in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
        if rf.get(qn(a)) is not None:
            del rf.attrib[qn(a)]
    for a in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rf.set(qn(a), TNR)


def en_math(el):
    a = el.getparent()
    while a is not None:
        if a.tag.endswith("}oMath") or a.tag.endswith("}oMathPara"):
            return True
        a = a.getparent()
    return False


def limpiar_ind_chars(p_el):
    ind = p_el.find(qn("w:pPr") + "/" + qn("w:ind"))
    if ind is not None:
        for a in ("w:firstLineChars", "w:hangingChars", "w:leftChars", "w:startChars"):
            if ind.get(qn(a)) is not None:
                del ind.attrib[qn(a)]


def fijar_interlineado(par):
    par.paragraph_format.line_spacing = 2.0


def fijar_espaciado(par):
    pf = par.paragraph_format
    pf.space_before = Pt(0)
    pf.space_after = Pt(0)
    sp = par._p.find(qn("w:pPr") + "/" + qn("w:spacing"))
    if sp is not None:
        for a in ("w:beforeAutospacing", "w:afterAutospacing", "w:beforeLines", "w:afterLines"):
            if sp.get(qn(a)) is not None:
                del sp.attrib[qn(a)]


def runs_de(par):
    return [Run(r, par) for r in par._p.iter(qn("w:r")) if not en_math(r)]


def quitar_prefijo(p_el, n):
    """Quita los primeros n caracteres del texto del párrafo (w:t, w:tab, w:br) sin tocar el resto del formato."""
    fb = "{http://schemas.openxmlformats.org/markup-compatibility/2006}Fallback"
    for nodo in list(p_el.iter(qn("w:t"), qn("w:tab"), qn("w:br"))):
        if n <= 0:
            break
        a = nodo.getparent()
        while a is not None and a is not p_el and a.tag != fb:
            a = a.getparent()
        if a is not None and a.tag == fb:
            continue
        if nodo.tag == qn("w:t"):
            t = nodo.text or ""
            nodo.text = t[n:]
            if nodo.text != t:
                nodo.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
            n -= len(t)
        else:
            nodo.getparent().remove(nodo)
            n -= 1


# ---------------------------------------------------------------- correcciones
def corregir_margenes(d, secciones):
    n = 0
    for s, info in zip(d.sections, secciones):
        if any(abs(m - 1.0) > auditar.TOL for m in info["margenes"]):
            s.top_margin = s.bottom_margin = s.left_margin = s.right_margin = Inches(1)
            n += 1
    return n


def corregir_aspecto_encabezados(d, pares, pars, destino=None):
    """APA-003 (encabezados): mismo tipo y tamaño que el texto y en negro. Toca los estilos de encabezado («Heading
    N», «Título N», «Title») y los runs de los párrafos con esos estilos; el texto conserva su fuente."""
    fuentes = {}
    for p in pars:
        if not p.get("en_tabla"):  # misma fuente principal que auditar.base_apa (APA-002/003)
            for f in p.get("fuentes", ()):
                fuentes[f] = fuentes.get(f, 0) + 1
    if destino:
        fn, fz = destino  # tras corregir_fuente el texto ya es Times New Roman 12
    elif not fuentes:
        return 0
    else:
        fn, fz = max(fuentes, key=fuentes.get)
    media = str(int(round(fz * 2)))
    n = 0

    def igualar(rpr):
        cambio = False
        rf = rpr.find(qn("w:rFonts"))
        if rf is not None and (nombre_rfonts(rf) or "").lower() != fn or (rf is not None and rf.get(qn("w:asciiTheme"))):
            for a in list(rf.attrib):
                del rf.attrib[a]
            for a in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
                rf.set(qn(a), fn.title() if fn.islower() else fn)
            cambio = True
        for tag in ("w:sz", "w:szCs"):
            s_ = rpr.find(qn(tag))
            if s_ is not None and s_.get(qn("w:val")) != media:
                s_.set(qn("w:val"), media)
                cambio = True
        c = rpr.find(qn("w:color"))
        if c is not None and (c.get(qn("w:val")) or "").upper() not in ("AUTO", "000000"):
            rpr.remove(c)
            cambio = True
        return cambio

    for st in d.styles.element.findall(qn("w:style")):
        nombre = (st.find(qn("w:name")).get(qn("w:val")) if st.find(qn("w:name")) is not None else "").lower()
        if nombre.startswith(("heading", "título", "titulo", "title")) and st.find(qn("w:rPr")) is not None:
            n += igualar(st.find(qn("w:rPr")))
    for el, p in pares:
        if p.get("es_titulo"):
            for r_el in el.iter(qn("w:r")):
                rpr = r_el.find(qn("w:rPr"))
                if rpr is not None:
                    n += igualar(rpr)
    return n


def corregir_fuente(d, pares):
    """Estilos, docDefaults y runs con fuente/tamaño explícito distinto -> Times New Roman 12."""
    cont = 0
    estilos = d.styles.element
    dd = estilos.find(qn("w:docDefaults"))
    if dd is None:
        dd = OxmlElement("w:docDefaults")
        estilos.insert(0, dd)
    rpd = dd.find(qn("w:rPrDefault"))
    if rpd is None:
        rpd = OxmlElement("w:rPrDefault")
        dd.insert(0, rpd)
    rpr = rpd.find(qn("w:rPr"))
    if rpr is None:
        rpr = OxmlElement("w:rPr")
        rpd.append(rpr)
    rf = rpr.get_or_add_rFonts()
    if not es_mono(nombre_rfonts(rf)):
        poner_tnr(rf)
    sz = rpr.get_or_add_sz()
    sz.set(qn("w:val"), "24")
    cont += 1
    for st in estilos.findall(qn("w:style")):
        nombre = (st.find(qn("w:name")).get(qn("w:val")) if st.find(qn("w:name")) is not None else "").lower()
        if nombre.startswith(ESTILOS_FUENTE_OMITIDOS):
            continue
        rp = st.find(qn("w:rPr"))
        if rp is None:
            continue
        rf = rp.find(qn("w:rFonts"))
        if rf is not None and not es_mono(nombre_rfonts(rf)) and (nombre_rfonts(rf) != TNR or rf.get(qn("w:asciiTheme"))):
            poner_tnr(rf)
            cont += 1
        if nombre in ESTILOS_TAMANO:
            s_ = rp.find(qn("w:sz"))
            if s_ is not None and s_.get(qn("w:val")) != "24" and not (rf is not None and es_mono(nombre_rfonts(rf))):
                s_.set(qn("w:val"), "24")
                sc = rp.find(qn("w:szCs"))
                if sc is not None:
                    sc.set(qn("w:val"), "24")
                cont += 1
    for p_el, p in pares:
        for r in p_el.iter(qn("w:r")):
            if en_math(r):
                continue
            rp = r.find(qn("w:rPr"))
            if rp is None:
                continue
            rf = rp.find(qn("w:rFonts"))
            nm = nombre_rfonts(rf)
            if rf is not None and not es_mono(nm) and (nm != TNR or rf.get(qn("w:asciiTheme")) or rf.get(qn("w:hAnsiTheme"))):
                poner_tnr(rf)
                cont += 1
            if not p.get("en_tabla") and not (rf is not None and es_mono(nm)):
                s_ = rp.find(qn("w:sz"))
                if s_ is not None and s_.get(qn("w:val")) != "24":
                    s_.set(qn("w:val"), "24")
                    sc = rp.find(qn("w:szCs"))
                    if sc is not None:
                        sc.set(qn("w:val"), "24")
                    cont += 1
    return cont


def solo_mono(p):
    f = p.get("fuentes") or ()
    return bool(f) and all(es_mono(a) for a, _ in f)


def corregir_parrafos_formato(d, pares, que):
    """Interlineado doble (004), espaciado 0 (005) y alineación (006) en párrafos fuera de tablas."""
    n = 0
    for p_el, p in pares:
        if p.get("en_tabla") or solo_mono(p):
            continue
        par = Paragraph(p_el, d._body)
        tocado = False
        if que == "interlineado":
            ls = p["interlineado"]
            if not (isinstance(ls, (int, float)) and abs(ls - 2.0) < 0.05):
                fijar_interlineado(par)
                tocado = True
        elif que == "espaciado":
            if p.get("esp_antes", 0) > auditar.TOL_PT or p.get("esp_despues", 0) > auditar.TOL_PT:
                fijar_espaciado(par)
                tocado = True
        elif que == "alineacion":
            if "JUSTIFY" in p["alineacion"] or "DISTRIBUTE" in p["alineacion"]:
                par.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
                tocado = True
        n += tocado
    return n


def corregir_sangria(d, pares, todos, cuerpo, entradas, fin_p):
    A = auditar
    ids_ent = {id(e) for e in entradas}
    por_id = {id(p): el for el, p in pares}
    n = 0
    for p in cuerpo:
        if id(p) in ids_ent or p.get("numerado") or p.get("imagen") or A.nivel_estilo(p):
            continue
        t = p["texto"]
        con_espacios = t.startswith("     ")
        if con_espacios:
            pass
        elif abs(p["sangria1"] - 0.5) <= A.TOL or t.startswith((" ", "\t")) or p["sangria1"] < 0:
            continue
        if A.RE_ROT_NUM.match(t.strip()) or A.RE_NOTA.match(t):
            continue
        if A.sin_sangria_legitima(todos, p) and not con_espacios:
            continue
        el = por_id[id(p)]
        if con_espacios:
            m = re.match(r"[ \t]+", t)
            quitar_prefijo(el, m.end())
        par = Paragraph(el, d._body)
        limpiar_ind_chars(el)
        par.paragraph_format.first_line_indent = Inches(0.5)
        n += 1
    return n


def poner_campo_pagina(par_el):
    def run(hijo):
        r = OxmlElement("w:r")
        rp = OxmlElement("w:rPr")
        rf = OxmlElement("w:rFonts")
        poner_tnr(rf)
        rp.append(rf)
        sz = OxmlElement("w:sz")
        sz.set(qn("w:val"), "24")
        rp.append(sz)
        r.append(rp)
        r.append(hijo)
        par_el.append(r)

    fc = OxmlElement("w:fldChar")
    fc.set(qn("w:fldCharType"), "begin")
    run(fc)
    it = OxmlElement("w:instrText")
    it.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    it.text = " PAGE "
    run(it)
    fc = OxmlElement("w:fldChar")
    fc.set(qn("w:fldCharType"), "separate")
    run(fc)
    t = OxmlElement("w:t")
    t.text = "1"
    run(t)
    fc = OxmlElement("w:fldChar")
    fc.set(qn("w:fldCharType"), "end")
    run(fc)


def _poner_ptab_antes_de_pagina(p_el):
    """Inserta `<w:r><w:ptab relativeTo="margin" alignment="right" leader="none"/></w:r>` antes del primer campo PAGE."""
    ini = None
    for f in p_el.iter(qn("w:fldSimple")):
        if ooxml.tipo_campo(f.get(qn("w:instr")) or "") == "PAGE":
            ini = f
            break
    if ini is None:
        ini = next((f["ini"] for f in listar_campos(p_el) if f["tipo"] == "PAGE"), None)
    if ini is None:
        return False
    r = OxmlElement("w:r")
    pt = OxmlElement("w:ptab")
    pt.set(qn("w:relativeTo"), "margin")
    pt.set(qn("w:alignment"), "right")
    pt.set(qn("w:leader"), "none")
    r.append(pt)
    ini.addprevious(r)
    return True


def arreglar_encabezado(hdr):
    """Devuelve True si cambió. Añade párrafo con PAGE a la derecha, o alinea a la derecha el que ya lo tiene."""
    el = hdr._element
    xml = el.xml
    if ooxml.tiene_pagina(el):
        for p_el in el.iter(qn("w:p")):
            if ooxml.tiene_pagina(p_el):
                resto = "".join(t.text or "" for t in p_el.iter(qn("w:t"))).strip()
                if p_el.find(".//" + qn("w:tab")) is None and (not resto or resto.isdigit()):
                    jc = p_el.find(qn("w:pPr") + "/" + qn("w:jc"))
                    if jc is None or jc.get(qn("w:val")) not in ("right", "end"):
                        Paragraph(p_el, hdr).paragraph_format.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                        return True
                elif p_el.find(".//" + qn("w:tab")) is None and p_el.find(".//" + qn("w:ptab")) is None and resto:
                    # texto (running head) + PAGE pegados, sin tabulador ni alineación derecha: tabulador posicional
                    # derecho antes del campo, para que el número quede a la derecha y el texto a la izquierda
                    jc = p_el.find(qn("w:pPr") + "/" + qn("w:jc"))
                    if jc is None or jc.get(qn("w:val")) not in ("right", "end"):
                        return _poner_ptab_antes_de_pagina(p_el)
        return False
    destino = None
    for p_el in el.findall(qn("w:p")):
        if not "".join(t.text or "" for t in p_el.iter(qn("w:t"))).strip() and not list(p_el.iter(qn("w:fldChar"), qn("w:fldSimple"), qn("w:drawing"), qn("w:pict"))):
            destino = p_el
            break
    par = Paragraph(destino, hdr) if destino is not None else hdr.add_paragraph()
    for ch in list(par._p):
        if ch.tag != qn("w:pPr"):
            par._p.remove(ch)
    par.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    poner_campo_pagina(par._p)
    return True


# ---------------------------------------------------------------- numeración de páginas (APA-008 / EST-010 / EST-011)
RE_PALABRA_PAG = re.compile(r"(?:p[aá]gina|page|p[aá]g\.?)\s*$", re.I)
RE_PALABRA_DE = re.compile(r"\s*(?:de|of|/)\s*$", re.I)
RE_SEPARADORES = re.compile(r"^[\s\-–—·|.:/]*$")


def _solo_texto(r):
    """Run cuyo único contenido (aparte de rPr) es un w:t."""
    hijos = [c for c in r if c.tag != qn("w:rPr")]
    return len(hijos) == 1 and hijos[0].tag == qn("w:t")


def _recortar_antes(ant, regex):
    """Quita del texto del run `ant` (solo texto) lo que case con `regex` al final; True si cambió."""
    if ant is None or not _solo_texto(ant):
        return False
    t = ant.find(qn("w:t"))
    txt = t.text or ""
    nuevo = regex.sub("", txt)
    if nuevo == txt:
        return False
    t.text = nuevo
    t.set(XML_SPACE, "preserve")
    return True


def listar_campos(p_el):
    """Campos complejos del párrafo: [{"tipo": PAGE|NUMPAGES|None, "runs": [...], "ini": run con el begin}]."""
    pila, out = [], []
    for r in p_el.iter(qn("w:r")):
        for c in r:
            if c.tag == qn("w:fldChar"):
                ty = c.get(qn("w:fldCharType"))
                if ty == "begin":
                    pila.append({"runs": [r], "instr": "", "ini": r})
                elif ty == "end" and pila:
                    f = pila.pop()
                    if r not in f["runs"]:
                        f["runs"].append(r)
                    f["tipo"] = ooxml.tipo_campo(f["instr"])
                    out.append(f)
                    if pila:
                        pila[-1]["runs"] += f["runs"]
            elif c.tag == qn("w:instrText") and pila:
                pila[-1]["instr"] += c.text or ""
        if pila and r not in pila[-1]["runs"]:
            pila[-1]["runs"].append(r)
    return out


def quitar_campos_pagina(p_el, tipos):
    """Quita del párrafo los campos PAGE/NUMPAGES de `tipos` (complejos y fldSimple) y las palabras que los acompañan
    («Página» antes de PAGE, «de»/«of» antes de NUMPAGES). Devuelve {tipo: n} de campos quitados."""
    quitados = {}
    for f in list(p_el.iter(qn("w:fldSimple"))):
        t = ooxml.tipo_campo(f.get(qn("w:instr")) or "")
        if t in tipos:
            f.getparent().remove(f)
            quitados[t] = quitados.get(t, 0) + 1
    rem, inicios = {}, {}
    for f in listar_campos(p_el):
        if f["tipo"] in tipos:
            for x in f["runs"]:
                rem[x] = f["tipo"]
            inicios[f["ini"]] = f["tipo"]
            quitados[f["tipo"]] = quitados.get(f["tipo"], 0) + 1
    if not rem:
        return quitados
    orden = list(p_el.iter(qn("w:r")))
    for k, r in enumerate(orden):
        if r in inicios and k and orden[k - 1] not in rem:
            _recortar_antes(orden[k - 1], RE_PALABRA_PAG if inicios[r] == "PAGE" else RE_PALABRA_DE)
    for r in rem:
        if r.getparent() is not None:
            r.getparent().remove(r)
    for r in orden:  # runs de texto que quedaron vacíos
        if r.getparent() is not None and r not in rem and _solo_texto(r) and not (r.find(qn("w:t")).text or ""):
            r.getparent().remove(r)
    return quitados


def solo_numeracion(p_el):
    """True si el párrafo ya no tiene contenido (solo espacios, separadores, tabuladores)."""
    if any(True for _ in p_el.iter(qn("w:fldChar"), qn("w:fldSimple"), qn("w:drawing"), qn("w:pict"), qn("w:sdt"))):
        return False
    return bool(RE_SEPARADORES.match(texto_de(p_el).replace("\t", " ")))


def _vaciar_parte(parte_el, tipos):
    """Quita los campos `tipos` de los párrafos de un encabezado/pie; borra los párrafos que solo eran numeración
    (la parte conserva al menos un párrafo). Devuelve {tipo: n}."""
    total = {}
    for p_el in list(parte_el.iter(qn("w:p"))):
        if not any(ooxml.tipo_campo(i) for i in ooxml.instrucciones(p_el)):
            continue
        q = quitar_campos_pagina(p_el, tipos)
        for t, n in q.items():
            total[t] = total.get(t, 0) + n
        if q and solo_numeracion(p_el) and p_el.getparent() is parte_el:
            if len(parte_el.findall(qn("w:p"))) > 1:
                parte_el.remove(p_el)
            else:
                for ch in list(p_el):
                    if ch.tag != qn("w:pPr"):
                        p_el.remove(ch)
    return total


def _solo_numero_en_pie(parte_el):
    """Pie con PAGE: quita NUMPAGES y las palabras «Página»/«de», dejando solo el número. Devuelve n de cambios."""
    n = 0
    for p_el in parte_el.iter(qn("w:p")):
        n += quitar_campos_pagina(p_el, {"NUMPAGES"}).get("NUMPAGES", 0)
        orden = list(p_el.iter(qn("w:r")))
        for f in listar_campos(p_el):
            k = orden.index(f["ini"])
            if f["tipo"] == "PAGE" and k:
                n += _recortar_antes(orden[k - 1], RE_PALABRA_PAG)
    return n


def _partes_seccion(d, k, s):
    """[(encabezado, pie)] propios de la sección (None donde se heredan de la anterior)."""
    return [(h, f) for _, h, f in ooxml.partes_seccion(s, k, d, pares=True, sec0_propia=True)]


def _pagina_tras_texto(hdr_el):
    """Encabezado sin PAGE cuyo único párrafo con contenido es texto (running head): añade al final de ese párrafo un
    tabulador derecho y el campo PAGE, en la misma línea. True si cambió."""
    if ooxml.tiene_pagina(hdr_el):
        return False
    con = [p_el for p_el in hdr_el.findall(qn("w:p")) if texto_de(p_el).strip()]
    if len(con) != 1 or any(True for _ in con[0].iter(qn("w:fldChar"), qn("w:fldSimple"), qn("w:drawing"), qn("w:pict"))):
        return False
    r = OxmlElement("w:r")
    pt = OxmlElement("w:ptab")
    pt.set(qn("w:relativeTo"), "margin")
    pt.set(qn("w:alignment"), "right")
    pt.set(qn("w:leader"), "none")
    r.append(pt)
    con[0].append(r)
    poner_campo_pagina(con[0])
    return True


def corregir_paginacion(d, secciones, modo, portada=None, solo_portada=False):
    """modo: encabezado | pie | ninguna. Nunca deja PAGE en encabezado y pie a la vez.
    portada (si | no | None) gobierna la primera página de la sección 0: «no» no la toca (la quita corregir_portada);
    None solo la toca si ya lleva número (no pone número a una portada que no lo tiene); «si» la numera como el resto.
    solo_portada: solo esa parte. Devuelve {"APA-008": n, "EST-010": n, "EST-011": n}."""
    r = {"APA-008": 0, "EST-010": 0, "EST-011": 0}

    def acum(q):
        r["EST-010"] += q.get("PAGE", 0)
        r["EST-011"] += q.get("NUMPAGES", 0)

    for k, (s, info) in enumerate(zip(d.sections, secciones)):
        for i, (h, f) in enumerate(_partes_seccion(d, k, s)):
            es_portada = k == 0 and i == 1
            if solo_portada and not es_portada:
                continue
            if es_portada and (portada == "no" or (portada is None and not any(
                    x is not None and not x.is_linked_to_previous and ooxml.tiene_pagina(x._element) for x in (h, f)))):
                continue
            if modo == "encabezado":
                if es_portada and h is not None and not h.is_linked_to_previous and _pagina_tras_texto(h._element):
                    r["APA-008"] += 1
                if h is not None and (i > 0 or not info["num_pagina"] or not info["num_derecha"]):
                    r["APA-008"] += arreglar_encabezado(h)
                if h is not None:
                    r["EST-011"] += _vaciar_parte(h._element, {"NUMPAGES"}).get("NUMPAGES", 0)
                if f is not None:
                    acum(_vaciar_parte(f._element, {"PAGE", "NUMPAGES"}))
            elif modo == "pie":
                if h is not None:
                    acum(_vaciar_parte(h._element, {"PAGE", "NUMPAGES"}))
                if f is not None:
                    if ooxml.tiene_pagina(f._element):
                        r["EST-011"] += _solo_numero_en_pie(f._element)
                    else:
                        vacio = next((p for p in f.paragraphs if not p.text.strip() and not list(p._p.iter(qn("w:fldChar")))), None)
                        par = vacio if vacio is not None else f.add_paragraph()
                        par.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
                        poner_campo_pagina(par._p)
                        r["EST-010"] += 1
            else:
                for parte in (h, f):
                    if parte is not None:
                        acum(_vaciar_parte(parte._element, {"PAGE", "NUMPAGES"}))
    return r


def _contenido(parte_el):
    """True si la parte tiene texto o campos."""
    return bool(texto_de(parte_el).strip()) or any(True for _ in parte_el.iter(qn("w:fldChar"), qn("w:fldSimple"), qn("w:drawing")))


def _copiar_parte(origen_el, destino_el):
    for ch in list(destino_el):
        destino_el.remove(ch)
    for ch in origen_el:
        destino_el.append(copy.deepcopy(ch))


def _quitar_cola_tabs(parte_el):
    """Tras quitar PAGE: runs finales que solo son tabulador (w:tab / w:ptab) ya no llevan nada a la derecha."""
    for p_el in parte_el.iter(qn("w:p")):
        while True:
            runs = p_el.findall(qn("w:r"))
            if not runs:
                break
            hijos = [c for c in runs[-1] if c.tag != qn("w:rPr")]
            if hijos and all(c.tag in (qn("w:tab"), qn("w:ptab")) for c in hijos):
                p_el.remove(runs[-1])
            else:
                break


def _portada_propia(s):
    """Garantiza primera página distinta en la sección 0 y partes first_page_header/footer con el contenido de las
    generales cuando no tenían definición propia o estaban vacías al activarla. Devuelve (n cambios, partes de la portada)."""
    n, activada = 0, False
    if not s.different_first_page_header_footer:
        s.different_first_page_header_footer = True
        n, activada = 1, True
    partes = []
    for gen, prim in ((s.header, s.first_page_header), (s.footer, s.first_page_footer)):
        if prim.is_linked_to_previous:
            prim.is_linked_to_previous = False
            vacia = True
        else:
            vacia = activada and not _contenido(prim._element)
        if vacia and not gen.is_linked_to_previous:
            _copiar_parte(gen._element, prim._element)
            n += 1
        partes.append(prim)
    return n, partes


def corregir_portada(d, portada_numero):
    """Numeración de la portada (primera página de la sección 0). `no`: primera página distinta, first_page_header con el
    contenido del encabezado (running head) y first_page_footer con el del pie, ambos sin PAGE/NUMPAGES. `si`: si la
    portada tiene encabezado/pie propios, los completa con los generales; la numeración la pone corregir_paginacion
    (solo_portada). Devuelve el número de cambios."""
    if not d.sections:
        return 0
    s = d.sections[0]
    if portada_numero == "si" and not s.different_first_page_header_footer:
        return 0  # la portada comparte el encabezado general: lleva el mismo número
    n, partes = _portada_propia(s)
    if portada_numero == "no":
        for prim in partes:
            n += sum(_vaciar_parte(prim._element, {"PAGE", "NUMPAGES"}).values())
            _quitar_cola_tabs(prim._element)
    return n


# ---------------------------------------------------------------- maquetación (EST-012 / EST-013 / EST-014)
def _poner_keep(doc, d, el):
    if doc.keep_next(el):
        return False
    Paragraph(el, d._body).paragraph_format.keep_with_next = True
    return True


def _marca_fila(tr, nombre):
    trpr = tr.get_or_add_trPr()
    e = trpr.find(qn("w:" + nombre))
    if e is not None and e.get(qn("w:val"), "1") not in ("0", "false", "off"):
        return False
    if e is not None:
        trpr.remove(e)
    trpr.append(OxmlElement("w:" + nombre))
    return True


def corregir_maquetacion(d, reglas=("EST-012", "EST-013", "EST-014")):
    """EST-012 (mantener juntos rótulo, título, cuerpo y nota), EST-013 (fila de encabezados repetida) y EST-014 (espacio
    antes del encabezado que sigue a tabla/figura/nota). Usa los detectores de maquetacion.py. Devuelve {regla: n}."""
    doc = maquetacion.Doc(d)
    its = maquetacion.items_cuerpo(d)
    r = {"EST-012": 0, "EST-013": 0, "EST-014": 0}
    for o in (maquetacion.objetos(its) if "EST-012" in reglas else ()):
        cambio = False
        cuerpo = its[o["cuerpo"]]
        if not o.get("debajo"):
            for i in (o["rot"], o["tit"]):
                if i is not None:
                    cambio |= _poner_keep(doc, d, its[i].el)
        j = maquetacion.siguiente_no_vacio(its, o["cuerpo"])
        con_nota = j is not None and its[j].nota
        if o["tipo"] == "tabla":
            filas = cuerpo.el.findall(qn("w:tr"))
            if len(filas) <= maquetacion.FILAS_CORTA:
                for n, tr in enumerate(filas):
                    cambio |= _marca_fila(tr, "cantSplit")
                    if n < len(filas) - 1 or con_nota:
                        for p_el in tr.iter(qn("w:p")):
                            cambio |= _poner_keep(doc, d, p_el)
        elif con_nota or (o.get("debajo") and j == o["rot"]):
            cambio |= _poner_keep(doc, d, cuerpo.el)
        r["EST-012"] += cambio
    for it in (its if "EST-013" in reglas else ()):
        if it.tbl:
            filas = it.el.findall(qn("w:tr"))
            if len(filas) > maquetacion.FILAS_CORTA and not maquetacion.con_encabezado_repetido(it.el):
                r["EST-013"] += _marca_fila(filas[0], "tblHeader")
    for k, _ in (maquetacion.encabezados_pegados(doc, its) if "EST-014" in reglas else ()):
        Paragraph(its[k].el, d._body).paragraph_format.space_before = Pt(24)
        r["EST-014"] += 1
    return r


def pone_bold(par, cursiva=None):
    for r in runs_de(par):
        r.font.bold = True
        if cursiva is True:
            r.font.italic = True


def corregir_encabezados(d, heads, que_ids):
    n = 0
    for el, p, nivel in heads:
        par = Paragraph(el, d._body)
        if nivel == 1 and "APA-025" in que_ids:
            par.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
            pone_bold(par)
        elif nivel == 2 and "APA-026" in que_ids:
            par.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
            pone_bold(par)
        elif nivel == 3 and "APA-027" in que_ids:
            par.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
            pone_bold(par, True)
        else:
            continue
        if p["sangria1"] or p["sangria_izq"]:
            limpiar_ind_chars(el)
            par.paragraph_format.first_line_indent = Inches(0)
            par.paragraph_format.left_indent = Inches(0)
        n += 1
    return n


def corregir_numeracion(d, heads):
    n = 0
    for el, p, _ in heads:
        cambio = False
        if p.get("numerado"):
            ppr = el.get_or_add_pPr()
            np_ = ppr.get_or_add_numPr()
            np_.get_or_add_numId().set(qn("w:val"), "0")
            cambio = True
        m = RE_PREFIJO_NUM.match(p["texto"])
        if m and auditar.RE_NUM_ENC.match(p["texto"]):
            quitar_prefijo(el, m.end())
            cambio = True
        n += cambio
    return n


def es_ingles(cuerpo, cfg):
    t = " " + " ".join(p["texto"] for p in cuerpo).lower() + " "
    en = sum(t.count(w) for w in (" the ", " and ", " of ", " is ", " that "))
    es = sum(t.count(w) for w in (" el ", " la ", " de ", " que ", " y ", " los "))
    if en + es < 5:
        return (cfg.get("opciones") or {}).get("idioma", "es") == "en"
    return en > es


def corregir_rotulo(d, todos, titulo, ingles, ids):
    el = ELEM_DE[id(titulo)]
    par = Paragraph(el, d._body)
    n = 0
    if "APA-059" in ids:
        etiqueta = "References" if ingles else "Referencias"
        ts = [t for t in el.iter(qn("w:t"))]
        if ts:
            ts[0].text = etiqueta
            for t in ts[1:]:
                t.text = ""
        else:
            r = OxmlElement("w:r")
            t = OxmlElement("w:t")
            t.text = etiqueta
            r.append(t)
            el.append(r)
        for tb in list(el.iter(qn("w:tab"))):
            tb.getparent().remove(tb)
        if titulo.get("numerado"):
            el.get_or_add_pPr().get_or_add_numPr().get_or_add_numId().set(qn("w:val"), "0")
        n += 1
    if "APA-059" in ids or "APA-012" in ids or "APA-013" in ids:
        par.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
        pone_bold(par)
        if titulo.get("sangria1") or titulo.get("sangria_izq"):
            limpiar_ind_chars(el)
            par.paragraph_format.first_line_indent = Inches(0)
            par.paragraph_format.left_indent = Inches(0)
        if "APA-059" in ids and not auditar.nivel_estilo(titulo):
            try:
                par.style = d.styles["Heading 1"]
            except KeyError:
                pass
        k = titulo["i"]
        prev = todos[k - 1] if k else None
        if not titulo["salto_antes"] and not (prev and prev["salto_antes"] is True and
                                              (not prev["texto"].strip() or prev["texto"].endswith("\n"))):
            par.paragraph_format.page_break_before = True
    return n


def corregir_refs_formato(d, entradas):
    n = 0
    for e in entradas:
        if "fuentes" not in e or e.get("numerado"):
            continue
        if not (abs(e["sangria1"] + 0.5) < auditar.TOL and abs(e["sangria_izq"] - 0.5) < auditar.TOL):
            el = ELEM_DE[id(e)]
            limpiar_ind_chars(el)
            pf = Paragraph(el, d._body).paragraph_format
            pf.left_indent = Inches(0.5)
            pf.first_line_indent = Inches(-0.5)
            n += 1
    return n


def corregir_doi(entradas):
    """APA-076: «doi:10.xxxx/yyy» -> «https://doi.org/10.xxxx/yyy» (mismo patrón que auditar)."""
    n = 0
    for e in entradas:
        if "fuentes" not in e or re.search(r"https?://(dx\.)?doi\.org/", e["texto"]):
            continue
        el = ELEM_DE[id(e)]
        t = texto_de(el)
        ed = [(m.start(), m.end(), "https://doi.org/") for m in re.finditer(r"\bdoi:\s*(?=10\.)", t, re.I)]
        n += aplicar_ediciones(el, ed) and len(ed)
    return n


def clave_entrada(e):
    """Misma clave que usa auditar.citas_apa para comprobar el orden de la lista (APA-061)."""
    A = auditar
    m = re.match(r"\s*([^,(]+?),.*?\((\d{4}[a-z]?|n\.d\.|s\.f\.)", e["texto"]) or \
        re.match(r"\s*([^.(]+?)\.\s*\((\d{4}[a-z]?|n\.d\.|s\.f\.)", e["texto"])
    if not m:
        return None
    return re.sub(r"^(?:the|an?|el|la|los|las)\s+", "", A.sin_acentos(A.sin_sigla(m.group(1))[0]).lower())


def ordenar_refs(entradas):
    con = [(clave_entrada(e), e) for e in entradas]
    con = [(k, e) for k, e in con if k is not None]
    orden = sorted(con, key=lambda x: x[0])
    if [id(e) for _, e in orden] == [id(e) for _, e in con]:
        return 0
    marcas = []
    for _, e in con:
        el = ELEM_DE[id(e)]
        m = OxmlElement("w:bookmarkEnd")  # marcador temporal inocuo
        m.set(qn("w:id"), "0")
        el.addprevious(m)
        marcas.append(m)
    for _, e in con:
        el = ELEM_DE[id(e)]
        el.getparent().remove(el)
    for m, (_, e) in zip(marcas, orden):
        m.addprevious(ELEM_DE[id(e)])
        m.getparent().remove(m)
    return sum(1 for (_, a), (_, b) in zip(con, orden) if a is not b)


def quitar_vacios(d, todos, fin_p):
    n = 0
    for p in todos[fin_p:]:
        if not p.get("en_tabla") and auditar.es_vacio(p) and not auditar.vacio_legitimo(todos, p):
            el = ELEM_DE[id(p)]
            if el.getparent() is not None and el.find(qn("w:pPr") + "/" + qn("w:sectPr")) is None:
                el.getparent().remove(el)
                n += 1
    return n


ELEM_DE = {}

# ---------------------------------------------------------------- edición de texto entre runs
FALLBACK = ooxml.FALLBACK
XML_SPACE = ooxml.XML_SPACE
nodos_texto = ooxml.nodos_texto  # mismos nodos y orden que auditar.texto_xml


def texto_de(p_el):
    """Texto del párrafo, normalizado como lo hace auditar.auditar (misma longitud que el original salvo NFC)."""
    t = "".join((n.text or "") if n.tag == qn("w:t") else ("\t" if n.tag == qn("w:tab") else "\n")
                for n in nodos_texto(p_el))
    return t.replace(" ", " ").replace(" ", " ")


def reemplazar(p_el, a, b, s):
    """Sustituye los caracteres [a, b) del texto del párrafo por s, tocando solo los runs afectados: el texto
    nuevo queda en el primer run implicado (con su formato) y se recortan los demás."""
    pos, primero = 0, True
    for n in nodos_texto(p_el):
        es_t = n.tag == qn("w:t")
        largo = len(n.text or "") if es_t else 1
        ini, fin = pos, pos + largo
        pos = fin
        if fin <= a or (ini >= b and not (a == b and ini == a)):
            continue
        if es_t:
            t = n.text or ""
            pre = t[:max(a - ini, 0)]
            post = t[b - ini:] if b < fin else ""
            n.text = pre + (s if primero else "") + post
            n.set(XML_SPACE, "preserve")
        elif primero:
            nuevo = OxmlElement("w:t")
            nuevo.text = s
            nuevo.set(XML_SPACE, "preserve")
            n.addprevious(nuevo)
            n.getparent().remove(n)
        else:
            n.getparent().remove(n)
        primero = False
    return not primero


def aplicar_ediciones(p_el, ediciones):
    """ediciones: lista de (a, b, nuevo) sobre texto_de(p_el); se aplican de derecha a izquierda."""
    n = 0
    for a, b, s in sorted(ediciones, key=lambda e: -e[0]):
        n += reemplazar(p_el, a, b, s)
    return n


# ---------------------------------------------------------------- APA-028 / APA-029
def corregir_enc_linea(d, pares, entradas, titulo, fin_p, ids):
    """Encabezados de nivel 4/5 «en línea»: la negrita (y cursiva) ya cubre el tramo del encabezado y el texto sigue
    en el mismo párrafo; solo falta la sangría de primera línea de 0.5 in (misma detección que auditar.encabezados_apa)."""
    A = auditar
    ids_ent = {id(e) for e in entradas}
    n = 0
    for el, p in pares:
        if p["i"] < fin_p:
            continue
        tr = p.get("tramos")
        if (not tr or p.get("en_tabla") or id(p) in ids_ent or A.nivel_estilo(p) or p.get("numerado") or p is titulo):
            continue
        k, pre = 0, ""
        while k < len(tr) and (tr[k][2] or not tr[k][0].strip()):
            pre += tr[k][0]
            k += 1
        pr, resto = pre.strip(), "".join(t[0] for t in tr[k:]).strip()
        if (len(pr) < 3 or len(pr.split()) > 12 or not pr.endswith(".") or ". " in pr[:-1] or len(resto) < 15
                or re.match(r"(tabla|figura|table|figure|nota|note)\b", pr, re.I) or not A.marca(p, 2, 0, len(pre))):
            continue
        nivel = 5 if A.marca(p, 1, 0, len(pre)) else 4
        if ("APA-029" if nivel == 5 else "APA-028") not in ids:
            continue
        if max(p["sangria1"], p["sangria_izq"]) < 0.4:
            limpiar_ind_chars(el)
            pf = Paragraph(el, d._body).paragraph_format
            pf.left_indent = Inches(0)
            pf.first_line_indent = Inches(0.5)
            p["sangria1"], p["sangria_izq"] = 0.5, 0.0
            n += 1
    return n


# ---------------------------------------------------------------- APA-036 narrativa mal formada
def corregir_narrativa(pares, cuerpo, ingles=False):
    """«Vaswani et al., 2017, propusieron» -> «Vaswani et al. (2017) propusieron» (mismos filtros que auditar)."""
    A = auditar
    ids_c = {id(p) for p in cuerpo}
    n = 0
    for el, p in pares:
        if id(p) not in ids_c:
            continue
        t = texto_de(el)
        ed = []
        for m in A.RE_NARR_COMA.finditer(t):
            antes = t[:m.start()]
            if antes.count("(") > antes.count(")") and re.search(r"(?:\(|;|véase|ver|see|e\.\s?g\.,|p\.\s?ej\.,)\s*$", antes, re.I):
                continue
            if re.match(r"(?:cap[ií]tulo|secci[oó]n|section|chapter|tablas?|figuras?|p[aá]rrafo|p[aá]ginas?|apartado|ecuaci[oó]n)\b", t[m.end():]):
                continue
            autores = m.group(1)
            if " & " in autores:  # en la narrativa la conjunción va escrita (APA 8.17)
                autores = autores.replace(" & ", " and " if ingles else " y ")
                ed.append((m.start(1), m.end(), f"{autores} ({m.group(2)}) "))
            else:
                ed.append((m.end(1), m.end(), f" ({m.group(2)}) "))
        n += aplicar_ediciones(el, ed) and len(ed)
    return n


# ---------------------------------------------------------------- APA-037 conjunción entre dos autores
def corregir_conjuncion(pares, cuerpo, ingles):
    """«Levenson & Shensa (2016)» -> «Levenson y Shensa (2016)» («and» en inglés); «(Hale y Guan, 2015)» ->
    «(Hale & Guan, 2015)». Mismos patrones que auditar.citas_apa."""
    A = auditar
    ids_c = {id(p) for p in cuerpo}
    n = 0
    for el, p in pares:
        if id(p) not in ids_c:
            continue
        t = texto_de(el)
        ed = []
        for m in A.RE_NARR_DOS.finditer(t):
            antes = t[:m.start()]
            if m.group(2) == "&" and antes.count("(") <= antes.count(")"):
                ed.append((m.start(2), m.end(2), "and" if ingles else "y"))
        for m in re.finditer(r"\((?:[^()]*;\s*)?[A-ZÁÉÍÓÚÑ][\w'’-]+(\s+y\s+)[A-ZÁÉÍÓÚÑ][\w'’-]+,\s*(?:\d{4}[a-z]?|s\.\s?f\.|n\.d\.)", t):
            ed.append((m.start(1), m.end(1), " & "))
        n += aplicar_ediciones(el, ed) and len(ed)
    return n


# ---------------------------------------------------------------- APA-043 orden alfabético en paréntesis
def ordenar_segmento(seg, grupos):
    """Ordena las obras (separadas por «;») de un segmento sin «see also» con la clave de auditar.orden_alfabetico.
    Las partes que auditar ignora (siglas, autores grupales, sin autor-año) conservan su lugar."""
    A = auditar
    claves_grupo = set(grupos.values())
    partes = seg.split(";")
    info = []
    for part in partes:
        m = A.RE_PREFIJO.match(part)
        cab = m.group(0) if m else re.match(r"\s*", part).group(0)
        cuerpo_ = part[len(cab):]
        cola = cuerpo_[len(cuerpo_.rstrip()):]
        cuerpo_ = cuerpo_.rstrip()
        ma = A.RE_AUTOR_AÑO.match(cuerpo_.strip())
        clave = None
        if ma:
            a = ma.group(1)
            if not ((a.isupper() and len(a) >= 2) or a in claves_grupo):
                y = ma.group(2)
                clave = (re.sub(r"[^a-z]", "", A.sin_acentos(a).lower()), ma.group(0)[:ma.start(2)].strip(),
                         y[:4] if y[:4].isdigit() else "9999", y)
        info.append([cab, cuerpo_, cola, clave])
    idx = [i for i, x in enumerate(info) if x[3] is not None]
    orden = sorted(idx, key=lambda i: info[i][3][:3])
    cuerpos = [info[i][1] for i in orden]
    for i, cu in zip(idx, cuerpos):
        info[i][1] = cu
    return ";".join(c + b + z for c, b, z, _ in info)


def corregir_orden_cita(pares, cuerpo, grupos):
    A = auditar
    ids_c = {id(p) for p in cuerpo}
    sep = re.compile("(" + A.RE_VEASE_TAMBIEN.pattern + ")", re.I)
    n = 0
    for el, p in pares:
        if id(p) not in ids_c:
            continue
        t = texto_de(el)
        ed = []
        for m in A.RE_PAR.finditer(t):
            dentro = m.group(1)
            if ";" not in dentro or not any(A.orden_alfabetico(g, grupos) for g in A.RE_VEASE_TAMBIEN.split(dentro)):
                continue
            trozos = sep.split(dentro)
            nuevo = "".join(ordenar_segmento(x, grupos) if i % 2 == 0 else x for i, x in enumerate(trozos))
            if nuevo != dentro:
                ed.append((m.start(1), m.end(1), nuevo))
        n += aplicar_ediciones(el, ed) and len(ed)
    return n


# ---------------------------------------------------------------- APA-065 sigla en la lista
RE_SIGLA_LISTA = re.compile(r"^[^()]*?(\s*\[[A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ0-9/&.\-]{1,14}\])\.?\s*\(")


def definir_sigla_en_texto(pares, cuerpo, nombre, sigla):
    """auditar liga la sigla con la entrada de la lista por la definición en el texto («Nombre [SIGLA]» o
    «Nombre (SIGLA, año)», APA 8.21). Si el texto no la define, se escribe en la primera cita que usa la sigla."""
    A = auditar
    el_de = {id(p): el for el, p in pares}
    textos = [(el_de[id(p)], texto_de(el_de[id(p)])) for p in cuerpo]
    if re.search(re.escape(nombre) + r"\s*(?:\[|\()" + re.escape(sigla) + r"[\],]", " ".join(t for _, t in textos)):
        return False
    S = re.escape(sigla)
    narr = re.compile(rf"(?<![\w\[/\-]){S}(?=\s\((?:{A.TOK_AÑO}))")
    paren = re.compile(rf"(?:(?<=\()|(?<=; )|(?<=;)){S}(?=,\s*(?:{A.TOK_AÑO}))")
    for el, t in textos:
        c = [(m.start(), m.end() + 2, f"{nombre} ({sigla}, ") for m in narr.finditer(t)] +             [(m.start(), m.end(), f"{nombre} [{sigla}]") for m in paren.finditer(t)]
        if c:
            a, b, s = min(c)
            return reemplazar(el, a, b, s)
    return False


def corregir_sigla(pares, cuerpo, entradas):
    n = 0
    for e in entradas:
        el = ELEM_DE[id(e)]
        t = texto_de(el)
        m = RE_SIGLA_LISTA.search(t)
        if not m:
            continue
        nombre, sigla = t[:m.start(1)].strip(), m.group(1).strip()[1:-1]
        definir_sigla_en_texto(pares, cuerpo, nombre, sigla)
        if reemplazar(el, m.start(1), m.end(1), ""):
            e["texto"] = unicodedata.normalize("NFC", texto_de(el))
            n += 1
    return n


# ---------------------------------------------------------------- APA-093 tablas
def _borde(nombre, val, sz="4"):
    b = OxmlElement("w:" + nombre)
    b.set(qn("w:val"), val)
    if val != "nil":
        b.set(qn("w:sz"), sz)
        b.set(qn("w:space"), "0")
        b.set(qn("w:color"), "auto")
    return b


def _insertar_antes(padre, nuevo, sucesores):
    for ch in padre:
        if ch.tag in {qn("w:" + s) for s in sucesores}:
            ch.addprevious(nuevo)
            return
    padre.append(nuevo)


def corregir_tablas(pares):
    """Solo líneas horizontales: arriba, bajo la fila de encabezado y abajo (tblBorders y tcBorders)."""
    n = 0
    hechas = set()
    for el, p in pares:
        if not (p.get("tabla_inicio") and p["tabla_info"]["vertical"]):
            continue
        tbl = el
        while tbl is not None and not (tbl.tag == qn("w:tbl") and not any(
                a.tag == qn("w:tbl") for a in tbl.iterancestors())):
            tbl = tbl.getparent()
        if tbl is None or tbl in hechas:
            continue
        hechas.add(tbl)
        for t in list(tbl.iter(qn("w:tbl"))):  # incluye la propia tabla y las anidadas
            pr = t.find(qn("w:tblPr"))
            if pr is None:
                pr = OxmlElement("w:tblPr")
                t.insert(0, pr)
            for old in pr.findall(qn("w:tblBorders")):
                pr.remove(old)
            tb = OxmlElement("w:tblBorders")
            for nombre, val in (("top", "single"), ("left", "nil"), ("start", "nil"), ("bottom", "single"),
                                ("right", "nil"), ("end", "nil"), ("insideH", "nil"), ("insideV", "nil")):
                tb.append(_borde(nombre, val))
            _insertar_antes(pr, tb, ("shd", "tblLayout", "tblCellMar", "tblLook", "tblCaption", "tblDescription"))
            filas = list(t.iterchildren(qn("w:tr")))
            for k, tr in enumerate(filas):
                for tc in tr.iterchildren(qn("w:tc")):
                    tcpr = tc.find(qn("w:tcPr"))
                    if tcpr is not None:
                        for old in tcpr.findall(qn("w:tcBorders")):
                            tcpr.remove(old)
                    if k == 0 and len(filas) > 1:
                        if tcpr is None:
                            tcpr = OxmlElement("w:tcPr")
                            tc.insert(0, tcpr)
                        cb = OxmlElement("w:tcBorders")
                        cb.append(_borde("bottom", "single"))
                        _insertar_antes(tcpr, cb, ("shd", "noWrap", "tcMar", "textDirection", "tcFitText", "vAlign", "hideMark"))
        n += 1
    return n


# ---------------------------------------------------------------- APA-145 / APA-115 / IEEE-140
def corregir_puntuacion(pares, cuerpo, entradas):
    A = auditar
    ids = {id(p) for p in cuerpo} | {id(p) for p in entradas}
    n = 0
    for el, p in pares:
        if id(p) not in ids:
            continue
        t = texto_de(el)
        ed = []
        for m in A.RE_PUNT_DOBLE.finditer(t):
            ed.append((m.start(), m.end(), m.group(0)[0]))
        if not p.get("en_tabla"):
            for m in re.finditer(r"(?<=\S) {2,}(?=\S)", t):
                if p.get("imagen") and t[m.end():].startswith("https://orcid.org"):
                    continue
                ed.append((m.start(), m.end(), " "))
        n += aplicar_ediciones(el, ed) and len(ed)
    return n


# ---------------------------------------------------------------- principal
def conteo(r):
    c = {}
    for h in r["hallazgos"]:
        c[h["id"]] = c.get(h["id"], 0) + 1
    return c


def corregir(path, perfil, out=None, solo=None, silencioso=False, paginacion=None, portada_numero=None):
    """Corrige `path` y devuelve dict con antes, despues, aplicadas {regla: n}, no_auto, avisos.
    paginacion: encabezado | pie | ninguna. Por defecto, APA -> encabezado; base IEEE -> no se toca (IEEE no la define).
    portada_numero: si | no | None. Por defecto el `portada_numero:` de .editorial.yaml; sin él no se toca la portada
    (una portada sin número no lo recibe; una con número se trata como el resto)."""
    log = (lambda *a: None) if silencioso else print
    auditar.validar_entrada(path, (".docx",))
    cfg = auditar.cargar_perfil(perfil)
    if cfg["base"] != "apa7":
        log(f"Perfil {perfil}: base {cfg['base']} no soportado aún (solo base APA 7).")
        return None
    path = pathlib.Path(path)
    out = pathlib.Path(out) if out else path.with_name(path.stem + ".corregido.docx")
    if out.resolve() == path.resolve():
        raise SystemExit("--out no puede ser el documento original")
    if paginacion is not None and paginacion not in MODOS_PAGINACION:
        raise SystemExit(f"--paginacion debe ser uno de {', '.join(MODOS_PAGINACION)}")
    if portada_numero is not None and portada_numero not in ("si", "no"):
        raise SystemExit("--portada-numero debe ser si o no")
    avisos = []
    explicita = portada_numero is not None
    portada_numero = portada_numero or auditar.portada_numero_equipo(str(path))
    if portada_numero and not explicita and solo and "EST-016" not in solo:
        portada_numero = None
    modo = paginacion or ("encabezado" if cfg["base"] == "apa7" else None)
    if modo is None:
        avisos.append("numeración de página sin tocar: IEEE no la define; elige --paginacion encabezado|pie|ninguna")
    antes = auditar.auditar(str(path), perfil)
    antes["hallazgos"] = list(antes["hallazgos"]) + maquetacion.revisar(str(path), cfg["base"], portada_numero)
    ids = {h["id"] for h in antes["hallazgos"]}
    objetivo = {r for r in REGLAS if r in ids and (not solo or r in solo)}

    pars, secciones = auditar.cargar_docx(str(path))
    pars = [p for p in pars if not p.get("nota_pie")]
    for p in pars:
        p["texto"] = unicodedata.normalize("NFC", p["texto"]).replace(" ", " ").replace(" ", " ")
    cuerpo, titulo, entradas = auditar.partir(pars)
    d = auditar.abrir_docx(str(path))
    els = elementos(d)
    if len(els) != len(pars):
        raise SystemExit(f"no se pudo alinear párrafos ({len(els)} vs {len(pars)}); no se corrige")
    pares = list(zip(els, pars))
    ELEM_DE.clear()
    for el, p in pares:
        ELEM_DE[id(p)] = el
    fin_p = auditar.fin_portada(pars)
    ids_ent = {id(e) for e in entradas}
    heads = []
    for el, p in pares:
        if p["i"] < fin_p:
            continue
        nivel = auditar.nivel_estilo(p)
        if not nivel or not p["texto"].strip() or id(p) in ids_ent or p is titulo:
            continue
        if auditar.titulo_limpio(p["texto"]) in auditar.TITULOS_REF:
            continue
        heads.append((el, p, nivel))

    grupos = {REGLAS[r] for r in objetivo}
    aplicadas = {}

    def reg(regla_ids, n):
        for r in regla_ids:
            if r in objetivo:
                aplicadas[r] = n

    if "margenes" in grupos:
        reg(["APA-001"], corregir_margenes(d, secciones))
    if "fuente" in grupos:
        a003 = [h for h in antes["hallazgos"] if h["id"] == "APA-003"]
        solo_enc = "APA-002" not in ids and all("encabezados con otro" in h["evidencia"] for h in a003)
        if solo_enc:  # la fuente del texto es válida (p. ej. Calibri 11): solo se igualan los encabezados a ella
            reg(["APA-003"], corregir_aspecto_encabezados(d, pares, pars))
        else:
            n_f = corregir_fuente(d, pares)
            reg(["APA-002", "APA-003"], n_f + corregir_aspecto_encabezados(d, pares, pars, ("times new roman", 12.0)))
    if "interlineado" in grupos:
        reg(["APA-004"], corregir_parrafos_formato(d, pares, "interlineado"))
    if "espaciado" in grupos:
        reg(["APA-005"], corregir_parrafos_formato(d, pares, "espaciado"))
    if "alineacion" in grupos:
        reg(["APA-006"], corregir_parrafos_formato(d, pares, "alineacion"))
    if "enc_linea" in grupos:
        n_enc = corregir_enc_linea(d, pares, entradas, titulo, fin_p, objetivo)
        reg(["APA-028", "APA-029"], n_enc)
        if n_enc and "sangria" not in grupos and (not solo or "APA-007" in solo):
            # al sangrar el encabezado en línea se corta la cadena «nota de tabla» (auditar.es_nota) y los párrafos
            # sin sangría que le siguen pasan a exigir la suya (APA-007)
            grupos.add("sangria")
            objetivo.add("APA-007")
    if "sangria" in grupos:
        reg(["APA-007"], corregir_sangria(d, pares, pars, cuerpo, entradas, fin_p))
    pag_ids = {"APA-008", "EST-010", "EST-011"}
    n_portada = 0
    if portada_numero == "si":
        n_portada += corregir_portada(d, "si")
    if modo and (paginacion and (not solo or solo & pag_ids) or "pagina" in grupos or "paginacion" in grupos):
        # con --paginacion explícito se aplica siempre; por defecto solo si hay un hallazgo de numeración
        cp = corregir_paginacion(d, secciones, modo, portada_numero)
        for r_, n_ in cp.items():
            if n_ and (not solo or r_ in solo):
                aplicadas[r_] = aplicadas.get(r_, 0) + n_
        if modo != "encabezado" and "APA-008" in objetivo:
            avisos.append("APA-008 sigue señalado: con --paginacion " + modo + (" no hay número en el encabezado" if modo == "pie" else " no hay número de página") + " (APA §2.18 lo pide arriba a la derecha)")
    if portada_numero == "no":
        n_portada += corregir_portada(d, "no")
    elif portada_numero == "si":
        if modo in ("encabezado", "pie") and d.sections[0].different_first_page_header_footer:
            n_portada += sum(corregir_paginacion(d, secciones, modo, "si", solo_portada=True).values())
        elif modo == "ninguna":
            avisos.append("portada_numero: si pero --paginacion ninguna: la portada queda sin número")
    if n_portada:
        aplicadas["EST-016"] = n_portada
    if "encabezados" in grupos:
        n = corregir_encabezados(d, heads, objetivo)
        reg(["APA-025", "APA-026", "APA-027"], n)
    if "numeracion" in grupos:
        reg(["APA-030"], corregir_numeracion(d, heads))
    if "rotulo" in grupos and titulo is not None:
        reg(["APA-059", "APA-012"], corregir_rotulo(d, pars, titulo, es_ingles(cuerpo, cfg), objetivo) or 1)
    if "refs_formato" in grupos:
        reg(["APA-060"], corregir_refs_formato(d, entradas))
    if "doi" in grupos:
        reg(["APA-076"], corregir_doi(entradas))
    if "narrativa" in grupos:
        reg(["APA-036"], corregir_narrativa(pares, cuerpo, es_ingles(cuerpo, cfg)))
    if "conjuncion" in grupos:
        reg(["APA-037"], corregir_conjuncion(pares, cuerpo, es_ingles(cuerpo, cfg)))
    if "orden_cita" in grupos:
        reg(["APA-043"], corregir_orden_cita(pares, cuerpo, auditar.grupos_apa(cuerpo, entradas)))
    if "puntuacion" in grupos:
        reg(["APA-145", "APA-115", "IEEE-140"], corregir_puntuacion(pares, cuerpo, entradas))
    sigla_n = corregir_sigla(pares, cuerpo, entradas) if "sigla" in grupos else 0
    reg(["APA-065"], sigla_n)
    if "refs_orden" in grupos or (sigla_n and (not solo or "APA-061" in solo)):
        movidas = ordenar_refs(entradas)
        reg(["APA-061"], movidas)
    if "tablas" in grupos:
        reg(["APA-093"], corregir_tablas(pares))
    d.save(str(out))
    if "APA-005" in objetivo or "APA-033" in ids:
        # los párrafos vacíos solo son espaciadores una vez corregidas las sangrías: se evalúan sobre la salida
        pars2, _ = auditar.cargar_docx(str(out))
        pars2 = [p for p in pars2 if not p.get("nota_pie")]
        d2 = auditar.abrir_docx(str(out))
        els2 = elementos(d2)
        if len(els2) == len(pars2):
            ELEM_DE.clear()
            for el, p in zip(els2, pars2):
                ELEM_DE[id(p)] = el
            nv = quitar_vacios(d2, pars2, auditar.fin_portada(pars2))
            if nv:
                d2.save(str(out))
                if "APA-005" in objetivo:
                    aplicadas["APA-005"] = aplicadas.get("APA-005", 0) + nv

    maq = {r_ for r_ in ("EST-012", "EST-013", "EST-014") if r_ in objetivo}
    if objetivo & {"APA-005", "APA-033", "APA-025", "APA-026", "APA-027"} and (not solo or "EST-014" in solo):
        maq.add("EST-014")  # quitar el espacio de los encabezados (APA-033) no debe pegar uno a una tabla o figura
    if maq:
        d3 = auditar.abrir_docx(str(out))
        for r_, n_ in corregir_maquetacion(d3, maq).items():
            if n_:
                aplicadas[r_] = aplicadas.get(r_, 0) + n_
        d3.save(str(out))
    despues = auditar.auditar(str(out), perfil)
    despues["hallazgos"] = list(despues["hallazgos"]) + maquetacion.revisar(str(out), cfg["base"], portada_numero)
    ca, cd = conteo(antes), conteo(despues)
    no_auto = sorted(cd)
    log(f"Entrada: {path}\nSalida:  {out}")
    log("Reglas corregidas (párrafos/elementos tocados):")
    for r in sorted(aplicadas):
        log(f"  {r}: {aplicadas[r]}")
    if not aplicadas:
        log("  (ninguna)")
    log("Conteo de hallazgos antes -> después:")
    for r in sorted(set(ca) | set(cd)):
        log(f"  {r}: {ca.get(r, 0)} -> {cd.get(r, 0)}")
    log(f"  TOTAL: {sum(ca.values())} -> {sum(cd.values())}")
    for a_ in avisos:
        log("Aviso: " + a_)
    if no_auto:
        log("No automático (queda para revisión manual): " + ", ".join(
            f"{r}" + (f" ({NO_AUTO[r]})" if r in NO_AUTO else "") for r in no_auto))
    return {"antes": ca, "despues": cd, "aplicadas": aplicadas, "no_auto": no_auto, "salida": str(out),
            "objetivo": sorted(objetivo), "avisos": avisos,
            "pendientes": {s: sum(h["severidad"] == s for h in despues["hallazgos"]) for s in ("crítica", "mayor", "menor")}}


def main():
    ap = argparse.ArgumentParser(description="Corrige el formato mecánico de un .docx sin tocar el original.")
    ap.add_argument("documento")
    ap.add_argument("--perfil", help="id de perfil; por defecto el `perfil:` de .editorial.yaml")
    ap.add_argument("--json", metavar="RUTA", help="escribe el resultado (antes/después, reglas aplicadas) como JSON")
    ap.add_argument("--out")
    ap.add_argument("--solo", help="reglas separadas por coma, p. ej. APA-002,APA-004")
    ap.add_argument("--portada-numero", choices=("si", "no"), dest="portada_numero",
                    help="si: la portada lleva número de página como el resto (APA §2.18, el 1); no: portada sin número (primera "
                         "página distinta, conserva el running head). Por defecto: `portada_numero:` de .editorial.yaml; sin él no se toca")
    ap.add_argument("--paginacion", choices=MODOS_PAGINACION,
                    help="dónde queda el número de página: encabezado (a la derecha, APA §2.18; por defecto en APA), pie o ninguna. "
                         "Nunca deja número en encabezado y pie a la vez; en IEEE sin este flag no se toca")
    a = ap.parse_args()
    cli.utf8()
    perfil = cli.perfil_por_defecto(ap, a.perfil, a.documento)
    solo = {x.strip().upper() for x in a.solo.split(",")} if a.solo else None
    r = corregir(a.documento, perfil, a.out, solo, paginacion=a.paginacion, portada_numero=a.portada_numero)
    if r is None:
        sys.exit(cli.ERROR)
    cli.escribir_json(a.json, r)
    sys.exit(cli.HALLAZGOS if r["pendientes"]["crítica"] or r["pendientes"]["mayor"] else cli.OK)


if __name__ == "__main__":
    main()
