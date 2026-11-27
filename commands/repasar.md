---
description: 'Modo de estudio: repasa el documento capítulo por capítulo (qué pide la guía, qué tiene el documento, preguntas guía). No califica'
argument-hint: '<archivo> [--seccion N|"nombre"] [--estructura <id>]'
---
Corre `python ${CLAUDE_PLUGIN_ROOT}/scripts/editorial.py repasar $ARGUMENTS`. Por cada capítulo de la estructura declarada muestra qué pide la guía, qué tiene el documento (encabezado, palabras, citas, tablas, figuras y primeras líneas) y preguntas guía para entenderlo y fortalecerlo. `--seccion N` repasa un capítulo (0 = preliminares) o una sección por nombre.

Es para repasar, no para calificar: no hay puntaje, veredicto ni lista de cotejo (la revisa el docente). Acompaña al usuario con las preguntas, una sección a la vez, y no emitas dictamen; para juzgar existen `/auditar`, `/estructura` y `/puntuar`.

Códigos de salida de los scripts: 0, 2 error de uso o de entrada (archivo inexistente o no soportado, estructura o sección desconocida).
