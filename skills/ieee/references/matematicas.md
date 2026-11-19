# IEEE: matemáticas, ecuaciones y LaTeX

Fuentes: `[Math Guide 2023 §X]` = IEEE "Editing Mathematics" V 10.27.2023 (`normas/ieee/actual/math-guide.txt`, PRIMARIA); `[SM p.N §X]` = Style Manual actual; `[Math LaTeX guide p.N]` = "IEEE Math Typesetting Guide for LaTeX Users" (`normas/ieee/IEEE-Math-Typesetting-Guide-for-LaTeX-Users.txt`, secundaria/histórica, útil para código LaTeX).

## 1. Numeración y referencia de ecuaciones

| Regla | Fuente |
|---|---|
| Numeración consecutiva de principio a fin del artículo; sin repetidos ni faltantes | [Math Guide 2023 §F]; [SM p.25 §Equation Numbers] |
| Número a ras de la derecha, en la línea de la última línea de la ecuación | [SM p.25 §Equation Numbers] |
| Estilos permitidos si el autor los usa: por sección `(1.1)`, `(1.2.1)`, `(A1)`; consistencia obligatoria | [Math Guide 2023 §F]; [SM p.13 §Text Equations] |
| Apéndices: numeración continua (mejor) o reiniciada `(A1)`, `(A2)` (permitida) | [Math Guide 2023 §F]; [SM p.13] |
| Guiones y puntos en el número: CONFLICTO. Math Guide 2023: normalmente se eliminan, `(1a)` y no `(1-a)`/`(2.a)`, consistente. Style Manual actual: se aceptan `(1a)`, `(1.1)`, `(1-1)` si son consistentes. Resolver: exigir consistencia y marcar `(1-a)` como menor | [Math Guide 2023 §F] vs [SM p.13] |
| En texto se cita solo el número entre paréntesis: `in (1)`; `Equation` solo al inicio de oración (`Equation (1) shows ...`) | [SM p.24 §Math 14] |
| No usar paréntesis dobles en texto: `(see (10))` pasa a `[see (10)]`; se conservan en matemáticas | [SM p.26 §III.A 8] |
| Ecuación de una referencia: `[1, eq. (8)]`, no "equation (8) of reference [1]" | [SM p.14 §References]; [Ref Guide 2025 §I.B] |

## 2. Gramática de la ecuación y puntuación [Math Guide 2023 §A; SM p.24-25 §Math]

- Una ecuación es parte de la oración: tiene sujeto y verbo; sigue las reglas gramaticales del texto.
- Una ecuación que cierra la oración termina en punto. Los comas finales se eliminan salvo que sean críticos para la puntuación de la oración.
- Solo se pone puntuación para introducir la ecuación si el texto previo es una oración completa: `where we had the following:` y luego `x = Y + Z.`
- Puntos suspensivos matemáticos: solo tres, entre comas y sobre la línea base (`x1, x2, …, xn`); con operadores van centrados (`x1 + x2 + … + xn`); no `x1, x2 … xn`.
- Condiciones: coma o paréntesis y espacio de 2 em entre la expresión principal y la condición; condiciones múltiples separadas por `;`; sin coma antes del símbolo "para todo" (∀).
- Quitar comas alrededor de variables en texto; verificar paréntesis/corchetes de intervalos (`[0,1)`).
- Distinguir "ell" y "oh" en cursiva de uno y cero.

## 3. Cursiva, redonda y negrita [Math Guide 2023 §I, §G; SM p.24-25; Math LaTeX p.2]

| Elemento | Composición | Fuente |
|---|---|---|
| Variables (en texto y en fórmulas) | Cursiva; deben coincidir en texto y en ecuaciones | [Math LaTeX guide p.2]; [SM p.24 §Math 1] |
| Vectores | Negrita; la Math Guide dice "usualmente, si el autor los distingue", el SM "negrita cursiva", la guía LaTeX "siempre negrita" | [Math Guide 2023 §G]; [SM p.24 §Math 1]; [Math LaTeX guide p.2] |
| Funciones y operadores | Redonda (roman) | [Math Guide 2023 §I] |
| Unidades, abreviaturas de unidades, palabras completas y abreviaturas de palabras | Redonda | [SM p.25] |
| Sub/superíndices variables | Cursiva; si son abreviaturas de palabras (`in`, `out`), redonda; un solo carácter puede ir en cursiva salvo que genere inconsistencia | [SM p.25] |
| Acrónimos en ecuaciones (`MSE`, `NCC`, `RMS`) | Redonda, igual que en el texto (`\text{MSE}`) | [Math LaTeX guide p.14-16] |
| Lógica booleana (`AND`, `OR`, `NOR`, `NAND`, `XOR`, `EXCLUSIVE-OR`) y palabras de instrucción | Versalitas (el Apéndice D del PDF 2024 las marca "small caps") | [SM 2024 Apéndice D p.43+] |

La tabla §H del Math Guide 2023 (cursiva / redonda / versalitas: `RC`, `p-n`, `p-i-n`, `A.M.`, `e.g.`, `et al.`, `in situ`, etc.) llega aplanada en el texto extraído (celdas vacías, sin marcas de columna) y la asignación columna-elemento no es recuperable; no hay otra copia de "Editing Mathematics" en el repo. Solo se confirman por fuentes independientes: versalitas para `A.M.`/`P.M.` y operadores lógicos AND, OR, NOT-AND, NOT-OR, EXCLUSIVE-OR [SM 2024 App. D, anotación "(small caps)"]; comandos de computadora en versalitas y lenguajes (Cobol, Java, LISP) en mayúscula/minúscula normal [SM p.23 §Capitalization]. El resto (`RC`, `p-n`, `e.g.`, `et al.`, `in situ`...) queda como laguna: ninguna regla del checklist depende de ella.

Funciones SIEMPRE en redonda [Math Guide 2023 §I]: `ad, arg, cos, cosh, cot (no ctg), coth, csc (no cosec), csch, curl, det, diag, dim, div, exp, hom, Im, inf, ker, lim, liminf, limsup, ln, log, lub, max, min, mod, Pr, Re, sec, sin, sinh, tan, tanh, tr, Tr, wr`. Espacio fino a ambos lados de funciones y diferenciales: `sin tt = log μr`, no `sintt` (no hace falta junto a un verbo u operador) [Math Guide 2023 §G].
Los corchetes angulares no son los signos menor/mayor que [Math Guide 2023 §G]. Abreviaturas de funciones y símbolos en redonda: §L del Math Guide 2023; el listado de [Math LaTeX guide p.2-3] añade `arcsin`, `arctan`, `int`, `Log`; `sgn` está en ambas.
`\approx` para aproximación numérica, `\simeq` equivalencia asintótica, `\sim` proporcionalidad, `\cong` congruencia [Math Guide 2023 §J].

## 4. Matemáticas en línea [Math Guide 2023 §B; SM p.24 §Math 9-10]
1) Cortar tras un verbo u operador (que quede en la línea superior).
2) Fracciones no apiladas en línea: usar barra `(c-d)/(k+4)`, con paréntesis si hay signo menos.
3) Signos colectivos (Σ, ∏, ∫) con límites al costado, no arriba/abajo.
4) Exponenciales largos: `exp[(zx2 + y)(α – 2yx) + zx]` en vez de `e` con superíndice largo.
5) Opcional: evitar raíces con barra larga: `(x + α)½`.

## 5. Ecuaciones destacadas (display): saltos y alineación [Math Guide 2023 §C, §D]
- Cortar en verbos matemáticos (`=`, `≥`, `≡`) y alinear sobre ellos; con un solo verbo, cortar en operadores y alinear a la derecha del verbo.
- Separar ecuaciones con un em quad si caben en la línea, o apilar y alinear en el verbo.
- Cortes dentro de paréntesis: en un operador, alineando dentro del paréntesis izquierdo; los pares de delimitadores deben tener tamaño proporcional al contenido.
- Punto al final de una fracción, caso o delimitador cerrado.
- Ecuaciones con el verbo en la mitad derecha: cortar antes de un operador.
- Solidus: cortar tras `/`. Producto implícito entre paréntesis: insertar `×` o `·` al cortar. Integrales: preferible no cortar hasta el diferencial.
- Algoritmos: no se editan; se conservan título, formato, puntuación y ubicación del autor [Math Guide 2023 §G].
- Jerarquía de delimitadores anidados: `{[( )]}` [Math Guide 2023 §J].
- Teoremas/pruebas: título del teorema como encabezado terciario sin número arábigo; prueba como cuaternario [Math Guide 2023 §E].
- Tipografía: todas las fuentes entre texto y ecuaciones deben coincidir [SM p.28 §IV Appendix, "Editing Mathematics"].

## 6. Convenciones LaTeX [Math LaTeX guide p.4-19] (guía secundaria; las reglas de composición de arriba mandan)

| Hacer | No hacer |
|---|---|
| `\[ ... \]` o `\begin{equation*}...\end{equation*}` para una línea sin número | `$$ ... $$` (obsoleto, "never"; mal espaciado vertical) |
| `\begin{equation}...\end{equation}` para una línea numerada | `eqnarray` (obsoleto) |
| `\begin{align}...\end{align}` para varias líneas (numeradas o no) | |
| Entorno `cases` para definiciones por casos, con `&` para alinear y `\text{...}` para las palabras (`\text{if }`, `\text{otherwise}`); columnas alineadas a la izquierda | `array` con `\left\lbrace`; palabras en cursiva; espaciado con `\;\;\;` (usar `\hfill` o tabulaciones) |
| `\max`, `\min`, `\sin`, `\arg` o `\text{arg min}` | `min`, `arg min` sin comando (salen en cursiva) |
| Límites arriba y abajo de operadores en display: sin `\nolimits` (que es para texto en línea o subelementos) | `\nolimits` en ecuaciones display |
| Dentro de fracciones los límites quedan al lado automáticamente: quitar `\limits` | |
| `\text{MSE}`, `\text{NCC}`, `\text{RMS}` para acrónimos | Acrónimos como variables en cursiva |
| `\left( ... \right)`, `\left[ ... \right]` para delimitadores que crecen con el contenido | `(` `)` fijos alrededor de fracciones o raíces altas |
| `\mathcal` para caligráfica | `rsfs` usado en lugar de `mathcal` |
| Usar dos columnas (IEEEtran) para detectar ecuaciones que desbordan la columna y recodificar como ecuaciones de ancho de página | |
Autores de Word: IEEE recomienda MathType 7 (desde 2019) y NO el editor de ecuaciones de Word [Math LaTeX guide p.20]. IEEE Xplore HTML usa MathJax (LaTeX/MathML) [Math LaTeX guide p.20].
Las plantillas IEEEtran sirven solo para estimar paginación; los saltos finales pueden cambiar [Math LaTeX guide p.19].

## 7. Alfabeto griego y símbolos [Math Guide 2023 §K, §L]
Tabla de alfabeto griego (Alpha a Omega) y de abreviaturas de funciones y símbolos en redonda en la §K/§L del Math Guide 2023; consultar `normas/ieee/actual/math-guide.txt`.

## 8. Adaptación al español (convención, no regla oficial IEEE)
- Texto: "la ecuación (1)", "de (2) se obtiene". La norma IEEE en texto corrido usa solo `(1)`; "Ecuación (1)" al inicio de oración es la traducción de `Equation`.
- Separador decimal: IEEE usa punto; en español la coma decimal es convención local y debe ser consistente. Espacio fino para miles se mantiene (`62 000`).
- Sin traducción de nombres de funciones: `sin`, `tan` (no `sen`, `tg`); si el documento usa `sen`/`tg`, es convención española, consistente y en redonda.
- Palabras en ecuaciones (`\text{si}`, `\text{en otro caso}`) en redonda.
