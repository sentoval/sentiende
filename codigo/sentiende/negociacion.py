# -*- coding: utf-8 -*-
"""Negociación de cada expediente (F-17) y marcas de la checklist.

- Notas fechadas de «Negociación banco» (cada nota puede ser de un banco concreto) y
  «Negociación cliente».
- Varios bancos por expediente (se negocia con varios a la vez), cada uno con su estado y sus
  contactos: gestor, director, oficina… (nombre, cargo, teléfonos, correo, oficina, dirección).
- Marcas de la checklist hechas a mano: «Solicitado» o «Sin pedir» (lo «Aportado» lo pone el programa).
- Tarjetas de visita: se detectan por tener poco texto con teléfono o correo y algo de banco o cargo.
  Nunca se guardan solas: el Centro de revisión siempre pregunta."""
import re
from .almacen import ahora

ESQUEMA = """
CREATE TABLE IF NOT EXISTS notas(
  id INTEGER PRIMARY KEY, expediente_id INTEGER, tipo TEXT, banco_id INTEGER, fecha TEXT, texto TEXT);
CREATE TABLE IF NOT EXISTS bancos_expediente(
  id INTEGER PRIMARY KEY, expediente_id INTEGER, entidad TEXT, estado TEXT DEFAULT 'En estudio', creado TEXT);
CREATE TABLE IF NOT EXISTS contactos(
  id INTEGER PRIMARY KEY, banco_id INTEGER, nombre TEXT, cargo TEXT, telefono TEXT, movil TEXT, email TEXT,
  oficina TEXT, direccion TEXT, notas TEXT, documento_id INTEGER, creado TEXT);
CREATE TABLE IF NOT EXISTS checklist_marcas(
  expediente_id INTEGER, clave TEXT, estado TEXT, fecha TEXT, PRIMARY KEY(expediente_id, clave));
"""
ESTADOS_BANCO = ["En estudio", "Documentación enviada", "Oferta recibida", "Aprobado", "Denegado", "Descartado"]
CAMPOS_CONTACTO = ("nombre", "cargo", "telefono", "movil", "email", "oficina", "direccion", "notas")


class ErrorNegociacion(Exception):
    pass


class Negociacion:
    def __init__(self, almacen):
        self.a = almacen
        self.db = almacen.db
        self.db.executescript(ESQUEMA)

    # ------------------------------------------------------------ todo lo de un expediente
    def de_expediente(self, eid):
        bancos = [dict(r) for r in self.db.execute("SELECT * FROM bancos_expediente WHERE expediente_id = ? ORDER BY id", (eid,))]
        for b in bancos:
            b["contactos"] = [dict(r) for r in self.db.execute("SELECT * FROM contactos WHERE banco_id = ? ORDER BY id", (b["id"],))]
        notas = [dict(r) for r in self.db.execute("SELECT * FROM notas WHERE expediente_id = ? ORDER BY fecha DESC, id DESC", (eid,))]
        marcas = {r["clave"]: {"estado": r["estado"], "fecha": r["fecha"]} for r in self.db.execute("SELECT * FROM checklist_marcas WHERE expediente_id = ?", (eid,))}
        return {"bancos": bancos, "notas": notas, "marcas": marcas, "estados_banco": ESTADOS_BANCO}

    # ------------------------------------------------------------ notas
    def nota(self, eid, tipo, texto, banco_id=None):
        texto = (texto or "").strip()
        if tipo not in ("banco", "cliente"):
            raise ErrorNegociacion("Tipo de nota desconocido.")
        if not texto:
            raise ErrorNegociacion("La nota está vacía.")
        c = self.db.execute("INSERT INTO notas(expediente_id, tipo, banco_id, fecha, texto) VALUES(?, ?, ?, ?, ?)",
                            (eid, tipo, banco_id if tipo == "banco" else None, ahora(), texto))
        self.db.commit()
        return c.lastrowid

    # ------------------------------------------------------------ bancos
    def banco(self, eid, entidad, estado=None, bid=None):
        entidad = (entidad or "").strip()
        if bid:
            if estado and estado not in ESTADOS_BANCO:
                raise ErrorNegociacion("Estado desconocido.")
            if entidad:
                self.db.execute("UPDATE bancos_expediente SET entidad = ? WHERE id = ?", (entidad, bid))
            if estado:
                self.db.execute("UPDATE bancos_expediente SET estado = ? WHERE id = ?", (estado, bid))
            self.db.commit()
            return bid
        if not entidad:
            raise ErrorNegociacion("Indica el banco.")
        ya = self.db.execute("SELECT id FROM bancos_expediente WHERE expediente_id = ? AND lower(entidad) = lower(?)", (eid, entidad)).fetchone()
        if ya:
            return ya["id"]
        c = self.db.execute("INSERT INTO bancos_expediente(expediente_id, entidad, creado) VALUES(?, ?, ?)", (eid, entidad, ahora()))
        self.db.commit()
        return c.lastrowid

    # ------------------------------------------------------------ contactos
    def contacto(self, banco_id, datos, cid=None, documento_id=None):
        valores = {k: (datos.get(k) or "").strip() for k in CAMPOS_CONTACTO}
        if not any(valores[k] for k in ("nombre", "telefono", "movil", "email", "oficina")):
            raise ErrorNegociacion("El contacto necesita al menos un nombre, un teléfono, un correo o una oficina.")
        if cid:
            self.db.execute(f"UPDATE contactos SET {', '.join(k + ' = ?' for k in valores)} WHERE id = ?", (*valores.values(), cid))
        else:
            c = self.db.execute(f"INSERT INTO contactos(banco_id, {', '.join(valores)}, documento_id, creado) VALUES(?, {', '.join('?' * len(valores))}, ?, ?)",
                                (banco_id, *valores.values(), documento_id, ahora()))
            cid = c.lastrowid
        self.db.commit()
        return cid

    def quitar_contacto(self, cid):
        self.db.execute("DELETE FROM contactos WHERE id = ?", (cid,))
        self.db.commit()

    # ------------------------------------------------------------ marcas de la checklist
    def marcar(self, eid, clave, estado):
        if estado in (None, "", "ninguna"):
            self.db.execute("DELETE FROM checklist_marcas WHERE expediente_id = ? AND clave = ?", (eid, clave))
        elif estado in ("solicitado", "sin_pedir"):
            self.db.execute("INSERT OR REPLACE INTO checklist_marcas VALUES(?, ?, ?, ?)", (eid, clave, estado, ahora()))
        else:
            raise ErrorNegociacion("Marca desconocida.")
        self.db.commit()


# ---------------------------------------------------------------- tarjetas de visita
TEL = re.compile(r"(?:\+?34[\s.-]?)?\b([6789]\d{2})[\s.-]?(\d{2,3})[\s.-]?(\d{2,3})[\s.-]?(\d{0,3})\b")
MAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
CARGOS = re.compile(r"\b(director[a]?|subdirector[a]?|gestor[a]?|gerente|asesor[a]?|comercial|responsable|banca\s+(?:personal|privada|empresas)|"
                    r"oficina|sucursal|agente|delegad[oa]|apoderad[oa]|interventor[a]?|account\s+manager)\b", re.I)
DIREC = re.compile(r"\b(c/|calle|avda\.?|avenida|av\.|plaza|pza\.?|paseo|ps\.?|carrer|ctra\.?|camino|ronda|gran\s+v[ií]a)\b.*|\b\d{5}\b.*", re.I)
OFICINA = re.compile(r"\b(?:oficina|sucursal|of\.)\s*(?:n[º°o.]*\s*)?(\d{3,4})\b", re.I)


MAIL_OCR = re.compile(r"\b([a-z][\w.+-]{2,})[O0Q©®]([a-z][\w-]+(?:\.[\w-]+)*\.[a-z]{2,4})\b")      # el OCR a veces lee la @ como O


def banco_en_texto(texto, bancos):
    """Busca el nombre (o un alias) de un banco de la base de conocimiento en el texto."""
    bajo = (texto or "").lower()
    for b in bancos or []:
        for n in [b.get("nombre", "")] + list(b.get("alias") or []):
            if len(n) >= 4 and re.search(r"(?<!\w)" + re.escape(n.lower()) + r"(?!\w)", bajo):
                return b["nombre"]
    return None


def parece_tarjeta(texto, entidad=None, n_dni=0, bancos=None):
    """Devuelve los datos de contacto si el texto parece una tarjeta de visita; si no, None.
    Una tarjeta tiene poco texto, un teléfono o un correo, y un cargo o el nombre de un banco."""
    palabras = re.findall(r"\w+", texto or "")
    if not palabras or len(palabras) > 90 or n_dni > 0:
        return None
    tels = ["".join(g for g in m.groups() if g) for m in TEL.finditer(texto)]
    tels = [t for t in dict.fromkeys(tels) if len(t) == 9]
    entidad = entidad or banco_en_texto(texto, bancos)
    mails = MAIL.findall(texto) or [f"{a}@{b}" for a, b in MAIL_OCR.findall(texto)]
    cargo = CARGOS.search(texto)
    if not (tels or mails) or not (cargo or entidad):
        return None
    lineas = [l.strip(" ¦|·-") for l in re.split(r"[\n¦]", texto) if l.strip(" ¦|·-")]
    datos = {"nombre": "", "cargo": "", "telefono": "", "movil": "", "email": mails[0] if mails else "", "oficina": "",
             "direccion": "", "entidad": entidad or ""}
    for t in tels:
        if t[0] in "67" and not datos["movil"]:
            datos["movil"] = t
        elif t[0] in "89" and not datos["telefono"]:
            datos["telefono"] = t
    for l in lineas:
        if not datos["cargo"] and CARGOS.search(l) and not TEL.search(l) and len(l) < 60:
            datos["cargo"] = l
        if not datos["direccion"] and DIREC.search(l) and not MAIL.search(l):
            datos["direccion"] = l
        m = OFICINA.search(l)
        if m and not datos["oficina"]:
            datos["oficina"] = m.group(1)
    # nombre: una línea de 2 a 4 palabras con letras, sin números ni @, que no sea el cargo ni el banco
    for l in lineas:
        w = l.split()
        if 2 <= len(w) <= 4 and not re.search(r"[\d@/]", l) and l != datos["cargo"] and not CARGOS.search(l) \
           and not (entidad and entidad.lower() in l.lower()) and all(x[0].isalpha() for x in w):
            datos["nombre"] = " ".join(x.capitalize() if x.isupper() else x for x in w)
            break
    return datos
