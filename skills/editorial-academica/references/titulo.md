# Título concreto

El título es una decisión del usuario; tú lo conviertes del objetivo general en algo concreto, fijo y sencillo, sin detallar de más.

## Receta
`[Nombre o sigla]: [objeto] + [para qué o ámbito]`, de 8 a 15 palabras.

- **Sí**: el nombre del proyecto, el objeto (qué es: «tutor musical», «sistema de inventarios») y el propósito o ámbito (para qué o para quién).
- **No**: método o técnica (LoRA, prompting, «comparando», «mediante», «basado en»), tecnologías, modelos y versiones (Gemma 3, Python 3.12), formatos (ABC), cifras ni porcentajes.
- **Promesas**: no prometas lo que el protocolo no evalúa. «Para apoyar», «para contribuir a» o «para explorar» en lugar de «para mejorar», «garantizar», «optimizar» o «encargado de», salvo que el diseño mida ese efecto.
- **Coherencia**: el objeto y el propósito del título deben aparecer en el objetivo general (CON-021). Si no, o el título dice más de lo que el objetivo promete o falta ajustar el objetivo.

## Pasos
1. `python <raíz>/scripts/editorial.py titulo <doc>`: lee el título de la portada y el objetivo general y diagnostica (palabras, sigla, detalle que sobra, promesas, cifras, términos del objetivo sin recoger).
2. Redacta **3 o 4 opciones** distintas (por ejemplo: la más corta, una con el ámbito, una con el propósito, una con la sigla ampliada). Evalúalas: `titulo <doc> --opcion "…" --opcion "…"` y muestra a cada una con su conteo de palabras y sus observaciones.
3. **Pide al usuario que elija** (AskUserQuestion o lista numerada). No elijas por él.
4. Fija la elegida en `.editorial.yaml`: `titulo: "TUTOR-AI: tutor musical con inteligencia artificial para apoyar la enseñanza de la música"`. Pasa a ser vinculante: la portada debe coincidir (INS-010) y cambiarlo exige repetir el proceso.
5. Ofrece ajustar el objetivo general para que use los términos del título (CON-021); no lo reescribas sin confirmación.

## Ejemplo
Objetivo: «Desarrollar y evaluar un prototipo de tutor musical generativo en español, ajustado con LoRA, que adapte sus respuestas al nivel del usuario y produzca notación ABC verificable, comparando su desempeño con un modelo base y con un modelo base con prompting especializado».

| Opción | Palabras |
|---|---:|
| TUTOR-AI: tutor musical con inteligencia artificial para apoyar la enseñanza de la música | 13 |
| TUTOR-AI: tutor musical en español que adapta sus respuestas al nivel del estudiante | 13 |
| TUTOR-AI: tutor musical generativo para la enseñanza de la teoría musical | 11 |

Fuera: LoRA, ABC, prompting, «comparando…» (son método), «verificable» (es un resultado) y «para mejorar» (el protocolo solo lo evalúa).

Ajustes en `.editorial.yaml` (opcionales): `titulo_config: {max_palabras: 15, sobran: ["texto"], promesas: ["texto"]}` suma términos a las listas por defecto.
