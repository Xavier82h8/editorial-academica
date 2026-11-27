# Calificar y ajustar sin cambiar el trabajo (modo fiel)

Cuando el usuario **solo quiere calificar su proyecto y hacer ajustes**, el documento que vuelve a sus manos tiene que ser el suyo: mismo texto, misma estructura, mismas citas, mismas referencias, con el formato en regla. La skill no toma caminos distintos para eso: hay un solo camino, y es este.

## La regla

Si el usuario pide **calificar, revisar, ajustar, corregir el formato o dejarlo listo**:

- **No redactes, no reescribas, no cambies estructura, citas ni contenido.** No invoques `redactor` ni `corrector-estilo` salvo que el usuario lo pida con esas palabras («mejora la redacción», «corrige la gramática»).
- **Califica con `calificar`** (solo lectura): `python <raíz>/scripts/editorial.py calificar <doc.docx> [--perfil <id>]`. Una corrida hace auditar + estructura + congruencia + puntuar + medir, verifica el sha256 del archivo y de su carpeta antes y después y no escribe nada. Da el puntaje, los hallazgos por prioridad y los «ajustes sugeridos».
- **Ajusta con `corregir --fiel`**: `python <raíz>/scripts/editorial.py corregir <doc.docx> --fiel [--perfil <id>]`. Solo cambia propiedades de formato: márgenes, fuente y tamaño, interlineado, sangrías, espacios, alineación, paginación, bordes de tabla, saltos y que tablas y figuras no se partan. Nunca el texto.
- **Todo cambio de texto es una propuesta que el usuario aprueba.** Lo que cambiaría texto (rótulo de sección «Bibliografía» -> «Referencias», forma de las citas narrativas y su orden, orden y forma de las referencias, DOI como URL, puntuación junto a la cita, siglas, numeración y MAYÚSCULAS de los títulos, rótulos de tablas y figuras) sale en `<doc>.propuestas.json` y en una lista legible (id de propuesta, regla, párrafo, antes, después, motivo). El usuario elige; se aplica con `corregir <doc.docx> --fiel --aplicar-propuestas <doc>.propuestas.json --solo P001,P003` (ids de propuesta o reglas; sin `--solo`, todas).
- **Certificado de fidelidad.** Tras cada `corregir` sale `fidelidad: texto idéntico`, o la lista exacta de cambios de texto, cada uno clasificado: `texto aprobado` (propuesta que el usuario aprobó), `texto NO aprobado` o, en el modo completo, `texto por reglas`. En modo fiel, un cambio de texto no aprobado es un error (código 1) y no se escribe la salida. `editorial.py comparar original.docx corregido.docx` da lo mismo suelto, más el resumen de los cambios de formato por grupo.

## Decisión de diseño: dónde vive el modo fiel

`--fiel` es una opción de `corregir`, no el comportamiento por defecto de la línea de comandos. Motivo: `entregar`, `convertir` y las pruebas de siempre dependen de que `corregir` corrija también texto por regla (numerar y poner en mayúsculas los capítulos que pide una guía institucional, ordenar las referencias). Lo que sí es el valor por defecto es **la skill**: `/corregir`, `/calificar`, el agente `juez-formato` y el orquestador llaman a `corregir` con `--fiel` siempre que el usuario no haya pedido, con esas palabras, que se corrija o reescriba texto. El modo completo (`corregir` sin `--fiel`) solo se usa si el usuario lo pide («aplica todas las correcciones», «entrega el documento institucional») o dentro de `entregar`.

## Qué perfil se aplicó

Todos los comandos imprimen al inicio `perfil aplicado: X (origen: CLI | .editorial.yaml en <ruta>)` y el JSON lo guarda en `perfil_aplicado`. Un `--perfil` explícito gana sobre el `perfil:` del `.editorial.yaml` de la carpeta; si ese archivo declara otro perfil, o trae un bloque institucional (`formato:`, `vinculante:`, excepciones, medidas…), se ignora entero y se avisa en stderr y en el JSON («se ignora .editorial.yaml de <ruta>: declara X, pediste Y»). Para aplicarlo igual, `--equipo <ruta>`. Si el usuario trabaja en una carpeta institucional, no pases `--perfil`: el `.editorial.yaml` manda y la línea lo dice.

## Pasos

1. `calificar` -> enseña el puntaje y los hallazgos por prioridad. Nada se tocó (lo dice la salida).
2. Enseña los «ajustes sugeridos» en tres grupos: automáticos de formato; automáticos que cambian texto (quedan como propuesta); los que requieren al usuario (contenido, fuentes que faltan, secciones ausentes, congruencia).
3. Si el usuario pide ajustar: `corregir --fiel`. Enseña el certificado y la lista de propuestas.
4. Pregunta cuáles propuestas aprueba (herramienta de opción múltiple, o lista numerada) y aplícalas con `--aplicar-propuestas ... --solo ...`.
5. Vuelve a `calificar` sobre `<doc>.corregido.docx` para mostrar el puntaje nuevo.
6. Lo que requiere al usuario se dice tal cual; no se inventa ni se resuelve «por él».

## Límites conocidos

- El certificado compara el texto visible (párrafos, tablas, encabezados y pies sin el número de página, notas). Un cambio de numeración automática de Word (lista numerada de los títulos) no es texto en el XML: el modo fiel lo trata como cambio de texto y lo propone, pero el certificado suelto (`comparar`) no lo ve.
- Las propuestas se generan encadenadas con el corrector de cada regla; dos reglas que tocan el mismo párrafo dan dos propuestas, y la segunda ya incluye el efecto de la primera.
- Las reglas de texto que el corrector no sabe resolver (p. ej. citas legales sin año) no producen propuesta: salen como «requieren al usuario».
