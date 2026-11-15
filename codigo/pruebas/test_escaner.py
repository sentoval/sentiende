# -*- coding: utf-8 -*-
"""Escáner por red (eSCL/AirScan) con un escáner simulado en este equipo, y lectura de respuestas mDNS."""
import socket, struct, tempfile, threading, unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from app import escaner


class Falso(BaseHTTPRequestHandler):
    paginas = 2
    def log_message(self, *a): pass
    def do_GET(self):
        if self.path.endswith("ScannerCapabilities"):
            b = b'<scan:ScannerCapabilities xmlns:pwg="x"><pwg:MakeAndModel>Escaner de Prueba</pwg:MakeAndModel></scan:ScannerCapabilities>'
            self.send_response(200); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b); return
        if self.path.endswith("NextDocument"):
            if Falso.paginas == 0:
                self.send_response(404); self.end_headers(); return
            Falso.paginas -= 1
            b = b"%PDF-1.4 hoja"
            self.send_response(200); self.send_header("Content-Type", "application/pdf"); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b); return
        self.send_response(404); self.end_headers()
    def do_POST(self):
        self.rfile.read(int(self.headers.get("Content-Length") or 0))
        self.send_response(201); self.send_header("Location", "/eSCL/ScanJobs/7"); self.send_header("Content-Length", "0"); self.end_headers()


class TestEscaner(unittest.TestCase):
    def test_escl(self):
        srv = ThreadingHTTPServer(("127.0.0.1", 0), Falso)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            ip = f"127.0.0.1:{srv.server_address[1]}"
            e = escaner.probar_escl(ip)
            self.assertEqual(e["nombre"], "Escaner de Prueba")
            with tempfile.TemporaryDirectory() as t:
                Falso.paginas = 2
                fs = escaner.escanear_escl(t, e["url"], alimentador=True)
                self.assertEqual(len(fs), 2)
                self.assertTrue(all(f.read_bytes().startswith(b"%PDF") for f in fs))
        finally:
            srv.shutdown()

    def test_mdns(self):
        def nombre(n):
            return b"".join(bytes([len(p)]) + p.encode() for p in n.split(".")) + b"\x00"
        inst = "Oficina._uscan._tcp.local"
        rr = lambda n, t, d: nombre(n) + struct.pack("!HHIH", t, 1, 120, len(d)) + d
        txt = b"".join(bytes([len(x)]) + x for x in (b"ty=HP OfficeJet", b"rs=eSCL"))
        paquete = struct.pack("!HHHHHH", 0, 0x8400, 0, 4, 0, 0) + rr("_uscan._tcp.local", 12, nombre(inst)) \
            + rr(inst, 33, struct.pack("!HHH", 0, 0, 8080) + nombre("hp.local")) + rr(inst, 16, txt) + rr("hp.local", 1, socket.inet_aton("192.168.1.40"))
        regs = escaner._leer_respuesta(paquete)
        tipos = {t: v for _, t, v in regs}
        self.assertEqual(tipos[12], inst)
        self.assertEqual(tipos[33], (8080, "hp.local"))
        self.assertEqual(tipos[16]["ty"], "HP OfficeJet")
        self.assertEqual(tipos[1], "192.168.1.40")


if __name__ == "__main__":
    unittest.main()
