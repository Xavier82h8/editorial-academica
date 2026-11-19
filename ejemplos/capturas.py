#!/usr/bin/env python3
"""Imágenes del ejemplo para el README: qué cambió, a tamaño legible, y por qué subió el puntaje.

Abre los .docx del ejemplo con LibreOffice (como los abriría un lector), los pasa a PDF y, con PyMuPDF, localiza en
cada página el fragmento que interesa («Participaron 120…», la tabla, la lista de referencias). Recorta esa zona en la
versión original y en la final, resalta en rojo el error y en verde la corrección, y arma una fila por problema con
una explicación en lenguaje claro. Además dibuja, con matplotlib, el puntaje de cada etapa desglosado por dimensión.

Escribe en docs/img/:
  ejemplo-contenido.png   coherencia y citas: lo que una revisión de formato no ve
  ejemplo-formato.png     títulos, paginación, tabla y referencias
  ejemplo-puntaje.png     53.6 -> 57.4 -> 94.4 desglosado por dimensión

Requiere LibreOffice (soffice), PyMuPDF, Pillow y matplotlib (pip install -r requirements-dev.txt).
  LibreOffice: winget install TheDocumentFoundation.LibreOffice | brew install --cask libreoffice | apt install libreoffice
Uso: python ejemplos/capturas.py      (antes, la cadena de ejemplos/README.md)
Salida: 0 correcto; 2 falta una herramienta o un .docx del ejemplo.
"""
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

AQUI = pathlib.Path(__file__).resolve().parent
RAIZ = AQUI.parent
IMG = RAIZ / "docs" / "img"
ORIGINAL, CORREGIDO, FINAL = "informe-ejemplo.docx", "informe-ejemplo.corregido.docx", "informe-ejemplo.final.docx"

FONDO, TARJETA, BORDE = (255, 255, 255), (246, 248, 250), (208, 215, 222)
TINTA, TENUE = (31, 35, 40), (89, 99, 110)
ROJO, ROJO_SUAVE = (207, 34, 46), (255, 129, 130)
VERDE, VERDE_SUAVE = (26, 127, 55), (74, 194, 107)
ANCHO_PANEL = 760

# Una fila por problema: título y explicación para cualquier lector; reglas para quien quiera el detalle.
# Cada lado: (texto que abre el recorte, texto que lo cierra, fragmentos a resaltar). Los textos se buscan en el PDF.
FILAS_CONTENIDO = [
    {"titulo": "El resumen y el método no cuentan lo mismo",
     "explica": "El resumen decía 120 participantes; el método, 112. Un lector atento duda de todo lo demás.",
     "reglas": "CON-001 · coherencia interna",
     "antes": ("=Resumen", "estudiantil.", ["120"]),
     "despues": ("=Resumen", "estudiantil.", ["112"])},
    {"titulo": "Citas que no se sostienen",
     "explica": "Una cita sin entrada en la lista, un dato sin fuente que se quedó como nota y una obra de cinco "
                "autores citada con dos.",
     "reglas": "APA-034 · EA-001 · APA-038 · APA-037",
     "antes": ("=Introducción", "(Twenge, 2017).",
               ["Levenson & Shensa (2016)", "[[FALTA FUENTE: dato de la OMS]]", "(Twenge, 2017)", "Hale y"]),
     "despues": ("=Introducción", "alteraciones del sueño.", ["Levenson et al. (2016)", "Hale &"])},
    {"titulo": "Un texto que solo repite la tabla",
     "explica": "Copiar las cifras de la tabla no le dice nada nuevo al lector; ahora el párrafo dice qué debe ver.",
     "reglas": "CON-008 · coherencia interna",
     "antes": ("Como se observa", "de mala calidad.", ["28", "4.1", "25.0", "51", "6.3", "54.9", "33", "8.2", "78.8"]),
     "despues": ("La proporción de", "p < .001.", ["se triplica"])},
    {"titulo": "Una conclusión más fuerte que los datos",
     "explica": "Una encuesta en un solo momento muestra que dos cosas van juntas, no que una cause la otra.",
     "reglas": "CON-007 · alcance causal",
     "antes": ("=Conclusiones", "primer semestre.", ["provoca"]),
     "despues": ("=Conclusiones", "primer semestre.", ["se asoció con"])},
]
FILAS_FORMATO = [
    {"titulo": "Títulos con el estilo de Word y dos números de página",
     "explica": "Títulos azules y más grandes que el texto; número arriba y «Página 2 de 3» abajo. APA pide un solo "
                "número, arriba a la derecha.",
     "reglas": "APA-003 · APA-025 · EST-010 · EST-011",
     "antes": {"tiras": [("arriba", "=Resumen", 2), ("abajo", None, 0)], "resaltar": ["Resumen", "Página 2 de 3"]},
     "despues": {"tiras": [("arriba", "=Resumen", 2), ("abajo", None, 0)], "resaltar": ["Resumen"]}},
    {"titulo": "La tabla",
     "explica": "Rejilla completa y una nota «Fuente:» que APA no usa. Ahora: solo líneas horizontales, título en "
                "cursiva, nota que empieza con «Nota.» y la tabla no se parte entre páginas.",
     "reglas": "APA-093 · APA-089 · APA-094 · EST-012 · EST-015",
     "antes": ("=Tabla 1", "Fuente: elaboración propia", ["Fuente: elaboración propia"]),
     "despues": ("=Tabla 1", "Nota.", ["Nota."])},
    {"titulo": "La lista de referencias",
     "explica": "Desordenada, sin sangría francesa, con «doi:» a la antigua y sin cursivas. Ahora en orden "
                "alfabético, con enlaces https://doi.org y revista y volumen en cursiva.",
     "reglas": "APA-061 · APA-060 · APA-076 · APA-072",
     "antes": ("=Referencias", "bmjopen-2014-006748", ["doi:10.1016/j.ypmed.2016.01.001"]),
     "despues": ("=Referencias", "j.ypmed.2016.01.001", ["https://doi.org/10.1016/j.ypmed.2016.01.001"])},
]


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


def fuente(tam, negrita=False):
    from PIL import ImageFont
    nombres = (["segoeuib.ttf", "DejaVuSans-Bold.ttf", "Arial Bold.ttf", "LiberationSans-Bold.ttf"] if negrita else
               ["segoeui.ttf", "DejaVuSans.ttf", "Arial.ttf", "LiberationSans-Regular.ttf"])
    for n in nombres:
        try:
            return ImageFont.truetype(n, tam)
        except OSError:
            continue
    return ImageFont.load_default()


# ------------------------------------------------------------------ recortes del PDF
def buscar(doc, texto, desde=0):
    """(número de página, rectángulo) de la primera aparición de `texto` desde la página `desde`. Con «=» delante,
    solo una línea que diga exactamente eso (un título: «=Tabla 1» no es «La Tabla 1 resume…»)."""
    import fitz
    for n in range(desde, len(doc)):
        if texto.startswith("="):
            for bl in doc[n].get_text("dict")["blocks"]:
                for ln in bl.get("lines", ()):
                    if "".join(s["text"] for s in ln["spans"]).strip() == texto[1:]:
                        return n, fitz.Rect(ln["bbox"])
            continue
        r = doc[n].search_for(texto)
        if r:
            return n, r[0]
    raise SystemExit(f"no se encontró «{texto}» en el PDF (¿cambió el ejemplo?)")


def caja_texto(pagina):
    """Márgenes reales del texto de la página (izquierda, derecha) en puntos."""
    bloques = [b for b in pagina.get_text("blocks") if b[4].strip()]
    return min(b[0] for b in bloques) - 6, max(b[2] for b in bloques) + 6


def render(pagina, clip, resaltar, color):
    """Recorte de la página a ANCHO_PANEL px de ancho, con los fragmentos `resaltar` subrayados en `color`."""
    import fitz
    from PIL import Image, ImageDraw
    escala = ANCHO_PANEL / clip.width
    pix = pagina.get_pixmap(matrix=fitz.Matrix(escala, escala), clip=clip, alpha=False)
    im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples).convert("RGBA")
    capa = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    for frag in resaltar:
        for r in pagina.search_for(frag, clip=clip):
            x0, y0 = (r.x0 - clip.x0) * escala - 3, (r.y0 - clip.y0) * escala - 2
            x1, y1 = (r.x1 - clip.x0) * escala + 3, (r.y1 - clip.y0) * escala + 2
            d.rounded_rectangle([x0, y0, x1, y1], radius=4, fill=color + (28,), outline=color + (255,), width=2)
    return Image.alpha_composite(im, capa).convert("RGB")


def recorte(doc, lado, color):
    """Imagen de un lado de una fila: tramo de texto (inicio, fin, resaltar[, página mínima]) o tiras de página."""
    import fitz
    from PIL import Image, ImageDraw
    if isinstance(lado, dict):  # tiras: parte de arriba (hasta un texto + n líneas) y pie de la misma página
        n, r_ini = buscar(doc, lado["tiras"][0][1], 1)
        pag = doc[n]
        x0, x1 = caja_texto(pag)
        x0, x1 = min(x0, 54), max(x1, pag.rect.width - 54)
        arriba = render(pag, fitz.Rect(x0, 30, x1, r_ini.y1 + 14 * lado["tiras"][0][2]), lado["resaltar"], color)
        abajo = render(pag, fitz.Rect(x0, pag.rect.height - 62, x1, pag.rect.height - 18), lado["resaltar"], color)
        sep = 30
        im = Image.new("RGB", (ANCHO_PANEL, arriba.height + sep + abajo.height), FONDO)
        im.paste(arriba, (0, 0))
        im.paste(abajo, (0, arriba.height + sep))
        d = ImageDraw.Draw(im)
        y = arriba.height + sep // 2
        for x in range(0, ANCHO_PANEL, 14):
            d.line([x, y, x + 6, y], fill=BORDE, width=2)
        d.text((ANCHO_PANEL // 2, y), " pie de página ", font=fuente(15), fill=TENUE, anchor="mm")
        return im
    ini, fin, resaltar = lado[:3]
    desde = lado[3] if len(lado) > 3 else 0
    n, r_ini = buscar(doc, ini, desde)
    _, r_fin = buscar(doc, fin, n)
    pag = doc[n]
    x0, x1 = caja_texto(pag)
    return render(pag, fitz.Rect(x0, r_ini.y0 - 6, x1, r_fin.y1 + 5), resaltar, color)


def fila(num, f, im_a, im_d):
    from PIL import Image, ImageDraw
    m, sep, cab = 28, 24, 104
    alto = max(im_a.height, im_d.height)
    w = 2 * ANCHO_PANEL + sep + 2 * m
    h = cab + 34 + alto + m
    out = Image.new("RGB", (w, h), FONDO)
    d = ImageDraw.Draw(out)
    d.ellipse([m, 22, m + 34, 56], fill=TINTA)
    d.text((m + 17, 39), str(num), font=fuente(20, True), fill=FONDO, anchor="mm")
    d.text((m + 48, 20), f["titulo"], font=fuente(27, True), fill=TINTA)
    d.text((w - m, 26), f["reglas"], font=fuente(16), fill=TENUE, anchor="ra")
    d.text((m + 48, 62), f["explica"], font=fuente(19), fill=TENUE)
    for k, (im, etiqueta, col) in enumerate(((im_a, "ANTES", ROJO), (im_d, "DESPUÉS", VERDE))):
        x = m + k * (ANCHO_PANEL + sep)
        d.text((x, cab), etiqueta, font=fuente(16, True), fill=col)
        y = cab + 30
        d.rectangle([x - 1, y - 1, x + ANCHO_PANEL, y + alto], fill=FONDO, outline=BORDE)
        out.paste(im, (x, y))
        d.rectangle([x, y, x + 3, y + alto - 1], fill=col)
    return out


def lamina(filas, docs, titulo, subtitulo):
    from PIL import Image, ImageDraw
    imgs = [fila(i, f, recorte(docs[ORIGINAL], f["antes"], ROJO), recorte(docs[FINAL], f["despues"], VERDE))
            for i, f in enumerate(filas, 1)]
    w = imgs[0].width
    cab = 96
    h = cab + sum(i.height for i in imgs) + 8 * (len(imgs) - 1) + 12
    out = Image.new("RGB", (w, h), TARJETA)
    d = ImageDraw.Draw(out)
    d.text((28, 22), titulo, font=fuente(32, True), fill=TINTA)
    d.text((28, 64), subtitulo, font=fuente(18), fill=TENUE)
    y = cab
    for im in imgs:
        out.paste(im, (0, y))
        y += im.height + 8
    return out


# ------------------------------------------------------------------ puntaje por etapa
def puntajes():
    res = {}
    for n in (ORIGINAL, CORREGIDO, FINAL):
        with tempfile.TemporaryDirectory() as t:
            j = pathlib.Path(t) / "p.json"
            extra = ["--evidencias", str(AQUI / "evidencias.json")] if n == FINAL else []
            subprocess.run([sys.executable, str(RAIZ / "scripts" / "editorial.py"), "puntuar", str(AQUI / n), "--perfil",
                            "apa7", "--estructura", "informe", "--fuentes", str(AQUI / "fuentes.json"), "--sin-historial",
                            "--json", str(j), *extra], capture_output=True)
            res[n] = json.loads(j.read_text(encoding="utf-8"))
    return res


def grafica_puntaje(p):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch
    dims = [("congruencia", "Coherencia interna", "#2a78d6"), ("fuentes", "Fuentes", "#eb6834"),
            ("formato", "Formato y citas", "#1baf7a"), ("estructura", "Estructura", "#eda100"),
            ("redaccion", "Redacción", "#e87ba4")]
    etapas = [(ORIGINAL, "Entrega original"), (CORREGIDO, "Tras la corrección\nautomática"),
              (FINAL, "Tras corregir\nel contenido")]
    plt.rcParams.update({"font.family": ["Segoe UI", "DejaVu Sans"], "font.size": 12})
    fig, ax = plt.subplots(figsize=(13, 5.6), dpi=130)
    fig.patch.set_facecolor("#ffffff")
    ys = [2, 1, 0]
    # bandas del veredicto, al fondo y sin color de estado: solo líneas finas con su nombre
    for x in (60, 75, 90):
        ax.axvline(x, color="#c3c2b7", lw=1, zorder=0)
    for a, z, nombre in ((0, 60, "Rechazado"), (60, 75, "Correcciones\nmayores"), (75, 90, "Correcciones\nmenores"),
                         (90, 100, "Publicable")):
        ax.text((a + z) / 2, 2.42, nombre, fontsize=10, color="#52514e", ha="center", va="bottom", linespacing=1.1)
    for (n, nombre), y in zip(etapas, ys):
        x = 0
        dims_n = p[n]["dimensiones"]
        ax.add_patch(FancyBboxPatch((0, y - 0.3), 100, 0.6, boxstyle="round,pad=0,rounding_size=0.5",
                                    fc="#f1f0ed", ec="none", zorder=1))
        for clave, etiqueta, color in dims:
            v = float(dims_n[clave])
            if v > 0:
                ax.barh(y, max(v - 0.35, 0.1), left=x + 0.15, height=0.6, color=color, zorder=2)
                if v >= 6:
                    ax.text(x + v / 2, y, f"{v:g}", ha="center", va="center", fontsize=10.5, color="#0b0b0b", zorder=3)
            x += v
        bajas = [f"{e} {float(dims_n[k]):g}" for k, e, _ in dims if float(dims_n[k]) < 6]
        if bajas and x < 85:  # lo que no cabe dentro de la barra, dicho en texto (un 0 no se ve)
            ax.text(x + 1.2, y, " · ".join(bajas), ha="left", va="center", fontsize=10.5, color="#52514e", zorder=3)
        total, banda = p[n]["total"], p[n]["banda"]
        ax.text(101.5, y + 0.06, f"{total:g}", ha="left", va="center", fontsize=19, weight="bold", color="#0b0b0b")
        ax.text(101.5, y - 0.26, banda, ha="left", va="center", fontsize=11, color="#52514e")
    ax.set_yticks(ys, [e[1] for e in etapas], fontsize=13)
    ax.set_xlim(0, 100)
    ax.set_ylim(-0.5, 2.85)
    ax.set_xticks([0, 20, 40, 60, 80, 100])
    ax.tick_params(axis="x", colors="#52514e", labelsize=10)
    ax.tick_params(axis="y", length=0)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color("#c3c2b7")
    # leyenda: una muestra por dimensión, con su peso máximo
    maximos = p[FINAL]["maximos"]
    hand = [plt.Rectangle((0, 0), 1, 1, color=c) for _, _, c in dims]
    ax.legend(hand, [f"{e} (máx. {maximos[k]})" for k, e, _ in dims], loc="upper center", bbox_to_anchor=(0.5, -0.1),
              ncol=5, frameon=False, fontsize=11, handlelength=1.2, columnspacing=1.6)
    fig.suptitle("Puntaje del informe en cada etapa, por dimensión (0 a 100)", x=0.015, ha="left", fontsize=17,
                 weight="bold", color="#0b0b0b", y=0.98)
    fig.text(0.015, 0.895, "La corrección automática arregla el formato, pero el documento sigue rechazado: lo que "
                           "pesa es la coherencia y las citas.", fontsize=12, color="#52514e")
    fig.subplots_adjust(left=0.15, right=0.9, top=0.8, bottom=0.2)
    fig.savefig(IMG / "ejemplo-puntaje.png", facecolor=fig.get_facecolor())
    plt.close(fig)


def main():
    try:
        import fitz  # noqa: F401
        import matplotlib  # noqa: F401
        import PIL  # noqa: F401
    except ImportError as e:
        print(f"falta {e.name}: pip install -r requirements-dev.txt", file=sys.stderr)
        sys.exit(2)
    import fitz
    faltan = [n for n in (ORIGINAL, CORREGIDO, FINAL) if not (AQUI / n).exists()]
    if faltan:
        print(f"faltan {faltan}: ejecuta antes la cadena de ejemplos/README.md", file=sys.stderr)
        sys.exit(2)
    IMG.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        tmp = pathlib.Path(tmp)
        docs = {n: fitz.open(a_pdf(AQUI / n, tmp, tmp / "perfil-lo")) for n in (ORIGINAL, FINAL)}
        lamina(FILAS_CONTENIDO, docs, "Lo que una revisión de formato no ve",
               "Fragmentos del informe de ejemplo tal como se ven en LibreOffice: en rojo el problema, en verde la "
               "corrección.").save(IMG / "ejemplo-contenido.png", optimize=True)
        lamina(FILAS_FORMATO, docs, "Y el formato, que se corrige solo",
               "Lo hace la corrección automática sobre una copia; el documento original no se toca."
               ).save(IMG / "ejemplo-formato.png", optimize=True)
        for d in docs.values():
            d.close()
    grafica_puntaje(puntajes())
    for n in ("ejemplo-contenido.png", "ejemplo-formato.png", "ejemplo-puntaje.png"):
        print("escrito", IMG / n)


if __name__ == "__main__":
    main()
