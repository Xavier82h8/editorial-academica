#!/usr/bin/env python3
"""Puntaje editorial 0-100 de un documento (rúbrica de la skill puntuar) con historial.

Uso:
  python -I puntuar.py <doc.docx|doc.md> --perfil <id> [--estructura informe] [--fuentes fuentes.json]
                       [--evidencias evidencias.json] [--congruencia-llm congruencia.json] [--sin-red]
                       [--json salida.json] [--sin-historial]
Sin --perfil / --estructura se usan los de `.editorial.yaml`. Salida: 0 sin hallazgos críticos ni mayores en ninguna
dimensión; 1 con ellos (o con bloqueos); 2 error de uso o de entrada (ver cli.py).

Dimensiones (pesos):
  Congruencia 30  scripts/congruencia.py (+ hallazgos del agente revisor-congruencia si se pasan): −5 crítica, −2 mayor, −0.5 menor
  Fuentes     25  V1-V3 (fuentes.py): si alguna falla vale 0 y bloquea «Publicable»; V4 calidad 40 %; V5 sustento 60 %
  Formato     20  scripts/auditar.py: −6 crítica, −3 mayor, −1 menor
  Estructura  15  scripts/estructura.py: 15 × cobertura de obligatorias, −1 por EST-002/EST-003/EST-004
  Redacción   10  señales mecánicas por cada 1000 palabras (puntuación, marcadores EA-001, oraciones > 40 palabras)
Bandas: ≥ 90 Publicable · 75-89 Correcciones menores · 60-74 Correcciones mayores · < 60 Rechazado.
Bloqueo: una fuente que falle V1-V3 o una incongruencia crítica impide «Publicable».
Todo es determinista (mismo documento ⇒ mismo puntaje); lo que viene de agentes entra por archivo JSON.
Historial: <carpeta del documento>/.editorial/puntajes.jsonl
"""
import argparse
import datetime as dt
import hashlib
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "skills" / "fuentes-academicas" / "scripts"))
import auditar  # noqa: E402
import cli  # noqa: E402
import estructura  # noqa: E402
import fuentes as modulo_fuentes  # noqa: E402  (skills/fuentes-academicas/scripts/fuentes.py)


PESO_FMT = {"crítica": 6, "mayor": 3, "menor": 1}
PESO_CON = {"crítica": 5, "mayor": 2, "menor": 0.5}


def banda(p):
    return "Publicable" if p >= 90 else "Correcciones menores" if p >= 75 else "Correcciones mayores" if p >= 60 else "Rechazado"


def dim_formato(doc, perfil):
    r = auditar.auditar(doc, perfil)
    H = [h for h in r["hallazgos"] if h["id"] != "EA-001" and not h["id"].startswith("FUE-")]  # FUE-V4N cuenta en «Fuentes»
    # por regla distinta: peso base la primera vez y 1/4 del peso por cada repetición, hasta el doble del base
    # (10 citas mal formadas son un problema de formato, no diez)
    pen, vistos = [], {}
    for h in H:
        base = PESO_FMT.get(h["severidad"], 1)
        k = vistos.get(h["id"], 0)
        p = base if k == 0 else (base / 4 if k < 5 else 0)
        vistos[h["id"]] = k + 1
        pen.append((p, h))
    return max(0.0, 20 - sum(p for p, _ in pen)), pen, r


def dim_congruencia(doc, llm=None):
    try:
        import congruencia
        H = list(congruencia.revisar(doc)["hallazgos"])
    except ImportError:
        H = []
    if llm:
        vistos = {(h["id"], h.get("evidencia")) for h in H}
        H += [h for h in json.loads(pathlib.Path(llm).read_text(encoding="utf-8")).get("hallazgos", [])
              if (h["id"], h.get("evidencia")) not in vistos]
    pen = [(PESO_CON.get(h["severidad"], 1), h) for h in H]
    critica = any(h["severidad"] == "crítica" for h in H)
    return max(0.0, 30 - sum(p for p, _ in pen)), pen, critica


def items_fuentes(doc, fuentes, r_fmt):
    """fuentes.json si se da; si no, la lista de referencias del documento parseada a CSL (refs_csl)."""
    if fuentes:
        return json.loads(pathlib.Path(fuentes).read_text(encoding="utf-8")), "fuentes.json"
    import refs_csl
    pars, _ = (auditar.cargar_docx if doc.lower().endswith(".docx") else auditar.cargar_md)(doc)
    _, _, entradas = auditar.partir(pars)
    textos = [e["texto"] for e in entradas if e["texto"].strip()]
    items = refs_csl.parsear_lista(textos) if textos else []
    for it, t in zip(items, textos):
        it["_original"] = t
    return items, "lista del documento"


def dim_fuentes(doc, fuentes, evidencias, r_fmt, sin_red):
    buscar = modulo_fuentes
    buscar.SIN_RED = sin_red
    items, origen = items_fuentes(doc, fuentes, r_fmt)
    if not items:
        return 0.0, [(25, {"id": "FUE-000", "severidad": "crítica", "ubicacion": "documento",
                           "evidencia": "sin referencias", "correccion": "citar fuentes verificadas"})], True, {}
    res = [buscar.verificar_item(it) for it in items]
    con_doi = [r for r in res if r["doi"]]
    fallan = [r for r in res if r["doi"] and not r["ok"]]          # DOI que no existe, no coincide o retractado: bloquea
    rotas = [r for r in res if not r["doi"] and r.get("url") == "roto"]
    url_ok = [r for r in res if not r["doi"] and r.get("url") in ("ok", "registro")]
    sin_ver = [r for r in res if not r["doi"] and r.get("url") in (None, "no verificable")]
    # V1/V3 sin comprobar por fallo de red o de consulta: no bloquea, pero no cuenta como verificada (medio crédito en V4)
    no_ver = [r for r in con_doi if r["ok"] and r.get("estado") == "no_verificado"]
    pen = []
    for r in fallan:
        motivo = r.get("nota") or "; ".join(r["v2"] + [a["tipo"] for a in r["v3"].get("avisos", [])])
        pen.append((25 / max(1, len(res)), {"id": "FUE-V123", "severidad": "crítica", "ubicacion": r["id"] or r["doi"],
                                            "evidencia": f"{r['doi']}: {motivo}", "correccion": "corregir o sustituir la fuente"}))
    for r in rotas:
        pen.append((10 / len(res), {"id": "FUE-URL", "severidad": "mayor", "ubicacion": r["id"] or "referencia",
                                    "evidencia": f"URL rota: {items[res.index(r)].get('URL')}",
                                    "correccion": "actualizar la URL o citar una versión archivada"}))
    for i, r in enumerate(res):
        if r.get("doi_sugerido"):
            pen.append((0.25, {"id": "APA-077", "severidad": "menor", "ubicacion": (items[i].get("title") or "")[:60],
                               "evidencia": f"la obra tiene DOI {r['doi_sugerido']} y la referencia no lo incluye",
                               "correccion": f"añadir https://doi.org/{r['doi_sugerido']} (APA 9.34)"}))
    # V4: DOI sin avisos y URL que responde (o registro hallado) cuentan completo; sin enlace comprobable, medio
    sin_doi = len(sin_ver)
    v4 = (sum(1 for r in con_doi if r["ok"] and r.get("estado") != "no_verificado" and not r.get("v4"))
          + len(url_ok) + 0.5 * len(sin_ver) + 0.5 * len(no_ver)) / len(res)
    # V5: evidencias del agente si existen; si no, la señal mecánica de cifras (solo con .md y fuentes.json)
    v5, det5 = None, ""
    if evidencias and pathlib.Path(evidencias).exists():
        ev = json.loads(pathlib.Path(evidencias).read_text(encoding="utf-8"))
        cnt = {k: sum(e["veredicto"] == k for e in ev) for k in ("respaldada", "parcial", "contradicha", "no verificable")}
        # «no verificable» (la fuente no publica resumen) cuenta la mitad, como V4 con los enlaces sin comprobar:
        # un documento con casi todo sin verificar no puede llegar al máximo por una sola afirmación respaldada
        v5 = (cnt["respaldada"] + 0.5 * cnt["parcial"] + 0.5 * cnt["no verificable"]) / len(ev) if ev else 0.5
        det5 = f"agente: {cnt}"
        for e in ev:
            if e["veredicto"] == "contradicha":
                pen.append((15 / max(1, len(ev)), {"id": "FUE-V5", "severidad": "mayor", "ubicacion": f"oración {e['n']}",
                                                   "evidencia": e["oracion"][:120], "correccion": e.get("sugerencia") or "corregir la afirmación"}))
    elif fuentes and doc.lower().endswith(".md"):
        import afirmaciones
        af = afirmaciones.extraer(pathlib.Path(doc).read_text(encoding="utf-8-sig"), items)
        if af:
            malas = [a for a in af if a["cifras_sin_respaldo"]]
            nover = [a for a in af if a["sin_resumen"] and not a["cifras_sin_respaldo"]]
            v5 = 0.8 * (len(af) - len(malas) - 0.5 * len(nover)) / len(af)  # sin el agente V5 el sentido no se verifica: máx. 0.8
            det5 = f"cifras sin respaldo: {len(malas)}/{len(af)}"
            for a in malas:
                pen.append((15 / len(af), {"id": "FUE-V5", "severidad": "mayor", "ubicacion": f"[{a['seccion']}]",
                                           "evidencia": a["oracion"][:120], "correccion": "la cifra no está en el resumen de la fuente citada"}))
    if v5 is None:
        v5 = 0.5  # sustento no verificable: ni premio ni castigo completo
        det5 = "no verificable (sin fuentes.json/.md ni evidencias.json)"
    # pirámide de fuentes (nivel de evidencia A-E, scripts/niveles.py) y FUE-V4N (afirmación sustantiva solo con fuente D/E)
    import niveles
    nivs = [(it.get("_nivel") or niveles.clasificar(it, it.get("_original")))["nivel"] for it in items]
    v4n = []
    try:  # FUE-V4N: afirmaciones sustantivas cuyas citas son todas de nivel D/E (aquí siempre; en auditar solo con `fuentes: {niveles: true}`)
        pars_, _ = (auditar.cargar_docx if doc.lower().endswith(".docx") else auditar.cargar_md)(doc)
        cuerpo_, _, entradas_ = auditar.partir(pars_)
        v4n = niveles.hallazgos_nivel_bajo(pars_, [p for p in cuerpo_ if p["texto"].strip()], entradas_, auditar.Hallazgo, auditar)[0]
    except Exception:  # noqa: BLE001  (sin lista o cuerpo analizable no hay afirmaciones que medir)
        v4n = []
    for h in v4n:
        pen.append((0.5, h))
    puntos = 0.0 if fallan else max(0.0, 10 * v4 + 15 * v5 - 0.5 * min(len(v4n), 6))  # tope de 3 puntos
    if no_ver:  # solo se reporta: el costo ya está en V4
        pen.append((0.0, {"id": "FUE-V3N", "severidad": "menor", "ubicacion": "lista de referencias",
                          "evidencia": f"{len(no_ver)} de {len(res)} fuentes con DOI sin comprobar (V1/V3): "
                                       + "; ".join(sorted({r['motivo'] for r in no_ver}))[:200],
                          "correccion": "repetir con red para comprobar existencia y retractaciones"}))
    if sin_doi:
        pen.append((5 * sin_doi / len(res), {"id": "FUE-V4", "severidad": "menor", "ubicacion": "lista de referencias",
                                            "evidencia": f"{sin_doi} de {len(res)} referencias sin enlace comprobable (DOI o URL que responda)",
                                            "correccion": "añadir DOI, o URL oficial que responda"}))
    det = {"origen": origen, "total": len(res), "con_doi": len(con_doi), "fallan_v123": len(fallan),
           "url_ok": len(url_ok), "url_rotas": len(rotas), "sin_enlace_comprobable": len(sin_ver),
           "no_verificado": len(no_ver),
           "v4": round(v4, 3), "v5": round(v5, 3), "v5_detalle": det5,
           "piramide": niveles.piramide(nivs), "peso_medio_nivel": niveles.peso_medio(nivs), "afirmaciones_nivel_bajo": len(v4n)}
    return puntos, pen, bool(fallan), det


def dim_estructura(doc, genero):
    r = estructura.revisar(doc, genero)
    maq = {"EST-010", "EST-011", "EST-012", "EST-013", "EST-014", "EST-015"}

    def peso(h):
        if h["id"] == "EST-001":
            return 15 / max(1, sum(s["obligatoria"] for s in r["secciones"]))
        if h["id"] in maq:  # maquetación: aviso ligero (las muestras oficiales APA tampoco fijan keep/cantSplit)
            return 1.0 if h["severidad"] == "mayor" else 0.5
        return 1

    pen = [(peso(h), h) for h in r["hallazgos"]]
    extra = sum(p for p, h in pen if h["id"] not in maq and h["id"] != "EST-001")
    extra += min(3.0, sum(p for p, h in pen if h["id"] in maq))  # tope de 3 puntos por maquetación
    return max(0.0, 15 * r["cobertura"] - extra), pen, r


def dim_redaccion(doc, r_fmt):
    # en Markdown el bloque YAML inicial no es prosa: no cuenta como oración larga (RED-001)
    pars, _ = auditar.cargar_docx(doc) if doc.lower().endswith(".docx") else auditar.cargar_md(doc, frontmatter=True)
    texto = " ".join(p["texto"] for p in pars if not p.get("es_titulo") and len(p["texto"]) > 80)
    palabras = max(1, len(texto.split()))
    import afirmaciones
    largas = [o for o in afirmaciones.oraciones(texto) if len(o.split()) > 40]  # no corta en «et al.» ni «p.»
    mec = [h for h in r_fmt["hallazgos"] if h["id"] in ("APA-115", "APA-145", "IEEE-140")]
    ea = [h for h in r_fmt["hallazgos"] if h["id"] == "EA-001"]
    pen = [(1.0, h) for h in mec]
    pen += [(3.0, h) for h in ea]
    pen += [(0.5, {"id": "RED-001", "severidad": "menor", "ubicacion": "texto", "evidencia": o[:100] + "…",
                   "correccion": "dividir la oración (más de 40 palabras)"}) for o in largas]
    por_mil = sum(p for p, _ in pen) * 1000 / palabras
    return max(0.0, 10 - por_mil), pen, {"palabras": palabras, "oraciones_largas": len(largas)}


def puntuar(doc, perfil, genero="informe", fuentes=None, evidencias=None, llm=None, sin_red=False):
    auditar.validar_entrada(doc)
    auditar.cargar_perfil(perfil)
    f_pts, f_pen, r_fmt = dim_formato(doc, perfil)
    c_pts, c_pen, c_crit = dim_congruencia(doc, llm)
    s_pts, s_pen, s_bloq, s_det = dim_fuentes(doc, fuentes, evidencias, r_fmt, sin_red)
    e_pts, e_pen, r_est = dim_estructura(doc, genero)
    r_pts, r_pen, r_det = dim_redaccion(doc, r_fmt)
    dims = {"congruencia": round(c_pts, 1), "fuentes": round(s_pts, 1), "formato": round(f_pts, 1),
            "estructura": round(e_pts, 1), "redaccion": round(r_pts, 1)}
    total = round(sum(dims.values()), 1)
    bloqueos = []
    if s_bloq:
        bloqueos.append("fuente que falla V1-V3")
    if c_crit:
        bloqueos.append("incongruencia crítica")
    b = banda(total)
    if b == "Publicable" and bloqueos:
        b = "Correcciones menores"
    todas = [(p, "formato", h) for p, h in f_pen] + [(p, "congruencia", h) for p, h in c_pen] + \
            [(p, "fuentes", h) for p, h in s_pen] + [(p, "estructura", h) for p, h in e_pen] + \
            [(p, "redaccion", h) for p, h in r_pen]
    top = sorted(todas, key=lambda x: -x[0])[:5]
    return {"documento": str(doc), "perfil": perfil, "estructura": genero, "total": total, "banda": b,
            "bloqueos": bloqueos, "dimensiones": dims,
            "conteo": {s: sum(h.get("severidad") == s for _, _, h in todas) for s in ("crítica", "mayor", "menor")},
            "maximos": {"congruencia": 30, "fuentes": 25, "formato": 20, "estructura": 15, "redaccion": 10},
            "detalle_fuentes": s_det, "detalle_redaccion": r_det,
            "top5": [{"dimension": d, "puntos": round(p, 1), **{k: h.get(k) for k in ("id", "severidad", "ubicacion", "evidencia", "correccion")}}
                     for p, d, h in top]}


def historial(r, doc):
    d = pathlib.Path(doc).resolve().parent / ".editorial"
    d.mkdir(exist_ok=True)
    h = hashlib.sha256(pathlib.Path(doc).read_bytes()).hexdigest()[:12]
    fila = {"fecha": dt.datetime.now().isoformat(timespec="seconds"), "documento": pathlib.Path(doc).name, "hash": h,
            "total": r["total"], "banda": r["banda"], "dimensiones": r["dimensiones"]}
    ruta = d / "puntajes.jsonl"
    previas = [json.loads(x) for x in ruta.read_text(encoding="utf-8").splitlines() if x.strip()] if ruta.exists() else []
    with open(ruta, "a", encoding="utf-8") as f:
        f.write(json.dumps(fila, ensure_ascii=False) + "\n")
    return [p for p in previas if p["documento"] == fila["documento"]][-5:]


def main():
    p = argparse.ArgumentParser(description="Puntaje editorial 0-100 con las 5 correcciones de mayor impacto.")
    p.add_argument("doc")
    p.add_argument("--perfil", help="por defecto, el de .editorial.yaml")
    p.add_argument("--estructura", help="por defecto, la de .editorial.yaml o «informe»")
    p.add_argument("--fuentes")
    p.add_argument("--evidencias")
    p.add_argument("--congruencia-llm")
    p.add_argument("--sin-red", action="store_true")
    p.add_argument("--equipo", help="ruta de .editorial.yaml: se aplica aunque pidas otro --perfil")
    p.add_argument("--json", metavar="RUTA", help="escribe el resultado completo como JSON")
    p.add_argument("--sin-historial", action="store_true",
                   help="no escribe el historial `.editorial/puntajes.jsonl` junto al documento (es del proyecto del usuario)")
    a = p.parse_args()
    cli.utf8()
    for opcion, ruta in (("--fuentes", a.fuentes), ("--evidencias", a.evidencias), ("--congruencia-llm", a.congruencia_llm)):
        if ruta and not pathlib.Path(ruta).is_file():
            cli.error(f"{opcion}: no existe el archivo {ruta}")
    a.perfil = cli.perfil_por_defecto(p, a.perfil, a.doc, a.equipo)
    eq = auditar.buscar_equipo(a.doc, a.equipo)
    cfg = (auditar.yaml.safe_load(eq.read_text(encoding="utf-8")) or {}) if eq else {}
    a.estructura = a.estructura or cfg.get("estructura") or "informe"
    r = puntuar(a.doc, a.perfil, a.estructura, a.fuentes, a.evidencias, a.congruencia_llm, a.sin_red)
    cli.escribir_json(a.json, r, indent=2)
    print(f"PUNTAJE: {r['total']}/100 — {r['banda']}" + (f"   (bloqueos: {', '.join(r['bloqueos'])})" if r["bloqueos"] else ""))
    for k, v in r["dimensiones"].items():
        print(f"  {k:<12} {v:>5} / {r['maximos'][k]}")
    det = dict(r["detalle_fuentes"])
    pir = det.pop("piramide", None)
    print(f"  fuentes: {det}")
    if pir:
        import niveles
        print("\nPirámide de fuentes (nivel de evidencia; peso medio " + str(det.get("peso_medio_nivel")) + "):")
        print(niveles.texto_piramide(pir, det.get("total")))
    print("\nCorrecciones de mayor impacto:")
    for i, t in enumerate(r["top5"], 1):
        print(f"  {i}. +{t['puntos']} {t['dimension']} | {t['id']} {t['severidad']} | {t['ubicacion']} | {t['evidencia']} | {t['correccion']}")
    if not a.sin_historial:
        prev = historial(r, a.doc)
        if prev:
            print("\nHistorial: " + " → ".join(f"{x['total']}" for x in prev) + f" → {r['total']}")
    sys.exit(cli.HALLAZGOS if r["bloqueos"] or r["conteo"]["crítica"] or r["conteo"]["mayor"] else cli.OK)


if __name__ == "__main__":
    main()
