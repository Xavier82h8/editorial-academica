#!/usr/bin/env python3
"""Reglas institucionales INS-001..015: el formato propio de la escuela, declarado en el bloque opcional `formato:` de
.editorial.yaml, y los modelos o instrucciones vinculantes del usuario, declarados en `vinculante:`. Sin esos bloques no corre
nada. Solo se evalúan .docx.

Claves de `formato:` y reglas (todas opcionales; cada una activa su regla):
  INS-001 mayor  `interlineado: 1.5` los párrafos de cuerpo y las entradas de la lista llevan ese interlineado
                 (se exentan tablas, rótulos, notas, líneas centradas, texto de menos de 12 pt y el anexo)
  INS-002 mayor  `alineacion: justificada|izquierda` los párrafos de cuerpo llevan esa alineación (se exentan las
                 entradas de la lista con sangría francesa, listas numeradas, citas en bloque y los de INS-001)
  INS-003 mayor  `nivel1: {mayusculas: true, numerado: true}` encabezados de nivel 1 en MAYÚSCULAS y numerados «N.»
                 consecutivos (los preliminares, como Resumen e índices, no se numeran; «Fuentes» y «Anexos» sí)
  INS-004 mayor  `niveles_numerados: true` encabezados de nivel 2 numerados «N.k.» con el número de su capítulo
  INS-005 mayor  `capitulo_pagina_nueva: true` cada encabezado de nivel 1 empieza en página nueva
  INS-006 mayor  `paginacion: {portada: sin_numero, preliminares: romanos, cuerpo: arabigos, posicion: pie_derecha}` formato de número de
                 página por sección (w:pgNumType): portada sin número, preliminares en romanos minúsculos, cuerpo
                 en arábigos que reinician en 1; `posicion` (encabezado_derecha | pie_derecha | pie_centro) dónde va el número
                 (se comprueba en cada sección; sin ella no se exige lugar, y APA-008 pasa a excepción si no es encabezado_derecha)
  INS-007 menor  `titulo_max_palabras: 20` el título de la portada no pasa de ese número de palabras
  INS-008 menor  `fuentes_recientes: {anios: 5, porcentaje: 70}` porcentaje de referencias con año reciente
                 (`anio_actual:` fija el año; por defecto el de hoy). Se mide sobre la literatura actualizable: salen del
                 cálculo las fuentes documentales (leyes, licencias, conjuntos de datos, software, directorios; se detectan
                 solas y `documentales:` añade más) y las obras fundacionales declaradas en `fundacionales:` con su
                 `motivo` (instrumento, prueba o teoría original que el documento usa). Ambas se informan en los avisos.
                 Con `arbitradas: true` solo cuenta como reciente la fuente de nivel A o B (norma, revista arbitrada, actas, libro:
                 la guía pide «literatura arbitrada … de los últimos 5 años»; scripts/niveles.py clasifica por el texto de la
                 referencia); por defecto cuenta cualquier fuente de la ventana de años.
  INS-009 menor  `voz: impersonal` primera persona (nosotros, nuestro, «realizaremos», «yo»…) en el cuerpo
  INS-010 mayor  `titulo: "…"` (clave de primer nivel de .editorial.yaml, el título elegido con `editorial.py titulo`): el título de la
                 portada debe coincidir con él (sin distinguir mayúsculas, acentos ni signos); es vinculante
  INS-010 mayor  portada oficial: `portada: {campos: [{nombre, patron|literal}…], fecha: mes_anio, numero_control: true,
                 logos: [SEP, TNE, ITE]}` (o `logos: [{nombre, ruta, alto_cm}]`, que además construye `editorial.py portada`) presencia y orden de los campos de la portada (el título del proyecto se declara con
                 `{nombre: titulo}`), fecha «Mes y Año» (no dd/mm/aaaa ni «03/Noviembre/2026»), número de control de cada integrante
                 (8 dígitos o letra y 8 dígitos; un [[PENDIENTE]] cuenta como falta); los logotipos solo avisan (número de imágenes)
  INS-011 mayor  `fuente: {nombre: Times New Roman, pt: 12}` fuente y tamaño de los encabezados y pies de página, y texto en color
                 (distinto de negro o automático); `corregir` lo arregla
  INS-012 mayor  `resumen: {palabras: [150, 250], sangria: false, un_parrafo: true, palabras_clave: [3, 5]}` el resumen (palabras, un solo
                 párrafo sin contar la línea de palabras clave, sin sangría de primera línea, número de palabras clave);
                 `corregir` quita la sangría
  INS-013 menor  `rotulos_pt: [8, 9]` tamaño de los rótulos «TABLA N» y «Fig. N.» fuera de ese rango; `corregir` lo arregla
  INS-015 mayor  fidelidad al modelo: cada entrada tipo `modelo` de `vinculante:` se compara con su ámbito (portada, documento o
                 seccion:<nombre>): orden de líneas, texto fijo, fuente, tamaño (0.5 pt), negrita, cursiva, color, alineación y cajas
                 (relleno y borde con color y grosor); cada diferencia es evidencia (INS-014 queda reservada)

Formato vinculante (`vinculante:` en .editorial.yaml, lista de {id, origen, fecha, tipo: modelo|instruccion, texto, spec, ambito}):
lo que el usuario da como formato, modelo o instrucción es regla. `modelo` lleva la spec JSON medida (`editorial.py modelo medir`);
`instruccion` lleva su `texto` (la reproduce el agente; el script solo la registra en los avisos). Precedencia: vinculante > perfil de
equipo (`formato:`, `excepciones:`) > norma base (APA, IEEE) > estructura de género. Una entrada inválida es error de uso (código 2).
Los hallazgos salen como los demás (auditar, puntuar). Las reglas APA que contradicen lo declarado (interlineado,
justificado, mayúsculas, numeración) pasan solas a excepción institucional (`excepciones_derivadas`).
"""
import datetime
import re
import sys
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import auditar  # noqa: E402
import ooxml  # noqa: E402
from auditar import Hallazgo  # noqa: E402
from docx.oxml.ns import qn  # noqa: E402

CLAVES = {"interlineado", "alineacion", "nivel1", "niveles_numerados", "capitulo_pagina_nueva", "paginacion",
          "titulo_max_palabras", "fuentes_recientes", "voz", "anio_actual", "portada", "fuente", "resumen", "rotulos_pt"}
AMBITOS_FIJOS = ("portada", "documento")
POSICIONES = ("encabezado_derecha", "pie_derecha", "pie_centro")
ALIAS_POSICION = {"encabezado": "encabezado_derecha", "pie": "pie_centro"}
RE_PRELIM = re.compile(r"^(resumen|abstract|indice|lista de|tabla de contenido|agradecimientos|dedicatoria|glosario|siglas)")
RE_NUM1 = re.compile(r"^\s*(\d{1,2})\.?\s+\S")
RE_NUM2 = re.compile(r"^\s*(\d{1,2})\.(\d{1,2})\.?\s+\S")
RE_CLAVE = re.compile(r"^\s*(palabras?\s+clave|keywords?)\s*:", re.I)
RE_ETIQUETA_PORTADA = re.compile(
    r"^\s*(tecnol[oó]gico|instituto|universidad|departamento|divisi[oó]n|secretar[ií]a|protocolo|taller|asignatura|materia|"
    r"integrantes?|autor(?:es)?|alumnos?|estudiantes?|docente|asesor|profesor|catedr[aá]tico|carrera|lugar|fecha|"
    r"presenta|presentan|nombre|n[uú]mero|TNE|sep\b|"
    # línea de lugar y fecha («Ciudad, Estado, noviembre de 2026»): cualquier ciudad, se reconoce por el mes
    r".*\b(?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|setiembre|octubre|noviembre|diciembre)\b)", re.I)
RE_LEYENDA = re.compile(r"asignatura|requisito|materia|presentad[oa]|elaborad[oa]", re.I)
RE_ANIO = re.compile(r"\(\s*((?:19|20)\d{2})[a-z]?\s*[,)]")
RE_PRENSA = re.compile(r"\(\s*(?:en prensa|in press)\s*\)", re.I)
# INS-008: fuentes documentales (no son literatura que se actualice): leyes y diarios oficiales, licencias, conjuntos de datos,
# software y directorios
RE_DOCUMENTAL = re.compile(
    r"^(?:Ley|Reglamento|C[óo]digo|Constituci[óo]n|Decreto|Acuerdo)\s+[A-ZÁÉÍÓÚ]|Diario Oficial|Bolet[íi]n Oficial|\bLicen[cs]e\b|\bLicencia\b|\bLicensing\b|\bTerms of (?:Use|Service)\b|\bT[ée]rminos de (?:uso|servicio)\b"
    r"|\[(?:Conjunto de datos|Data ?set|Software|Directorio[^\]]*|Programa inform[áa]tico)\]", re.I)


def clasificar_fuentes(entradas, fr):
    """{id(entrada): ("fundacional"|"documental", motivo)} de las referencias que INS-008 deja fuera del cálculo."""
    out = {}
    fund, docs = fr.get("fundacionales") or [], fr.get("documentales") or []
    for e in entradas:
        t = " ".join(e["texto"].split())
        hit = next((("fundacional", x["motivo"]) for x in fund if t.startswith(x["ref"])), None) or             next((("documental", x["motivo"]) for x in docs if t.startswith(x["ref"])), None)
        if hit is None and RE_DOCUMENTAL.search(t[:300]):
            hit = ("documental", "fuente documental (ley, licencia, conjunto de datos, software o directorio)")
        if hit:
            out[id(e)] = hit
    return out


def literatura_actualizable(lista, fr):
    """Denominador ÚNICO de INS-008 y de FUE-NIV (`porcentaje_arbitradas`): la literatura actualizable.
    Quedan fuera las documentales (leyes, licencias, datos, software, directorios), las fundacionales declaradas en
    `fuentes_recientes: fundacionales` y las referencias sin año reconocible. Devuelve
    {"base": [(entrada, anio)], "fuera": {id: (tipo, motivo)}, "sin_fecha": [entrada]}; `anio` es 9999 para «en prensa» (reciente) y 0 para «s. f.»."""
    fuera = clasificar_fuentes(lista, fr or {})
    base, sin_fecha = [], []
    for e in lista:
        if fuera.get(id(e)):
            continue
        t = e["texto"][:250]
        m = RE_ANIO.search(t)
        if m:
            base.append((e, int(m.group(1))))
        elif RE_PRENSA.search(t):
            base.append((e, 9999))  # en prensa: cuenta como reciente
        elif re.search(r"\((?:n\.d\.|s\.\s?f\.)", t):
            base.append((e, 0))  # sin fecha: cuenta en el denominador, nunca como reciente
        else:
            sin_fecha.append(e)
    return {"base": base, "fuera": fuera, "sin_fecha": sin_fecha}


def texto_exclusion(info):
    """Qué quedó fuera del denominador: «fuera del cálculo: N fundacionales, M documentales, K sin año»."""
    nf = sum(v[0] == "fundacional" for v in info["fuera"].values())
    nd = sum(v[0] == "documental" for v in info["fuera"].values())
    partes = [x for x in (f"{nf} fundacionales" if nf else "", f"{nd} documentales" if nd else "",
                          f"{len(info['sin_fecha'])} sin año" if info["sin_fecha"] else "") if x]
    return f" (fuera del cálculo: {', '.join(partes)})" if partes else ""


def nivel_por_entrada(entradas):
    """{id(entrada): nivel A-E} por el texto de la referencia (niveles.clasificar; sin red)."""
    import niveles
    import refs_csl
    ents = [e for e in entradas if e["texto"].strip()]
    items = refs_csl.parsear_lista([e["texto"] for e in ents])
    return {id(e): niveles.clasificar(it, e["texto"])["nivel"] for e, it in zip(ents, items)}


def _resumen_exclusion(clase):
    nf = sum(v[0] == "fundacional" for v in clase.values())
    nd = sum(v[0] == "documental" for v in clase.values())
    return f" (fuera del cálculo: {nf} fundacionales, {nd} documentales)" if nf or nd else ""


def avisos_fuentes(entradas, f):
    """Avisos de INS-008: qué referencias quedaron fuera del cálculo y si las fundacionales son demasiadas."""
    fr = (f or {}).get("fuentes_recientes")
    if not fr or not entradas:
        return []
    clase = clasificar_fuentes(entradas, fr)
    av = []
    if fr.get("arbitradas"):
        av.append("INS-008 con `arbitradas: true`: solo cuenta como reciente la fuente de nivel A o B (norma, revista arbitrada, actas, libro)")
    if clase:
        av.append("INS-008 calcula sobre la literatura actualizable;" + _resumen_exclusion(clase).strip(" ()").replace("fuera del cálculo:", " fuera del cálculo:"))
        for e in entradas:
            if id(e) in clase:
                tipo, motivo = clase[id(e)]
                av.append(f"  - {tipo}: {e['texto'][:70]}… ({motivo})")
    nf = sum(v[0] == "fundacional" for v in clase.values())
    if nf and nf * 100 > 40 * len(entradas):
        av.append(f"INS-008: {nf} de {len(entradas)} referencias declaradas fundacionales (más del 40 %): revisa que cada una sea una obra original que el documento usa")
    for x in fr.get("fundacionales") or []:
        if not any(" ".join(e["texto"].split()).startswith(x["ref"]) for e in entradas):
            av.append(f"INS-008: la fundacional «{x['ref']}» no coincide con ninguna referencia")
    return av
RE_COMILLADO = re.compile("“[^”]*”|«[^»]*»|\"[^\"]*\"")
PERSONA = [re.compile(x, re.I) for x in (
    r"\bnosotr[oa]s\b", r"\bnuestr[oa]s?\b", r"\byo\b", r"\bmi\s+(?:proyecto|trabajo|investigaci[oó]n|tesis|protocolo|estudio|propuesta)\b",
    r"\b(?:realizaremos|proponemos|desarrollaremos|consideramos|creemos|analizaremos|presentamos|pretendemos|buscamos|"
    r"utilizaremos|usaremos|obtendremos|evaluaremos|dise[ñn]aremos|implementaremos|elaboraremos|tenemos|podemos|debemos|"
    r"hemos|observamos|concluimos|planteamos|trabajamos)\b",
    r"\bvamos\s+a\b", r"\b(?:propongo|realizar[eé]|desarrollar[eé]|considero|pienso)\b", r"\bcreo\s+que\b")]


def _sin(s):
    return auditar.sin_acentos(s).lower()


def _bool(v):
    return v is True or (isinstance(v, str) and _sin(v).strip() in ("si", "true", "yes", "1"))


class ErrorPerfil(ValueError):
    """`vinculante:` inválido en .editorial.yaml: error de uso (código 2); los llamadores lo convierten con cli.error."""


def _rango(v, nombre, av, entero=True):
    """[min, max] de una lista de dos números (o None, con aviso)."""
    try:
        a, b = v
        a, b = (int(a), int(b)) if entero else (float(a), float(b))
        if a > b:
            raise ValueError
        return [a, b]
    except (TypeError, ValueError):
        av.append(f"formato.{nombre}: debe ser [mínimo, máximo] (p. ej. [150, 250])")
        return None


def normalizar_vinculante(lista, base=None):
    """Valida la lista `vinculante:` y devuelve las entradas normalizadas. Cada entrada: id (único), origen, fecha, tipo
    (modelo|instruccion), texto (instrucción) o spec (modelo: ruta a un JSON medido, relativa a .editorial.yaml) y ambito
    (portada | documento | seccion:<nombre>; por defecto portada para un modelo y documento para una instrucción).
    ErrorPerfil con todos los problemas si algo no cabe."""
    if lista is None:
        return []
    if not isinstance(lista, list):
        raise ErrorPerfil("vinculante: debe ser una lista de entradas {id, origen, fecha, tipo, texto|spec, ambito}")
    errores, out, ids = [], [], set()
    for n, e in enumerate(lista, 1):
        if not isinstance(e, dict):
            errores.append(f"vinculante[{n}]: debe ser un bloque de claves")
            continue
        i = str(e.get("id") or "").strip()
        pre = f"vinculante «{i}»" if i else f"vinculante[{n}]"
        if not i:
            errores.append(f"{pre}: falta `id`")
        elif i in ids:
            errores.append(f"{pre}: `id` repetido")
        ids.add(i)
        for k in ("origen", "fecha"):
            if not str(e.get(k) or "").strip():
                errores.append(f"{pre}: falta `{k}` (de dónde viene y cuándo se dio: «captura 26-nov», «guía p. 1»)")
        tipo = _sin(str(e.get("tipo") or "")).strip()
        if tipo not in ("modelo", "instruccion"):
            errores.append(f"{pre}: `tipo` debe ser modelo o instruccion")
        ambito = str(e.get("ambito") or ("portada" if tipo == "modelo" else "documento")).strip()
        if ambito not in AMBITOS_FIJOS and not (ambito.startswith("seccion:") and ambito[8:].strip()):
            errores.append(f"{pre}: `ambito` debe ser portada, documento o seccion:<nombre>, no «{ambito}»")
        item = {"id": i, "origen": str(e.get("origen") or "").strip(), "fecha": str(e.get("fecha") or "").strip(), "tipo": tipo, "ambito": ambito}
        if tipo == "instruccion":
            if not str(e.get("texto") or "").strip():
                errores.append(f"{pre}: una instruccion necesita `texto`")
            item["texto"] = " ".join(str(e.get("texto") or "").split())
        elif tipo == "modelo":
            ruta = str(e.get("spec") or "").strip()
            if not ruta:
                errores.append(f"{pre}: un modelo necesita `spec` (JSON medido con `editorial.py modelo medir`)")
            else:
                r = pathlib.Path(ruta)
                if not r.is_absolute() and base is not None:
                    r = pathlib.Path(base) / r
                import modelo_formato
                try:
                    item["spec"] = modelo_formato.cargar_spec(r)
                    item["spec_ruta"] = str(r)
                except modelo_formato.ErrorModelo as ex:
                    errores.append(f"{pre}: {ex}")
        out.append(item)
    if errores:
        raise ErrorPerfil("; ".join(errores))
    return out


def normalizar(raw, vinculante=None, base=None):
    """(formato normalizado, avisos). Claves desconocidas o valores no válidos se avisan y se ignoran. `vinculante` (la lista
    de .editorial.yaml, opcional) se valida con normalizar_vinculante y queda en f["vinculante"]; si es inválida lanza ErrorPerfil."""
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        return {}, ["formato: debe ser un bloque de claves (interlineado, alineacion, nivel1…)"]
    f, av = {}, []
    if vinculante is not None:
        f["vinculante"] = normalizar_vinculante(vinculante, base)
    for k in raw:
        if k not in CLAVES:
            av.append(f"formato: clave desconocida «{k}» (se ignora)")
    try:
        if raw.get("interlineado") is not None:
            f["interlineado"] = float(raw["interlineado"])
    except (TypeError, ValueError):
        av.append("formato.interlineado: debe ser un número (1.5, 2)")
    if raw.get("alineacion") is not None:
        a = _sin(str(raw["alineacion"]))
        if a.startswith(("justific", "justify")):
            f["alineacion"] = "justificada"
        elif a.startswith(("izq", "left")):
            f["alineacion"] = "izquierda"
        else:
            av.append("formato.alineacion: justificada | izquierda")
    n1 = raw.get("nivel1")
    if isinstance(n1, dict):
        f["nivel1"] = {"mayusculas": _bool(n1.get("mayusculas")), "numerado": _bool(n1.get("numerado"))}
    elif n1 is not None:
        av.append("formato.nivel1: bloque {mayusculas: true, numerado: true}")
    for k in ("niveles_numerados", "capitulo_pagina_nueva"):
        if raw.get(k) is not None:
            f[k] = _bool(raw[k])
    pg = raw.get("paginacion")
    if isinstance(pg, dict):
        g = {}
        if pg.get("portada") is not None:
            g["portada"] = "sin_numero" if "sin" in _sin(str(pg["portada"])) else "con_numero"
        for k, base in (("preliminares", "romanos"), ("cuerpo", "arabigos")):
            if pg.get(k) is not None:
                g[k] = "romanos" if _sin(str(pg[k])).startswith("roman") else "arabigos"
        if pg.get("posicion") is not None:
            pos = _sin(str(pg["posicion"])).strip().replace("-", "_").replace(" ", "_")
            pos = ALIAS_POSICION.get(pos, pos)
            if pos in POSICIONES:
                g["posicion"] = pos
            else:
                av.append("formato.paginacion.posicion: encabezado_derecha | pie_derecha | pie_centro")
        f["paginacion"] = g
    elif pg is not None:
        av.append("formato.paginacion: bloque {portada, preliminares, cuerpo}")
    if raw.get("titulo_max_palabras") is not None:
        try:
            f["titulo_max_palabras"] = int(raw["titulo_max_palabras"])
        except (TypeError, ValueError):
            av.append("formato.titulo_max_palabras: debe ser un entero")
    fr = raw.get("fuentes_recientes")
    if isinstance(fr, dict):
        try:
            f["fuentes_recientes"] = {"anios": int(fr.get("anios", 5)), "porcentaje": float(fr.get("porcentaje", 70)),
                                      "arbitradas": _bool(fr.get("arbitradas", False))}
        except (TypeError, ValueError):
            av.append("formato.fuentes_recientes: {anios: 5, porcentaje: 70}")
        if "fuentes_recientes" in f:
            for clave in ("fundacionales", "documentales"):
                lista = []
                for it in fr.get(clave) or []:
                    ref = (it.get("ref") if isinstance(it, dict) else None) or ""
                    motivo = (it.get("motivo") if isinstance(it, dict) else None) or ""
                    if not str(ref).strip() or not str(motivo).strip():
                        av.append(f"formato.fuentes_recientes.{clave}: cada entrada necesita `ref` y `motivo` ({it!r} se ignora)")
                        continue
                    lista.append({"ref": " ".join(str(ref).split()), "motivo": str(motivo).strip()})
                f["fuentes_recientes"][clave] = lista
    elif fr is not None:
        av.append("formato.fuentes_recientes: bloque {anios, porcentaje}")
    if raw.get("anio_actual") is not None:
        try:
            f["anio_actual"] = int(raw["anio_actual"])
        except (TypeError, ValueError):
            av.append("formato.anio_actual: debe ser un año")
    if raw.get("voz") is not None:
        if _sin(str(raw["voz"])).startswith("impersonal"):
            f["voz"] = "impersonal"
        else:
            av.append("formato.voz: solo se comprueba «impersonal»")
    fu = raw.get("fuente")
    if isinstance(fu, dict):
        g = {}
        if fu.get("nombre"):
            g["nombre"] = str(fu["nombre"]).strip()
        if fu.get("pt") is not None:
            try:
                g["pt"] = float(fu["pt"])
            except (TypeError, ValueError):
                av.append("formato.fuente.pt: debe ser un número")
        if g:
            f["fuente"] = g
        else:
            av.append("formato.fuente: bloque {nombre: Times New Roman, pt: 12}")
    elif fu is not None:
        av.append("formato.fuente: bloque {nombre: Times New Roman, pt: 12}")
    rs = raw.get("resumen")
    if isinstance(rs, dict):
        g = {}
        for k in ("palabras", "palabras_clave"):
            if rs.get(k) is not None:
                r_ = _rango(rs[k], "resumen." + k, av)
                if r_:
                    g[k] = r_
        for k in ("sangria", "un_parrafo"):
            if rs.get(k) is not None:
                g[k] = _bool(rs[k])
        f["resumen"] = g
    elif rs is not None:
        av.append("formato.resumen: bloque {palabras: [150, 250], sangria: false, un_parrafo: true, palabras_clave: [3, 5]}")
    if raw.get("rotulos_pt") is not None:
        r_ = _rango(raw["rotulos_pt"], "rotulos_pt", av, entero=False)
        if r_:
            f["rotulos_pt"] = r_
    po = raw.get("portada")
    if isinstance(po, dict):
        g = {"campos": []}
        for c in po.get("campos") or []:
            nombre = str(c.get("nombre") or "").strip() if isinstance(c, dict) else ""
            if not nombre:
                av.append(f"formato.portada.campos: cada campo necesita `nombre` ({c!r} se ignora)")
                continue
            item = {"nombre": nombre}
            if c.get("patron"):
                try:
                    re.compile(str(c["patron"]))
                    item["patron"] = str(c["patron"])
                except re.error as ex:
                    av.append(f"formato.portada.campos[{nombre}]: patrón inválido ({ex}); se ignora")
                    continue
            elif c.get("literal"):
                item["literal"] = str(c["literal"])
            elif _sin(nombre).startswith("titulo"):
                item["titulo"] = True
            else:
                av.append(f"formato.portada.campos[{nombre}]: necesita `patron` o `literal` (se ignora)")
                continue
            g["campos"].append(item)
        if po.get("fecha") is not None:
            if _sin(str(po["fecha"])).replace(" ", "_") in ("mes_anio", "mes_y_anio"):
                g["fecha"] = "mes_anio"
            else:
                av.append("formato.portada.fecha: solo se comprueba mes_anio")
        if po.get("numero_control") is not None:
            g["numero_control"] = _bool(po["numero_control"])
        if po.get("logos") is not None:
            if isinstance(po["logos"], list):
                g["logos"] = [{"nombre": str(x.get("nombre") or ""), **{k: x[k] for k in ("ruta", "alto_cm") if x.get(k) is not None}} if isinstance(x, dict) else str(x)
                              for x in po["logos"]]
            else:
                av.append("formato.portada.logos: lista de nombres (SEP, TNE, ITE) o de {nombre, ruta, alto_cm}")
        f["portada"] = g
    elif po is not None:
        av.append("formato.portada: bloque {campos, fecha, numero_control, logos}")
    return f, av


def excepciones_derivadas(f):
    """Excepciones APA que lo declarado en `formato:` hace innecesarias (se suman a las explícitas del perfil)."""
    out = []
    il = f.get("interlineado")
    if il and abs(il - 2.0) > 0.05:
        v = f"{il:g}"
        out.append({"regla": "APA-004", "motivo": f"formato institucional: interlineado {v}"})
        # APA-033 no necesita excepción: auditar exige a los encabezados el interlineado institucional (base_apa)
    if f.get("alineacion") == "justificada":
        out.append({"regla": "APA-006", "motivo": "formato institucional: párrafos justificados"})
    n1 = f.get("nivel1") or {}
    if n1.get("mayusculas"):
        out.append({"regla": "APA-025", "si_contiene": "mayúsculas", "motivo": "formato institucional: nivel 1 en mayúsculas"})
    if n1.get("numerado") or f.get("niveles_numerados"):
        out.append({"regla": "APA-030", "motivo": "formato institucional: capítulos y subcapítulos numerados"})
    pos = (f.get("paginacion") or {}).get("posicion")
    if pos and pos != "encabezado_derecha":
        out.append({"regla": "APA-008", "motivo": f"formato institucional: número de página en {pos.replace('_', ' ')}"})
    return out


# ---------------------------------------------------------------- selección de párrafos (la comparten auditar y corregir)
def es_prelim(p):
    return bool(RE_PRELIM.match(_sin(auditar.titulo_limpio(p["texto"]))))


def seleccion(pars, cuerpo, entradas):
    """Párrafos que juzgan las reglas: cuerpo (INS-001/002), entradas, encabezados de nivel 1 y 2 y fin de portada."""
    A = auditar
    fin_p = A.fin_portada(pars)
    ids_ent = {id(e) for e in entradas}
    previos = [p for p in pars if p["i"] >= fin_p and not p.get("en_tabla")]
    ids_ind = {id(p) for p in A.sin_indices(previos)}
    ids_cuerpo = {id(p) for p in cuerpo}
    c = []
    for p in pars:
        t = p["texto"]
        if (id(p) not in ids_cuerpo or id(p) not in ids_ind or p["i"] < fin_p or p.get("en_tabla") or p.get("es_titulo")
                or A.nivel_estilo(p) or len(t) <= 80 or p.get("imagen") or any(x in p["alineacion"] for x in ("CENTER", "RIGHT"))
                or A.RE_ROT_NUM.match(t.strip()) or A.RE_NOTA.match(t) or RE_CLAVE.match(t)):
            continue
        fz = [z for _, z in p.get("fuentes", ()) if z]
        if fz and max(fz) < 12:
            continue
        c.append(p)
    refs = [e for e in entradas if not e.get("en_tabla") and e["texto"].strip() and len(e["texto"]) > 40]
    h1 = [p for p in pars if p["i"] >= fin_p and A.nivel_estilo(p) == 1 and p["texto"].strip()]
    h2 = [p for p in pars if p["i"] >= fin_p and A.nivel_estilo(p) == 2 and p["texto"].strip()]
    cuerpo_ini = next((p["i"] for p in h1 if not es_prelim(p)), None)
    return {"fin_p": fin_p, "cuerpo": c, "refs": refs, "h1": h1, "h2": h2, "cuerpo_ini": cuerpo_ini, "ids_ent": ids_ent}


def excluido_alineacion(p, ids_ent):
    return bool(p.get("numerado") or id(p) in ids_ent or (p["sangria_izq"] >= 0.4 and p["sangria1"] < 0.4))


def inicia_pagina(pars, p):
    if p.get("salto_antes") or p.get("salto_estilo"):
        return True
    k = p["i"] - 1
    if k < 0 or k >= len(pars):
        return True
    prev = pars[k]
    if prev.get("sect"):
        return True
    return bool(prev.get("salto_antes") is True and (not prev["texto"].strip() or prev["texto"].endswith("\n")))


def numeracion_n1(h1):
    """[(párrafo, número o None)] de los capítulos (nivel 1 que no son preliminares)."""
    out = []
    for p in h1:
        if es_prelim(p):
            continue
        m = RE_NUM1.match(p["texto"])
        out.append((p, int(m.group(1)) if m and not RE_NUM2.match(p["texto"]) else None))
    return out


def _ej(lst, n=2):
    return "; ".join("«" + p["texto"][:40] + "»" for p in lst[:n])


# ---------------------------------------------------------------- reglas
def reglas(path, pars, cuerpo, titulo, entradas, f):
    A = auditar
    H = []
    S = seleccion(pars, cuerpo, entradas)
    ub = A.ubic
    il = f.get("interlineado")
    if il:
        malos = [p for p in S["cuerpo"] + S["refs"] if not (isinstance(p["interlineado"], (int, float)) and abs(p["interlineado"] - il) < 0.05)]
        if malos:
            p = malos[0]
            H.append(Hallazgo("INS-001", "mayor", ub(p), f"{len(malos)} párrafos sin interlineado {il:g} (p. ej. {p['interlineado']})",
                              f"interlineado {il:g} en el cuerpo y la lista de fuentes (formato institucional)"))
    al = f.get("alineacion")
    if al:
        malos = []
        for p in S["cuerpo"]:
            if excluido_alineacion(p, S["ids_ent"]):
                continue
            just = "JUSTIFY" in p["alineacion"]
            if just != (al == "justificada"):
                malos.append(p)
        if malos:
            H.append(Hallazgo("INS-002", "mayor", ub(malos[0]), f"{len(malos)} párrafos de cuerpo con alineación distinta de «{al}» (p. ej. {malos[0]['alineacion']})",
                              f"alineación {al} en los párrafos de cuerpo (formato institucional)"))
    n1 = f.get("nivel1") or {}
    caps = numeracion_n1(S["h1"])
    if n1.get("mayusculas"):
        malos = [p for p in S["h1"] if any(c.islower() for c in p["texto"] if c.isalpha())]
        if malos:
            H.append(Hallazgo("INS-003", "mayor", ub(malos[0]), f"{len(malos)} encabezados de nivel 1 no están en mayúsculas; p. ej. {_ej(malos)}",
                              "nivel 1 en MAYÚSCULAS (formato institucional)"))
    if n1.get("numerado"):
        sin = [p for p, n in caps if n is None and not p.get("numerado")]
        if sin:
            H.append(Hallazgo("INS-003", "mayor", ub(sin[0]), f"{len(sin)} encabezados de nivel 1 sin número «N.»; p. ej. {_ej(sin)}",
                              "numerar los capítulos «1.», «2.»… (los preliminares no llevan número)"))
        nums = [n for _, n in caps]
        if nums and all(n is not None for n in nums) and nums != list(range(1, len(nums) + 1)):
            H.append(Hallazgo("INS-003", "mayor", ub(caps[0][0]), f"numeración de capítulos no consecutiva: {', '.join(str(n) for n in nums)}",
                              "numerar los capítulos 1, 2, 3… sin saltos ni repeticiones"))
    if f.get("niveles_numerados"):
        malos, padre, nums_h = [], None, {}
        for p in sorted(S["h1"] + S["h2"], key=lambda q: q["i"]):
            if A.nivel_estilo(p) == 1:
                padre = None if es_prelim(p) else p
                continue
            if padre is None:
                continue
            m1 = RE_NUM1.match(padre["texto"])
            if not m1 or RE_NUM2.match(padre["texto"]) or p.get("numerado"):
                continue
            k = nums_h[id(padre)] = nums_h.get(id(padre), 0) + 1
            m = RE_NUM2.match(p["texto"])
            if not m or int(m.group(1)) != int(m1.group(1)) or int(m.group(2)) != k:
                malos.append(p)
        if malos:
            H.append(Hallazgo("INS-004", "mayor", ub(malos[0]), f"{len(malos)} encabezados de nivel 2 sin la numeración «N.k.» de su capítulo; p. ej. {_ej(malos)}",
                              "numerar los subcapítulos «1.1.», «1.2.»… con el número de su capítulo"))
    if f.get("capitulo_pagina_nueva"):
        malos = [p for p in S["h1"] if not inicia_pagina(pars, p)]
        if malos:
            H.append(Hallazgo("INS-005", "mayor", ub(malos[0]), f"{len(malos)} encabezados de nivel 1 no empiezan en página nueva; p. ej. {_ej(malos)}",
                              "salto de página antes de cada capítulo"))
    if f.get("paginacion"):
        H += paginacion(path, pars, S, f["paginacion"])
    mx = f.get("titulo_max_palabras")
    if mx:
        t = titulo_portada(pars, S["fin_p"])
        if t is not None and len(t["texto"].split()) > mx:
            H.append(Hallazgo("INS-007", "menor", ub(t), f"título de {len(t['texto'].split())} palabras (máximo {mx})", f"título de {mx} palabras como máximo"))
    fr = f.get("fuentes_recientes")
    if fr and entradas:
        anio = f.get("anio_actual") or datetime.date.today().year
        desde = anio - fr["anios"]
        tot = rec = 0
        lista = S["refs"] or entradas
        info_fr = literatura_actualizable(lista, fr)
        clase = info_fr["fuera"]
        nivel = {}
        if fr.get("arbitradas"):
            nivel = nivel_por_entrada(lista)
        for e, a in info_fr["base"]:
            arb = not fr.get("arbitradas") or nivel.get(id(e)) in ("A", "B")
            tot += 1
            rec += a >= desde and arb
        if tot and rec * 100 < fr["porcentaje"] * tot - 1e-9:
            excl = texto_exclusion(info_fr)
            que = f"son arbitradas (nivel A o B) y de {desde} o posteriores" if fr.get("arbitradas") else f"son de {desde} o posteriores"
            H.append(Hallazgo("INS-008", "menor", "lista de fuentes", f"{rec} de {tot} referencias actualizables ({100 * rec / tot:.0f} %) {que}{excl}",
                              f"al menos {fr['porcentaje']:g} % de las fuentes " + ("arbitradas (nivel A o B) " if fr.get("arbitradas") else "")
                              + f"de los últimos {fr['anios']} años"))
    if f.get("voz") == "impersonal":
        hits = []
        for p in pars:
            if p["i"] < S["fin_p"] or p.get("en_tabla") or p.get("es_titulo") or A.nivel_estilo(p) or id(p) in S["ids_ent"] or p is titulo:
                continue
            t = RE_COMILLADO.sub(" ", p["texto"])
            for rx in PERSONA:
                m = rx.search(t)
                if m:
                    hits.append((p, m.group(0)))
                    break
        if hits:
            p, w = hits[0]
            H.append(Hallazgo("INS-009", "menor", ub(p), f"{len(hits)} párrafos en primera persona; p. ej. «{w}»", "voz impersonal: tercera persona o «se» reflexivo"))
    if f.get("titulo_fijo"):
        H += titulo_fijado(pars, S, f)
    if f.get("portada"):
        est = next((p for p in pars[:S["fin_p"]] if p.get("estilo", "").lower() in ("title", "título", "titulo") and p["texto"].strip()), None)
        H += portada_oficial(pars, S, f["portada"], est)
    if f.get("fuente"):
        H += tipografia_encabezados(path, f["fuente"])
    if f.get("resumen"):
        H += resumen_reglas(pars, f["resumen"])
    if f.get("rotulos_pt"):
        H += rotulos_reglas(pars, S, f["rotulos_pt"])
    if f.get("vinculante"):
        H += fidelidad_modelo(path, f["vinculante"])
    return H


def titulo_fijado(pars, S, f):
    """INS-010: el título de la portada coincide con `titulo:` de .editorial.yaml (vinculante)."""
    import titulo as T
    if S["fin_p"] == 0:
        return []  # sin portada: lo dice el resto de INS-010 o EST-016
    campos = (f.get("portada") or {}).get("campos") or []
    bus = [_buscador(c) for c in campos if "titulo" not in c]
    real = T.titulo_de_portada(pars, S["fin_p"], bus)
    fijo = f["titulo_fijo"]
    if real is None:
        return [Hallazgo("INS-010", "mayor", "portada", f"no se reconoce el título en la portada; `titulo:` fija «{fijo[:90]}»",
                         "poner en la portada el título fijado en .editorial.yaml")]
    if T.norm(real) != T.norm(fijo):
        return [Hallazgo("INS-010", "mayor", "portada", f"el título de la portada «{real[:90]}» no coincide con el título fijado en .editorial.yaml «{fijo[:90]}»",
                         "reproducir el título fijado en la portada (cambiarlo exige elegir otro con `editorial.py titulo` y actualizar `titulo:`)")]
    return []


def titulo_portada(pars, fin_p):
    """Título de la portada: párrafo de estilo Title/Título, o la línea más larga que no es una etiqueta de la portada."""
    cands = [p for p in pars[:fin_p] if p["texto"].strip() and not p.get("en_tabla")]
    est = [p for p in cands if p.get("estilo", "").lower() in ("title", "título", "titulo")]
    if est:
        return est[0]
    ok = [p for p in cands if not RE_ETIQUETA_PORTADA.match(p["texto"]) and not RE_LEYENDA.search(p["texto"]) and len(p["texto"].split()) >= 4]
    return max(ok, key=lambda p: len(p["texto"])) if ok else None


# ---------------------------------------------------------------- INS-006: paginación por sección
def formato_seccion(sec_el):
    """(fmt, start) de w:pgNumType de un w:sectPr (fmt «decimal» si no se declara)."""
    from docx.oxml.ns import qn
    pg = sec_el.find(qn("w:pgNumType"))
    if pg is None:
        return "decimal", None
    return pg.get(qn("w:fmt")) or "decimal", pg.get(qn("w:start"))


def roles_por_seccion(pars, S, n_sec):
    """{n.º de sección: set de roles (portada, preliminares, cuerpo)} o None si las secciones no cuadran."""
    sec, roles = 0, {}
    for p in pars:
        r = "portada" if p["i"] < S["fin_p"] else ("cuerpo" if S["cuerpo_ini"] is not None and p["i"] >= S["cuerpo_ini"] else "preliminares")
        roles.setdefault(sec, set()).add(r)
        if p.get("sect"):
            sec += 1
    if sec != n_sec - 1:
        return None
    return roles


def lado_numero(p_el):
    """«derecha» | «centro» | «izquierda» | None (indeterminado: tabuladores) del párrafo que lleva el campo PAGE."""
    ptabs = [x.get(qn("w:alignment")) for x in p_el.iter(qn("w:ptab"))]
    if ptabs:
        return {"right": "derecha", "center": "centro", "left": "izquierda"}.get(ptabs[-1])
    jc = p_el.find(qn("w:pPr") + "/" + qn("w:jc"))
    v = jc.get(qn("w:val")) if jc is not None else None
    if v in ("right", "end"):
        return "derecha"
    if v == "center":
        return "centro"
    if any(True for _ in p_el.iter(qn("w:tab"))):
        return None
    return "izquierda"


def lugar_numero(d):
    """{(lugar, lado)} dónde está el número de página en las partes predeterminadas (no la primera página) de las secciones que
    las definen: lugar «encabezado» | «pie», lado como lado_numero (None si no se puede decir)."""
    out = {}
    for k, sec in enumerate(d.sections):
        for nom, h, f in ooxml.partes_seccion(sec, k, d, pares=True, sec0_propia=True):
            if nom.startswith("primera"):
                continue
            for lugar, parte in (("encabezado", h), ("pie", f)):
                if parte is None or not ooxml.tiene_pagina(parte._element):
                    continue
                for p_el in parte._element.iter(qn("w:p")):
                    if ooxml.tiene_pagina(p_el):
                        out.setdefault((lugar, lado_numero(p_el)), k + 1)
    return out


_LADO = {"derecha": "a la derecha", "centro": "centrado", "izquierda": "a la izquierda"}


def posicion_numero(d, posicion):
    """INS-006: el número de página está donde `posicion` declara (encabezado_derecha | pie_derecha | pie_centro)."""
    lugar_ok, lado_ok = posicion.split("_")
    flag = {"encabezado_derecha": "encabezado-derecha", "pie_derecha": "pie-derecha", "pie_centro": "pie-centro"}[posicion]
    H = []
    for (lugar, lado), k in sorted(lugar_numero(d).items(), key=lambda x: x[1]):
        if lado is None and lugar == lugar_ok:
            continue  # tabuladores: no se puede decir el lado, no se acusa
        if lugar != lugar_ok or lado != lado_ok:
            H.append(Hallazgo("INS-006", "mayor", f"sección {k}", f"el número de página está en el {lugar}" + (f", {_LADO[lado]}" if lado else "")
                              + f" y `paginacion.posicion` pide {posicion.replace('_', ' ')}",
                              f"número de página en el {lugar_ok}, {_LADO[lado_ok]} (/corregir --paginacion {flag})"))
    if not lugar_numero(d):
        H.append(Hallazgo("INS-006", "mayor", "documento", f"ninguna sección lleva número de página y `paginacion.posicion` pide {posicion.replace('_', ' ')}",
                          f"/corregir --paginacion {flag}"))
    return H


def paginacion(path, pars, S, cfg):
    A = auditar
    H = []
    d = A.abrir_docx(str(path))
    if cfg.get("posicion"):
        H += posicion_numero(d, cfg["posicion"])
    if cfg.get("portada") == "sin_numero":
        est, _ = A.estado_portada(d)
        if est != "ninguno":
            H.append(Hallazgo("INS-006", "mayor", "portada", f"la portada lleva número de página (en el {est})", "portada sin número visible (primera página distinta o sección propia sin PAGE)"))
    roles = roles_por_seccion(pars, S, len(d.sections))
    if roles is None:
        return H
    cuerpo_visto = False
    for k, sec in enumerate(d.sections):
        rs = roles.get(k, set())
        fmt, start = formato_seccion(sec._sectPr)
        if ("preliminares" in rs and "cuerpo" in rs) or ("portada" in rs and len(rs) > 1 and (cfg.get("preliminares") or cfg.get("cuerpo"))):
            H.append(Hallazgo("INS-006", "mayor", f"sección {k + 1}", f"la sección mezcla {', '.join(sorted(rs))} con un solo formato de número",
                              "separar portada, preliminares y cuerpo con saltos de sección (siguiente página)"))
            continue
        if rs == {"preliminares"} and cfg.get("preliminares") == "romanos" and fmt != "lowerRoman":
            H.append(Hallazgo("INS-006", "mayor", f"sección {k + 1}", f"preliminares con numeración «{fmt}» (se pide romanos minúsculos i, ii, iii)", "formato de número lowerRoman en la sección de los preliminares"))
        if rs == {"cuerpo"} and cfg.get("cuerpo") == "arabigos":
            if fmt != "decimal":
                H.append(Hallazgo("INS-006", "mayor", f"sección {k + 1}", f"cuerpo con numeración «{fmt}» (se pide arábigos)", "formato de número decimal en la sección del cuerpo"))
            elif not cuerpo_visto and start != "1":
                H.append(Hallazgo("INS-006", "mayor", f"sección {k + 1}", "la numeración del cuerpo no reinicia en 1 (w:pgNumType sin start=1)", "reiniciar en 1 la numeración del primer capítulo"))
            cuerpo_visto = True
    return H


# ---------------------------------------------------------------- INS-010: portada oficial
MESES = "enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|setiembre|octubre|noviembre|diciembre"
RE_MES_ANIO = re.compile(r"(?<![a-z])(?:" + MESES + r")\s+(?:de\s+)?(?:19|20)\d{2}(?!\d)")
RE_FECHA_MAL = re.compile(r"\d{1,2}\s*[/.\-]\s*(?:" + MESES + r"|\d{1,2})\s*[/.\-]\s*\d{2,4}|\d{1,2}\s+de\s+(?:" + MESES + r")")
RE_CONTROL = re.compile(r"(?<![A-Za-z0-9])[A-Za-z]?\d{8}(?!\d)")
RE_INTEGRANTES = re.compile(r"^\s*(integrantes?|autor(?:es)?|alumnos?|estudiantes?|equipo)\b\s*:?\s*(.*)$", re.I)
RE_PENDIENTE = re.compile(r"\[\[\s*PENDIENTE", re.I)
RE_PERSONAS = re.compile(r"\s*;\s*|(?<=\))\s*,?\s*|(?<=\d)\s*,\s*")


def lineas_portada(pars, fin_p):
    """Textos (una línea visual cada uno, sin vacías) de la portada y su párrafo de origen."""
    out = []
    for p in pars[:fin_p]:
        for t in p["texto"].split("\n"):
            t = " ".join(t.split())
            if t:
                out.append((t, p))
    return out


def _buscador(c):
    """Función texto -> bool de un campo de portada (literal contenido o patrón, sin distinguir mayúsculas ni acentos)."""
    if c.get("literal"):
        lit = _sin(" ".join(c["literal"].split()))
        return lambda t: lit in _sin(" ".join(t.split()))
    rx = re.compile(c["patron"])  # sin re.I: el patrón decide con (?i:...)
    return lambda t: bool(rx.search(t) or rx.search(_sin(t)))


def _candidato_titulo(t, otros, min_pal=5):
    return (len(t.split()) >= min_pal and not t.rstrip().endswith(":") and not RE_ETIQUETA_PORTADA.match(t)
            and not RE_CONTROL.search(t) and not any(f(t) for f in otros))


def portada_oficial(pars, S, cfg, titulo_est):
    """INS-010: [Hallazgo] por campos faltantes, orden, fecha y números de control."""
    H = []
    if S["fin_p"] == 0:
        return [Hallazgo("INS-010", "mayor", "documento", "no se reconoce la portada (el documento empieza con el cuerpo)",
                         "portada oficial al inicio, antes del resumen o del primer capítulo")]
    lineas = lineas_portada(pars, S["fin_p"])
    textos = [t for t, _ in lineas]
    campos = cfg.get("campos") or []
    bus = {c["nombre"]: _buscador(c) for c in campos if "titulo" not in c}
    faltan, desorden, pos, ultimo = [], [], {}, -1
    for c in campos:
        if "titulo" in c:
            est = next((k for k, (t, p) in enumerate(lineas) if p is titulo_est), None) if titulo_est is not None else None
            cands = [k for k, t in enumerate(textos) if _candidato_titulo(t, list(bus.values()))]
            k = est if est is not None else next((k for k in cands if k > ultimo), cands[0] if cands else None)
        else:
            f = bus[c["nombre"]]
            hits = [k for k, t in enumerate(textos) if f(t)]
            k = next((k for k in hits if k > ultimo), hits[0] if hits else None)
        if k is None:
            faltan.append(c["nombre"])
        elif k < ultimo:
            desorden.append(c["nombre"])
        else:
            ultimo = k
            pos[c["nombre"]] = k
    ub = "portada"
    if faltan:
        H.append(Hallazgo("INS-010", "mayor", ub, "faltan en la portada: " + "; ".join(faltan),
                          "añadir a la portada lo que pide la guía, con el formato de la portada modelo"))
    if desorden:
        H.append(Hallazgo("INS-010", "mayor", ub, "fuera de orden en la portada: " + "; ".join(desorden),
                          "ordenar la portada como la guía: " + " > ".join(c["nombre"] for c in campos)))
    if cfg.get("fecha") == "mes_anio":
        mal = next((t for t in textos if RE_FECHA_MAL.search(_sin(t))), None)
        bien = any(RE_MES_ANIO.search(_sin(t)) and not RE_FECHA_MAL.search(_sin(t)) for t in textos)
        if mal:
            H.append(Hallazgo("INS-010", "mayor", ub, f"fecha «{mal}»: la guía pide Mes y Año", "escribir la fecha como «Noviembre 2026» (mes y año, sin día)"))
        elif not bien:
            H.append(Hallazgo("INS-010", "mayor", ub, "falta la fecha en formato Mes y Año", "añadir la fecha como «Noviembre 2026»"))
    if cfg.get("numero_control"):
        sin = _sin_control(textos, [f for n, f in bus.items() if not RE_INTEGRANTES.match(n)])
        if sin is None:
            H.append(Hallazgo("INS-010", "mayor", ub, "no se identifican los integrantes (etiqueta «Integrantes:») para comprobar su número de control",
                              "listar los integrantes con su número de control"))
        elif sin[0]:
            H.append(Hallazgo("INS-010", "mayor", ub, f"{len(sin[0])} de {sin[1]} integrantes sin número de control: " + "; ".join(sin[0][:4]),
                              "número de control junto a cada integrante (8 dígitos o letra y 8 dígitos; [[PENDIENTE]] cuenta como falta)"))
    return H


def _sin_control(textos, otros):
    """(integrantes sin número de control, total) o None si no hay lista de integrantes; ([], n) si todos lo tienen."""
    for k, t in enumerate(textos):
        m = RE_INTEGRANTES.match(t)
        if not m:
            continue
        personas = [x.strip() for x in RE_PERSONAS.split(m.group(2)) if x and x.strip()]
        if not personas:
            for t2 in textos[k + 1:]:
                if t2.rstrip().endswith(":") or RE_ETIQUETA_PORTADA.match(t2) or any(f(t2) for f in otros):
                    break
                if RE_CONTROL.fullmatch(t2.strip()) and personas:
                    personas[-1] += " " + t2.strip()
                else:
                    personas.append(t2.strip())
        faltan = [x for x in personas if not RE_CONTROL.search(x) or RE_PENDIENTE.search(x)]
        return [x[:40] for x in faltan], len(personas)
    return None


def imagenes_portada(path, pars, fin_p):
    """Número de imágenes en la portada (párrafos) y en el encabezado de la primera sección."""
    n = sum(1 for p in pars[:fin_p] if p.get("imagen"))
    try:
        d = auditar.abrir_docx(str(path))
        s = d.sections[0]
        for h in (s.first_page_header if s.different_first_page_header_footer else s.header, ):
            n += sum(1 for _ in h._element.iter("{http://schemas.openxmlformats.org/drawingml/2006/main}blip",
                                                "{urn:schemas-microsoft-com:vml}imagedata"))
    except Exception:  # noqa: BLE001
        pass
    return n


# ---------------------------------------------------------------- INS-011: fuente de encabezados y pies
def _partes(d):
    """[(etiqueta, parte)] de encabezados y pies con definición propia de cada sección."""
    out = []
    for k, sec in enumerate(d.sections, 1):
        for nom, h, f in ooxml.partes_seccion(sec, k - 1, d, pares=True, sec0_propia=True):
            for tipo, parte in (("encabezado", h), ("pie", f)):
                if parte is not None:
                    out.append((f"{tipo} ({nom}sección {k})", parte))
    return out


def _runs_tipograficos(parte):
    """(w:p, w:r) de los runs que muestran algo: texto o campo."""
    for p_el in parte._element.iter(qn("w:p")):
        if not ooxml.texto_xml(p_el).strip() and not any(True for _ in p_el.iter(qn("w:instrText"))):
            continue
        for r_el in p_el.iter(qn("w:r")):
            if any(True for x in r_el.iter(qn("w:t"), qn("w:instrText")) if (x.text or "").strip()):
                yield p_el, r_el


def _negro(c):
    return max(int(c[k:k + 2], 16) for k in (1, 3, 5)) < 0x40


def desajustes_tipografia(d, fu):
    """[(etiqueta, w:r, resumen del problema)] de los runs de encabezados y pies que no cumplen `fuente:` ni son negros."""
    import modelo_formato as MF
    res = MF.Resolutor(d)
    out = []
    for etiq, parte in _partes(d):
        for p_el, r_el in _runs_tipograficos(parte):
            e = res.run(r_el, p_el)
            mal = []
            if fu.get("nombre") and MF.norm_fuente(e["fuente"]) != MF.norm_fuente(fu["nombre"]):
                mal.append(e["fuente"])
            if fu.get("pt") and abs(e["pt"] - fu["pt"]) > MF.TOL_PT:
                mal.append(f"{e['pt']:g} pt")
            if not _negro(e["color"]):
                mal.append(f"color {e['color']}")
            if mal:
                out.append((etiq, r_el, " ".join(mal)))
    return out


def tipografia_encabezados(path, fu):
    d = auditar.abrir_docx(str(path))
    mal = desajustes_tipografia(d, fu)
    if not mal:
        return []
    pide = " ".join(x for x in (fu.get("nombre"), f"{fu['pt']:g} pt" if fu.get("pt") else None) if x)
    distintos = []
    for etiq, _, r in mal:
        if (etiq, r) not in distintos:
            distintos.append((etiq, r))
    primero = distintos[0]
    mas = f" (+{len(distintos) - 1} más)" if len(distintos) > 1 else ""
    return [Hallazgo("INS-011", "mayor", primero[0], f"{primero[1]} en lugar de {pide}, texto negro{mas}",
                     f"encabezados y pies en {pide} y texto negro (formato institucional)")]


# ---------------------------------------------------------------- INS-012: resumen
RE_TITULO_RESUMEN = re.compile(r"^(resumen|abstract)$")


def info_resumen(pars):
    """(encabezado, párrafos del cuerpo del resumen, línea de palabras clave o None) o None si no hay resumen."""
    A = auditar
    for k, p in enumerate(pars):
        if p.get("en_tabla") or len(p["texto"]) > 30 or not RE_TITULO_RESUMEN.match(_sin(A.titulo_limpio(p["texto"]))):
            continue
        cuerpo, claves = [], None
        for q in pars[k + 1:]:
            if q.get("en_tabla") or A.nivel_estilo(q) or q.get("es_titulo") or q.get("salto_antes") or q.get("salto_estilo") or q.get("sect"):
                break
            if not q["texto"].strip():
                continue
            if RE_CLAVE.match(q["texto"]):
                claves = q
            else:
                cuerpo.append(q)
        return p, cuerpo, claves
    return None


def resumen_reglas(pars, cfg):
    info = info_resumen(pars)
    if info is None:
        return []
    enc, cuerpo, claves = info
    mal = []
    n = sum(len(q["texto"].split()) for q in cuerpo)
    lo_hi = cfg.get("palabras")
    if lo_hi and not lo_hi[0] <= n <= lo_hi[1]:
        mal.append(f"{n} palabras (se piden {lo_hi[0]}-{lo_hi[1]})")
    if cfg.get("un_parrafo") and len(cuerpo) > 1:
        mal.append(f"{len(cuerpo)} párrafos (se pide uno solo)")
    if cfg.get("sangria") is False:
        con = [q for q in cuerpo + ([claves] if claves else []) if q["sangria1"] > 0.05]
        if con:
            mal.append(f"{len(con)} párrafos con sangría de primera línea (se pide sin sangría)")
    rng = cfg.get("palabras_clave")
    if rng:
        if claves is None:
            mal.append("sin línea de palabras clave")
        else:
            k = len([x for x in re.split(r"[;,]", claves["texto"].split(":", 1)[1]) if x.strip(" .\t")])
            if not rng[0] <= k <= rng[1]:
                mal.append(f"{k} palabras clave (se piden {rng[0]}-{rng[1]})")
    if not mal:
        return []
    return [Hallazgo("INS-012", "mayor", auditar.ubic(enc), "; ".join(mal),
                     "resumen en un solo párrafo sin sangría, con el número de palabras y de palabras clave de la guía")]


# ---------------------------------------------------------------- INS-013: tamaño de los rótulos
def rotulos_fuera(pars, S, rango):
    """Párrafos de rótulo («TABLA I», «Fig. 1. …») cuyo tamaño sale de [min, max] pt."""
    A = auditar
    previos = [p for p in pars if p["i"] >= S["fin_p"] and not p.get("en_tabla")]
    out = []
    for p in A.sin_indices(previos):
        t = p["texto"].strip()
        m = A.RE_ROTULO.match(t)
        if not m or len(t) > 220 or p.get("imagen"):
            continue
        resto, punt = m.group(4).strip(), m.group(3)
        if resto and not punt and not t.isupper():
            continue  # «La tabla 2 muestra…» al inicio de una frase: mención, no rótulo
        tam = [z for _, z in p.get("fuentes", ()) if z]
        if tam and (max(tam) > rango[1] + 0.01 or min(tam) < rango[0] - 0.01):
            out.append(p)
    return out


def rotulos_reglas(pars, S, rango):
    mal = rotulos_fuera(pars, S, rango)
    if not mal:
        return []
    p = mal[0]
    tam = sorted({z for _, z in p.get("fuentes", ()) if z})
    return [Hallazgo("INS-013", "menor", auditar.ubic(p), f"{len(mal)} rótulos fuera de {rango[0]:g}-{rango[1]:g} pt (p. ej. {', '.join(f'{z:g}' for z in tam)} pt)",
                     f"rótulos de tabla y figura de {rango[0]:g} a {rango[1]:g} pt")]


# ---------------------------------------------------------------- INS-015: fidelidad al modelo vinculante
def fidelidad_modelo(path, vinculante):
    """INS-015: compara el ámbito de cada `modelo` vinculante con su spec; una diferencia por línea de la spec."""
    import modelo_formato as MF
    H = []
    for v in vinculante:
        if v["tipo"] != "modelo":
            continue
        try:
            difs = MF.comparar_docx(path, v["spec"], v["ambito"])
        except Exception as e:  # noqa: BLE001
            H.append(Hallazgo("INS-015", "mayor", v["ambito"], f"no se pudo comparar con el modelo «{v['id']}»: {e}", "revisar la spec del modelo"))
            continue
        for x in difs:
            ev = f"modelo «{v['id']}»: " + "; ".join(x["diferencias"])
            H.append(Hallazgo("INS-015", "mayor", f"{v['ambito']}, línea {x['linea']} del modelo «{x['texto'][:40]}»" if x["linea"] else v["ambito"],
                              ev, f"reproducir el modelo ({v['origen']}, {v['fecha']}) al pie de la letra"))
    return H


def avisos_extra(path, pars, cuerpo, titulo, entradas, f):
    """Avisos de INS-010 (logotipos) y de las instrucciones vinculantes (las reproduce el agente)."""
    av = []
    po = f.get("portada") or {}
    if po.get("logos"):
        S = seleccion(pars, cuerpo, entradas)
        n = imagenes_portada(path, pars, S["fin_p"])
        if n < len(po["logos"]):
            av.append(f"INS-010: la portada lleva {n} imágenes; la guía pide los logotipos de {', '.join(x['nombre'] if isinstance(x, dict) else x for x in po['logos'])} ({len(po['logos'])})")
    for v in f.get("vinculante") or []:
        if v["tipo"] == "instruccion":
            av.append(f"vinculante «{v['id']}» ({v['origen']}, {v['fecha']}; ámbito {v['ambito']}): {v['texto']} [instrucción registrada: la verifica el agente, no el script]")
    return av
