# -*- coding: utf-8 -*-
"""Controlador IA (v3.0) con una IA simulada: no sale nada a internet. Datos inventados."""
import json, tempfile, threading, unittest
from pathlib import Path
from sentiende.motor import Motor
from sentiende import ia as IA
from pruebas.muestras import pdf_texto

VAR = Path(__file__).resolve().parent.parent / "variantes" / "sefinancia"


class Simulada:
    """Responde lo que se le diga y guarda lo que recibe."""
    def __init__(self, respuestas, uso=None):
        self.respuestas, self.recibido = list(respuestas), []
        self.uso = uso or {"input_tokens": 3000, "output_tokens": 200, "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0}

    def __call__(self, clave, modelo, sistema, mensaje, max_tokens):
        self.recibido.append((sistema, mensaje))
        r = self.respuestas.pop(0) if self.respuestas else {"seguridad": 0, "motivo": "?"}
        return (r if isinstance(r, str) else json.dumps(r)), dict(self.uso)


def preparar(t):
    m = Motor(Path(t), VAR)
    pid = m.nueva_persona("Maria Pilar", "Sanz", "Roig", "23456789D")
    eid = m.crear_expediente(pid, "hipotecario")
    ent = Path(t) / "in"; ent.mkdir()
    pdf_texto(ent / "certificado.pdf", ["CERTIFICADO DE EMPRESA", "TALLERES RUIZ S.L. CIF B98765431 certifica que",
                                       "D.ª PILAR SANZ ROIG con DNI 23456789 presta servicios desde 03/02/2019",
                                       "con un salario bruto anual de 24.600,00 EUR. Telefono 612 345 678",
                                       "Domicilio: CALLE MAYOR 12, 3 B. Correo pilar.sanz@ejemplo.es",
                                       "Codigo seguro de verificacion: ABC123DEF456GHI", "Valencia, a 12 de octubre de 2026"])
    lote, ids = m.recibir([ent / "certificado.pdf"])
    m.procesar(lote)
    return m, pid, eid, lote, ids[0]


class TestIA(unittest.TestCase):
    def test_tapa_datos_y_pistas(self):
        with tempfile.TemporaryDirectory() as t:
            m, pid, eid, lote, did = preparar(t)
            c = IA.ControladorIA(m)
            prep = c.preparar(did)
            msg = prep["mensaje"]
            for real in ("PILAR", "SANZ", "ROIG", "23456789", "612", "MAYOR 12", "EJEMPLO.ES", "ABC123DEF456GHI", "B98765431"):
                self.assertNotIn(real, msg, f"se ha colado {real}")
            self.assertIn("24.600,00", msg)                        # los importes sí se envían
            self.assertIn("[EXP_A]", msg)
            self.assertIn("cifras iguales, falta la letra", msg)    # pista del DNI sin letra
            self.assertIn("nombre compuesto incompleto", msg)       # Pilar / Maria Pilar
            self.assertNotIn("SANZ", c.manual())
            m.almacen.db.close()

    def test_asigna_deshace_y_limites(self):
        with tempfile.TemporaryDirectory() as t:
            m, pid, eid, lote, did = preparar(t)
            sim = Simulada([])
            c = IA.ControladorIA(m, cliente=sim, descargar=lambda u, h=None: "")
            c.guardar({"clave": "sk-ant-prueba"})
            c.encender(True)
            prep = c.preparar(did)
            leida = prep["leidas"][0]["ficha"]
            sim.respuestas = [{"tipo": "certificado_empresa" if "certificado_empresa" in m.variante.docs else m.almacen.documento(did)["tipo"] or "vida_laboral",
                               "persona": "[PERSONA_1]", "expediente": "[EXP_A]", "misma_persona": [{"es": leida, "igual_a": "[PERSONA_1]"}],
                               "seguridad": 95, "motivo": "Mismo DNI sin letra y nombre abreviado."}]
            r = c.ejecutar_lote(lote, threading.RLock())
            self.assertEqual(r["consultas"], 1)
            d = m.almacen.documento(did)
            self.assertEqual((d["estado"], d["expediente_id"]), ("guardado", eid))
            acc = {x["tipo"]: x for x in c.informe(lote)["acciones"]}
            self.assertIn("asignado", acc)
            self.assertEqual(acc["misma_persona"]["estado"], "por_revisar")       # siempre como aviso
            self.assertIn("PILAR SANZ ROIG", m.almacen.persona(pid)["alias"])
            self.assertGreater(c.resumen()["hoy"], 0)
            # deshacer «misma persona»: vuelve todo a la revisión y se quita el alias
            c.deshacer(acc["misma_persona"]["id"])
            d = m.almacen.documento(did)
            self.assertEqual(d["estado"], "espera_emparejar")
            self.assertNotIn("PILAR SANZ ROIG", m.almacen.persona(pid)["alias"])
            self.assertFalse(list((m.carpetas.documentos / m.almacen.expediente(eid)["carpeta"]).glob("*.pdf")))
            # Joan lo guarda a mano después: el original pasa a su sitio y se aprende
            g = m.emparejar(did, eid, pid, tipo=d["tipo"] or "vida_laboral")
            self.assertEqual(g["estado"], "guardado")
            self.assertTrue(Path(g["ruta_original_final"]).exists())
            c.aprender_correccion(did)
            self.assertGreaterEqual(m.almacen.db.execute("SELECT COUNT(*) FROM ia_ejemplos").fetchone()[0], 1)
            # límite del día: con 0,0001 € no cabe ninguna consulta y se pausa
            c.guardar({"limite_dia": 0.5, "limite_lote": 5})
            m.almacen.db.execute("INSERT INTO ia_consultas(fecha, lote_id, coste_usd) VALUES(?, ?, ?)", (IA.ahora(), lote, 0.6)); m.almacen.db.commit()
            prep2 = c.preparar(did)
            with self.assertRaises(IA.LimiteAlcanzado):
                c._consultar(prep2, lote, did, "documento", threading.RLock())
            self.assertEqual(c.resumen()["estado"], "pausa")
            m.almacen.db.close()

    def test_nunca_crea_expedientes(self):
        with tempfile.TemporaryDirectory() as t:
            m, pid, eid, lote, did = preparar(t)
            sim = Simulada([{"tipo": None, "expediente": "NUEVO", "seguridad": 80, "motivo": "Persona sin expediente."}])
            c = IA.ControladorIA(m, cliente=sim, descargar=lambda u, h=None: "")
            c.guardar({"clave": "sk-ant-prueba"}); c.encender(True)
            n = m.almacen.db.execute("SELECT COUNT(*) FROM expedientes").fetchone()[0]
            c.ejecutar_lote(lote, threading.RLock())
            self.assertEqual(m.almacen.db.execute("SELECT COUNT(*) FROM expedientes").fetchone()[0], n)
            self.assertEqual(m.almacen.documento(did)["estado"], "espera_emparejar")
            self.assertEqual(c.informe(lote)["acciones"][0]["estado"], "para_ti")
            m.almacen.db.close()

    def test_separar_y_deshacer(self):
        with tempfile.TemporaryDirectory() as t:
            m = Motor(Path(t), VAR)
            from reportlab.pdfgen import canvas
            ent = Path(t) / "in"; ent.mkdir()
            c0 = canvas.Canvas(str(ent / "dos.pdf"))
            for txt in ("RECIBO DE SALARIOS OCTUBRE LIQUIDO A PERCIBIR 1.900,00", "RECIBO DE SALARIOS SEPTIEMBRE LIQUIDO A PERCIBIR 1.850,00"):
                c0.drawString(50, 800, txt); c0.showPage()
            c0.save()
            lote, ids = m.recibir([ent / "dos.pdf"]); m.procesar(lote)
            padre = [d for d in m.almacen.documentos("lote_id = ?", (lote,)) if d["estado"] == "espera_emparejar"][0]["id"]
            sim = Simulada([{"separar": [[1], [2]], "seguridad": 92, "motivo": "Dos meses distintos."}])
            c = IA.ControladorIA(m, cliente=sim, descargar=lambda u, h=None: "")
            c.guardar({"clave": "sk-ant-prueba"}); c.encender(True)
            c.ejecutar_lote(lote, threading.RLock())
            sep = [x for x in c.informe(lote)["acciones"] if x["tipo"] == "separado"][0]
            self.assertEqual(m.almacen.documento(padre)["estado"], "separado")
            c.deshacer(sep["id"])
            self.assertEqual(m.almacen.documento(padre)["estado"], "espera_emparejar")
            self.assertEqual({d["estado"] for d in m.almacen.documentos("padre_id = ?", (padre,))}, {"deshecho"})
            m.almacen.db.close()

    def test_respuesta_vacia_no_para_el_lote(self):
        with tempfile.TemporaryDirectory() as t:
            m, pid, eid, lote, did = preparar(t)
            sim = Simulada(["", ""])          # la IA no contesta nada útil
            c = IA.ControladorIA(m, cliente=sim, descargar=lambda u, h=None: "")
            c.guardar({"clave": "sk-ant-prueba"}); c.encender(True)
            r = c.ejecutar_lote(lote, threading.RLock())
            self.assertIsNone(r["parado"])
            acc = c.informe(lote)["acciones"]
            self.assertEqual((acc[0]["tipo"], acc[0]["titulo"]), ("para_ti", "Sin respuesta"))
            self.assertEqual(len(sim.recibido), 1)          # no se repite la consulta del mismo documento
            m.almacen.db.close()

    def test_reintenta_si_se_queda_sin_margen(self):
        llamadas = []
        def falso(clave, modelo, sistema, mensaje, max_tokens, timeout):
            llamadas.append(max_tokens)
            return ("", {"output_tokens": max_tokens}, "max_tokens") if len(llamadas) == 1 else ('{"seguridad": 50}', {"output_tokens": 300}, "end_turn")
        orig = IA._llamar
        IA._llamar = falso
        try:
            texto, uso = IA.llamar_api("k", "claude-haiku-5-5", "s", "m")
        finally:
            IA._llamar = orig
        self.assertEqual(llamadas, [4000, 8000])
        self.assertEqual(uso["output_tokens"], 4300)
        self.assertIn("seguridad", texto)

    def test_tarifas_una_vez_al_dia(self):
        with tempfile.TemporaryDirectory() as t:
            m = Motor(Path(t), VAR)
            pagina = ("<table><tr><td>Haiku 5.5 (≤100k)</td><td>$0.10</td><td>$0.125</td><td>$0.20</td><td>$0.01</td><td>$0.50</td></tr>"
                      "<tr><td>Sonnet 5.5</td><td>$2</td><td>$2.50</td><td>$4</td><td>$0.10</td><td>$10</td></tr>"
                      "<tr><td>Opus 5.5</td><td>$3</td><td>$5</td><td>$8</td><td>$0.20</td><td>$20</td></tr></table>")
            veces = []
            c = IA.ControladorIA(m, descargar=lambda u, h=None: veces.append(u) or pagina)
            r = c.comprobar_tarifas()
            self.assertEqual(r["estado"], "cambios")                 # Opus: 4 → 3
            self.assertEqual(r["cambios"]["claude-opus-5-5"]["entrada"], [4.0, 3.0])
            c.comprobar_tarifas(); c.comprobar_tarifas()             # mismo día: no se repite
            self.assertEqual(len(veces), 1)
            c.actualizar_tarifas()
            self.assertEqual(c.ajustes()["precios"]["claude-opus-5-5"]["entrada"], 3.0)
            self.assertAlmostEqual(IA.coste(IA.PRECIOS, "claude-haiku-5-5", {"input_tokens": 50_000}), 0.005)
            self.assertAlmostEqual(IA.coste(IA.PRECIOS, "claude-haiku-5-5", {"input_tokens": 200_000}), 0.10)   # tramo largo ×5
            m.almacen.db.close()


if __name__ == "__main__":
    unittest.main()
