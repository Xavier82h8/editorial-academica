#!/usr/bin/env python3
"""Modo calificar: auditar + estructura + congruencia + puntuar + medir en una corrida, SOLO LECTURA garantizada.

Uso: python scripts/editorial.py calificar doc.docx [--perfil ID] [--estructura GENERO] [--equipo RUTA] [--con-red] [--json RUTA]

Es lo que se corre cuando el usuario solo pide calificar o revisar su proyecto. No escribe nada: calcula el sha256 del archivo y
la lista de archivos de su carpeta antes y después, y si algo cambió termina con error (código 2). No escribe historial de
puntajes, ni .json, ni copias. Salida: perfil aplicado, puntaje con sus dimensiones, hallazgos por prioridad y «ajustes
sugeridos»: cuáles son automáticos de formato (`corregir --fiel`), cuáles automáticos pero cambian texto (propuestas que aprueba
el usuario) y cuáles requieren al usuario. Sin red por defecto (`--con-red` verifica las fuentes en línea).
Código de salida: 0 sin hallazgos críticos ni mayores, 1 con alguno, 2 error de uso o archivo modificado.
"""
import argparse
import hashlib
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import auditar  # noqa: E402
import cli  # noqa: E402

ORDEN = {"crítica": 0, "mayor": 1, "menor": 2}


def _sha(ruta):
    return hashlib.sha256(pathlib.Path(ruta).read_bytes()).hexdigest()


def _carpeta(ruta):
    """{ruta relativa: (tamaño, mtime_ns)} de la carpeta del documento y de su subcarpeta .editorial (donde iría el historial)."""
    base = pathlib.Path(ruta).resolve().parent
    out = {}
    for d in (base, base / ".editorial"):
        if d.is_dir():
            for e in os.scandir(d):
                if e.is_file():
                    st = e.stat()
                    out[str(pathlib.Path(e.path).relative_to(base))] = (st.st_size, st.st_mtime_ns)
    return out


def clasificar(hallazgos, base):
    """Reparte los hallazgos en automáticos (formato), automáticos con aprobación (cambian texto) y manuales.
    -> {"formato": {id: n}, "texto": {id: n}, "usuario": {id: (n, motivo)}}"""
    import corregir as C
    auto = set(C.REGLAS) if base == "apa7" else (set(C.REGLAS) & C.REGLAS_IEEE)
    out = {"formato": {}, "texto": {}, "usuario": {}}
    for h in hallazgos:
        i = h["id"]
        if i in auto and i in C.REGLAS_TEXTO:
            out["texto"][i] = out["texto"].get(i, 0) + 1
        elif i in auto:
            out["formato"][i] = out["formato"].get(i, 0) + 1
        else:
            motivo = C.NO_AUTO.get(i) or ("no tiene corrección automática: " + (h.get("correccion") or "decisión del autor"))
            n = out["usuario"].get(i, (0, motivo))[0] + 1
            out["usuario"][i] = (n, motivo)
    # reglas que corregir cubre solo en parte: lo que sobra queda para el usuario
    for i in list(out["formato"]) + list(out["texto"]):
        if i in C.NO_AUTO:
            n = (out["formato"].get(i) or out["texto"].get(i))
            out["usuario"][i] = (n, "en parte: " + C.NO_AUTO[i])
    return out


def calificar(doc, perfil, estructura, equipo=None, sin_red=True):
    """Todo el análisis, sin escribir nada. Devuelve el dict de resultados (con `solo_lectura`)."""
    import congruencia
    import estructura as E
    import medir
    import puntuar as P
    auditar.validar_entrada(doc)
    antes_hash, antes_dir = _sha(doc), _carpeta(doc)
    cfg = auditar.cargar_perfil(perfil)
    aud = auditar.auditar(doc, perfil, equipo)
    est = E.revisar(doc, estructura, perfil)
    con = congruencia.revisar(doc)
    pun = P.puntuar(doc, perfil, estructura, None, None, None, sin_red)
    ficha = med = None
    if str(doc).lower().endswith(".docx"):
        ficha = medir.ficha_docx(str(doc))
        med = _resumen_ficha(medir, ficha)
        if medir._hay_medidas(pathlib.Path(doc), equipo):
            import medidas as M
            med["reglas"] = M.evaluar_todo(ficha, None, [], None, pathlib.Path(doc), equipo, False, None)["resultados"]
    visto, todos = set(), []
    for origen, lista in (("auditar", aud["hallazgos"]), ("estructura", est["hallazgos"]), ("congruencia", con["hallazgos"])):
        for h in lista:
            k = (h["id"], h.get("ubicacion"), h.get("evidencia"))
            if k not in visto:
                visto.add(k)
                todos.append({**h, "origen": origen})
    todos.sort(key=lambda h: (ORDEN.get(h["severidad"], 3), h["id"]))
    if _sha(doc) != antes_hash or _carpeta(doc) != antes_dir:
        cli.error("ERROR: calificar modificó el archivo o su carpeta; es un defecto (calificar es de solo lectura). No uses esta corrida.")
    return {"documento": str(doc), "perfil": perfil, "estructura": estructura, "solo_lectura": {"sha256": antes_hash, "sin_cambios": True},
            "puntaje": {k: pun[k] for k in ("total", "banda", "bloqueos", "dimensiones", "maximos", "conteo", "top5")},
            "dictamen_mecanico": aud["dictamen_mecanico"], "cobertura_estructura": est["cobertura"], "hallazgos": todos,
            "ajustes": clasificar([h for h in todos if h["origen"] != "congruencia"], cfg["base"]) | {"congruencia": len([h for h in todos if h["origen"] == "congruencia"])},
            "medidas": med, "avisos": aud["avisos"], "excepciones": len(aud.get("excepciones", []))}


def _resumen_ficha(medir, ficha):
    sec = medir.seccion_principal(ficha)
    g = lambda a: medir.dominante(ficha, "cuerpo", a)  # noqa: E731
    return {"margenes_cm": {k: sec["margenes"][k]["cm"] for k in ("superior", "inferior", "izquierdo", "derecho")},
            "numero_pagina": sec["numero_pagina"]["donde"],
            "cuerpo": {"fuente": g("fuente"), "tamano_pt": g("tamano"), "alineacion": g("alineacion"),
                       "interlineado": (g("interlineado") or {}).get("texto") if isinstance(g("interlineado"), dict) else g("interlineado"),
                       "primera_linea_cm": (g("primera") or {}).get("cm") if isinstance(g("primera"), dict) else g("primera")}}


def imprimir(r):
    p = r["puntaje"]
    print(f"CALIFICAR: {r['documento']}   (solo lectura: sha256 {r['solo_lectura']['sha256'][:12]} igual antes y después; nada escrito)")
    print(f"PUNTAJE: {p['total']}/100 — {p['banda']}" + (f"   (bloqueos: {', '.join(p['bloqueos'])})" if p["bloqueos"] else ""))
    for k, v in p["dimensiones"].items():
        print(f"  {k:<12} {v:>5} / {p['maximos'][k]}")
    print(f"DICTAMEN MECÁNICO: {r['dictamen_mecanico']}   estructura: cobertura {r['cobertura_estructura']:.0%}   perfil: {r['perfil']}")
    m = r["medidas"]
    if m:
        mg = m["margenes_cm"]
        c = m["cuerpo"]
        print(f"MEDIDAS: márgenes sup {mg['superior']:g} / inf {mg['inferior']:g} / izq {mg['izquierdo']:g} / der {mg['derecho']:g} cm; "
              f"cuerpo {c['fuente']} {c['tamano_pt']} pt, interlineado {c['interlineado']}, primera línea {c['primera_linea_cm']} cm, {c['alineacion']}; "
              f"número de página: {m['numero_pagina']}")
        for x in m.get("reglas", []):
            print(f"  medida {x['estado'].upper()}: {x['texto']}")
    for av in r["avisos"][:6]:
        print("AVISO:", av)
    print(f"\nHALLAZGOS POR PRIORIDAD ({len(r['hallazgos'])}):")
    print("| # | ID | Severidad | Ubicación | Evidencia | Corrección |\n|---|---|---|---|---|---|")
    for i, h in enumerate(r["hallazgos"], 1):
        print(f"| {i} | {h['id']} | {h['severidad']} | {h['ubicacion']} | {h['evidencia']} | {h['correccion']} |")
    a = r["ajustes"]
    print("\nAJUSTES SUGERIDOS")
    if a["formato"]:
        print("  Automáticos, solo formato (no tocan el texto): " + ", ".join(f"{i} ({n})" for i, n in sorted(a["formato"].items())))
        print("      -> corregir DOC --fiel")
    if a["texto"]:
        print("  Con corrección automática que cambiaría texto (si el corrector puede resolverlas quedan como PROPUESTA; las apruebas tú): " + ", ".join(f"{i} ({n})" for i, n in sorted(a["texto"].items())))
        print("      -> corregir DOC --fiel genera <doc>.propuestas.json; --aplicar-propuestas ARCHIVO --solo ID,ID aplica las que apruebes")
    if a["usuario"]:
        print("  Requieren al usuario (no se corrigen solos):")
        for i, (n, motivo) in sorted(a["usuario"].items()):
            print(f"      {i} ({n}): {motivo}")
    if a["congruencia"]:
        print(f"  Congruencia ({a['congruencia']} hallazgos): decisión del autor; ninguna se corrige sola")
    if not (a["formato"] or a["texto"] or a["usuario"] or a["congruencia"]):
        print("  ninguno")
    print("\nNada de esto se aplicó. Calificar no redacta, no reescribe y no cambia estructura, citas ni contenido.")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="editorial calificar", description="Califica un documento sin tocarlo: auditar + estructura + congruencia + puntuar + medir.")
    ap.add_argument("documento")
    ap.add_argument("--perfil", help="id de perfil; por defecto el `perfil:` de .editorial.yaml")
    ap.add_argument("--estructura", help="género; por defecto el `estructura:` de .editorial.yaml o «informe»")
    ap.add_argument("--equipo", help="ruta de .editorial.yaml (si no, se busca hacia arriba desde el documento)")
    ap.add_argument("--con-red", action="store_true", dest="con_red", help="verifica las fuentes en línea (por defecto, sin red)")
    ap.add_argument("--json", metavar="RUTA", help="escribe el resultado completo como JSON (fuera de la carpeta del documento si quieres un solo-lectura estricto)")
    a = ap.parse_args(argv)
    cli.utf8()
    perfil = cli.perfil_por_defecto(ap, a.perfil, a.documento, a.equipo)
    estructura = a.estructura
    if not estructura:
        eq = auditar.buscar_equipo(a.documento, a.equipo)
        cfg = (auditar.yaml.safe_load(eq.read_text(encoding="utf-8")) or {}) if eq and eq.exists() else {}
        estructura = (cfg.get("estructura") if isinstance(cfg, dict) else None) or "informe"
    r = calificar(a.documento, perfil, estructura, a.equipo, not a.con_red)
    imprimir(r)
    cli.escribir_json(a.json, r, indent=2)
    sys.exit(cli.codigo(r["hallazgos"]))


if __name__ == "__main__":
    main()
