# -*- coding: utf-8 -*-
"""Contexto de lote (versión 3.0.2, en local, sin IA).

En vez de decidir documento a documento, se mira todo el lote junto, una vez leído y clasificado:
- Se juntan los nombres y DNI de todos los documentos en «identidades» (misma persona aunque el nombre
  venga incompleto, con un apellido de menos o una letra cambiada por el OCR).
- Un DNI solo se da por bueno si aparece en al menos 2 documentos del lote; entonces sirve para unir y
  para completar los demás (Joan, 16/11/2026).
- Titular: la identidad que aparece en la mayoría de los documentos con nombre (≥ 60 % por defecto).
  Si ya tiene expediente abierto, el lote va ahí; si no, se crea el expediente (y se avisa en la campanita).
- Cotitular: quien aparece junto al titular en un % importante (≥ 50 %) de los documentos COMPARTIDOS
  (renta, padrón, cuentas, préstamos, escrituras…), nunca en nóminas ni documentos individuales.
- Terceros: quien solo sale en escrituras, compraventas, notas simples… (notario, vendedores, banco).
- Documentos sin nombre: se buscan coincidencias con otros datos (cuenta, teléfono, correo, matrícula,
  referencia catastral) con documentos ya asignados.
- Atascos (opción A + C): se calcula cuando el lote no tiene nada en proceso; lo parado se deja fuera y,
  si termina después, se coloca con el contexto ya calculado sin cambiar lo hecho.
Todo lo que hace queda en el informe del lote (marcado «Local») y se puede deshacer."""
import datetime, difflib, json, re

from .extraer import norm, letra_dni, PARTICULAS

# Documentos que pueden ser de varias personas a la vez (para el cotitular)
COMPARTIDOS = {"renta", "padron", "extracto", "saldo", "prestamo", "escritura", "notasimple", "compraventa", "arras", "tasacion",
               "ibi", "planahorro", "fondos", "valores", "leasing", "renting", "solicitudaval", "aval", "estadocivil", "divorcio",
               "cuota", "presupuesto", "proyecto", "licencia", "autorizacionvt"}
# Documentos con muchos nombres donde casi todos son terceros
CON_TERCEROS = {"escritura", "compraventa", "notasimple", "arras", "tasacion", "constitucion", "divorcio", "aval", "solicitudaval"}
# Finalidad que se deduce por los tipos que trae el lote (si la variante no tiene checklist que encaje mejor)
PISTAS_FINALIDAD = {"licencia_taxi": {"licencia", "cap", "autorizacionvt", "fichatecnica", "carnet"},
                    "pyme": {"cif", "sociedades", "balance", "sumasysaldos", "iva", "ivaanual", "constitucion", "censo"},
                    "hipotecario": {"notasimple", "tasacion", "arras", "escritura"}}

EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")
TEL = re.compile(r"(?<![\d,.])(?:\+?34[ -]?)?([6789](?:[ -]?\d){8})(?![\d,])")


def _clave_dni(d):
    """Clave para comparar DNI/NIE: las 8 cifras (o la letra del NIE y 7 cifras), sin la letra final."""
    d = re.sub(r"[\s.-]", "", (d or "").upper())
    if len(d) == 10 and d[0] == "0":
        d = d[1:]
    m = re.match(r"^([XYZ]?\d{7,8})([A-Z])?$", d)
    return m.group(1)[-8:] if m and not m.group(1)[0].isalpha() else (m.group(1) if m else None)


def _con_letra(clave, vistos):
    """El DNI completo: la letra que se haya leído en algún documento, o la calculada."""
    for v in vistos:
        if v[-1:].isalpha() and _clave_dni(v) == clave:
            return v
    if clave and clave.isdigit() and len(clave) == 8:
        return clave + letra_dni(clave)
    return clave


def _tokens(p):
    nombre = [w for w in norm(p.get("nombre") or "").split() if w not in PARTICULAS]
    apes = [w for w in norm(f'{p.get("apellido1") or ""} {p.get("apellido2") or ""}').split() if w not in PARTICULAS]
    return nombre, apes


def compatibles(a, b):
    """¿Pueden ser la misma persona? Falta un apellido, nombre compuesto incompleto, una letra distinta…"""
    na, aa = _tokens(a)
    nb, ab = _tokens(b)
    ta, tb = set(na + aa), set(nb + ab)
    if not ta or not tb:
        return False
    if ta == tb:
        return True
    menor, mayor = (ta, tb) if len(ta) <= len(tb) else (tb, ta)
    if len(menor) >= 2 and menor <= mayor:          # le falta un apellido o un nombre
        return True
    if aa and ab and len(aa) >= 1 and len(ab) >= 1:
        ape_ok = aa[0] == ab[0] or difflib.SequenceMatcher(None, aa[0], ab[0]).ratio() >= .85
        nom_ok = (set(na) & set(nb)) or (na and nb and difflib.SequenceMatcher(None, " ".join(na), " ".join(nb)).ratio() >= .85)
        segundo = len(aa) < 2 or len(ab) < 2 or aa[1] == ab[1] or difflib.SequenceMatcher(None, aa[1], ab[1]).ratio() >= .85
        if ape_ok and nom_ok and segundo:
            return True
    return difflib.SequenceMatcher(None, " ".join(sorted(ta)), " ".join(sorted(tb))).ratio() >= .9


class _Uf:
    def __init__(self):
        self.p = {}

    def find(self, x):
        self.p.setdefault(x, x)
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[rb] = ra


class ContextoLote:
    def __init__(self, motor, ctrl):
        """ctrl: el ControladorIA (para apuntar las acciones en el mismo informe y poder deshacerlas)."""
        self.m, self.a, self.ctrl = motor, motor.almacen, ctrl
        self.db = self.a.db
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS lote_contexto(lote_id INTEGER PRIMARY KEY, estado TEXT, fecha TEXT, resumen TEXT);
        CREATE TABLE IF NOT EXISTS notificaciones(id INTEGER PRIMARY KEY, fecha TEXT, tipo TEXT, mensaje TEXT,
            expediente_id INTEGER, lote_id INTEGER, visto INTEGER DEFAULT 0);
        """)

    # ------------------------------------------------------------------ ajustes
    def ajustes(self):
        aj = self.m.gestion.ajustes()
        c = aj.get("contexto") or {}
        return {"activo": c.get("activo", True), "titular": float(c.get("titular", 60)), "cotitular": float(c.get("cotitular", 50)),
                "guardar": c.get("guardar", True), "minimo_docs": int(c.get("minimo_docs", 2))}

    # ------------------------------------------------------------------ ¿qué lotes están listos? (A + C)
    def pendientes(self):
        """Lotes sin nada en proceso que tienen documentos esperando y aún no se han mirado con el contexto
        (o que tienen documentos nuevos que llegaron después: los rezagados)."""
        out = []
        for r in self.db.execute("SELECT id FROM lotes ORDER BY id"):
            lid = r[0]
            docs = self.a.documentos("lote_id = ?", (lid,))
            if not docs or any(d["estado"] == "en_proceso" for d in docs):
                continue
            if any(d["estado"] == "espera_emparejar" and not (d["datos"] or {}).get("contexto") for d in docs):
                out.append(lid)
        return out

    # ------------------------------------------------------------------ análisis (no cambia nada)
    def _textos(self, d):
        t = [x["texto"] for x in self.a.textos_de(d["id"]).values()]
        if not t:
            for n in (d.get("paginas_sel") or range(1, (d["paginas"] or 1) + 1)):
                c = self.a.texto_cache(f'{d["huella"]}:{n}')
                if c:
                    t.append(c["texto"])
        return "\n".join(t)

    def analizar(self, lote_id):
        aj = self.ajustes()
        docs = [d for d in self.a.documentos("lote_id = ?", (lote_id,))
                if d["estado"] in ("espera_emparejar", "guardado", "limbo") and d["estado"] != "unido"]
        uf = _Uf()
        nodos = {}            # nodo -> persona leída (nombre…)
        en_doc = {}           # doc_id -> {nodo}
        dni_docs = {}         # clave DNI -> {doc_id}
        dni_vistos = {}       # clave -> [formas leídas]
        otros = {}            # doc_id -> {(clase, valor)}
        for d in docs:
            datos = d["datos"] or {}
            texto = norm(self._textos(d))
            en_doc[d["id"]] = set()
            for i, p in enumerate(datos.get("personas") or []):
                n = f"n{d['id']}_{i}"
                nodos[n] = p
                en_doc[d["id"]].add(n)
                k = _clave_dni(p.get("dni"))
                if k:
                    dni_docs.setdefault(k, set()).add(d["id"]); dni_vistos.setdefault(k, []).append(p["dni"])
                    uf.union(n, f"d{k}@{d['id']}")
            sueltos = []
            for v in (datos.get("dni") or []) + (datos.get("dni_letra_calculada") or []):
                k = _clave_dni(v)
                if k:
                    dni_docs.setdefault(k, set()).add(d["id"]); dni_vistos.setdefault(k, []).append(v)
                    sueltos.append(k)
            # un solo nombre y un solo DNI en el documento: van juntos
            ps = [n for n in en_doc[d["id"]]]
            if len(ps) == 1 and len(set(sueltos)) == 1:
                uf.union(ps[0], f"d{sueltos[0]}@{d['id']}")
            for k in set(sueltos):
                en_doc[d["id"]].add(f"d{k}@{d['id']}")
            o = set()
            for v in datos.get("iban") or []:
                o.add(("cuenta", v))
            for m in EMAIL.finditer(texto):
                o.add(("correo", m.group(0)))
            for m in TEL.finditer(texto):
                o.add(("teléfono", re.sub(r"\D", "", m.group(1))))
            if datos.get("matricula"):
                o.add(("matrícula", datos["matricula"]))
            if datos.get("ref_catastral"):
                o.add(("referencia catastral", datos["ref_catastral"]))
            otros[d["id"]] = o
        # DNI válido = aparece en al menos 2 documentos del lote: une las apariciones de todos los documentos
        fichados = {_clave_dni(r[0]) for r in self.db.execute("SELECT dni FROM personas WHERE dni IS NOT NULL")}
        validos = {k for k, s in dni_docs.items() if len(s) >= 2 or k in fichados}     # o el de una ficha que ya existe
        for k in validos:
            for did in dni_docs[k]:
                uf.union(f"D{k}", f"d{k}@{did}")
        # nombres compatibles (si no tienen DNI distintos y válidos)
        lista = list(nodos)
        for i, x in enumerate(lista):
            for y in lista[i + 1:]:
                if uf.find(x) == uf.find(y) or not compatibles(nodos[x], nodos[y]):
                    continue
                kx, ky = _clave_dni(nodos[x].get("dni")), _clave_dni(nodos[y].get("dni"))
                if kx and ky and kx != ky and kx in validos and ky in validos:
                    continue
                uf.union(x, y)
        # identidades
        ids = {}
        for did, ns in en_doc.items():
            for n in ns:
                r = uf.find(n)
                if n.startswith("d") and not any(uf.find(z) == r for z in nodos) and n[1:].split("@")[0] not in validos:
                    continue      # DNI de un solo documento y sin nombre: no sirve para unir
                ids.setdefault(r, {"nodos": set(), "docs": set()})
                ids[r]["nodos"].add(n)
                ids[r]["docs"].add(did)
        tipos = {d["id"]: d["tipo"] for d in docs}
        identidades = []
        for r, x in ids.items():
            nombres = [nodos[n] for n in x["nodos"] if n in nodos]
            claves = {n[1:].split("@")[0] for n in x["nodos"] if n.startswith("d")} & validos
            if not nombres and not claves:
                continue
            mejor = max(nombres, key=lambda p: (len((p.get("completo") or "").split()), sum(1 for q in nombres if norm(q.get("completo") or "") == norm(p.get("completo") or "")))) if nombres else None
            dni = None
            if claves:
                k = max(claves, key=lambda c: len(dni_docs[c]))
                dni = _con_letra(k, dni_vistos.get(k, []))
            variantes = sorted({norm(p.get("completo") or "").strip() for p in nombres if p.get("completo")})
            identidades.append({"clave": r, "persona": {k2: (mejor or {}).get(k2) for k2 in ("nombre", "apellido1", "apellido2", "completo")} if mejor else None,
                                "dni": dni, "variantes": variantes, "docs": sorted(x["docs"]),
                                "compartidos": sorted(did for did in x["docs"] if tipos.get(did) in COMPARTIDOS),
                                "individuales": sorted(did for did in x["docs"] if tipos.get(did) not in COMPARTIDOS)})
        identidades.sort(key=lambda i: (-len(i["docs"]), -len(i["individuales"])))
        for n, i in enumerate(identidades):
            i["n"] = n
        con_nombre = {did for i in identidades for did in i["docs"]}
        res = {"lote": lote_id, "identidades": identidades, "docs": {}, "titular": None, "cotitulares": [], "validos": sorted(validos)}
        if not identidades or not con_nombre:
            return res
        t = identidades[0]
        pct = 100 * len(t["docs"]) / len(con_nombre)
        res["cobertura"] = round(pct)
        if pct >= aj["titular"] and len(t["docs"]) >= aj["minimo_docs"]:
            res["titular"] = t["n"]
            # documentos compartidos «de verdad» del titular (renta, padrón, cuentas…); las escrituras y similares no cuentan
            comp_t = {x for x in t["compartidos"] if tipos.get(x) not in CON_TERCEROS} or set(t["compartidos"])
            candidatos = []
            for o in identidades[1:]:
                if not comp_t or not o.get("persona"):
                    continue
                juntos = len(comp_t & set(o["compartidos"]))
                if juntos and 100 * juntos / len(comp_t) >= aj["cotitular"]:
                    candidatos.append(o)
            # hijos: primer apellido de otro candidato y segundo apellido del titular (en la renta salen como descendientes)
            ape = lambda i: _tokens(i["persona"] or {})[1]
            ta = ape(t)
            for o in candidatos:
                oa = ape(o)
                hijo = len(oa) >= 2 and ta and oa[1] == ta[0] and any(ape(x) and ape(x)[0] == oa[0] for x in candidatos if x is not o)
                if not hijo:
                    res["cotitulares"].append(o["n"])
        grupo = ([res["titular"]] if res["titular"] is not None else []) + res["cotitulares"]
        # decisión por documento
        de_identidad = {}
        for i in identidades:
            for did in i["docs"]:
                de_identidad.setdefault(did, []).append(i["n"])
        asignados = {}
        for d in docs:
            ns = de_identidad.get(d["id"], [])
            del_grupo = [n for n in ns if n in grupo]
            terceros = [n for n in ns if n not in grupo and identidades[n].get("persona")]
            dec = {"terceros": terceros}
            if del_grupo:
                if d["tipo"] in COMPARTIDOS and len(del_grupo) >= 2:
                    dec.update(persona=None, comun=True, por="aparecen el titular y el cotitular")
                else:
                    # en un documento individual, la persona del grupo que más aparece en el lote
                    p = min(del_grupo, key=lambda n: grupo.index(n))
                    if d["tipo"] in CON_TERCEROS and d["tipo"] in COMPARTIDOS:
                        dec.update(persona=None, comun=True, por="documento de la operación")
                    else:
                        dec.update(persona=p, comun=False, por="nombre o DNI del documento")
                asignados[d["id"]] = dec
            res["docs"][d["id"]] = dec
        # documentos sin nadie del grupo: coincidencias por otros datos con documentos ya asignados
        valor_a_docs = {}
        for did, vs in otros.items():
            for v in vs:
                valor_a_docs.setdefault(v, set()).add(did)
        for d in docs:
            dec = res["docs"][d["id"]]
            if "persona" in dec or "comun" in dec:
                continue
            pistas = {}
            for v in otros.get(d["id"], ()):
                for od in valor_a_docs.get(v, ()):
                    if od != d["id"] and od in asignados:
                        o = asignados[od]
                        clave = ("comun", None) if o.get("comun") else ("persona", o.get("persona"))
                        pistas.setdefault(clave, []).append(v[0])
            if len(pistas) == 1:
                (cl, val), por = next(iter(pistas.items()))
                dec.update({"comun": True, "persona": None} if cl == "comun" else {"comun": False, "persona": val},
                           por="mismo " + " y ".join(sorted(set(por))) + " que otro documento del lote")
        return res

    # ------------------------------------------------------------------ elegir finalidad para un expediente nuevo
    def _finalidad(self, tipos):
        vis = [f for f in self.m.finalidades() if not f.get("oculta")]
        if not vis:
            return None
        docs = self.m.variante.docs
        def puntos(f):
            lista = {x["tipo"] for x in f.get("documentos") or []}
            # los tipos que solo sirven para una finalidad (licencia, CAP, compraventa de licencia…) pesan mucho
            propios = sum(1 for t in tipos if t in docs and (docs[t].get("finalidades") or []) == [f["id"]])
            return (propios * 10 + len(PISTAS_FINALIDAD.get(f["id"], set()) & tipos) * 5 + len(lista & tipos), -vis.index(f))
        return max(vis, key=puntos)["id"]

    # ------------------------------------------------------------------ persona: buscar la ficha o crearla
    def _persona(self, ident, crear):
        a = self.a
        if ident.get("dni"):
            for r in a.db.execute("SELECT * FROM personas WHERE dni IS NOT NULL"):
                if _clave_dni(r["dni"]) == _clave_dni(ident["dni"]):
                    return dict(r), False
        p = ident.get("persona")
        if p:
            for r in a.db.execute("SELECT * FROM personas"):
                r = dict(r)
                alias = json.loads(r.get("alias") or "[]")
                if compatibles(r, p) and not (ident.get("dni") and r["dni"] and _clave_dni(r["dni"]) != _clave_dni(ident["dni"])):
                    return r, False
                if any(v in alias for v in ident["variantes"]):
                    return r, False
        if not crear or not p or not p.get("nombre") or not p.get("apellido1"):
            return None, False
        pid = self.m.nueva_persona(p["nombre"], p.get("apellido1") or "", p.get("apellido2") or "", ident.get("dni"))
        return a.persona(pid), True

    def _apuntar_alias(self, persona, ident):
        al = json.loads(persona.get("alias") or "[]")
        propio = norm(f'{persona["nombre"]} {persona["apellido1"]} {persona["apellido2"] or ""}').strip()
        nuevos = [v for v in ident["variantes"] if v and v != propio and v not in al]
        if nuevos:
            al += nuevos
            self.db.execute("UPDATE personas SET alias = ? WHERE id = ?", (json.dumps(al, ensure_ascii=False), persona["id"]))
            self.db.commit()
        if ident.get("dni") and not persona.get("dni"):
            self.db.execute("UPDATE personas SET dni = ? WHERE id = ?", (ident["dni"], persona["id"]))
            self.db.commit()

    def notificar(self, tipo, mensaje, expediente_id=None, lote_id=None):
        self.db.execute("INSERT INTO notificaciones(fecha, tipo, mensaje, expediente_id, lote_id) VALUES(?, ?, ?, ?, ?)",
                        (datetime.datetime.now().isoformat(timespec="seconds"), tipo, mensaje, expediente_id, lote_id))
        self.db.commit()

    def notificaciones(self, todas=False):
        q = "SELECT n.*, e.nombre AS expediente FROM notificaciones n LEFT JOIN expedientes e ON e.id = n.expediente_id" + ("" if todas else " WHERE n.visto = 0") + " ORDER BY n.id DESC LIMIT 100"
        return [dict(r) for r in self.db.execute(q)]

    def visto(self, nid=None):
        if nid:
            self.db.execute("UPDATE notificaciones SET visto = 1 WHERE id = ?", (nid,))
        else:
            self.db.execute("UPDATE notificaciones SET visto = 1")
        self.db.commit()

    # ------------------------------------------------------------------ aplicar
    def aplicar(self, lote_id):
        """Calcula el contexto del lote y hace lo que está claro. Devuelve un resumen."""
        aj = self.ajustes()
        a, m, ctrl = self.a, self.m, self.ctrl
        ctx = self.analizar(lote_id)
        hechos = {"asignados": 0, "propuestos": 0, "expediente": None, "creado": False, "terceros": 0}
        pend = [d for d in a.documentos("lote_id = ? AND estado = 'espera_emparejar'", (lote_id,)) if not (d["datos"] or {}).get("contexto")]
        if not pend:
            return hechos
        ids = ctx["identidades"]
        eid, personas = None, {}
        if ctx["titular"] is not None:
            tit = ids[ctx["titular"]]
            p, nueva = self._persona(tit, crear=True)
            if p:
                personas[tit["n"]] = p["id"]
                if not nueva:
                    self._apuntar_alias(p, tit)
                abiertos = [r[0] for r in a.db.execute("SELECT e.id FROM expedientes e JOIN expediente_personas ep ON ep.expediente_id = e.id "
                                                      "WHERE ep.persona_id = ? AND e.estado = 'abierto' ORDER BY e.id DESC", (p["id"],))]
                if len(abiertos) == 1:
                    eid = abiertos[0]
                elif not abiertos:
                    tipos = {d["tipo"] for d in a.documentos("lote_id = ?", (lote_id,)) if d["tipo"]}
                    fin = self._finalidad(tipos)
                    if fin:
                        eid = m.crear_expediente(p["id"], fin)
                        e = a.expediente(eid)
                        hechos["creado"] = True
                        quien = f'{p["nombre"]} {p["apellido1"]} {p["apellido2"] or ""}'.strip()
                        ctrl._accion(lote_id, None, None, "expediente_creado", "Expediente creado",
                                     f"{e['nombre']} · {m.variante.meta['finalidades'][fin]}",
                                     f"{quien} aparece en {len(tit['docs'])} de los documentos del lote ({ctx.get('cobertura')} %)", 100, "hecha",
                                     {"expediente_id": eid, "persona_creada": p["id"] if nueva else None}, origen="local")
                        self.notificar("expediente", f"Expediente creado solo por el contexto del lote {lote_id}: {e['nombre']} "
                                       f"({m.variante.meta['finalidades'][fin]}). Revísalo.", eid, lote_id)
                        a.evento(f"Contexto del lote: expediente nuevo «{e['nombre']}» para {quien}", lote_id=lote_id, nivel="info")
                # (si tiene varios expedientes abiertos, no se elige: se propone en la revisión)
            for n in ctx["cotitulares"]:
                q, qnueva = self._persona(ids[n], crear=True)
                if not q:
                    continue
                personas[n] = q["id"]
                if not qnueva:
                    self._apuntar_alias(q, ids[n])
                if eid and q["id"] not in [x["id"] for x in a.personas_de(eid)]:
                    a.anadir_persona(eid, q["id"], "Cotitular")
                    ctrl._accion(lote_id, None, None, "cotitular", "Cotitular", f'{q["nombre"]} {q["apellido1"]} {q["apellido2"] or ""}'.strip(),
                                 f"Aparece con el titular en {len(set(ids[n]['compartidos']) & set(ids[ctx['titular']]['compartidos']))} documento(s) compartido(s)",
                                 100, "hecha", {"expediente_id": eid, "persona_id": q["id"], "persona_creada": q["id"] if qnueva else None}, origen="local")
        if eid:
            hechos["expediente"] = eid
        elif ctx["titular"] is not None and not personas:
            # el lote es de alguien que todavía no se puede fichar (p. ej. solo hay DNI, sin nombre): se espera a otro lote
            self.db.execute("INSERT OR REPLACE INTO lote_contexto(lote_id, estado, fecha, resumen) VALUES(?, 'esperando', ?, ?)",
                            (lote_id, datetime.datetime.now().isoformat(timespec="seconds"), json.dumps({"motivo": "titular sin nombre todavía"})))
            self.db.commit()
            return hechos
        for d in pend:
            dec = ctx["docs"].get(d["id"]) or {}
            datos = d["datos"] or {}
            # terceros (no se fichan)
            for n in dec.get("terceros") or []:
                p = ids[n].get("persona") or {}
                nm = norm(p.get("completo") or "").strip()
                if nm and d["tipo"] in CON_TERCEROS:
                    a.db.execute("INSERT OR IGNORE INTO terceros_lote VALUES(?, ?)", (lote_id, nm)); a.db.commit()
                    hechos["terceros"] += 1
            pid = personas.get(dec.get("persona")) if dec.get("persona") is not None else None
            comun = bool(dec.get("comun"))
            claro = eid and (comun or pid) and d["tipo"] and not d["motivo"] and (d["confianza"] or 0) >= 0.75
            if claro and aj["guardar"]:
                prev = m.gestion.nombre_previsto(d["id"], eid, None if comun else pid, d["tipo"], None, False, comun)
                if prev.get("existe"):
                    claro = False
            if claro and aj["guardar"]:
                try:
                    g = m.emparejar(d["id"], eid, None if comun else pid, de_expediente=comun)
                except Exception as e:      # no se puede: queda para Joan
                    datos = a.documento(d["id"])["datos"] or {}
                    datos.update(contexto=True, ia_propuesta={"texto": f"Contexto del lote: no se ha podido guardar ({e})", "seguridad": 0})
                    a.actualizar(d["id"], datos=datos)
                    continue
                quien = "todo el expediente" if comun else f'{a.persona(pid)["nombre"]} {a.persona(pid)["apellido1"]}'
                ctrl._accion(lote_id, d["id"], None, "asignado", "Asignado (contexto del lote)",
                             f"{m.variante.docs[d['tipo']]['nombres']['es'][0]} · {a.expediente(eid)['nombre']} · {quien} · {g['nombre_final']}",
                             f"Por {dec.get('por')}", 95, "hecha", {"datos": datos}, origen="local")
                hechos["asignados"] += 1
                continue
            # no está claro: se deja la propuesta para la revisión
            if eid and (comun or pid):
                quien = "todo el expediente" if comun else f'{a.persona(pid)["nombre"]} {a.persona(pid)["apellido1"]}'
                datos["ia_propuesta"] = {"texto": f"Contexto del lote: es de {quien} ({a.expediente(eid)['nombre']}), por {dec.get('por')}.",
                                         "seguridad": 80, "expediente_id": eid, "persona_id": pid, "tipo": d["tipo"], "comun": comun, "origen": "local"}
                hechos["propuestos"] += 1
            datos["contexto"] = True
            a.actualizar(d["id"], datos=datos)
        self.db.execute("INSERT OR REPLACE INTO lote_contexto(lote_id, estado, fecha, resumen) VALUES(?, 'hecho', ?, ?)",
                        (lote_id, datetime.datetime.now().isoformat(timespec="seconds"), json.dumps({**hechos, "identidades": len(ids), "cobertura": ctx.get("cobertura")})))
        self.db.commit()
        if hechos["asignados"] or hechos["propuestos"] or hechos["creado"]:
            a.evento(f"Contexto del lote {lote_id}: {hechos['asignados']} guardado(s), {hechos['propuestos']} propuesto(s)"
                     + (", expediente nuevo" if hechos["creado"] else ""), lote_id=lote_id, nivel="info")
        return hechos
