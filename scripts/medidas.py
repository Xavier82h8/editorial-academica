#!/usr/bin/env python3
"""Instrucciones del usuario como REGLAS MEDIBLES: parser de frases (español e inglés básico) y evaluador sobre la ficha de `medir`.

Una regla es `{que, valor, unidad, tolerancia, alcance, origen}`:
  que        margen_superior | margen_inferior | margen_izquierdo | margen_derecho | margenes (los cuatro) | sangria_primera_linea |
             sangria_francesa | sangria_izquierda | sangria_derecha | interlineado | fuente | tamano | espacio_antes | espacio_despues |
             numero_pagina | alineacion
  valor      número (con `unidad` cm, in, mm, pt) o texto: interlineado «1.5» / «doble» / «sencillo» (unidad `lineas`) o N pt con
             `modo: exacto`; fuente «Times New Roman»; numero_pagina «superior derecha» | «inferior centro» | «ninguno»;
             alineacion justificada | izquierda | centro | derecha
  tolerancia en la unidad de la regla; por defecto la de scripts/unidades.py (margen y sangría ±0.05 cm, espacio ±0.5 pt, tamaño ±0.25 pt)
  alcance    documento (cuerpo, títulos, resumen y referencias) | todo | cuerpo | resumen | referencias | titulos | titulo N | portada | seccion N
  origen     de dónde viene («usuario 2026-11-27: «márgenes 3 cm izquierda»»); sale en el hallazgo INS-016

En .editorial.yaml: `medidas:` es una lista de esas reglas (o de `{frase: "…", origen: "…"}`, que se parsea al leer; una frase que no se
entiende es error de uso). `editorial.py medir doc.docx --regla "frase"` las evalúa sin tocar el perfil.

Lo que el parser no entiende NO se adivina: vuelve como pregunta con opciones (unidad que falta, alcance que falta, valores que se
contradicen, «sangría 1.27» sin decir de qué). Lo que no tiene valor medible («que se vea profesional») sale «no medible: …» con su porqué.
Estados de una regla: cumple, no cumple, no medible. Lo equivalente (1.27 cm = 0.5 in = 36 pt; interlineado ×1.5 = exacto 18 pt con 12 pt)
cumple y lo dice.
"""
import datetime
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import unidades as U  # noqa: E402

QUE = ("margen_superior", "margen_inferior", "margen_izquierdo", "margen_derecho", "margenes", "sangria_primera_linea", "sangria_francesa",
       "sangria_izquierda", "sangria_derecha", "interlineado", "fuente", "tamano", "espacio_antes", "espacio_despues", "numero_pagina", "alineacion")
LADOS_MARGEN = ("superior", "inferior", "izquierdo", "derecho")
ALCANCES = ("documento", "todo", "cuerpo", "resumen", "referencias", "titulos", "portada")
ALINEACIONES = ("justificada", "izquierda", "centro", "derecha")
NOMBRE_QUE = {"margen_superior": "margen superior", "margen_inferior": "margen inferior", "margen_izquierdo": "margen izquierdo",
              "margen_derecho": "margen derecho", "sangria_primera_linea": "sangría de primera línea", "sangria_francesa": "sangría francesa",
              "sangria_izquierda": "sangría izquierda", "sangria_derecha": "sangría derecha", "interlineado": "interlineado", "fuente": "fuente",
              "tamano": "tamaño de fuente", "espacio_antes": "espacio antes", "espacio_despues": "espacio después", "numero_pagina": "número de página",
              "alineacion": "alineación"}


class ErrorMedidas(ValueError):
    """Bloque `medidas:` inválido; los llamadores lo convierten en error de uso (código 2)."""


def sin_acentos(t):
    return U.sin_acentos(t)


# ================================================================ normalizar reglas (YAML o parser)
def _alcance_valido(a):
    a = str(a or "documento").strip().lower()
    a = sin_acentos(a)
    if a in ALCANCES:
        return a
    m = re.fullmatch(r"(titulo|seccion)\s*(\d+)", a)
    if m and (m.group(1) == "seccion" or 1 <= int(m.group(2)) <= 5):
        return f"{m.group(1)} {int(m.group(2))}"
    raise ErrorMedidas(f"alcance «{a}» no válido (documento, todo, cuerpo, resumen, referencias, titulos, titulo N, portada, seccion N)")


def normalizar_regla(raw, n=0):
    """Una entrada de `medidas:` -> regla normalizada (dict). Lanza ErrorMedidas con el número de entrada si es inválida."""
    pre = f"medidas[{n}]: "
    if not isinstance(raw, dict):
        raise ErrorMedidas(pre + "debe ser un bloque {que, valor, unidad, tolerancia, alcance, origen}")
    que = sin_acentos(str(raw.get("que", ""))).strip().lower().replace(" ", "_")
    if que not in QUE:
        raise ErrorMedidas(pre + f"`que` «{raw.get('que')}» no válido; usa uno de: {', '.join(QUE)}")
    r = {"que": que}
    v = raw.get("valor")
    if v is None:
        raise ErrorMedidas(pre + "falta `valor`")
    u = raw.get("unidad")
    if que in ("fuente", "numero_pagina", "alineacion"):
        r["valor"] = str(v).strip()
        if que == "alineacion":
            a = sin_acentos(r["valor"]).lower()
            a = {"justificado": "justificada", "justify": "justificada", "justified": "justificada", "left": "izquierda", "center": "centro",
                 "centrado": "centro", "centrada": "centro", "right": "derecha"}.get(a, a)
            if a not in ALINEACIONES:
                raise ErrorMedidas(pre + f"`valor` de alineacion: {', '.join(ALINEACIONES)}")
            r["valor"] = a
        if que == "numero_pagina":
            z = _pos_numero(r["valor"])
            if z is None:
                raise ErrorMedidas(pre + "`valor` de numero_pagina: «superior derecha», «inferior centro», «ninguno»…")
            r["valor"] = z if z == "ninguno" else f"{z[0]} {z[1]}"
        r["unidad"] = ""
    elif que == "interlineado":
        if isinstance(v, str):
            k = sin_acentos(v).strip().lower()
            if k in U.NOMBRES_INTERLINEADO:
                v = U.NOMBRES_INTERLINEADO[k]
            else:
                try:
                    v = float(k.replace(",", "."))
                except ValueError:
                    raise ErrorMedidas(pre + "`valor` de interlineado: 1, 1.5, 2, sencillo, doble, o N con unidad pt y modo exacto")
        u = U.unidad(u) if u else "lineas"
        if u not in ("lineas", "pt"):
            raise ErrorMedidas(pre + "interlineado: `unidad` es lineas (múltiplo) o pt (con modo: exacto)")
        r["valor"], r["unidad"] = float(v), u
        r["modo"] = "exacto" if (u == "pt" or str(raw.get("modo", "")).lower() == "exacto") else "multiplo"
        if r["modo"] == "exacto":
            r["unidad"] = "pt"
    else:
        try:
            val = float(str(v).replace(",", "."))
        except ValueError:
            raise ErrorMedidas(pre + f"`valor` «{v}» debe ser un número")
        uu = U.unidad(u) if u else ("pt" if que in ("tamano", "espacio_antes", "espacio_despues") else None)
        if uu is None:
            if val == 0 and que.startswith(("sangria", "espacio")):
                uu = "cm" if que.startswith("sangria") else "pt"
            else:
                raise ErrorMedidas(pre + f"falta `unidad` (cm, in, mm, pt) para {NOMBRE_QUE.get(que, que)}")
        if uu not in ("cm", "in", "mm", "pt"):
            raise ErrorMedidas(pre + f"`unidad` «{u}» no válida (cm, in, mm, pt)")
        r["valor"], r["unidad"] = val, uu
    t = raw.get("tolerancia")
    if t is not None:
        try:
            r["tolerancia"] = float(t)
        except (TypeError, ValueError):
            raise ErrorMedidas(pre + "`tolerancia` debe ser un número (en la unidad de la regla)")
        if r["tolerancia"] < 0:
            raise ErrorMedidas(pre + "`tolerancia` no puede ser negativa")
    else:
        r["tolerancia"] = None
    try:
        r["alcance"] = _alcance_valido(raw.get("alcance"))
    except ErrorMedidas as e:
        raise ErrorMedidas(pre + str(e))
    if que.startswith("margen") and r["alcance"] not in ("documento", "todo") and not r["alcance"].startswith("seccion"):
        raise ErrorMedidas(pre + "los márgenes son de la sección o del documento (alcance documento o seccion N)")
    if que == "numero_pagina" and r["alcance"] not in ("documento", "todo"):
        raise ErrorMedidas(pre + "el número de página es de todo el documento (alcance documento)")
    r["origen"] = str(raw.get("origen") or "").strip()
    return r


def expandir(r):
    """`margenes` -> las cuatro reglas de margen; el resto, tal cual."""
    if r["que"] != "margenes":
        return [r]
    return [{**r, "que": "margen_" + lado} for lado in LADOS_MARGEN]


def normalizar_medidas(lista):
    """Lista de `medidas:` -> (reglas expandidas, preguntas de frases que no se entienden, no medibles). Error de uso si una entrada es inválida."""
    if lista is None:
        return [], [], []
    if not isinstance(lista, list):
        raise ErrorMedidas("medidas: debe ser una lista de reglas {que, valor, unidad, tolerancia, alcance, origen}")
    reglas, preguntas, no_med = [], [], []
    for n, raw in enumerate(lista, 1):
        if isinstance(raw, dict) and "frase" in raw and "que" not in raw:
            res = parsear(str(raw["frase"]), str(raw.get("origen") or ""))
            if res["preguntas"]:
                raise ErrorMedidas(f"medidas[{n}]: la frase «{raw['frase']}» no se entiende: " + res["preguntas"][0]["pregunta"])
            reglas += res["reglas"]
            no_med += res["no_medibles"]
            continue
        reglas += expandir(normalizar_regla(raw, n))
    return reglas, preguntas, no_med


def leer_medidas_yaml(doc, equipo=None):
    """(reglas, no medibles, ruta) del bloque `medidas:` del .editorial.yaml del documento. ([], [], None) si no hay."""
    import auditar
    ruta = auditar.buscar_equipo(str(doc), equipo)
    if not ruta or not ruta.exists():
        return [], [], None
    try:
        cfg = auditar.yaml.safe_load(ruta.read_text(encoding="utf-8")) or {}
    except auditar.yaml.YAMLError:
        return [], [], None
    if not isinstance(cfg, dict) or not cfg.get("medidas"):
        return [], [], ruta
    try:
        reglas, _, nm = normalizar_medidas(cfg["medidas"])
    except ErrorMedidas as e:
        import cli
        cli.error(f"{ruta}: {e}")
    return reglas, nm, ruta


# ================================================================ parser de frases
NUM_PALABRAS = {"un": 1, "una": 1, "uno": 1, "one": 1, "dos": 2, "two": 2, "tres": 3, "three": 3}
UNI = r"(?:centimetros?|centimeters?|centimetres?|cms?|milimetros?|millimeters?|mm|pulgadas?|pulg|inch(?:es)?|in(?!\s+(?:the|a|an|all|each|every|this|that|my|our|both)\b)|puntos?|points?|pts?|pt|twips?)"
QTY = re.compile(r"(?<![\w.])(\d+(?:[.,]\d+)?|una?|uno|one|dos|two|tres|three)\s*(?:\"|″)?\s*(" + UNI + r")?(?![a-z])")
QTY_COMILLA = re.compile(r"(\d+(?:[.,]\d+)?)\s*(\"|″)")
SUBJETIVO = re.compile(r"profesional|bonit|elegan|limpi[oa]|agradable|legible|moderno|estetic|se vea|se ve\b|luzca|quede bien|verse bien|"
                       r"look\b|nice|clean|professional|pretty|readable|elegant|appealing|modern|tidy|ordenad|prolij|atractiv|"
                       r"bien presentad|presentable|llamativ|sobri[oa]", re.I)
FUENTES_CONOCIDAS = ["times new roman", "arial", "calibri", "cambria", "courier new", "georgia", "verdana", "helvetica", "garamond", "tahoma",
                     "century gothic", "aptos", "palatino", "book antiqua", "trebuchet", "segoe ui", "lucida sans unicode", "comic sans", "open sans",
                     "roboto", "liberation serif", "computer modern"]
PARRILLA_PALABRAS = {"de", "del", "la", "el", "tamano", "size", "a", "en", "tipo", "sea", "es", "con", "y", "e", "and", "of", "puntos", "pt", "letra",
                     "fuente", "tipografia", "font"}

CAT = [  # (nombre, regex sobre texto sin acentos, minúsculas)
    ("margenes", re.compile(r"\bmargen(?:es)?\b|\bmargins?\b")),
    ("sangria", re.compile(r"sangri|sangrad|\bindent")),
    ("espacios", re.compile(r"espaci\w*\s+(?:previo|anterior|antes|despues|posterior)|espacio\s+(?:previo|anterior|antes|despues|posterior)|"
                            r"(?:spacing|space)\s+(?:before|after)|sin\s+espacios?\s+entre\s+parrafos|espaci\w*\s+entre\s+parrafos|espacio\s+entre\s+parrafos|"
                            r"(?:before|after)\s+(?:spacing|paragraph)|space\s+between\s+paragraphs|spacing\s+between\s+paragraphs|"
                            r"(?:antes|despues)\s+de\s+(?:cada\s+)?parrafo")),
    ("interlineado", re.compile(r"interlinead|espaciado\s+(?:entre\s+lineas|doble|sencillo|simple|exacto)|line\s+spacing|linespacing|doble\s+espaci|espaci\w*\s+doble|"
                                r"espacio\s+(?:doble|sencillo|simple)|double[- ]?spac|single[- ]?spac|1[.,]5\s+(?:lineas|lines|spac)|lineas?\s+de\s+separacion|"
                                r"espacio\s+y\s+medio|one and a half")),
    ("numero_pagina", re.compile(r"numero\s+de\s+pagina|numeros?\s+de\s+pagina|numeracion|page\s+numbers?|paginacion|numerar|paginas?\s+numerad|page\s+numbering")),
    ("fuente", re.compile(r"\bfuentes?\b|tipografia|tipo\s+de\s+letra|\bletra\b|\bfonts?\b|typeface|\btamano\b|\bsize\b|"
                          + "|".join(re.escape(f) for f in FUENTES_CONOCIDAS))),
    ("alineacion", re.compile(r"justific|alineacion|alineado|alineada|\balign|justified|justify|centrad[oa]\b|centered")),
]

SCOPES = [  # (alcance, regex)
    ("titulo N", re.compile(r"(?:titulos?|encabezados?|headings?)\s+(?:de\s+|del\s+)?(?:nivel|level)\s*(\d)|(?:nivel|level)\s*(\d)\s+(?:headings?|titulos?|encabezados?)|(?:heading|titulo)\s+(\d)\b")),
    ("seccion N", re.compile(r"\b(?:seccion|section)\s*(\d+)\b")),
    ("resumen", re.compile(r"\bresumen\b|\babstract\b")),
    ("referencias", re.compile(r"referencias|bibliografia|\breferences?\b|reference list|lista de (?:fuentes|referencias)|fuentes de informacion")),
    ("titulos", re.compile(r"\btitulos\b|encabezados\b|\bheadings\b|\btitles\b")),
    ("portada", re.compile(r"portada|\bcover\b|title page")),
    ("documento", re.compile(r"todo\s+el\s+(?:documento|texto|trabajo)|documento\s+completo|whole\s+document|entire\s+document|toda\s+la\s+tesis|todo\s+el\s+escrito|en\s+todo\b")),
    ("cuerpo", re.compile(r"\bcuerpo\b|parrafos|body|paragraphs|\btexto\b|\btext\b")),
]


def _hoy():
    return datetime.date.today().isoformat()


def _qtys(s, orig):
    """[(pos, valor, unidad|None)] de las cantidades de la cláusula (sin acentos); `s` y `orig` tienen igual longitud."""
    out = []
    for m in QTY.finditer(s):
        raw, un = m.group(1), m.group(2)
        if not un and re.search(r"(?:seccion|section|nivel|level|titulo|heading|encabezado|capitulo|chapter)\s*$", s[:m.start()]):
            continue  # «sección 2», «nivel 3»: es un número de parte, no una medida
        if raw in NUM_PALABRAS:
            if not un:
                continue  # «una» suelta no es cantidad
            v = float(NUM_PALABRAS[raw])
        else:
            v = float(raw.replace(",", "."))
        out.append((m.start(), v, U.unidad(un) if un else None, m.end()))
    for m in QTY_COMILLA.finditer(s):
        if not any(abs(p - m.start()) < 1 for p, *_ in out):
            out.append((m.start(), float(m.group(1).replace(",", ".")), "in", m.end()))
    # «3 cm» y «(1 pulgada)» que dicen lo mismo no son dos valores
    out.sort()
    return out


def _alcances(s):
    """[alcance…] mencionados (en orden de aparición) o []. `titulo N` y `seccion N` salen ya con su número."""
    hall = []
    for nombre, rx in SCOPES:
        for m in rx.finditer(s):
            if nombre == "titulo N":
                n = next(g for g in m.groups() if g)
                if 1 <= int(n) <= 5:
                    hall.append((m.start(), f"titulo {int(n)}"))
            elif nombre == "seccion N":
                hall.append((m.start(), f"seccion {int(m.group(1))}"))
            else:
                hall.append((m.start(), nombre))
    # «titulo nivel 2» no es además «titulos»/«cuerpo»: quita los genéricos que caen dentro de una mención específica
    hall.sort()
    out = []
    for pos, a in hall:
        if a not in out:
            out.append(a)
    if any(a.startswith("titulo ") for a in out) and "titulos" in out:
        out.remove("titulos")
    if "documento" in out and "cuerpo" in out:
        out.remove("cuerpo")
    return out


def _pos_numero(texto):
    """«superior derecha» -> ('superior', 'derecha'); «ninguno» -> 'ninguno'; None si no se entiende por completo."""
    s = sin_acentos(texto).lower()
    if re.search(r"\bsin\b|\bninguno\b|\bno page\b|no\s+number|\bnone\b|\bno\s+numer", s):
        return "ninguno"
    sup = bool(re.search(r"superior|arriba|encabezado|header|\btop\b|parte de arriba", s))
    inf = bool(re.search(r"inferior|abajo|\bpie\b|footer|bottom|parte de abajo", s))
    izq = bool(re.search(r"izquierd|\bleft\b", s))
    der = bool(re.search(r"derech|\bright\b", s))
    cen = bool(re.search(r"centr|\bcenter\b|\bcentre\b|\bmiddle\b", s))
    if sup == inf or (izq + der + cen) != 1:
        return None
    return ("superior" if sup else "inferior", "izquierda" if izq else "derecha" if der else "centro")


def _pregunta(frase, texto, opciones=()):
    return {"frase": frase, "pregunta": texto, "opciones": list(opciones)}


def _alcance_o_pregunta(frase, s, requiere=True):
    """(alcances, pregunta|None). Sin alcance y `requiere`: pregunta; si no, `documento`."""
    a = _alcances(s)
    if a:
        return a, None
    if requiere:
        return [], _pregunta(frase, "¿En qué parte del documento aplica? No lo dice y no lo adivino.",
                             ["cuerpo (párrafos de texto)", "resumen", "referencias", "títulos (o «título nivel N»)", "todo el documento"])
    return ["documento"], None


def _regla(que, valor, unidad, alcance, origen, modo=None, nota=None):
    r = {"que": que, "valor": valor, "unidad": unidad, "tolerancia": None, "alcance": alcance, "origen": origen}
    if modo:
        r["modo"] = modo
    if nota:
        r["nota"] = nota
    return r


def _cl_margenes(frase, s, orig, origen):
    reglas, pregs = [], []
    qs = _qtys(s, orig)
    # ¿dos cantidades que dicen lo mismo («2.54 cm (1 pulgada)»)? se funden
    lados = []
    for m in re.finditer(r"izquierd\w*|\bleft\b|derech\w*|\bright\b|superior\w*|\btop\b|arriba|inferior\w*|\bbottom\b|abajo", s):
        t = m.group(0)
        lados.append((m.start(), "izquierdo" if t.startswith(("izq", "left")) else "derecho" if t.startswith(("der", "right")) else
                      "superior" if t.startswith(("sup", "top", "arr")) else "inferior"))
    todos = re.search(r"todos?\s+los\s+lados|todos\s+los\s+margenes|cuatro\s+lados|all\s+(?:four\s+)?sides|each\s+side|every\s+side|en\s+todos|por\s+todos|de\s+todos", s)
    otros = [m.start() for m in re.finditer(r"los\s+demas|las\s+demas|el\s+resto|los\s+otros|los\s+restantes|the\s+(?:other|rest|remaining)|others|demas\s+lados", s)]
    if re.search(r"\b(?:o|or|ó)\b", re.sub(r"\bo\b(?=\s+\d)", "o", s)) and len(qs) >= 2 and re.search(r"\d(?:[.,]\d+)?\s*(?:" + UNI + r")?\s+(?:o|or)\s+\d", s):
        return [], [_pregunta(frase, "Dices dos medidas alternativas («X o Y»). ¿Cuál es la que vale?", [f"{v:g}" + (f" {u}" if u else "") for _, v, u, _ in qs[:3]])], []
    if not qs:
        return [], [_pregunta(frase, "¿Cuánto miden los márgenes? No dices la medida.",
                              ["2.54 cm (1 pulgada, «Normal» de Word)", "1.27 cm (0.5 in, «Estrecho»)", "otra medida: dímela con su unidad"])], []
    # «2.54 cm (1 pulgada)»: dos cantidades contiguas que dicen lo mismo en otra unidad son una sola
    dedup = []
    for q in qs:
        if dedup and dedup[-1][2] and q[2] and dedup[-1][2] != q[2] and q[0] - dedup[-1][3] < 8                 and abs(U.a_pt(dedup[-1][1], dedup[-1][2]) - U.a_pt(q[1], q[2])) < 0.5:
            continue
        dedup.append(q)
    qs = dedup
    unidades = {u for _, _, u, _ in qs if u}
    if len(unidades) > 1:
        return [], [_pregunta(frase, "Mezclas unidades en los márgenes; confirma cada medida con su unidad.", [f"{v:g} {u or '?'}" for _, v, u, _ in qs])], []
    if not unidades:
        return [], [_pregunta(frase, "¿En qué unidad están los márgenes?", ["centímetros (cm)", "pulgadas (in)", "puntos (pt)"])], []
    unidad = next(iter(unidades))
    comp = []
    if any(u is None for _, _, u, _ in qs):
        comp.append("unidad tomada de la otra medida de la frase")
    eventos = sorted([(p, "S", l) for p, l in lados] + [(p, "Q", (v, u or unidad)) for p, v, u, _ in qs] + [(p, "O", None) for p in otros] +
                     ([(todos.start(), "A", None)] if todos else []))
    asign = {}
    if eventos and eventos[0][1] in ("S",) or (eventos and eventos[0][1] == "O"):
        modo = "S"
    else:
        modo = "Q"
    seg = {"s": [], "o": False, "a": False, "q": None}
    segs = []

    def cierra():
        nonlocal seg
        if seg["q"] is not None or seg["s"] or seg["o"] or seg["a"]:
            segs.append(seg)
        seg = {"s": [], "o": False, "a": False, "q": None}
    for _, tipo, dato in eventos:
        if modo == "S":                      # lados antes de su cantidad
            if tipo == "S":
                seg["s"].append(dato)
            elif tipo == "O":
                seg["o"] = True
            elif tipo == "A":
                seg["a"] = True
            else:
                seg["q"] = dato
                cierra()
        else:                               # cantidad y luego sus lados
            if tipo == "Q":
                cierra()
                seg["q"] = dato
            elif tipo == "S":
                seg["s"].append(dato)
            elif tipo == "O":
                seg["o"] = True
            else:
                seg["a"] = True
    cierra()
    for sg in segs:
        if sg["q"] is None:
            return [], [_pregunta(frase, "Nombras un lado de los márgenes sin su medida.", [f"{x}" for x in sg["s"]])], []
        if not sg["s"] and not sg["o"]:
            sg["a"] = True
    pend_otros = [sg for sg in segs if sg["o"] and not sg["s"]]
    for sg in segs:
        if sg["a"] and not sg["s"]:
            for l in LADOS_MARGEN:
                asign.setdefault(l, sg["q"])
        for l in sg["s"]:
            if l in asign and asign[l] != sg["q"]:
                return [], [_pregunta(frase, f"El margen {l} sale con dos medidas distintas en la frase.", [f"{asign[l][0]:g} {asign[l][1]}", f"{sg['q'][0]:g} {sg['q'][1]}"])], []
            asign[l] = sg["q"]
    for sg in pend_otros:
        for l in LADOS_MARGEN:
            asign.setdefault(l, sg["q"])
    if not asign:
        return [], [_pregunta(frase, "No pude asociar las medidas a los lados de los márgenes.", [])], []
    al, pq = _alcances(s), None
    alc = [a for a in al if a == "documento" or a.startswith("seccion")] or ["documento"]
    if any(a not in ("documento",) and not a.startswith("seccion") for a in al):
        return [], [_pregunta(frase, "Los márgenes son de la página (documento o «sección N»), no de «" + next(a for a in al if a != "documento" and not a.startswith("seccion")) + "». ¿Qué quisiste decir?",
                              ["márgenes de todo el documento", "sangría izquierda de esa parte"])], []
    for l, (v, u) in asign.items():
        for a in alc:
            reglas.append(_regla("margen_" + l, v, u, a, origen, nota="; ".join(comp) or None))
    return reglas, pregs, []


def _cl_sangria(frase, s, orig, origen):
    qs = _qtys(s, orig)
    sin = bool(re.search(r"\bsin\s+sangri|no\s+indent|sin\s+sangrar|without\s+(?:an\s+)?indent|no\s+indentation|ninguna\s+sangria|sangria\s+(?:ninguna|cero|0)|\bzero\s+indent", s))
    primera = bool(re.search(r"primera\s+linea|first[- ]?line|1\.?\s*a\s+linea", s))
    franc = bool(re.search(r"francesa|hanging|colgante|negativa", s))
    izq = bool(re.search(r"sangria\s+izquierda|left\s+indent|indent\w*\s+(?:from\s+the\s+)?left|sangria\s+a\s+la\s+izquierda", s))
    der = bool(re.search(r"sangria\s+derecha|right\s+indent|sangria\s+a\s+la\s+derecha", s))
    ac, pq = _alcance_o_pregunta(frase, s)
    if pq:
        return [], [pq], []
    tipos = [t for t, f in (("sangria_primera_linea", primera), ("sangria_francesa", franc), ("sangria_izquierda", izq), ("sangria_derecha", der)) if f]
    if sin:
        if not tipos:
            tipos = ["sangria_primera_linea", "sangria_izquierda"]
        return [_regla(t, 0.0, "cm", a, origen) for t in tipos for a in ac], [], []
    if not qs:
        return [], [_pregunta(frase, "¿De cuánto es la sangría? No dices la medida.", ["1.27 cm (0.5 in)", "0 (sin sangría)", "otra medida con su unidad"])], []
    if len(qs) > 1 and len({round(U.a_pt(v, u or "cm")) for _, v, u, _ in qs}) > 1 and len(tipos) < 2:
        return [], [_pregunta(frase, "Das más de una medida de sangría. ¿Cuál vale y de qué tipo?", [f"{v:g} {u or '?'}" for _, v, u, _ in qs])], []
    unidades = {u for _, _, u, _ in qs if u}
    if not unidades:
        if all(v == 0 for _, v, _, _ in qs):
            unidades = {"cm"}
        else:
            return [], [_pregunta(frase, "¿En qué unidad está la sangría?", ["centímetros (cm)", "pulgadas (in)", "puntos (pt)"])], []
    if len(unidades) > 1:
        return [], [_pregunta(frase, "Mezclas unidades en la sangría; di cada medida con su unidad.", [f"{v:g} {u or '?'}" for _, v, u, _ in qs])], []
    if not tipos:
        return [], [_pregunta(frase, "¿Qué sangría es: de primera línea, francesa (las demás líneas) o de todo el párrafo?",
                              ["primera línea", "francesa (colgante, típica de referencias)", "izquierda (todo el párrafo)", "derecha"])], []
    if len(tipos) > 1:
        if len(qs) < len(tipos):
            return [], [_pregunta(frase, "Nombras varios tipos de sangría con una sola medida. ¿Cuál es de cada uno?", tipos)], []
    unidad = next(iter(unidades))
    v = qs[0][1]
    out = []
    for t in tipos:
        for a in ac:
            out.append(_regla(t, v, unidad, a, origen))
    return out, [], []


def _cl_interlineado(frase, s, orig, origen):
    ac, _ = _alcance_o_pregunta(frase, s, requiere=False)
    # exacto N pt
    exact = re.search(r"exact\w*|exactly", s)
    minimo = re.search(r"al\s+menos|minimo|at\s+least", s)
    vals = []
    if re.search(r"\bdoble\b|double", s):
        vals.append(("doble", 2.0))
    if re.search(r"sencillo|\bsimple\b|single", s):
        vals.append(("sencillo", 1.0))
    if re.search(r"uno\s+y\s+medio|espacio\s+y\s+medio|one\s+and\s+a\s+half", s):
        vals.append(("1.5", 1.5))
    nums = [(m.group(1), float(m.group(1).replace(",", "."))) for m in re.finditer(r"(?<![\w.])(\d+(?:[.,]\d+)?)\s*(?:" + UNI + r"|lineas?|lines?)?(?![\w])", s)]
    qs = _qtys(s, orig)
    en_pt = [(v, u) for _, v, u, _ in qs if u in ("pt", "cm", "in", "mm")]
    if minimo:
        return [], [_pregunta(frase, "«Al menos N pt» deja la línea crecer: no se puede afirmar. ¿Qué quieres exigir?", ["interlineado exacto de N pt", "múltiplo (1, 1.5, doble)"])], []
    if en_pt:
        if len(en_pt) > 1:
            return [], [_pregunta(frase, "Das dos alturas de línea; ¿cuál es?", [f"{v:g} {u}" for v, u in en_pt])], []
        v, u = en_pt[0]
        if not exact:
            return [], [_pregunta(frase, f"«{v:g} {u}» de interlineado: ¿exacto (la línea mide siempre eso) o «al menos»?", ["exacto", "al menos (no medible)"])], []
        return [_regla("interlineado", round(U.de_pt(U.a_pt(v, u), "pt"), 2), "pt", a, origen, modo="exacto") for a in ac], [], []
    ms = []
    for etiqueta, v in vals:
        ms.append(v)
    solo_nums = [v for _, v in nums if v not in (0.0,)]
    cand = list(ms)
    for t, v in nums:
        if v <= 3.0 and v not in cand and not (v == 1.5 and 1.5 in cand):
            if (re.search(r"(?<![\w.])" + re.escape(t) + r"\s*(?:lineas?|lines?)", s) or re.search(r"interlinead\w*\W+(?:de\s+|a\s+|:|=)?\s*" + re.escape(t), s)
                    or re.search(r"(?:line\s+spacing|spacing)\W+(?:of\s+|to\s+|is\s+)?" + re.escape(t), s) or re.search(r"(?<![\w.])" + re.escape(t) + r"\s+(?:spac|de\s+interlin)", s)
                    or not cand and re.fullmatch(r".*\binterlinead\w*\W+" + re.escape(t) + r"\W*$", s)):
                cand.append(v)
    cand = sorted(set(cand))
    if not cand:
        grandes = [v for t, v in nums if v > 3]
        if grandes:
            return [], [_pregunta(frase, f"«{grandes[0]:g}» no parece un múltiplo de interlineado. ¿Son puntos exactos?", ["sí, N pt exactos", "no: dime el múltiplo (1, 1.5, 2)"])], []
        return [], [_pregunta(frase, "¿Qué interlineado quieres?", ["sencillo (1)", "1.5 líneas", "doble (2)", "exacto N pt"])], []
    if len(cand) > 1:
        return [], [_pregunta(frase, "Dices más de un interlineado («X o Y»). ¿Cuál vale?", [f"{v:g}" for v in cand])], []
    return [_regla("interlineado", cand[0], "lineas", a, origen, modo="multiplo") for a in ac], [], []


def _cl_espacios(frase, s, orig, origen):
    ac, pq = _alcance_o_pregunta(frase, s)
    if pq:
        return [], [pq], []
    antes = bool(re.search(r"antes|previo|anterior|before", s))
    desp = bool(re.search(r"despues|posterior|after", s))
    entre = bool(re.search(r"entre\s+parrafos|between\s+paragraphs", s))
    sin = bool(re.search(r"\bsin\s+espaci|no\s+(?:extra\s+)?space|no\s+spacing|sin\s+separacion", s))
    qs = _qtys(s, orig)
    if sin:
        qs = [(0, 0.0, "pt", 0)]
    if not qs:
        return [], [_pregunta(frase, "¿Cuánto espacio? No dices la medida.", ["0 pt", "6 pt", "12 pt", "otra con su unidad"])], []
    if len(qs) > 1 and len({round(U.a_pt(v, u or "pt")) for _, v, u, _ in qs}) > 1:
        return [], [_pregunta(frase, "Das más de una medida de espacio; ¿cuál va antes y cuál después?", [f"{v:g} {u or '?'}" for _, v, u, _ in qs])], []
    v, u = qs[0][1], qs[0][2]
    if u is None and v != 0:
        return [], [_pregunta(frase, f"¿«{v:g}» de qué unidad es el espacio entre párrafos?", ["puntos (pt)", "centímetros (cm)", "líneas (no medible sin la fuente)"])], []
    u = u or "pt"
    if u not in ("pt", "cm", "in", "mm"):
        return [], [_pregunta(frase, f"Unidad «{u}» no medible para el espacio entre párrafos", ["pt", "cm"])], []
    if entre and not (antes or desp) and not sin:
        return [], [_pregunta(frase, "«Entre párrafos» puede ser el espacio antes, el después o ambos. ¿Cuál?", ["antes", "después", "ambos"])], []
    tipos = []
    if sin or antes:
        tipos.append("espacio_antes")
    if sin or desp:
        tipos.append("espacio_despues")
    if not tipos:
        return [], [_pregunta(frase, "¿Espacio antes o después del párrafo?", ["antes", "después", "ambos"])], []
    return [_regla(t, v, u, a, origen) for t in tipos for a in ac], [], []


def _nombre_fuente(orig, s):
    """Nombre de fuente de la cláusula: conocida o la palabra tras «fuente/letra/font»."""
    for f in FUENTES_CONOCIDAS:
        m = re.search(r"(?<![a-z])" + re.escape(f) + r"(?![a-z])", s)
        if m:
            return orig[m.start():m.end()].strip().title() if orig[m.start():m.end()].islower() else orig[m.start():m.end()].strip()
    m = re.search(r"(?:\bfuente|tipografia|tipo\s+de\s+letra|\bletra|\bfont|typeface)\s*(?:de\s+|del\s+|tipo\s+|es\s+|sea\s+|:|=|\s)\s*(?:la\s+)?([A-Za-z][A-Za-z0-9\- ]{1,40}?)(?=\s*(?:\d|,|;|\.|$|\s+(?:a|de|en|con|y|e|and|size|tamano|of|pt)\b))", orig, re.I)
    if m:
        cand = m.group(1).strip()
        if cand.lower() and sin_acentos(cand).lower() not in PARRILLA_PALABRAS and sin_acentos(cand).lower().split()[0] not in PARRILLA_PALABRAS:
            return cand
    return None


def _cl_fuente(frase, s, orig, origen):
    ac, _ = _alcance_o_pregunta(frase, s, requiere=False)
    nombre = _nombre_fuente(orig, s)
    qs = _qtys(s, orig)
    reglas = []
    tamanos = []
    for pos, v, u, fin in qs:
        if u in ("pt",):
            tamanos.append(v)
        elif u is None and 5 <= v <= 72 and (re.search(r"tamano|size|letra", s) or (nombre and s[max(0, pos - 4):pos].strip() == "" or nombre)):
            tamanos.append(v)
        elif u in ("cm", "mm", "in"):
            return [], [_pregunta(frase, f"El tamaño de la letra va en puntos, no en {u}. ¿Qué tamaño?", ["10 pt", "11 pt", "12 pt"])], []
    tamanos = sorted(set(tamanos))
    if len(tamanos) > 1:
        return [], [_pregunta(frase, "Das más de un tamaño de letra. ¿Cuál vale?", [f"{t:g} pt" for t in tamanos])], []
    if len(re.findall(r"\b(?:o|or)\b", s)) and nombre and any(f in s.split(nombre.lower(), 1)[-1] for f in FUENTES_CONOCIDAS if f != nombre.lower()):
        return [], [_pregunta(frase, "Das más de una fuente («X o Y»). ¿Cuál vale?", [])], []
    otras = [f for f in FUENTES_CONOCIDAS if re.search(r"(?<![a-z])" + re.escape(f) + r"(?![a-z])", s) and f != (nombre or "").lower()]
    if otras:
        return [], [_pregunta(frase, "Nombras más de una fuente. ¿Cuál vale?", [nombre] + [o.title() for o in otras] if nombre else [o.title() for o in otras])], []
    if nombre:
        reglas.append(_regla("fuente", nombre, "", ac[0], origen))
    if tamanos:
        reglas.append(_regla("tamano", tamanos[0], "pt", ac[0], origen))
    if not reglas:
        return [], [_pregunta(frase, "¿Qué fuente (nombre) o qué tamaño (en puntos)?", ["Times New Roman 12", "Arial 11", "Calibri 11"])], []
    out = []
    for r in reglas:
        for a in ac:
            out.append({**r, "alcance": a})
    return out, [], []


def _cl_numero_pagina(frase, s, orig, origen):
    z = _pos_numero(s)
    if z == "ninguno":
        return [_regla("numero_pagina", "ninguno", "", "documento", origen)], [], []
    if z is None:
        sup = bool(re.search(r"superior|arriba|encabezado|header|\btop\b", s))
        inf = bool(re.search(r"inferior|abajo|\bpie\b|footer|bottom", s))
        if sup and inf:
            return [], [_pregunta(frase, "Nombras la parte superior y la inferior para el número de página. ¿Cuál es?", ["arriba (encabezado)", "abajo (pie)"])], []
        if not (sup or inf):
            return [], [_pregunta(frase, "¿Dónde va el número de página?", ["arriba a la derecha (encabezado)", "abajo al centro (pie)", "abajo a la derecha (pie)", "sin número"])], []
        return [], [_pregunta(frase, "Falta decir el lado del número de página.", ["izquierda", "centro", "derecha"])], []
    return [_regla("numero_pagina", f"{z[0]} {z[1]}", "", "documento", origen)], [], []


def _cl_alineacion(frase, s, orig, origen):
    ac, pq = _alcance_o_pregunta(frase, s)
    if pq:
        return [], [pq], []
    cand = []
    if re.search(r"justific|justified|justify", s):
        cand.append("justificada")
    if re.search(r"izquierda|\bleft\b", s):
        cand.append("izquierda")
    if re.search(r"centrad|centered|\bcenter\b", s):
        cand.append("centro")
    if re.search(r"a\s+la\s+derecha|derecha\b|\bright\b", s):
        cand.append("derecha")
    cand = list(dict.fromkeys(cand))
    if not cand:
        return [], [_pregunta(frase, "¿Qué alineación?", ["justificada", "izquierda", "centrada", "derecha"])], []
    if len(cand) > 1:
        return [], [_pregunta(frase, "Dices más de una alineación; ¿cuál vale?", cand)], []
    return [_regla("alineacion", cand[0], "", a, origen) for a in ac], [], []


CLAUSULAS = {"margenes": _cl_margenes, "sangria": _cl_sangria, "interlineado": _cl_interlineado, "espacios": _cl_espacios,
             "numero_pagina": _cl_numero_pagina, "fuente": _cl_fuente, "alineacion": _cl_alineacion}


def _trozos(texto):
    """Parte la frase en cláusulas por «;», salto de línea y punto seguido (no decimal)."""
    t = re.sub(r"(?<=\d)\.(?=\d)", "\u0001", texto)
    t = re.sub(r"(?<=\d),(?=\d)", "\u0002", t)
    partes = re.split(r";|\n|\.\s+|\.$|\s+\+\s+", t)
    return [p.replace("\u0001", ".").replace("\u0002", ",").strip() for p in partes if p.strip()]


def _cortes(s):
    """Posiciones donde empieza cada categoría en la cláusula; devuelve [(pos, categoría)] sin solapar y ordenado."""
    hall = []
    for nombre, rx in CAT:
        for m in rx.finditer(s):
            hall.append((m.start(), nombre))
    hall.sort()
    out = []
    for pos, n in hall:
        if out and out[-1][1] == n:
            continue
        out.append((pos, n))
    # alineación «centrado» etc. dentro de una cláusula de número de página no es otra categoría
    nombres = [n for _, n in out]
    if "numero_pagina" in nombres:
        out = [(p, n) for p, n in out if n not in ("alineacion", "fuente") or n == "numero_pagina"]
    if "margenes" in nombres:
        out = [(p, n) for p, n in out if n != "alineacion"]
    # tamaño/fuente tras «sangría», «interlineado»… cuenta como la misma categoría si ya viene una
    return out


def parsear(frase, origen=None):
    """Frase en lenguaje natural -> {reglas, preguntas, no_medibles}. Lo que no entiende, nunca lo adivina."""
    origen = origen if origen else f"usuario {_hoy()}: «{' '.join(frase.split())}»"
    res = {"frase": frase, "reglas": [], "preguntas": [], "no_medibles": []}
    if not frase or not frase.strip():
        res["preguntas"].append(_pregunta(frase, "La frase está vacía.", []))
        return res
    for clausula in _trozos(frase):
        s = sin_acentos(clausula).lower()
        orig = sin_acentos(clausula)  # misma longitud que `s` para cortar el original
        s = s.replace(" ", " ")
        subj = SUBJETIVO.search(s)
        cortes = _cortes(s)
        if subj:
            res["no_medibles"].append({"frase": clausula, "motivo": f"«{subj.group(0).strip()}» es un juicio de gusto, sin valor que medir: dime la medida concreta (márgenes, interlineado, fuente…) y la mido"})
        if not cortes:
            if not subj:
                res["preguntas"].append(_pregunta(clausula, "No entendí qué medida pides. Puedo medir: márgenes, sangría (primera línea, francesa), interlineado, "
                                                  "fuente y tamaño, espacio antes/después, número de página (posición) y alineación.",
                                                  ["márgenes 2.54 cm", "sangría de primera línea 1.27 cm en el cuerpo", "interlineado 1.5", "fuente Times New Roman 12", "número de página arriba a la derecha"]))
            continue
        for k, (pos, cat) in enumerate(cortes):
            fin = cortes[k + 1][0] if k + 1 < len(cortes) else len(s)
            ini = 0 if k == 0 else pos
            sl_s, sl_o = s[ini:fin], orig[ini:fin]
            if cat == "fuente" and k > 0 and cortes[k - 1][1] == "fuente":
                continue
            rs, ps, nm = CLAUSULAS[cat](clausula if len(cortes) == 1 else clausula[ini:fin].strip(), sl_s, sl_o, origen)
            res["reglas"] += rs
            res["preguntas"] += ps
            res["no_medibles"] += nm
    return res


# ================================================================ evaluar sobre la ficha
def _tol_pt(r):
    q = r["que"]
    clave = "margen" if q.startswith("margen") else "sangria" if q.startswith("sangria") else "espacio" if q.startswith("espacio") else "tamano"
    return U.tolerancia(clave, r["unidad"] or ("cm" if clave in ("margen", "sangria") else "pt"), r.get("tolerancia"))


def texto_regla(r):
    nm = NOMBRE_QUE.get(r["que"], r["que"])
    if r["que"] == "interlineado":
        v = f"exacto {r['valor']:g} pt" if r.get("modo") == "exacto" else f"×{r['valor']:g}"
    elif r["que"] in ("fuente", "alineacion", "numero_pagina"):
        v = str(r["valor"])
    elif r["que"] == "tamano":
        v = f"{r['valor']:g} pt"
    else:
        v = U.texto_medida(U.a_pt(r["valor"], r["unidad"]))
    tol = r.get("tolerancia")
    return f"{nm} {v} en {r['alcance']}" + (f" (±{tol:g} {r['unidad']})" if tol is not None else "")


def _legible(pt):
    return U.texto_medida(pt)


EXENTO_ROTULO = re.compile(r"^\s*(?:tabla|table|figura|figure|fig\.?|nota|note)\b", re.I)


def _exento(p, todos_aud, que):
    """Motivo por el que el párrafo no cuenta para esta regla de cuerpo (tecnicismos que no son incumplimiento) o None."""
    import auditar as A
    a = p["aud"]
    if a.get("imagen"):
        return "imagen"
    if EXENTO_ROTULO.match(p["texto"]) or A.RE_NOTA.match(a["texto"]):
        return "rótulo o nota de tabla/figura"
    if que in ("sangria_primera_linea", "sangria_izquierda", "sangria_francesa", "alineacion"):
        if p["v"]["alineacion"] == "centro" and que != "alineacion":
            return "centrado"
        if re.match(r"\s*(keywords?|palabras clave)\s*:", a["texto"], re.I):
            return "palabras clave"
        if a.get("numerado"):
            return "lista numerada"
        if que in ("sangria_primera_linea", "sangria_izquierda") and A.sin_sangria_legitima(todos_aud, a):
            return "cita en bloque, resumen, nota o rótulo (APA 2.9, 8.27)"
        if que == "alineacion" and (p["v"]["primera"] < -0.5 or A.sin_sangria_legitima(todos_aud, a) and p["v"]["izq"] > 0.4 * 72 * 0.9):
            return "lista con sangría francesa o cita en bloque"
        if que in ("sangria_primera_linea",) and p["v"]["primera"] < 0:
            return "entrada con sangría francesa"
    return None


def _seleccion(ficha, alcance, que):
    """[párrafo] del alcance (sin vacíos ni tablas salvo `todo`)."""
    ps = [p for p in ficha["_parrafos"] if not p["vacio"]]
    if alcance == "todo":
        return ps
    if alcance == "documento":
        roles = ("cuerpo", "resumen", "referencias") if que in ("fuente", "tamano") else ("cuerpo", "resumen", "referencias")
        return [p for p in ps if p["rol"] in roles or p["rol"].startswith("titulo")]
    if alcance == "titulos":
        return [p for p in ps if p["rol"].startswith("titulo")]
    if alcance.startswith("titulo "):
        return [p for p in ps if p["rol"] == alcance]
    if alcance.startswith("seccion "):
        k = int(alcance.split()[1]) - 1
        return [p for p in ps if p["sec"] == k and not p["en_tabla"]]
    return [p for p in ps if p["rol"] == alcance]


def _res(r, estado, esperado, real, detalle=(), ejemplos=(), n=0, n_mal=0, avisos=(), exentos=None):
    return {"regla": r, "texto": texto_regla(r), "estado": estado, "esperado": esperado, "real": real, "detalle": list(detalle),
            "ejemplos": list(ejemplos), "n": n, "n_mal": n_mal, "avisos": list(avisos), "exentos": exentos or {}, "origen": r.get("origen", "")}


def _eval_margen(r, ficha, pdfm):
    lado = r["que"].split("_", 1)[1]
    clave = {"superior": "superior", "inferior": "inferior", "izquierdo": "izquierdo", "derecho": "derecho"}[lado]
    pedido = U.a_pt(r["valor"], r["unidad"])
    tol = _tol_pt(r)
    secs = ficha["secciones"]
    if r["alcance"].startswith("seccion"):
        k = int(r["alcance"].split()[1])
        secs = [s for s in secs if s["n"] == k]
        if not secs:
            return _res(r, "no medible", _legible(pedido), "—", [f"el documento no tiene sección {k}"])
    mal, vals, av = [], [], []
    for s in secs:
        real = s["margenes"][clave]["pt"]
        vals.append(real)
        if not s["margenes_declarados"]:
            av.append(f"sección {s['n']}: el sectPr no declara todos los pgMar; se cuenta 1 in (valor por defecto de Word)")
        if s["espejo"] and clave in ("izquierdo", "derecho"):
            av.append(f"sección {s['n']}: márgenes espejo; izquierdo/derecho son interior/exterior")
        if (s["margenes"]["canal"] or {}).get("pt", 0) and clave in ("izquierdo", "superior"):
            av.append(f"sección {s['n']}: tiene canal (encuadernación) de {s['margenes']['canal']['cm']:g} cm que no se suma aquí")
        if not U.igual(real, pedido, tol):
            mal.append((s["n"], real))
    real_txt = ", ".join(sorted({_legible(v) for v in vals}))
    if mal:
        return _res(r, "no cumple", _legible(pedido), real_txt, [f"sección {n}: {_legible(v)}" for n, v in mal], n=len(secs), n_mal=len(mal), avisos=av)
    return _res(r, "cumple", _legible(pedido), real_txt, n=len(secs), avisos=av)


def _valor_real(que, p):
    v = p["v"]
    return {"sangria_primera_linea": v["primera"], "sangria_izquierda": v["izq"], "sangria_derecha": v["der"], "espacio_antes": v["antes"],
            "espacio_despues": v["despues"], "tamano": v["tamano"]}.get(que)


def _eval_parrafos(r, ficha, pdfm):
    que = r["que"]
    sel = _seleccion(ficha, r["alcance"], que)
    if not sel:
        return _res(r, "no medible", texto_regla(r), "—", [f"no hay párrafos en el alcance «{r['alcance']}» (¿existe esa parte en el documento?)"])
    todos_aud = [p["aud"] for p in ficha["_parrafos"]]
    exentos, evaluados = {}, []
    for p in sel:
        if r["alcance"] != "todo" and que not in ("fuente", "tamano"):
            m = _exento(p, todos_aud, que)
            if m:
                exentos[m] = exentos.get(m, 0) + 1
                continue
        elif que in ("fuente", "tamano") and r["alcance"] != "todo" and (p["aud"].get("imagen") or EXENTO_ROTULO.match(p["texto"])):
            exentos["rótulo o imagen"] = exentos.get("rótulo o imagen", 0) + 1
            continue
        evaluados.append(p)
    if not evaluados:
        return _res(r, "no medible", texto_regla(r), "—", ["todos los párrafos del alcance son excepciones legítimas: " + ", ".join(f"{k} ({v})" for k, v in exentos.items())], exentos=exentos)
    mal, av, equiv, indet = [], [], 0, 0
    vistos = {}
    if que == "interlineado":
        pedido = {"modo": "exacto", "pt": r["valor"]} if r.get("modo") == "exacto" else {"modo": "multiplo", "valor": r["valor"]}
        tm = r.get("tolerancia") if r.get("modo") != "exacto" else None
        tp = r.get("tolerancia") if r.get("modo") == "exacto" else None
        for p in evaluados:
            est, nota = U.interlineado_cumple(p["v"]["interlineado"], pedido, p["v"]["tamano"], tm, tp)
            vistos[U.texto_interlineado(p["v"]["interlineado"])] = vistos.get(U.texto_interlineado(p["v"]["interlineado"]), 0) + 1
            if est == "distinto":
                mal.append((p, U.texto_interlineado(p["v"]["interlineado"]) + (f" ({nota})" if nota else "")))
            elif est == "equivalente":
                equiv += 1
                if nota and nota not in av:
                    av.append("equivalente: " + nota)
            elif est == "indeterminado":
                indet += 1
        if indet == len(evaluados):
            return _res(r, "no medible", texto_regla(r), "interlineado «al menos»", ["no se puede afirmar un valor exacto con «al menos N pt»"], n=len(evaluados))
        if indet:
            av.append(f"{indet} párrafos con interlineado «al menos» o sin w:line que no se pueden afirmar")
        esperado = f"×{r['valor']:g}" if r.get("modo") != "exacto" else f"exacto {r['valor']:g} pt"
        real = "; ".join(f"{k} ({n})" for k, n in sorted(vistos.items(), key=lambda x: -x[1])[:3])
    elif que == "fuente":
        import modelo_formato as MF
        buscado = MF.norm_fuente(r["valor"])
        for p in evaluados:
            vistos[p["v"]["fuente"]] = vistos.get(p["v"]["fuente"], 0) + 1
            if MF.norm_fuente(p["v"]["fuente"]) != buscado:
                mal.append((p, p["v"]["fuente"]))
            elif p["v"]["mixto"]:
                av.append("hay párrafos con varias fuentes/tamaños; se juzga la dominante de cada uno") if "varias" not in " ".join(av) else None
        esperado, real = r["valor"], "; ".join(f"{k} ({n})" for k, n in sorted(vistos.items(), key=lambda x: -x[1])[:3])
    elif que == "alineacion":
        for p in evaluados:
            vistos[p["v"]["alineacion"]] = vistos.get(p["v"]["alineacion"], 0) + 1
            if p["v"]["alineacion"] != r["valor"]:
                mal.append((p, p["v"]["alineacion"]))
        esperado, real = r["valor"], "; ".join(f"{k} ({n})" for k, n in sorted(vistos.items(), key=lambda x: -x[1])[:3])
    elif que == "sangria_francesa":
        pedido, tol = U.a_pt(r["valor"], r["unidad"]), _tol_pt(r)
        for p in evaluados:
            real_pt = -p["v"]["primera"]
            vistos[_legible(real_pt)] = vistos.get(_legible(real_pt), 0) + 1
            if not U.igual(real_pt, pedido, tol):
                mal.append((p, _legible(real_pt)))
            elif pedido and not U.igual(p["v"]["izq"], pedido, tol):
                av.append(f"párr. {p['i'] + 1}: la francesa es de {_legible(real_pt)} pero la sangría izquierda es {_legible(p['v']['izq'])}")
        esperado, real = f"francesa {_legible(pedido)}", "; ".join(f"{k} ({n})" for k, n in sorted(vistos.items(), key=lambda x: -x[1])[:3])
    else:
        pedido, tol = (r["valor"] if que == "tamano" else U.a_pt(r["valor"], r["unidad"])), _tol_pt(r)
        for p in evaluados:
            v = _valor_real(que, p)
            k = f"{v:g} pt" if que == "tamano" else _legible(v)
            vistos[k] = vistos.get(k, 0) + 1
            if not U.igual(v, pedido, tol):
                mal.append((p, k))
        esperado = f"{pedido:g} pt" if que == "tamano" else _legible(pedido)
        real = "; ".join(f"{k} ({n})" for k, n in sorted(vistos.items(), key=lambda x: -x[1])[:3])
    ej = [{"i": p["i"] + 1, "inicio": p["texto"][:40], "valor": v} for p, v in mal[:5]]
    if equiv:
        av.append(f"{equiv} párrafos cumplen por equivalencia (no por el mismo valor literal)")
    if mal:
        return _res(r, "no cumple", esperado, real, [f"párr. {e['i']} «{e['inicio']}»: {e['valor']}" for e in ej], ej, len(evaluados), len(mal), av, exentos)
    return _res(r, "cumple", esperado, real, [], [], len(evaluados), 0, av, exentos)


def _eval_numero_pagina(r, ficha, pdfm):
    secs = ficha["secciones"]
    pdf_pred = ((pdfm or {}).get("numero_pagina") or {}).get("predominante") if pdfm else None
    if r["valor"] == "ninguno":
        con = [s for s in secs if s["numero_pagina"]["partes"]]
        if con:
            return _res(r, "no cumple", "sin número de página", "; ".join(f"sección {s['n']}: {s['numero_pagina']['donde']}" for s in con), [f"sección {s['n']}" for s in con], n=len(secs), n_mal=len(con))
        return _res(r, "cumple", "sin número de página", "sin número", n=len(secs))
    zona_p, lado_p = r["valor"].split()
    zona = {"encabezado": "superior", "pie": "inferior"}
    mal, ok, av, indeter = [], 0, [], []
    for s in secs:
        partes = [x for x in s["numero_pagina"]["partes"] if x["parte"] == "predeterminada"] or s["numero_pagina"]["partes"]
        if not partes:
            solo_portada = s["parrafos"] and all(p["rol"] == "portada" for p in ficha["_parrafos"] if p["sec"] == s["n"] - 1 and not p["vacio"] and not p["en_tabla"])
            if solo_portada or not s["parrafos"]:
                continue  # portada sin número: legítimo
            mal.append((s["n"], "sin número de página"))
            continue
        for x in partes:
            if x["lado"] is None and zona[x["lugar"]] == zona_p:
                indeter.append(s["n"])
                continue
            if zona[x["lugar"]] != zona_p or x["lado"] != lado_p:
                mal.append((s["n"], f"{zona[x['lugar']]} {x['lado'] or 'lado indeterminado'}"))
            else:
                ok += 1
    if indeter and not mal:
        if pdf_pred:
            real = f"{pdf_pred['zona']} {pdf_pred['lado']} (medido en el PDF: el .docx usa tabuladores)"
            if (pdf_pred["zona"], pdf_pred["lado"]) == (zona_p, lado_p):
                return _res(r, "cumple", r["valor"], real, n=len(secs), avisos=[f"sección(es) {sorted(set(indeter))}: el .docx no dice el lado (tabuladores); se juzgó con el PDF"])
            return _res(r, "no cumple", r["valor"], real, [real], n=len(secs), n_mal=1, avisos=[f"se juzgó con el PDF porque el .docx usa tabuladores en la sección {sorted(set(indeter))}"])
        return _res(r, "no medible", r["valor"], "lado indeterminado", [f"sección(es) {sorted(set(indeter))}: el número va con tabuladores y el .docx no dice el lado; pasa el PDF (--pdf o --render)"], n=len(secs))
    if mal:
        return _res(r, "no cumple", r["valor"], "; ".join(sorted({f"sección {n}: {w}" for n, w in mal})), [f"sección {n}: {w}" for n, w in mal], n=len(secs), n_mal=len(mal))
    if pdf_pred and (pdf_pred["zona"], pdf_pred["lado"]) != (zona_p, lado_p):
        av.append(f"el PDF muestra el número {pdf_pred['zona']} {pdf_pred['lado']} en {pdf_pred['paginas']} páginas y el .docx lo declara {r['valor']}: aviso por discrepancia docx/PDF")
    return _res(r, "cumple", r["valor"], r["valor"], n=len(secs), avisos=av)


def evaluar_regla(r, ficha, pdfm=None):
    """Una regla normalizada sobre la ficha de `medir.ficha_docx` -> resultado {estado: cumple|no cumple|no medible, …}."""
    if r["que"].startswith("margen"):
        return _eval_margen(r, ficha, pdfm)
    if r["que"] == "numero_pagina":
        return _eval_numero_pagina(r, ficha, pdfm)
    return _eval_parrafos(r, ficha, pdfm)


def derivadas_del_perfil(cfg):
    """Reglas medibles de `formato:`, `reglas_guia:` y `fuente` de un perfil (para `medir --contra`). Solo lo que `medir` puede comprobar."""
    out = []
    fm = cfg.get("formato") if isinstance(cfg.get("formato"), dict) else {}
    rg = cfg.get("reglas_guia") if isinstance(cfg.get("reglas_guia"), dict) else {}
    o = "perfil: " + str(cfg.get("institucion") or "formato")
    if rg.get("margenes_cm") is not None:
        out += expandir(_regla("margenes", float(rg["margenes_cm"]), "cm", "documento", o + " (reglas_guia.margenes_cm)"))
    if rg.get("sangria_primera_linea_cm") is not None:
        out.append(_regla("sangria_primera_linea", float(rg["sangria_primera_linea_cm"]), "cm", "cuerpo", o + " (reglas_guia.sangria_primera_linea_cm)"))
    if fm.get("interlineado") is not None:
        out.append(_regla("interlineado", float(fm["interlineado"]), "lineas", "cuerpo", o + " (formato.interlineado)", modo="multiplo"))
    if isinstance(fm.get("fuente"), dict):
        if fm["fuente"].get("nombre"):
            out.append(_regla("fuente", str(fm["fuente"]["nombre"]), "", "documento", o + " (formato.fuente)"))
        if fm["fuente"].get("pt"):
            out.append(_regla("tamano", float(fm["fuente"]["pt"]), "pt", "documento", o + " (formato.fuente)"))
    if fm.get("alineacion"):
        out.append(_regla("alineacion", str(fm["alineacion"]), "", "cuerpo", o + " (formato.alineacion)"))
    pos = (fm.get("paginacion") or {}).get("posicion") if isinstance(fm.get("paginacion"), dict) else None
    if pos in ("encabezado_derecha", "pie_derecha", "pie_centro"):
        z, l = pos.split("_")
        out.append(_regla("numero_pagina", f"{'superior' if z == 'encabezado' else 'inferior'} {l}", "", "documento", o + " (formato.paginacion.posicion)"))
    return out


def evaluar_todo(ficha, pdfm, frases, origen, ruta_doc, equipo, usar_yaml, contra):
    """Evalúa frases (--regla), el bloque `medidas:` del .editorial.yaml y, con `contra`, las derivadas del perfil.
    -> {resultados, preguntas, no_medibles}."""
    import cli
    reglas, preguntas, no_med = [], [], []
    for f in frases or []:
        p = parsear(f, origen)
        reglas += [y for x in p["reglas"] for y in expandir(x)]
        preguntas += p["preguntas"]
        no_med += p["no_medibles"]
    yml, nm_yaml, ruta = leer_medidas_yaml(ruta_doc, equipo)
    reglas += yml
    no_med += nm_yaml
    if contra:
        import auditar
        ruta_c = pathlib.Path(contra) if contra != "perfil" else ruta
        if not ruta_c or not pathlib.Path(ruta_c).is_file():
            cli.error("--contra: no encuentro el perfil (pasa la ruta de un .editorial.yaml o ponlo junto al documento)")
        cfg = auditar.yaml.safe_load(pathlib.Path(ruta_c).read_text(encoding="utf-8")) or {}
        reglas += derivadas_del_perfil(cfg)
    resultados = [evaluar_regla(r, ficha, pdfm) for r in reglas]
    return {"resultados": resultados, "preguntas": preguntas, "no_medibles": no_med}


def imprimir(res):
    ico = {"cumple": "CUMPLE", "no cumple": "NO CUMPLE", "no medible": "no medible"}
    for x in res["resultados"]:
        print(f"{ico[x['estado']]}: {x['texto']}")
        print(f"    se pide: {x['esperado']}   hay: {x['real']}" + (f"   ({x['n_mal']} de {x['n']} fuera)" if x["n_mal"] else ""))
        for d in x["detalle"][:5]:
            print(f"      - {d}")
        if x["exentos"]:
            print("    no cuentan (excepciones legítimas): " + ", ".join(f"{k} ({v})" for k, v in x["exentos"].items()))
        for a in x["avisos"][:4]:
            print(f"    aviso: {a}")
        if x["origen"]:
            print(f"    origen: {x['origen']}")
    for p in res["preguntas"]:
        print(f"PREGUNTA: «{p['frase']}»: {p['pregunta']}" + (" Opciones: " + " | ".join(p["opciones"]) if p["opciones"] else ""))
    for n in res["no_medibles"]:
        print(f"no medible: «{n['frase']}»: {n['motivo']}")


# ================================================================ integración con auditar (INS-016) y excepciones APA
def excepciones_derivadas(reglas):
    """Excepciones APA que lo pedido por el usuario hace innecesarias (se suman a las del perfil de equipo)."""
    out, vistos = [], set()

    def add(regla, motivo):
        if regla not in vistos:
            vistos.add(regla)
            out.append({"regla": regla, "motivo": motivo})
    for r in reglas:
        o = r.get("origen") or "medida pedida por el usuario"
        q, a = r["que"], r["alcance"]
        if q.startswith("margen") and a in ("documento", "todo") and not U.igual(U.a_pt(r["valor"], r["unidad"]), 72.0, U.a_pt(U.TOLERANCIAS["margen"], "cm")):
            add("APA-001", f"medida pedida por el usuario: {texto_regla(r)} ({o})")
        if q == "interlineado" and a in ("documento", "todo", "cuerpo") and not (r.get("modo") != "exacto" and abs(r["valor"] - 2.0) < 0.05):
            add("APA-004", f"medida pedida por el usuario: {texto_regla(r)} ({o})")
            if a in ("documento", "todo"):
                add("APA-033", f"medida pedida por el usuario: {texto_regla(r)} ({o})")
        if q == "sangria_primera_linea" and a in ("documento", "todo", "cuerpo") and not U.igual(U.a_pt(r["valor"], r["unidad"]), 36.0, 3.6):
            add("APA-007", f"medida pedida por el usuario: {texto_regla(r)} ({o})")
        if q == "alineacion" and r["valor"] == "justificada" and a in ("documento", "todo", "cuerpo"):
            add("APA-006", f"medida pedida por el usuario: {texto_regla(r)} ({o})")
        if q in ("fuente", "tamano") and a in ("documento", "todo"):
            add("APA-002", f"medida pedida por el usuario: {texto_regla(r)} ({o})")
        if q == "numero_pagina" and r["valor"] != "superior derecha":
            add("APA-008", f"medida pedida por el usuario: {texto_regla(r)} ({o})")
    return out


def hallazgos(path, pars, reglas, no_medibles, Hallazgo):
    """INS-016: cada regla que no cumple es un hallazgo mayor con su origen. Devuelve (hallazgos, avisos)."""
    import medir
    ficha = medir.ficha_docx(str(path), pars)
    H, avisos = [], []
    for r in reglas:
        x = evaluar_regla(r, ficha)
        if x["estado"] == "no cumple":
            ej = x["ejemplos"][0] if x["ejemplos"] else None
            ubic = f"párrafo {ej['i']}: «{ej['inicio']}…»" if ej else (x["detalle"][0] if x["detalle"] else "documento")
            evid = f"{x['texto']}: hay {x['real']}" + (f"; {x['n_mal']} de {x['n']} fuera" if x["n_mal"] else "")
            H.append(Hallazgo("INS-016", "mayor", ubic, evid,
                              f"ajustar a {x['esperado']}. Origen: {r.get('origen') or 'medida declarada en `medidas:` de .editorial.yaml'}"))
        elif x["estado"] == "no medible":
            avisos.append(f"no medible: {x['texto']}: {' '.join(x['detalle']) or 'sin valor que medir'}")
        for a in x["avisos"]:
            if a.startswith("equivalente"):
                continue
    for n in no_medibles:
        avisos.append(f"no medible: «{n['frase']}»: {n['motivo']}")
    return H, avisos
