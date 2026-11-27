---
description: 'Califica un documento sin tocarlo: auditar + estructura + congruencia + puntuar + medir en una corrida, de solo lectura, con puntaje, hallazgos por prioridad y ajustes sugeridos (automáticos o del usuario)'
argument-hint: '<archivo.docx> [--perfil <id>] [--estructura <género>] [--con-red] [--json resultado.json]'
---
1. Corre `python ${CLAUDE_PLUGIN_ROOT}/scripts/editorial.py calificar $ARGUMENTS`. Es de SOLO LECTURA garantizada: compara el sha256 del archivo y la lista de archivos de su carpeta antes y después, no escribe historial ni copias, y falla (código 2) si algo cambió. Sin red por defecto (`--con-red` verifica las fuentes en línea).
2. Muestra tal cual: la línea «perfil aplicado», el puntaje por dimensión, las medidas efectivas, los hallazgos por prioridad (crítica, mayor, menor) y los «ajustes sugeridos»: automáticos de formato (`/corregir --fiel`), automáticos que cambian texto (quedan como propuesta que el usuario aprueba) y los que requieren al usuario.
3. **No redactes, no reescribas, no cambies estructura, citas ni contenido, y no invoques `redactor` ni `corrector-estilo`.** Si el usuario quiere ajustar, el camino es `/corregir` con `--fiel` (ver `skills/editorial-academica/references/calificar.md`). Lo que requiere al usuario se dice tal cual.

Códigos de salida de los scripts: 0 sin hallazgos críticos ni mayores, 1 con alguno, 2 error de uso o de entrada (o archivo modificado, que sería un defecto).
