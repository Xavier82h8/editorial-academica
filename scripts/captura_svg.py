#!/usr/bin/env python3
"""Corre un comando y convierte su salida de texto en un SVG con aspecto de terminal (sin dependencias).

Uso:
  python scripts/captura_svg.py SALIDA.svg [opciones] -- python scripts/editorial.py auditar doc.docx --perfil apa7

Opciones:
  --titulo TEXTO       título de la ventana (por defecto, el comando)
  --max-lineas N       muestra las primeras N líneas de la salida y «…» (por defecto 28)
  --cols N             ancho máximo en columnas; lo que sobra se corta con «…» (por defecto 110)
  --tabla-celda N      convierte las tablas Markdown (`| a | b |`) en columnas de texto alineadas con celdas de a lo sumo N caracteres
  --cols-tabla 1,2,4   con --tabla-celda, columnas de la tabla que se conservan (base 1)
  --sin-color          no resalta IDs de regla ni severidades (se conservan los colores ANSI de la salida)

El comando se ejecuta desde la raíz del repositorio; `python` se sustituye por el intérprete actual. La raíz del repositorio y
el directorio de usuario se sustituyen por `.` y `~` en la salida y en el comando mostrado, de modo que el SVG no contiene
rutas absolutas. Salida: 0 correcto; 2 error de uso. El código de salida del comando capturado no se propaga.
"""
import argparse
import html
import os
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
ANSI = re.compile(r"\x1b\[([0-9;]*)m")
OTROS_ESC = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
# paleta tipo GitHub oscuro
FONDO, BORDE, TEXTO, TENUE = "#0d1117", "#30363d", "#c9d1d9", "#8b949e"
COLORES = {30: "#484f58", 31: "#ff7b72", 32: "#3fb950", 33: "#d29922", 34: "#58a6ff", 35: "#bc8cff", 36: "#39c5cf", 37: "#c9d1d9",
           90: "#6e7681", 91: "#ffa198", 92: "#56d364", 93: "#e3b341", 94: "#79c0ff", 95: "#d2a8ff", 96: "#56d4dd", 97: "#f0f6fc"}
FUENTE = "ui-monospace, SFMono-Regular, Menlo, Consolas, 'Liberation Mono', 'DejaVu Sans Mono', monospace"
TAM, ANCHO_CAR, ALTO_LINEA = 13, 7.9, 19
RESALTE = [  # (regex, color) para texto sin color propio
    (re.compile(r"\b(?:APA|IEEE|CON|EST|FUE|RED|EA)-\w+\b"), COLORES[94]),
    (re.compile(r"\bcrítica\b"), COLORES[91]), (re.compile(r"\bmayor\b"), COLORES[33]), (re.compile(r"\bmenor\b"), COLORES[93]),
    (re.compile(r"\b(?:Publicable|Aprobado)\b"), COLORES[32]),
    (re.compile(r"\b(?:Correcciones mayores|Rechazado|HAY FALLAS)\b"), COLORES[91]),
    (re.compile(r"\[x\]"), COLORES[32]), (re.compile(r"\[ \]"), COLORES[91]),
]


def limpiar_rutas(texto):
    for r in {str(ROOT), ROOT.as_posix(), str(ROOT).replace("\\", "\\\\")}:
        texto = texto.replace(r + os.sep, "./").replace(r + "/", "./").replace(r, ".")
    home = pathlib.Path.home()
    for r in {str(home), home.as_posix()}:
        texto = texto.replace(r, "~")
    return texto


def tabla_a_columnas(lineas, celda_max, mantener):
    """Convierte bloques de tabla Markdown en columnas alineadas (cabecera en negrita, raya bajo ella)."""
    salida, i = [], 0
    while i < len(lineas):
        if not lineas[i].lstrip().startswith("|"):
            salida.append(lineas[i])
            i += 1
            continue
        bloque = []
        while i < len(lineas) and lineas[i].lstrip().startswith("|"):
            bloque.append(lineas[i])
            i += 1
        filas = []
        for l in bloque:
            celdas = [c.strip() for c in re.split(r"(?<!\\)\|", l.strip())[1:-1]]
            celdas = [c.replace("\\|", "|") for c in celdas]
            if mantener:
                celdas = [celdas[k - 1] for k in mantener if 0 < k <= len(celdas)]
            filas.append(("raya" if all(re.fullmatch(r":?-{2,}:?", c) for c in celdas) else "fila", celdas))
        datos = [c for t, c in filas if t == "fila"]
        recorta = lambda c: c if len(c) <= celda_max else c[:celda_max - 1].rstrip() + "…"  # noqa: E731
        datos = [[recorta(c) for c in f] for f in datos]
        n = max((len(f) for f in datos), default=0)
        anchos = [max((len(f[k]) for f in datos if k < len(f)), default=0) for k in range(n)]
        total = sum(anchos) + 2 * (n - 1)
        j = 0
        for k, (tipo, _) in enumerate(filas):
            if tipo == "raya":
                salida.append("─" * total)
                continue
            f = datos[j]
            j += 1
            texto = "  ".join(c.ljust(anchos[m]) for m, c in enumerate(f)).rstrip()
            cabecera = k + 1 < len(filas) and filas[k + 1][0] == "raya" and not any(t == "fila" for t, _ in filas[:k])
            salida.append(f"\x1b[1m{texto}\x1b[0m" if cabecera else texto)
    return salida


def segmentos(linea, resaltar):
    """Descompone una línea en [(texto, color|None, negrita)] a partir de los códigos ANSI."""
    linea = OTROS_ESC.sub(lambda m: m.group(0) if m.group(0).endswith("m") else "", linea)
    color, negrita, segs, pos = None, False, [], 0
    for m in ANSI.finditer(linea):
        if m.start() > pos:
            segs.append((linea[pos:m.start()], color, negrita))
        for code in (int(x) if x else 0 for x in (m.group(1) or "0").split(";")):
            if code == 0:
                color, negrita = None, False
            elif code == 1:
                negrita = True
            elif code in COLORES:
                color = COLORES[code]
            elif code == 39:
                color = None
        pos = m.end()
    if pos < len(linea):
        segs.append((linea[pos:], color, negrita))
    if not resaltar:
        return segs
    final = []
    for texto, color, negrita in segs:
        if color or not texto:
            final.append((texto, color, negrita))
            continue
        marcas = sorted((m.start(), m.end(), c) for rx, c in RESALTE for m in rx.finditer(texto))
        cursor = 0
        for a, b, c in marcas:
            if a < cursor:
                continue
            if a > cursor:
                final.append((texto[cursor:a], None, negrita))
            final.append((texto[a:b], c, negrita))
            cursor = b
        if cursor < len(texto):
            final.append((texto[cursor:], None, negrita))
    return final


def recortar_segs(segs, cols):
    largo = sum(len(t) for t, _, _ in segs)
    if largo <= cols:
        return segs
    res, usado = [], 0
    for t, c, b in segs:
        if usado + len(t) <= cols - 1:
            res.append((t, c, b))
            usado += len(t)
        else:
            res.append((t[:cols - 1 - usado], c, b))
            break
    res.append(("…", TENUE, False))
    return res


def svg(titulo, comando, lineas_segs, cols):
    pad, barra = 18, 38
    n = len(lineas_segs) + 2
    ancho = int(cols * ANCHO_CAR + 2 * pad)
    alto = barra + n * ALTO_LINEA + pad
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{ancho}" height="{alto}" viewBox="0 0 {ancho} {alto}" role="img" '
         f'aria-label="{html.escape(titulo, quote=True)}">',
         f'<rect x="0.5" y="0.5" width="{ancho - 1}" height="{alto - 1}" rx="10" fill="{FONDO}" stroke="{BORDE}"/>',
         f'<path d="M0.5 {barra} V10.5 a10 10 0 0 1 10 -10 H{ancho - 10.5} a10 10 0 0 1 10 10 V{barra} Z" fill="#161b22"/>',
         f'<line x1="0.5" y1="{barra}" x2="{ancho - 0.5}" y2="{barra}" stroke="{BORDE}"/>',
         '<circle cx="20" cy="19" r="6" fill="#ff5f56"/><circle cx="40" cy="19" r="6" fill="#ffbd2e"/>'
         '<circle cx="60" cy="19" r="6" fill="#27c93f"/>',
         f'<text x="{ancho / 2}" y="23" text-anchor="middle" font-family="{FUENTE}" font-size="12" fill="{TENUE}">'
         f'{html.escape(titulo)}</text>',
         f'<g font-family="{FUENTE}" font-size="{TAM}" fill="{TEXTO}" style="white-space:pre" xml:space="preserve">']
    y = barra + ALTO_LINEA + 4
    cmd = [("$ ", COLORES[32], True), (comando, None, False)]
    todas = [recortar_segs(cmd, cols)] + lineas_segs
    for segs in todas:
        partes = []
        for t, c, b in segs:
            atr = (f' fill="{c}"' if c else "") + (' font-weight="bold"' if b else "")
            # NBSP: los espacios no se pierden en ningún visor
            partes.append(f"<tspan{atr}>{html.escape(t).replace(' ', '&#160;')}</tspan>")
        o.append(f'<text x="{pad}" y="{y}" xml:space="preserve">{"".join(partes)}</text>')
        y += ALTO_LINEA
    o.append("</g></svg>")
    return "\n".join(o) + "\n"


def main():
    argv = sys.argv[1:]
    if "--" not in argv:
        print("uso: captura_svg.py SALIDA.svg [opciones] -- comando ...", file=sys.stderr)
        sys.exit(2)
    k = argv.index("--")
    cmd = argv[k + 1:]
    ap = argparse.ArgumentParser(description="Convierte la salida de un comando en un SVG estilo terminal.", usage="%(prog)s SALIDA.svg [opciones] -- comando ...")
    ap.add_argument("salida")
    ap.add_argument("--titulo")
    ap.add_argument("--max-lineas", type=int, default=28)
    ap.add_argument("--cols", type=int, default=110)
    ap.add_argument("--tabla-celda", type=int, default=0)
    ap.add_argument("--cols-tabla", default="")
    ap.add_argument("--sin-color", action="store_true")
    a = ap.parse_args(argv[:k])
    if not cmd:
        ap.error("falta el comando después de --")
    real = [sys.executable if c in ("python", "python3") and i == 0 else c for i, c in enumerate(cmd)]
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1", NO_COLOR="1")
    r = subprocess.run(real, cwd=ROOT, capture_output=True, env=env, text=True, encoding="utf-8", errors="replace")
    texto = limpiar_rutas((r.stdout + r.stderr).replace("\r\n", "\n"))
    lineas = texto.rstrip("\n").split("\n") if texto.strip() else ["(sin salida)"]
    if a.tabla_celda:
        mantener = [int(x) for x in a.cols_tabla.split(",") if x.strip()]
        lineas = tabla_a_columnas(lineas, a.tabla_celda, mantener)
    resto = len(lineas) - a.max_lineas
    if resto > 0:
        lineas = lineas[:a.max_lineas]
    segs = [recortar_segs(segmentos(l, not a.sin_color), a.cols) for l in lineas]
    if resto > 0:
        segs.append([(f"… (+{resto} líneas)", TENUE, False)])
    mostrado = limpiar_rutas(" ".join(cmd))
    ancho = max(max((sum(len(t) for t, _, _ in s) for s in segs), default=0), len(mostrado) + 2, 40)
    salida = pathlib.Path(a.salida)
    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_text(svg(a.titulo or mostrado, mostrado, segs, min(ancho, a.cols)), encoding="utf-8", newline="\n")
    print(f"escrito {limpiar_rutas(str(salida))} ({len(segs)} líneas)")


if __name__ == "__main__":
    main()
