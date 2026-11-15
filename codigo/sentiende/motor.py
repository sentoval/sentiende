# -*- coding: utf-8 -*-
"""Orquestador del motor: las 10 fases (M-01 a M-13, M-61, M-62).

    recibir()  -> fase 1
    procesar() -> fases 2 a 6, solas; se para en la 7 esperando respuesta
    emparejar() / al_limbo() -> fases 7 a 10
Cada fase deja su resultado en el almacén: si el programa se cierra, se reanuda
desde la última fase terminada sin repetir nada (M-61). Si algo falla, el documento
queda «parado» en esa fase con el motivo, y el original no se toca."""
import datetime, io, json, re, shutil, unicodedata
from pathlib import Path

from . import VERSION, FASES
from .almacen import Almacen
from .carpetas import Carpetas, libre
from .variante import Variante, VarianteError
from .recibir import huella, tipo_archivo, mover_a_entrada
from .lectura import leer
from .separar import separar
from .extraer import extraer, aprender_personas
from .clasificar import Clasificador
from .nombres import Nombrador, carpeta_expediente
from . import checklist, textos
from .negociacion import Negociacion, parece_tarjeta

class MotorError(Exception):
    pass

NOMBRE_FASE = dict(FASES)

class Motor:
    def __init__(self, raiz, carpeta_variante=None, variante_id="sefinancia"):
        self.carpetas = Carpetas(raiz)
        self.carpetas.crear()
        try:
            self.variante = Variante(carpeta_variante or self.carpetas.variantes / variante_id)
        except VarianteError as e:
            raise MotorError(str(e))
        if not self.variante.compat.compatible:
            raise MotorError(self.variante.compat.mensaje)
        self.almacen = Almacen(self.carpetas.datos / "sentiende.db")
        self.clasificador = Clasificador(self.variante)
        self.nombrador = Nombrador(self.variante)
        self._cargar_finalidades()
        self.negociacion = Negociacion(self.almacen)
        from .gestion import Gestion
        self.gestion = Gestion(self)
        self.gestion.aplicar()
        aprender_personas([dict(r) for r in self.almacen.db.execute("SELECT * FROM personas")])   # nombres ya confirmados

    # ------------------------------------------------------------ finalidades (editables por el usuario)
    def _ruta_finalidades(self):
        return self.carpetas.datos / "finalidades.json"

    def _cargar_finalidades(self):
        """Las finalidades y sus checklists son del usuario (Datos\\finalidades.json): las actualizaciones de
        la variante no las pisan. Las finalidades nuevas que traiga la variante se añaden si no se quitaron."""
        v = self.variante
        base_f = dict(v.meta.get("finalidades", {}))
        base_c = {k: x for k, x in v.checklists.items() if not k.startswith("_")}
        datos = {}
        if self._ruta_finalidades().exists():
            try:
                datos = json.loads(self._ruta_finalidades().read_text(encoding="utf-8"))
            except (OSError, ValueError):
                datos = {}
        fin = datos.get("finalidades") or {}
        chk = datos.get("checklists") or {}
        quitadas = set(datos.get("quitadas", []))
        for k, n in base_f.items():
            if k not in fin and k not in quitadas:
                fin[k] = n
                chk.setdefault(k, base_c.get(k, []))
        self._fin = {"finalidades": fin, "checklists": chk, "quitadas": sorted(quitadas), "ocultas": [o for o in datos.get("ocultas", []) if o in fin]}
        v.meta["finalidades"] = fin
        v.checklists = chk

    def _guardar_finalidades(self):
        self._ruta_finalidades().write_text(json.dumps(self._fin, ensure_ascii=False, indent=1), encoding="utf-8")
        self.variante.meta["finalidades"] = self._fin["finalidades"]
        self.variante.checklists = self._fin["checklists"]

    def finalidades(self):
        uso = dict(self.almacen.db.execute("SELECT finalidad, COUNT(*) FROM expedientes GROUP BY finalidad").fetchall())
        return [{"id": k, "nombre": n, "documentos": self._fin["checklists"].get(k, []), "expedientes": uso.get(k, 0),
                 "oculta": k in self._fin["ocultas"]} for k, n in self._fin["finalidades"].items()]

    def finalidades_visibles(self):
        """Las que se ofrecen al crear un expediente (las ocultas solo las conservan los expedientes que ya las tienen)."""
        return [k for k in self._fin["finalidades"] if k not in self._fin["ocultas"]]

    def ocultar_finalidad(self, fid, oculta=True):
        if fid not in self._fin["finalidades"]:
            raise MotorError(f"No existe la finalidad {fid}.")
        s = set(self._fin["ocultas"])
        s.add(fid) if oculta else s.discard(fid)
        self._fin["ocultas"] = sorted(s)
        self._guardar_finalidades()

    def guardar_finalidad(self, nombre, documentos=None, fid=None):
        """Crea (sin fid; checklist vacía) o cambia una finalidad. documentos: [{tipo, por, importancia, condicion}]."""
        nombre = (nombre or "").strip()
        if not nombre:
            raise MotorError("La finalidad necesita un nombre.")
        fin = self._fin["finalidades"]
        if fid is None:
            base = re.sub(r"[^a-z0-9]+", "_", unicodedata.normalize("NFD", nombre.lower()).encode("ascii", "ignore").decode()).strip("_") or "finalidad"
            fid, n = base, 2
            while fid in fin:
                fid, n = f"{base}_{n}", n + 1
            documentos = documentos or []
        elif fid not in fin:
            raise MotorError(f"No existe la finalidad {fid}.")
        if any(x.lower() == nombre.lower() for k, x in fin.items() if k != fid):
            raise MotorError(f"Ya hay una finalidad que se llama «{nombre}».")
        fin[fid] = nombre
        if documentos is not None:
            tipos = self.variante.docs
            limpio = []
            for dct in documentos:
                if dct.get("tipo") not in tipos:
                    raise MotorError(f"Tipo de documento desconocido: {dct.get('tipo')}")
                c = dct.get("condicion") or {}
                cond = {}
                if c.get("en_vigor"):
                    cond["en_vigor"] = True
                elif c.get("ultimos_meses"):
                    cond["ultimos_meses"] = max(1, min(60, int(c["ultimos_meses"])))
                elif c.get("ultimo_ejercicio"):
                    cond["ultimo_ejercicio"] = True
                elif c.get("max_dias"):
                    cond["max_dias"] = max(1, min(3650, int(c["max_dias"])))
                limpio.append({"tipo": dct["tipo"], "por": "expediente" if dct.get("por") == "expediente" else "titular",
                               "importancia": "imprescindible" if dct.get("importancia") == "imprescindible" else "recomendable",
                               "condicion": cond})
            self._fin["checklists"][fid] = limpio
        self._fin["quitadas"] = [q for q in self._fin["quitadas"] if q != fid]
        self._guardar_finalidades()
        return fid

    def quitar_finalidad(self, fid):
        n = self.almacen.db.execute("SELECT COUNT(*) FROM expedientes WHERE finalidad = ?", (fid,)).fetchone()[0]
        if n:
            raise MotorError(f"No se puede quitar: la usan {n} expediente(s). Se puede ocultar.")
        self._fin["finalidades"].pop(fid, None)
        self._fin["checklists"].pop(fid, None)
        self._fin["quitadas"] = sorted(set(self._fin["quitadas"]) | {fid})
        self._guardar_finalidades()

    # ------------------------------------------------------------ fase 1
    def recibir(self, rutas, origen="arrastrados", lote=None):
        """Mueve a Entrada\\, calcula la huella y detecta duplicados. Devuelve (lote_id, [doc_id]).
        lote: para añadir a un lote ya abierto (varios archivos soltados a la vez)."""
        a = self.almacen
        lote = lote or a.nuevo_lote(origen)
        ids = []
        for r in rutas:
            r = Path(r)
            clase = tipo_archivo(r) if r.exists() else None
            if not clase:
                a.evento(f"No se admite «{r.name}»: no es un PDF, imagen, Word o Excel válido. No se ha tocado.", lote_id=lote, fase=1, nivel="se")
                continue
            try:
                en_entrada = mover_a_entrada(r, self.carpetas.entrada)
            except OSError as e:
                a.evento(f"No se ha podido mover «{r.name}» a Entrada: {e}", lote_id=lote, fase=1, nivel="se")
                continue
            h = huella(en_entrada)
            previo = a.ya_procesado(h)
            doc = a.nuevo_documento(lote, r.name, en_entrada, h, en_entrada.suffix.lower())
            if previo:
                a.actualizar(doc, fase=1, estado="duplicado", duplicado_de=previo,
                             motivo=f"Idéntico al documento {previo}: no se vuelve a leer")
                a.evento(f"«{r.name}» es idéntico a uno ya recibido: no se procesa.", doc, lote, 1, "cliente")
            else:
                a.actualizar(doc, fase=1)
                a.evento(f"Recibido «{r.name}» ({clase}) en Entrada.", doc, lote, 1)
            ids.append(doc)
        return lote, ids

    # ------------------------------------------------------------ fases 2 a 6
    def procesar(self, lote_id=None):
        """Avanza todo lo pendiente hasta la fase 6. Devuelve los documentos tratados."""
        where = "estado = 'en_proceso' AND fase < 6" + (" AND lote_id = ?" if lote_id else "")
        # (las partes de un PDF separado se procesan al separarlo)
        docs = self.almacen.documentos(where, (lote_id,) if lote_id else ())
        for d in docs:
            self._procesar_doc(d)
        return [self.almacen.documento(d["id"]) for d in docs]

    def _procesar_doc(self, d):
        a, did, lote = self.almacen, d["id"], d["lote_id"]
        fase = d["fase"]
        try:
            ruta = Path(d["ruta_original"])
            clase = tipo_archivo(ruta)
            trabajo = self.carpetas.trabajo(lote)
            if fase < 4:      # fases 2, 3 y 4: leer, separar y orientar
                lec = leer(ruta, clase, d["huella"], a, trabajo)
                for av in lec.avisos:
                    a.evento(av, did, lote, 2, "se")
                a.actualizar(did, fase=4, paginas=len(lec.paginas), confianza=round(lec.confianza, 3),
                             rotaciones=[{"n": p.n, "rotacion": p.rotacion, "inclinacion": p.inclinacion, "origen": p.origen,
                                          "confianza": p.confianza, "imagen": p.imagen} for p in lec.paginas],
                             ruta_trabajo=str(trabajo))
                a.evento(f"Leído: {len(lec.paginas)} página(s) · " + ", ".join(sorted({p.origen for p in lec.paginas})), did, lote, 2)
                giros = [p for p in lec.paginas if p.rotacion or p.inclinacion]
                if giros:
                    a.evento("Orientado: " + ", ".join(f"pág. {p.n} {p.rotacion}°" + (f" y enderezada {p.inclinacion}°" if p.inclinacion else "") for p in giros), did, lote, 4)
                if len(lec.paginas) > 1 and self._separar(a.documento(did), lec):
                    return
                texto = self._texto(a.documento(did))
            else:
                texto = self._texto(d)
            d = a.documento(did)
            if d["fase"] < 5:
                datos = extraer(texto)
                a.actualizar(did, fase=5, datos=datos)
                a.evento(f"Datos: {len(datos['dni'])} DNI/NIE, {len(datos['iban'])} IBAN, {len(datos['fechas'])} fechas", did, lote, 5)
            c = self.clasificador.clasificar(texto)
            datos = a.documento(did)["datos"] or {}
            tarjeta = parece_tarjeta(texto, c.entidad, len(datos.get("dni") or []), self.clasificador.bancos)
            if tarjeta and not datos.get("tarjeta"):
                datos["tarjeta"] = tarjeta
                a.actualizar(did, datos=datos)
                a.evento("Parece una tarjeta de visita o datos de contacto de un banco: se preguntará en el Centro de revisión.", did, lote, 6, "revision")
            a.actualizar(did, fase=6, tipo=c.tipo, confianza=c.confianza,
                         alternativas=c.alternativas, indicios=c.indicios, entidad=c.entidad, entidad_por=c.entidad_por,
                         estado="espera_emparejar",
                         motivo={"ok": "", "revisar": f"Tipo dudoso ({round(c.confianza * 100)} %): revisar",
                                 "no_reconocido": "No reconocido: revisar"}[c.estado])
            a.evento(f"Clasificado (provisional): {c.tipo or 'no reconocido'} · {round(c.confianza * 100)} %" + (f" · entidad {c.entidad} por {c.entidad_por}" if c.entidad else ""), did, lote, 6,
                     "info" if c.estado == "ok" else "revision")
        except Exception as e:  # el documento se para en su fase; nada se pierde
            f = a.documento(did)["fase"] + 1
            a.actualizar(did, estado="parado", motivo=f"Fase {f} · {NOMBRE_FASE.get(f, '')}: {e}")
            a.evento(f"Parado en la fase {f}: {e}. El original sigue en Entrada.", did, lote, f, "se")

    def _separar(self, d, lec):
        """Fase 3. Si el PDF trae varios documentos (o páginas en blanco), crea un documento por parte.
        Devuelve True si el archivo se ha separado (las partes siguen el proceso por su cuenta)."""
        a, did, lote = self.almacen, d["id"], d["lote_id"]
        sep = separar([p.texto for p in lec.paginas], self.clasificador)
        por_n = {p.n: p for p in lec.paginas}
        if sep.en_blanco:
            a.evento(f"Páginas en blanco apartadas (no se borran del original): {', '.join(map(str, sep.en_blanco))}", did, lote, 3, "revision")
        if len(sep.partes) <= 1:
            if sep.partes and (sep.en_blanco or sep.reordenado):
                sel = sep.partes[0].paginas
                a.actualizar(did, paginas_sel=sel, paginas=len(sel), rotaciones=[r for n in sel for r in d["rotaciones"] if r["n"] == n])
                a.evento(f"Separar: un documento · páginas {', '.join(map(str, sel))}", did, lote, 3)
            else:
                a.evento("Separar: un solo documento", did, lote, 3)
            return False
        desc = []
        for i, parte in enumerate(sep.partes, 1):
            rango = f"pág. {parte.paginas[0]}" if len(parte.paginas) == 1 else "págs. " + ", ".join(map(str, parte.paginas))
            hijo = a.nuevo_documento(lote, f"{d['nombre_recibido']} ({rango})", d["ruta_original"], d["huella"], d["extension"], padre_id=did)
            a.actualizar(hijo, fase=4, paginas=len(parte.paginas), paginas_sel=parte.paginas, ruta_trabajo=d["ruta_trabajo"],
                         rotaciones=[r for n in parte.paginas for r in d["rotaciones"] if r["n"] == n],
                         confianza=min(por_n[n].confianza for n in parte.paginas))
            desc.append(f"{rango} ({parte.tipo or '¿?'})")
            self._procesar_doc(a.documento(hijo))
        a.actualizar(did, fase=3, estado="separado", motivo=f"Separado en {len(sep.partes)} documentos")
        a.evento(f"Separado en {len(sep.partes)} documentos: " + " · ".join(desc) + (" · páginas reordenadas por su numeración" if sep.reordenado else ""), did, lote, 3,
                 "revision" if sep.reordenado else "info")
        return True

    def _texto(self, d):
        sel = d.get("paginas_sel") or range(1, (d["paginas"] or 1) + 1)
        claves = [self.almacen.texto_cache(f'{d["huella"]}:{n}') for n in sel]
        return "\n\f\n".join(c["texto"] for c in claves if c)

    # ------------------------------------------------------------ fase 7: sugerencias y expedientes
    def sugerencias(self, doc_id):
        """Personas y expedientes conocidos que coinciden (M-26): primero por DNI/NIE y,
        si no hay DNI, por nombre y apellidos en cualquier orden (sin tildes ni mayúsculas)."""
        from .extraer import norm
        a = self.almacen
        d = a.documento(doc_id)
        datos = d["datos"] or {}
        out, vistos = [], set()
        def exps(pid):
            return [dict(x) for x in a.db.execute("SELECT e.*, ep.papel FROM expediente_personas ep JOIN expedientes e ON e.id = ep.expediente_id "
                                                   "WHERE ep.persona_id = ? AND e.estado = 'abierto'", (pid,))]
        for dni in datos.get("dni", []):
            p = a.persona_por_dni(dni)
            if p and p["id"] not in vistos:
                vistos.add(p["id"]); out.append({"persona": p, "expedientes": exps(p["id"]), "por": f"DNI {dni}"})
        conocidas = [dict(r) for r in a.db.execute("SELECT * FROM personas")]
        for leida in datos.get("personas", []):
            clave = set(norm(leida["completo"]).split())
            for p in conocidas:
                if p["id"] in vistos:
                    continue
                if set(norm(f'{p["nombre"]} {p["apellido1"]} {p["apellido2"]}').split()) == clave:
                    vistos.add(p["id"])
                    out.append({"persona": p, "expedientes": exps(p["id"]), "por": f"nombre «{leida['completo']}» (sin DNI: confirmar)"})
        return out

    def terceros_lote(self, lote_id):
        return [r[0] for r in self.almacen.db.execute("SELECT nombre FROM terceros_lote WHERE lote_id = ?", (lote_id,))]

    def personas_leidas(self, doc_id):
        """Personas que el documento nombra (para crear la persona sin teclear)."""
        return (self.almacen.documento(doc_id)["datos"] or {}).get("personas", [])

    def persona_desde_documento(self, doc_id, indice=0):
        leidas = self.personas_leidas(doc_id)
        if not leidas:
            raise MotorError("El documento no tiene ningún nombre reconocido: hay que escribirlo.")
        p = leidas[indice]
        return self.nueva_persona(p["nombre"], p["apellido1"], p["apellido2"], p.get("dni"))

    def nueva_persona(self, nombre, apellido1="", apellido2="", dni=None, es_empresa=False):
        p = self.almacen.persona_por_dni(dni) if dni else None
        if p:
            return p["id"]
        aprender_personas([{"nombre": nombre, "apellido1": apellido1, "apellido2": apellido2}])
        return self.almacen.nueva_persona(nombre, apellido1, apellido2, dni, es_empresa)

    def posibles_duplicados(self, nombre, apellido1, apellido2="", dni=None):
        """Personas ya fichadas que pueden ser la misma: mismo DNI, o mismo nombre y primer apellido."""
        from .extraer import norm
        a = self.almacen
        out = []
        for r in a.db.execute("SELECT * FROM personas"):
            p = dict(r)
            mismo_dni = bool(dni and p["dni"] and p["dni"].upper() == dni.upper())
            mismo_nombre = norm(p["nombre"]) == norm(nombre) and norm(p["apellido1"]) == norm(apellido1) and \
                (not apellido2 or not p["apellido2"] or norm(p["apellido2"]) == norm(apellido2))
            if mismo_dni or mismo_nombre:
                p["por"] = "mismo DNI" if mismo_dni else "mismo nombre"
                p["expedientes"] = [dict(x) for x in a.db.execute("SELECT e.id, e.nombre, e.carpeta, e.estado, ep.papel FROM expediente_personas ep "
                                                                   "JOIN expedientes e ON e.id = ep.expediente_id WHERE ep.persona_id = ?", (p["id"],))]
                out.append(p)
        return out

    def crear_expediente(self, persona_id, finalidad, fecha=None, nombre=None):
        if finalidad not in self.variante.meta.get("finalidades", {}):
            raise MotorError(f"Finalidad desconocida en {self.variante.nombre}: {finalidad}")
        if finalidad in self._fin["ocultas"]:
            raise MotorError("Esa finalidad está oculta: muéstrala en Ajustes para usarla en expedientes nuevos.")
        p = self.almacen.persona(persona_id)
        fecha = fecha or datetime.date.today()
        carpeta = carpeta_expediente(p, fecha, self.variante.nombres["sin_dni"])
        (self.carpetas.documentos / carpeta).mkdir(parents=True, exist_ok=True)
        (self.carpetas.originales / carpeta).mkdir(parents=True, exist_ok=True)
        nombre = nombre or f'{p["apellido1"]} {p["apellido2"]}'.strip() + " · " + self.variante.meta["finalidades"][finalidad]
        eid = self.almacen.nuevo_expediente(nombre, finalidad, carpeta)
        self.almacen.anadir_persona(eid, persona_id, "Titular")
        return eid

    def vincular_personas(self, expediente_id, otros, doc_id=None):
        """Las demás personas de un documento (p. ej. el segundo declarante de la renta):
        'cotitular' → se añade a este expediente como Cotitular; 'separado' → se ficha con su propio
        expediente (misma finalidad); 'tercero' → no se ficha."""
        a = self.almacen
        exp = a.expediente(expediente_id)
        hechos = []
        for o in otros or []:
            pe, accion = o.get("persona") or {}, o.get("accion")
            nombre = f'{pe.get("nombre", "")} {pe.get("apellido1", "")}'.strip()
            if accion == "misma" and o.get("persona_id"):        # es una persona que ya está, escrita de otra forma
                p0 = a.persona(int(o["persona_id"]))
                if p0:
                    from .extraer import norm
                    completo = " ".join(x for x in (pe.get("nombre"), pe.get("apellido1"), pe.get("apellido2")) if x)
                    alias = json.loads(p0.get("alias") or "[]")
                    if norm(completo).strip() not in alias:
                        alias.append(norm(completo).strip())
                        a.db.execute("UPDATE personas SET alias = ? WHERE id = ?", (json.dumps(alias, ensure_ascii=False), p0["id"]))
                        a.db.commit()
                    hechos.append(f"{nombre}: es {p0['nombre']} {p0['apellido1']} {p0['apellido2'] or ''} (nombre apuntado como alias)")
                continue
            if accion == "tercero" or not accion:
                if doc_id and (d0 := a.documento(doc_id)):        # se recuerda en el lote: en los siguientes documentos ya viene como tercero
                    from .extraer import norm
                    completo = " ".join(x for x in (pe.get("nombre"), pe.get("apellido1"), pe.get("apellido2")) if x)
                    a.db.execute("INSERT OR IGNORE INTO terceros_lote VALUES(?, ?)", (d0["lote_id"], norm(completo)))
                    a.db.commit()
                hechos.append(f"{nombre}: tercero, no se ficha"); continue
            if not pe.get("nombre") or not pe.get("apellido1"):
                raise MotorError(f"Faltan el nombre o el primer apellido de {nombre or 'la otra persona'}.")
            pid = self.nueva_persona(pe["nombre"], pe.get("apellido1", ""), pe.get("apellido2", ""), (pe.get("dni") or None))
            if accion == "cotitular" and pid in [p["id"] for p in a.personas_de(expediente_id)]:
                hechos.append(f"{nombre}: ya estaba en este expediente"); continue
            if accion == "cotitular":
                a.anadir_persona(expediente_id, pid, "Cotitular")
                hechos.append(f"{nombre}: cotitular de este expediente")
            elif accion == "separado":
                eid = self.crear_expediente(pid, exp["finalidad"])
                hechos.append(f"{nombre}: expediente propio {a.expediente(eid)['carpeta']}")
        if hechos and doc_id:
            d = a.documento(doc_id)
            a.evento("Otras personas del documento · " + " · ".join(hechos), doc_id, d["lote_id"] if d else None, 7)
        return hechos

    # ------------------------------------------------------------ unir fotos de un mismo documento
    def propuestas_union(self):
        """Fotos o escaneos de una página que llegaron juntos (mismo lote), esperan revisión y parecen
        el mismo tipo de documento: se propone unirlos en un PDF. Siempre se pregunta."""
        docs = [d for d in self.almacen.documentos("estado = 'espera_emparejar' AND unido_en IS NULL AND padre_id IS NULL")
                if d["extension"] in (".jpg", ".jpeg", ".png", ".tif", ".tiff", ".heic", ".webp", ".bmp") or (d["extension"] == ".pdf" and (d["paginas"] or 1) == 1 and any(r.get("origen") == "ocr" for r in d["rotaciones"] or []))]
        grupos = {}
        for d in docs:
            grupos.setdefault((d["lote_id"], d["tipo"]), []).append(d["id"])
        return [{"lote": k[0], "tipo": k[1], "documentos": v} for k, v in grupos.items() if len(v) > 1 and k[1]]

    def unir(self, ids):
        """Une varios documentos (en el orden dado) en un PDF nuevo que sigue el proceso desde la fase 2.
        Las fotos originales no se tocan hasta guardar; entonces van a Doc_original."""
        from PIL import Image, ImageOps
        a = self.almacen
        docs = [a.documento(int(i)) for i in ids]
        if len(docs) < 2 or any(d is None for d in docs):
            raise MotorError("Elige al menos dos documentos para unir.")
        if any(d["estado"] not in ("espera_emparejar", "parado") for d in docs):
            raise MotorError("Solo se pueden unir documentos que esperan revisión.")
        paginas = []
        for d in docs:
            for r in (d["rotaciones"] or [{"n": 1}]):
                if r.get("imagen") and Path(r["imagen"]).exists():
                    paginas.append(Image.open(r["imagen"]).convert("RGB"))
                elif d["extension"] == ".pdf":
                    from .lectura import imagen_pdf
                    paginas.append(imagen_pdf(d["ruta_original"], r["n"]))
                else:
                    paginas.append(ImageOps.exif_transpose(Image.open(d["ruta_original"])).convert("RGB"))
        lote = docs[0]["lote_id"]
        trabajo = self.carpetas.trabajo(lote)
        ruta = libre(trabajo / f"unido_{docs[0]['id']}.pdf")
        paginas[0].save(ruta, "PDF", resolution=200, save_all=True, append_images=paginas[1:])
        nuevo = a.nuevo_documento(lote, f"{Path(docs[0]['nombre_recibido']).stem} (+{len(docs) - 1} unidas).pdf", ruta, huella(ruta), ".pdf")
        a.actualizar(nuevo, fase=1)
        for d in docs:
            a.actualizar(d["id"], estado="unido", unido_en=nuevo, motivo=f"Unido en el documento {nuevo}")
        a.evento(f"Unidos {len(docs)} documentos en un PDF de {len(paginas)} páginas: " + ", ".join(d["nombre_recibido"] for d in docs), nuevo, lote, 1)
        return nuevo

    # ------------------------------------------------------------ fases 7 a 10
    def clave_fecha(self, tipo):
        """Qué fecha da nombre a este tipo de documento: 'periodo', 'emision', 'caducidad' o None."""
        doc = self.variante.docs.get(tipo) or {}
        regla = self.nombrador.r["dato_distintivo"].get(doc.get("zzzz")) or ""
        return next((c for c in (p.partition(":")[0] for p in regla.split("+")) if c in ("periodo", "emision", "caducidad")), None)

    def emparejar(self, doc_id, expediente_id, persona_id=None, de_expediente=False, tipo=None, privado=False, fecha=None):
        """Respuesta a la fase 7. tipo: confirma o corrige la clasificación provisional.
        fecha: la fecha del documento elegida en la revisión (AAAA-MM-DD); manda sobre la leída."""
        a = self.almacen
        d = a.documento(doc_id)
        if not d:
            raise MotorError(f"No existe el documento {doc_id}.")
        if not a.expediente(expediente_id):
            raise MotorError(f"No existe el expediente {expediente_id}.")
        if d["estado"] not in ("espera_emparejar", "parado", "limbo"):
            raise MotorError(f"El documento {doc_id} no espera emparejar (estado: {d['estado']}).")
        if tipo:
            a.evento(f"Tipo corregido a mano: {d['tipo']} → {tipo}", doc_id, d["lote_id"], 7)
        tipo = tipo or d["tipo"]
        if not tipo:
            raise MotorError("Hay que indicar el tipo: el documento no se ha reconocido.")
        if fecha:
            clave = self.clave_fecha(tipo)
            f = datetime.date.fromisoformat(fecha)
            datos = d["datos"] or {}
            if clave:
                datos[clave] = (f.replace(day=1) if clave == "periodo" else f).isoformat()
                a.actualizar(doc_id, datos=datos)
                a.evento(f"Fecha elegida a mano ({clave}): {f:%d/%m/%Y}", doc_id, d["lote_id"], 7)
        personas = a.personas_de(expediente_id)
        if de_expediente or not persona_id:
            persona = personas[0]          # documento común o sin persona indicada: primer titular
        else:
            persona = a.persona(persona_id)
            if persona_id not in [p["id"] for p in personas]:
                papel = "Cotitular" if any(p["papel"] == "Titular" for p in personas) else "Titular"
                a.anadir_persona(expediente_id, persona_id, papel)
                a.evento(f"{persona['nombre']} {persona['apellido1']} añadida al expediente como {papel}", doc_id, d["lote_id"], 7)
        a.actualizar(doc_id, fase=7, tipo=tipo, expediente_id=expediente_id, persona_id=persona["id"],
                     de_expediente=int(de_expediente), privado=int(privado), estado="en_proceso", motivo="")
        a.evento(f"Emparejado con el expediente {expediente_id}" + (" (de todo el expediente)" if de_expediente else f" · {persona['nombre']} {persona['apellido1']}"), doc_id, d["lote_id"], 7)
        return self._renombrar_y_guardar(doc_id)

    def guardar_tarjeta(self, doc_id, expediente_id, entidad, contacto):
        """Tarjeta de visita confirmada: el contacto va al banco del expediente (se añade si no estaba)
        y la imagen se guarda en SeDocumentos\\<expediente>\\Contactos\\ (el original, en Doc_original)."""
        a, c = self.almacen, self.carpetas
        d, exp = a.documento(doc_id), a.expediente(expediente_id)
        if not d or not exp:
            raise MotorError("No existe el documento o el expediente.")
        if d["estado"] not in ("espera_emparejar", "parado"):
            raise MotorError("Este documento ya no espera revisión.")
        bid = self.negociacion.banco(expediente_id, entidad)
        cid = self.negociacion.contacto(bid, contacto, documento_id=doc_id)
        ent = (self.clasificador.abrev5(entidad) if entidad else None) or re.sub(r"\W", "", entidad or "BANCO")[:5].upper()
        quien = re.sub(r"[^A-Za-z]", "", unicodedata.normalize("NFD", ((contacto.get("nombre") or "").split() + ["", ""])[1 if len((contacto.get("nombre") or "").split()) > 1 else 0] or "contacto").encode("ascii", "ignore").decode())
        dir_doc, dir_orig = c.documentos / exp["carpeta"] / "Contactos", c.originales / exp["carpeta"]
        dir_doc.mkdir(parents=True, exist_ok=True); dir_orig.mkdir(parents=True, exist_ok=True)
        destino = libre(dir_doc / f"CONTACTO_{ent}_{quien or 'contacto'}{d['extension'] if d['extension'] != '.pdf' else '.pdf'}")
        self._documento_editado(d, destino)
        orig = None
        if not d["padre_id"]:
            orig = libre(dir_orig / d["nombre_recibido"])
            shutil.move(d["ruta_original"], orig)
        self._limpiar_trabajo(d)
        a.fijar_textos(d)
        a.actualizar(doc_id, fase=10, estado="contacto", expediente_id=expediente_id, nombre_final=destino.name, ruta_final=str(destino),
                     motivo="", **({"ruta_original_final": str(orig)} if orig else {}))
        a.evento(f"Tarjeta de visita guardada como contacto de {entidad} en «{exp['nombre']}»: {destino.name}", doc_id, d["lote_id"], 10)
        return {"banco": bid, "contacto": cid, "nombre_final": destino.name}

    def no_es_tarjeta(self, doc_id):
        a = self.almacen
        d = a.documento(doc_id)
        datos = d["datos"] or {}
        datos["tarjeta_descartada"] = True
        a.actualizar(doc_id, datos=datos)
        a.evento("No es una tarjeta de visita: sigue como documento normal.", doc_id, d["lote_id"], 7)

    def al_limbo(self, doc_id, persona=None):
        a = self.almacen
        if not a.documento(doc_id):
            raise MotorError(f"No existe el documento {doc_id}.")
        p = persona or {"nombre": "", "apellido1": "", "dni": None}
        return self._renombrar_y_guardar(doc_id, limbo=True, persona=p)

    def sacar_del_limbo(self, doc_id):
        """Devuelve un documento del Limbo a la revisión. El PDF que estaba en _Limbo (ya con sus
        páginas y giros) pasa a ser la copia de trabajo; el original sigue donde está hasta guardarlo."""
        a, c = self.almacen, self.carpetas
        d = a.documento(doc_id)
        if not d or d["estado"] != "limbo":
            raise MotorError(f"El documento {doc_id} no está en el Limbo.")
        f = Path(d["ruta_final"] or "")
        if not f.exists():
            raise MotorError(f"No encuentro el archivo en el Limbo: {f}")
        w = libre(c.trabajo(d["lote_id"]) / f"limbo_{doc_id}{f.suffix.lower()}")
        shutil.move(f, w)
        paginas = 1
        if w.suffix.lower() == ".pdf":
            from pypdf import PdfReader
            paginas = len(PdfReader(str(w)).pages)
        a.actualizar(doc_id, estado="espera_emparejar", fase=7, ruta_original=str(w), extension=w.suffix.lower(),
                     paginas=paginas, paginas_sel=None, rotaciones=[{"n": i} for i in range(1, paginas + 1)],
                     ruta_trabajo=str(w.parent), ruta_final=None, nombre_final=None, motivo="Sacado del Limbo")
        a.evento("Sacado del Limbo: vuelve a la revisión", doc_id, d["lote_id"], 7)
        return a.documento(doc_id)

    def _renombrar_y_guardar(self, doc_id, limbo=False, persona=None):
        a, c = self.almacen, self.carpetas
        d = a.documento(doc_id)
        lote = d["lote_id"]
        try:
            # fase 8 · renombrar
            if not limbo:
                persona = a.persona(d["persona_id"])
                exp = a.expediente(d["expediente_id"])
            entidad_abrev = self.clasificador.abrev5(d["entidad"]) if d["entidad"] else None
            fecha_entrada = datetime.date.fromisoformat(d["creado"][:10])
            tipo = d["tipo"] or "desconocido"
            if tipo in self.variante.docs:
                nombre, revisar, motivo = self.nombrador.nombre(tipo, persona, d["datos"] or {}, entidad_abrev, fecha_entrada, bool(d["privado"]), d["extension"])
            else:
                nombre, revisar, motivo = f"SINTIPO_{fecha_entrada:%m%y}{d['extension']}", True, "Sin tipo"
            a.actualizar(doc_id, fase=8)
            a.evento(f"Nombre: {nombre}" + (f" · {motivo}" if motivo else ""), doc_id, lote, 8, "revision" if revisar else "info")
            # fase 9 · checklist
            a.actualizar(doc_id, fase=9)
            # fase 10 · guardar
            destino_dir = c.limbo if limbo else c.documentos / exp["carpeta"]
            orig_dir = c.originales_limbo if limbo else c.originales / exp["carpeta"]
            destino_dir.mkdir(parents=True, exist_ok=True)
            orig_dir.mkdir(parents=True, exist_ok=True)
            destino = libre(destino_dir / nombre)
            self._documento_editado(d, destino)
            orig_destino = None
            hermanos = a.documentos("padre_id = ? AND id != ? AND estado NOT IN ('guardado', 'limbo')", (d["padre_id"], doc_id)) if d["padre_id"] else []
            rescatado = Path(d["ruta_original"]).name.startswith("limbo_") and Path(d["ruta_original"]).parent.parent == c.trabajo_raiz
            if rescatado:         # venía del Limbo: la copia de trabajo sobra; el original real pasa de _Limbo a su sitio
                Path(d["ruta_original"]).unlink(missing_ok=True)
                if not limbo:
                    real = Path(d["ruta_original_final"] or "")
                    if real.is_file() and c.originales_limbo in real.parents:
                        orig_destino = libre(orig_dir / real.name)
                        compartido = a.documentos("ruta_original_final = ? AND id != ? AND estado = 'limbo'", (str(real), doc_id))
                        (shutil.copy2 if compartido else shutil.move)(real, orig_destino)
                        if not compartido and d["padre_id"]:
                            for h in a.documentos("padre_id = ? OR id = ?", (d["padre_id"], d["padre_id"])):
                                if h["ruta_original_final"] == str(real):
                                    a.actualizar(h["id"], ruta_original_final=str(orig_destino))
            elif hermanos:
                a.evento(f"El original se moverá a Doc_original cuando se guarden las otras {len(hermanos)} parte(s) del archivo.", doc_id, lote, 10)
            else:
                fuentes = a.documentos("unido_en = ?", (doc_id,))
                if fuentes:       # PDF unido a partir de fotos: los originales son las fotos; el PDF unido era de trabajo
                    for fu in fuentes:
                        dest_fu = libre(orig_dir / fu["nombre_recibido"])
                        shutil.move(fu["ruta_original"], dest_fu)
                        a.actualizar(fu["id"], ruta_original_final=str(dest_fu))
                    Path(d["ruta_original"]).unlink(missing_ok=True)
                    orig_destino = orig_dir
                else:
                    nombre_orig = a.documento(d["padre_id"])["nombre_recibido"] if d["padre_id"] else d["nombre_recibido"]
                    orig_destino = libre(orig_dir / nombre_orig)
                    shutil.move(d["ruta_original"], orig_destino)
                if d["padre_id"]:
                    for h in a.documentos("padre_id = ? OR id = ?", (d["padre_id"], d["padre_id"])):
                        a.actualizar(h["id"], ruta_original_final=str(orig_destino))
            self._limpiar_trabajo(d)
            a.fijar_textos(d)
            a.actualizar(doc_id, fase=10, estado="limbo" if limbo else "guardado", nombre_final=destino.name,
                         ruta_final=str(destino), **({"ruta_original_final": str(orig_destino)} if orig_destino else {}))
            a.evento(f"Guardado en {destino}" + (f" · original en {orig_destino}" if orig_destino else " · original todavía en Entrada"), doc_id, lote, 10)
            if not limbo:
                res = checklist.evaluar(self.variante, a, d["expediente_id"])
                a.poner_avisos_cliente(d["expediente_id"], res["avisos_cliente"])
                reg = textos.generar(a, c.documentos, d["expediente_id"], self.variante.nombres["sin_dni"])
                a.evento(f"Registro de texto actualizado: {reg.name}", doc_id, lote, 10)
            return a.documento(doc_id)
        except Exception as e:
            f = min(a.documento(doc_id)["fase"] + 1, 10)
            a.actualizar(doc_id, estado="parado", motivo=f"Fase {f} · {NOMBRE_FASE.get(f, '')}: {e}")
            a.evento(f"Parado en la fase {f}: {e}. Nada se ha perdido: el original sigue en Entrada.", doc_id, lote, f, "se")
            raise MotorError(f"Parado en la fase {f}: {e}")

    def _documento_editado(self, d, destino):
        """PDF final: páginas digitales tal cual y las leídas por OCR ya giradas y enderezadas."""
        from PIL import Image
        origen = Path(d["ruta_original"])
        pags = d["rotaciones"] or []
        if destino.suffix.lower() != ".pdf":
            shutil.copy2(origen, destino); return
        if d["extension"] in (".docx", ".xlsx"):
            raise MotorError("Convertir Word o Excel a PDF aún no está disponible: se guardará con su extensión original.")
        if d["extension"] == ".pdf" and not any(p.get("imagen") or p.get("giro") for p in pags) and not d.get("paginas_sel"):
            shutil.copy2(origen, destino); return
        from pypdf import PdfReader, PdfWriter
        from PIL import ImageOps
        w = PdfWriter()
        reader = PdfReader(str(origen)) if d["extension"] == ".pdf" else None
        def de_imagen(img):
            buf = io.BytesIO()
            img.convert("RGB").save(buf, "PDF", resolution=300)
            buf.seek(0)
            return PdfReader(buf).pages[0]
        for p in pags or [{"n": 1}]:
            giro = int(p.get("giro") or 0)          # giro hecho a mano en la revisión
            if p.get("imagen") and Path(p["imagen"]).exists():
                img = Image.open(p["imagen"])
                w.add_page(de_imagen(img.rotate(-giro, expand=True) if giro else img))
            elif reader:
                pg = reader.pages[p["n"] - 1]
                if giro:
                    pg.rotate(giro)
                w.add_page(pg)
            else:                                   # foto sin copia de trabajo (p. ej. sacada del Limbo)
                img = ImageOps.exif_transpose(Image.open(origen))
                total = (int(p.get("rotacion") or 0) + giro) % 360
                w.add_page(de_imagen(img.rotate(-total, expand=True) if total else img))
        with open(destino, "wb") as f:
            w.write(f)

    def _limpiar_trabajo(self, d):
        for p in d["rotaciones"] or []:
            if p.get("imagen"):
                Path(p["imagen"]).unlink(missing_ok=True)
        t = Path(d["ruta_trabajo"]) if d["ruta_trabajo"] else None
        if t and t.exists() and not any(t.iterdir()):
            t.rmdir()

    # ------------------------------------------------------------ datos temporales (M-69)
    def temporales(self):
        """Lo que ocupa la memoria temporal: copia de trabajo y textos guardados."""
        trabajo = [p for p in self.carpetas.trabajo_raiz.rglob("*") if p.is_file()]
        en_uso = {d["ruta_trabajo"] for d in self.almacen.documentos("estado IN ('en_proceso', 'espera_emparejar', 'parado')") if d["ruta_trabajo"]}
        huerfanos = [p for p in trabajo if str(p.parent) not in en_uso]
        n_textos, bytes_textos = self.almacen.db.execute("SELECT COUNT(*), COALESCE(SUM(LENGTH(texto)), 0) FROM textos").fetchone()
        return {"trabajo_archivos": len(trabajo), "trabajo_bytes": sum(p.stat().st_size for p in trabajo),
                "trabajo_sin_uso": len(huerfanos), "trabajo_sin_uso_bytes": sum(p.stat().st_size for p in huerfanos),
                "en_proceso": len(en_uso), "textos_paginas": n_textos, "textos_bytes": bytes_textos}

    def vaciar_trabajo(self, todo=False):
        """Borra la copia de trabajo. Por defecto solo lo que ya no usa ningún documento en proceso;
        con todo=True también lo de los documentos en proceso, que volverán a leerse."""
        en_proceso = self.almacen.documentos("estado IN ('en_proceso', 'espera_emparejar', 'parado')")
        en_uso = {d["ruta_trabajo"] for d in en_proceso if d["ruta_trabajo"]}
        borrados = 0
        for p in sorted(self.carpetas.trabajo_raiz.rglob("*"), reverse=True):
            if p.is_file() and (todo or str(p.parent) not in en_uso):
                p.unlink(); borrados += 1
            elif p.is_dir() and not any(p.iterdir()):
                p.rmdir()
        if todo:
            for d in en_proceso:      # vuelven a la fase 1 para releerse
                self.almacen.actualizar(d["id"], fase=1, estado="en_proceso", ruta_trabajo=None, rotaciones=None, motivo="Copia de trabajo vaciada: se vuelve a leer")
                self.almacen.db.execute("DELETE FROM textos WHERE clave LIKE ?", (f'{d["huella"]}:%',))
            self.almacen.db.commit()
        self.almacen.evento(f"Copia de trabajo vaciada ({borrados} archivos" + (", y documentos en proceso devueltos a la fase 1)" if todo else ")"), nivel="info")
        return borrados

    def vaciar_textos(self):
        """Vacía la memoria temporal de textos. El texto de los documentos ya guardados está aparte
        (y en sus _textos.txt), así que no se pierde; si llega otra vez un archivo ya visto, se volverá
        a leer. Los documentos en proceso conservan su texto."""
        en_proceso = {d["huella"] for d in self.almacen.documentos("estado IN ('en_proceso', 'espera_emparejar', 'parado')")}
        n = 0
        for (clave,) in self.almacen.db.execute("SELECT clave FROM textos").fetchall():
            if clave.split(":")[0] not in en_proceso:
                self.almacen.db.execute("DELETE FROM textos WHERE clave = ?", (clave,)); n += 1
        self.almacen.db.commit()
        self.almacen.evento(f"Memoria de textos vaciada ({n} páginas). Los registros de texto de los expedientes se conservan.", nivel="info")
        return n

    def regenerar_textos(self, expediente_id=None):
        ids = [expediente_id] if expediente_id else [r["id"] for r in self.almacen.db.execute("SELECT id FROM expedientes")]
        return [textos.generar(self.almacen, self.carpetas.documentos, e, self.variante.nombres["sin_dni"]) for e in ids]

    # ------------------------------------------------------------ estado (pantalla del motor)
    def estado(self, lote_id=None):
        docs = self.almacen.documentos("lote_id = ?" if lote_id else "1", (lote_id,) if lote_id else ())
        out = []
        for d in docs:
            if d["estado"] in ("guardado", "limbo", "contacto"):
                donde = {"editado": d["ruta_final"], "original": d["ruta_original_final"]}
            else:
                donde = {"original": d["ruta_original"], "trabajo": d["ruta_trabajo"]}
            out.append({"id": d["id"], "archivo": d["nombre_recibido"], "fase": d["fase"], "fase_nombre": NOMBRE_FASE.get(d["fase"], "Recibir"),
                        "estado": d["estado"], "tipo": d["tipo"], "confianza": d["confianza"], "motivo": d["motivo"], "donde": donde,
                        "expediente_id": d["expediente_id"], "persona_id": d["persona_id"], "nombre_final": d["nombre_final"]})
        return out
