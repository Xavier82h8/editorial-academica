#!/usr/bin/env python3
"""Regresión de la verificación de fuentes V1-V3 (existencia, metadatos, integridad).

Uso: python -I tests/run_fuentes.py [--sin-red]
Casos en tests/fuentes/v123.json (campo `_esperado`): preprint con versión publicada (MusicScaffold),
artículo retractado, entrada correcta, autor/año erróneos y DOI inexistente.
Usa la caché HTTP del usuario (scripts/datos.py: EDITORIAL_CACHE o el directorio del sistema; se siembra desde
<plugin>/.cache si existe; 7 días); con --sin-red solo la caché.
Código de salida 0 solo si todos los casos coinciden.
"""
import hashlib
import json
import os
import pathlib
import sys
import tempfile
import time
import urllib.error

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "skills" / "fuentes-academicas" / "scripts"))
import fuentes as buscar  # noqa: E402


def caso_sin_red():
    """Sin red y sin caché (directorio temporal): V1/V3 deben quedar no_verificado, nunca «verificado»/«no retractada».
    Segundo caso: red caída (urlopen falla) con una respuesta negativa cacheada ya caducada: no se usa y sigue no_verificado."""
    errores = []
    it = {"id": "x", "DOI": "10.1109/5.771073", "title": "Prueba", "type": "article-journal",
          "author": [{"family": "Autor", "given": "A."}], "issued": {"date-parts": [[2000]]}}
    previo = (buscar.CACHE_HTTP, buscar.SIN_RED, buscar.time.sleep, buscar.urllib.request.urlopen)
    with tempfile.TemporaryDirectory() as tmp:
        try:
            buscar.CACHE_HTTP = pathlib.Path(tmp)
            buscar.SIN_RED = True
            r = buscar.verificar_item(it)
            if r.get("estado") != "no_verificado" or r["v3"].get("estado") != "no_verificado":
                errores.append(f"sin red: estado={r.get('estado')} v3={r['v3'].get('estado')} (esperado no_verificado)")
            if not r["ok"] or r["v1"]:
                errores.append("sin red: debe no bloquear (ok=True) y no marcar V1 como comprobado")
            if "sin red" not in (r.get("motivo") or "") or r["v3"].get("avisos"):
                errores.append(f"sin red: motivo inesperado {r.get('motivo')!r}")
            # red caída con negativo caducado
            buscar.SIN_RED = False
            buscar.time.sleep = lambda s: None

            def caido(*a, **k):
                raise urllib.error.URLError("sin conexión simulada")
            buscar.urllib.request.urlopen = caido
            for u in ("https://api.crossref.org/works/" + buscar.urllib.parse.quote(it["DOI"], safe="/"),):
                f = buscar.CACHE_HTTP / (hashlib.sha1(u.encode()).hexdigest() + ".json")
                f.write_text("null", encoding="utf-8")
                viejo = time.time() - buscar.TTL_CACHE - 3600
                os.utime(f, (viejo, viejo))
            r = buscar.verificar_item(it)
            if r.get("estado") != "no_verificado" or r["v3"].get("estado") != "no_verificado" or r["v1"]:
                errores.append(f"red caída + negativo caducado: estado={r.get('estado')} (el 404 caducado no debe valer)")
        finally:
            buscar.CACHE_HTTP, buscar.SIN_RED, buscar.time.sleep, buscar.urllib.request.urlopen = previo
    return errores


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    buscar.SIN_RED = "--sin-red" in sys.argv or os.environ.get("EDITORIAL_SIN_RED") == "1"
    casos = json.loads((ROOT / "tests" / "fuentes" / "v123.json").read_text(encoding="utf-8"))
    fallas = 0
    for it in casos:
        esp = it["_esperado"]
        r = buscar.verificar_item(it)
        errores = []
        if r["ok"] != esp["ok"]:
            errores.append(f"ok={r['ok']} (esperado {esp['ok']})")
        if "preprint" in esp and r["v3"].get("preprint") != esp["preprint"]:
            errores.append("preprint no detectado")
        if "version_publicada" in esp and (r["v3"].get("version_publicada") or "").lower() != esp["version_publicada"].lower():
            errores.append(f"versión publicada {r['v3'].get('version_publicada')} (esperada {esp['version_publicada']})")
        if "aviso" in esp and not any(a["tipo"] == esp["aviso"] for a in r["v3"].get("avisos", [])):
            errores.append(f"falta aviso {esp['aviso']}")
        for campo in esp.get("v2", []):
            if campo not in r["v2"]:
                errores.append(f"V2 no detectó «{campo}»")
        fallas += bool(errores)
        print(("OK   " if not errores else "FALLA"), it["id"], "; ".join(errores))
    sin_red = caso_sin_red()
    print(("OK   " if not sin_red else "FALLA"), "caso sin red y sin caché", "; ".join(sin_red))
    fallas += bool(sin_red)
    print(f"== fuentes V1-V3: {len(casos) + 1 - fallas}/{len(casos) + 1}")
    sys.exit(1 if fallas else 0)


if __name__ == "__main__":
    main()
