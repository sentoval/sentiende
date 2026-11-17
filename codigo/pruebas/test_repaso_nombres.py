# -*- coding: utf-8 -*-
"""3.1.2 · repaso de nombres tras guardar: el primero de una serie coge su mes y el DNI aprendido sustituye a NOINFORMADO."""
import tempfile, unittest, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sentiende.motor import Motor
from sentiende.arreglos import repasar_nombres

VAR = Path(__file__).resolve().parents[1] / "variantes" / "sefinancia"


class RepasoNombres(unittest.TestCase):
    def test_serie_y_dni(self):
        with tempfile.TemporaryDirectory() as t:
            m = Motor(Path(t), VAR); a = m.almacen
            pid = a.nueva_persona("Ana", "Pons", "Vila")
            eid = a.nuevo_expediente("Pons Vila", "hipotecario", "AnaPons_NOINFORMADO_1126")
            a.anadir_persona(eid, pid, "Titular")
            carpeta = m.carpetas.documentos / "AnaPons_NOINFORMADO_1126"; carpeta.mkdir(parents=True)
            lote = a.nuevo_lote("prueba")
            ids = []
            for mes, nombre in (("2026-04-05", "APVNOINFORMADO_prestamo_CAJAM.pdf"), ("2026-05-05", "APVNOINFORMADO_prestamo_CAJAM_0526.pdf")):
                f = carpeta / nombre; f.write_bytes(b"%PDF-1.4")
                did = a.nuevo_documento(lote, nombre, str(f), mes, ".pdf")
                a.actualizar(did, estado="guardado", tipo="prestamo", entidad="Cajamar", expediente_id=eid, persona_id=pid, fase=10,
                             nombre_final=nombre, ruta_final=str(f), datos={"prestamos": ["5903"], "cuentas": [], "emision": mes, "fechas": [mes]})
                ids.append(did)
            a.db.execute("UPDATE personas SET dni = '12345678Z' WHERE id = ?", (pid,)); a.db.commit()
            repasar_nombres(m, a.documento(ids[1]))
            nombres = sorted(a.documento(i)["nombre_final"] for i in ids)
            self.assertEqual(nombres, ["APV678_prestamo_CAJAM_0426.pdf", "APV678_prestamo_CAJAM_0526.pdf"])
            self.assertTrue(all(Path(a.documento(i)["ruta_final"]).exists() for i in ids))
            self.assertEqual(a.expediente(eid)["carpeta"], "AnaPons_45678_1126")           # la carpeta también coge el DNI
            self.assertFalse(carpeta.exists())
            self.assertTrue(all("AnaPons_45678_1126" in a.documento(i)["ruta_final"] for i in ids))
            m.almacen.db.close()


if __name__ == "__main__":
    unittest.main()
