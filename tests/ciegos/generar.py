# -*- coding: utf-8 -*-
"""Generador CIEGO de documentos de prueba (sembrado segun la norma, no segun el juez).
Uso: python -I tests/ciegos/generar.py   -> tests/ciegos/docs/*.docx + esperado.json
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
OUT = HERE / "docs"
sys.path.insert(0, str(ROOT / "scripts"))
import crear_plantillas  # noqa: E402
PLANT = crear_plantillas.asegurar_plantillas()

# ----------------------------------------------------------------------------
# utilidades docx
# ----------------------------------------------------------------------------


def vaciar(doc):
    body = doc.element.body
    for el in list(body):
        if el.tag.endswith("}sectPr"):
            continue
        body.remove(el)


def add_runs(par, text):
    """*texto* -> cursiva."""
    for p in re.split(r"(\*[^*]+\*)", text):
        if not p:
            continue
        if p.startswith("*") and p.endswith("*") and len(p) > 2:
            r = par.add_run(p[1:-1])
            r.italic = True
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
    pend_primero = False
    cuerpo = []
    for item in spec["items"]:
        kind, text = item[0], item[1]
        tag = item[2] if len(item) > 2 else None
        if kind == "h1":
            add_par(doc, text, "Heading 1")
            pend_primero = True
        elif kind == "h2":
            add_par(doc, text, "Heading 2")
            pend_primero = True
        else:
            st = "First Paragraph" if pend_primero else "Body Text"
            pend_primero = False
            cuerpo.append((add_par(doc, text, st), tag))
    h = add_par(doc, spec["ref_titulo"], "Heading 1")
    if spec.get("salto_pagina"):
        h.paragraph_format.page_break_before = True
    refs = []
    for i, r in enumerate(spec["refs"], 1):
        if r.startswith("~"):          # entrada SIN [n] inicial (error sembrado)
            txt = r[1:]
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


# ----------------------------------------------------------------------------
# mutaciones (errores de maquetacion)
# ----------------------------------------------------------------------------


def m_margen(doc, cuerpo, refs):  # APA-001
    doc.sections[0].left_margin = Inches(1.5)


def m_fuente_tam(doc, cuerpo, refs):  # APA-002: TNR 10 en todo el texto
    for par in doc.paragraphs:
        for r in par.runs:
            r.font.name = "Times New Roman"
            r.font.size = Pt(10)


def m_interlineado(doc, cuerpo, refs):  # APA-004
    for par, tag in cuerpo:
        if tag == "single":
            par.paragraph_format.line_spacing = 1.0


def m_pagina_ausente(doc, cuerpo, refs):  # APA-008
    hp = doc.sections[0].header.paragraphs[0]
    for r in list(hp._p):
        if r.tag.endswith("}r"):
            hp._p.remove(r)


def m_sin_francesa(doc, cuerpo, refs):  # APA-060
    for p in refs:
        p.paragraph_format.left_indent = Inches(0)
        p.paragraph_format.first_line_indent = Inches(0)


def m_georgia(doc, cuerpo, refs):  # APA-003: Georgia 11 (permitida) junto a TNR 12
    for par, tag in cuerpo:
        if tag == "georgia":
            for r in par.runs:
                r.font.name = "Georgia"
                r.font.size = Pt(11)


def m_justificado(doc, cuerpo, refs):  # APA-006
    for par, tag in cuerpo:
        if tag == "justify":
            par.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY


def m_sangria_espacios(doc, cuerpo, refs):  # APA-007: solo espacios, sin sangria de formato
    for par, tag in cuerpo:
        if tag == "spaces":
            par.paragraph_format.first_line_indent = Inches(0)


MUT = {
    "margen": m_margen, "fuente_tam": m_fuente_tam, "interlineado": m_interlineado,
    "pagina_ausente": m_pagina_ausente, "sin_francesa": m_sin_francesa,
    "georgia": m_georgia, "justificado": m_justificado, "sangria_espacios": m_sangria_espacios,
}

# ----------------------------------------------------------------------------
# DOC 1  apa7_correcto  (riego inteligente)
# ----------------------------------------------------------------------------
FAO = "Organización de las Naciones Unidas para la Alimentación y la Agricultura"

APA7_OK = dict(
    plantilla="apa7", salida="apa7_correcto.docx", perfil="apa7",
    titulo="Riego inteligente basado en sensores de humedad del suelo",
    autor="Camila Rojas Medina",
    ref_titulo="Referencias", salto_pagina=True, numerar=None,
    items=[
        ("h1", "Introducción"),
        ("p", "La agricultura consume cerca del 70 % del agua dulce extraída en el mundo, por lo que mejorar la eficiencia del riego es una prioridad ambiental y económica (%s [FAO], 2020). Los sistemas de riego inteligente combinan sensores, comunicación inalámbrica y reglas de decisión para aplicar agua solo cuando el cultivo la necesita.".replace("%s", FAO)),
        ("p", "Pérez y López (2020) mostraron que el riego controlado por humedad del suelo redujo el consumo de agua entre 25 % y 40 % frente al riego por calendario. Sin embargo, la calibración de los sensores sigue siendo una fuente de error importante (Ruiz, 2019a, 2019b)."),
        ("h1", "Marco teórico"),
        ("h2", "Sensores de humedad"),
        ("p", "Los sensores capacitivos estiman el contenido volumétrico de agua a partir de la permitividad del suelo. Según Ruiz (2019a), su respuesta depende de la textura y la salinidad, de modo que cada parcela requiere una curva propia; la autora recomienda al menos tres puntos de calibración (Ruiz, 2019a, p. 14)."),
        ("h2", "Redes de comunicación"),
        ("p", "Las redes de sensores inalámbricos transmiten las lecturas a una pasarela central. Díaz (2018) compara tres protocolos de bajo consumo y concluye que LoRa ofrece el mejor equilibrio entre alcance y autonomía en predios de más de diez hectáreas. Fernández et al. (2018) confirmaron esa tendencia en huertos de aguacate, aunque con mayor pérdida de paquetes bajo vegetación densa."),
        ("h1", "Metodología"),
        ("p", "El prototipo se instaló en un lote experimental de maíz de 0,5 ha. Se usaron doce nodos con sensores a 20 y 40 cm de profundidad y una pasarela alimentada con energía solar. La evapotranspiración de referencia se obtuvo de la estación más cercana (Servicio Meteorológico Nacional, s.f.), y el riego se activó cuando la humedad cayó por debajo del 60 % de la capacidad de campo."),
        ("h1", "Resultados"),
        ("p", "Durante el ciclo, el sistema aplicó 312 mm frente a los 468 mm del lote testigo, un ahorro del 33 %, sin diferencias significativas en el rendimiento. Estos valores son coherentes con lo reportado en la literatura (Fernández et al., 2018; Pérez & López, 2020)."),
        ("p", "Los costos de instalación se recuperan en tres ciclos agrícolas, según el manual de referencia (De la Cruz, 2016). La adopción, además, depende de la capacitación del productor (FAO, 2020), por lo que la FAO (2020) recomienda programas de extensión rural."),
        ("h1", "Conclusiones"),
        ("p", "El riego inteligente es técnicamente viable y económicamente razonable para productores medianos. Futuros trabajos deberían evaluar la calibración automática de sensores y su integración con pronósticos meteorológicos."),
    ],
    refs=[
        "De la Cruz, H. (2016). *Manual de sensores para la agricultura* (2.ª ed.). Editorial Agrotec.",
        "Díaz, P. (2018). Redes de sensores inalámbricos para el campo. En C. Ortega (Ed.), *Agricultura digital: Tecnologías y aplicaciones* (pp. 45-72). Editorial Alfa.",
        "Fernández, A., Gómez, R., & Vargas, T. (2018). Evaluación de LoRa en huertos de aguacate. En *Actas del Congreso Iberoamericano de Agroinformática* (pp. 210-217). Universidad Autónoma Chapingo.",
        FAO + ". (2020). *El estado mundial de la agricultura y la alimentación 2020*. https://doi.org/10.4060/cb1447es",
        "Pérez, J., & López, M. (2020). Riego por humedad del suelo y ahorro hídrico en cultivos de maíz. *Revista de Ingeniería Agrícola, 10*(2), 55-68. https://doi.org/10.1016/j.ria.2020.04.003",
        "Ruiz, S. (2019a). Calibración de sensores capacitivos de humedad en suelos arcillosos. *Agrotecnia Aplicada, 7*(1), 12-29. https://doi.org/10.1234/aa.2019.071",
        "Ruiz, S. (2019b). Sistemas de riego por goteo con control automático. *Agrotecnia Aplicada, 7*(3), 101-118. https://doi.org/10.1234/aa.2019.073",
        "Servicio Meteorológico Nacional. (s.f.). *Datos de evapotranspiración de referencia*. https://smn.conagua.gob.mx/es/",
    ],
    mutaciones=[], errores=[],
)

# ----------------------------------------------------------------------------
# DOC 2  apa7_errores  (compiladores)
# ----------------------------------------------------------------------------
ISO = "Organización Internacional de Normalización"
APA7_ERR = dict(
    plantilla="apa7", salida="apa7_errores.docx", perfil="apa7",
    titulo="Enseñanza de compiladores con herramientas visuales",
    autor="Andrés Villalobos Peña",
    ref_titulo="Referencias", salto_pagina=True, numerar=None,
    items=[
        ("h1", "Introducción"),
        ("p", "El diseño de compiladores es una de las asignaturas más exigentes de la ingeniería en sistemas, porque integra teoría de lenguajes formales, estructuras de datos y arquitectura de computadores (Aho et al., 2007). Los estudiantes suelen percibir las fases del compilador como etapas aisladas, lo que dificulta comprender el flujo completo de la traducción."),
        ("p", "Salas y Díaz (2019) reportaron que las herramientas visuales de análisis sintáctico mejoraron la comprensión de las gramáticas LL(1) en un 22 %. No obstante, otros autores señalan que la visualización por sí sola no basta sin práctica de implementación (Quispe & Mamani, 2021)."),
        ("h1", "Marco teórico"),
        ("h2", "Análisis léxico y sintáctico"),
        ("p", "Un analizador léxico transforma la secuencia de caracteres en tokens, y el análisis sintáctico verifica que dichos tokens respeten la gramática del lenguaje (Cooper & Torczon, 2012). Mendoza (2020a) propone diseñar el analizador léxico con autómatas explícitos para facilitar su depuración en el aula, resultado consistente con experiencias previas (Salas y Díaz, 2019).", "single"),
        ("p", "Para las fases posteriores, Mendoza (2020b) presenta un generador de código intermedio de tres direcciones pensado para cursos introductorios; ambos trabajos pueden consultarse juntos (Mendoza, 2020a, 2020b). La tabla de símbolos, según el mismo autor, debe construirse desde la primera fase (Mendoza, 2020a, p. 12).", "single"),
        ("h1", "Metodología"),
        ("p", "Se trabajó con 48 estudiantes divididos en dos grupos. El grupo experimental usó una herramienta visual de gramáticas y el grupo de control, material impreso. Los ejercicios se basaron en un subconjunto del lenguaje C según la norma (%s [ISO], 2018), y las guías de apoyo se tomaron de recursos abiertos (Quintero, s.f.).".replace("%s", ISO), "single"),
        ("h1", "Resultados"),
        ("p", "El grupo experimental obtuvo una calificación media de 8,1 frente a 7,2 del grupo de control. La diferencia es consistente con la literatura (Cooper & Torczon, 2013) y con las prácticas descritas en la norma (ISO, 2018)."),
        ("p", "Los estudiantes valoraron especialmente la posibilidad de ver el árbol sintáctico construirse paso a paso. Aho et al. (2007) ya sugerían esta práctica; además, Cooper y Torczon (2012) la incluyen en sus ejercicios."),
        ("h1", "Conclusiones"),
        ("p", "Las herramientas visuales son un complemento útil, no un sustituto, de la práctica de implementación. Se recomienda ampliar el estudio a otros lenguajes y semestres."),
    ],
    refs=[
        "Aho, A. V., Lam, M. S., Sethi, R., & Ullman, J. D. (2007). *Compiladores: Principios, técnicas y herramientas* (2.ª ed.). Pearson Educación.",
        "Cooper, K. D., & Torczon, L. (2012). *Engineering a compiler* (2nd ed.). Morgan Kaufmann.",
        "Mendoza, C. (2020a). Diseño de un analizador léxico para lenguajes educativos. *Ingeniería y Sistemas, 9*(1), 5-20. https://doi.org/10.1000/is.2020.91",
        "Mendoza, C. (2020b). Generación de código intermedio en compiladores didácticos. *Ingeniería y Sistemas, 9*(2), 41-58. https://doi.org/10.1000/is.2020.92",
        ISO + ". (2018). *Lenguajes de programación: C (ISO/IEC 9899:2018)*. https://www.iso.org/standard/74528.html",
        "Quintero, D. (s.f.). *Tutorial de análisis sintáctico LL(1)*. https://compiladores.example.org/ll1",
        "Salas, M., & Díaz, E. (2019). Enseñanza de análisis sintáctico con herramientas visuales. *Revista de Educación en Ingeniería, 14*(27), 33-45. https://doi.org/10.26507/rei.v14n27.1021",
    ],
    mutaciones=["margen", "fuente_tam", "interlineado", "pagina_ausente", "sin_francesa"],
    errores=[
        {"id": "APA-001", "desc": "Margen izquierdo de 1,5 in (resto 1 in) en la unica seccion."},
        {"id": "APA-002", "desc": "Todo el documento en Times New Roman 10 pt (fuente permitida, tamaño equivocado); una sola fuente, asi que no cuenta como APA-003."},
        {"id": "APA-004", "desc": "Tres parrafos de cuerpo (Marco teorico y Metodologia) con interlineado sencillo 1.0 en vez de doble."},
        {"id": "APA-008", "desc": "Encabezado de pagina vacio: se elimino el campo PAGE (sin numero de pagina)."},
        {"id": "APA-034", "desc": "Cita (Quispe & Mamani, 2021) sin entrada en la lista. Todas las demas entradas estan citadas."},
        {"id": "APA-035", "desc": "Cita (Cooper & Torczon, 2013) con año distinto al de la lista (2012); la entrada 2012 sigue citada correctamente en otro lugar. Colateral posible: un juez que compare (apellido, año) podria reportar ademas APA-034 para el 2013; se siembra solo APA-035."},
        {"id": "APA-037", "desc": "Cita parentetica '(Salas y Díaz, 2019)' con 'y' en vez de '&' (la narrativa 'Salas y Díaz (2019)' es valida y tambien aparece)."},
        {"id": "APA-060", "desc": "Todas las entradas de la lista sin sangria francesa (sangria 0 y sin primera linea colgante)."},
    ],
)

# ----------------------------------------------------------------------------
# DOC 3  ieee_correcto  (redes 5G)
# ----------------------------------------------------------------------------
IEEE_OK = dict(
    plantilla="ieee", salida="ieee_correcto.docx", perfil="ieee",
    titulo="Cobertura y latencia en redes móviles 5G",
    autor="Daniela Ñáñez Ibáñez",
    ref_titulo="Referencias", salto_pagina=False, numerar="tab",
    items=[
        ("h1", "Introducción"),
        ("p", "Las redes de quinta generación (5G) se diseñaron para atender tres escenarios de uso: banda ancha móvil mejorada, comunicaciones masivas tipo máquina y comunicaciones ultra confiables de baja latencia [1]. Desde su definición inicial [2], la investigación ha avanzado en espectro, arquitectura y virtualización."),
        ("p", "Ref. [1] establece una latencia objetivo de 1 ms en el plano de usuario. Como se muestra en [2], el uso de ondas milimétricas es clave para alcanzar tasas de varios gigabits por segundo."),
        ("h1", "Espectro y cobertura"),
        ("p", "Las bandas milimétricas ofrecen gran ancho de banda, pero sufren fuerte atenuación y bloqueo [3]. En escenarios urbanos densos, Núñez y De la Cruz [3] midieron pérdidas adicionales por vegetación y vidrios metalizados."),
        ("p", "Para servicios de baja latencia, van der Berg et al. [4] proponen segmentar la red de acceso y priorizar el tráfico crítico. Como se aprecia en [4], la segmentación reduce la latencia de extremo a extremo en un 35 %."),
        ("h2", "Modelos de propagación"),
        ("p", "Los modelos clásicos de propagación se describen en [5], mientras que las particularidades de 5G NR se detallan en [6]. Los resultados de [6] son la base de las campañas de medición actuales."),
        ("h1", "Arquitectura y despliegue"),
        ("p", "La arquitectura de núcleo basada en servicios permite desplegar funciones de red virtualizadas y escalarlas según la demanda [6]. Una síntesis de los casos de uso comerciales se encuentra en [7]."),
        ("p", "Las pérdidas de propagación en la banda de 28 GHz superan en más de 20 dB las observadas en 3,5 GHz [3, Fig. 2]. Combinando espectro medio y alto, los operadores equilibran cobertura y capacidad [2], [5]."),
        ("h1", "Conclusiones"),
        ("p", "El despliegue de 5G exige una planificación conjunta de espectro, densificación y arquitectura [1], [4], [6]. Ref. [7] resume las recomendaciones para operadores."),
    ],
    refs=[
        "International Telecommunication Union, “IMT vision: Framework and overall objectives of the future development of IMT for 2020 and beyond,” ITU-R, Geneva, Switzerland, Recommendation ITU-R M.2083-0, Sep. 2015.",
        "J. G. Andrews *et al.*, “What will 5G be?,” *IEEE J. Sel. Areas Commun.*, vol. 32, no. 6, pp. 1065–1082, Jun. 2014, doi: 10.1109/JSAC.2014.2328098.",
        "M. Núñez and C. De la Cruz, “Cobertura de ondas milimétricas en entornos urbanos densos,” *IEEE Lat. Am. Trans.*, vol. 19, no. 3, pp. 412–420, Mar. 2021, doi: 10.1109/TLA.2021.9448297.",
        "T. van der Berg, J. Ibáñez, and L. Gómez, “Segmentación de red para servicios de baja latencia,” in *Proc. IEEE Latin-Amer. Conf. Commun. (LATINCOM)*, Rio de Janeiro, Brazil, 2022, pp. 1–6, doi: 10.1109/LATINCOM56090.2022.9999999.",
        "T. S. Rappaport, *Wireless Communications: Principles and Practice*, 2nd ed. Upper Saddle River, NJ, USA: Prentice Hall, 2002.",
        "E. Dahlman, S. Parkvall, and J. Sköld, “Spectrum and RF characteristics,” in *5G NR: The Next Generation Wireless Access Technology*, 2nd ed. London, U.K.: Academic Press, 2021, pp. 75–112.",
        "GSMA, “The 5G guide: A reference for operators,” GSMA. Accessed: Feb. 14, 2023. [Online]. Available: https://www.gsma.com/wp-content/uploads/2019/04/The-5G-Guide_GSMA_2019_04_29_compressed.pdf",
    ],
    mutaciones=[], errores=[],
)

# ----------------------------------------------------------------------------
# DOC 4  ieee_errores  (ciberseguridad industrial)
# ----------------------------------------------------------------------------
IEEE_ERR = dict(
    plantilla="ieee", salida="ieee_errores.docx", perfil="ieee",
    titulo="Seguridad de redes de tecnología operacional en plantas manufactureras",
    autor="Rodrigo Álvarez Ortega",
    ref_titulo="Referencias", salto_pagina=False, numerar="tab",
    items=[
        ("h1", "Introducción"),
        ("p", "La convergencia entre tecnologías de la información y de operación ha ampliado la superficie de ataque de las plantas industriales [2]. Ref. [1] ofrece la guía de referencia para proteger los sistemas de control industrial."),
        ("p", "Los incidentes recientes muestran que la ausencia de segmentación facilita el movimiento lateral de los atacantes. La segmentación se considera hoy la medida de mayor retorno en plantas manufactureras.[3]"),
        ("h1", "Amenazas"),
        ("p", "Los protocolos industriales heredados carecen de autenticación. Como se muestra en [4], un detector basado en aprendizaje automático identifica comandos anómalos sobre Modbus con alta sensibilidad."),
        ("p", "Los modelos de red y sus vulnerabilidades inherentes se describen con detalle en [5]. Para el caso de las redes OT de la región, Ibáñez [6] documenta configuraciones expuestas a internet."),
        ("h1", "Controles"),
        ("p", "Las guías nacionales recomiendan inventario de activos, parches priorizados y monitoreo continuo [7]. Una síntesis de los controles se aprecia en [3, Fig. 2]."),
        ("p", "Ambos enfoques, técnico y organizativo, son complementarios [2], [5]. La experiencia de las plantas piloto confirma que ninguno basta por sí solo."),
        ("h1", "Conclusiones"),
        ("p", "Las referencias [1]–[3] coinciden en que la segmentación, el inventario y la detección de anomalías deben implantarse de forma conjunta."),
    ],
    refs=[
        "K. Stouffer, J. Falco, and K. Scarfone, “Guide to industrial control systems (ICS) security,” NIST, Gaithersburg, MD, USA, Special Publication 800-82, Jun. 2011.",
        "M. Abomhara and G. M. Køien, “Cyber security and the Internet of Things: Vulnerabilities, threats, intruders and attacks,” *J. Cyber Secur. Mobility*, vol. 4, no. 1, pp. 65–88, 2015, doi: 10.13052/jcsm2245-1439.414.",
        "~L. Ibáñez and C. De la Cruz, “Segmentación de redes OT en plantas manufactureras,” *Rev. Iberoam. Autom. Inform. Ind.*, vol. 17, no. 2, pp. 150–161, Apr. 2020, doi: 10.4995/riai.2020.12345.",
        "R. Torres, “Detección de intrusiones en protocolos Modbus mediante aprendizaje automático,” *IEEE Access*, vol. 9, pp. 71234–71245, 2021, DOI: 10.1109/ACCESS.2021.3078123.",
        "A. S. Tanenbaum and D. J. Wetherall, *Computer Networks*, 5th ed. Boston, MA, USA: Pearson, 2011",
        "J. Ibáñez, “Seguridad en redes OT expuestas,” *Rev. Cibersegur.*, vol. 3, no. 1, 2021. [Online]. Available: https://rc.example.org/ibanez2021, doi: 10.7777/rc.2021.31.",
        "Instituto Nacional de Ciberseguridad, “Guía de seguridad en sistemas de control industrial,” INCIBE. Accessed: May 9, 2022. [Online]. Available: https://www.incibe.es/protege-tu-empresa/guias",
        "A. van der Berg, “Resiliencia de redes industriales ante ataques de denegación de servicio,” in *Proc. Int. Conf. Ind. Cybersecur.*, Madrid, Spain, 2020, pp. 21–28.",
    ],
    mutaciones=[],
    errores=[
        {"id": "IEEE-014", "desc": "La primera cita del documento es [2] y recien despues aparece [1]; el resto (3..7) aparece en orden. Todas las entradas existen."},
        {"id": "IEEE-002", "desc": "'plantas manufactureras.[3]': corchete despues del punto, fuera de la puntuacion. La entrada 3 existe y se cita ademas en otros lugares."},
        {"id": "IEEE-016", "desc": "La entrada 3 de la lista carece del '[3]' inicial. Colateral posible segun el juez: IEEE-012 si cuenta entradas por etiqueta en vez de por posicion; se siembra solo IEEE-016."},
        {"id": "IEEE-037", "desc": "Entrada [4] con 'DOI: 10.1109/...' (mayuscula) en vez de 'doi: 10...'; termina en punto."},
        {"id": "IEEE-038", "desc": "Entrada [5] (libro) sin punto final y sin terminar en URL."},
        {"id": "IEEE-040", "desc": "Entrada [6]: 'doi:' colocado despues de '[Online]. Available: URL' (el DOI va primero). El prefijo 'doi:' es correcto y la entrada termina en punto."},
        {"id": "IEEE-013", "desc": "Entrada [8] (van der Berg, 2020) nunca citada en el texto; las entradas 1-7 si estan citadas."},
        {"id": "IEEE-004", "desc": "'[1]–[3]' en las Conclusiones (rango con en dash). Los numeros 1, 2 y 3 ya estan citados individualmente antes, para no generar IEEE-013/014."},
    ],
)

# ----------------------------------------------------------------------------
# DOC 5  apa7-base+ieee-citas_correcto  (salud mental universitaria)
# ----------------------------------------------------------------------------
MIX1_OK = dict(
    plantilla="apa7-base+ieee-citas", salida="apa7-base+ieee-citas_correcto.docx", perfil="apa7-base+ieee-citas",
    titulo="Salud mental en estudiantes universitarios: factores de riesgo e intervenciones",
    autor="Valeria Contreras Núñez",
    ref_titulo="Referencias", salto_pagina=True, numerar="esp",
    items=[
        ("h1", "Introducción"),
        ("p", "La salud mental de los estudiantes universitarios se ha convertido en un tema prioritario para las instituciones de educación superior [1]. Diversos estudios reportan que entre 20 % y 35 % de los estudiantes presentan síntomas de ansiedad o depresión durante su primer año [2]."),
        ("p", "Ref. [1] define la salud mental como un estado de bienestar que permite afrontar las tensiones normales de la vida. Esta definición orienta el enfoque preventivo adoptado en este trabajo."),
        ("h1", "Factores de riesgo"),
        ("p", "Entre los factores más citados se encuentran la carga académica, la inseguridad económica y el aislamiento social [3]. Como se muestra en [4], el estrés académico predice el abandono de los estudios durante el primer año."),
        ("h2", "Evidencia cuantitativa"),
        ("p", "La participación en tutorías entre pares redujo los síntomas de ansiedad en un 18 % [3, Fig. 2]. Un resultado similar se reporta para estudiantes de ingeniería en [4]."),
        ("h1", "Intervenciones"),
        ("p", "Los servicios de orientación psicológica son el recurso más extendido [5]. Núñez [6] los describe como la primera línea de atención en el campus. Sin embargo, su cobertura es limitada: [2], [5] coinciden en que menos de un tercio de los estudiantes afectados recurre a ellos."),
        ("p", "Los programas integrados a la tutoría académica alcanzan mayor participación [6]. En [7] se establecen lineamientos oficiales para incorporar la atención en salud mental en los planes de bienestar institucional."),
        ("h1", "Conclusiones"),
        ("p", "La evidencia disponible sugiere combinar el acompañamiento entre pares con servicios profesionales [3], [5]. Se recomienda evaluar de forma continua el impacto de cada intervención, como se muestra en [6]."),
    ],
    refs=[
        "Organización Mundial de la Salud, “Salud mental de los adolescentes y jóvenes,” OMS. Accessed: Mar. 12, 2023. [Online]. Available: https://www.who.int/es/news-room/fact-sheets/detail/adolescent-mental-health",
        "R. P. Auerbach *et al.*, “WHO World Mental Health Surveys International College Student Project: Prevalence and distribution of mental disorders,” *J. Abnorm. Psychol.*, vol. 127, no. 7, pp. 623–638, Oct. 2018, doi: 10.1037/abn0000362.",
        "M. van der Berg and C. De la Cruz, “Programas de acompañamiento entre pares en universidades latinoamericanas,” *Rev. Psicol. Educ.*, vol. 12, no. 1, pp. 45–60, Jan. 2021, doi: 10.5555/rpe.2021.12145.",
        "A. Salazar, “Estrés académico y rendimiento en estudiantes de ingeniería,” in *Proc. 5th Int. Congr. Higher Educ.*, Bogotá, Colombia, 2019, pp. 112–119.",
        "L. Gómez Ramírez, *Psicología del bienestar universitario*, 2nd ed. Madrid, Spain: Pirámide, 2017.",
        "J. Núñez, “Servicios de orientación psicológica en el campus,” in *Educación Superior y Bienestar*, M. Ortiz, Ed. Mexico City, Mexico: UNAM Press, 2020, pp. 89–110.",
        "Ministerio de Educación, “Guía de salud mental para instituciones de educación superior,” Gobierno de Chile. Accessed: Jun. 5, 2023. [Online]. Available: https://www.mineduc.cl/guia-salud-mental",
    ],
    mutaciones=[], errores=[],
)

# ----------------------------------------------------------------------------
# DOC 6  apa7-base+ieee-citas_errores  (movilidad electrica)
# ----------------------------------------------------------------------------
MIX1_ERR = dict(
    plantilla="apa7-base+ieee-citas", salida="apa7-base+ieee-citas_errores.docx", perfil="apa7-base+ieee-citas",
    titulo="Electrificación del transporte urbano en ciudades intermedias",
    autor="Sebastián Ibáñez Quiroga",
    ref_titulo="Referencias", salto_pagina=False, numerar="esp",
    items=[
        ("h1", "Introducción"),
        ("p", "El transporte urbano genera cerca de una cuarta parte de las emisiones de dióxido de carbono del sector energético [1]. La electrificación de buses, taxis y flotas de reparto es la estrategia con mayor potencial de reducción [2], [3]."),
        ("p", "Ref. [2] propone un modelo de localización de estaciones de carga que minimiza el tiempo de espera de los usuarios. Como se muestra en [3, Fig. 2], el impacto de la carga simultánea sobre la red de distribución puede ser significativo en horas pico.", "justify"),
        ("h1", "Infraestructura de carga"),
        ("p", "La ubicación de las estaciones depende de la densidad de viajes y de la capacidad de la red local (Moreno, 2020). Las ciudades intermedias presentan además una menor disponibilidad de suelo urbano."),
        ("p", "Las flotas de reparto requieren cargadores de potencia media en los centros de distribución [4]. En [4], los autores optimizan las rutas considerando la autonomía de las baterías.", "georgia"),
        ("p", "     Las políticas de incentivo han sido determinantes en los países que lideran la adopción [5]. Según Ibáñez [6], las exenciones arancelarias explican buena parte del crecimiento de las ventas.", "spaces"),
        ("h1", "Políticas públicas"),
        ("p", "Los lineamientos nacionales fijan metas de renovación de flota para 2030 [7]. Las referencias [1, 2] coinciden en que el costo total de propiedad ya es competitivo para flotas de alto uso."),
        ("p", "Experiencias similares se reportan en varias ciudades europeas [9]."),
        ("h1", "Conclusiones"),
        ("p", "La electrificación del transporte urbano requiere coordinar infraestructura, regulación y financiamiento, como se muestra en [4]. Se recomienda priorizar las flotas de alto uso y los corredores de transporte público [2], [5].", "georgia"),
    ],
    refs=[
        "International Energy Agency, “Global EV outlook 2023,” IEA, Paris, France, Apr. 2023. [Online]. Available: https://www.iea.org/reports/global-ev-outlook-2023",
        "M. Moreno and L. Castaño, “Planificación de estaciones de carga en ciudades intermedias,” *IEEE Lat. Am. Trans.*, vol. 18, no. 5, pp. 812–820, May 2020, doi: 10.1109/TLA.2020.9082909.",
        "H. van der Berg, S. Ortega, and R. Lima, “Impacto de la electrificación del transporte público en la red de distribución,” *Energies*, vol. 14, no. 9, Art. no. 2501, Apr. 2021, doi: 10.3390/en14092501.",
        "P. Aguilar and T. De la Cruz, “Optimización de rutas para flotas eléctricas de reparto,” in *Proc. IEEE Int. Conf. Veh. Electron.*, Medellín, Colombia, 2019, pp. 1–6, doi: 10.1109/ICVE.2019.8888888.",
        "S. Pérez, *Movilidad urbana sostenible*, 1st ed. Santiago, Chile: Ed. Univ. Católica, 2018.",
        "R. Ibáñez, “Políticas de incentivo a vehículos eléctricos,” in *Transporte y Ciudad*, A. Salinas, Ed. Lima, Peru: Fondo Ed. PUCP, 2021, pp. 133–158.",
        "Ministerio de Transportes, “Estrategia nacional de movilidad eléctrica,” Gobierno de Chile. Accessed: Jun. 5, 2023. [Online]. Available: https://www.mtt.gob.cl/movilidad-electrica",
    ],
    mutaciones=["georgia", "justificado", "sangria_espacios"],
    errores=[
        {"id": "APA-003", "desc": "Dos parrafos de cuerpo (Infraestructura y Conclusiones) en Georgia 11 pt (fuente y tamaño permitidos por APA) mientras el resto esta en Times New Roman 12: dos fuentes en el cuerpo, sin disparar APA-002."},
        {"id": "APA-006", "desc": "Segundo parrafo de la Introduccion con alineacion justificada."},
        {"id": "APA-007", "desc": "Parrafo de 'Infraestructura de carga' iniciado con 5 espacios y con sangria de primera linea 0 (sin formato de parrafo)."},
        {"id": "APA-012", "desc": "El encabezado 'Referencias' sigue directamente a las Conclusiones, sin salto de pagina ni page_break_before."},
        {"id": "IEEE-001", "desc": "Cita autor-fecha '(Moreno, 2020)' en vez de [n]; la entrada [2] (Moreno) esta citada en otros lugares como [2], por lo que no hay IEEE-013."},
        {"id": "IEEE-003", "desc": "'[1, 2]' en vez de '[1], [2]' (Politicas publicas); las entradas 1 y 2 ya estan citadas antes."},
        {"id": "IEEE-012", "desc": "Cita '[9]' cuando la lista solo tiene 7 entradas."},
    ],
)

# ----------------------------------------------------------------------------
# DOC 7  ieee-base+apa7-citas_correcto  (energia solar)
# ----------------------------------------------------------------------------
AIE = "Agencia Internacional de Energía"
MIX2_OK = dict(
    plantilla="ieee-base+apa7-citas", salida="ieee-base+apa7-citas_correcto.docx", perfil="ieee-base+apa7-citas",
    titulo="Desempeño de sistemas fotovoltaicos en climas áridos",
    autor="Hugo Zúñiga Salazar",
    ref_titulo="REFERENCIAS", salto_pagina=False, numerar=None,
    items=[
        ("h1", "Introducción"),
        ("p", "La energía solar fotovoltaica es la fuente renovable de mayor crecimiento y seguirá liderando el aumento de la capacidad instalada en los próximos años (%s [AIE], 2022). En América Latina, las regiones áridas combinan alta radiación y baja nubosidad, condiciones favorables para esta tecnología (Ministerio de Energía y Minas, s.f.).".replace("%s", AIE)),
        ("p", "Mamani y Quispe (2021) demostraron que el sombreado parcial puede reducir hasta 30 % la producción de un arreglo conectado en serie. Estos hallazgos motivan el análisis de configuraciones alternativas."),
        ("h1", "Fundamentos"),
        ("p", "El dimensionamiento de sistemas aislados parte de la demanda diaria de energía y de las horas solares pico del sitio. De la Cruz (2019) recomienda añadir un margen de seguridad del 20 % para compensar pérdidas por suciedad y temperatura."),
        ("h2", "Degradación de módulos"),
        ("p", "En clima desértico, los módulos pierden entre 0,8 % y 1,2 % de potencia al año por estrés térmico (Jiménez et al., 2020). Jiménez et al. (2020) atribuyen buena parte de esa pérdida a la decoloración del encapsulante."),
        ("h2", "Almacenamiento"),
        ("p", "El almacenamiento con baterías de litio mejora la autonomía de las microrredes (Ramos, 2020a), aunque su costo sigue siendo la principal barrera (Ramos, 2020b). Ambos aspectos se discuten en conjunto (Ramos, 2020a, 2020b), y la vida útil esperada ronda los diez años (Ramos, 2020a, p. 41)."),
        ("h1", "Resultados"),
        ("p", "La comparación de tres configuraciones mostró que los microinversores superaron a los inversores centrales en sitios con sombreado parcial (Mamani & Quispe, 2021). El costo nivelado de la energía resultó coherente con las proyecciones internacionales (AIE, 2022)."),
        ("h1", "Conclusiones"),
        ("p", "Los sistemas fotovoltaicos en climas áridos son técnicamente viables, pero requieren un diseño cuidadoso frente al sombreado y la degradación térmica."),
    ],
    refs=[
        AIE + ". (2022). *Renewables 2022: Analysis and forecast to 2027*. https://www.iea.org/reports/renewables-2022",
        "De la Cruz, M. (2019). Cálculo de sistemas fotovoltaicos aislados. En R. Soto (Ed.), *Energías renovables en América Latina* (pp. 101-130). Editorial Tecnos.",
        "Jiménez, A., Ortega, P., & Salazar, B. (2020). Degradación de módulos fotovoltaicos en clima desértico. En *Actas del XV Congreso Iberoamericano de Energía Solar* (pp. 77-84). Asociación Peruana de Energía Solar.",
        "Mamani, R., & Quispe, L. (2021). Sombreado parcial y desempeño de arreglos fotovoltaicos. *Revista de Energías Renovables, 8*(1), 14-29. https://doi.org/10.1016/j.rer.2021.01.014",
        "Ministerio de Energía y Minas. (s.f.). *Atlas de radiación solar*. https://www.minem.gob.pe/atlas-solar",
        "Ramos, C. (2020a). Almacenamiento con baterías de litio en microrredes. *Energía y Sociedad, 12*(2), 33-50. https://doi.org/10.2222/es.2020.122",
        "Ramos, C. (2020b). Costos nivelados de energía en pequeñas instalaciones. *Energía y Sociedad, 12*(4), 71-88. https://doi.org/10.2222/es.2020.124",
    ],
    mutaciones=[], errores=[],
)

# ----------------------------------------------------------------------------
# DOC 8  ieee-base+apa7-citas_errores  (registros distribuidos)
# ----------------------------------------------------------------------------
OMA = "Organización Mundial de Aduanas"
MIX2_ERR = dict(
    plantilla="ieee-base+apa7-citas", salida="ieee-base+apa7-citas_errores.docx", perfil="ieee-base+apa7-citas",
    titulo="Registros distribuidos para la trazabilidad en cadenas de suministro agroalimentarias",
    autor="Marisol Peña Ferrer",
    ref_titulo="REFERENCIAS", salto_pagina=False, numerar=None,
    items=[
        ("h1", "Introducción"),
        ("p", "La trazabilidad de los alimentos exige registros confiables a lo largo de toda la cadena de suministro. Arias (2019) sostiene que los registros distribuidos reducen el tiempo de rastreo de lotes contaminados de días a segundos."),
        ("p", "Los contratos inteligentes automatizan la verificación de condiciones de transporte, como la temperatura, y liberan pagos de forma condicional (Castillo, Ferrer, & Montoya, 2020). Esta idea se discute también en el ámbito jurídico (Peña, 2017a, 2017b)."),
        ("h1", "Marco conceptual"),
        ("p", "Un registro distribuido mantiene copias sincronizadas de las transacciones entre los participantes. Gómez et al. (2021) analizan el consumo energético de los mecanismos de consenso y concluyen que las redes autorizadas bastan para consorcios logísticos (Gómez et al., 2021, p. 14)."),
        ("h2", "Aduanas y comercio internacional"),
        ("p", "Las administraciones aduaneras exploran estas tecnologías para agilizar la certificación de origen (%s [OMA], 2022). Según la misma fuente (ibid.), los pilotos requieren estándares de datos comunes.".replace("%s", OMA)),
        ("p", "Ibáñez y Torres (2018) describen una arquitectura de referencia con tres capas, que otras propuestas retoman (Ibáñez & Torres, 2018). El detalle jurídico de los contratos puede consultarse en Peña (2017a, p. 210)."),
        ("h1", "Discusión"),
        ("p", "La adopción depende de la gobernanza del consorcio y no solo de la tecnología (OMA, 2022). Los pilotos revisados muestran ahorros de tiempo, aunque con costos de integración altos."),
        ("h1", "Conclusiones"),
        ("p", "La cadena de suministro puede beneficiarse de registros distribuidos si se resuelven la gobernanza y la interoperabilidad. Se recomienda comenzar con consorcios pequeños y métricas claras."),
    ],
    refs=[
        "Arias, F. (2019). *Blockchain y trazabilidad alimentaria*. Ediciones Universitarias.",
        "Castillo, D., Ferrer, J., & Montoya, S. (2020). Trazabilidad con contratos inteligentes en el transporte refrigerado. *Revista de Logística Digital, 5*(2), 60-75. https://doi.org/10.3333/rld.2020.52",
        "Ibáñez, M., & Torres, C. (2018). Arquitectura de referencia para registros distribuidos en logística. *Revista de Sistemas Distribuidos, 3*(2), 88-102. https://doi.org/10.5555/rsd.2018.32.",
        "Gómez, P., Rivas, A., & Soto, L. (2021). Consumo energético de mecanismos de consenso en redes autorizadas. *Logística y Cadena de Valor, 11*(1), 9-24. doi:10.4444/lcv.2021.111",
        OMA + ". (2022). *Guía sobre tecnologías de registro distribuido en aduanas*. Recuperado de https://www.wcoomd.org/es/topics/facilitation",
        "Peña, R. (2017a). Contratos inteligentes en el comercio internacional. En A. Soto (Ed.), *Derecho y tecnología* (pp. 200-225). Editorial Jurídica.",
        "Peña, R. (2017b). Responsabilidad contractual en entornos automatizados. *Revista de Derecho Comercial, 21*(1), 77-96. https://doi.org/10.6666/rdc.2017.211",
        "Zambrano, E. (2018). *Gobernanza de datos en consorcios blockchain*. Editorial Nova.",
    ],
    mutaciones=[],
    errores=[
        {"id": "APA-034", "desc": "Entrada 'Zambrano, E. (2018)' nunca citada en el texto (todas las demas entradas estan citadas)."},
        {"id": "APA-038", "desc": "Cita '(Castillo, Ferrer, & Montoya, 2020)' con tres autores listados en vez de 'Castillo et al., 2020'."},
        {"id": "APA-042", "desc": "'(ibid.)' en la seccion Aduanas. Colateral posible: algun juez podria leerlo como cita sin entrada (APA-034); se siembra solo APA-042."},
        {"id": "APA-061", "desc": "Lista no alfabetica: 'Ibáñez' antecede a 'Gómez' (i antes de g). El resto esta en orden."},
        {"id": "APA-075", "desc": "Entrada de Ibáñez y Torres termina con punto despues del DOI (https://doi.org/10.5555/rsd.2018.32.)."},
        {"id": "APA-076", "desc": "Entrada de Gómez et al. con DOI como 'doi:10.4444/lcv.2021.111' en vez de https://doi.org/..., sin punto final (aislado de APA-075)."},
        {"id": "APA-079", "desc": "Entrada de la OMA con 'Recuperado de https://...' antes de la URL (sin fecha de consulta ni punto final)."},
    ],
)

DOCS = [APA7_OK, APA7_ERR, IEEE_OK, IEEE_ERR, MIX1_OK, MIX1_ERR, MIX2_OK, MIX2_ERR]


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
