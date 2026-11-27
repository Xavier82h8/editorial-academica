# Registro de cambios

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/); versionado semántico.

## [0.9.0] - 2026-11-27
### Destacado
- **`editorial.py medir`: la medida efectiva de un Word y de su PDF.** Ficha técnica con el valor que de verdad ve Word (docDefaults, estilo y sus bases, numeración, párrafo directo, run) por sección (página, márgenes, encabezado y pie, `w:pgNumType`, posición del número de página) y por grupo de párrafos y estilo (fuente, tamaño, interlineado auto ×1.5 frente a exacto 18 pt, espacios, sangría izquierda, derecha, de primera línea y francesa, alineación, color), cada longitud en cm, pt e in, con el conteo de párrafos por valor y las excepciones. Con PDF (PyMuPDF): márgenes reales, número de página por página, sangría visible, paso de línea y fuentes; sus discrepancias con el .docx son avisos, nunca violaciones.
- **Tus instrucciones, como reglas medibles.** `medir --regla "márgenes 3 cm izquierda"` y el bloque `medidas:` de `.editorial.yaml` (`{que, valor, unidad, tolerancia, alcance, origen}`); parser en español e inglés básico; lo ambiguo vuelve como pregunta y lo que no se puede medir sale «no medible: …». `auditar` emite INS-016 con el origen del usuario.
### Añadido
- `scripts/medir.py` (ficha, PDF, discrepancias, CLI), `scripts/medidas.py` (parser, evaluador, INS-016, excepciones APA derivadas), `scripts/unidades.py` (equivalencias y tolerancias en un solo lugar: 1.27 cm = 0.5 in = 36 pt; twips, EMU, medios puntos; interlineado 1.5 = auto ×1.5 = exacto 18 pt con 12 pt, y × 1.15 como aproximación declarada; tolerancias ±0.05 cm, ±0.5 pt, ±0.25 pt sobreescribibles por regla).
- Regla nueva **INS-016** (mayor): medida pedida por el usuario (`medidas:`); las exigencias APA que contradice (APA-001, APA-004, APA-033, APA-007, APA-006, APA-002, APA-008) pasan solas a excepción con el origen.
- `perfilar` emite el bloque `medidas:` con los márgenes y la sangría de primera línea que fija la guía, cada uno con su cita de origen.
- Comando `/medir` (`commands/medir.md|toml`) y `skills/editorial-academica/references/medir.md`.
- `tests/run_v09.py` (unidades, herencia, equivalencias que no dan hallazgo y valores fuera de tolerancia que sí, parser con casos ambiguos, PDF sintético, discrepancia docx/PDF como aviso, render real con LibreOffice, «no medible», INS-016, perfilar, CLI, exportación) y puerta en `tests/run_todo.py`.
### Cambiado
- `scripts/exportar_publico.py --forzar`: si el destino ya tiene remoto `origin`, conserva su `.git`, hace `git fetch origin` y crea el commit con `git commit-tree` del árbol exportado y por padre `origin/main` (historial conservado, push sin force; nunca hace push). Sin remoto, commit único como antes. El barrido de anonimización no cambia.

## [0.8.0] - 2026-11-27
### Destacado
- **`/perfilar`: la guía de tu escuela se convierte en reglas.** `editorial.py perfilar <guia.pdf|docx> [--modelo-portada <pdf|docx> --pagina N] [--out .editorial.yaml] [--estructura-id ID] [--responder respuestas.yaml]` lee la guía de formato y genera `.editorial.yaml` + `estructuras/<id>.yaml`, cada valor con su origen (`guía p. N: «cita literal»`); lo ambiguo y las preferencias (registro, persona, extensión por sección, densidad de citas, salida, fuentes a evitar) van a `preguntas:`. Nunca sobrescribe: `.editorial.propuesto.yaml` y un diff legible. Prueba dorada local con una guía real: 100 % de las claves de formato, 12/12 capítulos con sus 24 subcapítulos.
- **Entrega comprobada de punta a punta:** portada fiel al modelo (medida a 0.1 pt), índices con páginas medidas en el PDF y `entregar` (.docx + .pdf verificados).
- **Fuentes con contexto:** `fuentes --reemplazar --contexto doc.docx` exige términos de dominio del documento y descarta candidatas de dominios ajenos; bloque `fuentes:` del perfil (FUE-NIV) con el mismo denominador que INS-008.
- Caso real anonimizado: protocolo institucional de Taller de Investigación, 87.9 → 91 (portada fiel a la guía medida a 0.1 pt, índice real, 32 → 19 afirmaciones sin fuente arbitrada, ISO verificadas).
### Añadido
- **`/perfilar`** (`scripts/perfilar.py`, `commands/perfilar.md|toml`, `skills/editorial-academica/references/perfilar.md`): extrae con PyMuPDF/pdftotext o python-docx y patrones en español e inglés fuente y tamaño, márgenes, interlineado, alineación, sangría, jerarquía de títulos 1-5, paginación por partes (portada, preliminares, cuerpo; romanos/arábigos; posición), tablas y figuras (IEEE/APA, rótulo, numeración, pt), norma de citas, % y años de fuentes, mínimo de fuentes, título máximo, voz, tiempo verbal, resumen, portada (campos con literal o patrón, fecha, número de control, logos) y la estructura numerada con la descripción y las preguntas guía de cada capítulo. Con `--modelo-portada` mide la portada (`modelo_formato`) y registra un `vinculante` tipo modelo. `--responder` aplica las respuestas (número de opción, texto o lista). `--comparar` mide el porcentaje de claves y capítulos contra un perfil de referencia. `estructura` encuentra `<carpeta de .editorial.yaml>/estructuras/<id>.yaml`. `tests/run_perfilar.py` (guía inventada en .docx y PDF, inglés, sin sobrescribir, modelo, errores) y puerta en `tests/run_todo.py`; la prueba dorada con la guía real es local (`tests/reales/privado/`).
- `fuentes --reemplazar … --contexto <doc.docx>` (alias `--doc`): de una copia local del documento salen 5 a 8 términos de dominio (título de la portada, palabras clave del resumen, frecuencia en el cuerpo); se exigen en la consulta (de dos en dos, en español e inglés), se descartan las candidatas cuyo título + resumen compartan menos de 2 y la puntuación es solapamiento con la oración × solapamiento con el dominio. Solo viajan los términos, nunca el texto.
- `scripts/exportar_publico.py`: el barrido de privacidad también busca el nombre de la docente, la clave de asignatura y el nombre del archivo de la guía real.
### Corregido
- FUE-NIV `porcentaje_arbitradas` e INS-008 comparten una sola función de denominador (`institucional.literatura_actualizable`): la literatura actualizable, sin documentales, fundacionales declaradas ni referencias sin año; el mensaje dice qué se excluyó (antes 53 % frente a 79 % sobre el mismo protocolo).
- Una página de licencia, términos o conjunto de datos (Stack Exchange «Licensing», SPDX, Apache, Creative Commons) es documental (nivel D), no «foro» ni «wiki»: el tipo de documento pesa más que el dominio, y el bloque `evitar` no la marca.
- `auditar` ya no falla con `TypeError` si un `sectPr` no tiene `pgMar`: usa los márgenes por defecto de Word (1 in) y avisa.
- **Portada como función propia.** `editorial.py portada <doc.docx> [--out RUTA] [--campo nombre=valor …]` (`scripts/portada.py`): construye la portada desde `formato: portada:` y el `vinculante` tipo modelo con ámbito portada (campos en orden y textos; fuente, pt, negrita, cursiva, color, alineación, espacios, caja con relleno y borde izquierdo), con fila opcional de logos (`portada: logos: [{nombre, ruta, alto_cm}]`, hueco y aviso si falta el archivo). Reemplaza la portada detectada con `auditar.fin_portada` conservando su `sectPr`, escribe `<doc>.portada.docx` (nunca el original), deja `[[PENDIENTE]]` en los campos sin valor, afina el espaciado midiendo en LibreOffice (error final <= 0.5 pt) y corre INS-010 e INS-015 sobre el resultado (código 1 si hay diferencias). `--campo control.<integrante>=NNNNNNNN` rellena los números de control después. La spec admite `campo`, `nombre_negrita` y `y_fija` por línea.
- **Índices con páginas medidas.** `editorial.py indices <doc.docx>` (`scripts/indices.py`): campo `TOC \o "1-3" \h \z \u` con resultado precalculado y enlaces a marcadores `_Toc`, listas de tablas y figuras con los rótulos exactos, fuente de `formato: fuente:`, `updateFields` activo; las páginas salen del PDF de LibreOffice con PyMuPDF (número visible por sección según `w:pgNumType`, romanos y arábigos) y se repite hasta converger (máx. 4). `--comprobar` compara lo escrito con el PDF. Sin LibreOffice, código 2 con el mensaje de instalación (`scripts/libreoffice.py`).
- **Entrega.** `editorial.py entregar <doc.docx>` (`scripts/entregar.py`): corregir, portada (si el perfil la declara), índices, PDF, capturas PNG de la portada y los preliminares, y auditar + estructura + puntuar sobre el resultado; deja `<doc>.entrega.docx` y `<doc>.entrega.pdf` juntos y un resumen; código 1 si quedan críticos (p. ej. EA-001).
- **Cierre de fuentes.** `editorial.py fuentes --reemplazar "<oración>" --cita "<referencia o DOI>" [--n 5] [--out cand.json]` (`scripts/reemplazo_fuentes.py`): primero la versión publicada de la misma obra (Crossref `is-preprint-of`, OpenAlex, título + primer autor, ficha de arXiv) y luego candidatas de nivel A/B con consultas en español e inglés derivadas de la oración, resumen y fragmento coincidente; nunca aplica cambios. Bloque `fuentes: {minimo_nivel, porcentaje_arbitradas, evitar}` del perfil evaluado por `auditar` con la regla nueva FUE-NIV (mayor: fuente a evitar o porcentaje de arbitradas bajo el pedido; menor: bajo el nivel mínimo); declarado en `perfiles/instituto-ejemplo-protocolo.editorial.yaml`.
- `tests/run_v08.py` (pruebas sembradas; `--con-red` prueba la oración de Hosen 2025) y nueva puerta en `tests/run_todo.py`.

## [0.7.0] - 2026-11-27
### Añadido
- **Título concreto.** `editorial.py titulo <doc> [--max-palabras N] [--opcion "…"]`: extrae el título de la portada (también en varias líneas) y el objetivo general y diagnostica palabras, sigla, detalle de método o tecnología que sobra (LoRA, ABC, Gemma, prompting, «comparando», «mediante», «basado en», modelos y versiones), promesas de resultado («mejorar», «garantizar», «optimizar», «encargado de»), cifras y términos del objetivo que el título no recoge. Guía `skills/editorial-academica/references/titulo.md` (receta «Sigla: objeto + para qué», 8-15 palabras, 3-4 opciones, el usuario elige) y comando `/titulo`. `titulo:` en `.editorial.yaml` fija el título elegido (vinculante): INS-010 exige que la portada coincida. Regla nueva CON-021 (menor): el núcleo del título debe aparecer en el objetivo general.
- **Fuentes de punta a punta.** `editorial.py fuentes --desde-docx doc.docx --out fuentes.json`: lee la lista de referencias del Word, extrae DOI y URL, resuelve el DOI (Crossref/OpenAlex, caché), trae el resumen y busca DOI por título + primer autor + año aceptando solo coincidencia alta (si no, queda sin DOI con motivo). `afirmaciones doc.docx --fuentes fuentes.json` corre V5 sobre el Word con esos resúmenes.
- **Niveles de evidencia A-E** (`scripts/niveles.py`): norma o revista arbitrada, libro, informe de organismo, documentación de proveedor o datos, web o preprint; con Crossref `type`, OpenAlex `primary_location.source.type`, patrones del texto y dominio de la URL. `puntuar` muestra la pirámide de fuentes. FUE-V4N (menor): afirmación sustantiva sostenida solo por fuentes D/E (siempre en `/puntuar`; en `/auditar` con `fuentes: {niveles: true}`). INS-008 con `fuentes_recientes.arbitradas: true` cuenta como reciente solo el nivel A/B (activo en el perfil ITE).
- **Normas ISO/IEC** (`scripts/normas_iso.py`): `--verificar` prueba iso.org, la vista previa oficial de VDE (ed1 a ed4) y la muestra de iteh.ai, lee la portada con pdftotext (o PyMuPDF) y compara número, año, edición y título; `verificado` con `_verificacion.fuente_verificacion` o `no_verificado` con motivo.
- `editorial.py repasar <doc> [--seccion N]` y `/repasar`: modo de estudio por capítulo (qué pide la guía, qué tiene el documento, preguntas guía), sin puntaje ni veredicto.
- `corregir --paginacion encabezado-derecha|pie-derecha|pie-centro` (`encabezado` y `pie` siguen como alias) y `formato: paginacion: {posicion: pie_derecha}`: INS-006 comprueba el lugar, `corregir` lo usa sin flag, APA-008 pasa a excepción derivada y EST-010 propone la posición declarada.
- `tests/run_v07.py` (pruebas sembradas sin red; `--con-red` verifica ISO/IEC 25010:2023 y 25059:2023 en VDE) y nueva puerta en `tests/run_todo.py`.
### Cambiado
- AGENTS.md: una instrucción del usuario que contradice la guía se pregunta primero y, si confirma, se registra en `vinculante:` como excepción con motivo.
### Descartado
- La lista de cotejo no entra al puntaje (la revisa el docente): no hay `puntuar --cotejo`; `repasar` es el sustituto de estudio.

## [Sin publicar]
### Añadido
- Familia INS (reglas institucionales, 9 reglas deterministas): el bloque opcional `formato:` de `.editorial.yaml` EXIGE el formato de la escuela. INS-001 interlineado, INS-002 alineación, INS-003 nivel 1 en mayúsculas y numerado, INS-004 nivel 2 «N.k.», INS-005 capítulo en página nueva, INS-006 numeración por sección (portada sin número, preliminares en romanos, cuerpo en arábigos desde 1), INS-007 título de máximo N palabras, INS-008 porcentaje de fuentes recientes, INS-009 voz impersonal. Sin el bloque no cambia nada. Módulo `scripts/institucional.py`; `auditar` las emite y `puntuar` las cuenta en «Formato».
- Las excepciones APA que `formato:` contradice (APA-004, 033, 006, 025, 030) se derivan solas; las explícitas siguen valiendo. `formato.paginacion.portada: sin_numero` equivale a `portada_numero: no`.
- `corregir` aplica el formato institucional: 1.5, justificado, mayúsculas, numeración «N.» y «N.k.» (solo si los capítulos son claramente consecutivos), página nueva por capítulo, saltos de sección con `lowerRoman`/`decimal` (INS-006) y, con `tablas_figuras: ieee`, «Tabla N» -> «TABLA <romano>», «Figura N» -> «Fig. N. Título» debajo de la imagen y sus menciones (IEEE-089 e IEEE-085 pasan a corregibles en ese caso). Siguen manuales INS-007, 008 y 009.
- `perfiles/instituto-ejemplo-protocolo.editorial.yaml` declara `formato:` y deja sus excepciones APA-004/033/006/025/030 a las derivadas. `tests/estructura/crear_ith.py` genera el protocolo con tres secciones y variantes sembradas por regla; `prueba_ins` en `tests/run_equipo.py`.
- Formato vinculante: bloque `vinculante:` de `.editorial.yaml` (`id`, `origen`, `fecha`, `tipo: modelo|instruccion`, `texto`/`spec`, `ambito: portada|documento|seccion:<nombre>`), validado con error de uso (código 2). Precedencia: vinculante > perfil de equipo > norma base > estructura. `scripts/modelo_formato.py` y `editorial.py modelo medir|comparar`: mide un modelo PDF (PyMuPDF) o .docx (texto, fuente, pt, negrita, cursiva, color, alineación, espacio, cajas de relleno y barras de borde) y lo compara. Regla dura nueva en AGENTS.md y la skill: un formato, modelo o instrucción del usuario se mide, se registra y se reproduce al pie de la letra.
- Reglas nuevas: INS-010 portada oficial (campos en orden, fecha Mes y Año, número de control, logos como aviso), INS-011 fuente de encabezados y pies (corregible), INS-012 resumen (palabras, un párrafo, sin sangría, palabras clave; quita la sangría), INS-013 tamaño de rótulos (corregible), INS-015 fidelidad al modelo vinculante, EST-017 índice desactualizado (contenido, tablas y figuras). `perfiles/instituto-ejemplo-protocolo.editorial.yaml` las declara.
- `corregir` no toca la portada de un perfil institucional ni los ámbitos de `vinculante:` (copia y restitución antes de guardar); APA-005 y APA-093 nunca tocan la portada.
### Corregido
- `auditar.fin_portada`: un párrafo centrado de más de 80 caracteres (título largo en un solo párrafo) hacía que la segunda búsqueda devolviera 0 y la portada se tomara como preliminares (INS-006 la contaba como «i», APA-005 y APA-093 la modificaban).
### Cambiado
- `auditar.cargar_docx` informa `salto_estilo` (salto de página heredado del estilo del párrafo).

## [0.6.0] - 2026-11-19
### Añadido
- Perfil institucional de ejemplo `perfiles/instituto-ejemplo-protocolo.editorial.yaml` y estructura `estructuras/protocolo-instituto-ejemplo.yaml`: protocolo de Taller de Investigación I del Instituto Tecnológico de Ejemplo (TNE, ciclo 2026), preliminares y 12 capítulos, con excepciones motivadas por cada regla APA que la guía institucional (no se distribuye) cambia. Guía de uso y de cómo hacer el de otra escuela: `docs/PERFILES-INSTITUCIONALES.md`.
- `.editorial.yaml`: clave `tablas_figuras: ieee`. Sobre una base APA, APA-089 y APA-090 pasan a excepción institucional y corren IEEE-089 (TABLA + romano, mayúsculas, rótulo encima), IEEE-085 (pie «Fig. N.» debajo de la imagen), IEEE-091, IEEE-092 y APA-091 con mención previa a la aparición. Los índices de contenido, de tablas y de figuras no cuentan como rótulos ni menciones.
- EST-004: las estructuras admiten `palabras: min-max` y `palabras_clave: min-max` por sección (el Resumen de 150-250 palabras con 3-5 palabras clave).
- `tests/estructura/crear_ith.py` y `prueba_ith` en `tests/run_equipo.py`: protocolo ITE conforme (0 hallazgos) y variantes sembradas.
- Reglas deterministas de la tanda 2 (107 -> 120): APA-032 (un único subencabezado en una sección), 048 (cita textual de 6 o más palabras sin página), 064 (21 o más autores: 19 + … + el último), 074 (rango de páginas con guion), 080 (DOI y URL en la misma entrada), 081 (URL de bases de datos como EBSCOhost o ProQuest), 103 (siglas con puntos como `F.B.I.`) e IEEE-007 (`et al.` según los autores de la entrada), 015 (`REFERENCES` sin numeral), 031 (`vol.`, `no.`, `pp.`), 032 (mes abreviado), 070 (`REFERENCES` y `ACKNOWLEDGMENT` sin numerar), 129 (sin ™ ni ®). Sin descartes.
- `corregir` corrige APA-074 (guion -> raya en en las referencias).
- `tests/run_reglas_tanda2.py` (360 casos): 0 falsos positivos en las 83 referencias APA, las 138 IEEE y las citas oficiales; nueva puerta en `tests/run_todo.py`.
### Cambiado
- «Fuentes de información» se reconoce como título de la lista de referencias.
- La cita narrativa ya no toma un número de control entre paréntesis («Ana Pérez (21330001)») por un año.
- Las muestras oficiales de APA tienen 3 verdaderos positivos nuevos (APA-032 en dos documentos y APA-074 en uno): errores de las propias muestras.
- Las referencias del ejemplo de `ejemplos/` y de las rondas ciegas docs/docs2 usan raya en en los rangos de páginas, y los generadores añaden el segundo subencabezado que faltaba, para que los documentos «correctos» sigan en 0 hallazgos; las cifras del ejemplo (3/16/5, 28 -> 9, final 0) no cambian.

## [0.5.0] - 2026-11-19
### Añadido
- Reglas APA deterministas (tanda 1): APA-015 (apéndice sin mención o fuera de orden), 024 (salto de nivel de encabezado), 031 (encabezado «Introduction» al inicio; «Introducción» se acepta), 039 (`et al.` con 1 o 2 autores), 041 (fecha completa o «sin fecha» en la cita), 044 (mismo autor y año sin letra), 063 (autores sin `&`/`y` o con iniciales delante) y 066 (fecha de la referencia).
- `tests/run_reglas_apa.py`: 132 casos, 0 falsos positivos en las 83 referencias oficiales.
- `docs/PRIORIDAD-REGLAS.md`: puntuación impacto²/esfuerzo de las reglas que evalúa el agente (tanda 1, siguiente tanda, no automatizables).
- Reglas IEEE deterministas (tanda 1): IEEE-009 (ibid./op. cit.), 019 (obra repetida), 020 (`Apellido, I.`), 022 (más de 6 autores), 023 (`&`/`y` antes del último autor), 034 (referencia sin año), 041 (URL sin `[Online]. Available:`), 061 (Abstract de 150 a 250 palabras), 084 (`Figure N` en el texto), 089 (tabla con número arábigo), 091 (numeración consecutiva) y 092 (primeras menciones en orden).
- `corregir` corrige IEEE-023 e IEEE-084, también con base IEEE (solo IEEE-023, IEEE-084 e IEEE-140).
### Cambiado
- La numeración de la lista con saltos o repetidos se emite como IEEE-017 (crítica); IEEE-016 queda para la entrada sin `[n]`.
- Las rondas ciegas se regeneran también cuando su generador es más nuevo que `esperado.json`.

## [0.4.0] - 2026-11-19
### Añadido
- Maquetación (EST-010..016): paginación, portada, tablas y figuras que se parten, espacio tras tablas, formato de notas.
- Congruencia determinista CON-008, CON-009, CON-018, CON-019 y CON-020 (CON-010..017 los evalúa el agente).
- `corregir.py`: opciones `--paginacion encabezado|pie|ninguna` y `--portada-numero si|no` (también `portada_numero:` en `.editorial.yaml`).
- `scripts/editorial.py`: despachador único (`auditar`, `corregir`, `puntuar`, `estructura`, `congruencia`, `maquetacion`, `fuentes`, `convertir`, `render`).
- Multi-CLI: `AGENTS.md`, `GEMINI.md`, `gemini-extension.json`, `commands/*.toml` y `scripts/instalar.py --cli codex|gemini|cursor|copilot|opencode`.
- Catálogo de reglas generado: `scripts/catalogo.py` escribe `docs/REGLAS.md` (una prueba exige que esté al día).
- `scripts/obtener_normas.py`: descarga y verifica las normas públicas (`normas/` ya no se distribuye).
- Pruebas reproducibles sin normas (se saltan con aviso) y sin red (`--sin-red`, fixtures HTTP versionados); pruebas de CLI y de portabilidad.
- Borrador sintético de estudiante como sustituto de material real en las pruebas.
- Presentación: LICENSE (MIT), NOTICE, CONTRIBUTING, plantillas de issues y de PR, CI, estadísticas y capturas SVG reproducibles.

- `ejemplos/`: informe de ejemplo con errores reales y referencias verificadas, recorrido completo (53.6 → 57.4 → 94.4) y capturas antes/después renderizadas con LibreOffice (`ejemplos/capturas.py`).
- `docs/PRUEBAS-EN-VIVO.md`: la skill usada sin ayuda desde Codex y OpenCode con el mismo encargo.
- `APA-037`/`APA-038` en citas narrativas: «&» en «Autor & Autor (año)» y dos apellidos cuando la obra tiene tres o más autores.
- `APA-003` también señala encabezados con otro tamaño, fuente o color que el texto (el estilo «Heading» de Word); `corregir` los iguala al texto.
- `corregir` corrige `APA-037` (conjunción en citas) y `APA-076` (`doi:` → `https://doi.org/`).
### Cambiado
- Las plantillas Word (`plantillas/docx/*.docx`) ya no se versionan: `crear_plantillas.asegurar_plantillas()` las genera con el pandoc del usuario en su caché (`render`, `convertir` y las pruebas lo hacen solo). El repositorio público queda MIT + CSL CC BY-SA.
- Convención de salida de todos los scripts: 0 sin hallazgos, 1 hallazgos críticos o mayores, 2 error de uso o de entrada.
- Núcleo compartido (`ooxml.py`, `cli.py`, `datos.py`); el `buscar.py` de las skills pasa a `fuentes.py`.
- Caché e historial fuera de la carpeta del plugin (`EDITORIAL_CACHE`); render multiplataforma (pandoc y xelatex desde PATH).
- Marketplace renombrado a `editorial-academica` (antes `editorial-academica-dev`).

### Corregido
- Ninguna salida sobrescribe ya la entrada (`convertir`, `render`).
- Sin red, la verificación de fuentes devuelve `no_verificado` con motivo, nunca «ok»; los 404 en caché caducan.
- Detección del campo PAGE con `\bPAGE\b` (NUMPAGES ya no cuenta).
- `.pdf` y `.tex` en el juez determinista terminan con error claro (código 2) en lugar de un traceback.

- `APA-007`: un párrafo sin sangría tras una tabla o una nota, y el texto bajo el encabezado siguiente, pasaban como «nota de tabla» y no se señalaban ni se corregían.
- `corregir` ya no pega un encabezado a la tabla anterior al quitar el espacio extra de los encabezados (`EST-014`).
- V5 en .docx: «et al.» cortaba la búsqueda del autor y las citas narrativas no se enlazaban con su referencia.
- `CON-020`: «resultados», «datos» y «análisis» ya no cuentan como rastro de un objetivo.
- V5 en `/puntuar`: una afirmación «no verificable» cuenta la mitad; antes se excluía y una sola afirmación respaldada daba el máximo.
- `puntuar --fuentes/--evidencias/--congruencia-llm` con un archivo inexistente termina con código 2 y mensaje, no con un traceback.
- `maquetacion.py`: la regex de notas «Elaboración propia / Tomado de / Adaptado de» tenía un carácter de retroceso en lugar de `` y nunca coincidía; una prueba de portabilidad rechaza ahora caracteres de control en el código.
## [0.3.0] - 2026-11-18
### Añadido
- Verificación de fuentes V1-V5: existencia, metadatos, integridad (retractaciones, preprint → publicado), calidad y DOI faltantes, y sustento contra el resumen.
- Congruencia interna CON-001..007 y puntaje 0-100 con historial (`/puntuar`).
- Perfil de equipo `.editorial.yaml` con excepciones institucionales.
- Estructuras por género (tesis, informe, IMRyD, protocolo, revisión sistemática, ensayo, propuesta).
- `/corregir`: corrector determinista de formato APA en .docx (16 reglas), sin tocar el original.
- Orquestador con tareas de corregir, congruencia, fuentes, estructura y puntuar.

### Cambiado
- DOI sugerido por metadatos (APA 9.34); URL como V1 para sitios; V2 tolera subtítulo y autor grupal.

## [0.2.0] - 2026-11-18
### Añadido
- Dominio APA 7 e IEEE: checklists, perfiles combinados y plantillas CSL ajustadas.
- `/convertir`: pasa un .docx real entre APA e IEEE vía AST de pandoc, con parser de referencias a CSL-JSON.
- Salida en PDF y LaTeX (APA profesional, IEEEtran a dos columnas); fechas y términos en español.
- 17 muestras oficiales APA/IEEE como prueba de precisión: 0 falsos positivos.
- Juez y `/informe` probados de extremo a extremo con el plugin instalado.

### Corregido
- Falsos positivos hallados por rondas ciegas independientes y por documentos reales.

## [0.1.0] - 2026-11-18
### Añadido
- Juez editorial base: auditoría de formato, citas y referencias contra APA 7 e IEEE, con cada hallazgo citado por ID de regla.
- Citas en texto probadas contra ejemplos oficiales; errores sembrados y primeras rondas ciegas (precisión y recall >= 0.95).
