# Código · Sentiende 2.0.0 + variante SeFinancia 1.0.0

Primera fase del código (15/11/2026). Motor funcionando de principio a fin **sin pantallas**: se prueba con la línea de órdenes. Las pantallas (web dentro de una ventana) y el empaquetado en .exe vienen después.

## Estructura

```
codigo/
├─ sentiende/                 ← EL MOTOR (común a todas las aplicaciones; no tiene ejecutable propio)
│  ├─ __init__.py             versión del motor 2.0.0 y contrato 2
│  ├─ version.py              compatibilidad motor ↔ variante: dice cuál actualizar (M-18, M-19, M-67)
│  ├─ variante.py             carga la carpeta de configuración de la variante
│  ├─ carpetas.py             Entrada, Doc_original, SeDocumentos (+_Limbo), Papelera, Variantes, Datos (+Trabajo)
│  ├─ almacen.py              base de datos local (Datos\sentiende.db)
│  ├─ recibir.py              fase 1: mover a Entrada, huella, duplicados, tipos permitidos
│  ├─ lectura.py              fases 2 y 4: texto del PDF digital u OCR; orientar y enderezar; caché de páginas
│  ├─ separar.py              fase 3: separar PDF con varios documentos y páginas mezcladas
│  ├─ extraer.py              fase 5: DNI/NIE, CIF, IBAN (validados), fechas, importes, periodos…
│  ├─ clasificar.py           fase 6: tipo y entidad con la base de conocimiento (provisional)
│  ├─ nombres.py              fase 8: YYYXXX_nombrecorto_ZZZZ y carpeta nombre1apellido1_DNI5_MMAA
│  ├─ checklist.py            fase 9: lo que pide la variante y su estado
│  ├─ textos.py               archivo de texto del expediente (IMG678_textos.txt)
│  └─ motor.py                orquestador de las 10 fases; reanuda; se para sin perder nada
├─ variantes/
│  └─ sefinancia/             ← LA VARIANTE (solo configuración, sin código)
│     ├─ variante.json        nombre, versión 1.0.0, «requiere motor 2.x», colores, vocabulario, módulos
│     ├─ base_conocimiento.json   copia de 03_base_conocimiento/sentiende_base_conocimiento.json (55 tipos, 108 entidades…)
│     ├─ nombres.json         reglas de nombres
│     ├─ checklists.json      hipotecario (F-03); pyme y taxi en una actualización
│     └─ imagenes\            logo e icono (pendiente)
├─ app/                      ← LAS PANTALLAS (web dentro de una ventana; sin internet)
│  ├─ abrir.py                abre la ventana «SeFinancia · con Sentiende» (o el navegador con --navegador)
│  ├─ servidor.py             servidor local 127.0.0.1 + API; el motor trabaja en segundo plano
│  └─ web/                    index.html, app.css, app.js
├─ herramientas/sentiende_cli.py   probar el motor desde la línea de órdenes
└─ pruebas/                   pruebas automáticas con documentos inventados
```

## Qué hace ya

| Fase | Estado |
| --- | --- |
| 1 Recibir | Hecha: mueve a Entrada, huella, duplicado exacto (no se relee), rechaza lo que no es PDF/imagen/Word/Excel o no coincide con su extensión |
| 2 Leer | Hecha: texto del PDF digital; OCR para escaneos y fotos; caché por página |
| 3 Separar | Hecha: clasifica cada página, usa «Página X de N», une páginas sueltas a su documento aunque estén lejos, las reordena y aparta las páginas en blanco. Cada parte pasa a ser un documento; el original se mueve a Doc_original al guardar la última parte |
| 4 Orientar | Hecha: giros de 90/180/270 y enderezado de más de 1° |
| 5 Extraer datos | Hecha: DNI/NIE, CIF, IBAN, fechas, importes, periodo, ejercicio, caducidad, trimestre, matrícula, ref. catastral y **nombres de personas** (tarjeta del DNI, «apellidos, nombre», D./Dña., titular, titularidad; apellidos compuestos) con su DNI cercano |
| 6 Clasificar | Hecha: tipo, subtipo, confianza, alternativas, entidad (IBAN, CIF/BIC, nombre). Falta: logos por imagen |
| 7 Emparejar | Hecha la parte del motor: sugerencias por DNI y, sin DNI, por nombre en cualquier orden; crear la persona con lo leído en el documento; crear persona y expediente, asignar persona/papel o «de todo el expediente», Limbo. La pregunta la hará la pantalla |
| 8 Renombrar | Hecha con las reglas cerradas; si falta el dato distintivo usa la fecha de entrada y marca «revisar» |
| 10b Archivo de texto | Hecho: `IMG678_textos.txt` en la carpeta del expediente; datos temporales consultables y vaciables (orden `temporales`, `vaciar`, `textos`) |
| 9 Checklist | Hecha para hipotecario: en vigor, últimos N meses, último ejercicio, antigüedad máxima; Avisos Cliente sin repetir |
| 10 Guardar | Hecha: editado a SeDocumentos\<expediente>\, original a Doc_original\<expediente>\, vacía la copia de trabajo |

Si algo falla, el documento queda «parado» en su fase con el motivo y el original sigue en Entrada.

## Probar en Windows

0. Copiar `03_base_conocimiento/sentiende_base_conocimiento.json` del proyecto a `codigo/variantes/sefinancia/base_conocimiento.json` (en el proyecto no se duplica).

1. Instalar **Python 3.12 o superior** (python.org, marcar «Add to PATH»).
2. Instalar **Tesseract** (versión de UB Mannheim) con los idiomas español, catalán, euskera y gallego.
3. (Ya no hace falta Poppler: las páginas de los PDF se pasan a imagen con PDFium, que va dentro de pdfplumber.)
4. En la carpeta `codigo`: `pip install pdfplumber pypdf pypdfium2 pytesseract pillow opencv-python-headless numpy python-docx openpyxl pywebview` (y `reportlab` para las pruebas)
5. Pruebas automáticas (7): `python -m unittest pruebas.test_motor -v`
6. Con documentos de verdad (usa una carpeta de pruebas, **los archivos se mueven**):
   ```
   python herramientas\sentiende_cli.py --raiz D:\PruebaSentiende procesar C:\copias\*.pdf
   python herramientas\sentiende_cli.py --raiz D:\PruebaSentiende estado
   python herramientas\sentiende_cli.py --raiz D:\PruebaSentiende sugerir 1
   python herramientas\sentiende_cli.py --raiz D:\PruebaSentiende expediente --desde 1 --finalidad hipotecario
   (o a mano: expediente --nombre Iván --apellidos "Morales Gil" --dni 12345678Z --finalidad hipotecario)
   python herramientas\sentiende_cli.py --raiz D:\PruebaSentiende emparejar 1 --expediente 1
   python herramientas\sentiende_cli.py --raiz D:\PruebaSentiende checklist 1
   python herramientas\sentiende_cli.py --raiz D:\PruebaSentiende avisos
   ```

7. Las pantallas: `pip install pywebview` y luego `python -m app.abrir --raiz D:\PruebaSentiende`
   (sin pywebview, o con `--navegador`, se abre en el navegador). Pantallas de esta entrega: Bandeja de entrada
   (arrastrar, elegir, pegar con Ctrl+V; Escanear y Bluetooth visibles pero desactivados, Bluetooth «v1.1»),
   Motor de proceso (barra de progreso, 10 fases con explicación al pasar el ratón, dónde está cada archivo),
   Centro de revisión (visor de páginas, tipo, datos leídos, sugerencias, expediente nuevo con lo leído,
   «de todo el expediente», «No compartir», Limbo), Expedientes con su checklist, Avisos, Limbo y Ajustes
   (carpetas, datos temporales y vaciarlos, versiones). Buscar y Estadísticas aparecen como «pronto».

## Crear el programa (SeFinancia.exe)

`empaquetado/` es el kit: `Crear_SeFinancia.bat` + `construir/` (construir.py, lanzador.py, requisitos.txt) + una copia de `sentiende/`, `app/` y `variantes/sefinancia/` en `codigo/`. En Windows, doble clic en el .bat: instala lo que falte, crea `SeFinancia\SeFinancia.exe` con PyInstaller (carpeta, no un solo archivo; lo interno va en `Motor\`), copia Tesseract con los idiomas a `Motor\tesseract\`, monta `Variantes\sefinancia\` y se comprueba con `SeFinancia.exe --comprobar` (informe en `Datos\comprobacion.json`). Al rehacerlo solo cambia el .exe, `Motor\` y `Variantes\sefinancia\`; nunca las carpetas de documentos ni `Datos\`. Errores del programa: `Datos\registro.txt`.

El motor y la variante quedan como archivos sueltos: se actualizan sin volver a crear el .exe. El .exe (lanzador, versión 1) solo hace falta rehacerlo si el motor necesita librerías nuevas; el motor lo avisa (`LANZADOR_MINIMO` en `app/abrir.py`).

## Siguiente fase del código

1. Pantallas que faltan: Personas, Buscar, Estadísticas, Reglas, Tipos, Papelera, cambiar carpetas desde Ajustes.
2. Probar el kit en el equipo de Joan y corregir lo que salga (primera vez en Windows real).
