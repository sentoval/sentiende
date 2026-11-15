# -*- coding: utf-8 -*-
"""Fase 9 · Checklist (M-09, M-10, M-24). Comprueba lo que pide la variante para la finalidad
del expediente: por titular o por expediente, con sus condiciones (en vigor, últimos N meses,
último ejercicio, antigüedad máxima). Devuelve el estado de cada documento y los avisos al cliente."""
import datetime

PAPELES_TITULAR = {"Titular", "Cotitular"}

def _meses_atras(hoy, n):
    """Los n meses completos anteriores a hoy, del más reciente al más antiguo."""
    out, a, m = [], hoy.year, hoy.month
    for _ in range(n):
        m -= 1
        if m == 0:
            m, a = 12, a - 1
        out.append(datetime.date(a, m, 1))
    return out

def evaluar(variante, almacen, expediente_id, hoy=None):
    hoy = hoy or datetime.date.today()
    exp = almacen.expediente(expediente_id)
    items = variante.checklists.get(exp["finalidad"], [])
    personas = [p for p in almacen.personas_de(expediente_id) if p["papel"] in PAPELES_TITULAR]
    docs = almacen.documentos("expediente_id = ? AND estado = 'guardado'", (expediente_id,))
    filas, avisos = [], []
    for it in items:
        grupos = [(p, [d for d in docs if d["tipo"] == it["tipo"] and d["persona_id"] == p["id"] and not d["de_expediente"]]) for p in personas] \
            if it["por"] == "titular" else [(None, [d for d in docs if d["tipo"] == it["tipo"]])]
        for persona, encontrados in grupos:
            estado, detalle = _condicion(it.get("condicion", {}), encontrados, hoy)
            quien = f'{persona["nombre"]} {persona["apellido1"]}'.strip() if persona else "Expediente"
            nombre_tipo = variante.docs.get(it["tipo"], {}).get("nombres", {}).get("es", [it["tipo"]])[0]
            filas.append({"tipo": it["tipo"], "documento": nombre_tipo, "quien": quien, "estado": estado,
                          "detalle": detalle, "importancia": it.get("importancia"), "archivos": [d["nombre_final"] for d in encontrados]})
            if estado in ("Caducado", "Incompleto"):
                avisos.append(f"{nombre_tipo} · {quien}: {detalle}")
    recibidos = sum(1 for f in filas if f["estado"] == "Recibido")
    return {"finalidad": exp["finalidad"], "recibidos": recibidos, "total": len(filas), "filas": filas, "avisos_cliente": avisos}

def _condicion(cond, docs, hoy):
    if not docs:
        return "Pendiente", ""
    if cond.get("en_vigor"):
        cads = [d["datos"].get("caducidad") for d in docs if d["datos"] and d["datos"].get("caducidad")]
        if not cads:
            return "Recibido", "Caducidad no leída: revisar"
        if max(datetime.date.fromisoformat(c) for c in cads) < hoy:
            return "Caducado", f"caducó el {datetime.date.fromisoformat(max(cads)):%d/%m/%Y}"
        return "Recibido", f"en vigor hasta {datetime.date.fromisoformat(max(cads)):%d/%m/%Y}"
    if n := cond.get("ultimos_meses"):
        pedidos = _meses_atras(hoy, n)
        tiene = {datetime.date.fromisoformat(d["datos"]["periodo"]) for d in docs if d["datos"] and d["datos"].get("periodo")}
        faltan = [m for m in pedidos if m not in tiene]
        if not faltan:
            return "Recibido", f"{n} de {n}"
        nombres = ", ".join(f"{m:%m/%Y}" for m in faltan)
        return "Incompleto", f"{n - len(faltan)} de {n} · falta {nombres}"
    if cond.get("ultimo_ejercicio"):
        ej = {d["datos"].get("ejercicio") for d in docs if d["datos"]}
        return ("Recibido", f"ejercicio {hoy.year - 1}") if (hoy.year - 1) in ej else ("Incompleto", f"falta el ejercicio {hoy.year - 1}")
    if dias := cond.get("max_dias"):
        fechas = [datetime.date.fromisoformat(d["datos"]["fechas"][0]) for d in docs if d["datos"] and d["datos"].get("fechas")]
        if not fechas:
            return "Recibido", "Fecha no leída: revisar"
        f = max(fechas)
        if (hoy - f).days > dias:
            return "Caducado", f"tiene {(hoy - f).days} días (máximo {dias})"
        return "Recibido", f"del {f:%d/%m/%Y}"
    return "Recibido", ""
