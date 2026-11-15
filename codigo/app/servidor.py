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
from sentiende import checklist
from sentiende.carpetas import libre

WEB = Path(__file__).resolve().parent / "web"
CERROJO = threading.RLock()

class App:
    def __init__(self, raiz, carpeta_variante):
        self.motor = Motor(raiz, carpeta_variante)
        self.trabajando = False
        self._cola = []
        self._grupos = {}
        self._hilo = None

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
        finally:
            self.trabajando = False

    # ---------------- datos para las pantallas
    def info(self):
        v = self.motor.variante
        tipos = sorted(({"id": d["id"], "nombre": d["nombres"]["es"][0], "familia": d.get("familia")} for d in v.base["documentos"]), key=lambda x: x["nombre"])
        return {"motor": {"version": VERSION, "contrato": CONTRATO}, "variante": {k: v.meta.get(k) for k in ("id", "nombre", "version", "colores", "vocabulario", "finalidades", "papeles", "modulos")},
                "compatibilidad": v.compat.mensaje, "finalidades_visibles": self.motor.finalidades_visibles(), "fases": FASES, "tipos": tipos,
                "carpetas": {k: str(p) for k, p in self.motor.carpetas.rutas.items()}}

    def estado(self):
        a = self.motor.almacen
        lotes = [dict(r) for r in a.db.execute("SELECT * FROM lotes ORDER BY id DESC LIMIT 30")]
        docs = self.motor.estado()
        extra = {d["id"]: d for d in a.documentos("1")}
        for d in docs:
            e = extra[d["id"]]
            d.update(lote_id=e["lote_id"], padre_id=e["padre_id"], expediente_id=e["expediente_id"], nombre_final=e["nombre_final"], paginas=e["paginas"])
        for l in lotes:
            l["documentos"] = [d for d in docs if d["lote_id"] == l["id"] and d["estado"] != "separado"]
            l["separados"] = [d for d in docs if d["lote_id"] == l["id"] and d["estado"] == "separado"]
        cuenta = lambda *est: sum(1 for d in docs if d["estado"] in est)
        return {"trabajando": self.trabajando, "lotes": [l for l in lotes if l["documentos"] or l["separados"]],
                "cuentas": {"pendientes": cuenta("en_proceso", "espera_emparejar", "parado"), "revisar": cuenta("espera_emparejar", "parado"),
                            "limbo": cuenta("limbo"), "avisos": len(a.avisos_cliente()) + len(a.eventos(nivel="se"))}}

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
        d["fecha_clave"] = m.clave_fecha(d["tipo"]) if d["tipo"] else None
        d["fecha_claves"] = {t["id"]: m.clave_fecha(t["id"]) for t in m.variante.base["documentos"]}
        return d

    def expedientes(self):
        a = self.motor.almacen
        out = []
        for r in a.db.execute("SELECT * FROM expedientes ORDER BY id DESC"):
            e = dict(r)
            e["personas"] = a.personas_de(e["id"])
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
            else:
                from PIL import ImageOps
                img = ImageOps.exif_transpose(Image.open(ruta))
                if rot.get("rotacion") and not final:
                    img = img.rotate(-rot["rotacion"], expand=True)
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
            self._json({"error": str(e)}, 400 if isinstance(e, MotorError) else 500)
            if not isinstance(e, MotorError):
                traceback.print_exc()

        def do_GET(self):
            p = urlparse(self.path).path
            try:
                if p == "/" or not p.startswith("/api/"):
                    return self._estatico(p)
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
                    if p == "/api/expedientes": return self._json(app.expedientes())
                    if p == "/api/temporales": return self._json(app.motor.temporales())
                    if p == "/api/finalidades": return self._json(app.motor.finalidades())
                    if p == "/api/propuestas_union": return self._json(app.motor.propuestas_union())
                    if p == "/api/avisos":
                        a = app.motor.almacen
                        return self._json({"cliente": a.avisos_cliente(), "se": a.eventos(nivel="se")[-50:], "revision": a.eventos(nivel="revision")[-50:]})
                    if m := re.fullmatch(r"/api/documento/(\d+)", p): return self._json(app.documento(int(m.group(1))))
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
                with CERROJO:
                    m = app.motor
                    if p == "/api/procesar":
                        app._arrancar(); return self._json({"ok": True})
                    if p == "/api/expediente":
                        if datos.get("desde_documento"):
                            pid = m.persona_desde_documento(int(datos["desde_documento"]), int(datos.get("indice", 0)))
                        else:
                            pe = datos["persona"]
                            pid = m.nueva_persona(pe["nombre"], pe.get("apellido1", ""), pe.get("apellido2", ""), pe.get("dni") or None)
                        eid = m.crear_expediente(pid, datos["finalidad"])
                        return self._json({"expediente": eid, "persona": pid, "carpeta": m.almacen.expediente(eid)["carpeta"]})
                    if p == "/api/emparejar":
                        if datos.get("otros"):
                            m.vincular_personas(int(datos["expediente"]), datos["otros"], int(datos["documento"]))
                        d = m.emparejar(int(datos["documento"]), int(datos["expediente"]), datos.get("persona"), bool(datos.get("comun")),
                                        datos.get("tipo") or None, bool(datos.get("privado")), datos.get("fecha") or None)
                        return self._json(d)
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
