#!/usr/bin/env python3
"""Metadatos canónicos por DOI (content negotiation de doi.org -> CSL-JSON), con caché en disco.

Uso:
  python -I doi_csl.py --doi 10.1037/ppm0000185 [--sin-red]

(Antes `scripts/buscar.py`; se renombró para no chocar con skills/fuentes-academicas/scripts/fuentes.py, que busca y verifica
fuentes. Este módulo solo trae el CSL-JSON de un DOI para /convertir y refs_csl; no se duplica con fuentes.py, que usa
Crossref/OpenAlex y otro formato de metadatos.)

Importable: csl_por_doi(doi, sin_red=False) -> dict CSL-JSON | None
- Solo se envía el DOI a doi.org (no se envía texto del documento ni datos personales).
- User-Agent genérico, sin correo. Timeout corto y un reintento.
- Caché: <dir de caché del usuario>/doi/<doi>.json (ver datos.py: EDITORIAL_CACHE o el directorio del sistema).
  Un 404 también se cachea (el DOI no existe).
- Salida: 0 con el CSL-JSON; 1 si el DOI no existe (o no está en caché con --sin-red); 2 si no hay red.
"""
import argparse
import hashlib
import json
import pathlib
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import datos  # noqa: E402

CACHE = datos.dir_cache() / "doi"
UA = "editorial-academica/0.1"
TIMEOUT = 10


def normalizar_doi(doi):
    d = doi.strip()
    d = re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", "", d, flags=re.I)
    return d.strip().rstrip(".,;)")


def _ruta_cache(doi):
    nombre = re.sub(r"[^a-z0-9._-]", "_", doi.lower())[:120] + "-" + hashlib.sha1(doi.lower().encode()).hexdigest()[:8]
    return CACHE / (nombre + ".json")


def csl_por_doi(doi, sin_red=False):
    """CSL-JSON del DOI, o None si no existe / no hay red / no está en caché con --sin-red."""
    doi = normalizar_doi(doi)
    ruta = _ruta_cache(doi)
    if ruta.exists():
        try:
            d = json.loads(ruta.read_text(encoding="utf-8"))
            return None if d.get("_no_encontrado") else d
        except (OSError, ValueError):
            pass
    if sin_red:
        return None
    url = "https://doi.org/" + urllib.parse.quote(doi, safe="/:()-._;")
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.citationstyles.csl+json", "User-Agent": UA})
    ultimo = None
    for intento in range(2):
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                datos = json.loads(r.read().decode("utf-8"))
            CACHE.mkdir(parents=True, exist_ok=True)
            ruta.write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")
            return datos
        except urllib.error.HTTPError as e:
            if e.code == 404:
                CACHE.mkdir(parents=True, exist_ok=True)
                ruta.write_text(json.dumps({"_no_encontrado": True}), encoding="utf-8")
                return None
            ultimo = e
        except (urllib.error.URLError, TimeoutError, ValueError, OSError) as e:
            ultimo = e
        time.sleep(1.0)
    raise RuntimeError(f"doi.org no respondió para {doi}: {ultimo}")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--doi", required=True)
    p.add_argument("--sin-red", action="store_true", help="solo caché")
    a = p.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    try:
        d = csl_por_doi(a.doi, a.sin_red)
    except RuntimeError as e:
        print(e, file=sys.stderr)
        sys.exit(2)
    if d is None:
        print("DOI no encontrado (o no está en caché con --sin-red)", file=sys.stderr)
        sys.exit(1)
    print(json.dumps(d, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
