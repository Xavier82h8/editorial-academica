# Recursos para APA 7 e IEEE (catálogo)

Fecha de investigación: 2026-11-18. Proyecto: plugin editorial-academica.

Leyenda de autoridad:
- **1** = oficial (editor de la norma o organismo que la publica).
- **2** = institucional o académico reconocido (universidades, bibliotecas, infraestructura académica).
- **3** = secundario útil, con cautela.
- **4** = no fiable / evitar como referencia.

Leyenda de uso en el plugin: **juez** (reglas de evaluación), **corpus** (documentos de prueba con verdad de referencia), **plantilla**, **ES** (adaptación al español).

"Verificado" = se comprobó la URL con curl o WebFetch en esta fecha. "Sin verificar" = la URL viene de un buscador o de otro documento y no se abrió.

---

## 1. Muestras descargadas (ver `normas/muestras/`)

Todas tienen SHA-256 en `normas/muestras/SHA256SUMS`. Todas se comprobaron con `file`/cabecera y con `pdfinfo` o `unzip -l`. No se ejecutó ni extrajo nada.

| Archivo | URL exacta | Tamaño | SHA-256 | Tipo verificado |
|---|---|---|---|---|
| `normas/muestras/apa/student-paper-setup-guide.pdf` | https://apastyle.apa.org/instructional-aids/student-paper-setup-guide.pdf | 1 257 933 B | ad3e85d0586eeedb98ecc54d2d3be415c5f6e5049d97c0f6367313b2ffd0ae88 | PDF 1.7, 19 págs., "Student Paper Setup Guide", 7th Edition |
| `normas/muestras/apa/reference-examples.pdf` | https://apastyle.apa.org/instructional-aids/reference-examples.pdf | 108 429 B | 792e965a6945e673fb4e7a0527fd64b7631f4e8deb4922cdc1531e76edcef9cf | PDF 1.7, 4 págs., "APA Style Common Reference Examples" |
| `normas/muestras/apa/in-text-citation-checklist.pdf` | https://apastyle.apa.org/instructional-aids/in-text-citation-checklist.pdf | 227 653 B | d91458aa319d51c83d8b915bd089e821a72f64c77af4a1be883a1f4626e23dfc | PDF 1.7, 2 págs., "In-Text Citation Checklist, APA Style 7th Edition" |
| `normas/muestras/ieee/IEEEtran.zip` | https://mirrors.ctan.org/macros/latex/contrib/IEEEtran.zip | 1 727 001 B | e0cd4f5afbd42c8076092280e72b3e0a5111efe501d35de9f715cfb8da313cb4 | ZIP válido, 41 entradas (clase IEEEtran, `bare_conf.tex`, `bare_jrnl.tex`, `IEEEtran_HOWTO.pdf`). Fecha de los ficheros: 2015. |

Notas sobre las muestras:
- `IEEEtran.zip` es el paquete del CTAN. Es la clase LaTeX de IEEE más usada. **Sin verificar** que IEEE la distribuya como oficial; la página del CTAN la mantiene como paquete de autor. Sirve para plantilla LaTeX, no como corpus de artículos completos.
- No hay ningún artículo de ejemplo oficial de IEEE descargado (ver sección 5).

## 2. Documentos de descarga manual (anti-bots)

### 2.1 APA sample papers (DOCX y PDF anotados): descargados
- **Estado (19-nov):** los documentos de muestra (PDF y DOCX de estudiante y profesionales de APA, más las plantillas Word de IEEE; 17 DOCX en total) **sí se descargaron** a mano desde el navegador y viven en `normas/muestras/apa/estudiante/`, `normas/muestras/apa/profesional/` y `normas/muestras/ieee/`, con su SHA-256 en `normas/muestras/SHA256SUMS`. Son la verdad de referencia de la puerta «Juez: muestras oficiales».
- **Por qué no hay URL de archivo:** `apastyle.apa.org/style-grammar-guidelines/paper-format/sample-papers` devuelve un desafío anti-bot (Incapsula) a curl y a scripts, así que `scripts/obtener_normas.py` no puede bajarlos solo: los lista como «paso manual: abre <url> en el navegador y guarda en <ruta>» y verifica el hash cuando los pones en su sitio.
- **Dónde está cada enlace** (texto según la página, snapshot en `normas/apa/pages/paper-format__sample-papers.md`): sample papers de estudiante y profesional con anotaciones (PDF), con anotaciones como comentarios (DOCX) y sin anotaciones (DOCX); plantillas profesionales (Literature review, Mixed methods, Qualitative, Quantitative, Review); plantillas de estudiante (Annotated bibliography, Design project, Discussion post, Journalism assignment, Literature review, Quantitative study); Heading Levels Template (PDF).

### 2.2 IEEE templates oficiales (DOCX de conferencia y de revista)
- **Motivo del fallo:** `www.ieee.org` devuelve HTTP 202 con una página de 2 KB (desafío anti-bot) para todas las rutas de descarga probadas, incluida la página de templates de conferencias `https://www.ieee.org/conferences/publishing/templates.html`. Las rutas `…/content/dam/ieee-org/ieee/web/org/conferences/conference-template-letter.docx` y `…conference-template-a4.docx` (**sin verificar** que existan; eran candidatas de memoria) tampoco se pudieron bajar.
- **Descarga manual:**
  - IEEE Template Selector: https://template-selector.ieee.org/ (verificado, HTTP 200; app que genera el enlace de la plantilla según revista o conferencia).
  - Plantillas de revistas (Author Center): https://journals.ieeeauthorcenter.ieee.org/create-your-ieee-journal-article/authoring-tools-and-templates/tools-for-ieee-authors/ieee-article-templates/ (verificado, HTTP 200; el enlace de descarga no es visible en el HTML estático, hay que abrir la página en el navegador).
  - Conferencias: https://www.ieee.org/conferences/publishing/templates.html (sin verificar con curl; abrir en el navegador).
- Guardar en `normas/muestras/ieee/` y añadir a `SHA256SUMS`.

### 2.3 APA instructional aids restantes
- JARS, tutoriales y otros aids no se descargaron (fuera del alcance mínimo). Se pueden pedir después.

## 3. Catálogo de recursos

### 3.1 APA

| Recurso | URL | Autoridad | Cubre | Idioma | Uso en el plugin | Estado |
|---|---|---|---|---|---|---|
| APA Style, guías (grammar-guidelines) | https://apastyle.apa.org/style-grammar-guidelines | 1 | Reglas de la 7.ª ed.: formato, citas, referencias, tablas, lenguaje sin sesgo | EN | juez (fuente de reglas), verdad de referencia | Verificado (snapshot de 162 págs. en `normas/apa/pages/`) |
| APA Style, sample papers | https://apastyle.apa.org/style-grammar-guidelines/paper-format/sample-papers | 1 | Trabajos de muestra estudiante y profesional, y plantillas DOCX | EN | **corpus** (verdad de referencia completa) | Página verificada en snapshot; los DOCX/PDF están descargados a mano en `normas/muestras/apa/` (ver 2.1) |
| APA Style, instructional aids | https://apastyle.apa.org/instructional-aids | 1 | Guías rápidas, checklists, setup, referencias comunes | EN | **corpus** y **juez** | Verificado: 3 PDFs descargados |
| APA Style Blog | https://apastyle.apa.org/blog | 1 | Aclaraciones, casos (p. ej. citar IA generativa) | EN | juez (casos límite) | Verificado (raíz del blog HTTP 200; el snapshot de `normas/apa/blog` tiene 3 posts) |
| Publication Manual 7.ª ed. | https://www.apa.org/pubs/books/publication-manual-7th-edition | 1 | Norma completa | EN | Referencia de autoridad; **no descargar** (derechos) | Verificado HTTP 200 |
| Manual de Publicaciones de la APA, 4.ª ed. en español (7.ª en inglés) | ISBN 9786074488562 (Manual Moderno, 2021). Ficha de editorial: https://www.apa.org/pubs/books/manual-publicaciones | 1 (traducción oficial de APA; la editorial es Manual Moderno) | Traducción oficial de la 7.ª ed. al español | ES | **ES**: referencia para `y` vs `&`, `s. f.`, `Recuperado de` | URL de APA verificada HTTP 200 pero con desafío anti-bot en contenido; datos del ISBN según buscador (**sin verificar** en catálogo de la editorial) |
| Purdue OWL, APA | https://owl.purdue.edu/owl/research_and_citation/apa_style/index.html | 2 | Guía de formato y citas en inglés, con ejemplos | EN | juez (explicaciones), corpus pequeño | Verificado HTTP 200 |
| Universidad de Chile, Facultad de Derecho (guía APA 7) | https://derecho.uchile.cl/biblioteca/biblioteca-central/recursos-para-investigacion-academica/APA | 2 | Citas y referencias APA 7 en español, con adaptación al español (p. ej. `(s.f)`) | ES | **ES**: uso de `s.f.` | Verificado HTTP 200 y contenido (menciona "s.f.") |
| UNAM, FCA/SUAyED, "Cómo citar en APA" (PDF, 12 págs.) | https://suayedfca.unam.mx/assets/images/pdf/tedigo_como/como_citar_en_apa.pdf | 2 (facultad UNAM; no es la guía central de Bibliotecas) | Citas y referencias APA 7 en español | ES | **ES**, pero **con cuidado**: contiene errores (p. ej. una referencia con "García, B. & Uribe, J."; "Recuperado el [fecha] de" en referencias) | Verificado HTTP 200 y leído el texto |
| UNAM Bibliotecas, "Cómo hacer citas y referencias en formato APA" | https://bibliotecas.unam.mx/index.php/desarrollo-de-habilidadesinformativas/como-hacer-citas-y-referencias-en-formato-apa | 2 | Guía de citas en español | ES | juez y **ES** | **Sin verificar** (URL citada dentro del PDF de la FCA; no abierta) |
| Tecnológico de Monterrey, Biblioteca, APA 7 | https://biblioteca.tec.mx/APA-7a-ed (citas: https://biblioteca.tec.mx/APA-7a-ed/citas, referencias: https://biblioteca.tec.mx/APA-7a-ed/referencias) | 2 | Citas, referencias por tipo de documento (libros, artículos, tesis, web, Wikipedia, IA, audiovisual, leyes) | ES | juez y **ES**; ejemplos por tipo de fuente | Verificado HTTP 200 y contenido de citas |
| Universidad de Sevilla, Biblioteca, "Bibliografía y citas: APA 7ª" | https://guiasbus.us.es/bibliografiaycitas/apa7 | 2 | Guía de citas APA 7 | ES | **ES** | **URL no válida**: devuelve 404 (la encontró el buscador con fecha 2021). Buscar la guía vigente en la biblioteca de la US |
| Universidad Católica del Norte (Chile), guía APA 7 (PDF) | https://bibliotecas.ucn.cl/wp-content/uploads/2025/04/GuiaAPA7Edicionactualizado.pdf | 2 | Guía de citas APA 7 | ES | **ES** | **Sin verificar** (URL del buscador, no abierta) |
| normas-apa.org | https://normas-apa.org/ | 3 (no oficial; autoría no clara) | Guía en español de APA 7 con ejemplos | ES | Solo referencia ES; **no usar como verdad** | Verificado HTTP 200 (título "Normas APA – 7ma edición", idioma es-CO). No revisado en detalle |
| CSL oficial de APA (Zotero, `apa.csl`) | https://raw.githubusercontent.com/citation-style-language/styles/master/apa.csl (repo: https://github.com/citation-style-language/styles) | 1 (CSL oficial, mantenido por la comunidad CSL) | Motor de formato de citas APA 7 | EN | Generación de referencias de prueba (salida de referencia) | Verificado: título "APA Style 7th edition" |
| Blogs comerciales de "normas APA 7 en español" (p. ej. tesify.es) | https://tesify.es/normas-apa-septima-edicion-espana-latam-cambios-ejemplos-2026 | 4 | Resúmenes de cambios | ES | **No usar** como verdad. Sus fechas de adopción por universidades no están confirmadas | Visto en buscador; no abierto |

Recursos que tienen **ejemplos COMPLETOS** de documentos correctos (útiles como verdad de referencia para medir falsos positivos del juez):
- APA sample papers (student y professional, anotados): sección 2.1. Son la mejor verdad de referencia; ya están en `normas/muestras/apa/` (se descargan a mano; ver 2.1).
- APA instructional aids descargados: `student-paper-setup-guide.pdf` (19 págs., con diagramas anotados de portada, texto, tablas y figuras, y lista de referencias) y `reference-examples.pdf` (ejemplos de referencia por tipo, con número de sección del manual).
- Tec de Monterrey, guía de citas y referencias por tipo de documento (texto, no PDF).

Recursos para la **adaptación al español** de APA (uso de `y` vs `&`, `s. f.`, `Recuperado de`, etc.):
- Manual de Publicaciones de la APA, 4.ª ed. en español (sección 3.1). Es la fuente primaria. **No descargar**. Verificar en la edición física qué conviene.
- Universidad de Chile, Derecho (usa `s.f.`).
- Tec de Monterrey (su guía de citas indica `comunicación personal` para fuentes sin datos de publicación; el resto de formatos de recuperación no se verificó).
- **Advertencia:** los documentos en español no coinciden entre sí. El PDF de la FCA de la UNAM mezcla `&` en referencias y usa `Recuperado el … de`. No tomarlos como verdad sin contrastar con el manual en español.

### 3.2 IEEE

| Recurso | URL | Autoridad | Cubre | Idioma | Uso en el plugin | Estado |
|---|---|---|---|---|---|---|
| IEEE Author Center (revistas) | https://journals.ieeeauthorcenter.ieee.org/ | 1 | Preparación de artículos, plantillas, checklist | EN | juez y plantillas | Verificado: página de plantillas HTTP 200 |
| IEEE Editorial Style Manual for Authors | https://journals.ieeeauthorcenter.ieee.org/create-your-ieee-journal-article/create-the-text-of-your-article/ieee-editorial-style-manual/ | 1 | Estilo de redacción y formato del texto | EN | juez (fuente principal de reglas) | Enlace presente en la página verificada; local en `normas/ieee/actual/style-manual.txt` |
| IEEE Reference Guide (V 3.28.2025) | Google Doc enlazado desde IEEE Author Center (ver `normas/VERSION`) | 1 | Formato de referencias | EN | juez (reglas de referencias) | Local en `normas/ieee/actual/reference-guide.txt` |
| IEEE Math Typesetting Guide (V 10.27.2023) | Ver `normas/VERSION` | 1 | Matemáticas | EN | juez (fórmulas) | Local en `normas/ieee/actual/math-guide.txt` |
| IEEE Template Selector | https://template-selector.ieee.org/ | 1 | Enlaza a la plantilla oficial de cada revista o conferencia | EN | plantillas | Verificado HTTP 200 (app; no tiene enlace estático) |
| IEEE, plantillas de conferencias | https://www.ieee.org/conferences/publishing/templates.html | 1 | Plantillas DOCX y LaTeX de conferencias | EN | plantillas, corpus | **Sin verificar** (bloqueado por desafío anti-bot) |
| IEEE, abreviaturas de revistas | `normas/ieee/actual/abreviaturas-revistas.csv` | 1 (copia local) | Abreviaturas de títulos de revista | EN | juez (abreviaturas) | Local |
| IEEEtran (CTAN) | https://ctan.org/pkg/ieeetran (zip: https://mirrors.ctan.org/macros/latex/contrib/IEEEtran.zip) | 2 (clase LaTeX de autor individual; ver 1 en muestras) | Clase LaTeX para IEEE, `bare_conf.tex`, `bare_jrnl.tex`, bibtex `.bst` | EN | plantillas LaTeX y corpus de compilación | Verificado: descargado (ver sección 1) |
| IEEE PDF eXpress | https://pdf-express.ieee.org/ | 1 | Validación de PDF para IEEE Xplore | EN | Control de formato de salida | **Sin verificar** (no respondió: HTTP 000) |
| ieee.csl oficial (CSL, Zotero) | https://raw.githubusercontent.com/citation-style-language/styles/master/ieee.csl | 1 (CSL comunitario basado en IEEE Reference Guide 11.29.2023) | Motor de referencias IEEE | EN | Generación de referencias de prueba | Verificado: título "IEEE Reference Guide version 11.29.2023". Ojo: la versión local en `normas/plantillas/csl/ieee.csl` ya cubre 2025 |
| Universidades con guía IEEE | p. ej. Purdue OWL (la URL que se probó dio 404; buscar "IEEE" en https://owl.purdue.edu/owl/research_and_citation/ ) | 2 | Guías de citas IEEE en inglés | EN | juez (explicaciones) | Sin URL verificada de IEEE en Purdue |

Recursos con **ejemplos COMPLETOS** para IEEE: los artículos publicados en IEEE Xplore son propiedad de IEEE; no se descargaron. Las plantillas (sección 2.2) traen texto de ejemplo, que es lo más cercano a un documento completo. Solo se verificó que existen plantillas; no se bajaron.

### 3.3 Herramientas de verificación de referencias

| Recurso | URL | Autoridad | Cubre | Uso en el plugin | Estado |
|---|---|---|---|---|---|
| Crossref REST API | https://api.crossref.org/works/{DOI} | 1 (infraestructura de DOI) | Metadatos bibliográficos por DOI | juez: confirmar que el DOI existe y coincide con autor/año/título | Verificado HTTP 200 |
| Crossref, content negotiation | https://www.crossref.org/documentation/retrieve-metadata/content-negotiation/ ; también `https://doi.org/{DOI}` con cabecera `Accept: application/vnd.citationstyles.csl+json` | 1 | Metadatos en CSL-JSON desde doi.org | juez y generación de referencia | Verificado HTTP 200 |
| DOI.org | https://doi.org/ | 1 | Resolver DOI | juez: el DOI resuelve | Verificado HTTP 200 (prueba con 10.1038/nature12373) |
| OpenAlex API | https://api.openalex.org/works/doi:{DOI} | 2 | Metadatos abiertos de obras | juez (cruzar autores y año) | Verificado HTTP 200 |
| Semantic Scholar API | https://api.semanticscholar.org/graph/v1/paper/DOI:{DOI} | 2 | Metadatos y citas (requiere clave para uso intensivo) | juez (respaldo) | Verificado HTTP 200 (sin clave) |
| Retraction Watch (vía Crossref) | Blog de Crossref: https://www.crossref.org/blog/retraction-watch-retractions-now-in-the-crossref-api/ ; consulta: https://api.crossref.org/works?filter=update-type:retraction | 2 | Retractaciones | juez: marcar referencias retractadas | Verificado la consulta HTTP 200. Ojo: la página `crossref.org/services/retraction-watch/` devuelve 404 y no se usó. Los datos completos están en https://gitlab.com/crossref/retraction-watch-data (HTTP 200) |

Advertencia: la documentación de Crossref antigua habla de "Labs API" para Retraction Watch; el blog actual dice que ya está en la API de producción. Confirmar al implementar.

### 3.4 Versiones y control de cambios
- `normas/VERSION` ya registra la versión de cada fuente. No se modificó.

## 4. Recomendaciones para el plugin (resumen)
1. Usar como **verdad de referencia** solo los documentos oficiales: sample papers APA (descargados a mano, ver 2.1) y las guías rápidas ya descargadas.
2. Las guías de universidades en español sirven para casos de adaptación, pero **no son autoridad**. Contrastar cada caso con el Manual en español.
3. Para verificar referencias, usar Crossref y DOI.org primero; OpenAlex y Semantic Scholar como respaldo.
4. Retractaciones: consultar Crossref con `update-type:retraction`.

## 5. Fallos de descarga (resumen)
| Recurso | Motivo | Acción del usuario |
|---|---|---|
| APA sample papers (DOCX y PDF anotados, plantillas) | Desafío anti-bot en apastyle.apa.org (Incapsula) | Bajar a mano desde la página de sample papers (ver 2.1); `obtener_normas.py` los lista y verifica el hash |
| IEEE conference-template (DOCX/LaTeX) | Desafío anti-bot (HTTP 202) en ieee.org | Bajar desde template-selector.ieee.org o la página de conferencias (ver 2.2) |
| IEEE artículo de ejemplo oficial | No encontrado en IEEE Author Center de forma descargable | Sin alternativa oficial conocida; pedir al usuario |
| Universidad de Sevilla guía APA 7 | URL devuelve 404 | Buscar la guía vigente en la biblioteca de la US |
| PDF IEEE eXpress | No responde (HTTP 000) | Revisar en el navegador |

## 6. Reconstruir `normas/`

El repo público no incluye `normas/` (material con copyright de APA e IEEE): solo `RECURSOS.md`, `SHA256SUMS` y `VERSION`. Para tenerlo en local:

```
python scripts/obtener_normas.py              # descarga lo descargable y verifica SHA-256
python scripts/obtener_normas.py --lista      # qué falta y cómo obtenerlo
python scripts/obtener_normas.py --comprobar  # solo verifica lo presente
python scripts/obtener_normas.py --destino DIR  # reconstruir en otra carpeta
```

Con `EDITORIAL_NORMAS=DIR` las pruebas leen `normas/` de otra carpeta; sin el material, las puertas que lo necesitan imprimen `SALTADA: falta normas/… (python scripts/obtener_normas.py)` y cuentan como saltadas, no como fallos.

El script lee las filas de las tablas de este documento con la ruta `normas/<ruta>` en la primera columna y la URL en la segunda y los hashes de `normas/SHA256SUMS`, `normas/muestras/SHA256SUMS` y `normas/ieee/SHA256SUMS`. Nunca sobrescribe un archivo con hash correcto y solo guarda un archivo si su SHA-256 coincide.

| Archivo | URL | Notas |
|---|---|---|
| `normas/ieee/IEEE-Editorial-Style-Manual-for-Authors.pdf` | https://journals.ieeeauthorcenter.ieee.org/wp-content/uploads/sites/7/IEEE-Editorial-Style-Manual-for-Authors.pdf | Verificado 19-nov: descarga directa, hash coincide |
| `normas/ieee/IEEE-Math-Typesetting-Guide-for-LaTeX-Users.pdf` | https://journals.ieeeauthorcenter.ieee.org/wp-content/uploads/sites/7/IEEE-Math-Typesetting-Guide-for-LaTeX-Users.pdf | Verificado 19-nov: descarga directa, hash coincide |

Qué se reconstruye solo y qué no:
- **Automático:** `muestras/ieee/IEEEtran.zip` (CTAN), las 2 guías de IEEE en PDF con URL directa (tabla de arriba) y los archivos de `muestras/ieee/conference-*/`, que se extraen del zip correspondiente cuando este está presente.
- **Paso manual (anti-bots):** las 3 guías rápidas de APA (`apastyle.apa.org/instructional-aids/*.pdf`, ver sección 1, devuelven un desafío Incapsula a scripts), los documentos de muestra de APA (sección 2.1) y los zip de plantillas de conferencias de IEEE (`ieee.org`, HTTP 202; sección 2.2). El script imprime para cada uno «paso manual: abre <url> en el navegador y guarda en <ruta>».
- **No se reconstruye por URL:** `normas/apa/pages/`, `normas/apa/blog/`, `normas/apa/idx.html` y `normas/ieee/actual/` son snapshots convertidos a Markdown o texto; se regeneran con `/actualizar-normas`.
