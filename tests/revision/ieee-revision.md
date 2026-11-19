# Revisión cruzada del módulo IEEE (Fase 2, ítem 1)

Fuentes usadas: `normas/ieee/actual/` (Ref Guide V 3.28.2025 txt + html con cursivas, Style Manual actual, Math Guide V 10.27.2023, CSV). Secundarias solo para historia/desempate. Verificación mecánica: todos los ejemplos entre backticks de `referencias-por-tipo-1/2.md` se compararon carácter a carácter (sin espacios ni `*`) contra `reference-guide.txt`; las cursivas contra el HTML; las 306 abreviaturas de palabras (§IV.A) y 38 títulos de revista contra la guía y el CSV (0 diferencias salvo `Proc. IEEE`, que está en el CSV en celda multilínea).

| ID/ubicación | Clasificación | Problema | Corrección aplicada | Fuente |
|---|---|---|---|---|
| IEEE-001 | IMPRECISE | "nunca autor-año" choca con `Brown [4]` permitido | Se admite nombre junto al número | Ref Guide §I.A |
| IEEE-003 | UNSUPPORTED (parcial) | `[1, 2]` no está prohibido textualmente | Marcado "prohibición implícita" | Ref Guide §I.A |
| IEEE-005 | IMPRECISE | "ref. [n]" no prohibido (el SM mismo lo usa) | Solo "in reference [n]" | SM p.14 |
| IEEE-009, 010 | IMPRECISE | Fix auto "sí" exige renumerar/reescribir | Fix = no | Ref Guide §I.B |
| IEEE-011 / Thm.-Sect. | OK con conflicto | Ref Guide 2025 `Thm.`/`Sect.`; SM p.14 `Th.`/`Sec.` (idénticos a Ref Guide 2018: vestigio) | Gana Ref Guide (más específica y nueva); `Th.`/`Sec.` se aceptan, solo se reporta mezcla | Ref Guide §I.B; SM p.14; Ref Guide 2018 |
| IEEE-012, 017 | IMPRECISE | Fuente implícita; fix 017 exige renumerar | Tag "(implícito)"; 017 fix=no | Ref Guide §II |
| IEEE-013 | IMPRECISE | Tag mezclaba norma y convención | [CONV] primero | Ref Guide §I.A |
| IEEE-014 / orden primera aparición | OK como [CONV] | Rastreo en 8 textos: ninguna fuente lo dice; solo figuras/tablas (SM p.14). Severidad mayor no cabe en una [CONV] | Confirmado [CONV]; severidad menor; fix=no; citas-texto §6 actualizado | grep Ref Guide 2018/2023/2025, SM actual/2024, Math |
| IEEE-020 | IMPRECISE | Fix auto sí ambiguo con apellidos compuestos | Fix = no | Ref Guide §II |
| IEEE-021 | IMPRECISE | Omitía la excepción no-IEEE | Añadida | Ref Guide §II |
| IEEE-026 | IMPRECISE | No cubría título terminado en `?` | Añadido | Ref Guide §J ejemplos |
| IEEE-027 | IMPRECISE | Lista de cursivas incompleta (video, software) y conferencia "presented at" no va en cursiva | Corregido con HTML | Ref Guide HTML |
| IEEE-030 | WRONG (severidad) | Crítica para orden de campos; no invalida citación | Mayor | Ref Guide §M |
| IEEE-032 | IMPRECISE | La guía no lista meses; dataset/software usan mes completo | Lista de formas vistas, sin `Sept.`, excepción documentada | Ref Guide §II, §E, §O |
| IEEE-042 | IMPRECISE | "sin fecha estable" no está en la fuente; ejemplos con mes completo y sin `:` | Reescrita; fix=no | Ref Guide §III |
| IEEE-043 | OK | `[Online.]` con punto en la fuente | Nota de consistencia | Ref Guide §T |
| IEEE-045 | WRONG | Plantilla omitía nombre del editor (`X. Editor, Ed.`) | Corregida | Ref Guide §B |
| IEEE-046 | IMPRECISE | "sin of the" (la guía dice "most"); faltaba `USA` | Corregida | Ref Guide §C |
| IEEE-052 | UNSUPPORTED | "in press" no aparece en la guía; fix no mecánico | Quitado; fix=no | Ref Guide §M |
| IEEE-054 | IMPRECISE | Regla compuesta (arXiv + comunicación privada) | Dividida: 054 arXiv, nueva 136 | Ref Guide §S |
| IEEE-055 | IMPRECISE | Exigía URL/DOI; ejemplo MSDN no la tiene | Corregida | Ref Guide §O |
| IEEE-058 | OK [CONV] | Única [CONV] con severidad mayor | Excepción declarada en cabecera | política del plugin |
| IEEE-063, 075, 086, 105, 106, 107, 108, 109, 130, 091, 096 | IMPRECISE | Fix auto "sí" no es mecánico o exige renumerar/criterio | Fix = no; criterio definido en cabecera | SM / Math guides |
| IEEE-069 | UNSUPPORTED | "no se saltan niveles" no está en la norma | [CONV] | SM p.11 |
| IEEE-076 | IMPRECISE | Ejemplo "DC, no dc" inventado | Eliminado | SM p.5 |
| IEEE-079 | IMPRECISE | Faltaba excepción edición/gramática | Añadida | SM p.13 |
| IEEE-085 | IMPRECISE | "debajo" solo explícito para apaisadas | Anotado | SM p.14-15 |
| IEEE-093 | UNSUPPORTED | "implícito" citado como regla textual | [CONV] | SM p.25 |
| IEEE-094 | WRONG (página) | §F está en p.25, no p.24 | Corregida | SM índice |
| IEEE-095 | IMPRECISE | Omitía caso de editores no IEEE | Añadido | SM p.15 |
| IEEE-097 | OK | Compatible con Math Guide §F y SM p.13 | Fuentes completadas | Math §F; SM p.13 |
| IEEE-100 | WRONG (fuente) | Citaba Math Guide §H, que no dice "variables en cursiva" | Fuentes: SM Math 1, SM p.25, Math LaTeX p.2 | SM; Math LaTeX |
| IEEE-102 | IMPRECISE | Tres fuentes con matices distintos (usually boldface italic / always bold) | Matices explícitos | Math §G; SM; LaTeX p.2 |
| IEEE-104 | IMPRECISE | Faltaba excepción de subíndice de una letra | Añadida | SM p.25 |
| IEEE-110 | OK | Soportada | Fuente precisada (Rule 3) | Math §B; LaTeX p.11-12 |
| IEEE-112 | OK con conflicto | Math Guide §B R2 lo manda; SM Math 9 "not a necessity" | Conflicto anotado | Math §B; SM |
| IEEE-114 | IMPRECISE | Mezcla SM actual (micron, cps) y PDF 2024 (amp, db, b/s) | Separado por fuente | SM Math 8; SM 2024 App. C |
| IEEE-119 | OK con conflicto | SM Math 3 "siempre" vs "§Percentages: si hace falta" | Anotado | SM p.24 |
| IEEE-120, 122 | OK con nota | SM escribe `20%-30%` con guion; regla 122 pide en dash | Anotado | SM p.24 |
| IEEE-121, 123 | IMPRECISE | Faltaba marcador [EN] / fuentes (p.21, p.26) | Corregido | SM |
| IEEE-130 | IMPRECISE | "resaltados" se pierde en el export; fix no mecánico | Anotado; fix=no | SM p.17, App. E |
| Nuevas 131-139 | Nuevas | Huecos de cobertura | 131 cuaternarios; 132 tan/cot/csc/Pr; 133 Lena; 134 espacio fino; 135 blog/noticia; 136 no publicado; 137 manual/handbook; 138 dataset; 139 artículo por sonido | SM; Math Guide; Ref Guide |
| Resto de reglas (002, 004, 006-008, 015-016, 018-019, 022-025, 028-029, 031, 033-041, 044, 047-051, 053, 056-057, 059-062, 064-068, 070-074, 077-078, 080-084, 087-090, 092, 098-099, 101, 103, 111, 113, 115-118, 124-129) | OK | Verificadas contra texto; sin cambio sustantivo (algunas con aclaraciones menores) | Sin cambio | SM / Ref Guide / Math |
| referencias-por-tipo-1 §E Dataset | WRONG | Ejemplo terminaba `version/2`; la fuente termina `version/` | Corregido | Ref Guide §E |
| referencias-por-tipo-2 §O | WRONG | `MSDN Library...` sin cursiva; en el HTML sí | Cursiva | Ref Guide HTML |
| referencias-por-tipo-2 §P | WRONG | Ejemplo ITU sin cursiva (HTML la tiene en el título, con anomalía en "Switzerland,") | Título en cursiva completa | Ref Guide HTML |
| referencias-por-tipo-2 §M Early Access | IMPRECISE | Plantilla replicaba errata (`Periodical., Abbrev. month`, sin "early access") | Plantilla alineada al ejemplo + nota de errata | Ref Guide §M |
| referencias-por-tipo-2 §M Online | IMPRECISE | `10.1109.XXX` errata de la fuente | Nota | Ref Guide §M |
| referencias-por-tipo-1/2 (resto de ejemplos) | OK | Coincidencia exacta carácter a carácter (incluidos typos de la fuente) y cursivas con HTML | Sin cambio | Ref Guide txt/html |
| abreviaturas.md | OK | 306/306 palabras, 38/38 revistas, ejemplos §IV.C y editoriales verificados | Sin cambio | Ref Guide §IV; CSV |
| referencias-principios.md §6 (2018 vs 2025) | OK | Rangos, Jr./Sr., Th./Sec., sitio web, n.d. verificados contra Ref Guide 2018 | Sin cambio | Ref Guide 2018 |
| estilo-editorial §3 | WRONG | `Manuscript received` (PDF 2024); el SM actual dice `Received` | Corregido | SM p.6 |
| estilo-editorial §4 Abstract | WRONG | "números y unidades en redonda"; el SM dice "remain bold" | Corregido | SM p.10 |
| estilo-editorial §6 | IMPRECISE | "CRediT" no figura en el SM ("credit statements") | Corregido | SM p.13 |
| estilo-editorial §2 | UNSUPPORTED | Ejemplo DC/dc | Aclarado | SM p.5 |
| matematicas §3 cabecera / §5 | WRONG (tags) | Citaba §H como fuente; tipografía de fuentes está en SM Apéndice IV.2 no en Math 24; MathType/MathJax en p.20 no p.21 | Corregidos | Math; SM; LaTeX p.20 |
| matematicas §3 `sgn` | WRONG | Decía que LaTeX guide "añade sgn"; también está en Math §L | Corregido | Math §L |
| matematicas §H italic/roman/small caps | Laguna confirmada | El txt aplana la tabla; no hay otra copia en el repo | Documentadas solo las asignaciones confirmadas por SM 2024 App. D y SM p.23 | Math §H; SM |
| SKILL.md | IMPRECISE | "Las 10 más violadas" sin datos; "sin citas ni ecuaciones" en Abstract; precedencia ambigua entre primarias; huecos de tesis poco visibles; rangos | Retitulado; reescritos; hueco de tesis/informe en viñeta propia y explícita | SM; Ref Guide |

## Totales (139 reglas = 130 originales + 9 nuevas)

- Reglas originales revisadas: 130. OK sin cambio: ~75. OK con cambio de fuente/matiz o conflicto anotado: ~14. IMPRECISE: 30. UNSUPPORTED: 5 (003 parcial, 052, 069, 093, 076 ejemplo). WRONG: 4 (030 severidad, 045 plantilla, 094 página, 100 fuente). Retiradas: 0.
- Severidades cambiadas: 014 (mayor a menor), 030 (crítica a mayor). Fix auto cambiado de sí a no: 009, 010, 014, 017, 020, 052, 063, 075, 086, 091, 096, 105, 106, 107, 108, 109, 130 (17).
- Reglas nuevas: 9 (IEEE-131 a 139).
- Plantillas/ejemplos de referencias: 5 errores reales (dataset `version/2`, cursiva MSDN, cursiva ITU, plantilla Early Access, nota de errata Online) de ~110 ejemplos comparados.
- Estilo/matemáticas/SKILL: 9 afirmaciones WRONG/IMPRECISE corregidas.
- Los conteos por clase son aproximados para el bloque "OK"; las filas de la tabla son exhaustivas para todo lo no-OK.

## Preguntas abiertas
1. Math Guide §H (cursiva/redonda/versalitas): sin copia fuente con columnas; ¿se aporta el Google Doc o PDF original?
2. `Thm.`/`Sect.` vs `Th.`/`Sec.`: resuelto a favor de la Ref Guide 2025 (aceptando las otras). ¿Se prefiere que el juez las reporte como menor?
3. Cero decimal (SM Math 3 vs §Percentages): se exige el cero; confirmar política.
4. Hueco de maquetación de tesis/informe: sigue abierto por diseño (perfil de equipo, Fase 3).
5. IEEE-058 es [CONV] con severidad mayor (excepción declarada); ¿mantener?
6. Las páginas `SM p.N` derivan del índice del export (no hay numeración de página en el txt); no verificables al 100 %.
