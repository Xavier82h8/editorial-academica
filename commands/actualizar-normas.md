---
description: 'Descarga las normas oficiales APA e IEEE vigentes, las compara con el snapshot y lista las reglas afectadas'
---
1. **APA**: abre https://apastyle.apa.org/style-grammar-guidelines con Playwright (el sitio tiene protección anti-bot, así que curl no sirve). Dentro de la página, recorre con `fetch` todas las rutas `/style-grammar-guidelines/*` y los posts del blog sobre IA, y guarda el texto por página en `${CLAUDE_PLUGIN_ROOT}/normas/apa/pages/`. Revisa también `/style-grammar-guidelines/updates`.
2. **IEEE**: en https://journals.ieeeauthorcenter.ieee.org/create-your-ieee-journal-article/create-the-text-of-your-article/ieee-editorial-style-manual/ toma los enlaces actuales (Google Docs) del Style Manual, la Reference Guide, la Math Guide y la hoja de abreviaturas. Expórtalos (`/export?format=txt`, `/pub` o `format=csv`) a `normas/ieee/actual/`.
3. Haz el diff contra los archivos anteriores (git), actualiza `normas/VERSION` y `normas/SHA256SUMS`, y busca en `apa.csl` e `ieee.csl` la última versión de citation-style-language/styles.
4. Para cada cambio, localiza las reglas afectadas en `skills/*/references/checklist.md` y en las referencias, y propón la edición con la cita nueva. No edites sin la confirmación del usuario. Haz el commit con el mensaje `normas: snapshot AAAA-MM-DD`.

Códigos de salida: este comando no ejecuta scripts del plugin (usa Playwright y git); los errores los reporta el agente.
