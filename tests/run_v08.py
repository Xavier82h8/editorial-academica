#!/usr/bin/env python3
"""Pruebas sembradas de la versión 0.8.0 (sin red salvo --con-red): portada y salida como función propia, cierre de fuentes.

Uso: python -I tests/run_v08.py [--con-red]
  reemplazar      `fuentes --reemplazar` con respuestas sintéticas de Crossref/OpenAlex: la versión publicada de la misma obra primero,
                  solo candidatas A/B, fragmento del resumen que coincide con la oración, sin red (aviso, no excepción), nunca aplica cambios
  fuentes-perfil  bloque `fuentes:` del perfil (FUE-NIV): fuente a evitar, referencias bajo el mínimo, porcentaje de arbitradas;
                  sin el bloque no hay hallazgos; los documentales no cuentan
  portada         `editorial.py portada`: campos del perfil, --campo, literal, [[PENDIENTE]], títulos largos, logos con hueco y aviso,
                  INS-010 e INS-015 sobre el resultado (código 1 con un número de control pendiente), el original intacto, sectPr conservado
  portada-medida  con LibreOffice: el espaciado se afina midiendo (error final <= 0.5 pt contra el modelo)
  indices         con LibreOffice: campo TOC real, listas de tablas y figuras con rótulos exactos, números visibles por sección
                  (romanos y arábigos) iguales a los del PDF; sin LibreOffice, código 2 con el mensaje de instalación
  entregar        con LibreOffice: docx y pdf juntos, capturas, resumen; EA-001 deja código 1; el original intacto
  despachador     editorial.py lista portada, indices y entregar
  --con-red       la oración de Hosen (2025) con la referencia arXiv real: devuelve candidatas A/B con resumen (necesita red)
Código de salida 0 solo si todo pasa. Las pruebas que necesitan LibreOffice o PyMuPDF se saltan con «SALTADA: …» si no están.
"""
import contextlib
import hashlib
import io
import json
import os
import pathlib
import shutil
import struct
import subprocess
import sys
import tempfile
import zlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "skills" / "fuentes-academicas" / "scripts"))
CACHE = tempfile.mkdtemp(prefix="v08cache")
os.environ["EDITORIAL_CACHE"] = CACHE

import docx  # noqa: E402
from docx.enum.text import WD_ALIGN_PARAGRAPH  # noqa: E402
from docx.oxml import OxmlElement  # noqa: E402
from docx.oxml.ns import qn  # noqa: E402
from docx.shared import Pt  # noqa: E402

import auditar  # noqa: E402
import fuentes as F  # noqa: E402
import libreoffice  # noqa: E402
import reemplazo_fuentes as R  # noqa: E402

PY = [sys.executable, "-I", str(ROOT / "scripts" / "editorial.py")]
HAY_LO = libreoffice.buscar() is not None
try:
    import fitz  # noqa: F401
    HAY_FITZ = True
except ImportError:
    HAY_FITZ = False


def correr(*args, env=None):
    r = subprocess.run(PY + [str(a) for a in args], capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
    return r.returncode, r.stdout + r.stderr


def sha(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


def png(ruta, w=40, h=20):
    """PNG mínimo de un color (sin Pillow)."""
    def chunk(t, d):
        c = struct.pack(">I", len(d)) + t + d
        return c + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    raw = b"".join(b"\x00" + bytes([30, 54, 93]) * w for _ in range(h))
    pathlib.Path(ruta).write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


# ---------------------------------------------------------------- reemplazar
ABSTRACT_PUB = ("Fine-tuning small models is popular. We show that fine-tuning does not guarantee improvement when the training data "
                "contain errors. We release our recipe.")


def _inv(texto):
    inv = {}
    for i, w in enumerate(texto.split()):
        inv.setdefault(w, []).append(i)
    return inv


def prueba_reemplazar(tmp):
    fallas = []
    oracion = "Además, ajustarlos no asegura una mejora cuando los datos de entrenamiento contienen errores (Hosen, 2025)."
    cita = "Hosen, M. M. (2025). Fine-tuning a 7B advisor on free-tier GPUs. arXiv. https://arxiv.org/abs/2504.15610"
    pub = {"DOI": "10.1000/pub.1", "title": ["Fine-tuning a 7B advisor on free-tier GPUs"], "type": "journal-article", "container-title": ["Journal of Tuning"],
           "author": [{"family": "Hosen", "given": "M. M."}], "issued": {"date-parts": [[2025]]}, "abstract": ABSTRACT_PUB}
    cr = {"10.1000/pub.1": pub,
          "10.1000/a.1": {"DOI": "10.1000/a.1", "title": ["Noisy labels and fine-tuning of language models"], "type": "journal-article", "container-title": ["J. ML"],
                          "author": [{"family": "Ruiz"}], "issued": {"date-parts": [[2024]]}, "abstract": "Training data with errors degrade results. Fine-tuning gives no guarantee of improvement."},
          "10.1000/b.1": {"DOI": "10.1000/b.1", "title": ["A book about data"], "type": "monograph", "author": [{"family": "Gil"}],
                          "issued": {"date-parts": [[2022]]}, "abstract": "Un libro general sobre datos."},
          "10.1000/e.1": {"DOI": "10.1000/e.1", "title": ["Blog sobre ajuste"], "type": "posted-content", "author": [{"family": "Pez"}],
                          "issued": {"date-parts": [[2025]]}, "abstract": "Fine-tuning errors"}}
    oa = [{"doi": "https://doi.org/10.1000/e.1", "title": "x", "abstract_inverted_index": None},
          {"doi": "https://doi.org/10.1000/b.1", "title": "x", "abstract_inverted_index": None},
          {"doi": "https://doi.org/10.1000/a.1", "title": "x", "abstract_inverted_index": _inv(cr["10.1000/a.1"]["abstract"])}]
    guardado = {k: getattr(F, k) for k in ("metadatos_doi", "integridad", "crossref", "openalex_buscar", "get", "get_texto", "doi_por_metadatos_motivo")}
    try:
        F.metadatos_doi = lambda doi: ({"title": "Fine-tuning a 7B advisor on free-tier GPUs", "author": [{"family": "Hosen"}], "year": 2025, "type": "posted-content",
                                       "relation": {}, "updated-by": [], "registro": "doi.org"} if "arxiv" in doi.lower() else
                                      {"title": "Noisy labels and fine-tuning of language models", "author": [{"family": "Ruiz"}], "year": 2024, "type": "journal-article",
                                       "relation": {}, "updated-by": [], "registro": "crossref"})
        F.integridad = lambda doi, meta: {"version_publicada": "10.1000/pub.1", "preprint": True, "avisos": [], "estado": "verificado"}
        F.crossref = lambda doi: cr.get(doi.lower().replace("https://doi.org/", ""))
        F.openalex_buscar = lambda q, n, desde, idioma, oa_, orden=None: oa
        F.get = lambda url, tries=3: {}
        F.get_texto = lambda url, tries=2: ""
        F.doi_por_metadatos_motivo = lambda it: (None, "sin coincidencia")
        r = R.proponer(F, oracion, cita, n=5)
        if r["tipo_original"] != "preprint":
            fallas.append(f"la referencia arXiv debe ser preprint, salió {r['tipo_original']}")
        vp = r["version_publicada"]
        if not vp or vp[0]["doi"] != "10.1000/pub.1" or not vp[0].get("misma_obra"):
            fallas.append(f"la versión publicada de la misma obra debe ir primero: {vp}")
        dois = [c["doi"] for c in r["candidatas"]]
        if dois != ["10.1000/a.1", "10.1000/b.1"]:
            fallas.append(f"candidatas: solo nivel A (revista) y B (libro), sin el preprint posted-content ni la propia obra; salió {dois}")
        else:
            c = r["candidatas"][0]
            if c["fragmento"] not in cr["10.1000/a.1"]["abstract"] or c["coincidencia"] < 0.5 or c["nivel"] != "A" or not c["resumen"]:
                fallas.append(f"fragmento/coincidencia/nivel de la candidata: {c['fragmento']!r} {c['coincidencia']} {c['nivel']}")
        idiomas = {q["idioma"] for q in r["consultas"]}
        if idiomas != {"es", "en"}:
            fallas.append(f"consultas en español e inglés: {r['consultas']}")
        en = next((q["consulta"] for q in r["consultas"] if q["idioma"] == "en"), "")
        if "fine-tuning" not in en or "training" not in en or "errors" not in en:
            fallas.append(f"consulta en inglés mal derivada: {en!r}")
        # una referencia que ya es de revista: sin versión publicada que buscar
        r2 = R.proponer(F, oracion, "Ruiz, A. (2024). Noisy labels and fine-tuning of language models. J. ML, 3(2), 1-10. https://doi.org/10.1000/a.1", n=5)
        if r2["tipo_original"] is not None or r2["version_publicada"]:
            fallas.append(f"un artículo de revista no es preprint/web: {r2['tipo_original']} {r2['version_publicada']}")
        # sin red: aviso, no excepción
        def sin_red(url, tries=3):
            raise OSError("sin red simulada")
        F.get = sin_red
        F.crossref = lambda doi: (_ for _ in ()).throw(OSError("sin red simulada"))
        F.openalex_buscar = lambda *a, **k: (_ for _ in ()).throw(OSError("sin red simulada"))
        F.metadatos_doi = lambda doi: (_ for _ in ()).throw(OSError("sin red simulada"))
        r3 = R.proponer(F, oracion, cita, n=5)
        if r3["candidatas"] or not any("sin red" in a for a in r3["avisos"]):
            fallas.append(f"sin red: sin candidatas y con aviso «sin red»: {r3['avisos']}")
    finally:
        for k, v in guardado.items():
            setattr(F, k, v)
    if not R.terminos_clave("Hosen (2025) mostró que ajustar un modelo no garantiza una mejor calidad"):
        fallas.append("terminos_clave vacío")
    # CLI: --reemplazar sin --cita es error de uso
    code, out = correr("fuentes", "--reemplazar", "una oración", "--sin-red")
    if code != 2:
        fallas.append(f"--reemplazar sin --cita debe salir con 2, salió {code}")
    return fallas


# ---------------------------------------------------------------- fuentes: del perfil
def prueba_fuentes_perfil(tmp):
    fallas = []
    refs = ["Smith, J. (2022). Deep learning for music. Journal of Music AI, 12(3), 45-67. https://doi.org/10.1000/xyz",
            "Creswell, J. W. (2018). Designing and conducting mixed methods research (3rd ed.). SAGE Publications.",
            "Wikipedia. (2024). Large language model. https://en.wikipedia.org/wiki/Large_language_model",
            "Autor Anónimo. (2023). Cómo entrenar modelos. https://miblog.medium.com/como-entrenar",
            "Stack Exchange. (2024). Licensing. Open Source Stack Exchange. https://opensource.stackexchange.com/help/licensing",
            "Usuario123. (2023). How to fine-tune a model? Stack Overflow. https://stackoverflow.com/questions/99",
            "Google. (2026). Gemma 4 model card. Google AI for Developers. https://ai.google.dev/gemma/docs/model_card",
            "Ley Federal del Derecho de Autor. (1996, 24 de diciembre). Diario Oficial de la Federación."]
    cuerpo = ["Texto de introducción sin citas para que el documento tenga cuerpo y no sea una lista pelada de referencias."]
    base = pathlib.Path(tmp) / "fnv"
    base.mkdir()
    sep = chr(10)
    casos = [("", set()),
             ("fuentes:" + sep + "  minimo_nivel: B" + sep + "  porcentaje_arbitradas: 70" + sep + "  evitar: [wikipedia, blog, foro]" + sep,
              {"evitar", "minimo", "pct"})]
    for k, (bloque, esperado) in enumerate(casos):
        carpeta = base / str(k)
        carpeta.mkdir()
        (carpeta / ".editorial.yaml").write_text("perfil: apa7" + sep + bloque, encoding="utf-8")
        d = docx.Document()
        d.add_heading("Introducción", 1)
        d.add_paragraph(cuerpo[0])
        d.add_heading("Referencias", 1)
        for r in refs:
            p = d.add_paragraph(r)
            p.paragraph_format.left_indent = Pt(36)
            p.paragraph_format.first_line_indent = Pt(-36)
        d.save(str(carpeta / "d.docx"))
        res = auditar.auditar(str(carpeta / "d.docx"), "apa7")
        h = [x for x in res["hallazgos"] if x["id"] == "FUE-NIV"]
        evitar = [x for x in h if "a evitar" in x["evidencia"]]
        minimo = [x for x in h if "bajo el nivel mínimo" in x["evidencia"]]
        pct = [x for x in h if "arbitradas (nivel A o B)" in x["evidencia"]]
        hubo = {n for n, l in (("evitar", evitar), ("minimo", minimo), ("pct", pct)) if l}
        if hubo != esperado:
            fallas.append(f"FUE-NIV caso {k}: {hubo} (esperado {esperado}) {[x['evidencia'][:80] for x in h]}")
            continue
        if esperado:
            if len(evitar) != 3 or any(x["severidad"] != "mayor" for x in evitar + pct) or minimo[0]["severidad"] != "menor":
                fallas.append(f"FUE-NIV: tres fuentes a evitar (wikipedia, blog, foro) y severidades: {[(x['severidad'], x['evidencia'][:50]) for x in h]}")
            if "Ley Federal" in minimo[0]["evidencia"]:
                fallas.append("FUE-NIV: una fuente documental (ley) no debe contar bajo el mínimo")
            if "Gemma" not in minimo[0]["evidencia"]:
                fallas.append(f"FUE-NIV: Gemma (nivel D) está bajo el mínimo B: {minimo[0]['evidencia']}")
    # el perfil ITE del plugin lleva el bloque
    txt = (ROOT / "perfiles" / "instituto-ejemplo-protocolo.editorial.yaml").read_text(encoding="utf-8")
    if "minimo_nivel: B" not in txt or "porcentaje_arbitradas: 70" not in txt or "evitar: [wikipedia, blog, foro]" not in txt:
        fallas.append("perfiles/instituto-ejemplo-protocolo.editorial.yaml no declara el bloque fuentes:")
    return fallas


# ---------------------------------------------------------------- portada
def spec_portada(ruta, personas=2):
    """Spec medida (sintética) de una portada con una caja de integrantes de `personas` líneas."""
    def lin(texto, pt, neg, y0, alin="centro", col="#000000", cur=False, **extra):
        h = round(pt * 1.1, 1)
        d = {"texto": texto, "fuente": "TimesNewRomanPS-BoldMT" if neg else "TimesNewRomanPSMT", "pt": pt, "negrita": neg, "cursiva": cur, "color": col,
             "alineacion": alin, "bbox": [82.6 if alin == "izquierda" else 100.0, y0, 500.0, round(y0 + h, 1)]}
        d.update(extra)
        return d
    ls = [lin("INSTITUTO DEMO", 14, True, 90.0, col="#1B365D", campo="institución", fijo=True),
          lin("Dra. Eva Ruiz", 12, True, 130.0, col="#002060", campo="docente")]
    for k in range(3):  # el título largo de la prueba ocupa tres líneas con márgenes de 1 in
        ls.append(lin("TÍTULO DE EJEMPLO", 16, True, 200.0 + 22 * k, col="#1B365D", campo="título del proyecto"))
    ls.append(lin("Proyecto para la asignatura Demo", 12, False, 280.0, cur=True, campo="leyenda"))
    y = 320.0
    i_int = len(ls)
    ls.append(lin("INTEGRANTES", 11, True, y, "izquierda", "#1B365D", campo="integrantes"))
    y += 18
    for _ in range(personas):
        ls.append(lin("Nombre Apellido — No. de control: 21330001", 11, False, y, "izquierda", campo="integrantes", nombre_negrita=True))
        y += 14.5
    y1 = ls[-1]["bbox"][3] + 6
    ls.append(lin("Ciudad Ejemplo, Estado, México — Noviembre 2026", 11, True, y + 70, campo="lugar"))
    for i, l in enumerate(ls):
        prev = ls[i - 1]["bbox"][3] if i else 0.0
        l["espacio_antes"] = round(l["bbox"][1] - prev, 1)
    junto = list(range(i_int, i_int + 1 + personas))
    cajas = [{"tipo": "relleno", "color": "#F4F6F9", "bbox": [72.0, 314.0, 540.0, y1], "junto_a": junto},
             {"tipo": "barra_v", "color": "#1B365D", "grosor": 3.0, "lado": "izquierda", "bbox": [72.0, 314.0, 75.0, y1], "junto_a": junto}]
    ruta.write_text(json.dumps({"origen": "prueba", "pagina": [612.0, 792.0], "lineas": ls, "cajas": cajas}, ensure_ascii=False, indent=1), encoding="utf-8")


YAML_PORTADA = """perfil: apa7
formato:
  fuente: {nombre: Times New Roman, pt: 12}
  portada:
    campos:
      - {nombre: "institución", literal: "INSTITUTO DEMO"}
      - {nombre: "docente", patron: '(?i:^\\s*(?:docente|asesor)\\b)|^\\s*(?:MC|Dra?|Ing|Lic)\\.\\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]'}
      - {nombre: "título del proyecto"}
      - {nombre: "leyenda", literal: "Proyecto para la asignatura Demo"}
      - {nombre: "integrantes", patron: '(?i:^\\s*integrantes?\\b)'}
      - {nombre: "lugar", patron: '(?i:^\\s*Ciudad Ejemplo,)'}
    fecha: mes_anio
    numero_control: true
%(logos)s
vinculante:
  - id: portada-demo
    origen: "prueba sembrada"
    fecha: "2026-11-27"
    tipo: modelo
    ambito: portada
    spec: portada-spec.json
"""


def doc_portada(ruta, con_integrantes=True):
    d = docx.Document()
    for lado in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
        setattr(d.sections[0], lado, Pt(72))
    for t in ("INSTITUTO DEMO", "Dra. Ana Torres", "TUTOR-AI: TUTOR MUSICAL CON INTELIGENCIA ARTIFICIAL PARA APOYAR LA ENSEÑANZA DE LA MÚSICA EN EL NIVEL SUPERIOR",
              "Proyecto para la asignatura Demo", "Integrantes:", "Luis Gómez Ruiz — No. de control: 21330002", "Ana Ríos Soto — No. de control: [[PENDIENTE]]",
              "Ciudad Ejemplo, Estado, México — Noviembre 2026"):
        p = d.add_paragraph(t)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    import copy
    d.paragraphs[-1]._p.get_or_add_pPr().append(copy.deepcopy(d.sections[0]._sectPr))  # sectPr de la portada (sección 0)
    d.add_heading("1. INTRODUCCIÓN", 1)
    d.add_paragraph("Texto del cuerpo.")
    d.save(str(ruta))


def prueba_portada(tmp):
    fallas = []
    carpeta = pathlib.Path(tmp) / "port"
    carpeta.mkdir()
    spec_portada(carpeta / "portada-spec.json")
    png(carpeta / "logo.png")
    (carpeta / ".editorial.yaml").write_text(YAML_PORTADA % {"logos": ""}, encoding="utf-8")
    doc = carpeta / "d.docx"
    doc_portada(doc)
    h0 = sha(doc)
    # 1) sin controles completos: INS-010 por el [[PENDIENTE]], código 1; docente por --campo; integrantes por --campo
    out = carpeta / "salida.docx"
    code, txt = correr("portada", doc, "--out", out, "--sin-ajuste", "--campo", "docente=Dra. Eva Ruiz",
                       "--campo", "integrantes=Luis Gómez Ruiz:21330002; Ana Ríos Soto", "--json", carpeta / "r.json")
    if sha(doc) != h0:
        fallas.append("portada modificó el original")
    if code != 1 or "INS-010" not in txt or "sin número de control" not in txt:
        fallas.append(f"con un número de control pendiente: código 1 e INS-010 (salió {code}): {txt[-400:]}")
    if not out.exists():
        return fallas + ["no escribió la salida"]
    d = docx.Document(str(out))
    textos = [p.text for p in d.element.body.iter(qn("w:p")) for p in [docx.text.paragraph.Paragraph(p, d)]]
    textos = [t for t in textos if t.strip()]
    esperados = ["INSTITUTO DEMO", "Dra. Eva Ruiz", "TUTOR-AI: TUTOR MUSICAL CON INTELIGENCIA ARTIFICIAL PARA APOYAR LA ENSEÑANZA DE LA MÚSICA EN EL NIVEL SUPERIOR"]
    if textos[:2] != esperados[:2]:
        fallas.append(f"institución literal y docente por --campo: {textos[:3]}")
    titulo = textos[2:textos.index("Proyecto para la asignatura Demo")]
    if len(titulo) < 2 or " ".join(titulo).replace("  ", " ").upper() != esperados[2]:
        fallas.append(f"el título largo debe partirse en líneas sin perder texto: {titulo}")
    if "Proyecto para la asignatura Demo" not in textos:
        fallas.append("el literal de la leyenda se perdió")
    if sum("[[PENDIENTE]]" in t for t in textos) != 1 or not any("Ana Ríos Soto — No. de control: [[PENDIENTE]]" in t for t in textos):
        fallas.append(f"solo el integrante sin número queda [[PENDIENTE]]: {[t for t in textos if 'PENDIENTE' in t]}")
    if not any(t.startswith("Luis Gómez Ruiz — No. de control: 21330002") for t in textos):
        fallas.append("integrante con su número de control")
    if not d.element.body.find(".//" + qn("w:pPr") + "/" + qn("w:sectPr")) is not None:
        fallas.append("se perdió el sectPr de la portada")
    if auditar.buscar_equipo(str(out)) is None:
        fallas.append("el .editorial.yaml no se encuentra junto a la salida")
    # 2) con el número que faltaba: INS-010 e INS-015 en limpio y código 0
    out2 = carpeta / "salida2.docx"
    code, txt = correr("portada", out, "--out", out2, "--sin-ajuste", "--campo", "control.Ana=21330009")
    if code != 0 or "reproduce el perfil y el modelo" not in txt:
        fallas.append(f"con todos los números de control: INS-010 e INS-015 en limpio (código {code}): {txt[-500:]}")
    # 3) la salida igual al original es error de uso
    code, txt = correr("portada", doc, "--out", doc)
    if code != 2:
        fallas.append(f"--out igual al original debe salir con 2, salió {code}")
    # 4) logos: un archivo que existe y uno que falta (hueco + aviso)
    (carpeta / ".editorial.yaml").write_text(YAML_PORTADA % {"logos": "    logos:\n      - {nombre: A, ruta: logo.png, alto_cm: 2}\n      - {nombre: B, ruta: no-existe.png, alto_cm: 2}"}, encoding="utf-8")
    out3 = carpeta / "salida3.docx"
    code, txt = correr("portada", out2, "--out", out3, "--sin-ajuste")
    if "logo «B»" not in txt or "queda el hueco" not in txt:
        fallas.append(f"logo ausente: aviso y hueco: {txt[-300:]}")
    d3 = docx.Document(str(out3))
    if len(list(d3.element.body.iter("{http://schemas.openxmlformats.org/drawingml/2006/main}blip"))) != 1:
        fallas.append("la fila de logos debe llevar exactamente la imagen que existe")
    primera = d3.element.body[0]
    if primera.tag != qn("w:tbl") or len(primera.findall(".//" + qn("w:tc"))) != 2:
        fallas.append("la fila de logos es una tabla de dos celdas al inicio de la portada")
    # 5) sin perfil de portada: error de uso
    sin = pathlib.Path(tmp) / "sinperfil"
    sin.mkdir()
    (sin / ".editorial.yaml").write_text("perfil: apa7\n", encoding="utf-8")
    doc_portada(sin / "d.docx")
    code, txt = correr("portada", sin / "d.docx")
    if code != 2 or "formato: portada" not in txt:
        fallas.append(f"sin `formato: portada:` debe salir con 2 y explicarlo: {code} {txt[-200:]}")
    return fallas


def prueba_portada_medida(tmp):
    if not (HAY_LO and HAY_FITZ):
        print("SALTADA: portada-medida necesita LibreOffice y PyMuPDF")
        return []
    fallas = []
    carpeta = pathlib.Path(tmp) / "portm"
    carpeta.mkdir()
    spec_portada(carpeta / "portada-spec.json")
    (carpeta / ".editorial.yaml").write_text(YAML_PORTADA % {"logos": ""}, encoding="utf-8")
    doc = carpeta / "d.docx"
    doc_portada(doc)
    code, txt = correr("portada", doc, "--out", carpeta / "s.docx", "--campo", "integrantes=Luis Gómez Ruiz:21330002; Ana Ríos Soto:21330009", "--json", carpeta / "r.json")
    r = json.loads((carpeta / "r.json").read_text(encoding="utf-8"))
    aj = r["ajuste"]
    if not aj["ajustado"] or aj["error_max_pt"] is None or aj["error_max_pt"] > 0.5:
        fallas.append(f"el espaciado medido debe quedar a <= 0.5 pt del modelo: {aj}")
    if code != 0:
        fallas.append(f"portada completa debe salir con 0 (salió {code}): {txt[-300:]}")
    # medir la salida y comparar con la spec
    pdf = libreoffice.a_pdf(carpeta / "s.docx", carpeta / "pdf")
    with fitz.open(str(pdf)) as d:
        ys = {}
        for b in d[0].get_text("dict")["blocks"]:
            for ln in b.get("lines", []):
                t = "".join(s["text"] for s in ln["spans"]).strip()
                ys[t] = ln["bbox"][1]
    spec = json.loads((carpeta / "portada-spec.json").read_text(encoding="utf-8"))
    for l in spec["lineas"][:3]:
        t = l["texto"] if l["texto"] != "Dra. Eva Ruiz" else "Dra. Eva Ruiz"
        if t in ys and abs(ys[t] - l["bbox"][1]) > 0.8:
            fallas.append(f"«{t}» a {ys[t]:.1f} pt, el modelo la pone a {l['bbox'][1]} pt")
    return fallas


# ---------------------------------------------------------------- índices y entregar
def doc_con_secciones(ruta, pendiente=False):
    """Portada (sin número), preliminares (romanos) con los tres títulos de índice y cuerpo (arábigos desde 1) con tablas y figuras."""
    d = docx.Document()
    d.add_paragraph("Portada de prueba").alignment = WD_ALIGN_PARAGRAPH.CENTER
    fin_portada = d.add_paragraph("Ciudad Ejemplo, Estado, México — Noviembre 2026")
    fin_portada.alignment = WD_ALIGN_PARAGRAPH.CENTER

    def seccion(fmt, start):
        import copy
        sp = OxmlElement("w:sectPr")
        for hijo in d.sections[0]._sectPr:
            if hijo.tag in (qn("w:pgSz"), qn("w:pgMar")):
                sp.append(copy.deepcopy(hijo))
        pg = OxmlElement("w:pgNumType")
        if fmt:
            pg.set(qn("w:fmt"), fmt)
        if start is not None:
            pg.set(qn("w:start"), str(start))
        sp.append(pg)
        return sp
    fin_portada._p.get_or_add_pPr().append(seccion(None, None))
    for t in ("RESUMEN", "ÍNDICE DE CONTENIDO", "ÍNDICE DE TABLAS", "ÍNDICE DE FIGURAS"):
        h = d.add_paragraph(t)
        h.style = d.styles["Normal"]
        h.alignment = WD_ALIGN_PARAGRAPH.CENTER
        h.paragraph_format.page_break_before = True
        if t == "RESUMEN":
            d.add_paragraph("Resumen breve de prueba." + (" [[PENDIENTE]]" if pendiente else ""))
    ultimo = d.add_paragraph("")
    ultimo._p.get_or_add_pPr().append(seccion("lowerRoman", 1))
    for n in range(1, 5):
        h = d.add_heading(f"{n}. CAPÍTULO {n}", 1)
        h.paragraph_format.page_break_before = True
        d.add_paragraph("Texto " * 30)
        d.add_heading(f"{n}.1. Sección {n}.1", 2)
        for _ in range(3):
            d.add_paragraph("Un párrafo de relleno para ocupar espacio en la página. " * 12)
        if n == 2:
            d.add_paragraph("TABLA I").alignment = WD_ALIGN_PARAGRAPH.CENTER
            d.add_paragraph("COMPONENTES DE PRUEBA").alignment = WD_ALIGN_PARAGRAPH.CENTER
            d.add_paragraph("Contenido de la tabla.")
        if n == 3:
            d.add_paragraph("Fig. 1. Diagrama de prueba con un pie algo largo para ocupar más de una línea en la página")
    d.add_heading("Referencias", 1).paragraph_format.page_break_before = True
    d.add_paragraph("Smith, J. (2022). Deep learning for music. Journal of Music AI, 12(3), 45-67. https://doi.org/10.1000/xyz")
    final = d.sections[-1]._sectPr
    pg = OxmlElement("w:pgNumType")
    pg.set(qn("w:fmt"), "decimal")
    pg.set(qn("w:start"), "1")
    final.find(qn("w:cols")).addprevious(pg)
    d.save(str(ruta))
    return str(ruta)


def prueba_indices(tmp):
    fallas = []
    import indices
    # sin LibreOffice: código 2 y mensaje de instalación (se simula la ausencia)
    carpeta = pathlib.Path(tmp) / "ind"
    carpeta.mkdir()
    doc = doc_con_secciones(carpeta / "d.docx")
    guardado = libreoffice.buscar
    libreoffice.buscar = lambda: None
    err = io.StringIO()
    try:
        with contextlib.redirect_stderr(err):
            indices.construir(doc, None, None)
        fallas.append("sin LibreOffice debería terminar con SystemExit(2)")
    except SystemExit as e:
        if e.code != 2 or "LibreOffice" not in err.getvalue() or "winget install" not in err.getvalue():
            fallas.append(f"sin LibreOffice: código 2 con instrucciones: {e.code} {err.getvalue()!r}")
    finally:
        libreoffice.buscar = guardado
    if not (HAY_LO and HAY_FITZ):
        print("SALTADA: indices (con LibreOffice) necesita LibreOffice y PyMuPDF")
        return fallas
    h0 = sha(doc)
    out = carpeta / "s.docx"
    code, txt = correr("indices", doc, "--out", out, "--json", carpeta / "r.json")
    if sha(doc) != h0:
        fallas.append("indices modificó el original")
    r = json.loads((carpeta / "r.json").read_text(encoding="utf-8")) if (carpeta / "r.json").exists() else {}
    if code != 0 or not r.get("convergio") or r.get("vueltas", 9) > 4:
        fallas.append(f"los índices deben converger en <= 4 vueltas: código {code} {txt[-300:]}")
    if (r.get("encabezados"), r.get("tablas"), r.get("figuras")) != (9, 1, 1):
        fallas.append(f"inventario: {r.get('encabezados')} encabezados, {r.get('tablas')} tablas, {r.get('figuras')} figuras (esperado 9, 1, 1)")
    d = docx.Document(str(out))
    xml = d.element.xml
    if 'TOC \\o "1-3" \\h \\z \\u' not in xml or "w:hyperlink" not in xml or "_Toc" not in xml:
        fallas.append("el contenido debe ser un campo TOC real con enlaces a marcadores _Toc")
    if xml.count('w:fldCharType="begin"') != 1 or xml.count('w:fldCharType="end"') != 1 or xml.count('w:fldCharType="separate"') != 1:
        fallas.append("el campo TOC debe abrir, separar y cerrar una vez")
    if d.settings.element.find(qn("w:updateFields")) is None or d.settings.element.find(qn("w:updateFields")).get(qn("w:val")) != "true":
        fallas.append("updateFields debe quedar en true")
    escrito = indices.leer_escrito(d)
    por = {k[1]: v for k, v in escrito.items()}
    if por.get("1. CAPÍTULO 1") != "1":
        fallas.append(f"el primer capítulo debe llevar la página visible 1 (arábigos desde 1), lleva {por.get('1. CAPÍTULO 1')}")
    if ("tablas", "TABLA I. COMPONENTES DE PRUEBA") not in escrito or not any(k[1].startswith("Fig. 1. Diagrama de prueba") for k in escrito):
        fallas.append(f"rótulos exactos en las listas de tablas y figuras: {[k for k in escrito if k[0] != 'contenido']}")
    dif, av, n = indices.comprobar(out)
    if dif or n != 11:
        fallas.append(f"los números de los índices deben coincidir con el PDF: {dif[:3]} ({n} entradas)")
    code2, txt2 = correr("indices", out, "--comprobar")
    if code2 != 0:
        fallas.append(f"indices --comprobar sobre lo ya indexado: código {code2}: {txt2[-200:]}")
    # un número cambiado a mano se detecta
    d2 = docx.Document(str(out))
    for p in d2.element.body.iter(qn("w:p")):
        ts = [t for t in p.iter(qn("w:t"))]
        if len(ts) >= 2 and ts[0].text and ts[0].text.startswith("2. CAPÍTULO 2"):
            ts[-1].text = "99"
            break
    d2.save(str(carpeta / "roto.docx"))
    code3, txt3 = correr("indices", carpeta / "roto.docx", "--comprobar")
    if code3 != 1 or "dice 99" not in txt3:
        fallas.append(f"--comprobar debe detectar el número 99 (código {code3}): {txt3[-200:]}")
    return fallas


def prueba_entregar(tmp):
    if not (HAY_LO and HAY_FITZ):
        print("SALTADA: entregar necesita LibreOffice y PyMuPDF")
        return []
    fallas = []
    carpeta = pathlib.Path(tmp) / "ent"
    carpeta.mkdir()
    (carpeta / ".editorial.yaml").write_text("perfil: apa7\n", encoding="utf-8")
    doc = doc_con_secciones(carpeta / "d.docx", pendiente=True)
    h0 = sha(doc)
    code, txt = correr("entregar", doc, "--json", carpeta / "r.json")
    if sha(doc) != h0:
        fallas.append("entregar modificó el original")
    e_docx, e_pdf = carpeta / "d.entrega.docx", carpeta / "d.entrega.pdf"
    if not e_docx.exists() or not e_pdf.exists():
        return fallas + [f"entregar debe dejar .entrega.docx y .entrega.pdf juntos: {txt[-400:]}"]
    r = json.loads((carpeta / "r.json").read_text(encoding="utf-8"))
    if code != 1 or not any(h["id"] == "EA-001" for h in r["criticos"]):
        fallas.append(f"un [[PENDIENTE]] deja EA-001 crítico y código 1 (salió {code})")
    pasos = [p["paso"] for p in r["pasos"]]
    for esperado in ("corregir", "portada", "indices", "pdf", "capturas", "indices vs PDF", "auditar", "estructura", "puntuar"):
        if esperado not in pasos:
            fallas.append(f"falta el paso «{esperado}» del resumen: {pasos}")
    if not r["capturas"] or not (carpeta / "d.entrega.capturas" / "portada.png").exists():
        fallas.append("capturas PNG de la portada y los preliminares")
    if r["indices_distintos"]:
        fallas.append(f"los índices de la entrega no coinciden con su PDF: {r['indices_distintos'][:2]}")
    if "ENTREGA" not in txt or "docx:" not in txt or "pdf:" not in txt:
        fallas.append("el resumen impreso debe nombrar el docx y el pdf")
    # sin el marcador: ya no hay EA-001
    doc2 = doc_con_secciones(carpeta / "e.docx", pendiente=False)
    code2, txt2 = correr("entregar", doc2, "--sin-capturas", "--json", carpeta / "r2.json")
    r2 = json.loads((carpeta / "r2.json").read_text(encoding="utf-8")) if (carpeta / "r2.json").exists() else {"criticos": [{"id": "?"}]}
    if any(h["id"] == "EA-001" for h in r2["criticos"]):
        fallas.append("sin [[PENDIENTE]] no debe haber EA-001")
    if (carpeta / "e.entrega.capturas").exists():
        fallas.append("--sin-capturas no debe crear la carpeta de capturas")
    # la salida igual al original es error de uso
    code3, _ = correr("entregar", doc, "--out", doc)
    if code3 != 2:
        fallas.append(f"--out igual al original debe salir con 2, salió {code3}")
    return fallas


def prueba_despachador(tmp):
    fallas = []
    code, out = correr("--help")
    for c in ("portada", "indices", "entregar"):
        if c not in out:
            fallas.append(f"editorial.py --help no lista «{c}»")
    for c, flag in (("portada", "--campo"), ("indices", "--comprobar"), ("entregar", "--paginacion"), ("fuentes", "--reemplazar")):
        code, out = correr(c, "--help")
        if flag not in out:
            fallas.append(f"{c} --help no lista {flag}")
    return fallas


def prueba_con_red(tmp):
    """La oración de Hosen (2025) con su referencia arXiv real."""
    fallas = []
    oracion = "Además, ajustarlos no asegura una mejora cuando los datos de entrenamiento contienen errores (Hosen, 2025)."
    cita = ("Hosen, M. M. (2025). Fine-tuning a 7B advisor on free-tier GPUs: An adapter-handoff recipe and a synthetic-data reliability caution. "
            "arXiv. https://arxiv.org/abs/2504.15610")
    out = pathlib.Path(tmp) / "cand.json"
    code, txt = correr("fuentes", "--reemplazar", oracion, "--cita", cita, "--n", "5", "--out", out)
    if code != 0 or not out.exists():
        return [f"--reemplazar con red: código {code}: {txt[-300:]}"]
    r = json.loads(out.read_text(encoding="utf-8"))
    if r["tipo_original"] != "preprint":
        fallas.append(f"la referencia arXiv es preprint: {r['tipo_original']}")
    if not r["candidatas"] or any(c["nivel"] not in ("A", "B") for c in r["candidatas"]) or not any(c["resumen"] and c["fragmento"] for c in r["candidatas"]):
        fallas.append("candidatas A/B con resumen y fragmento")
    return fallas


# ---------------------------------------------------------------- denominador común, licencias, contexto, pgMar
def _doc_refs(carpeta, refs, yaml):
    carpeta.mkdir(parents=True, exist_ok=True)
    (carpeta / ".editorial.yaml").write_text(yaml, encoding="utf-8", newline="")
    d = docx.Document()
    d.add_heading("Introducción", 1)
    d.add_paragraph("Texto de introducción sin citas para que el documento tenga cuerpo.")
    d.add_heading("Referencias", 1)
    for r in refs:
        p = d.add_paragraph(r)
        p.paragraph_format.left_indent = Pt(36)
        p.paragraph_format.first_line_indent = Pt(-36)
    d.save(str(carpeta / "d.docx"))
    return str(carpeta / "d.docx")


def prueba_denominador(tmp):
    """FUE-NIV (porcentaje_arbitradas) e INS-008 comparten UNA función de denominador: la literatura actualizable."""
    import institucional
    fallas = []
    refs = ["Ruiz, A. (2025). Ajuste fino de modelos. Revista de Aprendizaje Automático, 12(3), 45-67. https://doi.org/10.1000/a1",
            "Gil, B. (2024). Datos con errores. Journal of Data Quality, 8(1), 1-20. https://doi.org/10.1000/a2",
            "Paz, C. (2026). Tutores inteligentes. Computers and Education, 15(2), 100-120. https://doi.org/10.1000/a3",
            "Vega, D. (2015). Modelos antiguos. Journal of Old Models, 3(4), 11-30. https://doi.org/10.1000/a4",
            "Creswell, J. W. (1996). Designing research (1st ed.). SAGE Publications.",
            "Apache Software Foundation. (2004). Apache License, Version 2.0. https://www.apache.org/licenses/LICENSE-2.0",
            "Autor, X. (2024). Cómo entrenar un modelo. https://miblog.medium.com/entrenar",
            "Google. (2026). Gemma model card. Google AI for Developers. https://ai.google.dev/gemma/docs/model_card",
            "Sociedad de Ejemplo. Informe de la sociedad sin fecha. Sociedad de Ejemplo."]
    nl = chr(10)
    yaml = ("perfil: apa7" + nl + "formato:" + nl + "  fuentes_recientes:" + nl + "    anios: 5" + nl + "    porcentaje: 70" + nl + "    arbitradas: true" + nl
            + "    fundacionales:" + nl + "      - {ref: 'Creswell, J. W. (1996)', motivo: 'obra original'}" + nl + "  anio_actual: 2026" + nl
            + "fuentes:" + nl + "  porcentaje_arbitradas: 70" + nl)
    ruta = _doc_refs(pathlib.Path(tmp) / "den", refs, yaml)
    res = auditar.auditar(ruta, "apa7")
    nv = [h for h in res["hallazgos"] if h["id"] == "FUE-NIV" and "arbitradas (nivel A o B)" in h["evidencia"]]
    i8 = [h for h in res["hallazgos"] if h["id"] == "INS-008"]
    if not nv or not i8:
        return [f"debe haber FUE-NIV porcentaje e INS-008: {[h['id'] for h in res['hallazgos']]}"]
    if "de 6 referencias" not in nv[0]["evidencia"] or "de 6 referencias" not in i8[0]["evidencia"]:
        fallas.append(f"mismo denominador (6): FUE-NIV {nv[0]['evidencia'][:90]!r} / INS-008 {i8[0]['evidencia'][:90]!r}")
    for h in (nv[0], i8[0]):
        if "1 fundacionales" not in h["evidencia"] or "1 documentales" not in h["evidencia"] or "1 sin año" not in h["evidencia"]:
            fallas.append(f"{h['id']}: el mensaje dice qué se excluyó: {h['evidencia'][:200]!r}")
    lst = [{"texto": r} for r in refs]
    info = institucional.literatura_actualizable(lst, {"fundacionales": [{"ref": "Creswell, J. W. (1996)", "motivo": "x"}]})
    if len(info["base"]) != 6 or len(info["fuera"]) != 2 or len(info["sin_fecha"]) != 1:
        fallas.append(f"literatura_actualizable: base {len(info['base'])} fuera {len(info['fuera'])} sin fecha {len(info['sin_fecha'])}")
    return fallas


def prueba_licencias(tmp):
    """Una página de licencia es documental (D), no foro; el tipo de documento gana sobre el dominio."""
    import niveles
    fallas = []
    casos = [("Stack Exchange. (2024). Licensing. Open Source Stack Exchange. https://opensource.stackexchange.com/help/licensing", "D"),
             ("SPDX. (2023). SPDX license list. https://spdx.org/licenses/", "D"),
             ("Apache Software Foundation. (2004). Apache License, Version 2.0. https://www.apache.org/licenses/LICENSE-2.0", "D"),
             ("Creative Commons. (2013). Attribution 4.0 International. https://creativecommons.org/licenses/by/4.0/", "D"),
             ("Reddit. (2024). Terms of Use. https://www.reddit.com/policies/user-agreement", "D"),
             ("Usuario123. (2023). How to fine-tune a model? Stack Overflow. https://stackoverflow.com/questions/99", "E"),
             ("Smith, J. (2021). Open licensing in practice. Journal of X, 3(2), 10-20. https://doi.org/10.1000/abc", "A")]
    for t, esp in casos:
        r = niveles.clasificar({}, t)
        if r["nivel"] != esp:
            fallas.append(f"{t[:50]}: nivel {r['nivel']} (esperado {esp}) {r['motivo']}")
    refs = ["Smith, J. (2022). Deep learning for music. Journal of Music AI, 12(3), 45-67. https://doi.org/10.1000/xyz",
            "Stack Exchange. (2024). Licensing. Open Source Stack Exchange. https://opensource.stackexchange.com/help/licensing"]
    ruta = _doc_refs(pathlib.Path(tmp) / "lic", refs, "perfil: apa7" + chr(10) + "fuentes:" + chr(10) + "  evitar: [foro]" + chr(10))
    res = auditar.auditar(ruta, "apa7")
    if [h for h in res["hallazgos"] if h["id"] == "FUE-NIV"]:
        fallas.append("FUE-NIV: la página «Licensing» no es un foro a evitar")
    return fallas


def doc_contexto(ruta):
    d = docx.Document()
    for t in ("INSTITUTO DE EJEMPLO", "TUTOR DE GUITARRA CON MODELOS DE LENGUAJE", "PARA LA ENSEÑANZA DE LA MÚSICA", "RESUMEN",
              "Se propone un tutor de guitarra basado en modelos de lenguaje para apoyar la enseñanza de la música.",
              "Palabras clave: tutor inteligente, modelos de lenguaje, educación musical, guitarra, notación."):
        d.add_paragraph(t)
    for _ in range(6):
        d.add_paragraph("El tutor de guitarra usa modelos de lenguaje y notación musical para que los estudiantes de música reciban retroalimentación sobre la técnica.")
    d.save(str(ruta))


def prueba_contexto(tmp):
    """`fuentes --reemplazar --contexto`: términos de dominio, consulta con dominio, descarte de dominios ajenos, puntuación = oración x dominio."""
    fallas = []
    ctx = pathlib.Path(tmp) / "ctx.docx"
    doc_contexto(ctx)
    t = R.terminos_dominio(ctx)
    if not (5 <= len(t) <= 8) or "tutor" not in t or not any(x.startswith("music") for x in t) or any(x in t for x in ("instituto", "resumen")):
        fallas.append(f"terminos_dominio: 5-8 términos del dominio sin portada ni genéricas: {t}")
    oracion = "Además, ajustarlos no asegura una mejora cuando los datos de entrenamiento contienen errores (Hosen, 2025)."
    q = R.consultas(oracion, t)
    if len(q) < 2 or not any(x in q[0][1] for x in t[:3]):
        fallas.append(f"las consultas exigen términos de dominio: {q}")
    cr = {"10.1000/a.1": {"DOI": "10.1000/a.1", "title": ["Fine-tuning language models for music tutoring with noisy data"], "type": "journal-article",
                          "container-title": ["J. Music Tech"], "author": [{"family": "Ruiz"}], "issued": {"date-parts": [[2024]]},
                          "abstract": "Training data with errors degrade a language model used as a music tutor. Fine-tuning gives no guarantee of improvement."},
          "10.1000/g.1": {"DOI": "10.1000/g.1", "title": ["Fine-tuning protein models: training data with errors in genomics"], "type": "journal-article",
                          "container-title": ["J. Genomics"], "author": [{"family": "Gen"}], "issued": {"date-parts": [[2024]]},
                          "abstract": "Training data with errors degrade protein folding results; fine-tuning gives no guarantee of improvement in genomics."}}
    oa = [{"doi": "https://doi.org/10.1000/g.1", "title": "x", "abstract_inverted_index": _inv(cr["10.1000/g.1"]["abstract"])},
          {"doi": "https://doi.org/10.1000/a.1", "title": "x", "abstract_inverted_index": _inv(cr["10.1000/a.1"]["abstract"])}]
    guardado = {k: getattr(F, k) for k in ("metadatos_doi", "integridad", "crossref", "openalex_buscar", "get", "get_texto", "doi_por_metadatos_motivo")}
    try:
        F.metadatos_doi = lambda doi: None
        F.integridad = lambda doi, meta: {"version_publicada": None}
        F.crossref = lambda doi: cr.get(doi.lower().replace("https://doi.org/", ""))
        F.openalex_buscar = lambda q_, n, desde, idioma, oa_, orden=None: oa
        F.get = lambda url, tries=3: {}
        F.get_texto = lambda url, tries=2: ""
        F.doi_por_metadatos_motivo = lambda it: (None, "sin coincidencia")
        cita = "Hosen, M. M. (2025). Fine-tuning a 7B advisor. arXiv. https://arxiv.org/abs/2504.15610"
        sin = R.proponer(F, oracion, cita, n=5)
        con = R.proponer(F, oracion, cita, n=5, contexto=str(ctx))
        if "10.1000/g.1" not in [c["doi"] for c in sin["candidatas"]]:
            fallas.append("sin contexto, la candidata de genómica sí aparece (así se demuestra el problema)")
        dois = [c["doi"] for c in con["candidatas"]]
        if dois != ["10.1000/a.1"]:
            fallas.append(f"con contexto solo la candidata del dominio: {dois}")
        else:
            c = con["candidatas"][0]
            if con["descartadas_por_dominio"] < 1 or not (0 < c["puntuacion"] <= 1) or abs(c["puntuacion"] - round(c["coincidencia"] * c["dominio"], 3)) > 1e-9:
                fallas.append(f"puntuación = oración x dominio y contador de descartadas: {c} {con['descartadas_por_dominio']}")
    finally:
        for k, v in guardado.items():
            setattr(F, k, v)
    code, out = correr("fuentes", "--help")
    if "--contexto" not in out or "--doc" not in out:
        fallas.append("fuentes --help lista --contexto y --doc")
    return fallas


def prueba_pgmar(tmp):
    """auditar con un sectPr sin pgMar: sin TypeError; márgenes por defecto de Word (1 in) y aviso."""
    ruta = pathlib.Path(tmp) / "sinmar.docx"
    d = docx.Document()
    d.add_heading("Introducción", 1)
    d.add_paragraph("Texto de prueba.")
    d.add_heading("Referencias", 1)
    sect = d.element.body.find(qn("w:sectPr"))
    mar = sect.find(qn("w:pgMar"))
    if mar is not None:
        sect.remove(mar)
    d.save(str(ruta))
    code, out = correr("auditar", ruta, "--perfil", "apa7")
    fallas = []
    if "TypeError" in out or "Traceback" in out:
        fallas.append(f"auditar con sectPr sin pgMar falla: {out[-300:]}")
    if code == 2:
        fallas.append(f"auditar sin pgMar no debe salir con 2: {out[-200:]}")
    if "sin márgenes declarados" not in out and "pgMar" not in out:
        fallas.append("aviso de márgenes por defecto ausente")
    if "APA-001" in out:
        fallas.append("sin márgenes declarados = 1 in por defecto: no hay APA-001")
    return fallas


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    con_red = "--con-red" in sys.argv
    tmp = tempfile.mkdtemp(prefix="v08")
    pruebas = [("reemplazar", prueba_reemplazar), ("fuentes-perfil", prueba_fuentes_perfil), ("denominador", prueba_denominador),
               ("licencias", prueba_licencias), ("contexto", prueba_contexto), ("pgmar", prueba_pgmar), ("portada", prueba_portada),
               ("portada-medida", prueba_portada_medida), ("indices", prueba_indices), ("entregar", prueba_entregar),
               ("despachador", prueba_despachador)]
    if con_red:
        pruebas.append(("reemplazar-con-red", prueba_con_red))
    solo = [a for a in sys.argv[1:] if not a.startswith("--")]
    if solo:
        pruebas = [x for x in pruebas if x[0] in solo]
    total = 0
    try:
        for nombre, fn in pruebas:
            try:
                fallas = fn(tmp)
            except Exception as ex:  # noqa: BLE001
                import traceback
                fallas = [f"EXCEPCIÓN {type(ex).__name__}: {ex}\n{traceback.format_exc()[-700:]}"]
            for f in fallas:
                print("FALLA", nombre, "-", f)
            total += len(fallas)
            print(("OK   " if not fallas else "FALLA"), nombre)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        shutil.rmtree(CACHE, ignore_errors=True)
    print(f"== v0.8: {len(pruebas)} grupos, {total} fallas" + (" (con red)" if con_red else ""))
    sys.exit(1 if total else 0)


if __name__ == "__main__":
    main()
