#!/usr/bin/env python3
"""Verificación de normas ISO/IEC cuando iso.org no responde (devuelve 403 a los clientes automáticos, siempre).

Una referencia «ISO/IEC … No. NNNNN:AAAA» (o una URL iso.org/standard/N) se comprueba en este orden:
  1. iso.org (la página del catálogo; casi siempre 403);
  2. vista previa oficial de VDE: https://assets.vde-verlag.de/iec-normen/preview-pdf/info_isoiec{NNNNN}%7Bed<E>.0%7Den.pdf
     (llaves URL-codificadas; se prueban ed1..ed4);
  3. muestra de iteh.ai, solo si la propia referencia trae esa URL (https://cdn.standards.iteh.ai/samples/<id iso>/…).
Del PDF se lee la portada con pdftotext (o PyMuPDF): «Reference number ISO/IEC NNNNN:AAAA(E)», «<Ordinal> edition AAAA-MM» y el
título, y se compara con la referencia (número, año, título).

verificar(norma, titulo) -> {"estado": "verificado" | "no_verificado" | "difiere", "motivo", "fuente_verificacion", "norma",
"edicion", "titulo_oficial", "url", "diferencias"}. Un fallo de red nunca es «verificado»: queda no_verificado con motivo.
Solo se envían números de norma a los servidores (nunca texto del documento del usuario).
Pruebas: `descargar` se puede sustituir (tests/run_v07.py usa un PDF de muestra sintético, sin red).
"""
import hashlib
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import datos  # noqa: E402

UA_NAVEGADOR = "Mozilla/5.0 (compatible; editorial-academica/0.7; +verificacion de normas)"
VDE = "https://assets.vde-verlag.de/iec-normen/preview-pdf/info_{org}{num}%7Bed{ed}.0%7Den.pdf"
ORDINALES = {"first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5, "sixth": 6}
LIMITE_BYTES = 6 * 1024 * 1024
RE_NORMA = re.compile(r"\b(ISO(?:/IEC)?(?:/IEEE)?|IEC)\b[^.\d]{0,30}?(?:(?:No|N[oº°]|n[uú]m)\.?\s*)?(\d{3,6}(?:-\d{1,2})?)\s*:\s*((?:19|20)\d{2})")
RE_URL_ISO = re.compile(r"iso\.org/(?:[a-z]{2}/)?(?:contents/data/)?standard/(\d+)", re.I)
RE_URL_ITEH = re.compile(r"https?://cdn\.standards\.iteh\.ai/samples/[^\s)\]>]+\.pdf", re.I)
RE_REF_PDF = re.compile(r"Reference\s+number\s+(ISO(?:/IEC)?(?:/IEEE)?|IEC)\s*(\d{3,6}(?:-\d{1,2})?)\s*:\s*((?:19|20)\d{2})", re.I)
RE_ED_PDF = re.compile(r"\b(First|Second|Third|Fourth|Fifth|Sixth)\s+edition\s+((?:19|20)\d{2}-\d{2})", re.I)


def descargar(url, tiempo=30):
    """(estado HTTP o None, bytes o None). Sustituible en pruebas. Lee como máximo LIMITE_BYTES."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA_NAVEGADOR})
        with urllib.request.urlopen(req, timeout=tiempo) as r:
            return r.status, r.read(LIMITE_BYTES)
    except urllib.error.HTTPError as e:
        return e.code, None
    except (urllib.error.URLError, OSError, TimeoutError):
        return None, None


def _haystack(it):
    partes = [str(it.get(k) or "") for k in ("title", "number", "publisher", "container-title", "_original", "URL", "note")]
    for a in it.get("author") or []:
        partes.append(str(a.get("literal") or a.get("family") or ""))
    return " ".join(partes)


RE_AUTOR_ORG = re.compile(r"^\s*(?:ISO|IEC|International Organi[sz]ation for Standardi[sz]ation|International Electrotechnical|ANSI|IEEE)\b", re.I)


def _parece_norma(it):
    """Un item CSL es la norma misma (no un artículo que la menciona): tipo `standard`, autor organismo de normas, título que
    empieza por el código de la norma o URL del catálogo de ISO."""
    a = (it.get("author") or [{}])[0]
    autor = str(a.get("literal") or a.get("family") or "")
    return (it.get("type") == "standard" or bool(RE_AUTOR_ORG.match(autor)) or bool(RE_URL_ISO.search(str(it.get("URL") or "")))
            or bool(re.match(r"\s*(?:ISO|IEC)\b", str(it.get("title") or ""))) or bool(RE_URL_ITEH.search(str(it.get("URL") or ""))))


def detectar(it):
    """Datos de norma ISO/IEC de un item CSL (o de un texto): {org, numero, anio, iso_id, titulo, iteh} o None."""
    if not isinstance(it, str) and not _parece_norma(it):
        return None
    texto = it if isinstance(it, str) else _haystack(it)
    titulo = "" if isinstance(it, str) else str(it.get("title") or "")
    m = RE_NORMA.search(texto)
    u = RE_URL_ISO.search(texto)
    iteh = RE_URL_ITEH.search(texto)
    if not m and not (u or iteh):
        return None
    d = {"org": m.group(1).upper() if m else None, "numero": m.group(2) if m else None, "anio": m.group(3) if m else None,
         "iso_id": u.group(1) if u else None, "titulo": titulo, "iteh": iteh.group(0) if iteh else None}
    if d["numero"] is None and not d["iteh"]:
        return d if u else None
    return d


def texto_pdf(datos_pdf, paginas=2):
    """Texto de las primeras páginas de un PDF: pdftotext si existe, si no PyMuPDF; None si no hay con qué leerlo."""
    with tempfile.TemporaryDirectory() as tmp:
        ruta = pathlib.Path(tmp) / "norma.pdf"
        ruta.write_bytes(datos_pdf)
        exe = shutil.which("pdftotext")
        if exe:
            r = subprocess.run([exe, "-l", str(paginas), "-layout", str(ruta), "-"], capture_output=True, timeout=60)
            if r.returncode == 0 and r.stdout.strip():
                return r.stdout.decode("utf-8", errors="replace")
        try:
            import fitz  # PyMuPDF
            with fitz.open(str(ruta)) as doc:
                return "\n".join(doc[i].get_text() for i in range(min(paginas, len(doc))))
        except Exception:  # noqa: BLE001
            return None


def leer_portada(texto):
    """{org, numero, anio, edicion, fecha, titulo} de la portada de una norma ISO/IEC; {} si no se reconoce."""
    t = texto.replace("\r", "")
    m = RE_REF_PDF.search(t)
    if not m:
        return {}
    out = {"org": m.group(1).upper(), "numero": m.group(2), "anio": m.group(3), "edicion": None, "fecha": None, "titulo": ""}
    e = RE_ED_PDF.search(t)
    if e:
        out["edicion"], out["fecha"] = ORDINALES[e.group(1).lower()], e.group(2)
        resto = t[e.end():].split("Reference number")[0]
        bloque = []
        for linea in resto.split("\n"):
            s = " ".join(linea.split())
            if not s:
                if bloque:
                    break
                continue
            bloque.append(s)
        out["titulo"] = " ".join(bloque)
    return out


def _palabras(t):
    import unicodedata
    t = unicodedata.normalize("NFD", t.lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return {w for w in re.findall(r"[a-z]{4,}", t)}


def titulos_compatibles(ref, oficial):
    """Las palabras significativas de la referencia están en el título oficial (o al revés) en al menos 60 %; sin título en la
    referencia no hay con qué comparar (compatible)."""
    a, b = _palabras(ref), _palabras(oficial)
    if not a or not b:
        return True
    comunes = a & b
    return len(comunes) >= 2 and len(comunes) / min(len(a), len(b)) >= 0.6


def _cache_pdf(url):
    return datos.dir_cache() / "normas" / (hashlib.sha1(url.encode()).hexdigest() + ".pdf")


def obtener_pdf(url, sin_red=False):
    """Bytes del PDF (de la caché o de la red); (bytes | None, motivo si no hay)."""
    ruta = _cache_pdf(url)
    if ruta.exists() and ruta.stat().st_size > 1000:
        return ruta.read_bytes(), None
    if sin_red:
        return None, "sin red y sin caché"
    estado, cuerpo = descargar(url)
    if estado == 200 and cuerpo and cuerpo[:4] == b"%PDF":
        try:
            ruta.parent.mkdir(parents=True, exist_ok=True)
            ruta.write_bytes(cuerpo)
        except OSError:
            pass
        return cuerpo, None
    if estado is None:
        return None, "sin red"
    return None, f"HTTP {estado}"


def _resultado(estado, motivo=None, **kw):
    return {"estado": estado, "motivo": motivo, "fuente_verificacion": None, "norma": None, "edicion": None,
            "titulo_oficial": None, "url": None, "diferencias": [], **kw}


def verificar(norma, sin_red=False):
    """Verifica una norma detectada con `detectar`. Ver el docstring del módulo para el orden de las fuentes."""
    intentos = []
    if norma.get("iso_id") and not sin_red:
        estado, cuerpo = descargar(f"https://www.iso.org/standard/{norma['iso_id']}.html")
        if estado == 200 and cuerpo:
            pag = cuerpo.decode("utf-8", errors="replace")
            if norma.get("numero") and re.search(re.escape(norma["numero"]) + r"\s*:\s*" + (norma.get("anio") or r"\d{4}"), pag):
                t = re.search(r"<title>([^<]+)</title>", pag)
                oficial = " ".join(t.group(1).split()) if t else None
                dif = ["título"] if (oficial and norma.get("titulo")
                                     and not titulos_compatibles(_sin_prefijo(norma["titulo"], norma), RE_NORMA.sub(" ", oficial))) else []
                return _resultado("difiere" if dif else "verificado",
                                  ("el título de la referencia no coincide con el oficial: " + oficial) if dif else None,
                                  fuente_verificacion="iso.org", norma=_nombre(norma), titulo_oficial=oficial,
                                  url=f"https://www.iso.org/standard/{norma['iso_id']}.html", diferencias=dif)
        intentos.append(f"iso.org: {'HTTP ' + str(estado) if estado else 'sin respuesta'}")
    candidatas = []   # (fuente, url)
    if norma.get("numero"):
        org = re.sub(r"[^a-z]", "", norma["org"].lower()) if norma.get("org") else "isoiec"
        num = norma["numero"]
        for e in (1, 2, 3, 4):
            candidatas.append(("vde-preview", VDE.format(org=org, num=num, ed=e)))
    if norma.get("iteh"):
        candidatas.append(("iteh", norma["iteh"]))
    if not candidatas:
        return _resultado("no_verificado", "la referencia no trae número de norma ni URL de muestra: " + "; ".join(intentos or ["nada que consultar"]))
    leidas, sin_lectura = [], 0
    for fuente, url in candidatas:
        pdf, motivo = obtener_pdf(url, sin_red)
        if pdf is None:
            if motivo not in ("HTTP 404", "HTTP 403"):
                intentos.append(f"{fuente} {url.rsplit('/', 1)[-1]}: {motivo}")
            continue
        txt = texto_pdf(pdf)
        if txt is None:
            sin_lectura += 1
            intentos.append(f"{fuente}: no hay pdftotext ni PyMuPDF para leer la portada")
            continue
        p = leer_portada(txt)
        if not p:
            intentos.append(f"{fuente}: la portada del PDF no trae «Reference number»")
            continue
        p.update(fuente=fuente, url=url)
        leidas.append(p)
    if not leidas:
        extra = "; ".join(intentos) or "sin vista previa oficial para esta norma (VDE respondió 404 en ed1..ed4)"
        if sin_red and not intentos:
            extra = "sin red y sin caché de la vista previa"
        return _resultado("no_verificado", "no se pudo leer una portada oficial: " + extra)
    num = norma.get("numero")
    deben = [p for p in leidas if (not num or p["numero"] == num)]
    if not deben:
        return _resultado("no_verificado", f"la portada oficial es de otra norma ({leidas[0]['org']} {leidas[0]['numero']}:{leidas[0]['anio']})")
    anio = norma.get("anio")
    exacta = next((p for p in deben if not anio or p["anio"] == anio), None)
    if exacta is None:
        eds = ", ".join(f"{p['anio']} (ed. {p['edicion']})" for p in deben)
        return _resultado("no_verificado", f"el año {anio} no coincide con las ediciones que ofrece la vista previa oficial: {eds}",
                          fuente_verificacion=deben[0]["fuente"], norma=_nombre(norma), url=deben[0]["url"], titulo_oficial=deben[0]["titulo"])
    dif = []
    if norma.get("titulo") and not titulos_compatibles(_sin_prefijo(norma["titulo"], norma), exacta["titulo"]):
        dif.append("título")
    ed = f"{exacta['edicion']}.ª edición {exacta['fecha']}" if exacta.get("edicion") else None
    return _resultado("difiere" if dif else "verificado", ("el título de la referencia no coincide con el oficial: " + exacta["titulo"]) if dif else None,
                      fuente_verificacion=exacta["fuente"], norma=f"{exacta['org']} {exacta['numero']}:{exacta['anio']}", edicion=ed,
                      titulo_oficial=exacta["titulo"], url=exacta["url"], diferencias=dif)


def _nombre(n):
    return f"{n.get('org') or 'ISO'} {n.get('numero') or ''}:{n.get('anio') or ''}".strip(" :")


def _sin_prefijo(titulo, norma):
    """Quita del título de la referencia el rótulo «ISO/IEC 25010:2023 …» para comparar solo el nombre de la norma."""
    return RE_NORMA.sub(" ", titulo)


def verificar_item(it, sin_red=False):
    """Para fuentes.verificar_item: None si el item no es una norma ISO/IEC; si lo es, el resultado de verificar()."""
    n = detectar(it)
    if not n:
        return None
    return verificar(n, sin_red)
