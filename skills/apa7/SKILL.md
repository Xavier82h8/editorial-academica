---
name: apa7
description: Use when writing, formatting or auditing a document in APA 7th edition style (paper format, citations, references, tables, bias-free language), including when APA is only the base layout or only the citation layer of a combined profile.
---

# APA 7.ª edición (módulo de conocimiento)

Fuente única: snapshot oficial de apastyle.apa.org (páginas de style-grammar-guidelines y posts de IA del blog). La fecha del snapshot está en `<raíz>/normas/VERSION` (línea `snapshot:`). Nunca se completa con memoria: si una regla no está en los `references/`, se responde "No cubierto por el snapshot; consultar Publication Manual §x" solo cuando la página nombra la sección. Si la consulta supera 6 meses desde esa fecha, sugerir `/actualizar-normas`.

Los ejemplos de reglas se conservan en inglés tal como los da APA. Las adaptaciones al español ("y" por "&", "s.f." por "n.d.", "(Ed.)/(Eds.)", "como se citó en") están rotuladas "Adaptación al español (convención, no regla oficial APA)". En APA 7 NO se escribe "Recuperado de" antes de un DOI o URL (solo "Retrieved [fecha], from" cuando la obra cambia y no se archiva; "Recuperado el [fecha] de" es la adaptación al español, convención no APA).

## Perfiles: qué capa cargar

- APA completo (`apa7`): todos los archivos según la tarea.
- APA solo base (`apa7-base+ieee-citas`): cargar formato-pagina, portada, encabezados, tablas-figuras, mecanica y gramatica-sesgo; NO citas-texto ni referencias-* (gobierna IEEE).
- APA solo citas (`ieee-base+apa7-citas`): cargar citas-texto, referencias-principios, referencias-por-tipo-1/2 y los grupos CIT y REF del checklist; la maquetación la gobierna IEEE.

## Índice de `references/` (cargar solo lo que la tarea necesita)

| Archivo | Cuándo cargarlo |
|---|---|
| `formato-pagina.md` | Márgenes, fuente, interlineado, sangrías, running head, numeración, orden de páginas, apéndices, accesibilidad; diferencias estudiante vs profesional |
| `portada.md` | Armar o revisar la portada (estudiante y profesional); tesis y disertaciones |
| `encabezados.md` | Niveles 1-5, formato exacto y reglas ("Introduction" no se rotula) |
| `citas-texto.md` | Cualquier cita en el texto: autor-fecha, et al., grupos, cita textual y en bloque, secundarias, comunicaciones personales, plagio |
| `referencias-principios.md` | Elementos de una entrada, orden, DOI/URL, base de datos, información faltante, obras incluidas, archivo |
| `referencias-por-tipo-1.md` | Plantilla y ejemplo de revista, libro, capítulo, informe, tesis, congreso, dataset, software, preprint, diccionario |
| `referencias-por-tipo-2.md` | Web, redes sociales (X, Bluesky, LinkedIn, Instagram, TikTok, Facebook), video, podcast, cine, OER, arte, IA |
| `ia-generativa.md` | Citar IA, describir su uso, prompts, declaración de contribución de IA |
| `tablas-figuras.md` | Componentes, numeración, notas, ubicación, color, atribución de copyright |
| `mecanica.md` | Abreviaturas, mayúsculas (title/sentence case), cursivas y comillas, listas, números, puntuación, ortografía |
| `gramatica-sesgo.md` | Tiempo verbal, voz, primera persona, they singular, antropomorfismo, lenguaje sin sesgo por categoría |
| `checklist.md` | Auditar: 145 reglas `APA-001`..`APA-145` (APA-140 a 144 de la revisión cruzada; APA-145 decisión del usuario) por grupo (PAG, POR, ENC, CIT, REF, TAB, MEC, LEN, IA) con severidad y columna `Fix` |

## Las 10 reglas más infringidas

1. **Citas y lista no coinciden**: toda cita está en la lista y viceversa; apellidos y años idénticos (APA-034, APA-035).
2. **Cita textual sin página**: autor, año y `p.`/`pp.` o párrafo/sección/marca de tiempo; nunca ubicaciones Kindle (APA-048, APA-051).
3. **et al.**: 3 o más autores se citan como `Primer autor et al.` desde la primera cita; en la lista se enumeran hasta 20 autores (APA-038, APA-064).
4. **"&" vs "and"**: `&` solo en parentética; en narrativa "and" (en español "y") (APA-037).
5. **Referencia mal formada**: título de artículo en sentence case sin cursiva; revista y volumen en cursiva; `8(3)` sin coma; sin punto tras DOI; DOI como `https://doi.org/...`; sin "Retrieved from" (APA-069, APA-072, APA-075, APA-076, APA-079).
6. **Lista**: rótulo "References", sangría francesa 0,5 in, orden alfabético, doble espacio (APA-059 a APA-061).
7. **Encabezados**: niveles exactos, sin numeración, sin encabezado "Introduction" (APA-025 a APA-031).
8. **Página**: márgenes 1 in, interlineado doble, texto sin justificar, número de página arriba a la derecha, running head solo profesional (APA-001, APA-004, APA-006, APA-008, APA-009).
9. **Portada**: título en negrita centrado y elementos en el orden de estudiante o profesional (APA-017 a APA-023).
10. **Tablas/figuras sin atribución ni mención**: número en negrita, título en cursiva, mención en el texto, atribución de copyright si se reproducen (APA-089, APA-091, APA-095). Cierra la lista el uso de IA sin declarar o con la IA como autora (APA-132, APA-133).

## Cómo usar este módulo

- Redactar: cargar solo los archivos del perfil; usar `fuentes.json` verificado para referencias; formatear con CSL y comprobar con el checklist.
- Auditar: recorrer `checklist.md` del grupo aplicable al perfil; cada hallazgo cita `ID`, ubicación, corrección y la fuente (`§ Manual | ruta de página`); las reglas `Fix: sí` las aplica el agente a petición (no hay flag `--fix` en los scripts); `python <raíz>/scripts/editorial.py corregir <doc.docx> --perfil apa7` automatiza las que `<raíz>/docs/REGLAS.md` marca como «corregible».
- Tesis y trabajos institucionales: la institución puede sustituir márgenes, portada y orden de páginas; registrar como excepción, no como violación.
- Rutas de fuente (`paper-format/title-page`, etc.) son relativas a `normas/apa/pages/` del repositorio (`a/b` = archivo `a__b.md`; `references/examples/x` = `references__examples__x.md`).
