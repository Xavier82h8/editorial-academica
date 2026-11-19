#!/usr/bin/env python3
"""Reglas deterministas de maquetación para .docx: numeración de página, tablas y figuras que no deben partirse,
espacio tras tabla/figura y forma de la nota. Lo usa estructura.py (sección «MAQUETACIÓN»).

Uso: python -I maquetacion.py <doc.docx> [--perfil apa7|ieee|...] [--json salida.json]
`--perfil` por defecto: el de `.editorial.yaml`, o apa7. Salida: 0 sin hallazgos o solo menores; 1 con hallazgos
mayores o críticos; 2 error de uso o de entrada (ver cli.py).

Reglas:
  EST-010 mayor  campo PAGE en el encabezado y también en el pie de la misma sección
  EST-011 menor  «Página X de Y» / NUMPAGES en encabezado o pie
  EST-012 menor  tabla o figura que puede partirse (rótulo/título sin keep_with_next, imagen separada de su rótulo
                 o nota, tabla corta con filas sin cantSplit)
  EST-013 menor  tabla de más de 20 filas sin fila de encabezados repetida (tblHeader)
  EST-014 menor  encabezado pegado al final de una tabla, imagen o nota (sin espacio antes ni línea en blanco)
  EST-016 menor  numeración de la portada contraria a la preferencia (`portada_numero: si|no` de .editorial.yaml;
                 si no, la del perfil: APA §2.18 pide número —el 1— en la portada; IEEE no define)
  EST-015 menor  nota con «Fuente:», remisión a una sección, «Elaboración propia a partir de las fuentes citadas» sin citar,
                 o «Tomado/Adaptado de» sin título entre comillas
"""
import argparse
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import auditar  # noqa: E402
import cli  # noqa: E402
import congruencia  # noqa: E402
import ooxml  # noqa: E402
from docx.oxml.ns import qn  # noqa: E402

FILAS_CORTA = 20
W_T, W_P, W_TBL, W_TR = qn("w:t"), qn("w:p"), qn("w:tbl"), qn("w:tr")
RE_NOTA = auditar.RE_NOTA
RE_FUENTE = re.compile(r"^\s*[*_]*\s*(fuentes?|source[s]?)\s*[*_]*\s*:", re.I)
RE_INICIO_NOTA = re.compile(r"^\s*[*_]*\s*(tomado\s+de|adaptado\s+de|elaboraci[oó]n\s+propia|adapted\s+from)\b", re.I)
RE_REMITE = re.compile(r"(?:(?:citad|indicad|mencionad|descrit|expuest)\w+\s+en\s+(?:la|esta|el)\s+(?:secci[oó]n|apartado|cap[ií]tulo)"
                       r"|\bver\s+(?:la\s+)?(?:secci[oó]n|apartado)|\bv[eé]ase\s+(?:la\s+)?(?:secci[oó]n|apartado)"
                       r"|\bsee\s+section)", re.I)
RE_ADAPTADO = re.compile(r"\b(tomado\s+de|adaptado\s+de|adapted\s+from|reprinted\s+from|reproducido\s+de)\b", re.I)
RE_VAGA = re.compile(r"elaboraci[oó]n\s+propia\s+(?:a\s+partir\s+de|con\s+base\s+en|basad[ao]\s+en)\s+(?:todas\s+)?(?:las|los|la|el)?\s*"
                     r"(?:fuentes?|referencias?|obras?|autores?|estudios?|trabajos?|textos?)\s+(?:indicad|citad|consultad|mencionad|referenciad|revisad|listad)\w+", re.I)
RE_CITA_NUM = re.compile(r"\[\s*\d+(?:\s*[,\-–]\s*\d+)*\s*\]")
RE_COMILLAS = re.compile(r"[\"“”«»]")
RE_AUT_ANIO = re.compile(r"([A-ZÁÉÍÓÚÑ][\wáéíóúñü'’-]+(?:\s+et\s+al\.)?(?:\s+(?:y|and|&)\s+[A-ZÁÉÍÓÚÑ][\wáéíóúñü'’-]+)?)"
                         r"(?:\s*\(\s*((?:19|20)\d{2})[a-z]?\s*\)|,\s*((?:19|20)\d{2})[a-z]?\b)")


def _H(*a):
    return auditar.Hallazgo(*a)


def _recorta(t, n=40):
    t = re.sub(r"\s+", " ", t or "").strip()
    return t if len(t) <= n else t[:n - 1] + "…"


# ---------------------------------------------------------------- lectura de propiedades (pPr directa + cadena de estilos)
class Doc:
    def __init__(self, d):
        self.d = d
        self.estilos = {s.get(qn("w:styleId")): s for s in d.styles.element.findall(qn("w:style"))}
        self.defecto = next((s for s in self.estilos.values() if s.get(qn("w:type")) == "paragraph"
                             and s.get(qn("w:default")) in ("1", "true")), None)

    def cadena(self, p_el):
        """pPr directa y las de los estilos (del párrafo hacia su base)."""
        out = []
        ppr = p_el.find(qn("w:pPr"))
        if ppr is not None:
            out.append(ppr)
        ps = ppr.find(qn("w:pStyle")) if ppr is not None else None
        st = self.estilos.get(ps.get(qn("w:val"))) if ps is not None else self.defecto
        vistos = set()
        while st is not None and id(st) not in vistos:
            vistos.add(id(st))
            sp = st.find(qn("w:pPr"))
            if sp is not None:
                out.append(sp)
            b = st.find(qn("w:basedOn"))
            st = self.estilos.get(b.get(qn("w:val"))) if b is not None else None
        return out

    def prop(self, p_el, getter):
        for ppr in self.cadena(p_el):
            v = getter(ppr)
            if v is not None:
                return v
        return None

    def keep_next(self, p_el):
        def g(ppr):
            e = ppr.find(qn("w:keepNext"))
            return None if e is None else e.get(qn("w:val"), "1") not in ("0", "false", "off")
        return bool(self.prop(p_el, g))

    def space_before(self, p_el):
        def g(ppr):
            sp = ppr.find(qn("w:spacing"))
            if sp is None:
                return None
            if sp.get(qn("w:beforeAutospacing")) in ("1", "true", "on"):
                return 14.0
            b, bl = sp.get(qn("w:before")), sp.get(qn("w:beforeLines"))
            if b is not None:
                return int(b) / 20
            return int(bl) / 100 * 12 if bl is not None else None
        return self.prop(p_el, g) or 0.0

    def salto_antes(self, p_el):
        def g(ppr):
            e = ppr.find(qn("w:pageBreakBefore"))
            return None if e is None else e.get(qn("w:val"), "1") not in ("0", "false", "off")
        return bool(self.prop(p_el, g))

    def nombre_estilo(self, p_el):
        ppr = p_el.find(qn("w:pPr"))
        ps = ppr.find(qn("w:pStyle")) if ppr is not None else None
        st = self.estilos.get(ps.get(qn("w:val"))) if ps is not None else self.defecto
        n = st.find(qn("w:name")) if st is not None else None
        return n.get(qn("w:val")) if n is not None else ""


texto_p = ooxml.texto_visible  # texto visible, sin el resultado en caché de los campos


def tiene_imagen(p_el):
    return any(True for _ in p_el.iter(qn("w:drawing"), qn("w:pict")))


def italicas(p_el):
    for r in p_el.iter(qn("w:r")):
        i = r.find(qn("w:rPr") + "/" + qn("w:i"))
        if i is not None and i.get(qn("w:val"), "1") not in ("0", "false", "off") and "".join(t.text or "" for t in r.iter(W_T)).strip():
            return True
    return False


# ---------------------------------------------------------------- campos de página en encabezado/pie
def campos(parte_el):
    """[(texto del párrafo con X/Y por PAGE/NUMPAGES, tiene PAGE, tiene NUMPAGES o «Página X de Y»)] de cada párrafo."""
    res = []
    for p_el in parte_el.iter(W_P):
        pag, tot = ooxml.tiene_pagina(p_el), ooxml.tiene_total(p_el)
        txt, en_res = [], False
        for n in p_el.iter(W_T, qn("w:fldChar"), qn("w:instrText"), qn("w:fldSimple")):
            if n.tag == qn("w:fldChar"):
                t = n.get(qn("w:fldCharType"))
                if t == "separate":
                    en_res = True
                elif t == "end":
                    en_res = False
            elif n.tag in (qn("w:instrText"), qn("w:fldSimple")):
                i = (n.text if n.tag == qn("w:instrText") else n.get(qn("w:instr"))) or ""
                txt.append({"NUMPAGES": "Y", "PAGE": "X"}.get(ooxml.tipo_campo(i), ""))
            elif not en_res and not any(a.tag == qn("w:fldSimple") for a in n.iterancestors()):
                txt.append(n.text or "")
        t = re.sub(r"\s+", " ", "".join(txt)).strip()
        res.append((t, pag, tot or bool(re.search(r"\b(p[aá]gina|page)\s*X\s*(de|of)\s*Y", t, re.I))))
    return res


def partes(sec):
    """[(nombre, encabezado, pie)] de una sección, sin las partes heredadas (linked_to_previous)."""
    return [(nom, None if h is None else h._element, None if f is None else f._element)
            for nom, h, f in ooxml.partes_seccion(sec)]


def paginacion(d, perfil):
    H, vistos = [], set()
    ieee = perfil.lower().startswith("ieee")
    for k, sec in enumerate(d.sections, 1):
        for nom, h, f in partes(sec):
            ch = campos(h) if h is not None else []
            cf = campos(f) if f is not None else []
            ph, pf = [c for c in ch if c[1]], [c for c in cf if c[1]]
            if ph and pf and ("dup", k) not in vistos:
                vistos.add(("dup", k))
                th, tf = " ".join(c[0] for c in ch if c[0]), " ".join(c[0] for c in cf if c[0])
                ev = f"encabezado: '{_recorta(th, 38)}' + PAGE; pie: '{_recorta(tf, 38)}' + PAGE"
                corr = ("IEEE no define la numeración de páginas (regla no definida); conservar una sola — preguntar al usuario"
                        if ieee else
                        "conservar solo el número del encabezado, a la derecha (APA §2.18); quitar el del pie — /corregir --paginacion encabezado")
                H.append(_H("EST-010", "mayor", f"{nom}sección {k}: encabezado y pie", ev, corr))
            for lugar, cs in (("encabezado", ch), ("pie", cf)):
                for t, _, tot in cs:
                    if tot and (lugar, t) not in vistos:
                        vistos.add((lugar, t))
                        corr = ("aviso: «Página X de Y» no está definido por IEEE; en IEEE la numeración de páginas es regla no definida"
                                if ieee else
                                'solo el número de página, sin "Página" ni total (APA §2.18)')
                        H.append(_H("EST-011", "menor", f"{nom}{lugar} de la sección {k}", f"'{_recorta(t, 60)}' (NUMPAGES/total de páginas)", corr))
    return H


def portada(d, path, perfil, preferencia=None):
    """(hallazgos EST-016, info). info = {portada_numero: encabezado|pie|ninguno, preferencia: si|no|None (declarada en
    .editorial.yaml), perfil_pide: si|None}. EST-016 solo si el estado contradice la preferencia declarada o, sin ella,
    la del perfil (APA: sí). Sin preferencia declarada, perfil APA y portada con número: sin hallazgo; el comando pregunta."""
    estado, _ = auditar.estado_portada(d)
    pref = preferencia or auditar.portada_numero_equipo(path)
    ieee = (perfil or "apa7").lower().startswith("ieee")
    perfil_pide = None if ieee else "si"
    efectiva = pref or perfil_pide
    info = {"portada_numero": estado, "preferencia": pref, "perfil_pide": perfil_pide}
    H = []
    if efectiva == "si" and estado == "ninguno":
        origen = "`portada_numero: si` de .editorial.yaml" if pref else "APA §2.18"
        H.append(_H("EST-016", "menor", "portada", "la portada no lleva número de página",
                    f"{origen} pide el número 1 en la portada; /editorial-academica:corregir --portada-numero si. "
                    "Si tu institución lo prohíbe, declara `portada_numero: no` en .editorial.yaml"))
    elif efectiva == "no" and estado != "ninguno":
        H.append(_H("EST-016", "menor", "portada", f"la portada lleva número de página (en el {estado})",
                    "`portada_numero: no` de .editorial.yaml: portada sin número; /editorial-academica:corregir --portada-numero no"))
    return H, info


def linea_portada(info):
    """Texto de una línea sobre la portada para la salida de los comandos."""
    est, pref = info["portada_numero"], info["preferencia"]
    if est == "ninguno":
        base = "Portada: sin número de página"
        if pref == "no":
            return base + " (declarado `portada_numero: no`)"
        if not info["perfil_pide"]:
            return base + " — IEEE no define la numeración de la portada"
        return base + " — APA §2.18 pide el 1 en la portada; si tu institución la pide sin número declara portada_numero: no en .editorial.yaml o usa /corregir --portada-numero no"
    base = f"Portada: lleva número en el {est}"
    if pref:
        return base + f" (declarado `portada_numero: {pref}`)"
    if info["perfil_pide"]:
        return base + " — APA §2.18 lo pide; si tu institución lo prohíbe declara `portada_numero: no` en .editorial.yaml o usa /corregir --portada-numero no"
    return base + " — IEEE no define la numeración de la portada"


# ---------------------------------------------------------------- cuerpo: tablas, figuras, notas
class Item:
    __slots__ = ("el", "tbl", "texto", "imagen", "rot")

    def __init__(self, el):
        self.el = el
        self.tbl = el.tag == W_TBL
        self.texto = "" if self.tbl else texto_p(el).strip()
        self.imagen = (not self.tbl) and tiene_imagen(el)
        self.rot = None
        if not self.tbl and self.texto:
            self.rot = congruencia.es_rotulo({"texto": self.texto, "estilo": ""})

    @property
    def vacio(self):
        return not self.tbl and not self.texto and not self.imagen

    @property
    def nota(self):
        return (not self.tbl) and bool(RE_NOTA.match(self.texto) or RE_FUENTE.match(self.texto) or RE_INICIO_NOTA.match(self.texto))


def items_cuerpo(d):
    return [Item(e) for e in d.element.body if e.tag in (W_P, W_TBL)]


def celdas(tbl):
    return [[re.sub(r"\s+", " ", " ".join(texto_p(p) for p in c.iter(W_P))).strip() for c in tr.findall(qn("w:tc"))]
            for tr in tbl.findall(W_TR)]


def sin_cantsplit(tbl):
    n = 0
    for tr in tbl.findall(W_TR):
        e = tr.find(qn("w:trPr") + "/" + qn("w:cantSplit"))
        if e is None or e.get(qn("w:val"), "1") in ("0", "false", "off"):
            n += 1
    return n


def con_encabezado_repetido(tbl):
    tr = tbl.find(W_TR)
    e = tr.find(qn("w:trPr") + "/" + qn("w:tblHeader")) if tr is not None else None
    return e is not None and e.get(qn("w:val"), "1") not in ("0", "false", "off")


def objetos(its):
    """Tablas y figuras con su rótulo: [{tipo, rot (índice o None), tit (índice o None), cuerpo (índice)}]."""
    out = []
    for r, it in enumerate(its):
        if it.rot is None or it.tbl:
            continue
        sig = its[r + 1] if r + 1 < len(its) else None
        sig2 = its[r + 2] if r + 2 < len(its) else None
        if sig is not None and (sig.tbl or sig.imagen) and it.rot[0] in ("tabla", "figura"):
            out.append({"tipo": "tabla" if sig.tbl else "figura", "rot": r, "tit": None, "cuerpo": r + 1})
        elif (sig is not None and sig2 is not None and (sig2.tbl or sig2.imagen) and sig.texto and sig.rot is None
              and not sig.nota and not sig.imagen):
            out.append({"tipo": "tabla" if sig2.tbl else "figura", "rot": r, "tit": r + 1, "cuerpo": r + 2})
    usados = {o["cuerpo"] for o in out}
    for c, it in enumerate(its):  # figura con el rótulo debajo (IEEE: «Fig. 1. …»)
        if it.imagen and c not in usados and c + 1 < len(its) and its[c + 1].rot is not None and not its[c + 1].tbl:
            out.append({"tipo": "figura", "rot": c + 1, "tit": None, "cuerpo": c, "debajo": True})
    return out


def siguiente_no_vacio(its, i):
    j = i + 1
    while j < len(its) and its[j].vacio:
        j += 1
    return j if j < len(its) else None


def partible(doc, its, o):
    """Causas por las que el objeto puede partirse (lista de textos)."""
    causas = []
    cuerpo = its[o["cuerpo"]]
    if o["tipo"] == "tabla":
        sin = [i for i in (o["rot"], o["tit"]) if i is not None and not doc.keep_next(its[i].el)]
        if sin:
            causas.append("rótulo y título sin keep_with_next" if len(sin) == 2 else
                          ("rótulo" if sin[0] == o["rot"] else "título") + " sin keep_with_next")
        n = len(cuerpo.el.findall(W_TR))
        if n <= FILAS_CORTA:
            f = sin_cantsplit(cuerpo.el)
            if f:
                causas.append(f"{f} de {n} filas sin cantSplit")
    else:
        if not o.get("debajo"):
            sin = [i for i in (o["rot"], o["tit"]) if i is not None and not doc.keep_next(its[i].el)]
            if sin:
                causas.append("rótulo/título sin keep_with_next")
        j = siguiente_no_vacio(its, o["cuerpo"])
        sigue = j is not None and (its[j].nota or (o.get("debajo") and j == o["rot"]) or (its[j].rot is not None and not its[j].tbl))
        if sigue and not doc.keep_next(cuerpo.el):
            causas.append("imagen sin keep_with_next hacia su " + ("rótulo" if o.get("debajo") else "nota"))
    return causas


def nombre_obj(its, o):
    return _recorta(its[o["rot"]].texto, 40)


def regla_012_013(doc, its, ieee):
    H = []
    for o in objetos(its):
        causas = partible(doc, its, o)
        if causas:
            H.append(_H("EST-012", "menor", nombre_obj(its, o), f"{o['tipo']} puede partirse: " + "; ".join(causas),
                        "mantener juntos rótulo, título, cuerpo y nota: keep_with_next en rótulo/título (y en la imagen), "
                        "cantSplit en las filas (/corregir)"))
    for k, it in enumerate(its):
        if not it.tbl:
            continue
        n = len(it.el.findall(W_TR))
        if n > FILAS_CORTA and not con_encabezado_repetido(it.el):
            o = next((x for x in objetos(its) if x["cuerpo"] == k), None)
            ubic = nombre_obj(its, o) if o else f"tabla de {n} filas (cuerpo, posición {k})"
            corr = "repetir la fila de encabezados en cada página (APA tablas-figuras): marcar la primera fila como fila de encabezado"
            if ieee:
                corr += '; figura de varias páginas: "(Continued.)"'
            H.append(_H("EST-013", "menor", ubic, f"tabla de {n} filas sin w:tblHeader en la primera fila", corr))
    return H


def es_encabezado(doc, it):
    return bool(it.texto) and not it.tbl and bool(auditar.nivel_estilo({"estilo": doc.nombre_estilo(it.el)}))


def encabezados_pegados(doc, its):
    """[(índice, 'tabla'|'figura'|'nota')] de los encabezados pegados al final de una tabla, imagen o nota."""
    out = []
    for k in range(1, len(its)):
        it, prev = its[k], its[k - 1]
        if not es_encabezado(doc, it):
            continue
        if not (prev.tbl or prev.imagen or prev.nota):
            continue
        if doc.space_before(it.el) > 0 or doc.salto_antes(it.el):
            continue
        # el encabezado de salida no puede tener tampoco un salto de página antes (párrafo anterior con salto final)
        if prev.el.tag == W_P and any(br.get(qn("w:type")) == "page" for br in prev.el.iter(qn("w:br"))):
            continue
        out.append((k, "tabla" if prev.tbl else "figura" if prev.imagen else "nota"))
    return out


def regla_014(doc, its):
    return [_H("EST-014", "menor", _recorta(its[k].texto, 50), f"encabezado pegado al final de una {que} (sin espacio antes ni línea en blanco)",
               "una línea en blanco a doble espacio antes del encabezado (APA tablas-figuras, opción 1)")
            for k, que in encabezados_pegados(doc, its)]


def autores_anio(tbl_el):
    """['Vaswani et al. (2017)', …] de las celdas de la tabla: columnas Año/Autores o citas autor-fecha."""
    filas = celdas(tbl_el)
    if not filas:
        return []
    cab = [c.lower() for c in filas[0]]
    ia = next((i for i, c in enumerate(cab) if re.match(r"(a[nñ]o|year|fecha)\b", c)), None)
    iu = next((i for i, c in enumerate(cab) if re.match(r"(autor|autores|author|authors)\b", c)), None)
    out = []
    if ia is not None and iu is not None:
        for f in filas[1:]:
            if len(f) > max(ia, iu):
                m = re.search(r"(?:19|20)\d{2}", f[ia])
                au = f[iu].strip().rstrip(",;") if f[iu].strip() else ""
                if m and au:
                    out.append(f"{_recorta(au, 60)} ({m.group(0)})")
    if not out:
        for f in filas:
            for c in f:
                for m in RE_AUT_ANIO.finditer(c):
                    out.append(f"{m.group(1)} ({m.group(2) or m.group(3)})")
    vistos = []
    for x in out:
        if x not in vistos:
            vistos.append(x)
    return vistos


def plantilla_nota(tbl_el):
    aa = autores_anio(tbl_el) if tbl_el is not None else []
    if aa:
        lista = ", ".join(aa[:6]) + (" y otros listados en la tabla" if len(aa) > 6 else "")
        return f"*Nota.* Elaboración propia con datos de {lista}."
    return ('*Nota.* Adaptado de "Título", por A. Autor, año, *Revista*, *vol*(n), p. (https://doi.org/…). '
            "Derechos de autor año de Titular.")


def regla_015(doc, its, ieee):
    H = []
    for k, it in enumerate(its):
        if not (it.tbl or it.imagen):
            continue
        j = siguiente_no_vacio(its, k)
        n = 0
        while j is not None and n < 4 and not its[j].tbl and not its[j].imagen and its[j].nota:
            nt = its[j]
            motivo = None
            if RE_FUENTE.match(nt.texto):
                motivo = "la nota empieza con «Fuente:»/«Source:» (APA usa «Nota.»)"
            elif RE_REMITE.search(nt.texto):
                motivo = "la nota remite a una sección en vez de citar las obras"
            elif RE_VAGA.search(nt.texto) and not RE_AUT_ANIO.search(nt.texto) and not RE_CITA_NUM.search(nt.texto):
                motivo = "la nota dice «elaboración propia a partir de las fuentes…» sin citar ninguna obra"
            elif RE_ADAPTADO.search(nt.texto) and not RE_COMILLAS.search(nt.texto) and not italicas(nt.el):
                motivo = "«Tomado/Adaptado de» sin el título entre comillas ni el formato APA"
            if motivo:
                o = next((x for x in objetos(its) if x["cuerpo"] == k), None)
                ubic = nombre_obj(its, o) if o else _recorta(nt.texto, 40)
                corr = plantilla_nota(it.el if it.tbl else None)
                if ieee:
                    corr = "IEEE no define notas de tabla/figura con «Nota.»; plantilla APA de referencia: " + corr
                H.append(_H("EST-015", "menor", ubic, f"{motivo}: «{_recorta(nt.texto, 70)}»", corr))
                break
            j, n = siguiente_no_vacio(its, j), n + 1
    return H


# ---------------------------------------------------------------- API
def revisar_info(path, perfil="apa7", portada_numero=None):
    """(hallazgos, info de portada) de un .docx. portada_numero (si|no) sustituye al de .editorial.yaml."""
    if perfil:
        auditar.cargar_perfil(perfil)
    d = auditar.abrir_docx(str(path))
    doc = Doc(d)
    its = items_cuerpo(d)
    ieee = (perfil or "apa7").lower().startswith("ieee")
    H = paginacion(d, perfil or "apa7")
    H += regla_012_013(doc, its, ieee)
    H += regla_014(doc, its)
    H += regla_015(doc, its, ieee)
    Hp, info = portada(d, path, perfil, portada_numero)
    return H + Hp, info


def revisar(path, perfil="apa7", portada_numero=None):
    """Hallazgos de maquetación (EST-010..016) de un .docx. `perfil`: id de perfil; base IEEE si empieza por «ieee»."""
    return revisar_info(path, perfil, portada_numero)[0]


def main():
    ap = argparse.ArgumentParser(description="Maquetación de un .docx: paginación, portada, tablas y figuras.")
    ap.add_argument("doc")
    ap.add_argument("--perfil", help="id de perfil; por defecto el de .editorial.yaml, o apa7")
    ap.add_argument("--json", metavar="RUTA", help="escribe hallazgos e info de portada como JSON")
    a = ap.parse_args()
    cli.utf8()
    perfil = cli.perfil_por_defecto(ap, a.perfil, a.doc, defecto="apa7")
    H, info = revisar_info(a.doc, perfil)
    cli.escribir_json(a.json, {"documento": a.doc, "perfil": perfil, "portada": info, "hallazgos": H})
    print(linea_portada(info))
    for i, h in enumerate(H, 1):
        print(f"| {i} | {h['id']} | {h['severidad']} | {h['ubicacion']} | {h['evidencia']} | {h['correccion']} |")
    sys.exit(cli.codigo(H))


if __name__ == "__main__":
    main()
