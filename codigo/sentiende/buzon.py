# -*- coding: utf-8 -*-
"""Política del correo (3.2, Joan 17/11/2026): decide con lo registrado si un correo es «apto».

- Remitente conocido: su dirección está en «Correos recibidos» (se apunta sola cuando un documento que llegó en
  su correo se guarda en el expediente de una persona) o en «Correo informado» (metido a mano) de alguna ficha.
- Remitentes bloqueados (los de la antigua «Correo por revisar»): se ignoran siempre.
- Solo fotos de un desconocido: aptas si el OCR reconoce un tipo de documento con ≥ 50 % de seguridad (el motor
  vuelve a filtrar al 75 %), si sale el nombre o el DNI de alguien registrado, o si el nombre del archivo ya dice
  qué es (p. ej. «dni.jpg»), aunque el OCR no pueda leerlo.
- Word o Excel de un desconocido (sin PDF): no se abren; se pregunta en la campanita (Sí / No / No y bloquear).
- Solo PDF de un desconocido (regla 3c): si al terminar el lote nada se relaciona con lo registrado (ningún
  documento reconocido ni ninguna persona), los documentos salen del programa y el correo vuelve a la entrada
  sin la etiqueta.
"""
import datetime, json, re
from pathlib import Path

from .extraer import norm

PALABRA_ARCHIVO = 3          # longitud mínima de una palabra del nombre del archivo para compararla con los tipos


def ahora():
    return datetime.datetime.now().isoformat(timespec="seconds")


class PoliticaCorreo:
    def __init__(self, motor, contexto):
        self.m, self.a, self.ctx = motor, motor.almacen, contexto
        self.db = self.a.db
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS correo_lotes(lote_id INTEGER PRIMARY KEY, remitente TEXT, message_id TEXT, carpeta TEXT,
            regla TEXT, estado TEXT DEFAULT 'activo', fecha TEXT);
        CREATE TABLE IF NOT EXISTS correo_preguntas(clave TEXT PRIMARY KEY, datos TEXT, estado TEXT DEFAULT 'pendiente',
            noti_id INTEGER, fecha TEXT);
        """)
        cols = [r[1] for r in self.db.execute("PRAGMA table_info(personas)")]
        if "correos_recibidos" not in cols:
            self.db.execute("ALTER TABLE personas ADD COLUMN correos_recibidos TEXT DEFAULT '[]'")
        if "correo_informado" not in cols:
            self.db.execute("ALTER TABLE personas ADD COLUMN correo_informado TEXT")
        self.db.commit()

    # ------------------------------------------------------------ remitentes
    def estado(self, email):
        email = (email or "").lower().strip()
        r = self.db.execute("SELECT estado FROM remitentes WHERE email = ?", (email,)).fetchone()
        if r and r[0] == "bloqueado":
            return "bloqueado", None
        for p in self.db.execute("SELECT nombre, apellido1, apellido2, correos_recibidos, correo_informado FROM personas"):
            correos = {x.lower() for x in json.loads(p["correos_recibidos"] or "[]")}
            correos |= {x.strip().lower() for x in re.split(r"[;,\s]+", p["correo_informado"] or "") if x.strip()}
            if email in correos:
                return "conocido", f'{p["nombre"]} {p["apellido1"]} {p["apellido2"] or ""}'.strip()
        return "desconocido", None

    def apuntar_remitente(self, doc):
        """Un documento que llegó por correo se ha guardado: su remitente pasa a «Correos recibidos» de la persona
        (o del titular si es de todo el expediente). Así el remitente queda conocido y no se hace tapón."""
        r = self.db.execute("SELECT remitente FROM correo_lotes WHERE lote_id = ?", (doc["lote_id"],)).fetchone()
        if not r or not r[0] or not doc.get("expediente_id"):
            return
        pid = doc.get("persona_id")
        if doc.get("de_expediente") or not pid:
            pers = self.a.personas_de(doc["expediente_id"])
            pid = pers[0]["id"] if pers else None
        if not pid:
            return
        fila = self.db.execute("SELECT correos_recibidos FROM personas WHERE id = ?", (pid,)).fetchone()
        correos = json.loads((fila and fila[0]) or "[]")
        if r[0] not in correos:
            correos.append(r[0])
            self.db.execute("UPDATE personas SET correos_recibidos = ? WHERE id = ?", (json.dumps(correos), pid))
            self.db.commit()

    # ------------------------------------------------------------ 3a: solo fotos
    def imagenes_aptas(self, rutas):
        tipos = self.m.variante.docs
        for r in rutas:
            # por el nombre del archivo («dni.jpg», «nomina_marzo.png»…), aunque no se pueda leer
            palabras = set(re.findall(r"[a-z]{%d,}" % PALABRA_ARCHIVO, norm(Path(r).stem).lower()))
            for d in tipos.values():
                nombres = {d["id"], (d.get("nombrecorto") or "").lower()} | {norm(n).lower() for n in d["nombres"].get("es", [])[:1]}
                if palabras & {x for x in nombres if x and len(x) >= PALABRA_ARCHIVO}:
                    return True
            try:
                from .lectura import leer
                texto = leer(r, "imagen").texto
            except Exception:
                continue
            c = self.m.clasificador.clasificar(texto)
            if c.tipo and c.confianza >= 0.5:
                return True
            if self._registrado_en(texto):
                return True
        return False

    def _registrado_en(self, texto):
        t = re.sub(r"\s+", " ", norm(texto))
        for p in self.db.execute("SELECT nombre, apellido1, apellido2, dni FROM personas"):
            if p["dni"] and p["dni"][:8] in t:
                return True
            completo = norm(f'{p["nombre"]} {p["apellido1"]}').strip()
            if len(completo.split()) >= 2 and completo in t:
                return True
        return False

    # ------------------------------------------------------------ 3b: Word / Excel de un desconocido
    def office(self, clave):
        r = self.db.execute("SELECT estado FROM correo_preguntas WHERE clave = ?", (clave,)).fetchone()
        if not r:
            return None
        return {"aceptado": "aceptado", "rechazado": "rechazado", "marca_quitada": "rechazado"}.get(r[0], "pendiente")

    def pedir_office(self, clave, datos):
        tipos = sorted({"Word" if n.lower().endswith(".docx") else "Excel" if n.lower().endswith(".xlsx") else "fotos"
                        for n in datos["archivos"]})
        msg = (f"Recibido correo con {'/'.join(t for t in tipos if t != 'fotos')}{' y fotos' if 'fotos' in tipos else ''} "
               f"de: {datos['remitente']} · «{datos['asunto']}» ({len(datos['archivos'])} adjunto(s), sin abrir). ¿Aceptar como apto?")
        self.ctx.notificar("correo_office", msg, None, None, {"clave": clave})
        nid = self.db.execute("SELECT MAX(id) FROM notificaciones").fetchone()[0]
        self.db.execute("INSERT OR REPLACE INTO correo_preguntas(clave, datos, estado, noti_id, fecha) VALUES(?, ?, 'pendiente', ?, ?)",
                        (clave, json.dumps(datos, ensure_ascii=False), nid, ahora()))
        self.db.commit()

    def contestar_office(self, nid, respuesta):
        """Botones de la campanita: 'si', 'no' o 'bloquear'."""
        r = self.db.execute("SELECT clave, datos FROM correo_preguntas WHERE noti_id = ?", (nid,)).fetchone()
        if not r:
            raise ValueError("Esa pregunta ya no está pendiente.")
        if respuesta == "si":
            estado = "aceptado"
        else:
            estado = "rechazado"
            if respuesta == "bloquear":
                email = json.loads(r["datos"]).get("email")
                if email:
                    self.db.execute("INSERT OR REPLACE INTO remitentes VALUES(?, 'bloqueado', ?)", (email, ahora()))
        self.db.execute("UPDATE correo_preguntas SET estado = ? WHERE clave = ?", (estado, r["clave"]))
        self.db.commit()
        self.ctx.visto(nid)
        return {"estado": estado}

    def quitar_marca(self):
        out = []
        for r in self.db.execute("SELECT clave, datos FROM correo_preguntas WHERE estado = 'rechazado'"):
            out.append({"clave": r["clave"], "uid": json.loads(r["datos"])["uid"]})
        return out

    def marca_quitada(self, clave):
        self.db.execute("UPDATE correo_preguntas SET estado = 'marca_quitada' WHERE clave = ?", (clave,))
        self.db.commit()

    # ------------------------------------------------------------ sin documentos (remitente conocido)
    def aviso_sin_docs(self, nombre, email, clave):
        self.ctx.notificar("correo", f"Recibido correo de {nombre} ({email}) sin documentos. Se ha quedado en la bandeja de entrada.",
                           None, None, {"clave": clave})

    # ------------------------------------------------------------ lotes que vienen de un correo
    def registrar(self, lote, remitente, message_id, carpeta, regla):
        self.db.execute("INSERT OR REPLACE INTO correo_lotes(lote_id, remitente, message_id, carpeta, regla, estado, fecha) "
                        "VALUES(?, ?, ?, ?, ?, 'activo', ?)", (lote, remitente, message_id, carpeta, regla, ahora()))
        self.db.commit()

    def revisar_3c(self):
        """Lotes de solo PDF de un desconocido ya terminados: si nada se relaciona con lo registrado, los documentos
        salen del programa y el correo se marca para volver a la entrada (lo hace la siguiente revisión del correo)."""
        quitados = []
        for r in self.db.execute("SELECT lote_id FROM correo_lotes WHERE regla = '3c' AND estado = 'activo'").fetchall():
            lote = r[0]
            docs = self.a.documentos("lote_id = ?", (lote,))
            if not docs or any(d["estado"] in ("en_proceso",) for d in docs):
                continue
            if self.db.execute("SELECT 1 FROM lote_contexto WHERE lote_id = ? AND estado = 'hecho'", (lote,)).fetchone() is None and \
                    any(d["estado"] == "espera_emparejar" for d in docs):
                continue                              # el contexto todavía no ha mirado el lote
            relacion = False
            for d in docs:
                datos = d["datos"] or {}
                if d["estado"] == "guardado" or (datos.get("ia_propuesta") or {}).get("expediente_id"):
                    relacion = True
                if datos.get("personas") and any(self._persona_registrada(p) for p in datos["personas"]):
                    relacion = True
            if relacion:
                self.db.execute("UPDATE correo_lotes SET estado = 'cerrado' WHERE lote_id = ?", (lote,))
                continue
            for d in docs:
                for k in ("ruta_original", "ruta_trabajo"):
                    try:
                        if d.get(k) and Path(d[k]).is_file():
                            Path(d[k]).unlink()       # copias del adjunto: el original sigue en el correo
                    except OSError:
                        pass
                self.a.actualizar(d["id"], estado="descartado", motivo="Correo sin relación con lo registrado: devuelto a la bandeja de entrada")
            self.db.execute("UPDATE correo_lotes SET estado = 'devolver' WHERE lote_id = ?", (lote,))
            self.a.evento(f"Correo de un remitente desconocido sin relación con nada registrado: {len(docs)} documento(s) quitados; "
                          "el correo vuelve a la bandeja de entrada sin la etiqueta.", lote_id=lote, nivel="info")
            quitados.append(lote)
        self.db.commit()
        return quitados

    def _persona_registrada(self, p):
        dni = (p.get("dni") or "")[:8]
        for r in self.db.execute("SELECT dni, nombre, apellido1 FROM personas"):
            if dni and r["dni"] and r["dni"][:8] == dni:
                return True
            if norm(f'{r["nombre"]} {r["apellido1"]}') == norm(f'{p.get("nombre") or ""} {p.get("apellido1") or ""}'):
                return True
        return False

    def devoluciones(self):
        return [{"id": r[0], "message_id": r[1], "carpeta": r[2]}
                for r in self.db.execute("SELECT lote_id, message_id, carpeta FROM correo_lotes WHERE estado = 'devolver'")]

    def devuelto(self, lote):
        self.db.execute("UPDATE correo_lotes SET estado = 'devuelto' WHERE lote_id = ?", (lote,))
        self.db.commit()
