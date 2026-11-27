#!/usr/bin/env python3
"""Unidades, equivalencias y tolerancias de medida: UNA sola tabla para `medir`, `medidas` y las reglas de `auditar`.

Equivalentes que NO son hallazgo: 2.54 cm = 1 in = 72 pt; 1.27 cm = 0.5 in = 36 pt; 1 in = 1440 twips = 914400 EMU;
12 pt = 24 medios puntos (w:sz). Todo se compara en puntos (pt) con la tolerancia de la medida.

Interlineado (cómo lo ve Word): hay tres reglas, y un mismo «1.5» puede venir de cualquiera:
  auto     w:line=360, lineRule=auto   múltiplo de la altura natural de la fuente (1.5 líneas)
  exact    w:line=360, lineRule=exact  18 pt fijos
  atLeast  w:line=360, lineRule=atLeast 18 pt como mínimo (la línea puede crecer: no se puede afirmar)
Equivalencia declarada: «múltiplo m» == auto m == exacto m × tamaño (nominal: 1.5 con 12 pt = 18 pt) y también
exacto m × tamaño × 1.15 (la altura natural de línea de Times New Roman, Calibri y Arial ronda 1.15 × el tamaño; así
mide Word un «1.5 líneas» automático: 12 pt -> 20.7 pt de línea). La segunda es APROXIMADA y se rotula «equivalente»
con su nota, nunca «igual». Una regla puede declarar `modo: exacto` para exigir los puntos tal cual.

Tolerancias por defecto (sobreescribibles por regla con `tolerancia`; son las que usa todo el plugin):
  margen ±0.05 cm, sangría ±0.05 cm, espacio antes/después ±0.5 pt, tamaño de fuente ±0.25 pt,
  interlineado en múltiplo ±0.02 y en puntos ±0.5 pt. En el PDF las cajas de texto traen el aire de la tipografía:
  TOLERANCIA_PDF (margen lateral ±0.15 cm, superior/inferior ±0.35 cm, sangría ±0.10 cm) solo se usa para AVISAR de
  discrepancias docx/PDF, nunca para un hallazgo.
"""
import re
import unicodedata

PT_IN = 72.0
CM_IN = 2.54
PT_CM = PT_IN / CM_IN            # 28.3465 pt por cm
TWIP_PT = 1 / 20.0
EMU_IN = 914400
EMU_PT = EMU_IN / PT_IN          # 12700
ALTURA_NATURAL = 1.15            # altura de línea natural / tamaño (aprox.) de las fuentes de texto habituales

TOLERANCIAS = {"margen": 0.05, "sangria": 0.05,          # cm
               "espacio": 0.5, "tamano": 0.25,           # pt
               "interlineado_multiplo": 0.02, "interlineado_pt": 0.5}
TOLERANCIA_PDF = {"lateral_cm": 0.15, "vertical_cm": 0.35, "sangria_cm": 0.10, "tamano_pt": 0.5}

# nombre (sin acentos, minúsculas) -> clave canónica
UNIDADES = {
    "cm": "cm", "cms": "cm", "centimetro": "cm", "centimetros": "cm", "centimeter": "cm", "centimeters": "cm", "centimetre": "cm", "centimetres": "cm",
    "mm": "mm", "milimetro": "mm", "milimetros": "mm", "millimeter": "mm", "millimeters": "mm",
    "in": "in", "inch": "in", "inches": "in", "pulgada": "in", "pulgadas": "in", "pulg": "in", '"': "in", "″": "in",
    "pt": "pt", "pts": "pt", "punto": "pt", "puntos": "pt", "point": "pt", "points": "pt",
    "twip": "twip", "twips": "twip", "emu": "emu", "emus": "emu",
    "mediopunto": "half", "mediospuntos": "half", "halfpoint": "half", "halfpoints": "half",
    "linea": "lineas", "lineas": "lineas", "line": "lineas", "lines": "lineas",
}


def sin_acentos(t):
    return "".join(c for c in unicodedata.normalize("NFD", str(t)) if unicodedata.category(c) != "Mn")


def unidad(nombre):
    """Clave canónica de una unidad escrita en español o inglés (cm, mm, in, pt, twip, emu, half, lineas) o None."""
    return UNIDADES.get(sin_acentos(nombre).strip().lower().rstrip("."))


def a_pt(valor, u):
    """Convierte `valor` en la unidad `u` a puntos."""
    u = unidad(u) or u
    f = {"pt": 1.0, "cm": PT_CM, "mm": PT_CM / 10, "in": PT_IN, "twip": TWIP_PT, "emu": 1 / EMU_PT, "half": 0.5}
    if u not in f:
        raise ValueError(f"unidad no convertible a puntos: {u!r}")
    return float(valor) * f[u]


def de_pt(pt, u):
    f = {"pt": 1.0, "cm": PT_CM, "mm": PT_CM / 10, "in": PT_IN, "twip": TWIP_PT, "emu": 1 / EMU_PT, "half": 0.5}
    return float(pt) / f[unidad(u) or u]


def todas(pt):
    """{cm, pt, in} de una longitud en puntos (redondeo de presentación: 0.01 cm, 0.01 pt, 0.001 in)."""
    if pt is None:
        return None
    return {"cm": round(pt / PT_CM, 3), "pt": round(pt, 2), "in": round(pt / PT_IN, 3)}


def texto_medida(pt):
    """«2.54 cm = 72 pt = 1 in» para mostrar."""
    if pt is None:
        return "—"
    t = todas(pt)
    return f"{t['cm']:g} cm = {t['pt']:g} pt = {t['in']:g} in"


def tolerancia(que, unidad_regla="cm", dada=None):
    """Tolerancia en PUNTOS de la medida `que` (margen, sangria, espacio, tamano). `dada` está en `unidad_regla`."""
    if dada is not None:
        return a_pt(dada, unidad_regla)
    base = TOLERANCIAS[que]
    return a_pt(base, "cm") if que in ("margen", "sangria") else base


def igual(a_pt_, b_pt_, tol_pt):
    """a == b dentro de la tolerancia (con un épsilon para que ±0.05 cm incluya el borde)."""
    return a_pt_ is not None and b_pt_ is not None and abs(a_pt_ - b_pt_) <= tol_pt + 1e-6


# ---------------------------------------------------------------- interlineado
NOMBRES_INTERLINEADO = {"sencillo": 1.0, "simple": 1.0, "single": 1.0, "1": 1.0,
                        "1.5": 1.5, "uno y medio": 1.5, "one and a half": 1.5,
                        "doble": 2.0, "double": 2.0, "2": 2.0}


def interlineado_de_xml(line, rule):
    """(w:line, w:lineRule) -> {'regla': 'auto', 'multiplo': 1.5} | {'regla': 'exact'|'atLeast', 'pt': 18.0}; None si no hay w:line."""
    if line is None:
        return None
    n = int(line)
    r = (rule or "auto")
    if r == "auto":
        return {"regla": "auto", "multiplo": round(n / 240.0, 3)}
    return {"regla": "exact" if r == "exact" else "atLeast", "pt": round(n / 20.0, 2)}


def texto_interlineado(il):
    if il is None:
        return "—"
    if il["regla"] == "auto":
        return f"auto ×{il['multiplo']:g} (w:line={round(il['multiplo'] * 240)})"
    return f"{'exacto' if il['regla'] == 'exact' else 'al menos'} {il['pt']:g} pt (w:line={round(il['pt'] * 20)})"


def interlineado_cumple(real, pedido, tam_pt, tol_multiplo=None, tol_pt=None):
    """Compara el interlineado efectivo `real` con el `pedido`.
    real:   salida de interlineado_de_xml.   pedido: {'modo': 'multiplo', 'valor': 1.5} | {'modo': 'exacto', 'pt': 18}.
    Devuelve (estado, nota): estado «igual» | «equivalente» | «distinto» | «indeterminado»."""
    tm = TOLERANCIAS["interlineado_multiplo"] if tol_multiplo is None else tol_multiplo
    tp = TOLERANCIAS["interlineado_pt"] if tol_pt is None else tol_pt
    if real is None:
        return "indeterminado", "sin w:line efectivo (Word usa 1 línea)"
    if real["regla"] == "atLeast":
        return "indeterminado", f"«al menos {real['pt']:g} pt»: la línea puede crecer; pide interlineado exacto o múltiplo para poder afirmarlo"
    if pedido["modo"] == "multiplo":
        m = pedido["valor"]
        if real["regla"] == "auto":
            return ("igual", "") if abs(real["multiplo"] - m) <= tm + 1e-9 else ("distinto", "")
        nominal = m * tam_pt
        if abs(real["pt"] - nominal) <= tp + 1e-6:
            return "equivalente", f"exacto {real['pt']:g} pt = {m:g} × {tam_pt:g} pt (nominal)"
        visual = nominal * ALTURA_NATURAL
        if abs(real["pt"] - visual) <= tp + 1e-6:
            return "equivalente", (f"exacto {real['pt']:g} pt ≈ {m:g} líneas automáticas de {tam_pt:g} pt en Word "
                                   f"(altura natural ≈ {ALTURA_NATURAL:g} × tamaño; aproximado)")
        return "distinto", f"exacto {real['pt']:g} pt; {m:g} líneas de {tam_pt:g} pt serían {nominal:g} pt"
    # pedido exacto N pt
    n = pedido["pt"]
    if real["regla"] == "exact":
        return ("igual", "") if abs(real["pt"] - n) <= tp + 1e-6 else ("distinto", "")
    m_pedido = n / tam_pt if tam_pt else 0
    if abs(real["multiplo"] * tam_pt - n) <= tp + 1e-6:
        return "equivalente", f"auto ×{real['multiplo']:g} de {tam_pt:g} pt = {real['multiplo'] * tam_pt:g} pt nominales"
    return "distinto", f"auto ×{real['multiplo']:g} (≈ {real['multiplo'] * tam_pt:g} pt nominales); se pidió {n:g} pt exactos"


def parsear_cantidad(texto, unidad_defecto=None):
    """«3 cm», «1.27cm», «0,5 pulgadas», «2.54 centímetros» -> (valor, unidad canónica) o None. Sin unidad: (valor, unidad_defecto o None)."""
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*([A-Za-zÁÉÍÓÚáéíóúñ\"″]+)?", str(texto))
    if not m:
        return None
    v = float(m.group(1).replace(",", "."))
    u = unidad(m.group(2)) if m.group(2) else None
    return v, (u or unidad_defecto)
