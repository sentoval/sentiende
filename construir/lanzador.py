# -*- coding: utf-8 -*-
"""SeFinancia.exe: el lanzador. Solo busca el motor en la carpeta Motor\\ y lo abre.

Va «congelado» dentro del .exe junto con Python y las librerías; el motor (Motor\\sentiende y
Motor\\app) y la variante (Variantes\\sefinancia) quedan como archivos sueltos para poder
actualizarlos por separado sin volver a crear el .exe."""
import importlib, os, sys
from pathlib import Path

LANZADOR = 3          # súbelo cuando cambien las librerías que lleva el .exe

def _para_pyinstaller():
    """Nunca se ejecuta: le dice a PyInstaller qué meter en el .exe (lo que usa el motor)."""
    import argparse, base64, collections, csv, ctypes, dataclasses, datetime, difflib, functools, glob, hashlib
    import http.server, io, itertools, json, locale, math, mimetypes, platform, queue, shutil, socket, sqlite3
    import statistics, string, subprocess, tempfile, textwrap, threading, time, traceback, unicodedata, uuid
    import urllib.parse, urllib.request, webbrowser, zipfile, xml.etree.ElementTree
    import imaplib, ssl, email, email.header, email.message, email.parser, email.policy, email.utils, inspect, ctypes.wintypes   # v1.1: correo
    import smtplib, hmac, email.generator, email.mime.multipart, email.mime.base, email.mime.text, email.contentmanager   # 3.2.1: enviar correo
    import numpy, cv2, PIL.Image, PIL.ImageOps, PIL.ImageDraw, PIL.ImageFont
    import pdfplumber, pypdf, pypdfium2, pytesseract, docx, openpyxl, webview

def _aviso(texto):
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, texto, "SeFinancia", 0x10)
    except Exception:
        print(texto)

def main():
    base = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
    motor = base / "Motor"
    if not (motor / "sentiende").is_dir() or not (motor / "app").is_dir():
        _aviso(f"Falta el motor Sentiende en:\n{motor}\n\nVuelve a crear o copiar el programa completo (SeFinancia.exe, Motor y Variantes).")
        return 2
    sys.path.insert(0, str(motor))
    try:
        abrir = importlib.import_module("app.abrir")
    except ImportError as e:
        _aviso(f"Este motor necesita una versión más nueva de SeFinancia.exe:\n{e}\n\nVuelve a crear el programa con «Crear_SeFinancia.bat». Tus documentos y datos no se tocan.")
        return 3
    return abrir.main(lanzador=LANZADOR)

if __name__ == "__main__":
    sys.exit(main() or 0)
