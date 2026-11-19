# Corpus dorado IEEE

Fuente única: `normas/ieee/actual/reference-guide.txt` (IEEE Reference Guide V 3.28.2025). Las cursivas salen de `reference-guide.html` (mismo documento). No se inventó ningún ejemplo: `esperado` es el texto oficial con su número de línea en el `.txt`.

## referencias.json

Arreglo de casos:

```json
{"id":"ieee-ref-001","tipo":"blog","variante":"...","fuente":"reference-guide.txt:126",
 "csl":{"id":"ieee-ref-001","type":"post-weblog", "...": "..."},
 "esperado":"A. Weissberger, “...,” *IEEE ComSoc Technol. Blog*, Sep. 23, 2024. [Online]. Available: ...",
 "comparable":true,"notas":"..."}
```

- `tipo`: familia de la guía (blog, libro, conferencia, curso, dataset, handbook, manual, lecture, legal, noticia, video, patente, periodico, informe, software, norma, tesis, gobierno, no-publicado, arxiv, sitio-web). `variante`: subsección o variante exacta.
- `fuente`: línea del `.txt` donde está el ejemplo (si la referencia se parte en dos líneas, es la primera).
- `csl`: CSL-JSON (variables y tipos de CSL 1.0.2) con `id` igual al del caso. Se construyó a mano a partir del ejemplo; es una interpretación y puede ajustarse, `esperado` no.
- `esperado`: ejemplo oficial sin el `[n]` inicial, cursivas como `*...*`. Cambios respecto al `.txt`: espacios duros (U+00A0) pasan a espacio normal y se recortaron las notas pegadas a la línea (`*** If the year...`, `*** Always use...`). Las erratas de la guía se conservan tal cual.
- `comparable`:
  - `true`: `ieee.csl` debería reproducirlo (ejemplos con formato estándar). Una diferencia es un defecto del CSL o del modelado, y se resuelve con parche en `plantillas/csl/ieee-editorial.csl` o con nota de postproceso.
  - `false`: la guía usa un estilo que `ieee.csl` no produce (formato antiguo `Autor. (Año). Título.`, legales, datasets, erratas de puntuación, etc.). Se espera diferencia: documentarla, no "arreglarla" a ciegas.
- `notas`: ambigüedades, erratas de la guía y decisiones de modelado.

## citas.json

```json
{"id":"ieee-cita-009","modo":"bracket|narrativa","lista":["ieee-ref-001", "..."],
 "items":[{"ref":"ieee-ref-005","locator":"Thm. 1","label":""}],
 "esperado":"[3, Thm. 1]","contexto":"...","fuente":"reference-guide.txt:99","notas":"..."}
```

- `lista`: orden de la bibliografía; la posición (base 1) es el número `[n]`. Es la forma de fijar la numeración (orden de aparición, `[CONV]`).
- `items`: referencias citadas juntas en una misma cita. `locator`/`label` son los de CSL; para Thm., Lemma, eq., Fig., Appendix, Sect., Ch., Algorithm CSL no tiene label equivalente, por lo que el texto va literal en `locator` con `label` vacío. Solo `pp.` usa `label: "page"`.
- `esperado`: solo el bloque entre corchetes. En `modo: "narrativa"` el nombre del autor es prosa y no se verifica por CSL; solo el número.
- La regla 2025: sin rangos (`[1], [2], [3], [4]`, nunca `[1]–[4]`).

## Método de comparación

1. Para cada caso `comparable:true`, renderizar `csl` con pandoc `--citeproc --csl plantillas/csl/ieee.csl` (bibliografía de un solo ítem) y quitar el `[n]` inicial.
2. Normalizar ambos lados antes de comparar: espacios múltiples a uno, comillas rectas a curvas, `–`/`-` en rangos de páginas no se unifican (se reporta).
3. Cursivas: comparar el texto con `*` y, aparte, sin `*`. La guía incluye en la cursiva el punto o la coma finales del título (`*Robot Vision.*`), mientras que CSL los pone fuera: tolerar mover signos de puntuación `.,` en el borde de la cursiva.
4. Resultado por caso: `idéntico`, `diferencia documentada` (con parche CSL o nota de postproceso) o `fallo`. Gate de la Fase 2: 100 % de los `comparable:true` idénticos o con diferencia documentada.
5. Citas: renderizar con pandoc `[@id1; @id2, p. 3]` (o equivalente) según `lista`/`items` y comparar el bloque entre corchetes.

## Ambigüedades de la guía (resumen)

Ver `notas` por caso. Las principales: ejemplos de formato antiguo que contradicen el formato básico, erratas de espaciado y comillas, dos versiones de un mismo ejemplo (RCA, Chiampi, Urazhdin), número de patente en tres formatos, `Art no.` sin punto, traductor con nombre completo, y la cursiva irregular (`Plastics, vol. 3, ...`, `Special Issue...`).
