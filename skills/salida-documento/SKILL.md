---
name: salida-documento
description: Use when producing the final file of an academic document written with the editorial-academica pipeline — Word .docx, Markdown, PDF or LaTeX — with APA 7, IEEE or combined profile layout and CSL-rendered references.
---

# Salida del documento

Entrada: Markdown con marcas `[@id]`, `fuentes.json` (CSL-JSON) y el perfil. **Las referencias siempre se generan con el CSL del perfil, nunca a mano.**

## Requisitos (verificar al inicio)
```bash
pandoc --version            # >= 3.x; si falta: winget install --id JohnMacFarlane.Pandoc (mac: brew install pandoc; Linux: apt install pandoc)
python -c "import docx"     # python-docx, para retoques de estilos
xelatex --version           # solo para PDF/LaTeX; si falta: winget install MiKTeX.MiKTeX (mac: brew install --cask mactex-no-gui; Linux: apt install texlive-xetex)
```
Si falta algo, díselo al usuario con el comando de instalación y no continúes ese formato.

Rutas (`<raíz>` es la carpeta del plugin (raíz: `${CLAUDE_PLUGIN_ROOT}` en Claude Code; `EDITORIAL_ROOT` o la ruta que dejó el instalador en otras CLI)): `<raíz>/plantillas/csl/{apa,ieee}.csl`, las plantillas Word `<perfil>.docx` (no se distribuyen: `python <raíz>/scripts/crear_plantillas.py` las genera con tu pandoc en la caché del usuario e imprime la carpeta; `render` lo hace solo), `<raíz>/plantillas/latex/`. Los scripts se llaman con `python <raíz>/scripts/editorial.py <subcomando>` (en mac/Linux, `python3` si hace falta).

## Camino por defecto: `render.py`
Úsalo siempre que exista; aplica CSL, idioma, plantilla y postproceso del perfil:
```bash
python <raíz>/scripts/editorial.py render doc.md --perfil <id> --fuentes fuentes.json --salida docx|pdf|latex|md [--out ruta]
```
- Base APA: genera la portada desde el YAML del Markdown. Estudiante: `title`, `author`, `affiliation`, `course`, `instructor`, `date`. Profesional (`apa7-profesional`): además `author-note`, `abstract`, `keywords`, `running-head`. Repite el título antes del cuerpo y pone «Referencias» en página nueva.
- La introducción no lleva encabezado (APA 2.11).
- Lo de abajo es la referencia manual si `render.py` falla.

## .docx (manual)
```bash
pandoc doc.md --citeproc --bibliography fuentes.json --csl "<raíz>/plantillas/csl/<csl>.csl" \
  -M lang=es-MX --reference-doc "<carpeta que imprime crear_plantillas.py>/<perfil>.docx" -o doc.docx
```
Después, la skill `document-skills:docx` aplica lo que pandoc no resuelve:
- portada según la base (APA estudiante/profesional, o IEEE);
- encabezado de página y numeración;
- en APA, salto de página antes de Referencias y sangría francesa de 0.5 in;
- en IEEE, columna `[n]`;
- títulos de tablas y figuras en la posición que pide la base.

## Markdown / PDF
- Markdown: `pandoc doc.md --citeproc ... -t gfm -o doc.final.md`.
- PDF: `pandoc doc.md --citeproc ... --pdf-engine=xelatex -V geometry:margin=1in -V mainfont="Times New Roman" -o doc.pdf`. Si no hay LaTeX, genera el .docx y conviértelo con la skill pdf o con LibreOffice (`soffice --headless --convert-to pdf`).

## LaTeX
- Base IEEE: `\documentclass[journal,onecolumn]{IEEEtran}` (para tesis o informe usa onecolumn), con `\bibliographystyle{IEEEtran}`.
- Base APA: `\documentclass[stu|man,12pt]{apa7}`, con `biblatex` y `style=apa`.
- Combinados: la clase de la base y el estilo bibliográfico de la norma de citas (`biblatex style=ieee` o `style=apa`).
- La bibliografía sale de `fuentes.json` con `pandoc fuentes.json -t biblatex -o refs.bib` (pandoc lee CSL-JSON).
- Compila con `latexmk -xelatex`.

## Cierre
Pasa siempre el archivo final por `juez-formato`: la conversión puede romper estilos.
