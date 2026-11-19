#!/usr/bin/env python3
"""Renderiza el ejemplo con LibreOffice y arma las imágenes «antes y después» del README (docs/img/ejemplo-*.png).

Requiere LibreOffice (soffice) y Pillow; para pasar de PDF a PNG usa pdftoppm (poppler o MiKTeX) o PyMuPDF.
  Windows: winget install TheDocumentFoundation.LibreOffice   mac: brew install --cask libreoffice   Linux: apt install libreoffice

Uso: python ejemplos/capturas.py            (antes ejecuta la cadena: ver ejemplos/README.md)
Salida: 0 correcto; 2 falta una herramienta o un .docx del ejemplo.
"""
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

AQUI = pathlib.Path(__file__).resolve().parent
IMG = AQUI.parent / "docs" / "img"
ETAPAS = [("informe-ejemplo.docx", "Entrega original"), ("informe-ejemplo.corregido.docx", "Tras corregir (automático)"),
          ("informe-ejemplo.final.docx", "Tras la revisión de contenido")]
FONDO, TINTA, TENUE, ROJO, VERDE = (246, 247, 249), (31, 35, 40), (101, 109, 118), (207, 34, 46), (26, 127, 55)


def soffice():
    for c in ("soffice", "libreoffice"):
        if shutil.which(c):
            return shutil.which(c)
    for c in (r"C:\Program Files\LibreOffice\program\soffice.exe", r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
              "/Applications/LibreOffice.app/Contents/MacOS/soffice"):
        if os.path.exists(c):
            return c
    print("falta LibreOffice (soffice): winget install TheDocumentFoundation.LibreOffice | brew install --cask libreoffice"
          " | apt install libreoffice", file=sys.stderr)
    sys.exit(2)


def a_pdf(docx, carpeta, perfil):
    # perfil de usuario propio: no toca el de LibreOffice del usuario ni choca con una instancia abierta
    subprocess.run([soffice(), f"-env:UserInstallation={perfil.as_uri()}", "--headless", "--convert-to", "pdf",
                    "--outdir", str(carpeta), str(docx)], check=True, capture_output=True, timeout=180)
    return carpeta / (docx.stem + ".pdf")


def a_png(pdf, prefijo, dpi):
    if shutil.which("pdftoppm"):
        subprocess.run(["pdftoppm", "-png", "-r", str(dpi), str(pdf), str(prefijo)], check=True, capture_output=True)
        return sorted(prefijo.parent.glob(prefijo.name + "-*.png"))
    try:
        import fitz  # PyMuPDF
    except ImportError:
        print("falta pdftoppm (poppler) o PyMuPDF (pip install pymupdf)", file=sys.stderr)
        sys.exit(2)
    out = []
    for i, pag in enumerate(fitz.open(pdf), 1):
        ruta = prefijo.parent / f"{prefijo.name}-{i}.png"
        pag.get_pixmap(dpi=dpi).save(ruta)
        out.append(ruta)
    return out


def fuente(tam, negrita=False):
    from PIL import ImageFont
    nombres = (["segoeuib.ttf", "DejaVuSans-Bold.ttf", "Arial Bold.ttf"] if negrita else
               ["segoeui.ttf", "DejaVuSans.ttf", "Arial.ttf"])
    for n in nombres:
        try:
            return ImageFont.truetype(n, tam)
        except OSError:
            continue
    return ImageFont.load_default()


def tira(paginas, titulo, nota, color, ancho_pag=230, sep=16):
    """Una fila: título y puntaje arriba, las páginas en miniatura debajo."""
    from PIL import Image, ImageDraw
    ims = [Image.open(p).convert("RGB") for p in paginas]
    alto_pag = int(ims[0].height * ancho_pag / ims[0].width)
    ims = [im.resize((ancho_pag, alto_pag), Image.LANCZOS) for im in ims]
    cab = 50
    w = 4 * (ancho_pag + sep) + sep
    h = cab + alto_pag + 2 * sep
    lienzo = Image.new("RGB", (w, h), FONDO)
    d = ImageDraw.Draw(lienzo)
    d.text((sep, sep), titulo, font=fuente(22, True), fill=TINTA)
    x = sep + d.textlength(titulo, font=fuente(22, True)) + 18
    d.text((x, sep + 3), nota, font=fuente(18, True), fill=color)
    for k, im in enumerate(ims):
        x = sep + k * (ancho_pag + sep)
        y = sep + cab
        d.rectangle([x + 3, y + 3, x + ancho_pag + 3, y + alto_pag + 3], fill=(208, 215, 222))
        lienzo.paste(im, (x, y))
        d.rectangle([x, y, x + ancho_pag - 1, y + alto_pag - 1], outline=(208, 215, 222))
    return lienzo


def apilar(filas, sep=0):
    from PIL import Image
    w = max(f.width for f in filas)
    h = sum(f.height for f in filas) + sep * (len(filas) - 1)
    out = Image.new("RGB", (w, h), FONDO)
    y = 0
    for f in filas:
        out.paste(f, (0, y))
        y += f.height + sep
    return out


def detalle(png_antes, png_despues, recorte, recorte_despues=None):
    """Dos recortes de la misma zona de una página, lado a lado, con su etiqueta."""
    from PIL import Image, ImageDraw
    a, b = (Image.open(p).convert("RGB") for p in (png_antes, png_despues))
    def cortar(im, rc):
        return im.crop(tuple(int(v * im.width if i % 2 == 0 else v * im.height) for i, v in enumerate(rc)))
    ra, rb = cortar(a, recorte), cortar(b, recorte_despues or recorte)
    sep, cab = 24, 56
    w = ra.width + rb.width + 3 * sep
    h = max(ra.height, rb.height) + cab + sep
    out = Image.new("RGB", (w, h), FONDO)
    d = ImageDraw.Draw(out)
    for k, (im, txt, col) in enumerate(((ra, "Antes", ROJO), (rb, "Después", VERDE))):
        x = sep + k * (ra.width + sep)
        d.text((x, 16), txt, font=fuente(24, True), fill=col)
        out.paste(im, (x, cab))
        d.rectangle([x - 1, cab - 1, x + im.width, cab + im.height], outline=(208, 215, 222))
    return out


def main():
    try:
        import PIL  # noqa: F401
    except ImportError:
        print("falta Pillow: pip install pillow", file=sys.stderr)
        sys.exit(2)
    faltan = [n for n, _ in ETAPAS if not (AQUI / n).exists()]
    if faltan:
        print(f"faltan {faltan}: ejecuta antes la cadena de ejemplos/README.md", file=sys.stderr)
        sys.exit(2)
    puntajes = {}
    for n, _ in ETAPAS:
        extra = ["--evidencias", str(AQUI / "evidencias.json")] if n.endswith("final.docx") else []
        r = subprocess.run([sys.executable, str(AQUI.parent / "scripts" / "editorial.py"), "puntuar", str(AQUI / n),
                            "--perfil", "apa7", "--estructura", "informe", "--fuentes", str(AQUI / "fuentes.json"),
                            "--sin-historial", *extra], capture_output=True, text=True, encoding="utf-8")
        puntajes[n] = r.stdout.splitlines()[0].replace("PUNTAJE: ", "Puntaje ").split("   (")[0]
    IMG.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        tmp = pathlib.Path(tmp)
        perfil = tmp / "perfil-lo"
        paginas = {}
        for n, _ in ETAPAS:
            pdf = a_pdf(AQUI / n, tmp, perfil)
            paginas[n] = a_png(pdf, tmp / pathlib.Path(n).stem.replace(".", "_"), 110)
        filas = [tira(paginas[n], t, f"{puntajes[n]} · {len(paginas[n])} páginas", ROJO if i < 2 else VERDE)
                 for i, (n, t) in enumerate(ETAPAS)]
        apilar(filas).save(IMG / "ejemplo-etapas.png", optimize=True)
        # detalle: página de resultados (la de la Tabla 1) antes y después
        def pag_tabla(n):
            import re
            texto = ""
            if shutil.which("pdftotext"):
                txt = tmp / (pathlib.Path(n).stem + ".txt")
                subprocess.run(["pdftotext", "-enc", "UTF-8", "-layout", str(tmp / (pathlib.Path(n).stem + ".pdf")), str(txt)],
                               capture_output=True)
                texto = txt.read_text(encoding="utf-8", errors="replace") if txt.exists() else ""
            for k, pag in enumerate(texto.split("\f")):
                if re.search(r"^\s*Tabla 1\s*$", pag, re.M):
                    return k
            return 2
        ia, ib = pag_tabla(ETAPAS[0][0]), pag_tabla(ETAPAS[2][0])
        detalle(paginas[ETAPAS[0][0]][ia], paginas[ETAPAS[2][0]][ib], (0.0, 0.0, 1.0, 1.0)).save(IMG / "ejemplo-tabla.png", optimize=True)
        # lista de referencias: al final de la última página antes; página propia después
        detalle(paginas[ETAPAS[0][0]][-1], paginas[ETAPAS[2][0]][-1], (0.08, 0.135, 0.92, 0.6),
                (0.08, 0.04, 0.92, 0.52)).save(IMG / "ejemplo-referencias.png", optimize=True)
    for n in ("ejemplo-etapas.png", "ejemplo-tabla.png", "ejemplo-referencias.png"):
        print("escrito", IMG / n)


if __name__ == "__main__":
    main()
