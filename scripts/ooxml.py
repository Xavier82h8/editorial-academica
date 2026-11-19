#!/usr/bin/env python3
"""Helpers OOXML compartidos por auditar, corregir y maquetacion (una sola copia).

- Campos de página: `tipo_campo`, `instrucciones`, `tiene_pagina`, `tiene_total`. PAGE se detecta con `\\bPAGE\\b`
  (NUMPAGES y SECTIONPAGES no cuentan como número de página).
- Texto de un párrafo XML: `texto_xml` (todo w:t/w:tab/w:br, también dentro de w:sdt y campos; es lo que ve el juez y
  sobre lo que edita el corrector) y `texto_visible` (sin el resultado en caché de los campos y con el tabulador como
  espacio: lo que lee una persona; lo usa maquetacion). Son variantes distintas a propósito: no se pueden unificar sin
  cambiar los offsets de las ediciones de corregir ni el texto de los rótulos de maquetacion.
- Partes de encabezado y pie por sección: `partes_seccion` (header, primera página y, si se pide, páginas pares),
  respetando `is_linked_to_previous`.
"""
import re

from docx.oxml.ns import qn

W_T, W_TAB, W_BR, W_P = qn("w:t"), qn("w:tab"), qn("w:br"), qn("w:p")
FALLBACK = "{http://schemas.openxmlformats.org/markup-compatibility/2006}Fallback"
XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"
RE_PAGE = re.compile(r"\bPAGE\b")
RE_TOTAL = re.compile(r"\b(?:NUMPAGES|SECTIONPAGES)\b")


# ---------------------------------------------------------------- texto
def nodos_texto(p_el):
    """Nodos w:t / w:tab / w:br del párrafo en orden de documento, sin los de mc:Fallback (duplican a su mc:Choice)."""
    out = []
    for n in p_el.iter(W_T, W_TAB, W_BR):
        a = n.getparent()
        while a is not None and a is not p_el and a.tag != FALLBACK:
            a = a.getparent()
        if a is not None and a.tag == FALLBACK:
            continue
        out.append(n)
    return out


def texto_xml(p_el):
    """Como p.text, pero incluye runs dentro de controles de contenido en línea (w:sdt) y campos."""
    return "".join((n.text or "") if n.tag == W_T else ("\t" if n.tag == W_TAB else "\n") for n in nodos_texto(p_el))


def texto_visible(p_el):
    """Texto visible del párrafo, sin el resultado en caché de los campos; el tabulador cuenta como un espacio."""
    out, en_resultado = [], False
    for n in p_el.iter(W_T, qn("w:fldChar"), W_TAB):
        if n.tag == qn("w:fldChar"):
            t = n.get(qn("w:fldCharType"))
            en_resultado = t == "separate" if t in ("separate", "end", "begin") else en_resultado
        elif n.tag == W_T and not en_resultado and not any(a.tag == qn("w:fldSimple") for a in n.iterancestors()):
            out.append(n.text or "")
        elif n.tag == W_TAB:
            out.append(" ")
    return "".join(out)


# ---------------------------------------------------------------- campos de página
def tipo_campo(instr):
    """«NUMPAGES» (también SECTIONPAGES), «PAGE» o None según la instrucción de un campo."""
    if RE_TOTAL.search(instr or ""):
        return "NUMPAGES"
    if RE_PAGE.search(instr or ""):
        return "PAGE"
    return None


def instrucciones(el):
    """Instrucciones de los campos del elemento: w:instrText (complejos) y w:instr de w:fldSimple."""
    return [x.text or "" for x in el.iter(qn("w:instrText"))] + [f.get(qn("w:instr")) or "" for f in el.iter(qn("w:fldSimple"))]


def tiene_pagina(el):
    """True si el elemento (párrafo o parte de encabezado/pie) lleva un campo PAGE."""
    return any(RE_PAGE.search(i) for i in instrucciones(el))


def tiene_total(el):
    """True si el elemento lleva NUMPAGES o SECTIONPAGES."""
    return any(RE_TOTAL.search(i) for i in instrucciones(el))


# ---------------------------------------------------------------- encabezados y pies
def partes_seccion(s, k=0, d=None, pares=False, sec0_propia=False):
    """[(nombre, encabezado, pie)] de la sección `s` (objetos python-docx; None donde se hereda de la anterior).

    Orden: predeterminada, primera página (si `different_first_page_header_footer`) y, con `pares=True`
    (necesita `d`) páginas pares si el documento las distingue. `sec0_propia=True` entrega siempre las partes de la
    sección 0 (k == 0) aunque no tengan definición propia (corregir las trata como suyas); con False, un
    encabezado/pie `linked_to_previous` es None en cualquier sección (maquetacion)."""
    def tomar(h, f):
        return tuple(None if (x.is_linked_to_previous and not (sec0_propia and k == 0)) else x for x in (h, f))
    out = [("", *tomar(s.header, s.footer))]
    if s.different_first_page_header_footer:
        out.append(("primera página, ", *tomar(s.first_page_header, s.first_page_footer)))
    if pares and d is not None and d.settings.odd_and_even_pages_header_footer:
        out.append(("páginas pares, ", *tomar(s.even_page_header, s.even_page_footer)))
    return out
