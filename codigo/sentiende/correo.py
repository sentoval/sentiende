# -*- coding: utf-8 -*-
"""Recibir por correo (v1.1). Lee un buzón IMAP y recoge los adjuntos admitidos.

Reglas de seguridad (decididas con Joan):
- Solo lectura + marca: nunca se envía, se borra ni se mueve ningún correo. Los mensajes se
  leen con BODY.PEEK (no se marcan como leídos) y, si el servidor lo permite, se les pone la
  etiqueta «SeFinancia» para no recogerlos dos veces. Además se guarda un registro local.
- Solo entran los tipos admitidos (PDF, fotos, Word .docx, Excel .xlsx). Nada con macros
  (.docm, .xlsm…) ni ejecutables: se ignoran y se apuntan.
- La contraseña se guarda cifrada con la cuenta de Windows (DPAPI): solo este usuario de este
  equipo puede leerla."""
import base64, datetime, email, imaplib, json, re, ssl
from email.header import decode_header, make_header
from pathlib import Path
from .recibir import PERMITIDOS
from .carpetas import libre

MARCA = "SeFinancia"
PREDEFINIDOS = {
    "gmail": {"nombre": "Gmail", "servidor": "imap.gmail.com", "puerto": 993,
              "nota": "Gmail pide una «contraseña de aplicación» (Cuenta de Google → Seguridad → Verificación en dos pasos → Contraseñas de aplicaciones)."},
    "outlook": {"nombre": "Outlook / Hotmail / Microsoft 365", "servidor": "outlook.office365.com", "puerto": 993,
                "nota": "Microsoft solo admite este acceso si la cuenta o la empresa tiene activado IMAP con contraseña; si no conecta, hay que pedirlo al administrador o usar otra cuenta."},
    "yahoo": {"nombre": "Yahoo", "servidor": "imap.mail.yahoo.com", "puerto": 993, "nota": "Yahoo pide una «contraseña de aplicación»."},
    "otro": {"nombre": "Otro (IMAP)", "servidor": "", "puerto": 993, "nota": "Los datos IMAP los da tu proveedor de correo."},
}
POR_DEFECTO = {"activo": False, "proveedor": "otro", "servidor": "", "puerto": 993, "usuario": "", "clave": "",
               "carpeta": "INBOX", "dias": 15, "remitentes": "", "cada_minutos": 0, "revisar_nuevos": True}
PELIGROSOS = re.compile(r"\.(docm|xlsm|pptm|dotm|xltm|xlam|exe|bat|cmd|com|scr|js|vbs|ps1|msi|jar|lnk|hta|zip|rar|7z)$", re.I)


class ErrorCorreo(Exception):
    pass


# ---------------------------------------------------------------- contraseña protegida
def _dpapi(datos, cifrar):
    import ctypes
    from ctypes import wintypes

    class BLOB(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]
    buf = ctypes.create_string_buffer(datos, len(datos))
    entrada, salida = BLOB(len(datos), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char))), BLOB()
    f = ctypes.windll.crypt32.CryptProtectData if cifrar else ctypes.windll.crypt32.CryptUnprotectData
    if not f(ctypes.byref(entrada), None, None, None, None, 0x1, ctypes.byref(salida)):
        raise ErrorCorreo("No se ha podido proteger la contraseña con la cuenta de Windows.")
    try:
        return ctypes.string_at(salida.pbData, salida.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(salida.pbData)


def proteger(clave):
    if not clave:
        return ""
    try:
        return "dpapi:" + base64.b64encode(_dpapi(clave.encode("utf-8"), True)).decode()
    except (AttributeError, OSError):          # fuera de Windows (pruebas): solo se oculta
        return "b64:" + base64.b64encode(clave.encode("utf-8")).decode()


def desproteger(guardada):
    if not guardada:
        return ""
    tipo, _, dato = guardada.partition(":")
    raw = base64.b64decode(dato)
    return (_dpapi(raw, False) if tipo == "dpapi" else raw).decode("utf-8")


# ---------------------------------------------------------------- ajustes
class Correo:
    def __init__(self, carpeta_datos):
        self.ruta = Path(carpeta_datos) / "correo.json"
        self.ruta_vistos = Path(carpeta_datos) / "correo_recogidos.json"

    def ajustes(self, con_clave=False):
        a = dict(POR_DEFECTO)
        if self.ruta.exists():
            a.update(json.loads(self.ruta.read_text(encoding="utf-8")))
        if not con_clave:
            a["hay_clave"] = bool(a.pop("clave", ""))
        return a

    def guardar(self, nuevos):
        a = self.ajustes(con_clave=True)
        for k in ("activo", "proveedor", "servidor", "puerto", "usuario", "carpeta", "dias", "remitentes", "cada_minutos", "revisar_nuevos"):
            if k in nuevos:
                a[k] = nuevos[k]
        if nuevos.get("clave"):
            a["clave"] = proteger(nuevos["clave"])
        a["puerto"] = int(a.get("puerto") or 993)
        a["dias"] = max(1, min(int(a.get("dias") or 15), 365))
        a["cada_minutos"] = max(0, int(a.get("cada_minutos") or 0))
        a["servidor"] = (a.get("servidor") or "").strip()
        a["usuario"] = (a.get("usuario") or "").strip()
        self.ruta.write_text(json.dumps(a, ensure_ascii=False, indent=2), encoding="utf-8")
        return self.ajustes()

    # ------------------------------------------------------------ conexión
    def _conectar(self, a=None):
        a = a or self.ajustes(con_clave=True)
        if not a["servidor"] or not a["usuario"] or not a.get("clave"):
            raise ErrorCorreo("Falta configurar el correo (servidor, usuario y contraseña) en Ajustes.")
        try:
            im = imaplib.IMAP4_SSL(a["servidor"], int(a["puerto"]), ssl_context=ssl.create_default_context(), timeout=30)
        except Exception as e:
            raise ErrorCorreo(f"No se puede conectar con {a['servidor']}: {e}")
        try:
            im.login(a["usuario"], desproteger(a["clave"]))
        except imaplib.IMAP4.error as e:
            raise ErrorCorreo(f"El servidor no acepta el usuario o la contraseña ({e.args[0].decode(errors='ignore') if isinstance(e.args[0], bytes) else e}).")
        return im

    def probar(self, a_prueba=None):
        a = self.ajustes(con_clave=True)
        if a_prueba:
            a.update({k: v for k, v in a_prueba.items() if k != "clave"})
            if a_prueba.get("clave"):
                a["clave"] = proteger(a_prueba["clave"])
        im = self._conectar(a)
        try:
            tipo, datos = im.select(_carpeta(a["carpeta"]), readonly=True)
            if tipo != "OK":
                raise ErrorCorreo(f"No existe la carpeta «{a['carpeta']}» en el buzón.")
            return {"ok": True, "mensajes": int(datos[0])}
        finally:
            _cerrar(im)

    # ------------------------------------------------------------ recoger
    def recoger(self, destino, recibir_lote, decidir=None, cuarentena=None):
        """Descarga los adjuntos admitidos de los correos nuevos.
        recibir_lote(rutas, descripcion) recibe los adjuntos de cada correo (un lote por correo).
        decidir(remitente) -> "ok" | "cuarentena" | "bloqueado": los remitentes nuevos van a «Correo por revisar»
        (cuarentena(rutas, remitente, asunto)) hasta que se aceptan. Devuelve un resumen."""
        a = self.ajustes(con_clave=True)
        vistos = set(json.loads(self.ruta_vistos.read_text(encoding="utf-8"))) if self.ruta_vistos.exists() else set()
        im = self._conectar(a)
        res = {"correos": 0, "adjuntos": 0, "ignorados": [], "lotes": [], "cuarentena": 0, "bloqueados": 0}
        try:
            tipo, datos = im.select(_carpeta(a["carpeta"]), readonly=False)   # escritura solo para la marca
            if tipo != "OK":
                raise ErrorCorreo(f"No existe la carpeta «{a['carpeta']}» en el buzón.")
            permanentes = " ".join(x.decode(errors="ignore") for x in (im.untagged_responses.get("PERMANENTFLAGS") or []))
            con_marca = "\\*" in permanentes or MARCA in permanentes
            desde = _fecha_imap(datetime.date.today() - datetime.timedelta(days=int(a["dias"])))
            crit = ["SINCE", desde] + (["UNKEYWORD", MARCA] if con_marca else [])
            tipo, ids = im.uid("SEARCH", None, *crit)
            uidval = (im.untagged_responses.get("UIDVALIDITY") or [b"0"])[0].decode()
            remitentes = [r.strip().lower() for r in (a.get("remitentes") or "").replace(";", ",").split(",") if r.strip()]
            for uid in (ids[0].split() if ids and ids[0] else []):
                clave = f"{a['usuario']}|{a['carpeta']}|{uidval}|{uid.decode()}"
                if clave in vistos:
                    continue
                tipo, partes = im.uid("FETCH", uid, "(BODY.PEEK[])")       # PEEK: no lo marca como leído
                crudo = next((p[1] for p in partes if isinstance(p, tuple)), None)
                if not crudo:
                    continue
                msg = email.message_from_bytes(crudo)
                de = _texto(msg.get("From", ""))
                if remitentes and not any(r in de.lower() for r in remitentes):
                    vistos.add(clave)
                    continue
                asunto = _texto(msg.get("Subject", "")) or "(sin asunto)"
                email_de = (re.search(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", de) or [de])[0].lower()
                decision = decidir(email_de) if decidir and a.get("revisar_nuevos", True) else "ok"
                if decision == "bloqueado":
                    res["bloqueados"] += 1; vistos.add(clave)
                    continue
                rutas = []
                for parte in msg.walk():
                    nombre = parte.get_filename()
                    if not nombre or parte.get_content_maintype() == "multipart":
                        continue
                    nombre = Path(_texto(nombre).replace("/", "_").replace("\\", "_")).name
                    cuerpo = parte.get_payload(decode=True) or b""
                    ext = Path(nombre).suffix.lower()
                    if PELIGROSOS.search(nombre) or ext not in PERMITIDOS:
                        res["ignorados"].append(f"{nombre} (de «{asunto}»)")
                        continue
                    if parte.get("Content-ID") and ext in (".png", ".jpg", ".jpeg") and len(cuerpo) < 40_000:
                        continue          # logotipos de la firma del correo
                    f = libre(Path(destino) / nombre)
                    f.write_bytes(cuerpo)
                    rutas.append(f)
                if rutas and decision == "cuarentena" and cuarentena:
                    cuarentena(rutas, email_de, asunto)
                    res["cuarentena"] += 1
                elif rutas:
                    res["lotes"].append(recibir_lote(rutas, f"correo «{asunto}» de {de}"))
                    res["adjuntos"] += len(rutas)
                res["correos"] += 1
                vistos.add(clave)
                if con_marca:
                    try:
                        im.uid("STORE", uid, "+FLAGS", f"({MARCA})")      # solo la marca: nada de borrar ni mover
                    except imaplib.IMAP4.error:
                        pass
        finally:
            _cerrar(im)
            self.ruta_vistos.write_text(json.dumps(sorted(vistos)), encoding="utf-8")
        return res


def _carpeta(c):
    c = c or "INBOX"
    return f'"{c}"' if " " in c and not c.startswith('"') else c


def _fecha_imap(f):
    meses = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    return f"{f.day:02d}-{meses[f.month - 1]}-{f.year}"


def _texto(v):
    try:
        return str(make_header(decode_header(v or "")))
    except Exception:
        return v or ""


def _cerrar(im):
    try:
        im.logout()          # sin EXPUNGE ni CLOSE: no se aplica ningún borrado
    except Exception:
        pass
