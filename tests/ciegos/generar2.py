# -*- coding: utf-8 -*-
"""Generador CIEGO ronda 2 (sembrado segun la norma, no segun el juez).
Uso: python -I tests/ciegos/generar2.py   -> tests/ciegos/docs2/*.docx + esperado.json
Referencias con prefijo '#N|' llevan la etiqueta [N] explicita (numeracion saltada);
con prefijo '~' van sin etiqueta.
"""
import json
import os
import sys
import re
from pathlib import Path

from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

HERE = Path(os.path.abspath(__file__)).parent
ROOT = HERE.parent.parent
OUT = HERE / "docs2"
sys.path.insert(0, str(ROOT / "scripts"))
import crear_plantillas  # noqa: E402
PLANT = crear_plantillas.asegurar_plantillas()


def vaciar(doc):
    body = doc.element.body
    for el in list(body):
        if not el.tag.endswith("}sectPr"):
            body.remove(el)


def add_runs(par, text):
    for p in re.split(r"(\*[^*]+\*)", text):
        if not p:
            continue
        if p.startswith("*") and p.endswith("*") and len(p) > 2:
            par.add_run(p[1:-1]).italic = True
        else:
            par.add_run(p)


def add_par(doc, text, style):
    par = doc.add_paragraph(style=style)
    add_runs(par, text)
    return par


def construir(spec):
    doc = Document(str(PLANT / (spec["plantilla"] + ".docx")))
    vaciar(doc)
    add_par(doc, spec["titulo"], "Title")
    add_par(doc, spec["autor"], "Author")
    pend = False
    cuerpo = []
    for item in spec["items"]:
        kind, text = item[0], item[1]
        tag = item[2] if len(item) > 2 else None
        if kind == "h1":
            add_par(doc, text, "Heading 1"); pend = True
        elif kind == "h2":
            add_par(doc, text, "Heading 2"); pend = True
        elif kind == "cap":      # rotulo de tabla (parrafo suelto, no cuenta como cuerpo)
            p = doc.add_paragraph(style="Table Caption")
            r = p.add_run(text)
            r.bold = tag == "bold"
        elif kind == "tbl":
            t = doc.add_table(rows=len(text), cols=len(text[0]))
            for i, fila in enumerate(text):
                for j, v in enumerate(fila):
                    t.cell(i, j).text = v
        else:
            st = "First Paragraph" if pend else "Body Text"
            pend = False
            cuerpo.append((add_par(doc, text, st), tag))
    h = add_par(doc, spec["ref_titulo"], "Heading 1")
    if spec.get("salto_pagina"):
        h.paragraph_format.page_break_before = True
    refs = []
    for i, r in enumerate(spec["refs"], 1):
        m = re.match(r"^#(\d+)\|", r)
        if r.startswith("~"):
            txt = r[1:]
        elif m:
            txt = "[%s]\t%s" % (m.group(1), r[m.end():])
        elif spec.get("numerar") == "tab":
            txt = "[%d]\t%s" % (i, r)
        elif spec.get("numerar") == "esp":
            txt = "[%d] %s" % (i, r)
        else:
            txt = r
        refs.append(add_par(doc, txt, "Bibliography"))
    for m in spec.get("mutaciones", []):
        MUT[m](doc, cuerpo, refs)
    return doc


def m_margen_sup(doc, c, r):       # APA-001 (margen superior)
    doc.sections[0].top_margin = Inches(1.5)


def m_arial12(doc, c, r):          # APA-002 (Arial 12; Arial solo vale a 11)
    for par in doc.paragraphs:
        for run in par.runs:
            run.font.name = "Arial"
            run.font.size = Pt(12)


def m_lista15(doc, c, r):          # APA-004 (lista a 1.5)
    for p in r:
        p.paragraph_format.line_spacing = 1.5


def m_pag_izq(doc, c, r):          # APA-008 (numero a la izquierda)
    doc.sections[0].header.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.LEFT


def m_refs_primera(doc, c, r):     # APA-060 (sangria de primera linea, no francesa)
    for p in r:
        p.paragraph_format.left_indent = Inches(0)
        p.paragraph_format.first_line_indent = Inches(0.5)


def m_calibri(doc, c, r):          # APA-003 (Calibri 11, permitida, junto a TNR 12)
    for par, tag in c:
        if tag == "calibri":
            for run in par.runs:
                run.font.name = "Calibri"
                run.font.size = Pt(11)


def m_justificado(doc, c, r):      # APA-006
    for par, tag in c:
        if tag == "justify":
            par.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY


def m_sin_sangria(doc, c, r):      # APA-007 (sangria 0, sin espacios)
    for par, tag in c:
        if tag == "noindent":
            par.paragraph_format.first_line_indent = Inches(0)


MUT = {"margen_sup": m_margen_sup, "arial12": m_arial12, "lista15": m_lista15,
       "pag_izq": m_pag_izq, "refs_primera": m_refs_primera, "calibri": m_calibri,
       "justificado": m_justificado, "sin_sangria": m_sin_sangria}

INEGI = "Instituto Nacional de Estadística y Geografía"
CFE = "Comisión Federal de Electricidad"

# ---------------------------------------------------------------- 1 apa7_correcto
D1 = dict(
    plantilla="apa7", salida="apa7_correcto.docx", perfil="apa7",
    titulo="Brecha digital y educación a distancia en escuelas rurales",
    autor="Paola Quintanilla Reyes",
    ref_titulo="Referencias", salto_pagina=True, numerar=None,
    items=[
        ("h1", "Introducción"),
        ("p", "La educación a distancia se expandió de forma abrupta durante la pandemia, pero su alcance en zonas rurales quedó condicionado por el acceso a internet y a energía eléctrica. Según el " + INEGI + " (2020), menos de la mitad de los hogares rurales contaba con conexión a internet, una cifra que contrasta con el promedio urbano (" + INEGI + ", 2020)."),
        ("p", "La electrificación es una condición previa. La " + CFE + " (CFE, 2019) reportó que más del 99 % de las viviendas del país tenía servicio eléctrico, aunque la CFE (2019) advierte que la calidad del suministro varía entre regiones."),
        ("h1", "Marco teórico"),
        ("h2", "Conectividad y aprendizaje"),
        ("p", "Díaz (2015) encontró una asociación positiva entre conectividad y rendimiento escolar, aun controlando por nivel socioeconómico (véase García-Márquez, 2016). La literatura previa coincide en este punto (Díaz, 2015; Ortega, 2017)."),
        ("p", "Los fundamentos pedagógicos de la educación mediada por tecnología se desarrollan en el tercer capítulo de la obra de referencia (Ramírez, 2018, cap. 3), mientras que la historia regional puede consultarse en Ponce de León (2014) y en otros trabajos recientes (Ponce de León, 2014)."),
        ("h2", "Formación docente"),
        ("p", "Los docentes rurales requieren materiales adaptados. Existen guías y orientaciones abiertas para el uso de la radio educativa y la telesecundaria (Ortega, s.f.-a, s.f.-b), y la formación continua mejora la apropiación de las herramientas (véase Ortega, 2017)."),
        ("h1", "Método"),
        ("p", "Se revisaron informes oficiales y artículos publicados entre 2014 y 2020, y se complementó el análisis con prensa regional. Un reportaje señala que varias escuelas rurales improvisaron aulas comunitarias con radio y cuadernillos (Ruiz, 2020, párr. 4)."),
        ("h1", "Discusión"),
        ("p", "Los resultados sugieren que la conectividad por sí sola no basta: se requieren energía estable, contenidos pertinentes y docentes capacitados (García-Márquez, 2016; Ponce de León, 2014)."),
        ("h1", "Conclusiones"),
        ("p", "Reducir la brecha digital rural exige políticas coordinadas de infraestructura, contenidos y formación docente. Futuros estudios deberían medir el efecto de la radio educativa frente a las plataformas en línea."),
    ],
    refs=[
        CFE + ". (2019). *Informe anual 2019: Cobertura del servicio eléctrico*. https://www.cfe.mx/informe2019",
        "Díaz, R. (2015). Conectividad y rendimiento escolar en comunidades rurales. *Revista Latinoamericana de Educación, 20*(1), 22–41. https://doi.org/10.1234/rle.2015.201",
        "García-Márquez, L. (2016). Plataformas de aprendizaje en línea para educación básica. *Tecnología y Aprendizaje, 4*(2), 55–70. https://doi.org/10.1234/ta.2016.42",
        INEGI + ". (2020). *Encuesta nacional sobre disponibilidad y uso de tecnologías de la información en los hogares 2020*. https://www.inegi.org.mx/programas/dutih/2020/",
        "Ortega, A. (s.f.-a). *Guía para docentes de telesecundaria*. https://ejemplo.org/guia-docentes",
        "Ortega, A. (s.f.-b). *Orientaciones para el uso de la radio educativa*. https://ejemplo.org/radio-educativa",
        "Ortega, A. (2017). Docentes rurales y formación continua. *Perfiles Educativos, 39*(155), 90–107. https://doi.org/10.1234/pe.2017.155",
        "Ponce de León, M. (2014). *Educación a distancia en América Latina*. Fondo Editorial Andino.",
        "Ramírez, J. (2018). *Pedagogía de la conectividad*. Editorial Mar Abierto.",
        "Ruiz, T. (2020, 14 de mayo). Escuelas rurales ante la pandemia. *Diario del Campo*. https://diariodelcampo.example.org/escuelas-rurales",
    ],
    mutaciones=[], errores=[],
)

# ---------------------------------------------------------------- 2 apa7_errores
D2 = dict(
    plantilla="apa7", salida="apa7_errores.docx", perfil="apa7",
    titulo="Ciberacoso entre adolescentes y bienestar subjetivo",
    autor="Iván Ledesma Arce",
    ref_titulo="Referencias", salto_pagina=True, numerar=None,
    items=[
        ("h1", "Introducción"),
        ("p", "El ciberacoso se ha consolidado como una de las formas de violencia escolar más frecuentes entre adolescentes. El " + INEGI + " (2021) estimó que una proporción importante de los usuarios de internet de 12 a 19 años vivió alguna situación de acoso digital (" + INEGI + ", 2021)."),
        ("p", "Smith and Jones (2018) documentaron que las víctimas presentan menor bienestar subjetivo a lo largo del tiempo (Smith and Jones, 2018). Este patrón se observa también en estudios de la región (Cárdenas & Mora, 2020; Valdés, 2016)."),
        ("h1", "Antecedentes"),
        ("p", "Aguilar (2019) vincula la violencia escolar con el uso intensivo de redes sociales y desarrolla los factores de riesgo familiares en el segundo capítulo (Aguilar, 2019, cap. 2). El papel de la familia es central (véase Valdés, 2016)."),
        ("p", "Según la misma fuente (ibíd., p. 33), la supervisión parental reduce la exposición a contenidos agresivos. Cárdenas y Mora (2020) coinciden en que el diálogo en casa protege a los adolescentes."),
        ("h2", "Prevención"),
        ("p", "Los protocolos de actuación recomiendan registrar el incidente, notificar a la familia y activar la red de apoyo escolar (Torres, s.f.)."),
        ("h2", "Detección"),
        ("p", "La detección temprana depende de que docentes y familias reconozcan las señales de alerta (Cárdenas & Mora, 2020)."),
        ("h1", "Método"),
        ("p", "Se aplicó una encuesta a 320 estudiantes de tres secundarias públicas. El instrumento midió victimización, agresión y bienestar subjetivo con escalas de cinco puntos."),
        ("h1", "Resultados"),
        ("p", "La prevalencia observada en la muestra (18 %) es similar a la reportada por Cárdenas y Mora (2020). Las diferencias por sexo no fueron significativas."),
        ("h1", "Conclusiones"),
        ("p", "El ciberacoso afecta el bienestar de los adolescentes y requiere intervenciones coordinadas entre escuela y familia."),
    ],
    refs=[
        "Aguilar, P. (2019). *Violencia escolar y redes sociales*. Editorial Educa.",
        "Cárdenas, L., & Mora, J. (2020). Prevalencia de ciberacoso en secundaria. *Revista de Psicología Escolar, 8*(1), 15–33. https://doi.org/10.5555/rpe.2020.81",
        "Gutiérrez, H. (2017). Intervenciones escolares contra el acoso. En S. Vega (Ed.), *Convivencia y escuela* (pp. 120–148). Editorial Nuevo Mundo.",
        INEGI + ". (2021). *Módulo sobre ciberacoso 2020*. https://www.inegi.org.mx/programas/mociba/2020/",
        "Smith, J., & Jones, K. (2018). Cyberbullying and adolescent well-being: A longitudinal study. *Journal of Youth Studies, 21*(3), 301–319. https://doi.org/10.1080/13676261.2017.1387919",
        "Torres, E. (s.f.). *Protocolo de actuación ante el ciberacoso*. https://ejemplo.org/protocolo",
        "Valdés, R. (2016). Familia y ciberacoso. *Psicología y Sociedad, 13*(2), 66–80. https://doi.org/10.5555/ps.2016.132",
    ],
    mutaciones=["margen_sup", "arial12", "lista15", "pag_izq", "refs_primera"],
    errores=[
        {"id": "APA-001", "desc": "Margen superior de 1,5 in (los demas 1 in)."},
        {"id": "APA-002", "desc": "Todo el texto en Arial 12 pt (Arial solo es valida a 11 pt); una sola fuente, sin APA-003."},
        {"id": "APA-004", "desc": "Las entradas de la lista de referencias con interlineado 1,5 (el cuerpo sigue en doble)."},
        {"id": "APA-008", "desc": "Campo PAGE presente pero encabezado alineado a la izquierda (no a la derecha)."},
        {"id": "APA-034", "desc": "Entrada 'Gutiérrez (2017)' nunca citada en el texto; las demas entradas si estan citadas."},
        {"id": "APA-037", "desc": "'(Smith and Jones, 2018)': 'and' dentro de cita parentetica en ingles dentro de texto en español (debe ser '&'). La narrativa 'Smith and Jones (2018)' es valida y tambien aparece."},
        {"id": "APA-042", "desc": "'(ibíd., p. 33)' en Antecedentes. Colateral posible: un juez podria tomarlo por cita sin entrada (APA-034); se siembra solo APA-042."},
        {"id": "APA-060", "desc": "Entradas de la lista con sangria de primera linea 0,5 in y margen izquierdo 0 (sangria normal de parrafo, no francesa)."},
    ],
)

# ---------------------------------------------------------------- 3 ieee_correcto
D3 = dict(
    plantilla="ieee", salida="ieee_correcto.docx", perfil="ieee",
    titulo="Mantenimiento predictivo de aerogeneradores con autoencoders",
    autor="Tomás Åkerman Villegas",
    ref_titulo="Referencias", salto_pagina=False, numerar="tab",
    items=[
        ("h1", "Introducción"),
        ("p", "El mantenimiento predictivo reduce los paros no programados en aerogeneradores mediante el análisis continuo de señales de vibración y temperatura [1]. Los modelos de aprendizaje automático han ganado terreno frente a los umbrales fijos [2, p. 14]."),
        ("p", "Diversas técnicas pueden aplicarse a los datos del sistema SCADA, e.g., [3]. Entre las más usadas se encuentran los bosques aleatorios y las redes neuronales [3], [4]."),
        ("h1", "Métodos"),
        ("p", "El detector de anomalías se basa en un autoencoder cuyo error de reconstrucción se compara con un umbral, como se describe en [5, Sec. III]. Los métodos de referencia son: [4], [6]."),
        ("h2", "Función de pérdida"),
        ("p", "La función de pérdida es el error cuadrático medio entre la entrada y su reconstrucción:"),
        ("p", "L = (1/N) Σ ‖xᵢ − x̂ᵢ‖²\t(3)"),
        ("p", "Eq. (3) se minimiza durante el entrenamiento, y su derivación sigue [7]. El umbral se fija en el percentil 99 del error obtenido con datos sanos [8]."),
        ("h1", "Resultados"),
        ("p", "La Tabla I resume el desempeño de los métodos en un parque de 24 turbinas."),
        ("cap", "TABLA I. DESEMPEÑO POR MÉTODO"),
        ("tbl", [["Método", "F1", "Fuente"], ["Bosque aleatorio", "0,91", "[4]"], ["Autoencoder", "0,94", "[5]"], ["Línea base por umbral", "0,78", "[2], [6]"]]),
        ("p", "Los resultados concuerdan con lo reportado en campo [9] y con el análisis económico de [10]. Un estudio posterior [11] confirma la reducción de costos de mantenimiento."),
        ("h1", "Conclusiones"),
        ("p", "Como se muestra en [9], el mantenimiento predictivo es viable a escala comercial. La evidencia [1], [3] y [11] respalda su adopción, y Ref. [10] cuantifica el ahorro esperado."),
    ],
    refs=[
        "IEC, “Wind energy generation systems – Part 25-1: Communications for monitoring and control of wind power plants,” IEC, Geneva, Switzerland, IEC 61400-25-1, 2017.",
        "Y. Zhao, D. Li, A. Dong, D. Kang, Q. Lv, and L. Shang, “Fault prediction and diagnosis of wind turbine generators using SCADA data,” *Energies*, vol. 10, no. 8, Art. no. 1210, Aug. 2017, doi: 10.3390/en10081210.",
        "M. Schlechtingen and I. Ferreira Santos, “Comparative analysis of neural network and regression based condition monitoring approaches for wind turbine fault detection,” *Mech. Syst. Signal Process.*, vol. 25, no. 5, pp. 1849–1875, Jul. 2011, doi: 10.1016/j.ymssp.2010.12.007.",
        "L. Breiman, “Random forests,” *Mach. Learn.*, vol. 45, no. 1, pp. 5–32, Oct. 2001, doi: 10.1023/A:1010933404324.",
        "J. Ibáñez, M. Ñancupil, and C. De la Cruz, “Detección de anomalías en aerogeneradores mediante autoencoders,” in *Proc. IEEE ANDESCON*, Quito, Ecuador, 2020, pp. 1–6, doi: 10.1109/ANDESCON50619.2020.9272101.",
        "I. Goodfellow, Y. Bengio, and A. Courville, *Deep Learning*. Cambridge, MA, USA: MIT Press, 2016.",
        "C. M. Bishop, *Pattern Recognition and Machine Learning*. New York, NY, USA: Springer, 2006.",
        "R. van der Berg, “Umbrales adaptativos para el monitoreo de condición,” in *Mantenimiento Industrial Avanzado*, P. Soto, Ed. Madrid, Spain: Ed. Técnica, 2019, pp. 201–230.",
        "Global Wind Energy Council, “Global wind report 2023,” GWEC. Accessed: Apr. 18, 2023. [Online]. Available: https://gwec.net/global-wind-report-2023",
        "A. Pérez-Luna, “Costos de operación y mantenimiento en parques eólicos,” *Energía Hoy*, vol. 5, no. 2, pp. 33–47, 2021, doi: 10.7777/eh.2021.52.",
        "S. Gómez and T. Åkesson, “Condition monitoring cost savings in offshore wind: A case study,” *Wind Energy*, vol. 24, no. 6, pp. 589–602, Jun. 2021, doi: 10.1002/we.2591.",
    ],
    mutaciones=[], errores=[],
)

# ---------------------------------------------------------------- 4 ieee_errores
D4 = dict(
    plantilla="ieee", salida="ieee_errores.docx", perfil="ieee",
    titulo="Gemelos digitales para la puesta en marcha de líneas de manufactura",
    autor="Nicolás Ñíguez Barrera",
    ref_titulo="Referencias", salto_pagina=False, numerar="tab",
    items=[
        ("h1", "Introducción"),
        ("p", "Un gemelo digital es una réplica virtual de un activo físico que se actualiza con datos en tiempo real [1]. Su adopción en manufactura crece por la promesa de reducir los tiempos de puesta en marcha [3]."),
        ("p", "La sincronización entre planta y modelo se resuelve con arquitecturas de bus de datos industriales [2]. Ref. [1] introduce el concepto y [4] lo extiende a líneas de ensamble aeroespacial."),
        ("h1", "Arquitectura"),
        ("p", "Se distinguen tres capas: adquisición, modelado y servicio, como se muestra en [5]. En la capa de modelado se emplean simulaciones de eventos discretos,[6] aunque también se usan modelos híbridos."),
        ("p", "Los costos de implantación y los beneficios esperados se analizan en [8]. Las referencias [2,3] coinciden en que la calidad de los datos es el principal riesgo del proyecto."),
        ("h1", "Casos de aplicación"),
        ("p", "Los estudios de caso en automoción [9] muestran reducciones de paros del 20 %. Las referencias [4]-[6] ofrecen guías de implantación por etapas."),
        ("p", "Como se muestra en [9], la integración con sistemas MES es determinante. En conjunto, [1], [5] describen el marco conceptual."),
    ],
    refs=[
        "M. Grieves and J. Vickers, “Digital twin: Mitigating unpredictable, undesirable emergent behavior in complex systems,” in *Transdisciplinary Perspectives on Complex Systems*, F.-J. Kahlen, S. Flumerfelt, and A. Alves, Eds. Cham, Switzerland: Springer, 2017, pp. 85–113.",
        "F. Tao, H. Zhang, A. Liu, and A. Y. C. Nee, “Digital twin in industry: State-of-the-art,” *IEEE Trans. Ind. Informat.*, vol. 15, no. 4, pp. 2405–2415, Apr. 2019, doi: 10.1109/TII.2018.2873186.",
        "J. Núñez and R. Ibáñez, “Gemelos digitales para la puesta en marcha virtual de líneas de producción,” *Rev. Iberoam. Autom. Inform. Ind.*, vol. 18, no. 3, pp. 245–256, Jul. 2021, https://doi.org/10.4995/riai.2021.15432",
        "E. Glaessgen and D. Stargel, “The digital twin paradigm for future NASA and U.S. Air Force vehicles,” in *Proc. 53rd AIAA/ASME/ASCE/AHS/ASC Struct., Struct. Dyn. Mater. Conf.*, Honolulu, HI, USA, 2012, pp. 1–14, doi: 10.2514/6.2012-1818.",
        "S. Boschert and R. Rosen, “Digital twin—The simulation aspect,” in *Mechatronic Futures*, P. Hehenberger and D. Bradley, Eds. Cham, Switzerland: Springer, 2016, pp. 59–74.",
        "A. Ñíguez, “Simulación de eventos discretos en plantas de ensamble,” *Rev. Ing. Ind.*, vol. 7, no. 1, 2020. [Online]. Available: https://rii.example.org/niguez2020. doi: 10.5555/rii.2020.71.",
        "#8|A. van der Berg and L. Gómez, “Costos y beneficios de los gemelos digitales en pymes,” in *Proc. Congr. Ing. Ind.*, Bogotá, Colombia, 2020, pp. 91–97",
        "#9|Siemens, “Digital twin in automotive manufacturing: Case studies,” Siemens AG. Accessed: Jan. 10, 2022. [Online]. Available: https://www.siemens.com/digital-twin-automotive",
    ],
    mutaciones=[],
    errores=[
        {"id": "IEEE-014", "desc": "Primeras apariciones en orden 1, 3, 2, 4...: [3] se cita antes que [2]."},
        {"id": "IEEE-002", "desc": "'eventos discretos,[6] aunque': corchete despues de la coma, fuera de la puntuacion."},
        {"id": "IEEE-003", "desc": "'[2,3]' (sin espacio, dos numeros en un corchete); 2 y 3 ya estaban citados antes."},
        {"id": "IEEE-004", "desc": "'[4]-[6]' rango con guion; 4, 5 y 6 ya estaban citados antes (no genera IEEE-013)."},
        {"id": "IEEE-017", "desc": "Numeracion saltada: las etiquetas de la lista son [1]..[6], [8], [9] (falta [7]). El texto cita por etiqueta ([8], [9]) y no cita [7]. Colateral posible: un juez que numere por posicion vera [9] sin entrada (IEEE-012); se siembra solo IEEE-017."},
        {"id": "IEEE-037", "desc": "Entrada [3] con DOI como 'https://doi.org/10.4995/...' sin 'Available:' ni 'doi:'; termina en URL."},
        {"id": "IEEE-038", "desc": "Entrada [8] (actas) sin punto final y sin terminar en URL."},
        {"id": "IEEE-040", "desc": "Entrada [6]: 'doi:' va despues de '[Online]. Available: URL.'. El prefijo es correcto y termina en punto."},
    ],
)

# ---------------------------------------------------------------- 5 mix1_correcto
D5 = dict(
    plantilla="apa7-base+ieee-citas", salida="apa7-base+ieee-citas_correcto.docx", perfil="apa7-base+ieee-citas",
    titulo="Realidad virtual en la rehabilitación motora posterior a un ictus",
    autor="Lucía Ponce de León Barrios",
    ref_titulo="Referencias", salto_pagina=True, numerar="esp",
    items=[
        ("h1", "Introducción"),
        ("p", "La rehabilitación motora tras un accidente cerebrovascular exige sesiones frecuentes y prolongadas, lo que limita el acceso en regiones con pocos terapeutas [1]. La realidad virtual ofrece un entorno motivador y cuantificable para la repetición de movimientos [2, p. 14]."),
        ("h1", "Antecedentes"),
        ("p", "Existen varias plataformas de bajo costo, e.g., [3]. Ref. [1] recomienda priorizar las intervenciones que puedan sostenerse en el domicilio del paciente."),
        ("p", "Las revisiones sistemáticas más recientes aportan resultados moderados a favor de la realidad virtual como complemento de la terapia convencional [4]. Los métodos de interacción más estudiados son: [4], [5, Sec. III]."),
        ("h2", "Interfaces hápticas"),
        ("p", "Ortega y García-Márquez [5] muestran que la retroalimentación háptica mejora la precisión del movimiento de la mano. Como se muestra en [5], el efecto es mayor en pacientes con déficit moderado."),
        ("h2", "Sistemas de seguimiento"),
        ("p", "Los sistemas de seguimiento por cámara permiten medir la amplitud del movimiento sin sensores en el cuerpo del paciente [4]."),
        ("h1", "Resultados comparados"),
        ("p", "La Tabla 1 resume la evidencia disponible por tipo de intervención."),
        ("cap", "Tabla 1", "bold"),
        ("cap", "Evidencia por tipo de intervención"),
        ("tbl", [["Intervención", "Efecto", "Fuente"], ["Videojuegos comerciales", "Moderado", "[3]"], ["Inmersiva con casco", "Alto", "[4], [5]"]]),
        ("p", "El fundamento técnico de los sistemas de realidad virtual se encuentra en [6]. La gamificación de las sesiones aumenta la adherencia [7], y las guías clínicas oficiales ya la contemplan [8]."),
        ("h1", "Conclusiones"),
        ("p", "La realidad virtual es un complemento prometedor de la rehabilitación convencional [2], [5]. Se recomienda evaluar su costo-efectividad en el contexto local, como se muestra en [8]."),
    ],
    refs=[
        "World Health Organization, “Rehabilitation,” WHO. Accessed: Feb. 2, 2023. [Online]. Available: https://www.who.int/news-room/fact-sheets/detail/rehabilitation",
        "G. Saposnik *et al.*, “Effectiveness of virtual reality using Wii gaming technology in stroke rehabilitation: A pilot randomized clinical trial and proof of principle,” *Stroke*, vol. 41, no. 7, pp. 1477–1484, Jul. 2010, doi: 10.1161/STROKEAHA.110.584979.",
        "M. Fuentes and L. Ponce de León, “Realidad virtual inmersiva en la rehabilitación de miembro superior,” *Rev. Mex. Ing. Biomed.*, vol. 41, no. 2, pp. 85–98, May 2020, doi: 10.17488/RMIB.41.2.7.",
        "K. E. Laver, B. Lange, S. George, J. E. Deutsch, G. Saposnik, and M. Crotty, “Virtual reality for stroke rehabilitation,” *Cochrane Database Syst. Rev.*, no. 11, Art. no. CD008349, Nov. 2017, doi: 10.1002/14651858.CD008349.pub4.",
        "A. Ortega and D. García-Márquez, “Diseño de interfaces hápticas para terapia motora,” in *Proc. IEEE Int. Conf. Rehabil. Robot. (ICORR)*, Toronto, ON, Canada, 2019, pp. 233–238, doi: 10.1109/ICORR.2019.8779494.",
        "G. C. Burdea and P. Coiffet, *Virtual Reality Technology*, 2nd ed. Hoboken, NJ, USA: Wiley, 2003.",
        "T. Vargas, “Gamificación en terapias de rehabilitación,” in *Salud Digital*, M. Ríos, Ed. Mexico City, Mexico: Ed. Médica Panamericana, 2021, pp. 150–172.",
        "Ministerio de Salud, “Guía de práctica clínica: Rehabilitación del accidente cerebrovascular,” Gobierno del Perú. Accessed: Mar. 20, 2022. [Online]. Available: https://www.gob.pe/minsa/guia-acv",
    ],
    mutaciones=[], errores=[],
)

# ---------------------------------------------------------------- 6 mix1_errores
D6 = dict(
    plantilla="apa7-base+ieee-citas", salida="apa7-base+ieee-citas_errores.docx", perfil="apa7-base+ieee-citas",
    titulo="Ciudades inteligentes y gestión adaptativa del tráfico",
    autor="Fabiola Ñañez Cordero",
    ref_titulo="Referencias", salto_pagina=False, numerar="esp",
    items=[
        ("h1", "Introducción"),
        ("p", "La congestión vehicular genera pérdidas económicas y ambientales considerables en las grandes ciudades [1]. Los sistemas de transporte inteligente buscan mitigarla con semáforos adaptativos [2, p. 14]."),
        ("p", "Entre las alternativas, e.g., [3], destacan el control por aprendizaje por refuerzo y los modelos de predicción de flujo. Las técnicas más usadas son: [4], [5, Sec. III].", "justify"),
        ("h1", "Control semafórico"),
        ("p", "Los semáforos adaptativos ajustan los tiempos de verde según la cola medida por sensores. Los resultados mejoran cuando se coordinan las intersecciones vecinas (Rivas, 2019)."),
        ("p", "La predicción del flujo con redes recurrentes amplía el horizonte de planificación [6]. Los datos de los sensores se transmiten por redes de baja potencia [7].", "calibri"),
        ("p", "Los costos de despliegue siguen siendo la principal barrera en ciudades intermedias. Una evaluación económica similar se reporta en [12].", "noindent"),
        ("h1", "Conclusiones"),
        ("p", "La coordinación de semáforos y la predicción de flujo son estrategias complementarias [2], [4]. Se recomienda comenzar con corredores piloto.", "calibri"),
    ],
    refs=[
        "INRIX, “2022 global traffic scorecard,” INRIX Research. Accessed: Mar. 8, 2023. [Online]. Available: https://inrix.com/scorecard/",
        "P. Mirchandani and L. Head, “A real-time traffic signal control system: Architecture, algorithms, and analysis,” *Transp. Res. C, Emerg. Technol.*, vol. 9, no. 6, pp. 415–432, Dec. 2001, doi: 10.1016/S0968-090X(00)00047-4.",
        "C. Rivas and L. Soto, “Control semafórico adaptativo con aprendizaje por refuerzo,” *Rev. Ing. Transp.*, vol. 6, no. 1, pp. 12–27, Jan. 2019, doi: 10.5555/rit.2019.61.",
        "H. Wei, G. Zheng, V. Gayah, and Z. Li, “A survey on traffic signal control methods,” 2019, *arXiv:1904.08117*.",
        "A. Ibáñez, “Detección de vehículos con redes convolucionales,” in *Proc. IEEE Colombian Conf. Commun. Comput. (COLCOM)*, Cali, Colombia, 2021, pp. 1–6, doi: 10.1109/COLCOM52689.2021.9591846.",
        "Y. Li, R. Yu, C. Shahabi, and Y. Liu, “Diffusion convolutional recurrent neural network: Data-driven traffic forecasting,” in *Proc. Int. Conf. Learn. Represent. (ICLR)*, Vancouver, BC, Canada, 2018, pp. 1–16.",
        "M. Ñahui, “Redes LoRaWAN para sensores urbanos,” in *Ciudades Inteligentes*, E. Salas, Ed. Lima, Peru: Fondo Ed. UPCH, 2020, pp. 99–120.",
        "Ministerio de Transportes, “Plan nacional de movilidad urbana sostenible,” Gobierno de España. Accessed: Jul. 1, 2022. [Online]. Available: https://www.transportes.gob.es/pnmus",
    ],
    mutaciones=["justificado", "calibri", "sin_sangria"],
    errores=[
        {"id": "APA-003", "desc": "Dos parrafos de cuerpo (Control semaforico y Conclusiones) en Calibri 11 pt (valida por si sola) junto a Times New Roman 12 en el resto."},
        {"id": "APA-006", "desc": "Segundo parrafo de la Introduccion justificado."},
        {"id": "APA-007", "desc": "Parrafo 'Los costos de despliegue...' con sangria de primera linea 0 (sin espacios), el resto con 0,5 in."},
        {"id": "APA-012", "desc": "'Referencias' sigue a las Conclusiones sin salto de pagina."},
        {"id": "IEEE-001", "desc": "Cita autor-fecha '(Rivas, 2019)' en vez de [n]; la entrada [3] (Rivas) se cita en otro lugar como [3]."},
        {"id": "IEEE-012", "desc": "Cita '[12]' cuando la lista tiene 8 entradas."},
        {"id": "IEEE-013", "desc": "Entrada [8] (Ministerio de Transportes) nunca citada; las entradas 1-7 si."},
    ],
)

# ---------------------------------------------------------------- 7 mix2_correcto
SEMARNAT = "Secretaría de Medio Ambiente y Recursos Naturales"
CONACYT = "Consejo Nacional de Ciencia y Tecnología"
D7 = dict(
    plantilla="ieee-base+apa7-citas", salida="ieee-base+apa7-citas_correcto.docx", perfil="ieee-base+apa7-citas",
    titulo="Gestión de residuos electrónicos en ciudades medianas",
    autor="Esteban Valdivia Ñúñez",
    ref_titulo="REFERENCIAS", salto_pagina=False, numerar=None,
    items=[
        ("h1", "Introducción"),
        ("p", "Los residuos de aparatos eléctricos y electrónicos son el flujo de desechos de más rápido crecimiento. El " + CONACYT + " (2019) estimó su generación anual en cientos de miles de toneladas (" + CONACYT + ", 2019)."),
        ("p", "La " + SEMARNAT + " (SEMARNAT, 2020) estableció metas de valorización, y la SEMARNAT (2020) exige planes de manejo a los grandes generadores."),
        ("h1", "Marco de referencia"),
        ("p", "El reciclaje de baterías de litio es especialmente crítico por su riesgo de incendio (Castro, 2015). Fernández-Cruz (2016) propone un enfoque de economía circular (véase también Vidal, 2017). La literatura concuerda en este punto (Castro, 2015; Vidal, 2017)."),
        ("h2", "Gestión integral"),
        ("p", "Los fundamentos de la gestión integral se presentan en el tercer capítulo de Mora Quintero (2018), y los criterios de selección de sitios en (Mora Quintero, 2018, cap. 3). Las guías operativas para puntos de acopio están disponibles en línea (Vidal, s.f.-a, s.f.-b)."),
        ("p", "Un reportaje reciente muestra que muchos municipios carecen de puntos de acopio (Navarro, 2020, párr. 4)."),
        ("h1", "Resultados"),
        ("p", "La Tabla I presenta las fracciones recuperables por tipo de residuo."),
        ("cap", "TABLA I. FRACCIONES RECUPERABLES POR TIPO DE RESIDUO"),
        ("tbl", [["Residuo", "Fracción", "Fuente"], ["Baterías de litio", "12 %", "Castro (2015)"], ["Placas de circuito", "30 %", "(Mora Quintero, 2018)"]]),
        ("h1", "Conclusiones"),
        ("p", "La gestión de residuos electrónicos requiere puntos de acopio accesibles, trazabilidad y metas de valorización exigibles (Vidal, 2017; SEMARNAT, 2020)."),
    ],
    refs=[
        "Castro, F. (2015). Reciclaje de baterías de litio. *Ciencia y Ambiente, 6*(1), 5–19. https://doi.org/10.1234/cya.2015.61",
        CONACYT + ". (2019). *Diagnóstico nacional de residuos electrónicos*. https://conacyt.example.mx/diag-raee",
        "Fernández-Cruz, A. (2016). Economía circular y residuos tecnológicos. *Gestión Ambiental, 12*(2), 40–58. https://doi.org/10.1234/ga.2016.122",
        "Mora Quintero, L. (2018). *Gestión integral de residuos electrónicos*. Editorial Verde.",
        "Navarro, S. (2020, 3 de marzo). Basura electrónica: el reto de las ciudades. *El Observador*. https://elobservador.example.org/basura-electronica",
        SEMARNAT + ". (2020). *Programa nacional para la prevención y gestión integral de residuos 2020-2024*. https://www.gob.mx/semarnat/documentos/programa-residuos",
        "Vidal, J. (s.f.-a). *Guía para puntos de acopio de residuos electrónicos*. https://ejemplo.org/acopio",
        "Vidal, J. (s.f.-b). *Manual de desmontaje seguro de equipos*. https://ejemplo.org/desmontaje",
        "Vidal, J. (2017). Trazabilidad de residuos en centros de acopio. *Revista de Residuos, 3*(1), 77–93. https://doi.org/10.1234/rr.2017.31",
    ],
    mutaciones=[], errores=[],
)

# ---------------------------------------------------------------- 8 mix2_errores
MD = "Ministerio del Deporte"
D8 = dict(
    plantilla="ieee-base+apa7-citas", salida="ieee-base+apa7-citas_errores.docx", perfil="ieee-base+apa7-citas",
    titulo="Nutrición y rendimiento en atletas universitarios",
    autor="Gabriela Tapia Ñuñoa",
    ref_titulo="REFERENCIAS", salto_pagina=False, numerar=None,
    items=[
        ("h1", "Introducción"),
        ("p", "La nutrición adecuada es un componente central del rendimiento de los atletas universitarios (Burke, 2018, cap. 2). El " + MD + " (2021) publicó recomendaciones para atletas de alto rendimiento, aunque reconoce que no siempre son aplicables al contexto universitario (" + MD + ", 2021)."),
        ("p", "La hidratación es un factor limitante en climas cálidos (Herrera, 2019). Herrero (2019) observó que una pérdida de peso corporal por sudor superior al 2 % reduce el rendimiento aeróbico."),
        ("h1", "Suplementación"),
        ("p", "La suplementación proteica se ha estudiado sobre todo en deportes de fuerza (Ríos, Soto, Vera, & Luna, 2019). Ríos et al. (2019) reportaron mejoras modestas en la masa magra."),
        ("p", "Para la recuperación posterior al ejercicio hay evidencia consistente (véase Sánchez, 2020), y la nutrición universitaria requiere además apoyo institucional (Sánchez, 2020; Vega, 2017)."),
        ("h2", "Herramientas de cálculo"),
        ("p", "Existen calculadoras abiertas de requerimientos energéticos (Tapia, s.f.), aunque su uso sin asesoría profesional no se recomienda (Campos, 2020)."),
        ("h1", "Conclusiones"),
        ("p", "La nutrición deportiva universitaria necesita guías propias, personal calificado y seguimiento continuo."),
    ],
    refs=[
        "Burke, L. (2018). *Nutrición en el deporte* (3.ª ed.). Editorial Deportiva.",
        "Herrero, M. (2019). Hidratación y rendimiento en atletas universitarios. *Revista de Ciencias del Deporte, 15*(2), 101–118. DOI: 10.5555/rcd.2019.152",
        "Ríos, A., Soto, M., Vera, L., & Luna, P. (2019). Suplementación proteica en deportes de fuerza. *Nutrición y Deporte, 4*(1), 9–27. https://doi.org/10.5555/nd.2019.41",
        MD + ". (2021). *Guía de alimentación para atletas de alto rendimiento*. Retrieved from https://www.mindeporte.example.gov/guia-alimentacion",
        "Sánchez, T. (2020). Carga de entrenamiento y recuperación nutricional. *Medicina del Deporte, 11*(3), 66–84. https://doi.org/10.5555/md.2020.113",
        "Tapia, R. (s.f.). *Calculadora de requerimientos energéticos*. https://calculadora.example.org/energia.",
        "Vega, J. (2017). Nutrición deportiva en la universidad. En P. Ortiz (Ed.), *Deporte y vida universitaria* (pp. 55–80). Editorial Campus.",
    ],
    mutaciones=[],
    errores=[
        {"id": "APA-034", "desc": "Cita '(Campos, 2020)' sin entrada en la lista; las 7 entradas estan citadas."},
        {"id": "APA-035", "desc": "Cita '(Herrera, 2019)' con apellido distinto al de la lista (Herrero, 2019); la entrada Herrero se cita correctamente en la oracion siguiente. Colateral posible: algun juez vera '(Herrera, 2019)' como cita sin entrada (APA-034); se siembra solo APA-035."},
        {"id": "APA-038", "desc": "'(Ríos, Soto, Vera, & Luna, 2019)' con cuatro autores en vez de 'Ríos et al.' (la narrativa 'Ríos et al. (2019)' es valida)."},
        {"id": "APA-061", "desc": "Lista no alfabetica: 'Ríos' va antes de 'Ministerio del Deporte' (M antes de R). El resto en orden."},
        {"id": "APA-075", "desc": "Entrada de Tapia (URL) con punto final despues de la URL."},
        {"id": "APA-076", "desc": "Entrada de Herrero con 'DOI: 10.5555/...' en vez de https://doi.org/..., sin punto final."},
        {"id": "APA-079", "desc": "Entrada del Ministerio del Deporte con 'Retrieved from https://...' antes de la URL, sin punto final."},
    ],
)

DOCS = [D1, D2, D3, D4, D5, D6, D7, D8]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    esperado = {}
    for spec in DOCS:
        doc = construir(spec)
        doc.save(str(OUT / spec["salida"]))
        esperado[spec["salida"]] = {"perfil": spec["perfil"], "errores": spec["errores"]}
        print("ok", spec["salida"])
    with open(OUT / "esperado.json", "w", encoding="utf-8") as f:
        json.dump(esperado, f, ensure_ascii=False, indent=2)
    print("ok esperado.json")


if __name__ == "__main__":
    main()
