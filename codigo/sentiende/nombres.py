# -*- coding: utf-8 -*-
"""Fase 8 · Renombrar (M-08, F-06). Aplica las reglas de la variante (nombres.json):
YYYXXX_nombrecorto_ZZZZ.pdf, carpeta de expediente nombre1apellido1_DNI5_MMAA,
NOINFORMADO sin DNI, -2/-3 si ya existe, -ant para el sustituido, PRIVADO_NO_COMPARTIR_."""
import datetime, re, unicodedata

PARTICULAS = {"de", "del", "la", "las", "los", "y", "i", "da", "das", "do", "dos"}
FORMAS = {"SL": "SL", "S L": "SL", "SA": "SA", "S A": "SA", "SLU": "SLU", "SCOOP": "SCOOP", "SLL": "SLL", "CB": "CB"}

def sin_tildes(s):
    s = unicodedata.normalize("NFD", s or "")
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.replace("ñ", "n").replace("Ñ", "N")

def limpio(s):
    return re.sub(r"[^A-Za-z0-9]", "", sin_tildes(s))

def palabras(s):
    return [p for p in re.split(r"[\s\-]+", sin_tildes(s or "").strip()) if p and p.lower() not in PARTICULAS]

def iniciales(*partes):
    return "".join(p[0].upper() for parte in partes for p in palabras(parte))

def numero_doc(dni):
    """Cifras del DNI/NIE/CIF sin letras (NIE: X=0, Y=1, Z=2)."""
    if not dni:
        return None
    d = dni.upper()
    if d[0] in "XYZ":
        d = str("XYZ".index(d[0])) + d[1:]
    return re.sub(r"\D", "", d) or None

def codigo_persona(persona, sin_dni="NOINFORMADO"):
    """Iván Morales Gil, 12345678Z -> IMG678. Empresa: Talleres Ruiz S.L., B98765432 -> TRSL432."""
    num = numero_doc(persona.get("dni"))
    if persona.get("es_empresa"):
        nombre = sin_tildes(persona["nombre"]).upper().replace(".", " ").replace(",", " ")
        forma = ""
        for f in sorted(FORMAS, key=len, reverse=True):
            if re.search(r"\b" + f + r"\s*$", nombre):
                forma = FORMAS[f]
                nombre = re.sub(r"\b" + f + r"\s*$", "", nombre)
                break
        ini = iniciales(nombre) + forma
    else:
        ini = iniciales(persona.get("nombre"), persona.get("apellido1"), persona.get("apellido2"))
    return ini + (num[-3:] if num else sin_dni)

def carpeta_expediente(persona, fecha, sin_dni="NOINFORMADO"):
    """{Nombre1}{Apellido1}_{DNI5}_{MMAA}: Iván Morales Gil, 12345678Z, nov 2026 -> IvanMorales_45678_1126."""
    num = numero_doc(persona.get("dni"))
    if persona.get("es_empresa"):
        p = palabras(persona["nombre"])
        base = "".join(x.capitalize() for x in p[:2])
    else:
        n = palabras(persona.get("nombre"))[:1]
        a = palabras(persona.get("apellido1"))[:1]
        base = "".join(x.capitalize() for x in n + a)
    return f"{limpio(base)}_{num[-5:] if num else sin_dni}_{fecha:%m%y}"

def _fmt(fecha_iso, formato):
    if not fecha_iso:
        return None
    f = datetime.date.fromisoformat(fecha_iso)
    if f.year < 1900:            # fecha leída de un sello antiguo: se trata como ilegible
        return None
    # 3.1.2 · sin strftime: en Windows «%y» falla con años anteriores a 1900 («format %y requires year >= 1900»)
    return {"MMAA": f"{f.month:02d}{f.year % 100:02d}", "AA": f"{f.year % 100:02d}", "AAAA": f"{f.year:04d}"}[formato]

def dato_distintivo(regla, datos, entidad_abrev=None):
    """Devuelve (texto, ok). Si no se puede leer el dato, ok=False y se usa la fecha de entrada."""
    if not regla:
        return None, True
    partes = regla.split("+")
    out = []
    for p in partes:
        clave, _, formato = p.partition(":")
        if clave == "entidad":
            v = entidad_abrev
        elif clave == "periodo":
            v = _fmt(datos.get("periodo"), formato)
        elif clave == "emision":
            f = datos.get("emision") or (datos["fechas"][0] if datos.get("fechas") else None)
            v = _fmt(f, formato) if f else None
        elif clave == "caducidad":
            v = _fmt(datos.get("caducidad"), formato)
        elif clave == "ejercicio":
            v = str(datos["ejercicio"]) if datos.get("ejercicio") else None
        elif clave == "trimestre":
            tri = datos.get("trimestre")
            v = f"{tri[0]}T{str(tri[1])[-2:]}" if tri and tri[1] else None     # 2T26: 2.º trimestre de 2026 (Joan, 16/11/2026)
        elif clave == "matricula":
            v = datos.get("matricula")
        elif clave == "numero":
            v = None   # n.º de licencia: se pide en la revisión
        else:
            v = None
        if not v and clave == "entidad" and datos.get("serie"):
            continue          # en una serie basta con el periodo
        if not v:
            return None, False
        out.append(v)
    # documentos en serie (recibos, extractos… de la misma cuenta con fechas distintas): cada uno con su periodo
    if datos.get("serie") and not any(p.partition(":")[0] in ("periodo", "emision", "trimestre") for p in partes):
        f = datos.get("periodo") or datos.get("emision") or ((datos.get("fechas") or [None])[0])
        if f:
            out.append(_fmt(f, "MMAA"))
    return "_".join(out), True

class Nombrador:
    def __init__(self, variante):
        self.v = variante
        self.r = variante.nombres

    def nombre(self, tipo, persona, datos, entidad_abrev=None, fecha_entrada=None, privado=False, extension=".pdf"):
        """Devuelve (nombre_de_archivo, revisar: bool, motivo)."""
        doc = self.v.docs.get(tipo)
        if not doc:
            raise ValueError(f"Tipo desconocido: {tipo}")
        regla = self.r["dato_distintivo"].get(doc.get("zzzz"))
        dato, ok = dato_distintivo(regla, datos, entidad_abrev)
        motivo = ""
        if not ok:
            f = fecha_entrada or datetime.date.today()
            dato = f"{f:%m%y}"
            motivo = f"Dato distintivo ({doc.get('zzzz')}) ilegible: se usa la fecha de entrada"
        partes = [codigo_persona(persona, self.r["sin_dni"]), doc["nombrecorto"]] + ([dato] if dato else [])
        ext = extension if tipo in self.r.get("mantener_extension", []) else self.r.get("extension", ".pdf")
        nombre = self.r["separador"].join(partes) + ext
        if privado:
            nombre = self.r["prefijo_privado"] + nombre
        return nombre, not ok, motivo
