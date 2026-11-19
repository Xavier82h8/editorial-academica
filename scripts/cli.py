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


def perfil_por_defecto(ap, perfil, doc, equipo=None, defecto=None):
    """`perfil` explícito, o el `perfil:` de .editorial.yaml, o `defecto`; si no hay ninguno, `ap.error` (código 2)."""
    if perfil:
        return perfil
    if doc:
        import auditar
        ruta = auditar.buscar_equipo(doc, equipo)
        if ruta and ruta.exists():
            try:
                cfg = auditar.yaml.safe_load(ruta.read_text(encoding="utf-8")) or {}
            except auditar.yaml.YAMLError:
                cfg = {}
            if isinstance(cfg, dict) and cfg.get("perfil"):
                return str(cfg["perfil"])
    if defecto:
        return defecto
    ap.error("falta --perfil (o un .editorial.yaml con `perfil:`)")


def codigo(hallazgos):
    """1 si algún hallazgo es crítico o mayor; 0 si no hay o solo hay menores."""
    return HALLAZGOS if any(h.get("severidad") in SEVERIDADES_QUE_FALLAN for h in hallazgos) else OK


def escribir_json(ruta, datos, indent=1):
    """Escribe `datos` como JSON UTF-8 en `ruta` (si `ruta` es falsa, no hace nada)."""
    if ruta:
        pathlib.Path(ruta).write_text(json.dumps(datos, ensure_ascii=False, indent=indent), encoding="utf-8")
