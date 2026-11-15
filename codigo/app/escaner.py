# -*- coding: utf-8 -*-
"""Escanear directamente (Windows). Usa WIA, el sistema de escáneres de Windows: abre el cuadro de
escaneo de Windows y guarda la imagen en la carpeta indicada. Sin programas añadidos."""
import datetime, os, subprocess, sys
from pathlib import Path

SCRIPT = r"""
$ErrorActionPreference = 'Stop'
$dlg = New-Object -ComObject WIA.CommonDialog
$img = $dlg.ShowAcquireImage(1, 0, 0, '{B96B3CAE-0728-11D3-9D7B-0000F81EF32E}', $false, $true, $false)
if ($img -eq $null) { exit 3 }
$img.SaveFile('{RUTA}')
"""


def escanear(carpeta):
    """Devuelve la ruta del archivo escaneado, o None si se canceló."""
    if sys.platform != "win32":
        raise RuntimeError("Escanear directamente solo funciona en Windows.")
    destino = Path(carpeta) / f"escaneo_{datetime.datetime.now():%Y%m%d_%H%M%S}.jpg"
    ps = SCRIPT.replace("{RUTA}", str(destino).replace("'", "''"))
    r = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
                       capture_output=True, text=True, creationflags=0x08000000)       # sin ventana negra
    if r.returncode == 3 or not destino.exists():
        if r.returncode not in (0, 3) and r.stderr:
            msg = r.stderr.strip().splitlines()[-1] if r.stderr.strip() else ""
            if "0x80210015" in r.stderr or "WIA" in r.stderr:
                raise RuntimeError("No se encuentra ningún escáner conectado (WIA). Comprueba que está encendido y que Windows lo reconoce.")
            raise RuntimeError(f"No se ha podido escanear: {msg}")
        return None
    return destino
