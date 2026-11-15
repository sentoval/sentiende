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
    low = texto.lower()
    nombres = {n: i + 1 for i, n in enumerate(MESES)} | MESES_OTROS
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
    """Fecha de emisión o del documento: la que va junto a su etiqueta; si no hay etiqueta, la más
    reciente que no sea futura (las de nacimiento, alta o antigüedad suelen ser antiguas)."""
    t = norm(texto)
    m = re.search(r"(FECHA DE EMISION|FECHA EMISION|FECHA DE EXPEDICION|EXPEDIDO|EXPEDICION|EMITIDO|EMISION|FECHA DEL DOCUMENTO|"
                  r"FECHA DE EXPEDICIO|DATA D.EMISSIO|A FECHA DE|[A-Z]+, A)\s*:?[^\n\d]{0,12}(\d{1,2})[/.-](\d{1,2})[/.-](\d{2,4})", t)
    if m and (f := _fecha(*m.group(2, 3, 4))):
        return f
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
PARTICULAS = {"DE", "DEL", "LA", "LAS", "LOS", "Y", "I", "DA", "DAS", "DO", "DOS", "SAN", "SANTA"}
CORTE = r"(?=\s+(?:NIF|N\.I\.F|DNI|D\.N\.I|NIE|N\.A\.F|NAF|SEXO|NACIONALIDAD|FECHA|DOMICILIO|CON\s+DNI|PROVISTO|MAYOR|VECIN|CIF|IBAN|CATEGORIA|GRUPO|ANTIG|NUM)\b|\s*[,;:\n(]|\s{2,}|$)"
NO_NOMBRE = set("""DNI NIF NIE CIF NAF NUM NUMERO DOCUMENTO NACIONAL IDENTIDAD ESPANA ESPANOLA ESP SEXO NACIONALIDAD FECHA
NACIMIENTO VALIDO HASTA DOMICILIO CALLE AVDA AVENIDA PLAZA PASEO CTRA CAMINO PISO PUERTA BAJO PROVINCIA MUNICIPIO
BANCO CAJA RURAL SL SA SLU SAU S.L. S.A. SOCIEDAD LIMITADA ANONIMA EMPRESA TRABAJADOR TRABAJADORA EMPLEADO TITULAR
TITULARES DECLARANTE CONTRIBUYENTE SOLICITANTE NOMBRE APELLIDOS APELLIDO CON PROVISTO MAYOR EDAD VECINO VECINA
SEGURIDAD SOCIAL TESORERIA GENERAL AGENCIA TRIBUTARIA INFORME VIDA LABORAL CERTIFICADO NOMINA RECIBO PERIODO
CUENTA IBAN SWIFT BIC CODIGO POSTAL TELEFONO TEL CORREO EMAIL DATOS PERSONALES CATEGORIA GRUPO ANTIGUEDAD
REGISTRO PROPIEDAD FINCA NOTA SIMPLE INFORMATIVA HOJA PAGINA DE A EL EN POR PARA""".split())
NOMBRE_RE = r"([A-Z][A-Z'\-]+(?: [A-Z][A-Z'\-]+){0,5}?)"

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

def _completo(txt, por, apellidos_primero=False):
    pz = _agrupar(txt.split())
    if len(pz) < 2:
        return None
    if apellidos_primero:   # MORALES GIL IVAN: dos apellidos y el resto nombre
        return _persona(" ".join(pz[2:]) or pz[-1], " ".join(pz[:2] if len(pz) > 2 else pz[:1]), por, len(pz) == 3)
    return _persona(pz[0] if len(pz) <= 3 else " ".join(pz[:-2]), " ".join(pz[1:] if len(pz) <= 3 else pz[-2:]), por, len(pz) == 3)

def personas(texto):
    """Nombres de personas que aparecen como titular, trabajador, declarante… con su DNI si está cerca."""
    t = norm(texto)
    encontradas = []
    def add(p, pos):
        if not p or len(p["completo"]) < 6:
            return
        cerca = t[max(0, pos - 60): pos + 160]
        dn = [dni_valido(m.group(0)) for m in re.finditer(r"\b0?\d{8}[ -]?[A-Z]\b|\b[XYZ][ -]?\d{7}[ -]?[A-Z]\b", cerca)]
        p["dni"] = next((x for x in dn if x), None)
        clave = frozenset(p["completo"].upper().split())
        if not any(clave <= frozenset(q["completo"].upper().split()) for q in encontradas):   # ni repetido ni un trozo de otro
            encontradas.append(p)
    # Tarjeta del DNI: APELLIDOS ... / NOMBRE ...
    m = re.search(r"APELLIDOS\s+" + NOMBRE_RE + CORTE + r"[\s\S]{0,80}?\bNOMBRE\s+" + NOMBRE_RE + CORTE, t)
    if m:
        add(_persona(m.group(2), m.group(1), "tarjeta DNI"), m.start())
    # APELLIDOS, NOMBRE (nóminas, certificados)
    for m in re.finditer(r"(?:TRABAJADOR|TRABAJADORA|EMPLEADO|APELLIDOS Y NOMBRE|NOMBRE Y APELLIDOS|DECLARANTE|TITULAR|CONTRIBUYENTE|SOLICITANTE)\s*:?\s*([A-Z][A-Z' \-]{3,60}?),\s*([A-Z][A-Z' \-]{1,40}?)" + CORTE, t):
        add(_persona(m.group(2).strip(), m.group(1).strip(), "apellidos, nombre"), m.start())
    # D./Dña./Don/Doña + nombre completo (orden habitual: nombre y apellidos)
    for m in re.finditer(r"\b(?:D\.?\s?/\s?DNA\.?|DNA\.?|DONA|DON|D\.|SR\.|SRA\.)\s+" + NOMBRE_RE + CORTE, t):
        add(_completo(m.group(1), "D./Dña. nombre apellidos"), m.start())
    # Nota simple, contratos: nombre y apellidos
    for m in re.finditer(r"(?:TITULARIDAD|PROPIETARIO|PROPIETARIA|VENDEDOR|VENDEDORA|COMPRADOR|COMPRADORA|ARRENDATARIO|ARRENDADOR)\s*:?\s+" + NOMBRE_RE + CORTE, t):
        add(_completo(m.group(1), "nombre apellidos"), m.start())
    # Titular de cuenta o declarante sin coma: suele ir apellidos primero
    for m in re.finditer(r"(?:TITULAR(?:ES)?|DECLARANTE|APELLIDOS Y NOMBRE)\s*:?\s+" + NOMBRE_RE + CORTE, t):
        if "," not in t[m.end(): m.end() + 2]:
            add(_completo(m.group(1), "titular (apellidos primero)", apellidos_primero=True), m.start())
    # Sin etiqueta conocida: el nombre suele estar junto a su DNI (misma línea o la de arriba)
    for m in re.finditer(r"\b0?\d{8}[ -]?[A-Z]\b|\b[XYZ][ -]?\d{7}[ -]?[A-Z]\b", t):
        if not dni_valido(m.group(0)):
            continue
        ini = t.rfind("\n", 0, m.start()) + 1
        fin = t.find("\n", m.end()); fin = len(t) if fin < 0 else fin
        previa = t[t.rfind("\n", 0, max(ini - 1, 0)) + 1: max(ini - 1, 0)] if ini > 0 else ""
        if re.search(r"\bS\.? ?[LA]\.?U?\b|\bCIF\b|SOCIEDAD|BANCO", previa):
            previa = ""                                   # la línea de arriba es una empresa
        for trozo in (t[ini:m.start()], t[m.end():fin], previa):
            if (c := re.match(r"\s*([A-Z][A-Z' \-]{3,50}?),\s*([A-Z][A-Z' \-]{1,30}?)\s*(?:$|\s{2,}|[;(])", trozo)):
                add(_persona(c.group(2).strip(), c.group(1).strip(), "junto al DNI (apellidos, nombre)"), m.start())
                break
            for g in re.finditer(r"[A-Z][A-Z'\-]+(?: [A-Z][A-Z'\-]+){1,5}", trozo):
                tramos, act = [], []
                for w in g.group(0).split() + ["DNI"]:          # tramos sin palabras de etiqueta
                    if w in NO_NOMBRE and w not in PARTICULAS:
                        if act: tramos.append(act)
                        act = []
                    else:
                        act.append(w)
                tramos = [x for x in tramos if len([w for w in x if w not in PARTICULAS]) >= 2]
                if tramos:
                    mejor = max(tramos, key=len)
                    while mejor and mejor[0] in PARTICULAS: mejor = mejor[1:]
                    while mejor and mejor[-1] in PARTICULAS: mejor = mejor[:-1]
                    if len(mejor) >= 2:
                        add(_completo(" ".join(mejor), "junto al DNI"), m.start())
                        break
    return encontradas
