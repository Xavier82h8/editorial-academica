# Registro de cambios

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/); versionado semántico.

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
