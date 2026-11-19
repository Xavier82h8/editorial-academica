#!/usr/bin/env python3
"""Regresión del perfil de equipo (.editorial.yaml): la excepción institucional quita el hallazgo y lo registra.

tests/ciegos/docs3/apa7_errores.docx (copiado a un temporal con tests/equipo/.editorial.yaml) tiene margen izquierdo de 1.5 in (APA-001). Con tests/equipo/.editorial.yaml
(excepción APA-001 si_contiene «1.5») debe quedar como EXC-APA-001 y no como hallazgo; el resto igual.
"""
import pathlib
import sys
import tempfile

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
    fallas = prueba_portada()
    for f in fallas:
        print("FALLA", f)
    ok = ok and not fallas
    print(("OK " if ok else "FALLA ") + f"== equipo: sin perfil {len(ids_sin)} hallazgos, con perfil {len(ids_con)} + "
          f"{len(con['excepciones'])} excepción institucional; portada_numero: no -> EXC-APA-008")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
