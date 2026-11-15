# -*- coding: utf-8 -*-
"""Abre la aplicación. Es lo que ejecuta SeFinancia.exe (a través de su lanzador).

Busca su carpeta raíz (la del ejecutable), prepara el OCR (Tesseract dentro de Motor\\tesseract o
el instalado en el equipo), arranca el servidor local y muestra las pantallas en una ventana propia
(pywebview, que en Windows usa el visor web del sistema). Si no está disponible, las abre en el
navegador predeterminado: el programa funciona igual.

Este archivo está en Motor\\app\\: se actualiza con el motor, sin tocar SeFinancia.exe."""
import argparse, datetime, json, os, shutil, sys, time, traceback, webbrowser
from pathlib import Path

AQUI = Path(__file__).resolve().parent.parent          # carpeta del código (en el programa: Motor\)
if str(AQUI) not in sys.path:
    sys.path.insert(0, str(AQUI))
from sentiende import VERSION
from sentiende.motor import MotorError

LANZADOR_MINIMO = 1          # versión mínima de SeFinancia.exe que necesita este motor
CONGELADO = getattr(sys, "frozen", False)

def mensaje(texto, titulo="SeFinancia", error=True):
    """Ventana de aviso de Windows (en el .exe no hay consola donde escribir)."""
    print(texto)
    if os.name == "nt":
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, texto, titulo, 0x10 if error else 0x40)
        except Exception:
            pass

def desbloquear():
    """Quita la marca «descargado de internet» (Zone.Identifier) a las DLL del programa.

    Al descomprimir un zip bajado de internet, Windows marca cada archivo; .NET se niega entonces
    a cargar las DLL de la ventana propia (pythonnet, WebView2) y el programa acaba en el navegador."""
    if os.name != "nt":
        return 0
    n = 0
    for f in AQUI.rglob("*.dll"):
        try:
            os.remove(str(f) + ":Zone.Identifier")
            n += 1
        except OSError:
            pass
    return n

def preparar_ocr():
    """Pone Tesseract al alcance del motor. Devuelve la ruta de tesseract.exe o None."""
    candidatos = [AQUI / "tesseract" / "tesseract.exe", AQUI / "tesseract" / "tesseract",
                  Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Tesseract-OCR" / "tesseract.exe",
                  Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Tesseract-OCR" / "tesseract.exe"]
    exe = next((c for c in candidatos if c.is_file()), None)
    if exe is None and shutil.which("tesseract"):
        exe = Path(shutil.which("tesseract"))
    if exe is None:
        return None
    import pytesseract
    pytesseract.pytesseract.tesseract_cmd = str(exe)
    os.environ["PATH"] = str(exe.parent) + os.pathsep + os.environ.get("PATH", "")
    if (exe.parent / "tessdata").is_dir():
        os.environ["TESSDATA_PREFIX"] = str(exe.parent / "tessdata")
    return exe

def comprobar(raiz, variante, tesseract):
    """Lo que hace «SeFinancia.exe --comprobar»: revisa que todo está y lo deja en un informe."""
    from sentiende.variante import Variante
    from sentiende import VERSION, CONTRATO
    r = {"motor": VERSION, "contrato": CONTRATO, "raiz": str(raiz), "variante": str(variante), "ok": True, "fallos": []}
    try:
        v = Variante(variante)
        r["variante_version"] = v.meta.get("version")
        r["compatibilidad"] = v.compat.mensaje
        if not v.compat.compatible:
            r["fallos"].append(v.compat.mensaje)
    except Exception as e:
        r["fallos"].append(f"Variante: {e}")
    for mod in ("pdfplumber", "pypdf", "pypdfium2", "pytesseract", "PIL", "cv2", "numpy", "docx", "openpyxl", "webview"):
        try:
            __import__(mod)
        except Exception as e:
            r["fallos"].append(f"Falta la librería {mod}: {e}")
    if tesseract:
        import pytesseract
        try:
            r["tesseract"] = str(pytesseract.get_tesseract_version())
            idiomas = set(pytesseract.get_languages(config=""))
            r["idiomas"] = sorted(idiomas)
            for i in ("spa", "osd"):
                if i not in idiomas:
                    r["fallos"].append(f"Tesseract no tiene el idioma «{i}»")
        except Exception as e:
            r["fallos"].append(f"Tesseract no responde: {e}")
    else:
        r["fallos"].append("No se encuentra Tesseract (OCR): los PDF digitales se leen, los escaneos y fotos no")
    r["ok"] = not r["fallos"]
    return r

def main(argv=None, lanzador=None):
    ap = argparse.ArgumentParser(description="SeFinancia con Sentiende")
    raiz_defecto = Path(sys.executable).parent if CONGELADO else AQUI / "_pruebas_app"
    ap.add_argument("--raiz", default=str(raiz_defecto), help="carpeta donde están (o se crearán) Entrada, SeDocumentos, Datos…")
    ap.add_argument("--variante", default=None, help="carpeta de la variante (por defecto Variantes\\sefinancia dentro de la raíz)")
    ap.add_argument("--puerto", type=int, default=0)
    ap.add_argument("--navegador", action="store_true", help="abrir en el navegador en vez de en una ventana propia")
    ap.add_argument("--comprobar", action="store_true", help="comprobar la instalación, escribir Datos\\comprobacion.json y salir")
    a = ap.parse_args(argv)
    raiz = Path(a.raiz)
    variante = Path(a.variante) if a.variante else raiz / "Variantes" / "sefinancia"
    if not variante.exists() and not CONGELADO:
        variante = AQUI / "variantes" / "sefinancia"

    # En el .exe no hay consola: los errores van a Datos\registro.txt
    if CONGELADO:
        (raiz / "Datos").mkdir(parents=True, exist_ok=True)
        sys.stdout = sys.stderr = open(raiz / "Datos" / "registro.txt", "a", encoding="utf-8", buffering=1)
        print(f"\n--- {datetime.datetime.now():%d/%m/%Y %H:%M} · motor {VERSION} · lanzador {lanzador}")

    if lanzador is not None and lanzador < LANZADOR_MINIMO:
        mensaje("Este motor necesita una versión más nueva de SeFinancia.exe.\n\nActualiza la aplicación (SeFinancia.exe); tus documentos y datos no se tocan.")
        return 3

    if CONGELADO:
        n = desbloquear()
        if n:
            print(f"Desbloqueadas {n} DLL marcadas como descargadas de internet")
    tesseract = preparar_ocr()
    if a.comprobar:
        r = comprobar(raiz, variante, tesseract)
        (raiz / "Datos").mkdir(parents=True, exist_ok=True)
        (raiz / "Datos" / "comprobacion.json").write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
        print(json.dumps(r, ensure_ascii=False, indent=1))
        return 0 if r["ok"] else 1

    from app.servidor import arrancar
    try:
        srv, app = arrancar(raiz, variante, a.puerto)
    except MotorError as e:
        mensaje(f"No se puede abrir el programa:\n\n{e}")
        return 2
    except Exception:
        traceback.print_exc()
        mensaje(f"No se puede abrir el programa. El detalle está en:\n{raiz / 'Datos' / 'registro.txt'}")
        return 2
    if tesseract is None:
        app.motor.almacen.evento("No se encuentra Tesseract (OCR): los PDF digitales se leen, pero los escaneos y las fotos no. "
                                 "Vuelve a crear el programa con «Crear_SeFinancia.bat».", nivel="se")
    url = f"http://127.0.0.1:{srv.server_address[1]}/"
    titulo = f"{app.motor.variante.nombre} · con Sentiende"
    print(f"{titulo} · {url} · carpeta {raiz}")
    if not a.navegador:
        try:
            import webview
            webview.create_window(titulo, url, width=1440, height=900, min_size=(1000, 680))
            webview.start()
            return 0
        except Exception:
            traceback.print_exc()          # sin ventana propia: se usa el navegador
    webbrowser.open(url)
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        return 0

if __name__ == "__main__":
    sys.exit(main())
