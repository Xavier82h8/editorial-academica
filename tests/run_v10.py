#!/usr/bin/env python3
"""Pruebas sembradas de la versión 0.10.0 (sin red): modo fiel, certificado de fidelidad, calificar sin tocar y precedencia del perfil.

Uso: python -I tests/run_v10.py
  precedencia   `--perfil` explícito gana sobre el `.editorial.yaml` de la carpeta (el bug: con uno institucional, `corregir --perfil apa7`
                numeraba y ponía en MAYÚSCULAS los títulos); se avisa en stderr y en el JSON; `--equipo` explícito lo aplica; sin --perfil manda el
                del .editorial.yaml; todos los comandos imprimen «perfil aplicado: X (origen: …)» al inicio
  fiel          docx con errores de formato Y de texto: `corregir --fiel` arregla el formato, deja el texto idéntico, escribe propuestas legibles
  propuestas    `--aplicar-propuestas` aplica solo las ids pedidas; el certificado las marca «texto aprobado»; un archivo de otro documento se rechaza
  certificado   un cambio de texto inyectado se detecta; en modo fiel termina con código 1 y no escribe la salida
  calificar     no modifica el archivo (sha256 ni carpeta), da puntaje, hallazgos por prioridad y ajustes automáticos o del usuario
  comparar      texto idéntico, cambio de texto detectado y resumen de formato por grupo (medir.py)
  completo      el modo completo (por defecto de la CLI) sigue corrigiendo texto y lo lista en el certificado como «por reglas»
Código de salida 0 solo si todo pasa.
"""
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import docx  # noqa: E402
from docx.enum.text import WD_ALIGN_PARAGRAPH  # noqa: E402
from docx.oxml import OxmlElement  # noqa: E402
from docx.oxml.ns import qn  # noqa: E402
from docx.shared import Inches, Pt  # noqa: E402

import fidelidad  # noqa: E402

PY = [sys.executable, "-I", str(ROOT / "scripts" / "editorial.py")]
LARGO = ("Los sistemas de tutoría inteligente han mostrado efectos positivos en el aprendizaje de la música, en particular cuando el "
         "estudiante explica lo aprendido a un agente que asume el rol de aprendiz")
FALLOS = []


def correr(*args, cwd=None):
    r = subprocess.run(PY + [str(a) for a in args], capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=cwd,
                       env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    return r.returncode, r.stdout, r.stderr


def comprobar(nombre, cond, detalle=""):
    print(("  ok     " if cond else "  FALLA  ") + nombre + ("" if cond else f"  [{detalle}]"))
    if not cond:
        FALLOS.append(nombre)


def sha(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


def sembrar(ruta, formato_mal=True):
    """APA en español con errores de FORMATO (márgenes 1.25 in, interlineado 1.5, justificado, sin sangría) y de TEXTO
    (lista rotulada «Bibliografía», DOI como «doi:», referencias fuera de orden)."""
    d = docx.Document()
    s = d.sections[0]
    s.top_margin = s.bottom_margin = s.left_margin = s.right_margin = Inches(1.25 if formato_mal else 1.0)
    n = d.styles["Normal"]
    n.font.name, n.font.size = "Times New Roman", Pt(12)
    n.paragraph_format.space_after = Pt(0)
    for h in ("Heading 1", "Heading 2"):
        d.styles[h].font.name, d.styles[h].font.size = "Times New Roman", Pt(12)
        d.styles[h].font.color.rgb = None
    # número de página arriba a la derecha
    hp = s.header.paragraphs[0]
    hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = hp.add_run()
    for tag, attr in (("w:fldChar", "begin"), ("w:instrText", None), ("w:fldChar", "end")):
        el = OxmlElement(tag)
        if attr:
            el.set(qn("w:fldCharType"), attr)
        else:
            el.set(qn("xml:space"), "preserve")
            el.text = " PAGE "
        run._r.append(el)

    def cuerpo(texto):
        p = d.add_paragraph(texto)
        p.paragraph_format.line_spacing = 1.5 if formato_mal else 2.0
        p.paragraph_format.first_line_indent = Inches(0 if formato_mal else 0.5)
        if formato_mal:
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        return p

    d.add_heading("Introducción", level=1)
    cuerpo(LARGO + " (Ker et al., 2018; Litjens et al., 2017). Además, otros trabajos coinciden (Shen et al., 2017).")
    d.add_heading("Guided Imagery", level=1)
    cuerpo(LARGO + ", según el análisis previo de Litjens et al. (2017).")
    h = d.add_heading("Bibliografía", level=1)
    h.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for t in ("Shen, D., Wu, G., & Suk, H.-I. (2017). Deep learning in medical image analysis. Annual Review of Biomedical Engineering, 19, "
              "221–248. doi:10.1146/annurev-bioeng-071516-044442",
              "Litjens, G., Kooi, T., Bejnordi, B. E., Setio, A. A. A., Ciompi, F., Ghafoorian, M., van der Laak, J. A. W. M., van Ginneken, B., "
              "& Sánchez, C. I. (2017). A survey on deep learning in medical image analysis. Medical Image Analysis, 42, 60–88. "
              "https://doi.org/10.1016/j.media.2017.07.005",
              "Ker, J., Wang, L., Rao, J., & Lim, T. (2018). Deep learning applications in medical image analysis. IEEE Access, 6, 9375–9389. "
              "https://doi.org/10.1109/access.2017.2788044"):
        p = d.add_paragraph(t)
        p.paragraph_format.left_indent = Inches(0 if formato_mal else 0.5)
        p.paragraph_format.first_line_indent = Inches(0 if formato_mal else -0.5)
        p.paragraph_format.line_spacing = 2.0
    d.save(str(ruta))


def textos(ruta):
    return [t for _, t in fidelidad.extraer(ruta)["cuerpo"] if fidelidad.norm(t)]


def margen_izq_in(ruta):
    return round(docx.Document(str(ruta)).sections[0].left_margin / 914400, 2)


def prueba_precedencia(tmp):
    print("== precedencia del perfil y línea «perfil aplicado»")
    d = tmp / "inst"
    d.mkdir()
    shutil.copy(ROOT / "perfiles" / "instituto-ejemplo-protocolo.editorial.yaml", d / ".editorial.yaml")
    doc = d / "tesis.docx"
    sembrar(doc)
    antes = textos(doc)
    h0 = sha(doc)
    # el bug: --perfil explícito + .editorial.yaml institucional en la carpeta
    code, out, err = correr("corregir", doc, "--perfil", "apa7", "--json", d / "r.json", "--out", d / "a.docx")
    comprobar("primera línea: perfil aplicado: apa7 (origen: CLI)", out.splitlines()[0] == "perfil aplicado: apa7 (origen: CLI)", out[:120])
    comprobar("avisa en stderr que ignora el .editorial.yaml", "se ignora .editorial.yaml de" in err and "pediste apa7" in err, err[:200])
    tx = textos(d / "a.docx")
    comprobar("los títulos no se numeran ni pasan a mayúsculas", "Introducción" in tx and "Guided Imagery" in tx
              and not any(t.startswith(("1. INTRODUCCIÓN", "2. GUIDED")) for t in tx), str(tx[:4]))
    r = json.loads((d / "r.json").read_text(encoding="utf-8"))
    ig = (r.get("perfil_aplicado") or {}).get("ignorado") or {}
    comprobar("el JSON dice qué perfil y qué equipo se aplicó", r["perfil_aplicado"]["perfil"] == "apa7" and r["perfil_aplicado"]["origen"] == "CLI"
              and "se ignora .editorial.yaml" in ig.get("mensaje", "") and ig.get("declara") == "apa7", str(r.get("perfil_aplicado")))
    comprobar("el original no cambió", sha(doc) == h0)
    # --equipo explícito: sí se aplica el bloque institucional
    code, out, err = correr("corregir", doc, "--perfil", "apa7", "--equipo", d / ".editorial.yaml", "--out", d / "b.docx")
    tb = textos(d / "b.docx")
    comprobar("con --equipo explícito sí se aplica el formato institucional", any(t.startswith("1. INTRODUCCIÓN") for t in tb), str(tb[:4]))
    comprobar("--equipo explícito no se ignora (sin aviso de «se ignora»)", "se ignora" not in err)
    comprobar("con --equipo la línea dice qué equipo se aplicó", out.splitlines()[0].startswith("perfil aplicado: apa7 (origen: CLI; equipo: .editorial.yaml en "), out[:160])
    # sin --perfil: manda el del .editorial.yaml y la línea lo dice
    code, out, err = correr("corregir", doc, "--out", d / "c.docx")
    comprobar("sin --perfil: origen .editorial.yaml en <ruta>", out.splitlines()[0].startswith("perfil aplicado: apa7 (origen: .editorial.yaml en ")
              and ".editorial.yaml" in out.splitlines()[0], out[:150])
    comprobar("sin --perfil se aplica el formato institucional", any(t.startswith("1. INTRODUCCIÓN") for t in textos(d / "c.docx")))
    # un .editorial.yaml que declara OTRO perfil, sin bloque institucional
    e = tmp / "otro"
    e.mkdir()
    (e / ".editorial.yaml").write_text("perfil: ieee\n", encoding="utf-8")
    shutil.copy(doc, e / "t.docx")
    code, out, err = correr("auditar", e / "t.docx", "--perfil", "apa7", "--json", e / "a.json")
    comprobar("declara otro perfil: aviso con el perfil declarado y el pedido", "declara ieee" in err and "pediste apa7" in err, err[:200])
    comprobar("auditar: perfil aplicado en la primera línea", out.splitlines()[0] == "perfil aplicado: apa7 (origen: CLI)")
    # todos los comandos imprimen la línea al inicio
    for sub, extra in (("auditar", ["--perfil", "apa7"]), ("puntuar", ["--perfil", "apa7", "--sin-historial", "--sin-red"]),
                       ("medir", ["--resumen"]), ("portada", ["--perfil", "apa7"]), ("entregar", ["--perfil", "apa7"]),
                       ("corregir", ["--perfil", "apa7", "--out", e / "z.docx"]), ("calificar", ["--perfil", "apa7"])):
        code, out, err = correr(sub, e / "t.docx", *extra)
        primera = out.splitlines()[0] if out.strip() else ""
        comprobar(f"{sub}: «perfil aplicado: …» al inicio", primera.startswith("perfil aplicado: "), f"{primera!r} {err[:120]!r}")
    code, out, err = correr("auditar", doc)  # d tiene .editorial.yaml con perfil: apa7
    comprobar("auditar sin --perfil: origen .editorial.yaml", "(origen: .editorial.yaml en " in out.splitlines()[0])


def prueba_fiel(tmp):
    print("== modo fiel")
    d = tmp / "fiel"
    d.mkdir()
    doc = d / "t.docx"
    sembrar(doc)
    h0, antes = sha(doc), textos(doc)
    code, out, err = correr("corregir", doc, "--perfil", "apa7", "--fiel", "--json", d / "r.json")
    sal = d / "t.corregido.docx"
    comprobar("termina bien y escribe la salida", sal.exists(), out[-300:] + err[-300:])
    comprobar("el original no cambió", sha(doc) == h0)
    comprobar("formato corregido: margen 1.25 in -> 1 in", margen_izq_in(doc) == 1.25 and margen_izq_in(sal) == 1.0, f"{margen_izq_in(sal)}")
    comprobar("el texto es IDÉNTICO al original", textos(sal) == antes, str(set(textos(sal)) ^ set(antes))[:300])
    comprobar("certificado: «fidelidad: texto idéntico»", "fidelidad: texto idéntico" in out, out[-200:])
    r = json.loads((d / "r.json").read_text(encoding="utf-8"))
    comprobar("JSON: modo fiel y fidelidad idéntica", r["modo"] == "fiel" and r["fidelidad"]["estado"] == "identico")
    pj = d / "t.propuestas.json"
    comprobar("escribe <doc>.propuestas.json", pj.exists())
    datos = json.loads(pj.read_text(encoding="utf-8"))
    props = datos["propuestas"]
    por_regla = {p["regla"]: p for p in props}
    comprobar("propone «Bibliografía» -> «Referencias» (APA-059)", "APA-059" in por_regla and por_regla["APA-059"]["antes"] == "Bibliografía"
              and por_regla["APA-059"]["despues"] == "Referencias", str(por_regla.get("APA-059")))
    comprobar("propone el DOI como URL (APA-076)", "APA-076" in por_regla and "doi:10." in por_regla["APA-076"]["antes"]
              and "https://doi.org/10." in por_regla["APA-076"]["despues"])
    comprobar("propone ordenar la lista (APA-061)", "APA-061" in por_regla and por_regla["APA-061"]["agrupada"])
    comprobar("cada propuesta trae id, regla, párrafo, antes, después y motivo",
              all(all(p.get(k) for k in ("id", "regla", "ubicacion", "antes", "despues", "motivo")) for p in props), str(props[:1]))
    comprobar("la lista legible sale por pantalla", "PROPUESTAS de cambio de texto" in out and "antes:" in out and "motivo:" in out)
    comprobar("ninguna propuesta se aplicó", "Referencias" not in textos(sal) and "Bibliografía" in textos(sal))
    # modo completo: lo de siempre, y lo lista como cambios por reglas
    code, out2, _ = correr("corregir", doc, "--perfil", "apa7", "--out", d / "completo.docx", "--json", d / "rc.json")
    tc = textos(d / "completo.docx")
    comprobar("modo completo sigue corrigiendo texto (Bibliografía -> Referencias)", "Referencias" in tc and "Bibliografía" not in tc)
    rc = json.loads((d / "rc.json").read_text(encoding="utf-8"))
    comprobar("el certificado del modo completo lista los cambios «por reglas»", rc["modo"] == "completo" and rc["fidelidad"]["estado"] == "cambios"
              and all(c["clase"].startswith("texto por reglas") for c in rc["fidelidad"]["cambios"]), str(rc["fidelidad"]["texto"]))
    return doc, datos


def prueba_aplicar(tmp, doc, datos):
    print("== propuestas aplicables por id")
    d = tmp / "fiel"
    pj = d / "t.propuestas.json"
    id059 = next(p["id"] for p in datos["propuestas"] if p["regla"] == "APA-059")
    code, out, err = correr("corregir", doc, "--perfil", "apa7", "--aplicar-propuestas", pj, "--solo", id059, "--out", d / "uno.docx", "--json", d / "ru.json")
    t1 = textos(d / "uno.docx")
    comprobar("aplica solo la propuesta pedida", "Referencias" in t1 and "Bibliografía" not in t1 and any("doi:10." in t for t in t1), out[-300:] + err[-200:])
    ru = json.loads((d / "ru.json").read_text(encoding="utf-8"))
    cs = ru["fidelidad"]["cambios"]
    comprobar("el certificado marca ese cambio como «texto aprobado» y no hay NO aprobados",
              len(cs) == 1 and cs[0]["clase"] == "texto aprobado" and cs[0]["antes"] == "Bibliografía" and ru["fidelidad"]["no_aprobados_n"] == 0, str(cs))
    comprobar("las demás siguen pendientes", ru["propuestas_aplicadas"] == [id059] and "Propuestas sin aplicar" in out)
    comprobar("la lista de referencias no se reordenó", [t for t in t1 if t.startswith(("Shen", "Litjens", "Ker"))][0].startswith("Shen"))
    # por regla, y todas
    code, out, err = correr("corregir", doc, "--perfil", "apa7", "--aplicar-propuestas", pj, "--solo", "APA-061", "--out", d / "orden.docx", "--json", d / "ro.json")
    t2 = [t for t in textos(d / "orden.docx") if t.startswith(("Shen", "Litjens", "Ker"))]
    comprobar("--solo acepta reglas: APA-061 ordena la lista", [x.split(",")[0] for x in t2] == ["Ker", "Litjens", "Shen"], str(t2))
    ro = json.loads((d / "ro.json").read_text(encoding="utf-8"))
    comprobar("el reorden queda aprobado en el certificado", ro["fidelidad"]["no_aprobados_n"] == 0 and ro["fidelidad"]["aprobados_n"] >= 1, ro["fidelidad"]["texto"])
    code, out, err = correr("corregir", doc, "--perfil", "apa7", "--aplicar-propuestas", pj, "--out", d / "todo.docx", "--json", d / "rt.json")
    rt = json.loads((d / "rt.json").read_text(encoding="utf-8"))
    comprobar("aplicar todas: sin cambios de texto no aprobados", code in (0, 1) and rt["fidelidad"]["no_aprobados_n"] == 0
              and set(rt["propuestas_aplicadas"]) == {p["id"] for p in datos["propuestas"]}, out[-300:] + err[-200:])
    comprobar("aplicar todas: igual que el modo completo en el texto", textos(d / "todo.docx") == textos(d / "completo.docx"))
    # propuestas de otro contenido
    otro = tmp / "fiel" / "otro.docx"
    sembrar(otro, formato_mal=False)
    d2 = docx.Document(str(otro))
    d2.add_paragraph("Un párrafo distinto que cambia el contenido del documento por completo y lo vuelve otro.")
    d2.save(str(otro))
    code, out, err = correr("corregir", otro, "--perfil", "apa7", "--aplicar-propuestas", pj, "--out", d / "x.docx")
    comprobar("un archivo de propuestas de otro documento se rechaza (código 1 o 2, sin salida)", code != 0 and not (d / "x.docx").exists() and "sha256" in (out + err), (out + err)[-200:])
    code, out, err = correr("corregir", doc, "--perfil", "apa7", "--aplicar-propuestas", pj, "--solo", "P999", "--out", d / "y.docx")
    comprobar("un id inexistente se avisa", "P999" in out and "ninguna propuesta" in out, out[-300:])


def prueba_certificado(tmp, doc):
    print("== certificado de fidelidad")
    d = tmp / "cert"
    d.mkdir()
    sal = d / "inyectado.docx"
    shutil.copy(doc, sal)
    dd = docx.Document(str(sal))
    p = next(p for p in dd.paragraphs if p.text.startswith("Los sistemas"))
    p.runs[0].text = p.runs[0].text.replace("positivos", "negativos")
    dd.save(str(sal))
    cert = fidelidad.comparar_texto(doc, sal)
    comprobar("detecta un cambio de texto inyectado", cert["estado"] == "cambios" and cert["no_aprobados_n"] == 1
              and "positivos" in cert["cambios"][0]["antes"] and "negativos" in cert["cambios"][0]["despues"], str(cert["cambios"][:1]))
    cert = fidelidad.comparar_texto(doc, sal, aprobados=[cert["cambios"][0]["antes"], cert["cambios"][0]["despues"]])
    comprobar("el mismo cambio, aprobado, se clasifica «texto aprobado»", cert["cambios"][0]["clase"] == "texto aprobado" and cert["no_aprobados_n"] == 0)
    # cambios de espacios, encabezado, pie y tabla
    c2 = d / "mas.docx"
    shutil.copy(doc, c2)
    d3 = docx.Document(str(c2))
    d3.sections[0].footer.paragraphs[0].text = "Pie nuevo"
    t = d3.add_table(rows=1, cols=1)
    t.cell(0, 0).text = "celda"
    d3.save(str(c2))
    cert = fidelidad.comparar_texto(doc, c2)
    cats = {c["categoria"] for c in cert["cambios"]}
    comprobar("detecta cambios en pie y tablas", {"encabezados", "tablas"} <= cats, str(cats))
    # el modo fiel se niega a escribir si la corrección cambia texto no aprobado (se simula un defecto del corrector)
    import corregir
    real = corregir._corregir

    def malo(path, perfil, out=None, *a, **k):
        r = real(path, perfil, out, *a, **k)
        if out and "-1-" in pathlib.Path(out).name:
            x = docx.Document(str(out))
            q = next(q for q in x.paragraphs if q.text.startswith("Los sistemas"))
            q.runs[0].text = q.runs[0].text + " INYECTADO"
            x.save(str(out))
        return r
    corregir._corregir = malo
    salida = d / "no-debe-existir.docx"
    try:
        corregir.corregir(str(doc), "apa7", str(salida), silencioso=True, fiel=True)
        rc = 0
    except SystemExit as e:
        rc = e.code
    finally:
        corregir._corregir = real
    ocultos = [f.name for f in d.iterdir() if f.name.startswith(".fiel-")]
    comprobar("modo fiel: cambio de texto no aprobado = error 1 y no se escribe la salida", rc == 1 and not salida.exists(), f"rc={rc}")
    comprobar("no deja archivos temporales", not ocultos and not [f for f in doc.parent.iterdir() if f.name.startswith(".fiel-")], str(ocultos))


def prueba_calificar(tmp, doc):
    print("== calificar (solo lectura)")
    d = tmp / "cal"
    d.mkdir()
    c = d / "t.docx"
    shutil.copy(doc, c)
    antes = {f.name: (f.stat().st_size, f.stat().st_mtime_ns) for f in d.iterdir()}
    h0 = sha(c)
    code, out, err = correr("calificar", c, "--perfil", "apa7", "--json", tmp / "cal.json")
    despues = {f.name: (f.stat().st_size, f.stat().st_mtime_ns) for f in d.iterdir()}
    comprobar("no modifica el archivo (sha256)", sha(c) == h0)
    comprobar("no escribe nada en la carpeta (ni historial ni copias)", antes == despues and not (d / ".editorial").exists(), str(set(despues) ^ set(antes)))
    comprobar("da puntaje, hallazgos por prioridad y ajustes", "PUNTAJE:" in out and "HALLAZGOS POR PRIORIDAD" in out and "AJUSTES SUGERIDOS" in out, out[:200])
    r = json.loads((tmp / "cal.json").read_text(encoding="utf-8"))
    sev = [h["severidad"] for h in r["hallazgos"]]
    orden = {"crítica": 0, "mayor": 1, "menor": 2}
    comprobar("hallazgos ordenados crítica > mayor > menor", [orden[s] for s in sev] == sorted(orden[s] for s in sev) and len(sev) > 3)
    aj = r["ajustes"]
    comprobar("distingue formato automático, texto por propuesta y lo que requiere al usuario",
              "APA-001" in aj["formato"] and "APA-059" in aj["texto"] and "APA-061" in aj["texto"] and "EST-001" in aj["usuario"], str({k: list(v) for k, v in aj.items() if isinstance(v, dict)}))
    comprobar("la ficha de medidas viene en el resultado", r["medidas"]["margenes_cm"]["izquierdo"] > 3 and r["solo_lectura"]["sha256"] == h0)
    comprobar("dice que no se aplicó nada", "Nada de esto se aplicó" in out)
    # un defecto simulado que escribiera junto al documento haría fallar la corrida
    import calificar
    real = calificar.auditar.auditar

    def escribe(*a, **k):
        (d / "intruso.txt").write_text("x")
        return real(*a, **k)
    calificar.auditar.auditar = escribe
    try:
        calificar.calificar(str(c), "apa7", "informe")
        rc = 0
    except SystemExit as e:
        rc = e.code
    finally:
        calificar.auditar.auditar = real
    comprobar("si algo escribiera en la carpeta, calificar falla (código 2)", rc == 2, f"rc={rc}")


def prueba_comparar(tmp, doc):
    print("== comparar")
    d = tmp / "comp"
    d.mkdir()
    code, out, err = correr("corregir", doc, "--perfil", "apa7", "--fiel", "--out", d / "f.docx")
    code, out, err = correr("comparar", doc, d / "f.docx", "--json", d / "c.json")
    comprobar("texto idéntico: código 0 y mensaje", code == 0 and "fidelidad: texto idéntico" in out, out[:200])
    comprobar("resume los cambios de formato por grupo (márgenes, interlineado)", "formato:" in out and "margen izquierdo" in out and "interlineado" in out, out[-500:])
    j = json.loads((d / "c.json").read_text(encoding="utf-8"))
    comprobar("el JSON trae la lista de cambios de formato", any(c["atributo"] == "margen izquierdo" for c in j["formato"]))
    code, out, err = correr("corregir", doc, "--perfil", "apa7", "--out", d / "c2.docx")
    code, out, err = correr("comparar", doc, d / "c2.docx", "--sin-formato")
    comprobar("texto distinto: código 1 y lista exacta de cambios", code == 1 and "Bibliografía" in out and "Referencias" in out and "texto NO aprobado" in out, out[:300])
    code, out, err = correr("comparar", doc, d / "no-existe.docx")
    comprobar("entrada inexistente: código 2", code == 2)


def main():
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="v10-"))
    try:
        prueba_precedencia(tmp)
        doc, datos = prueba_fiel(tmp)
        prueba_aplicar(tmp, doc, datos)
        prueba_certificado(tmp, doc)
        prueba_calificar(tmp, doc)
        prueba_comparar(tmp, doc)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"\n{'TODO OK' if not FALLOS else 'FALLAN: ' + '; '.join(FALLOS)}")
    sys.exit(0 if not FALLOS else 1)


if __name__ == "__main__":
    main()
