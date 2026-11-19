#!/usr/bin/env python3
"""Regresión de scripts/congruencia.py.

- tests/congruencia/sembrado.md: deben detectarse las 4 incongruencias deterministas de esperado.json
  (la quinta, id "LLM", es para el agente y no es detectable por el script).
- Muestras oficiales (normas/muestras/**/*.docx) y documentos ciegos correctos (tests/ciegos/docs*/**/*_correcto.docx):
  0 hallazgos críticos o mayores (falsos positivos). Los menores se imprimen pero no cuentan.
- tests/congruencia/tabla_repite.docx (generado por generar_con008.py): CON-008 exactamente 1 vez (párrafo que repite la
  Tabla 1) y ninguna en la Tabla 2 (párrafo que resume). Las muestras oficiales/ciegas deben dar 0 CON-008, aunque sea menor.
- tests/congruencia/hilo.docx y hilo_orden.docx (generar_hilo.py): CON-009, CON-018, CON-019 (hueco y orden) y CON-020
  aparecen exactamente donde deben (CON-020 solo en el objetivo sin rastro, no en el que tiene rastro). Las muestras
  oficiales/ciegas deben dar 0 de CON-008/009/018/019/020, aunque sean menores.
Última línea: «== congruencia: sembrado X/4, con008 Z/2, hilo H/6, muestras FP=Y»; salida 0 solo con X=4, Z=2, H=6 e Y=0.
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import congruencia  # noqa: E402
import obtener_normas  # noqa: E402

D = ROOT / "tests" / "congruencia"


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    esperado = json.loads((D / "esperado.json").read_text(encoding="utf-8"))
    deben = {e["id"] for e in esperado if e["id"] != "LLM"}
    r = congruencia.revisar(str(D / "sembrado.md"))
    halladas = {h["id"] for h in r["hallazgos"]}
    x = len(deben & halladas)
    for h in r["hallazgos"]:
        marca = "ok " if h["id"] in deben else "EXTRA"
        print(f"  sembrado {marca} {h['id']} {h['severidad']} | {h['ubicacion'][:50]} | {h['evidencia'][:90]}")
    for f in sorted(deben - halladas):
        print(f"  sembrado FALTA {f}")
    hc = congruencia.revisar(str(D / "tabla_repite.docx"))["hallazgos"]
    c8 = [h for h in hc if h["id"] == "CON-008"]
    z = int(len(c8) == 1 and "Tabla 1" in c8[0]["evidencia"] and "Lectura de la tabla" in c8[0]["ubicacion"]) + int(
        not any("Tabla 2" in h["evidencia"] for h in c8))
    for h in c8:
        print(f"  con008 {h['ubicacion'][:50]} | {h['evidencia'][:90]}")
    hl = 0
    r1 = congruencia.revisar(str(D / "hilo.docx"))["hallazgos"]
    r2 = congruencia.revisar(str(D / "hilo_orden.docx"))["hallazgos"]
    ids1 = [x["id"] for x in r1]
    for q in r1 + r2:
        print(f"  hilo {q['id']} {q['severidad']} | {q['ubicacion'][:45]} | {q['evidencia'][:80]}")
    hl += int(ids1.count("CON-009") == 1)
    hl += int(ids1.count("CON-018") == 1)
    hl += int(sum(x["id"] == "CON-019" and "falta Tabla 3" in x["evidencia"] for x in r1) == 1)
    c20 = [x for x in r1 if x["id"] == "CON-020"]
    hl += int(len(c20) == 1 and "mecanismos" in c20[0]["evidencia"] and "prevalencia" not in c20[0]["evidencia"].split("ni ")[0])
    hl += int(sum(x["id"] == "CON-019" and "Tabla 3 se menciona antes que Tabla 2" in x["evidencia"] for x in r2) == 1)
    hl += int(not any(x["id"] in ("CON-009", "CON-018", "CON-020") for x in r2))
    docs = sorted((obtener_normas.raiz_normas() / "muestras").rglob("*.docx"))
    if not docs:
        print(obtener_normas.aviso_salto("normas/muestras (falsos positivos en muestras oficiales)"))
    for d in sorted((ROOT / "tests" / "ciegos").glob("docs*")):
        docs += sorted(d.rglob("*_correcto.docx"))
    fp = 0
    for f in docs:
        try:
            hs = congruencia.revisar(str(f))["hallazgos"]
        except Exception as e:  # noqa: BLE001
            print(f"  ERROR {f.name}: {e!r}")
            fp += 1
            continue
        for h in hs:
            if h["severidad"] in ("crítica", "mayor") or h["id"] in ("CON-008", "CON-009", "CON-018", "CON-019", "CON-020"):
                fp += 1
                print(f"  FP {f.name}: {h['id']} {h['severidad']} | {h['ubicacion'][:50]} | {h['evidencia'][:100]}")
            else:
                print(f"  (menor) {f.name}: {h['id']} | {h['evidencia'][:100]}")
    print(f"== congruencia: sembrado {x}/{len(deben)}, con008 {z}/2, hilo {hl}/6, muestras FP={fp}")
    sys.exit(0 if x == len(deben) and z == 2 and hl == 6 and fp == 0 else 1)


if __name__ == "__main__":
    main()
