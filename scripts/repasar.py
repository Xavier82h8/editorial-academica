#!/usr/bin/env python3
"""Modo de estudio: repasa el documento capítulo por capítulo contra la estructura declarada. NO califica.

Uso:
  python -I scripts/repasar.py <doc.docx|doc.md> [--seccion N|"nombre"] [--estructura <id>] [--lineas 3] [--json RUTA]

Por cada capítulo de la estructura (`estructuras/<id>.yaml`, la de `.editorial.yaml` si no se da `--estructura`) muestra:
  1. qué pide la guía (propósito y extensión de la estructura);
  2. qué tiene el documento (encabezado hallado, palabras, subsecciones, citas, tablas, figuras y las primeras líneas);
  3. preguntas guía para entender y fortalecer esa parte (las de la estructura más las que salen de lo que se ve: sin citas,
     muy breve, sección ausente…).
`--seccion N` repasa solo el capítulo N (0 = preliminares: resumen e índices); `--seccion "objetivo general"` busca por nombre.
Sin puntaje, sin veredicto y sin reglas: es para repasar y entender el protocolo, no para calificar. La lista de cotejo de la
guía la revisa el docente; `puntuar`, `auditar` y `estructura` siguen siendo los comandos que juzgan.
Salida: 0; 2 error de uso o de entrada (ver cli.py).
"""
import argparse
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import auditar  # noqa: E402
import cli  # noqa: E402
import estructura  # noqa: E402
import yaml  # noqa: E402

RE_CITA_APA = re.compile(r"\([^()]{0,160}?\b(?:19|20)\d{2}[a-z]?\s*[,;)]|\b[A-ZÁÉÍÓÚÑ][\w'’\-]+(?:\s+(?:y|and|&|et al\.)\s+[A-ZÁÉÍÓÚÑ][\w'’\-]+|\s+et al\.)?\s*\((?:19|20)\d{2}[a-z]?")
RE_CITA_IEEE = re.compile(r"\[\d+(?:\s*[,–-]\s*\d+)*\]")
RE_TABLA = re.compile(r"^\s*(?:tabla|table)\s+(?:[ivxlc]+|\d+)\b", re.I)
RE_FIGURA = re.compile(r"^\s*(?:fig\.|figura|figure)\s*\d+", re.I)
RE_NUMERO = re.compile(r"(?<![\w.])\d+(?:[.,]\d+)?\s*%?")
PRELIM = ("resumen", "abstract", "indice")


def secciones_documento(path):
    """[{enc, norm, nivel, parrafos, palabras_propias}] en orden: un bloque por encabezado (el contenido anterior al primero queda en un bloque sin encabezado)."""
    pars, meta = estructura.cargar(path)
    bl, actual = [], {"enc": None, "norm": None, "nivel": 0, "parrafos": [], "i": -1}
    for p in pars:
        t = p["texto"].strip()
        estilo = (p.get("estilo") or "").lower()
        es_enc = ((p.get("es_titulo") and not estilo.startswith("title") and not re.match(r"t[ií]tulo(?!\s*\d)", estilo))
                  or estructura.es_preliminar_plano(p)) and 0 < len(t) < 160 and not estilo.startswith("toc")
        if es_enc:
            bl.append(actual)
            actual = {"enc": t, "norm": estructura.norm(t), "nivel": p.get("nivel") or auditar.nivel_estilo(p) or 1, "parrafos": [], "i": p["i"]}
        elif t and not estilo.startswith("toc"):
            actual["parrafos"].append({"texto": t, "tabla": bool(p.get("en_tabla"))})
    bl.append(actual)
    return bl


def alcance(bl, k):
    """Bloques del encabezado k y de sus subsecciones (hasta otro de nivel igual o superior)."""
    out = [bl[k]]
    for b in bl[k + 1:]:
        if b["enc"] is not None and b["nivel"] <= bl[k]["nivel"]:
            break
        out.append(b)
    return out


def medir(bl, k):
    bs = alcance(bl, k)
    texto = [p["texto"] for b in bs for p in b["parrafos"] if not p["tabla"]]
    todo = " ".join(texto)
    return {
        "palabras": len(todo.split()),
        "subsecciones": sum(1 for b in bs[1:] if b["enc"] is not None),
        "citas": len(RE_CITA_APA.findall(todo)) + len(RE_CITA_IEEE.findall(todo)),
        "tablas": sum(1 for t in texto if RE_TABLA.match(t)),
        "figuras": sum(1 for t in texto if RE_FIGURA.match(t)),
        "cifras": len(RE_NUMERO.findall(re.sub(r"\([^()]*\d{4}[^()]*\)", " ", todo))),
    }


def primeras_lineas(bl, k, n, ancho=220):
    """Primeros `n` párrafos propios de la sección (los de sus subsecciones se ven en sus propias filas)."""
    ps = [p["texto"] for p in bl[k]["parrafos"] if not p["tabla"] and len(p["texto"]) > 30]
    return [(t if len(t) <= ancho else t[:ancho].rsplit(" ", 1)[0] + "…") for t in ps[:n]]


def preguntas(s, presente, m):
    """Preguntas de la estructura más las que salen de lo que se ve en el documento."""
    q = list(s.get("preguntas") or [])
    if not presente:
        q.append("Esta parte no aparece: ¿qué pide la guía aquí y dónde del texto actual ya se dice algo parecido?")
        return q
    if m["palabras"] < 60 and not any(x in estructura.norm(s["nombre"]) for x in PRELIM):
        q.append(f"Tiene solo {m['palabras']} palabras: ¿qué le falta para responder las preguntas de arriba?")
    if m["citas"] == 0 and m["palabras"] >= 150:
        q.append("No tiene citas: ¿qué afirmaciones de esta parte necesitan una fuente y cuál la respalda?")
    if m["cifras"] >= 5 and m["citas"] == 0:
        q.append("Trae cifras sin cita: ¿de dónde sale cada cifra (fuente, cálculo propio, supuesto)?")
    if m["tablas"] + m["figuras"] == 0 and m["palabras"] >= 400:
        q.append("Es larga y sin tablas ni figuras: ¿alguna comparación o proceso se entendería mejor en una tabla o un esquema?")
    q.append("¿Puedes explicar esta parte en dos frases sin mirar el texto? Si no, ¿qué idea no está clara?")
    return q


def capitulos(est, bl):
    """[{n, nombre, secciones: [fila]}]: agrupa la estructura en preliminares (0) y capítulos (nivel 1 del documento)."""
    filas, nivel_prev = [], 1
    for s in est["secciones"]:
        alias = [estructura.norm(a) for a in s.get("alias", [])] + [estructura.norm(s["nombre"])]
        k = next((i for i, b in enumerate(bl) if b["enc"] and estructura.coincide(alias, b["norm"])), None)
        nivel = bl[k]["nivel"] if k is not None else nivel_prev
        nivel_prev = nivel
        prelim = any(estructura.norm(s["nombre"]).startswith(x) or (alias and alias[0].startswith(x)) for x in PRELIM)
        filas.append({"s": s, "k": k, "nivel": nivel, "prelim": prelim})
    caps, n = [], 0
    for f in filas:
        if f["prelim"]:
            if not caps or caps[-1]["n"] != 0:
                caps.append({"n": 0, "nombre": "Preliminares", "filas": []})
            caps[-1]["filas"].append(f)
        elif f["nivel"] <= 1 or not caps or caps[-1]["n"] == 0:
            n += 1
            caps.append({"n": n, "nombre": f["s"]["nombre"], "filas": [f]})
        else:
            caps[-1]["filas"].append(f)
    return caps


def repasar(path, genero, seccion=None, lineas=3):
    auditar.validar_entrada(path)
    ruta = ROOT / "estructuras" / f"{genero}.yaml"
    if not ruta.is_file():
        cli.error(f"estructura desconocida: {genero}. Válidas: {', '.join(sorted(f.stem for f in (ROOT / 'estructuras').glob('*.yaml')))}")
    est = yaml.safe_load(ruta.read_text(encoding="utf-8"))
    bl = secciones_documento(path)
    caps = capitulos(est, bl)
    if seccion is not None:
        if re.fullmatch(r"\d+", str(seccion)):
            caps = [c for c in caps if c["n"] == int(seccion)]
        else:
            q = estructura.norm(str(seccion))
            caps = [{**c, "filas": [f for f in c["filas"] if q in estructura.norm(f["s"]["nombre"])]} for c in caps]
            caps = [c for c in caps if c["filas"]]
        if not caps:
            cli.error(f"--seccion {seccion}: no hay capítulo ni sección con ese número o nombre (usa 0 para preliminares o un nombre de la estructura)")
    out = []
    for c in caps:
        secs = []
        for f in c["filas"]:
            s, k = f["s"], f["k"]
            m = medir(bl, k) if k is not None else None
            secs.append({"nombre": s["nombre"], "obligatoria": bool(s.get("obligatoria")), "pide_la_guia": s.get("proposito"),
                         "extension": s.get("extension") or s.get("palabras"),
                         "encabezado": bl[k]["enc"] if k is not None else None, "tiene": m,
                         "primeras_lineas": primeras_lineas(bl, k, lineas) if k is not None else [],
                         "preguntas": preguntas(s, k is not None, m)})
        out.append({"n": c["n"], "nombre": c["nombre"], "secciones": secs})
    return {"documento": str(path), "estructura": est["id"] if "id" in est else genero, "nombre": est.get("nombre"), "capitulos": out}


def imprimir(r):
    print(f"REPASO (modo de estudio, sin puntaje): {r['nombre'] or r['estructura']}")
    for c in r["capitulos"]:
        print("\n" + ("=" * 72))
        print("PRELIMINARES" if c["n"] == 0 else f"CAPÍTULO {c['n']}: {c['nombre']}")
        for s in c["secciones"]:
            print(f"\n- {s['nombre']}" + (" (obligatoria)" if s["obligatoria"] else ""))
            print(f"  La guía pide: {s['pide_la_guia'] or '—'}" + (f" [extensión: {s['extension']}]" if s["extension"] else ""))
            m = s["tiene"]
            if m is None:
                print("  El documento tiene: no encuentro esta parte.")
            else:
                print(f"  El documento tiene: «{s['encabezado']}», {m['palabras']} palabras, {m['subsecciones']} subsecciones, "
                      f"{m['citas']} citas, {m['tablas']} tablas, {m['figuras']} figuras, {m['cifras']} cifras.")
                for t in s["primeras_lineas"]:
                    print(f"    · {t}")
                if not s["primeras_lineas"] and m["subsecciones"]:
                    print("    (sin texto propio: se desarrolla en sus subsecciones)")
            print("  Preguntas para repasar:")
            for q in s["preguntas"]:
                print(f"    ? {q}")
    print("\nEsto es para repasar y entender el protocolo, no para calificar: no hay puntaje ni veredicto. "
          "La lista de cotejo la revisa el docente; para juzgar usa auditar, estructura o puntuar.")


def main():
    ap = argparse.ArgumentParser(description="Modo de estudio: repaso por capítulo (qué pide la guía, qué tiene el documento, preguntas guía). No califica.")
    ap.add_argument("documento")
    ap.add_argument("--seccion", help="capítulo N (0 = preliminares) o parte del nombre de una sección; por defecto, todos")
    ap.add_argument("--estructura", help="id de estructuras/<id>.yaml; por defecto el `estructura:` de .editorial.yaml o «informe»")
    ap.add_argument("--perfil", help="se acepta por uniformidad; el repaso no depende del perfil")
    ap.add_argument("--lineas", type=int, default=3, help="párrafos iniciales que se muestran por sección (por defecto 3)")
    ap.add_argument("--json", metavar="RUTA", help="escribe el repaso completo como JSON")
    a = ap.parse_args()
    cli.utf8()
    genero = a.estructura
    if not genero:
        eq = auditar.buscar_equipo(a.documento)
        cfg = (yaml.safe_load(eq.read_text(encoding="utf-8")) or {}) if eq and eq.exists() else {}
        genero = (cfg.get("estructura") if isinstance(cfg, dict) else None) or "informe"
    r = repasar(a.documento, genero, a.seccion, a.lineas)
    cli.escribir_json(a.json, r, indent=2)
    imprimir(r)
    sys.exit(cli.OK)


if __name__ == "__main__":
    main()
