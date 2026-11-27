# Perfilar: la guía de tu escuela se convierte en reglas

`/perfilar` lee la guía de formato de la escuela (PDF o .docx) y produce un perfil (`.editorial.yaml`) y una estructura de capítulos (`estructuras/<id>.yaml`). Cada valor lleva su origen: `guía p. N: «cita literal»`. Lo que la guía no dice, o dice de forma ambigua, se pregunta; las preferencias que ninguna guía dice se preguntan también. El script hace lo mecánico (patrones en español e inglés); tú haces las preguntas y revisas lo derivado.

## Pasos

1. **Pide la guía** (PDF o .docx) y, si el usuario la tiene, un **modelo de portada** (PDF o .docx) y su página. Un modelo de portada es formato vinculante: se mide, no se interpreta.
2. Corre:
   `python <raíz>/scripts/editorial.py perfilar <guia.pdf|docx> [--modelo-portada <pdf|docx> --pagina N] [--out .editorial.yaml] [--estructura-id <id>]`
   - Si `.editorial.yaml` ya existe, no se toca: sale `.editorial.propuesto.yaml` y `.editorial.propuesto.diff` (`~` cambia, `+` nuevo, `-` solo tuyo). Enséñale el diff y pregunta qué adopta; nunca copies encima sin que lo diga.
   - La estructura queda en `<carpeta del .editorial.yaml>/estructuras/<id>.yaml`; `estructura` y `repasar` la encuentran ahí al declarar `estructura: <id>`.
3. **Revisa los orígenes** (`origenes:`). Lo marcado «derivado de» no está dicho tal cual (p. ej. `fuentes.minimo_nivel: B` sale de «literatura arbitrada»): confírmalo con el usuario.
4. **Haz las `preguntas:`** (cada una con `id`, `clave`, `pregunta`, opciones numeradas y `valores`). Con una herramienta de preguntas de opción múltiple (`AskUserQuestion` en Claude Code, `ask_user` en Gemini CLI, `question` en OpenCode) úsala; sin ella, texto con opciones numeradas, una pregunta a la vez, y espera la respuesta. Estas siempre salen, aunque la guía sea completa, porque ninguna guía las dice:
   - `P-registro`: académico formal, técnico de ingeniería o divulgativo.
   - `P-extension`: extensión por sección (la de la guía, breve, media, amplia).
   - `P-citas-densidad`: una cita por afirmación sustantiva, una o dos por párrafo o las mínimas.
   - `P-salida`: `.docx` y `.pdf` verificados (`entregar`), solo `.docx` o solo `.pdf`.
   - `P-evitar`: fuentes que no admite (wikipedia, blogs, foros; redes y video).
   Y las que la guía dejó sin decir (alineación, fuente y tamaño, márgenes, interlineado, norma de citas, numeración de páginas, persona gramatical).
5. Guarda las respuestas en un archivo `respuestas.yaml` (`P-registro: 2`, `P-evitar: [1]`; por número de opción, por su texto o un valor libre) y repite el comando con `--responder respuestas.yaml`. Lo respondido pasa a los valores con origen «respuesta del usuario».
6. **Instrucción del usuario que contradiga la guía**: se pregunta primero; si confirma, se registra en `vinculante:` como excepción con motivo (AGENTS.md, regla 8). No la cambies en silencio.
7. Con el perfil aprobado, el usuario lo copia como `.editorial.yaml` (o lo haces tú tras confirmarlo) y se corre `/auditar`, `/estructura` y `/corregir` con él. Un valor que la guía fija distinto de APA (p. ej. márgenes que no son de 2.54 cm) sale como excepción propuesta; las reglas INS-001..015 comprueban el `formato:`.

## Qué extrae

| Bloque | Claves |
|---|---|
| Formato | `formato.fuente`, `interlineado`, `alineacion`, `nivel1`, `niveles_numerados`, `capitulo_pagina_nueva`, `paginacion` (portada, preliminares, cuerpo, posición), `titulo_max_palabras`, `fuentes_recientes`, `voz`, `resumen`, `rotulos_pt`, `portada` (campos, fecha, número de control, logos) |
| Nivel superior | `perfil` (norma de citas), `estructura`, `idioma`, `voz`, `tiempo_verbal`, `minimo_fuentes`, `anios_fuentes`, `porcentaje_recientes`, `portada_numero`, `tablas_figuras` |
| Fuentes | `fuentes.porcentaje_arbitradas`, `fuentes.minimo_nivel`, `fuentes.evitar` (pregunta) |
| Solo informativo | `reglas_guia`: márgenes, sangría de párrafo, jerarquía de títulos 1-5 (alineación, mayúsculas, negritas, cursivas, tipo oración, punto final, sangría) y tablas y figuras (posición del rótulo, numeración) |
| Preferencias | `preferencias`: registro, extensión, densidad de citas, salida |
| Modelo | con `--modelo-portada`: `vinculante` tipo modelo, ámbito `portada`, spec medida en `portada-modelo.json` |

La estructura trae, por cada capítulo y subcapítulo numerado de la guía, `nombre`, `alias`, `proposito` (la descripción de la guía), `preguntas` (las «preguntas guía» del capítulo), `nivel`, `numero` y `origen`; los preliminares (resumen, índices) con sus límites de palabras.

## Qué no hace

- No inventa: un valor sin patrón no se rellena; va a `preguntas:`.
- No sobrescribe: ni `.editorial.yaml` ni una estructura existente.
- No sube la guía a ningún servicio: todo es local.
- Una guía escaneada (PDF sin texto) sale con código 2: pide OCR o el .docx.

Comprobación con una guía real: `perfilar --comparar <perfil de referencia> --generado <perfil generado> [--comparar-estructura <ref> --generada-estructura <gen>]` imprime el porcentaje de claves que coinciden y los capítulos y subcapítulos hallados.
