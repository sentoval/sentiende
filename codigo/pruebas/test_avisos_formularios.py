# -*- coding: utf-8 -*-
"""3.1.2 · ignorar/posponer avisos de cliente, umbral de lectura pobre, formularios por apartados."""
import tempfile, unittest, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sentiende.almacen import Almacen
from sentiende.separar import separar, secciones
from sentiende.variante import Variante
from sentiende.clasificar import Clasificador

VAR = Path(__file__).resolve().parents[1] / "variantes" / "sefinancia"


class AvisosCliente(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.a = Almacen(Path(self.tmp.name) / "s.db")
        self.a.poner_avisos_cliente(1, ["Falta la nómina", "DNI caducado"])

    def tearDown(self):
        self.a.db.close(); self.tmp.cleanup()

    def test_ignorar_y_volver(self):
        self.a.marcar_aviso_cliente(1, "DNI caducado", "ignorar")
        self.assertEqual([x["mensaje"] for x in self.a.avisos_cliente(1)], ["Falta la nómina"])
        self.assertEqual(len(self.a.avisos_cliente(apartados=True)), 1)
        self.a.poner_avisos_cliente(1, ["Falta la nómina", "DNI caducado"])      # el motor vuelve a calcular: sigue ignorado
        self.assertEqual(len(self.a.avisos_cliente(1)), 1)
        self.a.marcar_aviso_cliente(1, "DNI caducado", "mostrar")
        self.assertEqual(len(self.a.avisos_cliente(1)), 2)

    def test_posponer(self):
        self.a.marcar_aviso_cliente(1, "Falta la nómina", "posponer", 7)
        self.assertEqual(len(self.a.avisos_cliente(1)), 1)
        self.a.db.execute("UPDATE avisos_cliente SET pospuesto = '2000-01-01T00:00:00'")    # ya pasó la fecha
        self.assertEqual(len(self.a.avisos_cliente(1)), 2)
        with self.assertRaises(RuntimeError):
            self.a.marcar_aviso_cliente(1, "Falta la nómina", "posponer", 3)


class Formularios(unittest.TestCase):
    def test_apartados(self):
        self.assertEqual(secciones("1. Solicitante\nxx\n2. Financiación que solicita\n3. Descripción"), [1, 2, 3])
        self.assertEqual(secciones("4. Declaración de bienes\n6. Persona de responsabilidad\n7. Otros datos"), [4, 6, 7])

    def test_no_parte_la_solicitud(self):
        cl = Clasificador(Variante(VAR))
        p1 = "Solicitud de aval AFIN SGR\n1. Solicitante\nNombre y apellidos\n2. Financiación que solicita\nPRESTAMO\n3. Descripción de la actividad\nTaxi"
        p2 = "4. Declaración de bienes (cumplimentar en caso de poseer bienes)\nACTIVOS FINANCIEROS (Plazos fijos y Fondos de Inversión)\nVALOR LIQUIDATIVO PARTICIPACIONES ISIN\n6. Persona de Responsabilidad Pública\n7. Otros datos"
        p3 = "El/los abajo firmantes AUTORIZA a AFIN SGR SOCIEDAD DE GARANTÍA RECÍPROCA a las notificaciones"
        s = separar([p1, p2, p3], cl)
        self.assertEqual([q.paginas for q in s.partes], [[1, 2, 3]])
        self.assertEqual(s.partes[0].tipo, "solicitudaval")


if __name__ == "__main__":
    unittest.main()
