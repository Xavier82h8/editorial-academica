---
description: 'Revisa la congruencia interna de un documento (objetivos-método-resultados-conclusiones, cifras, siglas, referencias cruzadas, alcance causal)'
argument-hint: '<archivo>'
---
Delega al agente `revisor-congruencia` con: $ARGUMENTS. Muestra la matriz de trazabilidad y los hallazgos CON-xxx. Guarda la salida en `congruencia.json` junto al documento para que `/puntuar` la use.

Códigos de salida de los scripts: 0 sin hallazgos (o solo menores), 1 con hallazgos críticos o mayores, 2 error de uso o de entrada (archivo inexistente o no soportado, perfil desconocido o ausente, herramienta externa ausente).
