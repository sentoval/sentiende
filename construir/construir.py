# -*- coding: utf-8 -*-
"""Crea (o actualiza) la carpeta del programa SeFinancia en este equipo Windows.

    SeFinancia\\
    ├─ SeFinancia.exe         lanzador (lleva dentro Python y las librerías)
    ├─ Motor\\                 motor Sentiende (sentiende\\, app\\), OCR (tesseract\\) y lo que usa el .exe
    ├─ Variantes\\sefinancia\\  configuración de la variante
    └─ Entrada\\, Doc_original\\, SeDocumentos\\, Papelera\\, Datos\\   (los crea el programa al abrirse)

Si la carpeta ya existe solo se sustituyen SeFinancia.exe, Motor\\ y Variantes\\sefinancia\\:
tus documentos (Entrada, Doc_original, SeDocumentos, Papelera) y tus datos (Datos) no se tocan.

Uso: «Crear_SeFinancia.bat» (hace doble clic por ti). Opciones: --destino CARPETA, --ensayo."""
import argparse, json, os, shutil, subprocess, sys, time, urllib.request
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent
CODIGO = KIT / "codigo"
TRABAJO = KIT / "construir" / "_trabajo"
IDIOMAS = ["spa", "cat", "eus", "glg", "eng", "osd"]
TESSDATA_URL = "https://github.com/tesseract-ocr/tessdata_fast/raw/main/{}.traineddata"

def paso(n, txt):
    print(f"\n[{n}/6] {txt}")

def falla(txt):
    print(f"\n*** {txt}")
    sys.exit(1)

def ejecutar(orden, **kw):
    print("   >", " ".join(str(o) for o in orden))
    return subprocess.run([str(o) for o in orden], **kw)

def buscar_tesseract():
    pf = Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
    for c in (pf / "Tesseract-OCR" / "tesseract.exe", Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Tesseract-OCR" / "tesseract.exe",
              Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "Tesseract-OCR" / "tesseract.exe"):
        if c.is_file():
            return c
    w = shutil.which("tesseract")
    return Path(w) if w else None

def copiar_codigo(origen, destino):
    if destino.exists():
        shutil.rmtree(destino)
    shutil.copytree(origen, destino, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "_pruebas_app"))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--destino", default=str(KIT / "SeFinancia"), help="carpeta del programa (por defecto SeFinancia\\ junto a este kit)")
    ap.add_argument("--estricto", action="store_true", help="terminar con error si la comprobación final falla (GitHub)")
    ap.add_argument("--ensayo", action="store_true", help="sin pip, winget ni PyInstaller: solo monta la carpeta (para probar el kit)")
    a = ap.parse_args()
    destino = Path(a.destino)
    print("=" * 64, "\n  SeFinancia · crear el programa en este equipo\n" + "=" * 64)

    paso(1, f"Python {sys.version.split()[0]}")
    if sys.version_info < (3, 10):
        falla("Hace falta Python 3.10 o superior (recomendado 3.12 o 3.13).")
    if sys.version_info >= (3, 14):
        print("   Aviso: con Python 3.14 alguna librería puede no estar lista todavía. Si falla, instala Python 3.13.")

    paso(2, "Librerías (pip)")
    if not a.ensayo:
        r = ejecutar([sys.executable, "-m", "pip", "install", "--upgrade", "--disable-pip-version-check", "-r", KIT / "construir" / "requisitos.txt"])
        if r.returncode:
            falla("pip no ha podido instalar las librerías. ¿Hay conexión a internet?")

    paso(3, "OCR (Tesseract)")
    tess = buscar_tesseract()
    if tess is None and not a.ensayo and shutil.which("winget"):
        print("   No está instalado: lo instalo con winget (UB Mannheim). Si Windows pide permiso, acepta.")
        ejecutar(["winget", "install", "-e", "--id", "UB-Mannheim.TesseractOCR", "--silent", "--accept-package-agreements", "--accept-source-agreements"])
        tess = buscar_tesseract()
    if tess is None:
        print("   *** No se encuentra Tesseract. El programa se creará igual, pero sin OCR solo leerá los PDF digitales.\n"
              "       Instálalo desde https://github.com/UB-Mannheim/tesseract/wiki y vuelve a ejecutar Crear_SeFinancia.bat.")
    else:
        print(f"   Encontrado: {tess}")

    paso(4, "Crear SeFinancia.exe (PyInstaller; tarda unos minutos)")
    dist = TRABAJO / "dist"
    if a.ensayo:
        (dist / "SeFinancia" / "Motor").mkdir(parents=True, exist_ok=True)
        shutil.copy2(KIT / "construir" / "lanzador.py", dist / "SeFinancia" / "SeFinancia.py")
    else:
        if dist.exists():
            shutil.rmtree(dist)
        orden = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--windowed", "--onedir",
                 "--name", "SeFinancia", "--contents-directory", "Motor",
                 "--collect-data", "webview", "--hidden-import", "webview.platforms.edgechromium",
                 "--hidden-import", "webview.platforms.winforms", "--hidden-import", "clr",
                 "--distpath", dist, "--workpath", TRABAJO / "build", "--specpath", TRABAJO]
        icono = CODIGO / "variantes" / "sefinancia" / "imagenes" / "icono.ico"
        if icono.is_file():
            orden += ["--icon", icono]
        r = ejecutar(orden + [KIT / "construir" / "lanzador.py"])
        if r.returncode or not (dist / "SeFinancia" / "SeFinancia.exe").is_file():
            falla("PyInstaller no ha podido crear el .exe. Copia lo que sale arriba y pásaselo a Claude.")

    paso(5, f"Montar la carpeta del programa: {destino}")
    nueva = not destino.exists()
    destino.mkdir(parents=True, exist_ok=True)
    origen = dist / "SeFinancia"
    for f in origen.iterdir():                        # SeFinancia.exe (y en el ensayo, SeFinancia.py)
        if f.is_file():
            shutil.copy2(f, destino / f.name)
    if (destino / "Motor").exists():
        shutil.rmtree(destino / "Motor")              # el motor no guarda datos del usuario
    shutil.copytree(origen / "Motor", destino / "Motor")
    copiar_codigo(CODIGO / "sentiende", destino / "Motor" / "sentiende")
    copiar_codigo(CODIGO / "app", destino / "Motor" / "app")
    copiar_codigo(CODIGO / "variantes" / "sefinancia", destino / "Variantes" / "sefinancia")
    if tess is not None and "tesseract" in tess.parent.name.lower():      # solo la carpeta propia de Tesseract
        shutil.copytree(tess.parent, destino / "Motor" / "tesseract", ignore=shutil.ignore_patterns("unins*", "*.html", "doc"))
        td = destino / "Motor" / "tesseract" / "tessdata"
        td.mkdir(exist_ok=True)
        for i in IDIOMAS:
            if not (td / f"{i}.traineddata").exists():
                print(f"   Descargando el idioma «{i}» del OCR…")
                try:
                    urllib.request.urlretrieve(TESSDATA_URL.format(i), td / f"{i}.traineddata")
                except Exception as e:
                    print(f"   *** No se ha podido descargar «{i}»: {e}")
    version = json.loads((CODIGO / "variantes" / "sefinancia" / "variante.json").read_text(encoding="utf-8"))["version"]
    (destino / "Motor" / "VERSION.txt").write_text(
        f"Sentiende (motor) · creado el {time.strftime('%d/%m/%Y %H:%M')}\nVariante SeFinancia {version}\n", encoding="utf-8")
    print("   Hecho." + ("" if nueva else " Tus carpetas de documentos y Datos no se han tocado."))

    paso(6, "Comprobar el programa")
    exe = [destino / "SeFinancia.exe"] if not a.ensayo else [sys.executable, destino / "SeFinancia.py"]
    ejecutar(exe + ["--comprobar"] + (["--raiz", destino] if a.ensayo else []), timeout=180)
    informe = destino / "Datos" / "comprobacion.json"
    if not informe.exists():
        falla(f"El programa no ha respondido a la comprobación. Mira {destino / 'Datos' / 'registro.txt'} y pásaselo a Claude.")
    r = json.loads(informe.read_text(encoding="utf-8"))
    print(f"   Motor {r['motor']} · {r.get('compatibilidad', '')}")
    if r.get("tesseract"):
        print(f"   OCR Tesseract {r['tesseract']} · idiomas: {', '.join(i for i in r.get('idiomas', []) if i in IDIOMAS)}")
    for f in r["fallos"]:
        print("   *** " + f)
    print("\n" + "=" * 64)
    if r["ok"]:
        print(f"  LISTO. Abre: {destino / 'SeFinancia.exe'}")
    else:
        print(f"  Creado con avisos (arriba). Se puede abrir: {destino / 'SeFinancia.exe'}")
    print("=" * 64)
    if a.estricto:
        sys.exit(0 if r["ok"] else 1)

    if not a.ensayo and os.name == "nt" and sys.stdin and sys.stdin.isatty():
        try:
            if input("\n¿Crear un acceso directo en el escritorio? (s/n): ").strip().lower().startswith("s"):
                ps = ("$d=[Environment]::GetFolderPath('Desktop');$s=(New-Object -ComObject WScript.Shell).CreateShortcut(\"$d\\SeFinancia.lnk\");"
                      f"$s.TargetPath='{destino / 'SeFinancia.exe'}';$s.WorkingDirectory='{destino}';$s.Save()")
                subprocess.run(["powershell", "-NoProfile", "-Command", ps])
                print("   Acceso directo creado.")
        except EOFError:
            pass

if __name__ == "__main__":
    main()
