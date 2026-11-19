# APA 7: checklist de auditoría (juez)

Reglas binarias (cumple / no cumple) comprobables en el documento. Fuente: snapshot oficial 2026-11-18 (`normas/VERSION`); el detalle de cada regla está en el archivo de `references/` indicado en la última columna.

- Columnas: `ID` · `Regla` · `Sev.` (crítica = deja inutilizable la cita o la referencia, o atribuye mal autoría o fuente; mayor = incumplimiento visible de la norma; menor = detalle cosmético) · `Fix` (sí = corrección puramente mecánica por script o plantilla, sin juicio del autor ni conversión de mayúsculas; no = requiere juicio, contenido o verificación externa) · `Fuente` (`§ Manual` cuando la página lo indica | ruta bajo `normas/apa/pages/`).
- Perfil: estas reglas aplican cuando APA es la base (PAG, POR, ENC, TAB) y/o la capa de citas (CIT, REF). En perfiles combinados el juez omite los grupos que no gobiernan; ver skill `combinar-formatos`.
- Tipo de trabajo: reglas marcadas (E) solo estudiante, (P) solo profesional. Tesis y disertaciones: la institución puede sustituir márgenes, portada y orden de páginas (APA-001, APA-011 y APA-017 a APA-023); registrar la excepción en vez de marcar violación.
- Documento en español: las reglas de idioma inglés (title case, "&", "n.d.", 0-9 en palabras, coma serial, they singular) se juzgan con la "Adaptación al español" del archivo de referencias correspondiente; son convención, no regla oficial APA, y se reportan con severidad reducida a menor salvo que el perfil o la institución las exija. Localización de las referencias (decisión del usuario, 18-nov-2026): se aceptan tanto los elementos en inglés ("&", "n.d.", "Retrieved", "Dec.", "No.") como traducidos ("y", "s.f.", "Recuperado", "dic.", "núm."); ninguna de las dos formas es hallazgo. Excepción: la cita parentética lleva siempre "&" (APA-037).

## PAG. Formato de página (formato-pagina.md) [APA-001 a APA-016]

| ID | Regla | Sev. | Fix | Fuente |
|---|---|---|---|---|
| APA-001 | Márgenes de 1 in (2,54 cm) en los cuatro lados (tesis: salvo margen institucional) | mayor | sí | § 2.22 \| paper-format/margins |
| APA-002 | La fuente es una de las permitidas con su tamaño (Aptos 12, Calibri 11, Arial 11, Lucida Sans Unicode 10, Times New Roman 12, Georgia 11, Computer Modern 10) o la predeterminada del procesador | mayor | sí | § 2.19 \| paper-format/font |
| APA-003 | Una sola fuente en todo el documento (excepciones: figuras 8-14 pt sans serif, código monoespaciado, notas al pie) | menor | sí | § 2.19 \| paper-format/font |
| APA-004 | Interlineado doble en texto, resumen, citas en bloque, números/títulos/notas de tablas y figuras, y lista de referencias | mayor | sí | § 2.21 \| paper-format/line-spacing |
| APA-005 | Sin espacio adicional antes o después de párrafos | menor | sí | § 2.21 \| paper-format/line-spacing |
| APA-006 | Texto alineado a la izquierda, margen derecho irregular; sin justificación completa | mayor | sí | § 2.23 \| paper-format/paragraph-format |
| APA-007 | Primera línea de cada párrafo con sangría de 0,5 in hecha con tabulador o formato de párrafo, no con espacios | mayor | sí | § 2.24 \| paper-format/paragraph-format |
| APA-008 | Número de página en la esquina superior derecha de todas las páginas, incluidas portada (lleva el 1), referencias y apéndices | mayor | sí | § 2.18 \| paper-format/page-header |
| APA-009 | (P) Running head (título abreviado) en mayúsculas, máximo 50 caracteres con espacios y puntuación, alineado a la izquierda del encabezado, en todas las páginas incluida la portada; (E) solo si lo pide el docente o la institución | mayor | no | § 2.18 \| paper-format/page-header |
| APA-010 | (P) El running head no lleva la etiqueta "Running head:" ni abreviaturas (se permite "&") | menor | sí | § 2.18 \| paper-format/page-header |
| APA-011 | Orden de páginas: portada, resumen (si hay), texto, referencias, notas al pie, tablas, figuras, apéndices (tablas/figuras y notas pueden ir incrustadas) | mayor | no | § 2.17 \| paper-format/order-pages |
| APA-012 | En general cada sección empieza en página nueva (resumen, referencias); cada apéndice siempre en página separada | menor | sí | § 2.17, 2.14 \| paper-format/order-pages, paper-format/appendices |
| APA-013 | Etiquetas de sección ("Abstract", "References") centradas y en negrita | mayor | sí | § 2.23 \| paper-format/paragraph-format |
| APA-014 | Cada apéndice en página propia con etiqueta "Appendix" (uno) o "Appendix A/B" (varios) y título en la línea siguiente, ambos centrados y en negrita | mayor | sí | § 2.14 \| paper-format/appendices |
| APA-015 | Cada apéndice se menciona en el texto, en el orden en que aparecen | mayor | no | § 2.14 \| paper-format/appendices |
| APA-016 | Comillas y apóstrofos tipográficos (curvos), no rectos | menor | sí | p. xviii (introducción) \| paper-format/accessibility/typography |

## POR. Portada (portada.md) [APA-017 a APA-023]

| ID | Regla | Sev. | Fix | Fuente |
|---|---|---|---|---|
| APA-017 | Existe portada con título, autores y afiliación (tesis: portada institucional) | mayor | no | § 2.3 \| paper-format/title-page |
| APA-018 | Título centrado, en negrita, en title case (adaptación al español, convención no APA: capitalización de oración), 3-4 líneas bajo el borde superior | mayor | sí | § 2.3 \| paper-format/title-page |
| APA-019 | Una línea en blanco a doble espacio entre título y autores | menor | sí | § 2.3 \| paper-format/title-page |
| APA-020 | Autores centrados en línea propia; dos: "and"; tres o más: comas y "and" antes del último | mayor | sí | § 2.3 \| paper-format/title-page |
| APA-021 | Afiliación con departamento y universidad separados por coma, centrada en la línea siguiente a los autores | mayor | no | § 2.3 \| paper-format/title-page |
| APA-022 | (E) La portada incluye, centrados y en este orden tras la afiliación: curso (número, dos puntos, nombre), instructor y fecha de entrega | mayor | no | § 2.3 \| paper-format/title-page |
| APA-023 | (P) Nota del autor en la mitad inferior de la portada con etiqueta "Author Note" centrada y en negrita y párrafos a la izquierda | mayor | sí | § 2.3 \| paper-format/title-page |

## ENC. Encabezados (encabezados.md) [APA-024 a APA-033]

| ID | Regla | Sev. | Fix | Fuente |
|---|---|---|---|---|
| APA-024 | Máximo cinco niveles; solo los necesarios, empezando por el 1; cada nivel subdivide al anterior sin saltar niveles | mayor | no | § 2.26 \| paper-format/headings |
| APA-025 | Nivel 1: centrado, negrita, title case | mayor | sí | § 2.27 \| paper-format/headings |
| APA-026 | Nivel 2: a la izquierda, negrita, title case | mayor | sí | § 2.27 \| paper-format/headings |
| APA-027 | Nivel 3: a la izquierda, negrita cursiva, title case | mayor | sí | § 2.27 \| paper-format/headings |
| APA-028 | Nivel 4: con sangría, negrita, title case, termina en punto y el texto sigue en la misma línea | mayor | sí | § 2.27 \| paper-format/headings |
| APA-029 | Nivel 5: con sangría, negrita cursiva, title case, termina en punto y el texto sigue en la misma línea | mayor | sí | § 2.27 \| paper-format/headings |
| APA-030 | Encabezados sin numeración ni letras ("1.", "A.") | mayor | sí | § 2.26 \| paper-format/headings |
| APA-031 | El texto no empieza con un encabezado "Introduction" (en español "Introducción": extensión por convención, no regla APA) | mayor | sí | § 2.26 \| paper-format/headings |
| APA-032 | Ninguna sección tiene un único subencabezado | menor | no | § 2.26 \| paper-format/headings |
| APA-033 | Encabezados a doble espacio y sin líneas en blanco antes o después | menor | sí | § 2.26 \| paper-format/headings |

## CIT. Citas en el texto (citas-texto.md) [APA-034 a APA-058]

| ID | Regla | Sev. | Fix | Fuente |
|---|---|---|---|---|
| APA-034 | Cada cita en el texto tiene su entrada en la lista de referencias y cada entrada está citada (excepciones: comunicaciones personales, menciones generales de sitios y software común, epígrafes, participantes, metaanálisis) | crítica | no | § 2.12, 8.4 \| references/works-included |
| APA-035 | Apellidos y años de las citas coinciden con los de la lista | crítica | no | § 8.10 \| citations/basic-principles |
| APA-036 | Citas en formato autor-fecha: parentética `(Autor, año)`; narrativa `Autor (año)` | mayor | sí | § 8.11 \| citations/basic-principles/parenthetical-versus-narrative |
| APA-037 | En parentética "&" entre autores, también en documentos en español (decisión del usuario, 18-nov-2026); en narrativa "and" ("y") | mayor | sí | § 8.10 \| citations/basic-principles/author-date |
| APA-038 | Tres o más autores: primer autor + "et al." desde la primera cita (salvo desambiguación, APA-046) | mayor | no | § 8.10-8.36 \| citations/basic-principles/author-date |
| APA-039 | Obra con uno o dos autores: se nombran todos en cada cita | mayor | sí | § 8.10-8.36 \| citations/basic-principles/author-date |
| APA-040 | Grupo autor con abreviatura: nombre completo con abreviatura la primera vez (corchetes en parentética, paréntesis con coma en narrativa) y solo abreviatura después | mayor | no | § 8.21 \| abbreviations/group-authors |
| APA-041 | La cita lleva solo el año (no fecha completa); sin fecha "n.d." ("s.f."); aceptada sin publicar "in press" | mayor | no | § 8.10 \| citations/basic-principles/author-date |
| APA-042 | No se usa "ibid." ni solo el número de página: la cita se repite completa | mayor | no | § 8.10 \| citations/basic-principles/author-date |
| APA-043 | Varias obras en un paréntesis: orden alfabético separado por punto y coma | mayor | sí | § 8.12 \| citations/basic-principles/multiple-works |
| APA-044 | Obras con mismo autor y año: letras a, b, c tras el año (n.d.-a) en cita y lista | mayor | no | § 8.19 \| citations/basic-principles/same-year-author |
| APA-045 | Primeros autores con mismo apellido e iniciales distintas: iniciales en todas las citas | mayor | no | § 8.20 \| citations/basic-principles/citing-authors-same-surname |
| APA-046 | Obras con 3+ autores que se acortan igual: se escriben apellidos hasta distinguirlas | menor | no | § 8.18 \| citations/basic-principles/same-year-first-author |
| APA-047 | Parte de una fuente con formato correcto: p., pp., para., Chapter, Table, Figure, marca de tiempo | mayor | sí | § 8.13 \| citations/basic-principles/parts-source |
| APA-048 | Toda cita textual lleva autor, año y página u otra ubicación | mayor | no | § 8.25 \| citations/quotations/page-numbers |
| APA-049 | Citas de menos de 40 palabras van entre comillas dentro del texto; de 40 o más en bloque sin comillas | mayor | no | § 8.25 \| citations/quotations |
| APA-050 | Cita en bloque sangrada 0,5 in, a doble espacio, sin punto tras el paréntesis de cita | mayor | sí | § 8.27 \| citations/quotations |
| APA-051 | Sin números de página: sección, párrafo o marca de tiempo; nunca ubicaciones de Kindle | mayor | no | § 8.28 \| citations/quotations/no-page-numbers |
| APA-052 | Omisiones con puntos suspensivos, adiciones entre corchetes, énfasis con "[emphasis added]" | mayor | no | § 8.30-8.31 \| citations/quotations/changes |
| APA-053 | La cita textual reproduce palabras, ortografía y puntuación del original; errores con "[sic]" | crítica | no | § 8.29 \| citations/quotations/errors |
| APA-054 | Fuente secundaria: "as cited in"; solo la secundaria en la lista | mayor | no | § 8.6 \| citations/secondary-sources |
| APA-055 | Comunicación personal: solo en el texto, con iniciales, apellido, "personal communication" y fecha; sin entrada en la lista (variante de conocimiento tradicional indígena no grabado: nombre completo y nación o grupo) | mayor | no | § 8.9 \| citations/personal-communications |
| APA-056 | Citas de participantes de la propia investigación sin referencia ni comunicación personal, con aviso de que son participantes | mayor | no | § 8.36 \| citations/quoting-participants |
| APA-057 | Hechos y cifras que no son de conocimiento común, paráfrasis e ideas ajenas tienen cita | crítica | no | § 8.1-8.3 \| citations/appropriate-citation, citations/basic-principles, citations/plagiarism |
| APA-058 | No hay sobrecitación: la misma cita no se repite en cada oración de un mismo párrafo con la misma fuente | menor | no | § 8.1 \| citations/appropriate-citation |

## REF. Lista de referencias (referencias-principios.md, referencias-por-tipo-1.md, referencias-por-tipo-2.md) [APA-059 a APA-088]

| ID | Regla | Sev. | Fix | Fuente |
|---|---|---|---|---|
| APA-059 | Lista rotulada "References" ("Reference" solo si hay una única entrada), centrada, negrita, en página nueva; no "Bibliography", "Works Cited" ni "Reference List" | mayor | sí | § 2.12 \| paper-format/reference-list |
| APA-060 | Sangría francesa de 0,5 in, doble espacio y sin espacio extra entre entradas | mayor | sí | § 9.43-9.49 \| paper-format/reference-list |
| APA-061 | Orden alfabético por la primera palabra de la entrada; sin autor: por título | mayor | sí | § 9.43-9.49 \| paper-format/reference-list |
| APA-062 | Cada entrada tiene autor, fecha, título y fuente | mayor | no | § 9.4-9.6 \| references/basic-principles |
| APA-063 | Autores invertidos (apellido, iniciales con espacio entre iniciales); coma entre autores y "&" ("y", adaptación al español) antes del último | mayor | no | § 9.7-9.37 \| references/elements-list-entry |
| APA-064 | De 2 a 20 autores se listan todos; con 21 o más: los 19 primeros, puntos suspensivos (sin "&") y el último | mayor | sí | § 9.7-9.37 \| references/elements-list-entry |
| APA-065 | Grupo autor con nombre completo, sin abreviatura ni siglas entre paréntesis | mayor | sí | § 9.11 \| references/elements-list-entry |
| APA-066 | Fecha entre paréntesis seguida de punto, con año primero (año, mes día) | mayor | sí | § 9.7-9.37 \| references/elements-list-entry |
| APA-067 | Sin fecha "(n.d.)" ("s.f."); aceptada sin publicar "(in press)"; no "in progress" | menor | sí | § 9.7-9.37 \| references/elements-list-entry |
| APA-068 | Sin autor: título en posición de autor; no "Anonymous" salvo que la obra esté firmada así | menor | no | § 9.4 \| references/missing-information |
| APA-069 | Título de artículo o capítulo en sentence case, sin cursiva ni comillas | mayor | no | § 9.7-9.37 \| references/elements-list-entry |
| APA-070 | Título de obra independiente (libro, informe, página web, tesis) en cursiva y sentence case | mayor | no | § 9.7-9.37 \| references/elements-list-entry |
| APA-071 | Descripción entre corchetes (mayúscula inicial, sin cursiva) en obras no tradicionales: software, datos, tesis, comunicados, videos, publicaciones de redes | mayor | no | § 9.21 \| references/elements-list-entry |
| APA-072 | Artículo de revista: revista y volumen en cursiva; número entre paréntesis sin cursiva; sin coma entre volumen y número | mayor | sí | § 10.1 \| references/basic-principles, examples/journal-article-references |
| APA-073 | Artículo de revista con número (issue) siempre; con páginas, o "Article" más número de artículo; si la revista no usa volumen, número o páginas, se omite el elemento ausente | mayor | no | § 10.1 \| references/examples/journal-article-references |
| APA-074 | Rangos de páginas con raya en (–) | menor | sí | § 10.1; § 8.25-8.27 \| references/examples/journal-article-references (raya en) |
| APA-075 | Punto después de cada elemento y ninguno después de DOI o URL | mayor | sí | § 9.4-9.6 \| references/basic-principles |
| APA-076 | DOI como hipervínculo `https://doi.org/...` | mayor | sí | § 9.34-9.36 \| references/dois-urls |
| APA-077 | Toda obra con DOI lo incluye | mayor | no | § 9.34-9.36 \| references/dois-urls |
| APA-078 | Los DOI y URL de la lista resuelven y apuntan a la obra citada | crítica | no | § 9.34-9.36 \| references/dois-urls |
| APA-079 | Sin "Retrieved from"/"Accessed from" ("Recuperado de") antes de DOI o URL | mayor | sí | § 9.34-9.36 \| references/dois-urls |
| APA-080 | Con DOI y URL se deja solo el DOI | menor | sí | § 9.34-9.36 \| references/dois-urls |
| APA-081 | Sin nombre ni URL de bases de datos académicas comunes (salvo obras propietarias o de circulación limitada) | mayor | no | § 9.30 \| references/database-information |
| APA-082 | Sin ISBN, ISSN ni lugar de publicación en libros | menor | sí | § 9.34-9.36, 9.7-9.37 \| references/dois-urls (ISBN/ISSN), references/elements-list-entry (lugar) |
| APA-083 | Libro: editorial al final, edición entre paréntesis tras el título sin cursiva | mayor | no | § 10.2 \| references/examples/book-references |
| APA-084 | Capítulo de libro editado: "In" + editores (inicial primero, "(Eds.)") + título del libro en cursiva + páginas + editorial; no hay entradas para capítulos de libros de autor único | mayor | no | § 10.3 \| references/examples/edited-book-chapter-references |
| APA-085 | Tesis: tipo de trabajo y universidad entre corchetes; si es publicada, base o repositorio como fuente | mayor | no | § 10.6 \| references/examples/published-dissertation-references |
| APA-086 | Publicación en redes: autor con @usuario entre corchetes, primeras 20 palabras en cursiva, descripción entre corchetes, sitio y URL | mayor | no | § 10.15 \| references/examples/x-references |
| APA-087 | Sin referencias de sitios web completos ni de comunicaciones personales | mayor | no | § 8.9 \| references/works-included, examples/whole-website-references |
| APA-088 | [PLUGIN, no es regla APA] Entrada verificada contra metadatos de Crossref/OpenAlex (autores, año, título, DOI coinciden) | crítica | no | Regla del plugin; APA solo define los cuatro elementos (§ 9.4 \| references/basic-principles) |

## TAB. Tablas y figuras (tablas-figuras.md) [APA-089 a APA-100]

| ID | Regla | Sev. | Fix | Fuente |
|---|---|---|---|---|
| APA-089 | Número ("Table 1"/"Figure 1") en negrita sobre el título; numeración en orden de mención | mayor | no | § 7.8-7.36 \| tables-figures/tables, figures |
| APA-090 | Título una línea doble bajo el número, en cursiva y title case | mayor | no | § 7.8-7.36 \| tables-figures/tables, figures |
| APA-091 | Toda tabla y figura se menciona en el texto por su número (la ubicación se define "tras su primera mención"). Regla por decisión del usuario (18-nov-2026): toda figura y tabla se menciona y explica en el texto | mayor | sí | § 7.8-7.36 \| tables-figures/tables, figures |
| APA-092 | Tabla con encabezados de columna, incluido el de la columna izquierda, centrados y en sentence case | menor | no | § 7.8-7.21 \| tables-figures/tables |
| APA-093 | Tabla con bordes horizontales mínimos; sin bordes verticales ni en cada celda | mayor | sí | § 7.8-7.21 \| tables-figures/tables |
| APA-094 | Notas con "Note." en cursiva; notas específicas con letras; probabilidad con asteriscos | menor | sí | § 7.8-7.21 \| tables-figures/sample-tables |
| APA-095 | Tabla o figura reproducida o adaptada de otra obra con atribución de copyright en la nota | crítica | no | § 12.14-12.18 \| citations/plagiarism |
| APA-096 | Texto dentro de figuras en sans serif de 8 a 14 pt | menor | no | § 2.19; § 7.22-7.36 \| paper-format/font, tables-figures/figures |
| APA-097 | Figura con ejes rotulados, unidades de medida y elementos explicados; leyenda dentro de la figura | mayor | no | § 7.22-7.36 \| tables-figures/figures |
| APA-098 | Colocación: incrustada tras su primera mención (arriba o abajo de la página, con línea en blanco) o en páginas tras las referencias | menor | no | § 2.17 \| paper-format/order-pages |
| APA-099 | Colores con contraste suficiente; la información no depende solo del color | mayor | no | § 7.26 \| tables-figures/colors |
| APA-100 | Imagen de stock o clip art: atribución y referencia según su licencia | mayor | no | § 12.14-12.18 \| references/examples/clip-art-references |

## MEC. Mecánica (mecanica.md) [APA-101 a APA-116]

| ID | Regla | Sev. | Fix | Fuente |
|---|---|---|---|---|
| APA-101 | Abreviatura definida en su primer uso (excepto las de diccionario, de medida, de tiempo con valor, latinas y estadísticas comunes) | mayor | no | § 6.25 \| abbreviations/definition |
| APA-102 | Tras definirla se usa solo la abreviatura; se usa al menos tres veces (salvo estándar para término largo) | menor | no | § 6.25 \| abbreviations/definition |
| APA-103 | Abreviaturas sin puntos (FBI, PhD) | menor | sí | cap. 6 \| abbreviations |
| APA-104 | Abreviaturas latinas (e.g., i.e., etc., cf., viz., vs.) solo en paréntesis; en la narración se escribe la traducción (excepciones: "v." en nombres de casos judiciales, "et al.") | menor | sí | § 6.29 \| abbreviations/latin |
| APA-105 | Title case en encabezados, títulos de tablas y figuras, y títulos de periódicos; sentence case en títulos de la lista, encabezados de columna y notas | mayor | no | § 6.17 \| capitalization/title-case, sentence-case |
| APA-106 | Nombres propios con mayúscula; cargos, enfermedades, terapias, teorías y procedimientos estadísticos en minúscula (salvo nombres propios incluidos) | menor | no | § 6.14-6.16 \| capitalization/proper-nouns, diseases-disorders-therapies |
| APA-107 | Cursiva en títulos de obras independientes y periódicos, y en términos clave solo en su primer uso | menor | no | § 6.22 \| italics-quotations/italics |
| APA-108 | Símbolos estadísticos y anclajes de escala en cursiva | menor | no | § 6.22 \| italics-quotations/italics |
| APA-109 | Coma serial en series de tres o más elementos; punto y coma si algún elemento lleva comas (en español rige la RAE, ver mecanica.md §6) | mayor | no | § 6.3 \| punctuation/serial-comma |
| APA-110 | Listas con letras minúsculas entre paréntesis (a), (b), no números, dentro de una oración | menor | no | § 6.50 \| lists/lettered |
| APA-111 | Viñetas: ítems que son oraciones empiezan con mayúscula y terminan con punto; ítems que son frases empiezan con minúscula y se puntúan de forma uniforme | menor | no | § 6.52 \| lists/bulleted |
| APA-112 | Números 0-9 en palabras y 10 o más en numerales (excepciones en APA-113 y APA-114) | mayor | no | § 6.32-6.33 \| numbers/numerals, words |
| APA-113 | Numerales siempre en medidas, porcentajes, edades, fechas y tiempos, puntuaciones, decimales, razones y dinero exacto | mayor | no | § 6.32 \| numbers/numerals |
| APA-114 | Un número al inicio de oración, título o encabezado se escribe en palabras (preferible reformular la oración) | menor | no | § 6.33 \| numbers/words |
| APA-115 | Un espacio tras punto final (no dos) | menor | sí | § 6.1 \| punctuation/space-after-period |
| APA-116 | Ortografía y guiones consistentes con el diccionario (Merriam-Webster, APA Dictionary; en español RAE, adaptación no APA) | menor | no | § 6.11 \| spelling-hyphenation/spelling |

## LEN. Gramática y lenguaje sin sesgo (gramatica-sesgo.md) [APA-117 a APA-131]

| ID | Regla | Sev. | Fix | Fuente |
|---|---|---|---|---|
| APA-117 | Tiempo verbal coherente por sección (pasado en procedimiento y resultados, presente en discusión y conclusiones) | menor | no | § 4.12 \| grammar/verb-tense |
| APA-118 | Voz activa predominante; pasiva solo cuando importa el receptor de la acción | menor | no | § 4.13 \| grammar/active-passive-voice |
| APA-119 | Primera persona "I"/"we" en lugar de "the author"; sin "we" editorial que no designe un grupo concreto (en español: salvo norma institucional impersonal) | menor | no | § 4.16 \| grammar/first-person-pronouns |
| APA-120 | Sin antropomorfismo ("the theory concludes", "rat couples") | menor | no | § 4.11 \| grammar/anthropomorphism |
| APA-121 | Sin "he" ni "she" como genéricos, ni "(s)he" o "s/he"; uso de "they" singular o reescritura (inglés) | mayor | no | § 4.18 \| grammar/singular-they |
| APA-122 | Sin "man"/"mankind" genéricos ni terminaciones "-man" en ocupaciones; sin "preferred pronouns" | mayor | no | § 5.5 \| bias-free-language/gender |
| APA-123 | Sin "males"/"females" como sustantivos; género y sexo no confundidos | menor | no | § 5.5 \| bias-free-language/gender |
| APA-124 | Sin adjetivos usados como sustantivos para personas ("the elderly", "the poor", "schizophrenics") ni etiquetas que reducen a la persona a su condición | mayor | no | § 5.2 \| bias-free-language/general-principles |
| APA-125 | Edad: rangos, media y mediana en el Método; "older adults" en lugar de "the elderly", "seniors" | mayor | no | § 5.3 \| bias-free-language/age |
| APA-126 | Discapacidad: sin términos condescendientes o negativos ("special needs", "wheelchair bound", "AIDS victim", "hearing-impaired"); lenguaje centrado en la persona o en la identidad según preferencia | mayor | no | § 5.4 \| bias-free-language/disability |
| APA-127 | Raza y etnia: nombres de grupos con mayúscula, sin guion, específicos; sin "Caucasian", "Oriental", "Afro-American", "Eskimo"; "minorities" solo como colectivo sin modificador (usar "people of color" o "racial/ethnic minorities") | mayor | no | § 5.7 \| bias-free-language/racial-ethnic-minorities |
| APA-128 | Comparaciones entre grupos con designaciones paralelas, sin presentar un grupo como norma ("normal") | menor | no | § 5.2, 5.7 \| bias-free-language/general-principles |
| APA-129 | Orientación sexual: sin "homosexual"/"homosexuality"; términos específicos | mayor | no | § 5.8 \| bias-free-language/sexual-orientation |
| APA-130 | Nivel socioeconómico: sin términos peyorativos ("the poor", "welfare mothers", "ghetto", "high-school dropouts"); sin "illegal immigrants" | mayor | no | § 5.9 \| bias-free-language/socioeconomic-status |
| APA-131 | Apóstrofo no forma plurales (cats, no cat's); posesivos correctos; sin contracciones ("it's") | menor | no | § 4.8, 4.18 \| grammar/plural-nouns, possessive-nouns |

## IA. IA generativa (ia-generativa.md) [APA-132 a APA-139]

| ID | Regla | Sev. | Fix | Fuente |
|---|---|---|---|---|
| APA-132 | El uso de IA en la redacción se revela (el post dice "normalmente será necesario") en el Método, la nota del autor o el texto, con cita de la herramienta o del chat; la cita en el cuerpo es necesaria aunque haya mención en la nota | crítica | no | blog/cite-generative-ai-references (Parte 1) |
| APA-133 | La IA no figura como autora del trabajo ni de la cita; el autor de la referencia es la empresa desarrolladora | crítica | no | references/examples/ai-references |
| APA-134 | Referencia de herramienta con empresa, año, nombre o modelo en cursiva, `[Large language model]` y URL | mayor | no | references/examples/ai-references |
| APA-135 | Referencia de chat con empresa, fecha completa, título del chat en cursiva y sentence case, `[Generative AI chat]`, herramienta o modelo y URL del chat | mayor | no | references/examples/ai-references |
| APA-136 | Sin número de versión por defecto (nombre del modelo o de la herramienta) | menor | sí | blog/cite-generative-ai-references |
| APA-137 | Los prompts se describen en el texto o en un apéndice, no en la referencia | menor | no | blog/cite-generative-ai-references |
| APA-138 | Las fuentes sugeridas por IA fueron verificadas: existen y los datos y DOI coinciden | crítica | no | blog/cite-generative-ai-references (el autor humano comprueba la exactitud de la salida); blog/how-to-cite-chatgpt (archivado 2023: ejemplo de DOI ajeno; es consejo, no regla) |
| APA-139 | Si el docente o la institución exige declaración de contribución de IA, está presente (no es requisito de APA Style) | mayor | no | blog/ai-contribution-statement |

## Reglas agregadas en la revisión cruzada [APA-140 a APA-145]

| ID | Regla | Sev. | Fix | Fuente |
|---|---|---|---|---|
| APA-140 | Metaanálisis: las referencias de estudios incluidos llevan asterisco inicial, integradas en la lista principal, con la frase "References marked with an asterisk indicate studies included in the meta-analysis." bajo el rótulo "References" (párrafo con sangría); las citas en el texto no llevan asterisco | menor | no | § 9.52 \| references/meta-analysis-references |
| APA-141 | Preprint: si existe versión final publicada se cita esa; el preprint se cita solo si fue el usado, con el archivo (PsyArXiv, PubMed Central) como fuente | mayor | no | § 10.8 \| references/examples/preprint-article-references |
| APA-142 | Fecha de recuperación ("Retrieved Month D, YYYY, from URL") solo en obras no archivadas diseñadas para cambiar (perfiles de redes, wikis sin enlace permanente, UpToDate, diccionarios en línea); ausente en las demás | menor | no | § 9.7-9.37 \| references/elements-list-entry |
| APA-143 | Fuente de aula, LMS o intranet: con referencia (nombre del sitio y URL) si el público destinatario tiene acceso; como comunicación personal si el trabajo es para publicación o un público sin acceso | mayor | no | § 8.8 \| citations/classroom-intranet-sources |
| APA-144 | Tabla de más de una página repite la fila de encabezados; tabla demasiado ancha en página horizontal | menor | sí | § 7.8-7.21 \| tables-figures/tables |
| APA-145 | Sin puntuación duplicada (`..` fuera de puntos suspensivos, `,,`, `;;`, `::`) ni espacios dobles dentro del párrafo (el doble espacio tras punto es APA-115). Petición del usuario, 18-nov-2026; corrección tipográfica general, no regla APA explícita | menor | sí | § 6.1 \| punctuation |
