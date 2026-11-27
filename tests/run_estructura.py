#!/usr/bin/env python3
"""Regresión del juez de estructura (scripts/estructura.py).

- Muestras oficiales APA empíricas con `articulo-imryd`: cobertura 100 % y sin EST-001/EST-002.
- tests/estructura: informe completo (0 EST-001/002), sin conclusiones (EST-001) y desordenado (EST-002).
- Maquetación (scripts/maquetacion.py): tests/estructura/maquetacion.docx (generado por crear_maquetacion.py) dispara los 6 IDs
  EST-010..EST-015; las muestras oficiales APA (normas/muestras/apa/*/*.docx) no disparan EST-010/011/014/015 y sus únicos
  EST-012/013 son los de MAQUETACION_REAL (las muestras oficiales de Word no fijan keep_with_next ni cantSplit en rótulos,
  imágenes y filas, y una tabla de 22 filas no repite su encabezado: defectos reales de maquetación, no falsos positivos).
- EST-016 (numeración de la portada, fixtures generados en un directorio temporal): portada con número + `portada_numero: no`
  -> EST-016; portada sin número + perfil apa7 sin yaml -> EST-016; portada sin número + `portada_numero: no` -> nada;
  portada con número sin yaml -> sin hallazgo pero maquetacion_info lo informa; IEEE sin yaml -> nada. Las muestras
  oficiales APA (todas llevan número en la portada) no disparan EST-016 (lo cubre MAQUETACION_REAL).
- Las estructuras de estructuras/*.yaml (incluida protocolo-instituto-ejemplo) cargan y tienen secciones obligatorias; EST-004 (límite de palabras del Resumen y palabras clave) lo cubre tests/run_equipo.py con el perfil ITE.
"""
import contextlib
import io
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import estructura  # noqa: E402
import obtener_normas  # noqa: E402
import maquetacion  # noqa: E402
import yaml  # noqa: E402

EMPIRICAS = ["apa/profesional/mixed-methods-professional-paper.docx", "apa/profesional/professional-paper.docx",
             "apa/profesional/qualitative-professional-paper.docx", "apa/profesional/quantitative-professional-paper.docx",
             "apa/estudiante/quantitative-study-student-paper.docx"]
MAQUETACION_REAL = {
    "estudiante/design-student-paper-template.docx": [("EST-012", "Figure 1"), ("EST-012", "Figure 2"), ("EST-012", "Figure 3"),
                                                      ("EST-012", "Figure 4"), ("EST-012", "Figure 5"), ("EST-012", "Figure 6"),
                                                      ("EST-012", "Figure 7")],
    "profesional/mixed-methods-professional-paper.docx": [("EST-012", "Table 1"), ("EST-012", "Table 2"), ("EST-012", "Table 3"),
                                                          ("EST-013", "Table 2")],
    "profesional/professional-paper-annotated.docx": [("EST-012", "Table 1"), ("EST-012", "Figure 1")],
    "profesional/professional-paper.docx": [("EST-012", "Table 1"), ("EST-012", "Figure 1")],
    "profesional/qualitative-professional-paper.docx": [("EST-012", "Table 1"), ("EST-012", "Table 2"), ("EST-012", "Figure 1")],
    "profesional/quantitative-professional-paper.docx": [("EST-012", "Figure 1"), ("EST-012", "Figure 2")],
    "profesional/review-professional-paper.docx": [("EST-012", "Figure 1")],
}
CASOS = [("informe_ok.md", set()), ("informe_sin_conclusiones.md", {"EST-001"}), ("informe_desordenado.md", {"EST-002"})]


def ids(r):
    return {h["id"] for h in r["hallazgos"] if h["id"] in ("EST-001", "EST-002")}


def prueba_portada(fallas):
    sys.path.insert(0, str(ROOT / "tests" / "estructura"))
    import crear_maquetacion  # noqa: E402
    casos = [  # (portada con número, yaml, perfil, EST-016 esperado, portada_numero, preferencia)
        (True, "portada_numero: no\n", "apa7", True, "encabezado", "no"),
        (False, None, "apa7", True, "ninguno", None),
        (False, "portada_numero: no\n", "apa7", False, "ninguno", "no"),
        (False, "portada_numero: si\n", "apa7", True, "ninguno", "si"),
        (True, None, "apa7", False, "encabezado", None),
        (True, "portada_numero: si\n", "apa7", False, "encabezado", "si"),
        (False, None, "ieee", False, "ninguno", None),
        (True, None, "ieee", False, "encabezado", None),
    ]
    with tempfile.TemporaryDirectory() as tmp:
        for k, (con, yml, perfil, esperado, estado, pref) in enumerate(casos):
            carpeta = pathlib.Path(tmp) / f"c{k}"
            carpeta.mkdir()
            if yml:
                (carpeta / ".editorial.yaml").write_text(f"perfil: {perfil}\n" + yml, encoding="utf-8")
            doc = crear_maquetacion.portada(carpeta / "doc.docx", con)
            r = estructura.revisar(str(doc), "informe", None if yml else perfil)
            ids = [h["id"] for h in r["maquetacion"]]
            info = r["maquetacion_info"]
            if ("EST-016" in ids) != esperado or info["portada_numero"] != estado or info["preferencia"] != pref:
                fallas.append(f"portada caso {k} (con={con}, yaml={yml!r}, {perfil}): ids {ids}, info {info}")
    return len(casos)


def prueba_entrada_invalida(fallas):
    """.pdf, archivo inexistente y perfil desconocido: mensaje claro en stderr y exit 2 (sin traceback)."""
    import subprocess
    with tempfile.TemporaryDirectory() as tmp:
        pdf = pathlib.Path(tmp) / "x.pdf"
        pdf.write_bytes(b"%PDF-1.4")
        ok_md = ROOT / "tests" / "estructura" / "informe_ok.md"
        casos = []
        for s, extra in (("auditar", ["--perfil", "apa7"]), ("congruencia", []), ("estructura", []), ("maquetacion", []),
                         ("puntuar", ["--perfil", "apa7"]), ("corregir", ["--perfil", "apa7"]), ("afirmaciones", [])):
            casos.append((f"{s} .pdf", [s, str(pdf), *extra], "formato no soportado"))
            casos.append((f"{s} inexistente", [s, str(pdf.with_name("no.docx")), *extra], "no existe"))
        casos.append(("auditar perfil desconocido", ["auditar", str(ok_md), "--perfil", "nope"], "Perfiles válidos: apa7"))
        for nombre, args, msg in casos:
            r = subprocess.run([sys.executable, "-I", str(ROOT / "scripts" / (args[0] + ".py")), *args[1:]],
                               capture_output=True, text=True, encoding="utf-8")
            if r.returncode != 2 or msg not in r.stderr or "Traceback" in r.stderr:
                fallas.append(f"{nombre}: exit {r.returncode}, stderr {r.stderr[-120:]!r}")
    return len(casos)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    fallas = []
    n_portada = prueba_portada(fallas)
    n_inv = prueba_entrada_invalida(fallas)
    gen = sorted((ROOT / "estructuras").glob("*.yaml"))
    for g in gen:
        d = yaml.safe_load(g.read_text(encoding="utf-8"))
        if not any(s.get("obligatoria") for s in d["secciones"]):
            fallas.append(f"{g.stem}: sin secciones obligatorias")
    muestras = obtener_normas.raiz_normas() / "muestras"
    n_emp = 0
    for m in EMPIRICAS:
        if not (muestras / m).is_file():
            continue
        n_emp += 1
        r = estructura.revisar(str(muestras / m), "articulo-imryd")
        if r["cobertura"] < 1 or ids(r):
            fallas.append(f"{m}: cobertura {r['cobertura']}, {sorted(ids(r))}")
    if n_emp < len(EMPIRICAS):
        print(obtener_normas.aviso_salto("normas/muestras (muestras IMRyD)") + f" [{len(EMPIRICAS) - n_emp}/{len(EMPIRICAS)}]")
    for f, esperado in CASOS:
        r = estructura.revisar(str(ROOT / "tests" / "estructura" / f), "informe")
        if ids(r) != esperado:
            fallas.append(f"{f}: {sorted(ids(r))} (esperado {sorted(esperado)})")
    n_maq = 0
    sys.path.insert(0, str(ROOT / "tests" / "estructura"))
    import crear_maquetacion  # noqa: E402
    tmp_maq = tempfile.TemporaryDirectory()  # el sembrado se regenera en un temporal: no ensucia el árbol de git
    sembrado = pathlib.Path(tmp_maq.name) / "maquetacion.docx"
    with contextlib.redirect_stdout(io.StringIO()):
        crear_maquetacion.main(sembrado)
    r = estructura.revisar(str(sembrado), "informe", "apa7")
    got = {h["id"] for h in r["maquetacion"]}
    falta = {f"EST-01{i}" for i in range(6)} - got
    if falta or {h["id"] for h in r["hallazgos"] if h["id"].startswith("EST-01")} != got:
        fallas.append(f"maquetacion.docx: faltan {sorted(falta)}; got {sorted(got)}")
    ieee = {h["id"] for h in estructura.revisar(str(sembrado), "informe", "ieee")["maquetacion"]}
    if ieee != got:
        fallas.append(f"maquetacion.docx perfil ieee: {sorted(ieee)} != {sorted(got)}")
    muestras_apa = sorted((muestras / "apa").glob("*/*.docx"))
    if not muestras_apa:
        print(obtener_normas.aviso_salto("normas/muestras/apa (maquetación de muestras)"))
    for f in muestras_apa:
        rel = f.relative_to(muestras / "apa").as_posix()
        obt = [(h["id"], h["ubicacion"]) for h in maquetacion.revisar(str(f), "apa7")]
        n_maq += 1
        if obt != MAQUETACION_REAL.get(rel, []):
            fallas.append(f"{rel}: maquetación {obt} (esperado {MAQUETACION_REAL.get(rel, [])})")
    tmp_maq.cleanup()
    for x in fallas:
        print("FALLA", x)
    print(f"== estructura: {len(gen)} géneros, {len(EMPIRICAS)} muestras IMRyD, {len(CASOS)} casos, "
          f"maquetación {n_maq} muestras APA + docx sembrado, EST-016 {n_portada} casos, entradas inválidas {n_inv} casos, {len(fallas)} fallas")
    sys.exit(1 if fallas else 0)


if __name__ == "__main__":
    main()
