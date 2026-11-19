---
description: 'Redacta una tesis o tesina completa con fuentes verificadas en el formato elegido'
argument-hint: '"<tema>" [--perfil ...] [--salida docx|md|pdf|latex]'
---
Usa la skill `editorial-academica` en modo redactar, con tipo de documento = tesis. Tema y opciones: $ARGUMENTS.
1. Fija el perfil y pide los datos de portada (institución, programa, autor, asesor, fecha) y la estructura de capítulos que exija la institución.
2. Con `investigador-fuentes` busca de 30 a 60 fuentes y confirma la selección con el usuario.
3. Acuerda el índice por capítulos. Redacta capítulo por capítulo con `redactor` (un subagente por capítulo) y después pasa cada uno por `corrector-estilo`.
4. Pasa el documento completo por `juez-formato` y repite hasta obtener el dictamen Aprobado.
5. Genera la salida con la skill `salida-documento`.

Códigos de salida de los scripts del pipeline (`fuentes`, `render`, `auditar`): 0 sin hallazgos, 1 con hallazgos críticos o mayores (o fuentes que fallan), 2 error de uso o de entrada.
