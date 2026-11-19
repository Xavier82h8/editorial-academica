---
name: fuentes-academicas
description: Use when an academic document needs sources — finding relevant, citable, verified literature (artículos, libros, tesis, normas, datasets) for a topic, checking that existing references are real, or building the fuentes.json that feeds APA/IEEE citation rendering.
---

# Fuentes académicas verificadas

**Regla dura:** una fuente entra a `fuentes.json` solo si tiene metadatos de Crossref (DOI que resuelve) o, cuando no tiene DOI, una URL oficial más `_verificacion.fecha_consulta`. Nunca escribas una referencia de memoria.

## Script
`python <raíz>/scripts/editorial.py fuentes ...` (raíz: `${CLAUDE_PLUGIN_ROOT}` en Claude Code; `EDITORIAL_ROOT` o la ruta que dejó el instalador en otras CLI); ejecuta `scripts/fuentes.py` de esta skill (Python 3 + stdlib). Códigos de salida: 0 todo bien, 1 fuentes que fallan, 2 error de uso o de entrada. Sin red, V1-V3 quedan «no verificado», nunca «ok».

| Objetivo | Comando |
|---|---|
| Buscar | `python <raíz>/scripts/editorial.py fuentes "consulta en inglés" --n 15 --clasicos 3 --out fuentes.json` |
| Fuentes en español | añade `--idioma es` (haz otra corrida en inglés y une ambas con `--append`) |
| Solo acceso abierto | `--oa` |
| Ventana temporal | `--desde 2018` (por defecto, últimos 10 años; `--clasicos` ignora la ventana) |
| Añadir un DOI conocido | `python <raíz>/scripts/editorial.py fuentes --doi 10.xxxx/yyy --out fuentes.json --append` |
| Auditar las referencias de un documento | extrae los DOI y luego `python <raíz>/scripts/editorial.py fuentes --verificar fuentes.json` (código de salida 1 si alguno falla) |

Ranking: relevancia en OpenAlex + citas por año + tipo de venue (revista o conferencia). Los trabajos retractados quedan excluidos.

## Proceso
1. Descompón el tema en 2-4 consultas en inglés (más una en español si el contexto es local) y córrelas con `--append`.
2. Lee títulos y resúmenes (OpenAlex `abstract_inverted_index` o la página del DOI) y descarta lo que no sea pertinente. **Relevancia > citas.**
3. Mezcla objetivo para una tesis: 2-4 clásicos, 60 % de fuentes de los últimos 5 años, al menos 1 revisión sistemática, y fuentes primarias para cada afirmación central.
4. Fuentes sin DOI (normas ISO/NOM, leyes, sitios gubernamentales, documentación de software): WebSearch/WebFetch en el sitio **oficial**; agrega a mano el ítem CSL con `URL`, `accessed` y `_verificacion: {fuente: "web-oficial", fecha_consulta: "AAAA-MM-DD"}`.
5. Antes de entregar, corre `--verificar fuentes.json`. Si algo falla, quítalo o reemplázalo.
6. El redactor solo cita `id` presentes en `fuentes.json`. Para cada afirmación, anota la página o sección de donde sale (va en el localizador `[n, p. x]` / `(Autor, año, p. x)`).

## Señales de fuente débil (avisar al usuario)
Revista sin indexar o depredadora (editorial desconocida, cientos de "special issues"), preprint sin revisión por pares cuando existe la versión publicada, más de 15 años de antigüedad sin ser un clásico, autocitas como sostén principal, o Wikipedia/blogs como fuente principal.

## Convenciones de modelado CSL-JSON (APA)
Convenciones que el CSL `<raíz>/plantillas/csl/apa-editorial.csl` espera (cada parche lleva comentario `editorial-academica:` en el CSL). Ejemplos en `<raíz>/tests/corpus/apa7/referencias.json`.
- **Usuario de red social** (X, Instagram, Bluesky, TikTok...): campo `container-title-short` con el usuario, p. ej. `"@BillGates"`. Se imprime `Gates, B. [@BillGates]. (2019, ...)`; la cita en texto sigue siendo `(Gates, 2019)`. Solo con `author` y tipo `post`/`webpage`. Autor grupal: `{"literal": "APA Style"}`.
- **Descriptor de publicación**: `genre: "Post"` y, si hay adjunto, `medium: "Image attached"` -> `[Image attached] [Post]` (corchetes separados, adjunto primero). Sin `medium` -> `[Post]`.
- **Perfil / página con fecha de consulta**: sin `issued` y con `accessed` + `URL` -> `(n.d.)` y `Retrieved ..., from URL`.
- **Historial de publicación** (retractación, reimpresión): texto completo en `references`, con `<i>...</i>` para cursivas; se imprime entre paréntesis tras el DOI/URL. Ej.: `"Retraction published 2012, <i>Revista, 38</i>[10], 1378"`. Requiere `issued`. Para obra original usar `original-date` (imprime `(Original work published 1969)`).
- **Coautor de portada** (`(with Byock, I.)`): `contributor: [{"family": "Byock", "given": "I."}]` en `book`, `pamphlet`, `report`, `standard`. Texto "with" fijo en inglés.
- **Estación del año** (`(2021, Winter)`): mes 21-24 en `issued.date-parts` (21 primavera, 22 verano, 23 otoño, 24 invierno); se imprime en artículos con volumen/número/páginas. Los meses 1-12 no se imprimen en ese caso (APA: revistas solo año).
- **Serie con número** (actas, libros): `collection-title` + `collection-number` -> `*Serie: Vol. 9562. Título*`. En `report`/`document`/`standard` la serie va tras el título, no antepuesta. Sin `collection-number` la serie no se imprime.
- **Edición**: texto completo en `edition` (`"50th anniversary ed."`); el CSL añade `ed.` solo si el valor es numérico.
- **Descriptor con `number`**: si el item tiene `number`, el `genre` se imprime con el número (`Report No. 5`); el descriptor entre corchetes sale de `medium`. Poner `medium` y dejar `genre` para el tipo.
- **Obra de contenido cambiante en base de datos propietaria** (UpToDate): `type: "entry-encyclopedia"` + `container-title` + `issued` + `accessed` + `URL` -> `*UpToDate*. Retrieved ..., from URL` (sin "In"). Sin `accessed` sigue el formato `In *Obra*` (Wikipedia, enciclopedias).
- **Diccionario/enciclopedia con `accessed`**: imprime `Retrieved fecha, from` aunque tenga `issued`; omitir `accessed` si no se debe imprimir.
- **Caso 083** (`alcance: "solo-autores"`): plantilla oficial de 21+ autores sin título real; `<raíz>/tests/run_csl.py` omite los casos con `alcance` (el bloque de autores se valida a mano: 19 primeros, `. . .`, último).
