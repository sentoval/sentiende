# -*- coding: utf-8 -*-
"""Recibir por correo (v1.1). Lee un buzón IMAP y recoge los adjuntos admitidos.

Reglas de seguridad (decididas con Joan):
- Nunca se envía ni se borra ningún correo. Los mensajes se leen con BODY.PEEK (no se marcan como
  leídos) y, si el servidor lo permite, se les pone la etiqueta «SeFinancia». Además se guarda un registro local.
- 3.2 (Joan, 17/11/2026): los correos «aptos» ya procesados se MUEVEN a la carpeta «procesadosMMAA» del buzón,
  solo con MOVE o con UIDPLUS (UID EXPUNGE de ese único correo). Si el servidor no tiene ninguna de las dos
  cosas, no se mueve: solo se marca. Nunca un EXPUNGE general (borraría otros correos marcados para borrar).
- Reglas de «apto» (con `politica`): espera de 1 minuto; remitente conocido con adjuntos → apto (sin adjuntos:
  aviso); desconocido sin adjuntos → «No_Apto_SeFina»; solo fotos → apto si se reconocen (OCR ≥ 50 % o el
  nombre del archivo dice qué es); con Word/Excel y sin PDF → se pregunta en la campanita (sin abrirlos);
  con algún PDF → apto (si es solo PDF y luego nada se relaciona con lo registrado, vuelve a INBOX).
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
NO_APTO = "No_Apto_SeFina"
ESPERA_SEGUNDOS = 60
IMAGENES = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".heic", ".bmp", ".webp"}
OFFICE = {".docx", ".xlsx"}
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
        clave = desproteger(a["clave"])
        google = any(x in (a["servidor"] or "").lower() for x in ("gmail", "googlemail", "google"))
        if google:
            clave = clave.replace(" ", "")      # la contraseña de aplicación se muestra como «abcd efgh ijkl mnop»
        try:
            im.login(a["usuario"], clave)
        except imaplib.IMAP4.error as e:
            detalle = e.args[0].decode(errors="ignore") if isinstance(e.args[0], bytes) else str(e)
            pista = ""
            if google:
                pista = (" · Gmail no deja entrar con la contraseña normal de la cuenta: hay que activar la verificación en dos pasos y crear "
                         "una «contraseña de aplicación» (myaccount.google.com/apppasswords). Pega aquí esos 16 caracteres y como usuario la dirección completa.")
            elif "AUTHENTICATIONFAILED" in detalle.upper():
                pista = " · Revisa el usuario (normalmente la dirección completa) y si tu proveedor pide una contraseña de aplicación."
            raise ErrorCorreo(f"El servidor no acepta el usuario o la contraseña ({detalle}).{pista}")
        # 3.1.2 · las capacidades se vuelven a pedir DESPUÉS de entrar: antes de entrar Gmail no anuncia MOVE ni UIDPLUS,
        # y por eso el programa creía que «el servidor no permite mover» (prueba del 17/11, 21:46)
        try:
            tipo, dat = im.capability()
            if tipo == "OK" and dat and dat[0]:
                im.capabilities = tuple(dat[0].decode(errors="ignore").upper().split())
        except Exception:
            pass
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

    # ------------------------------------------------------------ recoger (3.2: reglas de «apto»)
    def recoger_aptos(self, destino, recibir_lote, politica, ahora=None, esperar=True):
        """Revisa la carpeta de entrada con las reglas de Joan (ver arriba). `politica` decide con lo registrado:
        estado(email) -> ("conocido", nombre) | ("bloqueado", None) | ("desconocido", None);
        imagenes_aptas(rutas) -> bool; office(clave) -> "aceptado" | "rechazado" | None;
        pedir_office(clave, datos); aviso_sin_docs(nombre, email, clave); registrar(lote, remitente, message_id, carpeta, regla);
        devoluciones() -> [{"id", "message_id", "carpeta"}]; devuelto(id); quitar_marca() -> [{"clave", "uid"}]; marca_quitada(clave).
        recibir_lote(rutas, descripcion) -> id del lote."""
        a = self.ajustes(con_clave=True)
        vistos = set(json.loads(self.ruta_vistos.read_text(encoding="utf-8"))) if self.ruta_vistos.exists() else set()
        ahora = ahora or datetime.datetime.now(datetime.timezone.utc)
        im = self._conectar(a)
        res = {"correos": 0, "adjuntos": 0, "ignorados": [], "lotes": [], "no_aptos": 0, "esperando": 0,
               "preguntas": 0, "sin_docs": 0, "movidos": 0, "sin_mover": 0, "devueltos": 0, "bloqueados": 0}
        caps = {c.upper() if isinstance(c, str) else c.decode().upper() for c in (getattr(im, "capabilities", ()) or ())}
        puede_mover = "MOVE" in caps or "UIDPLUS" in caps
        entrada = a["carpeta"] or "INBOX"
        try:
            # 0. correos de la regla 3c que no se relacionaron con nada: vuelven a la entrada sin la etiqueta
            for d in politica.devoluciones():
                if self._devolver(im, d["message_id"], d["carpeta"], entrada, puede_mover, caps):
                    res["devueltos"] += 1
                if d["message_id"]:
                    vistos.add(f"mid|{d['message_id']}")          # devuelto: no se vuelve a recoger
                politica.devuelto(d["id"])
            tipo, datos = im.select(_carpeta(entrada), readonly=False)
            if tipo != "OK":
                raise ErrorCorreo(f"No existe la carpeta «{entrada}» en el buzón.")
            permanentes = " ".join(x.decode(errors="ignore") for x in (im.untagged_responses.get("PERMANENTFLAGS") or []))
            con_marca = "\\*" in permanentes or MARCA in permanentes
            uidval = (im.untagged_responses.get("UIDVALIDITY") or [b"0"])[0].decode()
            # 0b. Word/Excel que dijiste que no: se les quita la etiqueta y se olvidan
            for q in politica.quitar_marca():
                _etiquetar(im, str(q["uid"]), "-", MARCA, caps, con_marca)
                politica.marca_quitada(q["clave"])
            desde = _fecha_imap((ahora - datetime.timedelta(days=int(a["dias"]))).date())
            tipo, ids = im.uid("SEARCH", None, "SINCE", desde)
            carpeta_ok = f"procesados{ahora.astimezone():%m%y}"
            creada = False
            for uid in (ids[0].split() if ids and ids[0] else []):
                u = uid.decode()
                clave = f"{a['usuario']}|{entrada}|{uidval}|{u}"
                if clave in vistos:
                    continue
                tipo, partes = im.uid("FETCH", uid, "(INTERNALDATE BODY.PEEK[])")       # PEEK: no lo marca como leído
                cab = next((p[0] for p in partes if isinstance(p, tuple)), b"")
                crudo = next((p[1] for p in partes if isinstance(p, tuple)), None)
                if not crudo:
                    continue
                llegada = _internaldate(cab)
                if esperar and llegada and (ahora - llegada).total_seconds() < ESPERA_SEGUNDOS:   # solo en la revisión automática
                    res["esperando"] += 1           # aún no ha pasado 1 minuto: se mira en la siguiente vuelta
                    continue
                msg = email.message_from_bytes(crudo)
                de = _texto(msg.get("From", ""))
                asunto = _texto(msg.get("Subject", "")) or "(sin asunto)"
                email_de = (re.search(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", de) or [de])[0].lower()
                message_id = (msg.get("Message-ID") or "").strip()
                if message_id and f"mid|{message_id}" in vistos:
                    vistos.add(clave); continue
                adjuntos, ignorados = _adjuntos(msg)
                res["ignorados"] += [f"{n} (de «{asunto}»)" for n in ignorados]
                exts = {Path(n).suffix.lower() for n, _ in adjuntos}
                estado, nombre = politica.estado(email_de)
                marcar = lambda flag, signo="+": _etiquetar(im, u, signo, flag, caps, con_marca)
                if estado == "bloqueado":
                    res["bloqueados"] += 1; vistos.add(clave); continue
                regla = None
                if estado == "conocido":
                    if not adjuntos:
                        politica.aviso_sin_docs(nombre, email_de, clave)          # se queda en la entrada
                        res["sin_docs"] += 1; vistos.add(clave); continue
                    regla = "1"
                elif not adjuntos:                                               # 2
                    marcar(NO_APTO); res["no_aptos"] += 1; vistos.add(clave); continue
                elif ".pdf" in exts:
                    regla = "3c" if exts == {".pdf"} else "3d"
                elif exts & OFFICE:                                              # 3b: se pregunta sin abrir nada
                    decision = politica.office(clave)
                    if decision == "aceptado":
                        regla = "3b"
                    elif decision == "rechazado":
                        vistos.add(clave); continue
                    else:
                        if decision is None:
                            marcar(MARCA)
                            politica.pedir_office(clave, {"uid": u, "remitente": de, "email": email_de, "asunto": asunto,
                                                          "archivos": [n for n, _ in adjuntos]})
                            res["preguntas"] += 1
                        continue                     # sigue en la entrada hasta que contestes
                else:                                                            # 3a: solo fotos
                    tmp = Path(destino) / f".comprobar_{u}"
                    tmp.mkdir(parents=True, exist_ok=True)
                    rutas_tmp = []
                    for n, cuerpo in adjuntos:
                        f = tmp / n; f.write_bytes(cuerpo); rutas_tmp.append(f)
                    try:
                        apto = politica.imagenes_aptas(rutas_tmp)
                    finally:
                        for f in rutas_tmp:
                            f.unlink(missing_ok=True)
                        try:
                            tmp.rmdir()
                        except OSError:
                            pass
                    if not apto:
                        marcar(NO_APTO); res["no_aptos"] += 1; vistos.add(clave); continue
                    regla = "3a"
                # apto: se recogen los adjuntos, se marca y se mueve a «procesadosMMAA»
                rutas = []
                for n, cuerpo in adjuntos:
                    f = libre(Path(destino) / n)
                    f.write_bytes(cuerpo)
                    rutas.append(f)
                lote = recibir_lote(rutas, f"correo «{asunto}» de {de}")
                res["lotes"].append(lote); res["adjuntos"] += len(rutas); res["correos"] += 1
                marcar(MARCA)
                carpeta_final = entrada
                if puede_mover:
                    if not creada:
                        try:
                            im.create(_carpeta(carpeta_ok))
                        except imaplib.IMAP4.error:
                            pass                     # ya existía
                        creada = True
                    if _mover(im, u, carpeta_ok, caps):
                        carpeta_final = carpeta_ok; res["movidos"] += 1
                    else:
                        res["sin_mover"] += 1
                else:
                    res["sin_mover"] += 1
                politica.registrar(lote, email_de, message_id, carpeta_final, regla)
                if hasattr(politica, "aviso_procesado"):
                    politica.aviso_procesado(nombre or _nombre_de(de) or email_de, email_de, asunto, _cuerpo(msg), lote, carpeta_final)
                vistos.add(clave)
        finally:
            _cerrar(im)
            self.ruta_vistos.write_text(json.dumps(sorted(vistos)), encoding="utf-8")
        res["puede_mover"] = puede_mover
        return res

    def _devolver(self, im, message_id, carpeta, entrada, puede_mover, caps):
        """Regla 3c: el correo vuelve de «procesadosMMAA» a la entrada y se le quita la etiqueta."""
        if not message_id:
            return False
        tipo, _ = im.select(_carpeta(carpeta), readonly=False)
        if tipo != "OK":
            return False
        tipo, ids = im.uid("SEARCH", None, "HEADER", "Message-ID", message_id)
        hecho = False
        for uid in (ids[0].split() if ids and ids[0] else []):
            u = uid.decode()
            _etiquetar(im, u, "-", MARCA, caps, True)
            if carpeta != entrada and puede_mover:
                hecho = _mover(im, u, entrada, caps) or hecho
            else:
                hecho = True
        return hecho

    # ------------------------------------------------------------ recoger (hasta la 3.1: todo lo admitido)
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


def _adjuntos(msg):
    """[(nombre, bytes)] admitidos y [nombres] ignorados (macros, ejecutables, comprimidos…). Sin los logotipos de la firma."""
    buenos, malos = [], []
    for parte in msg.walk():
        nombre = parte.get_filename()
        if not nombre or parte.get_content_maintype() == "multipart":
            continue
        nombre = Path(_texto(nombre).replace("/", "_").replace("\\", "_")).name
        cuerpo = parte.get_payload(decode=True) or b""
        ext = Path(nombre).suffix.lower()
        if PELIGROSOS.search(nombre) or ext not in PERMITIDOS:
            malos.append(nombre)
            continue
        if parte.get("Content-ID") and ext in (".png", ".jpg", ".jpeg") and len(cuerpo) < 40_000:
            continue
        buenos.append((nombre, cuerpo))
    return buenos, malos


def _cuerpo(msg, maximo=600):
    """Texto del cuerpo del correo (texto plano; si solo hay HTML, sin etiquetas), recortado para el aviso."""
    texto = ""
    for parte in msg.walk():
        if parte.get_filename() or parte.get_content_maintype() != "text":
            continue
        try:
            t = parte.get_payload(decode=True).decode(parte.get_content_charset() or "utf-8", errors="replace")
        except Exception:
            continue
        if parte.get_content_subtype() == "plain":
            texto = t
            break
        if not texto:
            texto = re.sub(r"(?is)<(script|style).*?</\1>|<[^>]+>", " ", t)
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto[:maximo] + ("…" if len(texto) > maximo else "")


def _nombre_de(de):
    """«Pilar Sanz <pilar@x.es>» → «Pilar Sanz»."""
    n = re.sub(r"<[^>]*>", "", de or "").strip().strip('"')
    return n if n and "@" not in n else ""


def _store(im, uid, signo, flag):
    try:
        im.uid("STORE", uid, f"{signo}FLAGS", f"({flag})")
        return True
    except imaplib.IMAP4.error:
        return False


def _etiquetar(im, uid, signo, etiqueta, caps, con_marca=True):
    """Pone (+) o quita (-) la etiqueta. En Gmail las «palabras clave» IMAP no se ven en la web: allí se usa una
    etiqueta de Gmail de verdad (X-GM-LABELS), que se crea sola. En el resto, la palabra clave si el servidor la admite."""
    hecho = False
    if "X-GM-EXT-1" in caps:
        try:
            tipo, _ = im.uid("STORE", uid, f"{signo}X-GM-LABELS", f'("{etiqueta}")')
            hecho = tipo == "OK"
        except imaplib.IMAP4.error:
            pass
    if con_marca:
        hecho = _store(im, uid, signo, etiqueta) or hecho
    return hecho


def _mover(im, uid, carpeta, caps):
    """Mueve UN correo sin tocar los demás: MOVE si existe; si no, COPY + \\Deleted + UID EXPUNGE de ese uid (UIDPLUS)."""
    try:
        if "MOVE" in caps:
            tipo, _ = im.uid("MOVE", uid, _carpeta(carpeta))
            return tipo == "OK"
        if "UIDPLUS" in caps:
            tipo, _ = im.uid("COPY", uid, _carpeta(carpeta))
            if tipo != "OK":
                return False
            im.uid("STORE", uid, "+FLAGS", "(\\Deleted)")
            tipo, _ = im.uid("EXPUNGE", uid)          # solo este uid
            return tipo == "OK"
    except imaplib.IMAP4.error:
        return False
    return False


def _internaldate(cab):
    try:
        t = imaplib.Internaldate2tuple(cab if isinstance(cab, bytes) else str(cab).encode())
        if t:
            import time
            return datetime.datetime.fromtimestamp(time.mktime(t), datetime.timezone.utc)
    except Exception:
        pass
    return None


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
