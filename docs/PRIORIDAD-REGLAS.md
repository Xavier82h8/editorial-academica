# Prioridad de las reglas que hoy evalúa el agente

Escrito a mano (no lo genera ningún script). Fecha: 19-nov-2026, sobre el catálogo de `docs/REGLAS.md` (323 reglas, 237 de agente; tras las tandas 1 y 2 quedan 203).

**Fórmula:** prioridad = impacto² / esfuerzo; se divide entre 2 si el riesgo de falso positivo (FP) es alto.
- **Impacto 1-5**: severidad (crítica 5, mayor 4, menor 2) ajustada según lo frecuente que es el error en el piloto, los ejemplos y los ciegos.
- **Esfuerzo 1-5**: 1 = regex sobre lo que el juez ya extrae (entradas, cuerpo, rótulos); 3 = requiere parsear autores o secciones; 5 = requiere entender el texto.
- **FP**: riesgo de marcar texto correcto.

La frecuencia es cualitativa (lo que aparece en `pruebas-editorial/piloto`, `ejemplos/` y los ciegos docs/docs2/docs3), no un conteo medido.

## Tanda 1 (v0.5.0): reglas que pasan a ser deterministas

| # | Regla | Sev. | Imp. | Esf. | FP | Prioridad | Comprobación |
|---:|---|---|---:|---:|---|---:|---|
| 1 | IEEE-017 | crítica | 5 | 1 | bajo | 25.0 | numeración 1..N sin saltos ni repetidos (hoy la detecta el código, pero la emite como IEEE-016) |
| 2 | IEEE-034 | mayor | 4 | 1 | bajo | 16.0 | cada entrada tiene un año o `(n.d.)` |
| 3 | IEEE-023 | mayor | 4 | 1 | bajo | 16.0 | `and` antes del último autor (no `&` ni `y`); **corregible** |
| 4 | IEEE-091 | mayor | 4 | 1 | bajo | 16.0 | figuras y tablas numeradas de forma consecutiva |
| 5 | APA-066 | mayor | 4 | 1 | bajo | 16.0 | `(año).` o `(año, mes día).` tras los autores |
| 6 | APA-041 | mayor | 4 | 1 | bajo | 16.0 | la cita lleva solo el año; `s. f.`/`n.d.` |
| 7 | APA-024 | mayor | 4 | 1 | bajo | 16.0 | ningún nivel de encabezado se salta |
| 8 | IEEE-020 | crítica | 5 | 2 | medio | 12.5 | `J. K. Apellido`, nunca `Apellido, I.` |
| 9 | IEEE-009 | mayor | 3 | 1 | bajo | 9.0 | sin `ibid.` ni `op. cit.` |
| 10 | IEEE-084 | mayor | 3 | 1 | medio | 9.0 | en el texto se escribe `Fig. N`, no `Figure N`; **corregible** |
| 11 | IEEE-022 | mayor | 3 | 1 | bajo | 9.0 | más de 6 autores: primero + `et al.` |
| 12 | IEEE-092 | mayor | 3 | 1 | bajo | 9.0 | las primeras menciones de figuras y tablas van en orden |
| 13 | IEEE-089 | mayor | 3 | 1 | bajo | 9.0 | rótulo `TABLE`/`TABLA` + numeral romano |
| 14 | IEEE-061 | mayor | 3 | 1 | medio | 9.0 | Abstract de 150 a 250 palabras (solo si hay sección Abstract/Resumen) |
| 15 | IEEE-041 | mayor | 3 | 1 | bajo | 9.0 | si hay URL de acceso, `[Online]. Available:` |
| 16 | APA-015 | mayor | 3 | 1 | bajo | 9.0 | cada apéndice se menciona en el texto, en orden |
| 17 | APA-031 | mayor | 3 | 1 | bajo | 9.0 | el texto no empieza con un encabezado «Introducción»/«Introduction» |
| 18 | IEEE-019 | mayor | 4 | 2 | bajo | 8.0 | la misma obra no tiene dos números (mismo DOI o título normalizado) |
| 19 | APA-063 | mayor | 4 | 2 | medio | 8.0 | autores invertidos; `&`/`y` antes del último |
| 20 | APA-044 | mayor | 4 | 2 | bajo | 8.0 | mismo autor y año: letras a, b en la lista |
| 21 | APA-039 | mayor | 4 | 2 | bajo | 8.0 | obra de 1 o 2 autores citada con `et al.` |

## Tanda 2 (hecha): reglas que pasan a ser deterministas

Las 13 candidatas llegaron a 0 falsos positivos en las 83 referencias APA, las 138 IEEE, las citas oficiales, las 17 muestras oficiales (salvo los verdaderos positivos documentados en `tests/run_todo.py`), las rondas ciegas docs/docs2/docs3, `ejemplos/` y el piloto (`protocolo.final3.docx`, 0 hallazgos). Ninguna se descartó. Pruebas: `tests/run_reglas_tanda2.py` (360 casos) y los documentos sembrados de `tests/generar_docs.py`.

| Regla | Sev. | Imp. | Esf. | FP | Prioridad | Comprobación |
|---|---|---:|---:|---|---:|---|
| IEEE-007 | mayor | 3 | 2 | medio | 4.5 | `Wood et al. [7]` con 3 o más autores; con 1 o 2, todos los apellidos. Cruza `[n]` con los autores de su entrada y solo juzga la mención cuyo primer apellido es el de esa entrada (`In [3]`, `Ref. [3]`, `Fig. [2]` no cuentan); entradas con título entre comillas |
| APA-048 | mayor | 4 | 2 | alto | 4.0 | cita entre comillas de 6 o más palabras seguida de `(Autor, año)` sin `p.`, `pp.`, `párr.`, `cap.`, `sec.` ni otra ubicación. No cuenta: comillas cortas (ironía), títulos de artículos y obras tras `artículo`, `capítulo`, `titulado`…, comunicación personal; solo la cita autor-fecha pegada a las comillas (no la narrativa previa) |
| APA-032 | menor | 2 | 1 | bajo | 4.0 | un encabezado con exactamente un subencabezado del nivel siguiente (solo `.docx` con estilos de encabezado). Las muestras oficiales de APA lo incumplen en 3 secciones: son verdaderos positivos |
| APA-081 | mayor | 2 | 1 | bajo | 4.0 | URL de EBSCOhost, ProQuest, Ovid, Web of Science, Scopus, PsycNet, Gale o Nexis Uni. Quedan fuera `sciencedirect.com` (sitio de la editorial) y `jstor.org/stable` (las muestras oficiales de APA lo usan como enlace estable de un artículo sin DOI) y las tesis de ProQuest |
| APA-074 | menor | 2 | 1 | bajo | 4.0 | rango de páginas con `-` tras `pp.`, tras volumen y número o tras volumen; **corregible** (solo en la lista de referencias) |
| APA-080 | menor | 2 | 1 | bajo | 4.0 | una entrada con DOI y con otra URL. No es corregible: quitar la URL deja a veces `Recuperado de` suelto |
| APA-064 | mayor | 2 | 1 | bajo | 4.0 | 21 o más autores: 19 + `…` + el último, sin `&`; marca la lista completa de 21 o más y la elipsis con otro número de autores |
| IEEE-015 | menor | 2 | 1 | bajo | 4.0 | `REFERENCES`/`REFERENCIAS` con numeral romano o arábigo. Un rótulo con letra (`A. REFERENCES`) no se reconoce como lista |
| IEEE-070 | mayor | 2 | 1 | bajo | 4.0 | con 2 o más encabezados numerados, `REFERENCES` o `ACKNOWLEDGMENT` numerado (si los demás no se numeran, `REFERENCES` numerado sale como IEEE-015) |
| IEEE-031 | menor | 2 | 1 | bajo | 4.0 | `Vol.`, `No.`, `vol 5`, `no 3`, `pp 12`, `PP.`; `pp.` con guion o con una sola página; `p.` con rango. 5 ejemplos de la propia Reference Guide escriben `pp. 17-20` con guion (erratas de la guía, documentadas en la prueba) |
| IEEE-032 | menor | 2 | 1 | bajo | 4.0 | mes completo (`January`, `June`, `July`, `Sept.`) o sin punto (`Mar 2020`) junto a un año; no se juzga el título entre comillas, la cursiva, URL, datasets ni software; solo meses en inglés |
| APA-103 | menor | 2 | 1 | medio | 2.0 | siglas de 3 o más letras con puntos (`F.B.I.`, `E.U.A.`) y `Ph.D.`. No cuentan las de 2 letras (`U.S.`, iniciales), las iniciales seguidas de un apellido (`J.R.R. Tolkien`), las razones sociales (`S.A.P.I.`) ni lo citado entre comillas |
| IEEE-129 | menor | 1 | 1 | bajo | 1.0 | ™ o ® en el cuerpo (base IEEE) |

## No automatizables (se quedan en el agente)
Son de juicio puro, así que no se vuelven a puntuar: APA-053 (fidelidad de la cita textual), APA-057 (afirmaciones sin cita), APA-095 y APA-100 (permisos y copyright), APA-097 y APA-099 (contenido visual de figuras), APA-117 a APA-120 (tiempo verbal, voz, persona, antropomorfismo), APA-121 a APA-130 (lenguaje sin sesgo: requieren contexto), APA-132 y APA-139 (declaración de IA), IEEE-057 (datos inventados), IEEE-079 (uso de IA declarado), IEEE-100 a IEEE-104 (tipografía matemática en Word), IEEE-133 (imagen Lena).

Todas las demás reglas de agente que no aparecen arriba son de esfuerzo ≥ 3 (formato por tipo de referencia, portada, matemáticas en LaTeX, estilo en inglés). Se puntuarán ahora que las tandas 1 y 2 están cerradas.
