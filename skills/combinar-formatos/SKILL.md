---
name: combinar-formatos
description: Use when a document must mix two styles — one norm as the base layout (página, portada, encabezados, tablas, figuras, ecuaciones) and another for citations and the reference list (e.g. maquetación APA con referencias IEEE, o IEEE con citas APA), or when resolving a conflict between APA 7 and IEEE rules in the same document.
---

# Combinar formatos

Principio: **una capa = una norma**. Nunca mezclar reglas dentro de la misma capa.

## Capas

| Capa | Gobierna | La decide |
|---|---|---|
| **Base** | tamaño/márgenes, fuente, interlineado, portada, resumen, encabezados y su numeración, párrafos, listas, tablas y figuras (numeración, títulos, notas), ecuaciones, apéndices, mecánica (números, mayúsculas, abreviaturas), lenguaje sin sesgo | `base:` del perfil |
| **Citas** | cita en el texto, cita textual (marca de página o localizador), lista de referencias (título de sección excepto su estilo de encabezado, orden, sangría, formato de cada entrada), citas de IA generativa | `citas:` del perfil |

El **estilo visual del encabezado** de la lista de referencias lo pone la base; **el contenido y el orden** de la lista los pone la norma de citas.

## Perfiles disponibles
`perfiles/apa7.yaml`, `perfiles/ieee.yaml`, `perfiles/apa7-base+ieee-citas.yaml`, `perfiles/ieee-base+apa7-citas.yaml`. Para una plantilla institucional, copia el más cercano a `perfiles/<institucion>.yaml` y declara solo `overrides`.

## Conflictos resueltos

| Conflicto | APA base + IEEE citas | IEEE base + APA citas |
|---|---|---|
| Cita en el texto | `[n]`, por orden de primera aparición; sin rangos: `[1], [2], [3]` (Ref Guide 2025) | `(Autor, año)` / Autor (año) |
| Cita textual | `[n, p. 5]` | `(Autor, año, p. 5)` |
| Título de la lista | "Referencias", formato de encabezado de nivel 1 APA, en página nueva | "REFERENCIAS" con el estilo de encabezado IEEE sin número romano |
| Orden de la lista | numérico por aparición | alfabético por autor |
| Sangría | columna `[n]` alineada | francesa de 0.5 in |
| Autores en la lista | hasta 6, si son más: primero + *et al.* | hasta 20; si son 21 o más: 19 + … + último |
| Tablas y figuras | APA (Table 1 / Figure 1 en negrita, título en cursiva arriba) | IEEE (TABLE I arriba; Fig. 1. abajo) |
| Ecuaciones | numeradas (1) a la derecha (APA lo permite); referir como Ecuación 1 | (1); "Eq. (1)" solo al inicio de oración |
| Notas al pie | APA las desaconseja; úsalas solo si la institución lo pide | según IEEE |
| Uso de IA generativa | cita según IEEE (software / sitio en línea) + declaración de uso en Método o nota (APA) | entrada en la lista según APA; declaración de uso según APA |

## Proceso
1. Carga el perfil y lee `excluir_grupos` y `overrides`.
2. Carga solo los `references/` de la capa correspondiente: base → formato/encabezados/tablas/mecánica; citas → citas-texto/referencias.
3. Renderiza las referencias con el `csl` del perfil (la norma de citas).
4. El juez aplica solo los grupos activos de cada checklist, y los `overrides` tienen precedencia.
5. Todo conflicto nuevo que no esté en la tabla anterior: decidir con el principio de capas, añadirlo a la tabla y avisar al usuario.
