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
6. (3.1.2) Formularios con apartados numerados: si una página empieza por el apartado siguiente
   al último del documento en curso («3. Actividad» → «4. Declaración de bienes»), es su continuación
   aunque por sí sola parezca otro tipo (la solicitud de aval se partía en tres).
7. (3.1.2, P1) Misma cabecera (primeras líneas) o mismo número de póliza, contrato o cuenta que el documento en
   curso: es su continuación aunque parezca otro tipo (la pág. 2 del PIAS salía como nota simple).
8. (3.1.2, P2) Una página «1 de N» del mismo tipo que el documento en curso, con el mismo DNI o número, no abre
   documento nuevo si el tipo no va por meses (la comunicación del contrato al SEPE se separaba del contrato).
   Las nóminas, recibos y extractos sí se siguen separando.
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
    seccion: int = 0                               # último apartado numerado visto («7. Otros datos» -> 7)
    cabecera: frozenset = frozenset()              # palabras de las primeras líneas de su primera página
    claves: set = field(default_factory=set)       # DNI y números largos (póliza, contrato, cuenta) de sus páginas

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

SECCION_RE = re.compile(r"(?m)^\s*(\d{1,2})\s*[.)]\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]{2,}")

def secciones(texto):
    """Apartados numerados de un formulario («1. Solicitante», «4. Declaración de bienes»), en orden de aparición
    y solo si van subiendo (así no se confunden con listas o fechas)."""
    out = []
    for m in SECCION_RE.finditer(texto or ""):
        n = int(m.group(1))
        if 1 <= n <= 30 and (not out or out[-1] < n <= out[-1] + 3):
            out.append(n)
    return out

def continua_apartados(parte, secs):
    return bool(parte and parte.seccion and secs and parte.seccion < secs[0] <= parte.seccion + 2)

def cabecera(texto):
    """Palabras (de 3 letras o más) de las 3 primeras líneas con texto."""
    lineas = [l for l in norm(texto or "").split("\n") if utiles(l) >= 3][:3]
    return frozenset(w for l in lineas for w in re.findall(r"[A-ZÑ]{3,}", l))

def claves(texto):
    """DNI/NIE y números de 9 a 20 cifras (póliza, contrato, cuenta), sin espacios ni puntos dentro."""
    t = norm(texto or "")
    dnis = set(re.findall(r"\b[XYZ]?\d{7,8}[A-Z]\b", t))
    nums = set(re.findall(r"\b\d{9,20}\b", re.sub(r"(?<=\d)[ .\-](?=\d)", "", t)))
    return dnis | {n for n in nums if not any(n == d[:-1] or n.endswith(d[:-1]) for d in dnis)}

def misma_cabecera(c1, c2):
    return len(c1) >= 3 and len(c2) >= 3 and len(c1 & c2) / len(c1 | c2) >= 0.5

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
        info.append({"n": i, "blanco": False, "tipo": tipo, "puntos": pts, "num": numeracion(tx), "firma": firma(tx), "secs": secciones(tx),
                     "cab": cabecera(tx), "claves": claves(tx)})
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
        from .contexto import EN_SERIE
        sigue = continua_apartados(actual, p["secs"]) or bool(
            actual and p["puntos"] < 2 * UMBRAL_TIPO_CLARO and (misma_cabecera(actual.cabecera, p["cab"]) or actual.claves & p["claves"]))
        anexo = bool(actual and num and num[0] == 1 and p["tipo"] and p["tipo"] == actual.tipo
                     and actual.tipo not in EN_SERIE and actual.claves & p["claves"])
        nuevo = (actual is None or (num and num[0] == 1 and not anexo)
                 or (not sigue and p["tipo"] and p["puntos"] >= UMBRAL_TIPO_CLARO and p["tipo"] != actual.tipo))
        if nuevo:
            actual = Parte([p["n"]], p["tipo"], p["puntos"], num[1] if num else None, [p["firma"]], max(p["secs"] or [0]),
                           p["cab"], set(p["claves"]))
            partes.append(actual)
        else:
            actual.paginas.append(p["n"]); actual.firmas.append(p["firma"]); actual.claves |= p["claves"]
            actual.seccion = max([actual.seccion] + p["secs"])
            if p["puntos"] > actual.puntos and not actual.tipo:
                actual.tipo, actual.puntos = p["tipo"], p["puntos"]
    # 3.1.3 (Joan) · un «Cuadro contable» (cuentas, hojas de cálculo) se guarda como un único documento
    if partes and partes[0].tipo == "cuadrocontable" and len(partes) > 1:
        todas = [n for q in partes for n in q.paginas]
        partes = [Parte(todas, "cuadrocontable", max(q.puntos for q in partes), None, [f for q in partes for f in q.firmas])]
    reordenado = False
    numeros = {p["n"]: p["num"] for p in info if not p["blanco"]}
    for q in partes:
        orden = sorted(q.paginas, key=lambda n: (numeros[n][0] if numeros.get(n) else 0, q.paginas.index(n)))
        if orden != q.paginas or q.paginas != sorted(q.paginas):
            reordenado = True
        q.paginas = orden
    return Separacion(partes, en_blanco, reordenado)
