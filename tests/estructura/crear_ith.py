#!/usr/bin/env python3
"""Genera al vuelo un protocolo .docx que sigue la guía institucional ITE 2026 (perfil perfiles/instituto-ejemplo-protocolo.editorial.yaml).

crear(destino, sembrado=False): protocolo conforme a la guía (Times New Roman 12, márgenes 2.54 cm, interlineado 1.5,
párrafos justificados con sangría de 1.27 cm, nivel 1 centrado en MAYÚSCULAS con negritas y numerado en página nueva,
nivel 2 a la izquierda en negritas, portada sin número, TABLA I arriba con romanos, «Fig. 1.» abajo, resumen de 150-250
palabras con 3-5 palabras clave, lista «Fuentes de información»).

crear(destino, sembrado=True): el mismo documento con defectos sembrados que el perfil debe detectar:
  - «Tabla 1» con arábigo y en minúsculas (IEEE-089)        - pie de figura encima de la imagen (IEEE-085)
  - capítulo 8 «Cronograma de actividades» renombrado (EST-001)   - resumen de 80 palabras y 2 palabras clave (EST-004)

crear(destino, ins={...}): el documento conforme con defectos del formato institucional (INS-001..009), uno por nombre:
  doble (interlineado doble, INS-001)   izquierda (párrafos a la izquierda, INS-002)   minusculas (capítulo 1 en minúsculas,
  INS-003)   sinnumero (capítulo 2 sin número, INS-003)   num2 (subcapítulos del capítulo 3 con otro número, INS-004)
  sinsalto (capítulo 4 sin página nueva, INS-005)   romanos (preliminares en arábigos, INS-006)   sinreinicio (el cuerpo
  sigue la cuenta de los preliminares, INS-006)   titulo (título de 25 palabras, INS-007)   viejas (fuentes de más de 5 años,
  INS-008)   persona (primera persona, INS-009)   apa_rotulos (rótulos al estilo APA: «Tabla 1» y «Figura 1» + título encima
  de la imagen, con sus menciones; IEEE-089/IEEE-085, que /corregir convierte).
  Formato institucional ampliado (INS-010..013, EST-017) y modelo vinculante (INS-015):
  sin_titulo / sin_leyenda / sin_depto (portada sin ese campo, INS-010)   fecha_mal (fecha «03/Noviembre/2026», INS-010)
  sin_control (integrante sin número de control, INS-010)   portada_orden (leyenda antes del título, INS-010)
  enc_gris (encabezado en Arial 8 gris, INS-011)   resumen_sangria (resumen con sangría, INS-012)
  resumen_dos (resumen en dos párrafos, INS-012)   rotulos_12 (rótulos de 12 pt, INS-013)
  indice_viejo (índice de contenido con la estructura vieja, EST-017)   indice_tablas (índice de tablas con una tabla que no existe, EST-017)
  portada_caja (título en un solo párrafo largo y centrado, integrantes en una tabla-caja con relleno y barra izquierda y el
  resumen sin salto de página propio: el caso del piloto real; corregir no debe tocar esa portada)
  prelim_estilo (Resumen e Índice de contenido con el estilo propio «Título 1 preliminar», basado en Heading 1 con outlineLvl 9, e
  Índice de tablas y de figuras como párrafos centrados en negrita sin estilo de encabezado: EST-001 no debe darse por ausentes)
  modelo_caja (portada modelo: título azul de 14 pt y la leyenda en una caja con relleno #F4F6F9 y borde izquierdo #1B365D de 3 pt)
El documento tiene tres secciones: portada (sin número en la primera página), preliminares (romanos) y cuerpo (arábigos).
"""
import pathlib
import struct
import sys
import tempfile
import zlib

import docx
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.section import WD_SECTION
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import crear_maquetacion  # noqa: E402  (campo PAGE)

TNR = "Times New Roman"


def _png():
    """PNG de 1x1 píxeles (blanco), para la figura."""
    def trozo(tipo, datos):
        c = struct.pack(">I", len(datos)) + tipo + datos
        return c + struct.pack(">I", zlib.crc32(tipo + datos) & 0xFFFFFFFF)
    cuerpo = zlib.compress(b"\x00\xff\xff\xff")
    return b"\x89PNG\r\n\x1a\n" + trozo(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)) + trozo(b"IDAT", cuerpo) + trozo(b"IEND", b"")


def _fuente(est, tam=12, negrita=None, cursiva=None):
    est.font.name = TNR
    est.font.size = Pt(tam)
    est.font.color.rgb = RGBColor(0, 0, 0)
    if negrita is not None:
        est.font.bold = negrita
    if cursiva is not None:
        est.font.italic = cursiva
    rpr = est.element.get_or_add_rPr()
    rf = rpr.find(qn("w:rFonts"))
    if rf is None:
        rf = OxmlElement("w:rFonts")
        rpr.insert(0, rf)
    for a in list(rf.attrib):
        del rf.attrib[a]
    for a in ("ascii", "hAnsi", "eastAsia", "cs"):
        rf.set(qn("w:" + a), TNR)


_ESTADO = {"ins": frozenset(), "heads": []}


def _formato(p, alin=None, sangria=True, interlineado=None, mantener=False):
    ins = _ESTADO["ins"]
    if alin is None:
        alin = WD_ALIGN_PARAGRAPH.LEFT if "izquierda" in ins else WD_ALIGN_PARAGRAPH.JUSTIFY
    if interlineado is None:
        interlineado = 2.0 if "doble" in ins else 1.5
    pf = p.paragraph_format
    pf.alignment = alin
    pf.line_spacing = interlineado
    pf.space_before = Pt(0)
    pf.space_after = Pt(0)
    pf.first_line_indent = Cm(1.27) if sangria else None
    pf.keep_with_next = mantener or None
    return p


def _ejecutar(p, texto, tam=12, negrita=None, cursiva=None):
    r = p.add_run(texto)
    r.font.name = TNR
    r.font.size = Pt(tam)
    if negrita is not None:
        r.bold = negrita
    if cursiva is not None:
        r.italic = cursiva
    return r


def texto(d, t):
    p = d.add_paragraph()
    _formato(p)
    _ejecutar(p, t)
    return p


def sin_sangria(d, t, alin=None):
    p = d.add_paragraph()
    _formato(p, alin, sangria=False)
    _ejecutar(p, t)
    return p


def centrado(d, t, negrita=False, cursiva=False, tam=12, mantener=False):
    p = d.add_paragraph()
    _formato(p, WD_ALIGN_PARAGRAPH.CENTER, sangria=False, mantener=mantener)
    _ejecutar(p, t, tam, negrita or None, cursiva or None)
    return p


def _estilo_preliminar(d, nombre="Título 1 preliminar"):
    """Estilo propio basado en Heading 1, con nivel de esquema 9 (el índice de Word no lo lista)."""
    from docx.enum.style import WD_STYLE_TYPE
    if nombre not in [s.name for s in d.styles]:
        est = d.styles.add_style(nombre, WD_STYLE_TYPE.PARAGRAPH)
        est.base_style = d.styles["Heading 1"]
        lvl = OxmlElement("w:outlineLvl")
        lvl.set(qn("w:val"), "9")
        est.element.get_or_add_pPr().append(lvl)
    return d.styles[nombre]


def nivel1(d, t, nueva_pagina=True, estilo=None):
    if estilo == "plano":  # párrafo centrado en negrita sin estilo de encabezado (índices de tablas y de figuras)
        h = centrado(d, t, True, mantener=True)
        h.paragraph_format.page_break_before = nueva_pagina or None
        return h
    if estilo:
        h = d.add_paragraph(style=_estilo_preliminar(d, "Encabezado preliminar" if estilo == "preliminar_base" else "Título 1 preliminar"))
        _formato(h, WD_ALIGN_PARAGRAPH.CENTER, sangria=False, mantener=True)
        h.paragraph_format.page_break_before = nueva_pagina or None
        _ejecutar(h, t, 12, True)
        _ESTADO["heads"].append((1, t))
        return h
    h = d.add_heading(level=1)
    _formato(h, WD_ALIGN_PARAGRAPH.CENTER, sangria=False, mantener=True)
    h.paragraph_format.page_break_before = nueva_pagina or None
    _ejecutar(h, t, 12, True)
    _ESTADO["heads"].append((1, t))
    return h


def nivel2(d, t):
    h = d.add_heading(level=2)
    _formato(h, WD_ALIGN_PARAGRAPH.LEFT, sangria=False, mantener=True)
    _ejecutar(h, t, 12, True)
    _ESTADO["heads"].append((2, t))
    return h


def tabla(d, filas, rotulo, titulo):
    """Rótulo «TABLA I» y título en mayúsculas ARRIBA (8-9 pt), tabla centrada sin bordes verticales."""
    tam = 12 if "rotulos_12" in _ESTADO["ins"] else 9
    centrado(d, rotulo, True, tam=tam, mantener=True)
    centrado(d, titulo, True, tam=9, mantener=True)
    t = d.add_table(rows=len(filas), cols=len(filas[0]))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl_pr = t._tbl.tblPr
    bordes = OxmlElement("w:tblBorders")
    for lado in ("top", "bottom", "insideH"):
        b = OxmlElement("w:" + lado)
        for k, v in (("val", "single"), ("sz", "4"), ("space", "0"), ("color", "808080")):
            b.set(qn("w:" + k), v)
        bordes.append(b)
    tbl_pr.append(bordes)
    for i, fila in enumerate(filas):
        tr = t.rows[i]._tr
        trpr = tr.get_or_add_trPr()
        cs = OxmlElement("w:cantSplit")
        trpr.append(cs)
        for j, v in enumerate(fila):
            c = t.cell(i, j)
            p = c.paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.keep_with_next = i < len(filas) - 1 or None
            _ejecutar(p, v, 9, True if i == 0 else None)
    return t


def figura(d, imagen, pie, pie_arriba=False, apa=None):
    """Figura centrada; pie «Fig. 1. Texto» ABAJO en tipo oración (8-9 pt). Con pie_arriba=True se siembra el defecto."""
    def pie_par():
        centrado(d, pie, tam=12 if "rotulos_12" in _ESTADO["ins"] else 9, mantener=pie_arriba)
    if apa:  # APA: «Figura 1» y su título encima de la imagen
        centrado(d, apa[0], True, tam=9, mantener=True)
        centrado(d, apa[1], False, True, tam=9, mantener=True)
    if pie_arriba:
        pie_par()
    p = d.add_paragraph()
    _formato(p, WD_ALIGN_PARAGRAPH.CENTER, sangria=False, mantener=not pie_arriba)
    p.add_run().add_picture(imagen, width=Cm(10), height=Cm(5))
    if not pie_arriba and not apa:
        pie_par()


RESUMEN = ("El presente protocolo propone el diseño y desarrollo de una aplicación web progresiva con sincronización local y remota "
           "para la gestión de inventarios en microempresas comerciales de Ciudad Ejemplo, Estado. La iniciativa responde a la brecha de "
           "digitalización del sector, donde el control manual genera discrepancias entre el inventario físico y el registrado, así como "
           "demoras en el resurtido de productos críticos. El objetivo general consiste en reducir el porcentaje de discrepancia de "
           "inventario y el tiempo de registro operativo mediante un prototipo funcional con lectura de códigos desde la cámara móvil. "
           "Se empleará un enfoque cuantitativo de alcance explicativo, con una metodología de desarrollo incremental dividida en cuatro "
           "fases y una validación en escenarios reales con usuarios de tres comercios. Las tecnologías previstas incluyen JavaScript, "
           "una base de datos local en el navegador y un servicio de sincronización en la nube. Se espera que el prototipo disminuya al "
           "menos un veinte por ciento las discrepancias y facilite la toma de decisiones operativa en el sector.")
RESUMEN_CORTO = ("El presente protocolo propone el diseño y desarrollo de una aplicación web progresiva para la gestión de inventarios "
                 "en microempresas comerciales de Ciudad Ejemplo, Estado. Se empleará un enfoque cuantitativo y se espera reducir las "
                 "discrepancias de inventario.")
P_CAP = {
    1: "Este capítulo contextualiza la naturaleza tecnológica del proyecto y las razones que justifican su realización en el área de Sistemas y Computación (Pressman & Maxim, 2021).",
    2: "Se describe la situación problemática que motiva la investigación y se delimita el alcance espacial, temporal y tecnológico de la solución propuesta para el estudio.",
    3: "Se establecen los resultados concretos que se alcanzarán al concluir el proyecto, redactados con verbos en infinitivo y con criterios específicos, medibles y temporales.",
    4: "El proyecto se sustenta en el conocimiento existente sobre ingeniería de software, con el contraste de los autores revisados (Kurose & Ross, 2021; Pressman & Maxim, 2021; Sommerville, 2016).",
    5: "La formulación de este capítulo depende del alcance del estudio: se redactará una proposición afirmativa verificable con sus variables, indicadores y unidades de medida.",
    6: "Se describirá de manera reproducible el procedimiento técnico mediante el cual se ejecutará la investigación y se construirá la solución tecnológica del proyecto (Hernández-Sampieri & Mendoza, 2023).",
    7: "Se evaluarán las repercusiones del proyecto en su entorno y se garantizará el cumplimiento de los estándares profesionales y normativos de la ingeniería de software.",
    10: "Dado que el protocolo es un documento de planeación previa, se argumentará la factibilidad técnica, operativa y económica de la propuesta en tiempo futuro.",
}


def _numeracion(sec, fmt, inicio):
    """w:pgNumType de la sección: formato del número de página y, si se da, el número en que empieza."""
    el = sec._sectPr
    for x in el.findall(qn("w:pgNumType")):
        el.remove(x)
    pg = OxmlElement("w:pgNumType")
    pg.set(qn("w:fmt"), fmt)
    if inicio:
        pg.set(qn("w:start"), str(inicio))
    cols = el.find(qn("w:cols"))
    (cols.addprevious(pg) if cols is not None else el.append(pg))


def _caja(par_o_celda, relleno=None, borde_izq=None):
    """Relleno (shd) y/o borde izquierdo (color, grosor en pt) en un párrafo o en la celda de una tabla."""
    el = par_o_celda._p if hasattr(par_o_celda, "_p") else par_o_celda._tc
    pr = el.get_or_add_pPr() if hasattr(par_o_celda, "_p") else el.get_or_add_tcPr()
    if relleno:
        shd = OxmlElement("w:shd")
        shd.set(qn("w:val"), "clear")
        shd.set(qn("w:color"), "auto")
        shd.set(qn("w:fill"), relleno)
        pr.append(shd)
    if borde_izq:
        cont = OxmlElement("w:pBdr" if hasattr(par_o_celda, "_p") else "w:tcBorders")
        b = OxmlElement("w:left")
        for k, v in (("val", "single"), ("sz", str(int(borde_izq[1] * 8))), ("space", "4"), ("color", borde_izq[0])):
            b.set(qn("w:" + k), v)
        cont.append(b)
        if hasattr(par_o_celda, "_p"):
            pr.insert(0, cont)
        else:
            shd = pr.find(qn("w:shd"))
            (shd.addprevious(cont) if shd is not None else pr.append(cont))


def _portada(d, ins):
    """Portada oficial en el orden de la guía: institución, instituto, departamento, docente, título, leyenda, integrantes, lugar y fecha."""
    titulo = ("Sistema web progresivo para la gestión de inventarios en microempresas de Ciudad Ejemplo" if "titulo" not in ins else
              "Sistema web progresivo con sincronización local y remota para la gestión integral de inventarios, pedidos y "
              "resurtido en microempresas comerciales de Ciudad Ejemplo, Estado")
    leyenda = "Protocolo de Investigación para la asignatura Taller de Investigación I"
    integrantes = "Integrantes: Ana Pérez López (control 21330001), Luis Gómez Ruiz" + ("" if "sin_control" in ins else " (control 21330002)")
    lugar = ["Ciudad Ejemplo, Estado, noviembre de 2026"] if "fecha_mal" not in ins else ["Ciudad Ejemplo, Estado", "03/Noviembre/2026"]
    modelo = "modelo_caja" in ins
    lineas = [("SISTEMA TECNOLÓGICO NACIONAL (EJEMPLO)", True), ("INSTITUTO TECNOLÓGICO DE EJEMPLO", True)]
    if "sin_depto" not in ins:
        lineas.append(("Departamento de Sistemas y Computación", False))
    lineas += [("Docente: Nombre del docente", False), ("", False)]
    bloque = []
    if "sin_titulo" not in ins:
        bloque.append(("titulo", titulo, True))
    if "sin_leyenda" not in ins:
        bloque.append(("leyenda", leyenda, False))
    if "portada_orden" in ins:
        bloque.reverse()
    for t, neg in lineas:
        centrado(d, t, neg)
    for tipo, t, neg in bloque:
        if tipo == "titulo" and modelo:
            p = centrado(d, t, True, tam=14)
            p.runs[0].font.color.rgb = RGBColor(0x1B, 0x36, 0x5D)
        elif tipo == "leyenda" and modelo:
            _caja(centrado(d, t, neg), "F4F6F9", ("1B365D", 3))
        else:
            centrado(d, t, neg)
        if tipo == "titulo":
            centrado(d, "", False)
    if "portada_caja" in ins:  # integrantes en una tabla-caja con relleno y barra izquierda
        tb = d.add_table(rows=1, cols=1)
        celda = tb.cell(0, 0)
        _caja(celda, "F4F6F9", ("1B365D", 3))
        etiqueta, resto = integrantes.split(": ", 1)
        celda.paragraphs[0].text = ""
        _ejecutar(celda.paragraphs[0], etiqueta + ":", 12, True)
        for x in (m for m in resto.replace("), ", ")|").split("|")):
            _ejecutar(celda.add_paragraph(), x, 12)
    else:
        centrado(d, integrantes, False)
    for t in lugar:
        centrado(d, t, False)


def crear(destino, sembrado=False, ins=()):
    ins = frozenset(ins)
    _ESTADO["ins"] = ins
    _ESTADO["heads"] = []
    d = docx.Document()
    s = d.sections[0]
    for m in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
        setattr(s, m, Cm(2.54))
    _fuente(d.styles["Normal"])
    for nombre in ("Heading 1", "Heading 2", "Heading 3"):
        _fuente(d.styles[nombre], 12, True, False)
    # portada sin número; el resto con número arriba a la derecha
    s.different_first_page_header_footer = True
    hp = s.header.paragraphs[0]
    hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    if "enc_gris" in ins:  # encabezado como el del piloto real: Arial 8 pt gris
        r = hp.add_run("Protocolo de investigación ")
        r.font.name, r.font.size, r.font.color.rgb = "Arial", Pt(8), RGBColor(0x8C, 0x8C, 0x8C)
    crear_maquetacion.campo(hp, "PAGE")
    _portada(d, ins)
    # preliminares: sección propia con números romanos minúsculos (i, ii, iii…)
    sec = d.add_section(WD_SECTION.NEW_PAGE)
    sec.different_first_page_header_footer = False
    _numeracion(sec, "decimal" if "romanos" in ins else "lowerRoman", 1)
    pe = "prelim_estilo" in ins
    nivel1(d, "RESUMEN", "portada_caja" not in ins, "preliminar" if pe else None)
    resumen = RESUMEN_CORTO if sembrado is True else RESUMEN
    if "resumen_sangria" in ins:
        texto(d, resumen)
    elif "resumen_dos" in ins:
        mitad = resumen.index(". ", len(resumen) // 2) + 1
        sin_sangria(d, resumen[:mitad])
        sin_sangria(d, resumen[mitad:].strip())
    else:
        sin_sangria(d, resumen)
    sin_sangria(d, "Palabras clave: inventarios; aplicación web progresiva" + ("" if sembrado is True else "; sincronización; microempresas") + ".",
                WD_ALIGN_PARAGRAPH.LEFT)
    toc_h = nivel1(d, "ÍNDICE DE CONTENIDO", True, "preliminar_base" if pe else None)
    nivel1(d, "ÍNDICE DE TABLAS", True, "plano" if pe else None)
    centrado(d, "TABLA I. Cronograma de actividades por fases 	 12", False)
    centrado(d, "TABLA III. Presupuesto consolidado en MXN 	 13" if "indice_tablas" in ins else "TABLA II. Presupuesto consolidado en MXN 	 13", False)
    nivel1(d, "ÍNDICE DE FIGURAS", True, "plano" if pe else None)
    centrado(d, "Fig. 1. Diagrama de Gantt del proyecto 	 12", False)
    n_pre = len(_ESTADO["heads"])

    def cap(n, titulo, subs=(), cuerpo=None):
        rotulo = f"{n}. {titulo.upper()}"
        if n == 1 and "minusculas" in ins:
            rotulo = f"{n}. {titulo}"
        if (n == 2 and "sinnumero" in ins) or "sinnumeracion" in ins:
            rotulo = titulo.upper()
        nivel1(d, rotulo, not (n == 4 and "sinsalto" in ins))
        texto(d, cuerpo or P_CAP[n])
        for i, sub in enumerate(subs, 1):
            # sinnumeracion: ni capítulos ni subcapítulos numerados (caso del piloto real, con plantilla APA)
            nivel2(d, sub if "sinnumeracion" in ins else f"{2 if n == 3 and 'num2' in ins else n}.{i}. {sub}")
            texto(d, f"Este apartado desarrolla el tema «{sub.lower()}» de forma que se pueda verificar cada una de las afirmaciones del capítulo.")

    # cuerpo: sección propia con números arábigos que empiezan en 1
    sec = d.add_section(WD_SECTION.NEW_PAGE)
    sec.different_first_page_header_footer = False
    _numeracion(sec, "decimal", None if "sinreinicio" in ins else 1)
    cap(1, "Presentación del proyecto", ["Antecedentes y contexto general", "Propósito y justificación"])
    cap(2, "Planteamiento del problema", ["Descripción y delimitación del problema", "Pregunta(s) de investigación"])
    cap(3, "Objetivos y metas", ["Objetivo general", "Objetivos específicos", "Metas de la investigación"])
    cap(4, "Marco teórico", ["Estado del arte", "Bases teóricas y conceptuales", "Marco tecnológico"])
    cap(5, "Hipótesis o supuestos de investigación", ["Formulación de la hipótesis", "Supuesto de investigación",
                                                      "Definición operacional de variables e indicadores"])
    cap(6, "Diseño metodológico", ["Enfoque, alcance y tipo de estudio", "Población, muestra y escenario de pruebas",
                                   "Metodología de desarrollo tecnológico y procedimientos",
                                   "Técnicas e instrumentos de recolección de datos", "Técnicas de procesamiento y análisis de datos"])
    cap(7, "Impacto social, tecnológico y ético", ["Impacto social y económico", "Innovación y aporte tecnológico",
                                                   "Factibilidad, escalabilidad y consideraciones éticas"])
    # capítulo 8: tabla y Gantt, mencionados antes de aparecer
    nivel1(d, "8. " + ("PLANEACIÓN SEMANAL" if sembrado is True else "CRONOGRAMA DE ACTIVIDADES"))
    tardia = sembrado == "tardia"  # defecto: TABLA I y Fig. 1 se mencionan solo después de aparecer
    texto(d, ("Las actividades y los entregables por fase se presentan a continuación, junto con el diagrama de Gantt correspondiente "
              "a los diez meses de ejecución previstos para el proyecto." if tardia else
              ("La Tabla 1 describe las actividades y los entregables por fase, y la Figura 1 presenta el diagrama de Gantt correspondiente "
               if "apa_rotulos" in ins else
               "La TABLA I describe las actividades y los entregables por fase, y la Fig. 1 presenta el diagrama de Gantt correspondiente ")
              +
              "a los diez meses de ejecución previstos para el proyecto."))
    tabla(d, [("Fase", "Periodo", "Entregable"), ("1. Diagnóstico y requerimientos", "Meses 1-2", "Documento SRS"),
              ("2. Diseño de arquitectura", "Meses 3-4", "Diagramas UML"), ("3. Desarrollo e integración", "Meses 5-8", "Prototipo v1.0"),
              ("4. Pruebas y documentación", "Meses 9-10", "Informe de pruebas")],
          "Tabla 1" if sembrado is True or "apa_rotulos" in ins else "TABLA I",
          "Cronograma de actividades por fases" if "apa_rotulos" in ins else "CRONOGRAMA DE ACTIVIDADES POR FASES")
    png = pathlib.Path(tempfile.mkdtemp()) / "gantt.png"
    png.write_bytes(_png())
    figura(d, str(png), "Fig. 1. Diagrama de Gantt del proyecto", pie_arriba=sembrado is True,
           apa=("Figura 1", "Diagrama de Gantt del proyecto") if "apa_rotulos" in ins else None)
    # capítulo 9
    nivel1(d, "9. RECURSOS NECESARIOS Y PRESUPUESTO")
    texto(d, "Se desglosan los recursos humanos, tecnológicos y financieros que se requieren para garantizar la viabilidad operativa del proyecto en las cuatro fases.")
    nivel2(d, "9.1. Recursos humanos")
    texto(d, "El equipo se integrará por un líder de proyecto, dos desarrolladores y un asesor, con las horas-hombre estimadas para cada fase del cronograma.")
    nivel2(d, "9.2. Recursos tecnológicos")
    texto(d, "Se emplearán equipos de cómputo propios, un servicio de nube con plan gratuito y dispositivos móviles de prueba, con su costo de oportunidad estimado.")
    nivel2(d, "9.3. Presupuesto consolidado")
    texto(d, f"La {'Tabla 2' if 'apa_rotulos' in ins else 'TABLA II'} muestra el presupuesto consolidado en pesos mexicanos (MXN), con concepto, cantidad, costo unitario, subtotal y fuente de financiamiento"
             + (", y retoma las actividades de la TABLA I y la Fig. 1." if tardia else "."))
    tabla(d, [("Concepto", "Cantidad", "Costo unitario (MXN)", "Subtotal (MXN)"), ("Equipo de cómputo", "4", "12,000", "48,000"),
              ("Servicio en la nube", "10", "300", "3,000"), ("Dispositivos de prueba", "3", "4,000", "12,000"),
              ("Total", "", "", "63,000")],
          "Tabla 2" if "apa_rotulos" in ins else "TABLA II", "Presupuesto consolidado en MXN" if "apa_rotulos" in ins else "PRESUPUESTO CONSOLIDADO EN MXN")
    cap(10, "Conclusiones preliminares y viabilidad")
    if "persona" in ins:
        texto(d, "En este capítulo nosotros realizaremos la valoración final y proponemos continuar con el desarrollo del prototipo en el siguiente periodo.")
    # capítulo 11: fuentes de información (APA 7, sangría francesa 1.27 cm)
    nivel1(d, "11. FUENTES DE INFORMACIÓN")
    refs = ["Hernández-Sampieri, R., & Mendoza, C. P. (2023). Metodología de la investigación: Las rutas cuantitativa, cualitativa y mixta (2.ª ed.). McGraw-Hill.",
            "Kurose, J. F., & Ross, K. W. (2021). Computer networking: A top-down approach (8th ed.). Pearson.",
            "Pressman, R. S., & Maxim, B. R. (2021). Ingeniería del software: Un enfoque práctico (9.ª ed.). McGraw-Hill.",
            "Sommerville, I. (2016). Software engineering (10th ed.). Pearson."]
    if "viejas" in ins:
        refs = [r.replace("(2023)", "(2013)").replace("(2021)", "(2011)") for r in refs]
    for ref in refs:
        p = d.add_paragraph()
        _formato(p, WD_ALIGN_PARAGRAPH.JUSTIFY, sangria=False)
        p.paragraph_format.left_indent = Cm(1.27)
        p.paragraph_format.first_line_indent = Cm(-1.27)
        _ejecutar(p, ref)
    nivel1(d, "12. ANEXOS")
    texto(d, "Se incluyen los instrumentos de recolección de datos en el Anexo A, y los bocetos de interfaz en el Anexo B, según se indica en el diseño metodológico.")
    p = sin_sangria(d, "Anexo A. Instrumentos de recolección de datos", WD_ALIGN_PARAGRAPH.LEFT)
    p.runs[0].bold = True
    p = sin_sangria(d, "Anexo B. Bocetos de interfaz", WD_ALIGN_PARAGRAPH.LEFT)
    p.runs[0].bold = True
    # índice de contenido: una entrada por encabezado de nivel 1 y 2 del cuerpo (o la estructura vieja con «indice_viejo»)
    viejo = ["2.1 Antecedentes del problema", "2.2 Planteamiento del problema", "2.3 Objetivos de la investigación", "2.4 Justificación"]
    entradas = viejo if "indice_viejo" in ins else [t for _, t in _ESTADO["heads"][n_pre:]]
    ref = toc_h._p
    for k, t in reversed(list(enumerate(entradas))):
        q = d.add_paragraph()
        _formato(q, WD_ALIGN_PARAGRAPH.LEFT, sangria=False)
        _ejecutar(q, f"{t}	{k + 1}")
        ref.addnext(q._p)
    d.save(str(destino))
    return destino


if __name__ == "__main__":
    out = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path("protocolo-ith.docx")
    print("escrito", crear(out, "--sembrado" in sys.argv or ("tardia" if "--tardia" in sys.argv else False),
                           [a[6:] for a in sys.argv if a.startswith("--ins=")]))
