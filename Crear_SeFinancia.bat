@echo off
chcp 65001 >nul
title SeFinancia - crear el programa
cd /d "%~dp0"

set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY where python >nul 2>nul && set "PY=python"
if defined PY (
  %PY% -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)" >nul 2>nul || set "PY="
)
if not defined PY goto sinpython

%PY% construir\construir.py %*
echo.
pause
exit /b

:sinpython
echo No se encuentra Python 3.10 o superior en este equipo.
echo.
where winget >nul 2>nul || goto manual
echo Lo instalo ahora (Python 3.13, desde Microsoft winget). Si Windows pide permiso, acepta.
winget install -e --id Python.Python.3.13 --accept-package-agreements --accept-source-agreements
echo.
echo Cuando termine, CIERRA esta ventana y vuelve a hacer doble clic en Crear_SeFinancia.bat.
pause
exit /b

:manual
echo Instala Python desde https://www.python.org/downloads/  (marca "Add python.exe to PATH")
echo y vuelve a hacer doble clic en Crear_SeFinancia.bat.
pause
