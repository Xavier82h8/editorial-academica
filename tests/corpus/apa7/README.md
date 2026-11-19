# Corpus dorado APA 7

Fuente unica de verdad: snapshot oficial `normas/apa/pages/*.md` y `normas/apa/blog/*.md`. Cada `esperado` se copio literalmente del snapshot (verificado por script: la cadena existe en el archivo citado). Nada esta inventado salvo los items CSL de entrada.

## Archivos

- `referencias.json`: 83 casos de lista de referencias.
- `citas.json`: 42 casos de citas en el texto.

## Esquema de `referencias.json`

```json
{"id":"apa-ref-001","tipo":"articulo-revista-doi",
 "fuente":"<archivo del snapshot>#<encabezado>",
 "csl":{ "...CSL-JSON 1.0.2..." },
 "esperado":"Autor, A. (2019). Titulo. *Revista*, *8*(3), 207–217. https://doi.org/...",
 "notas":"...", "alcance":"solo-autores (opcional)"}
```

- `csl`: item CSL-JSON (`id` = id del caso). Pandoc lo consume dentro de `references:` o como `--bibliography`.
- `esperado`: cadena oficial; cursivas marcadas con `*...*` (como en el snapshot).
- `alcance: "solo-autores"` (apa-ref-083): el esperado es solo el bloque de autores (plantilla de 21+ autores).
- `notas`: elementos sin variable CSL estandar (postproceso), discrepancias del snapshot, riesgos de render.

## Esquema de `citas.json`

```json
{"id":"apa-cita-001","tipo":"un-autor","modo":"parentetica|narrativa",
 "items":[{"ref":"apa-ref-001"|"csl":{...},"locator":"","label":"page","prefix":"","suffix":""}],
 "contexto":[{csl}], "posicion":"primera|subsecuente", "abreviatura":"NIMH",
 "esperado":"(Luna, 2020)","fuente":"<archivo>","notas":"..."}
```

- `items`: obras citadas juntas, en el orden dado (el renderizador debe reordenar alfabeticamente cuando corresponda). Cada item usa `ref` (id de `referencias.json`) o `csl` inline.
- Los items `csl` inline son sinteticos y minimos (autor/anio/titulo ficticios): los ejemplos oficiales de citas usan apellidos sin entrada de referencia. Solo `esperado` es oficial.
- `contexto`: items presentes en la bibliografia pero no citados en este caso (necesarios para sufijos a/b y desambiguacion de "et al.").
- `posicion`/`abreviatura`: citas de autor grupal con abreviatura (primera vs. subsecuente). CSL no genera la abreviatura: postproceso.
- `items: []`: comunicacion personal; se compone como texto literal.
- `locator`/`label`: terminos de localizador CSL (`page`, `paragraph`, `chapter`...). Lo que CSL no soporta se emula con `prefix`/`suffix` (ver `notas`).

## Como comparar

1. Renderizar con pandoc (`--citeproc`, `apa.csl`) cada `csl` a bibliografia y cada caso de `citas.json` a cita.
2. Eliminar de ambos lados el marcador del snapshot `**opens in new window` y espacios finales (ya eliminados del `esperado`).
3. Normalizar espacios: colapsar `\s+` a un espacio, `strip()`, y NFC. Reemplazar NBSP por espacio.
4. Comparar el texto plano (sin `*`) con igualdad exacta.
5. Comparar la cursiva por separado: extraer los tramos `*...*` de cada lado (en el render: `<em>`/`\emph`/`*..*` de pandoc markdown) y comparar la lista de tramos. Tolerar que el snapshot parta o una cursivas contiguas (`*A*, *B*` vs `*A, B*`) fusionando tramos separados solo por signos de puntuacion.
6. Registrar cada diferencia como: parche CSL local (`plantillas/csl/apa-editorial.csl`), postproceso, o excepcion de snapshot.

## Excepciones y rarezas del snapshot

- Las paginas de blog (`blog__*.md`) no conservan cursivas: sus `esperado` no llevan `*`. No se pueden usar para validar cursivas.
- Algunos ejemplos del snapshot tienen errores de maquetacion: `Urdan T.` sin coma (apa-ref-030), `*Behavior Research Methods, 50*(2)` (cursiva incluye el volumen), `graduates *[Generative AI chat]` con espacio dentro de la cursiva, cursiva partida en `Proceedings ... *USA*`.
- apa-ref-083 usa la plantilla oficial con `Author, A. A.`; no es un ejemplo con nombres reales.
- Las localizaciones al espanol ("y" en vez de "&", "s.f.", "Recuperado") no estan en el corpus; este corpus es la verdad en ingles.

## Regenerar

El corpus se construyo con un script que busca cada `esperado` en el snapshot por prefijo de linea y falla si no existe, de modo que ninguna cadena esperada puede ser inventada. Si el snapshot cambia, volver a verificar que cada `esperado` siga presente.
