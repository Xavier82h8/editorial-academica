#!/usr/bin/env python3
"""Regresión del perfil de equipo (.editorial.yaml): la excepción institucional quita el hallazgo y lo registra.

tests/ciegos/docs3/apa7_errores.docx (copiado a un temporal con tests/equipo/.editorial.yaml) tiene margen izquierdo de 1.5 in (APA-001). Con tests/equipo/.editorial.yaml
(excepción APA-001 si_contiene «1.5») debe quedar como EXC-APA-001 y no como hallazgo; el resto igual.
"""
import contextlib
import copy
import io
import pathlib
import sys
import tempfile

from docx.oxml.ns import qn

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import auditar  # noqa: E402


def prueba_portada():
    """`portada_numero: no` + portada sin número (primera página distinta): APA-008 de la portada pasa a EXC-APA-008 con
    el motivo institucional; sin yaml (o con `portada_numero: si`) no hay excepción."""
    sys.path.insert(0, str(ROOT / "tests" / "estructura"))
    import crear_maquetacion  # noqa: E402
    fallas = []
    with tempfile.TemporaryDirectory() as tmp:
        for k, (yml, exc) in enumerate([("portada_numero: no\n", True), (None, False), ("portada_numero: si\n", False)]):
            carpeta = pathlib.Path(tmp) / f"c{k}"
            carpeta.mkdir()
            if yml:
                (carpeta / ".editorial.yaml").write_text("perfil: apa7\n" + yml, encoding="utf-8")
            r = auditar.auditar(str(crear_maquetacion.portada(carpeta / "doc.docx", False)), "apa7")
            e = [x for x in r["excepciones"] if x["id"] == "EXC-APA-008"]
            if bool(e) != exc or any(h["id"] == "APA-008" for h in r["hallazgos"]) or (e and e[0]["motivo"] != "la institución pide portada sin número"):
                fallas.append(f"portada yaml={yml!r}: excepciones {[x['id'] for x in r['excepciones']]}, "
                              f"hallazgos {[h['id'] for h in r['hallazgos'] if h['id'] == 'APA-008']}")
    return fallas


def prueba_ith():
    """Perfil institucional TNE ITE (perfiles/instituto-ejemplo-protocolo.editorial.yaml + estructuras/protocolo-instituto-ejemplo.yaml):
    un protocolo generado al vuelo que sigue la guía no tiene hallazgos (solo excepciones institucionales) ni en /auditar ni en
    /estructura; sin el perfil, APA lo reprueba (justificado, numeración…); y las variantes sembradas se detectan."""
    import shutil
    import estructura
    sys.path.insert(0, str(ROOT / "tests" / "estructura"))
    import crear_ith  # noqa: E402
    fallas = []
    perfil = ROOT / "perfiles" / "instituto-ejemplo-protocolo.editorial.yaml"
    with tempfile.TemporaryDirectory() as tmp:
        def doc(nombre, sembrado, con_perfil=True):
            carpeta = pathlib.Path(tmp) / nombre
            carpeta.mkdir()
            if con_perfil:
                shutil.copy(perfil, carpeta / ".editorial.yaml")
            return str(crear_ith.crear(carpeta / "protocolo.docx", sembrado))
        ok = doc("ok", False)
        r = auditar.auditar(ok, "apa7")
        exc = {e["id"] for e in r["excepciones"]}
        if r["hallazgos"] or not {"EXC-APA-004", "EXC-APA-006", "EXC-APA-008", "EXC-APA-030", "EXC-APA-059", "EXC-APA-089"} <= exc:
            fallas.append(f"ITE conforme: hallazgos {[h['id'] for h in r['hallazgos']]}, excepciones {sorted(exc)}")
        e = estructura.revisar(ok, "protocolo-instituto-ejemplo", "apa7")
        if e["hallazgos"] or e["cobertura"] != 1.0:
            fallas.append(f"ITE conforme: estructura {[(h['id'], h['evidencia']) for h in e['hallazgos']]} cobertura {e['cobertura']}")
        sin = {h["id"] for h in auditar.auditar(doc("sin", False, False), "apa7")["hallazgos"]}
        if not {"APA-004", "APA-006", "APA-030", "APA-059"} <= sin:
            fallas.append(f"ITE sin perfil: APA debería reprobarlo, solo {sorted(sin)}")
        mal = doc("mal", True)
        ids = {h["id"] for h in auditar.auditar(mal, "apa7")["hallazgos"]}
        em = estructura.revisar(mal, "protocolo-instituto-ejemplo", "apa7")
        evid = [h["evidencia"] for h in em["hallazgos"] if h["id"] == "EST-004"]
        if not {"IEEE-085", "IEEE-089"} <= ids:
            fallas.append(f"ITE sembrado: faltan IEEE-085/IEEE-089 en {sorted(ids)}")
        if not any(h["id"] == "EST-001" and "Cronograma de actividades" in h["evidencia"] for h in em["hallazgos"]):
            fallas.append("ITE sembrado: falta EST-001 de «Cronograma de actividades»")
        if len(evid) != 2 or not any("palabras clave" in x for x in evid) or not any("palabras (" in x for x in evid):
            fallas.append(f"ITE sembrado: EST-004 esperado para el resumen y las palabras clave, hay {evid}")
        tardia = {h["id"] for h in auditar.auditar(doc("tardia", "tardia"), "apa7")["hallazgos"]}
        if not {"APA-091", "IEEE-092"} <= tardia:
            fallas.append(f"ITE menciones tardías: faltan APA-091/IEEE-092 en {sorted(tardia)}")
    return fallas


def prueba_ins():
    """Reglas institucionales INS-001..009 (bloque `formato:` del perfil ITE): el protocolo conforme no da ningún INS; cada
    variante sembrada da el suyo; sin `formato:` no corre ninguna; /corregir arregla 001/002/003/005/006 y los rótulos IEEE, sin dejar
    hallazgos y sin cambiar nada en una segunda pasada."""
    import re
    import corregir
    sys.path.insert(0, str(ROOT / "tests" / "estructura"))
    import crear_ith  # noqa: E402
    fallas = []
    perfil = (ROOT / "perfiles" / "instituto-ejemplo-protocolo.editorial.yaml").read_text(encoding="utf-8")
    fijo = perfil.replace("  titulo_max_palabras: 20", "  anio_actual: 2026\n  titulo_max_palabras: 20")  # estable aunque pase el año
    sin_formato = re.sub(r"formato:.*?(?=\nexcepciones:)", "", fijo, flags=re.S)
    esperado = {"doble": "INS-001", "izquierda": "INS-002", "minusculas": "INS-003", "sinnumero": "INS-003", "num2": "INS-004",
                "sinsalto": "INS-005", "romanos": "INS-006", "sinreinicio": "INS-006", "titulo": "INS-007", "viejas": "INS-008",
                "persona": "INS-009"}
    with tempfile.TemporaryDirectory() as tmp:
        def doc(nombre, ins, yml=fijo):
            carpeta = pathlib.Path(tmp) / nombre
            carpeta.mkdir()
            (carpeta / ".editorial.yaml").write_text(yml, encoding="utf-8")
            return str(crear_ith.crear(carpeta / "protocolo.docx", False, ins))
        ok = auditar.auditar(doc("ok", ()), "apa7")
        if [h for h in ok["hallazgos"] if h["id"].startswith("INS-")] or ok["hallazgos"]:
            fallas.append(f"INS conforme: hallazgos {[(h['id'], h['evidencia']) for h in ok['hallazgos']]}")
        exc = {e["id"] for e in ok["excepciones"]}
        if not {"EXC-APA-004", "EXC-APA-006", "EXC-APA-030"} <= exc:
            fallas.append(f"INS: las excepciones APA derivadas de formato: no salieron, hay {sorted(exc)}")
        for nombre, regla in esperado.items():
            ids = {h["id"] for h in auditar.auditar(doc(nombre, (nombre,)), "apa7")["hallazgos"]}
            if regla not in ids:
                fallas.append(f"INS sembrado «{nombre}»: falta {regla}, hay {sorted(ids)}")
            otros = {i for i in ids if i.startswith("INS-")} - {regla}
            if otros:
                fallas.append(f"INS sembrado «{nombre}»: INS inesperados {sorted(otros)}")
        ids = {h["id"] for h in auditar.auditar(doc("sinfmt", ("doble", "izquierda", "persona"), sin_formato), "apa7")["hallazgos"]}
        if any(i.startswith("INS-") for i in ids):
            fallas.append(f"INS sin `formato:`: no debería correr ninguna, hay {sorted(i for i in ids if i.startswith('INS-'))}")
        # /corregir sobre un documento no conforme (formato institucional + rótulos APA que el perfil pide en IEEE)
        mal = doc("mal", ("doble", "izquierda", "minusculas", "sinnumero", "sinsalto", "romanos", "sinreinicio", "apa_rotulos"))
        antes = {h["id"] for h in auditar.auditar(mal, "apa7")["hallazgos"]}
        faltan = {"INS-001", "INS-002", "INS-003", "INS-005", "INS-006", "IEEE-085", "IEEE-089"} - antes
        if faltan:
            fallas.append(f"corregir ITE: el documento sembrado no tiene {sorted(faltan)}")
        r = corregir.corregir(mal, "apa7", silencioso=True)
        # EST-017: corregir renumera los encabezados y el índice escrito a mano queda desactualizado (se actualiza en Word)
        if {k: v for k, v in r["despues"].items() if k != "EST-017"}:
            fallas.append(f"corregir ITE: quedan {r['despues']}")
        r2 = corregir.corregir(r["salida"], "apa7", out=str(pathlib.Path(tmp) / "mal" / "segunda.docx"), silencioso=True)
        if r2["aplicadas"] or {k: v for k, v in r2["despues"].items() if k != "EST-017"}:
            fallas.append(f"corregir ITE no es idempotente: {r2['aplicadas']} {r2['despues']}")
        textos = [p.text for p in auditar.abrir_docx(r["salida"]).paragraphs]
        for esp in ("TABLA I", "TABLA II", "Fig. 1. Diagrama de Gantt del proyecto", "1. PRESENTACIÓN DEL PROYECTO", "2. PLANTEAMIENTO DEL PROBLEMA"):
            if esp not in textos:
                fallas.append(f"corregir ITE: falta el párrafo «{esp}»")
        if not any(t.startswith("La TABLA I describe") and "Fig. 1 presenta" in t for t in textos):
            fallas.append("corregir ITE: las menciones «Tabla 1» / «Figura 1» no pasaron a «TABLA I» / «Fig. 1»")
        # sin ninguna numeración (piloto real): una sola pasada numera capítulos (INS-003) y subcapítulos (INS-004)
        sn = doc("sinnum", ("sinnumeracion",))
        r = corregir.corregir(sn, "apa7", silencioso=True)
        if {k: v for k, v in r["despues"].items() if k != "EST-017"}:
            fallas.append(f"corregir ITE sin numeración: quedan {r['despues']} tras una pasada")
        textos = [p.text for p in auditar.abrir_docx(r["salida"]).paragraphs]
        if "2. PLANTEAMIENTO DEL PROBLEMA" not in textos or not any(t.startswith("2.1. ") for t in textos):
            fallas.append("corregir ITE sin numeración: no numeró «2.» ni «2.1.»")
        # interlineado 1.5 institucional con unos párrafos a 1.0 (piloto real, 23-nov: 4 [[PENDIENTE]] nuevos): auditar daba
        # APA-004 «interlineado 1.0», que la excepción derivada (si_contiene 1.5) no cubría, y corregir pasaba todo el cuerpo a
        # doble. APA-004 no debe aplicarse; solo INS-001 lleva esos párrafos a 1.5
        mx = doc("mixto", ())
        dm = auditar.abrir_docx(mx)
        for p in [p for p in dm.paragraphs if len(p.text) > 80][:4]:
            p.paragraph_format.line_spacing = 1.0
        dm.save(mx)
        r = corregir.corregir(mx, "apa7", silencioso=True)
        if "APA-004" in r["aplicadas"]:
            fallas.append(f"corregir ITE mixto: aplicó APA-004 (doble) con interlineado institucional 1.5: {r['aplicadas']}")
        dobles = [p.text[:40] for p in auditar.abrir_docx(r["salida"]).paragraphs
                  if p.paragraph_format.line_spacing is not None and abs(p.paragraph_format.line_spacing - 2.0) < 0.05]
        if dobles or any(h.startswith("INS-001") for h in r["despues"]):
            fallas.append(f"corregir ITE mixto: quedan párrafos a doble {dobles[:3]} o INS-001 {r['despues']}")
        # encabezados a 1.0 con espacio 24/12 pt (piloto real, 24-nov): con interlineado institucional APA-004 no corre y
        # nadie los tocaba; APA-033 los lleva al interlineado del perfil y sin espacio extra
        from docx.shared import Pt
        en = doc("enc10", ())
        de = auditar.abrir_docx(en)
        idx = [i for i, p in enumerate(de.paragraphs) if p.style.name.startswith("Heading")][1:4]
        for i in idx:
            pf = de.paragraphs[i].paragraph_format
            pf.line_spacing, pf.space_before, pf.space_after = 1.0, Pt(24), Pt(12)
        de.save(en)
        if len(idx) < 3 or "APA-033" not in {h["id"] for h in auditar.auditar(en, "apa7")["hallazgos"]}:
            fallas.append("corregir ITE encabezados: el sembrado no da APA-033")
        r = corregir.corregir(en, "apa7", silencioso=True)
        if r["despues"] or "APA-033" not in r["aplicadas"]:
            fallas.append(f"corregir ITE encabezados: aplicadas {r['aplicadas']}, quedan {r['despues']}")
        ps = auditar.abrir_docx(r["salida"]).paragraphs
        mal = [ps[i].text[:40] for i in idx if abs((ps[i].paragraph_format.line_spacing or 0) - 1.5) > 0.05
               or (ps[i].paragraph_format.space_after or 0) > 0]
        if mal:
            fallas.append(f"corregir ITE encabezados: siguen sin 1.5 o con espacio {mal}")
        # INS-008 sobre la literatura actualizable: fundacionales declaradas con motivo y documentales salen del cálculo
        fund = fijo.replace("  fuentes_recientes: {anios: 5, porcentaje: 70, arbitradas: true}",
                            "  fuentes_recientes:\n    anios: 5\n    porcentaje: 70\n    fundacionales:\n"
                            "      - {ref: \"Hernández-Sampieri, R., & Mendoza, C. P. (2013)\", motivo: \"texto de método que se aplica\"}\n"
                            "      - {ref: \"Kurose, J. F., & Ross, K. W. (2011)\", motivo: \"obra original del modelo de capas\"}\n"
                            "      - {ref: \"Pressman, R. S., & Maxim, B. R. (2011)\", motivo: \"proceso de software que se sigue\"}\n"
                            "      - {ref: \"Sommerville, I. (2016)\", motivo: \"modelo de requisitos que se usa\"}\n")
        if fund == fijo:
            fallas.append("INS-008: no se pudo sembrar el bloque fundacionales en el perfil")
        a = auditar.auditar(doc("fund", ("viejas",), fund), "apa7")
        if any(h["id"] == "INS-008" for h in a["hallazgos"]):
            fallas.append(f"INS-008 fundacionales: sigue el hallazgo {[h['evidencia'] for h in a['hallazgos'] if h['id'] == 'INS-008']}")
        if not any("4 fundacionales" in v for v in a["avisos"]) or not any("más del 40 %" in v for v in a["avisos"]):
            fallas.append(f"INS-008 fundacionales: faltan los avisos de exclusión {a['avisos']}")
        sin_motivo = fund.replace(', motivo: "modelo de requisitos que se usa"', "")
        a = auditar.auditar(doc("fund2", ("viejas",), sin_motivo), "apa7")
        if not any(h["id"] == "INS-008" for h in a["hallazgos"]):
            fallas.append("INS-008: una fundacional sin motivo no debe excluirse")
        # una ley de 1996 baja 3/4 (75 %) a 3/5 (60 %) si contara; como documental queda fuera
        ld = doc("ley", ())
        dl = auditar.abrir_docx(ld)
        som = next(p for p in dl.paragraphs if p.text.startswith("Sommerville"))
        nuevo = copy.deepcopy(som._p)
        som._p.addnext(nuevo)
        from docx.text.paragraph import Paragraph
        q = Paragraph(nuevo, som._parent)
        for r in q.runs[1:]:
            r._r.getparent().remove(r._r)
        q.runs[0].text = "Ley Federal del Derecho de Autor. (1996, 24 de diciembre). Diario Oficial de la Federación."
        dl.save(ld)
        a = auditar.auditar(ld, "apa7")
        if any(h["id"] == "INS-008" for h in a["hallazgos"]) or not any("1 documentales" in v for v in a["avisos"]):
            fallas.append(f"INS-008 documental: la ley contó o no se avisó {[h['evidencia'] for h in a['hallazgos'] if h['id'] == 'INS-008']} {a['avisos'][:3]}")
    return fallas


def prueba_ins_nuevas():
    """INS-010 (portada oficial), INS-011 (tipografía de encabezados), INS-012 (resumen), INS-013 (rótulos), EST-017 (índice
    desactualizado), formato vinculante (INS-015) y la protección de la portada y los ámbitos vinculantes en /corregir."""
    import json
    import re
    from lxml import etree
    import corregir
    import institucional
    import maquetacion
    import modelo_formato as MF
    sys.path.insert(0, str(ROOT / "tests" / "estructura"))
    import crear_ith  # noqa: E402
    fallas = []
    perfil = (ROOT / "perfiles" / "instituto-ejemplo-protocolo.editorial.yaml").read_text(encoding="utf-8")
    fijo = perfil.replace("  titulo_max_palabras: 20", "  anio_actual: 2026\n  titulo_max_palabras: 20")
    # seed -> (regla, texto que debe llevar la evidencia)
    esperado = {"sin_titulo": ("INS-010", "título del proyecto"), "sin_leyenda": ("INS-010", "leyenda oficial"),
                "sin_depto": ("INS-010", "departamento"), "fecha_mal": ("INS-010", "03/Noviembre/2026"),
                "sin_control": ("INS-010", "Luis Gómez Ruiz"), "portada_orden": ("INS-010", "fuera de orden"),
                "enc_gris": ("INS-011", "Arial 8 pt color #8C8C8C"), "resumen_sangria": ("INS-012", "sangría de primera línea"),
                "resumen_dos": ("INS-012", "2 párrafos"), "rotulos_12": ("INS-013", "12 pt")}
    with tempfile.TemporaryDirectory() as tmp:
        tmp = pathlib.Path(tmp)

        def doc(nombre, ins, yml=fijo, extra=None):
            carpeta = tmp / nombre
            carpeta.mkdir()
            (carpeta / ".editorial.yaml").write_text(yml, encoding="utf-8")
            for k, v in (extra or {}).items():
                (carpeta / k).write_text(v, encoding="utf-8")
            return str(crear_ith.crear(carpeta / "protocolo.docx", False, ins))
        ok = doc("ok", ())
        r = auditar.auditar(ok, "apa7")
        if r["hallazgos"] or maquetacion.revisar(ok, "apa7"):
            fallas.append(f"INS-010..013 conforme: hallazgos {[(h['id'], h['evidencia']) for h in r['hallazgos']]} {[h['id'] for h in maquetacion.revisar(ok, 'apa7')]}")
        if not any("0 imágenes" in a for a in r["avisos"]):
            fallas.append(f"INS-010: falta el aviso de logotipos {r['avisos']}")
        for nombre, (regla, texto) in esperado.items():
            r = auditar.auditar(doc(nombre, (nombre,)), "apa7")
            hs = [h for h in r["hallazgos"] if h["id"].startswith("INS-")]
            if {h["id"] for h in hs} != {regla}:
                fallas.append(f"{nombre}: se esperaba solo {regla}, hay {[(h['id'], h['evidencia']) for h in hs]}")
            elif not any(texto in h["evidencia"] for h in hs):
                fallas.append(f"{nombre}: la evidencia no menciona «{texto}»: {[h['evidencia'] for h in hs]}")
        # fechas aceptadas y rechazadas, y números de control (marcador pendiente cuenta como falta)
        for t, bien in (("Noviembre 2026", True), ("noviembre de 2026", True), ("03/Noviembre/2026", False), ("03/11/2026", False),
                        ("3 de noviembre de 2026", False)):
            mal = bool(institucional.RE_FECHA_MAL.search(auditar.sin_acentos(t).lower()))
            if mal == bien or (bien and not institucional.RE_MES_ANIO.search(auditar.sin_acentos(t).lower())):
                fallas.append(f"INS-010: la fecha «{t}» se juzgó mal")
        sc = institucional._sin_control(["Integrantes:", "Ana Pérez 21330001", "Luis Gómez B21330002", "Eva Ruiz [[PENDIENTE]]", "Ugo Paz 2133"], [])
        if sc is None or sc[1] != 4 or [x.split()[0] for x in sc[0]] != ["Eva", "Ugo"]:
            fallas.append(f"INS-010: números de control mal contados {sc}")
        # EST-017: índice de contenido y de tablas desactualizados
        for nombre in ("indice_viejo", "indice_tablas"):
            e = [h for h in maquetacion.revisar(doc(nombre, (nombre,)), "apa7") if h["id"] == "EST-017"]
            if len(e) != 1 or "desactualizado" not in e[0]["evidencia"]:
                fallas.append(f"EST-017 «{nombre}»: se esperaba un hallazgo, hay {[h['evidencia'] for h in e]}")
        ev = [h["evidencia"] for h in maquetacion.revisar(doc("iv2", ("indice_viejo",)), "apa7") if h["id"] == "EST-017"][0]
        if "2.1 Antecedentes del prob" not in ev or "1. PRESENTACIÓN DE" not in ev or "sobran" not in ev or "faltan" not in ev:
            fallas.append(f"EST-017: la evidencia debe citar entradas que no existen y encabezados que faltan: {ev}")
        # estructura: encabezados preliminares con estilo propio basado en Heading N (basedOn) o como párrafos centrados en negrita
        import estructura
        for nombre, ins_ in (("pe_ok", ()), ("pe_estilo", ("prelim_estilo",))):
            e = estructura.revisar(doc(nombre, ins_), "protocolo-instituto-ejemplo", "apa7")
            f1 = [h["evidencia"] for h in e["hallazgos"] if h["id"] == "EST-001"]
            if f1 or e["cobertura"] != 1.0:
                fallas.append(f"estructura «{nombre}»: EST-001 {f1}, cobertura {e['cobertura']}")
        pars_pe, _ = auditar.cargar_docx(str(tmp / "pe_estilo" / "protocolo.docx"))
        rs = next(p for p in pars_pe if p["texto"] == "RESUMEN")
        ic = next(p for p in pars_pe if p["texto"] == "ÍNDICE DE CONTENIDO")
        if auditar.nivel_estilo(rs) != 1 or auditar.nivel_estilo(ic) != 1 or not ic["es_titulo"] or ic["estilo"] != "Encabezado preliminar":
            fallas.append(f"nivel_estilo por basedOn: {rs['estilo']} -> {auditar.nivel_estilo(rs)}, {ic['estilo']} -> {auditar.nivel_estilo(ic)}")
        # corregir: INS-011 (fuente del encabezado), INS-012 (sangría del resumen) e INS-013 (tamaño de rótulos), idempotente
        tres = doc("tres", ("enc_gris", "resumen_sangria", "rotulos_12"))
        antes = {h["id"] for h in auditar.auditar(tres, "apa7")["hallazgos"]}
        if not {"INS-011", "INS-012", "INS-013"} <= antes:
            fallas.append(f"corregir INS-011..013: el sembrado no tiene los tres, hay {sorted(antes)}")
        r = corregir.corregir(tres, "apa7", silencioso=True)
        if r["despues"] or not {"INS-011", "INS-012", "INS-013"} <= set(r["aplicadas"]):
            fallas.append(f"corregir INS-011..013: aplicadas {r['aplicadas']}, quedan {r['despues']}")
        r2 = corregir.corregir(r["salida"], "apa7", out=str(tmp / "tres" / "segunda.docx"), silencioso=True)
        if r2["aplicadas"] or r2["despues"]:
            fallas.append(f"corregir INS-011..013 no es idempotente: {r2['aplicadas']} {r2['despues']}")
        d = auditar.abrir_docx(r["salida"])
        runs = [x for x in d.sections[0].header.paragraphs[0].runs if x.text.strip() and x.font.name]
        if not runs or any(x.font.name != "Times New Roman" or x.font.size.pt != 12 or str(x.font.color.rgb) != "000000" for x in runs):
            fallas.append(f"corregir INS-011: el encabezado no quedó en Times New Roman 12 negro: {[(x.font.name, x.font.size, x.font.color.rgb) for x in runs]}")
        # el caso del piloto real: título largo en un solo párrafo centrado, integrantes en una tabla-caja y resumen sin salto propio
        pc = doc("pcaja", ("portada_caja",))
        pars, _ = auditar.cargar_docx(pc)
        k_res = next(p["i"] for p in pars if p["texto"] == "RESUMEN")
        if auditar.fin_portada(pars) != k_res:
            fallas.append(f"fin_portada con título largo centrado: {auditar.fin_portada(pars)} en lugar de {k_res}")
        ids = {h["id"] for h in auditar.auditar(pc, "apa7")["hallazgos"]}
        if "INS-006" in ids or "INS-010" in ids:
            fallas.append(f"portada_caja: la portada no se reconoce, hallazgos {sorted(ids)}")
        r = corregir.corregir(pc, "apa7", silencioso=True)
        if "APA-005" in r["aplicadas"] or "APA-093" in r["aplicadas"]:
            fallas.append(f"corregir tocó la portada: {r['aplicadas']}")

        def cuerpo_sin_sect(ruta, n):
            hijos = [etree.fromstring(etree.tostring(e)) for e in list(auditar.abrir_docx(ruta).element.body)[:n]]
            for e in hijos:
                for sp in e.iter(qn("w:sectPr")):
                    sp.getparent().remove(sp)
            return [etree.tostring(e) for e in hijos]
        n_port = next(i for i, e in enumerate(auditar.abrir_docx(pc).element.body) if e.tag == qn("w:p") and "RESUMEN" in "".join(e.itertext()))
        if cuerpo_sin_sect(pc, n_port) != cuerpo_sin_sect(r["salida"], n_port):
            fallas.append("corregir cambió la portada (párrafos o tabla-caja): debe quedar tal cual")
        tbl = auditar.abrir_docx(r["salida"]).tables[0]._tbl
        if tbl.find(".//" + qn("w:tcBorders") + "/" + qn("w:left")) is None:
            fallas.append("corregir quitó la barra izquierda de la tabla-caja de la portada")
        # formato vinculante: modelo medido de un docx con caja y borde; INS-015 compara líneas, estilo y cajas
        modelo = doc("modelo", ("modelo_caja",))
        spec = MF.medir(modelo, ambito="portada")
        if not any(c["tipo"] == "relleno" and c["color"] == "#F4F6F9" for c in spec["cajas"]) or not any(
                c["tipo"] == "barra_v" and c["lado"] == "izquierda" and c["color"] == "#1B365D" and abs(c["grosor"] - 3) < 0.1 for c in spec["cajas"]):
            fallas.append(f"modelo medir: no se midieron el relleno y la barra izquierda {spec['cajas']}")
        for l in spec["lineas"]:
            if l["texto"] in ("SISTEMA TECNOLÓGICO NACIONAL (EJEMPLO)", "INSTITUTO TECNOLÓGICO DE EJEMPLO", "Departamento de Sistemas y Computación",
                              "Protocolo de Investigación para la asignatura Taller de Investigación I"):
                l["fijo"] = True
            elif l["texto"].startswith("Integrantes"):
                l["campo"] = "integrantes"
        sj = json.dumps(spec, ensure_ascii=False)
        vinc = fijo + ("\nvinculante:\n  - id: portada-modelo\n    origen: \"captura 26-nov\"\n    fecha: 2026-11-26\n    tipo: modelo\n"
                       "    spec: modelo.json\n    ambito: portada\n")
        ex = {"modelo.json": sj}
        i15 = lambda r_: [h for h in r_["hallazgos"] if h["id"] == "INS-015"]  # noqa: E731
        m_ok = auditar.auditar(doc("vok", ("modelo_caja",), vinc, ex), "apa7")
        if i15(m_ok):
            fallas.append(f"INS-015: el propio modelo no debe dar diferencias {[h['evidencia'] for h in i15(m_ok)]}")
        m_mal = auditar.auditar(doc("vmal", (), vinc, ex), "apa7")
        ev = " | ".join(h["evidencia"] for h in i15(m_mal))
        for esp in ("tamaño 12 pt (modelo 14", "color #000000 (modelo #1B365D)", "caja de relleno #F4F6F9 ausente", "borde izquierda #1B365D de 3 pt ausente"):
            if esp not in ev:
                fallas.append(f"INS-015: falta la diferencia «{esp}» en {ev}")
        if not all(h["severidad"] == "mayor" for h in i15(m_mal)):
            fallas.append("INS-015 debe ser mayor")
        m_fal = auditar.auditar(doc("vfal", ("modelo_caja", "sin_leyenda"), vinc, ex), "apa7")
        if not any("línea fija ausente" in h["evidencia"] for h in i15(m_fal)):
            fallas.append(f"INS-015: falta «línea fija ausente» {[h['evidencia'] for h in i15(m_fal)]}")
        arial = doc("varial", ("modelo_caja",), vinc, ex)
        da = auditar.abrir_docx(arial)
        pt = next(p for p in da.paragraphs if p.text.startswith("Sistema web"))
        pt.runs[0].font.name, pt.runs[0].font.bold, pt.runs[0].font.italic = "Arial", False, True
        da.save(arial)
        ev = " | ".join(h["evidencia"] for h in i15(auditar.auditar(arial, "apa7")))
        for esp in ("fuente Arial", "sin negrita", "con cursiva"):
            if esp not in ev:
                fallas.append(f"INS-015: falta la diferencia «{esp}» en {ev}")
        # `vinculante:` inválido: error de uso (código 2) con mensaje claro
        for nombre, bloque, frag in (("v1", "- {id: a, origen: x, fecha: 2026-11-26, tipo: otro}", "`tipo` debe ser modelo o instruccion"),
                                      ("v2", "- {id: a, origen: x, fecha: 2026-11-26, tipo: modelo, spec: no-existe.json}", "spec ilegible"),
                                      ("v3", "- {id: a, origen: x, fecha: 2026-11-26, tipo: instruccion}", "necesita `texto`"),
                                      ("v4", "- {id: a, fecha: 2026-11-26, tipo: instruccion, texto: t, ambito: pagina}", "falta `origen`")):
            d_ = doc(nombre, (), fijo + "\nvinculante:\n  " + bloque + "\n")
            try:
                with contextlib.redirect_stderr(io.StringIO()) as err:
                    auditar.auditar(d_, "apa7")
                fallas.append(f"vinculante inválido ({nombre}) no dio error")
            except SystemExit as e:
                if e.code != 2:
                    fallas.append(f"vinculante inválido ({nombre}): código {e.code}")
                elif frag not in err.getvalue() and not (nombre == "v4" and "falta `origen`" in err.getvalue()):
                    fallas.append(f"vinculante inválido ({nombre}): el mensaje de stderr no dice «{frag}»: {err.getvalue()}")
            try:
                institucional.normalizar({}, yaml_load(bloque), tmp)
            except institucional.ErrorPerfil as e:
                if frag not in str(e) and not (nombre == "v4" and "`ambito`" in str(e)):
                    fallas.append(f"vinculante inválido ({nombre}): mensaje {e}")
        # una instrucción con ámbito protege su sección: corregir no la toca y el aviso la registra
        ins_y = fijo + ("\nvinculante:\n  - {id: resumen-intacto, origen: \"mensaje 26-nov\", fecha: 2026-11-26, tipo: instruccion,"
                        " texto: \"El resumen queda como lo dio el usuario\", ambito: \"seccion:Resumen\"}\n")
        pr = doc("prot", ("resumen_sangria",), ins_y)
        a = auditar.auditar(pr, "apa7")
        if not any("El resumen queda como lo dio el usuario" in v for v in a["avisos"]):
            fallas.append(f"vinculante: el aviso de la instrucción no aparece {a['avisos']}")
        r = corregir.corregir(pr, "apa7", silencioso=True)
        sang = [p for p in auditar.abrir_docx(r["salida"]).paragraphs if p.text.startswith("El presente protocolo propone")]
        if "INS-012" in r["aplicadas"] or "INS-012" not in r["despues"] or not sang or not sang[0].paragraph_format.first_line_indent:
            fallas.append(f"vinculante: corregir tocó el ámbito protegido (aplicadas {r['aplicadas']}, quedan {r['despues']})")
        # medir un PDF (PyMuPDF): líneas con estilo, color, alineación y cajas
        try:
            import fitz
        except ImportError:
            fitz = None
        if fitz:
            pdf = tmp / "modelo.pdf"
            m = fitz.open()
            pg = m.new_page(width=612, height=792)
            pg.draw_rect(fitz.Rect(72, 100, 540, 140), color=None, fill=(0.957, 0.965, 0.976))
            pg.draw_rect(fitz.Rect(72, 100, 75, 140), color=None, fill=(0.106, 0.212, 0.365))
            pg.insert_text((90, 125), "Leyenda oficial", fontname="hebo", fontsize=14, color=(0.106, 0.212, 0.365))
            pg.insert_text((281.3, 200), "Centrado", fontname="helv", fontsize=12)
            m.save(str(pdf))
            m.close()
            sp = MF.medir(pdf)
            l0 = next((l for l in sp["lineas"] if l["texto"] == "Leyenda oficial"), None)
            l1 = next((l for l in sp["lineas"] if l["texto"] == "Centrado"), None)
            if not l0 or abs(l0["pt"] - 14) > 0.2 or not l0["negrita"] or l0["color"] != "#1B365D" or l0["alineacion"] != "izquierda":
                fallas.append(f"medir PDF: línea con estilo mal medida {l0}")
            if not l1 or l1["alineacion"] != "centro" or l1["color"] != "#000000":
                fallas.append(f"medir PDF: línea centrada mal medida {l1}")
            if not any(c["tipo"] == "relleno" and c["color"] == "#F4F6F9" and 0 in c["junto_a"] for c in sp["cajas"]) or not any(
                    c["tipo"] == "barra_v" and c["lado"] == "izquierda" and c["color"] == "#1B365D" for c in sp["cajas"]):
                fallas.append(f"medir PDF: cajas mal medidas {sp['cajas']}")
    return fallas


def yaml_load(texto):
    import yaml
    return yaml.safe_load(texto)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    sys.path.insert(0, str(ROOT / "tests" / "ciegos"))
    import asegurar
    import shutil
    asegurar.asegurar("docs3")
    original = ROOT / "tests" / "ciegos" / "docs3" / "apa7_errores.docx"
    # el .docx se genera al vuelo (deriva de plantillas pandoc no distribuidas); se copia junto al .editorial.yaml
    tmp = pathlib.Path(tempfile.mkdtemp())
    shutil.copy(ROOT / "tests" / "equipo" / ".editorial.yaml", tmp / ".editorial.yaml")
    doc = str(shutil.copy(original, tmp / "apa7_errores.docx"))
    con = auditar.auditar(doc, "apa7")
    sin = auditar.auditar(str(original), "apa7")
    ids_con = sorted(h["id"] for h in con["hallazgos"])
    ids_sin = sorted(h["id"] for h in sin["hallazgos"])
    ok = ("APA-001" in ids_sin and "APA-001" not in ids_con
          and [e["id"] for e in con["excepciones"]] == ["EXC-APA-001"]
          and sorted(ids_con + ["APA-001"]) == ids_sin)
    fallas = prueba_portada() + prueba_ith() + prueba_ins() + prueba_ins_nuevas()
    for f in fallas:
        print("FALLA", f)
    ok = ok and not fallas
    print(("OK " if ok else "FALLA ") + f"== equipo: sin perfil {len(ids_sin)} hallazgos, con perfil {len(ids_con)} + "
          f"{len(con['excepciones'])} excepción institucional; portada_numero: no -> EXC-APA-008; perfil ITE: conforme 0 hallazgos, sembrados detectados; formato institucional INS-001..013 detectado y corregido; portada oficial, índice (EST-017) y formato vinculante (INS-015)")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
