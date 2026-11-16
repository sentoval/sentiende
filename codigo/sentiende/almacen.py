# -*- coding: utf-8 -*-
"""Almacén local (M-17): una base SQLite en Datos\\sentiende.db.
Guarda lotes, documentos y su fase, texto leído por página (caché, M-61), personas,
expedientes, eventos (historial y motor de proceso) y correcciones."""
import json, sqlite3, datetime
from pathlib import Path

ESQUEMA = """
CREATE TABLE IF NOT EXISTS lotes(
  id INTEGER PRIMARY KEY, creado TEXT, origen TEXT, estado TEXT DEFAULT 'en_proceso');
CREATE TABLE IF NOT EXISTS documentos(
  id INTEGER PRIMARY KEY, lote_id INTEGER REFERENCES lotes(id),
  nombre_recibido TEXT, ruta_original TEXT, huella TEXT, extension TEXT, paginas INTEGER,
  fase INTEGER DEFAULT 0, estado TEXT DEFAULT 'en_proceso', motivo TEXT,
  tipo TEXT, confianza REAL, alternativas TEXT, indicios TEXT, entidad TEXT, entidad_por TEXT,
  datos TEXT, rotaciones TEXT, ruta_trabajo TEXT,
  expediente_id INTEGER, persona_id INTEGER, de_expediente INTEGER DEFAULT 0, privado INTEGER DEFAULT 0,
  nombre_final TEXT, ruta_final TEXT, ruta_original_final TEXT, duplicado_de INTEGER,
  padre_id INTEGER, paginas_sel TEXT, unido_en INTEGER,
  creado TEXT, actualizado TEXT);
CREATE INDEX IF NOT EXISTS idx_doc_huella ON documentos(huella);
CREATE TABLE IF NOT EXISTS textos(
  clave TEXT PRIMARY KEY, texto TEXT, origen TEXT, confianza REAL, rotacion INTEGER);
CREATE TABLE IF NOT EXISTS personas(
  id INTEGER PRIMARY KEY, nombre TEXT, apellido1 TEXT, apellido2 TEXT, dni TEXT UNIQUE,
  es_empresa INTEGER DEFAULT 0, alias TEXT DEFAULT '[]', creado TEXT);
CREATE TABLE IF NOT EXISTS expedientes(
  id INTEGER PRIMARY KEY, nombre TEXT, finalidad TEXT, carpeta TEXT, estado TEXT DEFAULT 'abierto',
  creado TEXT);
CREATE TABLE IF NOT EXISTS expediente_personas(
  expediente_id INTEGER, persona_id INTEGER, papel TEXT, orden INTEGER,
  PRIMARY KEY(expediente_id, persona_id, papel));
CREATE TABLE IF NOT EXISTS textos_documento(
  documento_id INTEGER, n INTEGER, texto TEXT, origen TEXT, confianza REAL,
  PRIMARY KEY(documento_id, n));
CREATE TABLE IF NOT EXISTS avisos_cliente(
  expediente_id INTEGER, mensaje TEXT, activo INTEGER DEFAULT 1, creado TEXT, resuelto TEXT,
  PRIMARY KEY(expediente_id, mensaje));
CREATE TABLE IF NOT EXISTS terceros_lote(
  lote_id INTEGER, nombre TEXT, PRIMARY KEY(lote_id, nombre));
CREATE TABLE IF NOT EXISTS eventos(
  id INTEGER PRIMARY KEY, fecha TEXT, documento_id INTEGER, lote_id INTEGER, fase INTEGER,
  nivel TEXT, mensaje TEXT);
"""

JSON_CAMPOS = {"alternativas", "indicios", "datos", "rotaciones", "paginas_sel"}

def ahora():
    return datetime.datetime.now().isoformat(timespec="seconds")

class Almacen:
    def __init__(self, ruta):
        Path(ruta).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(ruta, check_same_thread=False)   # la ventana y el motor usan hilos distintos (con cerrojo)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(ESQUEMA)
        cols = {r["name"] for r in self.db.execute("PRAGMA table_info(documentos)")}
        for c in ("padre_id INTEGER", "paginas_sel TEXT", "unido_en INTEGER"):      # bases de datos de versiones anteriores
            if c.split()[0] not in cols:
                self.db.execute(f"ALTER TABLE documentos ADD COLUMN {c}")
        self.db.execute("PRAGMA foreign_keys = ON")

    # ---------------- lotes y documentos
    def nuevo_lote(self, origen):
        c = self.db.execute("INSERT INTO lotes(creado, origen) VALUES(?, ?)", (ahora(), origen))
        self.db.commit()
        return c.lastrowid

    def nuevo_documento(self, lote_id, nombre, ruta, huella, extension, padre_id=None):
        c = self.db.execute("INSERT INTO documentos(lote_id, nombre_recibido, ruta_original, huella, extension, padre_id, creado, actualizado) "
                            "VALUES(?, ?, ?, ?, ?, ?, ?, ?)", (lote_id, nombre, str(ruta), huella, extension, padre_id, ahora(), ahora()))
        self.db.commit()
        return c.lastrowid

    def actualizar(self, doc_id, **campos):
        for k in JSON_CAMPOS & campos.keys():
            campos[k] = json.dumps(campos[k], ensure_ascii=False)
        campos["actualizado"] = ahora()
        sets = ", ".join(f"{k} = ?" for k in campos)
        self.db.execute(f"UPDATE documentos SET {sets} WHERE id = ?", (*campos.values(), doc_id))
        self.db.commit()

    def documento(self, doc_id):
        r = self.db.execute("SELECT * FROM documentos WHERE id = ?", (doc_id,)).fetchone()
        if not r:
            return None
        d = dict(r)
        for k in JSON_CAMPOS:
            d[k] = json.loads(d[k]) if d[k] else None
        d["modelo"] = (d.get("datos") or {}).get("modelo") if isinstance(d.get("datos"), dict) else None   # para la etiqueta «(131) …»
        return d

    def documentos(self, where="1", params=()):
        return [self.documento(r["id"]) for r in self.db.execute(f"SELECT id FROM documentos WHERE {where} ORDER BY id", params)]

    def ya_procesado(self, huella):
        """Duplicado exacto (M-61): mismo archivo ya recibido y no descartado."""
        r = self.db.execute("SELECT id FROM documentos WHERE huella = ? AND estado NOT IN ('error', 'duplicado') ORDER BY id LIMIT 1", (huella,)).fetchone()
        return r["id"] if r else None

    # ---------------- caché de texto por página (M-61)
    def texto_cache(self, clave):
        r = self.db.execute("SELECT * FROM textos WHERE clave = ?", (clave,)).fetchone()
        return dict(r) if r else None

    def guardar_texto(self, clave, texto, origen, confianza, rotacion):
        self.db.execute("INSERT OR REPLACE INTO textos VALUES(?, ?, ?, ?, ?)", (clave, texto, origen, confianza, rotacion))
        self.db.commit()

    # ---------------- texto permanente de cada documento guardado (M-68)
    def fijar_textos(self, doc):
        """Copia el texto de la memoria temporal al documento: vaciar la memoria no lo borra."""
        if self.textos_de(doc["id"]):
            return          # ya fijados (p. ej. documento rescatado del Limbo): no se pisan
        sel = doc.get("paginas_sel") or list(range(1, (doc["paginas"] or 1) + 1))
        for pos, n in enumerate(sel, 1):
            c = self.texto_cache(f'{doc["huella"]}:{n}')
            if c:
                self.db.execute("INSERT OR REPLACE INTO textos_documento VALUES(?, ?, ?, ?, ?)", (doc["id"], pos, c["texto"], c["origen"], c["confianza"]))
        self.db.commit()

    def textos_de(self, doc_id):
        return {r["n"]: dict(r) for r in self.db.execute("SELECT * FROM textos_documento WHERE documento_id = ? ORDER BY n", (doc_id,))}

    # ---------------- personas y expedientes
    def persona_por_dni(self, dni):
        r = self.db.execute("SELECT * FROM personas WHERE dni = ?", (dni,)).fetchone()
        return dict(r) if r else None

    def persona(self, pid):
        r = self.db.execute("SELECT * FROM personas WHERE id = ?", (pid,)).fetchone()
        return dict(r) if r else None

    def nueva_persona(self, nombre, apellido1="", apellido2="", dni=None, es_empresa=False):
        c = self.db.execute("INSERT INTO personas(nombre, apellido1, apellido2, dni, es_empresa, creado) VALUES(?, ?, ?, ?, ?, ?)",
                            (nombre, apellido1, apellido2, dni, int(es_empresa), ahora()))
        self.db.commit()
        return c.lastrowid

    def nuevo_expediente(self, nombre, finalidad, carpeta):
        c = self.db.execute("INSERT INTO expedientes(nombre, finalidad, carpeta, creado) VALUES(?, ?, ?, ?)", (nombre, finalidad, carpeta, ahora()))
        self.db.commit()
        return c.lastrowid

    def expediente(self, eid):
        r = self.db.execute("SELECT * FROM expedientes WHERE id = ?", (eid,)).fetchone()
        return dict(r) if r else None

    def anadir_persona(self, eid, pid, papel):
        orden = self.db.execute("SELECT COUNT(*) FROM expediente_personas WHERE expediente_id = ?", (eid,)).fetchone()[0]
        self.db.execute("INSERT OR IGNORE INTO expediente_personas VALUES(?, ?, ?, ?)", (eid, pid, papel, orden))
        self.db.commit()

    def personas_de(self, eid):
        return [dict(r) for r in self.db.execute(
            "SELECT p.*, ep.papel, ep.orden FROM expediente_personas ep JOIN personas p ON p.id = ep.persona_id "
            "WHERE ep.expediente_id = ? ORDER BY ep.orden", (eid,))]

    # ---------------- Avisos Cliente: estado actual, sin repetir (M-24, M-61)
    def poner_avisos_cliente(self, eid, mensajes):
        """Deja activos exactamente estos avisos del expediente; los demás quedan resueltos."""
        actuales = {r["mensaje"] for r in self.db.execute("SELECT mensaje FROM avisos_cliente WHERE expediente_id = ? AND activo = 1", (eid,))}
        for m in actuales - set(mensajes):
            self.db.execute("UPDATE avisos_cliente SET activo = 0, resuelto = ? WHERE expediente_id = ? AND mensaje = ?", (ahora(), eid, m))
        for m in set(mensajes) - actuales:
            self.db.execute("INSERT OR REPLACE INTO avisos_cliente(expediente_id, mensaje, activo, creado) VALUES(?, ?, 1, ?)", (eid, m, ahora()))
        self.db.commit()

    def avisos_cliente(self, eid=None):
        q = "SELECT * FROM avisos_cliente WHERE activo = 1" + (" AND expediente_id = ?" if eid else "")
        return [dict(r) for r in self.db.execute(q + " ORDER BY creado", (eid,) if eid else ())]

    # ---------------- eventos
    def evento(self, mensaje, documento_id=None, lote_id=None, fase=None, nivel="info"):
        self.db.execute("INSERT INTO eventos(fecha, documento_id, lote_id, fase, nivel, mensaje) VALUES(?, ?, ?, ?, ?, ?)",
                        (ahora(), documento_id, lote_id, fase, nivel, mensaje))
        self.db.commit()

    def eventos(self, documento_id=None, nivel=None):
        q, p = "SELECT * FROM eventos WHERE 1", []
        if documento_id is not None:
            q += " AND documento_id = ?"; p.append(documento_id)
        if nivel:
            q += " AND nivel = ?"; p.append(nivel)
        return [dict(r) for r in self.db.execute(q + " ORDER BY id", p)]
