# editorial-academica (Gemini CLI)

Editorial y juez académico APA 7 / IEEE. Las instrucciones completas (raíz, comandos, flujos, reglas duras, privacidad) están en AGENTS.md y son las mismas para esta CLI:

@./AGENTS.md

Particularidades de Gemini CLI:
- Raíz del plugin (`<raíz>` en AGENTS.md y en las skills): la carpeta de esta extensión (`~/.gemini/extensions/editorial-academica`) o la variable `EDITORIAL_ROOT`. Scripts: `python <raíz>/scripts/editorial.py <subcomando>`.
- Para preguntas de opción múltiple usa la herramienta `ask_user`; si no está disponible, pregunta en texto con opciones numeradas.
- Los agentes de `agents/*.md` son pasos secuenciales que ejecutas tú, salvo que tu versión soporte subagentes de extensión.
