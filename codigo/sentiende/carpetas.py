# -*- coding: utf-8 -*-
"""Carpetas del programa (M-14, M-13). Por defecto, junto al ejecutable:
Entrada, Doc_original, SeDocumentos (con _Limbo), Papelera, Variantes y Datos (con Trabajo).
Cada una se puede cambiar; la configuración se guarda en Datos\\ajustes.json."""
import json
from pathlib import Path

NOMBRES = {"entrada": "Entrada", "originales": "Doc_original", "documentos": "SeDocumentos",
           "papelera": "Papelera", "variantes": "Variantes", "datos": "Datos",
           "firmados": "_Firmados"}          # 3.1.3 (Joan, 19/11): zip de cada expediente al cobrarlo
LIMBO = "_Limbo"

class Carpetas:
    def __init__(self, raiz):
        self.raiz = Path(raiz)
        self.datos = self.raiz / NOMBRES["datos"]
        self._ajustes = self.datos / "ajustes.json"
        self.rutas = {k: self.raiz / v for k, v in NOMBRES.items()}
        if self._ajustes.exists():
            guardadas = json.loads(self._ajustes.read_text(encoding="utf-8")).get("carpetas", {})
            self.rutas.update({k: Path(v) for k, v in guardadas.items() if k in NOMBRES})
            self.datos = self.rutas["datos"]

    def crear(self):
        """Primer arranque: crea lo que falte. Devuelve las que ha creado."""
        creadas = []
        for p in list(self.rutas.values()) + [self.limbo, self.originales_limbo, self.trabajo_raiz]:
            if not p.exists():
                p.mkdir(parents=True)
                creadas.append(p)
        return creadas

    def cambiar(self, clave, nueva):
        self.rutas[clave] = Path(nueva)
        self.datos.mkdir(parents=True, exist_ok=True)
        aj = json.loads(self._ajustes.read_text(encoding="utf-8")) if self._ajustes.exists() else {}
        aj.setdefault("carpetas", {})[clave] = str(nueva)
        self._ajustes.write_text(json.dumps(aj, ensure_ascii=False, indent=1), encoding="utf-8")

    def __getattr__(self, k):
        if k in NOMBRES:
            return self.rutas[k]
        raise AttributeError(k)

    @property
    def limbo(self):
        return self.rutas["documentos"] / LIMBO

    @property
    def originales_limbo(self):
        return self.rutas["originales"] / LIMBO

    @property
    def trabajo_raiz(self):
        return self.rutas["datos"] / "Trabajo"

    def trabajo(self, lote_id):
        p = self.trabajo_raiz / f"lote_{lote_id}"
        p.mkdir(parents=True, exist_ok=True)
        return p

def libre(ruta):
    """Si ya existe, devuelve nombre-2, nombre-3… (regla de duplicados)."""
    ruta = Path(ruta)
    if not ruta.exists():
        return ruta
    n = 2
    while True:
        c = ruta.with_name(f"{ruta.stem}-{n}{ruta.suffix}")
        if not c.exists():
            return c
        n += 1
