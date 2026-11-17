# -*- coding: utf-8 -*-
"""3.1.2 · hojas sueltas parecidas (solo se propone) y relectura al girar una página a mano."""
import tempfile, unittest, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PIL import Image, ImageDraw, ImageFont
from sentiende.motor import Motor

VAR = Path(__file__).resolve().parents[1] / "variantes" / "sefinancia"
FUENTE = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def hoja(ruta, lineas, giro=0):
    img = Image.new("RGB", (1000, 1300), (250, 248, 240)); d = ImageDraw.Draw(img)
    f = ImageFont.truetype(FUENTE, 30) if Path(FUENTE).exists() else None
    d.rectangle((60, 40, 940, 120), fill=(30, 60, 140))
    for i, l in enumerate(lineas):
        d.text((80, 180 + i * 70), l, fill=(20, 20, 20), font=f)
    if giro:
        img = img.rotate(giro, expand=True)
    img.save(ruta, "JPEG"); return ruta


class Parecido(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); t = Path(self.tmp.name)
        self.m = Motor(t, VAR); self.a = self.m.almacen; self.t = t
        self.lote = self.a.nuevo_lote("prueba")

    def tearDown(self):
        self.a.db.close(); self.tmp.cleanup()

    def doc(self, nombre, lineas, tipo=None, conf=0.3, giro=0):
        ruta = hoja(self.t / nombre, lineas, giro)
        did = self.a.nuevo_documento(self.lote, nombre, str(ruta), nombre, ".jpg")
        self.a.actualizar(did, estado="espera_emparejar", tipo=tipo, confianza=conf, paginas=1, fase=6,
                          rotaciones=[{"n": 1, "imagen": str(ruta), "origen": "ocr"}])
        self.a.guardar_texto(f"{nombre}:1", "\n".join(lineas), "ocr", 0.7, 0)
        return did

    def test_propone_hojas_seguidas(self):
        x = self.doc("IMG_0012.jpg", ["Solicitud de préstamo", "1. Solicitante", "2. Importe que solicita", "3. Actividad"])
        y = self.doc("IMG_0013.jpg", ["4. Bienes del solicitante", "5. Otros datos", "Firma"])
        prop = self.m.propuestas_union()
        g = next(p for p in prop if x in p["documentos"])
        self.assertEqual(g["documentos"], [x, y])
        self.assertGreaterEqual(g["porcentaje"], 60)
        self.assertIn("los apartados siguen", g["motivos"])
        self.m.no_unir([x, y])                                  # «No, son distintos»: no se vuelve a proponer
        self.assertFalse([p for p in self.m.propuestas_union() if x in p["documentos"]])
        r = self.a.db.execute("SELECT fallos FROM parecido_aprendido WHERE senal = 'apartados'").fetchone()
        self.assertEqual(r[0], 1)

    def test_no_junta_tipos_claros_distintos(self):
        x = self.doc("IMG_0020.jpg", ["NÓMINA", "1. Devengos", "2. Deducciones"], "nomina", 0.95)
        self.doc("IMG_0021.jpg", ["3. Saldo", "Cuenta"], "saldo", 0.9)
        self.assertFalse([p for p in self.m.propuestas_union() if x in p["documentos"]])

    def test_relee_al_girar(self):
        x = self.doc("dni.jpg", ["DOCUMENTO NACIONAL DE IDENTIDAD", "APELLIDOS PONS VILA", "NOMBRE ANA"], giro=90)
        self.a.guardar_texto("dni.jpg:1", "bui", "ocr", 0.1, 0)
        self.m.gestion.girar(x, 1, 90)
        self.assertIn("IDENTIDAD", self.a.texto_cache("dni.jpg:1")["texto"])
        self.assertEqual(self.a.documento(x)["tipo"], "dni")


if __name__ == "__main__":
    unittest.main()
