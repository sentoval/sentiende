# -*- coding: utf-8 -*-
"""Genera documentos de ejemplo inventados para probar el motor (ningún dato real)."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

def iban_es(entidad, oficina="0001", dc="00", cuenta="1234567890"):
    bban = entidad + oficina + dc + cuenta
    num = int("".join(str(int(c, 36)) for c in bban + "ES00"))
    return f"ES{98 - num % 97:02d}{bban}"

def fuente(t=34):
    for f in ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "C:/Windows/Fonts/arial.ttf"]:
        if Path(f).exists():
            return ImageFont.truetype(f, t)
    return ImageFont.load_default()

def pdf_texto(ruta, lineas):
    c = canvas.Canvas(str(ruta), pagesize=A4)
    y = 800
    for l in lineas:
        c.drawString(50, y, l); y -= 18
    c.save()

def imagen_texto(lineas, ancho=1700, alto=1100, tam=34):
    img = Image.new("RGB", (ancho, alto), "white")
    d = ImageDraw.Draw(img)
    f = fuente(tam)
    y = 60
    for l in lineas:
        d.text((60, y), l, fill="black", font=f); y += int(tam * 1.6)
    return img

def generar(dest):
    dest = Path(dest); dest.mkdir(parents=True, exist_ok=True)
    iban = iban_es("2103")                      # Unicaja
    nomina = ["RECIBO INDIVIDUAL JUSTIFICATIVO DEL PAGO DE SALARIOS", "EMPRESA: TRANSPORTES LEVANTE S.L.   CIF B98765431",
              "TRABAJADOR: MORALES GIL, IVAN   NIF 12345678Z   N.A.F. 46/12345678/90",
              "PERIODO DE LIQUIDACION: 01 OCT 26 a 31 OCT 26", "SALARIO BASE 1.650,00  PLUS CONVENIO 320,00",
              "TOTAL DEVENGADO 2.412,77", "DEDUCCIONES: CONTINGENCIAS COMUNES  IRPF", "LIQUIDO A PERCIBIR 1.984,20",
              f"TRANSFERENCIA A: {iban[:4]} {iban[4:8]} {iban[8:12]} {iban[12:16]} {iban[16:20]} {iban[20:]}"]
    pdf_texto(dest / "NOMINA OCT.pdf", nomina)
    (dest / "copia nomina.pdf").write_bytes((dest / "NOMINA OCT.pdf").read_bytes())
    dni = imagen_texto(["ESPAÑA  DOCUMENTO NACIONAL DE IDENTIDAD", "APELLIDOS  MORALES GIL", "NOMBRE  IVAN",
                        "SEXO M   NACIONALIDAD ESP", "FECHA DE NACIMIENTO 14 03 1985", "NUM SOPORT BAA123456",
                        "VALIDO HASTA 20 10 2030", "DNI 12345678Z"])
    dni.rotate(90, expand=True).save(dest / "foto_dni.jpg", quality=90)
    vl = imagen_texto(["TESORERIA GENERAL DE LA SEGURIDAD SOCIAL", "INFORME DE VIDA LABORAL", "",
                       "D./Dña. IVAN MORALES GIL   DNI 12345678Z", "Fecha de emisión: 10/11/2026",
                       "Situación: ALTA  TRANSPORTES LEVANTE S.L.", "Días de alta: 4.210"], 1700, 2200)
    vl.save(dest / "vida_laboral_escaneada.pdf", "PDF", resolution=200)
    pdf_texto(dest / "nota simple.pdf", ["REGISTRO DE LA PROPIEDAD DE VALENCIA N.º 3", "NOTA SIMPLE INFORMATIVA",
              "Fecha: 02/11/2026", "FINCA DE VALENCIA N.º 12345 · REFERENCIA CATASTRAL 1234567YJ2713S0001AB",
              "TITULARIDAD: JOSE PEREZ NAVARRO, 87654321X", "CARGAS: NO HAY CARGAS REGISTRADAS"])
    pdf_texto(dest / "extracto.pdf", ["UNICAJA BANCO", "CONSULTA DE MOVIMIENTOS", f"IBAN {iban[:4]} {iban[4:8]} {iban[8:12]} {iban[12:16]} {iban[16:20]} {iban[20:]}",
              "TITULAR: MORALES GIL IVAN", "PERIODO: 01/10/2026 - 31/10/2026", "FECHA VALOR   CONCEPTO   IMPORTE   SALDO",
              "05/10/2026  TRANSFERENCIA RECIBIDA NOMINA  1.984,20  3.210,55", "12/10/2026  BIZUM  -25,00  3.185,55", "SALDO ANTERIOR 1.226,35"])
    # PDF mezclado: nómina · vida laboral pág. 1/2 · nota simple · vida laboral pág. 2/2 · página en blanco
    c = canvas.Canvas(str(dest / "escaneo_mezclado.pdf"), pagesize=A4)
    paginas = [
        ["RECIBO INDIVIDUAL JUSTIFICATIVO DEL PAGO DE SALARIOS", "TRABAJADOR: MORALES GIL, IVAN   NIF 12345678Z",
         "PERIODO DE LIQUIDACION: 01 SEP 26 a 30 SEP 26", "TOTAL DEVENGADO 2.398,10", "LIQUIDO A PERCIBIR 1.970,05"],
        ["TESORERIA GENERAL DE LA SEGURIDAD SOCIAL", "INFORME DE VIDA LABORAL", "D./Dña. IVAN MORALES GIL   DNI 12345678Z",
         "Fecha de emisión: 12/11/2026", "Página 1 de 2"],
        ["REGISTRO DE LA PROPIEDAD DE VALENCIA N.º 3", "NOTA SIMPLE INFORMATIVA", "Fecha: 05/11/2026",
         "TITULARIDAD: JOSE PEREZ NAVARRO, 87654321X", "CARGAS: NO HAY CARGAS REGISTRADAS"],
        ["SITUACIONES DEL TRABAJADOR", "REGIMEN GENERAL  TRANSPORTES LEVANTE S.L.  ALTA 01/03/2022", "Página 2 de 2"],
        [],
    ]
    for lineas in paginas:
        y = 800
        for l in lineas:
            c.drawString(50, y, l); y -= 18
        c.showPage()
    c.save()
    (dest / "programa.exe").write_bytes(b"MZ\x90\x00 no es un documento")
    (dest / "falso.pdf").write_bytes(b"MZ esto no es un PDF")
    return dest
