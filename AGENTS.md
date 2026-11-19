# editorial-academica: instrucciones para agentes (Codex, Gemini CLI, Cursor, Copilot, OpenCode, Claude Code)

Editorial y juez académico para tesis, informes, protocolos y artículos en **APA 7**, **IEEE** o un perfil combinado (maquetación de una norma, citas de la otra). Redacta con fuentes verificadas, audita y corrige el formato de un Word, revisa congruencia y estructura, y da un puntaje de 0 a 100. Todo lo mecánico lo hacen scripts deterministas; tú pones el juicio donde el script no llega.

## Raíz y cómo llamar los scripts

- **Raíz** = la carpeta que contiene `scripts/editorial.py`. Resuélvela así, en orden: la variable de entorno `EDITORIAL_ROOT`; la ruta absoluta que el instalador escribió en los `SKILL.md` instalados; la carpeta de este archivo (si estás dentro del repositorio); `${CLAUDE_PLUGIN_ROOT}` en Claude Code.
- Un solo punto de entrada, en cualquier sistema operativo: `python <raíz>/scripts/editorial.py <subcomando> [argumentos]` (en mac/Linux, `python3` si `python` no existe). No dependas del directorio actual.
- Subcomandos: `auditar`, `corregir`, `puntuar`, `estructura`, `congruencia`, `maquetacion`, `afirmaciones`, `fuentes`, `convertir`, `render`. `editorial.py <subcomando> --help` lista las opciones: léela antes de inventar un flag.
- Convención común: `--perfil <id>` (si falta, el `perfil:` de `.editorial.yaml`; sin ninguno, error), `--json RUTA` para el resultado estructurado.
- **Códigos de salida**: 0 sin hallazgos (o solo menores); 1 hallazgos críticos o mayores (o fuentes que fallan); 2 error de uso o de entrada (archivo inexistente o no soportado, perfil desconocido, herramienta externa ausente). El mensaje va a stderr, sin traceback.
- Requisitos: Python 3.10+ con `pip install -r <raíz>/requirements.txt` (python-docx, PyYAML, lxml); `pandoc` 3.x para render y convertir; `xelatex` solo para PDF/LaTeX.
- Perfiles (`<raíz>/perfiles/`): `apa7`, `apa7-profesional`, `ieee`, `apa7-base+ieee-citas`, `ieee-base+apa7-citas`. Un `.editorial.yaml` en el proyecto del usuario fija perfil, género y excepciones institucionales (ejemplo: `<raíz>/perfiles/equipo-ejemplo.editorial.yaml`).
- Catálogo de reglas con ID, severidad, quién las evalúa y fuente oficial: `<raíz>/docs/REGLAS.md`. Conocimiento por norma: skills `apa7`, `ieee`, `combinar-formatos`; cargas solo los `references/` que la tarea necesita.

## Reglas duras

1. **Nunca inventes fuentes, DOI, páginas ni reglas.** Una referencia entra solo con metadatos verificados (DOI que resuelve, o URL oficial más fecha de consulta). Sin verificar, no entra. Si una norma no cubre algo, di «No cubierto por el snapshot».
2. **Cada hallazgo cita su ID de regla** (`APA-xxx`, `IEEE-xxx`, `CON-xxx`, `EST-xxx`) y su fuente oficial, con evidencia literal del documento. No reportes como violación lo que no esté en el catálogo: ponlo en «observaciones (no vinculantes)».
3. **Nunca sobrescribas el original.** Las correcciones van a `<nombre>.corregido.<ext>` (o `.ieee.docx`, etc.); los scripts abortan con código 2 si la salida coincide con la entrada.
4. Los hallazgos de los scripts son vinculantes: inclúyelos tal cual, sin cambiar severidad. Tu aporte es lo que requiere juicio (lenguaje sin sesgo, claridad, adecuación de una cita, hilo conductor).
5. Referencias y citas se renderizan con CSL (`render`), no a mano. Ningún `[[FALTA FUENTE]]`, `[[TODO]]` ni `[[PENDIENTE]]` llega a la entrega (regla `EA-001`).
6. Un fallo de red no es «verificado»: queda `no_verificado` con motivo. Díselo al usuario.
7. Si la norma pudo cambiar (más de 6 meses desde `normas/VERSION`), sugiere actualizar el snapshot.

## Preguntar al usuario

Antes de escribir o juzgar fija: perfil, género del documento (tesis, informe, artículo IMRyD, protocolo, revisión sistemática, ensayo, propuesta), idioma y formato de salida. Si tu CLI tiene una herramienta de preguntas de opción múltiple (`AskUserQuestion` en Claude Code, `ask_user` en Gemini CLI, `question` en OpenCode), úsala. **Si no la tiene** (Codex, Cursor, Copilot CLI), pregunta en texto con opciones numeradas, p. ej. «1) Encabezado, a la derecha (APA §2.18, recomendada) 2) Pie 3) Ninguna», y espera la respuesta antes de continuar. No decidas por el usuario la numeración de páginas ni si la portada lleva número.

## Flujos

**Auditar** (`auditar`): `editorial.py auditar <doc> --perfil <id> --json juez.json` (.docx, .md, .txt; .pdf y .tex salen con 2: extrae el texto antes). Luego recorre el checklist de la norma (`skills/<apa7|ieee>/references/checklist.md`) solo en lo que el script no cubre y emite el dictamen: Aprobado, Correcciones menores, Correcciones mayores o Rechazado (cualquier crítica rechaza; más de 5 mayores = mayores).

**Corregir** (`corregir`): solo .docx y perfiles de base APA. `editorial.py corregir <doc.docx> --perfil apa7 [--paginacion encabezado|pie|ninguna] [--portada-numero si|no]` escribe `<doc>.corregido.docx` y lista lo «no automático». Con base IEEE sale con 2 (se audita, no se corrige). Lo no automático lo aplicas tú sobre la copia, y vuelves a auditar. Después **puntuar**.

**Puntuar** (`puntuar`): `editorial.py puntuar <doc> --perfil <id> [--estructura <género>] [--fuentes fuentes.json] [--evidencias evidencias.json] [--congruencia-llm congruencia.json]`. Congruencia 30, fuentes 25, formato 20, estructura 15, redacción 10. Muestra el puntaje por dimensión, los bloqueos, las 5 correcciones de mayor impacto y la evolución (historial en `.editorial/puntajes.jsonl` junto al documento; `--sin-historial` lo desactiva).

**Congruencia** (`congruencia`): `editorial.py congruencia <doc> --json congruencia_det.json` (CON-001..009 y 018..020, vinculantes). Después lee el documento completo y arma la matriz objetivo, método, resultados, conclusión con ubicación de cada celda; una celda vacía es hallazgo (CON-010 a CON-017, ver `agents/revisor-congruencia.md`). Guarda el resultado como `congruencia.json` para `puntuar`.

**Estructura y maquetación** (`estructura`): `editorial.py estructura <doc> --estructura <género> --perfil <id>`. Para .docx incluye maquetación EST-010..016. Preguntas obligatorias (ver arriba cómo preguntar):
- **Numeración (EST-010, número duplicado en encabezado y pie)**: ¿encabezado a la derecha (APA §2.18; recomendada en APA), pie o ninguna? En IEEE di que no define la numeración y que elige el usuario. Con la respuesta: `corregir --paginacion <elección>`.
- **Portada**: APA §2.18 pide número en la portada (lleva el 1); muchas instituciones lo prohíben. ¿Lleva número, sí o no? Si `.editorial.yaml` declara `portada_numero: si|no`, no preguntes: informa. Con la respuesta: `corregir --portada-numero si|no`, y sugiere guardarla en `.editorial.yaml`.
- EST-012 a EST-014 se corrigen solos; EST-015 (nota de tabla sin formato APA) exige que el usuario confirme la obra antes de reescribirla.

**Fuentes V1-V5** (`fuentes`, `afirmaciones`):
- V1 existencia (el DOI resuelve o la URL responde); V2 metadatos (título, primer autor y año coinciden); V3 integridad (retractaciones, preprint con versión publicada); V4 calidad (avisos y DOI faltantes); V5 sustento (cada oración citada contra el resumen de su fuente).
- Buscar: `editorial.py fuentes "consulta en inglés" --n 15 --clasicos 3 --out fuentes.json` (varias consultas con `--append`; `--idioma es` para español; `--doi 10.x/y --append` para añadir uno). Lee títulos y resúmenes y descarta lo impertinente (relevancia antes que citas). Sin DOI: sitio oficial, `URL`, `accessed` y `_verificacion.fecha_consulta`.
- Resúmenes: `editorial.py fuentes --resumenes fuentes.json`. Verificar: `editorial.py fuentes --verificar fuentes.json` (1 si alguna falla; quítala o reemplázala).
- V5: `editorial.py afirmaciones <doc.md> --fuentes fuentes.json --json afirmaciones.json`; las cifras se comparan con el resumen y el resto del veredicto (respalda, contradice, no verificable) es tuyo; guarda `evidencias.json` para `puntuar`. V5 solo verifica contra el resumen: lo que esté en el texto completo queda «no verificable».

**Convertir** (`convertir`): `editorial.py convertir <doc.docx> --a <perfil destino> [--de apa7|ieee] [--sin-red]` re-renderiza citas y referencias con CSL. Revisa el informe `<salida>.informe.md`: citas no mapeadas y discrepancias se proponen al usuario, nunca se resuelven inventando datos.

**Redactar un informe o una tesis** (no hay subagentes: ejecuta estos pasos en orden, leyendo cada instrucción en `<raíz>/agents/<nombre>.md`):
1. Fija perfil, género, tema y, para una tesis, los datos de portada (institución, programa, autor, asesor, fecha) y la estructura de capítulos de la institución.
2. Fuentes (`agents/investigador-fuentes.md`): informe de 8 a 20 fuentes, tesis de 30 a 60, con resumen y `fuentes.json` verificado; confirma la selección con el usuario.
3. Esquema desde `<raíz>/estructuras/<género>.yaml` (`editorial.py estructura --listar`): secciones obligatorias, preguntas que cada una responde, extensión orientativa. Acuérdalo con el usuario.
4. Redacta sección por sección (`agents/redactor.md`), solo con citas `[@id]` de `fuentes.json` y afirmaciones que el resumen de la fuente respalde. `--paginas N` son páginas de cuerpo (APA ≈ 275 palabras por página).
5. Corrección de estilo (`agents/corrector-estilo.md`): gramática, lenguaje sin sesgo, voz académica, sin tocar citas.
6. Verifica: `afirmaciones` (V5), `congruencia`, `fuentes --verificar`.
7. Entrega: `editorial.py render doc.md --perfil <id> --fuentes fuentes.json --salida docx|pdf|latex|md [--out ruta]` (skill `salida-documento`). Pasa el resultado por `auditar` y `puntuar` y corrige hasta Aprobado.

## Agentes y skills incluidos

Skills en `<raíz>/skills/`: `editorial-academica` (orquestador), `apa7`, `ieee`, `combinar-formatos`, `fuentes-academicas`, `salida-documento`. Agentes en `<raíz>/agents/*.md` (`juez-formato`, `revisor-congruencia`, `investigador-fuentes`, `verificador-afirmaciones`, `redactor`, `corrector-estilo`): en Claude Code y OpenCode son subagentes; donde no existan, son guiones de pasos para ti.

## Privacidad

Solo se envían a servicios externos (Crossref, OpenAlex, DataCite, doi.org) DOI, títulos y URL de las obras; **nunca el texto del documento del usuario**. La caché va a un directorio de usuario (`EDITORIAL_CACHE`, o `~/.cache/editorial-academica`), no al proyecto. No subas el documento a ningún servicio ni copies su contenido en consultas web. `--sin-red` desactiva toda consulta.

## Pruebas del plugin

`python -I <raíz>/tests/run_todo.py --rapido` (todas las puertas) y `python <raíz>/tests/run_portabilidad.py` (skills, rutas e instalador). Una regla nueva entra con su checklist, su prueba sembrada y `python <raíz>/scripts/catalogo.py` para regenerar `docs/REGLAS.md`.
