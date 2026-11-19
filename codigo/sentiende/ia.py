# -*- coding: utf-8 -*-
"""Controlador IA (versión 3.0). Resuelve solo, con la API de Anthropic, lo que el programa local
no ha sabido resolver, y después informa de cada cosa que ha hecho (con su motivo y «Deshacer»).

Reglas decididas con Joan (16/11/2026):
- Viene APAGADO. Se enciende y apaga con el botón «Controlador IA» de la barra lateral.
- Solo texto: nunca se envían imágenes ni archivos.
- Ningún dato personal sale del equipo: nombres, DNI/NIE/NIF, IBAN, teléfonos, correos, direcciones,
  fechas de nacimiento, matrículas, códigos de verificación… se cambian por fichas ([PERSONA_1],
  [DNI_1], [EXP_A]…). La tabla que traduce las fichas se queda en el equipo. Los importes y las
  fechas del documento sí se envían. En vez de los datos se envían «pistas de parecido»
  («[DNI_2] ≈ DNI de [PERSONA_1]: 8 de 8 cifras, falta la letra»).
- Expedientes nuevos: NUNCA los crea la IA; tampoco añade personas nuevas a un expediente.
  Si hace falta, deja el documento para Joan con su propuesta.
- Por debajo del umbral de seguridad (90 %) aplica igualmente, pero lo deja marcado para revisar.
  «Misma persona» siempre sale como aviso, con «Deshacer y decidir».
- Límites de gasto por día, mes y lote: al llegar se pausa y avisa; el resto sigue en local.
- No se entrena el modelo: cada consulta lleva un manual (reglas, tipos de documento, instrucciones
  de Joan y ejemplos anónimos de sus correcciones).
- Las tarifas se comprueban como máximo una vez al día (al encender, o a las 24 h si sigue encendida).
- La clave de la API se guarda cifrada con la cuenta de Windows (DPAPI)."""
import datetime, difflib, json, re, threading, time, urllib.error, urllib.request
from pathlib import Path

from .extraer import norm, letra_dni, es_nombre, es_apellido, PARTICULAS
from .correo import proteger, desproteger

URL_API = "https://api.anthropic.com/v1/messages"
URL_MODELOS = "https://api.anthropic.com/v1/models"
URL_PRECIOS = "https://platform.claude.com/docs/en/about-claude/pricing"
URL_CONSOLA = "https://platform.claude.com/settings/billing"     # saldo y compra de créditos de la API
VERSION_API = "2023-06-01"

MODELOS = {
    "claude-haiku-5-5": {"nombre": "Claude Haiku 5.5", "desc": "rápido y barato (recomendado)", "pagina": "Haiku 5.5"},
    "claude-sonnet-5-5": {"nombre": "Claude Sonnet 5.5", "desc": "más preciso", "pagina": "Sonnet 5.5"},
    "claude-opus-5-5": {"nombre": "Claude Opus 5.5", "desc": "casos difíciles", "pagina": "Opus 5.5"},
}
# Dólares por millón de tokens (página oficial de precios, consultada el 16/11/2026).
# Haiku 5.5: por encima de 100.000 tokens de entrada en una consulta, todo cuesta 5 veces más.
PRECIOS = {
    "claude-haiku-5-5": {"entrada": 0.10, "escritura": 0.125, "cache": 0.01, "salida": 0.50, "umbral_largo": 100000, "x_largo": 5},
    "claude-sonnet-5-5": {"entrada": 2.0, "escritura": 2.5, "cache": 0.10, "salida": 10.0},
    "claude-opus-5-5": {"entrada": 4.0, "escritura": 5.0, "cache": 0.20, "salida": 20.0},
}
FUNCIONES = {
    "clasificar": ["Clasificar documentos dudosos", "Cuando el programa no sabe qué tipo es o la confianza es baja."],
    "separar": ["Separar y ordenar páginas", "Separa PDF con varios documentos, ordena páginas sueltas (el final de una con el principio de la siguiente, pies y códigos de verificación) y une fotos del mismo documento."],
    "fechas": ["Fechas y periodos", "Fecha del documento, mes de la nómina, trimestre del modelo."],
    "personas": ["Persona y titular", "A qué persona pertenece y si un nombre escrito de otra forma es la misma persona."],
    "asignar": ["Asignar a un expediente existente", "Solo a expedientes que ya existen y a personas que ya están en ellos. Nunca crea expedientes."],
    "terceros": ["Terceros", "Personas que no se fichan: notario, vendedores, representantes del banco…"],
    "limbo": ["Mandar al Limbo", "Si el documento no es de ningún cliente, lo manda al Limbo en vez de dejarlo para ti."],
}
INSTRUCCIONES_SERIE = """- Las nóminas de la misma empresa y mes son de la misma persona aunque cambie el formato.
- Si un recibo de autónomo no dice el mes, usa la fecha de cargo.
- La vida laboral siempre va al titular, nunca al avalista.
- Para ordenar páginas sueltas, une la última frase de una página con la primera de la siguiente."""
POR_DEFECTO = {
    "activo": False, "clave": "", "modelo": "claude-haiku-5-5", "actua": "lote", "umbral": 90,
    "limite_dia": 0.50, "limite_mes": 10.0, "limite_lote": 0.10, "pausar": True, "cambio": 0.86,
    "funciones": {k: k != "limbo" for k in FUNCIONES}, "instrucciones": INSTRUCCIONES_SERIE, "aprender": True,
    "precios": PRECIOS, "tarifas": {"ultima": None, "estado": "", "detalle": "", "cambios": {}}, "extra_hoy": {}, "activado_en": None,
}
COMPARATIVA = {"fecha": "16/11/2026", "documentos": 20,
               "supuesto": "~4.000 tokens de manual + ~1.500 de documento + ~300 de respuesta por consulta",
               "modelos": [{"modelo": "claude-haiku-5-5", "desde": 0.01, "hasta": 0.03},
                           {"modelo": "claude-sonnet-5-5", "desde": 0.15, "hasta": 0.30},
                           {"modelo": "claude-opus-5-5", "desde": 0.30, "hasta": 0.60}]}

ESQUEMA = """
CREATE TABLE IF NOT EXISTS ia_consultas(
  id INTEGER PRIMARY KEY, fecha TEXT, lote_id INTEGER, documento_id INTEGER, clase TEXT, modelo TEXT,
  t_entrada INTEGER DEFAULT 0, t_salida INTEGER DEFAULT 0, t_cache INTEGER DEFAULT 0, t_escritura INTEGER DEFAULT 0,
  coste_usd REAL DEFAULT 0, segundos REAL, enviado TEXT, respuesta TEXT, mapa TEXT, error TEXT);
CREATE TABLE IF NOT EXISTS ia_acciones(
  id INTEGER PRIMARY KEY, fecha TEXT, lote_id INTEGER, documento_id INTEGER, consulta_id INTEGER, tipo TEXT,
  titulo TEXT, detalle TEXT, motivo TEXT, seguridad INTEGER, estado TEXT, deshacer TEXT, revisada INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS ia_lotes(lote_id INTEGER PRIMARY KEY, estado TEXT, fecha TEXT, coste_usd REAL DEFAULT 0, nota TEXT);
CREATE TABLE IF NOT EXISTS ia_ejemplos(id INTEGER PRIMARY KEY, fecha TEXT, contexto TEXT, correcto TEXT);
"""


class ErrorIA(RuntimeError):
    pass


def hoy():
    return datetime.date.today().isoformat()


def ahora():
    return datetime.datetime.now().isoformat(timespec="seconds")


def letras(n):
    s = ""
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


# ====================================================================== fichas (datos tapados)
# Palabras de documento que también son nombres o apellidos: no se tapan sueltas (sí dentro de un nombre completo).
COMUNES = {"SEGURIDAD", "SOCIAL", "AGENCIA", "TRIBUTARIA", "ESTATAL", "ADMINISTRACION", "HACIENDA", "BANCO", "CAJA", "RURAL", "GENERAL",
           "VALENCIA", "VALENCIANA", "MADRID", "ESPAÑA", "ESPANA", "CASTILLA", "LEON", "MURCIA", "GRANADA", "TOLEDO", "SEVILLA", "CORDOBA",
           "NOMINA", "TOTAL", "SALDO", "IMPORTE", "FECHA", "EUROS", "CUENTA", "LIQUIDO", "BRUTO", "NETO", "PERIODO", "EMPRESA", "CENTRO",
           "NOTARIO", "NOTARIA", "REGISTRO", "PROPIEDAD", "MAYOR", "NUEVA", "NUEVO", "REAL", "CRUZ", "SANTOS", "REYES", "PAZ", "LUZ", "MAR",
           "CAMPO", "MONTE", "PRADO", "VEGA", "PUERTO", "SIERRA", "TORRE", "TORRES", "PALACIO", "IGLESIA", "CALLE", "PLAZA", "SANTA", "SANTO",
           "ROSA", "BLANCO", "BLANCA", "LUNA", "SOL", "ROMERO", "HERRERO", "PASTOR", "CABALLERO", "GUERRA", "MORENO", "DELGADO", "MEDINA",
           "MERCADONA", "CAIXABANK", "BBVA", "SANTANDER", "UNICAJA", "SABADELL", "BANKINTER", "INGRESOS", "GASTOS", "PRESTAMO", "HIPOTECA"}


def vigilar(texto, palabras=()):
    """Última comprobación antes de enviar: qué tipos de dato personal siguen a la vista (sin decir cuáles).
    Si devuelve algo, la consulta NO se envía."""
    t = re.sub(r"\[[A-Z]+_[A-Z0-9]+\]", " ", texto or "")
    fallos = []
    if re.search(r"\b0?\d{8}\s?[A-Z]\b|\b[XYZ]\d{7}[A-Z]\b|\b\d{2}\.\d{3}\.\d{3}-?[A-Z]\b|\b(?:\d ){7}\d ?[A-Z]\b", t):
        fallos.append("un DNI o NIE")
    if re.search(r"(?:DNI|NIF|NIE|D\.N\.I|N\.I\.F|N\.I\.E)\.?[^\n]{0,14}?\b\d{7,9}\b", t):
        fallos.append("un número de DNI o NIF")
    if re.search(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", t):
        fallos.append("un correo")
    if re.search(r"(?<![\d,.])[6789]\d{2}\s?\d{3}\s?\d{3}(?![\d,])", t):
        fallos.append("un teléfono")
    if re.search(r"\bES\d{2}(?:\s?\d{4}){5}\b", t):
        fallos.append("una cuenta bancaria")
    ws = {w for w in palabras if len(w) >= 4 and w not in PARTICULAS and w not in COMUNES}
    if ws and set(re.findall(r"[A-ZÑÇ]{4,}", t)) & ws:
        fallos.append("un nombre o apellido conocido")
    return fallos


class Mascara:
    """Cambia datos personales por fichas. mapa: ficha -> dato real (solo en el equipo)."""

    def __init__(self):
        self.mapa, self._inv, self._n = {}, {}, {}

    def ficha(self, clase, real, clave=None):
        clave = (clase, clave if clave is not None else norm(str(real)).strip())
        if clave in self._inv:
            return self._inv[clave]
        n = self._n.get(clase, 0) + 1
        self._n[clase] = n
        t = f"[{clase}_{letras(n) if clase == 'EXP' else n}]"
        self._inv[clave], self.mapa[t] = t, real
        return t

    def buscar(self, clase, clave):
        return self._inv.get((clase, clave))

    # ------------------------------------------------------------------ texto
    def tapar(self, texto, personas=(), palabras=()):
        """personas: [{'clave', 'nombre', 'apellido1', 'apellido2', 'dni', 'ficha'?}] (las leídas y las candidatas).
        Devuelve el texto en mayúsculas, sin tildes y sin datos personales."""
        t = re.sub(r"\b(?:\d ){7}\d ?[A-Z]\b", lambda m: m.group(0).replace(" ", ""), norm(texto or ""))   # DNI con cifras separadas
        # códigos de verificación y similares (antes que los números sueltos)
        t = re.sub(r"((?:C[OÓ]DIGO\s+(?:SEGURO\s+)?(?:DE\s+)?VERIFICACI[OÓ]N|CSV|C\.S\.V\.?|REF(?:ERENCIA)?\s+ELECTR[OÓ]NICA)[^\n\w]{0,6})([A-Z0-9][A-Z0-9-]{9,})",
                   lambda m: m.group(1) + self.ficha("CSV", m.group(2)), t)
        t = re.sub(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", lambda m: self.ficha("EMAIL", m.group(0)), t)
        t = re.sub(r"\b[A-Z]{2}\d{2}(?:[ -]?[A-Z0-9]{4}){4,7}(?:[ -]?[A-Z0-9]{1,3})?\b", lambda m: self.ficha("IBAN", m.group(0), re.sub(r"\W", "", m.group(0))), t)
        t = re.sub(r"\b\d{4}[ -]\d{4}[ -]\d{2}[ -]\d{10}\b", lambda m: self.ficha("CUENTA", m.group(0), re.sub(r"\D", "", m.group(0))), t)
        t = re.sub(r"\b\d{7}[A-Z]{2}\d{4}[A-Z]\d{4}[A-Z]{2}\b", lambda m: self.ficha("CATASTRO", m.group(0)), t)
        t = re.sub(r"((?:NACIMIENTO|NACIDO|NACIDA|NAIXEMENT|F\.?\s?NAC\.?|FECHA NAC\.?)[^\n\d]{0,25})(\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4})",
                   lambda m: m.group(1) + self.ficha("FNAC", m.group(2)), t)
        # DNI / NIE / NIF (con letra, con un 0 delante, o de 8-9 cifras junto a la etiqueta) y CIF
        def dni(m):
            raw = re.sub(r"[\s.-]", "", m.group(0))
            if len(raw) == 10 and raw[0] == "0":
                raw = raw[1:]
            return self.ficha("DNI", raw, re.sub(r"[^0-9XYZ]", "", raw[:-1]) if raw[-1:].isalpha() and len(raw) > 8 else raw)
        t = re.sub(r"\b[XYZ][ .-]?\d{7}[ -]?[A-Z]\b|\b0?\d{8}[ -]?[A-Z]\b|\b\d{2}\.\d{3}\.\d{3}[ -]?[A-Z]\b", dni, t)
        t = re.sub(r"((?:DNI|NIF|NIE|D\.N\.I\.?|N\.I\.F\.?|N\.I\.E\.?)(?:[^\n\d\[]{0,4}(?:N[º°O2.]?|NUM\.?|NUMERO|NÚMERO)?)[^\n\dA-Z\[]{0,6})(\d{7,9}[ -]?[A-Z]?)\b",
                   lambda m: m.group(1) + self.ficha("DNI", m.group(2), re.sub(r"\D", "", m.group(2))[-8:]), t)
        t = re.sub(r"\b[ABCDEFGHJNPQRSUVW][ -]?\d{7}[ -]?[0-9A-J]\b", lambda m: self.ficha("NIF", m.group(0), re.sub(r"\W", "", m.group(0))), t)
        t = re.sub(r"\b\d{2}\s*/\s*\d{7,8}\s*[-/]?\s*\d{2}\b|\b\d{2}[ /]?\d{8}[ /]?\d{2}\b", lambda m: self.ficha("NAF", m.group(0), re.sub(r"\D", "", m.group(0))), t)
        t = re.sub(r"(?<![\d,.])(?:\+?34[ -]?)?[6789](?:[ -]?\d){8}(?![\d,])", lambda m: self.ficha("TEL", m.group(0), re.sub(r"\D", "", m.group(0))[-9:]), t)
        t = re.sub(r"\b\d{4}[ -]?[BCDFGHJKLMNPRSTVWXYZ]{3}\b", lambda m: self.ficha("MATRICULA", m.group(0), re.sub(r"\W", "", m.group(0))), t)
        t = re.sub(r"\b(?:C/|CALLE|CL\.|AVDA\.?|AVENIDA|AV\.|PLAZA|PZA\.?|PASEO|PG\.?|CAMINO|CTRA\.?|CARRETERA|PARTIDA|URBANIZACI[OÓ]N|URB\.|CARRER|PLAÇA|PASSEIG|AVINGUDA)\s+[^\n¦,;]{2,50}?(?:,?\s*(?:N[ºO°.]?\s*)?\d{1,4}[A-Z]?\b(?:[,\s]+(?:\d{1,2}[ºª°]?\s*[A-Z]?|ESC\.?\s*\w+|PTA\.?\s*\w+|PISO\s*\w+)){0,3})",
                   lambda m: self.ficha("DIRECCION", m.group(0)), t)
        # abreviaturas sin punto al principio de una línea o de un campo: «AV GASPAR …», «CL MAYOR 12», «C SAN VICENTE 3»
        t = re.sub(r"(?m)(^|¦|:)(\s*)((?:AV|AVD|AVDA|CL|C|CR|CRTA|PZ|PZA|PS|PSO|CM|CMNO|UR|URB|PG|PL|RD|TR|TRV|PJ|PTDA|CRER|PÇA)\s+[A-Z][^\n¦]{2,60})",
                   lambda m: m.group(1) + m.group(2) + self.ficha("DIRECCION", m.group(3).strip()), t)
        t = re.sub(r"((?:DOMICILIO|DIRECCI[OÓ]N|RESIDENCIA|DOMICILIADO EN|CON DOMICILIO EN|VECINO DE)(?:\s+FISCAL|\s+SOCIAL)?[\s:.]{1,4})(?!\[)([^\n¦]{4,70})",
                   lambda m: m.group(1) + self.ficha("DIRECCION", m.group(2).strip()), t)
        # personas conocidas: primero los nombres completos (en varios órdenes) y después cada palabra suelta
        reemplazos = []
        for p in personas:
            f = p.get("ficha")
            if not f:
                continue
            n, a1, a2 = (norm(p.get(k) or "").strip() for k in ("nombre", "apellido1", "apellido2"))
            for v in {f"{n} {a1} {a2}", f"{a1} {a2} {n}", f"{a1} {a2}, {n}", f"{a1} {a2},{n}", f"{n} {a1}", f"{a1}, {n}", f"{a1} {a2}"}:
                v = re.sub(r"\s+", " ", v).strip(" ,")
                if len(v) > 3 and " " in v:
                    reemplazos.append((v, f))
        for v, f in sorted(reemplazos, key=lambda x: -len(x[0])):
            t = re.sub(r"(?<![A-Z])" + re.escape(v).replace(r"\ ", r"\s+") + r"(?![A-Z])", f, t)
        sueltas = {}
        for p in personas:
            if p.get("ficha") and p.get("leida"):
                for w in norm(" ".join(p.get(k) or "" for k in ("nombre", "apellido1", "apellido2"))).split():
                    if len(w) >= 3 and w not in PARTICULAS:
                        sueltas.setdefault(w, p["ficha"])
        if sueltas:
            t = re.sub(r"(?<![A-Z\[_])(" + "|".join(map(re.escape, sorted(sueltas, key=len, reverse=True))) + r")(?![A-Z\]_])", lambda m: sueltas[m.group(1)], t)
        # nombres detrás de una etiqueta: «NOMBRE: …», «TITULAR …», «D.ª …», «A NOMBRE DE …», «SOBRE … CON NIF»
        pw = r"(?!(?:CON|NIF|DNI|NIE|CIF|EN|QUE|PARA|POR|SEGUN|MAYOR|EDAD|VECINO|VECINA|DOMICILIO|NACIDO|NACIDA|PROVISTO|PROVISTA|TITULAR|COMO|EL|LOS|LAS)\b)[A-ZÑÇ][A-ZÑÇ'-]+"
        nom = pw + r"(?:[ ]+(?:(?:DE|DEL|LA|LAS|LOS|Y|I)[ ]+)?" + pw + r"){1,4}(?:[ ]*,[ ]*" + pw + r"(?:[ ]+" + pw + r"){0,2})?"
        etiquetas = (r"APELLIDOS\s+Y\s+NOMBRE|NOMBRE\s+Y\s+APELLIDOS|APELLIDOS,?\s+NOMBRE|NOMBRE\s+COMPLETO|NOMBRE|APELLIDOS|COGNOMS\s+I\s+NOM|NOM\s+I\s+COGNOMS|NOM|COGNOMS|"
                     r"TITULAR(?:ES)?|COTITULAR(?:ES)?|TRABAJADOR(?:A)?|TREBALLADOR(?:A)?|EMPLEADO(?:A)?|CONTRIBUYENTE|DECLARANTE|C[OÓ]NYUGE|PERCEPTOR(?:A)?|"
                     r"SOLICITANTE|INTERESADO(?:A)?|BENEFICIARIO(?:A)?|PRESTATARIO(?:S|A|AS)?|AVALISTA(?:S)?|FIADOR(?:ES|A)?|COMPRADOR(?:ES|A)?|VENDEDOR(?:ES|A)?|"
                     r"ARRENDATARIO(?:A)?|ARRENDADOR(?:A)?|PROPIETARIO(?:A)?|FIRMANTE|D\./D(?:Ñ|N)?A\.?|D\.ª|DÑA\.?|DNA\.|DOÑA|DON|D\.|SR\.|SRA\.|SENYOR(?:A)?|A NOMBRE DE|EN NOMBRE DE|A FAVOR DE")
        def etiqueta(m):
            v = m.group(3)
            pal = [w for w in re.split(r"[ ,]+", v) if w and w not in PARTICULAS]
            if len(pal) < 2:
                return m.group(0)
            return m.group(1) + m.group(2) + self.ficha("NOMBRE", v.strip(), norm(" ".join(sorted(pal))))
        nom_l = nom.replace("[ ]", "[ \\n]")          # detrás de una etiqueta el nombre puede seguir en la línea siguiente
        t = re.sub(r"(?<![A-Z])(" + etiquetas + r")([\s:.¦-]{0,4})(?!\[)(" + nom_l + r")", etiqueta, t)
        t = re.sub(r"\b(SOBRE)(\s+)(?!\[)(" + nom + r")(?=\s*,?\s*(?:CON\s+)?(?:N\.?I\.?F|D\.?N\.?I|N\.?I\.?E|\[DNI_))", etiqueta, t)
        # «APELLIDO APELLIDO, NOMBRE» en una línea o un campo (cabecera de las nóminas, listados…)
        def coma(m):
            izq, der = m.group(2), m.group(3)
            if any(es_nombre(w) for w in der.split()) or any(es_apellido(w) for w in izq.split()):
                return m.group(1) + self.ficha("NOMBRE", f"{izq}, {der}", norm(" ".join(sorted((izq + " " + der).split()))))
            return m.group(0)
        t = re.sub(r"(?m)(^|¦|:\s)\s*([A-ZÑÇ][A-ZÑÇ'-]+(?:\s+(?:DE|DEL|LA|Y|I)?\s*[A-ZÑÇ][A-ZÑÇ'-]+){0,3})\s*,\s*([A-ZÑÇ][A-ZÑÇ'-]+(?:\s+[A-ZÑÇ][A-ZÑÇ'-]+){0,2})(?=\s*(?:$|¦|\d|\[))", coma, t)
        # palabras de nombres de cualquier persona conocida (del lote o de la base) que sigan sueltas
        if palabras:
            ws = sorted({w for w in palabras if len(w) >= 4 and w not in PARTICULAS and w not in COMUNES}, key=len, reverse=True)
            for k in range(0, len(ws), 300):
                t = re.sub(r"(?<![A-Z\[_])(" + "|".join(map(re.escape, ws[k:k + 300])) + r")(?![A-Z\]_])", lambda m: self.ficha("NOMBRE", m.group(1)), t)
        # red de seguridad: dos o más palabras seguidas, alguna de nombre de pila y el resto nombre o apellido
        def otros(m):
            texto_m = m.group(0)
            cola = re.search(r"(\s+(?:CON|EN|QUE|PARA|POR|Y|DE|DEL|SEGUN|COMO|NIF|DNI|NIE))+$", texto_m)
            if cola:                      # «… ROIG CON» → se tapa el nombre y se deja «CON»
                return otros_n(texto_m[:cola.start()]) + texto_m[cola.start():]
            return otros_n(texto_m)
        def otros_n(texto_m):
            pal = [w for w in texto_m.split() if w not in PARTICULAS]
            if len(pal) >= 2 and any(es_nombre(w) for w in pal) and sum(es_apellido(w) or es_nombre(w) for w in pal) >= len(pal) - 1 \
                    and not any(w in COMUNES for w in pal):
                return self.ficha("NOMBRE", texto_m)
            return texto_m
        t = re.sub(r"\b[A-ZÑÇ]{2,}(?:\s+(?:DE|DEL|LA|LOS|LAS|Y|I)?\s*[A-ZÑÇ]{2,}){1,4}\b", otros, t)
        return t


# ====================================================================== pistas de parecido
def _cifras(dni):
    return re.sub(r"\D", "", dni or "")


def pista_dni(a, b):
    """Cómo se parece el DNI leído (a) al fichado (b), sin decir ninguno de los dos."""
    if not a or not b:
        return None
    a, b = a.upper().replace(" ", "").replace("-", ""), b.upper().replace(" ", "").replace("-", "")
    if a == b:
        return "es el mismo DNI"
    ca, cb = _cifras(a), _cifras(b)
    if ca and ca == cb:
        if not a[-1:].isalpha() or not b[-1:].isalpha():
            return f"{len(ca)} de {len(cb)} cifras iguales, falta la letra"
        return f"{len(ca)} de {len(cb)} cifras iguales, letra distinta (posible error de lectura)"
    if len(ca) == len(cb) and len(ca) >= 7:
        iguales = sum(x == y for x, y in zip(ca, cb))
        if iguales >= len(ca) - 1:
            return f"{iguales} de {len(cb)} cifras iguales (posible error de lectura)"
    return None


def pista_nombre(a, b):
    """a, b: dicts con nombre/apellido1/apellido2. Devuelve (porcentaje, explicación) o None."""
    na, nb = norm(a.get("nombre") or "").split(), norm(b.get("nombre") or "").split()
    aa = [x for x in norm(f'{a.get("apellido1") or ""} {a.get("apellido2") or ""}').split() if x not in PARTICULAS]
    ab = [x for x in norm(f'{b.get("apellido1") or ""} {b.get("apellido2") or ""}').split() if x not in PARTICULAS]
    if not (na or aa) or not (nb or ab):
        return None
    ta, tb = " ".join(sorted(na + aa)), " ".join(sorted(nb + ab))
    pct = round(100 * difflib.SequenceMatcher(None, ta, tb).ratio())
    motivos = []
    if na != nb and na and nb and (set(na) < set(nb) or set(nb) < set(na)):
        motivos.append(f"nombre compuesto incompleto ({min(len(na), len(nb))} de {max(len(na), len(nb))} nombres)")
    elif na != nb and na and nb and difflib.SequenceMatcher(None, " ".join(na), " ".join(nb)).ratio() > .8:
        motivos.append("una letra distinta en el nombre (posible error de lectura)")
    if aa != ab:
        if aa and ab and (aa == ab[:len(aa)] or ab == aa[:len(ab)]):
            motivos.append("falta un apellido")
        elif sorted(aa) == sorted(ab):
            motivos.append("apellidos en otro orden")
        elif len(aa) == len(ab) and difflib.SequenceMatcher(None, " ".join(aa), " ".join(ab)).ratio() > .85:
            motivos.append("una letra distinta en los apellidos (posible error de lectura)")
    elif na == nb:
        motivos.append("nombre y apellidos iguales")
    if motivos and not any("iguales" in m for m in motivos) and aa == ab:
        motivos.append("apellidos iguales")
    if pct < 60 and not motivos:
        return None
    return pct, " · ".join(motivos) or "parecido"


# ====================================================================== precios
def coste(precios, modelo, uso):
    p = precios.get(modelo) or PRECIOS.get(modelo) or PRECIOS["claude-haiku-5-5"]
    e, w, c, s = (int(uso.get(k) or 0) for k in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens", "output_tokens"))
    x = p.get("x_largo", 1) if p.get("umbral_largo") and e + w + c > p["umbral_largo"] else 1
    return x * (e * p["entrada"] + w * p.get("escritura", p["entrada"] * 1.25) + c * p.get("cache", p["entrada"] * .1) + s * p["salida"]) / 1e6


def leer_precios(html):
    """Saca de la página oficial los precios de los tres modelos. Devuelve {modelo: {...}} o lanza ErrorIA."""
    txt = re.sub(r"<[^>]+>", " ", html or "")
    for a, b in (("&nbsp;", " "), ("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"), ("&#36;", "$"), ("&#x24;", "$")):
        txt = txt.replace(a, b)
    txt = re.sub(r"\s+", " ", txt)
    out = {}
    for mid, m in MODELOS.items():
        ok = None
        for pos in [x.start() for x in re.finditer(re.escape(m["pagina"]), txt)]:
            trozo = txt[pos:pos + 400]
            siguiente = min([trozo.find(o["pagina"], 3) for o in MODELOS.values() if trozo.find(o["pagina"], 3) > 0] or [400])
            vals = [float(v) for v in re.findall(r"\$\s?(\d+(?:\.\d+)?)", trozo[:siguiente])]
            if len(vals) >= 5 and vals[0] < vals[4]:
                ok = {"entrada": vals[0], "escritura": vals[1], "cache": vals[3], "salida": vals[4]}
                break
        if not ok:
            raise ErrorIA(f"No encuentro el precio de {m['nombre']} en la página de Anthropic.")
        out[mid] = ok
    return out


# ====================================================================== cliente de la API
ESFUERZO = "low"        # Joan (16/11, 19:00): esfuerzo bajo siempre; si hiciera falta más, se valorará


def llamar_api(clave, modelo, sistema, mensaje, max_tokens=4000, timeout=120):
    """Una consulta a la API de mensajes. Devuelve (texto, uso). El manual va en caché (más barato si se repite).
    Los modelos 5.5 piensan antes de contestar y ese razonamiento cuenta dentro de max_tokens: si la respuesta
    se queda sin texto por falta de margen, se repite una vez con el doble (solo se paga lo que se usa)."""
    total, texto = {}, ""
    for intento in (max_tokens, max_tokens * 2):
        texto, uso, motivo = _llamar(clave, modelo, sistema, mensaje, intento, timeout)
        for k, v in uso.items():
            if isinstance(v, (int, float)):
                total[k] = total.get(k, 0) + v
        if texto.strip() or motivo != "max_tokens":
            break
    return texto, total


def _llamar(clave, modelo, sistema, mensaje, max_tokens, timeout):
    cuerpo = {"model": modelo, "max_tokens": max_tokens, "output_config": {"effort": ESFUERZO},
              "system": [{"type": "text", "text": sistema, "cache_control": {"type": "ephemeral"}}],
              "messages": [{"role": "user", "content": mensaje}]}
    req = urllib.request.Request(URL_API, data=json.dumps(cuerpo).encode("utf-8"), method="POST",
                                 headers={"x-api-key": clave, "anthropic-version": VERSION_API, "content-type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            j = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            msg = json.loads(e.read().decode("utf-8")).get("error", {}).get("message", "")
        except Exception:
            msg = ""
        if e.code == 401:
            raise ErrorIA("La clave de la API no es válida.")
        if e.code == 400 and "credit" in msg.lower():
            raise ErrorIA("No quedan créditos en tu cuenta de la API: cómpralos en la consola de Anthropic.")
        if e.code in (429, 529, 503):
            raise ErrorIA("La API está ocupada ahora mismo: se volverá a intentar más tarde.")
        raise ErrorIA(f"La API ha respondido con un error ({e.code}): {msg or e.reason}")
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise ErrorIA(f"Sin conexión con la API: {getattr(e, 'reason', e)}")
    texto = "".join(b.get("text", "") for b in j.get("content", []) if b.get("type") == "text")
    return texto, j.get("usage", {}), j.get("stop_reason")


def json_de(texto):
    """El primer objeto JSON de la respuesta (aunque venga con texto alrededor)."""
    m = re.search(r"\{.*\}", texto or "", re.S)
    if not m:
        raise ErrorIA("La IA no ha respondido nada útil")
    try:
        return json.loads(m.group(0))
    except ValueError:
        raise ErrorIA("La respuesta de la IA no se entiende.")


# ====================================================================== el controlador
class ControladorIA:
    def __init__(self, motor, cliente=None, descargar=None):
        """cliente(clave, modelo, sistema, mensaje, max_tokens) -> (texto, uso). En las pruebas se pasa uno simulado.
        descargar(url, cabeceras) -> texto (para comprobar las tarifas)."""
        self.m, self.a = motor, motor.almacen
        self.db = self.a.db
        self.db.executescript(ESQUEMA)
        cols = {r[1] for r in self.db.execute("PRAGMA table_info(ia_acciones)")}
        if "origen" not in cols:          # 3.0.2: las acciones del contexto del lote (local) van en el mismo informe
            self.db.execute("ALTER TABLE ia_acciones ADD COLUMN origen TEXT DEFAULT 'ia'"); self.db.commit()
        self.cliente = cliente or llamar_api
        self.descargar = descargar or self._descargar
        self.trabajando = False
        self.error = None
        self.pausa = None
        self._cerrojo = threading.Lock()
        self.cerrojo = threading.RLock()        # el del motor (lo pone el servidor) para lo que se hace en segundo plano

    # ------------------------------------------------------------------ ajustes
    @property
    def _ruta(self):
        return self.m.carpetas.datos / "ia.json"

    def ajustes(self, con_clave=False):
        aj = json.loads(json.dumps(POR_DEFECTO))
        if self._ruta.exists():
            try:
                g = json.loads(self._ruta.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                g = {}
            for k, v in g.items():
                if isinstance(v, dict) and isinstance(aj.get(k), dict) and k != "extra_hoy":
                    aj[k].update(v)
                else:
                    aj[k] = v
        if not con_clave:
            aj["tiene_clave"] = bool(aj.pop("clave", ""))
        return aj

    def _escribir(self, aj):
        aj = {k: v for k, v in aj.items() if k != "tiene_clave"}
        self.m.carpetas.datos.mkdir(parents=True, exist_ok=True)
        self._ruta.write_text(json.dumps(aj, ensure_ascii=False, indent=1), encoding="utf-8")

    def guardar(self, nuevos):
        aj = self.ajustes(con_clave=True)
        if "clave" in nuevos:
            c = (nuevos.get("clave") or "").strip()
            if c and not c.startswith("sk-"):
                raise ErrorIA("Eso no parece una clave de la API de Anthropic (empieza por «sk-ant-»).")
            aj["clave"] = proteger(c) if c else ""
            if not c:
                aj["activo"] = False
        if "modelo" in nuevos:
            if nuevos["modelo"] not in MODELOS:
                raise ErrorIA("Modelo desconocido.")
            aj["modelo"] = nuevos["modelo"]
        if "actua" in nuevos:
            aj["actua"] = "manual" if nuevos["actua"] == "manual" else "lote"
        for k, lo, hi in (("limite_dia", 0.01, 1000), ("limite_mes", 0.01, 10000), ("limite_lote", 0.001, 1000), ("cambio", 0.1, 10), ("umbral", 50, 100)):
            if k in nuevos:
                try:
                    v = float(str(nuevos[k]).replace(",", "."))
                except ValueError:
                    raise ErrorIA(f"Valor no válido: {nuevos[k]}")
                aj[k] = round(max(lo, min(hi, v)), 4)
        if aj["limite_dia"] > aj["limite_mes"]:
            raise ErrorIA("El límite del día no puede ser mayor que el del mes.")
        for k in ("pausar", "aprender"):
            if k in nuevos:
                aj[k] = bool(nuevos[k])
        if "funciones" in nuevos:
            aj["funciones"] = {k: bool(nuevos["funciones"].get(k, aj["funciones"].get(k))) for k in FUNCIONES}
        if "instrucciones" in nuevos:
            aj["instrucciones"] = str(nuevos["instrucciones"] or "")[:6000]
        if "precios" in nuevos:
            for mid, p in (nuevos["precios"] or {}).items():
                if mid in MODELOS:
                    base = aj["precios"].setdefault(mid, dict(PRECIOS[mid]))
                    for c in ("entrada", "salida", "cache", "escritura"):
                        if c in p:
                            base[c] = max(0.0, float(str(p[c]).replace(",", ".")))
        self._escribir(aj)
        self.pausa = None
        return self.ajustes()

    def clave(self):
        g = self.ajustes(con_clave=True).get("clave")
        return desproteger(g) if g else ""

    def encender(self, activo):
        aj = self.ajustes(con_clave=True)
        if activo and not aj.get("clave"):
            raise ErrorIA("Primero escribe tu clave de la API en Ajustes › Controlador IA.")
        aj["activo"] = bool(activo)
        if activo:
            aj["activado_en"] = ahora()
        self._escribir(aj)
        self.pausa = None
        self.error = None
        if activo:
            threading.Thread(target=lambda: self.comprobar_tarifas(), daemon=True).start()
        return self.resumen()

    # ------------------------------------------------------------------ gasto y límites (en euros)
    def gasto(self, desde=None, lote_id=None):
        q, p = "SELECT COALESCE(SUM(coste_usd), 0), COUNT(*) FROM ia_consultas WHERE error IS NULL", []
        if desde:
            q += " AND fecha >= ?"; p.append(desde)
        if lote_id:
            q += " AND lote_id = ?"; p.append(lote_id)
        usd, n = self.db.execute(q, p).fetchone()
        return usd * self.ajustes()["cambio"], n

    def limites(self):
        aj = self.ajustes()
        extra = (aj.get("extra_hoy") or {}).get(hoy(), 0)
        return {"dia": aj["limite_dia"] + extra, "mes": aj["limite_mes"], "lote": aj["limite_lote"]}

    def subir_limite_hoy(self, euros):
        aj = self.ajustes(con_clave=True)
        aj["extra_hoy"] = {hoy(): round(max(0.0, float(str(euros).replace(",", "."))), 2)}
        self._escribir(aj)
        self.pausa = None
        return self.resumen()

    def _cabe(self, estimado, lote_id):
        """None si cabe; si no, el motivo de la pausa ('dia', 'mes') o 'lote'."""
        lim = self.limites()
        dia, _ = self.gasto(hoy())
        mes, _ = self.gasto(hoy()[:8] + "01")
        lote, _ = self.gasto(lote_id=lote_id)
        if mes + estimado > lim["mes"]:
            return "mes"
        if dia + estimado > lim["dia"]:
            return "dia"
        if lote + estimado > lim["lote"]:
            return "lote"
        return None

    def _estimar(self, sistema, mensaje, max_tokens):
        """Gasto previsto de una consulta: la entrada y una respuesta habitual (no el máximo permitido)."""
        aj = self.ajustes()
        p = aj["precios"].get(aj["modelo"], PRECIOS[aj["modelo"]])
        tokens = (len(sistema) + len(mensaje)) / 3.0
        return (tokens * p["entrada"] + min(max_tokens, 800) * p["salida"]) / 1e6 * aj["cambio"]

    # ------------------------------------------------------------------ estado para las pantallas
    def resumen(self):
        aj = self.ajustes()
        dia, n_dia = self.gasto(hoy())
        mes, n_mes = self.gasto(hoy()[:8] + "01")
        lim = self.limites()
        if not aj["activo"]:
            estado = "apagado"
        elif self.pausa and self.pausa.get("fecha") == hoy() and self.pausa["motivo"] in ("dia", "mes"):
            estado = "pausa"
        elif aj["pausar"] and (dia >= lim["dia"] or mes >= lim["mes"]):
            estado, self.pausa = "pausa", {"motivo": "dia" if dia >= lim["dia"] else "mes", "fecha": hoy()}
        elif self.error and self.error.get("tipo") == "red":
            estado = "sin_conexion"
        elif self.trabajando:
            estado = "trabajando"
        else:
            estado = "activo"
        # 3.0.3: lo «para ti» de documentos que ya has resuelto tú no cuenta
        por_revisar = self.db.execute("SELECT COUNT(*) FROM ia_acciones WHERE estado IN ('por_revisar', 'para_ti') AND revisada = 0 AND NOT (estado = 'para_ti' AND documento_id IS NOT NULL AND documento_id NOT IN (SELECT id FROM documentos WHERE estado IN ('espera_emparejar', 'parado'))) AND (documento_id IS NULL OR documento_id NOT IN (SELECT id FROM documentos WHERE estado IN ('unido', 'separado', 'sustituido', 'deshecho')))").fetchone()[0]
        return {"activo": aj["activo"], "estado": estado, "modelo": aj["modelo"], "hoy": round(dia, 4), "mes": round(mes, 4),
                "consultas_hoy": n_dia, "consultas_mes": n_mes, "limites": lim, "pausa": self.pausa if estado == "pausa" else None,
                "error": (self.error or {}).get("texto"), "por_revisar": por_revisar, "tiene_clave": aj["tiene_clave"],
                "trabajando": self.trabajando, "tarifas": aj.get("tarifas")}

    def pantalla(self):
        """Todo lo de Ajustes › Controlador IA."""
        aj = self.ajustes()
        r = self.resumen()
        _, n_mes = self.gasto(hoy()[:8] + "01")
        ej = self.db.execute("SELECT COUNT(*) FROM ia_ejemplos").fetchone()[0]
        ultima = self.db.execute("SELECT id FROM ia_consultas WHERE error IS NULL ORDER BY id DESC LIMIT 1").fetchone()
        return {"ajustes": aj, "resumen": r, "modelos": MODELOS, "funciones": FUNCIONES, "comparativa": COMPARATIVA,
                "media": round(r["mes"] / n_mes, 5) if n_mes else 0, "ejemplos": ej, "ultima_consulta": ultima[0] if ultima else None,
                "consola": URL_CONSOLA, "instrucciones_serie": INSTRUCCIONES_SERIE,
                "fichas": [["Nombres y apellidos", "[PERSONA_1]"], ["DNI, NIE y NIF", "[DNI_1] [NIF_1]"], ["Expedientes", "[EXP_A]"],
                           ["IBAN y cuentas", "[IBAN_1] [CUENTA_1]"], ["Direcciones", "[DIRECCION_1]"], ["Teléfonos y correos", "[TEL_1] [EMAIL_1]"],
                           ["Matrículas", "[MATRICULA_1]"], ["Fechas de nacimiento", "[FNAC_1]"], ["Códigos de verificación y Seguridad Social", "[CSV_1] [NAF_1]"],
                           ["Otras personas que salgan", "[NOMBRE_1]"]]}

    # ------------------------------------------------------------------ tarifas (máximo una vez al día)
    def _descargar(self, url, cabeceras=None):
        req = urllib.request.Request(url, headers={"User-Agent": "SeFinancia (comprobar tarifas)", **(cabeceras or {})})
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.read().decode("utf-8", "replace")

    def comprobar_tarifas(self, forzar=False):
        aj = self.ajustes(con_clave=True)
        t = aj.get("tarifas") or {}
        if not forzar and t.get("ultima") and t["ultima"][:10] == hoy():
            return t            # como máximo una comprobación al día (encender y apagar no la repite)
        nuevo = {"ultima": ahora(), "estado": "sin_cambios", "detalle": "", "cambios": {}, "leidos": {}}
        try:
            leidos = leer_precios(self.descargar(URL_PRECIOS))
            nuevo["leidos"] = leidos
            for mid, p in leidos.items():
                mio = aj["precios"].get(mid, {})
                dif = {c: [mio.get(c), v] for c, v in p.items() if mio.get(c) is None or abs(float(mio.get(c)) - v) > 1e-9}
                if dif:
                    nuevo["cambios"][mid] = dif
            if nuevo["cambios"]:
                nuevo["estado"] = "cambios"
                nuevo["detalle"] = "Han cambiado las tarifas: " + "; ".join(
                    f"{MODELOS[m]['nombre']}: " + ", ".join(f"{c} {v[0]} → {v[1]} $" for c, v in d.items()) for m, d in nuevo["cambios"].items())
                with self.cerrojo:
                    self.a.evento("Controlador IA: " + nuevo["detalle"] + ". Revisa la tabla de tarifas en Ajustes › Controlador IA.", nivel="se")
        except Exception as e:
            nuevo.update(estado="no_comprobado", detalle=f"No se ha podido comprobar: {e}")
        clave = desproteger(aj["clave"]) if aj.get("clave") else ""
        if clave:
            try:
                lista = json.loads(self.descargar(URL_MODELOS + "?limit=100", {"x-api-key": clave, "anthropic-version": VERSION_API}))
                ids = {x.get("id"): x for x in lista.get("data", [])}
                if aj["modelo"] not in ids:
                    nuevo["detalle"] += (" · " if nuevo["detalle"] else "") + f"El modelo elegido ({MODELOS[aj['modelo']]['nombre']}) ya no aparece en la lista de Anthropic: elige otro."
                    nuevo["estado"] = "cambios" if nuevo["estado"] != "no_comprobado" else nuevo["estado"]
            except Exception:
                pass
        aj["tarifas"] = nuevo
        self._escribir(aj)
        return nuevo

    def actualizar_tarifas(self):
        aj = self.ajustes(con_clave=True)
        leidos = (aj.get("tarifas") or {}).get("leidos") or {}
        if not leidos:
            raise ErrorIA("No hay tarifas nuevas leídas: pulsa «Comprobar ahora».")
        for mid, p in leidos.items():
            aj["precios"].setdefault(mid, dict(PRECIOS.get(mid, {}))).update(p)
        aj["tarifas"].update(estado="sin_cambios", cambios={}, detalle="Tabla actualizada con las tarifas oficiales.")
        self._escribir(aj)
        return self.pantalla()

    # ------------------------------------------------------------------ el manual que acompaña a cada consulta
    def manual(self):
        aj = self.ajustes()
        v = self.m.variante
        tipos = []
        for d in v.base["documentos"]:
            f = self.m.clave_fecha(d["id"])
            tipos.append(f"- {d['id']}: {d['nombres']['es'][0]} ({d.get('familia') or '-'})" + (f" · fecha que da nombre: {f}" if f else ""))
        ejemplos = [dict(r) for r in self.db.execute("SELECT contexto, correcto FROM ia_ejemplos ORDER BY id DESC LIMIT 12")]
        partes = [
            "Eres el Controlador IA de SeFinancia, un programa que ordena la documentación de expedientes de préstamos "
            "(hipotecas, pymes, licencias de taxi) en una gestoría de España. El programa ya ha leído el documento en el equipo "
            "y te consulta solo lo que no ha sabido resolver.",
            "PRIVACIDAD: todos los datos personales vienen cambiados por fichas entre corchetes ([PERSONA_1], [DNI_1], [EXP_A], "
            "[NIF_1], [IBAN_1], [DIRECCION_1], [TEL_1], [NOMBRE_1]…). Responde siempre con las mismas fichas. No intentes adivinar los datos reales.",
            "REGLAS DE TRABAJO:\n"
            "1. Nunca crees expedientes ni personas nuevas. Si el documento es de alguien que no está en ningún expediente de la lista, responde expediente \"NUEVO\".\n"
            "2. Solo puedes asignar a una persona que ya esté en ese expediente. Si el documento es de todo el expediente (escritura, tasación, nota simple de la vivienda…), usa \"comun\": true.\n"
            "3. Las pistas de parecido las calcula el programa comparando los datos reales: fíate de ellas. «Nombre compuesto incompleto», «falta un apellido» o "
            "«8 de 8 cifras, falta la letra» suelen ser la misma persona; dilo en \"misma_persona\".\n"
            "4. Personas que no se fichan (notario, vendedores, representantes del banco, empleados que firman): ponlas en \"terceros\".\n"
            "5. Páginas: si hay varias, decide si son un solo documento o varios (\"separar\": grupos de números de página) y su orden (\"orden\"). "
            "Une el final de una página con el principio de la siguiente aunque no haya número de página; los pies de página y los códigos de verificación iguales indican el mismo documento.\n"
            "6. La fecha (\"fecha\", AAAA-MM-DD) es la que da nombre al documento según su tipo: periodo (el mes: usa el día 1), emisión o caducidad.\n"
            "7. Si no se puede saber de quién es y no es de ningún cliente, \"expediente\": \"LIMBO\". Si dudas, baja la seguridad en vez de inventar.\n"
            "8. \"seguridad\" de 0 a 100: lo segura que estás de TODO lo que propones. \"motivo\": una o dos frases en español, para el gestor.",
            "TIPOS DE DOCUMENTO (usa el id):\n" + "\n".join(tipos),
        ]
        if (aj.get("instrucciones") or "").strip():
            partes.append("INSTRUCCIONES DEL GESTOR (mandan sobre las anteriores si chocan):\n" + aj["instrucciones"].strip())
        if ejemplos:
            partes.append("CORRECCIONES ANTERIORES DEL GESTOR (casos anónimos):\n" + "\n".join(f"- Caso: {e['contexto']}\n  Correcto: {e['correcto']}" for e in ejemplos))
        partes.append('RESPUESTA: solo un objeto JSON, sin texto alrededor, con estas claves:\n'
                      '{"tipo": "id o null", "fecha": "AAAA-MM-DD o null", "persona": "[PERSONA_n] o null", "comun": false, '
                      '"expediente": "[EXP_x] | NUEVO | LIMBO | null", "misma_persona": [{"es": "[PERSONA_n]", "igual_a": "[PERSONA_m]"}], '
                      '"terceros": ["[PERSONA_n]"], "separar": [[1,2],[3]] o null, "orden": [2,1,3] o null, "seguridad": 0, "motivo": "…"}')
        return "\n\n".join(partes)

    # ------------------------------------------------------------------ preparar la consulta de un documento
    def _candidatos(self, mas):
        """Expedientes abiertos con sus personas (como fichas). Devuelve (texto, personas_para_tapar, mapas)."""
        a = self.a
        lineas, personas, exps, pers = [], [], {}, {}
        for e in a.db.execute("SELECT * FROM expedientes WHERE estado = 'abierto' ORDER BY id DESC LIMIT 40"):
            e = dict(e)
            fe = mas.ficha("EXP", e["nombre"], f"exp{e['id']}")
            exps[fe] = e["id"]
            gente = []
            for p in a.personas_de(e["id"]):
                fp = mas.ficha("PERSONA", f"{p['nombre']} {p['apellido1']} {p['apellido2'] or ''}".strip(), f"p{p['id']}")
                pers[fp] = p["id"]
                personas.append({**p, "ficha": fp})
                tipos = sorted({r[0] for r in a.db.execute("SELECT tipo FROM documentos WHERE expediente_id = ? AND persona_id = ? AND estado = 'guardado'", (e["id"], p["id"])) if r[0]})
                gente.append(f"{fp} ({p['papel']}{'; ya tiene: ' + ', '.join(tipos[:12]) if tipos else ''})")
            fin = self.m.variante.meta.get("finalidades", {}).get(e["finalidad"], e["finalidad"])
            lineas.append(f"- {fe} · {fin} · personas: " + ("; ".join(gente) or "ninguna"))
        return "\n".join(lineas) or "(no hay expedientes abiertos)", personas, exps, pers

    def _pistas(self, leidas, personas, texto_doc, datos, mas):
        out = []
        for l in leidas:
            for p in personas:
                r = pista_nombre(l, p)
                if r and r[0] >= 60:
                    out.append(f"{l['ficha']} ≈ {p['ficha']}: {r[0]} % · {r[1]}")
                if l.get("dni") and p.get("dni"):
                    d = pista_dni(l["dni"], p["dni"])
                    if d:
                        out.append(f"DNI de {l['ficha']} ≈ DNI de {p['ficha']}: {d}")
        for f, dni in list(mas.mapa.items()):          # cada DNI tapado del texto, comparado con los fichados
            if not f.startswith("[DNI_"):
                continue
            for p in personas:
                d = pista_dni(dni, p.get("dni"))
                if d:
                    out.append(f"{f} ≈ DNI de {p['ficha']}: {d}")
        # el mismo NIF (empresa) en documentos ya guardados de una persona
        for cif in datos.get("cif") or []:
            f = mas.buscar("NIF", cif)
            if not f:
                continue
            for r in self.a.db.execute("SELECT DISTINCT persona_id FROM documentos WHERE estado = 'guardado' AND datos LIKE ?", (f'%"{cif}"%',)):
                fp = next((p["ficha"] for p in personas if p["id"] == r[0]), None)
                if fp:
                    out.append(f"{f} aparece también en documentos ya guardados de {fp}")
        return sorted(set(out))

    @staticmethod
    def _recortar(t, maximo=1800):
        if len(t) <= maximo:
            return t
        lineas = t.splitlines()
        cab, pie = lineas[:18], lineas[-10:]
        return "\n".join(cab) + f"\n[… {max(0, len(lineas) - 28)} líneas sin enviar …]\n" + "\n".join(pie)

    def palabras_conocidas(self, lote_id=None):
        """Todas las palabras de nombres que el programa conoce: fichas de personas (con sus alias) y
        nombres leídos en los documentos del lote. Se tapan aunque aparezcan sueltas, y si alguna sigue a la vista no se envía nada."""
        ws = set()
        for r in self.a.db.execute("SELECT nombre, apellido1, apellido2, alias FROM personas"):
            ws |= set(norm(" ".join(x or "" for x in r[:3])).split())
            for al in json.loads(r[3] or "[]"):
                ws |= set(norm(al).split())
        q = "SELECT datos FROM documentos" + (" WHERE lote_id = ?" if lote_id else "")
        for r in self.a.db.execute(q, (lote_id,) if lote_id else ()):
            try:
                for p in (json.loads(r[0] or "{}").get("personas") or []):
                    ws |= set(norm(p.get("completo") or "").split())
            except ValueError:
                pass
        return {w for w in ws if len(w) >= 4 and w.isalpha()}

    def preparar(self, doc_id):
        a, m = self.a, self.m
        d = a.documento(doc_id)
        palabras = self.palabras_conocidas(d["lote_id"])
        mas = Mascara()
        cand, personas, exps, pers = self._candidatos(mas)
        datos = d["datos"] or {}
        leidas = []
        for i, p in enumerate(datos.get("personas") or []):
            clave = set(norm(p.get("completo") or "").split())
            ya = next((x for x in personas if x.get("dni") and p.get("dni") and x["dni"].upper() == p["dni"].upper()), None) or \
                next((x for x in personas if not (x.get("dni") and p.get("dni")) and clave and (set(norm(f'{x["nombre"]} {x["apellido1"]} {x["apellido2"] or ""}').split()) == clave
                      or norm(p.get("completo") or "").strip() in json.loads(x.get("alias") or "[]"))), None)
            f = ya["ficha"] if ya else mas.ficha("PERSONA", p.get("completo") or "", "l" + norm(p.get("completo") or str(i)))
            leidas.append({**p, "ficha": f, "fichada": ya["id"] if ya else None, "leida": True})
        sel = d.get("paginas_sel") or list(range(1, (d["paginas"] or 1) + 1))
        textos = []
        for n in sel:
            c = a.texto_cache(f'{d["huella"]}:{n}')
            textos.append(c["texto"] if c else "")
        if not any(textos):
            textos = [x["texto"] for x in a.textos_de(doc_id).values()]
        tapar = leidas + personas
        paginas = [f"--- página {i} ---\n" + self._recortar(mas.tapar(t, tapar, palabras)) for i, t in enumerate(textos, 1)]
        terceros = [mas.buscar("PERSONA", "l" + nm) for nm in m.terceros_lote(d["lote_id"])]
        pistas = self._pistas(leidas, personas, "\n".join(textos), datos, mas)
        def _alt(x):
            if isinstance(x, dict):
                return f"{x.get('tipo')}" + (f" {round(float(x['confianza']) * 100)} %" if isinstance(x.get("confianza"), (int, float)) else "")
            if isinstance(x, (list, tuple)) and x:
                return f"{x[0]}" + (f" {round(float(x[1]) * 100)} %" if len(x) > 1 and isinstance(x[1], (int, float)) else "")
            return str(x)
        alt = ", ".join(_alt(x) for x in (d["alternativas"] or [])[:3])
        partes = [
            f"DOCUMENTO D{doc_id} · {len(textos)} página(s) · llegó como {Path(d['nombre_recibido']).suffix or 'archivo'}",
            f"Clasificación del programa: {d['tipo'] or 'no reconocido'} ({round((d['confianza'] or 0) * 100)} %)" + (f" · otras: {alt}" if alt else ""),
            "Personas que nombra el documento: " + (", ".join(l["ficha"] + (" (ya fichada)" if l["fichada"] else "") for l in leidas) or "ninguna reconocida"),
            "Fechas leídas: " + (", ".join(datos.get("fechas") or []) or "ninguna") + (f" · periodo {datos['periodo']}" if datos.get("periodo") else "") +
            (f" · ejercicio {datos['ejercicio']}" if datos.get("ejercicio") else "") + (f" · caducidad {datos['caducidad']}" if datos.get("caducidad") else ""),
        ]
        if [t for t in terceros if t]:
            partes.append("Ya marcados como terceros en este lote: " + ", ".join(t for t in terceros if t))
        partes.append("PISTAS DE PARECIDO (calculadas en el equipo):\n" + ("\n".join(pistas) or "ninguna"))
        partes.append("EXPEDIENTES ABIERTOS QUE PUEDES USAR:\n" + cand)
        partes.append("TEXTO DEL DOCUMENTO:\n" + "\n".join(paginas))
        mensaje = "\n\n".join(partes)
        return {"mensaje": mensaje, "mascara": mas, "exps": exps, "pers": pers, "leidas": leidas, "paginas": sel, "doc": d, "palabras": palabras}

    def preparar_union(self, ids):
        mas = Mascara()
        palabras = self.palabras_conocidas(self.a.documento(ids[0])["lote_id"])
        _, personas, _, _ = self._candidatos(mas)
        partes = ["TAREA: estas fotos o páginas sueltas llegaron juntas y parecen del mismo tipo. Di cuáles forman un mismo documento y en qué orden. "
                  'Responde solo JSON: {"grupos": [["D1","D3"],["D2"]], "seguridad": 0, "motivo": "…"} (cada D en un solo grupo; un grupo de uno = suelta).']
        for i in ids:
            d = self.a.documento(i)
            leidas = [{**p, "ficha": mas.ficha("PERSONA", p.get("completo") or "", "l" + norm(p.get("completo") or ""))} for p in (d["datos"] or {}).get("personas") or []]
            c = self.a.texto_cache(f'{d["huella"]}:{(d.get("paginas_sel") or [1])[0]}')
            t = mas.tapar(c["texto"] if c else "", [{**l, "leida": True} for l in leidas] + personas, palabras)
            ls = [x for x in t.splitlines() if x.strip()]
            partes.append(f"--- D{i} · tipo probable {d['tipo'] or '¿?'} ---\nprimeras líneas:\n" + "\n".join(ls[:8]) + "\núltimas líneas:\n" + "\n".join(ls[-6:]))
        return {"mensaje": "\n\n".join(partes), "mascara": mas, "palabras": palabras}

    def preparar_lote(self, doc_ids):
        """Una sola consulta para varios documentos del lote: la IA ve el conjunto y supervisa lo que ha
        decidido el contexto del lote (en local). Mismas fichas para todo el lote."""
        a = self.a
        mas = Mascara()
        cand, personas, exps, pers = self._candidatos(mas)
        lote_id = a.documento(doc_ids[0])["lote_id"]
        palabras = self.palabras_conocidas(lote_id)
        partes, preps = [], {}
        for did in doc_ids:
            d = a.documento(did)
            datos = d["datos"] or {}
            leidas = []
            for i, p in enumerate(datos.get("personas") or []):
                clave = set(norm(p.get("completo") or "").split())
                ya = next((x for x in personas if x.get("dni") and p.get("dni") and x["dni"].upper() == p["dni"].upper()), None) or \
                    next((x for x in personas if clave and (set(norm(f'{x["nombre"]} {x["apellido1"]} {x["apellido2"] or ""}').split()) == clave
                          or norm(p.get("completo") or "").strip() in json.loads(x.get("alias") or "[]"))), None)
                f = ya["ficha"] if ya else mas.ficha("PERSONA", p.get("completo") or "", "l" + norm(p.get("completo") or str(i)))
                leidas.append({**p, "ficha": f, "fichada": ya["id"] if ya else None, "leida": True})
            sel = d.get("paginas_sel") or list(range(1, (d["paginas"] or 1) + 1))
            textos = [x["texto"] for x in a.textos_de(did).values()] if d["estado"] == "guardado" else []
            if not textos:
                for n in sel:
                    c = a.texto_cache(f'{d["huella"]}:{n}')
                    textos.append(c["texto"] if c else "")
            if not any(textos):
                textos = [x["texto"] for x in a.textos_de(did).values()]
            cuerpo = "\n".join(f"(pág. {k}) " + self._recortar(mas.tapar(t, leidas + personas, palabras), 900) for k, t in enumerate(textos, 1))
            if d["estado"] == "guardado":
                pp = a.persona(d["persona_id"]) if d["persona_id"] else None
                fe = mas.buscar("EXP", f"exp{d['expediente_id']}")
                fp = mas.buscar("PERSONA", f"p{d['persona_id']}") if pp else None
                local = f"guardado por el programa en {fe or '?'}, " + ("de todo el expediente" if d["de_expediente"] else f"de {fp or '?'}")
            else:
                prop = datos.get("ia_propuesta") or {}
                fe = mas.buscar("EXP", f"exp{prop.get('expediente_id')}") if prop.get("expediente_id") else None
                fp = mas.buscar("PERSONA", f"p{prop.get('persona_id')}") if prop.get("persona_id") else None
                local = ("propuesto por el programa: " + (fe or "") + " " + ("todo el expediente" if prop.get("comun") else (fp or ""))) if fe else "sin decidir"
            pistas = self._pistas(leidas, personas, "", datos, mas)
            partes.append(f"=== D{did} · {len(textos)} pág. · tipo del programa: {d['tipo'] or 'no reconocido'} ({round((d['confianza'] or 0) * 100)} %) · {local}\n"
                          f"Personas: " + (", ".join(l["ficha"] for l in leidas) or "ninguna reconocida") + "\n"
                          + ("Pistas: " + "; ".join(pistas) + "\n" if pistas else "")
                          + f"Fechas: " + (", ".join((datos.get("fechas") or [])[:6]) or "ninguna") + "\n" + cuerpo)
            preps[did] = {"mascara": mas, "exps": exps, "pers": pers, "leidas": leidas, "paginas": sel, "doc": d, "palabras": palabras}
        mensaje = ("TAREA: estos documentos llegaron juntos (un lote). El programa ya ha decidido algunos con el contexto del lote. "
                   "Supervisa: confirma o corrige cada documento y decide los que quedan sin decidir.\n"
                   'Responde solo JSON: {"documentos": [{"doc": "D12", ...mismas claves que para un documento...}]}, un objeto por documento.\n\n'
                   "EXPEDIENTES ABIERTOS QUE PUEDES USAR:\n" + cand + "\n\n" + "\n\n".join(partes))
        return {"mensaje": mensaje, "mascara": mas, "palabras": palabras, "preps": preps}

    def _supervisar(self, preps, dec, cid, lote_id):
        """Aplica la respuesta de la IA a un documento del lote (supervisando lo que hizo el contexto local)."""
        did = preps["doc"]["id"]
        d = self.a.documento(did)
        if d["estado"] == "guardado":
            exp_ia = preps["exps"].get(dec.get("expediente"))
            per_ia = preps["pers"].get(dec.get("persona"))
            igual = exp_ia == d["expediente_id"] and (bool(dec.get("comun")) == bool(d["de_expediente"]) and (dec.get("comun") or per_ia == d["persona_id"]))
            if igual or not exp_ia and dec.get("expediente") in (None, ""):
                return []
            seg = int(dec.get("seguridad") or 0)
            if seg < self.ajustes()["umbral"]:
                return [self._accion(lote_id, did, cid, "para_ti", "La IA no está de acuerdo", f"Propone: {preps['mascara'].mapa.get(dec.get('expediente'), dec.get('expediente'))}",
                                     str(dec.get("motivo") or ""), seg, "para_ti", {})]
            for y in self.db.execute("SELECT id FROM ia_acciones WHERE documento_id = ? AND tipo = 'asignado' AND estado != 'deshecha'", (did,)).fetchall():
                self.deshacer(y[0], aprender=False)
            preps["doc"] = self.a.documento(did)
        return self.aplicar(preps, dec, cid)

    # ------------------------------------------------------------------ consultar (sin el cerrojo del motor)
    def _consultar(self, prep, lote_id, doc_id, clase, cerrojo, max_tokens=4000):
        fallos = vigilar(prep["mensaje"], prep.get("palabras") or ())
        if fallos:            # mejor no consultar que enviar un dato personal
            raise Bloqueado("No se ha enviado a la IA: quedaba " + " y ".join(fallos) + " sin tapar")
        with cerrojo:
            aj = self.ajustes(con_clave=True)
            sistema = self.manual()
            est = self._estimar(sistema, prep["mensaje"], max_tokens)
            motivo = self._cabe(est, lote_id)
            if motivo:
                if motivo in ("dia", "mes"):
                    self.pausa = {"motivo": motivo, "fecha": hoy()}
                    self.a.evento(f"Controlador IA en pausa: límite del {'día' if motivo == 'dia' else 'mes'} alcanzado. El programa sigue en local.", lote_id=lote_id, nivel="se")
                raise LimiteAlcanzado(motivo)
        t0 = time.time()
        try:
            texto, uso = self.cliente(desproteger(aj["clave"]), aj["modelo"], sistema, prep["mensaje"], max_tokens)
        except ErrorIA as e:
            self.error = {"texto": str(e), "tipo": "red" if "conexión" in str(e) else "api"}
            with cerrojo:
                self.db.execute("INSERT INTO ia_consultas(fecha, lote_id, documento_id, clase, modelo, enviado, error) VALUES(?, ?, ?, ?, ?, ?, ?)",
                                (ahora(), lote_id, doc_id, clase, aj["modelo"], prep["mensaje"], str(e)))
                self.db.commit()
            raise
        self.error = None
        usd = coste(aj["precios"], aj["modelo"], uso)
        with cerrojo:
            return self._guardar_consulta(aj, lote_id, doc_id, clase, uso, usd, t0, prep, texto)

    def _guardar_consulta(self, aj, lote_id, doc_id, clase, uso, usd, t0, prep, texto):
        c = self.db.execute("INSERT INTO ia_consultas(fecha, lote_id, documento_id, clase, modelo, t_entrada, t_salida, t_cache, t_escritura, coste_usd, segundos, enviado, respuesta, mapa) "
                            "VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                            (ahora(), lote_id, doc_id, clase, aj["modelo"], uso.get("input_tokens", 0), uso.get("output_tokens", 0),
                             uso.get("cache_read_input_tokens", 0), uso.get("cache_creation_input_tokens", 0), usd, round(time.time() - t0, 2),
                             prep["mensaje"], texto, json.dumps(prep["mascara"].mapa, ensure_ascii=False)))
        self.db.commit()
        return c.lastrowid, json_de(texto)

    # ------------------------------------------------------------------ aplicar (con el cerrojo del motor)
    def _accion(self, lote_id, doc_id, consulta_id, tipo, titulo, detalle, motivo, seguridad, estado, deshacer, origen="ia"):
        c = self.db.execute("INSERT INTO ia_acciones(fecha, lote_id, documento_id, consulta_id, tipo, titulo, detalle, motivo, seguridad, estado, deshacer, origen) "
                            "VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (ahora(), lote_id, doc_id, consulta_id, tipo, titulo, detalle, motivo,
                                                                        int(seguridad or 0), estado, json.dumps(deshacer or {}, ensure_ascii=False), origen))
        self.db.commit()
        return c.lastrowid

    def aplicar(self, prep, dec, consulta_id):
        """Hace lo que ha decidido la IA, dentro de lo permitido. Devuelve las acciones hechas."""
        a, m = self.a, self.m
        aj = self.ajustes()
        fn, umbral = aj["funciones"], aj["umbral"]
        d = a.documento(prep["doc"]["id"])
        did, lote = d["id"], d["lote_id"]
        if d["estado"] not in ("espera_emparejar", "parado"):
            return []
        seg = max(0, min(100, int(dec.get("seguridad") or 0)))
        motivo = str(dec.get("motivo") or "")[:600]
        est = "hecha" if seg >= umbral else "por_revisar"
        mapa = prep["mascara"].mapa
        real = lambda f: mapa.get(f, f)
        hechas = []
        # 1. separar en varios documentos
        sep = dec.get("separar")
        # 3.1.3 (Joan) · un «Cuadro contable» se guarda siempre como un único documento: no se separa
        if (dec.get("tipo") or d["tipo"]) == "cuadrocontable":
            sep = None
        if fn.get("separar") and isinstance(sep, list) and len(sep) >= 2:
            try:
                grupos = [[prep["paginas"][int(n) - 1] for n in g] for g in sep]
            except (ValueError, IndexError, TypeError):
                grupos = None
            if grupos and sorted(sum(grupos, [])) == sorted(prep["paginas"]):
                hijos = m.gestion.separar_manual(did, grupos)
                hechas.append(self._accion(lote, did, consulta_id, "separado", f"Separado en {len(grupos)} documentos",
                                           "Páginas " + " · ".join("+".join(map(str, g)) for g in sep), motivo, seg, est,
                                           {"hijos": hijos, "paginas_sel": d["paginas_sel"], "fase": d["fase"], "motivo": d["motivo"]}))
                a.evento(f"Controlador IA: separado en {len(grupos)} documentos · {motivo}", did, lote, 3)
                return hechas
        # 2. ordenar páginas
        orden = dec.get("orden")
        if fn.get("separar") and isinstance(orden, list) and len(orden) == len(prep["paginas"]) and len(orden) > 1:
            try:
                nuevo = [prep["paginas"][int(n) - 1] for n in orden]
            except (ValueError, IndexError, TypeError):
                nuevo = None
            if nuevo and sorted(nuevo) == sorted(prep["paginas"]) and nuevo != prep["paginas"]:
                rot = {r["n"]: r for r in d["rotaciones"] or []}
                a.actualizar(did, paginas_sel=nuevo, rotaciones=[rot.get(n, {"n": n}) for n in nuevo])
                hechas.append(self._accion(lote, did, consulta_id, "ordenado", "Páginas ordenadas", "Nuevo orden: " + ", ".join(map(str, orden)),
                                           motivo, seg, est, {"paginas_sel": d["paginas_sel"], "rotaciones": d["rotaciones"]}))
                d = a.documento(did)
        # 3. tipo
        tipo = dec.get("tipo") if dec.get("tipo") in m.variante.docs else None
        if tipo and fn.get("clasificar") and tipo != d["tipo"]:
            a.actualizar(did, tipo=tipo, confianza=max(d["confianza"] or 0, seg / 100), motivo=f"Tipo propuesto por la IA ({seg} %)")
            nombre_tipo = m.variante.etiqueta(tipo, d.get("modelo"))
            hechas.append(self._accion(lote, did, consulta_id, "clasificado", "Clasificado", f"{nombre_tipo} (antes: {d['tipo'] or 'no reconocido'})",
                                       motivo, seg, est, {"tipo": d["tipo"], "confianza": d["confianza"], "motivo": d["motivo"]}))
            d = a.documento(did)
        tipo = tipo or d["tipo"]
        # 4. terceros
        if fn.get("terceros"):
            for f in dec.get("terceros") or []:
                l = next((x for x in prep["leidas"] if x["ficha"] == f), None)
                if l and not l.get("fichada"):
                    nm = norm(l.get("completo") or "")
                    a.db.execute("INSERT OR IGNORE INTO terceros_lote VALUES(?, ?)", (lote, nm)); a.db.commit()
                    hechas.append(self._accion(lote, did, consulta_id, "tercero", "Tercero (no se ficha)", f"{l.get('completo')}", motivo, seg, est, {"nombre": nm}))
        # 5. misma persona (siempre como aviso para Joan)
        iguales = {}
        if fn.get("personas"):
            for par in dec.get("misma_persona") or []:
                es, igual = (par or {}).get("es"), (par or {}).get("igual_a")
                pid = prep["pers"].get(igual)
                l = next((x for x in prep["leidas"] if x["ficha"] == es), None)
                if pid and l and not l.get("fichada"):
                    p0 = a.persona(pid)
                    alias = json.loads(p0.get("alias") or "[]")
                    nm = norm(l.get("completo") or "").strip()
                    nuevo_alias = nm not in alias
                    if nuevo_alias:
                        alias.append(nm)
                        a.db.execute("UPDATE personas SET alias = ? WHERE id = ?", (json.dumps(alias, ensure_ascii=False), pid)); a.db.commit()
                    iguales[es] = pid
                    hechas.append(self._accion(lote, did, consulta_id, "misma_persona", "Misma persona",
                                               f"«{l.get('completo')}» es {p0['nombre']} {p0['apellido1']} {p0['apellido2'] or ''}".strip(),
                                               motivo, seg, "por_revisar", {"persona_id": pid, "alias": nm if nuevo_alias else None}))
                elif prep["pers"].get(es) and pid and prep["pers"][es] != pid:
                    hechas.append(self._accion(lote, did, consulta_id, "para_ti", "Posible ficha repetida",
                                               f"{real(es)} y {real(igual)} podrían ser la misma persona: únelas en Ajustes › Fichas repetidas si es así.", motivo, seg, "para_ti", {}))
        # 6. expediente
        exp = dec.get("expediente")
        if exp == "NUEVO":
            a.actualizar(did, motivo="IA: posible cliente nuevo · crea tú el expediente")
            hechas.append(self._accion(lote, did, consulta_id, "para_ti", "Posible cliente nuevo",
                                       "Parece de una persona sin expediente. La IA no crea expedientes: lo decides tú.", motivo, seg, "para_ti", {}))
            a.evento("Controlador IA: posible cliente nuevo; espera tu decisión. " + motivo, did, lote, 7, "revision")
            return hechas
        if exp == "LIMBO":
            if fn.get("limbo"):
                m.al_limbo(did)
                hechas.append(self._accion(lote, did, consulta_id, "limbo", "Al Limbo", "No es de ningún cliente", motivo, seg, est, {}))
            else:
                a.actualizar(did, motivo="IA: no parece de ningún cliente (¿Limbo?)")
                hechas.append(self._accion(lote, did, consulta_id, "para_ti", "¿Al Limbo?", "La IA cree que no es de ningún cliente.", motivo, seg, "para_ti", {}))
            return hechas
        eid = prep["exps"].get(exp)
        comun = bool(dec.get("comun"))
        pid = prep["pers"].get(dec.get("persona")) or iguales.get(dec.get("persona"))
        if not pid:
            l = next((x for x in prep["leidas"] if x["ficha"] == dec.get("persona")), None)
            pid = l.get("fichada") if l else None
        fecha = None
        if fn.get("fechas") and isinstance(dec.get("fecha"), str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", dec["fecha"]):
            try:
                datetime.date.fromisoformat(dec["fecha"]); fecha = dec["fecha"]
            except ValueError:
                pass
        if eid and fn.get("asignar") and tipo:
            en_exp = [p["id"] for p in a.personas_de(eid)]
            previsto = m.gestion.nombre_previsto(did, eid, None if comun else pid, tipo, fecha, False, comun) if (comun or pid in en_exp) else {}
            txt = ""
            if previsto.get("existe"):
                hechas.append(self._accion(lote, did, consulta_id, "para_ti", "Segunda aportación",
                                           f"Ya hay un {previsto['nombre']} en ese expediente: sustituir, añadir o descartar lo decides tú.", motivo, seg, "para_ti", {}))
            elif comun or (pid and pid in en_exp):
                antes = {"datos": d["datos"]}
                guardado = m.emparejar(did, eid, None if comun else pid, de_expediente=comun, fecha=fecha)
                e = a.expediente(eid)
                quien = "todo el expediente" if comun else " ".join(x for x in (a.persona(pid)["nombre"], a.persona(pid)["apellido1"]) if x)
                hechas.append(self._accion(lote, did, consulta_id, "asignado", "Asignado",
                                           f"{m.variante.docs[tipo]['nombres']['es'][0]} · {e['nombre']} · {quien} · {guardado['nombre_final']}",
                                           motivo, seg, est, antes))
                a.evento(f"Controlador IA: guardado en «{e['nombre']}» ({seg} %) · {motivo}", did, lote, 10)
                return hechas
            elif pid:
                txt = "Esa persona no está en el expediente: añadirla lo decides tú."
            else:
                txt = "No se sabe de qué persona del expediente es."
            if not previsto.get("existe"):
                hechas.append(self._accion(lote, did, consulta_id, "para_ti", "Falta decidir", f"Propuesta: {real(exp)}. {txt}", motivo, seg, "para_ti", {}))
        if hechas or motivo:
            d = a.documento(did)
            if d["estado"] in ("espera_emparejar", "parado"):
                datos = d["datos"] or {}
                datos["ia_propuesta"] = {"texto": motivo, "seguridad": seg, "expediente_id": eid, "persona_id": pid, "tipo": tipo, "fecha": fecha, "comun": comun}
                a.actualizar(did, datos=datos)
        return hechas

    # ------------------------------------------------------------------ lote completo
    def lotes_pendientes(self):
        """Lotes terminados en local (nada en proceso), con documentos esperando revisión, aún no pasados a la IA,
        y llegados después de encenderla."""
        aj = self.ajustes()
        desde = aj.get("activado_en") or "9999"
        out = []
        for r in self.db.execute("SELECT id, creado FROM lotes WHERE creado >= ? ORDER BY id", (desde,)):
            if self.db.execute("SELECT 1 FROM ia_lotes WHERE lote_id = ?", (r["id"],)).fetchone():
                continue
            docs = self.a.documentos("lote_id = ?", (r["id"],))
            if any(x["estado"] == "espera_emparejar" and not (x["datos"] or {}).get("contexto") for x in docs):
                continue          # primero el contexto del lote (en local); la IA lo supervisa después
            if docs and not any(x["estado"] == "en_proceso" for x in docs) and any(x["estado"] in ("espera_emparejar", "guardado") for x in docs):
                out.append(r["id"])
        return out

    def ejecutar_lote(self, lote_id, cerrojo):
        """Pasa a la IA lo pendiente de un lote. cerrojo: el del motor (se suelta mientras se espera a la API)."""
        if not self._cerrojo.acquire(blocking=False):
            raise ErrorIA("El Controlador IA ya está trabajando.")
        self.trabajando = True
        resumen = {"consultas": 0, "acciones": 0, "parado": None}
        try:
            with cerrojo:
                self.db.execute("INSERT OR REPLACE INTO ia_lotes(lote_id, estado, fecha) VALUES(?, 'trabajando', ?)", (lote_id, ahora())); self.db.commit()
            intentadas = set()          # cada grupo de fotos se consulta una sola vez
            for vuelta in range(3):
                with cerrojo:
                    ya = {r[0] for r in self.db.execute("SELECT documento_id FROM ia_consultas WHERE lote_id = ? AND documento_id IS NOT NULL", (lote_id,))}
                    locales = {r[0] for r in self.db.execute("SELECT documento_id FROM ia_acciones WHERE lote_id = ? AND origen = 'local' AND tipo = 'asignado' AND estado != 'deshecha'", (lote_id,))}
                    docs = [x["id"] for x in self.a.documentos("lote_id = ? AND estado IN ('espera_emparejar', 'guardado')", (lote_id,))
                            if x["id"] not in ya and not (x["datos"] or {}).get("ia_vista") and (x["estado"] == "espera_emparejar" or x["id"] in locales)]
                    fotos = [p for p in self.fotos_para_unir(lote_id) if tuple(p["documentos"]) not in intentadas] if self.ajustes()["funciones"].get("separar") else []
                    intentadas |= {tuple(p["documentos"]) for p in fotos}
                if not docs and not fotos:
                    break
                for grupo in fotos:
                    with cerrojo:
                        prep = self.preparar_union(grupo["documentos"])
                    try:
                        cid, dec = self._consultar(prep, lote_id, None, "union", cerrojo)
                    except LimiteAlcanzado:
                        raise
                    except ErrorIA as e:
                        if self.error:            # sin conexión, clave o créditos: se para el lote
                            raise
                        with cerrojo:             # las fotos se quedan sueltas; cada una se consulta después por separado
                            self._accion(lote_id, grupo["documentos"][0], None, "para_ti", "Fotos sin unir",
                                         f"{e}: las {len(grupo['documentos'])} fotos siguen sueltas y se miran una a una.", "", 0, "para_ti", {})
                        continue
                    resumen["consultas"] += 1
                    with cerrojo:
                        resumen["acciones"] += len(self._aplicar_union(grupo["documentos"], dec, cid, lote_id))
                        self.m.procesar(lote_id)
                with cerrojo:
                    docs = [x for x in docs if self.a.documento(x)["estado"] in ("espera_emparejar", "guardado")]
                for k in range(0, len(docs), 12):          # una consulta por cada 12 documentos del lote
                    trozo = docs[k:k + 12]
                    with cerrojo:
                        prep = self.preparar_lote(trozo)
                        bloq = []
                        while vigilar(prep["mensaje"], prep["palabras"]) and trozo:
                            # se busca qué documento tiene el dato que no se ha podido tapar y se aparta (queda para Joan)
                            malo = next((x for x in trozo if vigilar(self.preparar_lote([x])["mensaje"], prep["palabras"])), None)
                            if malo is None:
                                break
                            trozo = [x for x in trozo if x != malo]
                            bloq.append(malo)
                            self._accion(lote_id, malo, None, "para_ti", "No enviado a la IA",
                                         "Quedaba " + " y ".join(vigilar(self.preparar_lote([malo])["mensaje"], prep["palabras"])) + " sin tapar: por seguridad no se ha enviado.",
                                         "", 0, "para_ti", {})
                            self._marcar_vista(malo)
                            prep = self.preparar_lote(trozo) if trozo else None
                    if not trozo or not prep:
                        continue
                    try:
                        cid, dec = self._consultar(prep, lote_id, None, "lote", cerrojo, 4000 + 600 * len(trozo))
                    except LimiteAlcanzado:
                        raise
                    except ErrorIA as e:
                        if self.error:            # sin conexión, clave o créditos: se para el lote
                            raise
                        with cerrojo:
                            for did in trozo:
                                self._accion(lote_id, did, None, "para_ti", "Sin respuesta", f"{e}: queda para que lo decidas tú.", "", 0, "para_ti", {})
                                self._marcar_vista(did)
                        continue
                    resumen["consultas"] += 1
                    respuestas = {str(x.get("doc", "")).strip(): x for x in (dec.get("documentos") or []) if isinstance(x, dict)}
                    with cerrojo:
                        for did in trozo:
                            r = respuestas.get(f"D{did}")
                            self._marcar_vista(did)
                            if not r:
                                continue
                            try:
                                resumen["acciones"] += len(self._supervisar(prep["preps"][did], r, cid, lote_id))
                            except Exception as e:      # lo que no se puede aplicar se queda para Joan
                                self._accion(lote_id, did, cid, "para_ti", "No se ha podido aplicar", str(e), str(r.get("motivo") or ""), int(r.get("seguridad") or 0), "para_ti", {})
                        self.m.procesar(lote_id)
            estado = "hecho"
        except LimiteAlcanzado as e:
            resumen["parado"] = e.motivo
            estado = "limite_" + e.motivo
        except ErrorIA as e:
            resumen["parado"] = str(e)
            estado = "error"
        finally:
            self.trabajando = False
            self._cerrojo.release()
        with cerrojo:
            usd = self.db.execute("SELECT COALESCE(SUM(coste_usd), 0) FROM ia_consultas WHERE lote_id = ?", (lote_id,)).fetchone()[0]
            self.db.execute("UPDATE ia_lotes SET estado = ?, coste_usd = ?, nota = ? WHERE lote_id = ?", (estado, usd, json.dumps(resumen, ensure_ascii=False), lote_id)); self.db.commit()
            if resumen["consultas"]:
                self.a.evento(f"Controlador IA: lote {lote_id} · {resumen['consultas']} consulta(s), {resumen['acciones']} acción(es), {usd * self.ajustes()['cambio']:.3f} €"
                              + (f" · parado: {resumen['parado']}" if resumen["parado"] else ""), lote_id=lote_id, nivel="info")
        return resumen

    INDIVIDUALES = {"nomina", "nominaatr", "nominaxtr", "extracto", "prestamo", "saldo", "retenciones", "aeat", "segsocial", "vidalaboral", "renta",
                    "pension", "paro", "fraccionado", "iva", "ivaanual", "cuota", "cirbe", "sumasysaldos", "balance", "sociedades"}

    def fotos_para_unir(self, lote_id):
        """Solo fotos de verdad (imágenes de una página), nunca PDF; y nunca tipos que vienen de uno en uno (nóminas, extractos…)."""
        IMG = (".jpg", ".jpeg", ".png", ".tif", ".tiff", ".heic", ".webp", ".bmp")
        out = []
        for p in self.m.propuestas_union():
            if p["lote"] != lote_id or p["tipo"] in self.INDIVIDUALES:
                continue
            ids = [i for i in p["documentos"] if (self.a.documento(i)["extension"] or "").lower() in IMG]
            if len(ids) > 1:
                out.append({**p, "documentos": ids})
        return out

    def _marcar_vista(self, did):
        d = self.a.documento(did)
        if d:
            datos = d["datos"] or {}
            datos["ia_vista"] = True
            self.a.actualizar(did, datos=datos)

    def _aplicar_union(self, ids, dec, cid, lote_id):
        hechas = []
        seg = int(dec.get("seguridad") or 0)
        if seg < self.ajustes()["umbral"]:          # unir mal es peor que no unir: por debajo del umbral, nada
            self._accion(lote_id, ids[0], cid, "para_ti", "Fotos sin unir", f"La IA no está segura ({seg} %) de qué fotos van juntas: decídelo tú.",
                         str(dec.get("motivo") or ""), seg, "para_ti", {})
            return hechas
        est = "hecha"
        validos = {f"D{i}": i for i in ids}
        usados = set()
        for g in dec.get("grupos") or []:
            g = [validos[x] for x in g if x in validos and x not in usados]
            usados |= {f"D{i}" for i in g}
            if len(g) >= 2 and all(self.a.documento(i)["estado"] == "espera_emparejar" for i in g):
                nuevo = self.m.unir(g)
                hechas.append(self._accion(lote_id, nuevo, cid, "unido", f"Unidas {len(g)} fotos en un documento",
                                           " + ".join(self.a.documento(i)["nombre_recibido"] for i in g), str(dec.get("motivo") or ""), seg, est, {"fuentes": g}))
        return hechas

    # ------------------------------------------------------------------ deshacer
    def deshacer(self, accion_id, aprender=True):
        a, m = self.a, self.m
        r = self.db.execute("SELECT * FROM ia_acciones WHERE id = ?", (accion_id,)).fetchone()
        if not r:
            raise ErrorIA("No existe esa acción.")
        x = dict(r)
        if x["estado"] == "deshecha":
            return x
        u = json.loads(x["deshacer"] or "{}")
        did = x["documento_id"]
        d = a.documento(did) if did else None
        t = x["tipo"]
        # lo que depende de esta acción se deshace antes
        if t in ("clasificado", "misma_persona", "ordenado", "tercero") and d and d["estado"] in ("guardado", "limbo"):
            for y in self.db.execute("SELECT id FROM ia_acciones WHERE documento_id = ? AND tipo IN ('asignado', 'limbo') AND estado != 'deshecha'", (did,)).fetchall():
                self.deshacer(y[0], aprender=False)
            d = a.documento(did)
        if t == "asignado":
            if d["estado"] == "guardado":
                m.devolver_a_revision(did, "Deshecho lo que hizo la IA: vuelve a la revisión")
        elif t == "limbo":
            if d["estado"] == "limbo":
                m.sacar_del_limbo(did)
        elif t == "clasificado":
            a.actualizar(did, tipo=u.get("tipo"), confianza=u.get("confianza"), motivo="Deshecho el tipo que puso la IA")
        elif t == "ordenado":
            a.actualizar(did, paginas_sel=u.get("paginas_sel"), rotaciones=u.get("rotaciones"))
        elif t == "tercero":
            a.db.execute("DELETE FROM terceros_lote WHERE lote_id = ? AND nombre = ?", (x["lote_id"], u.get("nombre"))); a.db.commit()
        elif t == "misma_persona":
            if u.get("alias"):
                p0 = a.persona(u["persona_id"])
                alias = [z for z in json.loads(p0.get("alias") or "[]") if z != u["alias"]]
                a.db.execute("UPDATE personas SET alias = ? WHERE id = ?", (json.dumps(alias, ensure_ascii=False), p0["id"])); a.db.commit()
        elif t == "separado":
            for h in u.get("hijos") or []:
                for y in self.db.execute("SELECT id FROM ia_acciones WHERE documento_id = ? AND estado != 'deshecha'", (h,)).fetchall():
                    self.deshacer(y[0], aprender=False)
                hd = a.documento(h)
                if hd and hd["estado"] not in ("espera_emparejar", "parado", "deshecho"):
                    raise ErrorIA(f"Una parte ya se ha guardado a mano ({hd['nombre_final']}): deshazla antes desde el expediente.")
                a.actualizar(h, estado="deshecho", motivo="Separación de la IA deshecha")
            a.actualizar(did, estado="espera_emparejar", fase=7, paginas_sel=u.get("paginas_sel"), motivo="Deshecha la separación de la IA")
        elif t == "expediente_creado":
            eid = u.get("expediente_id")
            for y in self.db.execute("SELECT id FROM ia_acciones WHERE lote_id = ? AND tipo IN ('asignado', 'cotitular') AND estado != 'deshecha' AND id != ?",
                                     (x["lote_id"], accion_id)).fetchall():
                self.deshacer(y[0], aprender=False)
            if self.db.execute("SELECT COUNT(*) FROM documentos WHERE expediente_id = ? AND estado IN ('guardado', 'contacto')", (eid,)).fetchone()[0]:
                raise ErrorIA("El expediente ya tiene documentos guardados a mano: muévelos o elimínalo desde el expediente.")
            e = a.expediente(eid)
            pids = [r[0] for r in self.db.execute("SELECT persona_id FROM expediente_personas WHERE expediente_id = ?", (eid,))]
            self.db.execute("DELETE FROM expediente_personas WHERE expediente_id = ?", (eid,))
            self.db.execute("DELETE FROM expedientes WHERE id = ?", (eid,))
            for pid in pids:      # fichas creadas por el contexto y que no están en ningún otro sitio
                if pid == u.get("persona_creada") and not self.db.execute("SELECT 1 FROM expediente_personas WHERE persona_id = ?", (pid,)).fetchone() \
                        and not self.db.execute("SELECT 1 FROM documentos WHERE persona_id = ?", (pid,)).fetchone():
                    self.db.execute("DELETE FROM personas WHERE id = ?", (pid,))
            self.db.commit()
            if e:
                for base in (m.carpetas.documentos, m.carpetas.originales):
                    try:
                        (base / e["carpeta"]).rmdir()           # solo si ha quedado vacía
                    except OSError:
                        pass
            self.db.execute("UPDATE notificaciones SET visto = 1 WHERE expediente_id = ?", (eid,)) if self.db.execute(
                "SELECT name FROM sqlite_master WHERE name = 'notificaciones'").fetchone() else None
            self.db.commit()
        elif t == "cotitular":
            eid, pid = u.get("expediente_id"), u.get("persona_id")
            if self.db.execute("SELECT COUNT(*) FROM documentos WHERE expediente_id = ? AND persona_id = ? AND estado = 'guardado'", (eid, pid)).fetchone()[0]:
                for y in self.db.execute("SELECT a.id FROM ia_acciones a JOIN documentos d ON d.id = a.documento_id WHERE a.tipo = 'asignado' AND a.estado != 'deshecha' "
                                         "AND d.expediente_id = ? AND d.persona_id = ?", (eid, pid)).fetchall():
                    self.deshacer(y[0], aprender=False)
            if self.db.execute("SELECT COUNT(*) FROM documentos WHERE expediente_id = ? AND persona_id = ? AND estado = 'guardado'", (eid, pid)).fetchone()[0]:
                raise ErrorIA("Esa persona ya tiene documentos guardados a mano en el expediente.")
            self.db.execute("DELETE FROM expediente_personas WHERE expediente_id = ? AND persona_id = ?", (eid, pid)); self.db.commit()
        elif t == "unido":
            for y in self.db.execute("SELECT id FROM ia_acciones WHERE documento_id = ? AND estado != 'deshecha' AND id != ?", (did, accion_id)).fetchall():
                self.deshacer(y[0], aprender=False)
            d = a.documento(did)
            if d["estado"] not in ("espera_emparejar", "parado", "en_proceso"):
                raise ErrorIA("El documento unido ya se ha guardado a mano: deshazlo antes desde el expediente.")
            a.actualizar(did, estado="deshecho", motivo="Unión de la IA deshecha")
            Path(d["ruta_original"]).unlink(missing_ok=True)
            for f in u.get("fuentes") or []:
                a.actualizar(f, estado="espera_emparejar", unido_en=None, motivo="Deshecha la unión de la IA")
        self.db.execute("UPDATE ia_acciones SET estado = 'deshecha', revisada = 1 WHERE id = ?", (accion_id,)); self.db.commit()
        if did and a.documento(did) and a.documento(did)["estado"] in ("espera_emparejar", "parado"):
            datos = a.documento(did)["datos"] or {}
            if datos.pop("ia_propuesta", None) is not None:
                a.actualizar(did, datos=datos)
        a.evento(f"Deshecho lo que hizo la IA: {x['titulo']} · {x['detalle'] or ''}", did, x["lote_id"], nivel="info")
        if aprender and self.ajustes()["aprender"]:
            self._aprender(x)
        return dict(self.db.execute("SELECT * FROM ia_acciones WHERE id = ?", (accion_id,)).fetchone())

    def deshacer_lote(self, lote_id):
        ids = [r[0] for r in self.db.execute("SELECT id FROM ia_acciones WHERE lote_id = ? AND estado IN ('hecha', 'por_revisar') ORDER BY id DESC", (lote_id,))]
        hechos, fallos = 0, []
        for i in ids:
            try:
                if self.db.execute("SELECT estado FROM ia_acciones WHERE id = ?", (i,)).fetchone()[0] != "deshecha":
                    self.deshacer(i); hechos += 1
            except Exception as e:
                fallos.append(str(e))
        return {"deshechas": hechos, "fallos": fallos}

    def revisada(self, accion_id=None, lote_id=None):
        if accion_id:
            self.db.execute("UPDATE ia_acciones SET revisada = 1 WHERE id = ?", (accion_id,))
        elif lote_id:
            self.db.execute("UPDATE ia_acciones SET revisada = 1 WHERE lote_id = ?", (lote_id,))
        self.db.commit()

    # ------------------------------------------------------------------ aprendizaje (sin datos personales)
    def _aprender(self, accion):
        c = self.db.execute("SELECT enviado, respuesta FROM ia_consultas WHERE id = ?", (accion["consulta_id"],)).fetchone() if accion.get("consulta_id") else None
        if not c:
            return
        texto = c["enviado"] or ""
        cab = "\n".join(l for l in texto.splitlines()[:3])
        trozo = texto.split("TEXTO DEL DOCUMENTO:")[-1][:420]
        contexto = re.sub(r"\s+", " ", f"{cab} · {trozo}")[:600]
        detalle = re.sub(r"«[^»]*»", "«…»", accion.get("detalle") or "")
        correcto = f"La IA propuso «{accion['titulo']}» ({re.sub(r'[^·]*·', '', detalle)[:120]}) y el gestor lo deshizo: era incorrecto."
        self.db.execute("INSERT INTO ia_ejemplos(fecha, contexto, correcto) VALUES(?, ?, ?)", (ahora(), contexto, correcto)); self.db.commit()

    def aprender_correccion(self, doc_id):
        """Joan guarda a mano un documento en el que la IA se equivocó: se apunta cómo lo dejó (tipo), sin datos personales."""
        if not self.ajustes()["aprender"]:
            return
        r = self.db.execute("SELECT a.*, c.enviado FROM ia_acciones a JOIN ia_consultas c ON c.id = a.consulta_id WHERE a.documento_id = ? AND a.estado = 'deshecha' ORDER BY a.id DESC LIMIT 1", (doc_id,)).fetchone()
        d = self.a.documento(doc_id)
        if not r or not d or not d["tipo"]:
            return
        texto = r["enviado"] or ""
        contexto = re.sub(r"\s+", " ", "\n".join(texto.splitlines()[:2]) + " · " + texto.split("TEXTO DEL DOCUMENTO:")[-1][:400])[:600]
        self.db.execute("INSERT INTO ia_ejemplos(fecha, contexto, correcto) VALUES(?, ?, ?)",
                        (ahora(), contexto, f"tipo {d['tipo']}" + (" · de todo el expediente" if d["de_expediente"] else "")))
        self.db.commit()

    def exportar(self):
        ej = [dict(r) for r in self.db.execute("SELECT fecha, contexto, correcto FROM ia_ejemplos ORDER BY id")]
        ruta = self.m.carpetas.datos / f"aprendizaje_ia_{hoy()}.json"
        ruta.write_text(json.dumps({"programa": "Sentiende", "version": 1, "instrucciones": self.ajustes()["instrucciones"], "ejemplos": ej},
                                   ensure_ascii=False, indent=1), encoding="utf-8")
        return str(ruta)

    def importar(self, datos):
        ej = (datos or {}).get("ejemplos") or []
        n = 0
        for e in ej:
            if isinstance(e, dict) and e.get("contexto") and e.get("correcto"):
                self.db.execute("INSERT INTO ia_ejemplos(fecha, contexto, correcto) VALUES(?, ?, ?)", (e.get("fecha") or ahora(), str(e["contexto"])[:600], str(e["correcto"])[:300])); n += 1
        self.db.commit()
        return n

    def borrar_aprendizaje(self):
        self.db.execute("DELETE FROM ia_ejemplos"); self.db.commit()

    # ------------------------------------------------------------------ informe y consultas (pantallas)
    def informe(self, lote_id):
        acc = [dict(r) for r in self.db.execute("SELECT * FROM ia_acciones WHERE lote_id = ? ORDER BY id", (lote_id,))]
        for x in acc:
            d = self.a.documento(x["documento_id"]) if x["documento_id"] else None
            x["documento"] = {"id": d["id"], "archivo": d["nombre_recibido"], "estado": d["estado"], "expediente_id": d["expediente_id"],
                              "nombre_final": d["nombre_final"]} if d else None
            u = json.loads(x.pop("deshacer", None) or "{}")
            x["expediente_id"] = u.get("expediente_id")
        docs = [x for x in self.a.documentos("lote_id = ?", (lote_id,)) if x["estado"] not in ("separado", "unido", "deshecho")]
        por_ia = {x["documento_id"] for x in acc if x["tipo"] in ("asignado", "limbo") and x["estado"] != "deshecha"}
        l = self.db.execute("SELECT * FROM ia_lotes WHERE lote_id = ?", (lote_id,)).fetchone()
        usd = self.db.execute("SELECT COALESCE(SUM(coste_usd), 0) FROM ia_consultas WHERE lote_id = ?", (lote_id,)).fetchone()[0]
        consultas = [dict(r) for r in self.db.execute("SELECT id, documento_id, clase, modelo, coste_usd, error FROM ia_consultas WHERE lote_id = ? ORDER BY id", (lote_id,))]
        return {"lote": lote_id, "estado": dict(l) if l else None, "acciones": acc, "consultas": consultas,
                "cuentas": {"documentos": len(docs), "ia": len(por_ia),
                            "local": sum(1 for x in docs if x["estado"] in ("guardado", "limbo", "contacto") and x["id"] not in por_ia),
                            "para_ti": sum(1 for x in docs if x["estado"] in ("espera_emparejar", "parado"))},
                "coste": round(usd * self.ajustes()["cambio"], 4)}

    def lotes_con_informe(self):
        return [dict(r) for r in self.db.execute("SELECT l.*, (SELECT COUNT(*) FROM ia_acciones a WHERE a.lote_id = l.lote_id) AS acciones FROM ia_lotes l ORDER BY lote_id DESC LIMIT 30")]

    def consulta(self, cid):
        r = self.db.execute("SELECT * FROM ia_consultas WHERE id = ?", (cid,)).fetchone()
        if not r:
            raise ErrorIA("No existe esa consulta.")
        c = dict(r)
        c["mapa"] = json.loads(c["mapa"] or "{}")
        c["coste_eur"] = round((c["coste_usd"] or 0) * self.ajustes()["cambio"], 5)
        c["manual"] = {"reglas": True, "ejemplos": self.db.execute("SELECT COUNT(*) FROM ia_ejemplos").fetchone()[0]}
        return c

    def acciones_doc(self, doc_id):
        return [dict(r) for r in self.db.execute("SELECT id, tipo, titulo, detalle, motivo, seguridad, estado, revisada, lote_id, consulta_id, origen FROM ia_acciones WHERE documento_id = ? AND estado != 'deshecha' ORDER BY id", (doc_id,))]

    def por_revisar(self):
        return [dict(r) for r in self.db.execute("SELECT a.id, a.lote_id, a.documento_id, a.tipo, a.titulo, a.detalle, a.motivo, a.seguridad, a.estado, a.origen, "
                                                 "d.nombre_recibido AS archivo, d.nombre_final, d.estado AS estado_doc FROM ia_acciones a LEFT JOIN documentos d ON d.id = a.documento_id "
                                                 "WHERE a.estado IN ('por_revisar', 'para_ti') AND a.revisada = 0 AND NOT (a.estado = 'para_ti' AND a.documento_id IS NOT NULL AND a.documento_id NOT IN (SELECT id FROM documentos WHERE estado IN ('espera_emparejar', 'parado'))) AND (d.id IS NULL OR d.estado NOT IN ('unido', 'separado', 'sustituido', 'deshecho')) ORDER BY a.id DESC LIMIT 200")]


class Bloqueado(ErrorIA):
    """La comprobación final ha encontrado un dato personal: la consulta no sale del equipo."""


class LimiteAlcanzado(ErrorIA):
    def __init__(self, motivo):
        super().__init__({"dia": "límite del día alcanzado", "mes": "límite del mes alcanzado", "lote": "límite del lote alcanzado"}[motivo])
        self.motivo = motivo
