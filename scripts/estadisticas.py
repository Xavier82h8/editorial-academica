#!/usr/bin/env python3
"""Estadísticas reproducibles: corre las puertas de prueba y escribe docs/estadisticas.json y gráficas PNG en docs/img/.

Uso: python scripts/estadisticas.py [--sin-graficas] [--sin-red]
Requiere matplotlib (requirements-dev.txt) solo para las gráficas.

Qué mide:
  (a) precisión y recall del juez por ronda (errores sembrados, rondas ciegas docs/docs2/docs3, boceto sintético) y falsos
      positivos en las muestras oficiales (si falta normas/ la ronda queda «no disponible», sin fallar);
  (b) reglas por familia (de docs/REGLAS.md): deterministas, de agente, corregibles; más el desglose APA/IEEE: IDs que emite
      algún script (la «heurística» del catálogo), reglas que el checklist marca como automatizables («Fix: sí») y corregibles;
  (c) evolución del piloto anonimizado (valores registrados a mano en cada sesión: no se recalculan; el documento no se distribuye);
  (d) tiempo de cada puerta de la suite rápida.
Salida: 0 correcto; 2 error de uso.
"""
import argparse
import ast
import datetime
import json
import textwrap
import pathlib
import platform
import re
import sys
import tempfile
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))
import catalogo  # noqa: E402
import obtener_normas  # noqa: E402
import run_todo  # noqa: E402

SALIDA_JSON = ROOT / "docs" / "estadisticas.json"
IMG = ROOT / "docs" / "img"

# Evolución del piloto anonimizado («protocolo de investigación real de licenciatura»): puntaje de /puntuar por hito.
PILOTO = [
    ("Primera\nrevisión", 31.1),
    ("Fuentes sin\nfalsas alarmas", 65.8),
    ("Corrección\nautomática", 72.3),
    ("Correcciones\ndel autor", 91.5),
    ("Reglas nuevas:\nmás exigente", 87.0),
    ("Versión\nfinal", 91.4),
    ("Revisor aún\nmás estricto", 85.4),
    ("Nueva corrección\nautomática", 88.4),
]
# Primera medición ciega de las rondas 2 y 3 (antes de corregir lo que revelaron), según el historial del repositorio.
PRIMERA_MEDICION = {"ronda ciega docs2": {"precision": 1.00, "recall": 0.87}, "ronda ciega docs3": {"precision": 0.97, "recall": 1.00}}


def contar_juez(salida):
    """Suma esperados, detectados, falsos positivos y omitidos de la salida de tests/run_juez.py."""
    esp = det = fp = fn = 0
    for m in re.finditer(r"esperados=(\d+) detectados=(\d+) falsos\+=(\[.*?\]) omitidos=(\[.*?\])", salida):
        esp += int(m.group(1))
        det += int(m.group(2))
        fp += len(ast.literal_eval(m.group(3)))
        fn += len(ast.literal_eval(m.group(4)))
    prec = det / (det + fp) if det + fp else 1.0
    rec = det / (det + fn) if det + fn else 1.0
    return {"esperados": esp, "detectados": det, "falsos_positivos": fp, "omitidos": fn,
            "precision": round(prec, 3), "recall": round(rec, 3), "disponible": esp > 0}


def rondas():
    """(a) Una entrada por ronda del juez."""
    res = []
    casos = [("Errores sembrados", [], "errores sembrados")]
    sys.path.insert(0, str(ROOT / "tests" / "ciegos"))
    import asegurar  # las rondas ciegas no se versionan: se regeneran si faltan
    asegurar.asegurar()
    for d in sorted((ROOT / "tests" / "ciegos").glob("docs*")):
        if (d / "esperado.json").exists():
            casos.append((f"Ciega {d.name}", ["--dir", str(d)], f"ronda ciega {d.name}"))
    for etiqueta, args, clave in casos:
        code, out = run_todo.correr(["tests/run_juez.py"] + args)
        r = contar_juez(out)
        r.update(ronda=etiqueta, clave=clave, codigo=code)
        r.update({"primera_precision": PRIMERA_MEDICION.get(clave, {}).get("precision"),
                  "primera_recall": PRIMERA_MEDICION.get(clave, {}).get("recall")})
        res.append(r)
    _, out = run_todo.correr(["tests/run_real.py"])
    m = re.search(r"recall seguro\+mecánico = ([\d.]+) \((\d+)/(\d+)\)", out)
    fp = re.search(r"falsos positivos sobre IDs que cumplen = (\d+)", out)
    if m and fp:
        det, esp, nfp = int(m.group(2)), int(m.group(3)), int(fp.group(1))
        res.append({"ronda": "Boceto sintético", "clave": "boceto", "esperados": esp, "detectados": det, "falsos_positivos": nfp,
                    "omitidos": esp - det, "precision": round(det / (det + nfp), 3) if det + nfp else 1.0,
                    "recall": round(det / esp, 3) if esp else 1.0, "disponible": True, "codigo": 0})
    else:
        res.append({"ronda": "Boceto sintético", "clave": "boceto", "disponible": False})
    return res


def muestras_oficiales():
    """Falsos positivos del juez sobre las muestras oficiales APA/IEEE (necesita normas/muestras)."""
    if obtener_normas.falta("muestras"):
        return {"disponible": False, "motivo": "falta normas/muestras (python scripts/obtener_normas.py)"}
    run_todo.SALTOS.clear()
    ok, resumen = run_todo.puerta_muestras()
    m = re.match(r"(\d+) muestras, (\d+) verdaderos positivos esperados, (\d+) falsos positivos", resumen)
    if not m:
        return {"disponible": False, "motivo": "no se pudo leer el resultado"}
    return {"disponible": True, "muestras": int(m.group(1)), "verdaderos_positivos_esperados": int(m.group(2)),
            "falsos_positivos": int(m.group(3)), "puerta_ok": ok}


def reglas():
    """(b) Conteos del catálogo y desglose APA/IEEE."""
    rs = catalogo.recolectar()
    fam = {}
    for r in rs:
        p = r["id"].split("-")[0]
        f = fam.setdefault(p, {"total": 0, "deterministas": 0, "agente": 0, "corregibles": 0})
        f["total"] += 1
        f["deterministas" if r["auto"] else "agente"] += 1
        f["corregibles"] += bool(r["corregible"])
    ai = [r for r in rs if r["id"].startswith(("APA-", "IEEE-"))]
    return {"total": len(rs), "familias": fam,
            "apa_ieee": {"total": len(ai), "ids_en_scripts": len(catalogo.ids_en_scripts()),
                         "fix_si_en_checklist": sum(1 for r in ai if r["fix_checklist"]),
                         "corregibles": sum(1 for r in ai if r["corregible"]),
                         "nota": "«determinista» del catálogo = ID que aparece en algún script (heurística, igual a ids_en_scripts); "
                                 "«Fix: sí» = el checklist lo marca como mecánico; la brecha entre ambos es trabajo pendiente."}}


def tiempos(sin_red):
    """(d) Tiempo de cada puerta de la suite rápida (con --sin-red si se pide)."""
    tmp = tempfile.TemporaryDirectory() if sin_red else None
    if sin_red:
        run_todo.SIN_RED = True
        run_todo.ENV = run_todo.entorno_sin_red(tmp.name)
    puertas, inicio = [], time.perf_counter()
    for nombre, fn in run_todo.construir_pruebas(True):
        run_todo.SALTOS.clear()
        t0 = time.perf_counter()
        ok, _ = fn()
        puertas.append({"puerta": nombre, "segundos": round(time.perf_counter() - t0, 1), "ok": bool(ok), "saltada": bool(ok and run_todo.SALTOS)})
    total = round(time.perf_counter() - inicio, 1)
    if tmp:
        tmp.cleanup()
    return {"total_segundos": total, "sin_red": sin_red, "puertas": puertas,
            "entorno": f"Python {platform.python_version()}, {platform.system()}"}


# ---------------------------------------------------------------- gráficas
AZUL, VERDE, GRIS, NARANJA, ROJO, TINTA = "#1f5a99", "#2a8a6e", "#8a94a0", "#d9822b", "#b3402f", "#24292f"


def _estilo(plt):
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.edgecolor": "#8a94a0", "axes.labelcolor": TINTA,
                         "xtick.color": TINTA, "ytick.color": TINTA, "text.color": TINTA, "axes.spines.top": False,
                         "axes.spines.right": False, "axes.grid": True, "grid.color": "#e3e6ea", "grid.linewidth": 0.8,
                         "axes.axisbelow": True})


def _guardar(fig, nombre):
    """Fondo blanco con borde: legible en el tema claro y en el oscuro de GitHub."""
    from matplotlib.patches import Rectangle
    fig.patch.set_facecolor("white")
    fig.add_artist(Rectangle((0, 0), 1, 1, transform=fig.transFigure, fill=False, edgecolor="#c5cbd3", linewidth=2.5, zorder=100))
    IMG.mkdir(parents=True, exist_ok=True)
    fig.savefig(IMG / nombre, dpi=150, facecolor="white", metadata={"Software": None})
    print(f"escrito docs/img/{nombre}")


# paleta categórica validada (skill dataviz, modo claro) y tinta neutra
SERIE1, SERIE2, SERIE3, PISTA, TINTA2, TENUE2 = "#2a78d6", "#eb6834", "#1baf7a", "#f1f0ed", "#0b0b0b", "#52514e"


def _lienzo(plt, alto=5.2):
    plt.rcParams.update({"font.family": ["Segoe UI", "DejaVu Sans"], "font.size": 12, "axes.spines.top": False,
                         "axes.spines.right": False, "axes.grid": False, "text.color": TINTA2})
    return plt.figure(figsize=(13, alto), dpi=130)


def _titulos(fig, titulo, subtitulo):
    fig.text(0.015, 0.94, titulo, fontsize=18, weight="bold", color=TINTA2, va="top")
    fig.text(0.015, 0.865, subtitulo, fontsize=12, color=TENUE2, va="top")


NOMBRE_RONDA = {"errores sembrados": "Errores sembrados a propósito", "ronda ciega docs": "Documento nuevo a ciegas, 1",
                "ronda ciega docs2": "Documento nuevo a ciegas, 2", "ronda ciega docs3": "Documento nuevo a ciegas, 3",
                "boceto": "Borrador de estudiante"}


def grafica_juez(datos):
    """¿Encuentra los errores sin inventar otros? Barras de 0 a 100 % (nunca un eje recortado) y, aparte, las
    falsas alarmas en las muestras oficiales."""
    import matplotlib.pyplot as plt
    rs = [r for r in datos["rondas"] if r.get("disponible")]
    fig = _lienzo(plt, 5.6)
    _titulos(fig, "¿Encuentra los errores sin inventar otros?",
             "Documentos con errores conocidos: cuántos encontró el revisor y cuántas veces marcó algo que estaba bien.")
    ax = fig.add_axes([0.24, 0.17, 0.44, 0.6])
    ys = list(range(len(rs)))[::-1]
    for r, y in zip(rs, ys):
        frac = r["detectados"] / r["esperados"] if r["esperados"] else 1
        ax.barh(y, 100, height=0.56, color=PISTA, zorder=1)
        ax.barh(y, 100 * frac, height=0.56, color=SERIE1, zorder=2)
        fp = r.get("falsos_positivos", 0)
        ax.text(102, y + 0.1, f"{r['detectados']} de {r['esperados']}", fontsize=12.5, weight="bold", va="center")
        ax.text(102, y - 0.24, "1 falsa alarma" if fp == 1 else f"{fp} falsas alarmas", fontsize=10.5, color=TENUE2,
                va="center")
        pr, pp = r.get("primera_recall"), r.get("primera_precision")
        if pr is not None and pr < 1:
            ax.plot(100 * pr, y, marker="o", ms=10, mfc="white", mec=SERIE2, mew=2.5, zorder=3)
            ax.text(100 * pr - 2.5, y, f"1.ª vez: {round(pr * r['esperados'])} de {r['esperados']}", fontsize=10,
                    color="white", ha="right", va="center", zorder=4)
        elif pp is not None and pp < 1:
            n = round(r["esperados"] / pp - r["esperados"])
            ax.text(3, y, f"1.ª vez: {n} falsa alarma (ya corregida)", fontsize=10, color="white", va="center", zorder=4)
    ax.set_yticks(ys, [NOMBRE_RONDA.get(r.get("clave"), r["ronda"]) for r in rs], fontsize=12)
    ax.set_xlim(0, 100)
    ax.set_xticks([0, 25, 50, 75, 100], ["0 %", "25 %", "50 %", "75 %", "100 %"], fontsize=10, color=TENUE2)
    ax.tick_params(axis="y", length=0)
    for s in ("left", "bottom"):
        ax.spines[s].set_color("#c3c2b7")
    ax.plot([], [], marker="o", ms=9, mfc="white", mec=SERIE2, mew=2.5, ls="",
            label="primera medición, antes de corregir lo que reveló")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.1), frameon=False, fontsize=10.5)
    m = datos["muestras_oficiales"]
    if m.get("disponible"):
        fig.text(0.79, 0.64, f"{m['falsos_positivos']}", fontsize=64, weight="bold", color=TINTA2, va="center")
        fig.text(0.79, 0.48, "falsas alarmas", fontsize=15, weight="bold", va="center")
        fig.text(0.79, 0.36, f"en {m['muestras']} documentos de muestra\noficiales de APA e IEEE", fontsize=12,
                 color=TENUE2, va="center", linespacing=1.3)
        fig.text(0.79, 0.22, f"Los {m['verdaderos_positivos_esperados']} errores reales que traen\nesas muestras, sí los marca.",
                 fontsize=10.5, color=TENUE2, va="center", linespacing=1.3)
    fig.text(0.015, 0.025, "Los documentos «a ciegas» se escribieron con errores según la norma, sin mirar el revisor. "
             "Lo que la primera medición reveló se corrigió; hoy cada ronda es una prueba que no debe volver a fallar.",
             fontsize=9.5, color=TENUE2)
    _guardar(fig, "juez-precision-recall.png")
    plt.close(fig)


NOMBRE_FAMILIA = {"APA": "APA 7", "IEEE": "IEEE", "CON": "Coherencia interna", "EST": "Estructura y maquetación",
                  "FUE": "Fuentes", "EA": "Marcadores olvidados", "RED": "Redacción"}


def grafica_reglas(datos):
    """¿Quién revisa cada regla? Programa que además corrige, programa que solo detecta, o el agente de IA."""
    import matplotlib.pyplot as plt
    fam = datos["reglas"]["familias"]
    orden = [p for p in ("APA", "IEEE", "CON", "EST", "FUE", "EA", "RED") if p in fam]
    fig = _lienzo(plt, 5.6)
    _titulos(fig, f"¿Quién revisa cada una de las {datos['reglas']['total']} reglas?",
             "Lo mecánico lo hace el programa (siempre igual); lo que requiere criterio, tu agente de IA.")
    ax = fig.add_axes([0.2, 0.2, 0.5, 0.58])
    gris = "#a8a69e"
    seg = [("corrige", "El programa la revisa y la corrige", SERIE3),
           ("detecta", "El programa la revisa", SERIE1),
           ("agente", "La juzga tu agente de IA", gris)]
    ys = list(range(len(orden)))[::-1]
    for p, y in zip(orden, ys):
        f = fam[p]
        vals = {"corrige": f["corregibles"], "detecta": f["deterministas"] - f["corregibles"], "agente": f["agente"]}
        x = 0
        for k, _, c in seg:
            v = vals[k]
            if v:
                ax.barh(y, max(v - 0.8, 0.6), left=x + 0.4, height=0.6, color=c)
                if v >= 12:
                    ax.text(x + v / 2, y, str(v), ha="center", va="center", fontsize=10.5,
                            color=TINTA2 if c == gris else "white")
            x += v
        ax.text(x + 2, y, str(f["total"]), va="center", fontsize=12, weight="bold")
    ax.set_yticks(ys, [NOMBRE_FAMILIA.get(p, p) for p in orden], fontsize=12)
    ax.tick_params(axis="y", length=0)
    ax.tick_params(axis="x", colors=TENUE2, labelsize=10)
    for s in ("left", "bottom"):
        ax.spines[s].set_color("#c3c2b7")
    ax.legend([plt.Rectangle((0, 0), 1, 1, color=c) for _, _, c in seg], [t for _, t, _ in seg], loc="upper center",
              bbox_to_anchor=(0.5, -0.1), ncol=3, frameon=False, fontsize=10.5)
    ai = datos["reglas"]["apa_ieee"]
    hecho, meta = ai["ids_en_scripts"], ai["fix_si_en_checklist"]
    fig.text(0.76, 0.74, "Lo que falta automatizar", fontsize=14, weight="bold", va="top")
    fig.text(0.76, 0.66, f"De las {meta} reglas de APA e IEEE que se\npueden revisar de forma mecánica:", fontsize=11,
             color=TENUE2, va="top", linespacing=1.3)
    bx = fig.add_axes([0.76, 0.45, 0.2, 0.05])
    bx.barh(0, meta, color=PISTA, height=1)
    bx.barh(0, hecho, color=SERIE1, height=1)
    bx.set_xlim(0, meta)
    bx.set_axis_off()
    fig.text(0.76, 0.39, f"{hecho} ya las revisa el programa", fontsize=12, weight="bold", va="top")
    fig.text(0.76, 0.33, f"Las otras {meta - hecho} las revisa, mientras\ntanto, tu agente de IA.", fontsize=11,
             color=TENUE2, va="top", linespacing=1.3)
    _guardar(fig, "reglas-por-familia.png")
    plt.close(fig)


def grafica_piloto(datos):
    """Puntaje de un protocolo real en cada hito; bandas del veredicto como líneas con nombre, no colores."""
    import matplotlib.pyplot as plt
    pts = datos["piloto"]["hitos"]
    fig = _lienzo(plt, 5.6)
    _titulos(fig, "Un protocolo de investigación real, revisión tras revisión",
             "Puntaje de 0 a 100 de un protocolo de licenciatura (anonimizado) en cada etapa del desarrollo del editor.")
    ax = fig.add_axes([0.06, 0.22, 0.78, 0.56])
    xs = list(range(len(pts)))
    ys = [p["puntaje"] for p in pts]
    for v, nombre in ((60, "60 · correcciones mayores"), (75, "75 · correcciones menores"), (90, "90 · publicable")):
        ax.axhline(v, color="#c3c2b7", lw=1, zorder=0)
        ax.text(len(pts) - 0.5, v, "  " + nombre, fontsize=10, color=TENUE2, va="center", ha="left")
    ax.plot(xs, ys, color=SERIE1, lw=2, zorder=2)
    ax.plot(xs, ys, ls="", marker="o", ms=9, mfc=SERIE1, mec="white", mew=2, zorder=3)
    for i, (x, y) in enumerate(zip(xs, ys)):
        baja = i > 0 and y < ys[i - 1]
        ax.text(x, y + (-7.5 if baja else 3.5), f"{y:g}", ha="center", fontsize=12, weight="bold")
    ax.set_xticks(xs, [textwrap.fill(p["hito"], 15) for p in pts], fontsize=10)
    ax.set_xlim(-0.4, len(pts) - 0.5)
    ax.set_ylim(20, 100)
    ax.set_yticks([20, 40, 60, 80, 100])
    ax.tick_params(colors=TENUE2, labelsize=10)
    ax.tick_params(axis="x", colors=TINTA2, length=0)
    for s in ("left", "bottom"):
        ax.spines[s].set_color("#c3c2b7")
    fig.text(0.015, 0.025, "Las dos bajadas no son retrocesos del documento: el revisor se volvió más exigente y encontró "
             "cosas que antes dejaba pasar. Valores registrados en cada hito; el documento no se distribuye.",
             fontsize=9.5, color=TENUE2)
    _guardar(fig, "piloto-evolucion.png")
    plt.close(fig)


def grafica_tiempos(datos):
    import matplotlib.pyplot as plt
    _estilo(plt)
    t = datos["tiempos"]
    ps = sorted(t["puertas"], key=lambda p: p["segundos"])
    fig, ax = plt.subplots(figsize=(11, 4.6))
    nombres = [re.sub(r"\s*\(.*?\)", "", p["puerta"])[:70] for p in ps]
    ax.barh(range(len(ps)), [p["segundos"] for p in ps], color=[GRIS if p["saltada"] else AZUL for p in ps])
    for i, p in enumerate(ps):
        ax.text(p["segundos"] + 0.3, i, f"{p['segundos']:.1f} s" + (" (saltada)" if p["saltada"] else ""), va="center", fontsize=8.5)
    ax.set_yticks(range(len(ps)))
    ax.set_yticklabels(nombres, fontsize=8.5)
    ax.set_xlabel("Segundos")
    ax.set_title(f"Suite rápida: {t['total_segundos']:.0f} s en total ({t['entorno']}{', sin red' if t['sin_red'] else ''})", loc="left", fontweight="bold")
    fig.tight_layout()
    _guardar(fig, "suite-tiempos.png")
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description="Corre las puertas y escribe docs/estadisticas.json y las gráficas de docs/img/.")
    ap.add_argument("--sin-graficas", action="store_true", help="solo el JSON (no requiere matplotlib)")
    ap.add_argument("--sin-red", action="store_true", help="mide la suite con caché sembrada y proxy muerto (como la CI)")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    datos = {"generado": datetime.date.today().isoformat(), "version": json.loads(
        (ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"]}
    print("(a) juez por ronda…")
    datos["rondas"] = rondas()
    datos["muestras_oficiales"] = muestras_oficiales()
    print("(b) reglas…")
    datos["reglas"] = reglas()
    datos["piloto"] = {"descripcion": "protocolo de investigación real de licenciatura (anonimizado)",
                       "hitos": [{"hito": h.replace("\n", " "), "puntaje": v} for h, v in PILOTO]}
    print("(d) tiempos de la suite rápida…")
    datos["tiempos"] = tiempos(a.sin_red)
    SALIDA_JSON.parent.mkdir(parents=True, exist_ok=True)
    SALIDA_JSON.write_text(json.dumps(datos, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print("escrito docs/estadisticas.json")
    if a.sin_graficas:
        return
    try:
        import matplotlib
        matplotlib.use("Agg")
    except ImportError:
        print("matplotlib no está instalado (pip install -r requirements-dev.txt); solo se escribió el JSON", file=sys.stderr)
        sys.exit(2)
    for fn in (grafica_juez, grafica_reglas, grafica_piloto, grafica_tiempos):
        fn(datos)


if __name__ == "__main__":
    main()
