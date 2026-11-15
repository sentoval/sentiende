# -*- coding: utf-8 -*-
"""Gestión de expedientes y del programa (pantallas 15–33 del diseño):

- Estado y datos de la operación (F-16): fases en curso (abierto, documentación completa, enviado al banco,
  aprobado), firmado y cerrado sin operación, con importes, entidad, fechas, honorarios e historial.
- Favorito y prioridad de cada expediente.
- Papelera: eliminar un documento o un expediente entero (se mueve a Papelera\\ con un archivo de
  recuperación) y restaurarlo. Nada se borra de verdad desde el programa.
- Buscar en el texto de todos los documentos.
- Estadísticas.
- Segunda aportación: nombre que tendrá un documento y si ya existe uno igual en el expediente.
- Separar un PDF a mano y girar páginas a mano.
- Personas: editar la ficha (se renombran sus documentos si cambia el código) y cambiar su papel.
- Copia de seguridad de Datos y exportar un expediente en zip.
- Ajustes del usuario (Datos\\ajustes.json): umbrales de revisión, idiomas del OCR, apariencia, bienvenida."""
import datetime, json, re, shutil, zipfile
from pathlib import Path
from .almacen import ahora
from .carpetas import libre

ESQUEMA = """
CREATE TABLE IF NOT EXISTS operacion(expediente_id INTEGER PRIMARY KEY, datos TEXT);
CREATE TABLE IF NOT EXISTS historial_estado(id INTEGER PRIMARY KEY, expediente_id INTEGER, fecha TEXT, estado TEXT, nota TEXT);
CREATE TABLE IF NOT EXISTS marcas_expediente(expediente_id INTEGER PRIMARY KEY, favorito INTEGER DEFAULT 0, prioridad TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS cuarentena(id INTEGER PRIMARY KEY, fecha TEXT, remitente TEXT, asunto TEXT, carpeta TEXT, archivos TEXT, estado TEXT DEFAULT 'pendiente');
CREATE TABLE IF NOT EXISTS remitentes(email TEXT PRIMARY KEY, estado TEXT, fecha TEXT);
CREATE TABLE IF NOT EXISTS papelera(id INTEGER PRIMARY KEY, tipo TEXT, ref_id INTEGER, nombre TEXT, fecha TEXT, carpeta TEXT,
  datos TEXT, restaurado TEXT);
"""
FASES = {"abierto": "Abierto", "completo": "Documentación completa", "enviado": "Enviado al banco", "aprobado": "Aprobado"}
MOTIVOS_CIERRE = ["Denegado por el banco", "El cliente desiste", "Documentación incompleta", "Firmó con otra entidad", "Otro"]
PAPELES = ["Titular", "Cotitular", "Avalista", "Beneficiario", "Cónyuge o pareja no titular", "Administrador", "Titular anterior", "Tercero"]


class ErrorGestion(Exception):
    pass


def _num(v):
    try:
        return float(str(v).replace(".", "").replace(",", ".")) if isinstance(v, str) and "," in v else float(v)
    except (TypeError, ValueError):
        return None


class Gestion:
    def __init__(self, motor):
        self.m = motor
        self.a = motor.almacen
        self.db = self.a.db
        self.db.executescript(ESQUEMA)

    # ------------------------------------------------------------ ajustes del usuario
    @property
    def _ruta_ajustes(self):
        return self.m.carpetas.datos / "ajustes.json"

    def ajustes(self):
        aj = json.loads(self._ruta_ajustes.read_text(encoding="utf-8")) if self._ruta_ajustes.exists() else {}
        aj.setdefault("umbrales", dict(self.m.variante.meta.get("umbrales", {"revisar": 0.75, "no_reconocido": 0.4})))
        aj.setdefault("ocr", {"idiomas": ["spa", "cat", "eus", "glg"]})
        aj.setdefault("apariencia", {"tamano": 100})
        aj.setdefault("bienvenida_vista", False)
        aj["carpetas"] = {k: str(p) for k, p in self.m.carpetas.rutas.items()}
        return aj

    def guardar_ajustes(self, nuevos):
        for k, v in (nuevos.get("carpetas") or {}).items():          # primero las carpetas (escriben su parte del archivo)
            if k in ("entrada", "originales", "documentos", "papelera") and v and str(v) != str(self.m.carpetas.rutas[k]):
                p = Path(v)
                try:
                    p.mkdir(parents=True, exist_ok=True)
                except OSError as e:
                    raise ErrorGestion(f"No se puede usar la carpeta {v}: {e}")
                self.m.carpetas.cambiar(k, p)
                self.m.carpetas.crear()
        aj = json.loads(self._ruta_ajustes.read_text(encoding="utf-8")) if self._ruta_ajustes.exists() else {}
        if "umbrales" in nuevos:
            u = nuevos["umbrales"]
            r, n = float(u.get("revisar", 0.75)), float(u.get("no_reconocido", 0.4))
            if not (0.05 <= n < r <= 0.99):
                raise ErrorGestion("El umbral de «revisar» tiene que ser mayor que el de «no reconocido» (entre 5 y 99 %).")
            aj["umbrales"] = {"revisar": round(r, 2), "no_reconocido": round(n, 2)}
        if "ocr" in nuevos:
            idi = [i for i in nuevos["ocr"].get("idiomas", []) if i in ("spa", "cat", "eus", "glg", "eng")]
            aj["ocr"] = {"idiomas": idi or ["spa"]}
        if "apariencia" in nuevos:
            aj["apariencia"] = {"tamano": max(80, min(140, int(nuevos["apariencia"].get("tamano", 100))))}
        if "bienvenida_vista" in nuevos:
            aj["bienvenida_vista"] = bool(nuevos["bienvenida_vista"])
        if "avisos_se_visto" in nuevos:
            aj["avisos_se_visto"] = int(nuevos["avisos_se_visto"])
        self.m.carpetas.datos.mkdir(parents=True, exist_ok=True)
        self._ruta_ajustes.write_text(json.dumps(aj, ensure_ascii=False, indent=1), encoding="utf-8")
        self.aplicar()
        return self.ajustes()

    def aplicar(self):
        """Pone en marcha los ajustes guardados (umbrales e idiomas del OCR)."""
        aj = self.ajustes()
        self.m.variante.meta["umbrales"] = aj["umbrales"]
        from . import lectura
        lectura.IDIOMAS_PREFERIDOS = list(aj["ocr"]["idiomas"])

    # ------------------------------------------------------------ estado y datos de la operación
    def operacion(self, eid):
        exp = self.a.expediente(eid)
        if not exp:
            raise ErrorGestion("No existe el expediente.")
        r = self.db.execute("SELECT datos FROM operacion WHERE expediente_id = ?", (eid,)).fetchone()
        datos = json.loads(r["datos"]) if r else {}
        datos.setdefault("fase", "abierto")
        hist = [dict(x) for x in self.db.execute("SELECT * FROM historial_estado WHERE expediente_id = ? ORDER BY id DESC", (eid,))]
        return {"estado": exp["estado"], "datos": datos, "historial": hist, "fases": FASES, "motivos": MOTIVOS_CIERRE,
                "etiqueta": self.etiqueta(exp["estado"], datos)}

    @staticmethod
    def etiqueta(estado, datos):
        if estado == "firmado":
            return "Firmado"
        if estado == "cerrado":
            return "Cerrado sin operación"
        if estado == "unido":
            return "Unido a otro"
        if estado == "papelera":
            return "En la Papelera"
        return FASES.get((datos or {}).get("fase", "abierto"), "Abierto")

    def _guardar_datos(self, eid, datos):
        self.db.execute("INSERT OR REPLACE INTO operacion VALUES(?, ?)", (eid, json.dumps(datos, ensure_ascii=False)))

    def _historial(self, eid, estado, nota=""):
        self.db.execute("INSERT INTO historial_estado(expediente_id, fecha, estado, nota) VALUES(?, ?, ?, ?)", (eid, ahora(), estado, nota))

    @staticmethod
    def _honorarios(d):
        tipo, val = d.get("honorarios_tipo"), _num(d.get("honorarios_valor"))
        base = _num(d.get("importe_concedido")) or _num(d.get("importe_solicitado"))
        if val is None:
            return None
        return round(base * val / 100, 2) if tipo == "porcentaje" and base else (val if tipo != "porcentaje" else None)

    def guardar_operacion(self, eid, nuevos):
        op = self.operacion(eid)
        d = op["datos"]
        campos = ("importe_solicitado", "importe_concedido", "entidad", "fecha_envio", "fecha_aprobacion", "fecha_firma",
                  "honorarios_tipo", "honorarios_valor", "factura_num", "factura_fecha", "fecha_cobro", "nota", "contacto_email", "contacto_tel")
        for k in campos:
            if k in nuevos:
                d[k] = nuevos[k]
        d["honorarios_importe"] = self._honorarios(d)
        self._guardar_datos(eid, d)
        if nuevos.get("fecha_cobro") and op["estado"] == "firmado":
            self._historial(eid, "cobrado", f"Honorarios cobrados el {nuevos['fecha_cobro']}")
        self.db.commit()
        return self.operacion(eid)

    def cambiar_estado(self, eid, nuevo, extra=None):
        extra = extra or {}
        op = self.operacion(eid)
        d = op["datos"]
        exp = self.a.expediente(eid)
        if nuevo in FASES:
            d["fase"] = nuevo
            if nuevo == "enviado" and not d.get("fecha_envio"):
                d["fecha_envio"] = datetime.date.today().isoformat()
            if nuevo == "aprobado" and not d.get("fecha_aprobacion"):
                d["fecha_aprobacion"] = datetime.date.today().isoformat()
            estado_exp = "abierto"
            nota = FASES[nuevo]
        elif nuevo == "firmado":
            for k in ("importe_concedido", "entidad", "fecha_firma", "honorarios_tipo", "honorarios_valor"):
                if extra.get(k) not in (None, ""):
                    d[k] = extra[k]
            d.setdefault("fecha_firma", datetime.date.today().isoformat())
            d["honorarios_importe"] = self._honorarios(d)
            estado_exp, nota = "firmado", f"Firmado con {d.get('entidad') or '?'}" + (f" · honorarios {d['honorarios_importe']} € pendientes de cobro" if d.get("honorarios_importe") else "")
        elif nuevo == "cerrado":
            if not extra.get("motivo"):
                raise ErrorGestion("Indica el motivo del cierre.")
            d.update(motivo_cierre=extra["motivo"], fecha_cierre=extra.get("fecha") or datetime.date.today().isoformat(),
                     entidad_cierre=extra.get("entidad", ""), nota_cierre=extra.get("nota", ""))
            estado_exp, nota = "cerrado", f"Cerrado sin operación: {extra['motivo']}" + (f" ({extra['nota']})" if extra.get("nota") else "")
        elif nuevo == "reabrir":
            estado_exp, nota = "abierto", "Reabierto"
        else:
            raise ErrorGestion("Estado desconocido.")
        self._guardar_datos(eid, d)
        self.db.execute("UPDATE expedientes SET estado = ? WHERE id = ?", (estado_exp, eid))
        self._historial(eid, nuevo, nota)
        self.db.commit()
        self.a.evento(f"Expediente «{exp['nombre']}»: {nota}")
        return self.operacion(eid)

    # ------------------------------------------------------------ favorito y prioridad
    def marcas(self):
        return {r["expediente_id"]: {"favorito": bool(r["favorito"]), "prioridad": r["prioridad"] or ""}
                for r in self.db.execute("SELECT * FROM marcas_expediente")}

    def marcar(self, eid, favorito=None, prioridad=None):
        actual = self.marcas().get(eid, {"favorito": False, "prioridad": ""})
        if favorito is not None:
            actual["favorito"] = bool(favorito)
        if prioridad is not None:
            if prioridad not in ("", "baja", "media", "alta"):
                raise ErrorGestion("Prioridad desconocida.")
            actual["prioridad"] = prioridad
        self.db.execute("INSERT OR REPLACE INTO marcas_expediente VALUES(?, ?, ?)", (eid, int(actual["favorito"]), actual["prioridad"]))
        self.db.commit()
        return actual

    # ------------------------------------------------------------ papelera
    def _carpeta_papelera(self, nombre):
        p = libre(self.m.carpetas.papelera / f"{datetime.datetime.now():%Y-%m-%d_%H%M%S}_{re.sub(r'[^A-Za-z0-9_.-]', '_', nombre)}")
        p.mkdir(parents=True)
        return p

    def eliminar_documento(self, doc_id):
        a = self.a
        d = a.documento(doc_id)
        if not d or d["estado"] in ("papelera", "separado", "unido"):
            raise ErrorGestion("Ese documento no se puede eliminar.")
        destino = self._carpeta_papelera(d["nombre_final"] or d["nombre_recibido"])
        movidos = {}
        rutas = [("editado", d["ruta_final"])]
        compartido = d["ruta_original_final"] and a.documentos("ruta_original_final = ? AND id != ? AND estado NOT IN ('papelera')", (d["ruta_original_final"], doc_id))
        if d["estado"] in ("guardado", "limbo", "contacto"):
            if not compartido:
                rutas.append(("original", d["ruta_original_final"]))
        elif not d["padre_id"] and not a.documentos("padre_id = ?", (doc_id,)):
            rutas.append(("original", d["ruta_original"]))          # aún en revisión: el original está en Entrada
        for clave, r in rutas:
            if r and Path(r).is_file():
                n = libre(destino / Path(r).name)
                shutil.move(r, n)
                movidos[clave] = {"desde": r, "en": str(n)}
        info = {"documento": doc_id, "estado_antes": d["estado"], "expediente_id": d["expediente_id"], "movidos": movidos, "fecha": ahora()}
        (destino / "recuperacion.json").write_text(json.dumps(info, ensure_ascii=False, indent=1), encoding="utf-8")
        self.db.execute("INSERT INTO papelera(tipo, ref_id, nombre, fecha, carpeta, datos) VALUES('documento', ?, ?, ?, ?, ?)",
                        (doc_id, d["nombre_final"] or d["nombre_recibido"], ahora(), str(destino), json.dumps(info, ensure_ascii=False)))
        a.actualizar(doc_id, estado="papelera", motivo=f"En la Papelera ({destino.name})")
        a.evento(f"Documento enviado a la Papelera: {destino}", doc_id, d["lote_id"])
        if d["expediente_id"]:
            from .arreglos import _refrescar
            _refrescar(self.m, d["expediente_id"])
        return {"carpeta": str(destino)}

    def eliminar_expediente(self, eid):
        a, c = self.a, self.m.carpetas
        exp = a.expediente(eid)
        if not exp or exp["estado"] == "papelera":
            raise ErrorGestion("Ese expediente no se puede eliminar.")
        destino = self._carpeta_papelera(exp["carpeta"])
        movidos = {}
        for clave, base in (("documentos", c.documentos), ("originales", c.originales)):
            src = base / exp["carpeta"]
            if src.exists():
                shutil.move(str(src), destino / clave)
                movidos[clave] = {"desde": str(src), "en": str(destino / clave)}
        info = {"expediente": eid, "estado_antes": exp["estado"], "carpeta": exp["carpeta"], "movidos": movidos, "fecha": ahora()}
        (destino / "recuperacion.json").write_text(json.dumps(info, ensure_ascii=False, indent=1), encoding="utf-8")
        self.db.execute("INSERT INTO papelera(tipo, ref_id, nombre, fecha, carpeta, datos) VALUES('expediente', ?, ?, ?, ?, ?)",
                        (eid, exp["nombre"], ahora(), str(destino), json.dumps(info, ensure_ascii=False)))
        self.db.execute("UPDATE expedientes SET estado = 'papelera' WHERE id = ?", (eid,))
        self.db.commit()
        a.poner_avisos_cliente(eid, [])
        a.evento(f"Expediente «{exp['nombre']}» enviado a la Papelera con sus documentos y originales: {destino}")
        return {"carpeta": str(destino)}

    def papelera(self):
        return [dict(r) | {"datos": json.loads(r["datos"])} for r in self.db.execute("SELECT * FROM papelera WHERE restaurado IS NULL ORDER BY id DESC")]

    def restaurar(self, pid):
        r = self.db.execute("SELECT * FROM papelera WHERE id = ?", (pid,)).fetchone()
        if not r or r["restaurado"]:
            raise ErrorGestion("No está en la Papelera.")
        info = json.loads(r["datos"])
        for mv in info["movidos"].values():
            if Path(mv["en"]).exists():
                Path(mv["desde"]).parent.mkdir(parents=True, exist_ok=True)
                if Path(mv["desde"]).exists():
                    raise ErrorGestion(f"Ya hay algo en {mv['desde']}: muévelo antes de restaurar.")
                shutil.move(mv["en"], mv["desde"])
        if r["tipo"] == "documento":
            self.a.actualizar(r["ref_id"], estado=info["estado_antes"], motivo="Restaurado de la Papelera")
            if info.get("expediente_id"):
                from .arreglos import _refrescar
                _refrescar(self.m, info["expediente_id"])
        else:
            self.db.execute("UPDATE expedientes SET estado = ? WHERE id = ?", (info["estado_antes"], r["ref_id"]))
        self.db.execute("UPDATE papelera SET restaurado = ? WHERE id = ?", (ahora(), pid))
        self.db.commit()
        carpeta = Path(r["carpeta"])
        try:
            (carpeta / "recuperacion.json").unlink()
            carpeta.rmdir()
        except OSError:
            pass
        self.a.evento(f"Restaurado de la Papelera: {r['nombre']}")
        return {"ok": True}

    # ------------------------------------------------------------ buscar
    def buscar(self, q, limite=60):
        from .extraer import norm
        q = norm(q or "").strip()
        if len(q) < 3:
            raise ErrorGestion("Escribe al menos 3 letras.")
        palabras = q.split()
        exps = {r["id"]: dict(r) for r in self.db.execute("SELECT id, nombre FROM expedientes")}
        out = []
        for d in self.a.documentos("estado NOT IN ('separado', 'unido', 'papelera', 'duplicado')"):
            if d["privado"]:
                continue
            textos = [x["texto"] for x in self.a.textos_de(d["id"]).values()]
            if not textos:
                sel = d["paginas_sel"] or range(1, (d["paginas"] or 1) + 1)
                textos = [(self.a.texto_cache(f'{d["huella"]}:{n}') or {}).get("texto", "") for n in sel]
            completo = "\n".join(t or "" for t in textos)
            nt = norm(completo)
            campos = norm(" ".join(str(x or "") for x in (d["nombre_final"], d["nombre_recibido"], d["tipo"])))
            if all(p in nt or p in campos for p in palabras):
                import unicodedata
                plano = "".join((unicodedata.normalize("NFD", ch)[0] if ch else ch).lower() for ch in completo)   # misma longitud que el texto
                clave = unicodedata.normalize("NFD", (q.split() or [""])[0]).encode("ascii", "ignore").decode().lower()
                i = plano.find(clave)
                trozo = completo[max(0, i - 70): i + 110].replace("\n", " ").replace("¦", " ") if i >= 0 else completo[:150].replace("\n", " ")
                out.append({"id": d["id"], "nombre": d["nombre_final"] or d["nombre_recibido"], "tipo": d["tipo"], "estado": d["estado"],
                            "expediente_id": d["expediente_id"], "expediente": (exps.get(d["expediente_id"]) or {}).get("nombre", ""),
                            "trozo": trozo, "ruta": d["ruta_final"] or d["ruta_original"]})
                if len(out) >= limite:
                    break
        return out

    # ------------------------------------------------------------ estadísticas
    def estadisticas(self):
        exps = [dict(r) for r in self.db.execute("SELECT * FROM expedientes WHERE estado NOT IN ('unido', 'papelera')")]
        ops = {r["expediente_id"]: json.loads(r["datos"]) for r in self.db.execute("SELECT * FROM operacion")}
        fin = self.m.variante.meta.get("finalidades", {})
        cuenta = {"en_curso": 0, "firmados": 0, "cerrados": 0}
        por_fin, por_ent, motivos, dias = {}, {}, {}, []
        sol = firm = honor = pend = 0.0
        n_firm_imp = 0
        for e in exps:
            d = ops.get(e["id"], {})
            st = {"abierto": "en_curso", "firmado": "firmados", "cerrado": "cerrados"}.get(e["estado"])
            if st:
                cuenta[st] += 1
            f = por_fin.setdefault(fin.get(e["finalidad"], e["finalidad"]), {"total": 0, "firmados": 0, "cerrados": 0, "importe_firmado": 0.0})
            f["total"] += 1
            sol += _num(d.get("importe_solicitado")) or 0
            if e["estado"] == "firmado":
                f["firmados"] += 1
                imp = _num(d.get("importe_concedido")) or 0
                firm += imp; f["importe_firmado"] += imp; n_firm_imp += 1 if imp else 0
                ent = d.get("entidad") or "Sin indicar"
                pe = por_ent.setdefault(ent, {"firmados": 0, "importe": 0.0, "cerrados": 0}); pe["firmados"] += 1; pe["importe"] += imp
                h = _num(d.get("honorarios_importe")) or 0
                honor += h
                if not d.get("fecha_cobro"):
                    pend += h
                if d.get("fecha_firma"):
                    try:
                        dias.append((datetime.date.fromisoformat(d["fecha_firma"][:10]) - datetime.date.fromisoformat(e["creado"][:10])).days)
                    except ValueError:
                        pass
            if e["estado"] == "cerrado":
                f["cerrados"] += 1
                motivos[d.get("motivo_cierre") or "Sin motivo"] = motivos.get(d.get("motivo_cierre") or "Sin motivo", 0) + 1
                if d.get("entidad_cierre"):
                    por_ent.setdefault(d["entidad_cierre"], {"firmados": 0, "importe": 0.0, "cerrados": 0})["cerrados"] += 1
        # documentos que más cuesta conseguir: los pendientes en los expedientes en curso
        from . import checklist
        faltan = {}
        for e in exps:
            if e["estado"] != "abierto":
                continue
            try:
                for f in checklist.evaluar(self.m.variante, self.a, e["id"])["filas"]:
                    if f["estado"] != "Recibido":
                        faltan[f["documento"]] = faltan.get(f["documento"], 0) + 1
            except Exception:
                pass
        return {"cuenta": cuenta, "total": len(exps), "importe_solicitado": round(sol, 2), "importe_firmado": round(firm, 2),
                "media_firmada": round(firm / n_firm_imp, 2) if n_firm_imp else 0, "por_finalidad": por_fin, "por_entidad": por_ent,
                "motivos_cierre": motivos, "dias_hasta_firmar": round(sum(dias) / len(dias)) if dias else None,
                "honorarios_facturados": round(honor, 2), "honorarios_pendientes": round(pend, 2),
                "honorarios_medios": round(honor / cuenta["firmados"], 2) if cuenta["firmados"] else 0,
                "documentos_que_faltan": sorted(faltan.items(), key=lambda x: -x[1])[:10]}

    # ------------------------------------------------------------ segunda aportación
    def nombre_previsto(self, doc_id, expediente_id, persona_id=None, tipo=None, fecha=None, privado=False, comun=False):
        """Qué nombre tendrá el documento y si ya hay uno igual en ese expediente (segunda aportación)."""
        a, m = self.a, self.m
        d, exp = a.documento(doc_id), a.expediente(expediente_id)
        if not d or not exp:
            raise ErrorGestion("No existe el documento o el expediente.")
        tipo = tipo or d["tipo"]
        if not tipo or tipo not in m.variante.docs:
            return {"nombre": None, "existe": None}
        personas = a.personas_de(expediente_id)
        persona = personas[0] if comun or not persona_id else (a.persona(persona_id) or personas[0])
        datos = dict(d["datos"] or {})
        if fecha:
            clave = m.clave_fecha(tipo)
            if clave:
                f = datetime.date.fromisoformat(fecha)
                datos[clave] = (f.replace(day=1) if clave == "periodo" else f).isoformat()
        ent = m.clasificador.abrev5(d["entidad"]) if d["entidad"] else None
        nombre = m.nombrador.nombre(tipo, persona, datos, ent, datetime.date.fromisoformat(d["creado"][:10]), bool(privado), d["extension"])[0]
        ruta = m.carpetas.documentos / exp["carpeta"] / nombre
        previo = None
        if ruta.exists():
            previo = next((x for x in a.documentos("ruta_final = ?", (str(ruta),))), None)
        return {"nombre": nombre, "existe": ruta.exists(), "previo": {"id": previo["id"], "nombre": previo["nombre_final"], "creado": previo["creado"]} if previo else None}

    def sustituir_previo(self, expediente_id, nombre):
        """Antes de guardar el nuevo: el anterior pasa a llamarse …-ant y deja de contar en la checklist."""
        exp = self.a.expediente(expediente_id)
        ruta = self.m.carpetas.documentos / exp["carpeta"] / nombre
        if not ruta.exists():
            return None
        nueva = libre(ruta.with_name(f"{ruta.stem}-ant{ruta.suffix}"))
        shutil.move(str(ruta), nueva)
        for x in self.a.documentos("ruta_final = ?", (str(ruta),)):
            self.a.actualizar(x["id"], estado="sustituido", nombre_final=nueva.name, ruta_final=str(nueva), motivo="Sustituido por una aportación nueva")
            self.a.evento(f"Sustituido por una aportación nueva: ahora se llama {nueva.name}", x["id"], x["lote_id"])
        return str(nueva)

    # ------------------------------------------------------------ separar y girar a mano
    def separar_manual(self, doc_id, grupos):
        a, m = self.a, self.m
        d = a.documento(doc_id)
        if not d or d["estado"] not in ("espera_emparejar", "parado"):
            raise ErrorGestion("Solo se separan documentos que esperan revisión.")
        sel = d["paginas_sel"] or list(range(1, (d["paginas"] or 1) + 1))
        grupos = [[int(n) for n in g] for g in grupos if g]
        usadas = [n for g in grupos for n in g]
        if len(grupos) < 2 or sorted(usadas) != sorted(sel) or len(set(usadas)) != len(usadas):
            raise ErrorGestion("Reparte todas las páginas en dos documentos o más, sin repetir ninguna.")
        padre = d["padre_id"] or doc_id
        rot = {r["n"]: r for r in d["rotaciones"] or []}
        nuevos = []
        for g in grupos:
            rango = f"pág. {g[0]}" if len(g) == 1 else "págs. " + ", ".join(map(str, g))
            base = a.documento(padre)["nombre_recibido"]
            h = a.nuevo_documento(d["lote_id"], f"{base} ({rango})", d["ruta_original"], d["huella"], d["extension"], padre_id=padre)
            a.actualizar(h, fase=4, paginas=len(g), paginas_sel=g, ruta_trabajo=d["ruta_trabajo"], rotaciones=[rot.get(n, {"n": n}) for n in g],
                         confianza=d["confianza"])
            m._procesar_doc(a.documento(h))
            nuevos.append(h)
        a.actualizar(doc_id, estado="separado", motivo=f"Separado a mano en {len(grupos)} documentos")
        if padre != doc_id:
            pass
        else:
            a.actualizar(doc_id, fase=3)
        a.evento(f"Separado a mano en {len(grupos)} documentos: " + " · ".join("+".join(map(str, g)) for g in grupos), doc_id, d["lote_id"], 3)
        return nuevos

    def girar(self, doc_id, pos, grados):
        a = self.a
        d = a.documento(doc_id)
        sel = d["paginas_sel"] or list(range(1, (d["paginas"] or 1) + 1))
        n = sel[max(1, min(int(pos), len(sel))) - 1]
        rots = d["rotaciones"] or [{"n": x} for x in sel]
        r = next((x for x in rots if x.get("n") == n), None)
        if r is None:
            r = {"n": n}; rots.append(r)
        r["giro"] = (int(r.get("giro", 0)) + int(grados)) % 360
        a.actualizar(doc_id, rotaciones=rots)
        a.evento(f"Página {pos} girada a mano {grados}°", doc_id, d["lote_id"], 4)
        return r["giro"]

    # ------------------------------------------------------------ personas
    def personas(self):
        out = []
        for r in self.db.execute("SELECT * FROM personas ORDER BY apellido1, nombre"):
            p = dict(r)
            p["expedientes"] = [dict(x) for x in self.db.execute(
                "SELECT e.id, e.nombre, e.estado, ep.papel FROM expediente_personas ep JOIN expedientes e ON e.id = ep.expediente_id WHERE ep.persona_id = ?", (p["id"],))]
            p["documentos"] = self.db.execute("SELECT COUNT(*) FROM documentos WHERE persona_id = ? AND estado = 'guardado'", (p["id"],)).fetchone()[0]
            out.append(p)
        return out

    def editar_persona(self, pid, campos):
        a = self.a
        p = a.persona(pid)
        if not p:
            raise ErrorGestion("No existe esa persona.")
        nuevos = {k: (campos.get(k) or "").strip() for k in ("nombre", "apellido1", "apellido2", "dni") if k in campos}
        if "dni" in nuevos:
            nuevos["dni"] = nuevos["dni"].upper().replace("-", "").replace(" ", "") or None
            otro = a.persona_por_dni(nuevos["dni"]) if nuevos["dni"] else None
            if otro and otro["id"] != pid:
                raise ErrorGestion(f"Ese DNI ya es de {otro['nombre']} {otro['apellido1']}: si es la misma persona, únelas en Ajustes → Fichas repetidas.")
        if not nuevos.get("nombre", p["nombre"]) or not nuevos.get("apellido1", p["apellido1"]):
            raise ErrorGestion("El nombre y el primer apellido no pueden quedar vacíos.")
        self.db.execute(f"UPDATE personas SET {', '.join(k + ' = ?' for k in nuevos)} WHERE id = ?", (*nuevos.values(), pid))
        self.db.commit()
        from .arreglos import _colocar, _refrescar
        persona = a.persona(pid)
        afectados = set()
        for d in a.documentos("persona_id = ? AND estado = 'guardado'", (pid,)):
            a.actualizar(d["id"], **_colocar(self.m, d, a.expediente(d["expediente_id"]), persona, mover_original=False))
            afectados.add(d["expediente_id"])
        for r in self.db.execute("SELECT expediente_id FROM expediente_personas WHERE persona_id = ?", (pid,)).fetchall():
            afectados.add(r[0])
        for eid in afectados:
            _refrescar(self.m, eid)
        a.evento(f"Ficha de persona editada: {persona['nombre']} {persona['apellido1']}")
        return persona

    def cambiar_papel(self, eid, pid, papel):
        if papel not in PAPELES:
            raise ErrorGestion("Papel desconocido.")
        self.db.execute("UPDATE expediente_personas SET papel = ? WHERE expediente_id = ? AND persona_id = ?", (papel, eid, pid))
        self.db.commit()
        from .arreglos import _refrescar
        _refrescar(self.m, eid)
        return {"ok": True}

    # ------------------------------------------------------------ copias y exportar
    def copia_seguridad(self):
        c = self.m.carpetas
        destino = c.datos / "Copias"
        destino.mkdir(parents=True, exist_ok=True)
        z = destino / f"copia_datos_{datetime.datetime.now():%Y%m%d_%H%M}.zip"
        self.db.commit()
        with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as f:
            for p in c.datos.rglob("*"):
                if p.is_file() and not ({"Trabajo", "Copias", "Exportados", "Cuarentena"} & set(p.relative_to(c.datos).parts)):
                    f.write(p, p.relative_to(c.datos))
        return {"ruta": str(z), "bytes": z.stat().st_size}

    def exportar_expediente(self, eid, privados=False):
        c, exp = self.m.carpetas, self.a.expediente(eid)
        src = c.documentos / exp["carpeta"]
        destino = c.datos / "Exportados"
        destino.mkdir(parents=True, exist_ok=True)
        z = libre(destino / f"{exp['carpeta']}_{datetime.date.today():%Y%m%d}.zip")
        pref = self.m.nombrador.r.get("prefijo_privado", "PRIVADO_NO_COMPARTIR_")
        n = fuera = 0
        with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as f:
            for p in src.rglob("*") if src.exists() else []:
                if not p.is_file():
                    continue
                if p.name.startswith(pref) and not privados:
                    fuera += 1
                    continue
                f.write(p, Path(exp["carpeta"]) / p.relative_to(src)); n += 1
        return {"ruta": str(z), "archivos": n, "privados_fuera": fuera}


    # ------------------------------------------------------------ correo por revisar (remitentes nuevos)
    def decidir_remitente(self, email):
        r = self.db.execute("SELECT estado FROM remitentes WHERE email = ?", (email,)).fetchone()
        return {"confianza": "ok", "bloqueado": "bloqueado"}.get(r["estado"] if r else "", "cuarentena")

    def poner_en_cuarentena(self, rutas, remitente, asunto):
        carpeta = libre(self.m.carpetas.datos / "Cuarentena" / f"{datetime.datetime.now():%Y%m%d_%H%M%S}")
        carpeta.mkdir(parents=True)
        nombres = []
        for r in rutas:
            n = libre(carpeta / Path(r).name)
            shutil.move(str(r), n)
            nombres.append(n.name)
        self.db.execute("INSERT INTO cuarentena(fecha, remitente, asunto, carpeta, archivos) VALUES(?, ?, ?, ?, ?)",
                        (ahora(), remitente, asunto, str(carpeta), json.dumps(nombres, ensure_ascii=False)))
        self.db.commit()
        self.a.evento(f"Correo de un remitente nuevo ({remitente}, «{asunto}»): {len(nombres)} adjunto(s) esperan en «Correo por revisar».", nivel="revision")

    def cuarentena(self):
        return [dict(r) | {"archivos": json.loads(r["archivos"])} for r in self.db.execute("SELECT * FROM cuarentena WHERE estado = 'pendiente' ORDER BY id DESC")]

    def resolver_cuarentena(self, cid, accion):
        """accion: 'aceptar' (y el remitente pasa a ser de confianza), 'aceptar_una' (solo este correo),
        'rechazar' (los adjuntos van a la Papelera) o 'bloquear' (rechazar y no volver a recoger de ese remitente).
        Devuelve las rutas aceptadas (las mete en el motor quien llama)."""
        r = self.db.execute("SELECT * FROM cuarentena WHERE id = ?", (cid,)).fetchone()
        if not r or r["estado"] != "pendiente":
            raise ErrorGestion("Ese correo ya no está por revisar.")
        rutas = [Path(r["carpeta"]) / n for n in json.loads(r["archivos"])]
        if accion in ("aceptar", "aceptar_una"):
            if accion == "aceptar":
                self.db.execute("INSERT OR REPLACE INTO remitentes VALUES(?, 'confianza', ?)", (r["remitente"], ahora()))
            estado, salida = "aceptado", [p for p in rutas if p.exists()]
        elif accion in ("rechazar", "bloquear"):
            destino = self._carpeta_papelera(f"correo_{r['remitente']}")
            for p in rutas:
                if p.exists():
                    shutil.move(str(p), libre(destino / p.name))
            if accion == "bloquear":
                self.db.execute("INSERT OR REPLACE INTO remitentes VALUES(?, 'bloqueado', ?)", (r["remitente"], ahora()))
            estado, salida = "rechazado", []
        else:
            raise ErrorGestion("Acción desconocida.")
        self.db.execute("UPDATE cuarentena SET estado = ? WHERE id = ?", (estado, cid))
        self.db.commit()
        return salida
