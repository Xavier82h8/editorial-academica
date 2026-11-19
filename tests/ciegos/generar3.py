# -*- coding: utf-8 -*-
"""Genera 8 .docx (4 perfiles x correcto/errores) + esperado.json en tests/ciegos/docs3/.
Uso: python -I tests/ciegos/generar3.py
"""
import json, re, shutil, sys
from pathlib import Path
import docx
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.opc.constants import RELATIONSHIP_TYPE as RT

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "scripts"))
import crear_plantillas  # noqa: E402
PLANT = crear_plantillas.asegurar_plantillas()
SALIDA = Path(__file__).resolve().parent / "docs3"
TOKEN = re.compile(r"(\*[^*]+\*|<<[^>]+>>)")


def _fmt(run, font, size, italic=False):
    run.font.name = font
    run._element.rPr.rFonts.set(qn("w:eastAsia"), font)
    run.font.size = Pt(size)
    if italic:
        run.italic = True


def runs(p, texto, font, size):
    for tr in TOKEN.split(texto):
        if not tr:
            continue
        if tr.startswith("*"):
            _fmt(p.add_run(tr[1:-1]), font, size, italic=True)
        elif tr.startswith("<<"):
            url = tr[2:-2]
            # hipervínculo como campo HYPERLINK: todos los runs cuelgan de <w:p> y p.text conserva la URL
            def _fc(tipo):
                r = p.add_run(); c = OxmlElement("w:fldChar"); c.set(qn("w:fldCharType"), tipo); r._r.append(c)
            _fc("begin")
            r = p.add_run(); it = OxmlElement("w:instrText"); it.set(qn("xml:space"), "preserve")
            it.text = f' HYPERLINK "{url}" '; r._r.append(it)
            _fc("separate")
            rr = p.add_run(url); _fmt(rr, font, size)
            rr.font.underline = True
            from docx.shared import RGBColor
            rr.font.color.rgb = RGBColor(0x05, 0x63, 0xC1)
            _fc("end")
        else:
            _fmt(p.add_run(tr), font, size)


def nuevo(plantilla):
    d = docx.Document(str(PLANT / f"{plantilla}.docx"))
    body = d.element.body
    for el in list(body):
        if el.tag != qn("w:sectPr"):
            body.remove(el)
    s = d.sections[0]
    for m in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
        setattr(s, m, Inches(1))
    return d


def construir(nombre, plantilla, apa_layout, contenido, fuente, ref_fuente, ref_modo, ref_titulo, mods):
    font, size = fuente
    rfont, rsize = ref_fuente or fuente
    d = nuevo(plantilla)
    d.core_properties.title = contenido["titulo"]
    d.core_properties.author = "Autor de prueba"
    p = d.add_paragraph(style="Title")
    runs(p, contenido["titulo"], font, size)
    p.runs[0].bold = True
    for bloque in contenido["bloques"]:
        tipo, txt = bloque[0], bloque[1]
        pid = bloque[2] if len(bloque) > 2 else None
        if tipo == "h":
            p = d.add_paragraph(style="Heading 1")
            runs(p, txt, font, size)
            continue
        fn, sz = font, size
        if pid and mods.get(pid) == "fuente_otra":
            fn, sz = "Arial", 11
        p = d.add_paragraph(style="Body Text")
        runs(p, txt, fn, sz)
        if pid and mods.get(pid) == "sangria_espacios":
            p.paragraph_format.first_line_indent = Inches(0)
        if pid and mods.get(pid) == "interlineado_simple":
            p.paragraph_format.line_spacing = 1.0
        if "justificar" in mods:
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    h = d.add_paragraph(style="Heading 1")
    runs(h, ref_titulo, font, size)
    if apa_layout and "sin_pagina_nueva" not in mods:
        h.paragraph_format.page_break_before = True
    for i, ref in enumerate(contenido["refs"], 1):
        p = d.add_paragraph(style="Bibliography")
        if ref_modo == "apa":
            runs(p, ref, rfont, rsize)
            if "sin_francesa" in mods:
                p.paragraph_format.left_indent = Inches(0)
                p.paragraph_format.first_line_indent = Inches(0)
            else:
                p.paragraph_format.left_indent = Inches(0.5)
                p.paragraph_format.first_line_indent = Inches(-0.5)
        else:  # ieee: [n]<tab>texto, columna numérica colgante
            etiqueta = f"{i}." if "num_sin_corchetes" in mods else f"[{i}]"
            ancho = Inches(0.5) if apa_layout else Inches(0.35)
            p.paragraph_format.left_indent = ancho
            p.paragraph_format.first_line_indent = -ancho
            p.paragraph_format.tab_stops.add_tab_stop(ancho)
            runs(p, f"{etiqueta}\t{ref}", rfont, rsize)
    if "sin_numero_pagina" in mods:
        for hp in d.sections[0].header.paragraphs:
            for ch in list(hp._p):
                if ch.tag != qn("w:pPr"):
                    hp._p.remove(ch)
    if "margen_izq" in mods:
        d.sections[0].left_margin = Inches(1.5)
    d.save(str(SALIDA / nombre))


def V(err, clave, ok, bad):
    return bad if clave in err else ok


# ----------------------------------------------------------------- A: apa7
def cont_apa7(e):
    v = lambda k, a, b: V(e, k, a, b)
    b = [
        ("h", "Introducción"),
        ("p", "El crecimiento acelerado de las ciudades intermedias ha incrementado la superficie impermeable y, con ella, el volumen de escorrentía durante tormentas de corta duración. Salas y Díaz (2019) mostraron que los colectores combinados se desbordan con lluvias de periodo de retorno de apenas dos años. Por ello, diversas ciudades han incorporado jardines de lluvia y pavimentos permeables como medidas complementarias a la red gris (Lamas, 2021; "
              + v("APA-037", "Salas & Díaz", "Salas y Díaz") + ", 2019)."),
        ("p", "Los registros recientes confirman la tendencia. El Servicio Meteorológico Nacional [SMN] (2020) informó que la intensidad de las precipitaciones máximas diarias aumentó 12 % durante la última década, un cambio que presiona aún más a la infraestructura existente (SMN, 2020). La guía técnica del Ministerio de Ambiente (s.f.) recomienda evaluar la infiltración del suelo antes de definir el tipo de intervención."),
        ("h", "Método"),
        ("p", "Se modelaron cuatro microcuencas urbanas con SWMM v5.2 y los resultados se procesaron con un complemento escrito para la plataforma .NET. Cada microcuenca se calibró con registros pluviométricos horarios, y el nivel freático se mantuvo a una profundidad media de 0.75 m. La comparación entre escenarios se basó en el caudal pico simulado para una tormenta de diseño de 50 mm en una hora."),
        ("h", "Resultados"),
        ("p", "Los jardines de lluvia redujeron el caudal pico en 38 % respecto del escenario base "
              + v("APA-038", "(Ruiz et al., 2020, p. 14)", "(Ruiz, Mena & Paz, 2020, p. 14)")
              + ". La diferencia entre escenarios fue estadísticamente significativa (p < .05), mientras que los pavimentos permeables mostraron un efecto menor y dependiente del tipo de suelo."),
        ("h", "Discusión"),
        ("p", "Estos hallazgos concuerdan con lo planteado por Torres (2017), quien advierte que la eficacia de las medidas descentralizadas depende de su mantenimiento. En consecuencia, la planificación municipal debería asociar cada obra de infraestructura verde con un presupuesto operativo sostenido en el tiempo."),
    ]
    lamas = ("Lamas, J. (2021). Pavimentos permeables en climas húmedos: Una revisión sistemática. *Ingeniería del Agua*, *25*(2), 101–118. "
             + v("APA-079", "<<https://doi.org/10.4995/ia.2021.14562>>", "Recuperado de <<https://doi.org/10.4995/ia.2021.14562>>"))
    r = {
        "lamas": lamas,
        "min": "Ministerio de Ambiente. (s.f.). *Guía de drenaje urbano sostenible*. <<https://www.ambiente.example.org/guia-drenaje>>",
        "ruiz": "Ruiz, C., Mena, P., & Paz, D. (2020). Jardines de lluvia y reducción de caudales pico en microcuencas urbanas. *Revista de Hidrología Aplicada*, *14*(1), 5–22. <<https://doi.org/10.1234/rha.2020.014>>",
        "salas": "Salas, M., & Díaz, R. (2019). Capacidad de colectores combinados ante lluvias intensas. *Tecnología y Ciencias del Agua*, *10*(4), 33–57. <<https://doi.org/10.24850/j-tyca-2019-04-02>>",
        "smn": "Servicio Meteorológico Nacional. (2020). *Informe climático anual 2019* (Informe técnico n.º 45). <<https://www.smn.example.org/informe-2019>>",
        "torres": "Torres, L. (2017). *Hidrología urbana aplicada* (2.ª ed.). Editorial Andina.",
    }
    orden = ["lamas", "min", "ruiz", "salas", "smn", "torres"]
    if "APA-061" in e:
        orden = ["torres", "lamas", "min", "ruiz", "salas", "smn"]
    return {"titulo": "Infraestructura verde y reducción de la escorrentía pluvial en ciudades intermedias",
            "bloques": b, "refs": [r[k] for k in orden]}


# ----------------------------------------------------------------- B: ieee
def cont_ieee(e):
    v = lambda k, a, b: V(e, k, a, b)
    b = [
        ("h", "I. INTRODUCCIÓN"),
        ("p", v("IEEE-014",
                "La adopción de servicios en la nube por parte de las pequeñas y medianas empresas (PYMEs) ha ampliado su superficie de ataque [1]. Los informes sectoriales indican que el ransomware afecta con mayor frecuencia a organizaciones de menos de 250 empleados [2], [3].",
                "La adopción de servicios en la nube por parte de las pequeñas y medianas empresas (PYMEs) ha ampliado su superficie de ataque [2]. Los informes sectoriales indican que el ransomware afecta con mayor frecuencia a organizaciones de menos de 250 empleados [1], [3].")
              + " Brown [4] sostiene que la ausencia de personal dedicado a seguridad explica buena parte de esa brecha."),
        ("h", "II. MARCO DE REFERENCIA"),
        ("p", "El marco de ciberseguridad del NIST organiza las actividades en cinco funciones: identificar, proteger, detectar, responder y recuperar [1]. Su perfil para organizaciones pequeñas simplifica la selección de controles [3, Fig. 1], tal como se resume en la Fig. 2 [1]. Para la lista de controles básicos véase la Ref. [3]. "
              + v("IEEE-001", "Según Brown [4], los controles de acceso son los de mayor retorno de inversión.",
                  "Según (Brown, 2020), los controles de acceso son los de mayor retorno de inversión.")),
        ("h", "III. METODOLOGÍA"),
        ("p", "Se encuestó a 120 PYMEs de tres ciudades mediante un cuestionario aplicado con una herramienta desarrollada en .NET (v2.1). La tasa de respuesta fue de 0.75 y las respuestas se codificaron según los controles del marco [1]. Las prácticas de respaldo se contrastaron con las descritas en un estudio previo"
              + v("IEEE-002", " [5].", ".[5]")),
        ("h", "IV. RESULTADOS"),
        ("p", "Solo el 35 % de las empresas verificaba sus copias de seguridad, y la correlación entre esa práctica y la ausencia de incidentes fue r = "
              + v("IEEE-119", "0.25", ".25")
              + ". La adopción de autenticación multifactor, en cambio, se asoció con una reducción marcada de accesos indebidos "
              + v("IEEE-004", "[4], [5], [6]", "[4]–[6]") + "."),
        ("h", "V. CONCLUSIONES"),
        ("p", "Los resultados sugieren que las PYMEs deberían priorizar respaldos verificados y autenticación multifactor, tal como proponen otros estudios "
              + v("IEEE-003", "[2], [3]", "[2, 3]")
              + ". Para trabajos futuros se recomienda ampliar la muestra y medir el tiempo de recuperación tras incidentes reales [6]."
              + v("IEEE-012", "", " La guía regional ofrece métricas adicionales [7].")),
    ]
    refs = [
        "National Institute of Standards and Technology, \"Framework for improving critical infrastructure cybersecurity, version 1.1,\" NIST, Gaithersburg, MD, USA, Tech. Rep. CSWP 6, Apr. 2018, doi: 10.6028/NIST.CSWP.04162018" + v("IEEE-038", ".", ""),
        "Verizon, \"2023 data breach investigations report,\" Verizon, New York, NY, USA, 2023. [Online]. Available: https://www.verizon.example.com/dbir",
        "J. Smith and A. Gómez, \"Cyber hygiene in small enterprises,\" *IEEE Secur. Privacy*, vol. 19, no. 3, pp. 24–31, May 2021, " + v("IEEE-037", "doi", "DOI") + ": 10.1109/MSEC.2021.3059167.",
        "R. Brown, *Security for Small Businesses*. New York, NY, USA: Wiley, 2020.",
        "L. Pérez, M. Rojas, and C. Vega, \"Backup practices and ransomware recovery in SMEs,\" in *Proc. IEEE Int. Conf. Cyber Secur.*, Lima, Peru, 2022, pp. 112–119.",
        "A. Torres, \"Zero trust in micro-enterprises,\" *J. Inf. Secur.*, vol. 7, no. 2, pp. 55–70, 2021"
        + v("IEEE-040", ", doi: 10.1000/jis.2021.07. [Online]. Available: https://www.jis.example.org/7/2/55",
            ". [Online]. Available: https://www.jis.example.org/7/2/55, doi: 10.1000/jis.2021.07."),
    ]
    return {"titulo": "Prácticas de ciberseguridad y recuperación ante ransomware en pequeñas y medianas empresas",
            "bloques": b, "refs": refs}


# ----------------------------------------------------------------- C: apa7 base + ieee citas
def cont_apa_ieee(e):
    v = lambda k, a, b: V(e, k, a, b)
    b = [
        ("h", "Introducción"),
        ("p", "El consumo excesivo de azúcares libres en la infancia se asocia con sobrepeso y caries dental "
              + v("IEEE-003", "[1], [2]", "[1, 2]")
              + ". En el entorno escolar, los kioscos son una fuente frecuente de productos ultraprocesados, y su regulación sigue siendo heterogénea entre países [3]. Castro y Vera [2] señalan que los comedores escolares mejoran la calidad de la dieta cuando incorporan supervisión nutricional.", "APA-007"),
        ("p", "Sin embargo, la evidencia sobre el cumplimiento de las normas en los kioscos es escasa, como se resume en la Ref. [3, p. 45] y en la Fig. 1 [4]."),
        ("h", "Método"),
        ("p", "Se evaluó a 240 estudiantes de cuatro escuelas mediante un registro alimentario de tres días, procesado con una aplicación basada en .NET y la versión v2.1 del cuestionario de frecuencia de consumo [5]. El volumen medio de bebidas azucaradas fue de 0.75 L diarios por grupo. La intervención educativa siguió el protocolo previo"
              + v("IEEE-002", " [4].", ".[4]"), "APA-003"),
        ("h", "Resultados"),
        ("p", "El consumo de frutas aumentó 22 % tras la intervención, y la diferencia entre grupos fue significativa (p < .05). La proporción de estudiantes que adquiría bebidas azucaradas en el kiosco disminuyó de 64 % a 41 %, un cambio coherente con lo observado por Núñez et al. [4].", "APA-004"),
        ("h", "Discusión"),
        ("p", "Los resultados son consistentes con [2], donde el acompañamiento nutricional mejoró la dieta. No obstante, el cumplimiento de la normativa nacional vigente"
              + v("IEEE-013", " [6]", "") + " es parcial, por lo que se recomienda fortalecer la fiscalización [3]."),
    ]
    refs = [
        "World Health Organization, \"Guideline: Sugars intake for adults and children,\" WHO, Geneva, Switzerland, 2015. [Online]. Available: https://www.who.example.int/sugars-guideline",
        "M. Castro and L. Vera, \"Comedores escolares y estado nutricional infantil,\" *Rev. Nutr. Pública*, vol. 18, no. 2, pp. 77–90, Jun. 2020, doi: 10.5678/rnp.2020.18.2.77" + v("IEEE-038", ".", ""),
        "A. Ibarra, *Alimentación en la edad escolar*, 3rd ed. Madrid, Spain: Médica Ed., 2018.",
        "S. Núñez, D. Paredes, and J. Soto, \"Intervención educativa y consumo de frutas en primaria,\" in *Proc. Congr. Latinoam. Nutr.*, Bogotá, Colombia, 2021, pp. 201–208.",
        "K. Lund, \"Validation of a food frequency questionnaire for school children,\" *Nutrients*, vol. 12, no. 4, Art. no. 1021, Apr. 2020, doi: 10.3390/nu12041021.",
        "Ministerio de Educación, \"Normas para kioscos escolares saludables,\" Lima, Perú, Informe técnico 12, 2019.",
    ]
    return {"titulo": "Kioscos escolares y hábitos alimentarios en estudiantes de primaria",
            "bloques": b, "refs": refs}


# ----------------------------------------------------------------- D: ieee base + apa7 citas
def cont_ieee_apa(e):
    v = lambda k, a, b: V(e, k, a, b)
    b = [
        ("h", "I. INTRODUCCIÓN"),
        ("p", "La falta de acceso a electricidad continúa limitando la educación en zonas rurales dispersas. Según la Agencia Internacional de Energía [AIE] (2021), la capacidad solar instalada se duplicará en cinco años, aunque la electrificación escolar avanza con lentitud (AIE, 2021). Los costos y las barreras de operación han sido analizados desde la ingeniería y las ciencias sociales (Gómez et al., 2020; Pérez, 2020). El Ministerio de Energía y Minas (s.f.) ofrece un programa nacional que prioriza las escuelas sin conexión."),
        ("h", "II. MARCO TEÓRICO"),
        ("p", "El dimensionamiento de un sistema aislado depende de la irradiación local, el consumo diario y los días de autonomía (Gómez et al., 2020). Salas y Díaz (2019) compararon baterías de plomo-ácido y de litio y concluyeron que estas últimas reducen el costo por ciclo de vida, aunque exigen mayor inversión inicial ("
              + v("APA-037", "Salas & Díaz", "Salas y Díaz") + ", 2019)."),
        ("h", "III. METODOLOGÍA"),
        ("p", "Se dimensionaron sistemas para 18 escuelas con una hoja de cálculo desarrollada en .NET (v2.1). La irradiación media diaria utilizada fue de 5.4 kWh/m², y el factor de pérdidas del sistema se fijó en 0.75, valor adoptado de Gómez et al. (2020)."
              + v("APA-034", "", " El procedimiento sigue una práctica ampliamente adoptada (Okafor, 2021).")),
        ("h", "IV. RESULTADOS"),
        ("p", "El costo medio por escuela fue de USD 8 400, y el coeficiente de correlación entre irradiación y ahorro fue de r = "
              + v("IEEE-119", "0.25", ".25")
              + ". El mantenimiento comunitario redujo las fallas, un hallazgo coincidente con el de otros programas (Vega & Rojas, "
              + v("APA-035", "2018", "2016") + "). En la microred piloto, el tiempo de recuperación de la inversión fue de seis años (Pérez, 2020, p. 14). La vida útil de las baterías fue similar a la reportada "
              + v("APA-042", "(Pérez, 2020, p. 22)", "(ibid., p. 22)") + "."),
        ("h", "V. CONCLUSIONES"),
        ("p", "La electrificación fotovoltaica de escuelas rurales es técnicamente viable y económicamente razonable si se acompaña de formación comunitaria. Se recomienda que el Ministerio de Energía y Minas (s.f.) y las autoridades educativas coordinen el seguimiento de los sistemas instalados."),
    ]
    refs = [
        "Agencia Internacional de Energía. (2021). *Energías renovables 2021: Análisis y previsiones hasta 2026*. <<https://www.iea.example.org/renovables-2021>>",
        "Gómez, H., Ibáñez, T., & Marín, F. (2020). Dimensionamiento de sistemas fotovoltaicos aislados para escuelas rurales. *Energías Renovables y Medio Ambiente*, *45*, 33–47. "
        + v("APA-079", "<<https://doi.org/10.5555/erma.2020.45.33>>", "Recuperado de <<https://doi.org/10.5555/erma.2020.45.33>>"),
        "Ministerio de Energía y Minas. (s.f.). *Programa nacional de electrificación rural*. <<https://www.minem.example.gob/pner>>",
        "Pérez, A. (2020). *Energía solar para comunidades aisladas*. Editorial Sol.",
        "Salas, M., & Díaz, R. (2019). Baterías de litio en sistemas aislados: Costos y ciclo de vida. *Revista de Ingeniería Eléctrica*, *9*(2), 12–29. <<https://doi.org/10.7777/rie.2019.9.2.12>>"
        + v("APA-075", "", "."),
        "Vega, S., & Rojas, N. (2018). Mantenimiento comunitario de paneles solares. *Desarrollo Rural Sostenible*, *6*(1), 88–101. "
        + v("APA-076", "<<https://doi.org/10.8888/drs.2018.6.1.88>>", "DOI: 10.8888/drs.2018.6.1.88"),
    ]
    return {"titulo": "Electrificación fotovoltaica de escuelas rurales: dimensionamiento, costos y mantenimiento",
            "bloques": b, "refs": refs}


# ----------------------------------------------------------------- esperado
DESC = {
    "apa7": {
        "APA-001": "Margen izquierdo de 1.5 in (los otros tres de 1 in).",
        "APA-002": "Todo el documento en Verdana 12, fuente no permitida por APA 7.",
        "APA-006": "Todos los párrafos del cuerpo con alineación justificada.",
        "APA-037": "Primera cita parentética múltiple en Introducción: '(Lamas, 2021; Salas y Díaz, 2019)' con 'y' en vez de '&'.",
        "APA-038": "En Resultados: '(Ruiz, Mena & Paz, 2020, p. 14)' con tres autores en la primera cita, debía ser 'Ruiz et al.'.",
        "APA-059": "La lista se titula 'Bibliografía' en lugar de 'Referencias'.",
        "APA-061": "Lista de referencias desordenada: Torres (2017) aparece antes que Lamas, Ministerio, Ruiz, Salas y SMN.",
        "APA-079": "Entrada Lamas (2021) con 'Recuperado de' antes del DOI.",
    },
    "ieee": {
        "IEEE-001": "En Marco de referencia: 'Según (Brown, 2020)' cita autor-año en vez de número entre corchetes.",
        "IEEE-002": "En Metodología: '...estudio previo.[5]' corchete después del punto.",
        "IEEE-003": "En Conclusiones: '[2, 3]' en un solo corchete.",
        "IEEE-004": "En Resultados: rango '[4]–[6]' en lugar de '[4], [5], [6]'.",
        "IEEE-012": "Conclusiones cita '[7]' pero la lista solo tiene 6 entradas.",
        "IEEE-014": "Primera cita del texto es [2] y después [1], [3]: la numeración no sigue el orden de primera aparición.",
        "IEEE-037": "Referencia [3] usa 'DOI: 10.1109/...' en mayúscula.",
        "IEEE-038": "Referencia [1] termina en DOI sin punto final.",
        "IEEE-040": "Referencia [6]: el DOI va después de '[Online]. Available: URL'.",
        "IEEE-119": "En Resultados: 'r = .25' sin cero inicial.",
    },
    "apa7-base+ieee-citas": {
        "APA-003": "Párrafo de Método en Arial 11 mientras el resto del documento va en Times New Roman 12.",
        "APA-004": "Párrafo de Resultados con interlineado simple (1.0) en vez de doble.",
        "APA-007": "Primer párrafo de Introducción con sangría hecha con 5 espacios (sangría de primera línea 0).",
        "APA-008": "Encabezado sin número de página (se vació el campo PAGE).",
        "APA-012": "El encabezado 'Referencias' no inicia en página nueva.",
        "IEEE-002": "En Método: '...protocolo previo.[4]' corchete después del punto.",
        "IEEE-003": "En Introducción: '[1, 2]' en un solo corchete.",
        "IEEE-013": "La referencia [6] (Ministerio de Educación) no se cita en el texto.",
        "IEEE-016": "Las entradas de la lista están numeradas '1.', '2.'... sin corchetes.",
        "IEEE-038": "Referencia [2] termina en DOI sin punto final.",
    },
    "ieee-base+apa7-citas": {
        "APA-034": "En Metodología se cita '(Okafor, 2021)' que no tiene entrada en la lista.",
        "APA-035": "En Resultados '(Vega & Rojas, 2016)' pero la lista dice 2018.",
        "APA-037": "En Marco teórico: '(Salas y Díaz, 2019)' con 'y' en parentética en vez de '&'.",
        "APA-042": "En Resultados: '(ibid., p. 22)' en lugar de repetir la cita completa.",
        "APA-060": "Lista de referencias sin sangría francesa (todas las entradas a ras izquierdo).",
        "APA-075": "Entrada Salas y Díaz (2019) con punto final después del DOI.",
        "APA-076": "Entrada Vega y Rojas (2018) con 'DOI: 10.8888/...' en texto plano, sin https://doi.org/ ni hipervínculo.",
        "APA-079": "Entrada Gómez et al. (2020) con 'Recuperado de' antes del DOI.",
        "IEEE-119": "En Resultados: 'r = .25' sin cero inicial.",
    },
}

PERFILES = [
    # nombre, apa_layout, builder, fuente, ref_fuente, ref_modo, ref_titulo
    ("apa7", True, cont_apa7, ("Times New Roman", 12), None, "apa", "Referencias"),
    ("ieee", False, cont_ieee, ("Times New Roman", 10), ("Times New Roman", 8), "ieee", "REFERENCIAS"),
    ("apa7-base+ieee-citas", True, cont_apa_ieee, ("Times New Roman", 12), None, "ieee", "Referencias"),
    ("ieee-base+apa7-citas", False, cont_ieee_apa, ("Times New Roman", 10), ("Times New Roman", 8), "apa", "REFERENCIAS"),
]

# ID -> (modificación de formato, id de párrafo o None)
MODS = {
    "APA-001": ("margen_izq", None), "APA-002": ("fuente_global", None), "APA-006": ("justificar", None),
    "APA-003": ("fuente_otra", "APA-003"), "APA-004": ("interlineado_simple", "APA-004"),
    "APA-007": ("sangria_espacios", "APA-007"), "APA-008": ("sin_numero_pagina", None),
    "APA-012": ("sin_pagina_nueva", None), "APA-060": ("sin_francesa", None),
    "IEEE-016": ("num_sin_corchetes", None),
}


def main():
    if SALIDA.exists():
        shutil.rmtree(SALIDA)
    SALIDA.mkdir(parents=True)
    esperado = {}
    for nombre, apa_layout, fn, fuente, rf, rm, rt in PERFILES:
        for variante in ("correcto", "errores"):
            err = set(DESC[nombre]) if variante == "errores" else set()
            mods = {}
            for i in err:
                if i in MODS:
                    nom, pid = MODS[i]
                    mods[pid if pid else nom] = nom
            fte = ("Verdana", 12) if "fuente_global" in mods else fuente
            contenido = fn(err)
            if "APA-007" in mods:
                contenido["bloques"] = [
                    (t[0], "     " + t[1], t[2]) if len(t) > 2 and t[2] == "APA-007" else t
                    for t in contenido["bloques"]
                ]
            construir(f"{nombre}_{variante}.docx", nombre, apa_layout, contenido, fte,
                      (None if "fuente_global" in mods else rf), rm,
                      "Bibliografía" if "APA-059" in err else rt, mods)
            esperado[f"{nombre}_{variante}.docx"] = {
                "perfil": nombre,
                "errores": [{"id": i, "desc": DESC[nombre][i]} for i in sorted(err)],
            }
    with open(SALIDA / "esperado.json", "w", encoding="utf-8") as f:
        json.dump(esperado, f, ensure_ascii=False, indent=2)
    print("OK", len(esperado), "docs")


if __name__ == "__main__":
    main()
