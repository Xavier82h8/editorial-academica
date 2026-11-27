#!/usr/bin/env python3
"""Reglas de la tanda 2 (docs/PRIORIDAD-REGLAS.md): casos que deben saltar y casos que no.

Uso: python -I tests/run_reglas_tanda2.py
APA-048, 064, 074, 080, 081, 103 e IEEE-007, 015, 031, 032, 070, 129 (APA-032 y las rutas de .docx se prueban en
tests/generar_docs.py y en las muestras oficiales de tests/run_todo.py).
- 0 hallazgos en las 83 referencias oficiales de tests/corpus/apa7 y en las citas oficiales.
- IEEE: las 138 referencias de tests/corpus/ieee solo disparan IEEE-031 en los 5 ejemplos de la Reference Guide que escriben el
  rango de páginas con guion (erratas de la propia guía, ERRATAS_GUIA).
- Cada caso sembrado dispara exactamente su regla; cada caso limpio, ninguna.
"""
import json
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import auditar  # noqa: E402

REGLAS = {"APA-048", "APA-064", "APA-074", "APA-080", "APA-081", "APA-103",
          "IEEE-007", "IEEE-015", "IEEE-031", "IEEE-032", "IEEE-070", "IEEE-129"}
# Ejemplos de la Reference Guide 2025 con «pp. 17-20» (guion en vez de raya en): errata de la guía, no falso positivo.
ERRATAS_GUIA = {"ieee-ref-014", "ieee-ref-021", "ieee-ref-094", "ieee-ref-097", "ieee-ref-098"}

APELLIDOS = ["Alfa", "Beta", "Gamma", "Delta", "Epsilon", "Zeta", "Eta", "Theta", "Iota", "Kappa", "Lambda", "Mu", "Nu", "Xi",
             "Omicron", "Pi", "Rho", "Sigma", "Tau", "Upsilon", "Phi"]


def autores(n):
    return [f"{a}, A." for a in APELLIDOS[:n]]


AUT_19 = ", ".join(autores(19))
REFS_APA_OK = [
    "Pérez, A. (2020). Título. *Revista*, *3*(2), 1–2. https://doi.org/10.1000/abc.1",
    "Pérez, A. (2020). Título. Revista, 3, 11–20. https://doi.org/10.1000/abc.1",
    "Ríos, A. (2020). Título. En B. Soto (Ed.), *Libro* (pp. 10–20). Editorial.",
    "Mera, P. (2019, 24-26 de julio). Título. Sitio.",
    "Gil, B. (2020). Título. Informe No. 12-345. Editorial.",
    "Soto, C. (2021). Título. *Revista*, *3*(2), Artículo e12-4. https://doi.org/10.1000/abc.1-2",
    f"{AUT_19}, . . . {APELLIDOS[20]}, A. (2021). Título. Editorial.",
    f"{AUT_19}, … {APELLIDOS[20]}, A. (2021). Título. Editorial.",
    ", ".join(autores(20)[:19]) + f", & {APELLIDOS[19]}, A. (2021). Título. Editorial.",
    "Ortiz, P. (2018). Título. *Revista*, *4*(1), 10–20. https://www.sciencedirect.com/science/article/pii/S0123456789",
    "Gil, B. (2019). Título [Tesis doctoral, Universidad X]. ProQuest Dissertations. https://www.proquest.com/docview/12345",
    "Gil, B. (2019). Título. *Revista*, *4*(1), 10–20. http://www.jstor.org/stable/2742315",
    "Gil, B. (2019). Título. Sitio. https://www.ejemplo.org/articulo/12",
]
# (regla, entrada)
REFS_APA_MAL = [
    ("APA-074", "Pérez, A. (2020). Título. *Revista*, *3*(2), 1-2. https://doi.org/10.1000/abc.1"),
    ("APA-074", "Pérez, A. (2020). Título. Revista, 3, 11-20. https://doi.org/10.1000/abc.1"),
    ("APA-074", "Ríos, A. (2020). Título. En B. Soto (Ed.), *Libro* (pp. 10-20). Editorial."),
    ("APA-074", "Ríos, A. (2020). Título. En B. Soto (Ed.), *Libro* (pp. 10—20). Editorial."),
    ("APA-080", "Pérez, A. (2020). Título. *Revista*, *3*(2), 1–2. https://doi.org/10.1000/abc.1 https://revista.org/art/1"),
    ("APA-080", "Pérez, A. (2020). Título. *Revista*, *3*(2), 1–2. https://revista.org/art/1 doi:10.1000/abc.1"),
    ("APA-081", "Pérez, A. (2020). Título. *Revista*, *3*(2), 1–2. https://search.ebscohost.com/login.aspx?direct=true&AN=1"),
    ("APA-081", "Pérez, A. (2020). Título. *Revista*, *3*(2), 1–2. https://www.proquest.com/docview/123456"),
    ("APA-081", "Pérez, A. (2020). Título. Editorial. https://ebookcentral.proquest.com/lib/x/detail.action?docID=1"),
    ("APA-064", ", ".join(autores(21)[:20]) + f", & {APELLIDOS[20]}, A. (2021). Título. Editorial."),
    ("APA-064", f"{AUT_19}, . . . & {APELLIDOS[20]}, A. (2021). Título. Editorial."),
    ("APA-064", ", ".join(autores(6)) + f", . . . {APELLIDOS[20]}, A. (2021). Título. Editorial."),
]
CITAS_APA_OK = [
    "Según Pérez (2020), “el efecto fue grande en todos los grupos estudiados” (p. 4).",
    "El efecto fue “grande” en la muestra (Pérez, 2020) y “muy claro” (Gil, 2019).",
    "Lo llamó “la mejor forma de aprender” (Pérez, 2020).",
    "Pérez señaló que “el efecto fue grande en todos los grupos estudiados” (Pérez, 2020, p. 4).",
    "Pérez señaló que “el efecto fue grande en todos los grupos estudiados” (Pérez, 2020, pp. 4–5).",
    "Pérez señaló que “el efecto fue grande en todos los grupos estudiados” (Pérez, 2020, párr. 3).",
    "Pérez señaló que “el efecto fue grande en todos los grupos estudiados” (Pérez, 2020, cap. 2).",
    "Smith noted that “the effect was large in all groups studied” (Smith, 2020, para. 4).",
    "Pérez señaló que «el efecto fue grande en todos los grupos estudiados» (Pérez, 2020, p. 4).",
    "Pérez señaló que \"el efecto fue grande en todos los grupos estudiados\" (Pérez, 2020, p. 4).",
    "En el artículo “Efectos del sueño en el rendimiento escolar universitario” (Gil, 2020) se muestra el patrón.",
    "Como dijo un colega, “el efecto fue grande en todos los grupos estudiados” (J. Pérez, comunicación personal, 3 de marzo de 2020).",
    "El efecto fue grande en todos los grupos estudiados (Pérez, 2020) y “sorprendente” (Gil, 2019).",
    "Pérez señaló que “el efecto fue grande en todos los grupos estudiados”, como muestra la Figura 1.",
    "El FBI y la NASA publicaron el informe de la U.S. Census Bureau (2020) con el PhD de Pérez.",
    "J.R.R. Tolkien escribió la obra; Bimbo S.A.B. de C.V. reportó ganancias en EE. UU. y e.g. México.",
    "La sigla “F.B.I.” era la forma antigua, según la cita “el F.B.I. publicó el informe” (Gil, 2019, p. 3).",
]
CITAS_APA_MAL = [
    ("APA-048", "Pérez señaló que “el efecto fue grande en todos los grupos estudiados” (Pérez, 2020)."),
    ("APA-048", "Pérez señaló que \"el efecto fue grande en todos los grupos estudiados\" (Pérez, 2020)."),
    ("APA-048", "Pérez señaló: “El efecto fue grande en todos los grupos estudiados.” (Pérez, 2020)"),
    ("APA-048", "Pérez señaló que «el efecto fue grande en todos los grupos estudiados» (Pérez, 2020)."),
    ("APA-048", "Smith noted that “the effect was large in all groups studied” (Smith, 2020)."),
    ("APA-048", "Pérez señaló que “el efecto fue grande en todos los grupos estudiados” (Pérez, s. f.)."),
    ("APA-048", "Pérez señaló que “el efecto fue grande en todos los grupos estudiados” (Pérez et al., 2020; Gil, 2019)."),
    ("APA-103", "El F.B.I. publicó el informe sobre el caso."),
    ("APA-103", "Los E.U.A. firmaron el tratado en 2019."),
    ("APA-103", "Obtuvo el Ph.D. en 2019."),
    ("APA-103", "La U.S.A. creció."),
]
REFS_IEEE_OK = [
    "[1] J. K. Wood, A. Lee, and B. Kim, “Título uno,” *IEEE Trans. X*, vol. 5, no. 3, pp. 12–20, Jan. 2020.",
    "[2] J. K. Wood, “Título uno,” *IEEE Trans. X*, vol. 5, no. 3, p. 12, May 2020.",
    "[3] A. Smith, “Título,” in *Proc. Conf.*, Sep. 2019, pp. 1–5, doi: 10.1000/x.",
    "[4] A. Smith, “Título,” *Rev. Y*, vol. 7, Dec. 2021, Art. no. 4, doi: 10.1000/x.",
    "[5] A. Smith, “Notes from March 2020 and Sept. 2019,” *Rev. Y*, vol. 7, Mar. 2021.",
    "[6] A. Smith, Ed., Public Law No. 107-56, 2001.",
    "[7] S. Ansolabehere, M. Palmer, and A. Lee, January 20, 2014, “Precinct-Level Election Data. V1,” distributed by Harvard.",
    "[8] A. Smith, “Título,” *Rev. Y*, vol. 7, pp. 2.2-1–2.2-6, Jun. 2021.",
    "[9] A. Smith, “Título,” *Rev. Y*, vol. 7, pp. e12–e19, 2021. [Online]. Available: https://x.org/vol-2020-12-1",
]
REFS_IEEE_MAL = [
    ("IEEE-031", "[1] A. Smith, “Título,” *Rev. Y*, Vol. 7, no. 3, pp. 12–20, Jan. 2020."),
    ("IEEE-031", "[1] A. Smith, “Título,” *Rev. Y*, vol 7, no. 3, pp. 12–20, Jan. 2020."),
    ("IEEE-031", "[1] A. Smith, “Título,” *Rev. Y*, vol. 7, No. 3, pp. 12–20, Jan. 2020."),
    ("IEEE-031", "[1] A. Smith, “Título,” *Rev. Y*, vol. 7, no 3, pp. 12–20, Jan. 2020."),
    ("IEEE-031", "[1] A. Smith, “Título,” *Rev. Y*, vol. 7, no. 3, pp 12–20, Jan. 2020."),
    ("IEEE-031", "[1] A. Smith, “Título,” *Rev. Y*, vol. 7, no. 3, pp. 12-20, Jan. 2020."),
    ("IEEE-031", "[1] A. Smith, “Título,” *Rev. Y*, vol. 7, no. 3, p. 12–20, Jan. 2020."),
    ("IEEE-031", "[1] A. Smith, “Título,” *Rev. Y*, vol. 7, no. 3, pp. 12, Jan. 2020."),
    ("IEEE-031", "[1] A. Smith, “Título,” *Rev. Y*, vol. 7, no. 3, PP. 12–20, Jan. 2020."),
    ("IEEE-032", "[1] A. Smith, “Título,” *Rev. Y*, vol. 7, no. 3, pp. 12–20, January 2020."),
    ("IEEE-032", "[1] A. Smith, “Título,” *Rev. Y*, vol. 7, no. 3, pp. 12–20, June 3, 2020."),
    ("IEEE-032", "[1] A. Smith, “Título,” in *Proc. Conf.*, Sept. 2019, pp. 1–5."),
    ("IEEE-032", "[1] A. Smith, “Título,” *Rev. Y*, vol. 7, no. 3, pp. 12–20, Mar 2020."),
    ("IEEE-032", "[1] A. Smith, “Título,” *Rev. Y*, vol. 7, no. 3, pp. 12–20, 3 September 2020."),
]
ENTRADAS_CITA = [  # IEEE-007: 1 = tres autores; 2 = dos; 3 = uno; 4 = ocho (et al.)
    "[1] J. K. Wood, A. Lee, and B. Kim, “Título uno,” *Rev.*, vol. 1, no. 1, pp. 1–2, Jan. 2020.",
    "[2] A. Brown and C. Jones, “Título dos,” *Rev.*, vol. 1, no. 1, pp. 1–2, Jan. 2020.",
    "[3] D. Smith, “Título tres,” *Rev.*, vol. 1, no. 1, pp. 1–2, Jan. 2020.",
    "[4] E. Gray et al., “Título cuatro,” *Rev.*, vol. 1, no. 1, pp. 1–2, Jan. 2020.",
]
CUERPO_IEEE_OK = [
    "Wood et al. [1] demostraron el efecto.",
    "Brown and Jones [2] muestran el patrón.",
    "Smith [3] observó lo mismo.",
    "Gray et al. [4] lo confirman.",
    "In [1], the authors describe the method; see also Fig. [2] and Ref. [3].",
    "As shown in [2], the effect holds; Wood et al. [1], Brown and Jones [2] and Smith [3] agree.",
    "Los autores de [1] y de [4] coinciden; Table [2] resume los datos.",
]
CUERPO_IEEE_MAL = [
    "Wood and Lee [1] demostraron el efecto.",
    "Wood [1] demostró el efecto.",
    "Brown et al. [2] muestran el patrón.",
    "Brown [2] muestra el patrón.",
    "Smith et al. [3] observaron lo mismo.",
    "Gray [4] lo confirma.",
]
SIMBOLOS_OK = ["El sistema MATLAB y el protocolo Wi-Fi se usaron en el experimento (c) 2020."]
SIMBOLOS_MAL = ["El sistema MATLAB® se usó en el experimento.", "El protocolo Wi-Fi™ se usó en el experimento."]
# (regla esperada o None, documento md): encabezados IEEE
ENC_IEEE = [
    (None, "# I. INTRODUCTION\n\nTexto [1].\n\n# II. METHODS\n\nTexto.\n\n# ACKNOWLEDGMENT\n\nGracias.\n\n# REFERENCES\n\n[1] A. Smith, “Título,” *Rev.*, vol. 1, 2020."),
    (None, "# Introduction\n\nTexto [1].\n\n# REFERENCES\n\n[1] A. Smith, “Título,” *Rev.*, vol. 1, 2020."),
    ("IEEE-015", "# Introduction\n\nTexto [1].\n\n# V. REFERENCES\n\n[1] A. Smith, “Título,” *Rev.*, vol. 1, 2020."),
    ("IEEE-070", "# I. INTRODUCTION\n\nTexto [1].\n\n# II. METHODS\n\nTexto.\n\n# III. ACKNOWLEDGMENT\n\nGracias.\n\n# REFERENCES\n\n[1] A. Smith, “Título,” *Rev.*, vol. 1, 2020."),
    ("IEEE-070", "# I. INTRODUCTION\n\nTexto [1].\n\n# II. METHODS\n\nTexto.\n\n# IV. REFERENCES\n\n[1] A. Smith, “Título,” *Rev.*, vol. 1, 2020."),
]


def ids(h):
    return {x["id"] for x in h} & REGLAS


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    fallas = []
    corpus = json.loads((ROOT / "tests/corpus/apa7/referencias.json").read_text(encoding="utf-8"))
    ents = [{"texto": c["esperado"].replace("*", ""), "i": i} for i, c in enumerate(corpus)]
    for e in ents:
        for h in auditar.referencias_apa_tanda2([e]):
            fallas.append(f"FP corpus APA {h['id']}: {e['texto'][:80]}")
    citas = json.loads((ROOT / "tests/corpus/apa7/citas.json").read_text(encoding="utf-8"))
    ps = [{"texto": c["esperado"], "i": i} for i, c in enumerate(citas)]
    for h in auditar.cita_textual_apa(ps) + auditar.siglas_puntos_apa(ps):
        fallas.append(f"FP corpus citas APA {h['id']}: {h['evidencia']}")
    corpus_ieee = json.loads((ROOT / "tests/corpus/ieee/referencias.json").read_text(encoding="utf-8"))
    vistos = set()
    for c in corpus_ieee:
        for h in auditar.lista_ieee_tanda2([{"texto": c["esperado"], "i": 0}]):
            if h["id"] == "IEEE-031" and c["id"] in ERRATAS_GUIA:
                vistos.add(c["id"])
            else:
                fallas.append(f"FP corpus IEEE {h['id']} {c['id']}: {h['evidencia']}")
    if vistos != ERRATAS_GUIA:
        fallas.append(f"erratas de la guía no detectadas: {sorted(ERRATAS_GUIA - vistos)}")
    for t in REFS_APA_OK:
        got = ids(auditar.referencias_apa_tanda2([{"texto": t, "i": 0}]))
        if got:
            fallas.append(f"FP {sorted(got)} en «{t[:80]}»")
    for regla, t in REFS_APA_MAL:
        got = ids(auditar.referencias_apa_tanda2([{"texto": t, "i": 0}]))
        if got != {regla}:
            fallas.append(f"{regla}: salió {sorted(got)} para «{t[:80]}»")
    for t in CITAS_APA_OK:
        p = [{"texto": t, "i": 0}]
        got = ids(auditar.cita_textual_apa(p) + auditar.siglas_puntos_apa(p))
        if got:
            fallas.append(f"FP {sorted(got)} en «{t[:80]}»")
    for regla, t in CITAS_APA_MAL:
        p = [{"texto": t, "i": 0}]
        got = ids(auditar.cita_textual_apa(p) + auditar.siglas_puntos_apa(p))
        if got != {regla}:
            fallas.append(f"{regla}: salió {sorted(got)} para «{t[:80]}»")
    for t in REFS_IEEE_OK:
        got = ids(auditar.lista_ieee_tanda2([{"texto": t, "i": 0}]))
        if got:
            fallas.append(f"FP {sorted(got)} en «{t[:80]}»")
    for regla, t in REFS_IEEE_MAL:
        got = ids(auditar.lista_ieee_tanda2([{"texto": t, "i": 0}]))
        if got != {regla}:
            fallas.append(f"{regla}: salió {sorted(got)} para «{t[:80]}»")
    entradas = [{"texto": t, "i": i} for i, t in enumerate(ENTRADAS_CITA)]
    for t in CUERPO_IEEE_OK:
        got = ids(auditar.nombres_en_cita_ieee([{"texto": t, "i": 0}], entradas))
        if got:
            fallas.append(f"FP {sorted(got)} en «{t[:80]}»")
    for t in CUERPO_IEEE_MAL:
        got = ids(auditar.nombres_en_cita_ieee([{"texto": t, "i": 0}], entradas))
        if got != {"IEEE-007"}:
            fallas.append(f"IEEE-007: salió {sorted(got)} para «{t[:80]}»")
    for t in SIMBOLOS_OK:
        if ids(auditar.simbolos_ieee([{"texto": t, "i": 0}])):
            fallas.append(f"FP IEEE-129 en «{t[:80]}»")
    for t in SIMBOLOS_MAL:
        if ids(auditar.simbolos_ieee([{"texto": t, "i": 0}])) != {"IEEE-129"}:
            fallas.append(f"IEEE-129 no salió para «{t[:80]}»")
    with tempfile.TemporaryDirectory() as tmp:
        for k, (regla, md) in enumerate(ENC_IEEE):
            f = pathlib.Path(tmp) / f"enc{k}.md"
            f.write_text(md, encoding="utf-8")
            got = ids(auditar.auditar(str(f), "ieee")["hallazgos"]) & {"IEEE-015", "IEEE-070"}
            if got != ({regla} if regla else set()):
                fallas.append(f"encabezados IEEE caso {k}: se esperaba {regla}, salió {sorted(got)}")
    for f in fallas:
        print("FALLA", f)
    n = (len(corpus) + len(citas) + len(corpus_ieee) + len(REFS_APA_OK) + len(REFS_APA_MAL) + len(CITAS_APA_OK) + len(CITAS_APA_MAL)
         + len(REFS_IEEE_OK) + len(REFS_IEEE_MAL) + len(CUERPO_IEEE_OK) + len(CUERPO_IEEE_MAL) + len(SIMBOLOS_OK) + len(SIMBOLOS_MAL) + len(ENC_IEEE))
    print(f"== reglas tanda 2: {n} casos, {len(fallas)} fallas")
    sys.exit(1 if fallas else 0)


if __name__ == "__main__":
    main()
