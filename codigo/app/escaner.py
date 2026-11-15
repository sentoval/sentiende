# -*- coding: utf-8 -*-
"""Escanear directamente.

Dos caminos, y los dos aparecen en la misma lista:
1. **WIA** (el sistema de escáneres de Windows): los escáneres por USB y también los de red o Wi-Fi que
   Windows ya tiene instalados (por WSD o por el controlador del fabricante).
2. **eSCL / AirScan** (red o Wi-Fi, sin instalar nada en Windows): la mayoría de impresoras multifunción
   modernas lo llevan. Se buscan en la red local (mDNS, servicio _uscan._tcp) y también se puede
   escribir la IP a mano. Wi-Fi Direct funciona si el equipo está conectado a la red Wi-Fi Direct del escáner.

Todo es local: no sale nada a internet."""
import datetime, json, os, re, socket, struct, subprocess, sys, time, urllib.request, urllib.error
from pathlib import Path
from xml.etree import ElementTree as ET

JPEG = "{B96B3CAE-0728-11D3-9D7B-0000F81EF32E}"
PS_LISTA = r"""
$ErrorActionPreference = 'SilentlyContinue'
$dm = New-Object -ComObject WIA.DeviceManager
$out = @()
foreach ($d in $dm.DeviceInfos) { if ($d.Type -eq 1) {
  $n = ''; $p = ''; foreach ($prop in $d.Properties) { if ($prop.Name -eq 'Name') { $n = $prop.Value }; if ($prop.Name -eq 'Port') { $p = [string]$prop.Value } }
  $out += [pscustomobject]@{ id = $d.DeviceID; nombre = $n; puerto = $p } } }
$out | ConvertTo-Json -Compress
"""
PS_DIALOGO = r"""
$ErrorActionPreference = 'Stop'
$dlg = New-Object -ComObject WIA.CommonDialog
$img = $dlg.ShowAcquireImage(1, 0, 0, '{JPEG}', $false, $true, $false)
if ($img -eq $null) { exit 3 }
$img.SaveFile('{RUTA}')
"""
PS_DIRECTO = r"""
$ErrorActionPreference = 'Stop'
$dm = New-Object -ComObject WIA.DeviceManager
$info = $null; foreach ($d in $dm.DeviceInfos) { if ($d.DeviceID -eq '{ID}') { $info = $d } }
if ($info -eq $null) { Write-Error 'No se encuentra el escáner'; exit 4 }
$dev = $info.Connect()
$item = $dev.Items.Item(1)
foreach ($p in $item.Properties) {
  if ($p.PropertyID -eq 6147) { $p.Value = {DPI} }   # resolución horizontal
  if ($p.PropertyID -eq 6148) { $p.Value = {DPI} }   # resolución vertical
  if ($p.PropertyID -eq 6146) { $p.Value = {INTENT} } # 1 color, 2 grises
}
$img = $item.Transfer('{JPEG}')
$img.SaveFile('{RUTA}')
"""


def _powershell(script):
    return subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
                          capture_output=True, text=True, creationflags=0x08000000 if sys.platform == "win32" else 0, timeout=300)


def _nombre_archivo(carpeta, ext=".jpg"):
    return Path(carpeta) / f"escaneo_{datetime.datetime.now():%Y%m%d_%H%M%S}{ext}"


# ---------------------------------------------------------------- WIA (USB y red instalados en Windows)
def lista_wia():
    if sys.platform != "win32":
        return []
    try:
        r = _powershell(PS_LISTA)
        datos = json.loads(r.stdout or "[]")
    except Exception:
        return []
    datos = datos if isinstance(datos, list) else [datos]
    out = []
    for d in datos:
        puerto = str(d.get("puerto") or "")
        red = bool(re.search(r"https?://|\d+\.\d+\.\d+\.\d+|WSD|uuid:", puerto, re.I))
        out.append({"via": "wia", "id": d.get("id"), "nombre": d.get("nombre") or "Escáner", "conexion": "red (Windows)" if red else "USB / Windows"})
    return out


def escanear_wia(carpeta, device_id=None, dpi=300, color=True):
    """Con device_id escanea directamente; sin él abre el cuadro de escaneo de Windows. None si se cancela."""
    if sys.platform != "win32":
        raise RuntimeError("Escanear directamente solo funciona en Windows.")
    destino = _nombre_archivo(carpeta)
    ruta = str(destino).replace("'", "''")
    if device_id:
        ps = PS_DIRECTO.replace("{ID}", device_id.replace("'", "''")).replace("{DPI}", str(int(dpi))).replace("{INTENT}", "1" if color else "2")
    else:
        ps = PS_DIALOGO
    r = _powershell(ps.replace("{JPEG}", JPEG).replace("{RUTA}", ruta))
    if r.returncode == 3 or not destino.exists():
        if r.returncode not in (0, 3):
            err = (r.stderr or "").strip()
            if "0x80210015" in err or "0x80210006" in err:
                raise RuntimeError("El escáner no responde: comprueba que está encendido y conectado (USB o red).")
            raise RuntimeError("No se ha podido escanear: " + (err.splitlines()[-1] if err else f"código {r.returncode}"))
        return None
    return [destino]


# ---------------------------------------------------------------- eSCL / AirScan por red (mDNS)
def _nombre_dns(datos, i):
    partes, salto, fin = [], False, None
    while True:
        n = datos[i]
        if n == 0:
            i += 1
            break
        if n & 0xC0 == 0xC0:                       # puntero (compresión)
            if not salto:
                fin = i + 2
            i, salto = ((n & 0x3F) << 8) | datos[i + 1], True
            continue
        partes.append(datos[i + 1:i + 1 + n].decode("utf-8", "replace"))
        i += 1 + n
    return ".".join(partes), (fin if salto else i)


def _leer_respuesta(datos):
    """Registros de una respuesta mDNS: [(nombre, tipo, valor)]."""
    _, _, qd, an, ns, ar = struct.unpack("!HHHHHH", datos[:12])
    i, out = 12, []
    for _ in range(qd):
        _, i = _nombre_dns(datos, i)
        i += 4
    for _ in range(an + ns + ar):
        nombre, i = _nombre_dns(datos, i)
        tipo, _, _, largo = struct.unpack("!HHIH", datos[i:i + 10])
        i += 10
        rd = datos[i:i + largo]
        if tipo == 12:                              # PTR
            val = _nombre_dns(datos, i)[0]
        elif tipo == 33:                            # SRV: prioridad, peso, puerto, destino
            val = (struct.unpack("!H", rd[4:6])[0], _nombre_dns(datos, i + 6)[0])
        elif tipo == 1:                             # A
            val = socket.inet_ntoa(rd)
        elif tipo == 16:                            # TXT
            val, j = {}, 0
            while j < len(rd):
                l = rd[j]; t = rd[j + 1:j + 1 + l].decode("utf-8", "replace"); j += 1 + l
                if "=" in t:
                    k, v = t.split("=", 1); val[k.lower()] = v
        else:
            val = None
        out.append((nombre, tipo, val))
        i += largo
    return out


def _consulta(servicio):
    q = struct.pack("!HHHHHH", 0, 0, 1, 0, 0, 0)
    for parte in servicio.split("."):
        q += bytes([len(parte)]) + parte.encode()
    return q + b"\x00" + struct.pack("!HH", 12, 0x8001)       # PTR, respuesta directa (unicast)


def buscar_escl(segundos=2.0):
    """Escáneres eSCL (AirScan) de la red local. [{via, nombre, url}]"""
    regs = []
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    s.settimeout(0.3)
    try:
        for serv in ("_uscan._tcp.local", "_uscans._tcp.local"):
            s.sendto(_consulta(serv), ("224.0.0.251", 5353))
        fin = time.time() + segundos
        while time.time() < fin:
            try:
                datos, _ = s.recvfrom(9000)
                regs += _leer_respuesta(datos)
            except socket.timeout:
                continue
            except Exception:
                continue
    except OSError:
        return []
    finally:
        s.close()
    ptr = [v for n, t, v in regs if t == 12 and v and "_uscan" in n]
    srv = {n: v for n, t, v in regs if t == 33}
    txt = {n: v for n, t, v in regs if t == 16}
    a = {n: v for n, t, v in regs if t == 1}
    out = []
    for inst in dict.fromkeys(ptr):
        if inst not in srv:
            continue
        puerto, host = srv[inst]
        ip = a.get(host)
        if not ip:
            continue
        t = txt.get(inst, {})
        esquema = "https" if "_uscans" in inst else "http"
        ruta = (t.get("rs") or "eSCL").strip("/")
        out.append({"via": "escl", "nombre": t.get("ty") or inst.split("._uscan")[0], "url": f"{esquema}://{ip}:{puerto}/{ruta}", "conexion": "red / Wi-Fi (AirScan)"})
    return out


def probar_escl(direccion):
    """Comprueba una IP o URL escrita a mano. Devuelve el escáner o lanza un error."""
    d = direccion.strip()
    candidatos = [d] if d.startswith("http") else [f"http://{d}/eSCL", f"http://{d}:80/eSCL", f"https://{d}/eSCL", f"http://{d}:8080/eSCL"]
    for url in candidatos:
        try:
            with _abrir(url.rstrip("/") + "/ScannerCapabilities", timeout=4) as r:
                xml = r.read()
            nombre = re.search(rb"<pwg:MakeAndModel>(.*?)</pwg:MakeAndModel>", xml)
            return {"via": "escl", "nombre": (nombre.group(1).decode("utf-8", "replace") if nombre else f"Escáner {d}"), "url": url.rstrip("/"), "conexion": "red / Wi-Fi (AirScan)"}
        except Exception:
            continue
    raise RuntimeError(f"No hay ningún escáner AirScan (eSCL) en {d}. Comprueba la IP y que el equipo está en la misma red o Wi-Fi Direct.")


def _abrir(url, datos=None, metodo="GET", timeout=60):
    import ssl
    ctx = ssl.create_default_context()
    ctx.check_hostname, ctx.verify_mode = False, ssl.CERT_NONE           # los escáneres llevan certificados propios
    req = urllib.request.Request(url, data=datos, method=metodo, headers={"Content-Type": "text/xml"} if datos else {})
    return urllib.request.urlopen(req, timeout=timeout, context=ctx if url.startswith("https") else None)


def escanear_escl(carpeta, url, dpi=300, color=True, alimentador=False):
    """Escanea por eSCL. Del cristal, una página; del alimentador, todas las que haya (un PDF)."""
    trabajo = f"""<?xml version="1.0" encoding="UTF-8"?>
<scan:ScanSettings xmlns:scan="http://schemas.hp.com/imaging/escl/2011/05/03" xmlns:pwg="http://www.pwg.org/schemas/2010/12/sm">
  <pwg:Version>2.0</pwg:Version>
  <pwg:InputSource>{"Feeder" if alimentador else "Platen"}</pwg:InputSource>
  <scan:ColorMode>{"RGB24" if color else "Grayscale8"}</scan:ColorMode>
  <scan:XResolution>{int(dpi)}</scan:XResolution><scan:YResolution>{int(dpi)}</scan:YResolution>
  <pwg:DocumentFormat>application/pdf</pwg:DocumentFormat><scan:DocumentFormatExt>application/pdf</scan:DocumentFormatExt>
</scan:ScanSettings>""".encode()
    try:
        with _abrir(url.rstrip("/") + "/ScanJobs", trabajo, "POST", timeout=30) as r:
            loc = r.headers.get("Location")
    except urllib.error.HTTPError as e:
        if e.code == 503:
            raise RuntimeError("El escáner está ocupado: espera un momento y vuelve a intentarlo.")
        if e.code == 409 and alimentador:
            raise RuntimeError("No hay papel en el alimentador.")
        raise RuntimeError(f"El escáner ha rechazado el trabajo ({e.code}).")
    except OSError as e:
        raise RuntimeError(f"No se puede conectar con el escáner: {e}")
    if not loc:
        raise RuntimeError("El escáner no ha devuelto el trabajo.")
    if loc.startswith("/"):
        base = re.match(r"https?://[^/]+", url).group(0)
        loc = base + loc
    archivos = []
    while True:
        try:
            with _abrir(loc.rstrip("/") + "/NextDocument", timeout=120) as r:
                datos = r.read()
                tipo = r.headers.get("Content-Type", "")
        except urllib.error.HTTPError as e:
            if e.code == 404 and archivos:              # no hay más páginas
                break
            if e.code == 503:
                time.sleep(1); continue
            raise RuntimeError(f"El escáner no ha devuelto la imagen ({e.code}).")
        ext = ".pdf" if "pdf" in tipo or datos[:4] == b"%PDF" else ".jpg"
        destino = _nombre_archivo(carpeta, ext)
        if destino.exists():
            destino = destino.with_name(destino.stem + f"_{len(archivos) + 1}" + ext)
        destino.write_bytes(datos)
        archivos.append(destino)
        if not alimentador:
            break
    return archivos
