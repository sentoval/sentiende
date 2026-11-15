# -*- coding: utf-8 -*-
"""Recibir por Bluetooth (v1.1).

Windows ya trae el asistente para recibir archivos por Bluetooth (fsquirt.exe). El programa
lo abre en modo «Recibir» y vigila durante un rato las carpetas donde Windows deja lo recibido
(Documentos, la carpeta que elijas en el asistente si está entre las vigiladas, Descargas y
Escritorio). Lo que llega con un tipo admitido entra como un lote «Bluetooth»."""
import os, subprocess, sys, threading, time
from pathlib import Path

from sentiende.recibir import PERMITIDOS

MINUTOS = 15


def carpetas_vigiladas():
    casa = Path(os.environ.get("USERPROFILE") or Path.home())
    posibles = [casa / "Documents", casa / "Documentos", casa / "OneDrive" / "Documents", casa / "OneDrive" / "Documentos",
                casa / "Documents" / "Bluetooth Exchange Folder", casa / "Downloads", casa / "Desktop", casa / "OneDrive" / "Desktop"]
    return [p for p in dict.fromkeys(posibles) if p.is_dir()]


class Bluetooth:
    def __init__(self, recibir):
        self.recibir = recibir            # recibir(rutas) → lote
        self.hilo = None
        self.estado = {"activo": False, "recibidos": 0, "hasta": None, "mensaje": ""}

    def empezar(self):
        if sys.platform != "win32":
            raise RuntimeError("Recibir por Bluetooth solo funciona en Windows.")
        exe = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "fsquirt.exe"
        if not exe.exists():
            raise RuntimeError("Este Windows no tiene el asistente de Bluetooth (fsquirt.exe). ¿Tiene Bluetooth el equipo?")
        subprocess.Popen([str(exe), "-receive"])
        if not (self.hilo and self.hilo.is_alive()):
            self.hilo = threading.Thread(target=self._vigilar, daemon=True)
            self.hilo.start()
        return self.estado

    def _vigilar(self):
        inicio = time.time()
        fin = inicio + MINUTOS * 60
        self.estado.update(activo=True, recibidos=0, hasta=fin, mensaje="Esperando archivos por Bluetooth…")
        vistos, recogidos = {}, set()
        try:
            while time.time() < fin:
                time.sleep(2)
                nuevos = []
                for c in carpetas_vigiladas():
                    try:
                        for f in c.iterdir():
                            if f in recogidos or not f.is_file() or f.suffix.lower() not in PERMITIDOS:
                                continue
                            st = f.stat()
                            if st.st_mtime < inicio - 5 and st.st_ctime < inicio - 5:
                                continue
                            # se espera a que termine de escribirse: mismo tamaño dos vueltas seguidas
                            if vistos.get(f) == st.st_size:
                                nuevos.append(f)
                            vistos[f] = st.st_size
                    except OSError:
                        continue
                if nuevos:
                    recogidos.update(nuevos)
                    self.recibir(nuevos)
                    self.estado["recibidos"] += len(nuevos)
                    self.estado["mensaje"] = f"Recibidos {self.estado['recibidos']} archivo(s) por Bluetooth."
                    fin = max(fin, time.time() + 120)
        finally:
            self.estado.update(activo=False, mensaje=(f"Bluetooth: {self.estado['recibidos']} archivo(s) recibidos."
                                                     if self.estado["recibidos"] else "Bluetooth: no ha llegado nada."))
