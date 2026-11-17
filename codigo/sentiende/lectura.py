# -*- coding: utf-8 -*-
"""Fases 2 y 4 · Leer, orientar y enderezar (M-02, M-04, M-61).

- PDF con texto: se usa ese texto (instantáneo y sin errores).
- Escaneos, fotos y páginas sin texto: OCR con Tesseract, en este equipo.
- Antes del OCR se detecta la orientación (0/90/180/270) y la inclinación (> 1°) y se corrige.
- El texto de cada página se guarda con la huella del archivo: si vuelve a llegar, no se relee.
Las páginas corregidas se dejan como imágenes en la copia de trabajo (Datos\\Trabajo\\lote_N\\)."""
import io, re
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

MIN_TEXTO_PDF = 40          # caracteres útiles para dar por buena la capa de texto de un PDF
DPI = 300
IDIOMAS_PREFERIDOS = ["spa", "cat", "eus", "glg"]

@dataclass
class Pagina:
    n: int
    texto: str
    origen: str               # 'pdf', 'ocr', 'cache', 'office'
    confianza: float          # 0..1
    rotacion: int = 0         # grados aplicados (sentido horario)
    inclinacion: float = 0.0  # grados enderezados
    imagen: str | None = None # ruta de la imagen corregida en la copia de trabajo (si se ha usado OCR)

@dataclass
class Lectura:
    paginas: list = field(default_factory=list)
    avisos: list = field(default_factory=list)

    @property
    def texto(self):
        return "\n\f\n".join(p.texto for p in self.paginas)

    @property
    def confianza(self):
        return min((p.confianza for p in self.paginas), default=0.0)

def idiomas_ocr():
    import pytesseract
    try:
        hay = set(pytesseract.get_languages(config=""))
    except Exception:
        hay = {"spa"}
    elegidos = [l for l in IDIOMAS_PREFERIDOS if l in hay]
    return "+".join(elegidos or ["spa"])

def utiles(texto):
    return len(re.findall(r"[A-Za-zÁÉÍÓÚÑáéíóúñ0-9]", texto or ""))

# ------------------------------------------------------------------ orientar y enderezar
def orientacion(img):
    """Grados que hay que girar en sentido horario para poner el texto derecho."""
    import pytesseract
    try:
        osd = pytesseract.image_to_osd(img, config="--psm 0 -c min_characters_to_try=5")
        m = re.search(r"Rotate:\s*(\d+)", osd)
        conf = re.search(r"Orientation confidence:\s*([\d.]+)", osd)
        if m and (not conf or float(conf.group(1)) >= 1.0):
            rot = int(m.group(1)) % 360
            # Con confianza baja la detección automática se equivoca a veces: se comprueba leyendo.
            if rot and conf and float(conf.group(1)) < 5.0:
                if _conf_rapida(img) >= _conf_rapida(img.rotate(-rot, expand=True)):
                    return 0
            return rot
    except Exception:
        pass
    # Poco texto para la detección automática: se prueba cada giro y se queda el que mejor se lee.
    mejor, rot = -1.0, 0
    for r in (0, 90, 180, 270):
        c = _conf_rapida(img.rotate(-r, expand=True))
        if c > mejor:
            mejor, rot = c, r
    return rot

def _conf_rapida(img):
    import pytesseract
    small = img.copy()
    small.thumbnail((1400, 1400))
    d = pytesseract.image_to_data(small, lang="spa", config="--psm 6", output_type=pytesseract.Output.DICT)
    confs = [float(c) for c, w in zip(d["conf"], d["text"]) if w.strip() and float(c) >= 0]
    return sum(confs) / len(confs) * min(1, len(confs) / 10) if confs else 0.0

def inclinacion(img):
    """Ángulo de inclinación del texto en grados (positivo = girado a la izquierda)."""
    import cv2
    g = np.array(img.convert("L"))
    g = cv2.threshold(g, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    pts = np.column_stack(np.where(g > 0))
    if len(pts) < 500:
        return 0.0
    ang = cv2.minAreaRect(pts[:, ::-1].astype(np.float32))[-1]
    if ang > 45:
        ang -= 90
    if ang < -45:
        ang += 90
    return float(ang)

def corregir(img):
    """Devuelve (imagen corregida, rotación aplicada, inclinación corregida)."""
    rot = orientacion(img)
    if rot:
        img = img.rotate(-rot, expand=True, fillcolor="white")
    inc = inclinacion(img)
    if abs(inc) > 1.0 and abs(inc) < 15:
        img = img.rotate(inc, expand=True, fillcolor="white", resample=Image.BICUBIC)
    else:
        inc = 0.0
    return img, rot, round(inc, 1)

# ------------------------------------------------------------------ OCR
def ocr(img, idiomas):
    import pytesseract
    d = pytesseract.image_to_data(img, lang=idiomas, config="--psm 3", output_type=pytesseract.Output.DICT)
    lineas, actual, confs = [], None, []
    for i, w in enumerate(d["text"]):
        if not w.strip():
            continue
        c = float(d["conf"][i])
        if c >= 0:
            confs.append(c)
        clave = (d["block_num"][i], d["par_num"][i], d["line_num"][i])
        if clave != actual:
            lineas.append([])
            actual = clave
        lineas[-1].append(w)
    texto = "\n".join(" ".join(l) for l in lineas)
    return texto, (sum(confs) / len(confs) / 100) if confs else 0.0

def texto_pdf(page):
    """Texto de una página de PDF digital respetando los cuadros: si en una misma línea hay dos
    columnas separadas (p. ej. empresa a la izquierda y trabajador a la derecha en una nómina),
    se marcan con «¦» para que no se mezclen."""
    try:
        words = page.extract_words(x_tolerance=1.5, y_tolerance=3, keep_blank_chars=False)
    except Exception:
        words = []
    if not words:
        return page.extract_text() or ""
    words.sort(key=lambda w: (round(w["top"]), w["x0"]))
    lineas = []
    for w in words:
        if lineas and abs(w["top"] - lineas[-1][0]) <= 3:
            lineas[-1][1].append(w)
        else:
            lineas.append([w["top"], [w]])
    out = []
    for _, ws in lineas:
        ws.sort(key=lambda w: w["x0"])
        s = ws[0]["text"]
        for a, b in zip(ws, ws[1:]):
            alto = (a["bottom"] - a["top"]) or 8
            s += (" ¦ " if b["x0"] - a["x1"] > 2.2 * alto else " ") + b["text"]
        out.append(s)
    return "\n".join(out)

def imagen_pdf(ruta, n, dpi=None):
    """Página n (desde 1) de un PDF como imagen. Usa PDFium (va dentro de pdfplumber): sin programas externos."""
    import pypdfium2 as pdfium
    doc = pdfium.PdfDocument(str(ruta))
    try:
        return doc[n - 1].render(scale=(dpi or DPI) / 72).to_pil().convert("RGB")
    finally:
        doc.close()

_imagen_pdf = imagen_pdf

def _leer_imagen(img, n, trabajo, idiomas, prefijo):
    img, rot, inc = corregir(img)
    texto, conf = ocr(img, idiomas)
    ruta_img = None
    if trabajo:
        ruta_img = str(Path(trabajo) / f"{prefijo}_p{n}.jpg")
        img.save(ruta_img, "JPEG", quality=85, dpi=(DPI, DPI))
    return Pagina(n, texto, "ocr", round(conf, 3), rot, inc, ruta_img)

# ------------------------------------------------------------------ entrada principal
UMBRAL_LECTURA_POBRE = 0.6     # 3.1.2 · se cambia en Ajustes › OCR o con «Aceptar con este umbral» en Avisos del programa


def leer(ruta, clase, huella=None, almacen=None, trabajo=None):
    """Lee un archivo completo. clase: 'pdf', 'imagen', 'word' o 'excel'."""
    ruta = Path(ruta)
    idiomas = idiomas_ocr()
    prefijo = (huella or ruta.stem)[:12]
    res = Lectura()

    def desde_cache(n):
        if not (almacen and huella):
            return None
        c = almacen.texto_cache(f"{huella}:{n}")
        if not c:
            return None
        img = Path(trabajo) / f"{prefijo}_p{n}.jpg" if trabajo else None
        return Pagina(n, c["texto"], "cache", c["confianza"], c["rotacion"] or 0, 0.0, str(img) if img and img.exists() else None)

    def guardar(p):
        if almacen and huella:
            almacen.guardar_texto(f"{huella}:{p.n}", p.texto, p.origen, p.confianza, p.rotacion)

    if clase == "pdf":
        import pdfplumber
        with pdfplumber.open(str(ruta)) as pdf:
            total = len(pdf.pages)
            for n, page in enumerate(pdf.pages, 1):
                p = desde_cache(n)
                if p and (p.imagen or p.confianza >= 0.99):
                    res.paginas.append(p); continue
                texto = texto_pdf(page)
                if utiles(texto) >= MIN_TEXTO_PDF:
                    p = Pagina(n, texto, "pdf", 1.0, 0)
                else:
                    p = _leer_imagen(_imagen_pdf(ruta, n), n, trabajo, idiomas, prefijo)
                guardar(p); res.paginas.append(p)
    elif clase == "imagen":
        p = desde_cache(1)
        if not p or not p.imagen:
            img = ImageOps.exif_transpose(Image.open(ruta)).convert("RGB")
            p = _leer_imagen(img, 1, trabajo, idiomas, prefijo)
            guardar(p)
        res.paginas.append(p)
    elif clase == "word":
        import docx
        d = docx.Document(str(ruta))
        texto = "\n".join(par.text for par in d.paragraphs)
        res.paginas.append(Pagina(1, texto, "office", 1.0))
    elif clase == "excel":
        import openpyxl
        wb = openpyxl.load_workbook(str(ruta), read_only=True, data_only=True)   # nunca ejecuta macros
        filas = []
        for ws in wb.worksheets:
            for row in ws.iter_rows(values_only=True):
                vals = [str(v) for v in row if v is not None]
                if vals:
                    filas.append(" ".join(vals))
        res.paginas.append(Pagina(1, "\n".join(filas), "office", 1.0))
    else:
        raise ValueError(f"Tipo de archivo no admitido: {clase}")

    for p in res.paginas:
        if p.origen == "ocr" and p.confianza < UMBRAL_LECTURA_POBRE:
            res.avisos.append(f"Página {p.n}: lectura pobre ({round(p.confianza * 100)} %). Conviene volver a escanear.")
        if p.origen == "ocr" and utiles(p.texto) < 15:
            res.avisos.append(f"Página {p.n}: casi sin texto. Puede estar en blanco.")
    return res
