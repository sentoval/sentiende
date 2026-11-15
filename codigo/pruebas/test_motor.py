# -*- coding: utf-8 -*-
"""Pruebas del motor de principio a fin con documentos inventados.
    python -m unittest pruebas.test_motor -v      (desde la carpeta codigo)"""
import datetime, shutil, sys, tempfile, unittest
from pathlib import Path

AQUI = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AQUI))
from sentiende import version, VERSION, CONTRATO
from sentiende.motor import Motor, MotorError
from sentiende.extraer import dni_valido, iban_valido, cif_valido, extraer
from sentiende.nombres import codigo_persona, carpeta_expediente
from pruebas.muestras import generar

VARIANTE = AQUI / "variantes" / "sefinancia"

class Versiones(unittest.TestCase):
    def test_compatibilidad(self):
        v = {"nombre": "SeFinancia", "version": "1.0.0", "requiere_motor": {"contrato": 2, "minimo": "2.0.0"}}
        self.assertTrue(version.comprobar("2.0.0", 2, v).compatible)
        r = version.comprobar("2.0.0", 2, {**v, "requiere_motor": {"contrato": 3}})
        self.assertEqual((r.compatible, r.actualizar), (False, "motor"))
        r = version.comprobar("3.0.0", 3, v)
        self.assertEqual((r.compatible, r.actualizar), (False, "variante"))
        r = version.comprobar("2.0.0", 2, {**v, "requiere_motor": {"contrato": 2, "minimo": "2.1.0"}})
        self.assertEqual(r.actualizar, "motor")

class Datos(unittest.TestCase):
    def test_validaciones(self):
        self.assertEqual(dni_valido("12345678Z"), "12345678Z")
        self.assertIsNone(dni_valido("12345678A"))
        self.assertEqual(dni_valido("X1234567L"), "X1234567L")
        self.assertEqual(cif_valido("B98765431"), "B98765431")
        self.assertIsNone(cif_valido("B98765432"))
        self.assertEqual(iban_valido("ES91 2100 0418 4502 0005 1332"), "ES9121000418450200051332")
    def test_extraer(self):
        d = extraer("PERIODO DE LIQUIDACION: 01 OCT 26 a 31 OCT 26\nNIF 12345678Z\nLIQUIDO 1.984,20\nVÁLIDO HASTA 20 10 2030")
        self.assertEqual(d["periodo"], "2026-10-01")
        self.assertIn("12345678Z", d["dni"])
        self.assertIn(1984.20, d["importes"])
        self.assertEqual(d["caducidad"], "2030-10-20")
    def test_nombres(self):
        ivan = {"nombre": "Iván", "apellido1": "Morales", "apellido2": "Gil", "dni": "12345678Z"}
        self.assertEqual(codigo_persona(ivan), "IMG678")
        self.assertEqual(carpeta_expediente(ivan, datetime.date(2026, 11, 3)), "IvanMorales_45678_1126")
        self.assertEqual(codigo_persona({"nombre": "Talleres Ruiz S.L.", "dni": "B98765432", "es_empresa": True}), "TRSL432")
        self.assertEqual(codigo_persona({**ivan, "dni": None}), "IMGNOINFORMADO")

class ProcesoCompleto(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="sentiende_"))
        cls.muestras = generar(cls.tmp / "muestras")
        cls.raiz = cls.tmp / "SeFinancia"
        cls.m = Motor(cls.raiz, VARIANTE)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_todo(self):
        m, s = self.m, self.muestras
        # Las carpetas se crean solas
        for c in ["Entrada", "Doc_original", "SeDocumentos/_Limbo", "Papelera", "Datos/Trabajo"]:
            self.assertTrue((self.raiz / c).exists(), c)
        nombres = ["NOMINA OCT.pdf", "copia nomina.pdf", "extracto.pdf", "foto_dni.jpg", "vida_laboral_escaneada.pdf", "nota simple.pdf", "programa.exe", "falso.pdf"]
        lote, ids = m.recibir([s / n for n in nombres])
        self.assertEqual(len(ids), 6, "el .exe y el PDF falso no entran")
        self.assertTrue((s / "programa.exe").exists(), "lo no admitido no se toca")
        self.assertFalse((s / "NOMINA OCT.pdf").exists(), "lo recibido se mueve a Entrada")
        docs = {d["nombre_recibido"]: d for d in m.procesar(lote)}
        dup = m.almacen.documento(ids[1])
        self.assertEqual(dup["estado"], "duplicado")
        nom, dni, vl, ns, ext = (docs[n] for n in ["NOMINA OCT.pdf", "foto_dni.jpg", "vida_laboral_escaneada.pdf", "nota simple.pdf", "extracto.pdf"])
        self.assertEqual(nom["tipo"], "nomina"); self.assertEqual(nom["estado"], "espera_emparejar")
        self.assertEqual(nom["datos"]["periodo"], "2026-10-01")
        self.assertIsNone(nom["entidad"], "en una nómina el emisor es la empresa, no el banco")
        self.assertEqual(ext["tipo"], "extracto")
        self.assertEqual(ext["entidad"], "Unicaja")
        self.assertIn("IBAN", ext["entidad_por"])
        self.assertEqual(dni["tipo"], "dni")
        self.assertEqual(dni["rotaciones"][0]["rotacion"], 90, "la foto estaba girada 90° a la izquierda: se gira 90° a la derecha")
        self.assertIn("12345678Z", dni["datos"]["dni"])
        self.assertEqual(vl["tipo"], "vidalaboral")
        self.assertEqual(ns["tipo"], "notasimple")
        # Fase 7: sugerencia por DNI todavía sin persona conocida
        self.assertEqual(m.sugerencias(nom["id"]), [])
        pid = m.nueva_persona("Iván", "Morales", "Gil", "12345678Z")
        eid = m.crear_expediente(pid, "hipotecario", datetime.date(2026, 11, 3))
        self.assertEqual(m.almacen.expediente(eid)["carpeta"], "IvanMorales_45678_1126")
        self.assertEqual(len(m.sugerencias(nom["id"])), 1)
        g = m.emparejar(nom["id"], eid, pid)
        self.assertEqual(g["nombre_final"], "IMG678_nomina_1026.pdf")
        self.assertTrue(Path(g["ruta_final"]).exists())
        self.assertTrue(Path(g["ruta_original_final"]).exists())
        self.assertIn("Doc_original", g["ruta_original_final"])
        g = m.emparejar(dni["id"], eid, pid)
        self.assertEqual(g["nombre_final"], "IMG678_dni_30.pdf")
        g = m.emparejar(vl["id"], eid, pid)
        self.assertEqual(g["nombre_final"], "IMG678_vidalaboral_1126.pdf")
        g = m.emparejar(ext["id"], eid, pid)
        self.assertEqual(g["nombre_final"], "IMG678_extracto_UNICA_1026.pdf")
        g = m.emparejar(ns["id"], eid, de_expediente=True)
        self.assertEqual(g["nombre_final"], "IMG678_notasimple_1126.pdf")
        # Checklist
        from sentiende import checklist
        r = checklist.evaluar(m.variante, m.almacen, eid, hoy=datetime.date(2026, 11, 15))
        est = {f["tipo"]: f["estado"] for f in r["filas"]}
        self.assertEqual(est["dni"], "Recibido")
        self.assertEqual(est["nomina"], "Incompleto")
        self.assertEqual(est["vidalaboral"], "Recibido")
        self.assertEqual(est["notasimple"], "Recibido")
        self.assertEqual(est["tasacion"], "Pendiente")
        self.assertEqual(r["total"], 9)
        # Avisos Cliente sin repetir: uno por cosa que falta
        avs = [x["mensaje"] for x in m.almacen.avisos_cliente(eid)]
        self.assertEqual(len(avs), len(set(avs)))
        self.assertTrue(any("Nómina" in x for x in avs))
        # Registro de texto del expediente: IMG678_textos.txt con todos los documentos y su texto
        reg = self.raiz / "SeDocumentos" / "IvanMorales_45678_1126" / "IMG678_textos.txt"
        self.assertTrue(reg.exists())
        txt = reg.read_text(encoding="utf-8-sig")
        for n in ["IMG678_nomina_1026.pdf", "IMG678_dni_30.pdf", "IMG678_vidalaboral_1126.pdf", "IMG678_notasimple_1126.pdf"]:
            self.assertEqual(txt.count("ARCHIVO:   " + n), 1, n)
        self.assertIn("LIQUIDO A PERCIBIR", txt)
        self.assertIn("VIDA LABORAL", txt.upper())
        # Datos temporales: se pueden consultar y vaciar sin perder el registro
        self.assertGreater(m.temporales()["textos_paginas"], 0)
        m.vaciar_textos()
        self.assertEqual(m.temporales()["textos_paginas"], 0)
        m.regenerar_textos(eid)
        self.assertIn("LIQUIDO A PERCIBIR", reg.read_text(encoding="utf-8-sig"), "rehacer tras vaciar la memoria no pierde el texto")
        # La copia de trabajo se vacía al guardar
        self.assertFalse(any((self.raiz / "Datos" / "Trabajo").rglob("*.jpg")))
        # Reanudar: un segundo procesar no repite nada
        self.assertEqual(m.procesar(), [])

class SepararYNombres(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="sentiende_sep_"))
        cls.muestras = generar(cls.tmp / "muestras")
        cls.raiz = cls.tmp / "SeFinancia"
        cls.m = Motor(cls.raiz, VARIANTE)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_nombres_leidos(self):
        from sentiende.extraer import personas
        p = personas("TRABAJADOR: MORALES GIL, IVAN   NIF 12345678Z")[0]
        self.assertEqual((p["nombre"], p["apellido1"], p["apellido2"], p["dni"]), ("Ivan", "Morales", "Gil", "12345678Z"))
        p = personas("D. JUAN DE LA FUENTE GARCIA con DNI 11111111H")[0]
        self.assertEqual((p["apellido1"], p["apellido2"]), ("De La Fuente", "Garcia"))
        p = personas("Apellidos y nombre: MARTINEZ DE LA ROSA, ANA MARIA  NIF 12345678Z")[0]
        self.assertEqual((p["nombre"], p["apellido1"], p["apellido2"]), ("Ana Maria", "Martinez", "De La Rosa"))

    def test_pdf_mezclado(self):
        m = self.m
        lote, ids = m.recibir([self.muestras / "escaneo_mezclado.pdf"])
        m.procesar(lote)
        padre = m.almacen.documento(ids[0])
        self.assertEqual(padre["estado"], "separado")
        partes = m.almacen.documentos("padre_id = ?", (ids[0],))
        self.assertEqual([(p["tipo"], p["paginas_sel"]) for p in partes],
                         [("nomina", [1]), ("vidalaboral", [2, 4]), ("notasimple", [3])], "3 documentos; la pág. 5 en blanco se aparta")
        nom, vl, ns = partes
        # Nombres leídos y persona creada desde el documento
        self.assertEqual(m.personas_leidas(nom["id"])[0]["completo"], "Ivan Morales Gil")
        pid = m.persona_desde_documento(nom["id"])
        self.assertEqual(m.almacen.persona(pid)["dni"], "12345678Z")
        eid = m.crear_expediente(pid, "hipotecario", datetime.date(2026, 11, 3))
        self.assertTrue(any(s["por"].startswith("DNI") for s in m.sugerencias(vl["id"])))
        g = m.emparejar(nom["id"], eid, pid)
        self.assertEqual(g["nombre_final"], "IMG678_nomina_0926.pdf")
        self.assertIsNone(g["ruta_original_final"], "el original espera a que se guarden todas las partes")
        self.assertTrue(Path(padre["ruta_original"]).exists())
        g = m.emparejar(vl["id"], eid, pid)
        self.assertEqual(g["nombre_final"], "IMG678_vidalaboral_1126.pdf")
        from pypdf import PdfReader
        r = PdfReader(g["ruta_final"])
        self.assertEqual(len(r.pages), 2, "la vida laboral queda con sus 2 páginas, ya juntas y en orden")
        self.assertIn("Página 2 de 2", r.pages[1].extract_text())
        g = m.emparejar(ns["id"], eid, de_expediente=True)
        self.assertTrue(Path(g["ruta_original_final"]).exists(), "con la última parte, el original va a Doc_original")
        self.assertFalse(Path(padre["ruta_original"]).exists())
        txt = (self.raiz / "SeDocumentos" / "IvanMorales_45678_1126" / "IMG678_textos.txt").read_text(encoding="utf-8-sig")
        self.assertIn("pág. 4 del archivo recibido", txt)

if __name__ == "__main__":
    unittest.main(verbosity=2)
