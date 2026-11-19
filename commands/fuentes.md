---
description: 'Busca y verifica fuentes académicas para un tema y genera fuentes.json'
argument-hint: '"<tema>" [--n 15] [--idioma es]'
---
Delega al agente `investigador-fuentes` con el tema: $ARGUMENTS. La salida va en `./fuentes.json` dentro del directorio de trabajo actual. Muestra al usuario la tabla resumida y el resultado de la verificación.

Códigos de salida: `editorial.py fuentes --verificar` sale 0 si todas las fuentes pasan, 1 si alguna falla (DOI inexistente, metadatos distintos o retractada) y 2 por error de uso o de entrada. Sin red, las comprobaciones quedan «no verificado», nunca «ok».
