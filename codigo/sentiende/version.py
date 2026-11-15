# -*- coding: utf-8 -*-
"""Versiones y compatibilidad entre motor y variante (M-18, M-19, M-67).

Regla: mismo número mayor de contrato = compatible. Si la variante pide un motor
más nuevo que el instalado, hay que actualizar el motor; si el motor tiene un
contrato más nuevo que el que pide la variante, hay que actualizar la variante."""
from dataclasses import dataclass
import re

def parse(v):
    """'2.1.0' -> (2, 1, 0). Acepta '2', '2.1'."""
    m = re.fullmatch(r"\s*(\d+)(?:\.(\d+))?(?:\.(\d+))?\s*", str(v))
    if not m:
        raise ValueError(f"Versión no válida: {v!r}")
    return tuple(int(x or 0) for x in m.groups())

@dataclass
class Compatibilidad:
    compatible: bool
    actualizar: str | None      # None, "motor" o "variante"
    mensaje: str

def comprobar(motor_version, motor_contrato, variante):
    """variante: dict con 'nombre', 'version' y 'requiere_motor' {'contrato': 2, 'minimo': '2.0.0'}."""
    req = variante.get("requiere_motor") or {}
    nombre = f'{variante.get("nombre", "La variante")} {variante.get("version", "")}'.strip()
    contrato = int(req.get("contrato", -1))
    minimo = req.get("minimo", f"{contrato}.0.0")
    if contrato < 0:
        return Compatibilidad(False, "variante", f"{nombre} no indica qué motor necesita. Hace falta una versión nueva de la variante.")
    if contrato > motor_contrato:
        return Compatibilidad(False, "motor", f"{nombre} necesita el motor {contrato}.x y tienes el {motor_version}. Actualiza el motor.")
    if contrato < motor_contrato:
        return Compatibilidad(False, "variante", f"{nombre} está hecha para el motor {contrato}.x y tienes el {motor_version}. Actualiza la variante.")
    if parse(motor_version) < parse(minimo):
        return Compatibilidad(False, "motor", f"{nombre} necesita como mínimo el motor {minimo} y tienes el {motor_version}. Actualiza el motor.")
    return Compatibilidad(True, None, f"{nombre} es compatible con el motor {motor_version}.")
