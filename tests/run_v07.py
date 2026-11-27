#!/usr/bin/env python3
"""Pruebas sembradas de la versión 0.7.0 (sin red salvo --con-red): título concreto, fuentes con niveles, verificación de normas
ISO/IEC, modo de estudio `repasar` y posición del número de página.

Uso: python -I tests/run_v07.py [--con-red]
  titulo           diagnóstico (sigla, método que sobra, promesas, cifras), título multilínea de la portada, CON-021 e INS-010 (`titulo:`)
  niveles          clasificación A-E de referencias tipo, pirámide, INS-008 con `arbitradas: true`, FUE-V4N
  fuentes-docx     `fuentes --desde-docx` con respuestas simuladas de Crossref/OpenAlex (DOI del documento, DOI por título, rechazo
                   de coincidencias débiles, sin red)
  normas-iso       verificación con una vista previa VDE sintética (PDF generado aquí): verificado, difiere, año distinto, sin vista previa
  repasar          estructura del repaso, sin puntaje ni veredicto, --seccion
  paginacion       --paginacion pie-derecha|pie-centro|pie|encabezado-derecha, `formato.paginacion.posicion` (INS-006, EST-010, APA-008)
  --con-red        ISO/IEC 25010:2023 y 25059:2023 contra la vista previa oficial de VDE (necesita red)
Código de salida 0 solo si todo pasa.
"""
import contextlib
import io
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "skills" / "fuentes-academicas" / "scripts"))
sys.path.insert(0, str(ROOT / "tests" / "estructura"))
CACHE = tempfile.mkdtemp(prefix="v07cache")
os.environ["EDITORIAL_CACHE"] = CACHE  # antes de importar fuentes: su caché HTTP sale de datos.dir_cache()

import docx  # noqa: E402
from docx.enum.text import WD_ALIGN_PARAGRAPH  # noqa: E402
from docx.shared import Pt  # noqa: E402

import auditar  # noqa: E402
import congruencia  # noqa: E402
import corregir  # noqa: E402
import fuentes as F  # noqa: E402
import institucional  # noqa: E402
import maquetacion  # noqa: E402
import niveles  # noqa: E402
import normas_iso  # noqa: E402
import titulo as T  # noqa: E402
import crear_ith  # noqa: E402
import crear_maquetacion  # noqa: E402

PERFIL_ITE = (ROOT / "perfiles" / "instituto-ejemplo-protocolo.editorial.yaml").read_text(encoding="utf-8")
PY = [sys.executable, "-I", str(ROOT / "scripts" / "editorial.py")]


def doc_portada(destino, titulo_lineas, objetivo, extra_pre=()):
    """Documento mínimo: portada (centrada), salto, «Objetivo general» y su texto."""
    d = docx.Document()
    for t in ("SISTEMA TECNOLÓGICO NACIONAL (EJEMPLO)", "INSTITUTO TECNOLÓGICO DE EJEMPLO", "MC. Ana Pérez López", *titulo_lineas,
              "Protocolo de Investigación para la asignatura Taller de Investigación I", *extra_pre,
              "Integrantes: Luis Gómez Ruiz (control 21330002)", "Ciudad Ejemplo, Estado, noviembre de 2026"):
        p = d.add_paragraph(t)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    d.add_page_break()
    d.add_heading("3. OBJETIVOS Y METAS", 1)
    d.add_heading("3.1. Objetivo general", 2)
    d.add_paragraph(objetivo)
    d.save(str(destino))
    return str(destino)


def prueba_titulo(tmp):
    fallas = []
    ok = "TUTOR-AI: tutor musical con inteligencia artificial para apoyar la enseñanza de la música"
    r = T.diagnosticar(ok)
    if r["palabras"] != 13 or r["nombre_proyecto"] != "TUTOR-AI" or r["observaciones"]:
        fallas.append(f"título correcto: {r['palabras']} palabras, nombre {r['nombre_proyecto']}, observaciones {r['observaciones']}")
    mal = "tutor musical generativo en español con LoRA y Gemma 3 para mejorar la enseñanza, comparando prompting y notación ABC mediante RAG"
    r = T.diagnosticar(mal)
    sobran = {s["texto"].lower() for s in r["sobran"]}
    if not {"lora", "gemma 3", "comparando", "prompting", "abc", "mediante", "rag"} <= sobran:
        fallas.append(f"detalles que sobran mal detectados: {sorted(sobran)}")
    if not any("mejorar" in p for p in r["promesas"]) or r["nombre_proyecto"] is not None or r["palabras"] <= 15:
        fallas.append(f"promesa/sigla/extensión: promesas {r['promesas']} nombre {r['nombre_proyecto']} palabras {r['palabras']}")
    r = T.diagnosticar("Sistema para garantizar 30 % menos errores en el inventario de microempresas", cfg={"sobran": ["microempresas"]})
    if not r["promesas"] or not r["cifras"] or not any(s["texto"] == "microempresas" for s in r["sobran"]):
        fallas.append(f"garantizar/cifra/titulo_config: {r['promesas']} {r['cifras']} {r['sobran']}")
    # título en varias líneas, docente y leyenda fuera del título
    obj = ("Desarrollar un tutor musical con inteligencia artificial que apoye la enseñanza de la música a estudiantes de secundaria "
           "mediante explicaciones de teoría musical.")
    p1 = doc_portada(pathlib.Path(tmp) / "t1.docx", ["TUTOR-AI: TUTOR MUSICAL CON INTELIGENCIA", "ARTIFICIAL PARA APOYAR LA ENSEÑANZA", "DE LA MÚSICA"], obj)
    d = T.leer(p1)
    esperado = "TUTOR-AI: TUTOR MUSICAL CON INTELIGENCIA ARTIFICIAL PARA APOYAR LA ENSEÑANZA DE LA MÚSICA"
    if d["titulo"] != esperado:
        fallas.append(f"título multilínea: {d['titulo']!r}")
    if not d["objetivo"] or not d["objetivo"].startswith("Desarrollar un tutor"):
        fallas.append(f"objetivo general: {d['objetivo']!r}")
    # CON-021: coherente -> nada; título con términos ajenos al objetivo -> hallazgo menor
    if [h for h in congruencia.revisar(p1)["hallazgos"] if h["id"] == "CON-021"]:
        fallas.append("CON-021 falso positivo en título coherente con el objetivo")
    p2 = doc_portada(pathlib.Path(tmp) / "t2.docx", ["SIPROD: SISTEMA DE LOGÍSTICA FERROVIARIA PARA PUERTOS", "CARGUEROS DE SINALOA"], obj)
    h = [x for x in congruencia.revisar(p2)["hallazgos"] if x["id"] == "CON-021"]
    if len(h) != 1 or h[0]["severidad"] != "menor" or "log" not in h[0]["evidencia"].lower():
        fallas.append(f"CON-021 sembrado: {h}")
    # INS-010 por título fijado en .editorial.yaml
    base = pathlib.Path(tmp) / "fijo"
    base.mkdir()
    for k, (fijo, hay) in enumerate([("Sistema web progresivo para la gestión de inventarios en microempresas de Ciudad Ejemplo", False),
                                     ("Sistema web para inventarios", True)]):
        carpeta = base / f"c{k}"
        carpeta.mkdir()
        (carpeta / ".editorial.yaml").write_text(PERFIL_ITE.replace("  titulo_max_palabras: 20", "  anio_actual: 2026\n  titulo_max_palabras: 20")
                                                 + f'\ntitulo: "{fijo}"\n', encoding="utf-8")
        doc = str(crear_ith.crear(carpeta / "protocolo.docx", False, ()))
        r = auditar.auditar(doc, "apa7")
        ins = [x for x in r["hallazgos"] if x["id"] == "INS-010"]
        if bool(ins) != hay or (hay and "no coincide" not in ins[0]["evidencia"]):
            fallas.append(f"INS-010 titulo fijo ({fijo!r}): {[x['evidencia'] for x in ins]} otros {[x['id'] for x in r['hallazgos']]}")
    # CLI: --opcion y --json
    j = pathlib.Path(tmp) / "t.json"
    r = subprocess.run(PY + ["titulo", p1, "--opcion", ok, "--json", str(j)], capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0 or not j.exists() or len(json.loads(j.read_text(encoding="utf-8"))["opciones"]) != 1:
        fallas.append(f"CLI titulo: código {r.returncode} {r.stderr[-200:]}")
    return fallas


def referencias_docx(destino, cuerpo, refs, formato=None):
    d = docx.Document()
    d.add_heading("Introducción", 1)
    for t in cuerpo:
        d.add_paragraph(t)
    d.add_heading("Referencias", 1)
    for r in refs:
        p = d.add_paragraph(r)
        p.paragraph_format.left_indent = Pt(36)
        p.paragraph_format.first_line_indent = Pt(-36)
    d.save(str(destino))
    return str(destino)


def prueba_niveles(tmp):
    fallas = []
    casos = [
        ("International Organization for Standardization. (2023). ISO/IEC 25010:2023. Systems and software engineering. https://www.iso.org/standard/78176.html", "A"),
        ("Secretaría de Economía. (2015). NOM-151-SCFI-2016, Requisitos que deben observarse para la conservación de mensajes de datos. Diario Oficial.", "A"),
        ("Smith, J. (2022). Deep learning for music. Journal of Music AI, 12(3), 45-67. https://doi.org/10.1000/xyz", "A"),
        ("Lee, K. (2023). Music tutoring. In Proceedings of the 15th International Conference on Music (pp. 1-8). ACM. https://doi.org/10.1145/123", "A"),
        ("Creswell, J. W. (2018). Designing and conducting mixed methods research (3rd ed.). SAGE Publications.", "B"),
        ("Müller, M. (2015). Fundamentals of music processing. Springer.", "B"),
        ("Ley Federal del Derecho de Autor. (1996, 24 de diciembre). Diario Oficial de la Federación.", "C"),
        ("UNESCO. (2023). Guía para el uso de la IA generativa en educación. https://www.unesco.org/es/articles/guia", "C"),
        ("Google. (2026). Gemma 4 model card. Google AI for Developers. https://ai.google.dev/gemma/docs/core/model_card", "D"),
        ("abcjs. (s. f.). abcjs: Rendering ABC music notation [Software]. https://www.abcjs.net", "D"),
        ("Wikipedia. (2024). Large language model. https://en.wikipedia.org/wiki/Large_language_model", "E"),
        ("Vaswani, A. (2017). Attention is all you need. arXiv. https://arxiv.org/abs/1706.03762", "E"),
        ("Autor Anónimo. (2023). Cómo entrenar modelos. https://miblog.medium.com/como-entrenar", "E"),
    ]
    import refs_csl
    for texto, esperado in casos:
        it = refs_csl.parsear_lista([texto])[0]
        n = niveles.clasificar(it, texto)
        if n["nivel"] != esperado or not n["motivo"] or n["peso"] != niveles.PESOS[esperado]:
            fallas.append(f"nivel de «{texto[:50]}…»: {n['nivel']} ({n['motivo']}), esperado {esperado}")
    # tipos de Crossref y OpenAlex mandan sobre el texto
    if niveles.clasificar({"title": "x", "DOI": "10.1/a", "_verificacion": {"crossref_type": "posted-content"}})["nivel"] != "E":
        fallas.append("posted-content debe ser E")
    if niveles.clasificar({"title": "x", "DOI": "10.1/a", "_verificacion": {"crossref_type": "book-chapter"}})["nivel"] != "B":
        fallas.append("book-chapter debe ser B")
    if niveles.clasificar({"title": "x", "DOI": "10.1/a", "_verificacion": {"openalex_source_type": "journal"}})["nivel"] != "A":
        fallas.append("OpenAlex journal debe ser A")
    if niveles.piramide(["A", "A", "E"]) != {"A": 2, "B": 0, "C": 0, "D": 0, "E": 1}:
        fallas.append("pirámide mal contada")
    # INS-008: con `arbitradas: true` solo cuentan A/B como recientes
    refs = ["Google. (2026). Gemma 4 model card. Google AI for Developers. https://ai.google.dev/gemma/docs/model_card",
            "Wikipedia. (2025). Modelo de lenguaje. https://es.wikipedia.org/wiki/Modelo_de_lenguaje",
            "OWASP Foundation. (2025). OWASP Top 10 for LLM applications. https://genai.owasp.org/llm-top-10/",
            "Smith, J. (2022). Deep learning for music. Journal of Music AI, 12(3), 45-67. https://doi.org/10.1000/xyz"]
    cuerpo = ["Texto de introducción sin citas para que el documento tenga cuerpo y no sea una lista pelada de referencias."]
    for k, (arb, hay) in enumerate([(False, False), (True, True)]):
        carpeta = pathlib.Path(tmp) / f"i8{k}"
        carpeta.mkdir()
        (carpeta / ".editorial.yaml").write_text(
            "perfil: apa7\nformato:\n  anio_actual: 2026\n  fuentes_recientes: {anios: 5, porcentaje: 70, arbitradas: " + ("true" if arb else "false") + "}\n",
            encoding="utf-8")
        doc = referencias_docx(carpeta / "d.docx", cuerpo, refs)
        r = auditar.auditar(doc, "apa7")
        h = [x for x in r["hallazgos"] if x["id"] == "INS-008"]
        if bool(h) != hay or (hay and "arbitradas (nivel A o B)" not in h[0]["evidencia"]):
            fallas.append(f"INS-008 arbitradas={arb}: {[x['evidencia'] for x in h]}")
    # FUE-V4N: afirmación sustantiva sostenida solo por documentación (D); con revista (A) no
    for k, (ref, hay) in enumerate([("Google. (2026). Gemma 4 model card. Google AI for Developers. https://ai.google.dev/gemma/docs/model_card", True),
                                    ("Smith, J. (2022). Deep learning for music. Journal of Music AI, 12(3), 45-67. https://doi.org/10.1000/xyz", False)]):
        autor, anio = ("Google", "2026") if hay else ("Smith", "2022")
        carpeta = pathlib.Path(tmp) / f"v4n{k}"
        carpeta.mkdir()
        (carpeta / ".editorial.yaml").write_text("perfil: apa7" + chr(10) + "fuentes:" + chr(10) + "  niveles: true" + chr(10), encoding="utf-8")
        doc = referencias_docx(carpeta / "d.docx", [f"El modelo mejora un 30 % el rendimiento en tareas de razonamiento musical según la evidencia ({autor}, {anio})."], [ref])
        r = auditar.auditar(doc, "apa7")
        h = [x for x in r["hallazgos"] if x["id"] == "FUE-V4N"]
        if bool(h) != hay or (hay and (h[0]["severidad"] != "menor" or "nivel D" not in h[0]["evidencia"])):
            fallas.append(f"FUE-V4N ({'D' if hay else 'A'}): {[x['evidencia'] for x in h]}")
    return fallas


# ---------------------------------------------------------------- fuentes --desde-docx con respuestas simuladas
class RedSimulada:
    """Sustituye fuentes.get: responde Crossref/OpenAlex con datos fijos (lo demás, 404)."""

    def __init__(self):
        self.llamadas = []

    def __call__(self, url, tries=3):
        self.llamadas.append(url)
        if "api.crossref.org/works/10.1000/xyz" in url:
            return {"message": {"DOI": "10.1000/xyz", "type": "journal-article", "title": ["Deep learning for music"],
                                "author": [{"family": "Smith", "given": "J."}], "container-title": ["Journal of Music AI"],
                                "issued": {"date-parts": [[2022]]}, "volume": "12", "issue": "3", "page": "45-67", "ISSN": ["1234-5678"],
                                "abstract": "<jats:p>We study music tutoring.</jats:p>"}}
        if "api.crossref.org/works/10.2000/abc" in url:
            return {"message": {"DOI": "10.2000/abc", "type": "book-chapter", "title": ["Usability evaluation in industry"],
                                "author": [{"family": "Jordan", "given": "P."}], "container-title": ["Handbook"],
                                "issued": {"date-parts": [[1996]]}}}
        if "api.crossref.org/works?" in url and "query.bibliographic" in url:
            if "Attention" in url or "Attention" in urllib_unquote(url):
                return {"message": {"items": [{"DOI": "10.3000/attn", "title": ["Attention is all you need"],
                                               "author": [{"family": "Vaswani"}], "issued": {"date-parts": [[2017]]}}]}}
            if "Rutas" in urllib_unquote(url):   # mismo título, otro autor: no se acepta
                return {"message": {"items": [{"DOI": "10.4000/otro", "title": ["Rutas de la investigación cuantitativa y mixta"],
                                               "author": [{"family": "Pérez"}], "issued": {"date-parts": [[2014]]}}]}}
            return {"message": {"items": []}}
        if "api.crossref.org/works/10.3000/attn" in url:
            return {"message": {"DOI": "10.3000/attn", "type": "proceedings-article", "title": ["Attention is all you need"],
                                "author": [{"family": "Vaswani", "given": "A."}], "container-title": ["NeurIPS"],
                                "issued": {"date-parts": [[2017]]}}}
        if "api.openalex.org/works/doi:10.1000/xyz" in url:
            return {"abstract_inverted_index": {"We": [0], "study": [1], "music": [2], "tutoring": [3]},
                    "primary_location": {"source": {"type": "journal"}}}
        if "api.openalex.org" in url:
            return {"abstract_inverted_index": None, "primary_location": {"source": {"type": "conference"}}}
        return None


def urllib_unquote(u):
    import urllib.parse
    return urllib.parse.unquote_plus(u)


def prueba_fuentes_docx(tmp):
    fallas = []
    refs = ["Smith, J. (2022). Deep learning for music. Journal of Music AI, 12(3), 45-67. https://doi.org/10.1000/xyz",
            "Jordan, P. (1996). Usability evaluation in industry. En Handbook (pp. 1-10). https://doi.org/10.2000/abc",
            "Vaswani, A. (2017). Attention is all you need. Conference on Neural Information Processing Systems.",
            "Hernández, R. (2014). Rutas de la investigación cuantitativa y mixta. McGraw-Hill.",
            "Google. (2026). Gemma 4 model card. Google AI for Developers. https://ai.google.dev/gemma/docs/model_card",
            "Pérez Pérez, A. (2025). Doi inexistente. Revista Falsa, 1(1), 1-2. https://doi.org/10.9999/noexiste"]
    doc = referencias_docx(pathlib.Path(tmp) / "r.docx", ["Texto del cuerpo del documento con una cita (Smith, 2022)."], refs)
    previo = (F.get, F.SIN_RED, F.time.sleep)
    falsa = RedSimulada()
    F.get, F.SIN_RED, F.time.sleep = falsa, False, lambda s: None
    try:
        out = pathlib.Path(tmp) / "fuentes.json"
        items, rs = F.desde_docx(doc, out)
        if len(items) != 6 or rs["doi_en_documento"] != 3 or rs["doi_por_titulo"] != 1 or rs["doi_resuelto"] != 3 or rs["doi_no_resuelve"] != 1:
            fallas.append(f"conteos --desde-docx: {({k: v for k, v in rs.items() if k != 'sin_doi_motivos'})}")
        por_n = {i["_ref_n"]: i for i in items}
        if por_n[1].get("DOI", "").lower() != "10.1000/xyz" or por_n[1]["_nivel"]["nivel"] != "A" or "music tutoring" not in por_n[1].get("abstract", "").lower():
            fallas.append(f"ref 1 (DOI del documento): {por_n[1].get('DOI')} {por_n[1]['_nivel']} {por_n[1].get('abstract')}")
        if por_n[2]["_nivel"]["nivel"] != "B":
            fallas.append(f"ref 2 (capítulo): {por_n[2]['_nivel']}")
        if (por_n[3].get("DOI") or "").lower() != "10.3000/attn" or por_n[3]["_verificacion"].get("doi_encontrado_por") != "título + primer autor + año":
            fallas.append(f"ref 3 (DOI por título): {por_n[3].get('DOI')} {por_n[3].get('_verificacion')}")
        if por_n[4].get("DOI") or "primer autor" not in por_n[4]["_verificacion"].get("sin_doi_motivo", ""):
            fallas.append(f"ref 4 (coincidencia débil): {por_n[4].get('DOI')} {por_n[4].get('_verificacion')}")
        if por_n[5]["_nivel"]["nivel"] != "D":
            fallas.append(f"ref 5 (documentación): {por_n[5]['_nivel']}")
        if por_n[6]["_verificacion"].get("estado") != "falla" or "no resuelve" not in por_n[6]["_verificacion"].get("motivo", ""):
            fallas.append(f"ref 6 (DOI inexistente): {por_n[6]['_verificacion']}")
        ids = [i["id"] for i in items]
        if len(set(ids)) != len(ids) or "smith2022" not in ids:
            fallas.append(f"ids: {ids}")
        # V5 sobre el Word con ese fuentes.json: usa los resúmenes del archivo, sin red
        import afirmaciones
        res = afirmaciones.extraer_docx(doc, red=False, fuentes=json.loads(out.read_text(encoding="utf-8")))
        if not res or res[0]["ids"] != ["smith2022"] or "music tutoring" not in res[0]["resumenes"]["smith2022"].lower():
            fallas.append(f"V5 con fuentes.json: {[(r['ids'], list(r['resumenes'])) for r in res]}")
    finally:
        F.get, F.SIN_RED, F.time.sleep = previo
    # sin red: no se inventa nada; los DOI del documento quedan sin comprobar, no «verificados»
    previo = (F.CACHE_HTTP, F.SIN_RED, F.time.sleep)
    with tempfile.TemporaryDirectory() as t2:
        F.CACHE_HTTP, F.SIN_RED, F.time.sleep = pathlib.Path(t2), True, lambda s: None
        try:
            items, rs = F.desde_docx(doc, None)
            if rs["doi_resuelto"] or rs["sin_red"] != 3 or any(i.get("_verificacion", {}).get("estado") == "verificado" for i in items):
                fallas.append(f"sin red: {({k: v for k, v in rs.items() if k != 'sin_doi_motivos'})}")
            if len(rs["piramide"]) != 5 or sum(rs["piramide"].values()) != 6:
                fallas.append(f"pirámide sin red: {rs['piramide']}")
        finally:
            F.CACHE_HTTP, F.SIN_RED, F.time.sleep = previo
    return fallas


# ---------------------------------------------------------------- normas ISO con PDF sintético
def pdf_sintetico(lineas):
    """PDF mínimo de una página con cada (y, texto) en su posición; legible con pdftotext y PyMuPDF."""
    contenido = ["BT /F1 12 Tf"]
    for y, t in lineas:
        contenido.append(f"1 0 0 1 72 {y} Tm ({t}) Tj")
    contenido.append("ET")
    stream = "\n".join(contenido).encode("latin-1")
    objs = [b"<< /Type /Catalog /Pages 2 0 R >>", b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
            b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    out, pos = b"%PDF-1.4\n", []
    for i, o in enumerate(objs, 1):
        pos.append(len(out))
        out += f"{i} 0 obj\n".encode() + o + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode()
    out += b"".join(f"{p:010d} 00000 n \n".encode() for p in pos)
    out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return out


PDF_25010 = pdf_sintetico([(780, "INTERNATIONAL ISO/IEC"), (764, "STANDARD 25010"), (720, "Second edition"), (706, "2023-11"),
                           (660, "Systems and software engineering --"), (646, "Systems and software Quality"), (632, "Requirements and Evaluation"),
                           (618, "(SQuaRE) -- Product quality model"), (570, "Ingenierie des systemes et du logiciel -- Exigences de qualite"),
                           (500, "Reference number"), (486, "ISO/IEC 25010:2023(E)")])


def prueba_normas_iso(tmp, con_red):
    fallas = []
    leer = normas_iso.texto_pdf(PDF_25010)
    if leer is None:
        print("SALTADA: ni pdftotext ni PyMuPDF para leer el PDF sintético; normas-iso sin ejecutar")
        return fallas
    p = normas_iso.leer_portada(leer)
    if (p.get("numero"), p.get("anio"), p.get("edicion"), p.get("fecha")) != ("25010", "2023", 2, "2023-11") or "Product quality model" not in p.get("titulo", ""):
        fallas.append(f"portada del PDF sintético mal leída: {p}")
    pedidos = []

    def falso(url, tiempo=30):
        pedidos.append(url)
        if "iso.org" in url:
            return 403, None
        if "info_isoiec25010%7Bed2.0%7Den.pdf" in url:
            return 200, PDF_25010
        return 404, None
    previo, previo_url = normas_iso.descargar, F.url_resuelve
    normas_iso.descargar = falso
    F.url_resuelve = lambda url: "no verificable"   # iso.org no deja comprobar la URL (y la prueba no usa red)
    try:
        base = {"type": "standard", "author": [{"literal": "International Organization for Standardization"}], "issued": {"date-parts": [[2023]]},
                "title": "Systems and software engineering. Systems and software Quality Requirements and Evaluation (SQuaRE). Product quality model",
                "number": "ISO/IEC No. 25010:2023", "URL": "https://www.iso.org/standard/78176.html"}
        for nombre, mod, estado, buscar in [
                ("verificada", {}, "verificado", None),
                ("título distinto", {"title": "Recetas de cocina para pasteles"}, "difiere", "título"),
                ("año distinto", {"number": "ISO/IEC No. 25010:2011", "issued": {"date-parts": [[2011]]}}, "no_verificado", "no coincide con las ediciones"),
                ("sin vista previa", {"number": "ISO/IEC No. 99999:2020", "URL": "https://www.iso.org/standard/1.html"}, "no_verificado", "no se pudo leer una portada oficial")]:
            # cada caso con su propia caché de PDF (la caché de normas persiste entre casos)
            os.environ["EDITORIAL_CACHE"] = tempfile.mkdtemp(prefix="v07n", dir=tmp)
            it = {**base, **mod}
            pedidos.clear()
            r = F.verificar_item(it)
            v = r.get("_verificacion", {})
            if v.get("estado") != estado:
                fallas.append(f"ISO {nombre}: estado {v.get('estado')} (esperado {estado}) {v}")
                continue
            if estado == "verificado":
                if v.get("fuente_verificacion") != "vde-preview" or v.get("norma") != "ISO/IEC 25010:2023" or "2023-11" not in (v.get("edicion") or "") \
                        or not r["ok"] or r["estado"] != "verificado" or not r["v1"]:
                    fallas.append(f"ISO verificada: {v} ok={r['ok']} estado={r['estado']}")
                if not pedidos[0].startswith("https://www.iso.org/") or not any("assets.vde-verlag.de" in u and "%7Bed1.0%7D" in u for u in pedidos):
                    fallas.append(f"orden de fuentes: {pedidos}")
            elif estado == "difiere":
                if r["ok"] or "título" not in r["v2"]:
                    fallas.append(f"ISO título distinto: ok={r['ok']} v2={r['v2']}")
            elif buscar not in (v.get("motivo") or ""):
                fallas.append(f"ISO {nombre}: motivo {v.get('motivo')!r} sin «{buscar}»")
            if estado == "no_verificado" and r.get("estado") != "no_verificado":
                fallas.append(f"ISO {nombre}: el resultado de verificar_item debe quedar no_verificado, no {r.get('estado')}")
        # el DOI de un artículo que solo menciona la norma no se trata como norma
        art = {"type": "article-journal", "title": "A study of ISO/IEC 25010:2011 quality models", "author": [{"family": "Lee"}]}
        if normas_iso.detectar(art) is not None:
            fallas.append("un artículo que menciona la norma se detectó como norma")
        # sin red: solo caché; sin caché, no_verificado con motivo (nunca «verificado»)
        os.environ["EDITORIAL_CACHE"] = tempfile.mkdtemp(prefix="v07n", dir=tmp)
        r = normas_iso.verificar(normas_iso.detectar({**base}), sin_red=True)
        if r["estado"] != "no_verificado" or "sin red" not in (r["motivo"] or ""):
            fallas.append(f"ISO sin red: {r}")
    finally:
        normas_iso.descargar, F.url_resuelve = previo, previo_url
    if con_red:
        for num, anio, ed, fecha in (("25010", "2023", 2, "2023-11"), ("25059", "2023", 1, "2023-06")):
            os.environ["EDITORIAL_CACHE"] = tempfile.mkdtemp(prefix="v07r", dir=tmp)
            it = {"type": "standard", "author": [{"literal": "ISO/IEC"}], "title": "ISO/IEC " + num, "number": f"ISO/IEC {num}:{anio}", "issued": {"date-parts": [[int(anio)]]}}
            v = normas_iso.verificar(normas_iso.detectar(it))
            if v["estado"] != "verificado" or not (v["edicion"] or "").endswith(fecha) or not v["fuente_verificacion"]:
                fallas.append(f"ISO/IEC {num}:{anio} con red: {v}")
            else:
                print(f"  con red: ISO/IEC {num}:{anio} verificada con {v['fuente_verificacion']} ({v['edicion']})")
    return fallas


# ---------------------------------------------------------------- repasar
def prueba_repasar(tmp):
    import repasar
    fallas = []
    carpeta = pathlib.Path(tmp) / "rep"
    carpeta.mkdir()
    (carpeta / ".editorial.yaml").write_text(PERFIL_ITE, encoding="utf-8")
    doc = str(crear_ith.crear(carpeta / "protocolo.docx", False, ()))
    r = repasar.repasar(doc, "protocolo-instituto-ejemplo")
    caps = {c["n"]: c for c in r["capitulos"]}
    if 0 not in caps or not {1, 2, 3, 12} <= set(caps):
        fallas.append(f"capítulos del repaso: {sorted(caps)}")
    obj = next((s for c in r["capitulos"] for s in c["secciones"] if s["nombre"] == "Objetivo general"), None)
    if not obj or not obj["pide_la_guia"] or obj["tiene"] is None or not obj["preguntas"] or "3.1" not in (obj["encabezado"] or ""):
        fallas.append(f"sección «Objetivo general»: {obj}")
    texto = json.dumps(r, ensure_ascii=False).lower()
    if any(k in texto for k in ('"puntaje"', '"veredicto"', '"total"', '"banda"')):
        fallas.append("el repaso no debe traer puntaje ni veredicto")
    j = pathlib.Path(tmp) / "rep.json"
    p = subprocess.run(PY + ["repasar", doc, "--seccion", "3", "--json", str(j)], capture_output=True, text=True, encoding="utf-8", cwd=carpeta)
    if p.returncode != 0 or "no para calificar" not in p.stdout or "CAPÍTULO 3" not in p.stdout or "CAPÍTULO 4" in p.stdout:
        fallas.append(f"CLI repasar --seccion 3: código {p.returncode} {p.stderr[-200:]}")
    p = subprocess.run(PY + ["repasar", doc, "--seccion", "99"], capture_output=True, text=True, encoding="utf-8", cwd=carpeta)
    if p.returncode != 2:
        fallas.append(f"repasar --seccion 99 debe salir con 2, salió {p.returncode}")
    p = subprocess.run(PY + ["repasar", doc, "--seccion", "objetivo general"], capture_output=True, text=True, encoding="utf-8", cwd=carpeta)
    if p.returncode != 0 or "Objetivo general" not in p.stdout:
        fallas.append("repasar --seccion por nombre")
    return fallas


# ---------------------------------------------------------------- paginación
def prueba_paginacion(tmp):
    fallas = []
    carpeta = pathlib.Path(tmp) / "pg"
    carpeta.mkdir()
    yml = PERFIL_ITE.replace("  titulo_max_palabras: 20", "  anio_actual: 2026\n  titulo_max_palabras: 20")
    (carpeta / ".editorial.yaml").write_text(yml, encoding="utf-8")
    doc = str(crear_ith.crear(carpeta / "protocolo.docx", False, ()))
    esperado = {"pie-derecha": ("pie", "derecha"), "pie-centro": ("pie", "centro"), "pie": ("pie", "centro"),
                "encabezado-derecha": ("encabezado", "derecha"), "encabezado": ("encabezado", "derecha")}
    for modo, (lugar, lado) in esperado.items():
        out = carpeta / f"{modo}.docx"
        with contextlib.redirect_stdout(io.StringIO()):
            corregir.corregir(doc, "apa7", str(out), None, silencioso=True, paginacion=modo)
        pos = set(institucional.lugar_numero(auditar.abrir_docx(str(out))))
        if pos != {(lugar, lado)}:
            fallas.append(f"--paginacion {modo}: número en {pos} (esperado {(lugar, lado)})")
    # un pie que ya tiene el número centrado pasa a la derecha con pie-derecha, y `pie` no toca su alineación
    d = docx.Document(str(carpeta / "pie-centro.docx"))
    for modo, lado in (("pie-derecha", "derecha"), ("pie", "centro")):
        out = carpeta / f"re-{modo}.docx"
        with contextlib.redirect_stdout(io.StringIO()):
            corregir.corregir(str(carpeta / "pie-centro.docx"), "apa7", str(out), None, silencioso=True, paginacion=modo)
        pos = set(institucional.lugar_numero(auditar.abrir_docx(str(out))))
        if pos != {("pie", lado)}:
            fallas.append(f"re-{modo}: {pos}")
    # INS-006 con `posicion` declarada; APA-008 pasa a excepción; sin ella, no se exige lugar
    for posicion, doc_ok, doc_mal in (("pie_derecha", "pie-derecha.docx", "pie-centro.docx"), ("pie_centro", "pie-centro.docx", "pie-derecha.docx"),
                                      ("encabezado_derecha", "encabezado-derecha.docx", "pie-derecha.docx")):
        (carpeta / ".editorial.yaml").write_text(yml.replace("cuerpo: arabigos}", f"cuerpo: arabigos, posicion: {posicion}}}"), encoding="utf-8")
        for nombre, hay in ((doc_ok, False), (doc_mal, True)):
            r = auditar.auditar(str(carpeta / nombre), "apa7")
            h = [x for x in r["hallazgos"] if x["id"] == "INS-006"]
            if bool(h) != hay:
                fallas.append(f"INS-006 posicion={posicion} en {nombre}: {[x['evidencia'] for x in h]}")
            if posicion != "encabezado_derecha" and any(x["id"] == "APA-008" for x in r["hallazgos"]):
                fallas.append(f"APA-008 debe ser excepción con posicion={posicion} en {nombre}")
    # `corregir` sin --paginacion usa la posición declarada
    (carpeta / ".editorial.yaml").write_text(yml.replace("cuerpo: arabigos}", "cuerpo: arabigos, posicion: pie_derecha}"), encoding="utf-8")
    out = carpeta / "declarada.docx"
    with contextlib.redirect_stdout(io.StringIO()):
        corregir.corregir(doc, "apa7", str(out), None, silencioso=True)
    if set(institucional.lugar_numero(auditar.abrir_docx(str(out)))) != {("pie", "derecha")}:
        fallas.append(f"corregir sin flag con posicion pie_derecha: {institucional.lugar_numero(auditar.abrir_docx(str(out)))}")
    if [x for x in auditar.auditar(str(out), "apa7")["hallazgos"] if x["id"] in ("INS-006", "APA-008", "EST-010")]:
        fallas.append("el documento corregido con la posición declarada debe quedar sin INS-006/APA-008/EST-010")
    # EST-010 (número en encabezado y pie) propone la posición declarada
    d = docx.Document(str(carpeta / "pie-derecha.docx"))
    sec = d.sections[1]
    sec.header.is_linked_to_previous = False
    crear_maquetacion.campo(sec.header.paragraphs[0], "PAGE")
    sec.footer.is_linked_to_previous = False
    crear_maquetacion.campo(sec.footer.paragraphs[0], "PAGE")
    dup = carpeta / "doble.docx"
    d.save(str(dup))
    h = [x for x in maquetacion.revisar(str(dup), "apa7") if x["id"] == "EST-010"]
    if not h or "pie derecha" not in h[0]["correccion"] or "--paginacion pie-derecha" not in h[0]["correccion"]:
        fallas.append(f"EST-010 con posicion declarada: {[x['correccion'] for x in h]}")
    # posición inválida: aviso, no error
    (carpeta / ".editorial.yaml").write_text(yml.replace("cuerpo: arabigos}", "cuerpo: arabigos, posicion: arriba}"), encoding="utf-8")
    r = auditar.auditar(doc, "apa7")
    if not any("posicion" in a for a in r["avisos"]):
        fallas.append("posicion inválida: falta el aviso")
    p = subprocess.run(PY + ["corregir", doc, "--paginacion", "diagonal"], capture_output=True, text=True, encoding="utf-8", cwd=carpeta)
    if p.returncode != 2:
        fallas.append(f"--paginacion inválida debe salir con 2, salió {p.returncode}")
    return fallas


def prueba_despachador():
    fallas = []
    r = subprocess.run(PY + ["--help"], capture_output=True, text=True, encoding="utf-8")
    for c in ("titulo", "repasar"):
        if c not in r.stdout:
            fallas.append(f"editorial.py --help no lista «{c}»")
    r = subprocess.run(PY + ["fuentes", "--help"], capture_output=True, text=True, encoding="utf-8")
    if "--desde-docx" not in r.stdout:
        fallas.append("fuentes --help no lista --desde-docx")
    return fallas


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    con_red = "--con-red" in sys.argv
    tmp = tempfile.mkdtemp(prefix="v07")
    pruebas = [("titulo", lambda: prueba_titulo(tmp)), ("niveles", lambda: prueba_niveles(tmp)),
               ("fuentes-docx", lambda: prueba_fuentes_docx(tmp)), ("normas-iso", lambda: prueba_normas_iso(tmp, con_red)),
               ("repasar", lambda: prueba_repasar(tmp)), ("paginacion", lambda: prueba_paginacion(tmp)), ("despachador", prueba_despachador)]
    total = 0
    try:
        for nombre, fn in pruebas:
            try:
                fallas = fn()
            except Exception as ex:  # noqa: BLE001
                import traceback
                fallas = [f"EXCEPCIÓN {type(ex).__name__}: {ex}\n{traceback.format_exc()[-600:]}"]
            for f in fallas:
                print("FALLA", nombre, "-", f)
            total += len(fallas)
            print(("OK   " if not fallas else "FALLA"), nombre)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        shutil.rmtree(CACHE, ignore_errors=True)
    print(f"== v0.7: {len(pruebas)} grupos, {total} fallas" + (" (con red)" if con_red else ""))
    sys.exit(1 if total else 0)


if __name__ == "__main__":
    main()
