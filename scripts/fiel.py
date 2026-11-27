#!/usr/bin/env python3
"""Modo fiel de `corregir` (v0.10.0): el ajuste no toca el texto.

`corregir --fiel` solo cambia propiedades de formato. Cada corrección que cambiaría texto (rótulos de sección, forma y orden de las
referencias, citas, numeración o mayúsculas de títulos, puntuación, siglas, rótulos de tablas y figuras) se emite como PROPUESTA en
`<doc>.propuestas.json` y una lista legible; se aplica solo con `corregir --aplicar-propuestas ARCHIVO [--solo ID,ID]`.
Tras cualquier `corregir`, `fidelidad.py` compara el texto del original con el de la salida (certificado de fidelidad).

Cómo se generan las propuestas: sobre la salida fiel se corre cada regla de texto de `corregir.ORDEN_TEXTO`, una tras otra y
encadenadas, con el mismo corrector de siempre (`solo={regla}`); lo que cambia párrafo a párrafo es una propuesta. Al aplicarlas se
repite la cadena y se toma de cada paso solo el párrafo aprobado. Es determinista: mismo original y mismas opciones, mismo resultado
(el JSON guarda el sha256 del original y se rechaza si cambió).
"""
import copy
import hashlib
import json
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import auditar  # noqa: E402
import fidelidad  # noqa: E402

from docx.oxml.ns import qn  # noqa: E402

VERSION_PROPUESTAS = 1


def sha256(ruta):
    return hashlib.sha256(pathlib.Path(ruta).read_bytes()).hexdigest()


def _oculto(out, clave):
    return out.with_name(f".fiel-{clave}-{out.name}")


def _firmas(C, ruta):
    """[(texto, numId)] de cada párrafo (mismo orden que `corregir.elementos`) y los elementos."""
    d = auditar.abrir_docx(str(ruta))
    els = C.elementos(d)
    out = []
    for el in els:
        n = el.find(qn("w:pPr") + "/" + qn("w:numPr") + "/" + qn("w:numId"))
        v = n.get(qn("w:val")) if n is not None else None
        out.append((C.texto_de(el), None if v in (None, "0") else v))
    return d, els, out


def _mostrar(texto, num):
    return texto + (" [numeración automática de Word]" if num else "")


def _ubic(i, texto):
    t = " ".join(texto.split())
    return f"párrafo {i + 1}: «{t[:50]}{'…' if len(t) > 50 else ''}»"


def generar(C, base, perfil, r_fiel, out, log):
    """Propuestas de texto sobre la salida fiel `base`. Devuelve la lista de propuestas."""
    candidatos = [x for x in C.ORDEN_TEXTO if r_fiel["despues"].get(x)]
    _, _, f_base = _firmas(C, base)
    cur, f_cur = base, f_base
    propuestas = []
    creados = []
    try:
        for k, regla in enumerate(candidatos):
            nxt = _oculto(out, f"p{k}")
            creados.append(nxt)
            rr = C._corregir(cur, perfil, nxt, {regla}, True)
            if rr is None or not nxt.exists():
                continue
            _, _, f_nxt = _firmas(C, nxt)
            if len(f_nxt) != len(f_cur):
                log(f"Aviso: {regla}: la corrección cambia el número de párrafos; no se propone")
                continue
            cambios = [i for i in range(len(f_cur)) if f_cur[i] != f_nxt[i]]
            if not cambios:
                cur, f_cur = nxt, f_nxt
                continue
            if regla == "APA-061":  # el orden de la lista es una sola decisión
                propuestas.append({"regla": regla, "indices": cambios,
                                   "ubicacion": f"lista de referencias, {len(cambios)} entradas en otro orden (párrafos {cambios[0] + 1} a {cambios[-1] + 1})",
                                   "antes": [f_base[i][0] for i in cambios], "despues": [f_nxt[i][0] for i in cambios],
                                   "antes_base": [f_base[i][0] for i in cambios], "agrupada": True})
            else:
                for i in cambios:
                    propuestas.append({"regla": regla, "indices": [i], "ubicacion": _ubic(i, f_base[i][0]),
                                       "antes": _mostrar(*f_base[i]), "despues": _mostrar(*f_nxt[i]),
                                       "antes_base": [f_base[i][0]], "agrupada": False})
            cur, f_cur = nxt, f_nxt
    finally:
        for c in creados:
            c.unlink(missing_ok=True)
    for n, p in enumerate(propuestas, 1):
        p["id"] = f"P{n:03d}"
        p["motivo"] = C.MOTIVO_TEXTO.get(p["regla"], p["regla"])
    return propuestas


def escribir_propuestas(ruta, original, perfil, opciones, propuestas):
    datos = {"version": VERSION_PROPUESTAS, "documento": str(original), "sha256_original": sha256(original), "perfil": perfil,
             "opciones": opciones, "propuestas": propuestas}
    pathlib.Path(ruta).write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")


def imprimir_propuestas(propuestas, ruta, original, log):
    if not propuestas:
        log("Propuestas de cambio de texto: ninguna")
        return
    log(f"PROPUESTAS de cambio de texto ({len(propuestas)}): NO se aplicaron; el texto del documento queda como está. Archivo: {ruta}")
    for p in propuestas:
        log(f"  {p['id']} {p['regla']}  {p['ubicacion']}")
        a, b = p["antes"], p["despues"]
        if isinstance(a, list):
            for x, y in list(zip(a, b))[:6]:
                log(f"      antes:   {fidelidad._corto(x)}\n      después: {fidelidad._corto(y)}")
            if len(a) > 6:
                log(f"      … y {len(a) - 6} entradas más (en el JSON)")
        else:
            log(f"      antes:   {fidelidad._corto(a, 160)}\n      después: {fidelidad._corto(b, 160)}")
        log(f"      motivo:  {p['motivo']}")
    log(f"Para aplicar las que apruebes: corregir {original} --aplicar-propuestas {ruta} [--solo {propuestas[0]['id']},…]  (ids o reglas)")


def _elegidas(propuestas, solo_ids):
    if not solo_ids:
        return list(propuestas)
    s = {x.strip().upper() for x in solo_ids}
    return [p for p in propuestas if p["id"].upper() in s or p["regla"].upper() in s]


def aplicar(C, base, perfil, out, datos, solo_ids, log):
    """Aplica las propuestas aprobadas sobre `base` (salida fiel). Devuelve (ruta final, textos aprobados, aplicadas, avisos)."""
    elegidas = _elegidas(datos["propuestas"], solo_ids)
    desconocidas = [x for x in (solo_ids or []) if not any(x.strip().upper() in (p["id"].upper(), p["regla"].upper()) for p in datos["propuestas"])]
    avisos = [f"--solo {x}: no hay ninguna propuesta con ese id o regla" for x in desconocidas]
    _, _, f_base = _firmas(C, base)
    cur = base
    aprobados, aplicadas = [], []
    creados = []
    try:
        for k, regla in enumerate(C.ORDEN_TEXTO):
            ps = [p for p in elegidas if p["regla"] == regla]
            if not ps:
                continue
            nxt = _oculto(out, f"a{k}")
            creados.append(nxt)
            rr = C._corregir(cur, perfil, nxt, {regla}, True)
            if rr is None or not nxt.exists():
                avisos.append(f"{regla}: la corrección no produjo salida; propuestas {', '.join(p['id'] for p in ps)} sin aplicar")
                continue
            dc, ec, fc = _firmas(C, cur)
            dn, en, fn = _firmas(C, nxt)
            if len(ec) != len(en):
                avisos.append(f"{regla}: el número de párrafos cambió; propuestas {', '.join(p['id'] for p in ps)} sin aplicar")
                continue
            for p in ps:
                ok = True
                for j, i in enumerate(p["indices"]):
                    if i >= len(f_base) or f_base[i][0] != p["antes_base"][j]:
                        avisos.append(f"{p['id']}: el párrafo {i + 1} ya no coincide con lo propuesto (¿otro documento u otras opciones?); sin aplicar")
                        ok = False
                        break
                    if fc[i] == fn[i]:
                        avisos.append(f"{p['id']}: la regla ya no cambia el párrafo {i + 1}; sin aplicar")
                        ok = False
                        break
                if not ok:
                    continue
                for i in p["indices"]:
                    aprobados += [f_base[i][0], fc[i][0], fn[i][0]]
                    ec[i].getparent().replace(ec[i], copy.deepcopy(en[i]))
                aplicadas.append(p["id"])
            sig = _oculto(out, f"b{k}")
            creados.append(sig)
            dc.save(str(sig))
            cur = sig
        return cur, aprobados, aplicadas, avisos
    finally:
        for c in creados:
            if c != cur:
                c.unlink(missing_ok=True)


def corregir_con_certificado(path, perfil, out, solo, silencioso, paginacion, portada_numero, fiel, aplicar_json, solo_ids):
    import corregir as C  # el módulo importado (no `__main__` cuando corre vía runpy): ahí viven _corregir, ORDEN_TEXTO y elementos
    log = (lambda *a, **k: None) if silencioso else print
    tmp1 = _oculto(out, "1")
    limpiar = [tmp1]
    try:
        r = C._corregir(path, perfil, tmp1, solo, silencioso, paginacion, portada_numero, excluir_texto=fiel, etiqueta_salida=out)
        if r is None:
            return None
        final, aprobados, propuestas, avisos_f = tmp1, [], [], []
        ruta_prop = path.with_name(path.stem + ".propuestas.json")
        aplicadas = []
        if fiel and aplicar_json:
            ruta_j = pathlib.Path(aplicar_json)
            if not ruta_j.is_file():
                raise SystemExit(f"--aplicar-propuestas: no existe {aplicar_json}")
            try:
                datos = json.loads(ruta_j.read_text(encoding="utf-8"))
                datos["propuestas"], datos["sha256_original"]
            except (ValueError, KeyError, TypeError):
                raise SystemExit(f"--aplicar-propuestas: {aplicar_json} no es un archivo de propuestas válido")
            if datos["sha256_original"] != sha256(path):
                raise SystemExit(f"--aplicar-propuestas: {aplicar_json} se generó para otro contenido del documento (sha256 distinto); genera las propuestas de nuevo con --fiel")
            if datos.get("perfil") and datos["perfil"] != perfil:
                log(f"Aviso: las propuestas se generaron con el perfil {datos['perfil']} y se aplican con {perfil}")
            final, aprobados, aplicadas, avisos_f = aplicar(C, tmp1, perfil, out, datos, solo_ids, log)
            if final != tmp1:
                limpiar.append(final)
            propuestas = datos["propuestas"]
            log(f"Propuestas aplicadas: {', '.join(aplicadas) if aplicadas else '(ninguna)'}")
            for a_ in avisos_f:
                log("Aviso: " + a_)
            pend = [p for p in propuestas if p["id"] not in aplicadas]
            if pend:
                log(f"Propuestas sin aplicar: {', '.join(p['id'] for p in pend)} (siguen en {aplicar_json})")
        elif fiel:
            propuestas = generar(C, tmp1, perfil, r, out, log)
            escribir_propuestas(ruta_prop, path, perfil, {"paginacion": paginacion, "portada_numero": portada_numero,
                                                       "solo": sorted(solo) if solo else None}, propuestas)
            imprimir_propuestas(propuestas, ruta_prop, path, log)
        cert = fidelidad.comparar_texto(path, final, aprobados, modo="fiel" if fiel else "completo")
        if fiel and cert["no_aprobados_n"]:
            fidelidad.imprimir(cert, lambda *a: print(*a, file=sys.stderr))
            print("ERROR modo fiel: la salida cambia texto que nadie aprobó; no se escribe la salida. "
                  "Esto es un defecto de la corrección: repórtalo con el documento.", file=sys.stderr)
            raise SystemExit(1)
        os.replace(final, out)
        log(f"Salida escrita: {out}")
        fidelidad.imprimir(cert, log)
        r["salida"] = str(out)
        r["modo"] = ("fiel + propuestas aplicadas" if aplicar_json else "fiel") if fiel else "completo"
        r["fidelidad"] = cert
        r["propuestas"] = propuestas
        r["propuestas_aplicadas"] = aplicadas
        if fiel and not aplicar_json:
            r["propuestas_archivo"] = str(ruta_prop)
        r["avisos"] = list(r["avisos"]) + avisos_f
        return r
    finally:
        for c in limpiar:
            c.unlink(missing_ok=True)
