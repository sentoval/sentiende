# -*- coding: utf-8 -*-
"""Servidor local de las pantallas (solo en este equipo: 127.0.0.1, sin internet).

La ventana del programa muestra las pantallas (HTML) y estas hablan con el motor por /api/….
El trabajo pesado (leer, OCR) va en un hilo aparte para que la ventana no se congele;
un cerrojo evita que dos peticiones toquen el motor a la vez."""
import io, json, mimetypes, re, threading, traceback
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, unquote

from sentiende import VERSION, CONTRATO, FASES
from sentiende.motor import Motor, MotorError
from sentiende import checklist, arreglos
from sentiende.carpetas import libre
from sentiende.negociacion import ErrorNegociacion
from sentiende.gestion import ErrorGestion
from sentiende.ia import ControladorIA, ErrorIA, URL_MODELOS, VERSION_API
from sentiende.contexto import ContextoLote

WEB = Path(__file__).resolve().parent / "web"
CERROJO = threading.RLock()

class App:
    def __init__(self, raiz, carpeta_variante):
        self.motor = Motor(raiz, carpeta_variante)
        self.trabajando = False
        self._cola = []
        self._grupos = {}
        self._hilo = None
        from sentiende.correo import Correo
        from app.bluetooth import Bluetooth
        self.correo = Correo(self.motor.carpetas.rutas["datos"])
        self.correo_estado = {"trabajando": False, "ultimo": None, "resumen": None, "error": None}
        self.bluetooth = Bluetooth(lambda rutas: self.encolar(rutas, "bluetooth")[0])
        self.ia = ControladorIA(self.motor)
        self.ia.cerrojo = CERROJO
        self.contexto = ContextoLote(self.motor, self.ia)
        self._ia_hilo = None
        threading.Thread(target=self._correo_auto, daemon=True).start()
        threading.Thread(target=self._ia_auto, daemon=True).start()

    # ---------------- Controlador IA (v3.0)
    def ia_lote(self, lote_id):
        """Pasa un lote a la IA en segundo plano (el cerrojo del motor se suelta mientras se espera a la API)."""
        if self._ia_hilo and self._ia_hilo.is_alive():
            raise ErrorIA("El Controlador IA ya está trabajando.")
        def tarea():
            try:
                self.ia.ejecutar_lote(lote_id, CERROJO)
            except Exception as e:
                with CERROJO:
                    self.motor.almacen.evento(f"Controlador IA: {e}", lote_id=lote_id, nivel="se")
        self._ia_hilo = threading.Thread(target=tarea, daemon=True)
        self._ia_hilo.start()

    def _ia_auto(self):
        """Al terminar cada lote (si está encendida y en «al terminar cada lote»); y las tarifas, como máximo una vez al día."""
        import time
        tarifas = 0
        while True:
            time.sleep(15)
            try:
                if not self.trabajando:
                    self.pasar_contexto()
                with CERROJO:
                    aj = self.ia.ajustes()
                if not aj["activo"]:
                    continue
                tarifas += 15
                if tarifas >= 3600:
                    tarifas = 0
                    self.ia.comprobar_tarifas()          # no hace nada si ya se comprobó hoy
                if aj["actua"] != "lote" or self.trabajando or (self._ia_hilo and self._ia_hilo.is_alive()):
                    continue
                with CERROJO:
                    if self.ia.resumen()["estado"] == "pausa":
                        continue
                    pendientes = self.ia.lotes_pendientes()
                if pendientes:
                    self.ia_lote(pendientes[0])
            except Exception:
                pass

    # ---------------- correo (v1.1)
    def revisar_correo(self):
        """Recoge el correo en segundo plano; el estado se consulta en /api/correo."""
        if self.correo_estado["trabajando"]:
            return self.correo_estado
        self.correo_estado.update(trabajando=True, error=None)
        def tarea():
            import datetime
            try:
                def lote(rutas, descripcion):
                    l, ids = self.encolar(rutas, "correo")
                    with CERROJO:
                        self.motor.almacen.evento(f"Recibido por {descripcion}: {len(ids)} adjunto(s)", lote_id=l, fase=1)
                    return l
                def decidir(email):
                    with CERROJO:
                        return self.motor.gestion.decidir_remitente(email)
                def cuarentena(rutas, de, asunto):
                    with CERROJO:
                        self.motor.gestion.poner_en_cuarentena(rutas, de, asunto)
                self.correo_estado["resumen"] = self.correo.recoger(self.motor.carpetas.entrada, lote, decidir, cuarentena)
                for x in self.correo_estado["resumen"]["ignorados"]:
                    with CERROJO:
                        self.motor.almacen.evento(f"Correo: adjunto ignorado (tipo no admitido o con macros): {x}", fase=1, nivel="se")
            except Exception as e:
                self.correo_estado["error"] = str(e)
            finally:
                self.correo_estado.update(trabajando=False, ultimo=datetime.datetime.now().isoformat(timespec="seconds"))
        threading.Thread(target=tarea, daemon=True).start()
        return self.correo_estado

    def _correo_auto(self):
        import time
        espera = 0
        while True:
            time.sleep(30)
            try:
                a = self.correo.ajustes()
                if not (a.get("activo") and a.get("cada_minutos")):
                    continue
                espera += 30
                if espera >= int(a["cada_minutos"]) * 60:
                    espera = 0
                    self.revisar_correo()
            except Exception:
                pass

    # ---------------- trabajo en segundo plano
    def encolar(self, rutas, origen, grupo=None):
        """grupo: los archivos soltados a la vez llegan uno a uno pero van al mismo lote."""
        with CERROJO:
            lote, ids = self.motor.recibir(rutas, origen, self._grupos.get(grupo) if grupo else None)
            if grupo:
                self._grupos[grupo] = lote
        self._cola.append(lote)
        self._arrancar()
        return lote, ids

    def _arrancar(self):
        if self._hilo and self._hilo.is_alive():
            return
        self._hilo = threading.Thread(target=self._trabajar, daemon=True)
        self._hilo.start()

    def _trabajar(self):
        self.trabajando = True
        try:
            while True:
                with CERROJO:
                    pendientes = self.motor.almacen.documentos("estado = 'en_proceso' AND fase < 6")
                if not pendientes:
                    break
                for d in pendientes:
                    with CERROJO:
                        self.motor._procesar_doc(self.motor.almacen.documento(d["id"]))
            self.pasar_contexto()
        finally:
            self.trabajando = False

    def pasar_contexto(self):
        """Contexto del lote (en local) para los lotes que ya no tienen nada en proceso (y los rezagados)."""
        with CERROJO:
            if not self.contexto.ajustes()["activo"]:
                return
            for lid in self.contexto.pendientes():
                try:
                    self.contexto.aplicar(lid)
                except Exception as e:           # el contexto nunca para el programa: se avisa y se sigue
                    self.motor.almacen.evento(f"Contexto del lote {lid}: no se ha podido aplicar ({e}). Los documentos siguen en el Centro de revisión.", lote_id=lid, nivel="se")
                    for d in self.motor.almacen.documentos("lote_id = ? AND estado = 'espera_emparejar'", (lid,)):
                        datos = d["datos"] or {}
                        datos["contexto"] = True
                        self.motor.almacen.actualizar(d["id"], datos=datos)

    # ---------------- datos para las pantallas
    def info(self):
        v = self.motor.variante
        tipos = sorted(({"id": d["id"], "nombre": v.etiqueta(d["id"]), "orden": d["nombres"]["es"][0], "familia": d.get("familia")} for d in v.base["documentos"]), key=lambda x: x["orden"])
        return {"motor": {"version": VERSION, "contrato": CONTRATO}, "variante": {k: v.meta.get(k) for k in ("id", "nombre", "version", "colores", "vocabulario", "finalidades", "papeles", "modulos")},
                "compatibilidad": v.compat.mensaje, "finalidades_visibles": self.motor.finalidades_visibles(), "fases": FASES, "tipos": tipos,
                "carpetas": {k: str(p) for k, p in self.motor.carpetas.rutas.items()},
                "bancos": sorted(b["nombre"] for b in v.base.get("entidades_financieras", []))}

    def estado(self):
        a = self.motor.almacen
        lotes = [dict(r) for r in a.db.execute("SELECT * FROM lotes ORDER BY id DESC LIMIT 30")]
        docs = self.motor.estado()
        extra = {d["id"]: d for d in a.documentos("1")}
        for d in docs:
            e = extra[d["id"]]
            d.update(lote_id=e["lote_id"], padre_id=e["padre_id"], expediente_id=e["expediente_id"], nombre_final=e["nombre_final"], paginas=e["paginas"])
        ia_lotes = {r["lote_id"]: dict(r) for r in a.db.execute("SELECT l.*, (SELECT COUNT(*) FROM ia_acciones x WHERE x.lote_id = l.lote_id) AS acciones FROM ia_lotes l")}
        acciones = {r[0]: r[1] for r in a.db.execute("SELECT lote_id, COUNT(*) FROM ia_acciones GROUP BY lote_id")}
        for l in lotes:
            l["ia"] = ia_lotes.get(l["id"])
            l["acciones"] = acciones.get(l["id"], 0)
            l["documentos"] = [d for d in docs if d["lote_id"] == l["id"] and d["estado"] not in ("separado", "deshecho")]
            l["separados"] = [d for d in docs if d["lote_id"] == l["id"] and d["estado"] == "separado"]
        cuenta = lambda *est: sum(1 for d in docs if d["estado"] in est)
        return {"trabajando": self.trabajando, "ia": self.ia.resumen(), "lotes": [l for l in lotes if l["documentos"] or l["separados"]],
                "cuentas": {"pendientes": cuenta("en_proceso", "espera_emparejar", "parado"), "revisar": cuenta("espera_emparejar", "parado"),
                            "limbo": cuenta("limbo"), "avisos_cliente": len(a.avisos_cliente()),
                            "avisos_se": a.db.execute("SELECT COUNT(*) FROM eventos WHERE nivel = 'se' AND id > ?", (self.motor.gestion.ajustes().get("avisos_se_visto", 0),)).fetchone()[0],
                            "cuarentena": a.db.execute("SELECT COUNT(*) FROM cuarentena WHERE estado = 'pendiente'").fetchone()[0],
                            "notificaciones": a.db.execute("SELECT COUNT(*) FROM notificaciones WHERE visto = 0").fetchone()[0]}}

    def documento(self, did):
        m, a = self.motor, self.motor.almacen
        d = a.documento(did)
        if not d:
            raise MotorError(f"No existe el documento {did}")
        sel = d["paginas_sel"] or list(range(1, (d["paginas"] or 1) + 1))
        textos = []
        for n in sel:
            c = a.texto_cache(f'{d["huella"]}:{n}') or {}
            textos.append(c.get("texto", ""))
        if not any(textos):
            textos = [x["texto"] for x in a.textos_de(did).values()]
        d["texto_paginas"] = textos
        d["eventos"] = a.eventos(did)
        d["sugerencias"] = m.sugerencias(did)
        d["paginas_lista"] = sel
        from sentiende.extraer import norm
        terceros = set(m.terceros_lote(d["lote_id"]))
        for p in (d["datos"] or {}).get("personas", []):
            p["tercero_lote"] = norm(p.get("completo", "")) in terceros
        d["fecha_clave"] = m.clave_fecha(d["tipo"]) if d["tipo"] else None
        d["ia_acciones"] = self.ia.acciones_doc(did)
        d["fecha_claves"] = {t["id"]: m.clave_fecha(t["id"]) for t in m.variante.base["documentos"]}
        return d

    def expedientes(self):
        a = self.motor.almacen
        out = []
        marcas = self.motor.gestion.marcas()
        for r in a.db.execute("SELECT * FROM expedientes WHERE estado != 'papelera' ORDER BY id DESC"):
            e = dict(r)
            e["personas"] = a.personas_de(e["id"])
            op = a.db.execute("SELECT datos FROM operacion WHERE expediente_id = ?", (e["id"],)).fetchone()
            e["operacion"] = json.loads(op["datos"]) if op else {}
            e["etiqueta"] = self.motor.gestion.etiqueta(e["estado"], e["operacion"])
            e["marcas"] = marcas.get(e["id"], {"favorito": False, "prioridad": ""})
            try:
                c = checklist.evaluar(self.motor.variante, a, e["id"])
                e["checklist"] = {"recibidos": c["recibidos"], "total": c["total"]}
            except Exception:
                e["checklist"] = None
            out.append(e)
        return out

    def exportar_textos(self):
        """Datos\\textos_leidos.txt: lo que el motor ha leído y deducido de cada documento.
        Sirve para mejorar el reconocimiento (nombres, fechas) con documentos reales."""
        a = self.motor.almacen
        lineas = [f"SeFinancia · textos leídos · {len(a.documentos('1'))} documentos", ""]
        for d in a.documentos("estado != 'separado'"):
            datos = d["datos"] or {}
            lineas += ["=" * 70, f"DOCUMENTO {d['id']} · {d['nombre_recibido']}",
                       f"Tipo: {d['tipo'] or 'no reconocido'} ({round((d['confianza'] or 0) * 100)} %) · estado: {d['estado']} · fase {d['fase']}",
                       f"DNI leídos: {', '.join(datos.get('dni') or []) or '—'}",
                       f"Personas leídas: {'; '.join(p.get('completo', '') for p in datos.get('personas') or []) or 'ninguna'}",
                       f"Fechas leídas: {', '.join(datos.get('fechas') or []) or '—'}",
                       f"Periodo: {datos.get('periodo') or '—'} · ejercicio: {datos.get('ejercicio') or '—'} · caducidad: {datos.get('caducidad') or '—'}", ""]
            textos = self.documento(d["id"])["texto_paginas"]
            for i, tx in enumerate(textos, 1):
                lineas += [f"--- página {i} ---", tx or "(sin texto)", ""]
        ruta = self.motor.carpetas.rutas["datos"] / "textos_leidos.txt"
        ruta.write_text("\n".join(lineas), encoding="utf-8-sig")
        return str(ruta)

    def vista(self, did, pos, grande=False):
        """Imagen de una página para el visor (PNG)."""
        from PIL import Image
        d = self.motor.almacen.documento(did)
        sel = d["paginas_sel"] or list(range(1, (d["paginas"] or 1) + 1))
        n = sel[min(max(pos, 1), len(sel)) - 1]
        rot = next((r for r in (d["rotaciones"] or []) if r["n"] == n), {})
        if rot.get("imagen") and Path(rot["imagen"]).exists():
            img = Image.open(rot["imagen"])
        else:
            final = Path(d["ruta_final"]) if d["ruta_final"] else None
            if final and final.exists():
                ruta, pagina = final, sel.index(n) + 1          # el PDF guardado ya solo tiene sus páginas
            else:
                ruta = Path(d["ruta_original"]) if Path(d["ruta_original"]).exists() else Path(d["ruta_original_final"] or "")
                pagina = n
            if ruta.suffix.lower() == ".pdf":
                from sentiende.lectura import imagen_pdf
                img = imagen_pdf(ruta, pagina, dpi=200 if grande else 90)
            elif ruta.suffix.lower() in (".xlsx", ".xls", ".docx", ".doc", ".csv", ".txt") or not ruta.is_file():
                # 3.0.3: Excel y Word no tienen vista previa (antes daba error al abrirlos como imagen)
                from PIL import ImageDraw
                img = Image.new("RGB", (900, 1200), "white")
                dib = ImageDraw.Draw(img)
                dib.rectangle((60, 60, 840, 1140), outline=(180, 180, 180), width=3)
                dib.text((120, 560), f"Sin vista previa: {ruta.suffix.upper().lstrip('.') or 'archivo'}", fill=(90, 90, 90))
                dib.text((120, 600), "Ábrelo con su programa para verlo.", fill=(120, 120, 120))
            else:
                from PIL import ImageOps
                img = ImageOps.exif_transpose(Image.open(ruta))
                if rot.get("rotacion") and not final:
                    img = img.rotate(-rot["rotacion"], expand=True)
        giro = int(rot.get("giro") or 0)
        if giro and not (d["ruta_final"] and Path(d["ruta_final"]).exists()):
            img = img.rotate(-giro, expand=True)
        img = img.convert("RGB")
        img.thumbnail((2600, 3600) if grande else (1100, 1500))
        buf = io.BytesIO(); img.save(buf, "PNG"); return buf.getvalue()

def crear_manejador(app):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _json(self, obj, code=200):
            b = json.dumps(obj, ensure_ascii=False, default=str).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(b)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers(); self.wfile.write(b)

        def _cuerpo(self):
            n = int(self.headers.get("Content-Length") or 0)
            return self.rfile.read(n) if n else b""

        def _error(self, e):
            conocido = isinstance(e, (MotorError, ErrorNegociacion, ErrorGestion, RuntimeError))
            self._json({"error": str(e)}, 400 if conocido else 500)
            if not conocido:
                traceback.print_exc()

        def do_GET(self):
            p = urlparse(self.path).path
            try:
                if p == "/" or not p.startswith("/api/"):
                    return self._estatico(p)
                if p == "/api/escaneres":          # fuera del cerrojo: buscar en la red tarda un par de segundos
                    from app.escaner import lista_wia, buscar_escl
                    with CERROJO:
                        guardados = app.motor.gestion.ajustes().get("escaneres", [])
                    encontrados = lista_wia() + buscar_escl()
                    urls = {x.get("url") for x in encontrados}
                    return self._json(encontrados + [x | {"guardado": True} for x in guardados if x.get("url") not in urls])
                with CERROJO:
                    if p == "/api/info": return self._json(app.info())
                    if p in ("/api/logo", "/api/icono"):
                        v = app.motor.variante
                        im = v.meta.get("imagenes", {})
                        f = (Path(v.carpeta) / im.get("logo" if p == "/api/logo" else "icono", "")) if im else None
                        if not f or not f.is_file():
                            return self._json({"error": "Sin logo"}, 404)
                        b = f.read_bytes()
                        self.send_response(200); self.send_header("Content-Type", mimetypes.guess_type(str(f))[0] or "image/png")
                        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b); return
                    if p == "/api/estado": return self._json(app.estado())
                    if p == "/api/ia": return self._json(app.ia.pantalla())
                    if p == "/api/ia/manual": return self._json({"texto": app.ia.manual()})
                    if p == "/api/ia/lotes": return self._json(app.ia.lotes_con_informe())
                    if p == "/api/ia/por_revisar": return self._json(app.ia.por_revisar())
                    if m := re.fullmatch(r"/api/ia/informe/(\d+)", p): return self._json(app.ia.informe(int(m.group(1))))
                    if m := re.fullmatch(r"/api/ia/consulta/(\d+)", p): return self._json(app.ia.consulta(int(m.group(1))))
                    if p == "/api/expedientes": return self._json(app.expedientes())
                    if p == "/api/temporales": return self._json(app.motor.temporales())
                    if p == "/api/finalidades": return self._json(app.motor.finalidades())
                    if p == "/api/propuestas_union": return self._json(app.motor.propuestas_union())
                    if p == "/api/avisos":
                        a = app.motor.almacen
                        return self._json({"cliente": a.avisos_cliente(), "se": a.eventos(nivel="se")[-50:], "revision": a.eventos(nivel="revision")[-50:],
                                           "notificaciones": app.contexto.notificaciones(todas=True)})
                    if m := re.fullmatch(r"/api/documento/(\d+)", p): return self._json(app.documento(int(m.group(1))))
                    if p == "/api/correo":
                        from sentiende.correo import PREDEFINIDOS
                        return self._json({"ajustes": app.correo.ajustes(), "estado": app.correo_estado, "proveedores": PREDEFINIDOS})
                    if p == "/api/bluetooth": return self._json(app.bluetooth.estado)
                    if m := re.fullmatch(r"/api/negociacion/(\d+)", p): return self._json(app.motor.negociacion.de_expediente(int(m.group(1))))
                    g = app.motor.gestion
                    q = dict(x.split("=", 1) for x in (urlparse(self.path).query or "").split("&") if "=" in x)
                    if m := re.fullmatch(r"/api/operacion/(\d+)", p): return self._json(g.operacion(int(m.group(1))))
                    if p == "/api/estadisticas": return self._json(g.estadisticas())
                    if p == "/api/papelera": return self._json(g.papelera())
                    if p == "/api/personas": return self._json(g.personas())
                    if p == "/api/ajustes": return self._json(g.ajustes())
                    if p == "/api/cuarentena": return self._json(g.cuarentena())
                    if p == "/api/buscar": return self._json(g.buscar(unquote(q.get("q", "")).replace("+", " ")))
                    if p == "/api/reglas":
                        v = app.motor.variante
                        return self._json({"nombres": v.nombres, "tipos": [{"id": d["id"], "nombre": v.etiqueta(d["id"]), "familia": d.get("familia"),
                                           "corto": d.get("nombre_corto") or d["id"], "zzzz": d.get("zzzz"), "importancia": d.get("importancia"),
                                           "idiomas": sorted((d.get("nombres") or {}).keys()), "otros_nombres": (d.get("nombres") or {}).get("es", [])[1:6]}
                                          for d in v.base["documentos"]]})
                    if p == "/api/personas_repetidas": return self._json(arreglos.personas_repetidas(app.motor))
                    if m := re.fullmatch(r"/api/documentos_expediente/(\d+)", p):
                        a = app.motor.almacen
                        out = []
                        for d in a.documentos("expediente_id = ? AND estado = 'guardado'", (int(m.group(1)),)):
                            per = a.persona(d["persona_id"]) or {}
                            out.append({k: d.get(k) for k in ("id", "nombre_final", "tipo", "modelo", "nombre_recibido", "persona_id", "de_expediente", "privado", "ruta_final")}
                                       | {"persona": f'{per.get("nombre", "")} {per.get("apellido1", "")}'.strip()})
                        return self._json(sorted(out, key=lambda x: x["nombre_final"] or ""))
                    if m := re.fullmatch(r"/api/checklist/(\d+)", p): return self._json(checklist.evaluar(app.motor.variante, app.motor.almacen, int(m.group(1))))
                    if m := re.fullmatch(r"/api/vista/(\d+)/(\d+)", p):
                        b = app.vista(int(m.group(1)), int(m.group(2)), "grande=1" in (urlparse(self.path).query or ""))
                        self.send_response(200); self.send_header("Content-Type", "image/png"); self.send_header("Content-Length", str(len(b)))
                        self.end_headers(); self.wfile.write(b); return
                self._json({"error": "No existe"}, 404)
            except Exception as e:
                self._error(e)

        def do_POST(self):
            p = urlparse(self.path).path
            try:
                if p == "/api/subir":     # un archivo por petición; el nombre va en la cabecera
                    nombre = Path(unquote(self.headers.get("X-Nombre", "archivo"))).name
                    origen = self.headers.get("X-Origen", "arrastrados")
                    destino = libre(app.motor.carpetas.entrada / nombre)
                    destino.write_bytes(self._cuerpo())
                    lote, ids = app.encolar([destino], origen, self.headers.get("X-Grupo"))
                    return self._json({"lote": lote, "documentos": ids})
                datos = json.loads(self._cuerpo() or b"{}")
                if p == "/api/correo/guardar": return self._json(app.correo.guardar(datos))
                if p == "/api/correo/probar":
                    try: return self._json(app.correo.probar(datos or None))
                    except Exception as e: raise MotorError(str(e))
                if p == "/api/correo/revisar":
                    if not app.correo.ajustes()["servidor"]: raise MotorError("Primero configura el correo en Ajustes.")
                    return self._json(app.revisar_correo())
                if p == "/api/escaner_ip":
                    from app.escaner import probar_escl
                    try:
                        e = probar_escl(datos.get("direccion") or "")
                    except RuntimeError as ex:
                        raise MotorError(str(ex))
                    with CERROJO:
                        aj = app.motor.gestion.ajustes()
                        lista = [x for x in aj.get("escaneres", []) if x.get("url") != e["url"]] + [e]
                        app.motor.gestion.guardar_ajustes({"escaneres": lista})
                    return self._json(e)
                if p == "/api/escanear":
                    from app.escaner import escanear_wia, escanear_escl
                    try:
                        if datos.get("via") == "escl":
                            fs = escanear_escl(app.motor.carpetas.entrada, datos["url"], int(datos.get("dpi") or 300), datos.get("color", True), bool(datos.get("alimentador")))
                        else:
                            fs = escanear_wia(app.motor.carpetas.entrada, datos.get("id"), int(datos.get("dpi") or 300), datos.get("color", True))
                    except RuntimeError as e:
                        raise MotorError(str(e))
                    if not fs:
                        return self._json({"cancelado": True})
                    lote, ids = app.encolar(fs, "escáner")
                    return self._json({"lote": lote, "documentos": ids, "archivo": ", ".join(f.name for f in fs)})
                if p == "/api/abrir":
                    import os, subprocess, sys
                    ruta = Path(datos.get("ruta") or "")
                    raices = [Path(x).resolve() for x in app.motor.carpetas.rutas.values()]
                    if not ruta.exists() or not any(r == ruta.resolve() or r in ruta.resolve().parents for r in raices):
                        raise MotorError("Esa carpeta o archivo no es del programa.")
                    if sys.platform == "win32":
                        if datos.get("seleccionar") and ruta.is_file():
                            subprocess.Popen(["explorer", "/select,", str(ruta)])
                        else:
                            os.startfile(str(ruta))
                    return self._json({"ok": True})
                if p.startswith("/api/ia/"):
                    return self._json(self._ia_post(p[8:], datos))
                if p == "/api/bluetooth":
                    try: return self._json(app.bluetooth.empezar())
                    except RuntimeError as e: raise MotorError(str(e))
                with CERROJO:
                    m = app.motor
                    if p == "/api/procesar":
                        with CERROJO:
                            r = m.reanudar()
                        app._arrancar()
                        return self._json({"ok": True, **r})
                    if p == "/api/expediente":
                        if datos.get("desde_documento"):
                            pid = m.persona_desde_documento(int(datos["desde_documento"]), int(datos.get("indice", 0)))
                        else:
                            pe = datos["persona"]
                            dup = [x for x in m.posibles_duplicados(pe["nombre"], pe.get("apellido1", ""), pe.get("apellido2", ""), pe.get("dni") or None) if x["expedientes"]]
                            if dup and not datos.get("confirmado"):
                                x = dup[0]
                                raise MotorError(f"Ya existe {x['nombre']} {x['apellido1']} {x['apellido2'] or ''} ({x['por']}) en el expediente "
                                                 f"«{x['expedientes'][0]['nombre']}». Añade el documento a ese expediente o confirma que quieres otro.")
                            pid = m.nueva_persona(pe["nombre"], pe.get("apellido1", ""), pe.get("apellido2", ""), pe.get("dni") or None)
                        eid = m.crear_expediente(pid, datos["finalidad"])
                        return self._json({"expediente": eid, "persona": pid, "carpeta": m.almacen.expediente(eid)["carpeta"]})
                    if p == "/api/emparejar":
                        if datos.get("persona_datos") and not datos.get("persona"):
                            pe = datos["persona_datos"]
                            datos["persona"] = m.nueva_persona(pe["nombre"], pe.get("apellido1", ""), pe.get("apellido2", ""), pe.get("dni") or None)
                        segunda = datos.get("segunda")
                        if segunda == "duplicado":
                            return self._json(m.gestion.eliminar_documento(int(datos["documento"])) | {"nombre_final": "a la Papelera (duplicado)"})
                        if segunda == "limbo":
                            return self._json(m.al_limbo(int(datos["documento"])))
                        if segunda == "sustituir" and datos.get("nombre_previsto"):
                            m.gestion.sustituir_previo(int(datos["expediente"]), datos["nombre_previsto"])
                        if datos.get("otros"):
                            m.vincular_personas(int(datos["expediente"]), datos["otros"], int(datos["documento"]))
                        d = m.emparejar(int(datos["documento"]), int(datos["expediente"]), datos.get("persona"), bool(datos.get("comun")),
                                        datos.get("tipo") or None, bool(datos.get("privado")), datos.get("fecha") or None)
                        try:
                            app.ia.aprender_correccion(int(datos["documento"]))       # si la IA se había equivocado, se aprende
                        except Exception:
                            pass
                        return self._json(d)
                    neg = m.negociacion
                    if p == "/api/nota":
                        return self._json({"id": neg.nota(int(datos["expediente"]), datos["tipo"], datos.get("texto"), datos.get("banco"))})
                    if p == "/api/banco":
                        return self._json({"id": neg.banco(int(datos["expediente"]), datos.get("entidad"), datos.get("estado"), datos.get("id"))})
                    if p == "/api/contacto":
                        if datos.get("quitar"):
                            neg.quitar_contacto(int(datos["quitar"])); return self._json({"ok": True})
                        return self._json({"id": neg.contacto(int(datos["banco"]), datos, datos.get("id"))})
                    if p == "/api/marca":
                        neg.marcar(int(datos["expediente"]), datos["clave"], datos.get("estado")); return self._json({"ok": True})
                    if p == "/api/tarjeta":
                        if datos.get("no"):
                            m.no_es_tarjeta(int(datos["documento"])); return self._json({"ok": True})
                        return self._json(m.guardar_tarjeta(int(datos["documento"]), int(datos["expediente"]), datos.get("entidad"), datos.get("contacto") or {}))
                    g = m.gestion
                    if p == "/api/notificacion_vista":
                        app.contexto.visto(datos.get("id") and int(datos["id"]))
                        return self._json({"ok": True})
                    if p == "/api/avisos_se_vistos":
                        ultimo = m.almacen.db.execute("SELECT COALESCE(MAX(id), 0) FROM eventos WHERE nivel = 'se'").fetchone()[0]
                        return self._json(g.guardar_ajustes({"avisos_se_visto": ultimo}))
                    if p == "/api/estado_expediente":
                        return self._json(g.cambiar_estado(int(datos["expediente"]), datos["estado"], datos.get("extra")))
                    if p == "/api/operacion":
                        return self._json(g.guardar_operacion(int(datos["expediente"]), datos.get("datos") or {}))
                    if p == "/api/marcar_expediente":
                        return self._json(g.marcar(int(datos["expediente"]), datos.get("favorito"), datos.get("prioridad")))
                    if p == "/api/eliminar":
                        if datos.get("expediente"):
                            return self._json(g.eliminar_expediente(int(datos["expediente"])))
                        return self._json(g.eliminar_documento(int(datos["documento"])))
                    if p == "/api/restaurar": return self._json(g.restaurar(int(datos["id"])))
                    if p == "/api/nombre_previsto":
                        return self._json(g.nombre_previsto(int(datos["documento"]), int(datos["expediente"]), datos.get("persona"), datos.get("tipo"),
                                                            datos.get("fecha"), bool(datos.get("privado")), bool(datos.get("comun"))))
                    if p == "/api/separar": return self._json({"documentos": g.separar_manual(int(datos["documento"]), datos["grupos"])})
                    if p == "/api/girar": return self._json({"giro": g.girar(int(datos["documento"]), int(datos["pos"]), int(datos["grados"]))})
                    if p == "/api/persona": return self._json(g.editar_persona(int(datos["id"]), datos))
                    if p == "/api/papel": return self._json(g.cambiar_papel(int(datos["expediente"]), int(datos["persona"]), datos["papel"]))
                    if p == "/api/copia": return self._json(g.copia_seguridad())
                    if p == "/api/exportar_expediente": return self._json(g.exportar_expediente(int(datos["expediente"]), bool(datos.get("privados"))))
                    if p == "/api/ajustes": return self._json(g.guardar_ajustes(datos))
                    if p == "/api/expediente_manual":
                        pe = datos["persona"]
                        pid = m.nueva_persona(pe["nombre"], pe.get("apellido1", ""), pe.get("apellido2", ""), (pe.get("dni") or "").upper() or None)
                        manuales = [pid]
                        eid = m.crear_expediente(pid, datos["finalidad"])
                        for o in datos.get("otras") or []:
                            if o.get("nombre") and o.get("apellido1"):
                                oid = m.nueva_persona(o["nombre"], o.get("apellido1", ""), o.get("apellido2", ""), (o.get("dni") or "").upper() or None)
                                m.almacen.anadir_persona(eid, oid, o.get("papel") or "Cotitular")
                                manuales.append(oid)
                        # datos metidos a mano: referencia segura para lo que llegue después (3.0.3)
                        m.almacen.db.executemany("UPDATE personas SET manual = 1 WHERE id = ?", [(x,) for x in manuales])
                        m.almacen.db.commit()
                        return self._json({"expediente": eid})
                    if p == "/api/notificacion_cambiar":
                        return self._json(app.contexto.aplicar_cambio(int(datos["id"])) or {"ok": True})
                    if p == "/api/finalidad_expediente":
                        return self._json(m.cambiar_finalidad(int(datos["expediente"]), datos["finalidad"]))
                    if p == "/api/cuarentena":
                        rutas = g.resolver_cuarentena(int(datos["id"]), datos["accion"])
                        if rutas:
                            app.encolar(rutas, "correo")
                        return self._json({"ok": True, "aceptados": len(rutas)})
                    if p == "/api/arreglo":
                        acc = datos.get("accion")
                        if acc == "mover":
                            return self._json(arreglos.mover_documento(m, int(datos["documento"]), int(datos["expediente"]),
                                                                       int(datos["persona"]) if datos.get("persona") else None, datos.get("de_expediente")))
                        if acc == "unir_expedientes":
                            return self._json(arreglos.unir_expedientes(m, int(datos["origen"]), int(datos["destino"])))
                        if acc == "quitar_persona":
                            return self._json(arreglos.quitar_persona(m, int(datos["expediente"]), int(datos["persona"])))
                        if acc == "unir_personas":
                            return self._json(arreglos.unir_personas(m, int(datos["quitar"]), int(datos["quedar"]), bool(datos.get("forzar"))))
                        raise MotorError("Arreglo desconocido.")
                    if p == "/api/sacar_limbo":
                        return self._json(m.sacar_del_limbo(int(datos["documento"])))
                    if p == "/api/limbo":
                        return self._json(m.al_limbo(int(datos["documento"])))
                    if p == "/api/vaciar":
                        q = datos.get("que")
                        n = m.vaciar_textos() if q == "textos" else m.vaciar_trabajo(todo=q == "trabajo-todo")
                        return self._json({"vaciado": n})
                    if p == "/api/unir":
                        nuevo = m.unir(datos["documentos"]); app._arrancar()
                        return self._json({"documento": nuevo})
                    if p == "/api/finalidad":
                        if "ocultar" in datos:
                            m.ocultar_finalidad(datos["id"], bool(datos["ocultar"])); return self._json({"ok": True})
                        if datos.get("quitar"):
                            m.quitar_finalidad(datos["quitar"]); return self._json({"ok": True})
                        return self._json({"id": m.guardar_finalidad(datos.get("nombre"), datos.get("documentos"), datos.get("id"))})
                    if p == "/api/exportar_textos":
                        return self._json({"ruta": app.exportar_textos()})
                    if p == "/api/textos":
                        return self._json([str(r) for r in m.regenerar_textos(datos.get("expediente"))])
                self._json({"error": "No existe"}, 404)
            except Exception as e:
                self._error(e)

        def _ia_post(self, que, datos):
            ia = app.ia
            if que == "lote":
                with CERROJO:
                    r = ia.resumen()
                if not r["tiene_clave"]:
                    raise ErrorIA("Primero escribe tu clave de la API en Ajustes › Controlador IA.")
                if not r["activo"]:
                    raise ErrorIA("Enciende el Controlador IA (botón de la barra lateral).")
                with CERROJO:
                    ia.db.execute("DELETE FROM ia_lotes WHERE lote_id = ?", (int(datos["lote"]),)); ia.db.commit()
                app.ia_lote(int(datos["lote"]))
                return {"ok": True}
            if que == "probar":
                with CERROJO:
                    clave = (datos.get("clave") or "").strip() or ia.clave()
                if not clave:
                    raise ErrorIA("Escribe la clave de la API.")
                try:
                    lista = json.loads(ia.descargar(URL_MODELOS + "?limit=100", {"x-api-key": clave, "anthropic-version": VERSION_API}))
                except Exception as e:
                    msg = str(e)
                    raise ErrorIA("La clave no es válida." if "401" in msg else f"No se ha podido conectar con la API: {msg}")
                return {"ok": True, "modelos": [x.get("id") for x in lista.get("data", [])]}
            if que == "tarifas":
                return ia.comprobar_tarifas(forzar=True)
            if que == "consola":
                import webbrowser
                from sentiende.ia import URL_CONSOLA
                webbrowser.open(URL_CONSOLA)
                return {"ok": True}
            with CERROJO:
                if que == "ajustes": return ia.guardar(datos) and ia.pantalla()
                if que == "encender": return ia.encender(bool(datos.get("activo")))
                if que == "deshacer": return ia.deshacer(int(datos["accion"]))
                if que == "deshacer_lote": return ia.deshacer_lote(int(datos["lote"]))
                if que == "revisada": ia.revisada(datos.get("accion") and int(datos["accion"]), datos.get("lote") and int(datos["lote"])); return {"ok": True}
                if que == "actualizar_tarifas": return ia.actualizar_tarifas()
                if que == "limite_hoy": return ia.subir_limite_hoy(datos.get("euros", 0))
                if que == "exportar": return {"ruta": ia.exportar()}
                if que == "importar": return {"importados": ia.importar(datos.get("datos"))}
                if que == "borrar_aprendizaje": ia.borrar_aprendizaje(); return {"ok": True}
            raise ErrorIA("No existe")

        def _estatico(self, p):
            ruta = (WEB / ("index.html" if p in ("/", "") else p.lstrip("/"))).resolve()
            if WEB not in ruta.parents and ruta != WEB / "index.html" or not ruta.is_file():
                return self._json({"error": "No existe"}, 404)
            b = ruta.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", (mimetypes.guess_type(str(ruta))[0] or "application/octet-stream") + ("; charset=utf-8" if ruta.suffix in (".html", ".js", ".css") else ""))
            self.send_header("Content-Length", str(len(b)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers(); self.wfile.write(b)
    return H

def arrancar(raiz, carpeta_variante, puerto=0):
    app = App(raiz, carpeta_variante)
    srv = ThreadingHTTPServer(("127.0.0.1", puerto), crear_manejador(app))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    app._arrancar()          # reanuda lo que quedó a medias
    return srv, app
