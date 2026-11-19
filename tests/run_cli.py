#!/usr/bin/env python3
"""Convención de CLI: despachador `scripts/editorial.py`, códigos de salida (0/1/2), `--json`, `--perfil` desde
.editorial.yaml y directorio de caché (EDITORIAL_CACHE).

Uso: python -I tests/run_cli.py
Código de salida 0 solo si todo coincide.
"""
import json
import os
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
EDITORIAL = ROOT / "scripts" / "editorial.py"
OK_MD = ROOT / "tests" / "estructura" / "informe_ok.md"
SUBCOMANDOS = ("auditar", "corregir", "puntuar", "estructura", "congruencia", "maquetacion", "afirmaciones", "fuentes",
               "convertir", "render")


def correr(args, cwd=None, env=None, flags=("-I",)):
    r = subprocess.run([sys.executable, *flags, str(EDITORIAL), *args], capture_output=True, text=True, encoding="utf-8",
                       cwd=cwd, env=env)
    return r.returncode, r.stdout, r.stderr


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    fallas = []
    with tempfile.TemporaryDirectory() as tmp:
        # despachador: --help lista los subcomandos, --version lee plugin.json, desde otro cwd, con y sin -I
        version = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"]
        for flags in (("-I",), ()):
            code, out, err = correr(["--help"], cwd=tmp, flags=flags)
            faltan = [c for c in SUBCOMANDOS if c not in out]
            if code != 0 or faltan:
                fallas.append(f"--help {flags}: exit {code}, faltan {faltan}")
            code, out, _ = correr(["--version"], cwd=tmp, flags=flags)
            if code != 0 or version not in out:
                fallas.append(f"--version {flags}: exit {code}, {out!r}")
        for c in SUBCOMANDOS:
            code, _, err = correr([c, "--help"], cwd=tmp)
            if code != 0:
                fallas.append(f"{c} --help: exit {code} {err[-100:]!r}")
        code, _, err = correr(["no-existe"], cwd=tmp)
        if code != 2 or "desconocido" not in err:
            fallas.append(f"subcomando desconocido: exit {code}")
        for opcion in ("--fuentes", "--evidencias", "--congruencia-llm"):  # archivo auxiliar inexistente: 2, sin traceback
            code, _, err = correr(["puntuar", str(OK_MD), "--perfil", "apa7", "--sin-historial", opcion, "no-existe.json"], cwd=tmp)
            if code != 2 or "Traceback" in err or "no existe" not in err:
                fallas.append(f"puntuar {opcion} inexistente: exit {code} {err[-100:]!r}")
        # códigos de salida y --json
        sal = pathlib.Path(tmp) / "a.json"
        code, _, _ = correr(["auditar", str(OK_MD), "--perfil", "apa7", "--json", str(sal)], cwd=tmp)
        if code not in (0, 1) or not sal.exists() or "hallazgos" not in json.loads(sal.read_text(encoding="utf-8")):
            fallas.append(f"auditar --json: exit {code}, json {'sí' if sal.exists() else 'no'}")
        código_h = json.loads(sal.read_text(encoding="utf-8"))["conteo"] if sal.exists() else {}
        esperado = 1 if código_h.get("crítica") or código_h.get("mayor") else 0
        if code != esperado:
            fallas.append(f"auditar: exit {code}, esperado {esperado} con conteo {código_h}")
        for sub_, extra in (("auditar", []), ("render", []), ("corregir", [])):
            code, _, err = correr([sub_, str(OK_MD), *extra], cwd=tmp)
            if code != 2 or "--perfil" not in err:
                fallas.append(f"{sub_} sin --perfil: exit {code}, {err[-100:]!r}")
        # --perfil desde .editorial.yaml
        d = pathlib.Path(tmp) / "proyecto"
        d.mkdir()
        (d / ".editorial.yaml").write_text("perfil: apa7\n", encoding="utf-8")
        md = d / "doc.md"
        md.write_bytes(OK_MD.read_bytes())
        code, out, err = correr(["auditar", str(md)], cwd=tmp)
        if code not in (0, 1) or "DICTAMEN" not in out:
            fallas.append(f"auditar con perfil de .editorial.yaml: exit {code}, {err[-100:]!r}")
        # entrada no soportada o inexistente por el despachador: exit 2, mensaje claro, sin traceback
        for ext, contenido in ((".pdf", b"%PDF-1.4"), (".tex", b"\\documentclass{article}")):
            ruta = pathlib.Path(tmp) / ("x" + ext)
            ruta.write_bytes(contenido)
            for sub_, extra in (("auditar", ["--perfil", "apa7"]), ("puntuar", ["--perfil", "apa7"]),
                                ("estructura", []), ("congruencia", []), ("maquetacion", [])):
                if ext == ".tex" and sub_ != "auditar":
                    continue
                code, _, err = correr([sub_, str(ruta), *extra], cwd=tmp)
                if code != 2 or "formato no soportado" not in err or "Traceback" in err:
                    fallas.append(f"{sub_} {ext}: exit {code}, {err[-100:]!r}")
        code, _, err = correr(["auditar", str(pathlib.Path(tmp) / "no-existe.docx"), "--perfil", "apa7"], cwd=tmp)
        if code != 2 or "no existe" not in err or "Traceback" in err:
            fallas.append(f"auditar inexistente: exit {code}, {err[-100:]!r}")
        code, _, err = correr(["auditar", str(OK_MD), "--perfil", "no-existe"], cwd=tmp)
        if code != 2 or "Traceback" in err:
            fallas.append(f"auditar perfil desconocido: exit {code}, {err[-100:]!r}")
        # códigos 0/1 con documentos de verdad conocida (ronda ciega: correcto = sin hallazgos, errores = críticos o mayores)
        ciegos = ROOT / "tests" / "ciegos" / "docs"
        for nombre, esperado in (("apa7_correcto.docx", 0), ("apa7_errores.docx", 1)):
            if (ciegos / nombre).exists():
                code, _, err = correr(["auditar", str(ciegos / nombre), "--perfil", "apa7"], cwd=tmp)
                if code != esperado:
                    fallas.append(f"auditar {nombre}: exit {code}, esperado {esperado} {err[-100:]!r}")
        # --json en cada subcomando con resultado estructurado: archivo UTF-8 con JSON válido y el mismo código que sin --json
        sembrado = ROOT / "tests" / "estructura" / "maquetacion.docx"
        for sub_, extra in (("congruencia", [str(ROOT / "tests" / "congruencia" / "sembrado.md")]),
                            ("estructura", [str(OK_MD), "--estructura", "informe"]),
                            ("maquetacion", [str(sembrado), "--perfil", "apa7"]),
                            ("puntuar", [str(OK_MD), "--perfil", "apa7", "--sin-historial", "--sin-red"])):
            sal_j = pathlib.Path(tmp) / f"{sub_}.json"
            code, _, err = correr([sub_, *extra, "--json", str(sal_j)], cwd=tmp)
            try:
                datos_j = json.loads(sal_j.read_text(encoding="utf-8"))
            except (OSError, ValueError) as e:
                fallas.append(f"{sub_} --json: exit {code}, sin JSON válido ({type(e).__name__}) {err[-100:]!r}")
                continue
            code_sin, _, _ = correr([sub_, *extra], cwd=tmp)
            if code not in (0, 1) or code != code_sin or not isinstance(datos_j, dict):
                fallas.append(f"{sub_} --json: exit {code} (sin --json {code_sin})")
        # caché: EDITORIAL_CACHE manda; la antigua <plugin>/.cache solo siembra
        cache = pathlib.Path(tmp) / "cache"
        env = dict(os.environ, EDITORIAL_CACHE=str(cache))
        code = subprocess.run([sys.executable, "-I", "-c",
                               "import sys; sys.path.insert(0, sys.argv[1]); import datos; print(datos.dir_cache())",
                               str(ROOT / "scripts")], capture_output=True, text=True, encoding="utf-8", env=env)
        if code.returncode != 0 or pathlib.Path(code.stdout.strip()) != cache:
            fallas.append(f"EDITORIAL_CACHE: {code.stdout!r} {code.stderr[-100:]!r}")
    print("== cli: despachador, --help/--version, códigos de salida, --json, --perfil de .editorial.yaml, EDITORIAL_CACHE")
    for f in fallas:
        print("FALLA", f)
    print(f"{'OK' if not fallas else 'FALLAS'}: {len(fallas)} fallas")
    return 1 if fallas else 0


if __name__ == "__main__":
    sys.exit(main())
