#!/usr/bin/env python3
"""Directorio de datos del usuario (caché de red) fuera del plugin.

Orden: `EDITORIAL_CACHE` si está definida; si no, el directorio de caché del sistema:
  - Windows: %LOCALAPPDATA%/editorial-academica/cache
  - macOS:   ~/Library/Caches/editorial-academica
  - Linux:   ${XDG_CACHE_HOME:-~/.cache}/editorial-academica

Migración: si existe la caché antigua `<plugin>/.cache` y el directorio nuevo no existe (o está vacío), se copia como
semilla: no se pierde la caché tibia (las pruebas `--sin-red` dependen de ella). La antigua no se borra.

El historial de /puntuar (`.editorial/puntajes.jsonl`) NO va aquí: es del proyecto del usuario y vive junto al documento
(desactivable con `puntuar --sin-historial`).
"""
import os
import pathlib
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
CACHE_ANTIGUA = ROOT / ".cache"


def dir_cache():
    """Directorio de caché del usuario (se crea al primer uso; ver la docstring del módulo)."""
    env = os.environ.get("EDITORIAL_CACHE")
    if env:
        base = pathlib.Path(env).expanduser()
    elif sys.platform == "win32":
        base = pathlib.Path(os.environ.get("LOCALAPPDATA") or (pathlib.Path.home() / "AppData" / "Local")) / "editorial-academica" / "cache"
    elif sys.platform == "darwin":
        base = pathlib.Path.home() / "Library" / "Caches" / "editorial-academica"
    else:
        base = pathlib.Path(os.environ.get("XDG_CACHE_HOME") or (pathlib.Path.home() / ".cache")) / "editorial-academica"
    _migrar(base)
    return base


def _migrar(base):
    if not CACHE_ANTIGUA.is_dir() or (base.exists() and any(base.iterdir())):
        return
    try:
        shutil.copytree(CACHE_ANTIGUA, base, dirs_exist_ok=True)
    except OSError:
        pass  # sin permiso o disco lleno: la caché se reconstruye con la red
