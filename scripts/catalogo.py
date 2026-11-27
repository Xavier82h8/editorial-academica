#!/usr/bin/env python3
"""Genera docs/REGLAS.md: catálogo de todas las reglas del plugin, por familia, con severidad, si se evalúa de forma
determinista o por el agente, si `corregir.py` la corrige, y su fuente.

Uso:
  python scripts/catalogo.py              escribe docs/REGLAS.md
  python scripts/catalogo.py --comprobar  sale 1 si docs/REGLAS.md está desactualizado (puerta de tests/run_portabilidad.py)
  python scripts/catalogo.py --stdout     imprime el catálogo sin escribirlo

Fuentes de datos (no se escribe ninguna regla a mano salvo FUE-*, RED-* y EA-001, que no tienen tabla propia):
  APA-xxx / IEEE-xxx  skills/apa7|ieee/references/checklist.md (columnas ID, regla, severidad, fix, fuente)
  CON-001..020        docstring de scripts/congruencia.py (deterministas) y agents/revisor-congruencia.md (agente)
  EST-001..004        docstring de scripts/estructura.py;  EST-010..017: docstring de scripts/maquetacion.py
  INS-001..015        docstring de scripts/institucional.py (formato institucional del bloque `formato:` y modelos del bloque `vinculante:` de .editorial.yaml)
Clasificación «Evaluación»: `determinista` si el ID aparece en algún script (el juez lo emite); `agente` si solo está en el
checklist o en las instrucciones de un agente; `+ corregible` si está en `corregir.REGLAS`.
Salida: 0 correcto (o catálogo al día); 1 con --comprobar si está desactualizado; 2 error de uso.
"""
import argparse
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
HERE = ROOT / "scripts"
SALIDA = ROOT / "docs" / "REGLAS.md"
sys.path.insert(0, str(HERE))
import cli  # noqa: E402

PLUGIN = "Práctica editorial del plugin"
# Fuente oficial de reglas propias del plugin (sin tabla de fuente en el código)
FUENTE_EXTRA = {
    "EST-001": "estructuras/<género>.yaml (" + PLUGIN + ")", "EST-002": "estructuras/<género>.yaml (" + PLUGIN + ")",
    "EST-003": "estructuras/<género>.yaml (" + PLUGIN + ")", "EST-004": "estructuras/<género>.yaml (" + PLUGIN + ")",
    "EST-010": "APA § 2.18 (IEEE no define la numeración)", "EST-011": "APA § 2.18",
    "EST-012": PLUGIN + " (APA cap. 7, tablas y figuras)", "EST-013": PLUGIN + " (APA cap. 7)",
    "EST-014": PLUGIN + " (APA 2.21)", "EST-015": "APA cap. 7 (notas de tablas y figuras)",
    "EST-016": "APA § 2.18 (IEEE no define la portada)", "EST-017": PLUGIN + " (índices de Word: el resultado mostrado debe coincidir con los encabezados)",
    "EA-001": PLUGIN,
}
# FUE-*, RED-* y EA-001 se emiten en puntuar.py/auditar.py sin tabla propia: id -> (severidad, descripción, fuente)
OTRAS = {
    "EA-001": ("crítica", "Marcador del redactor (`[[FALTA FUENTE: …]]`, `[[TODO]]`, `[[PENDIENTE]]`) que llega a la entrega",
               PLUGIN + " (scripts/auditar.py)"),
    "FUE-000": ("crítica", "El documento no tiene referencias verificables (dimensión «Fuentes» a cero)", PLUGIN + " (scripts/puntuar.py)"),
    "FUE-V123": ("crítica", "Fuente con DOI inexistente, metadatos que no coinciden o retractada (V1-V3)", PLUGIN + " (V1-V3)"),
    "FUE-URL": ("mayor", "Fuente sin DOI cuya URL no responde (V1)", PLUGIN + " (V1)"),
    "FUE-V5": ("mayor", "Afirmación citada que la fuente no respalda o contradice según su resumen (V5)", PLUGIN + " (V5)"),
    "FUE-V3N": ("menor", "Fuentes con DOI que no se pudieron comprobar por fallo de red (no verificado, nunca «ok»)", PLUGIN + " (V1/V3)"),
    "FUE-V4N": ("menor", "Afirmación sustantiva (cifra, resultado, eficacia) sostenida solo por fuentes de nivel D o E (documentación, web, blog, preprint) (V4)",
                PLUGIN + " (scripts/niveles.py)"),
    "FUE-NIV": ("mayor", "Bloque `fuentes:` del perfil incumplido: fuente de un tipo a evitar (wikipedia, blog, foro…) o porcentaje de fuentes arbitradas bajo el pedido (mayor); referencias bajo `minimo_nivel` (menor)",
                PLUGIN + " (scripts/niveles.py)"),
    "FUE-V4": ("menor", "Referencias sin enlace comprobable (ni DOI ni URL que responda) (V4)", PLUGIN + " (V4)"),
    "RED-001": ("menor", "Oración de más de 40 palabras en la dimensión «Redacción»", PLUGIN + " (scripts/puntuar.py)"),
}
FAMILIAS = [  # (prefijo, título, nota)
    ("APA", "APA 7: formato, citas y referencias", "Norma: Publication Manual 7.ª ed. (snapshot en `normas/VERSION`)."),
    ("IEEE", "IEEE: citas, referencias, estructura, figuras, matemáticas", "Norma: IEEE Reference Guide 2025 y Editorial Style Manual (`normas/VERSION`)."),
    ("CON", "CON: congruencia interna", "Sin norma oficial: práctica editorial. Las deterministas las emite `congruencia.py`; las demás, el agente `revisor-congruencia`."),
    ("EST", "EST: estructura por género y maquetación", "EST-001..004: `estructura.py` con `estructuras/<género>.yaml`; EST-010..017: `maquetacion.py` (.docx)."),
    ("INS", "INS: reglas institucionales (bloques `formato:` y `vinculante:` de .editorial.yaml)", "Solo se evalúan con `formato:` o `vinculante:` en el perfil de equipo; las emite `institucional.py` desde `auditar.py`. Ver `docs/PERFILES-INSTITUCIONALES.md`."),
    ("EA", "EA: entrega", "Reglas de la entrega."),
    ("FUE", "FUE: verificación de fuentes (dimensión «Fuentes» de `/puntuar`)", "V1 existencia, V2 metadatos, V3 integridad, V4 calidad, V5 sustento."),
    ("RED", "RED: redacción (dimensión «Redacción» de `/puntuar`)", "Heurísticas de claridad."),
]


def limpia(t):
    return re.sub(r"(?<!\\)\|", r"\\|", re.sub(r"\s+", " ", t).strip())


def ids_en_scripts():
    """IDs APA/IEEE que algún script emite o corrige (el juez determinista los cubre)."""
    ids = set()
    for f in HERE.glob("*.py"):
        if f.name in ("catalogo.py", "corregir.py"):
            continue
        ids |= set(re.findall(r"\b(?:APA|IEEE)-\d{3}\b", f.read_text(encoding="utf-8")))
    return ids


def checklist(prefijo, ruta):
    """Filas `| ID | regla | sev | fix | fuente |` de un checklist, con su grupo (encabezado `## `)."""
    filas, grupo = [], ""
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        if linea.startswith("## "):
            grupo = re.sub(r"\s*[\[(].*$", "", linea[3:]).strip().rstrip(":.")
            continue
        m = re.match(r"\|\s*(%s-\d{3})\s*\|(.*)\|\s*$" % prefijo, linea)
        if not m:
            continue
        celdas = re.split(r"(?<!\\)\|", m.group(2))
        if len(celdas) < 4:
            continue
        regla, sev, fix, *fuente = [c.strip() for c in celdas]
        filas.append({"id": m.group(1), "sev": sev.lower(), "desc": limpia(regla), "fuente": limpia(" | ".join(fuente)),
                      "grupo": grupo, "fix_checklist": fix.lower().startswith("s")})
    return filas


def docstring(ruta):
    t = ruta.read_text(encoding="utf-8")
    m = re.search(r'"""(.*?)"""', t, re.S)
    return m.group(1) if m else ""


def reglas_docstring(ruta, prefijo, sangria_cont=6):
    """Líneas `  [- ]XXX-nnn severidad[:] texto` de un docstring, con sus líneas de continuación (más sangradas)."""
    reglas, actual = {}, None
    for linea in docstring(ruta).splitlines():
        m = re.match(r"\s*(?:-\s+)?(%s-\d{3})\s+(crítica|mayor|menor)\s*:?\s*(.*)$" % prefijo, linea)
        if m:
            actual = m.group(1)
            reglas[actual] = {"id": actual, "sev": m.group(2), "desc": m.group(3)}
        elif actual and re.match(r"\s{%d,}\S" % sangria_cont, linea) and not re.match(r"\s*(?:-\s+)?[A-Z]+-\d{3}\s", linea):
            reglas[actual]["desc"] += " " + linea.strip()
        else:
            actual = None
    for r in reglas.values():
        r["desc"] = limpia(r["desc"])
    return reglas


def reglas_agente():
    """CON-010..017 (y cualesquiera otras) de las instrucciones del agente `revisor-congruencia`."""
    t = (ROOT / "agents" / "revisor-congruencia.md").read_text(encoding="utf-8")
    out = {}
    for m in re.finditer(r"(CON-\d{3}) (crítica|mayor|menor):\s*([^;\n]*)", t):
        out.setdefault(m.group(1), {"id": m.group(1), "sev": m.group(2), "desc": limpia(m.group(3)).rstrip(".")})
    return out


def recortar(texto, n=230):
    if len(texto) <= n:
        return texto
    return texto[:n].rsplit(" ", 1)[0] + "…"


def recolectar():
    import corregir
    corregibles = set(corregir.REGLAS)
    en_scripts = ids_en_scripts()
    reglas = []
    for pref, carpeta in (("APA", "apa7"), ("IEEE", "ieee")):
        for r in checklist(pref, ROOT / "skills" / carpeta / "references" / "checklist.md"):
            r["auto"] = r["id"] in en_scripts or r["id"] in corregibles
            r["fuente"] = r["fuente"]
            reglas.append(r)
    con = reglas_docstring(HERE / "congruencia.py", "CON", 2)
    for r in con.values():
        r.update(auto=True, fuente=(re.search(r"(APA \d+(?:\.\d+)*)", r["desc"]) or [None, PLUGIN])[1] if "APA" in r["desc"] else PLUGIN,
                 grupo="Congruencia")
    for i, r in reglas_agente().items():
        if i not in con:
            r.update(auto=False, fuente=PLUGIN, grupo="Congruencia")
            con[i] = r
    reglas += con.values()
    est = reglas_docstring(HERE / "estructura.py", "EST", 8)
    est.update(reglas_docstring(HERE / "maquetacion.py", "EST", 10))
    for r in est.values():
        r.update(auto=True, fuente=FUENTE_EXTRA.get(r["id"], PLUGIN), grupo="Estructura" if int(r["id"][4:]) < 10 else "Maquetación")
        reglas.append(r)
    for r in reglas_docstring(HERE / "institucional.py", "INS", 10).values():
        r.update(auto=True, fuente="Guía institucional declarada en `formato:` del perfil de equipo (" + PLUGIN + ")", grupo="Institucional")
        if r["id"] == "INS-015":
            r["fuente"] = "Modelo vinculante del usuario, declarado en `vinculante:` del perfil de equipo (" + PLUGIN + ")"
        reglas.append(r)
    for i, (sev, desc, fuente) in OTRAS.items():
        reglas.append({"id": i, "sev": sev, "desc": desc, "fuente": fuente, "auto": True, "grupo": "Entrega"})
    reglas.sort(key=lambda r: (r["id"].split("-")[0], r["id"]))
    for r in reglas:
        r["corregible"] = r["id"] in corregibles
        d = r["desc"].rstrip(".")
        r["desc"] = recortar(d[:1].upper() + d[1:])
        r["eval"] = ("determinista" if r["auto"] else "agente") + (" + corregible" if r["corregible"] else "")
    return reglas


def render():
    reglas = recolectar()
    por = {p: [r for r in reglas if r["id"].startswith(p + "-")] for p, _, _ in FAMILIAS}
    n_det = sum(1 for r in reglas if r["auto"])
    n_cor = sum(1 for r in reglas if r["corregible"])
    L = ["# Catálogo de reglas", "",
         "<!-- Generado por scripts/catalogo.py; no editar a mano (python scripts/catalogo.py). -->", "",
         f"**{len(reglas)} reglas**: {n_det} con comprobación determinista (las emite un script), "
         f"{len(reglas) - n_det} que evalúa el agente (juicio), {n_cor} que `corregir.py` corrige de forma automática.", "",
         "| Familia | Reglas | Deterministas | De agente | Corregibles |", "|---|---:|---:|---:|---:|"]
    for p, titulo, _ in FAMILIAS:
        rs = por[p]
        L.append(f"| {p} | {len(rs)} | {sum(1 for r in rs if r['auto'])} | {sum(1 for r in rs if not r['auto'])} | "
                 f"{sum(1 for r in rs if r['corregible'])} |")
    L += ["", "Columna **Evaluación**: `determinista` = el juez (script) emite el ID; `agente` = lo evalúa un agente con el checklist "
          "(se marca como juicio); `+ corregible` = `corregir.py` lo corrige (`corregir.REGLAS`). Una regla del checklist con "
          "«Fix: sí» pero sin script sigue siendo del agente.", ""]
    for p, titulo, nota in FAMILIAS:
        rs = por[p]
        if not rs:
            continue
        L += [f"## {titulo}", "", nota, "", "| ID | Severidad | Evaluación | Descripción | Fuente oficial |", "|---|---|---|---|---|"]
        for r in rs:
            L.append(f"| {r['id']} | {r['sev']} | {r['eval']} | {r['desc']} | {r['fuente']} |")
        L.append("")
    return "\n".join(L).rstrip("\n") + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description="Genera docs/REGLAS.md a partir de los checklists y docstrings.")
    ap.add_argument("--comprobar", action="store_true", help="sale 1 si docs/REGLAS.md no coincide con lo generado")
    ap.add_argument("--stdout", action="store_true", help="imprime el catálogo sin escribirlo")
    a = ap.parse_args(argv)
    cli.utf8()
    texto = render()
    if a.stdout:
        print(texto, end="")
        return 0
    if a.comprobar:
        actual = SALIDA.read_text(encoding="utf-8").replace("\r\n", "\n") if SALIDA.exists() else ""
        if actual != texto:
            print("docs/REGLAS.md está desactualizado: python scripts/catalogo.py", file=sys.stderr)
            return 1
        print("docs/REGLAS.md al día")
        return 0
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    SALIDA.write_text(texto, encoding="utf-8", newline="\n")
    print(f"escrito {SALIDA.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
