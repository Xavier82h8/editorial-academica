#!/usr/bin/env python3
"""`/perfilar`: la guía de formato de tu escuela (PDF o .docx) se convierte en reglas (.editorial.yaml + estructuras/<id>.yaml).

Uso:
  python scripts/editorial.py perfilar <guia.pdf|docx> [--modelo-portada <pdf|docx> --pagina N] [--out .editorial.yaml]
                              [--estructura-id ID] [--responder respuestas.yaml] [--json RUTA]
  python scripts/editorial.py perfilar --comparar <perfil.yaml> [--comparar-estructura <estructura.yaml>] <perfil-generado.yaml> [<estructura-generada.yaml>]

Qué hace (todo determinista, con patrones en español e inglés; nada sale de la máquina):
 1. Extrae el texto de la guía (PyMuPDF o pdftotext para PDF; python-docx para .docx, tablas incluidas) y quita encabezados repetidos.
 2. Saca con patrones: fuente y tamaño, márgenes, interlineado, alineación, sangría, jerarquía de títulos (niveles 1-5), paginación por
    partes (portada, preliminares, cuerpo; romanos/arábigos; posición), tablas y figuras (estilo IEEE/APA, posición del rótulo, tamaño),
    norma de citas, % de fuentes y antigüedad, mínimo de fuentes, título máximo de palabras, voz y tiempo verbal, resumen (palabras,
    palabras clave, sangría), elementos de la portada y la estructura de capítulos y subcapítulos numerados con su descripción
    (preguntas guía incluidas) -> `estructuras/<id>.yaml`.
 3. Cada valor lleva su origen en `origenes:` («guía p. N: «cita literal»»). Lo derivado (no dicho tal cual) dice «derivado de».
 4. Lo que el patrón no saca o es ambiguo, y las preferencias que ninguna guía dice (registro, persona, extensión por sección, densidad
    de citas, salida .docx + .pdf, fuentes a evitar), va a `preguntas:` con opciones; `--responder respuestas.yaml` las aplica
    (`P-<clave>: 2` por número de opción, por su texto, una lista o un texto libre).
 5. Con `--modelo-portada` mide la portada con modelo_formato (`editorial.py modelo medir`) y registra un `vinculante` tipo modelo.
 6. NUNCA sobrescribe un `.editorial.yaml` existente: escribe `.editorial.propuesto.yaml` y un diff legible
    (`.editorial.propuesto.diff`). Con `estructuras/<id>.yaml` igual (`<id>.propuesto.yaml`).

Salida: 0 (aunque queden preguntas); 2 error de uso o de entrada (guía inexistente, ilegible o sin texto).
"""
import argparse
import datetime as dt
import json
import pathlib
import re
import shutil
import subprocess
import sys
import unicodedata

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cli  # noqa: E402

import yaml  # noqa: E402

VERSION_FORMATO = 1
FUENTES_TIPO = r"Times New Roman|Arial|Calibri|Cambria|Garamond|Georgia|Helvetica|Verdana|Courier New|Book Antiqua|Palatino(?: Linotype)?|Tahoma"


# ---------------------------------------------------------------- utilidades
def sin_acentos(t):
    return "".join(c for c in unicodedata.normalize("NFD", t or "") if unicodedata.category(c) != "Mn")


def norm(t):
    """Minúsculas, sin acentos ni puntuación, espacios colapsados (para comparar nombres)."""
    return " ".join(re.sub(r"[^a-z0-9 ]+", " ", sin_acentos(t).lower()).split())


def plano(t):
    return " ".join((t or "").replace("\xa0", " ").split())


def num(s):
    """'2,54' -> 2.54 ; '12' -> 12 (entero si no tiene decimales)."""
    v = float(str(s).replace(",", "."))
    return int(v) if v == int(v) else v


def es_mayus(t):
    letras = [c for c in t if c.isalpha()]
    return bool(letras) and sum(c.isupper() for c in letras) / len(letras) >= 0.8


# ---------------------------------------------------------------- lectura de la guía
class Guia:
    """Texto de la guía por página. `paginas[i]` es el texto crudo de la página i+1 (líneas separadas por salto de línea);
    `lineas` son (página, texto) ya sin encabezados repetidos. Para .docx las «páginas» son los saltos de página (o una sola)."""

    def __init__(self, ruta):
        self.ruta = pathlib.Path(ruta)
        self.paginas = []
        self.tipo = ""
        self._leer()
        self.lineas = self._limpiar()
        self.plano_pag = {i + 1: plano(" ".join(l for p, l in self.lineas if p == i + 1)) for i in range(len(self.paginas))}
        self.todo = plano(" ".join(l for _, l in self.lineas))

    def _leer(self):
        r = self.ruta
        if not r.is_file():
            cli.error(f"no existe la guía: {r}")
        ext = r.suffix.lower()
        if ext == ".pdf":
            self.tipo = "pdf"
            self.paginas = self._leer_pdf(r)
        elif ext == ".docx":
            self.tipo = "docx"
            self.paginas = self._leer_docx(r)
        else:
            cli.error(f"guía no soportada ({ext}): usa .pdf o .docx")
        if not any(p.strip() for p in self.paginas):
            cli.error(f"la guía no tiene texto extraíble: {r} (¿es un PDF escaneado? conviértelo con OCR o pásalo a .docx)")

    @staticmethod
    def _leer_pdf(r):
        try:
            import fitz
            with fitz.open(str(r)) as d:
                return [p.get_text("text") for p in d]
        except ImportError:
            pass
        exe = shutil.which("pdftotext")
        if not exe:
            cli.error("para leer un PDF instala PyMuPDF (`pip install pymupdf`) o poppler (pdftotext)")
        out = subprocess.run([exe, "-layout", "-enc", "UTF-8", str(r), "-"], capture_output=True, text=True, encoding="utf-8", errors="replace")
        if out.returncode != 0:
            cli.error(f"pdftotext falló con {r}: {out.stderr.strip()[:200]}")
        return out.stdout.split("\f")

    @staticmethod
    def _leer_docx(r):
        import docx
        from docx.oxml.ns import qn
        try:
            d = docx.Document(str(r))
        except Exception as ex:  # noqa: BLE001
            cli.error(f"no se pudo abrir {r}: {type(ex).__name__}: {ex}")
        paginas, actual = [], []

        def cierra():
            nonlocal actual
            paginas.append("\n".join(actual))
            actual = []

        for el in d.element.body:
            if el.tag == qn("w:p"):
                texto = "".join(t.text or "" for t in el.iter(qn("w:t")))
                salta = any(b.get(qn("w:type")) == "page" for b in el.iter(qn("w:br"))) or next(el.iter(qn("w:lastRenderedPageBreak")), None) is not None
                if salta and actual:
                    cierra()
                if texto.strip():
                    actual.append(texto.strip())
            elif el.tag == qn("w:tbl"):
                for fila in el.iter(qn("w:tr")):
                    celdas = []
                    for c in fila.iter(qn("w:tc")):
                        celdas.append(plano("".join(t.text or "" for t in c.iter(qn("w:t")))))
                    actual.append(" ".join(x for x in celdas if x))
        cierra()
        return [p for p in paginas if p.strip()] or [""]

    def _limpiar(self):
        """Quita encabezados y pies que se repiten en varias páginas."""
        cuenta = {}
        for p in self.paginas:
            for l in {plano(x) for x in p.splitlines() if x.strip()}:
                cuenta[l] = cuenta.get(l, 0) + 1
        n = len(self.paginas)
        repetidas = {l for l, c in cuenta.items() if n >= 3 and c >= max(3, int(0.4 * n)) and not re.match(r"^\d{1,2}\.", l)}
        out = []
        for i, p in enumerate(self.paginas, 1):
            for x in p.splitlines():
                x = plano(x)
                if not x or x in repetidas or re.fullmatch(r"\d{1,3}", x):
                    continue
                out.append((i, x))
        return out

    def donde(self, pagina):
        return f"p. {pagina}" if len(self.paginas) > 1 else "apartado único"


def cita_literal(texto, ini, fin, max_len=190):
    """Fragmento literal alrededor de [ini, fin): unos 40 caracteres antes y 50 después (ajustados a palabra y a límite de oración o
    de viñeta); si el propio hallazgo es más largo que `max_len`, se abrevia con «[…]» en medio."""
    a = max(texto.rfind(". ", 0, ini), texto.rfind("• ", 0, ini))
    a = 0 if a < 0 else a + 2
    if ini - a > 40:
        a = texto.find(" ", ini - 40, ini)
        a = ini if a < 0 else a + 1
    cands = [x for x in (texto.find(". ", fin), texto.find(" • ", fin)) if x >= 0]
    b = min(cands) + 1 if cands else len(texto)
    if b - fin > 50:
        b = texto.find(" ", fin + 50)
        b = len(texto) if b < 0 else b
    frag = plano(texto[a:b]).strip(" •")
    if len(frag) > max_len:
        frag = frag[:max_len - 70].rsplit(" ", 1)[0] + " […] " + frag[-60:].split(" ", 1)[-1]
    return frag


class Datos:
    """Valores extraídos: clave con puntos -> (valor, origen). `derivado` marca lo que no está dicho tal cual."""

    def __init__(self):
        self.v = {}

    def poner(self, clave, valor, origen):
        if clave not in self.v:
            self.v[clave] = (valor, origen)

    def tiene(self, clave):
        return clave in self.v

    def valor(self, clave, defecto=None):
        return self.v[clave][0] if clave in self.v else defecto


def buscar(g, rx, flags=re.I, pagina=None):
    """(match, página, texto de la página) del primer patrón hallado, en orden de páginas."""
    for i in sorted(g.plano_pag):
        if pagina and i != pagina:
            continue
        t = g.plano_pag[i]
        m = re.search(rx, t, flags)
        if m:
            return m, i, t
    return None, None, None


def origen(g, m, pag, t):
    return f"guía {g.donde(pag)}: «{cita_literal(t, m.start(), m.end())}»"


# ---------------------------------------------------------------- extractores de formato
def extraer_formato(g, d):
    # idioma
    pal = re.findall(r"[a-záéíóúñ]+", g.todo.lower())
    es_n = sum(w in ("el", "la", "los", "las", "de", "del", "que", "con", "para", "una", "se", "en", "y") for w in pal)
    en_n = sum(w in ("the", "of", "and", "with", "that", "for", "is", "are", "in", "to", "be") for w in pal)
    d.poner("idioma", "es" if es_n >= en_n else "en", f"derivado de: idioma predominante del texto de la guía ({'español' if es_n >= en_n else 'inglés'})")

    # fuente y tamaño
    m, p, t = buscar(g, rf"(?P<n>{FUENTES_TIPO})\s*(?:a|de|en|,|:|-|at)?\s*(?P<pt>\d{{1,2}}(?:[.,]\d)?)\s*(?:puntos?|pts?\b\.?|points?|-?point)")
    if not m:
        m, p, t = buscar(g, rf"(?P<pt>\d{{1,2}}(?:[.,]\d)?)\s*[- ]?(?:puntos?|pts?\b\.?|points?|-?point)\s*(?:de\s+|font\s+)?(?:la\s+)?(?:fuente\s+|tipograf[ií]a\s+)?(?P<n>{FUENTES_TIPO})")
    if m:
        o = origen(g, m, p, t)
        d.poner("formato.fuente.nombre", m.group("n"), o)
        d.poner("formato.fuente.pt", num(m.group("pt")), o)

    # márgenes
    m, p, t = buscar(g, r"m[aá]rgenes?\b[^.]{0,120}?(?P<v>\d+(?:[.,]\d+)?)\s*(?P<u>cm|cent[ií]metros|mm|in\b|pulgadas?|inch(?:es)?)")
    if not m:
        m, p, t = buscar(g, r"margins?\b[^.]{0,120}?(?P<v>\d+(?:\.\d+)?)\s*(?P<u>inch(?:es)?|in\b|cm|mm)")
    if m:
        v, u = num(m.group("v")), sin_acentos(m.group("u")).lower()
        cm = v * (0.1 if u == "mm" else 1) if u.startswith(("c", "mm")) else v * 2.54
        d.poner("reglas_guia.margenes_cm", round(cm, 2), origen(g, m, p, t))

    # interlineado
    m, p, t = buscar(g, r"interlineado\b[^.\d]{0,60}?(?P<v>\d(?:[.,]\d+)?)\s*(?:l[ií]neas?)?")
    v = None
    if m:
        v = num(m.group("v"))
    else:
        m, p, t = buscar(g, r"interlineado\s+(?P<t>doble|sencillo|simple)")
        if m:
            v = {"doble": 2, "sencillo": 1, "simple": 1}[m.group("t").lower()]
        else:
            m, p, t = buscar(g, r"(?:line spacing|spacing)[^.]{0,40}?(?P<t>1\.5|double|single)|(?P<t2>double|single)[- ]spaced")
            if m:
                k = (m.group("t") or m.group("t2")).lower()
                v = 1.5 if k == "1.5" else 2 if k == "double" else 1
    if m and v is not None:
        d.poner("formato.interlineado", v, origen(g, m, p, t))

    # alineación
    m, p, t = buscar(g, r"(?:alineaci[oó]n|alignment)[^.]{0,60}?\b(?P<a>justificad[ao]s?|justified|izquierda|left)\b|\b(?P<b>justificad[ao]s?|justified|left[- ]aligned)\b(?:\s+(?:en|in)\s+(?:p[aá]rrafos|paragraphs))?")
    if m:
        a = sin_acentos((m.group("a") or m.group("b") or "")).lower()
        d.poner("formato.alineacion", "justificada" if a.startswith(("justif",)) else "izquierda", origen(g, m, p, t))

    # sangría de párrafo
    m, p, t = buscar(g, r"sangr[ií]a\s+de\s+primera\s+l[ií]nea\s+de\s+(?P<v>\d+(?:[.,]\d+)?)\s*(?P<u>cm|pulgadas?|in\b|mm)|first[- ]line\s+indent(?:ation)?\s+(?:of\s+)?(?P<v2>\d+(?:\.\d+)?)\s*(?P<u2>cm|inch(?:es)?|in\b|mm)")
    if m:
        v = num(m.group("v") or m.group("v2"))
        u = sin_acentos((m.group("u") or m.group("u2"))).lower()
        d.poner("reglas_guia.sangria_primera_linea_cm", round(v * (0.1 if u == "mm" else 1 if u.startswith("c") else 2.54), 2), origen(g, m, p, t))

    # voz y tiempo verbal
    m, p, t = buscar(g, r"impersonal|tercera persona|voz pasiva refleja|third person|impersonal voice")
    if m:
        o = origen(g, m, p, t)
        d.poner("voz", "impersonal", o)
        d.poner("formato.voz", "impersonal", o)
    else:
        m, p, t = buscar(g, r"primera persona|first person")
        if m:
            d.poner("reglas_guia.voz", "primera_persona", origen(g, m, p, t))
    m, p, t = buscar(g, r"tiempo\s+(?:verbal\s+)?(?P<a>futuro|presente|pasado)(?:\s+o\s+(?P<b>futuro|presente|pasado))?|(?P<c>future|present|past)\s+tense")
    if m:
        ts = [x.lower() for x in (m.group("a"), m.group("b"), m.group("c")) if x]
        d.poner("tiempo_verbal", "_".join(sorted(ts, key=["futuro", "presente", "pasado", "future", "present", "past"].index)) or ts[0], origen(g, m, p, t))

    # título: máximo de palabras
    for i in sorted(g.plano_pag):
        t = g.plano_pag[i]
        for m in re.finditer(r"(?:m[aá]ximo|no\s+(?:m[aá]s\s+de|(?:debe\s+|deber[aá]\s+)?exceda\w*|(?:debe\s+|deber[aá]\s+)?exceder)|sin\s+exceder|hasta|up to|no more than|maximum(?: of)?)\s*(?:de\s+)?(?:(?P<a>\d{1,2})\s*(?:a|-|–|to)\s*)?(?P<b>\d{1,2})\s*(?:palabras|words)", t, re.I):
            if re.search(r"t[ií]tulo|title", t[max(0, m.start() - 260):m.start()], re.I):
                d.poner("formato.titulo_max_palabras", int(m.group("b")), origen(g, m, i, t))
                break
        if d.tiene("formato.titulo_max_palabras"):
            break

    # fuentes: porcentaje y antigüedad
    m, p, t = buscar(g, r"(?:al menos|m[ií]nimo|por lo menos|at least|no menos de)\s+(?:el\s+)?(?P<p>\d{1,3})\s*%(?P<mid>[^.]{0,260}?)(?:[uú]ltimos|[uú]ltimo|past|last)\s+(?P<a>\d{1,2})\s*(?:a[ñn]os|years)")
    if m:
        o = origen(g, m, p, t)
        arb = bool(re.search(r"arbitrad|peer[- ]review|indexad", m.group("mid"), re.I))
        d.poner("anios_fuentes", int(m.group("a")), o)
        d.poner("porcentaje_recientes", int(m.group("p")), o)
        d.poner("formato.fuentes_recientes.anios", int(m.group("a")), o)
        d.poner("formato.fuentes_recientes.porcentaje", int(m.group("p")), o)
        d.poner("formato.fuentes_recientes.arbitradas", arb, o)
        if arb:
            d.poner("fuentes.porcentaje_arbitradas", int(m.group("p")), o)
            d.poner("fuentes.minimo_nivel", "B", "derivado de: la guía pide literatura arbitrada (artículos, actas, libros especializados o normas = niveles A y B) · " + o)
    m, p, t = buscar(g, r"(?:al menos|m[ií]nimo de|at least)\s+(?P<n>\d{1,3})\s+(?:art[ií]culos|fuentes|referencias|trabajos|tesis|sources|articles|papers)")
    if m:
        d.poner("minimo_fuentes", int(m.group("n")), origen(g, m, p, t))

    # resumen
    i_res = None
    for i in sorted(g.plano_pag):
        mm = re.search(r"(?:res[uú]men|abstract)\b[^•]{0,700}", g.plano_pag[i], re.I)
        if mm and re.search(r"\d{2,3}\s*(?:a|-|–|y|to)\s*\d{2,3}\s*(?:palabras|words)", mm.group(0), re.I):
            i_res, seg, t = i, mm, g.plano_pag[i]
            break
    if i_res:
        s = seg.group(0)
        mp = re.search(r"(?P<a>\d{2,3})\s*(?:a|-|–|y|to)\s*(?P<b>\d{2,3})\s*(?:palabras|words)", s, re.I)
        o = f"guía {g.donde(i_res)}: «{cita_literal(t, seg.start() + mp.start(), seg.start() + mp.end())}»"
        d.poner("formato.resumen.palabras", [int(mp.group("a")), int(mp.group("b"))], o)
        if re.search(r"un solo p[aá]rrafo|one paragraph|single paragraph|un p[aá]rrafo", s, re.I):
            mm2 = re.search(r"un solo p[aá]rrafo|one paragraph|single paragraph|un p[aá]rrafo", s, re.I)
            d.poner("formato.resumen.un_parrafo", True, f"guía {g.donde(i_res)}: «{cita_literal(t, seg.start() + mm2.start(), seg.start() + mm2.end())}»")
        ms = re.search(r"sin\s+sangr[ií]a|no indent|not indent|without indent|con\s+sangr[ií]a|indented", s, re.I)
        if ms:
            d.poner("formato.resumen.sangria", not re.match(r"sin|no|not|without", ms.group(0), re.I), f"guía {g.donde(i_res)}: «{cita_literal(t, seg.start() + ms.start(), seg.start() + ms.end())}»")
        mk = re.search(r"(?P<a>\d)\s*(?:a|-|–|to)\s*(?P<b>\d)\s*(?:palabras clave|keywords|key words)", s, re.I)
        if mk:
            d.poner("formato.resumen.palabras_clave", [int(mk.group("a")), int(mk.group("b"))], f"guía {g.donde(i_res)}: «{cita_literal(t, seg.start() + mk.start(), seg.start() + mk.end())}»")

    # rótulos de tablas y figuras
    for i in sorted(g.plano_pag):
        t = g.plano_pag[i]
        for m in re.finditer(r"(?P<a>\d{1,2})\s*(?:-|–|a|to)\s*(?P<b>\d{1,2})\s*(?:pt|puntos|points)", t, re.I):
            if re.search(r"tablas?|figuras?|tables?|figures?|r[oó]tulos?|captions?", t[max(0, m.start() - 220):m.start()], re.I):
                d.poner("formato.rotulos_pt", [int(m.group("a")), int(m.group("b"))], origen(g, m, i, t))
                break
    m, p, t = buscar(g, r"(?:tablas?|tables?|figuras?|figures?)\s*\((?:estilo\s+|style\s+)?(?P<e>IEEE|APA)\b")
    if m:
        d.poner("tablas_figuras", m.group("e").lower(), origen(g, m, p, t))
        for nombre, rx in (("tablas", r"(?:tablas?|tables?)\s*\((?:estilo\s+|style\s+)?(?:IEEE|APA)\)(?P<s>.{0,260})"), ("figuras", r"(?:figuras?|figures?)\s*\((?:estilo\s+|style\s+)?(?:IEEE|APA)\)(?P<s>.{0,260})")):
            mm = re.search(rx, t, re.I)
            if mm:
                s = sin_acentos(mm.group("s")).lower()
                s = re.split(r"\bfiguras?\b|\bfigures?\b|\bcitas\b", s)[0] if nombre == "tablas" else re.split(r"\bcitas\b|\btiempo\b", s)[0]
                info = {}
                if re.search(r"superior|arriba|above|top", s):
                    info["rotulo"] = "superior"
                elif re.search(r"inferior|abajo|below|bottom", s):
                    info["rotulo"] = "inferior"
                if "mayuscula" in s or "uppercase" in s:
                    info["mayusculas"] = True
                if "romana" in s or "roman" in s:
                    info["numeracion"] = "romana"
                elif "arabiga" in s or "arabic" in s:
                    info["numeracion"] = "arabiga"
                if re.search(r"tipo oracion|sentence case", s):
                    info["tipo_texto"] = "oracion"
                if info:
                    d.poner(f"reglas_guia.{nombre}", info, origen(g, mm, p, t))

    # citas: norma
    m, p, t = buscar(g, r"(?:citas?\s+y\s+referencias|citations?\s+and\s+references|referencias\s+bibliogr[aá]ficas|referencing)\W[^•]{0,160}?\b(?P<n>APA|IEEE)\b")
    if not m:
        m, p, t = buscar(g, r"\b(?P<n>APA|IEEE)\b[^•]{0,70}?(?:redacci[oó]n y citaci[oó]n|citaci[oó]n|citas)")
    if not m:
        m, p, t = buscar(g, r"(?:citas?|citaci[oó]n|citations?)[^.•]{0,160}?\b(?P<n>APA|IEEE)\b")
    if m:
        d.poner("perfil", "apa7" if m.group("n").upper() == "APA" else "ieee", origen(g, m, p, t))
        m7, p7, t7 = buscar(g, r"APA\s*\(?\s*(?:7|siete)|7\.?\s*[ªa]?\.?\s*edici[oó]n|APA\s*7")
        if m7 and m.group("n").upper() == "APA":
            d.poner("reglas_guia.version_apa", 7, origen(g, m7, p7, t7))

    # paginación
    paginacion_extraer(g, d)
    # jerarquía de títulos
    jerarquia_extraer(g, d)


def paginacion_extraer(g, d):
    m, p, t = buscar(g, r"portada\s*:?\s*sin n[uú]mero|cover(?: page)?\s*:?\s*no (?:page )?number|portada[^.•]{0,40}sin n[uú]mero")
    if m:
        o = origen(g, m, p, t)
        d.poner("formato.paginacion.portada", "sin_numero", o)
        d.poner("portada_numero", False, o)
    m, p, t = buscar(g, r"(?:preliminares?|front matter|resumen e [ií]ndices?)[^•]{0,140}?(?P<r>n[uú]meros? romanos?|roman numerals?)")
    if m:
        d.poner("formato.paginacion.preliminares", "romanos", origen(g, m, p, t))
    m, p, t = buscar(g, r"(?:cuerpo|body|cap[ií]tulo 1)[^•]{0,200}?(?P<r>n[uú]meros? ar[aá]bigos?|arabic numerals?)")
    if m:
        d.poner("formato.paginacion.cuerpo", "arabigos", origen(g, m, p, t))
    m, p, t = buscar(g, r"esquina\s+(?:superior|inferior)\s+(?:derecha|izquierda)|top[- ](?:right|center)|upper[- ]right|encabezado[^.]{0,25}derecha|pie\s+de\s+p[aá]gina[^.]{0,30}(?:derecha|centr\w+)|bottom[- ](?:right|center)|(?:centrad[oa]|centro)\s+(?:en\s+)?(?:el\s+)?pie")
    if m:
        s = sin_acentos(m.group(0)).lower()
        pos = "encabezado_derecha" if ("superior" in s or "top" in s or "upper" in s or "encabezado" in s) else ("pie_derecha" if ("derecha" in s or "right" in s) else "pie_centro")
        d.poner("formato.paginacion.posicion", pos, origen(g, m, p, t))


def jerarquia_extraer(g, d):
    niveles = {}
    for i in sorted(g.plano_pag):
        t = g.plano_pag[i]
        for m in re.finditer(r"(?:Nivel|Level)\s*(?P<n>[1-5])\s*[:.]\s*(?P<d>.+?)(?=(?:Nivel|Level)\s*[1-5]\s*[:.]|•|\.\s|$)", t):
            n = int(m.group("n"))
            if n in niveles:
                continue
            s = sin_acentos(m.group("d")).lower()
            r = {}
            if re.search(r"centrad|center", s):
                r["alineacion"] = "centrado"
            elif re.search(r"izquierda|left|flush", s):
                r["alineacion"] = "izquierda"
            if re.search(r"mayuscula|uppercase|all caps", s):
                r["mayusculas"] = True
            if re.search(r"negrita|bold", s):
                r["negritas"] = True
            if re.search(r"cursiva|italic", s):
                r["cursivas"] = True
            if re.search(r"tipo oracion|sentence case", s):
                r["tipo_texto"] = "oracion"
            elif re.search(r"title case|tipo titulo", s):
                r["tipo_texto"] = "titulo"
            if re.search(r"punto final|ending with a period|with a period", s):
                r["punto_final"] = True
            ms = re.search(r"sangria\s*(?P<v>\d+(?:[.,]\d+)?)\s*cm|indent\w*\s*(?P<v2>\d+(?:\.\d+)?)\s*(?:cm|in)", s)
            if ms:
                r["sangria_cm"] = num(ms.group("v") or ms.group("v2"))
            if re.search(r"pagina nueva|new page", s):
                r["pagina_nueva"] = True
            niveles[n] = (r, origen(g, m, i, t))
    if niveles:
        d.poner("reglas_guia.jerarquia_titulos", {f"nivel{n}": r for n, (r, _) in sorted(niveles.items())}, " · ".join(o for n, (_, o) in sorted(niveles.items())).replace("» · guía p. ", "» · p. "))
        r1, o1 = niveles.get(1, ({}, ""))
        if r1:
            d.poner("formato.nivel1.mayusculas", bool(r1.get("mayusculas")), o1)
            if r1.get("pagina_nueva"):
                d.poner("formato.capitulo_pagina_nueva", True, o1)
    m, p, t = buscar(g, r"(?:cada\s+)?cap[ií]tulo\s+de\s+nivel\s+1\s+debe\s+iniciar\s+en\s+una\s+p[aá]gina\s+nueva|each (?:level 1|chapter)[^.]{0,40}(?:begin|start)[^.]{0,20}new page|inicia\s+en\s+p[aá]gina\s+nueva")
    if m:
        d.poner("formato.capitulo_pagina_nueva", True, origen(g, m, p, t))


# ---------------------------------------------------------------- portada
CAMPOS_PORTADA = [  # (patrón en la frase de la guía, campo)
    (r"instituci[oó]n|institution|university|universidad", {"nombre": "institución"}),
    (r"departamento|department|facultad|escuela", {"nombre": "departamento"}),
    (r"t[ií]tulo|title", {"nombre": "título del proyecto"}),
    (r"leyenda|legend|caption", {"nombre": "leyenda oficial del protocolo"}),
    (r"integrantes|autor(?:es)?|students?|members|alumnos", {"nombre": "integrantes", "patron": r"(?i:^\s*integrantes?\b)"}),
    (r"docente|asesor|profesor|advisor|supervisor|instructor", {"nombre": "docente", "patron": r"(?i:^\s*(?:docente|profesor|asesor|advisor)\b)"}),
    (r"lugar|ciudad|place|city", {"nombre": "lugar"}),
]


def lineas_institucion(g):
    """Líneas en MAYÚSCULAS del encabezado de la primera página (hasta el título de la guía): nombre de la institución."""
    nom = []
    for pag, l in g.lineas:
        if pag != 1:
            break
        if re.search(r"gu[ií]a|estructura|lineamientos|protocolo|guide|manual|template|plantilla|formato|formatting", l, re.I):
            break
        if es_mayus(l) and len(l.split()) >= 2:
            nom.append(l)
    return nom


def portada_extraer(g, d):
    m, p, t = buscar(g, r"portada(?:\s+oficial)?\b[^•]{0,40}?(?:\([^)]*\))?\s*:\s*(?:debe|deber[aá]|must|should)\s+(?:incluir|llevar|contener|include)(?P<s>[^•]{0,700})")
    if not m:
        m, p, t = buscar(g, r"(?:cover page|title page|portada)[^•]{0,60}(?:must|should|debe)\s+(?:include|incluir)(?P<s>[^•]{0,700})")
    if not m:
        return
    s = m.group("s")
    o = origen(g, m, p, t)
    pos = []
    for rx, campo in CAMPOS_PORTADA:
        mm = re.search(rx, s, re.I)
        if mm:
            pos.append((mm.start(), dict(campo)))
    pos.sort(key=lambda x: x[0])
    campos = []
    inst = lineas_institucion(g)
    dep = next((l for _, l in g.lineas if _ == 1 and re.match(r"(?i)departamento\b", l)), None)
    for _, c in pos:
        if c["nombre"] == "institución":
            if inst:
                c["nombre"], c["literal"] = f"institución ({inst[0]})", inst[0]
            else:
                c["patron"] = r"(?i:^\s*(?:universidad|instituto|tecnol[oó]gico|facultad|escuela|college|university|institute)\b)"
            campos.append(c)
            if len(inst) > 1 and re.match(r"(?i)instituto|facultad|escuela|centro|school|institute", inst[1]):
                campos.append({"nombre": f"instituto ({inst[1]})", "literal": inst[1]})
            continue
        if c["nombre"] == "departamento":
            if dep:
                resto = re.sub(r"(?i)^departamento\s+de\s+", "", dep)
                c["nombre"] = f"departamento ({resto})"
                c["literal"] = dep
            else:
                c["patron"] = r"(?i:^\s*(?:departamento|facultad|escuela|divisi[oó]n|department|school)\b)"
            campos.append(c)
            continue
        if c["nombre"] == "leyenda oficial del protocolo":
            ml = re.search(r"leyenda\s*['\"“‘«]([^'\"”’»]+)['\"”’»]", s, re.I)
            if ml:
                c["literal"] = plano(ml.group(1))
            else:
                c["patron"] = r"(?i:^\s*(?:protocolo|tesis|tesina|proyecto|informe|thesis|report)\b)"
        if c["nombre"] == "lugar":
            ml = re.search(r"(?:lugar|ciudad)\s*\(([^)]+)\)", s, re.I)
            if ml:
                c["nombre"] = f"lugar ({plano(ml.group(1))})"
                c["patron"] = "(?i:^\\s*" + r",\s*".join(re.escape(x.strip().lower()) for x in ml.group(1).split(",")) + ")"
        if c["nombre"] == "lugar" and "patron" not in c:
            c["patron"] = r"(?i:^\s*[A-ZÁÉÍÓÚÑ][\wáéíóúñ ]+,\s*[A-ZÁÉÍÓÚÑ])"
        campos.append(c)
    if campos:
        d.poner("formato.portada.campos", campos, o)
    mf = re.search(r"(?:fecha|date)\s*\((?P<f>[^)]+)\)", s, re.I)
    if mf:
        f = sin_acentos(mf.group("f")).lower()
        if ("mes" in f and "ano" in f) or ("month" in f and "year" in f):
            d.poner("formato.portada.fecha", "mes_anio", f"guía {g.donde(p)}: «{plano(mf.group(0))}»")
    if re.search(r"n[uú]mero de control|student (?:id|number)|control number", s, re.I):
        d.poner("formato.portada.numero_control", True, o)
    ml = re.search(r"logotipos?[^()]{0,40}\((?P<l>[^)]+)\)|logos?[^()]{0,40}\((?P<l2>[^)]+)\)", s, re.I)
    if ml:
        logos = [x.strip() for x in re.split(r",|\sy\s|\sand\s", ml.group("l") or ml.group("l2")) if x.strip()]
        d.poner("formato.portada.logos", logos, f"guía {g.donde(p)}: «{plano(ml.group(0))}»")


# ---------------------------------------------------------------- estructura de capítulos
STOP_BLOQUE = re.compile(r"^(?:GU[IÍ]A R[AÁ]PIDA|EJEMPLOS?\b|EJEMPLO DE|TABLA\s+[IVX]+\b|SECCI[OÓ]N\s+[IVX]+\b|SECTION\s+[IVX]+\b|QUICK GUIDE|EXAMPLE)", re.I)
CAP_RX = re.compile(r"^(?:(?:cap[ií]tulo|chapter)\s+)?(?P<n>\d{1,2})\s*[.)]?\s+(?P<t>\S.*)$", re.I)
SUB_RX = re.compile(r"^(?:[•\-–]\s*)?(?P<c>\d{1,2})\.(?P<s>\d{1,2})\.?\s+(?P<t>[A-ZÁÉÍÓÚÑ¿].*)$")
SUBSUB_RX = re.compile(r"^(?:[•\-–]\s*)?(?P<c>\d{1,2})\.(?P<s>\d{1,2})\.(?P<ss>\d{1,2})\.?\s+(?P<t>[A-ZÁÉÍÓÚÑ¿].*)$")
PARTES_NO = re.compile(r"^(?:\d+\s*(?:cm|mm|pt|pulgadas|l[ií]neas|%|puntos|a[ñn]os)\b)", re.I)


def acronimos(g):
    s = set()
    for _, l in g.lineas:
        if not es_mayus(l):
            for w in re.findall(r"\b[A-ZÁÉÍÓÚÑ]{2,}(?:/[A-Z]{2,})*\b", l):
                for x in w.split("/"):
                    s.add(x)
    return s


def a_oracion(t, acr):
    """Convierte un encabezado (MAYÚSCULAS o Title Case) a tipo oración conservando siglas."""
    base = re.sub(r"\s+", " ", t).strip(" .:")
    todo_mayus = es_mayus(base)
    out = []
    for i, w in enumerate(base.split(" ")):
        core = re.sub(r"[^\wÁÉÍÓÚÑáéíóúñ]", "", w)
        if core in acr and len(core) >= 2 or any(c.isdigit() for c in core) or re.fullmatch(r"[A-Z]{2,}", core) and not todo_mayus:
            out.append(w)
        elif i == 0:
            out.append(w[:1].upper() + w[1:].lower() if todo_mayus or w[1:].islower() or w[1:].isupper() else w)
        else:
            out.append(w.lower() if (todo_mayus or w[:1].isupper()) else w)
    return " ".join(out)


def quitar_parentesis(t):
    """(título sin paréntesis finales, [texto de los paréntesis])."""
    ext = re.findall(r"\(([^)]*)\)", t)
    base = re.sub(r"\s*\([^)]*\)\s*", " ", t).strip()
    # «Pregunta(s)» es parte del nombre
    if re.search(r"\w\(s\)", t):
        base, ext = t, []
    return base, ext


def aliases(nombre, original, extra=()):
    vistos, out = set(), []
    for x in (nombre, original, *extra):
        n = norm(x)
        if n and n not in vistos:
            vistos.add(n)
            out.append(n)
    return out


def recorta(t, n):
    t = plano(t)
    return t if len(t) <= n else t[:n].rsplit(" ", 1)[0] + " […]"


def primeras_oraciones(texto, max_chars=300):
    t = plano(texto)
    if len(t) <= max_chars:
        return t
    cortes = [m.end() for m in re.finditer(r"[.;:]\s", t) if m.end() <= max_chars]
    return t[:cortes[-1]].strip() if cortes else t[:max_chars].rsplit(" ", 1)[0] + "…"


def estructura_extraer(g, estructura_id):
    """Estructura de la guía: {id, nombre, front_matter, secciones[...]} desde las líneas numeradas, o None si no hay capítulos."""
    acr = acronimos(g)
    L = g.lineas
    secciones, front = [], []
    cap_actual = None
    # 1) cabeceras numeradas
    marcas = []  # (índice de línea, nivel, número, título, es_vineta)
    ultimo_cap = 0
    for k, (pag, l) in enumerate(L):
        if STOP_BLOQUE.match(l):
            marcas.append((k, 0, None, l, False))
            continue
        ms = SUBSUB_RX.match(l)
        if ms and int(ms.group("c")) == ultimo_cap and not PARTES_NO.match(ms.group("t")):
            marcas.append((k, 3, f"{ms.group('c')}.{ms.group('s')}.{ms.group('ss')}", ms.group("t"), l.startswith(("•", "-", "–"))))
            continue
        ms = SUB_RX.match(l)
        if ms and int(ms.group("c")) == ultimo_cap and not PARTES_NO.match(ms.group("t")):
            marcas.append((k, 2, f"{ms.group('c')}.{ms.group('s')}", ms.group("t"), l.startswith(("•", "-", "–"))))
            continue
        mc = CAP_RX.match(l)
        if mc and 1 <= int(mc.group("n")) <= 40 and len(l.split()) <= 14 and (es_mayus(mc.group("t")) or re.match(r"(?i)cap[ií]tulo|chapter", l)) \
                and int(mc.group("n")) in (ultimo_cap + 1, ultimo_cap) and not re.search(r"[.;]$", mc.group("t").strip()) and not PARTES_NO.match(mc.group("t")):
            if int(mc.group("n")) == ultimo_cap + 1:
                ultimo_cap += 1
                marcas.append((k, 1, str(ultimo_cap), mc.group("t"), False))
    caps = [m for m in marcas if m[1] == 1]
    if not caps:
        return None
    # 2) descripción: líneas hasta la siguiente marca o bloque ilustrativo
    def cuerpo_de(k0, k1):
        return [L[j][1] for j in range(k0 + 1, k1)]

    for idx, mk in enumerate(marcas):
        k, nivel, numero, titulo, vineta = mk
        if nivel == 0:
            continue
        k1 = marcas[idx + 1][0] if idx + 1 < len(marcas) else len(L)
        lineas = cuerpo_de(k, k1)
        pag = L[k][0]
        orig_titulo = titulo
        desc = ""
        if vineta and ":" in titulo:
            titulo, desc0 = titulo.split(":", 1)
            lineas = [desc0.strip()] + lineas
        titulo_limpio, parent = quitar_parentesis(titulo.strip().rstrip(":"))
        desc = primeras_oraciones(" ".join(lineas))
        nombre = a_oracion(titulo_limpio, acr)
        original = re.sub(r"\s+", " ", orig_titulo).strip(" .:")
        sec = {"nombre": nombre, "alias": aliases(nombre, titulo_limpio, [p for p in parent]), "obligatoria": True, "nivel": nivel, "numero": numero,
               "proposito": desc, "preguntas": [], "origen": f"guía p. {pag}: «{numero}. {recorta(original, 90)}»"}
        secciones.append(sec)
    # 3) preguntas guía por capítulo (GUÍA RÁPIDA) -> capítulo anterior
    cap_idx = None
    for idx, mk in enumerate(marcas):
        k, nivel, numero, titulo, _ = mk
        if nivel == 1:
            cap_idx = idx
        if nivel == 0 and cap_idx is not None:
            k1 = marcas[idx + 1][0] if idx + 1 < len(marcas) else len(L)
            bloque = " ".join(L[j][1] for j in range(k, k1))
            mp = re.search(r"(?:preguntas gu[ií]a|guiding questions)\s*:\s*(?P<q>.+?)(?=ejemplo|example|$)", bloque, re.I)
            if mp:
                qs = [q.strip() + "?" for q in re.split(r"\?", mp.group("q")) if len(q.strip()) > 3]
                for s in secciones:
                    if s["nivel"] == 1 and s["numero"] == marcas[cap_idx][2]:
                        s["preguntas"] = qs
    # 4) preliminares: viñetas «Resumen / Abstract (página i): …»
    prelim = []
    ini = next((j for j, (_, l) in enumerate(L) if re.match(r"(?i)(?:p[aá]ginas?\s+preliminares|front matter|preliminary pages)", l) and len(l) < 90), None)
    if ini is not None:
        fin = next((mk[0] for mk in caps if mk[0] > ini), len(L))
        bloque = []
        for j in range(ini + 1, fin):
            l = L[j][1]
            if l.startswith("•") or not bloque:
                bloque.append([L[j][0], l.lstrip("• ").strip()])
            else:
                bloque[-1][1] += " " + l
        for pag, txt in bloque:
            mm = re.match(r"(?P<t>[^:]{2,90}?):\s*(?P<d>.+)$", txt)
            if not mm:
                continue
            titulo, desc = mm.group("t"), mm.group("d")
            base, parent = quitar_parentesis(titulo)
            if re.match(r"(?i)portada", base):
                front.append(f"{base.lower()} ({'; '.join(parent)})" if parent else base.lower())
                continue
            partes = [x.strip() for x in re.split(r"\s+e\s+(?=[ÍIí]ndice)", base)] if re.search(r"[ÍIí]ndice.+\se\s+[ÍIí]ndice", base) else [base]
            for part in partes:
                nombre_p = a_oracion(re.split(r"\s*/\s*", part)[0], acr)
                alias_extra = [x for x in re.split(r"\s*/\s*", part)[1:]]
                prelim.append({"nombre": nombre_p, "alias": aliases(nombre_p, part, alias_extra), "obligatoria": True, "nivel": 0, "numero": None,
                               "proposito": primeras_oraciones(desc), "preguntas": [], "origen": f"guía p. {pag}: «{recorta(txt, 110)}»"})
    return {"id": estructura_id, "prelim": prelim, "front": front, "secciones": secciones}


def estructura_a_yaml(est, d, nombre_doc):
    """Dict listo para yaml: front_matter, preliminares (con límites del resumen) y secciones."""
    pre = est["prelim"]
    for s in pre:
        if norm(s["nombre"]) == "resumen":
            if d.tiene("formato.resumen.palabras"):
                a, b = d.valor("formato.resumen.palabras")
                s["palabras"] = f"{a}-{b}"
            if d.tiene("formato.resumen.palabras_clave"):
                a, b = d.valor("formato.resumen.palabras_clave")
                s["palabras_clave"] = f"{a}-{b}"
    out = {"id": est["id"], "nombre": nombre_doc, "front_matter": est["front"] or [], "secciones": []}
    for s in pre + est["secciones"]:
        item = {"nombre": s["nombre"], "alias": s["alias"], "obligatoria": True}
        item["nivel"] = s["nivel"] if s["nivel"] else 1
        if s["numero"]:
            item["numero"] = s["numero"]
        item["proposito"] = s["proposito"]
        item["preguntas"] = s["preguntas"]
        for k in ("palabras", "palabras_clave"):
            if k in s:
                item[k] = s[k]
        item["origen"] = s["origen"]
        out["secciones"].append(item)
    return out


# ---------------------------------------------------------------- preguntas
def _op(*pares):
    return [{"n": i + 1, "texto": t, "valor": v} for i, (t, v) in enumerate(pares)]


def preguntas_para(d):
    """Lo que la guía no dijo o es ambiguo + preferencias que ninguna guía dice."""
    P = []

    def falta(clave, pid, texto, opciones, tipo="unica", ambito="guia"):
        P.append({"id": pid, "clave": clave, "ambito": ambito, "tipo": tipo, "pregunta": texto, "opciones": opciones})

    if not d.tiene("formato.fuente.nombre"):
        falta("formato.fuente", "P-fuente", "La guía no dice la fuente y el tamaño. ¿Cuáles usas?",
              _op(("Times New Roman 12 pt (APA 7)", {"nombre": "Times New Roman", "pt": 12}), ("Calibri 11 pt", {"nombre": "Calibri", "pt": 11}),
                  ("Arial 11 pt", {"nombre": "Arial", "pt": 11}), ("Otra: dímela (nombre y tamaño)", None)))
    if not d.tiene("reglas_guia.margenes_cm"):
        falta("reglas_guia.margenes_cm", "P-margenes", "La guía no dice los márgenes. ¿Cuáles?", _op(("2.54 cm (1 pulgada) en los cuatro lados", 2.54), ("3 cm izquierdo y 2.5 cm los demás", 3), ("Otros: dímelos", None)))
    if not d.tiene("formato.interlineado"):
        falta("formato.interlineado", "P-interlineado", "La guía no dice el interlineado. ¿Cuál?", _op(("Doble (APA 7)", 2), ("1.5", 1.5), ("Sencillo", 1)))
    if not d.tiene("formato.alineacion"):
        falta("formato.alineacion", "P-alineacion", "La guía no dice la alineación del cuerpo. ¿Cuál?", _op(("Izquierda (APA 7)", "izquierda"), ("Justificada", "justificada")))
    if not d.tiene("perfil"):
        falta("perfil", "P-citas", "La guía no dice la norma de citas y referencias. ¿Cuál?", _op(("APA 7.ª edición (autor-año)", "apa7"), ("IEEE (numérica [1])", "ieee")))
    if not d.tiene("formato.paginacion.preliminares") and not d.tiene("formato.paginacion.cuerpo"):
        falta("formato.paginacion", "P-paginacion", "La guía no dice cómo numerar las páginas. ¿Cómo?",
              _op(("Portada sin número, preliminares en romanos y cuerpo en arábigos", {"portada": "sin_numero", "preliminares": "romanos", "cuerpo": "arabigos"}),
                  ("Todo en arábigos desde la portada", {"portada": "con_numero", "cuerpo": "arabigos"}), ("Sin numeración", None)))
    if not d.tiene("voz") and not d.tiene("reglas_guia.voz"):
        falta("preferencias.persona", "P-persona", "La guía no dice la persona gramatical. ¿Cuál?",
              _op(("Impersonal (tercera persona o «se»)", "impersonal"), ("Primera persona del plural", "primera_plural"), ("Primera persona del singular", "primera_singular")), ambito="preferencia")
    # preferencias que ninguna guía dice
    falta("preferencias.registro", "P-registro", "¿Qué registro de redacción prefieres?",
          _op(("Académico formal", "academico_formal"), ("Técnico de ingeniería (directo, con cifras)", "tecnico"), ("Claro y divulgativo", "divulgativo")), ambito="preferencia")
    falta("preferencias.extension", "P-extension", "¿Qué extensión por sección quieres?",
          _op(("La que marque la guía, sin límite propio", "segun_guia"), ("Breve: 1 a 2 páginas por capítulo", "breve"), ("Media: 3 a 5 páginas por capítulo", "media"), ("Amplia: 6 o más", "amplia")), ambito="preferencia")
    falta("preferencias.densidad_citas", "P-citas-densidad", "¿Cuántas citas por párrafo?",
          _op(("Una cita por cada afirmación sustantiva (cifra, resultado, eficacia)", "por_afirmacion"), ("Una o dos por párrafo", "una_o_dos"), ("Solo donde la guía lo pida", "minimas")), ambito="preferencia")
    falta("preferencias.salida", "P-salida", "¿Qué salida entregas?",
          _op((".docx y .pdf verificados con `entregar`", ["docx", "pdf"]), ("Solo .docx", ["docx"]), ("Solo .pdf", ["pdf"])), ambito="preferencia")
    if not d.tiene("fuentes.evitar"):
        falta("fuentes.evitar", "P-evitar", "¿Qué tipos de fuente no admites?",
              _op(("Wikipedia, blogs y foros", ["wikipedia", "blog", "foro"]), ("Además redes sociales y video", ["wikipedia", "blog", "foro", "redes", "video"]), ("Ninguno", [])), ambito="preferencia")
    return P


def aplicar_respuestas(d, preguntas, ruta):
    """Aplica `respuestas.yaml`: {id o clave: número de opción | texto de la opción | lista | valor libre}. Devuelve (pendientes, aplicadas)."""
    try:
        resp = yaml.safe_load(pathlib.Path(ruta).read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as ex:
        cli.error(f"no se pudo leer {ruta}: {ex}")
    if not isinstance(resp, dict):
        cli.error(f"{ruta}: debe ser un mapa {{id: respuesta}}")
    pend, ap = [], []
    for q in preguntas:
        clave = next((k for k in (q["id"], q["clave"]) if k in resp), None)
        if clave is None:
            pend.append(q)
            continue
        r = resp[clave]
        ops = q["opciones"]
        valor, hallado = r, False

        def uno(x):
            if isinstance(x, int) and not isinstance(x, bool) and 1 <= x <= len(ops):
                return True, ops[x - 1]["valor"]
            if isinstance(x, str):
                for o in ops:
                    if norm(x) in (norm(o["texto"]), norm(str(o["valor"]))):
                        return True, o["valor"]
            return False, x

        if isinstance(r, list) and len(r) == 1 and q["tipo"] != "multiple":
            hallado, valor = uno(r[0])
        elif isinstance(r, list):
            valor = [uno(x)[1] for x in r]
            hallado = True
        else:
            hallado, valor = uno(r)
        if valor is None:  # opción «otra: dímela» sin valor
            pend.append(q)
            continue
        d.poner(q["clave"], valor, f"respuesta del usuario ({q['id']}): «{r}»")
        ap.append(q["id"])
    return pend, ap


# ---------------------------------------------------------------- armado
def anidar(planos):
    """{'a.b.c': v} -> {'a': {'b': {'c': v}}}"""
    out = {}
    for k, v in planos.items():
        cur = out
        partes = k.split(".")
        for x in partes[:-1]:
            cur = cur.setdefault(x, {})
        cur[partes[-1]] = v
    return out


def institucion_de(g):
    nom = lineas_institucion(g)
    acr = acronimos(g)
    partes = [" ".join(w.lower() if w.lower() in ("de", "del", "la", "y", "para") else w[:1].upper() + w[1:].lower() for w in a_oracion(x, acr).split()) for x in nom]
    extra = []
    ma = re.search(r"asignatura\s*:\s*(?P<a>[^(\n]+?)\s*(?:\(|$)", " ".join(l for _, l in g.lineas[:30]), re.I)
    mc = re.search(r"(?:ciclo|cycle)\s+(?P<c>20\d{2})", g.todo, re.I)
    if ma:
        extra.append(plano(ma.group("a")))
    if mc:
        extra.append(f"ciclo {mc.group('c')}")
    txt = ", ".join(partes)
    return (txt + (f" ({', '.join(extra)})" if extra else "")).strip() or None


def construir(g, estructura_id, modelo=None, pagina=1, responder=None):
    d = Datos()
    extraer_formato(g, d)
    portada_extraer(g, d)
    est = estructura_extraer(g, estructura_id)
    if est:
        n_caps = sum(1 for s in est["secciones"] if s["nivel"] == 1)
        n_subs = sum(1 for s in est["secciones"] if s["nivel"] > 1)
        d.poner("estructura", estructura_id, f"derivado de: {n_caps} capítulos y {n_subs} subcapítulos numerados hallados en la guía → estructuras/{estructura_id}.yaml")
        if n_subs >= 2:
            ejemplo = next(s for s in est["secciones"] if s["nivel"] > 1)
            d.poner("formato.niveles_numerados", True, f"derivado de: subcapítulos numerados en la guía ({ejemplo['origen']})")
        if n_caps:
            c1 = est["secciones"][0]
            d.poner("formato.nivel1.numerado", True, f"derivado de: capítulos numerados en la guía ({c1['origen']})")
    ins = institucion_de(g)
    if ins:
        d.poner("institucion", ins, "derivado de: encabezado de la primera página de la guía")
    preguntas = preguntas_para(d)
    aplicadas = []
    if responder:
        preguntas, aplicadas = aplicar_respuestas(d, preguntas, responder)
    return d, est, preguntas, aplicadas


ORDEN_FORMATO = ["interlineado", "alineacion", "nivel1", "niveles_numerados", "capitulo_pagina_nueva", "paginacion", "titulo_max_palabras",
                 "fuentes_recientes", "voz", "fuente", "resumen", "rotulos_pt", "portada"]
ORDEN_TOP = ["institucion", "perfil", "estructura", "idioma", "voz", "tiempo_verbal", "minimo_fuentes", "anios_fuentes", "porcentaje_recientes",
             "portada_numero", "tablas_figuras", "formato", "fuentes", "medidas", "reglas_guia", "preferencias", "vinculante", "origenes", "preguntas"]


def perfil_dict(d, preguntas, vinculante=None):
    planos = {k: v for k, (v, _) in d.v.items()}
    # el formato no admite claves extra: ya lo garantiza el origen de las claves
    anid = anidar(planos)
    if "formato" in anid:
        f = anid["formato"]
        anid["formato"] = {k: f[k] for k in ORDEN_FORMATO if k in f} | {k: v for k, v in f.items() if k not in ORDEN_FORMATO}
    # excepciones propuestas: lo que la guía fija distinto de APA
    m = planos.get("reglas_guia.margenes_cm")
    if m is not None and abs(float(m) - 2.54) > 0.06:
        anid.setdefault("excepciones", []).append({"regla": "APA-001", "motivo": f"Guía: márgenes de {m} cm"})
    # medidas: lo que la guía fija y `medir` comprueba (INS-016); el interlineado, la fuente y la alineación ya los cubre `formato:`
    meds = []
    for clave, que, alcance in (("reglas_guia.margenes_cm", "margenes", "documento"), ("reglas_guia.sangria_primera_linea_cm", "sangria_primera_linea", "cuerpo")):
        if clave in d.v:
            valor, org = d.v[clave]
            meds.append({"que": que, "valor": float(valor), "unidad": "cm", "alcance": alcance, "origen": org})
    if meds:
        anid["medidas"] = meds
    anid["origenes"] = {k: o for k, (_, o) in d.v.items()}
    if vinculante:
        anid["vinculante"] = vinculante
    if preguntas:
        anid["preguntas"] = [{"id": q["id"], "clave": q["clave"], "pregunta": q["pregunta"],
                              "opciones": [f"{o['n']}) {o['texto']}" for o in q["opciones"]], "valores": [o["valor"] for o in q["opciones"]]} for q in preguntas]
    return {k: anid[k] for k in ORDEN_TOP if k in anid} | {k: v for k, v in anid.items() if k not in ORDEN_TOP}


CABECERA = ("# Perfil generado por `editorial.py perfilar` a partir de la guía institucional. Cada valor tiene su origen en `origenes:`\n"
            "# («guía p. N: «cita literal»»; «derivado de» si no está dicho tal cual). Lo que falta o es ambiguo está en `preguntas:`;\n"
            "# respóndelas en un archivo y vuelve a correr con `--responder`. Revísalo antes de copiarlo como `.editorial.yaml`.\n")


def volcar(dic):
    """El bloque principal en estilo compacto; `origenes` y `preguntas` en bloque (una línea por valor, sin partir citas)."""
    principal = {k: v for k, v in dic.items() if k not in ("origenes", "preguntas")}
    txt = CABECERA + yaml.safe_dump(principal, allow_unicode=True, sort_keys=False, default_flow_style=None, width=140)
    for k in ("origenes", "preguntas"):
        if k in dic:
            txt += yaml.safe_dump({k: dic[k]}, allow_unicode=True, sort_keys=False, default_flow_style=False, width=100000)
    return txt


# ---------------------------------------------------------------- diff legible
def aplanar(x, pre=""):
    if isinstance(x, dict):
        out = {}
        for k, v in x.items():
            out.update(aplanar(v, f"{pre}{k}."))
        return out
    return {pre.rstrip("."): x}


def diff_legible(actual, propuesto):
    a, b = aplanar(actual), aplanar(propuesto)
    L = []
    for k in sorted(set(a) | set(b)):
        if k.startswith(("origenes", "preguntas")):
            continue
        if k not in a:
            L.append(f"+ {k}: {json.dumps(b[k], ensure_ascii=False)}   (nuevo)")
        elif k not in b:
            L.append(f"- {k}: {json.dumps(a[k], ensure_ascii=False)}   (solo en tu archivo; se conserva)")
        elif a[k] != b[k]:
            L.append(f"~ {k}: {json.dumps(a[k], ensure_ascii=False)} -> {json.dumps(b[k], ensure_ascii=False)}   (la guía dice otra cosa)")
    return L


# ---------------------------------------------------------------- comparación (prueba dorada)
def _plano_comparable(v):
    if isinstance(v, str):
        return norm(v)
    if isinstance(v, (list, tuple)):
        return [_plano_comparable(x) for x in v]
    return v


def _contiene_tokens(gold, gen):
    tg = set(norm(gold).split())
    tn = set(norm(gen).split())
    return bool(tg) and len(tg & tn) / len(tg) >= 0.75


def comparar_perfil(gen, ref):
    """Compara un perfil generado con uno de referencia, clave por clave del de referencia (formato, fuentes y nivel superior).
    Devuelve {total, coinciden, porcentaje, formato: {total, coinciden, porcentaje}, fallas: [(clave, esperado, obtenido)]}."""
    a_ref = {k: v for k, v in aplanar(ref).items() if not k.startswith(("excepciones", "origenes", "preguntas", "vinculante", "reglas_guia", "preferencias", "medidas"))}
    a_gen = aplanar(gen)
    claves = {}
    # lo comparable: claves de referencia agrupadas (portada.campos como conjunto de primeras palabras)
    fallas, ok, total = [], 0, 0
    fmt_ok = fmt_total = 0
    for k, v in a_ref.items():
        if k.startswith("formato.portada.campos"):
            continue
        total += 1
        g = a_gen.get(k)
        if k == "institucion":
            bien = g is not None and _contiene_tokens(v, g)
        else:
            bien = _plano_comparable(g) == _plano_comparable(v) if g is not None else False
        # YAML 1.1: «no»/«si» como texto
        if not bien and isinstance(v, bool) and isinstance(g, str):
            bien = (norm(g) in ("si", "yes", "true")) == v
        ok += bien
        if k.startswith("formato."):
            fmt_total += 1
            fmt_ok += bien
        if not bien:
            fallas.append((k, v, g))
    # portada.campos: fracción de campos de referencia presentes por su primera palabra
    cr = (ref.get("formato") or {}).get("portada", {}).get("campos") or []
    cg = (gen.get("formato") or {}).get("portada", {}).get("campos") or []
    if cr:
        primeras = {norm(c.get("nombre", "")).split(" ")[0] for c in cg}
        hit = sum(1 for c in cr if norm(c.get("nombre", "")).split(" ")[0] in primeras)
        frac = hit / len(cr)
        total += 1
        fmt_total += 1
        ok += frac
        fmt_ok += frac
        if frac < 1:
            fallas.append(("formato.portada.campos", [c.get("nombre") for c in cr], [c.get("nombre") for c in cg]))
    return {"total": total, "coinciden": round(ok, 2), "porcentaje": round(100 * ok / total, 1) if total else 0.0,
            "formato": {"total": fmt_total, "coinciden": round(fmt_ok, 2), "porcentaje": round(100 * fmt_ok / fmt_total, 1) if fmt_total else 0.0},
            "fallas": fallas}


def _coincide_nombre(a, ref):
    """El nombre/alias de `a` (generado) equivale al de `ref`: igual, uno prefijo del otro, o por alias."""
    na = {norm(a["nombre"])} | {norm(x) for x in a.get("alias", [])}
    nr = {norm(ref["nombre"])} | {norm(x) for x in ref.get("alias", [])}
    if na & nr:
        return True
    return any(x and y and (x.startswith(y + " ") or y.startswith(x + " ")) for x in {norm(a["nombre"])} for y in {norm(ref["nombre"])})


def comparar_estructura(gen, ref):
    """Compara la estructura generada con una de referencia: cuántos capítulos (numerados en la guía) de la referencia están en la
    generada, cuántos de sus subcapítulos cuelgan del capítulo correcto, y los preliminares."""
    rs, gs = ref["secciones"], gen["secciones"]
    pos, desde = [], 0
    for r in rs:
        j = next((j for j in range(desde, len(gs)) if _coincide_nombre(gs[j], r)), None)
        pos.append(j)
        if j is not None:
            desde = j + 1
    es_cap = lambda j: j is not None and gs[j].get("numero") and gs[j].get("nivel", 1) == 1  # noqa: E731
    cap_ref = [i for i, j in enumerate(pos) if es_cap(j)]
    primero = min(cap_ref) if cap_ref else len(rs)
    prel_ref = [i for i in range(primero)]
    sub_ref = [i for i in range(primero, len(rs)) if i not in cap_ref]
    sub_ok, cap_actual = 0, None
    for i in range(primero, len(rs)):
        if i in cap_ref:
            cap_actual = gs[pos[i]]["numero"]
        elif pos[i] is not None and cap_actual is not None and str(gs[pos[i]].get("numero") or "").startswith(cap_actual + "."):
            sub_ok += 1
    return {"capitulos_referencia": len(cap_ref),
            "subcapitulos_referencia": len(sub_ref), "subcapitulos_en_su_capitulo": sub_ok,
            "preliminares_referencia": len(prel_ref), "preliminares_hallados": sum(pos[i] is not None for i in prel_ref),
            "capitulos_generados": sum(1 for s in gs if s.get("numero") and s.get("nivel", 1) == 1),
            "subcapitulos_generados": sum(1 for s in gs if s.get("numero") and s.get("nivel", 1) > 1),
            "perdidas": [rs[i]["nombre"] for i, j in enumerate(pos) if j is None], "total_referencia": len(rs), "coinciden": sum(j is not None for j in pos)}


# ---------------------------------------------------------------- CLI
def escribir_seguro(ruta, texto):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with open(ruta, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(texto)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="editorial perfilar", description="La guía de formato de tu escuela (PDF o .docx) se convierte en un perfil (.editorial.yaml) y una estructura de capítulos.")
    ap.add_argument("guia", nargs="?", help="guía en .pdf o .docx")
    ap.add_argument("--modelo-portada", metavar="PDF|DOCX", help="modelo de portada: se mide y se registra como `vinculante` tipo modelo")
    ap.add_argument("--pagina", type=int, default=1, help="página del modelo de portada (por defecto 1)")
    ap.add_argument("--out", default=".editorial.yaml", help="perfil de salida (por defecto .editorial.yaml); si existe se escribe .editorial.propuesto.yaml")
    ap.add_argument("--estructura-id", help="id de la estructura de capítulos (por defecto el nombre de la guía)")
    ap.add_argument("--responder", metavar="RESPUESTAS.yaml", help="aplica respuestas a las `preguntas:` ({id: opción})")
    ap.add_argument("--json", metavar="RUTA", help="resultado estructurado")
    ap.add_argument("--comparar", metavar="REFERENCIA.yaml", help="compara el perfil de `--out` (o el propuesto) con un perfil de referencia y sale")
    ap.add_argument("--comparar-estructura", metavar="REFERENCIA.yaml", help="con --comparar: estructura de referencia")
    ap.add_argument("--generado", metavar="PERFIL.yaml", help="con --comparar: perfil generado a comparar")
    ap.add_argument("--generada-estructura", metavar="ESTRUCTURA.yaml", help="con --comparar: estructura generada a comparar")
    a = ap.parse_args(argv)
    cli.utf8()

    if a.comparar:
        if not a.generado:
            ap.error("--comparar necesita --generado <perfil.yaml>")
        gen = yaml.safe_load(pathlib.Path(a.generado).read_text(encoding="utf-8")) or {}
        ref = yaml.safe_load(pathlib.Path(a.comparar).read_text(encoding="utf-8")) or {}
        r = comparar_perfil(gen, ref)
        print(f"perfil: {r['coinciden']}/{r['total']} claves coinciden ({r['porcentaje']} %); formato {r['formato']['porcentaje']} %")
        for k, esp, obt in r["fallas"]:
            print(f"  ≠ {k}: esperado {esp!r}, generado {obt!r}")
        if a.comparar_estructura and a.generada_estructura:
            er = yaml.safe_load(pathlib.Path(a.comparar_estructura).read_text(encoding="utf-8"))
            eg = yaml.safe_load(pathlib.Path(a.generada_estructura).read_text(encoding="utf-8"))
            e = comparar_estructura(eg, er)
            print(f"estructura: {e['capitulos_referencia']}/{e['capitulos_generados']} capítulos hallados, {e['subcapitulos_en_su_capitulo']}/{e['subcapitulos_referencia']} subcapítulos en su capítulo, "
                  f"{e['preliminares_hallados']}/{e['preliminares_referencia']} preliminares, {e['coinciden']}/{e['total_referencia']} secciones")
            for n in e["perdidas"]:
                print(f"  ≠ sin equivalente en la generada: {n}")
        cli.escribir_json(a.json, r)
        return 0

    if not a.guia:
        ap.error("falta la guía (.pdf o .docx)")
    g = Guia(a.guia)
    eid = a.estructura_id or re.sub(r"[^a-z0-9]+", "-", norm(pathlib.Path(a.guia).stem)).strip("-")[:40] or "estructura-guia"
    d, est, preguntas, aplicadas = construir(g, eid, responder=a.responder)

    out = pathlib.Path(a.out)
    carpeta = out.resolve().parent
    vinc = None
    if a.modelo_portada:
        import modelo_formato
        spec = modelo_formato.medir(a.modelo_portada, a.pagina)
        ruta_spec = carpeta / "portada-modelo.json"
        if ruta_spec.exists():
            ruta_spec = carpeta / "portada-modelo.propuesto.json"
        cli.escribir_json(str(ruta_spec), spec)
        vinc = [{"id": "portada-modelo", "origen": f"modelo {pathlib.Path(a.modelo_portada).name} p. {a.pagina}, medido con modelo_formato",
                 "fecha": dt.date.today().isoformat(), "tipo": "modelo", "spec": ruta_spec.name, "ambito": "portada"}]
        print(f"modelo de portada medido: {ruta_spec} ({len(spec['lineas'])} líneas, {len(spec['cajas'])} cajas)")

    dic = perfil_dict(d, preguntas, vinc)
    resultado = {"guia": str(a.guia), "paginas": len(g.paginas), "claves": len(d.v), "preguntas": [q["id"] for q in preguntas], "respondidas": aplicadas}

    # perfil: nunca sobrescribe
    if out.exists():
        destino = out.with_name(".editorial.propuesto.yaml") if out.name == ".editorial.yaml" else out.with_name(out.stem + ".propuesto" + out.suffix)
        try:
            actual = yaml.safe_load(out.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError:
            actual = {}
        L = diff_legible(actual, dic)
        diff_ruta = destino.with_suffix(".diff")
        escribir_seguro(diff_ruta, "\n".join(L) + ("\n" if L else "") if L else "sin diferencias\n")
        print(f"{out} ya existe: NO se sobrescribe. Propuesta en {destino}")
        print(f"diferencias ({len(L)}), también en {diff_ruta}:")
        for x in L[:40]:
            print("  " + x)
        if len(L) > 40:
            print(f"  … y {len(L) - 40} más")
        resultado.update(perfil=str(destino), diff=str(diff_ruta), sobrescribio=False)
    else:
        destino = out
        resultado.update(perfil=str(destino), sobrescribio=False)
    escribir_seguro(destino, volcar(dic))
    print(f"perfil escrito en {destino}: {len(d.v)} valores con su origen")

    # estructura
    if est:
        eyaml = estructura_a_yaml(est, d, f"Estructura de la guía «{pathlib.Path(a.guia).stem}»")
        ruta_e = carpeta / "estructuras" / f"{eid}.yaml"
        if ruta_e.exists():
            ruta_e = ruta_e.with_name(f"{eid}.propuesto.yaml")
            print(f"estructuras/{eid}.yaml ya existe: no se sobrescribe; propuesta en {ruta_e}")
        escribir_seguro(ruta_e, "# Estructura generada por `editorial.py perfilar` (cada sección con su origen en la guía). Úsala con `estructura: " + eid + "` en .editorial.yaml.\n"
                        + yaml.safe_dump(eyaml, allow_unicode=True, sort_keys=False, width=140))
        n1 = sum(1 for s in est["secciones"] if s["nivel"] == 1)
        print(f"estructura escrita en {ruta_e}: {len(est['prelim'])} preliminares, {n1} capítulos, {len(est['secciones']) - n1} subcapítulos")
        resultado.update(estructura=str(ruta_e), capitulos=n1, subcapitulos=len(est["secciones"]) - n1)
    else:
        print("aviso: no se hallaron capítulos numerados en la guía; no se genera estructura")
    if preguntas:
        print(f"\n{len(preguntas)} preguntas pendientes (responde en un archivo y repite con --responder):")
        for q in preguntas:
            print(f"  {q['id']}: {q['pregunta']}")
            for o in q["opciones"]:
                print(f"      {o['n']}) {o['texto']}")
    cli.escribir_json(a.json, resultado)
    return 0


if __name__ == "__main__":
    sys.exit(main())
