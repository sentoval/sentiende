# -*- coding: utf-8 -*-
"""3.1.2 · errores de la prueba del 17/11 por la noche: fecha de 1856, NIF encima del nombre en la renta, nombres al unir."""
import unittest, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sentiende.extraer import fechas, personas
from sentiende.nombres import _fmt
from sentiende.almacen import nombre_limpio


class Noche(unittest.TestCase):
    def test_fecha_antigua(self):
        self.assertEqual([f for _, f in fechas("Sello del Colegio 03/03/1856")], [])
        self.assertIsNone(_fmt("1856-03-03", "MMAA"))
        self.assertEqual(_fmt("2026-03-03", "MMAA"), "0326")

    def test_nif_encima_en_la_renta(self):
        t = ("Primer declarante\nNIF ¦ 12345678Z 0001\nApellidos y nombre ¦ RAMOS GAY MIGUEL ANGEL 0002\nSexo ¦ Hombre 0005\n"
             "Descendientes\nApellidos y nombre ¦ RAMOS FERNANDEZ MAYRA 0076\nFecha de nacimiento ¦ 04/12/2023 0077\n"
             "NIF ¦ 87654321X 0075\nApellidos y nombre ¦ RAMOS SERISOLA ARIADNA 0076\n")
        p = {x["completo"]: x["dni"] for x in personas(t)}
        self.assertEqual(p.get("Miguel Angel Ramos Gay"), "12345678Z")
        self.assertIsNone(p.get("Mayra Ramos Fernandez"))
        self.assertEqual(p.get("Ariadna Ramos Serisola"), "87654321X")

    def test_nombre_al_unir_y_separar(self):
        self.assertEqual(nombre_limpio("WhatsApp Image 2026-11-15 at 07.13.57a (+3 unidas).pdf (págs (+1 unidas).pdf (págs. 3, 4)"),
                         "WhatsApp Image 2026-11-15 at 07.13.57a")


if __name__ == "__main__":
    unittest.main()


class Noche2(unittest.TestCase):
    def test_nif_del_empresario_en_la_nomina(self):
        t = ("CALABUIG JAQUOTOT, VICENTE\nAV GASPAR 12\n46020 VALENCIA\nNIF. 12345678Z 413\nBALLESTER GARCIA, JOAN 16/1538095- 67\n"
             "N MATRIC | ANTIGUEDAD\nCALABUIG JAQUOTOT VICENTE | CONDUCTOR | 21 FEB 25 | 87654321X\n")
        p = {x["completo"]: x["dni"] for x in personas(t)}
        self.assertNotEqual(p.get("Vicente Calabuig Jaquotot"), "12345678Z")

    def test_renta_individual_y_menor(self):
        from sentiende.extraer import tributacion
        self.assertEqual(tributacion("Opción de tributación\nTributación individual ¦ X 0068"), "individual")
        t = "Descendientes\nApellidos y nombre ¦ RAMOS SERISOLA ARIADNA 0076\nFecha de nacimiento ¦ 04/12/2019 0077\n"
        self.assertTrue(any(x.get("nacimiento") == "2019-12-04" for x in personas(t)))
