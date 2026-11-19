# IEEE: checklist de auditoría (IDs IEEE-001 a IEEE-140)

Uso: el juez evalúa cada regla como cumple / no cumple / no aplica, y reporta `ID · ubicación · qué está mal · corrección · fuente`. Reglas binarias y comprobables en el texto del documento. Severidad: crítica = invalida la citación o el formato base; mayor = viola regla explícita de IEEE; menor = detalle de mecánica. Las reglas [CONV] llevan severidad propia del plugin (no de IEEE); IEEE-058 (integridad de fuentes) es la única [CONV] con severidad mayor.
Fix auto = una corrección mecánica es segura: cambio local, sin decidir contenido y sin renumerar ni tocar otras partes del documento. Si exige renumerar (citas, figuras, ecuaciones) o elegir, es "no". Marcadores de ámbito: [EN] solo aplica a texto en inglés; [ART] solo si el documento es un artículo IEEE (en tesis o informe con maquetación IEEE aplicar solo si el perfil lo pide); [CONV] regla de convención del plugin, no textual en las normas.
Fuentes: `Ref Guide 2025` = Reference Guide V 3.28.2025; `SM` = Style Manual actual (páginas de su índice); `SM 2024` = PDF 2024; `Math Guide 2023`; `Math LaTeX` = guía LaTeX secundaria (páginas numeradas por su encabezado). Detalle de cada regla en los demás archivos de `references/`.
Si Ref Guide 2018 y 2025 difieren, vale 2025 (ver `referencias-principios.md` §6). Si Ref Guide 2025 y SM difieren en notación de referencias, vale la Ref Guide (más específica y más nueva; el SM conserva la notación 2018).
Rangos: CIT 001-014; REF 015-058 y 135-138; EST 059-083 y 131; FIG 084-095 y 133; MAT 096-112, 132 y 134; MEC 113-130 y 139.

## CIT: citas en el texto

| ID | Regla verificable (binaria, comprobable en el documento) | Severidad | Fix auto | Fuente |
|---|---|---|---|---|
| IEEE-001 | Las citas en texto son números entre corchetes en la línea (`[1]`); no hay citas autor-año como cita, ni superíndices, ni números entre paréntesis. Se admite nombrar al autor junto al número (`Brown [4]`) | crítica | no | [Ref Guide 2025 §I.A] |
| IEEE-002 | El corchete va dentro de la puntuación: no aparece `.[n]` ni `,[n]` (correcto `... [n].` / `... [n],`) | menor | sí | [Ref Guide 2025 §I.A] |
| IEEE-003 | Cada número va en su propio corchete separado por coma (`[1], [2]`); no hay `[1, 2]` ni `[1,2]` (las únicas comas internas son de partes: `[3, Fig. 1]`). La guía solo muestra la forma `[1], [2]`; la prohibición de `[1, 2]` es implícita | mayor | sí | [Ref Guide 2025 §I.A, ejemplos] |
| IEEE-004 | No hay rangos con en dash entre corchetes (`[1]–[4]`, `[1]-[4]`); los números se escriben todos (`[1], [2], [3], [4]`) | mayor | sí | [Ref Guide 2025 §I.A] |
| IEEE-005 | No aparece "in reference [n]" como sustituto del número; se escribe `in [n]` | menor | sí | [SM p.14 §References] |
| IEEE-006 | Un autor nombrado antes del número ("Smith [1]") solo si su nombre es esencial para la oración; "In Smith [1]" se reduce a "in [1]" | menor | no | [SM p.14 §References] |
| IEEE-007 | Citas en texto de una referencia con 3 o más autores usan `et al.` (`Wood et al. [7]`); con 1 o 2 autores se nombran todos (`Brown and Jones [5]`) | mayor | no | [Ref Guide 2025 §I.A] |
| IEEE-008 | No hay años como identificador de cita (`[Smith 2019]`, `Smith (2019) [1]`) salvo que la fecha sea relevante para el tema | menor | no | [SM p.14 §References] |
| IEEE-009 | No hay "ibid.", "op. cit." en el texto ni en la lista; se cita de nuevo el número anterior (exige renumerar) | mayor | no | [Ref Guide 2025 §I.B] |
| IEEE-010 | Las citas a una parte de una fuente usan `[n, parte]` (`[3, Fig. 1]`, `[3, pp. 5–10]`, `[3, eq. (2)]`); no hay "Fig. 2 of reference [1]" ni "equation (8) of reference [1]" | mayor | no | [Ref Guide 2025 §I.B]; [SM p.14 §References] |
| IEEE-011 | Abreviaturas de parte: `Thm.`, `Sect.`, `Ch.`, `pp.`, `eq.`, `Fig.`, `Appendix`, `Algorithm`, `Lemma` (Ref Guide 2025). `Th.` y `Sec.` (SM p.14, vestigio de la guía 2018) se aceptan sin reportar; solo se reporta mezclar ambas familias en el mismo documento | menor | sí | [Ref Guide 2025 §I.B] vs [SM p.14 §References] |
| IEEE-012 | Cada cita numérica del texto corresponde a una entrada existente de la lista (sin números sobrantes). Implícito en la numeración de la guía | crítica | no | [Ref Guide 2025 §I.A, §II] (implícito) |
| IEEE-013 | Cada entrada de la lista se cita en el texto. La norma dice que citar es opcional ("need not be cited"); es política del plugin, reportar como observación | menor | no | [CONV]; contraste [Ref Guide 2025 §I.A] |
| IEEE-014 | Las referencias se numeran por orden de primera aparición en el texto (1, 2, 3 ...). Verificado: ninguna fuente oficial local (Ref Guide 2018/2023/2025, SM actual y 2024, Math guides) lo dice; solo exige orden numérico para las primeras citas de figuras y tablas. Reportar como convención | menor | no | [CONV]; analogía [SM p.14 §Text Citation of Figures and Tables] |

## REF: lista de referencias

| ID | Regla verificable (binaria, comprobable en el documento) | Severidad | Fix auto | Fuente |
|---|---|---|---|---|
| IEEE-015 | La lista tiene encabezado `REFERENCES` (en español `REFERENCIAS`), sin numeral romano ni letra | menor | sí | [SM p.12 §Text Section Headings] |
| IEEE-016 | Cada entrada empieza con su número entre corchetes, a ras izquierdo en columna propia, colgando fuera del cuerpo de la referencia | menor | sí | [Ref Guide 2025 §II] |
| IEEE-017 | La numeración de la lista es consecutiva 1..N, sin saltos ni números repetidos (implícito; renumerar exige corregir las citas) | crítica | no | [Ref Guide 2025 §II, §I.B NOTE] (implícito) |
| IEEE-018 | Un número = una fuente: ninguna entrada reúne varias obras ni añade comentarios ("see also", "For example", notas) | crítica | no | [Ref Guide 2025 §II]; [SM p.14 §References] |
| IEEE-019 | La misma obra no figura con dos números (una por página o parte citada) | mayor | no | [SM p.14 §References] |
| IEEE-020 | Nombres de autor con inicial(es) ANTES del apellido y sin nombre completo (`J. K. Author`); ninguna entrada usa `Apellido, I.` | crítica | no | [Ref Guide 2025 §II] |
| IEEE-021 | Publicaciones IEEE: se listan todos los autores hasta 6. En fuentes no IEEE se admite `et al.` si la fuente no da más nombres | mayor | no | [Ref Guide 2025 §II] |
| IEEE-022 | Si la fuente tiene más de 6 autores se escribe solo el primero seguido de `et al.` | mayor | sí | [Ref Guide 2025 §II] |
| IEEE-023 | Antes del último autor va `and` (no `&`, no `y`), con coma seriada en 3 o más autores (`A, B, and C`); con 2 autores `A and B` | mayor | sí | [Ref Guide 2025 §II, ejemplos] |
| IEEE-024 | Sufijos Jr., Sr., III sin coma previa (`W. P. Pratt Jr.`) | menor | sí | [Ref Guide 2025 §II] |
| IEEE-025 | Sin títulos ni afiliaciones junto a los autores (Dr., Prof., Ph.D.) | menor | sí | [Ref Guide 2025 §T Websites] |
| IEEE-026 | El título de artículo, capítulo o paper va entre comillas (curvas, como en la guía) y la coma o el punto cierra dentro de ellas. Si el título termina en `?` la coma puede omitirse (`...difference?” CBS News`) | mayor | sí | [Ref Guide 2025 §B, §J, §M, ejemplos] |
| IEEE-027 | En cursiva: título de libro, de revista (abreviado), de conferencia (tras `in Proc.`; no si es "presented at"), de blog, de fuente de noticias, de manual/handbook, de norma, de video y de software. Sin cursiva: artículo, capítulo, tesis, reporte, dataset, sitio web | menor | sí | [Ref Guide 2025 §II, versión HTML] |
| IEEE-028 | Títulos de revista abreviados según `abreviaturas.md` o el CSV oficial; no aparecen nombres completos de revistas de varias palabras | mayor | no | [Ref Guide 2025 §IV.A, §IV.C]; [CSV abreviaturas-revistas] |
| IEEE-029 | Títulos de revista de una sola palabra no se abrevian (`Science`, `Nature`) | menor | no | [Ref Guide 2025 §M Periodicals] |
| IEEE-030 | Artículo de revista con el orden `vol. x, no. x, pp. xxx–xxx, Mon. year` (más `doi:` si hay) | mayor | sí | [Ref Guide 2025 §M Periodicals] |
| IEEE-031 | `vol.`, `no.`, `pp.` (o `p.` si es una sola página) en minúscula con punto; páginas con en dash | menor | sí | [Ref Guide 2025 §M] |
| IEEE-032 | Mes abreviado en periódicos, conferencias, libros y similares: `Jan., Feb., Mar., Apr., May, Jun., Jul., Aug., Sep., Oct., Nov., Dec.` (formas de los ejemplos; la guía no da lista ni usa `Sept.`; `May` sin punto). Los ejemplos de dataset y software usan mes completo, así que no se reporta ahí | menor | sí | [Ref Guide 2025 §II, §M, ejemplos] |
| IEEE-033 | Dos meses del mismo número separados por barra (`Jul./Aug. 2013`) | menor | sí | [Ref Guide 2025 §II] |
| IEEE-034 | Toda referencia incluye al menos el año; sin fecha se escribe `(n.d.)` en el lugar de la fecha | mayor | no | [Ref Guide 2025 §II] |
| IEEE-035 | Se incluyen número y mes en artículos de IEEE Transactions cuando existen en IEEE Xplore (requiere consulta externa; no verificable solo con el texto) | menor | no | [Ref Guide 2025 §II, §M] |
| IEEE-036 | Artículo con identificador usa `Art. no. xxx` en vez de páginas | menor | no | [Ref Guide 2025 §M Article ID] |
| IEEE-037 | DOI escrito `doi: 10.xxxx/...` (prefijo minúscula con dos puntos y espacio); no `DOI:` ni `https://doi.org/` salvo la variante "DOI resolver" (`doi: http://dx.doi.org/...`) | menor | sí | [Ref Guide 2025 §M Periodicals, §E Datasets] |
| IEEE-038 | Las referencias que no terminan en URL terminan en punto, también las que terminan en DOI | menor | sí | [Ref Guide 2025 §II] |
| IEEE-039 | Las referencias que terminan en URL no llevan punto final | menor | sí | [Ref Guide 2025 §II, §III] |
| IEEE-040 | Con DOI o fecha de acceso Y URL, el DOI/fecha va primero, luego punto, luego `[Online]. Available: URL`; no se pone el DOI después de la URL (patrón 2018) | mayor | sí | [Ref Guide 2025 §II, §III] |
| IEEE-041 | Fuente en línea con `[Online]. Available: URL` (video: `[Online Video]. Available:`) | mayor | sí | [Ref Guide 2025 §III, §K] |
| IEEE-042 | Fecha de acceso con formato `Accessed: Mon. D, YYYY.` en sitios web, manuales en línea, libros en línea y videos. La guía no la exige en artículos con DOI; la sección III remite a la versión final del autor para su posición. Los ejemplos de dataset y software usan mes completo y el de redes sociales omite los dos puntos | mayor | no | [Ref Guide 2025 §III, §I, §K, §T] |
| IEEE-043 | Sitio web: `J. Smith. “Page Title.” Website Title. Accessed: ... [Online]. Available: URL` (no la forma 2018 `(accessed ...)` entre paréntesis tras la URL). La guía escribe `[Online.]` con punto en esta sección: aceptar ambas formas, exigir consistencia | mayor | sí | [Ref Guide 2025 §T Websites] |
| IEEE-044 | Libro: `A. Author, Title. City, State (solo EE. UU.), Country: Publisher, year.` con ciudad, país y editorial presentes (el ejemplo de libro extranjero omite el país) | mayor | no | [Ref Guide 2025 §B Book] |
| IEEE-045 | Capítulo de libro: `“Chapter,” in Book, X. Editor, Ed., City: Publisher, year, ch. x, pp. xxx–xxx.` (nombre de editor solo si lo hay; `Eds.` si son varios) | mayor | no | [Ref Guide 2025 §B] |
| IEEE-046 | Conferencia: `in Proc. Abbrev. Conf. Name, [City, State, Country,] year, pp. xxx–xxx.` con palabras abreviadas (`Proc.`, `Int.`, `Conf.`, `Symp.`, `Annu.`), ordinal en números (`4th`), casi sin artículos ni preposiciones ("of the", "on" se omiten) y `USA` tras ciudad y estado en lugares de EE. UU. | mayor | no | [Ref Guide 2025 §C] |
| IEEE-047 | Paper "presented at" incluye lugar, fechas y número de paper si existe | menor | no | [Ref Guide 2025 §C Conference Paper] |
| IEEE-048 | Tesis: `“Title,” M.S. thesis` o `Ph.D. dissertation`, `Abbrev. Dept., Abbrev. Univ., City, State/Country, year.`; "thesis"/"dissertation" según lo use el autor o la institución | mayor | no | [Ref Guide 2025 §Q] |
| IEEE-049 | Reporte técnico: `“Title,” Institution, City, State, Country, Rep. xxx, Mon. year.` | mayor | no | [Ref Guide 2025 §N] |
| IEEE-050 | Norma: `*Title of Standard*, Standard number, Corporate author, location, date.` | mayor | no | [Ref Guide 2025 §P] |
| IEEE-051 | Patente con día del mes: `U.S. Patent x xxx xxx, Mon. D, year.` (la guía pide conservar o solicitar el día; algunos ejemplos suyos lo omiten) | mayor | no | [Ref Guide 2025 §L] |
| IEEE-052 | Artículo aceptado y no publicado: `to be published` (no "to appear in"); no aceptado: `submitted for publication`; sin enviar: `unpublished` | menor | no | [Ref Guide 2025 §M, §S] |
| IEEE-053 | Artículo Early Access: `early access, Mon. D, year, doi: ...` y se cita la versión de la revista, no la de arXiv | menor | no | [Ref Guide 2025 §M Early Access] |
| IEEE-054 | Preprint: `“Title,” year, arXiv:number.` | menor | no | [Ref Guide 2025 §S Preprint arXiv] |
| IEEE-055 | Software o dataset con autor(es), título, fecha o versión y distribuidor o repositorio; localizador (URL o DOI) cuando existe. La guía da un ejemplo de software sin URL (`MSDN Library Visual Studio 6.0. (2001). Microsoft.`) | mayor | no | [Ref Guide 2025 §O, §E] |
| IEEE-056 | Obras en otro idioma con `(in Language)` tras el título (artículo) o la editorial (libro) | menor | no | [Ref Guide 2025 §B Foreign, §M Other Language] |
| IEEE-057 | Ninguna entrada tiene datos inventados o incompletos sin marcar: autor, título, año y fuente presentes (la guía pide obtener la información relevante; la prohibición de inventar es política del plugin) | crítica | no | [Ref Guide 2025 §II]; [CONV] |
| IEEE-058 | Cada DOI de la lista resuelve y coincide con los metadatos (autor, año, revista) en Crossref | mayor | no | [CONV] (política anti-alucinación del plugin) |
| IEEE-135 | Blog o noticia en línea: `J. K. Author, “Title,” *Source*, Mon. D, year. [Online]. Available: URL` (noticia impresa: sin la parte `[Online]`) | menor | no | [Ref Guide 2025 §A, §J] |
| IEEE-136 | Referencia no publicada: `J. K. Author, private communication, Mon. year.` o `J. K. Author, “Title,” unpublished.` | menor | no | [Ref Guide 2025 §S] |
| IEEE-137 | Manual o handbook impreso: `*Name*, x ed., Abbrev. Co., City, State, Country, year, pp. xxx–xxx.`; en línea: `J. K. Author (or Co.). *Name*, x ed. (year). Accessed: Date. [Online]. Available: URL` | menor | no | [Ref Guide 2025 §F, §I] |
| IEEE-138 | Dataset: `Author, Date, “Title of Dataset,” Source, doi: xxx.` o `..., Source. [Online]. Available: URL` | menor | no | [Ref Guide 2025 §E] |

## EST: estructura y encabezados

| ID | Regla verificable (binaria, comprobable en el documento) | Severidad | Fix auto | Fuente |
|---|---|---|---|---|
| IEEE-059 | Orden de secciones: Abstract, Index Terms, [Nomenclature], Introduction, cuerpo, Conclusion, Appendix(es), [Conflict of Interest], Acknowledgment, References [ART] | mayor | no | [SM p.5 §II, p.13] |
| IEEE-060 | Hay Abstract (un único párrafo) salvo editoriales y otras excepciones [ART] | mayor | no | [SM p.10 §Abstract] |
| IEEE-061 | El Abstract tiene entre 150 y 250 palabras [ART] | mayor | no | [SM p.5 §II] |
| IEEE-062 | El Abstract no contiene ecuaciones numeradas, citas numeradas ni notas al pie | mayor | no | [SM p.10 §Abstract] |
| IEEE-063 | Hay Index Terms, en orden alfabético, primera palabra en mayúscula y el resto en minúscula salvo nombres propios, tras el Abstract [ART] | mayor | no | [SM p.10 §Index Terms] |
| IEEE-064 | Index Terms con formato `Index Terms—t1, t2, ...` (acrónimos con definición seguida de sigla entre paréntesis) | menor | sí | [SM p.10 §Index Terms] |
| IEEE-065 | Acrónimos definidos la primera vez en el Abstract y de nuevo en el cuerpo (palabra completa + sigla entre paréntesis), salvo los de Nomenclature | mayor | no | [SM p.21 §Acronyms] |
| IEEE-066 | Encabezados primarios en mayúsculas con numeral romano (`I. INTRODUCTION`) si se enumeran | mayor | sí | [SM p.11 §Text Section Headings] |
| IEEE-067 | Encabezados secundarios `A. Title` (letra mayúscula + punto), cursiva | menor | sí | [SM p.11] |
| IEEE-068 | Encabezados terciarios `1) Title:` en cursiva, corridos con el texto y terminados en dos puntos | menor | sí | [SM p.11; SM 2024 p.11] |
| IEEE-069 | Los niveles de encabezado no se saltan y la enumeración es consistente en todo el documento (la norma solo dice que enumerar es deseable, no obligatorio) | mayor | no | [CONV]; contexto [SM p.11] |
| IEEE-070 | `REFERENCES` y `ACKNOWLEDGMENT` sin enumerar aunque los demás encabezados sí | mayor | sí | [SM p.12] |
| IEEE-071 | Introduction, Conclusion y Acknowledgment en singular; `Acknowledgment` sin "e" entre g y m [EN] | menor | sí | [SM p.11, p.13] |
| IEEE-072 | Referencias internas a secciones: `Section II`, `Section II-A`, `Section II-A1` (mayúscula, sin "Subsection", sin punto) [EN] | menor | sí | [SM p.12] |
| IEEE-073 | Apéndice único sin numerar; varios con `APPENDIX I` o `APPENDIX A`; plural `Appendixes` | menor | no | [SM p.12-13] |
| IEEE-074 | Teoremas, lemas y pruebas: teorema como encabezado terciario sin número arábigo y prueba como cuaternario | menor | no | [SM p.12]; [Math Guide 2023 §E] |
| IEEE-075 | Título en capitalización IEEE: artículos, conjunciones coordinantes y preposiciones cortas en minúscula salvo inicial/final; preposiciones de más de 3 letras en mayúscula [EN] | menor | no | [SM p.5 §Title] |
| IEEE-076 | El título no contiene ecuaciones detalladas ni abreviaturas en minúscula (salvo unidades y acrónimos), que deben ir en mayúscula | menor | no | [SM p.5 §Title] |
| IEEE-077 | Acknowledgment en tercera persona, sin Mr./Mrs./Miss y sin notas personales | menor | no | [SM p.13 §Acknowledgment] |
| IEEE-078 | Apoyo financiero declarado en la primera nota al pie, no en Acknowledgment (salvo algunas Transactions) [ART] | menor | no | [SM p.7, p.13] |
| IEEE-079 | Uso de IA generativa (texto, figuras, imágenes, código) declarado en Acknowledgment con sistema, secciones y nivel de uso. Edición y gramática quedan fuera de la política (divulgación solo recomendada) | mayor | no | [SM p.13 §Acknowledgment] |
| IEEE-080 | Conflict of Interest, si existe, en sección propia antes de Acknowledgment | menor | no | [SM p.13 §Conflict of Interest] |
| IEEE-081 | Primera nota al pie sin numerar, sin asteriscos ni daggers; las demás numeradas consecutivamente con superíndice tras la puntuación (por lo general antes de guion, dos puntos y punto y coma) [ART] | menor | no | [SM p.6, p.17] |
| IEEE-082 | Listas con etiquetas `1)`, `2)`, luego `a)`, luego `i)` (paréntesis de cierre único) | menor | sí | [SM p.17 §Lists in Text] |
| IEEE-083 | Listas en línea: introducidas por dos puntos, ítems separados por `;` y paralelos | menor | sí | [SM p.17] |
| IEEE-131 | Encabezados cuaternarios: como los terciarios (cursiva, corridos, dos puntos finales) pero con letra minúscula + `)` como etiqueta y solo la primera letra del título en mayúscula. El ejemplo del PDF 2024 muestra `1a)` | menor | no | [SM p.11; SM 2024 p.11] |

## FIG: figuras y tablas

| ID | Regla verificable (binaria, comprobable en el documento) | Severidad | Fix auto | Fuente |
|---|---|---|---|---|
| IEEE-084 | En texto, las figuras se citan `Fig. N` (también al inicio de oración, también `Fig. 1(a)`); no `Figure N` | mayor | sí | [SM p.14 §Text Citation of Figures and Tables] |
| IEEE-085 | Pie de figura con formato `Fig. N.` + espacio em + texto, primera palabra en mayúscula; va debajo de la figura (explícito solo para figuras apaisadas; implícito en general) | mayor | sí | [SM p.14-15] |
| IEEE-086 | El pie de figura o de tabla no empieza con A, An ni The ("in general") | menor | no | [SM p.14] |
| IEEE-087 | Subpartes `(a)`, `(b)` aparecen en el pie antes de su descripción y con estilo consistente | menor | no | [SM p.14] |
| IEEE-088 | Las notas de figura van dentro del pie | menor | no | [SM p.14] |
| IEEE-089 | Tablas rotuladas `TABLE` + numeral romano, centrado encima de la tabla [EN] (en español `TABLA I`, ver adaptación) | mayor | sí | [SM p.15 §Tables] |
| IEEE-090 | La descripción de la tabla va bajo el rótulo y no termina en punto | menor | sí | [SM p.15] |
| IEEE-091 | Numeración de figuras y tablas consecutiva, sin saltos ni repetidos, incluyendo apéndices (renumerar exige corregir las citas) | mayor | no | [SM p.13 §Appendix] |
| IEEE-092 | Las primeras citas de figuras y de tablas aparecen en orden numérico | mayor | no | [SM p.14] |
| IEEE-093 | Toda figura y tabla se cita en el texto (implícito en la regla de colocación cerca de la primera mención). Regla por decisión del usuario (18-nov-2026) | mayor | sí | [CONV]; contexto [SM p.25 §F.1] |
| IEEE-094 | Cada figura o tabla se ubica cerca de su primera mención, preferiblemente después, y arriba de la columna/página | menor | no | [SM p.25 §F.1] |
| IEEE-095 | Gráfico reutilizado de una publicación IEEE: número(s) de referencia al final del pie. De otros editores: permiso previo y su leyenda al final del pie | mayor | no | [SM p.15 §Obtaining permission] |
| IEEE-133 | No se usa la imagen "Lena" (no se aceptan artículos con ella desde el 1 abr 2024) [ART] | mayor | no | [SM p.14 §Use of the Lena Image] |

## MAT: matemáticas

| ID | Regla verificable (binaria, comprobable en el documento) | Severidad | Fix auto | Fuente |
|---|---|---|---|---|
| IEEE-096 | Ecuaciones numeradas consecutivamente, número a ras derecho en la línea de la última línea, sin repetidos ni faltantes (renumerar exige corregir las citas) | mayor | no | [SM p.25 §Equation Numbers]; [Math Guide 2023 §F] |
| IEEE-097 | El estilo del número es consistente (`(1)`, `(1a)`, o por sección `(1.1)`); sin mezclar `(1-a)` con `(1a)`. El SM acepta `(1a)`, `(1.1)`, `(1-1)` si son consistentes; la Math Guide prefiere `(1a)` a `(1-a)` | menor | sí | [Math Guide 2023 §F]; [SM p.13 §Text Equations] |
| IEEE-098 | En texto la ecuación se cita como `(n)`; `Equation` se escribe completo solo al inicio de oración (la norma no da `Eq.` abreviado; en citas de parte sí: `[3, eq. (2)]`) | menor | sí | [SM p.24 §Math 14] |
| IEEE-099 | No hay paréntesis dobles en texto (`(see (10))`); se usa `[see (10)]` | menor | sí | [SM p.26 §III.A 8] |
| IEEE-100 | Las variables van en cursiva y coinciden en texto y en fórmulas | mayor | no | [SM p.24 §Math 1]; [SM p.25 §Displayed Equations]; [Math LaTeX p.2] |
| IEEE-101 | Funciones y operadores (sin, cos, log, ln, exp, max, min, lim, det, arg, Re, Im) en redonda; en LaTeX con `\sin`, `\max`, `\text{arg min}` | mayor | sí | [Math Guide 2023 §I]; [Math LaTeX p.2-3, p.9-11] |
| IEEE-102 | Vectores en negrita (SM: "usually boldface italic"; Math Guide: "usually ... if distinguished by the author"; Math LaTeX: "always in bold") y de forma consistente | menor | no | [Math LaTeX p.2]; [Math Guide 2023 §G]; [SM p.24 §Math 1] |
| IEEE-103 | Acrónimos dentro de ecuaciones (MSE, RMS, NCC) en redonda (`\text{}`), igual que en el texto | menor | sí | [Math LaTeX p.13-16]; [SM p.25 §Displayed Equations] |
| IEEE-104 | Unidades y abreviaturas de palabras en sub/superíndices en redonda; un subíndice de una sola letra puede ir en cursiva si evita inconsistencias | menor | no | [SM p.25 §Displayed Equations] |
| IEEE-105 | La ecuación que cierra la oración termina en punto; la puntuación de entrada solo si el texto previo es oración completa; la coma final se elimina salvo que sea crítica | menor | no | [SM p.24 §Use of Periods and Commas]; [Math Guide 2023 §A] |
| IEEE-106 | Puntos suspensivos matemáticos: tres puntos, en la línea base entre comas (`x1, x2, …, xn`) o centrados con operadores | menor | no | [SM p.24 §Ellipses]; [Math Guide 2023 §A] |
| IEEE-107 | En LaTeX no se usa `$$ ... $$` ni `eqnarray`; se usa `equation`, `equation*`, `align` o `\[ \]` | mayor | no | [Math LaTeX p.4] |
| IEEE-108 | Definiciones por casos con `cases` (no `array` con `\left\lbrace`) y palabras con `\text{}` | menor | no | [Math LaTeX p.5-8] |
| IEEE-109 | Delimitadores que envuelven fracciones o raíces usan `\left ... \right` | menor | no | [Math LaTeX p.16-18] |
| IEEE-110 | Límites de sumas/integrales arriba y abajo en display (sin `\nolimits`) y al costado en línea | menor | sí | [Math LaTeX p.11-12]; [Math Guide 2023 §B Rule 3] |
| IEEE-111 | Ordinales matemáticos `zeroth, first, nth, (k + 1)th`, no `1st` ni `(k + 1)st` | menor | sí | [SM p.24 §Math 13] |
| IEEE-112 | Fracciones en línea con barra (`(c-d)/(k+4)`), no apiladas. Conflicto: la Math Guide lo manda ("should not appear stacked"); el SM lo permite como opcional ("not a necessity") | menor | no | [Math Guide 2023 §B Rule 2]; [SM p.24 §Math 9] |
| IEEE-132 | Nombres de función: `tan` (no tg), `cot` (no ctg ni ctn), `csc` (no cosec), `Pr` (no Prob.) | menor | sí | [Math Guide 2023 §I, §L] |
| IEEE-134 | Espacio fino a ambos lados de funciones y diferenciales en redonda (`sin t`, no `sint`), salvo junto a un verbo u operador | menor | no | [Math Guide 2023 §G] |

## MEC: mecánica, unidades y estilo

| ID | Regla verificable (binaria, comprobable en el documento) | Severidad | Fix auto | Fuente |
|---|---|---|---|---|
| IEEE-113 | Número y unidad separados por espacio normal (`3.05 mm`, `2 A`), sin espacio fino y sin pegarlos | menor | sí | [SM p.24 §Math 6] |
| IEEE-114 | Unidades con abreviatura estándar (A, V, W, Hz, dB, µm, b/s); no `amp`, `cps`, `c/s`, `db`, `micron`. `micron`, `cps` y `µ` están en SM Math 8; `amp`, `db` y `b/s` en el Apéndice C del PDF 2024 | mayor | sí | [SM p.24 §Math 8]; [SM 2024 App. C p.35-42] |
| IEEE-115 | Rangos con unidad una sola vez (`40–50 mm`) salvo unidades distintas (`50 inches to 7 feet`) | menor | sí | [SM p.24 §Ranges With Units] |
| IEEE-116 | Unidad como adjetivo compuesto con guion solo si hace falta (`10-kV voltage`); sin guion si no es adjetivo (`a line 4 in long`) | menor | no | [SM p.24 §Math 5] |
| IEEE-117 | Numerales con unidades; sin unidades se deletrean 1 a 10 y se usan numerales desde 11, salvo inicio de oración | menor | no | [SM p.24 §Math 12] |
| IEEE-118 | Números de 5 dígitos o más con espacio fino, sin coma (`62 000`, pero `4000`) | menor | sí | [SM p.24 §Math 7] |
| IEEE-119 | Decimales con cero inicial (`0.25`) y sin ceros finales innecesarios. Conflicto en el SM: Math 3 dice "siempre" cero inicial; §Percentages and Decimals dice "si hace falta para claridad" (`.25`); se exige siempre el cero (Math 3; decisión del usuario, 18-nov-2026) | mayor | sí | [SM p.24 §Math 3]; [SM p.24 §Percentages and Decimals] |
| IEEE-120 | Porcentajes con número y `%`; el símbolo se repite en rangos (`20%-30%`; el SM lo escribe con guion corto en ese ejemplo) | menor | sí | [SM p.24 §Percentages and Decimals] |
| IEEE-121 | Sumas de dinero con `$`, no "dollars" [EN] | menor | sí | [SM p.25 §Math 15] |
| IEEE-122 | En dash en rangos de páginas, años y valores; tras "from" se usa "to", no en dash | menor | sí | [SM p.22 §The En or Em Dash] |
| IEEE-123 | Plurales de unidades con "s" (`3 bits/s`); plural de años y acrónimos sin apóstrofo (`1990s`, `FETs`) [EN] | menor | sí | [SM p.22 §Plurals]; [SM p.21 §Acronyms]; [SM p.26 §III.A 9] |
| IEEE-124 | Sin contracciones en texto técnico (`do not`, `cannot`; se permiten `don't care`, `best-case`, `worst-case`) [EN] | menor | sí | [SM p.23 §Contractions] |
| IEEE-125 | Fechas en el cuerpo en formato internacional con mes completo (`4 June 2002`); no aplica a la lista de referencias [EN] | menor | sí | [SM p.23 §Dates] |
| IEEE-126 | Coma antes de la conjunción final en series de tres o más [EN] | menor | sí | [SM p.26 §III.A 2] |
| IEEE-127 | La puntuación va dentro de las comillas salvo dos puntos y punto y coma; comillas simples para cita dentro de cita [EN] | menor | sí | [SM p.26 §III.A 6] |
| IEEE-128 | Ortografía americana (`behavior`, `center`, `polarization`) [EN] | menor | sí | [SM p.22 §Spelling] |
| IEEE-129 | Sin símbolos ™ ni ® en el texto corrido | menor | sí | [SM p.22 §Trademarks] |
| IEEE-130 | Lenguaje inclusivo: sin términos de la Guía (blacklist, able-bodied, A.D./B.C., caretaker, Caucasian). El export no conserva cuáles están resaltados como "evitar siempre"; el reemplazo requiere criterio | menor | no | [SM p.17 §Inclusive Language]; [SM 2024 App. E] |
| IEEE-139 | Artículo indefinido según el sonido de la sigla (`an FCC regulation`, `a BRI`) [EN] | menor | no | [SM p.21 §Acronyms] |
| IEEE-140 | Sin puntuación duplicada (`..` fuera de puntos suspensivos, `,,`, `;;`, `::`) ni espacios dobles dentro del párrafo. Petición del usuario, 18-nov-2026; corrección tipográfica general | menor | sí | [decisión del usuario] |
