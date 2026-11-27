#!/usr/bin/env python3
"""Convención de línea de comandos compartida por todos los scripts (y por `editorial.py`).

- `--perfil ID`: si falta, se usa el `perfil:` de `.editorial.yaml` (el primero hacia arriba desde el documento,
  `auditar.buscar_equipo`); sin ninguno, error de uso (código 2). En `convertir`, `--perfil` es alias de `--a`.
- `--json RUTA`: donde hay resultado estructurado, lo escribe como JSON UTF-8.
- Códigos de salida:
    0  sin hallazgos, o solo menores
    1  hay hallazgos críticos o mayores (`codigo(hallazgos)`); en `fuentes --verificar`, fuentes que fallan
    2  error de uso o de entrada (archivo inexistente o de formato no soportado, perfil desconocido, herramienta
       externa ausente, falta un argumento): mensaje claro en stderr, sin traceback
"""
import json
import pathlib
import sys

OK, HALLAZGOS, ERROR = 0, 1, 2
SEVERIDADES_QUE_FALLAN = ("crítica", "mayor")


def utf8():
    """stdout/stderr en UTF-8 aunque la consola de Windows use otra página de códigos."""
    for flujo in (sys.stdout, sys.stderr):
        try:
            flujo.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass


def error(msg):
    """Mensaje a stderr y salida con código 2."""
    utf8()
    print(msg, file=sys.stderr)
    sys.exit(ERROR)


# Qué perfil se aplicó y de dónde salió (la última llamada a `perfil_por_defecto`); los scripts lo vuelcan a su JSON.
APLICADO = {}


# Claves de un .editorial.yaml que lo vuelven institucional: con ellas el archivo cambia lo que se exige y se corrige.
CLAVES_INSTITUCIONALES = ("formato", "vinculante", "excepciones", "medidas", "tablas_figuras", "titulo", "portada_numero", "fuentes", "reglas_guia")


def _equipo_declarado(doc, equipo):
    """(ruta del .editorial.yaml, `perfil:` que declara, claves institucionales que trae) del que encontraría la búsqueda hacia
    arriba; (None, None, []) sin ninguno."""
    if not doc:
        return None, None, []
    import auditar
    ruta = auditar.buscar_equipo(doc, equipo, ignorados=False)
    if not ruta or not ruta.exists():
        return None, None, []
    try:
        cfg = auditar.yaml.safe_load(ruta.read_text(encoding="utf-8")) or {}
    except auditar.yaml.YAMLError:
        cfg = {}
    if not isinstance(cfg, dict):
        cfg = {}
    return ruta, (str(cfg["perfil"]) if cfg.get("perfil") else None), [k for k in CLAVES_INSTITUCIONALES if cfg.get(k)]


def perfil_por_defecto(ap, perfil, doc, equipo=None, defecto=None, anunciar=True, ignorar_equipo=True):
    """Perfil que se aplica y su origen. Precedencia: `--perfil` explícito > `perfil:` de .editorial.yaml > `defecto`; sin
    ninguno, `ap.error` (código 2).

    Si el perfil viene de `--perfil` y el .editorial.yaml encontrado hacia arriba declara OTRO perfil, o trae un bloque
    institucional (`formato:`, `vinculante:`, excepciones, medidas…) aunque declare el mismo, ese archivo se ignora entero
    (nada de su bloque se aplica) salvo que se pida con `--equipo`: se avisa en stderr y queda en `APLICADO["ignorado"]`.
    `--perfil apa7` explícito significa «APA 7 tal cual», no «APA 7 más la institución de esta carpeta». Imprime al inicio «perfil aplicado: X (origen: CLI | .editorial.yaml en <ruta> | …)»."""
    global APLICADO
    if equipo:
        import auditar
        auditar.EQUIPO_EXPLICITO = pathlib.Path(equipo)
    ruta, declarado, inst = _equipo_declarado(doc, equipo)
    ignorado = None
    if perfil:
        origen = "CLI"
        if ruta and ignorar_equipo and ((declarado and declarado != perfil) or inst):
            if equipo:
                if declarado and declarado != perfil:
                    _stderr(f"aviso: --equipo explícito {ruta} declara el perfil {declarado} y pediste {perfil}: se aplica su bloque con el perfil {perfil}")
            else:
                import auditar
                auditar.IGNORADOS.add(ruta.resolve())
                detalle = f"declara {declarado or 'ningún perfil'}" + (f" con bloque institucional ({', '.join(inst)})" if inst else "")
                ignorado = {"ruta": str(ruta), "declara": declarado, "pediste": perfil, "bloque_institucional": inst,
                            "mensaje": f"se ignora .editorial.yaml de {ruta}: {detalle}, pediste {perfil}"}
                _stderr("aviso: " + ignorado["mensaje"] + " (usa --equipo para aplicarlo)")
    elif declarado:
        perfil, origen = declarado, f".editorial.yaml en {ruta}"
    elif defecto:
        perfil, origen = defecto, "por defecto"
    else:
        ap.error("falta --perfil (o un .editorial.yaml con `perfil:`)")
    if origen == "CLI" and ruta and not ignorado:
        origen += f"; equipo: .editorial.yaml en {ruta}"
    APLICADO = {"perfil": perfil, "origen": origen, "equipo": str(ruta) if ruta and not ignorado else None, "ignorado": ignorado}
    if anunciar:
        print(f"perfil aplicado: {perfil} (origen: {origen})")
    return perfil


def _stderr(msg):
    utf8()
    print(msg, file=sys.stderr)


def con_perfil(datos):
    """Copia de `datos` (dict de resultado) con la clave `perfil_aplicado` (perfil, origen y .editorial.yaml ignorado, si lo hubo)."""
    if isinstance(datos, dict) and APLICADO:
        datos = {**datos, "perfil_aplicado": dict(APLICADO)}
    return datos


def codigo(hallazgos):
    """1 si algún hallazgo es crítico o mayor; 0 si no hay o solo hay menores."""
    return HALLAZGOS if any(h.get("severidad") in SEVERIDADES_QUE_FALLAN for h in hallazgos) else OK


def escribir_json(ruta, datos, indent=1):
    """Escribe `datos` como JSON UTF-8 en `ruta` (si `ruta` es falsa, no hace nada)."""
    if ruta:
        datos = con_perfil(datos)
        pathlib.Path(ruta).write_text(json.dumps(datos, ensure_ascii=False, indent=indent), encoding="utf-8")
