# -*- coding: utf-8 -*-
"""Contexto de lote (3.0.2): titular, cotitular, hijos fuera, DNI en 2 documentos, otros datos y deshacer. Datos inventados."""
import tempfile, threading, unittest
from pathlib import Path
from sentiende.motor import Motor
from sentiende.ia import ControladorIA
from sentiende.contexto import ContextoLote, compatibles
from pruebas.muestras import pdf_texto

VAR = Path(__file__).resolve().parent.parent / "variantes" / "sefinancia"
IBAN = "ES91 2100 0418 4502 0005 1332"


def lote_familia(t):
    m = Motor(Path(t), VAR)
    ent = Path(t) / "in"; ent.mkdir()
    pdf_texto(ent / "nomina.pdf", ["RECIBO INDIVIDUAL JUSTIFICATIVO DEL PAGO DE SALARIOS", "EMPRESA: TALLERES RUIZ SL", "TRABAJADOR: SANZ ROIG, PILAR",
                                  "DNI 23456789D", "PERIODO DE LIQUIDACION 01 SEP 26 A 30 SEP 26", "TOTAL DEVENGADO 1.900,00", "LIQUIDO A PERCIBIR 1.650,00"])
    pdf_texto(ent / "vida.pdf", ["INFORME DE VIDA LABORAL", "TESORERIA GENERAL DE LA SEGURIDAD SOCIAL", "NOMBRE Y APELLIDOS: PILAR SANZ ROIG",
                                "DNI 23456789D", "SITUACIONES DE ALTA EN EL REGIMEN GENERAL", "DIAS COTIZADOS 4.120"])
    pdf_texto(ent / "renta.pdf", ["DECLARACION DE LA RENTA MODELO 100 EJERCICIO 2025", "AGENCIA TRIBUTARIA IMPUESTO SOBRE LA RENTA DE LAS PERSONAS FISICAS",
                                 "PRIMER DECLARANTE: PILAR SANZ ROIG NIF 23456789D", "CONYUGE: JORGE GIL MAS NIF 34567890V",
                                 "DESCENDIENTES: LUCAS GIL SANZ", "BASE IMPONIBLE GENERAL 41.200,00", "CUOTA RESULTANTE 6.100,00"])
    pdf_texto(ent / "padron.pdf", ["CERTIFICADO DE EMPADRONAMIENTO", "AYUNTAMIENTO DE VALENCIA", "PADRON MUNICIPAL DE HABITANTES",
                                  "NOMBRE: PILAR SANZ ROIG DNI 23456789D", "NOMBRE: JORGE GIL MAS DNI 34567890V", "NOMBRE: LUCAS GIL SANZ"])
    pdf_texto(ent / "extracto.pdf", ["EXTRACTO DE CUENTA", "MOVIMIENTOS DE LA CUENTA " + IBAN, "TITULAR: PILAR SANZ ROIG", "TITULAR: JORGE GIL MAS",
                                    "01/09/2026 NOMINA TALLERES RUIZ 1.650,00 SALDO 3.200,00", "05/09/2026 RECIBO LUZ -60,00 SALDO 3.140,00"])
    pdf_texto(ent / "saldo.pdf", ["CERTIFICADO DE SALDO", "LA ENTIDAD CERTIFICA QUE LA CUENTA " + IBAN, "PRESENTABA A FECHA 21 DE AGOSTO DE 2026 UN SALDO DE 3.000,00 EUR"])
    lote, ids = m.recibir([ent / f for f in ("nomina.pdf", "vida.pdf", "renta.pdf", "padron.pdf", "extracto.pdf", "saldo.pdf")])
    m.procesar(lote)
    return m, lote


class TestContexto(unittest.TestCase):
    def test_nombres_compatibles(self):
        self.assertTrue(compatibles({"nombre": "Pilar", "apellido1": "Sanz", "apellido2": "Roig"}, {"nombre": "Maria Pilar", "apellido1": "Sanz", "apellido2": "Roig"}))
        self.assertTrue(compatibles({"nombre": "Monica", "apellido1": "Fernandez"}, {"nombre": "Monica", "apellido1": "Fernandez", "apellido2": "Benavides"}))
        self.assertTrue(compatibles({"nombre": "Vicente", "apellido1": "Calabuig", "apellido2": "Jaquoto"}, {"nombre": "Vicente", "apellido1": "Calabuig", "apellido2": "Jaquotot"}))
        self.assertFalse(compatibles({"nombre": "Jorge", "apellido1": "Gil", "apellido2": "Mas"}, {"nombre": "Lucas", "apellido1": "Gil", "apellido2": "Sanz"}))

    def test_lote_familia(self):
        with tempfile.TemporaryDirectory() as t:
            m, lote = lote_familia(t)
            ctrl = ControladorIA(m)
            c = ContextoLote(m, ctrl)
            ctx = c.analizar(lote)
            ids = ctx["identidades"]
            self.assertIsNotNone(ctx["titular"])
            self.assertIn("PILAR", ids[ctx["titular"]]["persona"]["completo"].upper())
            cot = [ids[n]["persona"]["completo"].upper() for n in ctx["cotitulares"]]
            self.assertTrue(any("JORGE" in x for x in cot), cot)
            self.assertFalse(any("LUCAS" in x for x in cot), "el hijo no es cotitular")
            self.assertEqual(c.pendientes(), [lote])
            r = c.aplicar(lote)
            self.assertTrue(r["creado"])
            eid = r["expediente"]
            papeles = {p["nombre"].upper(): p["papel"] for p in m.almacen.personas_de(eid)}
            self.assertEqual(papeles.get("PILAR"), "Titular")
            self.assertEqual(papeles.get("JORGE"), "Cotitular")
            self.assertEqual(len(c.notificaciones()), 1)
            guardados = m.almacen.documentos("lote_id = ? AND estado = 'guardado'", (lote,))
            self.assertGreaterEqual(len(guardados), 3, [(d["nombre_recibido"], d["tipo"], d["confianza"], d["motivo"]) for d in m.almacen.documentos("lote_id = ?", (lote,))])
            saldo = next(d for d in m.almacen.documentos("lote_id = ?", (lote,)) if d["nombre_recibido"] == "saldo.pdf")
            self.assertIn("cuenta", (ctx["docs"][saldo["id"]].get("por") or ""))          # sin nombre: por la cuenta
            self.assertEqual(c.pendientes(), [])
            # deshacer «expediente creado»: todo vuelve a la revisión y el expediente desaparece
            acc = next(x for x in ctrl.informe(lote)["acciones"] if x["tipo"] == "expediente_creado")
            ctrl.deshacer(acc["id"])
            self.assertIsNone(m.almacen.expediente(eid))
            self.assertEqual(m.almacen.documentos("lote_id = ? AND estado = 'guardado'", (lote,)), [])
            m.almacen.db.close()

    def test_ia_supervisa_el_contexto(self):
        import json
        with tempfile.TemporaryDirectory() as t:
            m, lote = lote_familia(t)
            recibido = []
            def sim(clave, modelo, sistema, mensaje, max_tokens):
                recibido.append(mensaje)
                nom = next(d for d in m.almacen.documentos("lote_id = ?", (lote,)) if d["nombre_recibido"] == "nomina.pdf")
                exp = next(x for x in mensaje.split("\n") if x.startswith("- [EXP_"))[2:9].strip(" ·")
                return json.dumps({"documentos": [{"doc": f"D{nom['id']}", "tipo": "nomina", "expediente": exp, "comun": True, "seguridad": 95, "motivo": "prueba"}]}), \
                    {"input_tokens": 1000, "output_tokens": 100}
            ctrl = ControladorIA(m, cliente=sim, descargar=lambda u, h=None: "")
            ctrl.guardar({"clave": "sk-ant-prueba"}); ctrl.encender(True)
            c = ContextoLote(m, ctrl)
            c.aplicar(lote)
            ctrl.ejecutar_lote(lote, threading.RLock())
            self.assertEqual(len(recibido), 1)
            for real in ("PILAR", "SANZ", "JORGE", "23456789", "2100 0418"):
                self.assertNotIn(real, recibido[0])
            nom = next(d for d in m.almacen.documentos("lote_id = ?", (lote,)) if d["nombre_recibido"] == "nomina.pdf")
            self.assertEqual((nom["estado"], nom["de_expediente"]), ("guardado", 1))     # corregido por la IA
            m.almacen.db.close()

    def test_dni_en_un_solo_documento_no_vale(self):
        with tempfile.TemporaryDirectory() as t:
            m = Motor(Path(t), VAR)
            ent = Path(t) / "in"; ent.mkdir()
            pdf_texto(ent / "a.pdf", ["CERTIFICADO DE ESTAR AL CORRIENTE", "AGENCIA TRIBUTARIA", "NIF 45678901G"])
            pdf_texto(ent / "b.pdf", ["CERTIFICADO DE ESTAR AL CORRIENTE", "TESORERIA GENERAL DE LA SEGURIDAD SOCIAL", "NIF 56789012B"])
            lote, ids = m.recibir([ent / "a.pdf", ent / "b.pdf"]); m.procesar(lote)
            ctx = ContextoLote(m, ControladorIA(m)).analizar(lote)
            self.assertEqual(ctx["validos"], [])
            self.assertIsNone(ctx["titular"])
            m.almacen.db.close()


if __name__ == "__main__":
    unittest.main()


class TestSeries(unittest.TestCase):
    def test_recibos_en_serie(self):
        """Recibos sin titular, misma cuenta (tapada con asteriscos) y meses distintos: se guardan juntos, cada uno con su mes."""
        with tempfile.TemporaryDirectory() as t:
            m, lote = lote_familia(t)
            c = ContextoLote(m, ControladorIA(m))
            r = c.aplicar(lote)
            eid = r["expediente"]
            ent = Path(t) / "in2"; ent.mkdir()
            for mes, dia in (("ABRIL", "01-04-2026"), ("MAYO", "04-05-2026"), ("JUNIO", "01-06-2026")):
                pdf_texto(ent / f"recibo_{mes}.pdf", ["ADEUDO POR DOMICILIACIONES SEPA", "OFICINA PATRAIX FECHA " + dia,
                                                     "IBAN: ES9121000418450******1332", "RECIBO 13 DE 72 FINANCIACION DE VEHICULO",
                                                     "IMPORTE 250,00 EUR", "TOTAL ADEUDADO 250,00 EUR"])
            lote2, _ = m.recibir(sorted(ent.iterdir()))
            m.procesar(lote2)
            ctx = c.analizar(lote2)
            self.assertEqual(len(ctx["series"]), 1, ctx.get("series"))
            # sin nombres en el lote: la cuenta ya está en el extracto y el certificado guardados → propuesta de ese expediente
            pend = m.almacen.documentos("lote_id = ? AND estado = 'espera_emparejar'", (lote2,))
            self.assertTrue(all(ctx["docs"][d["id"]].get("expediente_id") == eid for d in pend), ctx["docs"])
            c.aplicar(lote2)
            pend = m.almacen.documentos("lote_id = ? AND estado = 'espera_emparejar'", (lote2,))
            self.assertEqual(len(pend), 3)
            # Joan confirma uno en la revisión: los otros dos de la serie se guardan con la misma decisión y su mes
            g = m.emparejar(pend[0]["id"], eid, de_expediente=True)
            self.assertEqual(len(g.get("serie_guardados") or []), 2, g)
            nombres = sorted(d["nombre_final"] for d in m.almacen.documentos("lote_id = ? AND estado = 'guardado'", (lote2,)))
            self.assertEqual(len(nombres), 3)
            self.assertEqual([n.rsplit("_", 1)[-1] for n in nombres], ["0426.pdf", "0526.pdf", "0626.pdf"], nombres)   # sin «-2», «-3»
            m.almacen.db.close()


class TestManual(unittest.TestCase):
    def test_expediente_manual_es_la_referencia(self):
        """Expediente abierto a mano con un DNI casi igual al leído: se usan los datos manuales y se avisa para confirmarlo."""
        with tempfile.TemporaryDirectory() as t:
            m = Motor(Path(t), VAR)
            c = ContextoLote(m, ControladorIA(m))
            pid = m.nueva_persona("Pilar", "Sanz", "Roig", "23456780D")
            eid = m.crear_expediente(pid, "hipotecario")
            m.almacen.db.execute("UPDATE personas SET manual = 1 WHERE id = ?", (pid,)); m.almacen.db.commit()
            m.almacen.db.close()
            m, lote = lote_familia(t)
            c = ContextoLote(m, ControladorIA(m))
            r = c.aplicar(lote)
            self.assertEqual(r["expediente"], eid)                      # no crea otro expediente
            self.assertFalse(r["creado"])
            ns = [n for n in c.notificaciones() if n["tipo"] == "parecido"]
            self.assertEqual(len(ns), 1, c.notificaciones())
            self.assertIn("23456789D", ns[0]["mensaje"])
            self.assertEqual(m.almacen.persona(pid)["dni"], "23456780D")   # manda lo manual
            c.aplicar_cambio(ns[0]["id"])                                   # «Cambiar por los del documento»
            self.assertEqual(m.almacen.persona(pid)["dni"], "23456789D")
            self.assertEqual([n for n in c.notificaciones() if n["tipo"] == "parecido"], [])
            # cambiar la financiación del expediente
            m.cambiar_finalidad(eid, "licencia_taxi")
            self.assertEqual(m.almacen.expediente(eid)["finalidad"], "licencia_taxi")
            self.assertTrue(m.almacen.expediente(eid)["nombre"].endswith("Préstamo licencia taxi"))
            m.almacen.db.close()


class TestDatosLeidos(unittest.TestCase):
    def test_datos_del_expediente(self):
        from sentiende.gestion import datos_leidos
        with tempfile.TemporaryDirectory() as t:
            m, lote = lote_familia(t)
            r = ContextoLote(m, ControladorIA(m)).aplicar(lote)
            d = datos_leidos(m, r["expediente"])
            tit = next(p for p in d["personas"] if p["papel"] == "Titular")
            self.assertEqual(tit["dni"], "23456789D")
            self.assertIn("bancos", d)
            m.almacen.db.close()
