# -*- coding: utf-8 -*-
"""Estado de la operación, honorarios, favorito/prioridad y Papelera (datos inventados, sin OCR)."""
import tempfile, unittest
from pathlib import Path
from sentiende.motor import Motor

VAR = Path(__file__).resolve().parent.parent / "variantes" / "sefinancia"


class TestGestion(unittest.TestCase):
    def test_operacion_y_papelera(self):
        with tempfile.TemporaryDirectory() as t:
            m = Motor(Path(t), VAR); g = m.gestion
            pid = m.nueva_persona("Ivan", "Morales", "Gil", "12345678Z")
            eid = m.crear_expediente(pid, "hipotecario")
            self.assertEqual(g.operacion(eid)["etiqueta"], "Abierto")
            g.guardar_operacion(eid, {"importe_solicitado": "200000", "honorarios_tipo": "porcentaje", "honorarios_valor": "1,5"})
            self.assertEqual(g.cambiar_estado(eid, "enviado")["etiqueta"], "Enviado al banco")
            op = g.cambiar_estado(eid, "firmado", {"importe_concedido": "180000", "entidad": "CaixaBank"})
            self.assertEqual((op["estado"], op["datos"]["honorarios_importe"]), ("firmado", 2700.0))
            e = g.estadisticas()
            self.assertEqual((e["cuenta"]["firmados"], e["honorarios_pendientes"]), (1, 2700.0))
            g.marcar(eid, favorito=True, prioridad="alta")
            self.assertEqual(g.marcas()[eid], {"favorito": True, "prioridad": "alta"})
            with self.assertRaises(Exception):
                g.cambiar_estado(eid, "cerrado", {})            # sin motivo, no
            (m.carpetas.documentos / m.almacen.expediente(eid)["carpeta"] / "x.pdf").write_bytes(b"%PDF-1.4")
            g.eliminar_expediente(eid)
            self.assertEqual(m.almacen.expediente(eid)["estado"], "papelera")
            g.restaurar(g.papelera()[0]["id"])
            self.assertEqual(m.almacen.expediente(eid)["estado"], "firmado")
            self.assertTrue((m.carpetas.documentos / m.almacen.expediente(eid)["carpeta"] / "x.pdf").exists())
            m.almacen.db.close()          # en Windows, la carpeta temporal no se borra con la base abierta


if __name__ == "__main__":
    unittest.main()
