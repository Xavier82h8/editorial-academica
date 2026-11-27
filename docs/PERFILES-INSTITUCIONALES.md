# Perfiles institucionales

Una escuela puede pedir un formato que difiere de APA 7 o de IEEE (interlineado, justificado, encabezados numerados en mayúsculas, tablas al estilo IEEE, portada propia). Un perfil institucional lo declara en un `.editorial.yaml` y una estructura de género lista las secciones que su guía exige. El revisor informa lo que la guía cambia como «excepción institucional», con su motivo, y no como error.

**Generar el perfil desde la guía.** En vez de escribir el `.editorial.yaml` a mano, `python scripts/editorial.py perfilar <guia.pdf|docx> [--modelo-portada <pdf|docx> --pagina N] --estructura-id <id>` lo propone a partir de la guía de tu escuela: cada valor trae su origen (`guía p. N: «cita literal»`), la estructura de capítulos queda en `estructuras/<id>.yaml` y lo que la guía no dice se pregunta (ver `skills/editorial-academica/references/perfilar.md`). Si ya hay un `.editorial.yaml`, lo deja intacto y escribe `.editorial.propuesto.yaml` con un diff legible.

## Ejemplo incluido: protocolo de Taller de Investigación I (TNE, Instituto Tecnológico de Ejemplo, ciclo 2026)

Basado en la guía institucional ITE 2026 (no se distribuye). Son dos archivos:

- `perfiles/instituto-ejemplo-protocolo.editorial.yaml`: perfil de equipo. Base APA 7, estructura `protocolo-instituto-ejemplo`, español, voz impersonal, portada sin número, `tablas_figuras: ieee` y un bloque `formato:` con lo que la guía exige (1.5, justificado, nivel 1 en mayúsculas y numerado, página nueva por capítulo, romanos y arábigos, título de 20 palabras, 70 % de fuentes de los últimos 5 años, voz impersonal) y una excepción con motivo por cada regla APA que la guía cambia y que `formato:` no deriva sola (niveles 2 a 5, lista titulada «Fuentes de información», portada oficial, orden de páginas con índices).
- `estructuras/protocolo-instituto-ejemplo.yaml`: resumen de 150-250 palabras con 3-5 palabras clave, tres índices y los 12 capítulos con sus subcapítulos.

### Uso

1. Copia el perfil a la carpeta del protocolo con el nombre `.editorial.yaml`:
   `cp perfiles/instituto-ejemplo-protocolo.editorial.yaml <carpeta del protocolo>/.editorial.yaml`
2. Audita y revisa la estructura; el perfil y la estructura se toman del `.editorial.yaml`:
   `/auditar protocolo.docx` y `/estructura protocolo.docx`. `/puntuar` y `/corregir` también lo leen.
3. Lee las líneas `EXCEPCIÓN INSTITUCIONAL`: son lo que APA pide y la guía cambia. Todo lo demás es un hallazgo.

### Qué comprueba y qué no

Comprueba: citas y lista APA 7; rótulos de tablas y figuras al estilo IEEE (`TABLA I` arriba y en mayúsculas, `Fig. 1.` debajo de la imagen, numeración consecutiva, primera mención en orden y antes de que aparezcan); presencia y orden de las secciones; Resumen de 150-250 palabras con 3-5 palabras clave (EST-004); portada sin número; y, con el bloque `formato:`, el formato propio de la guía (reglas INS, abajo).

No comprueba: el tiempo verbal, la coherencia Problema → Pregunta → Objetivo → Hipótesis ni la calidad de las fuentes; los cubren `/fuentes`, `/congruencia` y la revisión del agente con la lista de cotejo de la guía. `minimo_fuentes`, `tiempo_verbal` y `idioma` del perfil son datos orientativos.

## Formato institucional: el bloque `formato:` (reglas INS)

Una excepción solo quita exigencias de APA. Para EXIGIR el formato de la escuela, el `.editorial.yaml` lleva un bloque opcional `formato:`; sin él no corre ninguna regla INS y nada cambia. Todas las claves son opcionales y cada una activa su regla. Solo se evalúan `.docx`.

| Clave | Regla | Sev. | Qué exige |
|---|---|---|---|
| `interlineado: 1.5` | INS-001 | mayor | Interlineado de los párrafos de cuerpo y de las entradas de la lista. Se exentan tablas, rótulos, notas, líneas centradas, texto menor de 12 pt y el anexo. `2` = doble. |
| `alineacion: justificada` (o `izquierda`) | INS-002 | mayor | Alineación del cuerpo. Se exentan la lista de fuentes (sangría francesa), listas numeradas, citas en bloque, rótulos y líneas centradas. |
| `nivel1: {mayusculas: true, numerado: true}` | INS-003 | mayor | Nivel 1 en MAYÚSCULAS y numerado «N.» consecutivo. Resumen, índices y similares no se numeran; «Fuentes» y «Anexos» sí. |
| `niveles_numerados: true` | INS-004 | mayor | Nivel 2 «N.k.» con el número de su capítulo, consecutivo. |
| `capitulo_pagina_nueva: true` | INS-005 | mayor | Cada nivel 1 empieza en página nueva (salto directo, del estilo, o de sección). |
| `paginacion: {portada: sin_numero, preliminares: romanos, cuerpo: arabigos, posicion: pie_derecha}` | INS-006 | mayor | `posicion` (`encabezado_derecha`, `pie_derecha`, `pie_centro`) fija dónde va el número: se comprueba en cada sección, `/corregir` lo usa sin `--paginacion` (modos `encabezado-derecha`, `pie-derecha`, `pie-centro`; `pie` y `encabezado` son alias) y APA-008 pasa a excepción derivada si no es `encabezado_derecha`; EST-010 propone esa posición. |
| (cont. INS-006) | Portada sin número visible; secciones de preliminares en `lowerRoman`; secciones de cuerpo en `decimal` y reiniciadas en 1. Requiere saltos de sección entre portada, preliminares y cuerpo. `portada: sin_numero` equivale a `portada_numero: no`. |
| `titulo_max_palabras: 20` | INS-007 | menor | Título de la portada (estilo Title, o la línea más larga que no es etiqueta de la portada). |
| `fuentes_recientes: {anios: 5, porcentaje: 70, arbitradas: true}` | INS-008 | menor | Con `arbitradas: true` solo cuenta como reciente la fuente de nivel A o B (norma, revista arbitrada, actas, libro; `scripts/niveles.py`). Porcentaje de referencias con año ≥ año actual − años, **sobre la literatura actualizable**. Salen del cálculo las fuentes documentales (leyes y diarios oficiales, licencias, `[Conjunto de datos]`, `[Software]`, `[Directorio…]`; se detectan solas, y `documentales:` añade más) y las obras fundacionales que el documento usa (instrumento, prueba estadística o teoría original), declaradas en `fundacionales:` como `{ref: "Brooke, J. (1996)", motivo: "…"}`; sin `motivo` no se excluyen. `/auditar` lista cada exclusión con su motivo y avisa si las fundacionales pasan del 40 %. `anio_actual:` fija el año (por defecto el de hoy); «s. f.» cuenta como no reciente. |
| `voz: impersonal` | INS-009 | menor | Primera persona en el cuerpo: nosotros, nuestro/a/s, yo, «mi proyecto», y una lista conservadora de verbos («realizaremos», «proponemos», «creemos»…). Se ignoran las citas entre comillas. |

| `portada: {campos, fecha: mes_anio, numero_control: true, logos: […]}` | INS-010 | mayor | Portada oficial. `campos` es la lista ordenada de lo que debe aparecer, cada uno con `nombre` y `literal` (texto contenido, sin distinguir mayúsculas ni acentos) o `patron` (regex; usa `(?i:…)` si no debe distinguir mayúsculas); `{nombre: título del proyecto}` sin patrón exige un título (estilo Title, o una línea de 5 palabras o más que no sea etiqueta). Falta, o fuera de orden, es hallazgo. `fecha: mes_anio` acepta «Noviembre 2026» y «noviembre de 2026» y rechaza dd/mm/aaaa y «03/Noviembre/2026». `numero_control: true`: cada integrante con 8 dígitos o letra y 8 dígitos (un `[[PENDIENTE]]` cuenta como falta). `logos` solo cuenta imágenes en la portada o en el encabezado de la primera página: si faltan, es un aviso y no un hallazgo. |
| `fuente: {nombre: Times New Roman, pt: 12}` | INS-011 | mayor | Fuente y tamaño del texto de los encabezados y pies de página (y color negro o automático). `/corregir` lo arregla. |
| `resumen: {palabras: [150, 250], sangria: false, un_parrafo: true, palabras_clave: [3, 5]}` | INS-012 | mayor | Resumen: número de palabras, un solo párrafo (sin contar la línea de palabras clave), sin sangría de primera línea y número de palabras clave. `/corregir` quita la sangría. |
| `rotulos_pt: [8, 9]` | INS-013 | menor | Tamaño de los rótulos «TABLA N» y «Fig. N.». `/corregir` los lleva al límite más cercano. |

Además, `/estructura` revisa EST-017: el índice de contenido (campo TOC o escrito bajo «Índice») debe coincidir con los encabezados de nivel 1 a 3, y los índices de tablas y de figuras con los rótulos (se compara lo que el índice muestra, no el campo; se actualiza en Word).

Las severidades: mayor lo que se ve a simple vista en cada página (001-006, 010-012); menor lo que exige juicio o edición del autor (007-009, 013). Cuentan en la dimensión «Formato» de `/puntuar` como cualquier otro hallazgo.

**Excepciones derivadas.** Lo declarado en `formato:` convierte solo en excepción institucional las reglas APA que lo contradicen: `interlineado` distinto de 2 → APA-004 y APA-033; `alineacion: justificada` → APA-006; `nivel1.mayusculas` → APA-025 (mayúsculas); `nivel1.numerado` o `niveles_numerados` → APA-030. Las excepciones explícitas siguen funcionando y se suman. Un valor no reconocido en `formato:` sale como aviso y se ignora.

**`/corregir` con `formato:`.** Aplica el formato institucional en lugar del de APA donde chocan (y no aplica las correcciones APA que el perfil anula): interlineado y alineación del cuerpo (INS-001, INS-002), nivel 1 en mayúsculas (INS-003) y centrado y negritas (APA-025), numeración «N.» y «N.k.» solo si no hay y los capítulos ya numerados coinciden con su posición (si no, lo avisa y queda manual), página nueva por capítulo (INS-005), sangría de 1.27 cm y Times New Roman 12 en títulos (APA-007, APA-003). Con `tablas_figuras: ieee` convierte «Tabla N» en «TABLA <romano>» con el título en mayúsculas encima, «Figura N» + título en «Fig. N. Título» debajo de la imagen, y las menciones («Tabla 3» → «TABLA III», «Figuras 2 y 3» → «Figs. 2 y 3»). INS-006: inserta saltos de sección entre portada, preliminares y cuerpo y fija `lowerRoman` desde i y `decimal` desde 1 (solo `w:sectPr` y `w:pgNumType`; el número visible lo sigue poniendo el campo PAGE del encabezado; si el límite cae junto a una tabla, queda manual). También INS-011 (fuente, tamaño y color negro de encabezados y pies), INS-012 (quita la sangría del resumen) e INS-013 (tamaño de los rótulos). Siguen manuales INS-007 (acortar el título), INS-008 (buscar fuentes más recientes), INS-009 (reescribir en voz impersonal), INS-010 (portada oficial), INS-015 (reproducir el modelo) y EST-017 (actualizar el índice en Word).

**Claves de primer nivel que acompañan a `formato:`.** `titulo: "…"` fija el título elegido con `editorial.py titulo` (vinculante: la portada debe coincidir, INS-010; CON-021 lo contrasta con el objetivo general). `titulo_config: {max_palabras, sobran, promesas}` ajusta el diagnóstico. `fuentes: {niveles: true}` hace que `/auditar` añada FUE-V4N (afirmación sustantiva solo con fuentes de nivel D/E; `/puntuar` la calcula siempre). El mismo bloque admite `minimo_nivel: B` (cada referencia de nivel B o mejor, salvo documentales y fundacionales declaradas; menor), `porcentaje_arbitradas: 70` (al menos ese porcentaje de referencias de nivel A o B; mayor) y `evitar: [wikipedia, blog, foro]` (dominios y tipos de fuente que la guía no admite; mayor), todos con la regla FUE-NIV; sin ellos no corre. `editorial.py fuentes --reemplazar` propone con qué sustituirlas.

**Portada construida por el plugin.** `formato: portada: campos:` fija los campos y su orden; `portada: logos:` acepta nombres sueltos (`[SEP, TNE, ITE]`: solo avisa si faltan imágenes) o `[{nombre, ruta, alto_cm}]` (rutas relativas al `.editorial.yaml`; `editorial.py portada` pone la fila de logos arriba y deja el hueco si falta el archivo). Con un `vinculante` tipo `modelo` de ámbito `portada`, `editorial.py portada` la reproduce: marca cada línea de la spec medida con `"campo": "<nombre del campo>"` (las líneas sin marca se asocian por su contenido), `"nombre_negrita": true` en las líneas «Nombre — No. de control» y `"y_fija": true` en el pie que va en posición absoluta. INS-015 compara las líneas en orden: la spec debe tener tantas líneas de título e integrantes como la portada final.

## Medidas pedidas: el bloque `medidas:` (INS-016)

Márgenes, sangrías, interlineado, fuente, tamaño, espacios, número de página y alineación que el usuario (o la guía) fija como valor medible: `medidas: [{que, valor, unidad, tolerancia, alcance, origen}]` (o `{frase: "…", origen: "…"}`, que se parsea al leer). `auditar` mide el valor efectivo del .docx (`editorial.py medir`) y emite INS-016 (mayor) con el origen; la exigencia APA equivalente (APA-001, APA-004, APA-033, APA-007, APA-006, APA-002, APA-008) pasa sola a excepción. `perfilar` lo rellena con los márgenes y la sangría de primera línea de la guía. Detalle en `skills/editorial-academica/references/medir.md`.

## Formato vinculante: el bloque `vinculante:` (INS-015)

Lo que el usuario da como formato, modelo o instrucción es regla y se cumple al pie de la letra: se mide, se registra y se reproduce; si algo no cabe o contradice la norma, se pregunta; nunca se adapta en silencio. Decoración libre (p. ej. logos) solo si el usuario lo dice.

```yaml
vinculante:
  - id: portada-modelo
    origen: "captura 26-nov"        # de dónde viene (captura, guía p. 1, mensaje)
    fecha: 2026-11-26
    tipo: modelo                    # modelo (spec medida) | instruccion (texto)
    spec: portada-modelo.json       # ruta relativa a .editorial.yaml
    ambito: portada                 # portada | documento | seccion:<nombre>
  - id: resumen-intacto
    origen: "mensaje 26-nov"
    fecha: 2026-11-26
    tipo: instruccion
    texto: "El resumen queda como lo dio el usuario"
    ambito: "seccion:Resumen"
```

- **Medir.** `python scripts/editorial.py modelo medir modelo.pdf --pagina 1 --out portada-modelo.json` (PDF con PyMuPDF; también `.docx`). Por línea: texto, fuente, pt, negrita, cursiva, color, alineación, espacio previo; y las cajas (rellenos y barras de borde con color y grosor, con las líneas que acompañan). Marca a mano en la spec las líneas `"fijo": true` (texto literal obligatorio) o `"campo": "nombre"` (contenido variable con el mismo estilo); sin marca cuentan como campo. `modelo comparar documento.docx spec.json` muestra las diferencias sin correr el juez.
- **INS-015 (mayor).** Compara el ámbito con la spec: orden, texto fijo, fuente, tamaño (tolerancia 0.5 pt), negrita, cursiva, color, alineación y cajas. Cada diferencia es evidencia. El estilo de un `.docx` se resuelve como Word: run, estilo de carácter, estilo de párrafo y bases, docDefaults.
- **Instrucciones.** No las comprueba un script: el agente las reproduce y el juez las lista en los avisos.
- **Precedencia.** vinculante > perfil de equipo (`formato:`, `excepciones:`) > norma base (APA, IEEE) > estructura de género.
- **`/corregir`.** Nunca aplica reglas de cuerpo dentro de la portada de un perfil institucional ni de un ámbito vinculante (un modelo, o una instrucción con ámbito distinto de `documento`): esos bloques salen tal cual. Con o sin perfil, APA-005 y APA-093 no tocan la portada.
- Una entrada inválida (tipo desconocido, falta `origen`, `fecha`, `texto` o `spec`, spec ilegible, ámbito malo) es error de uso: código 2 con el motivo.

## Hacer el perfil de otra escuela a partir de su guía

1. **Copia el ejemplo.** `perfiles/equipo-ejemplo.editorial.yaml` (genérico) o el de ITE como punto de partida; guárdalo con el nombre de tu institución, p. ej. `perfiles/<institucion>-<documento>.editorial.yaml`.
2. **Fija los valores por defecto.** `perfil:` (`apa7`, `ieee`, `apa7-base+ieee-citas`…), `estructura:` (género o la tuya), `idioma:`, `voz:`, `portada_numero: si|no`.
3. **Declara el formato que exige la guía en `formato:`** (interlineado, alineación, nivel 1, numeración, páginas, título, fuentes recientes, voz: ver la tabla de arriba). **Lista lo demás que la guía cambia respecto de la norma.** Para cada formato de la guía busca la regla en `docs/REGLAS.md` (por ejemplo APA-004 interlineado, APA-006 alineación, APA-025 a APA-030 encabezados, APA-059 título de la lista, APA-001 márgenes) y crea una excepción `regla:` con `motivo:` que cite la guía y el apartado. Usa `si_contiene:` cuando la guía solo cambia un valor (p. ej. `"1.5"` en APA-004): así un interlineado distinto sigue siendo error. Una excepción sin `si_contiene` oculta todos los hallazgos de esa regla.
4. **Tablas y figuras de otra norma.** `tablas_figuras: ieee` sobre base APA pasa APA-089 y APA-090 a excepción y activa IEEE-085, 089, 091, 092 y la mención previa (APA-091).
5. **Escribe la estructura.** Copia `estructuras/protocolo.yaml` (o la de ITE) como `estructuras/<id>.yaml`. Por sección: `nombre`, `alias` (sin numeración, acentos ni mayúsculas: se normalizan; evita alias de una sola palabra que aparezcan en otros títulos), `obligatoria`, `proposito`, `preguntas` (lo que la sección debe responder), `orden_libre` y, si la guía lo pide, `palabras: min-max` y `palabras_clave: min-max`. Pon el id en `estructura:` del perfil.
6. **Pruébalo.** Un documento conforme debe dar 0 hallazgos y solo excepciones; uno con defectos sembrados debe detectarlos. `tests/estructura/crear_ith.py` y `prueba_ith` de `tests/run_equipo.py` son el modelo. Después `python scripts/catalogo.py` y `python -I tests/run_todo.py --sin-red`.
7. **No copies la guía al repositorio.** Las guías institucionales tienen sus propios derechos: describe sus reglas con tus palabras y cítala como «guía institucional <escuela> <año> (no se distribuye)».
