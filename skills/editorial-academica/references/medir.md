# Medir: márgenes, sangría y todo lo que el usuario pide

Antes de decir «los márgenes están mal» o «la sangría no es la pedida», se mide. `editorial.py medir` da el valor EFECTIVO (el que ve Word), no el que está escrito en un solo lugar del XML, y compara lo que el usuario pidió con equivalencias y tolerancias declaradas. Así no hay hallazgos falsos por tecnicismos (1.27 cm contra 0.5 in, «1.5» automático contra exacto 18 pt, un estilo que hereda la sangría de su base).

## Cuándo usarlo
- El usuario da una medida («márgenes de 3 cm a la izquierda», «sangría francesa de 1.27 cm en las referencias», «interlineado 1.5», «número de página arriba a la derecha»): conviértela en regla medible, mídela y reporta con el origen de su mensaje.
- Antes de afirmar un valor de formato: `medir <doc.docx>` da la ficha por sección y por grupo de párrafos, con cm, pt e in.
- Cuando hay un PDF (el que entregó el usuario, o `--render` con LibreOffice): `medir <doc.docx> --pdf doc.pdf` mide los márgenes reales, la posición del número en cada página y la sangría visible.

## Pasos
1. **Ficha**: `python <raíz>/scripts/editorial.py medir <doc.docx> [--pdf doc.pdf | --render] [--json ficha.json] [--seccion N]`.
   - Secciones: tamaño de página, márgenes (superior, inferior, izquierdo, derecho, encabezado, pie, canal), `w:pgNumType` (formato e inicio), primera página distinta y dónde va el número de página.
   - Grupos (portada, títulos 1-5, resumen, cuerpo, referencias, tablas, otros) y estilos: fuente, tamaño, interlineado como lo ve Word, espacio antes y después, sangría izquierda, derecha, de primera línea y francesa, alineación, color, negrita y cursiva. Cada atributo cuenta cuántos párrafos tienen cada valor y lista las excepciones con su número de párrafo y primeras palabras.
2. **Instrucción del usuario**: `... medir <doc.docx> --regla "márgenes 3 cm izquierda" --regla "sangría de primera línea 1.27 cm en el cuerpo"`. Cada una sale CUMPLE, NO CUMPLE o no medible, con lo que se pide, lo que hay, ejemplos y el origen. El código de salida es 1 si alguna no cumple.
3. **Persistirla**: si el usuario la da como regla del documento, guárdala en `.editorial.yaml`, en `medidas:` (con `origen: "usuario AAAA-MM-DD: «su frase»"`); `auditar` la evalúa como **INS-016** y las exigencias APA que contradice (APA-001 márgenes, APA-004 y APA-033 interlineado, APA-007 sangría, APA-006 justificado, APA-002 fuente, APA-008 número) pasan solas a excepción con ese motivo.
4. **Lo que no entiende, pregúntalo.** El parser devuelve `PREGUNTA:` con opciones; hazla al usuario (herramienta de opción múltiple o lista numerada) y repite con la respuesta. Nunca adivines una unidad, un alcance ni cuál de dos valores vale.
5. **Lo que no se puede medir, dilo**: «no medible: …» con el porqué (juicio de gusto, cuadro de texto, número con tabuladores sin PDF, alcance que el documento no tiene, interlineado «al menos»). Nunca lo des por bueno.

## Bloque `medidas:` de `.editorial.yaml`
```yaml
medidas:
  - {que: margenes, valor: 3, unidad: cm, tolerancia: 0.05, alcance: documento, origen: "usuario 2026-11-27: «márgenes de 3 cm»"}
  - {que: sangria_primera_linea, valor: 1.27, unidad: cm, alcance: cuerpo, origen: "guía p. 2: «sangría de 1.27 cm»"}
  - {que: interlineado, valor: 1.5, alcance: cuerpo, origen: "usuario 2026-11-27"}
  - {frase: "número de página arriba a la derecha", origen: "usuario 2026-11-27"}   # se parsea al leer; si no se entiende, error de uso
```
`que`: `margenes` (los cuatro) | `margen_superior|inferior|izquierdo|derecho` | `sangria_primera_linea` | `sangria_francesa` | `sangria_izquierda` | `sangria_derecha` | `interlineado` (valor 1, 1.5, 2; o N con `unidad: pt` = exacto) | `fuente` | `tamano` | `espacio_antes` | `espacio_despues` | `numero_pagina` (`superior derecha`, `inferior centro`, `ninguno`) | `alineacion` (justificada, izquierda, centro, derecha).
`alcance`: `documento` (cuerpo, títulos, resumen y referencias) | `todo` | `cuerpo` | `resumen` | `referencias` | `titulos` | `titulo N` | `portada` | `seccion N`. Los márgenes y el número de página son del documento o de una sección.
`perfilar` emite este bloque con los márgenes y la sangría de primera línea que la guía fija, cada uno con su cita de origen.

## Qué cuenta como equivalente (scripts/unidades.py)
- 2.54 cm = 1 in = 72 pt; 1.27 cm = 0.5 in = 36 pt; 1 in = 1440 twips = 914400 EMU; 12 pt = 24 medios puntos.
- Interlineado «1.5» = automático ×1.5 = exacto 18 pt con letra de 12 pt (múltiplo × tamaño). También se acepta exacto m × tamaño × 1.15, que es como Word dibuja un «1.5 líneas» automático (la altura natural de línea de Times New Roman, Calibri o Arial es ≈ 1.15 × el tamaño); es APROXIMADO y sale «equivalente» con su nota. «Al menos N pt» no se puede afirmar: no medible.
- Tolerancias por defecto: márgenes y sangrías ±0.05 cm, espacios ±0.5 pt, tamaño ±0.25 pt, interlineado ±0.02 (múltiplo) o ±0.5 pt. Una regla las cambia con `tolerancia` (en su unidad).
- Excepciones legítimas que no cuentan en las reglas de párrafo: imágenes, rótulos y notas de tabla o figura, citas en bloque, párrafos centrados, listas numeradas, entradas con sangría francesa (para la primera línea), palabras clave. El resultado dice cuántas excluyó.

## El PDF y las discrepancias
Se mide con PyMuPDF: caja de texto por página sin encabezado, pie ni número (mediana y percentiles), posición del número por página (superior/inferior; izquierda/centro/derecha), sangría visible de primera línea y francesa por geometría de líneas, paso de línea, fuentes y tamaños reales. Con texto no justificado el margen derecho medido es mayor que el real, y la caja de una línea incluye el aire de la tipografía: por eso el PDF solo AVISA de discrepancias con el .docx («discrepancia docx/PDF»), con tolerancias más anchas (`TOLERANCIA_PDF`), y nunca produce un hallazgo. Un PDF de LibreOffice usa fuentes sustitutas (Liberation Serif por Times New Roman): el aviso lo dice cuando son métricamente compatibles.
