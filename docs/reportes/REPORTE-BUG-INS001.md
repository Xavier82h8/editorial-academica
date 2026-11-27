# Reporte de Corrección: Bug INS-001 en `corregir.py` e `institucional.py`

## 1. Descripción del Problema
Al ejecutar `editorial.py corregir` sobre documentos con perfil institucional (como `instituto-ejemplo-protocolo.editorial.yaml`, que exige `interlineado: 1.5`), los párrafos con interlineado 1.5 eran sobreescritos con interlineado doble 2.0 (`APA-004`). Posteriormente, al auditar el archivo corregido, surgían hasta 282 hallazgos de `INS-001` («párrafos sin interlineado 1.5 (p. ej. 2.0)»).

---

## 2. Causa Raíz

El fallo se originaba por una interacción en dos niveles entre `institucional.py` y `corregir.py`:

1. **Filtro restrictivo en excepciones derivadas (`scripts/institucional.py`):**
   En `excepciones_derivadas()`, la regla `APA-004` se registraba con `"si_contiene": "1.5"`. Si en el documento original existían párrafos aislados con interlineado 1.0, la evidencia reportada por `auditar.py` era `"interlineado 1.0"`. Dado que `"1.5"` no aparecía en dicha evidencia, `APA-004` no se convertía en excepción institucional (`EXC-APA-004`) y permanecía activa como hallazgo mayor.
2. **Prevalencia de APA-004 sobre formato institucional en `corregir.py`:**
   Al existir un hallazgo de `APA-004`, el grupo `"interlineado"` se activaba en `corregir.py`. La función `corregir_parrafos_formato(d, pares, "interlineado")` forzaba interlineado 2.0 (doble espacio estándar de APA) sobre todos los párrafos de cuerpo fuera de tablas, ignorando que el perfil de equipo definía `interlineado: 1.5`.
3. **Caché desactualizada en `corregir_ins_cuerpo`:**
   Cuando posteriormente se ejecutaba `corregir_ins_cuerpo()`, la condición `abs(p["interlineado"] - il) < 0.05` consultaba el diccionario en memoria `p` obtenido al inicio. Como esos párrafos originalmente tenían 1.5, la función asumió erróneamente que seguían en 1.5 y solo modificó los 4 párrafos que originalmente tenían 1.0, dejando el resto en 2.0.

---

## 3. Cambios Implementados

### A. `scripts/institucional.py`
En `excepciones_derivadas(f)`:
- Se removió la restricción `si_contiene: v` para `APA-004`. Cuando una institución define un interlineado propio (p. ej., 1.5), la exigencia de interlineado doble de APA queda completamente sustituida por `INS-001`. Cualquier párrafo que se desvíe del interlineado institucional es auditado y corregido por `INS-001`, no por `APA-004`.

### B. `scripts/corregir.py`
En `corregir()`:
- Se adelantó la resolución de `equipo_fmt` y `S_ins` antes de aplicar las correcciones de párrafo estándar.
- Se condicionó la ejecución de `corregir_parrafos_formato(d, pares, "interlineado")` para que se omita si `equipo_fmt` define un interlineado institucional (`equipo_fmt.get("interlineado")`), delegando enteramente el ajuste a `corregir_ins_cuerpo()`.
- De manera análoga, se protegió la alineación de párrafos (`corregir_parrafos_formato(d, pares, "alineacion")`) para no forzar alineación izquierda cuando la institución exige `justificada`.

---

## 4. Validación y Pruebas

1. **Suite de pruebas de equipo (`tests/run_equipo.py`):**
   - Ejecución exitosa con código de salida 0:
     `OK == equipo: sin perfil 8 hallazgos, con perfil 7 + 1 excepción institucional; portada_numero: no -> EXC-APA-008; perfil ITE: conforme 0 hallazgos, sembrados detectados; formato institucional INS-001..009 detectado y corregido`
2. **Validación sobre piloto real (`protocolo.ith12.docx`):**
   - Antes de la corrección: `INS-001` reportaba 4 párrafos no conformes (1.0), y la versión previa corregida reportaba 282 párrafos rotos con 2.0.
   - Tras la corrección: `protocolo.ith12.corregido.docx` tiene **0 hallazgos de INS-001**, **0 hallazgos de INS-002** y **0 hallazgos de INS-005**.
   - Los párrafos de cuerpo mantienen su interlineado institucional 1.5 y justificación requerida por el perfil ITE.
