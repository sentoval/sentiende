# -*- coding: utf-8 -*-
"""Arreglar lo ya guardado (v1.1): mover un documento a otro expediente, unir dos expedientes
y unir dos fichas de la misma persona.

Nunca se borra un documento ni un original: los archivos se mueven (y se renombran si cambia
la persona); todo queda en el historial de eventos."""
import datetime, json, shutil
from pathlib import Path
from . import checklist, textos
from .carpetas import libre


from .motor import MotorError


class ErrorArreglo(MotorError):
    pass


def _refrescar(m, eid):
    """Checklist, avisos y registro de texto de un expediente después de un cambio."""
    a = m.almacen
    e = a.expediente(eid)
    if not e or e["estado"] != "abierto":
        return
    res = checklist.evaluar(m.variante, a, eid)
    a.poner_avisos_cliente(eid, res["avisos_cliente"])
    nuevo = textos.generar(a, m.carpetas.documentos, eid, m.variante.nombres["sin_dni"])
    for f in Path(nuevo).parent.glob("*_textos.txt"):      # si cambió el primer titular, el registro viejo sobra
        if f != Path(nuevo) and f.read_text(encoding="utf-8-sig", errors="ignore").startswith("REGISTRO DE TEXTO RECONOCIDO"):
            f.unlink()


def _nombre(m, d, persona):
    entidad = m.clasificador.abrev5(d["entidad"]) if d["entidad"] else None
    entrada = datetime.date.fromisoformat(d["creado"][:10])
    if d["tipo"] in m.variante.docs:
        return m.nombrador.nombre(d["tipo"], persona, d["datos"] or {}, entidad, entrada, bool(d["privado"]), Path(d["ruta_final"]).suffix)[0]
    return Path(d["ruta_final"]).name


def _papel_nuevo(a, eid):
    return "Cotitular" if any(p["papel"] == "Titular" for p in a.personas_de(eid)) else "Titular"


def _colocar(m, d, exp, persona, mover_original=True):
    """Pone el archivo final (y su original) en la carpeta del expediente con el nombre que toca."""
    a, c = m.almacen, m.carpetas
    final = Path(d["ruta_final"] or "")
    if not final.exists():
        raise ErrorArreglo(f"No encuentro el archivo guardado: {final}")
    nombre = _nombre(m, d, persona)
    dir_doc = c.documentos / exp["carpeta"]
    dir_doc.mkdir(parents=True, exist_ok=True)
    destino = final if final.parent == dir_doc and final.name == nombre else libre(dir_doc / nombre)
    if destino != final:
        shutil.move(str(final), destino)
    cambios = {"nombre_final": destino.name, "ruta_final": str(destino)}
    orig = Path(d["ruta_original_final"] or "")
    dir_orig = c.originales / exp["carpeta"]
    if mover_original and orig.is_file() and orig.parent != dir_orig:
        dir_orig.mkdir(parents=True, exist_ok=True)
        # el original puede ser de varias partes de un mismo archivo: si alguna se queda, se copia
        otros = [x for x in a.documentos("ruta_original_final = ? AND id != ?", (str(orig), d["id"]))
                 if x["expediente_id"] != exp["id"]]
        nuevo = libre(dir_orig / orig.name)
        (shutil.copy2 if otros else shutil.move)(str(orig), nuevo)
        cambios["ruta_original_final"] = str(nuevo)
    elif orig.is_dir() and orig != dir_orig:          # PDF unido desde fotos: los originales son varias fotos
        dir_orig.mkdir(parents=True, exist_ok=True)
        for fu in a.documentos("unido_en = ?", (d["id"],)):
            f = Path(fu["ruta_original_final"] or "")
            if f.is_file():
                n = libre(dir_orig / f.name)
                shutil.move(str(f), n)
                a.actualizar(fu["id"], ruta_original_final=str(n))
        cambios["ruta_original_final"] = str(dir_orig)
    return cambios


def mover_documento(m, doc_id, expediente_id, persona_id=None, de_expediente=None):
    """Lleva un documento guardado a otro expediente (o a otra persona del mismo).
    persona_id: de quién es; si no se indica, la misma persona si está en el destino, o el primer titular."""
    a = m.almacen
    d = a.documento(doc_id)
    if not d or d["estado"] != "guardado":
        raise ErrorArreglo("Solo se pueden mover documentos ya guardados en un expediente.")
    exp = a.expediente(expediente_id)
    if not exp:
        raise ErrorArreglo(f"No existe el expediente {expediente_id}.")
    de_expediente = bool(d["de_expediente"]) if de_expediente is None else bool(de_expediente)
    antes = d["expediente_id"]
    personas = a.personas_de(expediente_id)
    if de_expediente:
        persona = personas[0]
    else:
        pid = persona_id or d["persona_id"]
        persona = a.persona(pid)
        if not persona:
            raise ErrorArreglo("Esa persona no existe.")
        if pid not in [p["id"] for p in personas]:
            papel = _papel_nuevo(a, expediente_id)
            a.anadir_persona(expediente_id, pid, papel)
            a.evento(f"{persona['nombre']} {persona['apellido1']} añadida al expediente «{exp['nombre']}» como {papel}", doc_id, d["lote_id"])
    cambios = _colocar(m, d, exp, persona)
    a.actualizar(doc_id, expediente_id=expediente_id, persona_id=persona["id"], de_expediente=int(de_expediente), **cambios)
    a.evento(f"Arreglo: movido de «{(a.expediente(antes) or {}).get('nombre', '?')}» a «{exp['nombre']}» · ahora se llama {cambios['nombre_final']}", doc_id, d["lote_id"])
    for eid in {antes, expediente_id}:
        _refrescar(m, eid)
    return a.documento(doc_id)


def unir_expedientes(m, origen_id, destino_id):
    """Pasa todo lo del expediente origen al destino (personas y documentos) y cierra el origen."""
    a = m.almacen
    if origen_id == destino_id:
        raise ErrorArreglo("Elige dos expedientes distintos.")
    o, dst = a.expediente(origen_id), a.expediente(destino_id)
    if not o or not dst:
        raise ErrorArreglo("No existe alguno de los dos expedientes.")
    ya = {p["id"] for p in a.personas_de(destino_id)}
    for p in a.personas_de(origen_id):
        if p["id"] not in ya:
            a.anadir_persona(destino_id, p["id"], _papel_nuevo(a, destino_id) if p["papel"] == "Titular" else p["papel"])
            ya.add(p["id"])
    docs = a.documentos("expediente_id = ? AND estado = 'guardado'", (origen_id,))
    for d in docs:
        mover_documento(m, d["id"], destino_id, d["persona_id"], d["de_expediente"])
    # lo que aún esté en revisión apuntando al origen pasa al destino
    a.db.execute("UPDATE documentos SET expediente_id = ? WHERE expediente_id = ?", (destino_id, origen_id))
    a.db.execute("UPDATE expedientes SET estado = 'unido' WHERE id = ?", (origen_id,))
    a.db.commit()
    a.poner_avisos_cliente(origen_id, [])
    # carpetas vacías del origen: el registro de texto se crea solo y se puede quitar
    c = m.carpetas
    dd = c.documentos / o["carpeta"]
    for f in dd.glob("*.txt") if dd.exists() else []:
        if f.name == textos.nombre_registro(a, origen_id, m.variante.nombres["sin_dni"]):
            f.unlink()
    for carpeta in (dd, c.originales / o["carpeta"]):
        if carpeta.exists() and not any(carpeta.iterdir()):
            carpeta.rmdir()
    a.evento(f"Arreglo: expediente «{o['nombre']}» unido a «{dst['nombre']}» ({len(docs)} documentos)")
    _refrescar(m, destino_id)
    return {"destino": destino_id, "documentos": len(docs)}


def unir_personas(m, quitar_id, quedar_id, forzar=False):
    """Dos fichas de la misma persona: todo lo de 'quitar' pasa a 'quedar' y la ficha sobrante se elimina.
    Los documentos se renombran si su código cambia (p. ej. el DNI)."""
    a = m.almacen
    if quitar_id == quedar_id:
        raise ErrorArreglo("Elige dos personas distintas.")
    q, k = a.persona(quitar_id), a.persona(quedar_id)
    if not q or not k:
        raise ErrorArreglo("No existe alguna de las dos personas.")
    if q["dni"] and k["dni"] and q["dni"].upper() != k["dni"].upper() and not forzar:
        raise ErrorArreglo(f"Tienen DNI distintos ({q['dni']} y {k['dni']}): no pueden ser la misma persona. "
                           "Si uno está mal leído, confirma y se quedará el DNI de la ficha que se conserva.")
    afectados = set()
    for r in a.db.execute("SELECT * FROM expediente_personas WHERE persona_id = ?", (quitar_id,)).fetchall():
        eid = r["expediente_id"]
        afectados.add(eid)
        esta = a.db.execute("SELECT papel FROM expediente_personas WHERE expediente_id = ? AND persona_id = ?", (eid, quedar_id)).fetchone()
        if esta:
            if r["papel"] == "Titular" and esta["papel"] != "Titular":      # se queda el papel más fuerte
                a.db.execute("UPDATE expediente_personas SET papel = 'Titular', orden = ? WHERE expediente_id = ? AND persona_id = ?", (r["orden"], eid, quedar_id))
            a.db.execute("DELETE FROM expediente_personas WHERE expediente_id = ? AND persona_id = ?", (eid, quitar_id))
        else:
            a.db.execute("UPDATE expediente_personas SET persona_id = ? WHERE expediente_id = ? AND persona_id = ?", (quedar_id, eid, quitar_id))
    docs = a.documentos("persona_id = ?", (quitar_id,))
    a.db.execute("UPDATE documentos SET persona_id = ? WHERE persona_id = ?", (quedar_id, quitar_id))
    from .extraer import norm
    alias = json.loads(k.get("alias") or "[]") + json.loads(q.get("alias") or "[]")
    for x in [norm(f'{q["nombre"]} {q["apellido1"]} {q["apellido2"] or ""}').strip()]:
        if x not in alias:
            alias.append(x)
    a.db.execute("UPDATE personas SET alias = ? WHERE id = ?", (json.dumps(sorted(set(alias)), ensure_ascii=False), quedar_id))
    a.db.execute("DELETE FROM personas WHERE id = ?", (quitar_id,))
    if not k["dni"] and q["dni"]:
        a.db.execute("UPDATE personas SET dni = ? WHERE id = ?", (q["dni"], quedar_id))
    for campo in ("apellido2",):
        if not k[campo] and q[campo]:
            a.db.execute(f"UPDATE personas SET {campo} = ? WHERE id = ?", (q[campo], quedar_id))
    a.db.commit()
    persona = a.persona(quedar_id)
    for d in docs:
        d = a.documento(d["id"])
        if d["estado"] == "guardado" and d["expediente_id"]:
            cambios = _colocar(m, d, a.expediente(d["expediente_id"]), persona, mover_original=False)
            a.actualizar(d["id"], **cambios)
            afectados.add(d["expediente_id"])
    a.evento(f"Arreglo: «{q['nombre']} {q['apellido1']}» (ficha {quitar_id}) unida a «{k['nombre']} {k['apellido1']}» (ficha {quedar_id})")
    for eid in afectados:
        _refrescar(m, eid)
    return persona


def quitar_persona(m, expediente_id, persona_id):
    """Quita a una persona de un expediente (p. ej. un cotitular añadido por error). Solo si no tiene
    documentos guardados en él; si después no está en ningún expediente ni tiene documentos, se borra su ficha."""
    a = m.almacen
    exp, p = a.expediente(expediente_id), a.persona(persona_id)
    if not exp or not p:
        raise ErrorArreglo("No existe ese expediente o esa persona.")
    docs = a.documentos("expediente_id = ? AND persona_id = ? AND estado = 'guardado'", (expediente_id, persona_id))
    if docs:
        raise ErrorArreglo(f"{p['nombre']} {p['apellido1']} tiene {len(docs)} documento(s) en este expediente. "
                           "Muévelos antes a otra persona o a otro expediente («Mover…»).")
    personas = a.personas_de(expediente_id)
    if len(personas) == 1:
        raise ErrorArreglo("Es la única persona del expediente: no se puede quitar.")
    a.db.execute("DELETE FROM expediente_personas WHERE expediente_id = ? AND persona_id = ?", (expediente_id, persona_id))
    if not any(x["papel"] == "Titular" for x in a.personas_de(expediente_id)):      # siempre queda un titular
        primero = a.personas_de(expediente_id)[0]
        a.db.execute("UPDATE expediente_personas SET papel = 'Titular' WHERE expediente_id = ? AND persona_id = ?", (expediente_id, primero["id"]))
    borrada = False
    if not a.db.execute("SELECT 1 FROM expediente_personas WHERE persona_id = ?", (persona_id,)).fetchone() and \
       not a.db.execute("SELECT 1 FROM documentos WHERE persona_id = ?", (persona_id,)).fetchone():
        a.db.execute("DELETE FROM personas WHERE id = ?", (persona_id,))
        borrada = True
    a.db.commit()
    a.evento(f"Arreglo: {p['nombre']} {p['apellido1']} quitada del expediente «{exp['nombre']}»" + (" · su ficha se ha borrado (no estaba en ningún otro)" if borrada else ""))
    _refrescar(m, expediente_id)
    return {"ok": True, "ficha_borrada": borrada}


def personas_repetidas(m):
    """Parejas de fichas que parecen la misma persona (mismo DNI o mismo nombre y apellidos)."""
    from .extraer import norm
    gente = [dict(r) for r in m.almacen.db.execute("SELECT * FROM personas ORDER BY id")]
    out = []
    for i, p in enumerate(gente):
        for q in gente[i + 1:]:
            mismo_dni = p["dni"] and q["dni"] and p["dni"].upper() == q["dni"].upper()
            mismo_nombre = norm(p["nombre"]) == norm(q["nombre"]) and norm(p["apellido1"]) == norm(q["apellido1"]) and \
                (not p["apellido2"] or not q["apellido2"] or norm(p["apellido2"]) == norm(q["apellido2"]))
            if mismo_dni or mismo_nombre:
                out.append({"a": p, "b": q, "por": "mismo DNI" if mismo_dni else "mismo nombre",
                            "dni_distinto": bool(p["dni"] and q["dni"] and p["dni"].upper() != q["dni"].upper())})
    return out
