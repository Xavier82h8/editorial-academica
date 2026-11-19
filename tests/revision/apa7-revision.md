# Revisión cruzada APA 7 (skills/apa7)

Fuente de verdad: `normas/apa/pages/*.md` y `normas/apa/blog/*.md` (snapshot 2026-11-18). Revisión de las 139 reglas del checklist y de los 12 archivos de `references/`. Método: lectura de las páginas del snapshot por tema y comprobación automática de cada ejemplo/plantilla (subcadena literal, con y sin marcas de cursiva) contra el snapshot. Los ejemplos de referencias coinciden carácter a carácter con el snapshot salvo los casos listados.

| ID/ubicación | Clasificación | Problema | Corrección aplicada | Fuente snapshot |
|---|---|---|---|---|
| APA-008 | IMPRECISE | Severidad crítica para un detalle de encabezado; no hace inutilizable la cita | Sev. mayor; añadido "portada lleva el 1" | paper-format/page-header |
| APA-009 | IMPRECISE | Fix "sí" pero abreviar el título requiere juicio; faltaba caso estudiante y "con espacios y puntuación" | Fix no; texto ampliado | paper-format/page-header |
| APA-012 | IMPRECISE | "Siempre en página nueva" cuando el snapshot dice "en general" (solo apéndices son siempre) | Reformulada | paper-format/order-pages, appendices |
| APA-016 | IMPRECISE | Cita § 2.19 en página que no nombra sección | Fuente: p. xviii (introducción) | paper-format/accessibility/typography |
| APA-017 | IMPRECISE | Severidad crítica excesiva | Mayor | paper-format/title-page |
| APA-018 | UNSUPPORTED | Capitalización de oración en español sin rótulo | Rotulada "adaptación, convención no APA" | paper-format/title-page |
| APA-024 | IMPRECISE | Faltaba "solo los necesarios, empezando por el 1" | Añadido | paper-format/headings |
| APA-031 | UNSUPPORTED | "Introducción" en español no es regla APA | Rotulada como extensión por convención | paper-format/headings |
| APA-038 | IMPRECISE | Fix "sí" pese a excepción de desambiguación | Fix no; remite a APA-046 | citations/basic-principles/author-date |
| APA-039 | IMPRECISE | Redacción confusa ("una o dos obras con uno o dos autores") | Reformulada | citations/basic-principles/author-date |
| APA-041, APA-042 | IMPRECISE | Fix "sí" requiere juicio (n.d./in press; reescribir cita) | Fix no | citations/basic-principles/author-date |
| APA-048 | IMPRECISE | Severidad crítica: la obra sigue identificada | Mayor | citations/quotations/page-numbers |
| APA-055 | IMPRECISE | No recogía la variante indígena (nombre completo, nación) | Añadida | citations/personal-communications |
| APA-057 | IMPRECISE | Fuente solo appropriate-citation; "hechos y cifras no comunes" está en basic-principles | Fuente ampliada | citations/basic-principles |
| APA-059 | IMPRECISE | "(o Reference)" sin condición | "solo si hay una única entrada" | paper-format/reference-list |
| APA-063 | IMPRECISE | Fix "sí" (invertir nombres exige juicio); "y" sin rótulo | Fix no; "y" rotulada adaptación | references/elements-list-entry |
| APA-064 | IMPRECISE | Severidad menor para omitir autores; faltaba "sin &" | Mayor; texto | references/elements-list-entry |
| APA-069, APA-070 | IMPRECISE | Fix "sí" incluye conversión de mayúsculas (juicio) | Fix no | references/elements-list-entry |
| APA-073 | WRONG | "con número (issue) y con páginas" omitía los casos sin volumen/páginas | Reformulada con los casos del snapshot | references/examples/journal-article-references |
| APA-074 | IMPRECISE | Fuente "cap. 10" | § 10.1; § 8.25-8.27 | journal-article-references, page-numbers |
| APA-081 | IMPRECISE | Fix "sí" (decidir si la base es propietaria requiere juicio) | Fix no | references/database-information |
| APA-082 | IMPRECISE | Fuente no respaldaba "lugar de publicación" | Fuente: dois-urls + elements-list-entry | references/dois-urls, elements-list-entry |
| APA-083, APA-085 | IMPRECISE | Fuente "cap. 10" | § 10.2 y § 10.6 | book-references, published-dissertation |
| APA-088 | UNSUPPORTED | Regla del plugin presentada con fuente APA | Rotulada [PLUGIN, no es regla APA] | references/basic-principles (solo 4 elementos) |
| APA-089, APA-090 | IMPRECISE | Fix "sí" con renumeración y title case (juicio); fuente "cap. 7" | Fix no; § 7.8-7.36 | tables-figures/tables, figures |
| APA-091 | UNSUPPORTED | El snapshot solo dice "tras la primera mención"; no exige explícitamente mención | Nota aclaratoria; fuente § 7.8-7.36 | tables-figures/tables |
| APA-092..094, APA-097 | IMPRECISE | Fuente "cap. 7" | § 7.8-7.21 / § 7.22-7.36 | tables-figures |
| APA-096 | IMPRECISE | Fix "sí" no aplicable a imágenes | Fix no | tables-figures/figures |
| APA-100 | IMPRECISE | Fuente "cap. 10" | § 12.14-12.18 | clip-art-references |
| APA-104 | IMPRECISE | Faltaban excepciones "v." y "et al." | Añadidas | abbreviations/latin |
| APA-105, 108, 109, 110, 111, 112, 113, 131 | IMPRECISE | Fix "sí" con conversión de mayúsculas o juicio | Fix no | capitalization, numbers, lists |
| APA-106 | IMPRECISE | § 6.16 solo cubre enfermedades; nombres propios son § 6.14-6.15 | § 6.14-6.16 | capitalization/proper-nouns |
| APA-109 | UNSUPPORTED | Coma serial en español choca con la RAE sin aviso | Remite a mecanica.md §6 | punctuation/serial-comma |
| APA-114 | WRONG | "salvo reescritura imposible" no existe: el snapshot manda palabras ("cuando sea posible, reformular") | Reformulada | numbers/words |
| APA-116 | UNSUPPORTED | RAE sin rótulo de adaptación | Rotulada | spelling-hyphenation/spelling |
| APA-126 | IMPRECISE | "victim" suelto; el snapshot dice "AIDS victim"; "hearing impaired" con guion | Corregidos | bias-free-language/disability |
| APA-127 | IMPRECISE | "minorities" siempre prohibido; con modificador (racial/ethnic) se admite | Matizada | bias-free-language/racial-ethnic-minorities |
| APA-132 | IMPRECISE | El post dice "normalmente será necesario", no absoluto | Matizada | blog/cite-generative-ai-references |
| APA-138 | IMPRECISE | Fuente solo el post archivado de 2023 | Añadida Parte 1 (verificar la salida); aclarado consejo, no regla | blog cite-generative-ai-references, how-to-cite-chatgpt |
| APA-139 | IMPRECISE | No indicaba que no es requisito de APA | Añadido | blog/ai-contribution-statement |
| Header checklist | IMPRECISE | Definiciones de severidad y de Fix poco operativas | Redefinidas (crítica = inutiliza/atribuye mal; Fix sí = mecánico sin juicio ni mayúsculas) | n/a |
| APA-140..144 (nuevas) | OK (agregadas) | Reglas del snapshot sin cubrir: metaanálisis, preprint, fecha de recuperación, aula/intranet, tablas largas | Agregadas | references/meta-analysis-references, preprint-article, elements-list-entry, citations/classroom-intranet-sources, tables-figures/tables |
| SKILL.md | IMPRECISE | "139 reglas"; rutas `a/b` sin explicar; "Recuperado el" sin rótulo de convención | 144 reglas; mapeo a__b.md; rótulo | n/a |
| formato-pagina §1 | UNSUPPORTED | Resumen "Sí" para profesional no está en el snapshot | "No definido en el snapshot" | paper-format/sample-papers |
| formato-pagina §10 | UNSUPPORTED | Instrucción para encabezados de nivel 4-5 (resaltar solo el encabezado) no figura en el snapshot | Eliminada | paper-format/accessibility/headings |
| portada.md (común) | IMPRECISE | "Todo centrado" contradice nota del autor a la izquierda | Excepción añadida | paper-format/title-page |
| portada.md tesis | WRONG | Remite a `referencias-por-tipo.md` inexistente | `referencias-por-tipo-1.md` §11 | n/a |
| encabezados.md §3 | UNSUPPORTED | Ejemplo "2.1/2.2" inventado (los encabezados no se numeran) | Eliminado | paper-format/headings |
| citas-texto §1 | IMPRECISE | "Mito de 5-10 años" viene de un titular de blog, no de una página | Aclarado | citations/basic-principles (lista de blog) |
| citas-texto §2 | UNSUPPORTED | Consejo "e por y ante i/hi" no está en el snapshot | Eliminado | n/a |
| citas-texto §8 | UNSUPPORTED | "prácticas comunes en guías hispanas" sin respaldo | Reformulado como convención | n/a |
| citas-texto §9, Gaps | WRONG | Ubicación del blog de traducción propia; archivo `referencias-por-tipo.md` inexistente | Corregidos | citations/basic-principles/parts-source |
| referencias-principios (cabecera, §9) | WRONG/UNSUPPORTED | Archivo inexistente; "§9.44-9.47" no nombrado por el snapshot | Corregidos a §9.43-9.49 | paper-format/reference-list |
| referencias-principios §1 | UNSUPPORTED | "Cursiva en puntuación interna" y "editar citas sugeridas por la obra" sin respaldo; puntuación entre partes solo deducida | Eliminados / rotulado deducido | references/basic-principles |
| referencias-principios §2, §4 | UNSUPPORTED | "algunas guías mantienen &"; regla de mayúscula tras dos puntos en español | Eliminados / reformulado (RAE) | n/a |
| por-tipo-1 cabecera | IMPRECISE | Plantillas derivadas sin rotular; "..." ambiguo | Aclarado | references/elements-list-entry |
| por-tipo-1 §1 | IMPRECISE | Ejemplo Kairos truncado con "..." | Ejemplo oficial completo | journal-article-references |
| por-tipo-1 §14 | UNSUPPORTED | Plantilla de software atribuida al snapshot; el Gap la negaba | Rotulada derivada y Gap reconciliado | references/elements-list-entry, examples |
| por-tipo-1 §11, §15, ERIC | WRONG | Secciones erróneas (9.30 para preprint/ERIC; "cap. 10" para tesis) | 10.8 y 10.6 | preprint-article, eric-database, dissertation pages |
| por-tipo-2 §8, ia-generativa §2 | IMPRECISE | Ejemplo de chat copia un artefacto de marcado (`graduates *[`) | Cursiva cerrada correctamente + nota | references/examples/ai-references |
| ia-generativa §1, §5 | UNSUPPORTED | "las revistas APA lo establecen" y "Para trabajos del plugin" sin rótulo | Atribuido al post / rotulado convención del plugin | blog/ai-contribution-statement |
| gramatica-sesgo (género) | WRONG | `man the project`; el snapshot dice `man a project` | Corregido | bias-free-language/gender |
| tablas-figuras | IMPRECISE | "cap. 7" genérico | § 7.8-7.21 y § 7.22-7.36 | tables-figures/tables, figures |

## Verificados sin cambio (OK)

APA-001..007, 010, 011, 013..015, 019..023, 025..030, 032, 033, 034..037, 040, 043..047, 049..054, 056, 058, 060..062, 065..068, 071, 072, 075..080, 084, 086, 087, 092, 095, 098, 099, 101..103, 107, 115, 117..125, 128..130, 133..137. Todos los ejemplos literales de `referencias-por-tipo-1/2`, `referencias-principios` (base de datos, archivo), `citas-texto` y `ia-generativa` coinciden con el snapshot. Tablas de verbos, plurales/posesivos, abreviaturas, números, listas, ortografía y las categorías de lenguaje sin sesgo verificadas término por término (excepto lo corregido arriba). El § 9.21 de APA-071 sí está respaldado (lo cita ai-references).

## Totales (por elemento revisado: reglas + secciones de references)

| Clasificación | Cantidad |
|---|---|
| OK | 96 reglas (91 sin cambios + 5 nuevas APA-140..144 no cuentan como revisadas) y ~95 % de los ejemplos de referencia |
| WRONG | 6 (APA-073, APA-114, portada.md remisión, referencias-principios cabecera/§9, por-tipo-1 secciones, gramática "man the project") |
| UNSUPPORTED | 13 (APA-018, 031, 088, 091, 109, 116; formato-pagina x2; encabezados §3; citas-texto §2, §8; referencias-principios §1/§2/§4; por-tipo-1 §14; ia-generativa §1/§5) |
| IMPRECISE | 41 (severidades, Fix, fuentes "cap. N", redacción) |

(Cifras aproximadas por agrupación de filas; el detalle fila a fila está en la tabla.)

## Preguntas abiertas

1. APA-091: el snapshot no exige explícitamente "mencionar cada tabla/figura"; mantener como regla o rebajar.
2. Resumen/keywords profesionales y contenido de la nota del autor (§2.7) no están en el snapshot.
3. Severidad de APA-053 y APA-095 se dejó crítica (atribución errónea); decidir si se mantiene.
4. Fix "sí" restantes (p. ej. APA-018, 025-029) cubren solo formato visual; la conversión de mayúsculas se trata como juicio.
5. Software (§10.10), reseñas (§10.7) y legales (cap. 11) sin página oficial en el snapshot.
