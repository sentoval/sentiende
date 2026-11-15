# -*- coding: utf-8 -*-
"""Cargador de variantes (M-18). Una variante es una carpeta de configuración:
variante.json + base de conocimiento + nombres + checklists + imágenes. No lleva código."""
import json
from pathlib import Path
from . import VERSION, CONTRATO
from .version import comprobar

class VarianteError(Exception):
    pass

class Variante:
    OBLIGATORIOS = ("id", "nombre", "version", "requiere_motor", "archivos")

    def __init__(self, carpeta):
        self.carpeta = Path(carpeta)
        ruta = self.carpeta / "variante.json"
        if not ruta.exists():
            raise VarianteError(f"No se encuentra {ruta}. ¿Está bien instalada la variante?")
        self.meta = self._json(ruta)
        falta = [k for k in self.OBLIGATORIOS if k not in self.meta]
        if falta:
            raise VarianteError(f"variante.json incompleto: falta {', '.join(falta)}")
        self.compat = comprobar(VERSION, CONTRATO, self.meta)
        arch = self.meta["archivos"]
        self.base = self._json(self.carpeta / arch["base_conocimiento"])
        self.nombres = self._json(self.carpeta / arch["nombres"])
        self.checklists = self._json(self.carpeta / arch["checklists"])
        self.docs = {d["id"]: d for d in self.base["documentos"]}

    def _json(self, ruta):
        try:
            return json.loads(Path(ruta).read_text(encoding="utf-8"))
        except FileNotFoundError:
            raise VarianteError(f"Falta el archivo de la variante: {ruta}")
        except json.JSONDecodeError as e:
            raise VarianteError(f"El archivo {ruta} está mal escrito (línea {e.lineno}): {e.msg}")

    # atajos
    id = property(lambda s: s.meta["id"])
    nombre = property(lambda s: s.meta["nombre"])
    version = property(lambda s: s.meta["version"])
    umbral_revisar = property(lambda s: s.meta.get("umbrales", {}).get("revisar", 0.75))
    umbral_no_reconocido = property(lambda s: s.meta.get("umbrales", {}).get("no_reconocido", 0.40))
