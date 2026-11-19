# -*- coding: utf-8 -*-
"""3.1.3 · «Preparar envío» de la documentación de un expediente (boceto de Joan, 18/11/2026).

Vías (decididas con Joan):
- «correo_sentiende»: el programa ENVÍA el correo con la cuenta configurada en Ajustes › Correo (SMTP), solo cuando Joan
  pulsa el botón, a los destinatarios que él ha marcado. Es la única excepción a «el módulo de correo nunca envía».
  Nunca se borra nada. Se guarda una copia (.eml) en Datos\\Envios.
- «correo_borrador»: prepara un borrador (.eml con «X-Unsent: 1») con los adjuntos y lo abre en el programa de correo
  del equipo (Outlook, Thunderbird…); el envío lo hace Joan desde allí.
- «whatsapp»: WhatsApp no deja adjuntar archivos desde otro programa. Se copian los archivos a una carpeta, se abre la
  carpeta y se abre WhatsApp con el texto (el asunto al principio) para el móvil marcado.
- «carpeta»: los archivos sueltos en una carpeta, con «mensaje.txt» (asunto, texto y destinatarios).
- «zip»: un zip con los archivos y «mensaje.txt».
Todo va a Datos\\Envios\\<carpeta del expediente>\\<fecha>_<vía>. Los originales no se tocan (siempre se copia)."""
import datetime, mimetypes, re, shutil, ssl, zipfile
# smtplib se importa solo al enviar: el SeFinancia.exe de la 3.2.0 (lanzador 2) no lo lleva dentro y el programa no abría
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from pathlib import Path
from .carpetas import libre

VIAS = ("correo_sentiende", "correo_borrador", "whatsapp", "carpeta", "zip")
MAX_CORREO = 24 * 1024 * 1024          # Gmail y Outlook rechazan más de ~25 MB
SMTP = {"gmail": ("smtp.gmail.com", 465), "outlook": ("smtp.office365.com", 587), "yahoo": ("smtp.mail.yahoo.com", 465)}
ETIQUETAS = {"correo_sentiende": "correo", "correo_borrador": "borrador", "whatsapp": "whatsapp", "carpeta": "carpeta", "zip": "zip"}


class ErrorEnvio(Exception):
    pass


def _archivos(m, eid, ids):
    a = m.almacen
    out = []
    for i in ids:
        d = a.documento(int(i))
        if not d or d.get("expediente_id") != eid or d.get("estado") != "guardado":
            raise ErrorEnvio("Uno de los documentos marcados ya no está guardado en este expediente. Vuelve a abrir el expediente.")
        p = Path(d.get("ruta_final") or "")
        if not p.is_file():
            raise ErrorEnvio(f"No se encuentra el archivo {p.name or d.get('nombre_final')}.")
        out.append(p)
    if not out:
        raise ErrorEnvio("Marca al menos un documento.")
    return out


def texto_resumen(asunto, texto, destinatarios, archivos):
    l = [f"Asunto: {asunto}", "", "Destinatarios:"]
    l += [f"  · {d.get('valor')} — {d.get('quien') or ''} ({', '.join(d.get('origenes') or [])})".rstrip() for d in destinatarios] or ["  (ninguno)"]
    l += ["", "Texto:", "", texto, "", f"Archivos ({len(archivos)}):"] + [f"  · {p.name}" for p in archivos]
    l += ["", f"Preparado con SeFinancia el {datetime.datetime.now():%d/%m/%Y a las %H:%M}."]
    return "\r\n".join(l)


def _mensaje(remite, para, asunto, texto, archivos, borrador):
    msg = EmailMessage()
    if remite:
        msg["From"] = remite
    msg["To"] = ", ".join(para)
    msg["Subject"] = asunto
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid(domain="sefinancia.local")
    if borrador:
        msg["X-Unsent"] = "1"                      # Outlook lo abre como borrador para enviar
    msg.set_content(texto)
    for p in archivos:
        tipo = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
        mt, st = tipo.split("/", 1)
        msg.add_attachment(p.read_bytes(), maintype=mt, subtype=st, filename=p.name)
    return msg


def _smtp(ajustes):
    if (ajustes.get("smtp_servidor") or "").strip():
        return ajustes["smtp_servidor"].strip(), int(ajustes.get("smtp_puerto") or 465)
    if ajustes.get("proveedor") in SMTP:
        return SMTP[ajustes["proveedor"]]
    s = (ajustes.get("servidor") or "").lower()
    if "gmail" in s or "google" in s:
        return SMTP["gmail"]
    if s.startswith("imap."):
        return "smtp." + s[5:], 465
    raise ErrorEnvio("No sé el servidor de salida (SMTP) de tu correo: ponlo en Ajustes › Correo.")


def enviar_smtp(ajustes, clave, msg):
    try:
        import smtplib
    except ImportError:
        raise ErrorEnvio("Falta el módulo de envío de correo en esta versión del programa: vuelve a crear el programa con el kit (Crear_SeFinancia.bat).")
    host, puerto = _smtp(ajustes)
    if "gmail" in host:
        clave = clave.replace(" ", "")
    ctx = ssl.create_default_context()
    try:
        if puerto == 465:
            s = smtplib.SMTP_SSL(host, puerto, context=ctx, timeout=60)
        else:
            s = smtplib.SMTP(host, puerto, timeout=60); s.starttls(context=ctx)
        with s:
            s.login(ajustes["usuario"], clave)
            s.send_message(msg)
    except smtplib.SMTPAuthenticationError as e:
        raise ErrorEnvio(f"El servidor de salida no acepta el usuario o la contraseña ({e.smtp_code}). En Gmail hace falta la contraseña de aplicación.")
    except (smtplib.SMTPException, OSError) as e:
        raise ErrorEnvio(f"No se ha podido enviar el correo por {host}: {e}. No se ha enviado nada.")


def movil_wa(numero):
    n = re.sub(r"\D", "", numero or "")
    if len(n) == 9 and n[0] in "67":
        n = "34" + n
    if len(n) < 11:
        raise ErrorEnvio(f"«{numero}» no parece un móvil para WhatsApp.")
    return n


def preparar(m, correo, eid, via, ids, asunto, texto, destinatarios, abrir=None):
    """Hace el envío por la vía elegida. `abrir(ruta_o_url, seleccionar)` lo pone el servidor (Windows)."""
    if via not in VIAS:
        raise ErrorEnvio("Vía de envío desconocida.")
    exp = m.almacen.expediente(eid)
    if not exp:
        raise ErrorEnvio("No existe el expediente.")
    archivos = _archivos(m, eid, ids)
    asunto, texto = (asunto or "").strip(), (texto or "").strip()
    mails = [d["valor"].strip() for d in destinatarios if d.get("tipo") == "mail" and d.get("valor")]
    moviles = [d["valor"] for d in destinatarios if d.get("tipo") == "tel" and d.get("valor")]
    if via.startswith("correo") and not mails:
        raise ErrorEnvio("Marca al menos un correo en Destinatarios.")
    if via == "whatsapp" and not moviles:
        raise ErrorEnvio("Marca al menos un móvil en Destinatarios.")
    base = m.carpetas.datos / "Envios" / exp["carpeta"]
    carpeta = libre(base / f"{datetime.datetime.now():%Y-%m-%d_%H%M}_{ETIQUETAS[via]}")
    carpeta.mkdir(parents=True)
    resumen = texto_resumen(asunto, texto, destinatarios, archivos)
    abrir = abrir or (lambda *x: None)
    res = {"carpeta": str(carpeta), "archivos": len(archivos)}

    if via in ("correo_sentiende", "correo_borrador"):
        total = sum(p.stat().st_size for p in archivos)
        if via == "correo_sentiende" and total > MAX_CORREO:
            raise ErrorEnvio(f"Los adjuntos ocupan {total / 1048576:.1f} MB y el correo no admite más de 24 MB. Quita documentos o envía un zip por otra vía.")
        aj = correo.ajustes(con_clave=True)
        from .correo import desproteger
        if via == "correo_sentiende":
            if not aj.get("usuario") or not aj.get("clave"):
                raise ErrorEnvio("Para enviar desde Sentiende hace falta tener el correo configurado en Ajustes › Correo.")
            msg = _mensaje(aj["usuario"], mails, asunto, texto, archivos, borrador=False)
            enviar_smtp(aj, desproteger(aj["clave"]), msg)
            (carpeta / "correo_enviado.eml").write_bytes(bytes(msg))
            res["enviado"] = True
        else:
            msg = _mensaje(aj.get("usuario") or "", mails, asunto, texto, archivos, borrador=True)
            eml = carpeta / "borrador.eml"
            eml.write_bytes(bytes(msg))
            abrir(str(eml), False)
            res["ruta"] = str(eml)
    elif via == "whatsapp":
        for p in archivos:
            shutil.copy2(p, libre(carpeta / p.name))
        from urllib.parse import quote
        url = f"https://wa.me/{movil_wa(moviles[0])}?text=" + quote(f"*{asunto}*\n\n{texto}" if asunto else texto)
        abrir(str(carpeta), False)
        abrir(url, False)
        res.update(url=url, otros_moviles=len(moviles) - 1)
    elif via == "carpeta":
        for p in archivos:
            shutil.copy2(p, libre(carpeta / p.name))
        (carpeta / "mensaje.txt").write_text(resumen, encoding="utf-8-sig")
        abrir(str(carpeta), False)
    else:
        z = carpeta / f"{exp['carpeta']}_{datetime.date.today():%Y%m%d}.zip"
        with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as f:
            usados = set()
            for p in archivos:
                n = p.name
                while n in usados:
                    n = "_" + n
                usados.add(n); f.write(p, n)
            f.writestr("mensaje.txt", "﻿" + resumen)
        abrir(str(z), True)
        res["ruta"] = str(z)

    quien = ", ".join(mails + moviles) or "—"
    m.almacen.evento(f"Envío de documentación ({ETIQUETAS[via]}) del expediente {exp['carpeta']}: {len(archivos)} archivo(s) · {quien} · «{asunto}»")
    return res


# ---------------------------------------------------------------- 3.1.3 · envíos vía Sentiende: ahora o programados
# (Joan, 18/11/2026) «Vía Sentiende» pregunta Ahora / Programado. Todos quedan apuntados en la tabla `envios`;
# los programados se envían solos a su hora MIENTRAS EL PROGRAMA ESTÉ ABIERTO (al cerrar se avisa). Si un envío
# falla, queda «error» y sale la campanita roja «Problema de envío» en el lateral.
def _tabla(db):
    db.execute("""CREATE TABLE IF NOT EXISTS envios(id INTEGER PRIMARY KEY, expediente_id INTEGER, creado TEXT, cuando TEXT,
                  estado TEXT, datos TEXT, error TEXT, hecho TEXT, visto INTEGER DEFAULT 0)""")


def _ahora():
    return datetime.datetime.now().replace(microsecond=0)


def programar(m, correo, eid, ids, asunto, texto, destinatarios, cuando=None):
    """cuando=None → se envía ahora mismo. Devuelve el envío (con su estado)."""
    import json
    db = m.almacen.db; _tabla(db)
    if cuando:
        try:
            t = datetime.datetime.fromisoformat(str(cuando)[:16])
        except ValueError:
            raise ErrorEnvio("Fecha y hora de envío no válidas.")
        if t <= _ahora():
            raise ErrorEnvio("La fecha y hora del envío programado ya ha pasado.")
    _archivos(m, eid, ids)                                   # comprueba ya que los documentos existen
    if not [d for d in destinatarios if d.get("tipo") == "mail"]:
        raise ErrorEnvio("Marca al menos un correo en Destinatarios.")
    datos = json.dumps({"documentos": [int(i) for i in ids], "asunto": asunto, "texto": texto, "destinatarios": destinatarios}, ensure_ascii=False)
    cur = db.execute("INSERT INTO envios(expediente_id, creado, cuando, estado, datos) VALUES(?, ?, ?, 'programado', ?)",
                     (eid, _ahora().isoformat(), (t if cuando else _ahora()).isoformat(), datos))
    db.commit()
    if not cuando:
        return ejecutar(m, correo, cur.lastrowid)
    m.almacen.evento(f"Envío programado para el {t:%d/%m/%Y a las %H:%M} (expediente {eid})")
    return envio(m, cur.lastrowid)


def envio(m, i):
    import json
    _tabla(m.almacen.db)
    r = m.almacen.db.execute("SELECT * FROM envios WHERE id = ?", (i,)).fetchone()
    if not r:
        raise ErrorEnvio("No existe ese envío.")
    e = dict(r); d = json.loads(e.pop("datos") or "{}")
    exp = m.almacen.expediente(e["expediente_id"]) or {}
    e.update(asunto=d.get("asunto"), documentos=len(d.get("documentos") or []), expediente=exp.get("nombre"),
             para=[x["valor"] for x in d.get("destinatarios") or [] if x.get("tipo") == "mail"])
    return e


def ejecutar(m, correo, i):
    import json
    db = m.almacen.db
    r = db.execute("SELECT * FROM envios WHERE id = ?", (i,)).fetchone()
    d = json.loads(r["datos"])
    try:
        res = preparar(m, correo, r["expediente_id"], "correo_sentiende", d["documentos"], d["asunto"], d["texto"], d["destinatarios"])
        db.execute("UPDATE envios SET estado = 'enviado', hecho = ?, error = NULL WHERE id = ?", (_ahora().isoformat(), i))
    except Exception as e:                                   # se apunta y sale la campanita roja
        db.execute("UPDATE envios SET estado = 'error', hecho = ?, error = ?, visto = 0 WHERE id = ?", (_ahora().isoformat(), str(e), i))
        m.almacen.evento(f"Problema de envío: {e}", nivel="aviso")
    db.commit()
    return envio(m, i)


RETRASO_MAX = datetime.timedelta(minutes=5)


def vencidos(m, correo):
    """Lo llama un hilo del servidor cada 30 s: envía los programados cuya hora ya ha llegado.
    Si ha pasado más de 5 minutos (el programa estaba cerrado), NO se envía: queda «retrasado» y se pregunta
    con la campanita roja (Joan, 19/11/2026: «pregunta antes de enviarlo con retraso»)."""
    db = m.almacen.db; _tabla(db)
    ahora, out = _ahora(), []
    for i, cuando in db.execute("SELECT id, cuando FROM envios WHERE estado = 'programado' AND cuando <= ?", (ahora.isoformat(),)).fetchall():
        if ahora - datetime.datetime.fromisoformat(cuando) > RETRASO_MAX:
            db.execute("UPDATE envios SET estado = 'retrasado', visto = 0 WHERE id = ?", (i,)); db.commit()
            m.almacen.evento(f"Envío programado para el {cuando[:16].replace('T', ' ')} sin enviar (el programa estaba cerrado): se pregunta antes de enviarlo", nivel="aviso")
            out.append(envio(m, i))
        else:
            out.append(ejecutar(m, correo, i))
    return out


def lista(m, eid=None):
    _tabla(m.almacen.db)
    q, p = "SELECT id FROM envios WHERE estado IN ('programado', 'error', 'retrasado')", []
    if eid:
        q += " AND expediente_id = ?"; p.append(eid)
    return [envio(m, r[0]) for r in m.almacen.db.execute(q + " ORDER BY cuando", p)]


def cuentas(m):
    _tabla(m.almacen.db)
    c = lambda q: m.almacen.db.execute(q).fetchone()[0]
    return {"programados": c("SELECT COUNT(*) FROM envios WHERE estado = 'programado'"),
            "errores": c("SELECT COUNT(*) FROM envios WHERE estado IN ('error', 'retrasado') AND visto = 0")}


def accion(m, correo, i, que):
    db = m.almacen.db
    if que == "cancelar":
        db.execute("UPDATE envios SET estado = 'cancelado', hecho = ? WHERE id = ? AND estado IN ('programado', 'error', 'retrasado')", (_ahora().isoformat(), i))
    elif que == "visto":
        db.execute("UPDATE envios SET visto = 1 WHERE id = ?", (i,))
    elif que in ("reintentar", "enviar"):
        return ejecutar(m, correo, i)
    else:
        raise ErrorEnvio("Acción desconocida.")
    db.commit()
    return envio(m, i)
