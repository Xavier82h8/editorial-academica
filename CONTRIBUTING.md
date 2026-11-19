# Cómo contribuir

Gracias por querer mejorar editorial-academica. Este documento resume cómo preparar el entorno, correr las pruebas y añadir reglas.

## Entorno
```bash
git clone https://github.com/Xavier82h8/editorial-academica
cd editorial-academica
python -m pip install -r requirements-dev.txt   # ejecución + matplotlib (estadísticas)
```
Requiere Python 3.10+ y pandoc 3.x en el PATH (`winget install --id JohnMacFarlane.Pandoc`, `brew install pandoc`, `apt install pandoc`). xelatex solo hace falta para PDF y LaTeX.

Las normas oficiales (`normas/`) no se distribuyen. Sin ellas, las pruebas que las necesitan se saltan con el aviso «SALTADA». Para obtenerlas: `python scripts/obtener_normas.py`.

## Correr las pruebas
```bash
python tests/run_todo.py --rapido --sin-red     # lo mismo que corre la CI
python tests/run_todo.py                        # completa (llama a pandoc: CSL, citas, convertir)
python tests/run_portabilidad.py                # skills, rutas, instalador, catálogo
```
Debe terminar con `TODO OK`. Ningún cambio puede bajar los umbrales (precisión y recall >= 0.95; 0 falsos positivos en las muestras oficiales).

## Añadir una regla
1. **ID**: familia y número libres (`APA-xxx`, `IEEE-xxx`, `CON-xxx`, `EST-xxx`). Revisa el último en `docs/REGLAS.md`.
2. **Checklist**: añade la entrada con severidad, descripción y fuente oficial (sección de la norma) en `skills/apa7/references/checklist.md` o `skills/ieee/references/checklist.md`; las reglas de congruencia y de estructura tienen sus propios catálogos.
3. **Implementación**: si es mecánica, impleméntala en el script que corresponda (`scripts/auditar.py`, `congruencia.py`, `estructura.py` o `maquetacion.py`) emitiendo el ID. Si requiere juicio, déjala solo en el checklist para el agente. Si el arreglo es seguro, añádelo a `scripts/corregir.py` (`REGLAS`).
4. **Caso sembrado**: añade un error sembrado que la regla detecte (generadores en `tests/generar_docs.py` o `tests/ciegos/`) y su entrada en `esperado.json`.
5. **0 falsos positivos**: corre las muestras oficiales y los documentos correctos (`python tests/run_todo.py`); cualquier hallazgo nuevo sobre documentos legítimos es un falso positivo y bloquea el cambio.
6. **Regenera lo derivado**:
   ```bash
   python scripts/catalogo.py                    # docs/REGLAS.md
   python scripts/instalar.py --generar-toml     # commands/*.toml
   ```
7. Anota el cambio en `CHANGELOG.md`.

## Estilo
- Python 3.10, solo biblioteca estándar más las dependencias de `requirements.txt`.
- Mensajes, docstrings y documentación en español; los identificadores existentes se respetan.
- Finales de línea LF (`.gitattributes` los fuerza). Los scripts deben funcionar igual en Windows, macOS y Linux.
- Códigos de salida: 0 limpio, 1 hallazgos, 2 error de uso o de entrada.
- No añadas datos personales ni documentos reales a las pruebas: usa material sintético.

## Reportar falsos positivos
Usa la plantilla «Falso positivo» de Issues. Incluye el ID de regla, el texto mínimo y anónimo que lo dispara y por qué cumple la norma, citando la sección oficial. Un fragmento de tres líneas basta.
