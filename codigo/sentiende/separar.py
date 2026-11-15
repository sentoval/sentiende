# -*- coding: utf-8 -*-
"""Fase 3 · Separar (M-03, M-22). Un PDF puede traer varios documentos, y a veces con las
páginas mezcladas (p. ej. la página 2 de la vida laboral detrás de la nota simple).

Cómo se decide:
1. Cada página se clasifica por separado y se mira si dice «Página X de N».
2. Las páginas casi vacías son «en blanco»: no se borran, se apartan y se avisa.
3. Empieza documento nuevo cuando una página dice «1 de N» o tiene un tipo claro distinto
   del documento en curso. Una página «X de N» (X > 1) se une a su documento aunque esté lejos.
4. Dentro de cada documento las páginas se ordenan por su numeración.
5. Las páginas que comparten código de verificación (CSV, referencia electrónica…) o el mismo pie
   de página son del mismo documento: nunca se separan (renta, vida laboral, certificados).
El resultado es una propuesta: se puede corregir en la pantalla Separar."""
import re
from dataclasses import dataclass, field
from .extraer import norm

UMBRAL_TIPO_CLARO = 6          # puntos para que una página abra documento nuevo por sí sola
MIN_TEXTO_PAGINA = 15

@dataclass
class Parte:
    paginas: list = field(default_factory=list)   # números de página del archivo, en orden final
    tipo: str | None = None
    puntos: int = 0
    total_declarado: int | None = None             # N de «página X de N»
    firmas: list = field(default_factory=list)     # códigos y pies de sus páginas

@dataclass
class Separacion:
    partes: list
    en_blanco: list
    reordenado: bool

def numeracion(texto):
    """'Página 2 de 3', 'pág. 2/3', 'Pàgina 2 de 3', '2 / 3' al pie -> (2, 3)."""
    t = norm(texto)
    m = re.search(r"\b(?:PAGINA|PAG\.?|PAGE|ORRIALDEA|FOLIO|HOJA)\s*(\d{1,3})\s*(?:DE|/|OF|-)\s*(\d{1,3})\b", t)
    if not m:
        m = re.search(r"(?m)^\s*(\d{1,2})\s*/\s*(\d{1,2})\s*$", t)
    if m:
        x, n = int(m.group(1)), int(m.group(2))
        if 1 <= x <= n <= 500:
            return x, n
    return None

CODIGO_RE = re.compile(r"(?:CODIGO SEGURO|C\.?S\.?V|VERIFICACION|REFERENCIA ELECTRONICA|CODIGO ELECTRONICO|C\.U\.D|CODI SEGUR|"
                       r"VERIFICACIO|LOCALIZADOR|N\.? ?DE REGISTRO|REFERENCIA)[^\n]{0,60}?\b((?=[A-Z0-9]*\d)(?=[A-Z0-9]*[A-Z])[A-Z0-9]{8,24})\b")

def firma(texto):
    """Lo que identifica al documento en cada página: códigos de verificación y el pie repetido."""
    t = norm(texto)
    codigos = set(CODIGO_RE.findall(t))
    lineas = [l for l in t.split("\n") if utiles(l) > 10]
    pie = re.sub(r"[\d¦ ]+", " ", " ".join(lineas[-2:])).strip() if lineas else ""
    return codigos, pie if len(pie) > 30 else ""

def mismo_documento(f1, f2):
    return bool(f1[0] & f2[0]) or (f1[1] and f1[1] == f2[1])

def utiles(texto):
    return len(re.findall(r"[A-Za-z0-9ÁÉÍÓÚÑáéíóúñ]", texto or ""))

def separar(textos, clasificador):
    """textos: lista con el texto de cada página (en el orden del archivo)."""
    info = []
    for i, tx in enumerate(textos, 1):
        if utiles(tx) < MIN_TEXTO_PAGINA:
            info.append({"n": i, "blanco": True}); continue
        res = clasificador.puntuar(norm(tx))
        tipo, pts = (res[0][1], res[0][0]) if res else (None, 0)
        info.append({"n": i, "blanco": False, "tipo": tipo, "puntos": pts, "num": numeracion(tx), "firma": firma(tx)})
    partes, en_blanco, pendientes = [], [p["n"] for p in info if p["blanco"]], []
    actual = None
    for p in (x for x in info if not x["blanco"]):
        num = p["num"]
        # Mismo código de verificación o mismo pie que un documento ya abierto: es suyo.
        hermano = next((q for q in reversed(partes) if any(mismo_documento(p["firma"], f) for f in q.firmas)), None)
        if hermano:
            hermano.paginas.append(p["n"]); hermano.firmas.append(p["firma"])
            if p["puntos"] > hermano.puntos:
                hermano.tipo, hermano.puntos = p["tipo"], p["puntos"]
            actual = hermano
            continue
        if num and num[0] > 1:
            # Continuación: busca un documento abierto con la misma numeración total (y tipo, si lo hay)
            destino = next((q for q in reversed(partes) if q.total_declarado == num[1] and (not p["tipo"] or p["puntos"] < UMBRAL_TIPO_CLARO or q.tipo == p["tipo"])), None)
            if destino:
                destino.paginas.append(p["n"]); destino.firmas.append(p["firma"]); continue
            if actual and not actual.total_declarado:
                actual.paginas.append(p["n"]); actual.firmas.append(p["firma"]); continue
        nuevo = (actual is None or (num and num[0] == 1)
                 or (p["tipo"] and p["puntos"] >= UMBRAL_TIPO_CLARO and p["tipo"] != actual.tipo))
        if nuevo:
            actual = Parte([p["n"]], p["tipo"], p["puntos"], num[1] if num else None, [p["firma"]])
            partes.append(actual)
        else:
            actual.paginas.append(p["n"]); actual.firmas.append(p["firma"])
            if p["puntos"] > actual.puntos and not actual.tipo:
                actual.tipo, actual.puntos = p["tipo"], p["puntos"]
    reordenado = False
    numeros = {p["n"]: p["num"] for p in info if not p["blanco"]}
    for q in partes:
        orden = sorted(q.paginas, key=lambda n: (numeros[n][0] if numeros.get(n) else 0, q.paginas.index(n)))
        if orden != q.paginas or q.paginas != sorted(q.paginas):
            reordenado = True
        q.paginas = orden
    return Separacion(partes, en_blanco, reordenado)
