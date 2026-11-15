# -*- coding: utf-8 -*-
"""Correo: solo lectura + marca, adjuntos admitidos, nada con macros (con un buzón simulado)."""
import email.message, imaplib, tempfile, unittest
from pathlib import Path
from sentiende import correo


def mensaje(asunto, adjuntos, de="gestor@banco.es"):
    m = email.message.EmailMessage()
    m["From"], m["Subject"] = de, asunto
    m.set_content("Te adjunto la documentación.")
    for nombre, datos in adjuntos:
        m.add_attachment(datos, maintype="application", subtype="octet-stream", filename=nombre)
    return m.as_bytes()


class Buzon:
    """Imita lo justo de imaplib.IMAP4_SSL y apunta todo lo que se le pide."""
    def __init__(self, mensajes):
        self.mensajes, self.ordenes, self.untagged_responses = mensajes, [], {}
    def __call__(self, *a, **k):
        return self
    def login(self, u, c):
        self.ordenes.append(("LOGIN", u)); return "OK", [b""]
    def select(self, carpeta, readonly=False):
        self.untagged_responses = {"PERMANENTFLAGS": [b"(\\Seen \\*)"], "UIDVALIDITY": [b"7"]}
        return "OK", [str(len(self.mensajes)).encode()]
    def uid(self, orden, *args):
        self.ordenes.append((orden,) + tuple(a if isinstance(a, str) else a.decode() if isinstance(a, bytes) else a for a in args))
        if orden == "SEARCH":
            return "OK", [" ".join(str(i + 1) for i in range(len(self.mensajes))).encode()]
        if orden == "FETCH":
            return "OK", [(b"1 (BODY[] {1}", self.mensajes[int(args[0]) - 1]), b")"]
        return "OK", [b""]
    def logout(self):
        self.ordenes.append(("LOGOUT",))


class TestCorreo(unittest.TestCase):
    def test_recoge_solo_lo_admitido_y_no_borra(self):
        pdf = b"%PDF-1.4 prueba"
        buzon = Buzon([mensaje("Nóminas", [("nomina.pdf", pdf), ("macro.docm", b"PK\x03\x04"), ("virus.exe", b"MZ")]),
                       mensaje("Sin adjuntos", [])])
        real = imaplib.IMAP4_SSL
        imaplib.IMAP4_SSL = buzon
        try:
            with tempfile.TemporaryDirectory() as t:
                c = correo.Correo(t)
                c.guardar({"servidor": "imap.ejemplo.es", "usuario": "u@ejemplo.es", "clave": "secreta"})
                self.assertNotIn("secreta", Path(t, "correo.json").read_text())
                lotes = []
                res = c.recoger(t, lambda rutas, desc: lotes.append([Path(r).name for r in rutas]) or len(lotes))
                self.assertEqual(lotes, [["nomina.pdf"]])
                self.assertEqual(res["correos"], 2)
                self.assertEqual(len(res["ignorados"]), 2)
                hechas = [o[0] for o in buzon.ordenes]
                self.assertTrue(all(o in ("LOGIN", "SEARCH", "FETCH", "STORE", "LOGOUT") for o in hechas))
                self.assertTrue(all("PEEK" in o[2] for o in buzon.ordenes if o[0] == "FETCH"))
                self.assertTrue(all(o[2] == "+FLAGS" and "Deleted" not in o[3] for o in buzon.ordenes if o[0] == "STORE"))
                # la segunda vez no vuelve a recoger nada
                lotes.clear(); c.recoger(t, lambda rutas, desc: lotes.append(rutas))
                self.assertEqual(lotes, [])
        finally:
            imaplib.IMAP4_SSL = real


if __name__ == "__main__":
    unittest.main()
