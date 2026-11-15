# -*- coding: utf-8 -*-
"""Fase 1 · Recibir (M-01, M-61). Mueve lo recibido a Entrada\\ (no copia), calcula la
huella y detecta duplicados exactos antes de gastar tiempo en leerlos.
Comprueba que el contenido coincide con la extensión: lo que no es un tipo permitido no entra."""
import hashlib, shutil
from pathlib import Path
from .carpetas import libre

PERMITIDOS = {".pdf": "pdf", ".jpg": "imagen", ".jpeg": "imagen", ".png": "imagen", ".tif": "imagen", ".tiff": "imagen",
              ".heic": "imagen", ".docx": "word", ".xlsx": "excel"}
FIRMAS = {"pdf": [b"%PDF"], "imagen": [b"\xff\xd8\xff", b"\x89PNG", b"II*\x00", b"MM\x00*", b"\x00\x00\x00"],
          "word": [b"PK\x03\x04"], "excel": [b"PK\x03\x04"]}

def huella(ruta, bloque=1 << 20):
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        while True:
            b = f.read(bloque)
            if not b:
                break
            h.update(b)
    return h.hexdigest()

def tipo_archivo(ruta):
    """Devuelve 'pdf', 'imagen', 'word', 'excel' o None si no se admite o no coincide."""
    ruta = Path(ruta)
    clase = PERMITIDOS.get(ruta.suffix.lower())
    if not clase:
        return None
    with open(ruta, "rb") as f:
        cab = f.read(12)
    if ruta.suffix.lower() == ".heic":
        return clase if b"ftyp" in cab else None
    return clase if any(cab.startswith(s) for s in FIRMAS[clase]) else None

def mover_a_entrada(ruta, entrada):
    """Si el archivo no está ya en Entrada\\, se mueve allí (decidido: mover, no copiar)."""
    ruta, entrada = Path(ruta), Path(entrada)
    if ruta.parent.resolve() == entrada.resolve():
        return ruta
    destino = libre(entrada / ruta.name)
    shutil.move(str(ruta), destino)
    return destino
