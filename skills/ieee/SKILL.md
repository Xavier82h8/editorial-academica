---
name: ieee
description: Use when writing, formatting or auditing a document in IEEE style (numbered citations, IEEE reference list, editorial style, equations, figures/tables), including when IEEE is only the base layout or only the citation layer of a combined profile.
---

# IEEE (módulo de conocimiento)

Reglas de estilo IEEE para redactar y auditar. Todo sale de documentos oficiales IEEE guardados en `normas/ieee/` (versiones y fecha de snapshot en `normas/VERSION`). Si una regla no está en esos documentos, NO se inventa: se reporta como "sin regla IEEE" (vacío). Texto del plugin en español; plantillas y ejemplos en inglés tal como los da IEEE; adaptaciones al español aparecen siempre rotuladas "Adaptación al español (convención, no regla oficial IEEE)".

## Fuentes y precedencia

1. PRIMARIAS (`normas/ieee/actual/`): Reference Guide V 3.28.2025 (`reference-guide.txt`), Editorial Style Manual actual (`style-manual.txt`), Editing Mathematics V 10.27.2023 (`math-guide.txt`), abreviaturas de revistas (`abreviaturas-revistas.csv`).
2. SECUNDARIAS (`normas/ieee/*.pdf|txt`): Reference Guide 2018, Style Manual 2024, Math Typesetting Guide for LaTeX Users. Sirven para lo que el export pierde (numeración de encabezados, apéndices de unidades) y para código LaTeX.
3. Conflicto entre fuentes: Reference Guide 2025 manda en formato de referencias y citas (p. ej. `Thm.`/`Sect.` frente a `Th.`/`Sec.` del Style Manual); Style Manual en texto del artículo; Math Guide en matemáticas; primaria sobre secundaria. El conflicto se registra (ver `references/referencias-principios.md` §6 y `references/citas-texto.md`). Hay contradicciones internas en el propio SM (cero decimal, `20%-30%`), anotadas en el checklist.

## Qué cargar (divulgación progresiva)

| Archivo en `references/` | Cargar cuando |
|---|---|
| `citas-texto.md` | escribir o auditar citas `[n]` en el cuerpo: rangos, et al., partes `[3, Fig. 1]`, ibid., renumeración |
| `referencias-principios.md` | formato general de la lista: autores, 6 autores, DOI/URL, fechas, `(n.d.)`, cambios 2018 a 2025 |
| `referencias-por-tipo-1.md` | referencias de blogs, libros, conferencias, cursos, datasets, handbooks, lecturas, legales, manuales |
| `referencias-por-tipo-2.md` | noticias, video, patentes, periódicos, reportes, software, normas, tesis, gobierno, no publicados, sitios web |
| `abreviaturas.md` | abreviar palabras y títulos de revistas/conferencias en referencias (apunta al CSV oficial) |
| `estilo-editorial.md` | estructura, encabezados I./A./1), título, abstract, figuras y tablas, listas, números, unidades, gramática, lenguaje inclusivo |
| `matematicas.md` | ecuaciones, numeración, cursiva/redonda, LaTeX (`align`, `cases`, `\left`) |
| `checklist.md` | auditar: reglas `IEEE-001` a `IEEE-140` con severidad, fix automático y fuente |

## Uso según perfil

- Perfil `ieee` completo: cargar todo lo anterior según la tarea.
- IEEE solo como BASE (maquetación) con citas de otra norma (`ieee-base+apa7-citas`): cargar `estilo-editorial.md`, `matematicas.md` y las secciones EST, FIG, MAT, MEC (IEEE-059 a IEEE-134, 139 y 140, salvo 135-138 que son REF). NO aplicar CIT ni REF.
- IEEE solo como CITAS (`apa7-base+ieee-citas`): cargar `citas-texto.md`, `referencias-*.md`, `abreviaturas.md` y las secciones CIT y REF (IEEE-001 a IEEE-058 y 135 a 138). La base (página, portada, encabezados, tablas, figuras) la gobierna la otra norma.
- Redactar: construir las referencias desde metadatos verificados (CSL-JSON) y contrastar con las plantillas; no inventar campos faltantes.
- Auditar: recorrer `checklist.md`, citar siempre ID y fuente en cada hallazgo; marcar vacíos de la norma como "sin regla IEEE" y las reglas [CONV] como convención.

## Las 10 reglas de mayor impacto (selección del plugin; no hay datos de frecuencia de error)

1. Citas `[n]` en la línea y DENTRO de la puntuación (`... as shown in [1].`); nunca autor-año. IEEE-001, 002.
2. Varias citas: `[1], [2], [3]`; los rangos `[1]–[4]` ya NO se usan (guía 2025): escribir `[1], [2], [3], [4]`. IEEE-003, 004.
3. Un número por referencia; cada fuente su número; sin "ibid." ni "op. cit."; las partes se citan `[3, Fig. 1]`. IEEE-009, 010, 018, 019.
4. Autores con inicial(es) ANTES del apellido (`J. K. Author`); hasta 6 autores todos; más de 6: primero + `et al.`; Jr./Sr. sin coma. IEEE-020 a 024.
5. Título de artículo entre comillas con la coma dentro; título de revista abreviado y en cursiva; `vol. x, no. x, pp. xxx–xxx, Mon. year, doi: ...`. IEEE-026 a 031.
6. DOI y fecha de acceso ANTES de la URL (`Accessed: ..., doi: ... [Online]. Available: URL`); punto final salvo que termine en URL. IEEE-037 a 041.
7. Referencias sin fecha llevan `(n.d.)`; ninguna referencia sin año ni datos inventados. IEEE-034, 057.
8. Figuras `Fig. 1.` (en texto siempre "Fig."); tablas `TABLE I` en romano, con descripción sin punto final. IEEE-084, 085, 089, 090.
9. Ecuaciones numeradas `(1)` consecutivas a la derecha; variables en cursiva; funciones (`sin`, `log`, `max`) en redonda; sin `$$` ni `eqnarray` en LaTeX. IEEE-096, 100, 101, 107.
10. Abstract en un párrafo de 150 a 250 palabras sin citas numeradas ni ecuaciones numeradas; Index Terms en orden alfabético; encabezados `I.` / `A.` / `1)`; `REFERENCES` y `ACKNOWLEDGMENT` sin numerar. IEEE-060 a 064, 066 a 068, 070.

Rangos del checklist: CIT 001-014, REF 015-058 y 135-138, EST 059-083 y 131, FIG 084-095 y 133, MAT 096-112, 132 y 134, MEC 113-130, 139 y 140. La fuente de verdad es `references/checklist.md`.

## Vacíos conocidos (no inventar)

- Las normas NO dicen textualmente que las referencias se numeren por orden de primera aparición ni cómo citar una tabla en texto (`Table I`). Tratar como convención del plugin y avisar.
- HUECO (maquetación de tesis o informe): ninguna fuente IEEE define portada, márgenes, tipografía, interlineado, numeración de páginas, tabla de contenido, capítulos ni páginas preliminares de una tesis o informe. El Style Manual es solo para artículos de IEEE Transactions/Journals/Letters (menciona una tesis únicamente en la primera nota al pie) y la guía LaTeX aclara que IEEEtran no es presentación final. Para esos puntos usar la plantilla del perfil/institución (Fase 3: perfil de equipo) y reportar "regla no definida por IEEE", nunca un ID IEEE. Lo que sí aplica a una tesis con maquetación IEEE: encabezados, figuras/tablas, ecuaciones, mecánica y citas/lista (ver `estilo-editorial.md` §14).
- Sin plantilla para leyes ni documentos de gobierno de países distintos de EE. UU., ni para grados de licenciatura en tesis.

## Adaptación al español (convención, no regla oficial IEEE)

- Encabezado `REFERENCIAS`; `et al.` sin traducir; marcadores `[Online]. Available:`, `Accessed:`, `doi:` en inglés por defecto (alternativa localizada solo si es consistente).
- `Fig. 1.` y `TABLE I` (o `TABLA I`) de forma consistente; coma decimal o punto decimal, uno solo en todo el documento.
- Reglas marcadas [EN] en el checklist (ortografía americana, contracciones, coma serial, fechas `4 June 2002`) no se exigen en español.

## Versiones

Fechas y versiones de las normas en `normas/VERSION` (snapshot 2026-11-18). Reference Guide 2025 vigente; la 2018 está superada. Si la consulta tiene más de 6 meses, sugerir `/actualizar-normas`.
