---
description: 'Juez editorial: audita formato, citas y referencias de un documento contra APA 7, IEEE o un perfil combinado'
argument-hint: '<archivo> [--perfil apa7|apa7-profesional|ieee|apa7-base+ieee-citas|ieee-base+apa7-citas] [--fix]'
---
Delega al agente `juez-formato` con: $ARGUMENTS. Si no se dio `--perfil`, pregunta primero cuál usar. Muestra el dictamen completo. `--fix` no es una opción de ningún script: es una petición al agente. Con ella, el agente aplica solo las reglas `Fix auto: sí` y guarda la versión corregida como `<nombre>.corregido.<ext>`; nunca sobrescribas el original. Para el formato mecánico de un .docx, `/editorial-academica:corregir` es la vía determinista.


Códigos de salida de los scripts: 0 sin hallazgos (o solo menores), 1 con hallazgos críticos o mayores, 2 error de uso o de entrada (archivo inexistente o no soportado, perfil desconocido o ausente, herramienta externa ausente).