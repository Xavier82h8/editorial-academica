# APA 7: IA generativa (citar, describir el uso, declaración de contribución)

Fuente: `normas/apa/blog/blog__cite-generative-ai-references.md` (McAdoo et al., 2025-09-09), `blog__how-to-cite-chatgpt.md` (archivado, reemplazado), `blog__ai-contribution-statement.md` (Woods y Alea Albada, 2026-09-15), `normas/apa/pages/references__examples__ai-references.md`. Formato de referencias: `referencias-por-tipo-2.md` §8.

Estatus de las fuentes: los posts de blog son guía de APA Style; el de la declaración de contribución dice explícitamente que NO cambia las pautas de APA Style y que la declaración no es requisito formal salvo que lo fije el docente o la institución.

## 1. Principios

- No presentar texto generado por IA como propio (conducta académica no ética). Hay usos legítimos (buscar información, resumir junto con la lectura, editar o analizar la escritura propia, lluvia de ideas, traducir, revisar consistencia y estilo, generar tablas y figuras, crear y refinar código); lo permitido depende de políticas del docente, departamento o editorial.
- Transparencia: si se usó IA al redactar, normalmente hay que revelarlo y citar el chat y/o la herramienta. APA recomienda pecar por exceso de transparencia.
- La IA no puede ser autora: no es una persona consciente que pueda dar consentimiento y asumir derechos y responsabilidades de autoría (el post de declaración de contribución indica que APA Journals dice "no", citando la Parte 3, que no está en el snapshot). El autor de la referencia es la empresa desarrolladora.
- El autor humano debe verificar la salida de la IA (exactitud). Las referencias que genera una IA pueden ser falsas (el post de 2023 halló una referencia inexistente con un DOI de otro artículo): verificar toda fuente que sugiera.
- Citar la IA aunque no se haya usado, si el trabajo trata sobre IA.

## 2. Plantillas

`[§ Manual 10.10 (software) | ai-references; blog cite-generative-ai-references]`

| Qué citar | Plantilla | Ejemplo |
|---|---|---|
| Herramienta en general | `AI Company. (year). *Tool/Model name* [Description]. URL` | `OpenAI. (2025). *ChatGPT* [Large language model]. https://chatgpt.com` |
| Chat concreto | `AI Company. (year, month day). *Title of chat* [Generative AI chat]. Tool/Model. URL of chat` | `OpenAI. (2026, February 10). *Top 10 writing topics for high school graduates* [Generative AI chat]. ChatGPT. https://chatgpt.com/share/698b9233-1b58-8008-858d-cede516f4240` |

Otros ejemplos oficiales: `Google. (2025). *Gemini 3 Flash* [Large language model]. https://gemini.google.com`; `Perplexity AI. (2026). *Perplexity* [Large language model]. https://www.perplexity.ai`; `Anthropic. (2025). *Claude 4 Sonnet* [Large language model]. https://claude.ai/new` (post de 2025).

Citas: parentética `(OpenAI, 2025)`; narrativa `OpenAI (2025)`; varias: `(Anthropic, 2025; Google, 2025; OpenAI, 2025; Perplexity AI, 2025)`.

Elementos:
- Autor: empresa que desarrolló la herramienta.
- Fecha: herramienta = año de la última actualización (si no se sabe, preguntar a la IA; si no indica, año de copyright del sitio o app). Chat = año, mes y día en que ocurrió o terminó.
- Título: herramienta = nombre general (ChatGPT, Gemini) o del modelo (ChatGPT-5, Gemini 3 Flash). Chat = título del chat en cursiva y sentence case; conviene editar el título en la herramienta para que sea descriptivo.
- Descripción entre corchetes (sin cursiva): `[Large language model]` para herramientas de chat (otras posibles según el tipo de modelo); `[Generative AI chat]` para chats (adaptable).
- Fuente: herramienta = solo URL (autor = editorial, no se repite). Chat = nombre de la herramienta o modelo + URL del chat (usar el enlace de compartir).
- Números de versión: ya no se incluyen por defecto (2025); incluir el nombre del modelo si está disponible o solo el nombre de la herramienta. Si la IA muestra versión, va entre paréntesis sin cursiva tras el nombre. El formato antiguo `ChatGPT (Mar 14 version)` del post de 2023 está archivado y reemplazado.
- Quien reabre un enlace compartido puede continuar el chat, pero en las herramientas probadas los demás lectores solo ven la conversación original.

Adaptación al español (convención, no regla oficial APA): `OpenAI. (2025). *ChatGPT* [Modelo de lenguaje de gran tamaño]. https://chatgpt.com` y `[Chat de IA generativa]` si el documento está en español; mantener nombre de empresa y herramienta sin traducir.

## 3. Cuándo citar el chat y cuándo la herramienta

`[§ Manual 8.1, 9.21 | blog cite-generative-ai-references]`

| Uso | Qué citar | Dónde revelarlo |
|---|---|---|
| Chat cuya salida se cita o se reproduce | Chat concreto (si ayuda al lector) | Método (o introducción en ensayos/reseñas); cita en el texto + lista |
| Editar, analizar, organizar o refinar la escritura propia | Herramienta en general | Método o nota del autor + cita en el cuerpo + referencia general; no hace falta exponer cada borrador |
| Traducir una fuente (o pocas oraciones) para entenderla | No citar la IA; citar la fuente original si se cita o parafrasea | Cuidar matices; para adaptar instrumentos usar traductor humano |
| Traducir texto propio para entrega o publicación | Herramienta en general | Declarar que se usó IA para traducir; revisión por hablante nativo |
| Crear o refinar código (R, SPSS) | Herramienta; el chat solo si el código es central | Según centralidad del código |
| Tablas, figuras u otras representaciones visuales | Herramienta | Nota de la tabla o figura |
| IA como parte de la metodología (tutor, terapeuta con participantes) | Herramienta en general | Conservar los chats como datos; el informe solo muestra resúmenes; consultar la política institucional de privacidad |

Ejemplos de frases en el texto: `I used Claude 3.7 Sonnet (Anthropic, 2025), a generative artificial intelligence (AI) tool, to generate a list of grammatical concepts that high school students should know by the end of the 12th grade.` / `I used ChatGPT (OpenAI, 2025) to edit my paper and provide feedback on clarity and flow.` Se puede añadir mención general en la nota del autor, pero la cita en el cuerpo sigue siendo necesaria (las políticas de nota del autor varían por editorial).

## 4. Prompts

- Documentar los prompts para los registros propios; incluirlos en el texto, un apéndice o material suplementario solo si ayudan al lector (decidir con editor o docente).
- No van en la referencia (la referencia es del chat, no del prompt): no encajan en autor-fecha-título-fuente, no sirven para recuperar la obra y serían largos.
- Ejemplo oficial: `I provided the following prompt to Gemini (Google, 2025): "Please create an image of students in a classroom studying grammar concepts." After reviewing the initial image created, I refined the images by adding more detail ...`
- Si se reproduce la respuesta larga, ponerla en un apéndice o material suplementario y mencionarlo en el texto: `(OpenAI, 2023; see Appendix A for the full transcript)` (post de 2023, archivado).

## 5. Declaración de contribución de IA (AI contribution statement)

`[§ Manual: sin sección; guía externa | blog ai-contribution-statement]`

- No es requisito de APA Style: solo si lo exige el instructor o la institución. El post "no representa un cambio a las pautas de APA Style".
- Es un documento estructurado que el docente da al estudiante para declarar por escrito cómo usó IA en cualquier parte del trabajo (generar ideas, desarrollar hipótesis, editar el texto final). Funciona como punto medio entre documentar todo el historial de chat y no decir nada.
- Beneficios: transparencia, registro sistemático, mayor conciencia metacognitiva del estudiante; permite a expertos juzgar si el uso fue legítimo.
- Ejemplo de declaración de los autores: `AI contribution statement: No AI tools were used in any way to help us develop this blog post.`
- Detalles de la guía (PDF "AI Contribution Statement Guide", 277 KB) y de la plantilla: No cubierto por el snapshot (el PDF no está capturado). Referencia citada: Alea Albada, N., & Woods, V. E. (2025). Giving credit where credit is due: An artificial intelligence contribution statement for research methods writing assignments. *Teaching of Psychology*, *52*(3), 279–284. https://doi.org/10.1177/00986283241259750
- Convención del plugin (no APA): si la institución no pide formato, redactar la declaración como párrafo breve en Método o nota del autor con: herramienta y modelo, para qué se usó (tarea concreta), qué se revisó y verificó, y cita/referencia.

## Gaps

- Partes 2 y 3 de la serie (IA como motor de búsqueda e integrada en software común; si la IA está "permitida" en APA Style) son nombradas en las páginas pero no están en el snapshot: No cubierto por el snapshot; consultar los posts en apastyle.apa.org/blog (cite-generative-ai-allowed).
- Política de autoría de revistas APA sobre IA: solo se afirma que APA Journals dice "no" a IA como autor (McAdoo et al., 2025b, citado en el post).
