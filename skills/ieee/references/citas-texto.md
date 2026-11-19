# IEEE: citas en el texto

Fuente primaria: Reference Guide V 3.28.2025 (`normas/ieee/actual/reference-guide.txt`) + Style Manual actual (`.../style-manual.txt`). Tags: `[Ref Guide 2025 §X]`, `[Style Manual (actual) §X]`.
Ejemplos en inglés verbatim, como los da IEEE.

## 1. Forma básica

| Regla | Detalle | Fuente |
|---|---|---|
| Número entre corchetes, en la línea (no superíndice) | `[1]` | [Ref Guide 2025 §I.A] |
| El corchete va DENTRO de la puntuación | "...as shown in prior work [1]." (el punto sigue al corchete) | [Ref Guide 2025 §I.A] |
| Las referencias "no necesitan" citarse en texto, pero si se citan, siguen estas reglas | Se tratan gramaticalmente como notas al pie o como sustantivos | [Ref Guide 2025 §I.A] |
| Un número = una referencia | Prohibido agrupar varias fuentes bajo un número ("[37] ... ver además X; Y; Z"); cada fuente su número, el comentario pasa a texto o nota al pie | [Style Manual (actual) §References p.14]; [Ref Guide 2025 §II] |
| No combinar referencias | "Do not combine references. There must be only one reference with each number." | [Ref Guide 2025 §II] |
| Cada parte/página citada de la misma fuente NO recibe número nuevo | Se unifica en un número y se cita con notación `[n, ...]` | [Style Manual (actual) §References p.14] |

## 2. Varias referencias juntas (cambio 2025)

Ejemplos verbatim de la guía 2025:
`According to [1]; as demonstrated in [2]; as shown by Brown [4], [5]; as mentioned earlier [2], [4], [5], [6], [7], [9]; Smith [4] and Brown and Jones [5]; Wood et al. [7]`

| Regla | Detalle | Fuente |
|---|---|---|
| Cada número en su propio corchete, separados por coma | `[1], [2], [3]` (la guía solo muestra esta forma; `[1, 2, 3]` no aparece en ningún ejemplo, prohibición implícita) | [Ref Guide 2025 §I.A] |
| Rangos: NO se usa en dash; se escriben TODOS los números | `[1]–[4]` pasa a `[1], [2], [3], [4]` | [Ref Guide 2025 §I.A] |
| La guía 2018 usaba `[2], [4]–[7], [9]`; está superada | Conflicto resuelto a favor de 2025 | [Ref Guide 2025 §I.A] (vs. Ref Guide 2018 §I.A) |
| El en dash del Style Manual actual ya no lista "reference numbers" | Coherente con el cambio | [Style Manual (actual) §The En or Em Dash p.22] |

## 3. Con autor y como sustantivo

| Regla | Ejemplo | Fuente |
|---|---|---|
| Como sustantivo | `as demonstrated in [3]; according to [4]` | [Ref Guide 2025 §I.A] |
| No escribir "in reference [1]" | Escribir `in [1]` | [Style Manual (actual) §References p.14] |
| No poner el nombre del autor antes del número salvo que sea esencial para la oración | "In Smith [1]" se cambia por "in [1]"; se admite "Smith [1] reduced calculated time ..." | [Style Manual (actual) §References p.14] |
| `et al.` en texto cuando la referencia tiene 3 o más autores | `Wood et al. [7]` | [Ref Guide 2025 §I.A] (NOTE) |
| 1 o 2 autores nombrados en texto: se nombran todos | `Smith [4] and Brown and Jones [5]` | [Ref Guide 2025 §I.A] |
| Años no se usan como identificador | Borrar fechas en texto salvo que sean relevantes para el tema | [Style Manual (actual) §References p.14] |
| Si se nombra un autor en texto, verificar su ortografía contra la lista | | [Style Manual (actual) §References p.14] |
| "For example" no va dentro de la lista de referencias; va en el texto | `(For example, see [5].)` | [Style Manual (actual) §References p.14] |

## 4. Citar partes de una referencia

Formas verbatim de la guía 2025 (ex "ibid." con página nueva u otro dato):
`[3, Thm. 1]; [3, Lemma 2]; [3, pp. 5–10]; [3, eq. (2)]; [3, Fig. 1]; [3, Appendix I]; [3, Sect. 4.5]; [3, Ch. 2, pp. 5–10]; [3, Algorithm 5].`

| Regla | Detalle | Fuente |
|---|---|---|
| Parte dentro del mismo corchete tras coma | `[3, Fig. 1]` | [Ref Guide 2025 §I.B] |
| Reescribir "in Fig. 2 of reference [1]" como `in [1, Fig. 2]` | idem "equation (8) of reference [1]" pasa a `[1, eq. (8)]` | [Style Manual (actual) §References p.14] |
| Abreviaturas de parte (2025): `Thm.`, `Sect.`, `pp.`, `eq.`, `Ch.`, `Fig.` | | [Ref Guide 2025 §I.B] |
| CONFLICTO interno: el Style Manual actual aún da `[1, Sec. IV]`, `[1, Th. 4.2]`; la Reference Guide 2025 da `Sect.`, `Thm.` | Gana la Reference Guide 2025 para formato de referencias; aceptar `Sec.`/`Th.` como menor | [Style Manual (actual) §References p.14] vs [Ref Guide 2025 §I.B] |

## 5. ibid. / op. cit. y renumeración

| Regla | Detalle | Fuente |
|---|---|---|
| Eliminar "ibid." y "op. cit." de la lista | Remiten a una referencia previa | [Ref Guide 2025 §I.B] |
| En texto, citar el número de la referencia anterior y renumerar la lista | Si trae página/dato nuevo, usar la forma `[n, ...]` | [Ref Guide 2025 §I.B] |
| Renumerar la lista exige renumerar las citas en texto | Consultar al autor al renumerar | [Ref Guide 2025 §I.B] (NOTE) |
| Notas/frases ajenas al formato de referencia se sacan de la lista: pasan a texto o nota al pie y se renumera | | [Style Manual (actual) §References p.14] |

## 6. Orden de numeración (VACÍO en las fuentes)

Las tres normas oficiales NO dicen textualmente "numerar por orden de primera aparición". Lo único explícito: las primeras citas de figuras y tablas van en orden numérico [Style Manual (actual) §Text Citation of Figures and Tables p.14]. Comprobado en Ref Guide 2018/2023/2025, SM actual y 2024 y Math guides: ninguna lo dice. La numeración por orden de aparición es práctica asumida por el plugin (IEEE-014, [CONV]). Marcarla en reportes como "regla de convención, no textual en la norma".

## 7. Adaptación al español (convención, no regla oficial IEEE)

- Mantener `et al.` sin cursiva ni traducción ("y col." no).
- Mantener corchetes numéricos; no usar "(Autor, año)" salvo perfil APA de citas.
- Frases puente en español: "como se muestra en [3]", "según [4], [6] y [7]". Sustantivo: "en [3]".
- Parte de referencia: conservar la notación inglesa `[3, Fig. 1]`, `[3, pp. 5–10]` (opcional `[3, Sect. 4.5]`).
- Cita al inicio de oración: "En [1] se demuestra..." (no "La referencia [1]...").
