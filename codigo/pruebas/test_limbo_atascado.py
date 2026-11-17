# -*- coding: utf-8 -*-
"""3.1.2b · DNI de Joan atascado: guardado en el Limbo, «parado» buscando el original en Entrada.
Al emparejarlo después tiene que recuperarse y guardarse en su expediente sin perder nada."""
import tempfile, unittest, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PIL import Image
from sentiende.motor import Motor

VAR = Path(__file__).resolve().parents[1] / "variantes" / "sefinancia"


class LimboAtascado(unittest.TestCase):
    def test_recupera_y_guarda(self):
        with tempfile.TemporaryDirectory() as t:
            m = Motor(Path(t), VAR); a = m.almacen; c = m.carpetas
            pid = a.nueva_persona("Joan", "Ballester", "Garcia", "12345678Z")
            eid = a.nuevo_expediente("Ballester Garcia", "hipotecario", "JoanBallester_45678_1126")
            a.anadir_persona(eid, pid, "Titular")
            lote = a.nuevo_lote("correo")
            c.limbo.mkdir(parents=True, exist_ok=True); c.originales_limbo.mkdir(parents=True, exist_ok=True)
            orig = c.originales_limbo / "DNI JOAN.jpg"; Image.new("RGB", (400, 260), "white").save(orig, "JPEG")
            limbo_pdf = c.limbo / "NOINFORMADO_dni_1126.pdf"; Image.new("RGB", (400, 260), "white").save(limbo_pdf, "PDF")
            did = a.nuevo_documento(lote, "DNI JOAN.jpg", str(c.entrada / "DNI JOAN.jpg"), "h1", ".jpg")
            a.actualizar(did, estado="espera_emparejar", tipo="dni", confianza=1.0, paginas=1, fase=9,
                         ruta_final=str(limbo_pdf), ruta_original_final=str(orig), datos={})
            m.emparejar(did, eid, pid)
            d = a.documento(did)
            self.assertEqual(d["estado"], "guardado")
            self.assertTrue(Path(d["ruta_final"]).exists())
            self.assertTrue(Path(d["ruta_original_final"]).exists())
            self.assertIn("JoanBallester_45678_1126", d["ruta_original_final"])
            self.assertFalse(limbo_pdf.exists())
            a.db.close()

    def test_no_guarda_dos_veces_en_el_limbo(self):
        with tempfile.TemporaryDirectory() as t:
            m = Motor(Path(t), VAR); a = m.almacen
            lote = a.nuevo_lote("correo")
            did = a.nuevo_documento(lote, "x.jpg", str(Path(t) / "no_existe.jpg"), "h2", ".jpg")
            a.actualizar(did, estado="limbo", fase=10)
            self.assertEqual(m.al_limbo(did)["estado"], "limbo")
            a.db.close()


if __name__ == "__main__":
    unittest.main()
