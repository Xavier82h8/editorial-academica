---
description: 'Redacta un informe, reporte o artículo corto con fuentes verificadas en el formato elegido'
argument-hint: '"<tema>" [--perfil ...] [--salida docx|md|pdf|latex] [--paginas N]'
---
Usa la skill `editorial-academica` en modo redactar, con tipo de documento = informe o artículo (estructura IMRyD o la que pida el usuario). Tema y opciones: $ARGUMENTS. Busca de 8 a 20 fuentes (con resumen). `--paginas N` son páginas de cuerpo, sin portada ni referencias; el redactor las convierte a palabras (APA ≈ 275 por página). Sigue el mismo pipeline que `/tesis`, pero redacta en una sola pasada.

Códigos de salida de los scripts del pipeline (`fuentes`, `render`, `auditar`): 0 sin hallazgos, 1 con hallazgos críticos o mayores (o fuentes que fallan), 2 error de uso o de entrada.
