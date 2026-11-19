# editorial-academica

**Una skill para tu agente de IA que revisa tesis, informes y artículos como lo haría un comité editorial: formato APA 7 o IEEE, citas, fuentes que existen de verdad y un documento que se sostiene de principio a fin.**

[![Pruebas](https://github.com/Xavier82h8/editorial-academica/actions/workflows/pruebas.yml/badge.svg)](https://github.com/Xavier82h8/editorial-academica/actions/workflows/pruebas.yml)
[![Licencia: MIT](https://img.shields.io/badge/licencia-MIT-green.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](requirements.txt)
[![Versión 0.4.0](https://img.shields.io/badge/versi%C3%B3n-0.4.0-informational.svg)](CHANGELOG.md)
[![APA 7 | IEEE](https://img.shields.io/badge/normas-APA%207%20%7C%20IEEE-8a2be2.svg)](docs/REGLAS.md)
[![Agent Skills](https://img.shields.io/badge/Agent%20Skills-Claude%20Code%20%7C%20Codex%20%7C%20Gemini%20%7C%20OpenCode-black.svg)](#instalación)

> Tu asesor no debería gastar la revisión en márgenes, sangrías y comas de la lista de referencias. Que lo haga la máquina, con la regla citada, y que la conversación con tu asesor sea sobre tus ideas.

## En un minuto

Le pides a tu agente de IA que revise tu documento. La skill hace tres cosas, en este orden:

1. **Revisa.** Encuentra cada problema y te dice dónde está y qué regla incumple: de APA 7, de IEEE o de coherencia interna (que el documento no se contradiga).
2. **Corrige lo mecánico.** Márgenes, títulos, numeración de páginas, tablas y lista de referencias, sobre una copia. Tu archivo original no se toca.
3. **Te guía en lo demás.** Lo que exige decidir contenido (una cifra que no cuadra, una cita sin fuente) te lo explica para que tú o tu agente lo arreglen, y te da un puntaje de 0 a 100 para saber cuánto falta.

Así se ve con un [informe de ejemplo](ejemplos/README.md) de tres páginas:

![Puntaje del informe de ejemplo en cada etapa: 53.6 la entrega original, 57.4 tras la corrección automática y 94.4 tras corregir el contenido, desglosado en coherencia, fuentes, formato, estructura y redacción](docs/img/ejemplo-puntaje.png)

La corrección automática deja bien márgenes, títulos y tablas, pero el puntaje casi no sube: lo que lo hunde es que el resumen y el método se contradicen y que hay citas sin fuente. Eso no se arregla moviendo márgenes, y por eso el editor lo separa y lo explica:

![Antes y después de cuatro problemas de contenido: el resumen dice 120 participantes y el método 112; citas sin referencia y un dato sin fuente; un párrafo que repite la tabla; una conclusión causal con un diseño que no lo permite](docs/img/ejemplo-contenido.png)

<details>
<summary><b>Ver también el antes y después del formato</b> (títulos, numeración de páginas, tabla y referencias)</summary>

![Antes y después del formato: títulos con estilo de Word y dos números de página; tabla con rejilla y nota mal escrita; lista de referencias desordenada](docs/img/ejemplo-formato.png)

</details>

<sub>Fragmentos reales del documento abierto con LibreOffice, no maquetas. Los datos del informe son ficticios; sus cuatro referencias son reales y se verificaron contra Crossref. Cómo reproducirlo: [ejemplos/README.md](ejemplos/README.md).</sub>

## Qué es una skill (y por qué esto no es una app)

Una *skill* es un paquete de instrucciones y herramientas que un agente de IA de terminal (Claude Code, Codex, Gemini CLI, OpenCode, Cursor, Copilot CLI) lee cuando le pides algo de su tema. No hay interfaz que aprender: hablas con tu agente como siempre.

```text
tú      › usa la skill editorial-academica para auditar informe-ejemplo.docx con el perfil apa7
agente  › (lee la skill, ejecuta el revisor automático y lee el documento)
          Dictamen: Rechazado
          Hallazgos: 4 críticos, 16 mayores, 5 menores.
          IDs de regla: APA-001, APA-003, APA-004, … APA-034, APA-037, APA-038, APA-057, … EA-001
```

<sub>Respuesta real de Codex CLI con la skill instalada ([registro](docs/PRUEBAS-EN-VIVO.md)). `APA-057` (un dato sin cita) lo añadió el agente: es una regla de criterio que el revisor automático no evalúa.</sub>

Por dentro, la skill reparte el trabajo en dos manos:

| | Quién lo hace | Ejemplos |
|---|---|---|
| **Lo mecánico** | Un programa en Python que, con el mismo documento, da siempre el mismo resultado | márgenes, interlineado, numeración de página, orden de la lista, cita sin referencia, tamaño de muestra que no cuadra, DOI que no existe |
| **Lo que requiere criterio** | Tu agente de IA, guiado por las listas de verificación de la skill | lenguaje sin sesgo, si una conclusión se sostiene, si la fuente dice lo que le atribuyes |

Cada hallazgo, venga de donde venga, cita su regla (`APA-034`, `IEEE-093`, `CON-001`) y la sección oficial. Si un hallazgo no tiene regla, no es un hallazgo: es una opinión, y se marca como tal.

## El ejemplo, paso a paso

| Etapa | Puntaje | Qué pasó |
|---|---:|---|
| Entrega original | **53.6** Rechazado | El revisor encuentra 24 problemas de formato y citas, 4 de coherencia y 4 de maquetación |
| Corrección automática, sobre una copia | **57.4** Rechazado | Quedan 9 de 28. Los que quedan no son de formato: son de contenido y piden una decisión |
| Corrección del contenido, siguiendo cada hallazgo | **94.4** Publicable | Ningún problema pendiente. No llega a 100 porque 3 de las 4 fuentes no publican su resumen, y el editor no da por buena una afirmación que no pudo comprobar |

Además de lo que muestran las imágenes, encontró un objetivo que nunca vuelve a aparecer en el método ni en las conclusiones (`CON-020`). Cada problema lleva un código de regla (`CON-001`, `APA-038`…) que remite a la norma oficial; la lista completa está en [docs/REGLAS.md](docs/REGLAS.md).

## Instalación

| CLI | Cómo | ¿Probado de verdad? |
|---|---|---|
| **Claude Code** | `/plugin marketplace add Xavier82h8/editorial-academica` y `/plugin install editorial-academica@editorial-academica` | Sí: todo el desarrollo y un piloto real |
| **Codex** | `python scripts/instalar.py --cli codex` | [Sí](docs/PRUEBAS-EN-VIVO.md), con el ejemplo |
| **OpenCode** | `python scripts/instalar.py --cli opencode` | [Sí](docs/PRUEBAS-EN-VIVO.md), con el ejemplo |
| **Gemini CLI** | `gemini extensions install https://github.com/Xavier82h8/editorial-academica` | Instalador probado; ejecución en vivo pendiente |
| **Cursor / Copilot CLI** | `python scripts/instalar.py --cli cursor` (o `copilot`) | Instalador probado; ejecución en vivo pendiente |
| **Sin agente** | `pip install -r requirements.txt` y `python scripts/editorial.py <comando> …` | Sí: es lo que usan las pruebas |

Con `instalar.py`, añade `--proyecto DIR` para instalar solo en un proyecto. Requisitos: Python 3.10+; [pandoc](https://pandoc.org/installing.html) 3.x para `render` y `convertir`; xelatex (MiKTeX o TeX Live) solo para PDF y LaTeX. Las instrucciones que leen los agentes están en [AGENTS.md](AGENTS.md).

## Inicio rápido

En tu agente basta con pedirlo («audita mi tesis en APA 7»). Desde la terminal, sin agente:

```bash
pip install -r requirements.txt
python scripts/editorial.py auditar mi_tesis.docx --perfil apa7     # qué está mal, con regla y sección oficial
python scripts/editorial.py corregir mi_tesis.docx --perfil apa7    # escribe mi_tesis.corregido.docx; el original no se toca
python scripts/editorial.py puntuar mi_tesis.corregido.docx --perfil apa7
```

![Auditoría del informe de ejemplo](docs/img/demo-auditar.svg)

## Comandos

En Claude Code son `/editorial-academica:<nombre>`; en cualquier otro lado, `python scripts/editorial.py <nombre>`.

| Comando | Para qué | Ejemplo |
|---|---|---|
| `auditar` | Dictamen de formato, citas y referencias, cada hallazgo con su ID de regla | `auditar tesis.docx --perfil apa7` |
| `corregir` | Arregla lo mecánico en una copia `.corregido.docx` | `corregir tesis.docx --perfil apa7 --paginacion encabezado` |
| `puntuar` | Puntaje 0-100, las 5 correcciones que más lo suben e historial | `puntuar tesis.docx --perfil apa7` |
| `congruencia` | Objetivos, método, resultados y conclusiones; cifras, siglas y referencias cruzadas | `congruencia tesis.docx` |
| `estructura` | Secciones que exige el género y maquetación (paginación, tablas, portada) | `estructura tesis.docx --estructura tesis --perfil apa7` |
| `fuentes` | Busca y verifica fuentes (V1-V5) y genera `fuentes.json` | `fuentes "evaluación con IA generativa" --n 15 --out fuentes.json` |
| `convertir` | Pasa un Word de APA a IEEE (o al revés) re-renderizando citas y referencias | `convertir tesis.docx --a ieee` |
| `render` | Markdown con `[@id]` a .docx, PDF, LaTeX o md con CSL | `render informe.md --perfil apa7 --fuentes fuentes.json --salida docx` |
| `informe`, `tesis` | Redacta solo con fuentes verificadas (con tu agente) | `/editorial-academica:informe "tema" --perfil apa7` |

## Tres cosas que nunca hace

1. **Inventar una fuente.** Una referencia entra solo si su DOI resuelve en Crossref o DataCite (o su URL oficial responde, con fecha de consulta). Si no, no entra.
2. **Tocar tu original.** Todo se escribe en una copia; si la copia fuera a caer sobre el original, el programa se detiene.
3. **Dar por verificado lo que no pudo comprobar.** Un fallo de red queda `no_verificado` con su motivo, y una fuente sin resumen público deja su afirmación «no verificable», que cuenta la mitad, no completa.

## Cómo está hecho

```mermaid
flowchart LR
    D[Tu documento<br/>.docx o .md] --> J[Revisor automático]
    J --> F[Formato y citas] & E[Estructura y<br/>maquetación] & G[Coherencia interna]
    D --> V[Verificador de fuentes<br/>Crossref, OpenAlex]
    D --> A[Tu agente de IA:<br/>lo que pide criterio]
    F & E & G & V & A --> P[Puntaje 0-100 y<br/>qué arreglar primero]
    P --> K[Corrector automático<br/>sobre una copia]
    K --> J
```

Cada pieza, en palabras y en código:

| Pieza | Qué hace | Dónde está |
|---|---|---|
| Revisor de formato y citas | Abre el Word como lo guarda Word (estilos, márgenes, campos de número de página) y compara cada párrafo, cita y referencia con las reglas de APA 7 o IEEE | [`scripts/auditar.py`](scripts/auditar.py) |
| Revisor de coherencia | Busca el tamaño de muestra en resumen, método y resultados; siglas usadas antes de definirse; tablas citadas que no existen; objetivos que no vuelven a aparecer; «causa» donde el diseño solo permite «se asocia» | [`scripts/congruencia.py`](scripts/congruencia.py) |
| Revisor de estructura y maquetación | Comprueba que estén las secciones que pide el tipo de documento (tesis, informe, protocolo…), una sola numeración de página y tablas que no se parten entre páginas | [`scripts/estructura.py`](scripts/estructura.py), [`scripts/maquetacion.py`](scripts/maquetacion.py) |
| Corrector automático | Aplica lo mecánico editando por dentro el archivo .docx (su XML), sin tocar el texto, y siempre en una copia | [`scripts/corregir.py`](scripts/corregir.py) |
| Verificador de fuentes | Consulta cada DOI en Crossref, OpenAlex y DataCite: que exista, que título, autor y año coincidan, que no esté retractada; y compara cada afirmación citada con el resumen de la obra | [`skills/fuentes-academicas/scripts/fuentes.py`](skills/fuentes-academicas/scripts/fuentes.py), [`scripts/afirmaciones.py`](scripts/afirmaciones.py) |
| Puntaje | Junta todo en un número de 0 a 100 con pesos fijos y ordena las correcciones por cuánto suben el puntaje | [`scripts/puntuar.py`](scripts/puntuar.py) |
| Instrucciones para el agente | Qué preguntar antes de empezar, en qué orden trabajar y qué no inventar nunca | [`AGENTS.md`](AGENTS.md), [`skills/`](skills), [`agents/`](agents) |
| Un solo punto de entrada | Un comando, `editorial.py <tarea>`, que llama a cualquiera de los anteriores en Windows, macOS o Linux | [`scripts/editorial.py`](scripts/editorial.py) |
| Instalador | Copia la skill a la carpeta que lee cada agente (Codex, OpenCode, Cursor…) | [`scripts/instalar.py`](scripts/instalar.py) |

Todas las reglas, con su gravedad, quién las revisa (el programa o el agente) y su fuente oficial, están en [docs/REGLAS.md](docs/REGLAS.md).

![Estructura y maquetación del informe de ejemplo](docs/img/demo-estructura.svg)

### Verificación de fuentes V1-V5

Cinco comprobaciones por cada referencia, de la más básica a la más fina:

- **V1 existencia**: el DOI resuelve (Crossref o DataCite) o la URL responde.
- **V2 metadatos**: título, primer autor y año coinciden con el registro.
- **V3 integridad**: retractaciones y expresiones de preocupación; si citas un preprint, sugiere la versión publicada.
- **V4 calidad**: avisos (revista sin ISSN, preprint sin revisión) y DOI faltantes (APA 9.34).
- **V5 sustento**: compara cada oración citada con el resumen de su fuente y marca lo contradicho o lo que la fuente no dice.

### Puntaje

| Dimensión | Peso |
|---|---:|
| Coherencia interna (congruencia) | 30 |
| Fuentes | 25 |
| Formato y citas | 20 |
| Estructura | 15 |
| Redacción | 10 |

Bandas: **90 o más** Publicable, **75-89** Correcciones menores, **60-74** Correcciones mayores, **menos de 60** Rechazado. Una fuente que falle V1-V3 o una incongruencia crítica bloquean «Publicable» aunque la suma alcance. El historial entre versiones queda en `.editorial/puntajes.jsonl` junto al documento (`--sin-historial` lo desactiva).

![Puntaje del informe de ejemplo tras la revisión](docs/img/demo-puntuar.svg)

## Resultados

¿Cómo saber si un revisor automático es confiable? Con dos preguntas: si **encuentra** los errores que hay, y si **no inventa** errores donde no los hay. Para medirlo se usan documentos cuyos errores se conocen de antemano.

![¿Encuentra los errores sin inventar otros? 36 de 36 errores sembrados, 30 de 30, 30 de 30 y 37 de 37 en tres documentos a ciegas, 19 de 19 en un borrador de estudiante, y 0 falsas alarmas en 17 documentos de muestra oficiales](docs/img/juez-precision-recall.png)

| Qué se midió | Resultado |
|---|---|
| Documentos de prueba con errores sembrados a propósito | encontró 36 de 36, sin falsas alarmas |
| Tres documentos nuevos, escritos con errores según la norma sin mirar el revisor | hoy encuentra los 97; la primera vez se le escaparon 4 y marcó 1 de más, y se corrigió |
| Borrador sintético de estudiante | 19 de 19, sin falsas alarmas |
| 17 documentos de muestra oficiales de APA e IEEE, que están bien hechos | **0 falsas alarmas** |
| Protocolo de investigación real de licenciatura (anonimizado) | de 31,1 a 88,4 sobre 100 |
| Uso real desde otros agentes | Codex y OpenCode, sin ayuda, llegaron al mismo dictamen ([detalle](docs/PRUEBAS-EN-VIVO.md)) |
| Batería de pruebas | unos 100 segundos; corre sola en Windows y Linux con cada cambio (GitHub Actions) |

En términos técnicos: precisión y exhaustividad (*recall*) de 1,00 en todas las rondas. Ese 1,00 significa que ninguna ronda conocida vuelve a fallar, no que el revisor sea infalible con documentos nuevos.

![¿Quién revisa cada una de las 323 reglas? El programa revisa y corrige 32, revisa otras 54 y el agente de IA juzga 237; de las 115 reglas mecánicas de APA e IEEE, 56 ya están automatizadas](docs/img/reglas-por-familia.png)

De las 323 reglas, el programa revisa 86 (y de esas, corrige solo 32); las 237 restantes las juzga tu agente porque piden criterio, como el lenguaje sin sesgo o si una cita respalda lo que se le atribuye. A la derecha está lo pendiente: APA e IEEE tienen 115 reglas que se podrían revisar de forma mecánica y hoy 56 ya lo están.

![Un protocolo de investigación real, revisión tras revisión: de 31.1 a 91.5, baja a 87 con reglas nuevas, sube a 91.4, baja a 85.4 con un revisor más estricto y vuelve a 88.4 tras la corrección automática](docs/img/piloto-evolucion.png)

Las dos bajadas no son retrocesos del documento: el revisor se volvió más exigente y encontró cosas que antes dejaba pasar. La última la provocó el ejemplo de esta página, que destapó dos fallos del propio revisor: dejaba pasar párrafos sin sangría después de una tabla, y contaba como comprobadas las afirmaciones cuya fuente no publica resumen. Preferimos un puntaje más bajo y cierto.

<sub>Todas las cifras de esta sección las calcula un script que corre las pruebas y dibuja las gráficas ([`scripts/estadisticas.py`](scripts/estadisticas.py)); los datos crudos están en [docs/estadisticas.json](docs/estadisticas.json).</sub>

## Perfiles y `.editorial.yaml`

Perfiles: `apa7`, `apa7-profesional`, `ieee`, `apa7-base+ieee-citas`, `ieee-base+apa7-citas` (maquetación de una norma, citas de la otra).

Un `.editorial.yaml` en la carpeta del proyecto fija el perfil y el género por defecto y las excepciones de tu institución; el revisor las informa como «excepción institucional», no como error.

```yaml
institucion: "Mi universidad"
perfil: apa7
estructura: tesis
portada_numero: no            # APA §2.18 pide número en la portada; muchas instituciones lo prohíben
excepciones:
  - regla: APA-001            # márgenes
    si_contiene: "1.5"        # solo el margen izquierdo de 1.5 in
    motivo: "La guía institucional pide 1.5 in para encuadernar"
```

Ejemplo completo en [perfiles/equipo-ejemplo.editorial.yaml](perfiles/equipo-ejemplo.editorial.yaml).

## Privacidad

Solo se envían a servicios externos (Crossref, OpenAlex, DataCite, doi.org) **DOI, títulos y URL de las obras**; nunca el texto de tu documento. La caché vive en tu directorio de usuario (`EDITORIAL_CACHE`, o `~/.cache/editorial-academica`), no en el proyecto. `--sin-red` desactiva toda consulta. Lo que tu agente haga con el documento depende de tu agente y de su proveedor.

## Límites

- El sustento de una cita (V5) solo se comprueba contra el resumen de la fuente; lo que esté solo en el texto completo queda «no verificable».
- `corregir` solo corrige perfiles de base APA; con base IEEE se audita pero sale con código 2.
- Las reglas que juzga el agente (lenguaje sin sesgo, claridad, si una cita respalda lo que dice) dependen de su criterio: dos corridas, o dos agentes, pueden diferir.
- Las normas oficiales (`normas/`) no se distribuyen; se obtienen con `python scripts/obtener_normas.py`. Sin ellas, las pruebas que las necesitan se saltan con aviso.
- El revisor automático lee .docx y Markdown; PDF y LaTeX los evalúa el agente tras extraer el texto.
- Probado en vivo en Claude Code, Codex y OpenCode; en Gemini CLI, Cursor y Copilot solo el instalador.

## Hoja de ruta

- Corrector automático para perfiles de base IEEE.
- Encabezados de nivel 4 y 5 en línea.
- V5 con texto completo de fuentes de acceso abierto.
- Citas dentro de celdas de tabla (APA-034).
- Prueba en vivo en Gemini CLI, Cursor y Copilot CLI.
- Servidor MCP para usar el revisor desde cualquier cliente.

## Contribuir

Lee [CONTRIBUTING.md](CONTRIBUTING.md): entorno, pruebas (`python tests/run_todo.py --rapido --sin-red`) y cómo añadir una regla con su caso sembrado. Los falsos positivos se reportan con la plantilla de Issues. Cambios por versión en [CHANGELOG.md](CHANGELOG.md).

## Licencia y avisos

Código bajo [licencia MIT](LICENSE). Las plantillas CSL son del proyecto Citation Style Language (CC BY-SA 3.0) y otros materiales de terceros se detallan en [NOTICE](NOTICE). APA® es marca de la American Psychological Association e IEEE® del Institute of Electrical and Electronics Engineers; este proyecto es independiente y no está afiliado a ellas.

## English summary

**editorial-academica** is an **agent skill** that turns your terminal AI agent (Claude Code, Codex, Gemini CLI, OpenCode, Cursor, Copilot CLI) into an editorial board for academic documents (theses, reports, articles) in **APA 7** or **IEEE** style, or a mix (layout from one, citations from the other). You just ask your agent ("audit my thesis in APA 7"); the skill tells it how, and ships the tools it runs.

- **Deterministic judge**: format, citations, structure, layout and internal consistency (sample size that changes between abstract and method, causal claims from a cross-sectional design, objectives that never reappear), each finding tied to a rule ID and its official section. Judgment calls are left to the agent and labelled as such.
- **Source verification V1-V5**: existence, metadata, retractions, quality and claim support against abstracts (Crossref, OpenAlex). Only DOIs, titles and URLs leave your machine, never the document text. Network failures are reported as `no_verificado`, never as verified.
- **Score 0-100** with the five highest-impact fixes; `corregir` fixes mechanical APA formatting on a copy, never on your original.
- **Measured**: 0 false positives on 17 official APA/IEEE samples; precision and recall of 1.00 on seeded and blind regression rounds; a [worked example](ejemplos/README.md) from 53.6 to 94.4, rendered with LibreOffice; [live runs](docs/PRUEBAS-EN-VIVO.md) in Codex and OpenCode reaching the same verdict as the judge.
- **Honest limits**: V5 checks abstracts only, the auto-corrector targets APA-based profiles, agent rules are non-deterministic, and the official standards are not distributed (`python scripts/obtener_normas.py`).

Install: `/plugin marketplace add Xavier82h8/editorial-academica` (Claude Code), `gemini extensions install https://github.com/Xavier82h8/editorial-academica` (Gemini CLI), `python scripts/instalar.py --cli codex|opencode|cursor|copilot`, or `pip install -r requirements.txt` for the plain CLI. MIT licensed; see [NOTICE](NOTICE) for third-party material. APA® and IEEE® are trademarks of their owners; this project is not affiliated with them.
