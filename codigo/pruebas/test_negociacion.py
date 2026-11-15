# -*- coding: utf-8 -*-
"""Tarjetas de visita (siempre se preguntan) y negociación con varios bancos. Datos inventados."""
import sqlite3, tempfile, unittest
from pathlib import Path
from sentiende.almacen import Almacen
from sentiende.negociacion import Negociacion, parece_tarjeta

BANCOS = [{"nombre": "CaixaBank", "alias": ["La Caixa"]}, {"nombre": "Banco Sabadell", "alias": ["Sabadell"]}]


class TestTarjeta(unittest.TestCase):
    def test_tarjeta(self):
        t = "CaixaBank\nLAURA PERIS SANCHO\nDirectora de Oficina\nOficina 1234\nAvda. del Puerto 45, 46023 Valencia\nTel. 963 123 456 Móvil 611 222 333\nlaura.perisOejemplo.es"
        d = parece_tarjeta(t, None, 0, BANCOS)
        self.assertEqual((d["entidad"], d["nombre"], d["movil"], d["telefono"], d["oficina"], d["email"]),
                         ("CaixaBank", "Laura Peris Sancho", "611222333", "963123456", "1234", "laura.peris@ejemplo.es"))

    def test_no_tarjeta(self):
        largo = "Nómina del mes de agosto " * 30 + " Tel. 963 123 456 Banco Sabadell"
        self.assertIsNone(parece_tarjeta(largo, None, 0, BANCOS))                 # mucho texto
        self.assertIsNone(parece_tarjeta("Sabadell oficina 963123456", None, 1, BANCOS))   # lleva DNI: es de un titular
        self.assertIsNone(parece_tarjeta("Juan Pérez García\nC/ Mayor 3", None, 0, BANCOS))  # sin teléfono ni correo


class TestNegociacion(unittest.TestCase):
    def test_bancos_contactos_notas_marcas(self):
        with tempfile.TemporaryDirectory() as t:
            n = Negociacion(Almacen(Path(t) / "s.db"))
            b1 = n.banco(1, "CaixaBank"); b2 = n.banco(1, "Banco Sabadell")
            self.assertEqual(n.banco(1, "caixabank"), b1)                  # no se repite
            n.contacto(b1, {"nombre": "Laura Peris", "cargo": "Directora", "movil": "611222333"})
            n.nota(1, "banco", "Oferta 80 % a 30 años", b1); n.nota(1, "cliente", "Prefiere fijo")
            n.banco(1, None, "Oferta recibida", b1)
            n.marcar(1, "5:nomina", "solicitado")
            r = n.de_expediente(1)
            self.assertEqual([b["entidad"] for b in r["bancos"]], ["CaixaBank", "Banco Sabadell"])
            self.assertEqual(r["bancos"][0]["estado"], "Oferta recibida")
            self.assertEqual(r["bancos"][0]["contactos"][0]["nombre"], "Laura Peris")
            self.assertEqual(len(r["notas"]), 2)
            self.assertEqual(r["marcas"]["5:nomina"]["estado"], "solicitado")


if __name__ == "__main__":
    unittest.main()
