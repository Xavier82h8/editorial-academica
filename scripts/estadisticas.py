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
    ("Base inicial", 31.1),
    ("Sin falsos positivos\ndel verificador", 65.8),
    ("Tras corregir.py", 72.3),
    ("Tras correcciones", 91.5),
    ("Con reglas nuevas de\nmaquetación y congruencia", 87.0),
    ("Final (sesión 6)", 91.4),
    ("Juez más estricto:\nsangrías y V5", 85.4),
    ("Tras corregir.py\n(de nuevo)", 88.4),
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


def grafica_juez(datos):
    import matplotlib.pyplot as plt
    _estilo(plt)
    rs = [r for r in datos["rondas"] if r.get("disponible")]
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(11, 4.6), gridspec_kw={"width_ratios": [3, 1.25]})
    x = range(len(rs))
    w = 0.36
    b1 = ax.bar([i - w / 2 for i in x], [r["precision"] for r in rs], w, color=AZUL, label="Precisión")
    b2 = ax.bar([i + w / 2 for i in x], [r["recall"] for r in rs], w, color=VERDE, label="Recall")
    for b in list(b1) + list(b2):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.004, f"{b.get_height():.2f}", ha="center", va="bottom", fontsize=8.5)
    for i, r in enumerate(rs):
        if r.get("primera_precision") is not None:
            ax.plot(i - w / 2, r["primera_precision"], marker="D", color=NARANJA, markersize=6, zorder=5)
            ax.plot(i + w / 2, r["primera_recall"], marker="D", color=NARANJA, markersize=6, zorder=5)
    ax.plot([], [], marker="D", color=NARANJA, linestyle="", label="Primera medición ciega\n(antes de corregir lo hallado)")
    ax.set_xticks(list(x))
    ax.set_xticklabels([f"{r['ronda']}\n({r['esperados']} errores)" for r in rs], fontsize=9)
    ax.set_ylim(0.8, 1.1)
    ax.set_yticks([0.8, 0.85, 0.9, 0.95, 1.0])
    ax.axhline(0.95, color=ROJO, linewidth=1, linestyle="--")
    ax.text(-0.48, 0.953, "umbral 0,95", color=ROJO, fontsize=8, ha="left", va="bottom", bbox={"facecolor": "white", "edgecolor": "none", "pad": 1})
    ax.set_title("Juez determinista por ronda", loc="left", fontweight="bold")
    ax.legend(loc="upper center", ncol=3, frameon=False, fontsize=8.5)
    m = datos["muestras_oficiales"]
    ax2.set_axis_off()
    ax2.set_title("Muestras oficiales APA/IEEE", loc="left", fontweight="bold")
    if m.get("disponible"):
        ax2.text(0.02, 0.62, f"{m['falsos_positivos']}", fontsize=54, color=VERDE if m["falsos_positivos"] == 0 else ROJO, fontweight="bold")
        ax2.text(0.02, 0.45, "falsos positivos", fontsize=12)
        ax2.text(0.02, 0.30, f"en {m['muestras']} documentos oficiales", fontsize=10)
        ax2.text(0.02, 0.20, f"({m['verdaderos_positivos_esperados']} errores reales de las\npropias muestras, detectados)", fontsize=9, color=GRIS)
    else:
        ax2.text(0.02, 0.5, "No disponible\n(falta normas/)", fontsize=12, color=GRIS)
    fig.text(0.01, 0.01, "Rondas ciegas: documentos sembrados con errores según la norma, no según el juez. Hoy 1,00 tras corregir lo que cada ronda reveló.",
             fontsize=8, color=GRIS)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    _guardar(fig, "juez-precision-recall.png")
    plt.close(fig)


def grafica_reglas(datos):
    import matplotlib.pyplot as plt
    _estilo(plt)
    fam = datos["reglas"]["familias"]
    orden = [p for p in ("APA", "IEEE", "CON", "EST", "FUE", "EA", "RED") if p in fam]
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(11, 4.6), gridspec_kw={"width_ratios": [1.5, 1]})
    cor = [fam[p]["corregibles"] for p in orden]
    det = [fam[p]["deterministas"] - fam[p]["corregibles"] for p in orden]
    ag = [fam[p]["agente"] for p in orden]
    y = range(len(orden))
    ax.barh(y, cor, color=VERDE, label="Determinista y corregible")
    ax.barh(y, det, left=cor, color=AZUL, label="Determinista (solo detecta)")
    ax.barh(y, ag, left=[a + b for a, b in zip(cor, det)], color=GRIS, label="Agente (juicio)")
    for i, p in enumerate(orden):
        ax.text(fam[p]["total"] + 2, i, str(fam[p]["total"]), va="center", fontsize=9)
    ax.set_yticks(list(y))
    ax.set_yticklabels(orden)
    ax.invert_yaxis()
    ax.set_xlabel("Reglas")
    ax.set_title(f"{datos['reglas']['total']} reglas por familia", loc="left", fontweight="bold")
    ax.legend(loc="lower right", frameon=True, facecolor="white", edgecolor="#c5cbd3", fontsize=8.5)
    ai = datos["reglas"]["apa_ieee"]
    etiquetas = ["Reglas APA/IEEE", "«Fix: sí» en\nel checklist", "IDs que emite\nalgún script", "Corregibles\nautomáticamente"]
    vals = [ai["total"], ai["fix_si_en_checklist"], ai["ids_en_scripts"], ai["corregibles"]]
    cols = [GRIS, NARANJA, AZUL, VERDE]
    ax2.bar(range(4), vals, color=cols)
    for i, v in enumerate(vals):
        ax2.text(i, v + 4, str(v), ha="center", fontsize=10, fontweight="bold")
    ax2.set_xticks(range(4))
    ax2.set_xticklabels(etiquetas, fontsize=8)
    ax2.set_ylim(0, ai["total"] * 1.12)
    ax2.set_title("APA/IEEE: lo automatizable vs lo hecho", loc="left", fontweight="bold", fontsize=10.5)
    fig.text(0.01, 0.01, f"El conteo «determinista» es una heurística (ID presente en un script). El checklist marca {ai['fix_si_en_checklist']} reglas como "
             f"mecánicas y solo {ai['ids_en_scripts']} están implementadas: la brecha es trabajo pendiente.", fontsize=8, color=GRIS)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    _guardar(fig, "reglas-por-familia.png")
    plt.close(fig)


def grafica_piloto(datos):
    import matplotlib.pyplot as plt
    _estilo(plt)
    pts = datos["piloto"]["hitos"]
    fig, ax = plt.subplots(figsize=(11, 4.6))
    xs = list(range(len(pts)))
    ys = [p["puntaje"] for p in pts]
    ax.axhspan(85, 100, color="#e6f2ec", zorder=0)
    ax.text(len(pts) - 0.55, 86, "banda «Publicable»", fontsize=8.5, color=VERDE, ha="right")
    ax.plot(xs, ys, color=AZUL, linewidth=2, marker="o", markersize=8, zorder=3)
    for i, (x, y) in enumerate(zip(xs, ys)):
        ax.annotate(f"{y:.1f}", (x, y), textcoords="offset points", xytext=(0, 11 if i != 4 else -18), ha="center", fontweight="bold")
    ax.set_xticks(xs)
    ax.set_xticklabels([textwrap.fill(p["hito"], 20) for p in pts], fontsize=8.5)
    ax.set_ylim(20, 100)
    ax.set_ylabel("Puntaje /puntuar (0-100)")
    ax.set_title("Piloto anonimizado: protocolo de investigación real de licenciatura", loc="left", fontweight="bold")
    ax.annotate("Más reglas = más hallazgos:\nel puntaje baja y luego se corrige", (4, 87), xytext=(2.6, 52), fontsize=8.5, color=GRIS,
                arrowprops={"arrowstyle": "->", "color": GRIS})
    fig.text(0.01, 0.01, "Valores registrados en cada hito de desarrollo; el documento original no se distribuye.", fontsize=8, color=GRIS)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
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
