# -*- coding: utf-8 -*-
"""Nombres y fechas con formatos reales (datos inventados), en castellano y valenciano."""
import unittest
from sentiende.extraer import extraer, personas
from sentiende.separar import firma, mismo_documento

def nombres(tx):
    return [p["completo"] for p in personas(tx)]

class Nombres(unittest.TestCase):
    def test_nomina_dos_cuadros(self):
        tx = "NOMINA\nTRANSPORTES LEVANTE, S.L. ¦ GARCIA PUCHADES,LAURA\nCL.ALFONSO ROIG ALFONSO, S/N ¦ 12345678Z"
        self.assertEqual(nombres(tx), ["Laura Garcia Puchades"])
    def test_padron_bilingue_valor_encima(self):
        tx = "rShr ¦ VICENT SOLER MARTI\nNom i cognoms / Nombre y apellidos\nIdentificació / Identificación ¦ 012345678-Z"
        self.assertEqual(nombres(tx), ["Vicent Soler Marti"])
    def test_renta_apellidos_y_nombre(self):
        p = personas("Primer declarante\nNIF: 12345678Z\nApellidos y nombre: PEREZ GIL JUAN CARLOS")[0]
        self.assertEqual((p["nombre"], p["apellido1"], p["apellido2"]), ("Juan Carlos", "Perez", "Gil"))
    def test_vida_laboral_d_da_salto_de_linea(self):
        self.assertIn("Laura Garcia Puchades", nombres("resulta que D/Dª\nLAURA GARCIA PUCHADES , nacido/a el 1 de marzo de 1985"))
    def test_escritura_don_y_dona(self):
        self.assertEqual(nombres("Que Don José López Marquez y Doña\nTomasa Muñoz Cara-\nballo, son dueños"), ["Jose Lopez Marquez", "Tomasa Munoz Caraballo"])
    def test_no_cuela_falsos(self):
        self.assertEqual(nombres("Representante Legal: ¦ DNI: 12345678Z\nSOLICITUD DE DEVOLUCION"), [])

class Fechas(unittest.TestCase):
    def test_periodo_texto(self):
        self.assertEqual(extraer("Periodo de liquidación: del 01 de Agosto al 31 de Agosto de 2026")["periodo"], "2026-08-01")
        self.assertEqual(extraer("Període de liquidació: del 01 d'agost al 31 d'agost de 2026")["periodo"], "2026-08-01")
    def test_emision_ciudad_y_nacimiento(self):
        d = extraer("Data / Fecha 27/03/1985\nAlta en Padrón 01/03/1991\nValència, 11/09/2026")
        self.assertEqual(d["emision"], "2026-09-11")

class Separar(unittest.TestCase):
    def test_mismo_codigo_de_verificacion(self):
        a = firma("Página uno\nCódigo Seguro de Verificación AB12CD34EF56GH78 en https://sede")
        b = firma("Otra cosa\nVerificación AB12CD34EF56GH78 en https://sede")
        self.assertTrue(mismo_documento(a, b))

if __name__ == "__main__":
    unittest.main()
