# IEEE: principios de la lista de referencias

Fuente primaria: Reference Guide V 3.28.2025 (`normas/ieee/actual/reference-guide.txt`). La guía 2018 (`normas/ieee/IEEE-Reference-Guide.txt`) es histórica. Tags: `[Ref Guide 2025 §X]`.
Cursiva en plantillas: `*texto*`. Las plantillas por tipo están en `referencias-por-tipo-1.md` y `-2.md`.

## 1. Maquetación de la lista

| Regla | Fuente |
|---|---|
| Los números van pegados al margen izquierdo, en su propia columna, "colgando" fuera del cuerpo de la referencia | [Ref Guide 2025 §II] |
| Números en la línea, entre corchetes: `[1]`, `[2]` | [Ref Guide 2025 §II] |
| Un solo número por referencia; no combinar referencias | [Ref Guide 2025 §II] |
| Encabezado de la lista: `REFERENCES` sin enumerar (primary heading sin numeral romano) | [Style Manual (actual) §Text Section Headings p.11] |
| Si la referencia impresa trae URL, puede ir al final (estilo de referencias online) | [Ref Guide 2025 §II] |
| Las URL no llevan hipervínculo en la prueba de imprenta | [Ref Guide 2025 §III] |

## 2. Nombres de autores

| Regla | Ejemplo | Fuente |
|---|---|---|
| Nombre de pila reducido a inicial(es), ANTES del apellido (también editores) | `J. K. Author` | [Ref Guide 2025 §II] |
| Dos autores: "A and B" | `B. Klaus and P. Horn` | [Ref Guide 2025 §B Book] |
| 3 a 6 autores: todos, con coma y "and" antes del último | `D. Caratelli, M. C. Viganó, G. Toso, and P. Angeletti` | [Ref Guide 2025 §C Conference Paper] |
| Más de 6 nombres: primer autor + `et al.` | `J. Yanamadala et al.,` | [Ref Guide 2025 §II] |
| Publicaciones IEEE: obligatorio listar TODOS hasta 6 | | [Ref Guide 2025 §II] |
| No IEEE: `et al.` permitido si no se dan más nombres | | [Ref Guide 2025 §II] |
| Sufijos Jr., Sr., III: SIN comas | `Michael Smith Jr.; Ray Barnett Sr.; Lucas Molignaro III` | [Ref Guide 2025 §II] |
| Autor corporativo: nombre completo en lugar del autor | `Westinghouse Electric Corporation (...)`, `Bureau of Meteorology,` | [Ref Guide 2025 §B Book, §N Reports] |
| Editores: `X. Editor, Ed.` / `Eds.` | `J. S. Brake, Ed.` | [Ref Guide 2025 §B] |
| Sitios web: autores en el orden de la página; sin títulos ni afiliaciones | | [Ref Guide 2025 §T Websites] |

## 3. Puntuación final, DOI, URL, fecha de acceso

| Regla | Fuente |
|---|---|
| Toda referencia termina en punto, también las que terminan en DOI | [Ref Guide 2025 §II] |
| EXCEPCIÓN: las que terminan en URL no llevan punto final | [Ref Guide 2025 §II, §III] |
| Si hay DOI o fecha de acceso Y URL: primero el DOI o la fecha de acceso, luego punto, luego la URL | [Ref Guide 2025 §II] |
| DOI con prefijo `doi: ` (minúscula, dos puntos, espacio) | [Ref Guide 2025 §M Periodicals] |
| Fecha de acceso: `Accessed: Abbrev. month day, year.` | [Ref Guide 2025 §III] |
| La posición de la fecha de acceso debe coincidir con la de la versión final enviada por el autor | [Ref Guide 2025 §III] |
| Medio en línea: `[Online]. Available: URL` (video: `[Online Video]. Available:`) | [Ref Guide 2025 §III, §K] |

Ordenaciones permitidas (§III, verbatim):
```
Accessed date. DOI. [Online]. Available: URL (no period at end)
Accessed date. [Online]. Available: URL (no period at end)
Accessed date. DOI (add period at end).
DOI. URL (no period at end)
(No accessed date), DOI (add period at end unless URL).
URL (no period at end)
```

Cortes de URL al maquetar [Ref Guide 2025 §III]: cortar tras `/`, `//` o punto; cortar ANTES de guion, tilde, guion bajo, `?`, `%`; antes o después de `=` y `&` (igual para `@`); no añadir guiones ni espacios; no dejar que la URL se divida con guion de silabeo.

## 4. Fechas y meses

| Regla | Fuente |
|---|---|
| Toda referencia lleva fecha con al menos el año (o año de acceso si aplica) | [Ref Guide 2025 §II] |
| Sin fecha: `(n.d.)` en el lugar de la fecha. Ej. `BAR50 Series Infineon PIN Diode Datasheet. (n.d.). [Online]. Available: http://www.infineon.com` | [Ref Guide 2025 §II] |
| Mes abreviado. Formas vistas en los ejemplos: Jan., Feb., Mar., Apr., May, Jun., Jul., Aug., Sep., Oct., Nov., Dec. (la guía no da lista explícita) | [Ref Guide 2025 §II, ejemplos] |
| Dos meses para el mismo número: separados por barra, luego año: `Jul./Aug. 2013` | [Ref Guide 2025 §II] |
| Rango de días: `Oct. 5–8, 2010` (en dash) | [Ref Guide 2025 §C Conference Paper] |
| Early Access: usar la "Date of Publication" | [Ref Guide 2025 §II] |
| Artículos en un volumen: usar fecha del volumen/número | [Ref Guide 2025 §II] |
| Número y mes de IEEE Transactions: si faltan, buscarlos en IEEE Xplore (no todas incluyen número/mes) | [Ref Guide 2025 §II] |
| En referencias rige el estilo de referencias; en el cuerpo del texto IEEE usa formato internacional con mes completo (`4 June 2002`) | [Style Manual (actual) §Dates p.23] |

## 5. Información faltante y otros

- "References may not include all information; please obtain and include relevant information." No se inventan datos [Ref Guide 2025 §II].
- Antes de 1988 los volúmenes de IEEE Transactions llevaban sigla (`vol. AC-26`); excepción: Proc. IEEE [Ref Guide 2025 §M Periodicals].
- Títulos de revista de UNA palabra no se abrevian (`Science`, `Nature`) [Ref Guide 2025 §M Periodicals].
- Article ID confundido con páginas: número único largo, rango no secuencial o `1–XX` con volumen indican Art. no.; consultar al autor [Ref Guide 2025 §M Article ID].
- Cursivas (según el HTML 2025): título de libro, nombre de conferencia, título abreviado de revista, título de blog / fuente de noticias, título de manual o handbook, título de norma, título de video. NO llevan cursiva: título de artículo (entre comillas), tesis, reporte, datos de editorial [Ref Guide 2025 §II ejemplos, versión HTML].
- Comillas: el título de artículo/capítulo/paper va entre comillas; la coma va dentro de las comillas: `“Title of paper,”` [Ref Guide 2025 §II ejemplos].

## 6. Cambios 2018 a 2025

| Tema | Guía 2018 | Guía 2025 (vigente) |
|---|---|---|
| Rangos en texto | `[4]–[7]` | `[4], [5], [6], [7]`, sin en dash |
| Jr./Sr./III | Texto decía "use commas around", ejemplos sin coma | Sin comas |
| DOI/fecha vs URL | DOI después de la URL | DOI o fecha de acceso primero, punto, luego URL |
| Sin fecha | no regulado | `(n.d.)` |
| Partes de referencia | `Th.`, `Sec.` | `Thm.`, `Sect.` |
| Sitios web | `(accessed Feb. 1, 2009).` entre paréntesis tras la URL | `Accessed: Feb. 1, 2009. [Online.] Available: URL` |
| Datasets | `Title, Source, Date, doi:` | `Author, Date, “Title of Dataset,” Source, doi:`; añade principios FORCE11 |
| Tipos nuevos | n/a | Blog, Legal Citations, News Articles, Software (separado de Manuals), Periodical in Early Access, Preprint arXiv |
| Libros traducidos | `Book Translated` | `Book (Foreign Publication or Translated)` con `trans.` |
| Revista de una palabra | no regulado | no se abrevia |
| Tips de abreviar títulos | n/a | `-ology` a `-ol.`, `-graphy` a `-gr.`, compuestas por la última palabra |
| Abreviaturas | `Automat. Contr.`, `Sec.` | `Autom. Control`, `Sect.`; nuevas `Archit.`, `Art.`, `Co.`, `Navig.`, `Thm.`, `Vol.`, `Vis.` |
| Conferencias | "nombre de la conferencia en cursiva" | frase retirada del texto; la cursiva sigue en el HTML |

Fuente: comparación de `normas/ieee/IEEE-Reference-Guide.txt` (V 11.12.2018) con `normas/ieee/actual/reference-guide.txt` (V 3.28.2025).

## 7. Adaptación al español (convención, no regla oficial IEEE)

- Encabezado: `REFERENCIAS` (o `Referencias`) en lugar de `REFERENCES`; sin numeral.
- Por defecto conservar los marcadores en inglés tal cual los da IEEE (`[Online]. Available:`, `Accessed:`, `doi:`, `Ed.`, `vol.`, `no.`, `pp.`, `et al.`) para que el juez los compruebe. Alternativa localizada válida solo si es consistente en todo el documento: `[En línea]. Disponible:`, `Consultado:`.
- Meses: mantener abreviaturas inglesas (Jan., Feb., ...) por defecto; alternativa consistente: ene., feb., mar., abr., may., jun., jul., ago., sep., oct., nov., dic.
- Títulos de obras en español: capitalización de oración (mayúscula solo inicial y nombres propios); IEEE no regula capitalización de títulos en español.
- Mantener `et al.`; topónimos con país en forma consistente (`Bogotá, Colombia`).
