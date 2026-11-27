---
description: 'Ficha técnica de medidas efectivas (márgenes, sangría, interlineado, fuente, número de página) de un Word y su PDF, y reglas medibles que pide el usuario'
argument-hint: '<doc.docx|pdf> [--pdf doc.pdf | --render] [--json ficha.json] [--seccion N] [--regla "márgenes 3 cm izquierda"]… [--medidas] [--contra perfil]'
---
1. Corre `python ${CLAUDE_PLUGIN_ROOT}/scripts/editorial.py medir $ARGUMENTS`: da el valor EFECTIVO (herencia resuelta como Word) por sección (página, márgenes, numeración, posición del número de página) y por grupo de párrafos y estilo (fuente, tamaño, interlineado, espacios, sangrías, alineación), cada longitud en cm, pt e in, con las excepciones por párrafo. Con `--pdf doc.pdf` o `--render` mide también el PDF (márgenes reales, número de página por página, sangría visible) y avisa de las discrepancias docx/PDF (aviso, no violación).
2. Una instrucción del usuario («márgenes 3 cm izquierda», «sangría francesa 1.27 cm en referencias», «interlineado 1.5») va con `--regla "frase"`: CUMPLE, NO CUMPLE o no medible, con el origen. Si sale `PREGUNTA:`, hazla al usuario (opciones) y repite: nunca adivines unidad, alcance ni cuál de dos valores vale. Guárdala en `medidas:` de `.editorial.yaml` si es regla del documento (`auditar` la emite como INS-016).
3. Lo que salga «no medible: …» se reporta tal cual, con su porqué; nunca se da por cumplido. Sigue `skills/editorial-academica/references/medir.md`.

Códigos de salida de los scripts: 0 sin incumplimientos, 1 con alguna regla que no cumple, 2 error de uso o de entrada.
