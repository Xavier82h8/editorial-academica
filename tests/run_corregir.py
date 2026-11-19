#!/usr/bin/env python3
"""Prueba de scripts/corregir.py: tras corregir los *_errores de perfil apa7 desaparecen todos los hallazgos de las
reglas que corrige, no aparece ninguno nuevo y los *_correcto siguen en 0 hallazgos. Además un .docx sintético
(creado en un directorio temporal) con un caso de cada regla nueva: APA-028, 036, 043, 065, 093, 115, 145.

Uso: python -I tests/run_corregir.py
"""
import json
import pathlib
import shutil
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import auditar  # noqa: E402
import corregir  # noqa: E402
import maquetacion  # noqa: E402
import ooxml  # noqa: E402

from docx import Document  # noqa: E402
from docx.enum.text import WD_BREAK  # noqa: E402
from docx.oxml.ns import qn  # noqa: E402
from docx.shared import Inches, Pt  # noqa: E402

sys.path.insert(0, str(ROOT / "tests" / "ciegos"))
import asegurar  # noqa: E402
asegurar.asegurar("docs3", "docs")
DIRS = [ROOT / "tests" / "ciegos" / "docs3", ROOT / "tests" / "ciegos" / "docs"]
NUEVAS = ["APA-028", "APA-036", "APA-043", "APA-065", "APA-093", "APA-115", "APA-145"]


def _cuerpo(d, partes, sangria=0.5):
    """Párrafo de cuerpo; partes = [(texto, negrita, cursiva)] o un str."""
    p = d.add_paragraph()
    pf = p.paragraph_format
    pf.first_line_indent = Inches(sangria)
    pf.line_spacing = 2.0
    pf.space_before = pf.space_after = Pt(0)
    for x in ([(partes, False, False)] if isinstance(partes, str) else partes):
        r = p.add_run(x[0])
        r.bold, r.italic = x[1] or None, x[2] or None
    return p


def sintetico(path):
    d = Document()
    s = d.sections[0]
    s.top_margin = s.bottom_margin = s.left_margin = s.right_margin = Inches(1)
    for nombre in ("Normal", "Heading 1", "Heading 2", "Heading 3"):
        f = d.styles[nombre].font
        f.name, f.size, f.color.rgb = "Times New Roman", Pt(12), None
        rf = d.styles[nombre].element.get_or_add_rPr().get_or_add_rFonts()
        for a in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
            if rf.get(qn(a)) is not None:
                del rf.attrib[qn(a)]
        rf.set(qn("w:eastAsia"), "Times New Roman")
    d.styles["Normal"].paragraph_format.line_spacing = 2.0
    d.styles["Normal"].paragraph_format.space_after = Pt(0)
    # número de página en el encabezado
    hp = s.header.paragraphs[0]
    hp.alignment = 2
    corregir.poner_campo_pagina(hp._p)
    # portada
    for t in ("Modelos de lenguaje en la música", "Ana Pérez", "Universidad Ejemplo"):
        p = d.add_paragraph(t)
        p.alignment = 1
    d.paragraphs[0].runs[0].bold = True
    d.paragraphs[-1].add_run().add_break(WD_BREAK.PAGE)

    def enc(texto, nivel):
        p = d.add_heading(texto, level=nivel)
        p.paragraph_format.line_spacing = 2.0
        p.paragraph_format.space_before = p.paragraph_format.space_after = Pt(0)
        p.alignment = 1 if nivel == 1 else 0
        for r in p.runs:
            r.bold, r.italic = True, (True if nivel == 3 else None)
            r.font.color.rgb = None
        return p

    enc("Marco Teórico", 1)
    # APA-036: narrativa mal formada, partida en varios runs (uno en cursiva en medio)
    _cuerpo(d, [("Vaswani et al., 20", False, False), ("17, propusieron", False, False),
                (" la atención", False, True), (" como base del modelo.", False, False)])
    _cuerpo(d, "Smith & Jones, 2018, mostraron un efecto notable y López, 2019, confirmó el hallazgo en otro corpus.")
    # APA-043: orden alfabético (con «véase también»); APA-145/115: puntuación y espacios
    _cuerpo(d, "Los modelos grandes mejoran (Zhou et al., 2024; Zhao et al., 2025; véase también Wu, 2020; Adams, 2019) "
               "con datos propios y otros estudios lo apoyan (Smith & Jones, 2018; López, 2019).")
    _cuerpo(d, "El método se aplica.. La segunda parte usa uno,, dos;; tres, y así sucesivamente... Fin de párrafo.  "
               "Otra oración tras doble espacio.")
    _cuerpo(d, "La política institucional se detalla en la documentación (Amazon Web Services [AWS], 2023).")
    _cuerpo(d, "Como cita legal sin año aparece (art. 16, fr. VI) en la norma aplicable (Ley Federal del Derecho de Autor, 2020).")
    enc("Método", 2)
    enc("Diseño del Estudio", 3)
    # APA-028 / APA-029: encabezados en línea sin sangría (negrita / negrita cursiva solo en el tramo del encabezado)
    _cuerpo(d, [("Enfoque de entrenamiento.", True, False),
                (" El texto sigue en la misma línea y describe el procedimiento de entrenamiento con detalle.", False, False)],
            sangria=0.0)
    _cuerpo(d, [("Ajuste fino por etapas.", True, True),
                (" El texto continúa en el mismo párrafo y explica cada etapa del ajuste con suficiente extensión.", False, False)],
            sangria=0.0)
    # APA-093: tabla con rejilla
    for t, neg, cur in (("Tabla 1", True, False), ("Resultados por modelo", False, True)):
        p = d.add_paragraph()
        p.paragraph_format.line_spacing = 2.0
        p.paragraph_format.space_before = p.paragraph_format.space_after = Pt(0)
        r = p.add_run(t)
        r.bold, r.italic = neg or None, cur or None
    tb = d.add_table(rows=3, cols=2)
    tb.style = "Table Grid"
    for i, fila in enumerate((("Modelo", "Precisión"), ("A", "0.81"), ("B", "0.84"))):
        for j, v in enumerate(fila):
            c = tb.cell(i, j)
            c.paragraphs[0].text = v
    p = d.add_paragraph()
    p.paragraph_format.line_spacing = 2.0
    p.paragraph_format.space_before = p.paragraph_format.space_after = Pt(0)
    p.add_run("Nota.").italic = True
    p.add_run(" Elaboración propia.")
    p.paragraph_format.space_after = Pt(0)
    # referencias (APA-065: sigla en el autor grupal)
    p = d.add_heading("Referencias", level=1)
    p.alignment = 1
    p.paragraph_format.page_break_before = True
    p.paragraph_format.line_spacing = 2.0
    p.paragraph_format.space_before = p.paragraph_format.space_after = Pt(0)
    for r in p.runs:
        r.bold = True
        r.font.color.rgb = None
    refs = ["Adams, B. (2019). Aprendizaje automático aplicado. Editorial Uno.",
            "Amazon Web Services [AWS]. (2023). Guía del desarrollador. https://aws.example.com/guia",
            "Ley Federal del Derecho de Autor. (2020). Diario Oficial de la Federación. https://leyes.example.com/lfda",
            "López, C. (2019). Corpus musicales. Editorial Dos.",
            "Smith, J., & Jones, K. (2018). Efectos del entrenamiento. Editorial Tres.",
            "Vaswani, A., Shazeer, N., Parmar, N., Uszkoreit, J., Jones, L., Gomez, A., Kaiser, L., & Polosukhin, I. (2017). "
            "La atención es todo lo que necesitas. Editorial Cuatro.",
            "Wu, D. (2020). Modelos de lenguaje. Revista Cinco, 3(1), 1-9. doi:10.5555/wu.2020.1",
            "Zhao, H. (2025). Escalado de modelos. Editorial Seis.",
            "Zhou, Q. (2024). Datos propios. Editorial Siete."]
    for t in refs:
        e = d.add_paragraph(t)
        e.paragraph_format.left_indent = Inches(0.5)
        e.paragraph_format.first_line_indent = Inches(-0.5)
        e.paragraph_format.line_spacing = 2.0
        e.paragraph_format.space_before = e.paragraph_format.space_after = Pt(0)
    d.save(path)


def prueba_sintetico(tmp, fallos):
    src = tmp / "sintetico.docx"
    sintetico(str(src))
    ca = corregir.conteo(auditar.auditar(str(src), "apa7"))
    faltan = [x for x in NUEVAS if x not in ca]
    if faltan:
        fallos.append(f"sintético: el juez no reporta {faltan} antes de corregir: {ca}")
    r = corregir.corregir(str(src), "apa7", silencioso=True)
    cd = r["despues"]
    print(f"{'sintetico':<34} antes={dict(sorted(ca.items()))} después={dict(sorted(cd.items()))}")
    for x in NUEVAS:
        if x == "APA-036":
            if cd.get(x, 0) != 1:  # solo debe quedar la cita legal
                fallos.append(f"sintético: APA-036 debería quedar en 1 (cita legal), quedó {cd.get(x, 0)}")
        elif cd.get(x, 0):
            fallos.append(f"sintético: persiste {x} ({cd[x]})")
    nuevos = [x for x in cd if cd[x] > ca.get(x, 0)]
    if nuevos:
        fallos.append(f"sintético: hallazgos nuevos {nuevos}")
    # el formato de los runs se conserva y el texto queda como se espera
    d2 = Document(r["salida"])
    textos = [p.text for p in d2.paragraphs]
    esperados = ["Vaswani et al. (2017) propusieron la atención como base del modelo.",
                 "Smith y Jones (2018) mostraron un efecto notable y López (2019) confirmó el hallazgo",
                 "(Zhao et al., 2025; Zhou et al., 2024; véase también Adams, 2019; Wu, 2020)",
                 "El método se aplica. La segunda parte usa uno, dos; tres, y así sucesivamente... Fin de párrafo. Otra",
                 "Amazon Web Services. (2023)."]
    for e in esperados:
        if not any(e in t for t in textos):
            fallos.append(f"sintético: falta el texto corregido «{e}»")
    p0 = next(p for p in d2.paragraphs if p.text.startswith("Vaswani"))
    cur = [r_.text for r_ in p0.runs if r_.italic]
    if cur != [" la atención"]:
        fallos.append(f"sintético: la cursiva de los runs no se conservó: {cur}")
    leg = [p.text for p in d2.paragraphs if "art. 16, fr. VI" in p.text]
    if not leg:
        fallos.append("sintético: la cita legal fue tocada")
    for p in d2.paragraphs:
        if p.text.startswith(("Enfoque de entrenamiento.", "Ajuste fino por etapas.")):
            if abs(p.paragraph_format.first_line_indent.inches - 0.5) > 0.01:
                fallos.append(f"sintético: sin sangría 0.5 in en «{p.text[:25]}»")
            b = [r_.text for r_ in p.runs if r_.bold]
            if b != [p.runs[0].text]:
                fallos.append(f"sintético: negrita fuera del tramo del encabezado en «{p.text[:25]}»: {b}")
    # --solo: solo toca la regla pedida
    r2 = corregir.corregir(str(src), "apa7", out=str(tmp / "sintetico_solo.docx"), solo={"APA-145"}, silencioso=True)
    c2 = r2["despues"]
    if c2.get("APA-145", 0) or not c2.get("APA-043", 0) or not c2.get("APA-093", 0):
        fallos.append(f"sintético --solo APA-145: resultado inesperado {c2}")
    # idempotencia
    r3 = corregir.corregir(r["salida"], "apa7", out=str(tmp / "sintetico_2.docx"), silencioso=True)
    if any(v for v in r3["aplicadas"].values()) or r3["despues"] != cd:
        fallos.append(f"sintético: segunda pasada no es idempotente: {r3['aplicadas']}")


def _campos(parte):
    """(n PAGE, n NUMPAGES) en una parte de encabezado/pie (campos complejos y fldSimple)."""
    ins = [x.text or "" for x in parte._element.iter(qn("w:instrText"))] +           [f.get(qn("w:instr")) or "" for f in parte._element.iter(qn("w:fldSimple"))]
    return (sum(1 for i in ins if ooxml.tipo_campo(i) == "PAGE"), sum(1 for i in ins if ooxml.tipo_campo(i) == "NUMPAGES"))


def _pag_total(d):
    """{'h': PAGE en encabezados, 'f': PAGE en pies, 'n': NUMPAGES en todos} sobre las partes propias de cada sección."""
    r = {"h": 0, "f": 0, "n": 0}
    for s in d.sections:
        for h, f in ((s.header, s.footer), (s.first_page_header, s.first_page_footer)):
            for parte, k in ((h, "h"), (f, "f")):
                if not parte.is_linked_to_previous:
                    pg, nm = _campos(parte)
                    r[k] += pg
                    r["n"] += nm
    return r


def _textos(d):
    return [p.text for p in d.paragraphs]


def prueba_maquetacion(tmp, fallos):
    fx = ROOT / "tests" / "estructura" / "maquetacion.docx"
    if not fx.exists():
        fallos.append("falta tests/estructura/maquetacion.docx (crear_maquetacion.py)")
        return
    src = tmp / "maquetacion.docx"
    shutil.copy(fx, src)
    textos0 = _textos(Document(str(src)))
    ids0 = {h["id"] for h in maquetacion.revisar(str(src), "apa7")}
    if not {"EST-010", "EST-011", "EST-012", "EST-013", "EST-014", "EST-015"} <= ids0:
        fallos.append(f"maquetación: el fixture no dispara las 6 reglas: {sorted(ids0)}")
    res = {}
    for modo in (None, "pie", "ninguna"):
        out = tmp / f"maq_{modo or 'defecto'}.docx"
        r = corregir.corregir(str(src), "apa7", out=str(out), silencioso=True, paginacion=modo)
        res[modo] = r
        d = Document(str(out))
        t = _pag_total(d)
        cab = "".join(x.text for x in d.sections[0].header.paragraphs)
        esperado = {None: {"h": 1, "f": 0, "n": 0}, "pie": {"h": 0, "f": 1, "n": 0}, "ninguna": {"h": 0, "f": 0, "n": 0}}[modo]
        if t != esperado:
            fallos.append(f"maquetación --paginacion {modo}: campos {t} (esperado {esperado})")
        if "Protocolo de prueba" not in cab:
            fallos.append(f"maquetación --paginacion {modo}: se perdió el texto del encabezado: {cab!r}")
        if _textos(d) != textos0:
            fallos.append(f"maquetación --paginacion {modo}: cambió el texto de los párrafos")
        ids = {h["id"] for h in maquetacion.revisar(str(out), "apa7")}
        if ids & {"EST-010", "EST-011", "EST-012", "EST-013", "EST-014"}:
            fallos.append(f"maquetación --paginacion {modo}: persisten {sorted(ids)}")
        if "EST-015" not in ids:
            fallos.append(f"maquetación --paginacion {modo}: EST-015 debía quedar (no automático)")
        if "EST-015" not in r["no_auto"] or "EST-015" not in corregir.NO_AUTO:
            fallos.append("maquetación: EST-015 no figura en no_auto")
        if modo is None:
            if "APA-008" in {h["id"] for h in auditar.auditar(str(out), "apa7")["hallazgos"]}:
                fallos.append("maquetación: el fixture sigue con APA-008 tras corregir (texto + PAGE sin alineación derecha)")
            # tabla corta: filas cantSplit; tabla larga: tblHeader; rótulo/título keep_with_next
            tbls = d.tables
            if not all(tr._tr.find(qn("w:trPr") + "/" + qn("w:cantSplit")) is not None for tr in tbls[0].rows):
                fallos.append("maquetación: la tabla corta no tiene cantSplit en todas las filas")
            if tbls[1].rows[0]._tr.find(qn("w:trPr") + "/" + qn("w:tblHeader")) is None:
                fallos.append("maquetación: la tabla larga no tiene tblHeader")
            if any(tr._tr.find(qn("w:trPr") + "/" + qn("w:cantSplit")) is not None for tr in tbls[1].rows):
                fallos.append("maquetación: la tabla larga no debía recibir cantSplit")
            kn = {p.text: p.paragraph_format.keep_with_next for p in d.paragraphs}
            if not (kn.get("Tabla 1") and kn.get("Estudios previos") and kn.get("Tabla 2") and kn.get("Registro de pruebas")):
                fallos.append(f"maquetación: rótulo/título sin keep_with_next: {kn}")
            if kn.get("Fuente: elaboración propia"):
                fallos.append("maquetación: la nota no debía recibir keep_with_next")
            esp = next(p for p in d.paragraphs if p.text == "Resultados").paragraph_format.space_before
            if esp is None or abs(esp.pt - 24) > 0.1:
                fallos.append(f"maquetación: encabezado tras tabla sin espacio antes de 24 pt ({esp})")
            r2 = corregir.corregir(str(out), "apa7", out=str(tmp / "maq_2.docx"), silencioso=True)
            if any(v for v in r2["aplicadas"].values()) or r2["despues"] != r["despues"]:
                fallos.append(f"maquetación: segunda pasada no idempotente: {r2['aplicadas']}")
    print(f"{'maquetacion.docx':<34} antes={dict(sorted(res[None]['antes'].items()))} después={dict(sorted(res[None]['despues'].items()))}")
    # IEEE sin --paginacion no se toca: la rama se cubre con avisos (corregir devuelve None para base IEEE hoy)
    # EST-015: notas vagas sin cita disparan; con cita no
    d = Document()
    for nota in ("Nota. Elaboración propia a partir de las fuentes citadas.",
                 "Nota. Elaboración propia con base en las fuentes consultadas.",
                 "Nota. Elaboración propia con datos de Vaswani et al. (2017) y Devlin et al. (2018).",
                 "Nota. Elaboración propia a partir de las fuentes citadas en Vaswani et al. (2017)."):
        d.add_paragraph("Tabla 1")
        d.add_paragraph("Estudios previos")
        t = d.add_table(rows=2, cols=2)
        t.cell(0, 0).text, t.cell(0, 1).text, t.cell(1, 0).text, t.cell(1, 1).text = "Año", "Autor", "2017", "Vaswani"
        d.add_paragraph(nota)
        d.add_paragraph("Texto.")
    f = tmp / "notas.docx"
    d.save(str(f))
    n15 = [h["evidencia"] for h in maquetacion.revisar(str(f), "apa7") if h["id"] == "EST-015"]
    if len(n15) != 2 or not all("elaboración propia a partir" in e.lower() or "elaboración propia con base" in e.lower() for e in n15):
        fallos.append(f"EST-015 notas vagas: {n15}")


def _portada_estado(path):
    """(primera página distinta, [(PAGE, texto) de header, footer, first_page_header, first_page_footer])."""
    d = Document(str(path))
    s = d.sections[0]
    partes = []
    for x in (s.header, s.footer, s.first_page_header, s.first_page_footer):
        ins = [i.text or "" for i in x._element.iter(qn("w:instrText"))]
        partes.append((sum(1 for i in ins if ooxml.tipo_campo(i) == "PAGE"), "".join(p.text for p in x.paragraphs).strip()))
    return s.different_first_page_header_footer, partes


def prueba_portada(tmp, fallos):
    """--portada-numero no|si, su interacción con --paginacion, idempotencia y .editorial.yaml (portada_numero)."""
    sys.path.insert(0, str(ROOT / "tests" / "estructura"))
    import crear_maquetacion  # noqa: E402
    con = crear_maquetacion.portada(tmp / "p_con.docx", True)
    sin = crear_maquetacion.portada(tmp / "p_sin.docx", False)
    # (origen, portada_numero, paginacion, PAGE en [h, f, h1, f1], texto del running head en h1, texto en f1)
    casos = [(con, "no", None, [1, 0, 0, 0], "TITULO ABREVIADO", "Pie institucional"),
             (sin, "si", None, [1, 0, 1, 0], "TITULO ABREVIADO", ""),
             (con, "no", "pie", [0, 1, 0, 0], "TITULO ABREVIADO", "Pie institucional"),
             (sin, "si", "pie", [0, 1, 0, 1], "TITULO ABREVIADO", "Pie institucional"),
             (sin, None, None, [1, 0, 0, 0], "TITULO ABREVIADO", ""),
             (con, None, None, [1, 0, 0, 0], "", "")]
    for k, (src, pn, pag, pags, rh, pf1) in enumerate(casos):
        out = tmp / f"p_out{k}.docx"
        r = corregir.corregir(str(src), "apa7", out=str(out), silencioso=True, paginacion=pag, portada_numero=pn)
        dif, partes = _portada_estado(out)
        et = f"portada caso {k} ({src.name}, --portada-numero {pn}, --paginacion {pag})"
        if [x[0] for x in partes] != pags:
            fallos.append(f"{et}: PAGE por parte {[x[0] for x in partes]} (esperado {pags})")
        if pn and not dif:
            fallos.append(f"{et}: sin primera página distinta")
        if pn == "no" and (partes[2][1] != rh or partes[3][1] != pf1):
            fallos.append(f"{et}: running head/pie de la portada {partes[2][1]!r}/{partes[3][1]!r}")
        if pn == "si" and not partes[2][1].startswith(rh):
            fallos.append(f"{et}: se perdió el running head de la portada: {partes[2][1]!r}")
        if pn and any(v for k_, v in r["despues"].items() if k_ == "EST-016"):
            fallos.append(f"{et}: EST-016 persiste {r['despues']}")
        if pn is None and not pag and src is sin and r["despues"].get("EST-016") != 1:
            fallos.append(f"{et}: sin decisión la portada no se toca y EST-016 queda señalado: {r['despues']}")
        r2 = corregir.corregir(str(out), "apa7", out=str(tmp / f"p_out{k}b.docx"), silencioso=True, paginacion=pag, portada_numero=pn)
        if r2["aplicadas"] or _portada_estado(tmp / f"p_out{k}b.docx") != (dif, partes):
            fallos.append(f"{et}: segunda pasada no idempotente {r2['aplicadas']}")
    # .editorial.yaml con portada_numero: no -> es el valor por defecto de corregir
    carpeta = tmp / "p_yaml"
    carpeta.mkdir()
    (carpeta / ".editorial.yaml").write_text("perfil: apa7\nportada_numero: no\n", encoding="utf-8")
    shutil.copy(con, carpeta / "doc.docx")
    out = carpeta / "salida.docx"
    r = corregir.corregir(str(carpeta / "doc.docx"), "apa7", out=str(out), silencioso=True)
    if [x[0] for x in _portada_estado(out)[1]] != [1, 0, 0, 0] or r["despues"].get("EST-016"):
        fallos.append(f"portada con .editorial.yaml portada_numero: no: {_portada_estado(out)} {r['despues']}")
    if r["antes"].get("EST-016") != 1:
        fallos.append(f"portada con .editorial.yaml: EST-016 debía estar en antes: {r['antes']}")


def _doc_con_encabezado(path, instr):
    """.docx de una página cuyo encabezado lleva solo un campo (fldSimple) con la instrucción `instr`."""
    from docx.oxml import OxmlElement
    d = Document()
    d.add_paragraph("Texto de prueba.")
    par = d.sections[0].header.paragraphs[0]
    f = OxmlElement("w:fldSimple")
    f.set(qn("w:instr"), instr)
    par._p.append(f)
    d.save(str(path))
    return path


def prueba_numpages(tmp, fallos):
    """Un encabezado con solo NUMPAGES (o SECTIONPAGES) no cuenta como número de página (regex de palabra, no subcadena)."""
    for k, (instr, esperado) in enumerate(((" NUMPAGES ", False), (" SECTIONPAGES ", False), (" PAGE \\* MERGEFORMAT ", True))):
        doc = _doc_con_encabezado(tmp / f"np_{k}.docx", instr)
        con = Document(str(doc)).sections[0].header._element
        if ooxml.tiene_pagina(con) != esperado:
            fallos.append(f"PAGE por subcadena: {instr!r} -> tiene_pagina={not esperado}")
        r = auditar.auditar(str(doc), "apa7")
        tiene_008 = any(h["id"] == "APA-008" and "no tiene campo PAGE" in h["evidencia"] for h in r["hallazgos"])
        if tiene_008 == esperado:
            fallos.append(f"PAGE por subcadena: {instr!r} -> «sin campo PAGE» {'presente' if tiene_008 else 'ausente'}")
    src = _doc_con_encabezado(tmp / "np_fix.docx", " NUMPAGES ")
    out = tmp / "np_fix_out.docx"
    corregir.corregir(str(src), "apa7", out=str(out), silencioso=True)
    h = Document(str(out)).sections[0].header._element
    if not ooxml.tiene_pagina(h):
        fallos.append("corregir no añadió PAGE a un encabezado que solo tenía NUMPAGES")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    docs = 0
    ok_total, y_total, nuevos_total = 0, 0, 0
    fallos = []
    with tempfile.TemporaryDirectory() as tmp:
        tmp = pathlib.Path(tmp)
        for carpeta in DIRS:
            esperado = json.loads((carpeta / "esperado.json").read_text(encoding="utf-8"))
            for nombre, info in esperado.items():
                if info["perfil"] != "apa7":
                    continue
                es_error = "errores" in nombre
                etiqueta = f"{carpeta.name}/{nombre}"
                src = tmp / f"{carpeta.name}_{nombre}"
                shutil.copy(carpeta / nombre, src)
                antes = auditar.auditar(str(src), "apa7")
                r = corregir.corregir(str(src), "apa7", silencioso=True)
                if r is None:
                    fallos.append(f"{etiqueta}: corregir devolvió None")
                    continue
                docs += 1
                ca, cd = r["antes"], r["despues"]
                reglas = [x for x in ca if x in corregir.REGLAS and x not in corregir.PARCIALES]
                quedan = [x for x in reglas if cd.get(x, 0)]
                nuevos = [x for x in cd if cd[x] > ca.get(x, 0)]
                ok_total += len(reglas) - len(quedan)
                y_total += len(reglas)
                nuevos_total += len(nuevos)
                estado = "OK"
                if quedan:
                    estado = "FALLA"
                    fallos.append(f"{etiqueta}: persisten {quedan}")
                if nuevos:
                    estado = "FALLA"
                    fallos.append(f"{etiqueta}: hallazgos nuevos {nuevos}")
                if not es_error and cd:
                    estado = "FALLA"
                    fallos.append(f"{etiqueta}: el correcto ya no está en 0 hallazgos: {cd}")
                print(f"{etiqueta:<34} {estado:<5} antes={dict(sorted(ca.items()))} después={dict(sorted(cd.items()))}")
                if es_error:  # idempotencia: corregir lo ya corregido no cambia nada
                    r2 = corregir.corregir(r["salida"], "apa7", out=str(tmp / ("2_" + src.name)), silencioso=True)
                    if r2["aplicadas"] and any(v for v in r2["aplicadas"].values()):
                        fallos.append(f"{etiqueta}: segunda pasada vuelve a tocar {r2['aplicadas']}")
                        estado = "FALLA"
                    if r2["despues"] != cd:
                        fallos.append(f"{etiqueta}: segunda pasada cambia los hallazgos")
        prueba_sintetico(tmp, fallos)
        prueba_maquetacion(tmp, fallos)
        prueba_portada(tmp, fallos)
        prueba_numpages(tmp, fallos)
    for f in fallos:
        print("FALLO:", f)
    print(f"== corregir: {docs} docs, reglas corregidas {ok_total}/{y_total}, nuevos {nuevos_total}, sintético incluido")
    sys.exit(0 if not fallos and docs else 1)


if __name__ == "__main__":
    main()
