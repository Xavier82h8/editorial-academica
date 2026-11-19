#!/usr/bin/env python3
"""Reconstruye `normas/` en local (en el repo público solo viven RECURSOS.md, SHA256SUMS y VERSION).

`normas/` contiene material con copyright de APA e IEEE (guías, muestras, plantillas): no se redistribuye. Este script lo
descarga de su fuente pública y verifica cada archivo con los SHA-256 de `normas/SHA256SUMS`, `normas/muestras/SHA256SUMS`
y `normas/ieee/SHA256SUMS`. Las URLs salen de las tablas de `normas/RECURSOS.md` (filas con la ruta `normas/...` y la URL).

Uso:
  python scripts/obtener_normas.py                 descarga lo que falta y verifica
  python scripts/obtener_normas.py --lista         imprime qué falta y cómo obtenerlo (no descarga)
  python scripts/obtener_normas.py --comprobar     solo verifica los hashes de lo presente (no descarga)
  python scripts/obtener_normas.py --destino DIR   reconstruye en DIR en vez de normas/ (o EDITORIAL_NORMAS)
  python scripts/obtener_normas.py --solo TEXTO    limita a las rutas que contengan TEXTO (repetible)

Reglas: nunca sobrescribe un archivo con hash correcto; baja a un temporal y solo lo mueve si el hash coincide; reintenta
con un User-Agent de navegador si el primero es rechazado; lo que bloquea bots (403, 202, Incapsula/Cloudflare) se lista
como «paso manual: abre <url> en el navegador y guarda en <ruta>»; los zip de plantillas ya presentes se extraen archivo a
archivo (sin extractall). Los snapshots convertidos (apa/pages, apa/blog, ieee/actual, *.txt) no se reconstruyen byte a
byte por URL: se regeneran con /actualizar-normas.

Otros scripts y pruebas usan `raiz_normas()` (EDITORIAL_NORMAS o <plugin>/normas) y `falta()` para saltarse con aviso lo que
necesita normas/.
Salida: 0 todo presente y verificado; 1 faltan archivos o hay hashes distintos; 2 error de uso.
"""
import argparse
import hashlib
import os
import pathlib
import re
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
MANIFIESTO = ROOT / "normas"
UA_HONESTO = "editorial-academica/obtener_normas (descarga de normas oficiales para pruebas locales)"
UA_NAVEGADOR = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/130.0.0.0 Safari/537.36")
BLOQUEO = (202, 401, 403, 429, 503)

# Archivos que salen de un zip ya presente (prefijo relativo a normas/ -> zip relativo a normas/).
DERIVADOS = {
    "muestras/ieee/conference-latex/": "muestras/ieee/conference-latex-template_10-17-19.zip",
    "muestras/ieee/conference-word/": "muestras/ieee/Conference-Templates-Word.zip",
}
# Dónde bajar a mano lo que no tiene URL directa o la bloquea (prefijo -> página).
PAGINAS = [
    ("muestras/apa/estudiante/", "https://apastyle.apa.org/style-grammar-guidelines/paper-format/sample-papers"),
    ("muestras/apa/profesional/", "https://apastyle.apa.org/style-grammar-guidelines/paper-format/sample-papers"),
    ("muestras/apa/", "https://apastyle.apa.org/instructional-aids"),
    ("muestras/ieee/", "https://www.ieee.org/conferences/publishing/templates.html"),
    ("ieee/", "https://journals.ieeeauthorcenter.ieee.org/create-your-ieee-journal-article/authoring-tools-and-templates/"
              "tools-for-ieee-authors/ieee-article-templates/"),
]
# Snapshots convertidos: no se bajan por URL (se regeneran con /actualizar-normas).
SNAPSHOTS = ("apa/pages/", "apa/blog/", "apa/idx.html", "ieee/actual/")


def raiz_normas():
    """Raíz de normas para pruebas y scripts: EDITORIAL_NORMAS si está definida; si no, <plugin>/normas."""
    env = os.environ.get("EDITORIAL_NORMAS")
    return pathlib.Path(env).expanduser() if env else MANIFIESTO


def falta(*rel, patron="*.docx"):
    """True si bajo raiz_normas()/rel no hay ningún archivo que cumpla `patron` (p. ej. falta('muestras'))."""
    base = raiz_normas().joinpath(*rel)
    return not (base.is_dir() and any(base.rglob(patron)))


def aviso_salto(que="normas/muestras"):
    return f"SALTADA: falta {que} (python scripts/obtener_normas.py)"


def sha256(ruta):
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def _rel_segura(rel):
    p = pathlib.PurePosixPath(rel)
    return None if p.is_absolute() or ".." in p.parts or not p.parts else p.as_posix()


def leer_sumas(manifiesto):
    """{ruta relativa a normas/: sha256} de los tres SHA256SUMS (rutas relativas a su carpeta, `./x` o `normas/x`)."""
    sumas = {}
    for sub in ("", "muestras", "ieee"):
        f = manifiesto / sub / "SHA256SUMS" if sub else manifiesto / "SHA256SUMS"
        if not f.is_file():
            continue
        for linea in f.read_text(encoding="utf-8", errors="replace").splitlines():
            m = re.match(r"^([0-9a-fA-F]{64})\s+\*?(.+?)\s*$", linea)
            if not m:
                continue
            ruta = m.group(2).replace("\\", "/")
            ruta = ruta[len("normas/"):] if ruta.startswith("normas/") else "/".join(x for x in (sub, ruta.removeprefix("./")) if x)
            ruta = _rel_segura(ruta)
            if ruta:
                sumas[ruta] = m.group(1).lower()
    return sumas


def leer_urls(manifiesto):
    """{ruta relativa a normas/: url} de las filas `| `normas/...` | https://... |` de RECURSOS.md."""
    f = manifiesto / "RECURSOS.md"
    urls = {}
    if f.is_file():
        for m in re.finditer(r"\|\s*`normas/([^`]+)`\s*\|\s*(https?://[^\s|]+)", f.read_text(encoding="utf-8", errors="replace")):
            ruta = _rel_segura(m.group(1))
            if ruta:
                urls[ruta] = m.group(2).rstrip(".,;")
    return urls


def _pagina(rel):
    return next((p for pref, p in PAGINAS if rel.startswith(pref)), None)


def _derivado(rel):
    for pref, zip_rel in DERIVADOS.items():
        if rel.startswith(pref):
            return pref, zip_rel
    return None


def _descargar(url, destino, esperado):
    """Descarga `url` a `destino` solo si el hash coincide. Devuelve (ok, motivo)."""
    ultimo = "sin respuesta"
    for ua in (UA_HONESTO, UA_NAVEGADOR):
        req = urllib.request.Request(url, headers={"User-Agent": ua, "Accept": "*/*", "Accept-Language": "en-US,en;q=0.9"})
        tmp = None
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                if r.status in BLOQUEO:
                    ultimo = f"HTTP {r.status} (anti-bots)"
                    continue
                datos = r.read()
        except urllib.error.HTTPError as e:
            ultimo = f"HTTP {e.code}" + (" (anti-bots)" if e.code in BLOQUEO else "")
            if e.code in BLOQUEO:
                continue
            return False, ultimo
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            return False, f"sin red o conexión rechazada ({type(e).__name__})"
        if hashlib.sha256(datos).hexdigest() != esperado:
            ultimo = f"el contenido no coincide con el SHA-256 ({len(datos)} B; probable desafío anti-bots)"
            continue
        destino.parent.mkdir(parents=True, exist_ok=True)
        try:
            with tempfile.NamedTemporaryFile(dir=destino.parent, delete=False, suffix=".part") as t:
                tmp = pathlib.Path(t.name)
                t.write(datos)
            os.replace(tmp, destino)
        finally:
            if tmp and tmp.exists():
                tmp.unlink()
        return True, "descargado"
    return False, ultimo


def _extraer(rel, pref, zip_ruta, destino, esperado):
    """Extrae un solo miembro del zip a `destino` si su hash coincide."""
    miembro = rel[len(pref):]
    try:
        with zipfile.ZipFile(zip_ruta) as z:
            datos = z.read(miembro)
    except (OSError, KeyError, zipfile.BadZipFile) as e:
        return False, f"no se pudo leer {miembro} del zip ({type(e).__name__})"
    if hashlib.sha256(datos).hexdigest() != esperado:
        return False, "el miembro del zip no coincide con el SHA-256"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(datos)
    return True, "extraído del zip"


def estado(rel, esperado, base):
    f = base / rel
    if not f.is_file():
        return "falta"
    return "ok" if sha256(f) == esperado else "distinto"


def clasificar(rel, urls):
    if rel in urls:
        return "url"
    if _derivado(rel):
        return "zip"
    if rel.startswith(SNAPSHOTS):
        return "snapshot"
    return "manual"


def main(argv=None):
    for flujo in (sys.stdout, sys.stderr):
        try:
            flujo.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(description="Reconstruye normas/ en local y verifica SHA-256 (ver la docstring del script).")
    ap.add_argument("--destino", help="carpeta donde reconstruir (por defecto EDITORIAL_NORMAS o <plugin>/normas)")
    ap.add_argument("--manifiesto", default=str(MANIFIESTO), help="carpeta con RECURSOS.md y los SHA256SUMS (por defecto <plugin>/normas)")
    ap.add_argument("--lista", action="store_true", help="imprime qué falta y cómo obtenerlo; no descarga")
    ap.add_argument("--comprobar", action="store_true", help="solo verifica los hashes de lo presente; no descarga")
    ap.add_argument("--solo", action="append", default=[], metavar="TEXTO", help="limita a las rutas que contengan TEXTO")
    a = ap.parse_args(argv)
    manifiesto = pathlib.Path(a.manifiesto)
    base = pathlib.Path(a.destino).expanduser() if a.destino else raiz_normas()
    sumas = leer_sumas(manifiesto)
    if not sumas:
        print(f"error: no hay SHA256SUMS en {manifiesto}", file=sys.stderr)
        return 2
    urls = leer_urls(manifiesto)
    rutas = sorted(r for r in sumas if not a.solo or any(s in r for s in a.solo))
    if not rutas:
        print(f"error: --solo {a.solo} no coincide con ninguna ruta del manifiesto", file=sys.stderr)
        return 2

    ok = distintos = 0
    faltan = {"url": [], "zip": [], "snapshot": [], "manual": []}
    for rel in rutas:
        est = estado(rel, sumas[rel], base)
        if est == "ok":
            ok += 1
        elif est == "distinto":
            distintos += 1
            print(f"HASH DISTINTO: normas/{rel} (no coincide con SHA256SUMS)")
            if not (a.comprobar or a.lista) and rel in urls:
                faltan["url"].append(rel)  # se intenta bajar de nuevo a un temporal; solo reemplaza si el hash coincide
        else:
            faltan[clasificar(rel, urls)].append(rel)

    if not (a.comprobar or a.lista):
        # 1) URLs directas; 2) zip ya presentes (incluidos los recién bajados); 3) lo que quede va a pasos manuales
        for rel in list(faltan["url"]):
            bien, motivo = _descargar(urls[rel], base / rel, sumas[rel])
            print(f"{'OK  ' if bien else 'FALLA'} normas/{rel}: {motivo}" + ("" if bien else f" [{urls[rel]}]"))
            if bien:
                ok += 1
                faltan["url"].remove(rel)
        for rel in list(faltan["zip"]):
            pref, zip_rel = _derivado(rel)
            if not (base / zip_rel).is_file():
                continue
            bien, motivo = _extraer(rel, pref, base / zip_rel, base / rel, sumas[rel])
            if bien:
                ok += 1
                faltan["zip"].remove(rel)
            else:
                print(f"FALLA normas/{rel}: {motivo}")
        distintos = sum(estado(r, sumas[r], base) == "distinto" for r in rutas)

    if a.comprobar:
        print(f"== comprobar: {ok} archivos con hash correcto, {distintos} con hash distinto, "
              f"{sum(len(v) for v in faltan.values())} ausentes (no se descargan con --comprobar) [{base}]")
        return 1 if distintos else 0

    # informe de lo que falta
    n_falta = 0
    for rel in faltan["url"]:
        n_falta += 1
        print(f"FALTA (descargable): normas/{rel} <- {urls[rel]}" if a.lista else
              f"paso manual: abre {urls[rel]} en el navegador y guarda en {base / rel}")
    for rel in faltan["zip"]:
        n_falta += 1
        pref, zip_rel = _derivado(rel)
        print(f"FALTA (se extrae de normas/{zip_rel} cuando exista): normas/{rel}" if a.lista else
              f"paso manual: consigue normas/{zip_rel} y vuelve a correr este script (extrae {rel})")
    for rel in faltan["manual"]:
        n_falta += 1
        pag = _pagina(rel) or "https://apastyle.apa.org/ o https://www.ieee.org/"
        print(f"FALTA (manual): normas/{rel}" if a.lista else f"paso manual: abre {pag} en el navegador y guarda en {base / rel}")
    if faltan["snapshot"]:
        grupos = {}
        for rel in faltan["snapshot"]:
            grupos.setdefault(next(p for p in SNAPSHOTS if rel.startswith(p)), []).append(rel)
        for pref, lst in sorted(grupos.items()):
            n_falta += len(lst)
            print(f"SNAPSHOT: {len(lst)} archivo(s) de normas/{pref}: no se bajan por URL (copia convertida a Markdown/texto); "
                  "regenerar con /actualizar-normas")
    total = len(rutas)
    print(f"== normas [{base}]: {ok}/{total} verificados, {distintos} con hash distinto, {n_falta} ausentes")
    return 1 if (n_falta or distintos) else 0


if __name__ == "__main__":
    sys.exit(main())
