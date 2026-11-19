# -*- coding: utf-8 -*-
"""3.1.3 · «Preparar envío»: carpeta y zip con mensaje.txt, borrador .eml con adjuntos, WhatsApp con el asunto
al principio y envío vía Sentiende (SMTP simulado). Nunca se tocan los originales."""
import email, tempfile, unittest, sys, zipfile
from pathlib import Path
from unittest import mock
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sentiende.motor import Motor
from sentiende.correo import Correo
from sentiende import envio

VAR = Path(__file__).resolve().parents[1] / "variantes" / "sefinancia"
DEST = [{"tipo": "mail", "valor": "ana@banco.es", "quien": "Ana Peris", "origenes": ["manual"]},
        {"tipo": "tel", "valor": "655 12 34 56", "quien": "Ana Peris", "origenes": ["tarjeta de visita (OCR)"]}]


class Envio(unittest.TestCase):
    def preparar(self, t):
        m = Motor(Path(t), VAR); a = m.almacen
        pid = a.nueva_persona("Vicente", "Calabuig", "Jaquotot", "12345678Z")
        eid = a.nuevo_expediente("Calabuig", "hipotecario", "VicenteCalabuig_45678_1126")
        a.anadir_persona(eid, pid, "Titular")
        carpeta = m.carpetas.documentos / "VicenteCalabuig_45678_1126"; carpeta.mkdir(parents=True)
        ids = []
        for n in ("VCJ678_dni_1126.pdf", "VCJ678_nomina_1026.pdf"):
            f = carpeta / n; f.write_bytes(b"%PDF-1.4 prueba " + n.encode())
            did = a.nuevo_documento(a.nuevo_lote("manual"), n, str(f), "h" + n, ".pdf")
            a.actualizar(did, estado="guardado", expediente_id=eid, persona_id=pid, ruta_final=str(f), nombre_final=n)
            ids.append(did)
        return m, Correo(m.carpetas.datos), eid, ids, carpeta

    def test_carpeta_y_zip(self):
        with tempfile.TemporaryDirectory() as t:
            m, c, eid, ids, orig = self.preparar(t)
            r = envio.preparar(m, c, eid, "carpeta", ids, "Documentación", "Hola, Ana", DEST)
            d = Path(r["carpeta"])
            self.assertEqual(sorted(p.name for p in d.iterdir()), ["VCJ678_dni_1126.pdf", "VCJ678_nomina_1026.pdf", "mensaje.txt"])
            txt = (d / "mensaje.txt").read_text(encoding="utf-8-sig")
            self.assertIn("Asunto: Documentación", txt); self.assertIn("ana@banco.es", txt); self.assertIn("Hola, Ana", txt)
            r = envio.preparar(m, c, eid, "zip", ids, "Documentación", "Hola", DEST)
            with zipfile.ZipFile(r["ruta"]) as z:
                self.assertEqual(sorted(z.namelist()), ["VCJ678_dni_1126.pdf", "VCJ678_nomina_1026.pdf", "mensaje.txt"])
            self.assertEqual(len(list(orig.iterdir())), 2)          # los originales siguen ahí
            m.almacen.db.close()

    def test_borrador_y_whatsapp(self):
        with tempfile.TemporaryDirectory() as t:
            m, c, eid, ids, _ = self.preparar(t)
            abiertos = []
            r = envio.preparar(m, c, eid, "correo_borrador", ids, "Documentación", "Hola", DEST, abrir=lambda *x: abiertos.append(x[0]))
            msg = email.message_from_bytes(Path(r["ruta"]).read_bytes())
            self.assertEqual(msg["X-Unsent"], "1"); self.assertEqual(msg["To"], "ana@banco.es")
            self.assertEqual(len([p for p in msg.walk() if p.get_filename()]), 2)
            r = envio.preparar(m, c, eid, "whatsapp", ids[:1], "Documentación", "Hola", DEST, abrir=lambda *x: abiertos.append(x[0]))
            self.assertTrue(r["url"].startswith("https://wa.me/34655123456?text=%2ADocumentaci"))
            self.assertIn(r["carpeta"], abiertos)
            with self.assertRaises(envio.ErrorEnvio):
                envio.preparar(m, c, eid, "whatsapp", ids, "A", "B", DEST[:1])      # sin móvil
            m.almacen.db.close()

    def test_via_sentiende(self):
        with tempfile.TemporaryDirectory() as t:
            m, c, eid, ids, _ = self.preparar(t)
            with self.assertRaises(envio.ErrorEnvio):                              # sin correo configurado
                envio.preparar(m, c, eid, "correo_sentiende", ids, "A", "B", DEST)
            c.guardar({"proveedor": "gmail", "servidor": "imap.gmail.com", "usuario": "yo@gmail.com", "clave": "abcd efgh ijkl mnop"})
            enviados = []
            class SMTP:
                def __init__(self, host, puerto, **k): self.host = host
                def __enter__(self): return self
                def __exit__(self, *a): pass
                def login(self, u, k): enviados.append((self.host, u, k))
                def send_message(self, msg): enviados.append(msg)
            with mock.patch("smtplib.SMTP_SSL", SMTP):
                r = envio.preparar(m, c, eid, "correo_sentiende", ids, "Documentación", "Hola", DEST)
            self.assertTrue(r["enviado"])
            self.assertEqual(enviados[0], ("smtp.gmail.com", "yo@gmail.com", "abcdefghijklmnop"))
            self.assertEqual(enviados[1]["To"], "ana@banco.es")
            self.assertTrue((Path(r["carpeta"]) / "correo_enviado.eml").exists())
            m.almacen.db.close()

    def test_programado_y_error(self):
        import datetime
        with tempfile.TemporaryDirectory() as t:
            m, c, eid, ids, _ = self.preparar(t)
            with self.assertRaises(envio.ErrorEnvio):                              # hora pasada
                envio.programar(m, c, eid, ids, "A", "B", DEST, "2020-01-01T10:00")
            luego = (datetime.datetime.now() + datetime.timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M")
            e = envio.programar(m, c, eid, ids, "A", "B", DEST, luego)
            self.assertEqual((e["estado"], envio.cuentas(m)["programados"]), ("programado", 1))
            self.assertEqual(envio.vencidos(m, c), [])                             # aún no toca
            m.almacen.db.execute("UPDATE envios SET cuando = '2020-01-01T00:00:00'"); m.almacen.db.commit()
            r = envio.vencidos(m, c)                                               # programa cerrado a esa hora → se pregunta
            self.assertEqual(r[0]["estado"], "retrasado")
            self.assertEqual(envio.cuentas(m), {"programados": 0, "errores": 1})
            r = envio.accion(m, c, e["id"], "enviar")                              # sin correo configurado → error
            self.assertEqual(r["estado"], "error")
            self.assertEqual(envio.cuentas(m), {"programados": 0, "errores": 1})
            envio.accion(m, c, e["id"], "visto")
            self.assertEqual(envio.cuentas(m)["errores"], 0)
            self.assertEqual(envio.accion(m, c, e["id"], "cancelar")["estado"], "cancelado")
            m.almacen.db.close()


if __name__ == "__main__":
    unittest.main()
