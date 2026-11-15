# -*- coding: utf-8 -*-
"""Fase 6 · Clasificar (M-06, M-50). Puntúa las palabras clave, nombres (en los cuatro idiomas)
y sinónimos de cada tipo de la base de conocimiento de la variante. Detecta subtipos.
Identifica la entidad en este orden: IBAN, CIF/BIC del pie legal, nombre en el texto
(el logo por imagen llegará en otra fase). La web o el correo nunca deciden solos.
El resultado es provisional hasta emparejar (fase 7)."""
import re
from dataclasses import dataclass, field
from .extraer import norm

@dataclass
class Clasificacion:
    tipo: str | None
    confianza: float
    estado: str                       # 'ok', 'revisar' o 'no_reconocido'
    indicios: list = field(default_factory=list)
    alternativas: list = field(default_factory=list)
    entidad: str | None = None
    entidad_por: str = ""

def _contiene(t, frase):
    f = norm(frase)
    return len(f) > 3 and re.search(r"(?<![A-Z0-9])" + re.escape(f) + r"(?![A-Z0-9])", t) is not None

class Clasificador:
    def __init__(self, variante):
        self.v = variante
        self.docs = variante.base["documentos"]
        self.bancos = variante.base["entidades_financieras"]
        self.admin = variante.base.get("administraciones", [])

    def puntuar(self, t):
        res = []
        for doc in self.docs:
            if doc.get("subtipo_de"):
                continue
            fuertes = [k for k in doc["palabras_clave"] if _contiene(t, k)]
            nombres = {n for lang in doc["nombres"].values() for n in lang if _contiene(t, n)}
            sin = [n for n in doc["sinonimos"] if _contiene(t, n)]
            p = 3 * len(fuertes) + 2 * len(nombres) + len(sin)
            if p:
                res.append((p, doc["id"], fuertes[:4] + sorted(nombres)[:2] + sin[:1]))
        res.sort(key=lambda r: -r[0])
        return res

    def clasificar(self, texto):
        t = norm(texto)
        res = self.puntuar(t)
        if not res:
            return Clasificacion(None, 0.0, "no_reconocido")
        p1, ganador, por = res[0]
        p2 = res[1][0] if len(res) > 1 else 0
        # Confianza: lo que se separa del segundo y lo fuerte que es la evidencia (6 puntos = clara).
        separacion = (p1 - p2) / p1
        fuerza = min(1.0, p1 / 6)
        conf = round(0.5 * fuerza + 0.5 * fuerza * (0.4 + 0.6 * separacion), 2)
        for sub in self.docs:
            if sub.get("subtipo_de") == ganador and any(_contiene(t, r) for r in sub.get("requiere", [])):
                por = por + [f"subtipo por «{next(r for r in sub['requiere'] if _contiene(t, r))}»"]
                ganador = sub["id"]
                break
        estado = "ok" if conf >= self.v.umbral_revisar else ("revisar" if conf >= self.v.umbral_no_reconocido else "no_reconocido")
        ent, ent_por = self.entidad(t, ganador)
        alts = [{"tipo": r[1], "puntos": r[0]} for r in res[1:4]]
        return Clasificacion(ganador, conf, estado, por, alts, ent, ent_por)

    def entidad(self, t, tipo=None):
        if tipo:
            em = next((d.get("emisores", []) for d in self.docs if d["id"] == tipo), [])
            if em and not {"banco", "financiera", "sgr"} & set(em):
                for a in self.admin:
                    for lang in a["nombres"].values():
                        for n in lang:
                            if len(n) > 8 and _contiene(t, n):
                                return a["id"], f"organismo en el texto ({n})"
                return None, ""
        m = re.search(r"\bES\d{2}(?:[ -]?\d{4}){5}\b", t)
        if m:
            cod = re.sub(r"[ -]", "", m.group(0))[4:8]
            for b in self.bancos:
                if cod in b["codigos_entidad"]:
                    return b["nombre"], f"IBAN (código {cod})"
        plano = t.replace("-", "")
        for b in self.bancos:
            if b.get("cif") and b["cif"] in plano:
                return b["nombre"], "CIF de la entidad"
            if b.get("bic") and b["bic"] in t:
                return b["nombre"], "BIC"
        for b in self.bancos:
            for n in [b.get("nombre_legal"), b["nombre"]] + b.get("alias", []):
                if n and len(n) > 4 and _contiene(t, n):
                    return b["nombre"], f"nombre en el texto ({n})"
        return None, ""

    def abrev5(self, entidad):
        b = next((x for x in self.bancos if x["nombre"] == entidad), None)
        if b and b.get("abrev5"):
            return b["abrev5"]
        return re.sub(r"[^A-Z]", "", norm(entidad or ""))[:5] or None
