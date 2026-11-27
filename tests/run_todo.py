#!/usr/bin/env python3
"""Regresión única: encadena CSL, citas en texto, juez sobre docs sembrados y rondas ciegas.

Uso: python -I tests/run_todo.py [--rapido] [--sin-red]   (--rapido omite las puertas que llaman a pandoc: CSL, citas,
/convertir y referencias en español)
Código de salida 0 solo si todas las puertas pasan. Pensado para CI y antes de cada commit.

Puertas (no pueden bajar respecto al estado del 18-nov-2026):
- CSL APA 7: 82/82 exactos (IGUAL). CSL IEEE: >= 63/67 IGUAL o IGUAL-TEXTO, 0 ERROR.
- Citas en texto: 0 DIFIERE y 0 ERROR (run_citas.py sale con 0).
- Juez: precisión y recall >= 0.95 en tests/docs y en cada tests/ciegos/docs*/ con esperado.json.
- /convertir (tests/run_convertir.py): parser de referencias APA/IEEE con apellidos, año y título >= 0.95 y el resto >= 0.85;
  ida y vuelta de citas >= 0.95 (mismo perfil y cruzado APA<->IEEE).
- Muestras oficiales (normas/muestras: APA estudiante y profesional, plantillas Word de IEEE): los hallazgos de `auditar.py`
  deben ser exactamente los de VERDADEROS_POSITIVOS (errores reales de las propias muestras, con su justificación); todo
  lo demás es falso positivo y la puerta falla.
- Informativa (no bloquea): tests/run_real.py, borrador sintético de estudiante vs su verdad esperada (recall mecánico seguro >= 0.90, 0 FP);
  evalúa además los json de tests/reales/privado/ (ignorada por git) si existen.
- Sin normas/ (repo público; ver scripts/obtener_normas.py) las puertas que leen normas/ se saltan con «SALTADA: …» y no fallan;
  con --sin-red (o EDITORIAL_SIN_RED=1) no hay red: la caché HTTP se siembra desde tests/fixtures/http y el proxy se deshabilita.
  EDITORIAL_NORMAS apunta las pruebas a otra carpeta de normas.
"""
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import obtener_normas  # noqa: E402

MUESTRAS = obtener_normas.raiz_normas() / "muestras"  # EDITORIAL_NORMAS o <plugin>/normas
FIXTURES_HTTP = ROOT / "tests" / "fixtures" / "http"
# Errores reales de las propias muestras oficiales (documento -> [(id, texto que debe aparecer en la evidencia)]).
VERDADEROS_POSITIVOS = {
    # doble espacio tras punto («severe.  They authors»): APA 6.1 / APA-115
    "annotated-bibliography-student-paper.docx": [("APA-115", "severe.  They"),
                                                  # «pp. 107-115»: rango de páginas con guion en vez de raya en (APA-074)
                                                  ("APA-074", "107-115")],
    # márgenes de 0.94/0.19/0.93/0.9 in en la sección de portada y resumen (APA 2.22: 1 in)
    "design-student-paper-template.docx": [("APA-001", "0.19"),
                                           # cita «(History of Quill Pens, n.d.)» pero la lista tiene a «History of Pencils» como autor
                                           ("APA-034", "Pens, n.d."), ("APA-034", "History of Pencils"),
                                           # nota de figura «by A. Westra, 2023» frente a la lista «Westra, A. (2020)»
                                           ("APA-034", "Westra (2020)"),
                                           # «Topic Background» (nivel 1) con un único subencabezado, «Shang Writing» (APA 2.26 / APA-032)
                                           ("APA-032", "Topic Background")],
    # la «E» de «Emotion Review» no está en cursiva (APA 9.25: título de la revista en cursiva)
    "literature-review-professional-paper.docx": [("APA-072", "Emotion Review")],
    # «(Simmons & Smiley, 2010)» sin entrada en la lista (APA 8.3)
    "mixed-methods-professional-paper.docx": [("APA-034", "Simmons, 2010")],
    # párrafo vacío suelto entre dos párrafos de texto (APA 2.21)
    "professional-paper.docx": [("APA-005", "vacíos")],
    "professional-paper-annotated.docx": [("APA-005", "vacíos")],
    # «Pew Research Center, 2017» frente a la lista (2019)
    "qualitative-professional-paper.docx": [("APA-035", "Center, 2017")],
    # «(Beach, 1989)» frente a la lista «Beach, R. (1986)»
    "review-professional-paper.docx": [("APA-035", "Beach, 1989"),
                                       # «Course Design» y «Outcomes» (nivel 1) con un único subencabezado cada uno (APA-032)
                                       ("APA-032", "Course Design")],
    # «email address  or ORCID»: doble espacio entre palabras en el texto de ejemplo (IEEE-140; la plantilla Letter ya lo corrigió)
    "conference-template-a4.docx": [("IEEE-140", "email address  or ORCID")] * 2,
}
PY = [sys.executable, "-I"]
SIN_RED = "--sin-red" in sys.argv or os.environ.get("EDITORIAL_SIN_RED") == "1"
ENV = None      # entorno de los subprocesos; con --sin-red se rellena en main() (caché sembrada, proxy muerto)
SALTOS = []     # líneas «SALTADA: …» de la puerta en curso (las imprime el propio script o la puerta)
UMBRAL_CSL = {"apa7": ("IGUAL", 82), "ieee": ("IGUAL+TEXTO", 63)}


def correr(args):
    r = subprocess.run(PY + args, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", env=ENV)
    salida = r.stdout + r.stderr
    SALTOS.extend(l.strip() for l in salida.splitlines() if l.strip().startswith("SALTADA:"))
    return r.returncode, salida


def entorno_sin_red(tmp):
    """Entorno sin red: caché de usuario sembrada con tests/fixtures/http y proxy muerto (una fuga falla en vez de pasar)."""
    cache = pathlib.Path(tmp) / "cache"
    shutil.copytree(FIXTURES_HTTP, cache)
    muerto = "http://127.0.0.1:9"
    return dict(os.environ, EDITORIAL_CACHE=str(cache), EDITORIAL_SIN_RED="1", HTTP_PROXY=muerto, HTTPS_PROXY=muerto,
                http_proxy=muerto, https_proxy=muerto, NO_PROXY="", no_proxy="")


def puerta_csl():
    _, out = correr(["tests/run_csl.py"])
    fallas = []
    for norma, (modo, minimo) in UMBRAL_CSL.items():
        m = re.search(r"== " + norma + r" \([^)]*\): \{'IGUAL': (\d+), 'IGUAL-TEXTO': (\d+), 'DIFIERE': (\d+), 'ERROR': (\d+)\}", out)
        if not m:
            fallas.append(f"{norma}: no se pudo leer el resumen")
            continue
        igual, texto, _, error = map(int, m.groups())
        valor = igual if modo == "IGUAL" else igual + texto
        if valor < minimo or error:
            fallas.append(f"{norma}: {modo}={valor} (mínimo {minimo}), ERROR={error}")
    return not fallas, "; ".join(fallas) or "APA 82/82, IEEE >= 63/67"


def puerta_es():
    code, out = correr(["tests/run_es.py"])
    return code == 0, out.strip().splitlines()[-1] if out.strip() else "sin salida"


def puerta_fuentes():
    code, out = correr(["tests/run_fuentes.py"] + (["--sin-red"] if SIN_RED else []))
    return code == 0, out.strip().splitlines()[-1] if out.strip() else "sin salida"


def puerta_sustento():
    code, out = correr(["tests/run_sustento.py"])
    return code == 0, out.strip().splitlines()[-1] if out.strip() else "sin salida"


def puerta_congruencia():
    code, out = correr(["tests/run_congruencia.py"])
    lineas = [l for l in out.strip().splitlines() if l.startswith("== congruencia")]
    resumen = lineas[-1] if lineas else (out.strip().splitlines() or ["sin salida"])[-1]
    if code:
        resumen += "\n" + "\n".join(l for l in out.splitlines() if "FP " in l or "FALTA" in l or "ERROR" in l)
    return code == 0, resumen


def puerta_estructura():
    code, out = correr(["tests/run_estructura.py"])
    return code == 0, out.strip().splitlines()[-1] if out.strip() else "sin salida"


def puerta_equipo():
    code, out = correr(["tests/run_equipo.py"])
    return code == 0, out.strip().splitlines()[-1] if out.strip() else "sin salida"


def puerta_cli():
    code, out = correr(["tests/run_cli.py"])
    return code == 0, out.strip().splitlines()[-1] if out.strip() else "sin salida"


def puerta_ejemplo():
    code, out = correr(["tests/run_ejemplo.py"])
    return code == 0, " | ".join(l for l in out.strip().splitlines() if l.startswith(("==", "FALLO", "OK"))) or "sin salida"


def puerta_portabilidad():
    code, out = correr(["tests/run_portabilidad.py"])
    return code == 0, out.strip().splitlines()[-1] if out.strip() else "sin salida"


def puerta_v07():
    """v0.7: título concreto (CON-021, INS-010), niveles de fuentes, --desde-docx, verificación de normas ISO/IEC, repasar y posición del número de página."""
    code, out = correr(["tests/run_v07.py"])
    return code == 0, chr(10).join(l for l in out.splitlines() if l.startswith(("FALLA", "== v0.7"))) or out.strip()[-300:]


def puerta_v08():
    """v0.8: portada y salida (portada, indices, entregar), `fuentes --reemplazar` y bloque `fuentes:` del perfil (FUE-NIV)."""
    code, out = correr(["tests/run_v08.py"])
    return code == 0, chr(10).join(l for l in out.splitlines() if l.startswith(("FALLA", "SALTADA", "== v0.8"))) or out.strip()[-300:]


def puerta_v09():
    """v0.9: `medir` (ficha de medidas efectivas, PDF), reglas del usuario medibles (INS-016), equivalencias y tolerancias, exportación con historial."""
    code, out = correr(["tests/run_v09.py"])
    return code == 0, chr(10).join(l for l in out.splitlines() if l.startswith(("FALLA", "SALTADA", "== v0.9"))) or out.strip()[-300:]


def puerta_perfilar():
    """`/perfilar`: guía sintética (.docx y PDF) -> perfil y estructura con origen, preguntas, sin sobrescribir, modelo de portada, inglés."""
    code, out = correr(["tests/run_perfilar.py"])
    ok = code == 0
    extra = ""
    dorada = ROOT / "tests" / "reales" / "privado" / "run_perfilar_dorada.py"
    if dorada.exists():  # prueba dorada LOCAL con la guía real (no se distribuye; se salta sola si falta el archivo de la guía)
        c2, o2 = correr([str(dorada.relative_to(ROOT))])
        ok = ok and c2 == 0
        extra = " | dorada local: " + (o2.strip().splitlines() or [""])[-1]
    return ok, chr(10).join(l for l in out.splitlines() if l.startswith(("FALLA", "SALTADA", "== perfilar"))) + extra


def puerta_puntuar():
    code, out = correr(["tests/run_puntuar.py"] + (["--sin-red"] if SIN_RED else []))
    return code == 0, out.strip().splitlines()[-1] if out.strip() else "sin salida"


def puerta_corregir():
    code, out = correr(["tests/run_corregir.py"])
    return code == 0, out.strip().splitlines()[-1] if out.strip() else "sin salida"


def puerta_citas():
    code, out = correr(["tests/run_citas.py"])
    res = re.findall(r"== citas (\w+): (\{[^}]*\})", out)
    return code == 0, " ".join(f"{n} {d}" for n, d in res) or out[-300:]


def puerta_convertir():
    """/convertir: ida y vuelta del parser de referencias (apellidos, año, título >= 0.95; resto >= 0.85) y de las citas (>= 0.95)."""
    code, out = correr(["tests/run_convertir.py"])
    filas = re.findall(r"== parser (\w+) \((\d+) referencias\)((?:\n  .*)+)", out)
    partes = []
    for norma, n, cuerpo in filas:
        v = {m[0]: float(m[1]) for m in re.findall(r"^\s+(\S+)\s+\d+/\d+\s+=\s+([\d.]+)", cuerpo, re.M)}
        partes.append(f"{norma} apellidos {v.get('apellidos', 0):.2f} año {v.get('año', 0):.2f} título {v.get('título', 0):.2f}")
    citas = [float(x) for x in re.findall(r"=\s+([\d.]+)\s+\[(?:OK|BAJO)[^\]]*\]", out.split("== citas")[-1])] if "== citas" in out else []
    if citas:
        partes.append(f"citas min {min(citas):.2f} ({len(citas)} rutas)")
    return code == 0, "; ".join(partes) or out[-300:]


def puerta_reglas_apa():
    """Reglas APA finas (APA-015/039/041/044/063/066): 0 FP en las 83 referencias oficiales y casos sembrados exactos."""
    code, out = correr(["tests/run_reglas_apa.py"])
    return code == 0, out.strip().splitlines()[-1] if out.strip() else "sin salida"


def puerta_reglas_tanda2():
    """Reglas de la tanda 2 (APA-048/064/074/080/081/103, IEEE-007/015/031/032/070/129): 0 FP en los corpus oficiales y casos sembrados exactos."""
    code, out = correr(["tests/run_reglas_tanda2.py"])
    return code == 0, out.strip().splitlines()[-1] if out.strip() else "sin salida"


def puerta_juez(dir_=None):
    args = ["tests/run_juez.py"] + (["--dir", str(dir_)] if dir_ else [])
    code, out = correr(args)
    m = re.search(r"precisión=([\d.]+) recall=([\d.]+)", out)
    resumen = m.group(0) if m else out[-300:]
    if code:
        resumen += "\n" + "\n".join(l for l in out.splitlines() if "FALLA" in l or l.lstrip().startswith(("FP ", "FN ")))
    return code == 0, resumen


def puerta_muestras():
    """Muestras oficiales: sin falsos positivos; los hallazgos deben coincidir con VERDADEROS_POSITIVOS."""
    if obtener_normas.falta("muestras"):
        SALTOS.append(obtener_normas.aviso_salto("normas/muestras"))
        return True, "sin muestras oficiales que auditar"
    import auditar
    docs = [(f, "apa7") for f in sorted((MUESTRAS / "apa" / "estudiante").glob("*.docx"))]
    docs += [(f, "apa7-profesional") for f in sorted((MUESTRAS / "apa" / "profesional").glob("*.docx"))]
    docs += [(f, "ieee") for f in sorted((MUESTRAS / "ieee" / "conference-word").rglob("*.docx"))]
    fallas, total_fp, total_tp = [], 0, 0
    for f, perfil in docs:
        try:
            hallazgos = auditar.auditar(str(f), perfil)["hallazgos"]
        except Exception as e:  # noqa: BLE001
            fallas.append(f"{f.name}: ERROR {e!r}")
            continue
        esperados = list(VERDADEROS_POSITIVOS.get(f.name, []))
        for h in hallazgos:
            k = next((e for e in esperados if e[0] == h["id"] and e[1] in h["evidencia"] + h["ubicacion"]), None)
            if k:
                esperados.remove(k)
                total_tp += 1
            else:
                total_fp += 1
                fallas.append(f"{f.name}: FP {h['id']} {h['ubicacion'][:40]} | {h['evidencia'][:60]}")
        fallas += [f"{f.name}: FN {e[0]} {e[1]}" for e in esperados]
    resumen = f"{len(docs)} muestras, {total_tp} verdaderos positivos esperados, {total_fp} falsos positivos"
    return not fallas, resumen + ("\n" + "\n".join("  " + x for x in fallas) if fallas else "")


def puerta_real():
    """Informativa: borrador sintético (y, si existe tests/reales/privado/, el real) vs verdad esperada (recall mecánico seguro >= 0.90, 0 FP)."""
    code, out = correr(["tests/run_real.py"])
    m = re.search(r"recall seguro\+mecánico = ([\d.]+) \((\d+/\d+)\)", out)
    fp = re.search(r"falsos positivos sobre IDs que cumplen = (\d+)", out)
    return code == 0, (f"recall mecánico seguro={m.group(1)} ({m.group(2)}), falsos positivos={fp.group(1)}" if m and fp else out[-300:])


def construir_pruebas(rapido):
    """Lista (nombre, función) de las puertas; la reutiliza scripts/estadisticas.py."""
    pruebas = []
    if not rapido:
        pruebas += [("CSL vs corpus dorado", puerta_csl), ("Citas en texto", puerta_citas),
                    ("/convertir: parser de referencias y citas", puerta_convertir),
                    ("Referencias en español (es-MX) y fechas", puerta_es)]
    pruebas.append(("Fuentes V1-V3 (existencia, metadatos, retractación, preprint)", puerta_fuentes))
    pruebas.append(("Fuentes V5 sustento (cifras y veredictos)", puerta_sustento))
    pruebas.append(("Congruencia: determinista CON-001..009 y 018..020 (CON-010..017 son del agente)", puerta_congruencia))
    pruebas.append(("Estructura por género (7 géneros, muestras IMRyD)", puerta_estructura))
    pruebas.append(("Perfil de equipo (excepción institucional)", puerta_equipo))
    pruebas.append(("CLI: despachador, códigos de salida, --json, caché", puerta_cli))
    pruebas.append(("Portabilidad: skills, rutas, instalador, catálogo REGLAS.md", puerta_portabilidad))
    pruebas.append(("Ejemplo del README (ejemplos/): cifras publicadas", puerta_ejemplo))
    pruebas.append(("v0.7: título, niveles de fuentes, --desde-docx, normas ISO, repasar, paginación", puerta_v07))
    pruebas.append(("v0.8: portada, índices, entregar, fuentes --reemplazar, bloque fuentes: del perfil", puerta_v08))
    pruebas.append(("v0.9: medir, reglas medibles del usuario (INS-016), unidades y tolerancias, exportación con historial", puerta_v09))
    pruebas.append(("/perfilar: guía -> reglas con origen, preguntas, sin sobrescribir", puerta_perfilar))
    pruebas.append(("/puntuar estable y sensible", puerta_puntuar))
    pruebas.append(("Corrector de formato docx (corregir.py)", puerta_corregir))
    pruebas.append(("Reglas APA finas: corpus oficial 0 FP y casos sembrados", puerta_reglas_apa))
    pruebas.append(("Reglas tanda 2: corpus oficiales 0 FP y casos sembrados", puerta_reglas_tanda2))
    pruebas.append(("Juez: errores sembrados", puerta_juez))
    pruebas.append(("Juez: muestras oficiales", puerta_muestras))
    sys.path.insert(0, str(ROOT / "tests" / "ciegos"))
    import asegurar  # no se versionan (plantillas derivadas de pandoc): se regeneran si faltan
    asegurar.asegurar()
    for d in sorted((ROOT / "tests" / "ciegos").glob("docs*")):
        if (d / "esperado.json").exists():
            pruebas.append((f"Juez: ronda ciega {d.name}", lambda d=d: puerta_juez(d)))
    return pruebas


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    pruebas = construir_pruebas("--rapido" in sys.argv)
    ok_total = True
    global ENV
    tmp_red = tempfile.TemporaryDirectory() if SIN_RED else None
    if SIN_RED:
        ENV = entorno_sin_red(tmp_red.name)
        os.environ["EDITORIAL_CACHE"] = ENV["EDITORIAL_CACHE"]  # también para lo que corra en este proceso
        print("(sin red: caché sembrada desde tests/fixtures/http, proxy deshabilitado)")
    saltadas = 0
    for nombre, fn in pruebas:
        SALTOS.clear()
        ok, detalle = fn()
        ok_total &= ok
        if ok and SALTOS:
            saltadas += 1
            detalle += " | " + SALTOS[0]
        print(f"[{'SALTADA' if ok and SALTOS else 'OK' if ok else 'FALLA'}] {nombre}: {detalle}")
    SALTOS.clear()
    ok, detalle = puerta_real()  # informativa: no cambia el código de salida
    print(f"[{'OK' if ok else 'AVISO'}] Juez: boceto real sintético (informativa): {detalle}")
    if tmp_red:
        tmp_red.cleanup()
    print((f"\nTODO OK ({saltadas} saltadas)" if saltadas else "\nTODO OK") if ok_total else "\nHAY FALLAS")
    sys.exit(0 if ok_total else 1)


if __name__ == "__main__":
    main()
