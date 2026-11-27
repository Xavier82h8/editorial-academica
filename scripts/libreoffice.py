#!/usr/bin/env python3
"""LibreOffice (soffice) como herramienta externa: ubicarlo y convertir un .docx a PDF con un perfil de usuario propio.

Lo usan `portada.py`, `indices.py` y `entregar.py`. Sin LibreOffice, `requerir()` sale con código 2 y un mensaje claro
(instalación por sistema); `buscar()` devuelve None. Un perfil de usuario temporal evita tocar el de LibreOffice del usuario y
chocar con una instancia abierta.
"""
import atexit
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cli  # noqa: E402

INSTALAR = ("LibreOffice (soffice) no está instalado: winget install TheDocumentFoundation.LibreOffice | "
            "brew install --cask libreoffice | apt install libreoffice")


def buscar():
    """Ruta de soffice o None. Orden: EDITORIAL_SOFFICE, el PATH, rutas habituales de Windows y macOS."""
    env = os.environ.get("EDITORIAL_SOFFICE")
    if env and pathlib.Path(env).is_file():
        return env
    for c in ("soffice", "libreoffice"):
        r = shutil.which(c)
        if r:
            return r
    for c in (r"C:\Program Files\LibreOffice\program\soffice.exe", r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
              "/Applications/LibreOffice.app/Contents/MacOS/soffice"):
        if pathlib.Path(c).is_file():
            return c
    return None


def requerir():
    """soffice o error de uso (código 2) con instrucciones de instalación."""
    r = buscar()
    if not r:
        cli.error(INSTALAR)
    return r


_PERFIL = None


def _perfil_usuario():
    """Perfil de usuario de LibreOffice propio y reutilizado durante todo el proceso (el primer arranque es lo lento)."""
    global _PERFIL
    if _PERFIL is None or not _PERFIL.exists():
        _PERFIL = pathlib.Path(tempfile.mkdtemp(prefix="editorial-lo-"))
        atexit.register(shutil.rmtree, str(_PERFIL), True)
    return _PERFIL


def a_pdf(docx, salida_dir=None, tiempo=240):
    """Convierte `docx` a PDF y devuelve la ruta del PDF (en `salida_dir` o una carpeta temporal nueva). Error 2 si falla."""
    soffice = requerir()
    docx = pathlib.Path(docx)
    salida_dir = pathlib.Path(salida_dir) if salida_dir else pathlib.Path(tempfile.mkdtemp(prefix="editorial-pdf-"))
    salida_dir.mkdir(parents=True, exist_ok=True)
    perfil = _perfil_usuario()
    try:
        r = subprocess.run([soffice, f"-env:UserInstallation={perfil.as_uri()}", "--headless", "--convert-to", "pdf",
                            "--outdir", str(salida_dir), str(docx)], capture_output=True, text=True, timeout=tiempo)
    except subprocess.TimeoutExpired:
        cli.error(f"LibreOffice tardó más de {tiempo} s en convertir {docx.name}")
    pdf = salida_dir / (docx.stem + ".pdf")
    if r.returncode != 0 or not pdf.exists():
        cli.error(f"LibreOffice no pudo convertir {docx.name} a PDF: {(r.stderr or r.stdout).strip()[:300]}")
    return pdf


def requerir_pymupdf():
    try:
        import fitz  # noqa: F401
    except ImportError:
        cli.error("esta función necesita PyMuPDF: pip install pymupdf")
    return __import__("fitz")
