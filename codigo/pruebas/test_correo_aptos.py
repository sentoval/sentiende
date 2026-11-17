# -*- coding: utf-8 -*-
"""Correo 3.2: reglas de «apto» (Joan, 17/11/2026) con un buzón simulado. Nunca se borra nada."""
import datetime, email.message, imaplib, tempfile, unittest
from pathlib import Path
from sentiende import correo

AHORA = datetime.datetime(2026, 11, 17, 10, 0, tzinfo=datetime.timezone.utc)


def mensaje(asunto, adjuntos, de="cliente@correo.es", mid=None):
    m = email.message.EmailMessage()
    m["From"], m["Subject"], m["Message-ID"] = de, asunto, mid or f"<{asunto.replace(' ', '')}@x>"
    m.set_content("Te adjunto la documentación.")
    for nombre, datos in adjuntos:
        m.add_attachment(datos, maintype="application", subtype="octet-stream", filename=nombre)
    return m.as_bytes()


class Buzon:
    """IMAP de mentira con carpetas, etiquetas, MOVE y llegada de cada correo."""
    def __init__(self, mensajes, caps=("IMAP4REV1", "MOVE")):
        self.carpetas = {"INBOX": {i + 1: {"raw": raw, "flags": set(), "llegada": lleg} for i, (raw, lleg) in enumerate(mensajes)}}
        self.capabilities, self.sel, self.ordenes, self.untagged_responses, self.sig = caps, "INBOX", [], {}, 100
    def __call__(self, *a, **k):
        return self
    def login(self, u, c):
        return "OK", [b""]
    def select(self, carpeta, readonly=False):
        carpeta = carpeta.strip('"')
        if carpeta not in self.carpetas:
            return "NO", [b""]
        self.sel = carpeta
        self.untagged_responses = {"PERMANENTFLAGS": [b"(\\Seen \\*)"], "UIDVALIDITY": [b"7"]}
        return "OK", [str(len(self.carpetas[carpeta])).encode()]
    def create(self, carpeta):
        self.ordenes.append(("CREATE", carpeta)); self.carpetas.setdefault(carpeta.strip('"'), {}); return "OK", [b""]
    def uid(self, orden, *args):
        self.ordenes.append((orden,) + tuple(a.decode() if isinstance(a, bytes) else a for a in args))
        c = self.carpetas[self.sel]
        if orden == "SEARCH":
            if "HEADER" in args:
                mid = args[-1]
                return "OK", [" ".join(str(u) for u, m in c.items() if mid.encode() in m["raw"]).encode()]
            return "OK", [" ".join(str(u) for u in c).encode()]
        u = int(args[0])
        if orden == "FETCH":
            m = c[u]
            cab = f'{u} (INTERNALDATE "{imaplib.Time2Internaldate(m["llegada"].timestamp()).strip(chr(34))}" BODY[] {{1}}'.encode()
            return "OK", [(cab, m["raw"]), b")"]
        if orden == "STORE":
            flag = args[2].strip("()")
            (c[u]["flags"].add if args[1].startswith("+") else c[u]["flags"].discard)(flag)
            return "OK", [b""]
        if orden == "MOVE":
            destino = args[1].strip('"')
            self.sig += 1
            self.carpetas.setdefault(destino, {})[self.sig] = c.pop(u)
            return "OK", [b""]
        if orden in ("COPY", "EXPUNGE"):
            raise AssertionError("con MOVE no hace falta COPY ni EXPUNGE")
        return "OK", [b""]
    def logout(self):
        self.ordenes.append(("LOGOUT",))


class Pol:
    def __init__(self, conocidos=(), office=None):
        self.conocidos, self.respuesta, self.preguntas, self.sin_docs, self.registrados = set(conocidos), office, [], [], []
        self.a_devolver, self.a_quitar = [], []
    def estado(self, e): return ("conocido", "Pilar Sanz") if e in self.conocidos else ("desconocido", None)
    def imagenes_aptas(self, rutas): return any("dni" in Path(r).name.lower() for r in rutas)
    def office(self, clave): return self.respuesta
    def pedir_office(self, clave, datos): self.preguntas.append(datos)
    def aviso_sin_docs(self, nombre, e, clave): self.sin_docs.append(nombre)
    def registrar(self, lote, rem, mid, carpeta, regla): self.registrados.append((lote, rem, mid, carpeta, regla))
    def aviso_procesado(self, nombre, e, asunto, cuerpo, lote, carpeta): self.avisos = getattr(self, "avisos", []) + [(nombre, e, asunto, cuerpo, carpeta)]
    def devoluciones(self): return self.a_devolver
    def devuelto(self, i): self.a_devolver = []
    def quitar_marca(self): return self.a_quitar
    def marca_quitada(self, c): self.a_quitar = []


def preparar(t):
    c = correo.Correo(t)
    c.guardar({"servidor": "imap.ejemplo.es", "usuario": "u@ejemplo.es", "clave": "x"})
    return c


class TestAptos(unittest.TestCase):
    def setUp(self):
        self.real = imaplib.IMAP4_SSL

    def tearDown(self):
        imaplib.IMAP4_SSL = self.real

    def test_reglas(self):
        viejo = AHORA - datetime.timedelta(minutes=10)
        pdf, jpg = b"%PDF-1.4", b"\xff\xd8\xff"
        b = Buzon([
            (mensaje("conocido con pdf", [("nomina.pdf", pdf)], "pilar@correo.es"), viejo),         # 1 apto
            (mensaje("conocido sin nada", [], "pilar@correo.es"), viejo),                           # 1 sin docs: aviso
            (mensaje("desconocido sin nada", []), viejo),                                           # 2 no apto
            (mensaje("foto dni", [("dni.jpg", jpg)]), viejo),                                       # 3a apto (nombre)
            (mensaje("foto rara", [("IMG_001.jpg", jpg)]), viejo),                                  # 3a no apto
            (mensaje("excel", [("cuentas.xlsx", b"PK"), ("foto.jpg", jpg)]), viejo),                # 3b pregunta
            (mensaje("solo pdf", [("papeles.pdf", pdf)]), viejo),                                   # 3c apto
            (mensaje("mezcla", [("a.xlsx", b"PK"), ("b.pdf", pdf)]), viejo),                        # 3d apto
            (mensaje("recien llegado", [("c.pdf", pdf)]), AHORA - datetime.timedelta(seconds=20)),  # espera 1 minuto
        ])
        imaplib.IMAP4_SSL = b
        with tempfile.TemporaryDirectory() as t:
            c, pol, lotes = preparar(t), Pol(conocidos={"pilar@correo.es"}), []
            res = c.recoger_aptos(t, lambda rutas, d: lotes.append(sorted(Path(r).name for r in rutas)) or len(lotes), pol, ahora=AHORA, esperar=True)
            self.assertEqual(lotes, [["nomina.pdf"], ["dni.jpg"], ["papeles.pdf"], ["a.xlsx", "b.pdf"]])
            self.assertEqual([r[4] for r in pol.registrados], ["1", "3a", "3c", "3d"])
            self.assertEqual(pol.sin_docs, ["Pilar Sanz"])
            self.assertEqual(len(pol.preguntas), 1)
            self.assertEqual(res["esperando"], 1)
            self.assertEqual(len(pol.avisos), 4)
            self.assertEqual(pol.avisos[0][:4], ("Pilar Sanz", "pilar@correo.es", "conocido con pdf", "Te adjunto la documentación."))
            self.assertEqual(pol.avisos[0][4], "procesados1126")
            proc = b.carpetas["procesados1126"]
            self.assertEqual(len(proc), 4)
            self.assertTrue(all(correo.MARCA in m["flags"] for m in proc.values()))
            inbox = {email.message_from_bytes(m["raw"])["Subject"]: m["flags"] for m in b.carpetas["INBOX"].values()}
            self.assertEqual(inbox["desconocido sin nada"], {correo.NO_APTO})
            self.assertEqual(inbox["foto rara"], {correo.NO_APTO})
            self.assertEqual(inbox["excel"], {correo.MARCA})            # espera tu respuesta con la etiqueta
            self.assertEqual(inbox["conocido sin nada"], set())        # se queda en la entrada
            self.assertIn("recien llegado", inbox)
            self.assertFalse(any(o[0] in ("EXPUNGE", "COPY") for o in b.ordenes))
            self.assertTrue(all("PEEK" in o[2] for o in b.ordenes if o[0] == "FETCH"))
            # contestas «Sí» al Excel: en la siguiente vuelta se recoge y se mueve; el recién llegado ya ha esperado
            pol.respuesta = "aceptado"
            lotes.clear()
            c.recoger_aptos(t, lambda rutas, d: lotes.append(sorted(Path(r).name for r in rutas)) or 9, pol, ahora=AHORA + datetime.timedelta(minutes=2))
            self.assertEqual(lotes, [["c.pdf"], ["cuentas.xlsx", "foto.jpg"]] if lotes[0] == ["c.pdf"] else [["cuentas.xlsx", "foto.jpg"], ["c.pdf"]])
            # regla 3c: el correo de solo PDF vuelve a la entrada sin la etiqueta
            mid = next(r[2] for r in pol.registrados if r[4] == "3c")
            pol.a_devolver = [{"id": 1, "message_id": mid, "carpeta": "procesados1126"}]
            c.recoger_aptos(t, lambda r, d: 0, pol, ahora=AHORA + datetime.timedelta(minutes=3))
            vuelto = [m for m in b.carpetas["INBOX"].values() if b"solopdf" in m["raw"]]
            self.assertEqual(len(vuelto), 1)
            self.assertNotIn(correo.MARCA, vuelto[0]["flags"])

    def test_a_mano_no_espera(self):
        b = Buzon([(mensaje("recien", [("p.pdf", b"%PDF")]), AHORA - datetime.timedelta(seconds=5))])
        imaplib.IMAP4_SSL = b
        with tempfile.TemporaryDirectory() as t:
            res = preparar(t).recoger_aptos(t, lambda r, d: 1, Pol(), ahora=AHORA, esperar=False)
            self.assertEqual((res["esperando"], len(res["lotes"])), (0, 1))

    def test_sin_move_no_se_mueve_nada(self):
        b = Buzon([(mensaje("solo pdf", [("p.pdf", b"%PDF")]), AHORA - datetime.timedelta(minutes=5))], caps=("IMAP4REV1",))
        imaplib.IMAP4_SSL = b
        with tempfile.TemporaryDirectory() as t:
            res = preparar(t).recoger_aptos(t, lambda r, d: 1, Pol(), ahora=AHORA)
            self.assertEqual(res["sin_mover"], 1)
            self.assertEqual(len(b.carpetas["INBOX"]), 1)                # sigue en la entrada, solo marcado
            self.assertFalse(any(o[0] in ("MOVE", "COPY", "EXPUNGE", "CREATE") for o in b.ordenes))

    def test_gmail_anuncia_move_despues_de_entrar(self):
        """3.1.2 · Gmail no anuncia MOVE hasta entrar; la etiqueta va como etiqueta de Gmail (X-GM-LABELS)."""
        b = BuzonGmail([(mensaje("solo pdf", [("p.pdf", b"%PDF")]), AHORA - datetime.timedelta(minutes=5))])
        imaplib.IMAP4_SSL = b
        with tempfile.TemporaryDirectory() as t:
            res = preparar(t).recoger_aptos(t, lambda r, d: 1, Pol(), ahora=AHORA)
            self.assertEqual((res["movidos"], res["sin_mover"]), (1, 0))
            self.assertEqual(len(b.carpetas["INBOX"]), 0)
            self.assertIn(("STORE", "1", "+X-GM-LABELS", f'("{correo.MARCA}")'), b.ordenes)


class BuzonGmail(Buzon):
    def __init__(self, mensajes):
        super().__init__(mensajes, caps=("IMAP4REV1", "X-GM-EXT-1", "AUTH=PLAIN"))     # antes de entrar
    def capability(self):
        return "OK", [b"IMAP4rev1 UNSELECT IDLE NAMESPACE QUOTA ID XLIST CHILDREN X-GM-EXT-1 UIDPLUS COMPRESS=DEFLATE ENABLE MOVE"]
    def uid(self, orden, *args):
        if orden == "STORE" and "X-GM-LABELS" in args[1]:
            self.ordenes.append((orden,) + tuple(args)); return "OK", [b""]
        return super().uid(orden, *args)


if __name__ == "__main__":
    unittest.main()
