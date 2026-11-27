#!/usr/bin/env python3
"""Ficha técnica de medidas: el VALOR EFECTIVO de márgenes, sangría, interlineado, fuente… de un .docx (y, si se da, de su PDF).

Uso:
  python scripts/editorial.py medir <doc.docx> [--pdf doc.pdf | --render] [--json out.json] [--seccion N]
                              [--regla "márgenes 3 cm izquierda"]… [--medidas] [--contra perfil|RUTA.yaml]
  python scripts/editorial.py medir <doc.pdf>            (solo la medición del PDF)

Qué mide (cada longitud en cm, pt e in; ver scripts/unidades.py para equivalencias y tolerancias):
  .docx  Resuelve la herencia como Word: docDefaults -> estilo (y sus basedOn) -> numeración -> párrafo directo -> run.
         Por SECCIÓN: tamaño de página, márgenes (superior, inferior, izquierdo, derecho, encabezado, pie, canal), w:pgNumType
         (formato y inicio), primera página distinta, y DÓNDE va el número de página (encabezado/pie, lado).
         Por GRUPO de párrafos (portada, títulos 1-5, resumen, cuerpo, referencias, tabla, otros) y por ESTILO: fuente, tamaño,
         interlineado como lo ve Word (auto ×1.5 frente a exacto 18 pt), espacio antes y después, sangría izquierda, derecha,
         de primera línea y francesa, alineación, color, negrita y cursiva. Cuenta cuántos párrafos tienen cada valor y lista las
         excepciones (n.º de párrafo y primeras palabras).
  PDF    (PyMuPDF) caja de texto por página sin encabezado, pie ni número (márgenes: mediana y percentiles), posición del número
         de página por página (superior/inferior, izquierda/centro/derecha), sangría visible de primera línea en los párrafos de
         cuerpo, paso de línea, fuentes y tamaños reales de los spans.
  Docx frente a PDF: las diferencias salen como AVISO (p. ej. Word frente a LibreOffice), nunca como violación.
  Lo que no se puede medir sale como «no medible: …» con su porqué; nunca se da por bueno.

Reglas del usuario (scripts/medidas.py): `--regla "frase"` (repetible) o el bloque `medidas:` de .editorial.yaml
(`--medidas`, o sin flags si el bloque existe) se evalúan sobre la ficha: cumple / NO CUMPLE / no medible / PREGUNTA. Una frase que
no se entiende vuelve como pregunta, nunca se adivina. `--contra perfil` evalúa además lo medible de `formato:`/`reglas_guia:`
del perfil. `auditar` emite INS-016 con las mismas reglas.
Salida: 0 sin incumplimientos, 1 con alguna regla que no cumple, 2 error de uso o de entrada.
"""
import argparse
import collections
import json
import pathlib
import re
import statistics
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cli  # noqa: E402
import ooxml  # noqa: E402
import unidades as U  # noqa: E402

from docx.oxml.ns import qn  # noqa: E402

VERSION_FICHA = 1
ROLES_TITULO = ("titulo 1", "titulo 2", "titulo 3", "titulo 4", "titulo 5")
# fuentes que LibreOffice sustituye por una métricamente compatible (no es discrepancia real)
SUSTITUCIONES = {"timesnewroman": {"liberationserif", "tinos", "nimbusroman", "times", "timesroman"}, "arial": {"liberationsans", "arimo", "nimbussans"},
                 "calibri": {"carlito"}, "cambria": {"caladea"}, "couriernew": {"liberationmono", "cousine"},
                 "helvetica": {"liberationsans", "arimo", "nimbussans"}, "georgia": {"gelasio"}}


# ================================================================ herencia en .docx
class Efectivo:
    """Valores efectivos de un párrafo, como los resuelve Word. Reutiliza `modelo_formato.Resolutor` para los runs."""

    def __init__(self, d):
        import modelo_formato as MF
        self.d = d
        self.res = MF.Resolutor(d)
        dd = d.styles.element.find(qn("w:docDefaults"))
        self.ppr_def = dd.find(qn("w:pPrDefault") + "/" + qn("w:pPr")) if dd is not None else None
        self.numeracion = self._numeracion()

    def _numeracion(self):
        from lxml import etree
        for parte in self.d.part.package.iter_parts():
            if str(parte.partname).endswith("/numbering.xml"):
                try:
                    raiz = etree.fromstring(parte.blob)
                except Exception:  # noqa: BLE001
                    return None
                return raiz
        return None

    def _lvl_ppr(self, num_id, ilvl):
        raiz = self.numeracion
        if raiz is None or num_id in (None, "0"):
            return None
        num = next((n for n in raiz.findall(qn("w:num")) if n.get(qn("w:numId")) == str(num_id)), None)
        if num is None:
            return None
        a = num.find(qn("w:abstractNumId"))
        an = next((x for x in raiz.findall(qn("w:abstractNum")) if a is not None and x.get(qn("w:abstractNumId")) == a.get(qn("w:val"))), None)
        if an is None:
            return None
        for lv in an.findall(qn("w:lvl")):
            if lv.get(qn("w:ilvl")) == str(ilvl):
                return lv.find(qn("w:pPr"))
        return None

    def _numpr(self, ppr):
        if ppr is None:
            return None, 0
        n = ppr.find(qn("w:numPr"))
        if n is None:
            return None, 0
        nid, il = n.find(qn("w:numId")), n.find(qn("w:ilvl"))
        return (nid.get(qn("w:val")) if nid is not None else None), int(il.get(qn("w:val"))) if il is not None else 0

    def fuentes_ppr(self, p_el):
        """[(origen, w:pPr)] por prioridad: párrafo, numeración, estilo (y bases), docDefaults."""
        out = []
        ppr = p_el.find(qn("w:pPr"))
        nid, il = self._numpr(ppr)
        if ppr is not None:
            out.append(("párrafo", ppr))
        if nid not in (None, "0"):
            out.append(("numeración", self._lvl_ppr(nid, il)))
        for s in self.res._estilo_parrafo(p_el):
            nom = s.find(qn("w:name"))
            sp = s.find(qn("w:pPr"))
            out.append((f"estilo «{nom.get(qn('w:val')) if nom is not None else s.get(qn('w:styleId'))}»", sp))
            if nid is None:
                snid, sil = self._numpr(sp)
                if snid not in (None, "0"):
                    out.append(("numeración del estilo", self._lvl_ppr(snid, sil)))
        out.append(("docDefaults", self.ppr_def))
        return [(o, x) for o, x in out if x is not None]

    @staticmethod
    def _primero(fuentes, tag, *attrs):
        """(valor, origen) del primer elemento `tag` de las fuentes que define alguno de `attrs`."""
        for o, x in fuentes:
            e = x.find(qn(tag))
            if e is None:
                continue
            for a in attrs:
                if e.get(qn(a)) is not None:
                    return e.get(qn(a)), o
        return None, None

    def parrafo(self, p_el):
        """Dict con las longitudes en PUNTOS: izq, der, primera (negativa = francesa), antes, despues; interlineado
        ({regla, multiplo|pt}); alineacion; y `avisos` con lo que no se puede resolver."""
        f = self.fuentes_ppr(p_el)
        avisos = []
        v = {}
        for clave, attrs in (("izq", ("w:left", "w:start")), ("der", ("w:right", "w:end"))):
            x, _ = self._primero(f, "w:ind", *attrs)
            v[clave] = int(x) / 20.0 if x is not None else 0.0
        fl, _ = self._primero(f, "w:ind", "w:firstLine")
        hg, o_h = self._primero(f, "w:ind", "w:hanging")
        # firstLine y hanging son excluyentes dentro de un mismo w:ind: gana el de la fuente más cercana
        for o, x in f:
            e = x.find(qn("w:ind"))
            if e is None:
                continue
            if e.get(qn("w:firstLine")) is not None or e.get(qn("w:hanging")) is not None:
                v["primera"] = (int(e.get(qn("w:firstLine"))) if e.get(qn("w:firstLine")) is not None else -int(e.get(qn("w:hanging")))) / 20.0
                break
        else:
            v["primera"] = 0.0
        for o, x in f:
            e = x.find(qn("w:ind"))
            if e is not None and any(e.get(qn(a)) is not None for a in ("w:leftChars", "w:startChars", "w:firstLineChars", "w:hangingChars", "w:rightChars")):
                avisos.append("sangría en caracteres (w:*Chars): su ancho depende de la fuente")
                break
        for clave, tag, lines, auto in (("antes", "w:before", "w:beforeLines", "w:beforeAutospacing"), ("despues", "w:after", "w:afterLines", "w:afterAutospacing")):
            if self._primero(f, "w:spacing", auto)[0] in ("1", "true", "on"):
                v[clave] = 14.0
                avisos.append(f"espacio {'antes' if clave == 'antes' else 'después'} automático (como en HTML): se cuenta 14 pt")
                continue
            x, _ = self._primero(f, "w:spacing", tag)
            if x is None and self._primero(f, "w:spacing", lines)[0] is not None:
                avisos.append("espacio en líneas (w:*Lines): depende del tamaño de la fuente")
            v[clave] = int(x) / 20.0 if x is not None else 0.0
        ln, o_ln = self._primero(f, "w:spacing", "w:line")
        regla = None
        if ln is not None:  # el w:lineRule viene del mismo elemento que w:line
            for o, x in f:
                e = x.find(qn("w:spacing"))
                if e is not None and e.get(qn("w:line")) is not None:
                    regla = e.get(qn("w:lineRule"))
                    break
        v["interlineado"] = U.interlineado_de_xml(ln, regla) or {"regla": "auto", "multiplo": 1.0}
        if ln is None:
            avisos.append("sin w:line efectivo: Word usa una línea (×1)")
        j, _ = self._primero(f, "w:jc", "w:val")
        v["alineacion"] = {"center": "centro", "right": "derecha", "end": "derecha", "both": "justificada", "distribute": "justificada",
                           "left": "izquierda", "start": "izquierda"}.get(j, "izquierda")
        v["avisos"] = avisos
        return v

    def runs(self, p_el):
        """Valores de fuente del párrafo: dominante por número de caracteres y si es mixto."""
        pesos = collections.defaultdict(int)
        for r in p_el.iter(qn("w:r")):
            a = r.getparent()
            while a is not None and a is not p_el and a.tag != ooxml.FALLBACK:
                a = a.getparent()
            if a is not None and a.tag == ooxml.FALLBACK:
                continue
            tx = "".join(t.text or "" for t in r.iter(ooxml.W_T))
            if not tx.strip():
                continue
            e = self.res.run(r, p_el)
            pesos[(e["fuente"], e["pt"], e["color"], e["negrita"], e["cursiva"])] += len(tx)
        if not pesos:
            e = self.res.run(None, p_el)
            return {"fuente": e["fuente"], "tamano": e["pt"], "color": e["color"], "negrita": e["negrita"], "cursiva": e["cursiva"], "mixto": False, "vacio": True}
        dom = max(pesos, key=pesos.get)
        return {"fuente": dom[0], "tamano": dom[1], "color": dom[2], "negrita": dom[3], "cursiva": dom[4],
                "mixto": len({(k[0], k[1]) for k in pesos}) > 1, "vacio": False}


# ================================================================ secciones
def _num_pagina_seccion(sec, k, d):
    """[{parte, lugar, lado}] de las partes de la sección que llevan un campo PAGE."""
    import institucional
    out = []
    heredado = False
    for nom, h, f in ooxml.partes_seccion(sec, k, d, pares=True, sec0_propia=True):
        for lugar, parte in (("encabezado", h), ("pie", f)):
            if parte is None or not ooxml.tiene_pagina(parte._element):
                continue
            for p_el in parte._element.iter(qn("w:p")):
                if ooxml.tiene_pagina(p_el):
                    out.append({"parte": (nom.strip(", ") or "predeterminada"), "lugar": lugar, "lado": institucional.lado_numero(p_el)})
    return out


def _texto_parte(parte):
    try:
        return " ".join(ooxml.texto_visible(p).strip() for p in parte._element.iter(qn("w:p")) if ooxml.texto_visible(p).strip())[:70]
    except Exception:  # noqa: BLE001
        return ""


def secciones_ficha(d, parrafos):
    import institucional
    out = []
    mirror = d.settings.element.find(qn("w:mirrorMargins")) is not None
    for k, sec in enumerate(d.sections):
        el = sec._sectPr
        sz, mg = el.find(qn("w:pgSz")), el.find(qn("w:pgMar"))

        def tw(e, a):
            return int(e.get(qn(a))) / 20.0 if e is not None and e.get(qn(a)) is not None else None
        ancho, alto = tw(sz, "w:w"), tw(sz, "w:h")
        m = {n: tw(mg, "w:" + n) for n in ("top", "bottom", "left", "right", "header", "footer", "gutter")}
        declarado = mg is not None and all(m[n] is not None for n in ("top", "bottom", "left", "right"))
        efectivo = {n: (m[n] if m[n] is not None else U.PT_IN) for n in ("top", "bottom", "left", "right")}
        fmt, inicio = institucional.formato_seccion(el)
        n_par = sum(1 for p in parrafos if p["sec"] == k and not p["en_tabla"])
        nums = _num_pagina_seccion(sec, k, d)
        heredado = False
        if not nums and k > 0 and (sec.header.is_linked_to_previous or sec.footer.is_linked_to_previous):
            nums, heredado = (out[-1]["numero_pagina"]["partes"], True) if out else ([], False)
        pred = [n for n in nums if n["parte"] == "predeterminada"] or nums
        out.append({
            "n": k + 1, "parrafos": n_par,
            "pagina": {"ancho": U.todas(ancho), "alto": U.todas(alto), "orientacion": (sz.get(qn("w:orient")) if sz is not None else None) or ("horizontal" if ancho and alto and ancho > alto else "vertical")} if ancho else None,
            "margenes": {"superior": U.todas(efectivo["top"]), "inferior": U.todas(efectivo["bottom"]),
                         "izquierdo": U.todas(efectivo["left"]), "derecho": U.todas(efectivo["right"]),
                         "encabezado": U.todas(m["header"]), "pie": U.todas(m["footer"]), "canal": U.todas(m["gutter"] or 0.0)},
            "margenes_declarados": declarado,
            "espejo": mirror,
            "ancho_texto": U.todas(ancho - efectivo["left"] - efectivo["right"] - (m["gutter"] or 0.0)) if ancho else None,
            "numeracion": {"formato": fmt, "inicio": int(inicio) if inicio not in (None, "") else None},
            "primera_pagina_distinta": bool(sec.different_first_page_header_footer),
            "numero_pagina": {"partes": nums, "heredado": heredado,
                              "donde": ("sin número" if not pred else ", ".join(sorted({f"{n['lugar']} {n['lado'] or 'lado indeterminado (tabuladores)'}" for n in pred})))},
            "encabezado_texto": _texto_parte(sec.header) if not sec.header.is_linked_to_previous else "",
            "pie_texto": _texto_parte(sec.footer) if not sec.footer.is_linked_to_previous else "",
            "_sectPr": None,
        })
        out[-1].pop("_sectPr")
    return out


# ================================================================ párrafos, grupos y estilos
def roles(pars_aud):
    """{i: rol} con la partición de auditar: portada, titulo N, resumen, cuerpo, referencias, tabla, otros, vacio, posterior."""
    import auditar as A
    import institucional as I
    fin_p = A.fin_portada(pars_aud)
    cuerpo_a, titulo_ref, entradas = A.partir(pars_aud)
    ids_ent = {id(e) for e in entradas}
    res = I.info_resumen(pars_aud)
    ids_res = {id(q) for q in (res[1] + ([res[2]] if res[2] else []))} if res else set()
    fin_ref = (max((e["i"] for e in entradas), default=titulo_ref["i"] if titulo_ref else None))
    out = {}
    for p in pars_aud:
        t = p["texto"].strip()
        if p.get("en_tabla"):
            r = "tabla"
        elif not t and not p.get("imagen"):
            r = "vacio"
        elif p["i"] < fin_p:
            r = "portada"
        elif A.nivel_estilo(p) or p.get("es_titulo"):
            n = A.nivel_estilo(p)
            r = f"titulo {n}" if n else "titulo (otro)"
        elif id(p) in ids_ent:
            r = "referencias"
        elif id(p) in ids_res:
            r = "resumen"
        elif fin_ref is not None and p["i"] > fin_ref:
            r = "posterior a referencias"
        elif len(t) > 80 and "CENTER" not in p["alineacion"] and not p.get("imagen"):
            r = "cuerpo"
        else:
            r = "otros"
        out[p["i"]] = r
    return out


def recorrer(d):
    """[(w:p, en_tabla, n.º de sección 0-based)] en el orden de auditar.cargar_docx."""
    import modelo_formato as MF
    res, sec = [], 0
    for p_el, tb in MF.parrafos_cuerpo(d):
        res.append((p_el, tb, sec))
        if not tb and p_el.find(qn("w:pPr") + "/" + qn("w:sectPr")) is not None:
            sec += 1
    return res


RE_ESTILO_INDICE = re.compile(r"^(?:toc\s*\d*|toc\s*heading|tdc\s*\d*|tdc\s*heading|table\s+of\s+(?:figures|authorities)|tabla\s+de\s+(?:ilustraciones|figuras|autoridades)|"
                               r"[ií]ndice\s*\d*|contenido\s*\d*|encabezado\s+de\s+tdc|encabezado\s+de\s+tabla\s+de\s+contenido)$", re.I)


def es_indice(ef, p_el, en_campo_toc):
    """True si el párrafo es parte de un índice: estilo toc N / TOC Heading / table of figures (o su nombre localizado, por el
    styleId o por la cadena basedOn) o dentro de un campo TOC/TOF."""
    if en_campo_toc:
        return True
    ps = p_el.find(qn("w:pPr") + "/" + qn("w:pStyle"))
    if ps is None:
        return False
    for s in ef.res.cadena(ps.get(qn("w:val"))):
        n = s.find(qn("w:name"))
        for cand in (n.get(qn("w:val")) if n is not None else "", s.get(qn("w:styleId")) or ""):
            if RE_ESTILO_INDICE.match(cand.strip()):
                return True
    return False


def _campos_toc(rec):
    """[bool] por párrafo: ¿empieza o sigue dentro de un campo TOC/TOF (complejo o fldSimple)?"""
    pila, out = [], []
    for p_el, _tb, _sec in rec:
        dentro = any(pila)
        for n in p_el.iter(qn("w:fldChar"), qn("w:instrText"), qn("w:fldSimple")):
            if n.tag == qn("w:fldSimple"):
                dentro = dentro or bool(re.match(r"\s*(?:TOC|TOF)(?![A-Za-z])", n.get(qn("w:instr")) or ""))
            elif n.tag == qn("w:instrText"):
                if pila and pila[-1] is None:
                    pila[-1] = bool(re.match(r"\s*(?:TOC|TOF)(?![A-Za-z])", n.text or ""))
                    dentro = dentro or pila[-1]
            else:
                t = n.get(qn("w:fldCharType"))
                if t == "begin":
                    pila.append(None)
                elif t == "end" and pila:
                    pila.pop()
        out.append(dentro)
    return out


def _estilo_nombre(ef, p_el):
    ps = p_el.find(qn("w:pPr") + "/" + qn("w:pStyle"))
    sid = ps.get(qn("w:val")) if ps is not None else (ef.res.def_par.get(qn("w:styleId")) if ef.res.def_par is not None else None)
    s = ef.res.estilos.get(sid)
    n = s.find(qn("w:name")) if s is not None else None
    return n.get(qn("w:val")) if n is not None else (sid or "Normal")


ATRIBUTOS = [("fuente", "fuente"), ("tamano", "tamaño (pt)"), ("interlineado", "interlineado"), ("antes", "espacio antes"),
             ("despues", "espacio después"), ("izq", "sangría izquierda"), ("der", "sangría derecha"),
             ("primera", "primera línea (+) / francesa (−)"), ("alineacion", "alineación"), ("color", "color"),
             ("negrita", "negrita"), ("cursiva", "cursiva")]
LONGITUDES = {"antes", "despues", "izq", "der", "primera"}


def _clave(attr, v):
    if attr == "interlineado":
        return U.texto_interlineado(v)
    if attr in LONGITUDES:
        return round(v, 1)
    if attr == "tamano":
        return round(v, 2)
    return v


def _rep(attr, clave, muestra):
    if attr in LONGITUDES:
        return U.todas(clave)
    if attr == "interlineado":
        return {"texto": clave, **muestra}
    return clave


def _estadistica(lista, max_exc=8):
    """Estadística de un grupo: por atributo, valores con su conteo, dominante y excepciones."""
    out = {}
    for attr, _ in ATRIBUTOS:
        cont = collections.Counter(_clave(attr, p["v"][attr]) for p in lista)
        muestra = {}
        for p in lista:
            muestra.setdefault(_clave(attr, p["v"][attr]), p["v"][attr])
        dom = cont.most_common(1)[0][0]
        exc = [{"i": p["i"] + 1, "inicio": p["texto"][:40], "valor": _rep(attr, _clave(attr, p["v"][attr]), p["v"][attr])}
               for p in lista if _clave(attr, p["v"][attr]) != dom]
        out[attr] = {"dominante": _rep(attr, dom, muestra[dom]), "valores": [{"valor": _rep(attr, k, muestra[k]), "n": n} for k, n in cont.most_common()],
                     "excepciones": exc[:max_exc], "excepciones_total": len(exc)}
    return out


def parrafos_ficha(d, ef, pars_aud):
    rec = recorrer(d)
    cuerpo = [p for p in pars_aud if not p.get("nota_pie")]
    if len(rec) != len(cuerpo):
        raise RuntimeError(f"el recorrido de párrafos ({len(rec)}) no coincide con el del juez ({len(cuerpo)})")
    rol = roles(cuerpo)
    out = []
    toc = _campos_toc(rec)
    for (p_el, tb, sec), a, en_toc in zip(rec, cuerpo, toc):
        if es_indice(ef, p_el, en_toc) and not tb:
            rol[a["i"]] = "indice"  # entradas del índice (toc N, table of figures, campo TOC): no son cuerpo ni títulos
        v = ef.parrafo(p_el)
        v.update({k: x for k, x in ef.runs(p_el).items()})
        out.append({"i": a["i"], "texto": a["texto"].strip(), "rol": rol[a["i"]], "sec": sec, "en_tabla": tb, "estilo": _estilo_nombre(ef, p_el),
                    "v": v, "aud": a, "vacio": rol[a["i"]] == "vacio"})
    return out


def grupos_y_estilos(parrafos):
    util = [p for p in parrafos if not p["vacio"]]
    por_rol = collections.defaultdict(list)
    por_estilo = collections.defaultdict(list)
    for p in util:
        por_rol[p["rol"]].append(p)
        por_estilo[p["estilo"]].append(p)
    orden = ["portada", "titulo 1", "titulo 2", "titulo 3", "titulo 4", "titulo 5", "titulo (otro)", "resumen", "cuerpo", "referencias", "posterior a referencias", "indice", "otros", "tabla"]
    grupos = [{"grupo": r, "n": len(por_rol[r]), "atributos": _estadistica(por_rol[r])} for r in orden if por_rol.get(r)]
    estilos = [{"estilo": e, "n": len(l), "atributos": _estadistica(l)} for e, l in sorted(por_estilo.items(), key=lambda x: -len(x[1]))]
    return grupos, estilos


NO_MEDIBLE_SIN_PDF = [
    {"que": "posición exacta del número de página", "motivo": "el .docx declara el campo PAGE y su alineación; el lugar real lo da el PDF (--pdf o --render)"},
    {"que": "campos con resultado calculado (índices, NUMPAGES, referencias cruzadas)", "motivo": "sin render el .docx solo trae el resultado en caché; el PDF trae el real"},
]
NO_MEDIBLE_BASE = [
    {"que": "texto en cuadros de texto, formas y WordArt", "motivo": "los párrafos dentro de w:txbxContent no se recorren: su formato no está en esta ficha"},
    {"que": "juicios de estilo («se ve profesional», «limpio», «legible»)", "motivo": "no hay valor numérico que medir; se pregunta al usuario qué medida concreta quiere"},
]


def ficha_docx(path, pars=None, con_pdf=False):
    """Ficha de `path`. `pars` (opcional): los párrafos que ya leyó `auditar.cargar_docx`, para no leer el documento dos veces."""
    import auditar as A
    d = A.abrir_docx(path)
    if pars is None:
        pars, _ = A.cargar_docx(path)
    ef = Efectivo(d)
    parrafos = parrafos_ficha(d, ef, pars)
    secs = secciones_ficha(d, parrafos)
    grupos, estilos = grupos_y_estilos(parrafos)
    no_med = [dict(x) for x in (NO_MEDIBLE_BASE if con_pdf else NO_MEDIBLE_SIN_PDF + NO_MEDIBLE_BASE)]
    chars = collections.Counter(a for p in parrafos if not p["vacio"] for a in p["v"]["avisos"])
    for a, n in chars.items():
        no_med.append({"que": f"{a} ({n} párrafos)", "motivo": "se cuenta interlineado sencillo (×1), como hace Word" if "w:line" in a else "el valor en puntos es una aproximación"})
    for s in secs:
        if not s["margenes_declarados"]:
            no_med.append({"que": f"márgenes de la sección {s['n']}", "motivo": "el sectPr no declara pgMar completo: se cuenta el valor por defecto de Word (1 in)"})
        if any(n["lado"] is None for n in s["numero_pagina"]["partes"]):
            no_med.append({"que": f"lado del número de página en la sección {s['n']}", "motivo": "va con tabuladores: solo el PDF dice dónde cae"})
        if s["espejo"]:
            no_med.append({"que": f"márgenes de la sección {s['n']}", "motivo": "márgenes simétricos (espejo): izquierdo/derecho son interior/exterior según la página"})
    return {"version_ficha": VERSION_FICHA, "documento": str(path), "secciones": secs, "grupos": grupos, "estilos": estilos,
            "no_medible": no_med, "_parrafos": parrafos}


# ================================================================ PDF
def _pct(xs, q):
    xs = sorted(xs)
    if not xs:
        return None
    k = (len(xs) - 1) * q
    a, b = int(k), min(int(k) + 1, len(xs) - 1)
    return xs[a] + (xs[b] - xs[a]) * (k - a)


RE_NUMERO = re.compile(r"^\s*(?:\d{1,4}|[ivxlcdm]{1,8}|[IVXLCDM]{1,8})\s*$")


def _lado(cx, ancho):
    return "izquierda" if cx < ancho * 0.38 else ("derecha" if cx > ancho * 0.62 else "centro")


def medir_pdf(ruta):
    """Medidas del PDF por página y agregadas (puntos y cm/in). Sale con código 2 si falta PyMuPDF o el PDF no abre."""
    try:
        import fitz
    except ImportError:
        cli.error("medir un PDF necesita PyMuPDF: pip install pymupdf")
    try:
        doc = fitz.open(str(ruta))
    except Exception as e:  # noqa: BLE001
        cli.error(f"no se pudo abrir el PDF {ruta}: {e}")
    paginas, numeros, spans_tot = [], [], collections.Counter()
    todas_lineas = []
    for n, pg in enumerate(doc, 1):
        W, H = pg.rect.width, pg.rect.height
        lineas = []
        for b in pg.get_text("dict")["blocks"]:
            if b.get("type") != 0:
                continue
            for k, ln in enumerate(b["lines"]):
                sp = [s for s in ln["spans"] if s["text"].strip()]
                if not sp:
                    continue
                dom = max(sp, key=lambda s: len(s["text"].strip()))
                lineas.append({"bbox": ln["bbox"], "texto": "".join(s["text"] for s in ln["spans"]).strip(), "size": dom["size"], "font": dom["font"],
                               "y": dom["origin"][1], "bloque": id(b), "k": k, "spans": sp})
                for s in sp:
                    spans_tot[(s["font"], round(s["size"], 1))] += len(s["text"].strip())
        # número de página: span numérico suelto en la franja superior o inferior (12 % de la altura)
        cand = None
        for ln in lineas:
            for s in ln["spans"]:
                x0, y0, x1, y1 = s["bbox"]
                if RE_NUMERO.match(s["text"]) and (y1 < H * 0.12 or y0 > H * 0.88):
                    zona = "superior" if (y0 + y1) / 2 < H / 2 else "inferior"
                    puntaje = (y0 if zona == "superior" else H - y1)
                    if cand is None or puntaje < cand[0]:
                        cand = (puntaje, {"pagina": n, "texto": s["text"].strip(), "zona": zona, "lado": _lado((x0 + x1) / 2, W),
                                          "x0": round(x0, 1), "x1": round(x1, 1), "y0": round(y0, 1), "y1": round(y1, 1)}, s)
        if cand:
            numeros.append(cand[1])
        paginas.append({"n": n, "ancho": W, "alto": H, "lineas": lineas, "num": cand[2] if cand else None})
        todas_lineas.append(lineas)
    # encabezados y pies: texto repetido (sin dígitos) en las franjas de la misma altura en varias páginas
    rep = collections.Counter()
    for pg in paginas:
        vistos = set()
        for ln in pg["lineas"]:
            y0, y1 = ln["bbox"][1], ln["bbox"][3]
            if y1 < pg["alto"] * 0.075 or y0 > pg["alto"] * 0.925:
                vistos.add((re.sub(r"\d+", "#", ln["texto"]), round(y0 / 3)))
        rep.update(vistos)
    umbral = max(2, int(0.3 * len(paginas)))
    marco = {k for k, c in rep.items() if c >= umbral}
    cajas = []
    for pg in paginas:
        cuerpo = []
        for ln in pg["lineas"]:
            y0, y1 = ln["bbox"][1], ln["bbox"][3]
            en_franja = y1 < pg["alto"] * 0.075 or y0 > pg["alto"] * 0.925
            en_franja_num = y1 < pg["alto"] * 0.12 or y0 > pg["alto"] * 0.88
            if (en_franja and (re.sub(r"\d+", "#", ln["texto"]), round(y0 / 3)) in marco) or (en_franja_num and RE_NUMERO.match(ln["texto"])):
                continue
            cuerpo.append(ln)
        pg["cuerpo"] = cuerpo
        if cuerpo:
            cajas.append({"pagina": pg["n"], "lineas": len(cuerpo), "x0": min(l["bbox"][0] for l in cuerpo), "x1": max(l["bbox"][2] for l in cuerpo),
                          "y0": min(l["bbox"][1] for l in cuerpo), "y1": max(l["bbox"][3] for l in cuerpo)})
    W0, H0 = (paginas[0]["ancho"], paginas[0]["alto"]) if paginas else (0, 0)
    llenas = [c for c in cajas if c["lineas"] >= 3] or cajas
    agregado = None
    if llenas:
        q = lambda k, f: _pct([c[k] for c in llenas], f)  # noqa: E731
        agregado = {
            "paginas_consideradas": len(llenas),
            "izquierda": {"mediana": U.todas(q("x0", 0.5)), "minimo": U.todas(min(c["x0"] for c in llenas))},
            "derecha": {"p90": U.todas(W0 - q("x1", 0.9)), "mediana": U.todas(W0 - q("x1", 0.5)), "minimo": U.todas(W0 - max(c["x1"] for c in llenas))},
            "superior": {"p10": U.todas(q("y0", 0.1)), "mediana": U.todas(q("y0", 0.5)), "minimo": U.todas(min(c["y0"] for c in llenas))},
            "inferior": {"p90": U.todas(H0 - q("y1", 0.9)), "mediana": U.todas(H0 - q("y1", 0.5)), "minimo": U.todas(H0 - max(c["y1"] for c in llenas))},
        }
    # tamaño de cuerpo = el de mayor peso
    tam_cuerpo = None
    if spans_tot:
        pesos = collections.Counter()
        for (f, s), c in spans_tot.items():
            pesos[s] += c
        tam_cuerpo = pesos.most_common(1)[0][0]
    # sangría visible de primera línea (y francesa) y paso de línea, por geometría de las líneas de cuerpo de cada página: los
    # PDF de LibreOffice y de Word parten un párrafo en varios bloques, así que no se puede medir por bloque
    sang, pasos = [], []
    for pg in paginas:
        ls = sorted((l for l in pg["cuerpo"] if tam_cuerpo and abs(l["size"] - tam_cuerpo) <= 0.6), key=lambda l: (l["y"], l["bbox"][0]))
        if len(ls) < 4:
            continue
        izq = _pct([l["bbox"][0] for l in ls], 0.05)  # percentil 5: el margen izquierdo de la página (la mediana caería entre la primera línea sangrada y las demás)
        der = max(l["bbox"][2] for l in ls)
        corto = izq + 0.75 * (der - izq)
        par = lambda a_, b_: 0.9 * tam_cuerpo < b_["y"] - a_["y"] < 3.2 * tam_cuerpo  # noqa: E731  (líneas consecutivas del mismo bloque de texto)
        for k, l in enumerate(ls):
            x = l["bbox"][0]
            if k + 1 < len(ls) and par(l, ls[k + 1]):
                pasos.append(ls[k + 1]["y"] - l["y"])
            sig = ls[k + 1] if k + 1 < len(ls) and par(l, ls[k + 1]) else None
            ant = ls[k - 1] if k and par(ls[k - 1], l) else None
            if 2 <= x - izq <= 80 and sig is not None and abs(sig["bbox"][0] - izq) <= 1.5:
                sang.append(round(x - sig["bbox"][0], 1))               # primera línea sangrada
            elif abs(x - izq) <= 1.5 and sig is not None and 2 <= sig["bbox"][0] - izq <= 80:
                sig2 = ls[k + 2] if k + 2 < len(ls) and par(sig, ls[k + 2]) else None
                if sig2 is not None and abs(sig2["bbox"][0] - sig["bbox"][0]) <= 1.5:
                    sang.append(round(x - sig["bbox"][0], 1))           # francesa: primera línea a la izquierda de las demás
            elif abs(x - izq) <= 1.5 and ant is not None and ant["bbox"][2] < corto and sig is not None and abs(sig["bbox"][0] - izq) <= 1.5:
                sang.append(0.0)                                         # párrafo que empieza tras una línea corta, sin sangría
    hist = collections.Counter(round(s / U.PT_CM, 2) for s in sang)
    fuentes = collections.Counter()
    total = sum(spans_tot.values()) or 1
    for (f, s), c in spans_tot.items():
        fuentes[(f, s)] += c
    info = doc.metadata or {}
    res = {
        "documento": str(ruta), "paginas": len(paginas), "productor": info.get("producer") or info.get("creator") or "",
        "pagina": {"ancho": U.todas(W0), "alto": U.todas(H0)} if paginas else None,
        "margenes": agregado,
        "por_pagina": [{"pagina": c["pagina"], "lineas": c["lineas"], "izquierda_cm": round(c["x0"] / U.PT_CM, 2), "derecha_cm": round((W0 - c["x1"]) / U.PT_CM, 2),
                        "superior_cm": round(c["y0"] / U.PT_CM, 2), "inferior_cm": round((H0 - c["y1"]) / U.PT_CM, 2)} for c in cajas],
        "numero_pagina": {"por_pagina": numeros, "paginas_con_numero": len(numeros), "paginas_sin_numero": [p["n"] for p in paginas if p["n"] not in {x["pagina"] for x in numeros}],
                          "predominante": (lambda c: {"zona": c[0][0][0], "lado": c[0][0][1], "paginas": c[0][1]} if c else None)(collections.Counter((x["zona"], x["lado"]) for x in numeros).most_common(1))},
        "sangria_primera_linea": {"bloques": len(sang), "histograma_cm": {f"{k:g}": n for k, n in sorted(hist.items())},
                                  "moda_cm": (hist.most_common(1)[0][0] if hist else None), "moda_pt": (round(hist.most_common(1)[0][0] * U.PT_CM, 1) if hist else None)},
        "paso_linea": ({"mediana_pt": round(statistics.median(pasos), 2), "tamano_pt": tam_cuerpo, "razon": round(statistics.median(pasos) / tam_cuerpo, 3)} if pasos and tam_cuerpo else None),
        "tamano_cuerpo_pt": tam_cuerpo,
        "fuentes": [{"fuente": f, "norm": _norm_fuente(f), "pt": s, "porcentaje": round(100 * c / total, 1)} for (f, s), c in fuentes.most_common(6)],
        "notas": ["margen derecho e inferior: con texto no justificado o páginas cortas el valor medido es MAYOR que el real (se usa el percentil 90 de los bordes por página)",
                  "la caja de cada línea incluye el aire de la tipografía: el margen superior medido puede exceder el declarado en una fracción del interlineado"],
    }
    return res


def _norm_fuente(n):
    import modelo_formato as MF
    return MF.norm_fuente(n)


# ================================================================ docx frente a PDF
def seccion_principal(ficha):
    c = collections.Counter(p["sec"] for p in ficha["_parrafos"] if p["rol"] == "cuerpo")
    k = c.most_common(1)[0][0] if c else 0
    return ficha["secciones"][min(k, len(ficha["secciones"]) - 1)]


def dominante(ficha, grupo, attr):
    g = next((g for g in ficha["grupos"] if g["grupo"] == grupo), None)
    return g["atributos"][attr]["dominante"] if g else None


def discrepancias(ficha, pdfm):
    """Avisos (texto) donde el .docx y el PDF no dicen lo mismo. Nunca son hallazgos: Word y LibreOffice maquetan distinto."""
    av = []
    sec = seccion_principal(ficha)
    tol = U.TOLERANCIA_PDF
    pdf_pag = pdfm.get("pagina")
    if sec.get("pagina") and pdf_pag and not any(abs(s["pagina"]["ancho"]["pt"] - pdf_pag["ancho"]["pt"]) < 3 and abs(s["pagina"]["alto"]["pt"] - pdf_pag["alto"]["pt"]) < 3
                                                 for s in ficha["secciones"] if s.get("pagina")):
        av.append(f"tamaño de página: el .docx dice {sec['pagina']['ancho']['cm']:g} × {sec['pagina']['alto']['cm']:g} cm y el PDF {pdf_pag['ancho']['cm']:g} × {pdf_pag['alto']['cm']:g} cm")
    m, g = sec["margenes"], pdfm.get("margenes")
    if g:
        def cm(x):
            return x["cm"]
        justif = (dominante(ficha, "cuerpo", "alineacion") or "") == "justificada"
        izq = cm(g["izquierda"]["mediana"])
        if abs(izq - cm(m["izquierdo"])) > tol["lateral_cm"]:
            av.append(f"margen izquierdo: el .docx dice {cm(m['izquierdo']):g} cm y el PDF mide {izq:g} cm")
        der = cm(g["derecha"]["p90"])
        if der < cm(m["derecho"]) - tol["lateral_cm"] or (justif and der > cm(m["derecho"]) + tol["lateral_cm"]):
            av.append(f"margen derecho: el .docx dice {cm(m['derecho']):g} cm y el PDF mide {der:g} cm")
        sup = cm(g["superior"]["p10"])
        if sup < cm(m["superior"]) - tol["vertical_cm"]:
            av.append(f"margen superior: el .docx dice {cm(m['superior']):g} cm y el PDF tiene texto a {sup:g} cm del borde")
        inf = cm(g["inferior"]["p90"])
        if inf < cm(m["inferior"]) - tol["vertical_cm"]:
            av.append(f"margen inferior: el .docx dice {cm(m['inferior']):g} cm y el PDF tiene texto a {inf:g} cm del borde")
    # fuente y tamaño del cuerpo
    f_docx, t_docx = dominante(ficha, "cuerpo", "fuente"), dominante(ficha, "cuerpo", "tamano")
    if pdfm.get("fuentes"):
        top = pdfm["fuentes"][0]
        nd = _norm_fuente(f_docx) if f_docx else None
        if nd and top["norm"] != nd:
            if top["norm"] in SUSTITUCIONES.get(nd, ()):
                av.append(f"fuente: el .docx pide {f_docx} y el PDF usa {top['fuente']} (sustituta métricamente compatible; los PDF de Word usan la original)")
            else:
                av.append(f"fuente: el .docx pide {f_docx} y el PDF usa {top['fuente']}")
        if t_docx and abs(top["pt"] - t_docx) > tol["tamano_pt"]:
            av.append(f"tamaño: el .docx dice {t_docx:g} pt y el PDF {top['pt']:g} pt")
    # sangría de primera línea
    s = pdfm.get("sangria_primera_linea") or {}
    pc = dominante(ficha, "cuerpo", "primera")
    if s.get("bloques", 0) >= 3 and pc:
        if abs(s["moda_cm"] - pc["cm"]) > tol["sangria_cm"]:
            av.append(f"sangría de primera línea: el .docx dice {pc['cm']:g} cm y en el PDF la más frecuente es {s['moda_cm']:g} cm ({s['bloques']} párrafos medidos)")
    # número de página
    pred = (pdfm.get("numero_pagina") or {}).get("predominante")
    docx_pos = {(n["lugar"], n["lado"]) for n in sec["numero_pagina"]["partes"] if n["parte"] == "predeterminada"} or {(n["lugar"], n["lado"]) for n in sec["numero_pagina"]["partes"]}
    if pred and docx_pos:
        zona = {"encabezado": "superior", "pie": "inferior"}
        ok = any(zona[l] == pred["zona"] and (lado is None or lado == pred["lado"]) for l, lado in docx_pos)
        if not ok:
            donde = ", ".join(f"{l} {lado or '(tabuladores)'}" for l, lado in sorted(docx_pos, key=str))
            av.append(f"número de página: el .docx lo pone en {donde} y el PDF lo muestra {pred['zona']} {pred['lado']} en {pred['paginas']} páginas")
    elif not pred and docx_pos:
        av.append("número de página: el .docx lleva el campo PAGE y el PDF no muestra ningún número suelto en las franjas superior e inferior")
    # interlineado
    il, pl = dominante(ficha, "cuerpo", "interlineado"), pdfm.get("paso_linea")
    if il and pl and pl["tamano_pt"]:
        if il["regla"] == "exact":
            if abs(pl["mediana_pt"] - il["pt"]) > 1.0:
                av.append(f"interlineado: el .docx fija {il['pt']:g} pt exactos y el PDF mide {pl['mediana_pt']:g} pt de línea a línea")
        elif il["regla"] == "auto":
            lo, hi = il["multiplo"] * 1.0, il["multiplo"] * 1.30
            if not lo - 0.05 <= pl["razon"] <= hi + 0.05:
                av.append(f"interlineado: el .docx dice ×{il['multiplo']:g}; el PDF mide {pl['mediana_pt']:g} pt de línea a línea ({pl['razon']:g} × el tamaño; se espera {lo:g}-{hi:g})")
    return av


# ================================================================ salida legible
def _f(pt):
    if pt is None:
        return "—"
    if isinstance(pt, dict):
        pt = pt["pt"]
    t = U.todas(pt)
    return f"{t['cm']:g} cm ({t['pt']:g} pt, {t['in']:g} in)"


def _v(attr, x):
    if attr in LONGITUDES:
        return f"{x['cm']:g} cm ({x['pt']:g} pt, {x['in']:g} in)"
    if attr == "interlineado":
        return x["texto"]
    if attr == "tamano":
        return f"{x:g} pt"
    if isinstance(x, bool):
        return "sí" if x else "no"
    return str(x)


def imprimir(ficha, pdfm=None, avisos_pdf=(), seccion=None, cuantas=5):
    print(f"FICHA TÉCNICA: {ficha['documento']}")
    print("\n== SECCIONES ==")
    for s in ficha["secciones"]:
        if seccion and s["n"] != seccion:
            continue
        p, m = s["pagina"], s["margenes"]
        print(f"Sección {s['n']} ({s['parrafos']} párrafos)" + (f"  página {p['ancho']['cm']:g} × {p['alto']['cm']:g} cm ({p['ancho']['in']:g} × {p['alto']['in']:g} in), {p['orientacion']}" if p else ""))
        for k in ("superior", "inferior", "izquierdo", "derecho"):
            print(f"  margen {k:<10} {_f(m[k]['pt'])}")
        print(f"  encabezado {_f(m['encabezado']['pt']) if m['encabezado'] else '—'}   pie {_f(m['pie']['pt']) if m['pie'] else '—'}   canal {_f(m['canal']['pt'])}")
        if not s["margenes_declarados"]:
            print("  (el sectPr no declara pgMar completo: valores por defecto de Word)")
        n = s["numeracion"]
        print(f"  numeración: formato {n['formato']}" + (f", inicia en {n['inicio']}" if n["inicio"] is not None else "") + f"; primera página distinta: {'sí' if s['primera_pagina_distinta'] else 'no'}")
        print(f"  número de página: {s['numero_pagina']['donde']}" + (" (heredado)" if s["numero_pagina"]["heredado"] else ""))
        if s["encabezado_texto"] or s["pie_texto"]:
            print(f"  encabezado: «{s['encabezado_texto']}»   pie: «{s['pie_texto']}»")
    print("\n== GRUPOS DE PÁRRAFOS (valor efectivo; entre paréntesis, cuántos párrafos lo tienen) ==")
    for g in ficha["grupos"]:
        print(f"\n[{g['grupo']}] {g['n']} párrafos")
        for attr, nombre in ATRIBUTOS:
            a = g["atributos"][attr]
            vals = "; ".join(f"{_v(attr, x['valor'])} ({x['n']})" for x in a["valores"][:3]) + (" …" if len(a["valores"]) > 3 else "")
            print(f"  {nombre:<32} {vals}")
            for e in a["excepciones"][:cuantas]:
                print(f"      excepción: párr. {e['i']} «{e['inicio']}»: {_v(attr, e['valor'])}")
            if a["excepciones_total"] > cuantas:
                print(f"      … y {a['excepciones_total'] - cuantas} más")
    print("\n== ESTILOS (por nombre de estilo de párrafo) ==")
    for e in ficha["estilos"][:12]:
        a = e["atributos"]
        print(f"  {e['estilo']:<28} {e['n']:>4} párr.  {a['fuente']['dominante']} {a['tamano']['dominante']:g} pt  {a['interlineado']['dominante']['texto']}  "
              f"antes {a['antes']['dominante']['pt']:g}/después {a['despues']['dominante']['pt']:g} pt  1.ª línea {a['primera']['dominante']['cm']:g} cm  {a['alineacion']['dominante']}")
    if pdfm:
        print("\n== PDF ==")
        print(f"{pdfm['paginas']} páginas, productor: {pdfm['productor'] or '—'}" + (f"; página {pdfm['pagina']['ancho']['cm']:g} × {pdfm['pagina']['alto']['cm']:g} cm" if pdfm["pagina"] else ""))
        g = pdfm["margenes"]
        if g:
            print(f"márgenes medidos (caja de texto sin encabezado, pie ni número; {g['paginas_consideradas']} páginas):")
            for k, ref in (("izquierda", "mediana"), ("derecha", "p90"), ("superior", "p10"), ("inferior", "p90")):
                print(f"  {k:<10} {_f(g[k][ref]['pt'])}   [{ref}; mínimo {g[k]['minimo']['cm']:g} cm]")
        n = pdfm["numero_pagina"]
        if n["predominante"]:
            p = n["predominante"]
            print(f"número de página: {p['zona']} {p['lado']} en {p['paginas']} de {pdfm['paginas']} páginas" + (f"; sin número: {n['paginas_sin_numero'][:12]}" if n["paginas_sin_numero"] else ""))
        else:
            print("número de página: ninguno visible")
        s = pdfm["sangria_primera_linea"]
        print(f"sangría visible de primera línea: {s['bloques']} párrafos medidos; histograma (cm): {s['histograma_cm']}")
        if pdfm["paso_linea"]:
            pl = pdfm["paso_linea"]
            print(f"paso de línea: {pl['mediana_pt']:g} pt con letra de {pl['tamano_pt']:g} pt (× {pl['razon']:g})")
        print("fuentes reales: " + "; ".join(f"{x['fuente']} {x['pt']:g} pt ({x['porcentaje']:g} %)" for x in pdfm["fuentes"][:4]))
        for nt in pdfm["notas"]:
            print("  nota:", nt)
    for a in avisos_pdf:
        print("AVISO (docx frente a PDF; no es violación):", a)
    for nm in ficha["no_medible"]:
        print(f"no medible: {nm['que']}: {nm['motivo']}")


def a_json(ficha, pdfm, avisos_pdf, resultados=None):
    out = {k: v for k, v in ficha.items() if not k.startswith("_")}
    if pdfm is not None:
        out["pdf"] = pdfm
        out["avisos_docx_vs_pdf"] = list(avisos_pdf)
    if resultados is not None:
        out["reglas"] = resultados
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="Ficha técnica de medidas efectivas de un .docx (y su PDF) y reglas medibles del usuario.")
    ap.add_argument("documento", help=".docx (o .pdf: solo la medición del PDF)")
    ap.add_argument("--pdf", help="PDF del mismo documento (mide márgenes reales, número de página, sangría visible)")
    ap.add_argument("--render", action="store_true", help="genera el PDF con LibreOffice para medirlo (en una carpeta temporal)")
    ap.add_argument("--json", metavar="RUTA", help="escribe la ficha completa como JSON")
    ap.add_argument("--seccion", type=int, help="muestra solo la sección N")
    ap.add_argument("--regla", action="append", default=[], metavar="FRASE", help="regla del usuario en lenguaje natural (repetible): «márgenes 3 cm izquierda»")
    ap.add_argument("--origen", default=None, help="de dónde viene la regla (por defecto «usuario <fecha>»)")
    ap.add_argument("--medidas", action="store_true", help="evalúa el bloque `medidas:` de .editorial.yaml")
    ap.add_argument("--contra", metavar="perfil|RUTA", help="evalúa también lo medible de `formato:` y `reglas_guia:` del perfil (`perfil` = el .editorial.yaml del documento)")
    ap.add_argument("--equipo", help="ruta de .editorial.yaml (si no, se busca hacia arriba desde el documento)")
    ap.add_argument("--resumen", action="store_true", help="no imprime la ficha, solo el veredicto de las reglas")
    ap.add_argument("--perfil", help="id de perfil (opcional: medir no lo necesita; si lo das y el .editorial.yaml declara otro, ese archivo se ignora)")
    a = ap.parse_args(argv)
    cli.utf8()
    ruta = pathlib.Path(a.documento)
    if not ruta.is_file():
        cli.error(f"no existe {a.documento}")
    ext = ruta.suffix.lower()
    if ext not in (".docx", ".pdf"):
        cli.error(f"formato no soportado: {ext} (usa .docx o .pdf)")
    cli.perfil_por_defecto(ap, a.perfil, str(ruta), a.equipo, defecto="ninguno")
    pdfm = avisos_pdf = None
    ficha = None
    if ext == ".pdf":
        pdfm = medir_pdf(ruta)
        cli.escribir_json(a.json, {"pdf": pdfm})
        _imprimir_solo_pdf(pdfm)
        sys.exit(0)
    pdf_ruta = a.pdf
    ficha = ficha_docx(str(ruta), con_pdf=bool(a.pdf or a.render))
    if a.render:
        import libreoffice
        import tempfile
        pdf_ruta = str(libreoffice.a_pdf(ruta, tempfile.mkdtemp(prefix="medir-pdf-")))
    if pdf_ruta:
        if not pathlib.Path(pdf_ruta).is_file():
            cli.error(f"no existe el PDF {pdf_ruta}")
        pdfm = medir_pdf(pdf_ruta)
        avisos_pdf = discrepancias(ficha, pdfm)
    resultados = None
    if a.regla or a.medidas or a.contra or _hay_medidas(ruta, a.equipo):
        import medidas as M
        resultados = M.evaluar_todo(ficha, pdfm, a.regla, a.origen, ruta, a.equipo, a.medidas, a.contra)
    if not a.resumen:
        imprimir(ficha, pdfm, avisos_pdf or (), a.seccion)
    if resultados is not None:
        print("\n== REGLAS MEDIBLES ==")
        import medidas as M
        M.imprimir(resultados)
    cli.escribir_json(a.json, a_json(ficha, pdfm, avisos_pdf or (), resultados))
    sys.exit(1 if resultados and any(r["estado"] == "no cumple" for r in resultados["resultados"]) else 0)


def _imprimir_solo_pdf(pdfm):
    fake = {"documento": pdfm["documento"], "secciones": [], "grupos": [], "estilos": [], "no_medible": []}
    imprimir(fake, pdfm)


def _hay_medidas(ruta, equipo):
    try:
        import medidas as M
        return bool(M.leer_medidas_yaml(ruta, equipo)[0])
    except SystemExit:
        raise
    except Exception:  # noqa: BLE001
        return False


if __name__ == "__main__":
    main()
