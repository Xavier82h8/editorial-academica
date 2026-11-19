#!/usr/bin/env python3
"""Juez de estructura por género: compara las secciones del documento con estructuras/<genero>.yaml.

Uso:
  python -I estructura.py <doc.docx|doc.md> --estructura informe|tesis|articulo-imryd|protocolo|revision-sistematica|ensayo|propuesta [--json salida.json]
  python -I estructura.py --listar

Reglas:
  EST-001 mayor  sección obligatoria ausente
  EST-002 menor  secciones obligatorias fuera del orden del género
  EST-003 menor  extensión de una sección muy lejos de la orientativa (< 1/2 o > 2 veces), solo en documentos de 800+ palabras
La introducción sin encabezado (APA 2.11) cuenta como presente si hay texto antes del primer encabezado de sección.
Salida JSON: {documento, estructura, secciones: [{nombre, presente, encabezado, palabras}], hallazgos, cobertura}
cobertura = obligatorias presentes / obligatorias (dimensión «Estructura» de /puntuar).

Maquetación (solo .docx, scripts/maquetacion.py), se suma a «hallazgos» y va también en «maquetacion»:
  EST-010 mayor  PAGE en encabezado y pie    EST-011 menor  «Página X de Y»
  EST-012 mayor  tabla/figura que puede partirse    EST-013 menor  tabla larga sin fila de encabezado repetida
  EST-014 menor  encabezado pegado a tabla/figura/nota    EST-015 menor  nota «Fuente:»/remite a sección/«Adaptado de» sin título
  EST-016 menor  numeración de la portada contraria a `portada_numero:` de .editorial.yaml (o a APA §2.18: la portada lleva el 1)
«maquetacion_info»: {portada_numero: encabezado|pie|ninguno, preferencia: si|no|None, perfil_pide: si|None}
--perfil <id> elige el perfil de formato (por defecto el de .editorial.yaml, si no apa7); --estructura por defecto
la de .editorial.yaml, si no «informe».
Salida: 0 sin hallazgos o solo menores; 1 con hallazgos críticos o mayores; 2 error de uso o de entrada (ver cli.py).
"""
import argparse
import json
import pathlib
import re
import sys
import unicodedata

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import auditar  # noqa: E402
import cli  # noqa: E402
import maquetacion  # noqa: E402
import yaml  # noqa: E402


def norm(t):
    t = unicodedata.normalize("NFKD", t or "")
    t = "".join(c for c in t if not unicodedata.combining(c)).lower()
    t = re.sub(r"^\s*((cap[ií]tulo|chapter|secci[oó]n|section)\s+)?([0-9]+(\.[0-9]+)*|[ivxlc]+)[.)]?\s+", "", t)
    return re.sub(r"[^a-z0-9 ]+", " ", t).strip()


def cargar(path):
    meta = {}
    if path.lower().endswith(".docx"):
        pars, _ = auditar.cargar_docx(path)
        for p in pars:
            p["nivel"] = auditar.nivel_estilo(p) or (1 if p.get("es_titulo") else 0)
        titulos = [p["texto"] for p in pars if (p.get("estilo") or "").lower() in ("title", "título", "titulo")]
        if titulos:
            meta["title"] = titulos[0]
    else:
        pars, meta = auditar.cargar_md(path, frontmatter=True)  # el YAML inicial (title, abstract) va aparte
    return [p for p in pars if not p.get("nota_pie")], meta


def bloques(pars, meta):
    """Lista de [encabezado normalizado | None, texto, palabras propias, nivel]."""
    titulo = norm(str(meta.get("title", "")))
    if not titulo:  # título con estilo de encabezado: es el encabezado que se repite (portada y antes del cuerpo)
        encs = [norm(p["texto"]) for p in pars if p.get("es_titulo") and p["texto"].strip()]
        rep = [t for t in encs if encs.count(t) > 1]
        titulo = rep[0] if rep else ""
    out = [[None, "", 0, 0]]
    for p in pars:
        t = p["texto"].strip()
        estilo = (p.get("estilo") or "").lower()
        es_enc = p.get("es_titulo") and not estilo.startswith(("title", "título", "titulo")) and len(t) < 160
        if es_enc and norm(t) != titulo:
            out.append([norm(t), t, 0, p.get("nivel") or 1])
        elif es_enc and titulo and norm(t) == titulo:
            out.append([None, "", 0, 1])  # título repetido antes del cuerpo (APA 2.11): empieza la introducción
        elif not p.get("en_tabla"):
            out[-1][2] += len(t.split())
    if meta.get("abstract"):
        out.insert(0, ["resumen", "Resumen (metadatos)", len(str(meta["abstract"]).split()), 1])
    return out


def palabras_seccion(bl, i):
    """Palabras del encabezado i más las de sus subsecciones (hasta otro encabezado de nivel igual o superior)."""
    n = bl[i][2]
    for b in bl[i + 1:]:
        if b[0] is not None and b[3] <= bl[i][3]:
            break
        n += b[2]
    return n


def coincide(alias, enc):
    """Coincide si el encabezado es el alias, empieza por él o lo contiene como palabras completas
    («Diseño del marco teórico», «Bosquejo del método»)."""
    return any(enc == a or enc.startswith(a + " ") or (len(a) >= 5 and re.search(r"\b" + re.escape(a) + r"\b", enc))
               for a in alias)


def perfil_de(path, perfil=None):
    """Perfil explícito, o el `perfil:` de .editorial.yaml (hacia arriba desde el documento), o apa7."""
    if perfil:
        return perfil
    ruta = auditar.buscar_equipo(path)
    if ruta and ruta.exists():
        try:
            return (yaml.safe_load(ruta.read_text(encoding="utf-8")) or {}).get("perfil") or "apa7"
        except yaml.YAMLError:
            pass
    return "apa7"


def revisar(path, genero, perfil=None):
    auditar.validar_entrada(path)
    ruta_g = ROOT / "estructuras" / f"{genero}.yaml"
    if not ruta_g.is_file():
        print(f"estructura desconocida: {genero}. Válidas: {', '.join(sorted(f.stem for f in (ROOT / 'estructuras').glob('*.yaml')))}",
              file=sys.stderr)
        sys.exit(2)
    est = yaml.safe_load(ruta_g.read_text(encoding="utf-8"))
    pars, meta = cargar(path)
    bl = bloques(pars, meta)
    total = sum(b[2] for b in bl)
    H, filas, pos = [], [], []
    todos_alias = [[norm(a) for a in s.get("alias", [])] + [norm(s["nombre"])] for s in est["secciones"]]
    finales = [norm(a) for a in ("referencias", "references", "bibliografia", "apendices", "anexos", "appendix", "appendices")]
    total -= sum(palabras_seccion(bl, i) for i, b in enumerate(bl) if b[0] and coincide(finales, b[0]))  # % sobre el cuerpo
    libres = [i for i, b in enumerate(bl) if b[0] and b[3] <= 1 and not any(coincide(al, b[0]) for al in todos_alias)]
    for s in est["secciones"]:
        alias = [norm(a) for a in s.get("alias", [])] + [norm(s["nombre"])]
        idx = [i for i, b in enumerate(bl) if b[0] and coincide(alias, b[0])]
        if not idx and s.get("comodin"):  # p. ej. «Desarrollo» de un ensayo: encabezados temáticos
            idx = libres
        presente = bool(idx)
        palabras = sum(palabras_seccion(bl, i) for i in idx)
        enc = bl[idx[0]][1] if idx else None
        sin_enc = [i for i, b in enumerate(bl) if b[0] is None and b[2] >= 60]
        if not presente and "introduccion" in alias and sin_enc:
            i0 = sin_enc[-1] if len(sin_enc) > 1 else sin_enc[0]  # tras el título repetido, si lo hay
            presente, palabras, enc, idx = True, bl[i0][2], "(sin encabezado, APA 2.11)", [i0]
        filas.append({"nombre": s["nombre"], "obligatoria": s.get("obligatoria", False), "presente": presente,
                      "encabezado": enc, "palabras": palabras})
        if s.get("obligatoria") and not presente:
            H.append(auditar.Hallazgo("EST-001", "mayor", "documento", f"falta «{s['nombre']}»",
                                      f"añadir la sección: {s.get('proposito', '')}"))
        if s.get("obligatoria") and presente and not s.get("orden_libre"):
            pos.append((idx[0], s["nombre"]))
        m = re.match(r"(\d+)\s*-\s*(\d+)\s*%", str(s.get("extension", "")))
        if m and presente and total >= 800:
            lo, hi = int(m.group(1)) / 100, int(m.group(2)) / 100
            frac = palabras / total
            if frac < lo / 2 or frac > hi * 2:
                H.append(auditar.Hallazgo("EST-003", "menor", enc or s["nombre"],
                                          f"{s['nombre']}: {frac:.0%} del texto (orientativo {s['extension']})",
                                          "ajustar la extensión de la sección"))
    orden = [n for _, n in sorted(pos)]
    esperado = [n for _, n in pos]
    if orden != esperado:
        H.append(auditar.Hallazgo("EST-002", "menor", "documento", " → ".join(orden),
                                  "orden del género: " + " → ".join(esperado)))
    obl = [f for f in filas if f["obligatoria"]]
    cob = sum(f["presente"] for f in obl) / len(obl) if obl else 1.0
    maq, info = [], None
    if str(path).lower().endswith(".docx"):
        maq, info = maquetacion.revisar_info(path, perfil_de(path, perfil))
        H += maq
    return {"documento": str(path), "estructura": genero, "secciones": filas, "hallazgos": H, "maquetacion": maq,
            "maquetacion_info": info, "cobertura": round(cob, 3), "palabras": total}


def main():
    p = argparse.ArgumentParser(description="Revisa que el documento tenga las secciones que exige su género.")
    p.add_argument("doc", nargs="?")
    p.add_argument("--estructura", help="género (--listar los muestra); por defecto el `estructura:` de .editorial.yaml o «informe»")
    p.add_argument("--perfil", help="perfil de formato (apa7, ieee, …); por defecto .editorial.yaml o apa7")
    p.add_argument("--json", metavar="RUTA", help="escribe el resultado completo como JSON")
    p.add_argument("--listar", action="store_true")
    a = p.parse_args()
    cli.utf8()
    if a.listar or not a.doc:
        for f in sorted((ROOT / "estructuras").glob("*.yaml")):
            print(f.stem, "—", yaml.safe_load(f.read_text(encoding="utf-8"))["nombre"])
        return
    if not a.estructura:
        eq = auditar.buscar_equipo(a.doc)
        cfg = (yaml.safe_load(eq.read_text(encoding="utf-8")) or {}) if eq and eq.exists() else {}
        a.estructura = (cfg.get("estructura") if isinstance(cfg, dict) else None) or "informe"
    r = revisar(a.doc, a.estructura, a.perfil)
    cli.escribir_json(a.json, r, indent=2)
    print(f"ESTRUCTURA: {r['estructura']}   cobertura de obligatorias: {r['cobertura']:.0%}   palabras={r['palabras']}")
    for f in r["secciones"]:
        print(f"  [{'x' if f['presente'] else ' '}] {f['nombre']}{' *' if f['obligatoria'] else ''}"
              f"{'  ← ' + f['encabezado'] if f['encabezado'] else ''}  ({f['palabras']} palabras)")
    maq = {id(h) for h in r["maquetacion"]}
    fila = lambda i, h: print(f"| {i} | {h['id']} | {h['severidad']} | {h['ubicacion']} | {h['evidencia']} | {h['correccion']} |")  # noqa: E731
    for i, h in enumerate([h for h in r["hallazgos"] if id(h) not in maq], 1):
        fila(i, h)
    if a.doc.lower().endswith(".docx"):
        print(f"MAQUETACIÓN: {len(r['maquetacion'])} hallazgos (EST-010..EST-016)")
        print(maquetacion.linea_portada(r["maquetacion_info"]))
        for i, h in enumerate(r["maquetacion"], 1):
            fila(i, h)
    sys.exit(cli.codigo(r["hallazgos"]))


if __name__ == "__main__":
    main()
