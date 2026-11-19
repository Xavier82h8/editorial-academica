# Catálogo de reglas

<!-- Generado por scripts/catalogo.py; no editar a mano (python scripts/catalogo.py). -->

**323 reglas**: 86 con comprobación determinista (las emite un script), 237 que evalúa el agente (juicio), 32 que `corregir.py` corrige de forma automática.

| Familia | Reglas | Deterministas | De agente | Corregibles |
|---|---:|---:|---:|---:|
| APA | 145 | 42 | 103 | 26 |
| IEEE | 140 | 14 | 126 | 1 |
| CON | 20 | 12 | 8 | 0 |
| EST | 10 | 10 | 0 | 5 |
| EA | 1 | 1 | 0 | 0 |
| FUE | 6 | 6 | 0 | 0 |
| RED | 1 | 1 | 0 | 0 |

Columna **Evaluación**: `determinista` = el juez (script) emite el ID; `agente` = lo evalúa un agente con el checklist (se marca como juicio); `+ corregible` = `corregir.py` lo corrige (`corregir.REGLAS`). Una regla del checklist con «Fix: sí» pero sin script sigue siendo del agente.

## APA 7: formato, citas y referencias

Norma: Publication Manual 7.ª ed. (snapshot en `normas/VERSION`).

| ID | Severidad | Evaluación | Descripción | Fuente oficial |
|---|---|---|---|---|
| APA-001 | mayor | determinista + corregible | Márgenes de 1 in (2,54 cm) en los cuatro lados (tesis: salvo margen institucional) | § 2.22 \| paper-format/margins |
| APA-002 | mayor | determinista + corregible | La fuente es una de las permitidas con su tamaño (Aptos 12, Calibri 11, Arial 11, Lucida Sans Unicode 10, Times New Roman 12, Georgia 11, Computer Modern 10) o la predeterminada del procesador | § 2.19 \| paper-format/font |
| APA-003 | menor | determinista + corregible | Una sola fuente en todo el documento (excepciones: figuras 8-14 pt sans serif, código monoespaciado, notas al pie) | § 2.19 \| paper-format/font |
| APA-004 | mayor | determinista + corregible | Interlineado doble en texto, resumen, citas en bloque, números/títulos/notas de tablas y figuras, y lista de referencias | § 2.21 \| paper-format/line-spacing |
| APA-005 | menor | determinista + corregible | Sin espacio adicional antes o después de párrafos | § 2.21 \| paper-format/line-spacing |
| APA-006 | mayor | determinista + corregible | Texto alineado a la izquierda, margen derecho irregular; sin justificación completa | § 2.23 \| paper-format/paragraph-format |
| APA-007 | mayor | determinista + corregible | Primera línea de cada párrafo con sangría de 0,5 in hecha con tabulador o formato de párrafo, no con espacios | § 2.24 \| paper-format/paragraph-format |
| APA-008 | mayor | determinista + corregible | Número de página en la esquina superior derecha de todas las páginas, incluidas portada (lleva el 1), referencias y apéndices | § 2.18 \| paper-format/page-header |
| APA-009 | mayor | determinista | (P) Running head (título abreviado) en mayúsculas, máximo 50 caracteres con espacios y puntuación, alineado a la izquierda del encabezado, en todas las páginas incluida la portada; (E) solo si lo pide el docente o la institución | § 2.18 \| paper-format/page-header |
| APA-010 | menor | determinista | (P) El running head no lleva la etiqueta "Running head:" ni abreviaturas (se permite "&") | § 2.18 \| paper-format/page-header |
| APA-011 | mayor | agente | Orden de páginas: portada, resumen (si hay), texto, referencias, notas al pie, tablas, figuras, apéndices (tablas/figuras y notas pueden ir incrustadas) | § 2.17 \| paper-format/order-pages |
| APA-012 | menor | determinista + corregible | En general cada sección empieza en página nueva (resumen, referencias); cada apéndice siempre en página separada | § 2.17, 2.14 \| paper-format/order-pages, paper-format/appendices |
| APA-013 | mayor | determinista | Etiquetas de sección ("Abstract", "References") centradas y en negrita | § 2.23 \| paper-format/paragraph-format |
| APA-014 | mayor | agente | Cada apéndice en página propia con etiqueta "Appendix" (uno) o "Appendix A/B" (varios) y título en la línea siguiente, ambos centrados y en negrita | § 2.14 \| paper-format/appendices |
| APA-015 | mayor | agente | Cada apéndice se menciona en el texto, en el orden en que aparecen | § 2.14 \| paper-format/appendices |
| APA-016 | menor | agente | Comillas y apóstrofos tipográficos (curvos), no rectos | p. xviii (introducción) \| paper-format/accessibility/typography |
| APA-017 | mayor | agente | Existe portada con título, autores y afiliación (tesis: portada institucional) | § 2.3 \| paper-format/title-page |
| APA-018 | mayor | agente | Título centrado, en negrita, en title case (adaptación al español, convención no APA: capitalización de oración), 3-4 líneas bajo el borde superior | § 2.3 \| paper-format/title-page |
| APA-019 | menor | agente | Una línea en blanco a doble espacio entre título y autores | § 2.3 \| paper-format/title-page |
| APA-020 | mayor | agente | Autores centrados en línea propia; dos: "and"; tres o más: comas y "and" antes del último | § 2.3 \| paper-format/title-page |
| APA-021 | mayor | agente | Afiliación con departamento y universidad separados por coma, centrada en la línea siguiente a los autores | § 2.3 \| paper-format/title-page |
| APA-022 | mayor | determinista | (E) La portada incluye, centrados y en este orden tras la afiliación: curso (número, dos puntos, nombre), instructor y fecha de entrega | § 2.3 \| paper-format/title-page |
| APA-023 | mayor | agente | (P) Nota del autor en la mitad inferior de la portada con etiqueta "Author Note" centrada y en negrita y párrafos a la izquierda | § 2.3 \| paper-format/title-page |
| APA-024 | mayor | agente | Máximo cinco niveles; solo los necesarios, empezando por el 1; cada nivel subdivide al anterior sin saltar niveles | § 2.26 \| paper-format/headings |
| APA-025 | mayor | determinista + corregible | Nivel 1: centrado, negrita, title case | § 2.27 \| paper-format/headings |
| APA-026 | mayor | determinista + corregible | Nivel 2: a la izquierda, negrita, title case | § 2.27 \| paper-format/headings |
| APA-027 | mayor | determinista + corregible | Nivel 3: a la izquierda, negrita cursiva, title case | § 2.27 \| paper-format/headings |
| APA-028 | mayor | determinista + corregible | Nivel 4: con sangría, negrita, title case, termina en punto y el texto sigue en la misma línea | § 2.27 \| paper-format/headings |
| APA-029 | mayor | determinista + corregible | Nivel 5: con sangría, negrita cursiva, title case, termina en punto y el texto sigue en la misma línea | § 2.27 \| paper-format/headings |
| APA-030 | mayor | determinista + corregible | Encabezados sin numeración ni letras ("1.", "A.") | § 2.26 \| paper-format/headings |
| APA-031 | mayor | agente | El texto no empieza con un encabezado "Introduction" (en español "Introducción": extensión por convención, no regla APA) | § 2.26 \| paper-format/headings |
| APA-032 | menor | agente | Ninguna sección tiene un único subencabezado | § 2.26 \| paper-format/headings |
| APA-033 | menor | determinista | Encabezados a doble espacio y sin líneas en blanco antes o después | § 2.26 \| paper-format/headings |
| APA-034 | crítica | determinista | Cada cita en el texto tiene su entrada en la lista de referencias y cada entrada está citada (excepciones: comunicaciones personales, menciones generales de sitios y software común, epígrafes, participantes, metaanálisis) | § 2.12, 8.4 \| references/works-included |
| APA-035 | crítica | determinista | Apellidos y años de las citas coinciden con los de la lista | § 8.10 \| citations/basic-principles |
| APA-036 | mayor | determinista + corregible | Citas en formato autor-fecha: parentética `(Autor, año)`; narrativa `Autor (año)` | § 8.11 \| citations/basic-principles/parenthetical-versus-narrative |
| APA-037 | mayor | determinista + corregible | En parentética "&" entre autores, también en documentos en español (decisión del usuario, 18-nov-2026); en narrativa "and" ("y") | § 8.10 \| citations/basic-principles/author-date |
| APA-038 | mayor | determinista | Tres o más autores: primer autor + "et al." desde la primera cita (salvo desambiguación, APA-046) | § 8.10-8.36 \| citations/basic-principles/author-date |
| APA-039 | mayor | agente | Obra con uno o dos autores: se nombran todos en cada cita | § 8.10-8.36 \| citations/basic-principles/author-date |
| APA-040 | mayor | agente | Grupo autor con abreviatura: nombre completo con abreviatura la primera vez (corchetes en parentética, paréntesis con coma en narrativa) y solo abreviatura después | § 8.21 \| abbreviations/group-authors |
| APA-041 | mayor | agente | La cita lleva solo el año (no fecha completa); sin fecha "n.d." ("s.f."); aceptada sin publicar "in press" | § 8.10 \| citations/basic-principles/author-date |
| APA-042 | mayor | determinista | No se usa "ibid." ni solo el número de página: la cita se repite completa | § 8.10 \| citations/basic-principles/author-date |
| APA-043 | mayor | determinista + corregible | Varias obras en un paréntesis: orden alfabético separado por punto y coma | § 8.12 \| citations/basic-principles/multiple-works |
| APA-044 | mayor | agente | Obras con mismo autor y año: letras a, b, c tras el año (n.d.-a) en cita y lista | § 8.19 \| citations/basic-principles/same-year-author |
| APA-045 | mayor | agente | Primeros autores con mismo apellido e iniciales distintas: iniciales en todas las citas | § 8.20 \| citations/basic-principles/citing-authors-same-surname |
| APA-046 | menor | agente | Obras con 3+ autores que se acortan igual: se escriben apellidos hasta distinguirlas | § 8.18 \| citations/basic-principles/same-year-first-author |
| APA-047 | mayor | agente | Parte de una fuente con formato correcto: p., pp., para., Chapter, Table, Figure, marca de tiempo | § 8.13 \| citations/basic-principles/parts-source |
| APA-048 | mayor | agente | Toda cita textual lleva autor, año y página u otra ubicación | § 8.25 \| citations/quotations/page-numbers |
| APA-049 | mayor | agente | Citas de menos de 40 palabras van entre comillas dentro del texto; de 40 o más en bloque sin comillas | § 8.25 \| citations/quotations |
| APA-050 | mayor | agente | Cita en bloque sangrada 0,5 in, a doble espacio, sin punto tras el paréntesis de cita | § 8.27 \| citations/quotations |
| APA-051 | mayor | agente | Sin números de página: sección, párrafo o marca de tiempo; nunca ubicaciones de Kindle | § 8.28 \| citations/quotations/no-page-numbers |
| APA-052 | mayor | agente | Omisiones con puntos suspensivos, adiciones entre corchetes, énfasis con "[emphasis added]" | § 8.30-8.31 \| citations/quotations/changes |
| APA-053 | crítica | agente | La cita textual reproduce palabras, ortografía y puntuación del original; errores con "[sic]" | § 8.29 \| citations/quotations/errors |
| APA-054 | mayor | agente | Fuente secundaria: "as cited in"; solo la secundaria en la lista | § 8.6 \| citations/secondary-sources |
| APA-055 | mayor | agente | Comunicación personal: solo en el texto, con iniciales, apellido, "personal communication" y fecha; sin entrada en la lista (variante de conocimiento tradicional indígena no grabado: nombre completo y nación o grupo) | § 8.9 \| citations/personal-communications |
| APA-056 | mayor | agente | Citas de participantes de la propia investigación sin referencia ni comunicación personal, con aviso de que son participantes | § 8.36 \| citations/quoting-participants |
| APA-057 | crítica | agente | Hechos y cifras que no son de conocimiento común, paráfrasis e ideas ajenas tienen cita | § 8.1-8.3 \| citations/appropriate-citation, citations/basic-principles, citations/plagiarism |
| APA-058 | menor | agente | No hay sobrecitación: la misma cita no se repite en cada oración de un mismo párrafo con la misma fuente | § 8.1 \| citations/appropriate-citation |
| APA-059 | mayor | determinista + corregible | Lista rotulada "References" ("Reference" solo si hay una única entrada), centrada, negrita, en página nueva; no "Bibliography", "Works Cited" ni "Reference List" | § 2.12 \| paper-format/reference-list |
| APA-060 | mayor | determinista + corregible | Sangría francesa de 0,5 in, doble espacio y sin espacio extra entre entradas | § 9.43-9.49 \| paper-format/reference-list |
| APA-061 | mayor | determinista + corregible | Orden alfabético por la primera palabra de la entrada; sin autor: por título | § 9.43-9.49 \| paper-format/reference-list |
| APA-062 | mayor | agente | Cada entrada tiene autor, fecha, título y fuente | § 9.4-9.6 \| references/basic-principles |
| APA-063 | mayor | agente | Autores invertidos (apellido, iniciales con espacio entre iniciales); coma entre autores y "&" ("y", adaptación al español) antes del último | § 9.7-9.37 \| references/elements-list-entry |
| APA-064 | mayor | agente | De 2 a 20 autores se listan todos; con 21 o más: los 19 primeros, puntos suspensivos (sin "&") y el último | § 9.7-9.37 \| references/elements-list-entry |
| APA-065 | mayor | determinista + corregible | Grupo autor con nombre completo, sin abreviatura ni siglas entre paréntesis | § 9.11 \| references/elements-list-entry |
| APA-066 | mayor | agente | Fecha entre paréntesis seguida de punto, con año primero (año, mes día) | § 9.7-9.37 \| references/elements-list-entry |
| APA-067 | menor | agente | Sin fecha "(n.d.)" ("s.f."); aceptada sin publicar "(in press)"; no "in progress" | § 9.7-9.37 \| references/elements-list-entry |
| APA-068 | menor | agente | Sin autor: título en posición de autor; no "Anonymous" salvo que la obra esté firmada así | § 9.4 \| references/missing-information |
| APA-069 | mayor | agente | Título de artículo o capítulo en sentence case, sin cursiva ni comillas | § 9.7-9.37 \| references/elements-list-entry |
| APA-070 | mayor | agente | Título de obra independiente (libro, informe, página web, tesis) en cursiva y sentence case | § 9.7-9.37 \| references/elements-list-entry |
| APA-071 | mayor | agente | Descripción entre corchetes (mayúscula inicial, sin cursiva) en obras no tradicionales: software, datos, tesis, comunicados, videos, publicaciones de redes | § 9.21 \| references/elements-list-entry |
| APA-072 | mayor | determinista | Artículo de revista: revista y volumen en cursiva; número entre paréntesis sin cursiva; sin coma entre volumen y número | § 10.1 \| references/basic-principles, examples/journal-article-references |
| APA-073 | mayor | agente | Artículo de revista con número (issue) siempre; con páginas, o "Article" más número de artículo; si la revista no usa volumen, número o páginas, se omite el elemento ausente | § 10.1 \| references/examples/journal-article-references |
| APA-074 | menor | agente | Rangos de páginas con raya en (–) | § 10.1; § 8.25-8.27 \| references/examples/journal-article-references (raya en) |
| APA-075 | mayor | determinista | Punto después de cada elemento y ninguno después de DOI o URL | § 9.4-9.6 \| references/basic-principles |
| APA-076 | mayor | determinista + corregible | DOI como hipervínculo `https://doi.org/...` | § 9.34-9.36 \| references/dois-urls |
| APA-077 | mayor | determinista | Toda obra con DOI lo incluye | § 9.34-9.36 \| references/dois-urls |
| APA-078 | crítica | agente | Los DOI y URL de la lista resuelven y apuntan a la obra citada | § 9.34-9.36 \| references/dois-urls |
| APA-079 | mayor | determinista | Sin "Retrieved from"/"Accessed from" ("Recuperado de") antes de DOI o URL | § 9.34-9.36 \| references/dois-urls |
| APA-080 | menor | agente | Con DOI y URL se deja solo el DOI | § 9.34-9.36 \| references/dois-urls |
| APA-081 | mayor | agente | Sin nombre ni URL de bases de datos académicas comunes (salvo obras propietarias o de circulación limitada) | § 9.30 \| references/database-information |
| APA-082 | menor | agente | Sin ISBN, ISSN ni lugar de publicación en libros | § 9.34-9.36, 9.7-9.37 \| references/dois-urls (ISBN/ISSN), references/elements-list-entry (lugar) |
| APA-083 | mayor | agente | Libro: editorial al final, edición entre paréntesis tras el título sin cursiva | § 10.2 \| references/examples/book-references |
| APA-084 | mayor | agente | Capítulo de libro editado: "In" + editores (inicial primero, "(Eds.)") + título del libro en cursiva + páginas + editorial; no hay entradas para capítulos de libros de autor único | § 10.3 \| references/examples/edited-book-chapter-references |
| APA-085 | mayor | agente | Tesis: tipo de trabajo y universidad entre corchetes; si es publicada, base o repositorio como fuente | § 10.6 \| references/examples/published-dissertation-references |
| APA-086 | mayor | agente | Publicación en redes: autor con @usuario entre corchetes, primeras 20 palabras en cursiva, descripción entre corchetes, sitio y URL | § 10.15 \| references/examples/x-references |
| APA-087 | mayor | agente | Sin referencias de sitios web completos ni de comunicaciones personales | § 8.9 \| references/works-included, examples/whole-website-references |
| APA-088 | crítica | agente | [PLUGIN, no es regla APA] Entrada verificada contra metadatos de Crossref/OpenAlex (autores, año, título, DOI coinciden) | Regla del plugin; APA solo define los cuatro elementos (§ 9.4 \| references/basic-principles) |
| APA-089 | mayor | determinista | Número ("Table 1"/"Figure 1") en negrita sobre el título; numeración en orden de mención | § 7.8-7.36 \| tables-figures/tables, figures |
| APA-090 | mayor | agente | Título una línea doble bajo el número, en cursiva y title case | § 7.8-7.36 \| tables-figures/tables, figures |
| APA-091 | mayor | determinista | Toda tabla y figura se menciona en el texto por su número (la ubicación se define "tras su primera mención"). Regla por decisión del usuario (18-nov-2026): toda figura y tabla se menciona y explica en el texto | § 7.8-7.36 \| tables-figures/tables, figures |
| APA-092 | menor | agente | Tabla con encabezados de columna, incluido el de la columna izquierda, centrados y en sentence case | § 7.8-7.21 \| tables-figures/tables |
| APA-093 | mayor | determinista + corregible | Tabla con bordes horizontales mínimos; sin bordes verticales ni en cada celda | § 7.8-7.21 \| tables-figures/tables |
| APA-094 | menor | determinista | Notas con "Note." en cursiva; notas específicas con letras; probabilidad con asteriscos | § 7.8-7.21 \| tables-figures/sample-tables |
| APA-095 | crítica | agente | Tabla o figura reproducida o adaptada de otra obra con atribución de copyright en la nota | § 12.14-12.18 \| citations/plagiarism |
| APA-096 | menor | agente | Texto dentro de figuras en sans serif de 8 a 14 pt | § 2.19; § 7.22-7.36 \| paper-format/font, tables-figures/figures |
| APA-097 | mayor | agente | Figura con ejes rotulados, unidades de medida y elementos explicados; leyenda dentro de la figura | § 7.22-7.36 \| tables-figures/figures |
| APA-098 | menor | agente | Colocación: incrustada tras su primera mención (arriba o abajo de la página, con línea en blanco) o en páginas tras las referencias | § 2.17 \| paper-format/order-pages |
| APA-099 | mayor | agente | Colores con contraste suficiente; la información no depende solo del color | § 7.26 \| tables-figures/colors |
| APA-100 | mayor | agente | Imagen de stock o clip art: atribución y referencia según su licencia | § 12.14-12.18 \| references/examples/clip-art-references |
| APA-101 | mayor | agente | Abreviatura definida en su primer uso (excepto las de diccionario, de medida, de tiempo con valor, latinas y estadísticas comunes) | § 6.25 \| abbreviations/definition |
| APA-102 | menor | agente | Tras definirla se usa solo la abreviatura; se usa al menos tres veces (salvo estándar para término largo) | § 6.25 \| abbreviations/definition |
| APA-103 | menor | agente | Abreviaturas sin puntos (FBI, PhD) | cap. 6 \| abbreviations |
| APA-104 | menor | agente | Abreviaturas latinas (e.g., i.e., etc., cf., viz., vs.) solo en paréntesis; en la narración se escribe la traducción (excepciones: "v." en nombres de casos judiciales, "et al.") | § 6.29 \| abbreviations/latin |
| APA-105 | mayor | agente | Title case en encabezados, títulos de tablas y figuras, y títulos de periódicos; sentence case en títulos de la lista, encabezados de columna y notas | § 6.17 \| capitalization/title-case, sentence-case |
| APA-106 | menor | agente | Nombres propios con mayúscula; cargos, enfermedades, terapias, teorías y procedimientos estadísticos en minúscula (salvo nombres propios incluidos) | § 6.14-6.16 \| capitalization/proper-nouns, diseases-disorders-therapies |
| APA-107 | menor | agente | Cursiva en títulos de obras independientes y periódicos, y en términos clave solo en su primer uso | § 6.22 \| italics-quotations/italics |
| APA-108 | menor | agente | Símbolos estadísticos y anclajes de escala en cursiva | § 6.22 \| italics-quotations/italics |
| APA-109 | mayor | agente | Coma serial en series de tres o más elementos; punto y coma si algún elemento lleva comas (en español rige la RAE, ver mecanica.md §6) | § 6.3 \| punctuation/serial-comma |
| APA-110 | menor | agente | Listas con letras minúsculas entre paréntesis (a), (b), no números, dentro de una oración | § 6.50 \| lists/lettered |
| APA-111 | menor | agente | Viñetas: ítems que son oraciones empiezan con mayúscula y terminan con punto; ítems que son frases empiezan con minúscula y se puntúan de forma uniforme | § 6.52 \| lists/bulleted |
| APA-112 | mayor | agente | Números 0-9 en palabras y 10 o más en numerales (excepciones en APA-113 y APA-114) | § 6.32-6.33 \| numbers/numerals, words |
| APA-113 | mayor | agente | Numerales siempre en medidas, porcentajes, edades, fechas y tiempos, puntuaciones, decimales, razones y dinero exacto | § 6.32 \| numbers/numerals |
| APA-114 | menor | agente | Un número al inicio de oración, título o encabezado se escribe en palabras (preferible reformular la oración) | § 6.33 \| numbers/words |
| APA-115 | menor | determinista + corregible | Un espacio tras punto final (no dos) | § 6.1 \| punctuation/space-after-period |
| APA-116 | menor | agente | Ortografía y guiones consistentes con el diccionario (Merriam-Webster, APA Dictionary; en español RAE, adaptación no APA) | § 6.11 \| spelling-hyphenation/spelling |
| APA-117 | menor | agente | Tiempo verbal coherente por sección (pasado en procedimiento y resultados, presente en discusión y conclusiones) | § 4.12 \| grammar/verb-tense |
| APA-118 | menor | agente | Voz activa predominante; pasiva solo cuando importa el receptor de la acción | § 4.13 \| grammar/active-passive-voice |
| APA-119 | menor | agente | Primera persona "I"/"we" en lugar de "the author"; sin "we" editorial que no designe un grupo concreto (en español: salvo norma institucional impersonal) | § 4.16 \| grammar/first-person-pronouns |
| APA-120 | menor | agente | Sin antropomorfismo ("the theory concludes", "rat couples") | § 4.11 \| grammar/anthropomorphism |
| APA-121 | mayor | agente | Sin "he" ni "she" como genéricos, ni "(s)he" o "s/he"; uso de "they" singular o reescritura (inglés) | § 4.18 \| grammar/singular-they |
| APA-122 | mayor | agente | Sin "man"/"mankind" genéricos ni terminaciones "-man" en ocupaciones; sin "preferred pronouns" | § 5.5 \| bias-free-language/gender |
| APA-123 | menor | agente | Sin "males"/"females" como sustantivos; género y sexo no confundidos | § 5.5 \| bias-free-language/gender |
| APA-124 | mayor | agente | Sin adjetivos usados como sustantivos para personas ("the elderly", "the poor", "schizophrenics") ni etiquetas que reducen a la persona a su condición | § 5.2 \| bias-free-language/general-principles |
| APA-125 | mayor | agente | Edad: rangos, media y mediana en el Método; "older adults" en lugar de "the elderly", "seniors" | § 5.3 \| bias-free-language/age |
| APA-126 | mayor | agente | Discapacidad: sin términos condescendientes o negativos ("special needs", "wheelchair bound", "AIDS victim", "hearing-impaired"); lenguaje centrado en la persona o en la identidad según preferencia | § 5.4 \| bias-free-language/disability |
| APA-127 | mayor | agente | Raza y etnia: nombres de grupos con mayúscula, sin guion, específicos; sin "Caucasian", "Oriental", "Afro-American", "Eskimo"; "minorities" solo como colectivo sin modificador (usar "people of color" o "racial/ethnic minorities") | § 5.7 \| bias-free-language/racial-ethnic-minorities |
| APA-128 | menor | agente | Comparaciones entre grupos con designaciones paralelas, sin presentar un grupo como norma ("normal") | § 5.2, 5.7 \| bias-free-language/general-principles |
| APA-129 | mayor | agente | Orientación sexual: sin "homosexual"/"homosexuality"; términos específicos | § 5.8 \| bias-free-language/sexual-orientation |
| APA-130 | mayor | agente | Nivel socioeconómico: sin términos peyorativos ("the poor", "welfare mothers", "ghetto", "high-school dropouts"); sin "illegal immigrants" | § 5.9 \| bias-free-language/socioeconomic-status |
| APA-131 | menor | agente | Apóstrofo no forma plurales (cats, no cat's); posesivos correctos; sin contracciones ("it's") | § 4.8, 4.18 \| grammar/plural-nouns, possessive-nouns |
| APA-132 | crítica | agente | El uso de IA en la redacción se revela (el post dice "normalmente será necesario") en el Método, la nota del autor o el texto, con cita de la herramienta o del chat; la cita en el cuerpo es necesaria aunque haya mención en la nota | blog/cite-generative-ai-references (Parte 1) |
| APA-133 | crítica | agente | La IA no figura como autora del trabajo ni de la cita; el autor de la referencia es la empresa desarrolladora | references/examples/ai-references |
| APA-134 | mayor | agente | Referencia de herramienta con empresa, año, nombre o modelo en cursiva, `[Large language model]` y URL | references/examples/ai-references |
| APA-135 | mayor | agente | Referencia de chat con empresa, fecha completa, título del chat en cursiva y sentence case, `[Generative AI chat]`, herramienta o modelo y URL del chat | references/examples/ai-references |
| APA-136 | menor | agente | Sin número de versión por defecto (nombre del modelo o de la herramienta) | blog/cite-generative-ai-references |
| APA-137 | menor | agente | Los prompts se describen en el texto o en un apéndice, no en la referencia | blog/cite-generative-ai-references |
| APA-138 | crítica | agente | Las fuentes sugeridas por IA fueron verificadas: existen y los datos y DOI coinciden | blog/cite-generative-ai-references (el autor humano comprueba la exactitud de la salida); blog/how-to-cite-chatgpt (archivado 2023: ejemplo de DOI ajeno; es consejo, no regla) |
| APA-139 | mayor | agente | Si el docente o la institución exige declaración de contribución de IA, está presente (no es requisito de APA Style) | blog/ai-contribution-statement |
| APA-140 | menor | agente | Metaanálisis: las referencias de estudios incluidos llevan asterisco inicial, integradas en la lista principal, con la frase "References marked with an asterisk indicate studies included in the meta-analysis." bajo el rótulo… | § 9.52 \| references/meta-analysis-references |
| APA-141 | mayor | agente | Preprint: si existe versión final publicada se cita esa; el preprint se cita solo si fue el usado, con el archivo (PsyArXiv, PubMed Central) como fuente | § 10.8 \| references/examples/preprint-article-references |
| APA-142 | menor | agente | Fecha de recuperación ("Retrieved Month D, YYYY, from URL") solo en obras no archivadas diseñadas para cambiar (perfiles de redes, wikis sin enlace permanente, UpToDate, diccionarios en línea); ausente en las demás | § 9.7-9.37 \| references/elements-list-entry |
| APA-143 | mayor | agente | Fuente de aula, LMS o intranet: con referencia (nombre del sitio y URL) si el público destinatario tiene acceso; como comunicación personal si el trabajo es para publicación o un público sin acceso | § 8.8 \| citations/classroom-intranet-sources |
| APA-144 | menor | agente | Tabla de más de una página repite la fila de encabezados; tabla demasiado ancha en página horizontal | § 7.8-7.21 \| tables-figures/tables |
| APA-145 | menor | determinista + corregible | Sin puntuación duplicada (`..` fuera de puntos suspensivos, `,,`, `;;`, `::`) ni espacios dobles dentro del párrafo (el doble espacio tras punto es APA-115). Petición del usuario, 18-nov-2026; corrección tipográfica general, no… | § 6.1 \| punctuation |

## IEEE: citas, referencias, estructura, figuras, matemáticas

Norma: IEEE Reference Guide 2025 y Editorial Style Manual (`normas/VERSION`).

| ID | Severidad | Evaluación | Descripción | Fuente oficial |
|---|---|---|---|---|
| IEEE-001 | crítica | determinista | Las citas en texto son números entre corchetes en la línea (`[1]`); no hay citas autor-año como cita, ni superíndices, ni números entre paréntesis. Se admite nombrar al autor junto al número (`Brown [4]`) | [Ref Guide 2025 §I.A] |
| IEEE-002 | menor | determinista | El corchete va dentro de la puntuación: no aparece `.[n]` ni `,[n]` (correcto `... [n].` / `... [n],`) | [Ref Guide 2025 §I.A] |
| IEEE-003 | mayor | determinista | Cada número va en su propio corchete separado por coma (`[1], [2]`); no hay `[1, 2]` ni `[1,2]` (las únicas comas internas son de partes: `[3, Fig. 1]`). La guía solo muestra la forma `[1], [2]`; la prohibición de `[1, 2]` es… | [Ref Guide 2025 §I.A, ejemplos] |
| IEEE-004 | mayor | determinista | No hay rangos con en dash entre corchetes (`[1]–[4]`, `[1]-[4]`); los números se escriben todos (`[1], [2], [3], [4]`) | [Ref Guide 2025 §I.A] |
| IEEE-005 | menor | agente | No aparece "in reference [n]" como sustituto del número; se escribe `in [n]` | [SM p.14 §References] |
| IEEE-006 | menor | agente | Un autor nombrado antes del número ("Smith [1]") solo si su nombre es esencial para la oración; "In Smith [1]" se reduce a "in [1]" | [SM p.14 §References] |
| IEEE-007 | mayor | agente | Citas en texto de una referencia con 3 o más autores usan `et al.` (`Wood et al. [7]`); con 1 o 2 autores se nombran todos (`Brown and Jones [5]`) | [Ref Guide 2025 §I.A] |
| IEEE-008 | menor | agente | No hay años como identificador de cita (`[Smith 2019]`, `Smith (2019) [1]`) salvo que la fecha sea relevante para el tema | [SM p.14 §References] |
| IEEE-009 | mayor | agente | No hay "ibid.", "op. cit." en el texto ni en la lista; se cita de nuevo el número anterior (exige renumerar) | [Ref Guide 2025 §I.B] |
| IEEE-010 | mayor | agente | Las citas a una parte de una fuente usan `[n, parte]` (`[3, Fig. 1]`, `[3, pp. 5–10]`, `[3, eq. (2)]`); no hay "Fig. 2 of reference [1]" ni "equation (8) of reference [1]" | [Ref Guide 2025 §I.B]; [SM p.14 §References] |
| IEEE-011 | menor | agente | Abreviaturas de parte: `Thm.`, `Sect.`, `Ch.`, `pp.`, `eq.`, `Fig.`, `Appendix`, `Algorithm`, `Lemma` (Ref Guide 2025). `Th.` y `Sec.` (SM p.14, vestigio de la guía 2018) se aceptan sin reportar; solo se reporta mezclar ambas… | [Ref Guide 2025 §I.B] vs [SM p.14 §References] |
| IEEE-012 | crítica | determinista | Cada cita numérica del texto corresponde a una entrada existente de la lista (sin números sobrantes). Implícito en la numeración de la guía | [Ref Guide 2025 §I.A, §II] (implícito) |
| IEEE-013 | menor | determinista | Cada entrada de la lista se cita en el texto. La norma dice que citar es opcional ("need not be cited"); es política del plugin, reportar como observación | [CONV]; contraste [Ref Guide 2025 §I.A] |
| IEEE-014 | menor | determinista | Las referencias se numeran por orden de primera aparición en el texto (1, 2, 3 ...). Verificado: ninguna fuente oficial local (Ref Guide 2018/2023/2025, SM actual y 2024, Math guides) lo dice; solo exige orden numérico para las… | [CONV]; analogía [SM p.14 §Text Citation of Figures and Tables] |
| IEEE-015 | menor | agente | La lista tiene encabezado `REFERENCES` (en español `REFERENCIAS`), sin numeral romano ni letra | [SM p.12 §Text Section Headings] |
| IEEE-016 | menor | determinista | Cada entrada empieza con su número entre corchetes, a ras izquierdo en columna propia, colgando fuera del cuerpo de la referencia | [Ref Guide 2025 §II] |
| IEEE-017 | crítica | agente | La numeración de la lista es consecutiva 1..N, sin saltos ni números repetidos (implícito; renumerar exige corregir las citas) | [Ref Guide 2025 §II, §I.B NOTE] (implícito) |
| IEEE-018 | crítica | agente | Un número = una fuente: ninguna entrada reúne varias obras ni añade comentarios ("see also", "For example", notas) | [Ref Guide 2025 §II]; [SM p.14 §References] |
| IEEE-019 | mayor | agente | La misma obra no figura con dos números (una por página o parte citada) | [SM p.14 §References] |
| IEEE-020 | crítica | agente | Nombres de autor con inicial(es) ANTES del apellido y sin nombre completo (`J. K. Author`); ninguna entrada usa `Apellido, I.` | [Ref Guide 2025 §II] |
| IEEE-021 | mayor | agente | Publicaciones IEEE: se listan todos los autores hasta 6. En fuentes no IEEE se admite `et al.` si la fuente no da más nombres | [Ref Guide 2025 §II] |
| IEEE-022 | mayor | agente | Si la fuente tiene más de 6 autores se escribe solo el primero seguido de `et al.` | [Ref Guide 2025 §II] |
| IEEE-023 | mayor | agente | Antes del último autor va `and` (no `&`, no `y`), con coma seriada en 3 o más autores (`A, B, and C`); con 2 autores `A and B` | [Ref Guide 2025 §II, ejemplos] |
| IEEE-024 | menor | agente | Sufijos Jr., Sr., III sin coma previa (`W. P. Pratt Jr.`) | [Ref Guide 2025 §II] |
| IEEE-025 | menor | agente | Sin títulos ni afiliaciones junto a los autores (Dr., Prof., Ph.D.) | [Ref Guide 2025 §T Websites] |
| IEEE-026 | mayor | agente | El título de artículo, capítulo o paper va entre comillas (curvas, como en la guía) y la coma o el punto cierra dentro de ellas. Si el título termina en `?` la coma puede omitirse (`...difference?” CBS News`) | [Ref Guide 2025 §B, §J, §M, ejemplos] |
| IEEE-027 | menor | agente | En cursiva: título de libro, de revista (abreviado), de conferencia (tras `in Proc.`; no si es "presented at"), de blog, de fuente de noticias, de manual/handbook, de norma, de video y de software. Sin cursiva: artículo,… | [Ref Guide 2025 §II, versión HTML] |
| IEEE-028 | mayor | agente | Títulos de revista abreviados según `abreviaturas.md` o el CSV oficial; no aparecen nombres completos de revistas de varias palabras | [Ref Guide 2025 §IV.A, §IV.C]; [CSV abreviaturas-revistas] |
| IEEE-029 | menor | agente | Títulos de revista de una sola palabra no se abrevian (`Science`, `Nature`) | [Ref Guide 2025 §M Periodicals] |
| IEEE-030 | mayor | agente | Artículo de revista con el orden `vol. x, no. x, pp. xxx–xxx, Mon. year` (más `doi:` si hay) | [Ref Guide 2025 §M Periodicals] |
| IEEE-031 | menor | agente | `vol.`, `no.`, `pp.` (o `p.` si es una sola página) en minúscula con punto; páginas con en dash | [Ref Guide 2025 §M] |
| IEEE-032 | menor | agente | Mes abreviado en periódicos, conferencias, libros y similares: `Jan., Feb., Mar., Apr., May, Jun., Jul., Aug., Sep., Oct., Nov., Dec.` (formas de los ejemplos; la guía no da lista ni usa `Sept.`; `May` sin punto). Los ejemplos de… | [Ref Guide 2025 §II, §M, ejemplos] |
| IEEE-033 | menor | agente | Dos meses del mismo número separados por barra (`Jul./Aug. 2013`) | [Ref Guide 2025 §II] |
| IEEE-034 | mayor | agente | Toda referencia incluye al menos el año; sin fecha se escribe `(n.d.)` en el lugar de la fecha | [Ref Guide 2025 §II] |
| IEEE-035 | menor | agente | Se incluyen número y mes en artículos de IEEE Transactions cuando existen en IEEE Xplore (requiere consulta externa; no verificable solo con el texto) | [Ref Guide 2025 §II, §M] |
| IEEE-036 | menor | agente | Artículo con identificador usa `Art. no. xxx` en vez de páginas | [Ref Guide 2025 §M Article ID] |
| IEEE-037 | menor | determinista | DOI escrito `doi: 10.xxxx/...` (prefijo minúscula con dos puntos y espacio); no `DOI:` ni `https://doi.org/` salvo la variante "DOI resolver" (`doi: http://dx.doi.org/...`) | [Ref Guide 2025 §M Periodicals, §E Datasets] |
| IEEE-038 | menor | determinista | Las referencias que no terminan en URL terminan en punto, también las que terminan en DOI | [Ref Guide 2025 §II] |
| IEEE-039 | menor | agente | Las referencias que terminan en URL no llevan punto final | [Ref Guide 2025 §II, §III] |
| IEEE-040 | mayor | determinista | Con DOI o fecha de acceso Y URL, el DOI/fecha va primero, luego punto, luego `[Online]. Available: URL`; no se pone el DOI después de la URL (patrón 2018) | [Ref Guide 2025 §II, §III] |
| IEEE-041 | mayor | agente | Fuente en línea con `[Online]. Available: URL` (video: `[Online Video]. Available:`) | [Ref Guide 2025 §III, §K] |
| IEEE-042 | mayor | agente | Fecha de acceso con formato `Accessed: Mon. D, YYYY.` en sitios web, manuales en línea, libros en línea y videos. La guía no la exige en artículos con DOI; la sección III remite a la versión final del autor para su posición. Los… | [Ref Guide 2025 §III, §I, §K, §T] |
| IEEE-043 | mayor | agente | Sitio web: `J. Smith. “Page Title.” Website Title. Accessed: ... [Online]. Available: URL` (no la forma 2018 `(accessed ...)` entre paréntesis tras la URL). La guía escribe `[Online.]` con punto en esta sección: aceptar ambas… | [Ref Guide 2025 §T Websites] |
| IEEE-044 | mayor | agente | Libro: `A. Author, Title. City, State (solo EE. UU.), Country: Publisher, year.` con ciudad, país y editorial presentes (el ejemplo de libro extranjero omite el país) | [Ref Guide 2025 §B Book] |
| IEEE-045 | mayor | agente | Capítulo de libro: `“Chapter,” in Book, X. Editor, Ed., City: Publisher, year, ch. x, pp. xxx–xxx.` (nombre de editor solo si lo hay; `Eds.` si son varios) | [Ref Guide 2025 §B] |
| IEEE-046 | mayor | agente | Conferencia: `in Proc. Abbrev. Conf. Name, [City, State, Country,] year, pp. xxx–xxx.` con palabras abreviadas (`Proc.`, `Int.`, `Conf.`, `Symp.`, `Annu.`), ordinal en números (`4th`), casi sin artículos ni preposiciones ("of… | [Ref Guide 2025 §C] |
| IEEE-047 | menor | agente | Paper "presented at" incluye lugar, fechas y número de paper si existe | [Ref Guide 2025 §C Conference Paper] |
| IEEE-048 | mayor | agente | Tesis: `“Title,” M.S. thesis` o `Ph.D. dissertation`, `Abbrev. Dept., Abbrev. Univ., City, State/Country, year.`; "thesis"/"dissertation" según lo use el autor o la institución | [Ref Guide 2025 §Q] |
| IEEE-049 | mayor | agente | Reporte técnico: `“Title,” Institution, City, State, Country, Rep. xxx, Mon. year.` | [Ref Guide 2025 §N] |
| IEEE-050 | mayor | agente | Norma: `*Title of Standard*, Standard number, Corporate author, location, date.` | [Ref Guide 2025 §P] |
| IEEE-051 | mayor | agente | Patente con día del mes: `U.S. Patent x xxx xxx, Mon. D, year.` (la guía pide conservar o solicitar el día; algunos ejemplos suyos lo omiten) | [Ref Guide 2025 §L] |
| IEEE-052 | menor | agente | Artículo aceptado y no publicado: `to be published` (no "to appear in"); no aceptado: `submitted for publication`; sin enviar: `unpublished` | [Ref Guide 2025 §M, §S] |
| IEEE-053 | menor | agente | Artículo Early Access: `early access, Mon. D, year, doi: ...` y se cita la versión de la revista, no la de arXiv | [Ref Guide 2025 §M Early Access] |
| IEEE-054 | menor | agente | Preprint: `“Title,” year, arXiv:number.` | [Ref Guide 2025 §S Preprint arXiv] |
| IEEE-055 | mayor | agente | Software o dataset con autor(es), título, fecha o versión y distribuidor o repositorio; localizador (URL o DOI) cuando existe. La guía da un ejemplo de software sin URL (`MSDN Library Visual Studio 6.0. (2001). Microsoft.`) | [Ref Guide 2025 §O, §E] |
| IEEE-056 | menor | agente | Obras en otro idioma con `(in Language)` tras el título (artículo) o la editorial (libro) | [Ref Guide 2025 §B Foreign, §M Other Language] |
| IEEE-057 | crítica | agente | Ninguna entrada tiene datos inventados o incompletos sin marcar: autor, título, año y fuente presentes (la guía pide obtener la información relevante; la prohibición de inventar es política del plugin) | [Ref Guide 2025 §II]; [CONV] |
| IEEE-058 | mayor | agente | Cada DOI de la lista resuelve y coincide con los metadatos (autor, año, revista) en Crossref | [CONV] (política anti-alucinación del plugin) |
| IEEE-059 | mayor | agente | Orden de secciones: Abstract, Index Terms, [Nomenclature], Introduction, cuerpo, Conclusion, Appendix(es), [Conflict of Interest], Acknowledgment, References [ART] | [SM p.5 §II, p.13] |
| IEEE-060 | mayor | agente | Hay Abstract (un único párrafo) salvo editoriales y otras excepciones [ART] | [SM p.10 §Abstract] |
| IEEE-061 | mayor | agente | El Abstract tiene entre 150 y 250 palabras [ART] | [SM p.5 §II] |
| IEEE-062 | mayor | agente | El Abstract no contiene ecuaciones numeradas, citas numeradas ni notas al pie | [SM p.10 §Abstract] |
| IEEE-063 | mayor | agente | Hay Index Terms, en orden alfabético, primera palabra en mayúscula y el resto en minúscula salvo nombres propios, tras el Abstract [ART] | [SM p.10 §Index Terms] |
| IEEE-064 | menor | agente | Index Terms con formato `Index Terms—t1, t2, ...` (acrónimos con definición seguida de sigla entre paréntesis) | [SM p.10 §Index Terms] |
| IEEE-065 | mayor | agente | Acrónimos definidos la primera vez en el Abstract y de nuevo en el cuerpo (palabra completa + sigla entre paréntesis), salvo los de Nomenclature | [SM p.21 §Acronyms] |
| IEEE-066 | mayor | agente | Encabezados primarios en mayúsculas con numeral romano (`I. INTRODUCTION`) si se enumeran | [SM p.11 §Text Section Headings] |
| IEEE-067 | menor | agente | Encabezados secundarios `A. Title` (letra mayúscula + punto), cursiva | [SM p.11] |
| IEEE-068 | menor | agente | Encabezados terciarios `1) Title:` en cursiva, corridos con el texto y terminados en dos puntos | [SM p.11; SM 2024 p.11] |
| IEEE-069 | mayor | agente | Los niveles de encabezado no se saltan y la enumeración es consistente en todo el documento (la norma solo dice que enumerar es deseable, no obligatorio) | [CONV]; contexto [SM p.11] |
| IEEE-070 | mayor | agente | `REFERENCES` y `ACKNOWLEDGMENT` sin enumerar aunque los demás encabezados sí | [SM p.12] |
| IEEE-071 | menor | agente | Introduction, Conclusion y Acknowledgment en singular; `Acknowledgment` sin "e" entre g y m [EN] | [SM p.11, p.13] |
| IEEE-072 | menor | agente | Referencias internas a secciones: `Section II`, `Section II-A`, `Section II-A1` (mayúscula, sin "Subsection", sin punto) [EN] | [SM p.12] |
| IEEE-073 | menor | agente | Apéndice único sin numerar; varios con `APPENDIX I` o `APPENDIX A`; plural `Appendixes` | [SM p.12-13] |
| IEEE-074 | menor | agente | Teoremas, lemas y pruebas: teorema como encabezado terciario sin número arábigo y prueba como cuaternario | [SM p.12]; [Math Guide 2023 §E] |
| IEEE-075 | menor | agente | Título en capitalización IEEE: artículos, conjunciones coordinantes y preposiciones cortas en minúscula salvo inicial/final; preposiciones de más de 3 letras en mayúscula [EN] | [SM p.5 §Title] |
| IEEE-076 | menor | agente | El título no contiene ecuaciones detalladas ni abreviaturas en minúscula (salvo unidades y acrónimos), que deben ir en mayúscula | [SM p.5 §Title] |
| IEEE-077 | menor | agente | Acknowledgment en tercera persona, sin Mr./Mrs./Miss y sin notas personales | [SM p.13 §Acknowledgment] |
| IEEE-078 | menor | agente | Apoyo financiero declarado en la primera nota al pie, no en Acknowledgment (salvo algunas Transactions) [ART] | [SM p.7, p.13] |
| IEEE-079 | mayor | agente | Uso de IA generativa (texto, figuras, imágenes, código) declarado en Acknowledgment con sistema, secciones y nivel de uso. Edición y gramática quedan fuera de la política (divulgación solo recomendada) | [SM p.13 §Acknowledgment] |
| IEEE-080 | menor | agente | Conflict of Interest, si existe, en sección propia antes de Acknowledgment | [SM p.13 §Conflict of Interest] |
| IEEE-081 | menor | agente | Primera nota al pie sin numerar, sin asteriscos ni daggers; las demás numeradas consecutivamente con superíndice tras la puntuación (por lo general antes de guion, dos puntos y punto y coma) [ART] | [SM p.6, p.17] |
| IEEE-082 | menor | agente | Listas con etiquetas `1)`, `2)`, luego `a)`, luego `i)` (paréntesis de cierre único) | [SM p.17 §Lists in Text] |
| IEEE-083 | menor | agente | Listas en línea: introducidas por dos puntos, ítems separados por `;` y paralelos | [SM p.17] |
| IEEE-084 | mayor | agente | En texto, las figuras se citan `Fig. N` (también al inicio de oración, también `Fig. 1(a)`); no `Figure N` | [SM p.14 §Text Citation of Figures and Tables] |
| IEEE-085 | mayor | agente | Pie de figura con formato `Fig. N.` + espacio em + texto, primera palabra en mayúscula; va debajo de la figura (explícito solo para figuras apaisadas; implícito en general) | [SM p.14-15] |
| IEEE-086 | menor | agente | El pie de figura o de tabla no empieza con A, An ni The ("in general") | [SM p.14] |
| IEEE-087 | menor | agente | Subpartes `(a)`, `(b)` aparecen en el pie antes de su descripción y con estilo consistente | [SM p.14] |
| IEEE-088 | menor | agente | Las notas de figura van dentro del pie | [SM p.14] |
| IEEE-089 | mayor | agente | Tablas rotuladas `TABLE` + numeral romano, centrado encima de la tabla [EN] (en español `TABLA I`, ver adaptación) | [SM p.15 §Tables] |
| IEEE-090 | menor | agente | La descripción de la tabla va bajo el rótulo y no termina en punto | [SM p.15] |
| IEEE-091 | mayor | agente | Numeración de figuras y tablas consecutiva, sin saltos ni repetidos, incluyendo apéndices (renumerar exige corregir las citas) | [SM p.13 §Appendix] |
| IEEE-092 | mayor | agente | Las primeras citas de figuras y de tablas aparecen en orden numérico | [SM p.14] |
| IEEE-093 | mayor | determinista | Toda figura y tabla se cita en el texto (implícito en la regla de colocación cerca de la primera mención). Regla por decisión del usuario (18-nov-2026) | [CONV]; contexto [SM p.25 §F.1] |
| IEEE-094 | menor | agente | Cada figura o tabla se ubica cerca de su primera mención, preferiblemente después, y arriba de la columna/página | [SM p.25 §F.1] |
| IEEE-095 | mayor | agente | Gráfico reutilizado de una publicación IEEE: número(s) de referencia al final del pie. De otros editores: permiso previo y su leyenda al final del pie | [SM p.15 §Obtaining permission] |
| IEEE-096 | mayor | agente | Ecuaciones numeradas consecutivamente, número a ras derecho en la línea de la última línea, sin repetidos ni faltantes (renumerar exige corregir las citas) | [SM p.25 §Equation Numbers]; [Math Guide 2023 §F] |
| IEEE-097 | menor | agente | El estilo del número es consistente (`(1)`, `(1a)`, o por sección `(1.1)`); sin mezclar `(1-a)` con `(1a)`. El SM acepta `(1a)`, `(1.1)`, `(1-1)` si son consistentes; la Math Guide prefiere `(1a)` a `(1-a)` | [Math Guide 2023 §F]; [SM p.13 §Text Equations] |
| IEEE-098 | menor | agente | En texto la ecuación se cita como `(n)`; `Equation` se escribe completo solo al inicio de oración (la norma no da `Eq.` abreviado; en citas de parte sí: `[3, eq. (2)]`) | [SM p.24 §Math 14] |
| IEEE-099 | menor | agente | No hay paréntesis dobles en texto (`(see (10))`); se usa `[see (10)]` | [SM p.26 §III.A 8] |
| IEEE-100 | mayor | agente | Las variables van en cursiva y coinciden en texto y en fórmulas | [SM p.24 §Math 1]; [SM p.25 §Displayed Equations]; [Math LaTeX p.2] |
| IEEE-101 | mayor | agente | Funciones y operadores (sin, cos, log, ln, exp, max, min, lim, det, arg, Re, Im) en redonda; en LaTeX con `\sin`, `\max`, `\text{arg min}` | [Math Guide 2023 §I]; [Math LaTeX p.2-3, p.9-11] |
| IEEE-102 | menor | agente | Vectores en negrita (SM: "usually boldface italic"; Math Guide: "usually ... if distinguished by the author"; Math LaTeX: "always in bold") y de forma consistente | [Math LaTeX p.2]; [Math Guide 2023 §G]; [SM p.24 §Math 1] |
| IEEE-103 | menor | agente | Acrónimos dentro de ecuaciones (MSE, RMS, NCC) en redonda (`\text{}`), igual que en el texto | [Math LaTeX p.13-16]; [SM p.25 §Displayed Equations] |
| IEEE-104 | menor | agente | Unidades y abreviaturas de palabras en sub/superíndices en redonda; un subíndice de una sola letra puede ir en cursiva si evita inconsistencias | [SM p.25 §Displayed Equations] |
| IEEE-105 | menor | agente | La ecuación que cierra la oración termina en punto; la puntuación de entrada solo si el texto previo es oración completa; la coma final se elimina salvo que sea crítica | [SM p.24 §Use of Periods and Commas]; [Math Guide 2023 §A] |
| IEEE-106 | menor | agente | Puntos suspensivos matemáticos: tres puntos, en la línea base entre comas (`x1, x2, …, xn`) o centrados con operadores | [SM p.24 §Ellipses]; [Math Guide 2023 §A] |
| IEEE-107 | mayor | agente | En LaTeX no se usa `$$ ... $$` ni `eqnarray`; se usa `equation`, `equation*`, `align` o `\[ \]` | [Math LaTeX p.4] |
| IEEE-108 | menor | agente | Definiciones por casos con `cases` (no `array` con `\left\lbrace`) y palabras con `\text{}` | [Math LaTeX p.5-8] |
| IEEE-109 | menor | agente | Delimitadores que envuelven fracciones o raíces usan `\left ... \right` | [Math LaTeX p.16-18] |
| IEEE-110 | menor | agente | Límites de sumas/integrales arriba y abajo en display (sin `\nolimits`) y al costado en línea | [Math LaTeX p.11-12]; [Math Guide 2023 §B Rule 3] |
| IEEE-111 | menor | agente | Ordinales matemáticos `zeroth, first, nth, (k + 1)th`, no `1st` ni `(k + 1)st` | [SM p.24 §Math 13] |
| IEEE-112 | menor | agente | Fracciones en línea con barra (`(c-d)/(k+4)`), no apiladas. Conflicto: la Math Guide lo manda ("should not appear stacked"); el SM lo permite como opcional ("not a necessity") | [Math Guide 2023 §B Rule 2]; [SM p.24 §Math 9] |
| IEEE-113 | menor | agente | Número y unidad separados por espacio normal (`3.05 mm`, `2 A`), sin espacio fino y sin pegarlos | [SM p.24 §Math 6] |
| IEEE-114 | mayor | agente | Unidades con abreviatura estándar (A, V, W, Hz, dB, µm, b/s); no `amp`, `cps`, `c/s`, `db`, `micron`. `micron`, `cps` y `µ` están en SM Math 8; `amp`, `db` y `b/s` en el Apéndice C del PDF 2024 | [SM p.24 §Math 8]; [SM 2024 App. C p.35-42] |
| IEEE-115 | menor | agente | Rangos con unidad una sola vez (`40–50 mm`) salvo unidades distintas (`50 inches to 7 feet`) | [SM p.24 §Ranges With Units] |
| IEEE-116 | menor | agente | Unidad como adjetivo compuesto con guion solo si hace falta (`10-kV voltage`); sin guion si no es adjetivo (`a line 4 in long`) | [SM p.24 §Math 5] |
| IEEE-117 | menor | agente | Numerales con unidades; sin unidades se deletrean 1 a 10 y se usan numerales desde 11, salvo inicio de oración | [SM p.24 §Math 12] |
| IEEE-118 | menor | agente | Números de 5 dígitos o más con espacio fino, sin coma (`62 000`, pero `4000`) | [SM p.24 §Math 7] |
| IEEE-119 | mayor | determinista | Decimales con cero inicial (`0.25`) y sin ceros finales innecesarios. Conflicto en el SM: Math 3 dice "siempre" cero inicial; §Percentages and Decimals dice "si hace falta para claridad" (`.25`); se exige siempre el cero (Math 3;… | [SM p.24 §Math 3]; [SM p.24 §Percentages and Decimals] |
| IEEE-120 | menor | agente | Porcentajes con número y `%`; el símbolo se repite en rangos (`20%-30%`; el SM lo escribe con guion corto en ese ejemplo) | [SM p.24 §Percentages and Decimals] |
| IEEE-121 | menor | agente | Sumas de dinero con `$`, no "dollars" [EN] | [SM p.25 §Math 15] |
| IEEE-122 | menor | agente | En dash en rangos de páginas, años y valores; tras "from" se usa "to", no en dash | [SM p.22 §The En or Em Dash] |
| IEEE-123 | menor | agente | Plurales de unidades con "s" (`3 bits/s`); plural de años y acrónimos sin apóstrofo (`1990s`, `FETs`) [EN] | [SM p.22 §Plurals]; [SM p.21 §Acronyms]; [SM p.26 §III.A 9] |
| IEEE-124 | menor | agente | Sin contracciones en texto técnico (`do not`, `cannot`; se permiten `don't care`, `best-case`, `worst-case`) [EN] | [SM p.23 §Contractions] |
| IEEE-125 | menor | agente | Fechas en el cuerpo en formato internacional con mes completo (`4 June 2002`); no aplica a la lista de referencias [EN] | [SM p.23 §Dates] |
| IEEE-126 | menor | agente | Coma antes de la conjunción final en series de tres o más [EN] | [SM p.26 §III.A 2] |
| IEEE-127 | menor | agente | La puntuación va dentro de las comillas salvo dos puntos y punto y coma; comillas simples para cita dentro de cita [EN] | [SM p.26 §III.A 6] |
| IEEE-128 | menor | agente | Ortografía americana (`behavior`, `center`, `polarization`) [EN] | [SM p.22 §Spelling] |
| IEEE-129 | menor | agente | Sin símbolos ™ ni ® en el texto corrido | [SM p.22 §Trademarks] |
| IEEE-130 | menor | agente | Lenguaje inclusivo: sin términos de la Guía (blacklist, able-bodied, A.D./B.C., caretaker, Caucasian). El export no conserva cuáles están resaltados como "evitar siempre"; el reemplazo requiere criterio | [SM p.17 §Inclusive Language]; [SM 2024 App. E] |
| IEEE-131 | menor | agente | Encabezados cuaternarios: como los terciarios (cursiva, corridos, dos puntos finales) pero con letra minúscula + `)` como etiqueta y solo la primera letra del título en mayúscula. El ejemplo del PDF 2024 muestra `1a)` | [SM p.11; SM 2024 p.11] |
| IEEE-132 | menor | agente | Nombres de función: `tan` (no tg), `cot` (no ctg ni ctn), `csc` (no cosec), `Pr` (no Prob.) | [Math Guide 2023 §I, §L] |
| IEEE-133 | mayor | agente | No se usa la imagen "Lena" (no se aceptan artículos con ella desde el 1 abr 2024) [ART] | [SM p.14 §Use of the Lena Image] |
| IEEE-134 | menor | agente | Espacio fino a ambos lados de funciones y diferenciales en redonda (`sin t`, no `sint`), salvo junto a un verbo u operador | [Math Guide 2023 §G] |
| IEEE-135 | menor | agente | Blog o noticia en línea: `J. K. Author, “Title,” *Source*, Mon. D, year. [Online]. Available: URL` (noticia impresa: sin la parte `[Online]`) | [Ref Guide 2025 §A, §J] |
| IEEE-136 | menor | agente | Referencia no publicada: `J. K. Author, private communication, Mon. year.` o `J. K. Author, “Title,” unpublished.` | [Ref Guide 2025 §S] |
| IEEE-137 | menor | agente | Manual o handbook impreso: `*Name*, x ed., Abbrev. Co., City, State, Country, year, pp. xxx–xxx.`; en línea: `J. K. Author (or Co.). *Name*, x ed. (year). Accessed: Date. [Online]. Available: URL` | [Ref Guide 2025 §F, §I] |
| IEEE-138 | menor | agente | Dataset: `Author, Date, “Title of Dataset,” Source, doi: xxx.` o `..., Source. [Online]. Available: URL` | [Ref Guide 2025 §E] |
| IEEE-139 | menor | agente | Artículo indefinido según el sonido de la sigla (`an FCC regulation`, `a BRI`) [EN] | [SM p.21 §Acronyms] |
| IEEE-140 | menor | determinista + corregible | Sin puntuación duplicada (`..` fuera de puntos suspensivos, `,,`, `;;`, `::`) ni espacios dobles dentro del párrafo. Petición del usuario, 18-nov-2026; corrección tipográfica general | [decisión del usuario] |

## CON: congruencia interna

Sin norma oficial: práctica editorial. Las deterministas las emite `congruencia.py`; las demás, el agente `revisor-congruencia`.

| ID | Severidad | Evaluación | Descripción | Fuente oficial |
|---|---|---|---|---|
| CON-001 | crítica | determinista | Tamaño de muestra distinto entre Resumen / Método / Resultados / Discusión / Conclusiones | Práctica editorial del plugin |
| CON-002 | mayor | determinista | Porcentajes de una misma distribución que suman más de 100.5 | Práctica editorial del plugin |
| CON-003 | mayor | determinista | Sigla definida más de una vez | Práctica editorial del plugin |
| CON-004 | menor | determinista | Sigla usada antes de su definición | Práctica editorial del plugin |
| CON-005 | mayor | determinista | Referencia cruzada rota (Tabla/Figura/Apéndice sin rótulo ni encabezado) | Práctica editorial del plugin |
| CON-006 | mayor | determinista | Promesa incumplida («en la sección de X» sin encabezado X) | Práctica editorial del plugin |
| CON-007 | mayor | determinista | Lenguaje causal en Discusión/Conclusiones con diseño no experimental | Práctica editorial del plugin |
| CON-008 | menor | determinista | El texto repite la tabla. Un párrafo que menciona «Tabla N» (o está entre los 3 que siguen a la tabla y su nota) trae >= 4 cifras, autores o siglas de esa tabla, y ellos son >= 50 % de las cifras y nombres del párrafo. Solo .docx… | Práctica editorial del plugin |
| CON-009 | menor | determinista | Redundancia. Oraciones (>= 12 palabras) casi duplicadas en párrafos distintos: shingles de 5 palabras normalizadas, Jaccard >= 0.6 (>= 0.85 si una está en el resumen). Excluye citas textuales, rótulos, notas, celdas, referencias | Práctica editorial del plugin |
| CON-010 | mayor | agente | Objetivo sin método | Práctica editorial del plugin |
| CON-011 | mayor | agente | Objetivo sin resultado | Práctica editorial del plugin |
| CON-012 | mayor | agente | Objetivo sin conclusión | Práctica editorial del plugin |
| CON-013 | crítica | agente | Conclusión sin resultado que la respalde (afirma algo que los resultados no muestran) | Práctica editorial del plugin |
| CON-014 | mayor | agente | El resumen no refleja el documento (otro objetivo, otro n, resultado que no aparece) | Práctica editorial del plugin |
| CON-015 | mayor | agente | Alcance excedido (generaliza a otra población, o «demuestra» con un diseño que solo permite asociar), si el determinista no lo marcó ya como CON-007 | Práctica editorial del plugin |
| CON-016 | menor | agente | Un concepto con dos nombres distintos sin aclararlo (inconsistencia terminológica) | Práctica editorial del plugin |
| CON-017 | menor | agente | Tiempo verbal incoherente en Método/Resultados (pasado) frente a Conclusiones | Práctica editorial del plugin |
| CON-018 | menor | determinista | Tras definir una sigla, la forma completa reaparece >= 2 veces sin la sigla al lado (APA 6.25: tras definirla, usar solo la abreviatura). Excluye encabezados, tablas, referencias y el resumen (APA: definirla en el resumen y en el… | APA 6.25 |
| CON-019 | mayor | determinista | Numeración de tablas, figuras y apéndices: huecos (Tabla 1, 2, 4), rótulos duplicados o primera mención fuera de orden (Tabla 3 antes que Tabla 2). APA cap. 7 (tablas/figuras en orden de mención) y 2.14 (apéndices en orden) | Práctica editorial del plugin |
| CON-020 | mayor | determinista | Objetivo o pregunta sin rastro: ningún término clave del objetivo (bajo un encabezado «Objetivos»/«Preguntas de investigación») aparece en método, resultados, discusión ni conclusiones (ni cronograma/plan de análisis). Práctica… | Práctica editorial del plugin |

## EST: estructura por género y maquetación

EST-001..003: `estructura.py` con `estructuras/<género>.yaml`; EST-010..016: `maquetacion.py` (.docx).

| ID | Severidad | Evaluación | Descripción | Fuente oficial |
|---|---|---|---|---|
| EST-001 | mayor | determinista | Sección obligatoria ausente | estructuras/<género>.yaml (Práctica editorial del plugin) |
| EST-002 | menor | determinista | Secciones obligatorias fuera del orden del género | estructuras/<género>.yaml (Práctica editorial del plugin) |
| EST-003 | menor | determinista | Extensión de una sección muy lejos de la orientativa (< 1/2 o > 2 veces), solo en documentos de 800+ palabras | estructuras/<género>.yaml (Práctica editorial del plugin) |
| EST-010 | mayor | determinista + corregible | Campo PAGE en el encabezado y también en el pie de la misma sección | APA § 2.18 (IEEE no define la numeración) |
| EST-011 | menor | determinista + corregible | «Página X de Y» / NUMPAGES en encabezado o pie | APA § 2.18 |
| EST-012 | menor | determinista + corregible | Tabla o figura que puede partirse (rótulo/título sin keep_with_next, imagen separada de su rótulo o nota, tabla corta con filas sin cantSplit) | Práctica editorial del plugin (APA cap. 7, tablas y figuras) |
| EST-013 | menor | determinista + corregible | Tabla de más de 20 filas sin fila de encabezados repetida (tblHeader) | Práctica editorial del plugin (APA cap. 7) |
| EST-014 | menor | determinista + corregible | Encabezado pegado al final de una tabla, imagen o nota (sin espacio antes ni línea en blanco) | Práctica editorial del plugin (APA 2.21) |
| EST-015 | menor | determinista | Nota con «Fuente:», remisión a una sección, «Elaboración propia a partir de las fuentes citadas» sin citar, o «Tomado/Adaptado de» sin título entre comillas | APA cap. 7 (notas de tablas y figuras) |
| EST-016 | menor | determinista | Numeración de la portada contraria a la preferencia (`portada_numero: si\|no` de .editorial.yaml; si no, la del perfil: APA §2.18 pide número —el 1— en la portada; IEEE no define) | APA § 2.18 (IEEE no define la portada) |

## EA: entrega

Reglas de la entrega.

| ID | Severidad | Evaluación | Descripción | Fuente oficial |
|---|---|---|---|---|
| EA-001 | crítica | determinista | Marcador del redactor (`[[FALTA FUENTE: …]]`, `[[TODO]]`, `[[PENDIENTE]]`) que llega a la entrega | Práctica editorial del plugin (scripts/auditar.py) |

## FUE: verificación de fuentes (dimensión «Fuentes» de `/puntuar`)

V1 existencia, V2 metadatos, V3 integridad, V4 calidad, V5 sustento.

| ID | Severidad | Evaluación | Descripción | Fuente oficial |
|---|---|---|---|---|
| FUE-000 | crítica | determinista | El documento no tiene referencias verificables (dimensión «Fuentes» a cero) | Práctica editorial del plugin (scripts/puntuar.py) |
| FUE-URL | mayor | determinista | Fuente sin DOI cuya URL no responde (V1) | Práctica editorial del plugin (V1) |
| FUE-V123 | crítica | determinista | Fuente con DOI inexistente, metadatos que no coinciden o retractada (V1-V3) | Práctica editorial del plugin (V1-V3) |
| FUE-V3N | menor | determinista | Fuentes con DOI que no se pudieron comprobar por fallo de red (no verificado, nunca «ok») | Práctica editorial del plugin (V1/V3) |
| FUE-V4 | menor | determinista | Referencias sin enlace comprobable (ni DOI ni URL que responda) (V4) | Práctica editorial del plugin (V4) |
| FUE-V5 | mayor | determinista | Afirmación citada que la fuente no respalda o contradice según su resumen (V5) | Práctica editorial del plugin (V5) |

## RED: redacción (dimensión «Redacción» de `/puntuar`)

Heurísticas de claridad.

| ID | Severidad | Evaluación | Descripción | Fuente oficial |
|---|---|---|---|---|
| RED-001 | menor | determinista | Oración de más de 40 palabras en la dimensión «Redacción» | Práctica editorial del plugin (scripts/puntuar.py) |
