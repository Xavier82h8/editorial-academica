#!/usr/bin/env python3
"""Renderiza un documento Markdown con marcas [@id] según un perfil (APA 7 / IEEE / combinado).

Uso:
  python -I render.py doc.md --perfil apa7 --fuentes fuentes.json --salida docx [--out doc.docx] [--json res.json]
  python -I render.py --refs fuentes.json --perfil ieee          # solo imprime la lista de referencias
(`--perfil` por defecto: el de .editorial.yaml.)

Requiere pandoc >= 3 (y xelatex para --salida pdf). Se buscan primero en PATH (shutil.which) en cualquier sistema; las
rutas habituales de Windows/macOS son solo respaldo. El CSL y el idioma salen de perfiles/<perfil>.yaml.
Fuente de la salida LaTeX/PDF: Times New Roman; si fc-list indica que no está, TeX Gyre Termes o Liberation Serif.
Salida: 0 si se generó; 2 en cualquier error (entrada inexistente, perfil desconocido, pandoc/xelatex ausentes, pandoc falla).
"""
import argparse
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import cli  # noqa: E402

FORMATOS = {"docx": "docx", "md": "gfm", "html": "html", "pdf": "pdf", "latex": "latex", "plain": "plain"}


def pista_instalacion(herramienta):
    """Cómo instalar `herramienta` ('pandoc' | 'xelatex') en el sistema operativo actual."""
    if sys.platform == "win32":
        return {"pandoc": "winget install --id JohnMacFarlane.Pandoc",
                "xelatex": "winget install --id MiKTeX.MiKTeX"}[herramienta]
    if sys.platform == "darwin":
        return {"pandoc": "brew install pandoc", "xelatex": "brew install --cask basictex  (o mactex-no-gui)"}[herramienta]
    return {"pandoc": "sudo apt install pandoc  (Fedora: sudo dnf install pandoc; Arch: sudo pacman -S pandoc)",
            "xelatex": "sudo apt install texlive-xetex texlive-latex-extra  (Fedora: sudo dnf install texlive-xetex)"}[herramienta]


def _buscar_exe(nombre, respaldo):
    """Ejecutable en PATH (cualquier sistema operativo); si no, la primera ruta de respaldo que exista; si no, None."""
    exe = shutil.which(nombre)
    if exe:
        return exe
    for c in respaldo:
        if pathlib.Path(c).exists():
            return str(c)
    return None


def pandoc():
    exe = _buscar_exe("pandoc", (pathlib.Path.home() / "AppData/Local/Pandoc/pandoc.exe",
                                 "C:/Program Files/Pandoc/pandoc.exe",
                                 "/opt/homebrew/bin/pandoc", "/usr/local/bin/pandoc"))
    if not exe:
        cli.error(f"pandoc no encontrado en PATH. Instala: {pista_instalacion('pandoc')}")
    return exe


def perfil(pid):
    p = ROOT / "perfiles" / f"{pid}.yaml"
    if not p.exists():
        validos = ", ".join(sorted(f.stem for f in (ROOT / "perfiles").glob("*.yaml") if ".editorial" not in f.stem))
        sys.stderr.reconfigure(encoding="utf-8")
        print(f"perfil desconocido: {pid}. Perfiles válidos: {validos}", file=sys.stderr)
        sys.exit(2)
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def lang(cfg):
    return {"es": "es-MX", "en": "en-US"}.get((cfg.get("opciones") or {}).get("idioma", "es"), "es-MX")


def args_comunes(cfg, fuentes, idioma=None):
    a = ["--citeproc", "--bibliography", str(fuentes), "--csl", str(ROOT / cfg["csl"]),
         "-M", f"lang={idioma or lang(cfg)}", "-M", "link-citations=false"]
    # los términos en español salen del bloque <locale xml:lang="es"> de cada CSL (pandoc no acepta un archivo de locale)
    if cfg.get("citas") == "apa7":  # narrativa "and"/"y" (después de --citeproc)
        a += ["--lua-filter", str(ROOT / "plantillas/filtros/narrativa-apa.lua")]
    return a


def limpiar_fuentes(path):
    """Quita claves internas (_verificacion) que citeproc no entiende."""
    items = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    nombres = {"author", "editor", "translator", "director", "container-author", "collection-editor",
               "composer", "interviewer", "recipient", "reviewed-author", "chair", "compiler", "contributor",
               "curator", "editorial-director", "executive-producer", "guest", "host", "illustrator",
               "narrator", "organizer", "original-author", "performer", "producer", "script-writer",
               "series-creator"}
    fechas = {"issued", "accessed", "original-date", "event-date", "submitted", "available-date"}
    for it in items:
        it.pop("_verificacion", None)
        if it.get("number") and str(it.get("page", "")) == str(it["number"]):
            it.pop("page")  # Crossref repite el número de artículo (eLocator) como página
        for k, v in list(it.items()):
            if isinstance(v, list) and k not in nombres:
                it[k] = ", ".join(map(str, v))      # p. ej. ISSN/ISBN de Crossref
            if k in fechas and isinstance(v, dict):
                it[k] = {kk: vv for kk, vv in v.items() if kk in ("date-parts", "season", "circa", "literal", "raw")}
    tmp = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
    json.dump(items, tmp, ensure_ascii=False)
    tmp.close()
    return tmp.name


def entorno_tex():
    """Entorno con xelatex en PATH. Si no está en PATH, se prueban MiKTeX (Windows) y TeX Live/MacTeX (macOS) como respaldo.
    Si no se encuentra en ninguna parte, termina con código 2 y la pista de instalación del sistema."""
    env = dict(os.environ)
    if not shutil.which("xelatex"):
        for c in (pathlib.Path.home() / "AppData/Local/Programs/MiKTeX/miktex/bin/x64",
                  pathlib.Path("C:/Program Files/MiKTeX/miktex/bin/x64"),
                  pathlib.Path("/Library/TeX/texbin"), pathlib.Path("/usr/local/texlive/bin")):
            if (c / "xelatex.exe").exists() or (c / "xelatex").exists():
                env["PATH"] = str(c) + os.pathsep + env.get("PATH", "")
                break
        else:
            cli.error(f"xelatex no encontrado en PATH (hace falta para --salida pdf). Instala: {pista_instalacion('xelatex')}")
    return env


FUENTES_TIPOGRAFICAS = ("Times New Roman", "TeX Gyre Termes", "Liberation Serif")


def fuente_principal():
    """(familia, aviso) para `mainfont` de xelatex: Times New Roman; si fc-list indica que no está, TeX Gyre Termes o
    Liberation Serif (equivalentes métricos); si no hay ninguna, se deja Times New Roman y se avisa. Sin fc-list
    (Windows y macOS, que traen Times New Roman) no se puede comprobar: se asume Times New Roman."""
    fc = shutil.which("fc-list")
    if not fc:
        if sys.platform in ("win32", "darwin"):
            return FUENTES_TIPOGRAFICAS[0], None
        return FUENTES_TIPOGRAFICAS[0], ("no se pudo comprobar la fuente (falta fc-list); si xelatex no encuentra "
                                         "«Times New Roman», instala fonts-liberation o fonts-texgyre")
    try:
        r = subprocess.run([fc, ":", "family"], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
    except (OSError, subprocess.SubprocessError):
        return FUENTES_TIPOGRAFICAS[0], None
    familias = {f.strip().lower() for linea in r.stdout.splitlines() for f in linea.split(",")}
    for n in FUENTES_TIPOGRAFICAS:
        if n.lower() in familias:
            return n, (None if n == FUENTES_TIPOGRAFICAS[0] else f"«Times New Roman» no está instalada: se usa «{n}» (equivalente métrico)")
    return FUENTES_TIPOGRAFICAS[0], ("no hay «Times New Roman», «TeX Gyre Termes» ni «Liberation Serif»: se deja Times New Roman "
                                     "y xelatex puede fallar. Instala: sudo apt install fonts-liberation (o fonts-texgyre)")


def args_latex(cfg, idioma=None):
    """Plantilla pandoc segun la base del perfil (apa7 | ieee): plantillas/latex/<base>.latex."""
    base = cfg["base"]
    op = cfg.get("opciones") or {}
    fuente, aviso = fuente_principal()
    if aviso:
        print("aviso: " + aviso, file=sys.stderr)
    a = ["--template", str(ROOT / "plantillas/latex" / f"{base}.latex"),
         "--lua-filter", str(ROOT / "plantillas/filtros/latex-base.lua"),
         "-M", f"perfil-base={base}", "-V", "indent=true", "-V", f"mainfont={fuente}",
         "-V", "csquotes=true"]
    if base == "apa7":
        if op.get("tipo_trabajo") == "profesional":
            a += ["-V", "profesional=true"]
    else:  # ieee: dos columnas (conference) salvo columnas: 1 (informe/tesis)
        if str(op.get("columnas", 2)) == "1":
            a += ["-V", "classoption=journal", "-V", "classoption=onecolumn", "-V", "ieee-onecolumn=true"]
        else:
            a += ["-V", "classoption=conference"]
    return a


def render_doc(a):
    """Renderiza `a.doc`; devuelve la ruta de salida."""
    cfg = perfil(a.perfil)
    if not pathlib.Path(a.fuentes).is_file():
        cli.error(f"no existe el archivo de fuentes: {a.fuentes} (usa --fuentes)")
    fu = limpiar_fuentes(a.fuentes)
    try:
        return _render_doc(a, cfg, fu)
    finally:
        pathlib.Path(fu).unlink(missing_ok=True)


def _render_doc(a, cfg, fu):
    ent = pathlib.Path(a.doc)
    if not ent.is_file():
        print(f"no existe el archivo: {a.doc}", file=sys.stderr)
        sys.exit(2)
    ext = "md" if a.salida == "md" else a.salida
    if a.out:
        out = a.out
    else:
        out = str(ent.with_suffix("." + ext))
        if pathlib.Path(out).resolve() == ent.resolve():
            out = str(ent.with_suffix(".salida." + ext))
    if pathlib.Path(out).resolve() == ent.resolve():
        print(f"la salida ({out}) coincide con la entrada: no se sobrescribe. Usa otra --out.", file=sys.stderr)
        sys.exit(2)
    cmd = [pandoc(), a.doc, *args_comunes(cfg, fu, a.idioma), "-o", out]
    if a.salida != "pdf":
        cmd[2:2] = ["-t", FORMATOS[a.salida]]
    if a.salida == "docx":
        import crear_plantillas  # import tardío: crear_plantillas importa render
        ref_doc = crear_plantillas.asegurar_plantillas() / f"{a.perfil}.docx"
        if ref_doc.exists():
            cmd += ["--reference-doc", str(ref_doc)]
    env = None
    if a.salida in ("pdf", "latex"):
        cmd += args_latex(cfg, a.idioma)
    if a.salida == "pdf":
        env = entorno_tex()  # solo el PDF necesita xelatex; .tex no
        cmd += ["--pdf-engine=xelatex"]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", env=env)
    if r.returncode:
        cli.error(r.stderr)
    if a.salida == "docx":
        postproceso_docx(out, cfg, metadatos(a.doc))
    print(out)
    return out


def metadatos(doc):
    """Bloque YAML inicial del Markdown (dict; vacío si no hay)."""
    try:
        t = pathlib.Path(doc).read_text(encoding="utf-8-sig")
    except OSError:
        return {}
    if not t.startswith("---"):
        return {}
    fin = t.find("\n---", 3)
    if fin < 0:
        return {}
    try:
        m = yaml.safe_load(t[3:fin])
    except yaml.YAMLError:
        return {}
    return m if isinstance(m, dict) else {}


def _lista(v):
    if v is None:
        return []
    return [str(x.get("name", "") if isinstance(x, dict) else x) for x in (v if isinstance(v, list) else [v])]


def portada_apa(d, meta, es, profesional=True):
    """Portada APA 7 (§ 2.3), resumen y título repetido antes del cuerpo (§ 2.11).
    Profesional: título, autores, filiaciones, nota del autor y running head en mayúsculas (≤ 50 caracteres).
    Estudiante: título, autores, afiliación, curso, instructor y fecha de entrega (APA-022); sin running head."""
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Inches
    titulo = str(meta.get("title", "")).strip()
    if not titulo:
        return
    frente = {"Title", "Subtitle", "Author", "Date", "Abstract Title", "Abstract"}
    for p in list(d.paragraphs):
        if p.style.name not in frente:
            break
        p._p.getparent().remove(p._p)
    primero = d.paragraphs[0]._p if d.paragraphs else None

    def nuevo(texto, estilo="Normal", centrado=False, negrita=None, sangria=False, salto=False):
        p = d.add_paragraph(style=estilo)
        if texto:
            p.add_run(texto).bold = negrita
        if centrado:
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.first_line_indent = Inches(0.5 if sangria else 0)
        if salto:
            p.paragraph_format.page_break_before = True
        if primero is not None:
            primero.addprevious(p._p)
        return p

    autores = _lista(meta.get("author"))
    conj = " y " if es else " and "
    linea = autores[0] if len(autores) == 1 else (", ".join(autores[:-1]) + conj + autores[-1] if autores else "")
    for _ in range(3):
        nuevo("")
    nuevo(titulo, "Title", True, True)
    if meta.get("subtitle"):
        nuevo(str(meta["subtitle"]), "Title", True, True)
    nuevo("")
    if linea:
        nuevo(linea, centrado=True)
    for k in ("affiliation", "institute"):
        for af in _lista(meta.get(k)):
            nuevo(af, centrado=True)
    if not profesional:
        for k in ("course", "instructor"):
            for v in _lista(meta.get(k)):
                nuevo(v, centrado=True)
    if meta.get("date"):
        nuevo(str(meta["date"]), centrado=True)
    nota = "" if not profesional else str(meta.get("author-note", "")).strip()
    if nota:
        nuevo("")
        nuevo(str(meta.get("author-note-title") or ("Nota del autor" if es else "Author Note")), "Heading 1")
        for par in [x.strip() for x in nota.split("\n\n") if x.strip()]:
            nuevo(" ".join(par.split()), sangria=True)
    resumen = str(meta.get("abstract", "")).strip()
    if resumen:
        nuevo("Resumen" if es else "Abstract", "Heading 1", salto=True)
        nuevo(" ".join(resumen.split()))
        kw = _lista(meta.get("keywords"))
        if kw:
            p = nuevo("", sangria=True)
            p.add_run(("Palabras clave" if es else "Keywords") + ": ").italic = True
            p.add_run(", ".join(kw))
    nuevo(titulo, "Heading 1", salto=True)
    if not profesional:
        return
    rh = str(meta.get("running-head") or titulo).upper()[:50].rstrip()  # el primer run del encabezado es el marcador
    for s in d.sections:
        runs = s.header.paragraphs[0].runs
        if runs:
            runs[0].text = rh


def postproceso_docx(path, cfg, meta=None):
    """Ajustes que pandoc no hace: lista de referencias en página nueva cuando la base es APA;
    portada, resumen y running head del trabajo profesional (apa7-profesional)."""
    import docx
    d = docx.Document(path)
    for p in d.paragraphs:
        if p.text.strip().lower() in {"references", "referencias"} and cfg["base"] == "apa7":
            p.paragraph_format.page_break_before = True
    op = cfg.get("opciones") or {}
    if cfg["base"] == "apa7" and meta:
        lg = str(meta.get("lang") or lang(cfg))
        portada_apa(d, meta, lg.lower().startswith("es"), op.get("tipo_trabajo") == "profesional")
    d.save(path)


def render_refs(fuentes, pid, idioma=None, fmt="plain", ids=None):
    """Devuelve la bibliografía renderizada (lista de entradas) para un perfil."""
    cfg = perfil(pid)
    fu = limpiar_fuentes(fuentes)
    try:
        ids = ids or [i["id"] for i in json.loads(pathlib.Path(fu).read_text(encoding="utf-8"))]
        md = "---\nnocite: |\n  " + ", ".join("@" + i for i in ids) + "\n---\n"
        r = subprocess.run([pandoc(), "-f", "markdown", "-t", fmt, "--wrap=none", *args_comunes(cfg, fu, idioma)],
                           input=md, capture_output=True, text=True, encoding="utf-8")
    finally:
        pathlib.Path(fu).unlink(missing_ok=True)
    if r.returncode:
        raise RuntimeError(r.stderr)
    return r.stdout


def main():
    p = argparse.ArgumentParser(description="Renderiza Markdown con marcas [@id] a docx/pdf/latex/html/md según un perfil.")
    p.add_argument("doc", nargs="?")
    p.add_argument("--perfil", help="id de perfil; por defecto el `perfil:` de .editorial.yaml")
    p.add_argument("--fuentes", default="fuentes.json")
    p.add_argument("--salida", choices=list(FORMATOS), default="docx")
    p.add_argument("--out")
    p.add_argument("--idioma", help="es-MX | en-US (por defecto, el del perfil)")
    p.add_argument("--refs", help="solo renderiza la lista de referencias de este CSL-JSON")
    p.add_argument("--json", metavar="RUTA", help="escribe {salida, perfil, formato} como JSON")
    a = p.parse_args()
    cli.utf8()
    a.perfil = cli.perfil_por_defecto(p, a.perfil, a.doc or a.refs)
    if a.refs:
        try:
            print(render_refs(a.refs, a.perfil, a.idioma))
        except RuntimeError as e:
            cli.error(str(e))
    elif a.doc:
        out = render_doc(a)
        cli.escribir_json(a.json, {"salida": str(out), "perfil": a.perfil, "formato": a.salida})
    else:
        p.error("falta doc o --refs")


if __name__ == "__main__":
    main()
