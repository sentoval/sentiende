# -*- coding: utf-8 -*-
"""Fase 3 · Separar (M-03, M-22). Un PDF puede traer varios documentos, y a veces con las
páginas mezcladas (p. ej. la página 2 de la vida laboral detrás de la nota simple).

Cómo se decide:
1. Cada página se clasifica por separado y se mira si dice «Página X de N».
2. Las páginas casi vacías son «en blanco»: no se borran, se apartan y se avisa.
3. Empieza documento nuevo cuando una página dice «1 de N» o tiene un tipo claro distinto
   del documento en curso. Una página «X de N» (X > 1) se une a su documento aunque esté lejos.
4. Dentro de cada documento las páginas se ordenan por su numeración.
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
        info.append({"n": i, "blanco": False, "tipo": tipo, "puntos": pts, "num": numeracion(tx)})
    partes, en_blanco, pendientes = [], [p["n"] for p in info if p["blanco"]], []
    actual = None
    for p in (x for x in info if not x["blanco"]):
        num = p["num"]
        if num and num[0] > 1:
            # Continuación: busca un documento abierto con la misma numeración total (y tipo, si lo hay)
            destino = next((q for q in reversed(partes) if q.total_declarado == num[1] and (not p["tipo"] or p["puntos"] < UMBRAL_TIPO_CLARO or q.tipo == p["tipo"])), None)
            if destino:
                destino.paginas.append(p["n"]); continue
            if actual and not actual.total_declarado:
                actual.paginas.append(p["n"]); continue
        nuevo = (actual is None or (num and num[0] == 1)
                 or (p["tipo"] and p["puntos"] >= UMBRAL_TIPO_CLARO and p["tipo"] != actual.tipo))
        if nuevo:
            actual = Parte([p["n"]], p["tipo"], p["puntos"], num[1] if num else None)
            partes.append(actual)
        else:
            actual.paginas.append(p["n"])
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
