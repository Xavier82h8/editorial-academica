# Pruebas en vivo en otras CLI

Las pruebas automáticas (`tests/run_portabilidad.py`) comprueban que las skills, rutas e instalador estén bien formados. Esta página registra lo que pasó al **usarla de verdad** desde cada CLI, sin ayuda: se instaló con `scripts/instalar.py --cli <cli> --proyecto <carpeta vacía>`, se copió [`ejemplos/informe-ejemplo.docx`](../ejemplos/informe-ejemplo.docx) y se dio a cada CLI el mismo encargo en modo no interactivo:

> Usa la skill editorial-academica para auditar informe-ejemplo.docx con el perfil apa7. No modifiques ningún archivo. Al final responde solo con: el dictamen, el número de hallazgos por severidad y la lista de IDs de regla encontrados.

Referencia: el juez determinista da **Rechazado, 3 críticas, 16 mayores, 5 menores** (19 IDs distintos).

| CLI | Versión y modelo | Fecha | Qué hizo | Resultado |
|---|---|---|---|---|
| Claude Code | plugin del marketplace | 2026-11 | Usado en todo el desarrollo y en el piloto real | Funciona: comandos `/editorial-academica:*`, subagentes y preguntas de opción múltiple |
| Codex CLI | 0.159.3, `gpt-6-luna` | 2026-11-19 | Leyó `SKILL.md` y `agents/juez-formato.md` desde la ruta que dejó el instalador, consultó `auditar --help`, corrió el juez y revisó el texto del documento (6 comandos) | **Rechazado, 4 críticas, 16 mayores, 5 menores**: los 24 hallazgos del juez más uno de juicio propio, `APA-057` (el dato de la OMS sin cita), que es una regla de agente |
| OpenCode | 2.2.7, `tidepool-alpha-free` | 2026-11-19 | Cargó la skill con su herramienta nativa `Skill`, consultó `auditar --help`, tuvo un tropiezo propio (importar el despachador como módulo) y corrió el juez | **Rechazado, 3 críticas, 16 mayores, 5 menores**: idéntico al juez |
| Gemini CLI | 0.50.0 | sin probar | El modo no interactivo necesita autoaprobar comandos (`--yolo`); queda para una prueba con el usuario delante | Instalador y `commands/*.toml` comprobados por `run_portabilidad.py` |
| Cursor, Copilot CLI | — | sin probar | No instalados en la máquina de pruebas | Instalación real en carpeta temporal comprobada por `run_portabilidad.py` (archivos y rutas) |

Lo que esto muestra: con solo leer las instrucciones instaladas, dos agentes de proveedores distintos encontraron el despachador, usaron el juez determinista y reportaron sus hallazgos sin cambiar severidades; el que añadió algo lo hizo con una regla marcada como de agente, que es lo que `AGENTS.md` pide.

Para repetirlo con tu CLI:

```bash
python scripts/instalar.py --cli codex --proyecto /tmp/prueba     # o gemini, opencode, cursor, copilot
cp ejemplos/informe-ejemplo.docx /tmp/prueba/
cd /tmp/prueba && codex exec "Usa la skill editorial-academica para auditar informe-ejemplo.docx con el perfil apa7"
```
