# -*- coding: utf-8 -*-
"""Fase 5 · Extraer datos (M-05, M-27). Saca DNI/NIE, CIF, IBAN, fechas, importes, periodos,
ejercicios, caducidades, trimestres, matrículas y referencias catastrales, validando lo
que tiene dígito de control. Todo se normaliza para poder compararlo."""
import datetime, re, unicodedata

LETRAS_DNI = "TRWAGMYFPDXBNJZSQVHLCKE"
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
MESES_ABR = ["ENE", "FEB", "MAR", "ABR", "MAY", "JUN", "JUL", "AGO", "SEP", "OCT", "NOV", "DIC"]
# catalán, euskera y gallego para los meses más habituales en los documentos
MESES_OTROS = {"gener": 1, "febrer": 2, "març": 3, "maig": 5, "juny": 6, "juliol": 7, "agost": 8, "setembre": 9, "octubre": 10,
               "novembre": 11, "desembre": 12, "urtarrila": 1, "otsaila": 2, "martxoa": 3, "apirila": 4, "maiatza": 5, "ekaina": 6,
               "uztaila": 7, "abuztua": 8, "iraila": 9, "urria": 10, "azaroa": 11, "abendua": 12, "xaneiro": 1, "febreiro": 2,
               "maio": 5, "xuño": 6, "xullo": 7, "setembro": 9, "outubro": 10, "decembro": 12}

def norm(s):
    """Mayúsculas, sin tildes, espacios simples y confusiones típicas del OCR (M-27)."""
    s = unicodedata.normalize("NFD", (s or "").upper())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = s.replace("N.1.F", "N.I.F").replace("]", "L")
    return re.sub(r"[ \t]+", " ", s)

def letra_dni(num):
    return LETRAS_DNI[int(num) % 23]

def dni_valido(s):
    s = re.sub(r"[\s-]", "", s.upper())
    m = re.fullmatch(r"0?(\d{8})([A-Z])", s)
    if m:
        return m.group(1) + m.group(2) if letra_dni(m.group(1)) == m.group(2) else None
    m = re.fullmatch(r"([XYZ])(\d{7})([A-Z])", s)
    if m:
        num = "XYZ".index(m.group(1)) * 10 ** 7 + int(m.group(2))
        return s if letra_dni(num) == m.group(3) else None
    return None

def cif_valido(s):
    s = re.sub(r"[\s-]", "", s.upper())
    m = re.fullmatch(r"([ABCDEFGHJNPQRSUVW])(\d{7})([0-9A-J])", s)
    if not m:
        return None
    d = m.group(2)
    pares = sum(int(d[i]) for i in (1, 3, 5))
    impares = sum(sum(divmod(int(d[i]) * 2, 10)) for i in (0, 2, 4, 6))
    control = (10 - (pares + impares) % 10) % 10
    return s if m.group(3) in (str(control), "JABCDEFGHI"[control]) else None

def iban_valido(s):
    s = re.sub(r"[\s-]", "", s.upper())
    if not re.fullmatch(r"ES\d{22}", s):
        return None
    num = "".join(str(int(c, 36)) for c in s[4:] + s[:4])
    return s if int(num) % 97 == 1 else None

def _fecha(d, m, a):
    try:
        a = int(a); a = a + 2000 if a < 100 else a
        return datetime.date(a, int(m), int(d))
    except ValueError:
        return None

def fechas(texto):
    out = []
    for m in re.finditer(r"\b(\d{1,2})[/.-](\d{1,2})[/.-](\d{4}|\d{2})\b", texto):
        f = _fecha(*m.groups())
        if f:
            out.append((m.start(), f))
    low = norm(texto).lower()
    nombres = {norm(n).lower(): i + 1 for i, n in enumerate(MESES)} | {norm(k).lower(): v for k, v in MESES_OTROS.items()}
    pat = r"\b(\d{1,2})\s+(?:de\s+|d[e']\s*)?(" + "|".join(sorted(nombres, key=len, reverse=True)) + r")\s+(?:de\s+|del\s+)?(\d{4})\b"
    for m in re.finditer(pat, low):
        f = _fecha(m.group(1), nombres[m.group(2)], m.group(3))
        if f:
            out.append((m.start(), f))
    out.sort()
    return [f for _, f in out]

def importes(texto):
    vals = []
    for m in re.finditer(r"(?<![\d.,])(\d{1,3}(?:\.\d{3})*,\d{2})(?![\d,])", texto):
        vals.append(float(m.group(1).replace(".", "").replace(",", ".")))
    return vals

MES_NUM = {norm(n): i + 1 for i, n in enumerate(MESES)} | {norm(k): v for k, v in MESES_OTROS.items()}
MES_RE = "|".join(sorted(MES_NUM, key=len, reverse=True))

def periodo(texto):
    """Mes al que corresponde (nóminas, extractos, CIRBE): devuelve date(año, mes, 1) o None."""
    t = norm(texto)
    m = re.search(r"(\d{1,2})\s(ENE|FEB|MAR|ABR|MAY|JUN|JUL|AGO|SEP|OCT|NOV|DIC)\s(\d{2})\s+A\s+(\d{1,2})\s(ENE|FEB|MAR|ABR|MAY|JUN|JUL|AGO|SEP|OCT|NOV|DIC)\s(\d{2})", t)
    if m:
        return datetime.date(2000 + int(m.group(6)), MESES_ABR.index(m.group(5)) + 1, 1)
    m = re.search(r"(PERIODO|PERIODE|ALDIA|PERIODO DE LIQUIDACION)[^\n]{0,40}?(\d{1,2})[/.-](\d{1,2})[/.-](\d{2,4})(?:[^\n]{0,15}?(\d{1,2})[/.-](\d{1,2})[/.-](\d{2,4}))?", t)
    if m:
        f = _fecha(*(m.group(5, 6, 7) if m.group(5) else m.group(2, 3, 4)))
        if f:
            return f.replace(day=1)
    # «del 01 de agosto al 31 de agosto de 2026» / «del 01 d'agost al 31 d'agost de 2026»
    m = re.search(r"(?:PERIODO|PERIODE|LIQUIDACION|LIQUIDACIO)[^\n]{0,40}?\bDEL?\s+\d{1,2}\s+D(?:E\s+|')(" + MES_RE + r")\b[^\n]{0,20}?\bAL?\s+\d{1,2}\s+D(?:E\s+|')(" + MES_RE + r")\b\s+(?:DE\s+|DEL\s+)?(\d{4})", t)
    if m:
        return datetime.date(int(m.group(3)), MES_NUM[m.group(2)], 1)
    meses_up = [norm(x) for x in MESES]
    m = re.search(r"(PERIODO|MES|NOMINA|NOMINA DE|MENSUALIDAD)[^\n]{0,25}?\b(" + "|".join(meses_up) + r")\b[^\n\d]{0,6}(\d{4})", t)
    if m:
        return datetime.date(int(m.group(3)), meses_up.index(m.group(2)) + 1, 1)
    return None

def ejercicio(texto):
    t = norm(texto)
    m = re.search(r"(EJERCICIO|EXERCICI|EKITALDIA|EXERCICIO|PERIODO IMPOSITIVO)\s*:?\s*(20\d{2})", t)
    if m:
        return int(m.group(2))
    m = re.search(r"\b(?:RENTA|IRPF|MODELO 100)\D{0,12}(20\d{2})\b", t)
    return int(m.group(1)) if m else None

def caducidad(texto):
    t = norm(texto)
    m = re.search(r"(VALIDO HASTA|VALIDEZ|FECHA DE CADUCIDAD|CADUCIDAD|CADUCA|VALID UNTIL|DATE OF EXPIRY)[^\n]{0,25}?(\d{1,2})[ /.-](\d{1,2})[ /.-](\d{2,4})", t)
    if m:
        return _fecha(*m.group(2, 3, 4))
    return None

def emision(texto, todas):
    """Fecha de emisión o del documento: la que va junto a su etiqueta (castellano o valenciano) o junto
    a la ciudad al pie («València, 11/09/2026»); si no hay, la más reciente que no sea futura (las de
    nacimiento, alta o antigüedad suelen ser antiguas)."""
    t = norm(texto)
    etiquetas = (r"FECHA DE EMISION|FECHA EMISION|FECHA DE EXPEDICION|EXPEDIDO EL|EXPEDIDO|EXPEDICION|EMITIDO EL|EMISION|FECHA DEL DOCUMENTO|"
                 r"DATA D.EMISSIO|DATA D.EXPEDICIO|EXPEDIT|EMES EL|AL DIA|A FECHA DE|EN FECHA|PRESENTACION REALIZADA EL|FECHA DE PRESENTACION|"
                 r"DATA DE PRESENTACIO|FECHA DE FIRMA|FIRMADO EL|SIGNAT EL|FECHA DE CERTIFICACION")
    for m in re.finditer(r"(?:" + etiquetas + r")\s*:?\s*([^\n]{0,40})", t):
        if (f := fechas(m.group(1))):
            return f[0]
    m = re.search(r"(?m)^\s*(?:EN\s+)?[A-Z][A-Z' ]{2,30},\s*(?:A\s+)?(\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}|\d{1,2}\s+DE?\s*'?\s*[A-Z]+\s+(?:DE\s+|DEL\s+)?\d{4})", t)
    if m and (f := fechas(m.group(1))):
        return f[0]
    hoy = datetime.date.today()
    validas = [f for f in todas if f <= hoy]
    return max(validas) if validas else None

def trimestre(texto):
    t = norm(texto)
    m = re.search(r"\b([1-4])\s?T\b|\b([1-4])[ºO]?\s?TRIMESTRE\b", t)
    if not m:
        return None
    n = int(m.group(1) or m.group(2))
    a = ejercicio(texto)
    return (n, a)

def extraer(texto, base=None):
    t = norm(texto)
    dnis, dnis_calc = [], []
    for m in re.finditer(r"\b0?(\d{8})[ -]?([A-Z])\b|\b([XYZ])[ -]?(\d{7})[ -]?([A-Z])\b", t):
        v = dni_valido(m.group(0))
        if v and v not in dnis:
            dnis.append(v)
    for m in re.finditer(r"(?:DNI|NIF|N\.I\.F|D\.N\.I)[^\n\dA-Z]{0,6}(\d{8})\b(?![ -]?[A-Z])", t):
        v = m.group(1) + letra_dni(m.group(1))
        if v not in dnis and v not in dnis_calc:
            dnis_calc.append(v)
    cifs = []
    for m in re.finditer(r"\b[ABCDEFGHJNPQRSUVW][ -]?\d{7}[ -]?[0-9A-J]\b", t):
        v = cif_valido(m.group(0))
        if v and v not in cifs:
            cifs.append(v)
    ibans = []
    for m in re.finditer(r"\bES\d{2}(?:[ -]?\d{4}){5}\b", t):
        v = iban_valido(m.group(0))
        if v and v not in ibans:
            ibans.append(v)
    fs = fechas(texto)
    tri = trimestre(texto)
    d = {
        "dni": dnis, "dni_letra_calculada": dnis_calc, "cif": cifs, "iban": ibans,
        "fechas": [f.isoformat() for f in fs], "importes": importes(texto),
        "periodo": (p.isoformat() if (p := periodo(texto)) else None),
        "ejercicio": ejercicio(texto),
        "caducidad": (c.isoformat() if (c := caducidad(texto)) else None),
        "emision": (e.isoformat() if (e := emision(texto, fs)) else None),
        "trimestre": list(tri) if tri else None,
        "matricula": (m.group(0).replace(" ", "").replace("-", "") if (m := re.search(r"\b\d{4}[ -]?[BCDFGHJKLMNPRSTVWXYZ]{3}\b", t)) else None),
        "ref_catastral": (m.group(0) if (m := re.search(r"\b\d{7}[A-Z]{2}\d{4}[A-Z]\d{4}[A-Z]{2}\b", t)) else None),
        "personas": personas(texto),
    }
    return d

# ------------------------------------------------------------------ personas (nombre y apellidos)
# Cómo se buscan (castellano y valenciano):
#  1. Etiquetas: «Nombre y apellidos / Nom i cognoms», «Apellidos y nombre / Cognoms i nom», «Trabajador»,
#     «Declarante», «Titular», «D./Dña., D/Dª»… con el valor en la misma línea, en el cuadro de al lado o debajo.
#  2. «APELLIDOS, NOMBRE» en cualquier cuadro (nóminas).
#  3. Junto a un DNI válido, aunque no haya etiqueta.
# Cada candidato se valida con listas de nombres y apellidos frecuentes (y los de las personas ya
# confirmadas en el programa): así no se cuelan «Representante legal», calles ni empresas.
from pathlib import Path as _Path

PARTICULAS = {"DE", "DEL", "LA", "LAS", "LOS", "Y", "I", "DA", "DAS", "DO", "DOS", "SAN", "SANTA"}
SEP = "¦"            # separa cuadros o columnas de una misma línea (lo pone la lectura de los PDF)

def _lista(nombre):
    f = _Path(__file__).with_name("datos") / nombre
    try:
        return {w for l in f.read_text(encoding="utf-8").splitlines() if not l.startswith("#") for w in l.split()}
    except OSError:
        return set()

NOMBRES_PILA = _lista("nombres.txt")
APELLIDOS = _lista("apellidos.txt")
_APRENDIDOS = {"nombres": set(), "apellidos": set()}

def aprender_personas(personas):
    """Añade los nombres y apellidos de las personas ya confirmadas (los da el motor al arrancar)."""
    for p in personas:
        _APRENDIDOS["nombres"] |= set(norm(p.get("nombre") or "").split()) - PARTICULAS
        _APRENDIDOS["apellidos"] |= set(norm(f'{p.get("apellido1") or ""} {p.get("apellido2") or ""}').split()) - PARTICULAS

def es_nombre(w):
    return w in NOMBRES_PILA or w in _APRENDIDOS["nombres"]

def es_apellido(w):
    return w in APELLIDOS or w in _APRENDIDOS["apellidos"]

NO_NOMBRE = set("""DNI NIF NIE CIF NAF NUM NUMERO DOCUMENTO NACIONAL IDENTIDAD IDENTIFICATIVO IDENTIFICACION ESPANA ESPANOLA ESP SEXO NACIONALIDAD
FECHA NACIMIENTO VALIDO HASTA DOMICILIO CALLE AVDA AVENIDA PLAZA PASEO CTRA CAMINO PISO PUERTA BAJO PROVINCIA MUNICIPIO BANCO CAJA RURAL
SL SA SLU SAU SOCIEDAD LIMITADA ANONIMA EMPRESA TRABAJADOR TRABAJADORA EMPLEADO TITULAR TITULARES DECLARANTE CONTRIBUYENTE SOLICITANTE NOMBRE
APELLIDOS APELLIDO CON PROVISTO MAYOR EDAD VECINO VECINA SEGURIDAD SOCIAL TESORERIA GENERAL AGENCIA TRIBUTARIA INFORME VIDA LABORAL
CERTIFICADO NOMINA RECIBO PERIODO CUENTA IBAN SWIFT BIC CODIGO POSTAL TELEFONO TEL CORREO EMAIL DATOS PERSONALES CATEGORIA GRUPO ANTIGUEDAD
REGISTRO PROPIEDAD FINCA NOTA SIMPLE INFORMATIVA HOJA PAGINA EL EN POR PARA QUE SON SU SUS LO AL UN UNA CONYUGE PROGENITOR HIJO HIJA PRIMER
SEGUNDO SOLICITUD DEVOLUCION REPRESENTANTE LEGAL ACTIVIDAD ECONOMICA PAGADOR ANUALIDADES ANUALIDAD IMPORTE FIGURAN DURANTE ANO OTRO OTRA
NOM COGNOMS COGNOM TREBALLADOR TREBALLADORA DECLARANT CARRER PASSEIG PLACA HABITANT DADES IDENTIFICACIO NASCUT NASCUDA DATA ENTITAT SITUACIO
CL PZ PZA AV CR URB AJUNTAMENT VALENCIA MADRID BARCELONA ALICANTE CASTELLON GENERALITAT NOTARIO NOTARI ANTE MI COMPARECEN INTERVIENEN SENOR SENORA DON DONA PROPIO PROPIA DERECHO DUENO DUENA DUENOS CARACTER CONSTE""".split())
DIRECCION = r"(?:\bCL\b\.?|\bC/|\bCALLE\b|\bCARRER\b|\bAVDA\b\.?|\bAV\b\.|\bAVENIDA\b|\bPZA\b\.?|\bPLAZA\b|\bPLACA\b|\bPASEO\b|\bPASSEIG\b|\bPG\b\.|\bCTRA\b\.?|\bCAMI\b|\bCAMINO\b|\bPARTIDA\b|\bURB\b\.?)\s*$"

def _agrupar(tokens):
    """Une partículas con la palabra siguiente: DE LA FUENTE -> una sola pieza."""
    out, buf = [], []
    for tk in tokens:
        buf.append(tk)
        if tk not in PARTICULAS:
            out.append(" ".join(buf)); buf = []
    if buf:
        out.append(" ".join(buf))
    return out

def _persona(nombre, apellidos, por, orden_seguro=True):
    ap = _agrupar(apellidos.split())
    return {"nombre": nombre.title(), "apellido1": ap[0].title() if ap else "", "apellido2": " ".join(ap[1:]).title(),
            "completo": f"{nombre} {apellidos}".title(), "por": por, "orden_seguro": orden_seguro}

def _palabras(txt):
    return [w for w in re.sub(r"[^A-Z' \-]", " ", txt).split() if w.strip("-'")]

def _partir(tokens, orden, por):
    """Decide qué es nombre y qué apellidos. orden: 'nombre' (nombre primero), 'apellidos' o None (adivinar)."""
    tk = [w.strip("-") for w in tokens if w.strip("-")]
    if len(tk) < 2 or len(tk) > 7 or any(w in NO_NOMBRE for w in tk):
        return None
    if orden is None:
        orden = "nombre" if es_nombre(tk[0]) and not es_apellido(tk[0]) else ("apellidos" if es_nombre(tk[-1]) else "nombre")
    # Nombre compuesto: se alarga mientras sea un nombre de pila y queden al menos dos apellidos
    # (o la palabra no pueda ser apellido: «Miguel» o «Gil» son las dos cosas).
    if orden == "nombre":
        k = 1
        while k < len(tk) - 1 and es_nombre(tk[k]) and (not es_apellido(tk[k]) or len(tk) - k - 1 >= 2):
            k += 1
        nombre, apellidos = tk[:k], tk[k:]
    else:
        k = len(tk) - 1
        while k > 1 and es_nombre(tk[k - 1]) and (not es_apellido(tk[k - 1]) or k - 1 >= 2):
            k -= 1
        apellidos, nombre = tk[:k], tk[k:]
    return _persona(" ".join(nombre), " ".join(apellidos), por, True)

def _valida(p, fuerte):
    """fuerte: viene de una etiqueta clara. Si no, hace falta un nombre y un apellido conocidos."""
    if not p:
        return False
    nom = set(norm(p["nombre"]).split()) - PARTICULAS
    ape = set(norm(f'{p["apellido1"]} {p["apellido2"]}').split()) - PARTICULAS
    if not nom or not ape:
        return False
    todas = nom | ape
    if any(w in NO_NOMBRE or len(w) < 2 for w in todas) or len(todas) > 6:
        return False
    desconocidas = [w for w in todas if not es_nombre(w) and not es_apellido(w)]
    if len(desconocidas) > (2 if fuerte else 1):
        return False
    conocido_n = any(es_nombre(w) for w in nom)
    conocido_a = any(es_apellido(w) for w in ape)
    return (conocido_n or conocido_a) if fuerte else (conocido_n and conocido_a)

ETIQUETAS = [   # (expresión, orden, fuerza)
    (r"APELLIDOS Y NOMBRE|APELLIDOS,? NOMBRE|COGNOMS I NOM|COGNOMS,? NOM", "apellidos"),
    (r"NOMBRE Y APELLIDOS|NOM I COGNOMS|NOMBRE COMPLETO|NOM COMPLET", "nombre"),
    (r"D\.?\s?/\s?D[NAª]\.?|D\.?\s?/\s?DNA|DONA|DON|D\.|SR\.|SRA\.|EN/NA", "nombre"),
    (r"TRABAJADOR[A]?|TREBALLADOR[A]?|EMPLEADO|EMPLEADA|PRIMER DECLARANTE|SEGUNDO DECLARANTE|DECLARANTE|DECLARANT|CONYUGE|CONTRIBUYENTE|"
     r"SOLICITANTE|SOL.LICITANT|INTERESADO|INTERESADA|INTERESSAT|TITULAR(?:ES)?|TITULARIDAD|TITULARITAT|PROPIETARIO|PROPIETARIA|VENDEDOR|VENDEDORA|"
     r"COMPRADOR|COMPRADORA|ARRENDATARIO|ARRENDADOR|PRESTATARIO|AVALISTA|BENEFICIARIO|BENEFICIARIA", None),
]

def personas(texto):
    """Nombres de personas del documento, validados, con su DNI si está cerca. Los más seguros primero."""
    t = re.sub(r"([A-Z])-\n([A-Z])", r"\1\2", norm(texto))      # palabras partidas con guion al final de línea
    encontradas = []
    def add(p, pos, fuerte):
        if not _valida(p, fuerte):
            return
        cerca = t[max(0, pos - 80): pos + 200]
        dn = [dni_valido(m.group(0)) for m in re.finditer(r"\b0?\d{8}[ -]?[A-Z]\b|\b[XYZ][ -]?\d{7}[ -]?[A-Z]\b", cerca)]
        p["dni"] = next((x for x in dn if x), None)
        clave = frozenset(norm(p["completo"]).split())
        for q in encontradas:
            cq = frozenset(norm(q["completo"]).split())
            if clave <= cq:
                return
            if cq < clave:                     # el nuevo es más completo: sustituye
                encontradas[encontradas.index(q)] = p
                return
        encontradas.append(p)
    def valor(resto):
        """El nombre que sigue a una etiqueta: hasta el siguiente cuadro, coma de dato o etiqueta."""
        v = re.split(r"\s*(?:¦|;|\(|\b(?:NIF|N\.I\.F|DNI|D\.N\.I|NIE|N\.A\.F|NAF|SEXO|SEXE|NACIONALIDAD|NACIONALITAT|FECHA|DATA|DOMICILIO|DOMICILI|"
                     r"CON DNI|AMB DNI|PROVISTO|MAYOR|VECIN|CIF|IBAN|CATEGORIA|GRUPO|ANTIG|NUM|NACIDO|NACIDA|NASCUT|IDENTIFICACIO)\b|\s\d)", resto, maxsplit=1)[0]
        v = re.split(r"\s+(?:Y|E|I)\s+(?:DON|DONA|D\.|EN|NA)\b", v, maxsplit=1)[0]   # «Don X y Doña Y»: cada uno por su lado
        return v.strip(" :.-/")
    # 1. Etiquetas
    for expr, orden in ETIQUETAS:
        for m in re.finditer(r"(?<![A-Z])(?:" + expr + r")(?![A-Z])\s*[:¦]?\s*", t):
            ini_linea = t.rfind("\n", 0, m.start()) + 1
            if re.search(DIRECCION, t[ini_linea:m.start()]):
                continue
            fin = t.find("\n", m.end()); fin = len(t) if fin < 0 else fin
            resto = t[m.end():fin]
            if "/" in resto[:3] or re.match(r"\s*/\s*(NOMBRE|APELLIDOS|NOM|COGNOMS)", resto):   # «Nom i cognoms / Nombre y apellidos»
                resto = re.sub(r"^\s*/\s*(?:NOMBRE Y APELLIDOS|APELLIDOS Y NOMBRE|NOMBRE|APELLIDOS)\s*[:¦]?\s*", "", resto)
            opciones = [valor(resto)]
            if orden == "nombre":                  # nombre primero: la coma cierra el nombre (no es «apellidos, nombre»)
                opciones = [opciones[0].split(",")[0]]
            sig0 = t.find("\n", fin + 1); sig0 = len(t) if sig0 < 0 else sig0
            if 0 < len(_palabras(opciones[0])) < 3:   # el nombre sigue en la línea de abajo («DOÑA MÓNICA / FERNÁNDEZ BENAVIDES»)
                opciones.append(opciones[0] + " " + valor(t[fin + 1:sig0].split("¦")[0]).split(",")[0])
            if len(_palabras(opciones[0])) < 2:   # el valor está en otra línea: debajo (tablas, «D/Dª» al final) o justo encima
                col = len(t[ini_linea:m.start()].split("¦")) - 1      # misma columna de la tabla
                sig = t.find("\n", fin + 1); sig = len(t) if sig < 0 else sig
                ant_fin = max(ini_linea - 1, 0); ant_ini = t.rfind("\n", 0, ant_fin) + 1
                for linea in (t[fin + 1:sig], t[ant_ini:ant_fin] if ini_linea else ""):
                    celdas = linea.split("¦")
                    orden_celdas = [celdas[min(col, len(celdas) - 1)]] + celdas if celdas else []
                    opciones += [valor(c) for c in orden_celdas]
            for v in sorted(opciones, key=lambda o: -len(_palabras(o))) if orden == "nombre" else opciones:
                if orden == "nombre":
                    v = v.split(",")[0]
                if "," in v:
                    a, n = v.split(",", 1)
                    p = _persona(" ".join(_palabras(n)), " ".join(_palabras(a)), "etiqueta (apellidos, nombre)")
                else:
                    p = _partir(_palabras(v), orden, "etiqueta")
                if _valida(p, True):
                    add(p, m.start(), True)
                    break
    # 2. APELLIDOS, NOMBRE en cualquier cuadro
    for m in re.finditer(r"(?:^|¦|\n)\s*([A-Z][A-Z' \-]{3,50}?)\s*,\s*([A-Z][A-Z' \-]{1,30}?)\s*(?=¦|\n|$)", t):
        if re.search(r"\b(?:S\.?\s?L|S\.?\s?A|S\.?\s?L\.?\s?U|C\.?\s?B)\.?$", m.group(2).strip()):
            continue
        add(_persona(" ".join(_palabras(m.group(2))), " ".join(_palabras(m.group(1))), "apellidos, nombre"), m.start(), False)
    # 3. Junto a un DNI válido
    for m in re.finditer(r"\b0?\d{8}[ -]?[A-Z]\b|\b[XYZ][ -]?\d{7}[ -]?[A-Z]\b", t):
        if not dni_valido(m.group(0)):
            continue
        ini = t.rfind("\n", 0, m.start()) + 1
        fin = t.find("\n", m.end()); fin = len(t) if fin < 0 else fin
        previa = t[t.rfind("\n", 0, max(ini - 1, 0)) + 1: max(ini - 1, 0)] if ini > 0 else ""
        for trozo in (t[ini:m.start()], t[m.end():fin], previa):
            for celda in reversed(trozo.split("¦")):
                if re.search(r"\bS\.?\s?[LA]\.?U?\b|\bCIF\b|SOCIEDAD|BANCO", celda):
                    continue
                for g in re.finditer(r"[A-Z][A-Z'\-]+(?: [A-Z][A-Z'\-]+){1,6}", celda):
                    if re.search(DIRECCION, celda[:g.start()]):
                        continue
                    pal = [w for w in g.group(0).split() if w not in NO_NOMBRE or w in PARTICULAS]
                    p = _partir(pal, None, "junto al DNI") if len(pal) == len(g.group(0).split()) else None
                    add(p, m.start(), False)
    return encontradas
