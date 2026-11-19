---
description: 'Convierte un .docx con citas escritas a mano a otro perfil de formato (APA 7, IEEE o combinado), re-renderizando citas y referencias'
argument-hint: '<archivo.docx> --a <perfil destino> (alias --perfil) [--de apa7|ieee] [--out ruta.docx] [--sin-red] [--informe ruta.md]'
---
Usa la skill `editorial-academica` en modo convertir: $ARGUMENTS.

El trabajo lo hace `convertir` (`scripts/convertir.py`) (determinista; el modelo solo revisa el informe y decide qué hacer con lo que queda pendiente).

```
python ${CLAUDE_PLUGIN_ROOT}/scripts/editorial.py convertir doc.docx --a ieee --out C:/ruta/salida.docx
python ${CLAUDE_PLUGIN_ROOT}/scripts/editorial.py convertir doc.docx --a apa7 --de ieee --sin-red
```

1. **Ejecuta el script.** Opciones: `--a` perfil destino (`apa7`, `ieee`, `apa7-base+ieee-citas`, `ieee-base+apa7-citas`; `--perfil` es un alias válido, pero documentamos `--a`); `--de` norma de origen (por defecto se autodetecta); `--out` ruta del .docx (por defecto `<doc>.<perfil>.docx` junto al original; el original nunca se sobrescribe); `--sin-red` no consulta Crossref (usa solo la caché `doi/` del directorio de caché (`EDITORIAL_CACHE`; ver README)); `--informe` ruta del informe (por defecto `<salida>.informe.md`); `--idioma es-MX|en-US` (por defecto se detecta).
2. **Qué hace.**
   - Lee el .docx con pandoc (AST: conserva tablas e imágenes, que se extraen a `<salida>_media/`).
   - Localiza la lista de referencias (último encabezado «Referencias», «Fuentes consultadas», «2.10 Fuentes consultadas», etc.) y la parsea a CSL-JSON con `scripts/refs_csl.py` (APA o IEEE). Cada entrada lleva `_verificacion`: `{metodo: doi-crossref|parser, estado: verificada|no-verificada|discrepancia, notas}`.
   - Si la entrada tiene DOI, `scripts/doi_csl.py` pide el CSL-JSON a doi.org (solo se envía el DOI; con caché y reintento). Si título, año y primer autor coinciden, Crossref completa los campos que faltan (volumen, número, páginas, autores truncados con «et al.») y queda «verificada»; si no coinciden queda «discrepancia» y se conserva lo que dice el documento. Sin DOI queda «no-verificada»: no se inventa ningún metadato.
   - Convierte las citas del texto, también las de las tablas, a citas de pandoc: parentéticas APA (`(Hu et al., 2022)`, grupos con `;`, localizadores `p.`, `pp.`, `cap.`, `párr.`, `arts. 27 y 78`, prefijos `véase`, `as cited in`, varios años, `s. f.-a`, sufijos `2026a`), narrativas (`Zheng et al. (2023)`), autores grupales con sigla (`[SCJN]` la primera vez, `SCJN` después, `LFDA`) e IEEE (`[1]`, `[1, Fig. 2]`, `[1], [3]`, `[1]–[3]`, `Brown [4]`).
   - Quita la lista original y pone «Referencias» con `::: {#refs}`; las entradas que no se citan se conservan con `nocite`.
   - Renderiza con `scripts/render.py` (CSL y plantilla del perfil destino) y pasa `scripts/auditar.py` al resultado.
3. **Revisa el informe** (`<salida>.informe.md`): entradas verificadas, discrepancias y no verificadas; citas convertidas y **no mapeadas con su contexto** (quedan intactas en el texto); entradas no citadas; hallazgos del juez; y lo que se pierde en la conversión (portada, estilos personalizados, campos de Word).
4. Para las citas no mapeadas y las discrepancias, propón la corrección al usuario; no las resuelvas inventando datos. Después de cualquier edición manual, vuelve a pasar `juez-formato` (agente) con el perfil destino para lo que requiere juicio.

Pruebas: `python -I tests/run_convertir.py` (ida y vuelta del parser con el corpus dorado y de las citas, sin red); también corre dentro de `tests/run_todo.py`.

Códigos de salida de los scripts: 0 sin hallazgos (o solo menores), 1 con hallazgos críticos o mayores, 2 error de uso o de entrada (archivo inexistente o no soportado, perfil desconocido o ausente, herramienta externa ausente). La salida nunca sobrescribe el original ni su `.md`; si coincidiera con la entrada, aborta con 2.
