#!/usr/bin/env python3
"""Entrega: del .docx de trabajo al .docx y .pdf finales, verificados, en un solo comando.

Uso:
  python scripts/editorial.py entregar <doc.docx> [--perfil ID] [--paginacion encabezado-derecha|pie-derecha|pie-centro|ninguna]
                              [--portada-numero si|no] [--campo nombre=valor ...] [--equipo .editorial.yaml] [--out RUTA.docx]
                              [--sin-capturas] [--json RUTA]

Pasos, en este orden (cada uno trabaja sobre el resultado del anterior; el original nunca se toca):
  1. corregir    formato mecánico (`corregir.py`; con --paginacion y --portada-numero como allí)
  2. portada     solo si `formato: portada: campos:` del perfil la declara: se construye desde el perfil y el modelo vinculante
                 (`portada.py`; --campo pasa los valores, p. ej. los números de control)
  3. indices     contenido (campo TOC), tablas y figuras con páginas medidas (`indices.py`)
  4. PDF         LibreOffice del resultado
  5. capturas    PNG de la portada y de las páginas preliminares (carpeta `<doc>.entrega.capturas/`)
  6. verificar   los números de los índices contra el PDF final; auditar + estructura + puntuar sobre el resultado
Deja juntos `<doc>.entrega.docx` y `<doc>.entrega.pdf` (o la ruta de --out) y un resumen con los hallazgos y el puntaje.
Salida: 0 sin hallazgos críticos; 1 si quedan críticos (p. ej. EA-001: un `[[PENDIENTE]]` que no se rellenó); 2 error de uso o falta
LibreOffice o PyMuPDF (el PDF es parte de la entrega).
"""
import argparse
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import auditar  # noqa: E402
import cli  # noqa: E402
import indices  # noqa: E402
import libreoffice  # noqa: E402
from docx import Document  # noqa: E402

EDITORIAL = HERE / "editorial.py"


def correr(cmd, *args):
    """(código, salida) de `editorial.py <cmd> …` en un proceso aparte."""
    r = subprocess.run([sys.executable, "-I", str(EDITORIAL), cmd, *map(str, args)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def ultima(salida, n=3):
    return " | ".join(l.strip() for l in salida.strip().splitlines()[-n:])


def capturas(pdf, docx, destino, avisos):
    """PNG de la portada y de las hojas preliminares (número visible en romanos). Devuelve las rutas."""
    fitz = libreoffice.requerir_pymupdf()
    doc = Document(str(docx))
    pgs = indices.paginas_pdf(pdf)
    vis = indices.visibles(pgs, indices.secciones(doc), avisos)
    elegidas = [0] + [j for j, v in enumerate(vis) if j and re.fullmatch(r"[ivxlcdm]+", v)]
    destino.mkdir(parents=True, exist_ok=True)
    out = []
    with fitz.open(str(pdf)) as d:
        for j in elegidas[:12]:
            nombre = "portada.png" if j == 0 else f"preliminar-{vis[j]}.png"
            ruta = destino / nombre
            d[j].get_pixmap(dpi=80).save(str(ruta))
            out.append(str(ruta))
    return out


def entregar(documento, perfil, paginacion=None, portada_numero=None, campos=(), equipo=None, salida=None, con_capturas=True):
    auditar.validar_entrada(documento, (".docx",))
    libreoffice.requerir()
    libreoffice.requerir_pymupdf()
    entrada = pathlib.Path(documento).resolve()
    out = pathlib.Path(salida).resolve() if salida else entrada.with_name(entrada.stem + ".entrega.docx")
    if out == entrada:
        cli.error("la salida coincide con el original: la entrega nunca se escribe sobre el original (usa --out distinto)")
    ruta_eq = auditar.buscar_equipo(str(entrada), equipo)
    f, _av = auditar.formato_equipo(str(entrada), equipo)
    tiene_portada = bool(((f or {}).get("portada") or {}).get("campos"))
    pasos, avisos = [], []
    eq_args = ["--equipo", str(ruta_eq)] if ruta_eq else []
    # carpeta de trabajo junto al original: corregir busca el .editorial.yaml hacia arriba desde su salida y así mide con el mismo perfil
    with tempfile.TemporaryDirectory(prefix=".entrega-", dir=str(entrada.parent)) as tmp:
        tmp = pathlib.Path(tmp)
        actual = entrada
        # 1. corregir
        args = [str(actual), "--perfil", perfil, "--out", str(tmp / "1-corregido.docx"), "--json", str(tmp / "corregir.json")] + eq_args
        if paginacion:
            args += ["--paginacion", paginacion]
        if portada_numero:
            args += ["--portada-numero", portada_numero]
        code, sal = correr("corregir", *args)
        if code == 2 or not (tmp / "1-corregido.docx").exists():
            cli.error("corregir falló: " + ultima(sal))
        res_c = json.loads((tmp / "corregir.json").read_text(encoding="utf-8")) if (tmp / "corregir.json").exists() else {}
        pasos.append({"paso": "corregir", "codigo": code, "detalle": f"{sum(res_c.get('antes', {}).values())} -> {sum(res_c.get('despues', {}).values())} hallazgos"
                      if res_c else ultima(sal, 1)})
        actual = tmp / "1-corregido.docx"
        # 2. portada
        if tiene_portada:
            args = [str(actual), "--out", str(tmp / "2-portada.docx"), "--perfil", perfil, "--json", str(tmp / "portada.json")] + eq_args
            for c in campos:
                args += ["--campo", c]
            code, sal = correr("portada", *args)
            if code == 2 or not (tmp / "2-portada.docx").exists():
                cli.error("portada falló: " + ultima(sal))
            rp = json.loads((tmp / "portada.json").read_text(encoding="utf-8")) if (tmp / "portada.json").exists() else {}
            pasos.append({"paso": "portada", "codigo": code, "detalle": f"{len(rp.get('hallazgos', []))} diferencias INS-010/INS-015, {rp.get('pendientes', 0)} campos pendientes"})
            avisos += rp.get("avisos", [])
            actual = tmp / "2-portada.docx"
        else:
            pasos.append({"paso": "portada", "codigo": 0, "detalle": "el perfil no declara `formato: portada:`: se deja la portada como está"})
        # 3. índices
        code, sal = correr("indices", str(actual), "--out", str(tmp / "3-indices.docx"), "--json", str(tmp / "indices.json"), *eq_args)
        if code == 2 or not (tmp / "3-indices.docx").exists():
            cli.error("indices falló: " + ultima(sal))
        ri = json.loads((tmp / "indices.json").read_text(encoding="utf-8")) if (tmp / "indices.json").exists() else {}
        pasos.append({"paso": "indices", "codigo": code, "detalle": f"{ri.get('encabezados', 0)} encabezados, {ri.get('tablas', 0)} tablas, {ri.get('figuras', 0)} figuras; "
                      f"{ri.get('vueltas', '?')} vueltas, {'convergió' if ri.get('convergio') else 'NO convergió'}"})
        avisos += ri.get("avisos", [])
        shutil.copyfile(str(tmp / "3-indices.docx"), str(out))
    # 4. PDF junto al .docx
    pdf = libreoffice.a_pdf(out, out.parent)
    pasos.append({"paso": "pdf", "codigo": 0, "detalle": str(pdf)})
    # 5. capturas
    caps = []
    if con_capturas:
        caps = capturas(pdf, out, out.with_name(out.stem + ".capturas"), avisos)
        pasos.append({"paso": "capturas", "codigo": 0, "detalle": f"{len(caps)} PNG en {out.with_name(out.stem + '.capturas')}"})
    # 6. verificar
    dif, av_i, n_i = indices.comprobar(out, pdf)
    pasos.append({"paso": "indices vs PDF", "codigo": 1 if dif else 0, "detalle": f"{len(dif)} distintos de {n_i} entradas" if dif else f"los {n_i} números coinciden"})
    code_a, _ = correr("auditar", str(out), "--perfil", perfil, "--json", str(out.with_name(out.stem + ".auditoria.json")), *eq_args)
    aud = json.loads(out.with_name(out.stem + ".auditoria.json").read_text(encoding="utf-8"))
    out.with_name(out.stem + ".auditoria.json").unlink()
    code_e, sal_e = correr("estructura", str(out), "--perfil", perfil, "--json", str(out.with_name(out.stem + ".estructura.json")))
    est = {}
    ruta_e = out.with_name(out.stem + ".estructura.json")
    if ruta_e.exists():
        est = json.loads(ruta_e.read_text(encoding="utf-8"))
        ruta_e.unlink()
    code_p, sal_p = correr("puntuar", str(out), "--perfil", perfil, "--sin-historial", "--json", str(out.with_name(out.stem + ".puntaje.json")), *eq_args)
    pun = {}
    ruta_p = out.with_name(out.stem + ".puntaje.json")
    if ruta_p.exists():
        pun = json.loads(ruta_p.read_text(encoding="utf-8"))
        ruta_p.unlink()
    conteo = aud.get("conteo", {})
    criticos = [h for h in aud.get("hallazgos", []) if h["severidad"] == "crítica"]
    pasos.append({"paso": "auditar", "codigo": code_a, "detalle": f"{conteo.get('crítica', 0)} críticos, {conteo.get('mayor', 0)} mayores, {conteo.get('menor', 0)} menores"})
    pasos.append({"paso": "estructura", "codigo": code_e, "detalle": f"cobertura {est.get('cobertura', '?')}, {len(est.get('hallazgos', []))} hallazgos de estructura, "
                  f"{len(est.get('maquetacion', []))} de maquetación"})
    pasos.append({"paso": "puntuar", "codigo": code_p, "detalle": f"{pun.get('total', '?')}/100 {pun.get('banda', '')}"})
    return {"docx": str(out), "pdf": str(pdf), "capturas": caps, "pasos": pasos, "avisos": avisos + av_i, "criticos": criticos,
            "hallazgos": aud.get("hallazgos", []), "puntaje": pun.get("total"), "indices_distintos": dif}


def main(argv=None):
    ap = argparse.ArgumentParser(prog="editorial entregar", description="corregir, portada, índices, PDF, capturas y auditoría: deja .entrega.docx y .entrega.pdf.")
    ap.add_argument("documento")
    ap.add_argument("--perfil", help="id de perfil; por defecto el `perfil:` de .editorial.yaml")
    ap.add_argument("--paginacion", choices=("encabezado-derecha", "encabezado", "pie-derecha", "pie-centro", "pie", "ninguna"))
    ap.add_argument("--portada-numero", choices=("si", "no"), dest="portada_numero")
    ap.add_argument("--campo", action="append", default=[], metavar="NOMBRE=VALOR", help="valor de un campo de la portada (repetible; ver `editorial.py portada --help`)")
    ap.add_argument("--equipo", help="ruta de .editorial.yaml (si no, se busca hacia arriba desde el documento)")
    ap.add_argument("--out", metavar="RUTA.docx", help="salida (por defecto <doc>.entrega.docx; el PDF lleva el mismo nombre)")
    ap.add_argument("--sin-capturas", action="store_true", dest="sin_capturas")
    ap.add_argument("--json", metavar="RUTA")
    a = ap.parse_args(argv)
    cli.utf8()
    perfil = cli.perfil_por_defecto(ap, a.perfil, a.documento, a.equipo)
    r = entregar(a.documento, perfil, a.paginacion, a.portada_numero, a.campo, a.equipo, a.out, not a.sin_capturas)
    print("ENTREGA")
    for p in r["pasos"]:
        print(f"  {p['paso']:<16} {'ok' if p['codigo'] == 0 else 'código ' + str(p['codigo']):<9} {p['detalle']}")
    print(f"  docx: {r['docx']}\n  pdf:  {r['pdf']}")
    for av in r["avisos"][:10]:
        print("aviso:", av)
    for h in r["criticos"][:8]:
        print(f"CRÍTICO {h['id']}: {h['ubicacion']}: {h['evidencia']}")
    if len(r["criticos"]) > 8:
        print(f"  … y {len(r['criticos']) - 8} críticos más")
    for h in r["hallazgos"]:
        if h["severidad"] == "mayor":
            print(f"mayor {h['id']}: {h['ubicacion']}: {h['evidencia']}")
    cli.escribir_json(a.json, r)
    if r["criticos"]:
        print(f"quedan {len(r['criticos'])} hallazgos críticos: la entrega no está lista")
        return cli.HALLAZGOS
    print("sin hallazgos críticos")
    return cli.OK


if __name__ == "__main__":
    sys.exit(main())
