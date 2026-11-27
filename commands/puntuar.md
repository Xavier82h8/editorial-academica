---
description: 'Puntaje editorial 0-100 de un documento (congruencia, fuentes, formato, estructura, redacción) con las 5 correcciones de mayor impacto e historial'
argument-hint: '<archivo> [--perfil <id>] [--estructura <género>] [--fuentes fuentes.json]'
---
1. Fija perfil y género (de los argumentos, de `.editorial.yaml` o preguntando).
2. Si hay `.md` con `[@id]` y `fuentes.json`, corre el agente `verificador-afirmaciones` para producir `evidencias.json` (V5). Si hay apartado de Método/Resultados, corre el agente `revisor-congruencia` y guarda su salida como `congruencia.json`.
3. Corre `python ${CLAUDE_PLUGIN_ROOT}/scripts/editorial.py puntuar $ARGUMENTS [--evidencias evidencias.json] [--congruencia-llm congruencia.json]`.
4. Muestra el puntaje por dimensión, la banda, los bloqueos y las 5 correcciones con los puntos que suma cada una. Si hay historial, muestra la evolución. Ofrece aplicar las correcciones (para las de formato, con `/corregir --fiel`: solo formato, el texto no cambia). Para calificar sin tocar nada de una sola vez: `/calificar`.

Códigos de salida de los scripts: 0 sin hallazgos (o solo menores), 1 con hallazgos críticos o mayores, 2 error de uso o de entrada (archivo inexistente o no soportado, perfil desconocido o ausente, herramienta externa ausente). En `puntuar`, 1 también si hay bloqueos.
