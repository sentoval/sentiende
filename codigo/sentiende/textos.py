# -*- coding: utf-8 -*-
"""Registro de texto del expediente (M-68).

En la carpeta de cada expediente se genera YYYXXX_textos.txt (código del primer titular):
cada documento guardado, con sus datos y el texto reconocido página a página.
El texto sale del texto guardado con cada documento (Datos\\sentiende.db), que no se borra al
vaciar la memoria temporal,
y el archivo se regenera entero cada vez que cambia el expediente: nunca queda desfasado
ni repite nada. Los documentos «No compartir» se citan, pero su texto no se incluye."""
import datetime
from pathlib import Path
from .nombres import codigo_persona

SEP = "=" * 78

def nombre_registro(almacen, expediente_id, sin_dni="NOINFORMADO"):
    personas = almacen.personas_de(expediente_id)
    cod = codigo_persona(personas[0], sin_dni) if personas else "EXPEDIENTE"
    return f"{cod}_textos.txt"

def generar(almacen, carpeta_docs, expediente_id, sin_dni="NOINFORMADO"):
    """Escribe (o reescribe) el registro de texto del expediente. Devuelve su ruta."""
    destino, out = _contenido(almacen, carpeta_docs, expediente_id, sin_dni)
    destino.parent.mkdir(parents=True, exist_ok=True)
    tmp = destino.with_suffix(".tmp")
    tmp.write_text("\n".join(out), encoding="utf-8-sig")   # con BOM: el Bloc de notas lo abre bien
    tmp.replace(destino)
    return destino


def desactualizado(almacen, carpeta_docs, expediente_id, sin_dni="NOINFORMADO"):
    """3.1.3 (Joan, 19/11): ¿el registro de texto ya no coincide con lo guardado? (falta, hay documentos nuevos,
    movidos, renombrados, girados o leídos otra vez). Se compara todo menos la línea «Generado:»."""
    try:
        destino, out = _contenido(almacen, carpeta_docs, expediente_id, sin_dni)
        if not destino.exists():
            return bool(almacen.documentos("expediente_id = ? AND estado = 'guardado'", (expediente_id,)))
        lineas = lambda t: [l for l in t.replace("\r\n", "\n").replace("\r", "\n").split("\n") if not l.startswith("Generado: ")]
        return lineas(destino.read_text(encoding="utf-8-sig")) != lineas("\n".join(out))
    except Exception:
        return False


def _contenido(almacen, carpeta_docs, expediente_id, sin_dni):
    exp = almacen.expediente(expediente_id)
    destino = Path(carpeta_docs) / exp["carpeta"] / nombre_registro(almacen, expediente_id, sin_dni)
    docs = sorted(almacen.documentos("expediente_id = ? AND estado = 'guardado'", (expediente_id,)), key=lambda d: d["nombre_final"] or "")
    personas = ", ".join(f'{p["nombre"]} {p["apellido1"]} {p["apellido2"]}'.strip() + f' ({p["papel"]})' for p in almacen.personas_de(expediente_id))
    out = [f"REGISTRO DE TEXTO RECONOCIDO · {exp['nombre']}",
           f"Carpeta: {exp['carpeta']} · Personas: {personas}",
           f"Generado: {datetime.datetime.now():%d/%m/%Y %H:%M} · {len(docs)} documentos",
           "Este archivo lo crea Sentiende y se rehace solo: no hace falta editarlo.", ""]
    for d in docs:
        rot = {i: p for i, p in enumerate(d["rotaciones"] or [], 1)}      # por posición en el documento
        out += [SEP, f"ARCHIVO:   {d['nombre_final']}", f"ORIGINAL:  {d['nombre_recibido']} (recibido {d['creado'][:16].replace('T', ' ')})",
                f"TIPO:      {d['tipo']} · confianza {round((d['confianza'] or 0) * 100)} %" + (f" · entidad {d['entidad']}" if d["entidad"] else ""),
                f"PÁGINAS:   {d['paginas'] or 1}", SEP]
        if d["privado"]:
            out += ["[Documento «No compartir»: su texto no se incluye en este registro.]", ""]
            continue
        fijos = almacen.textos_de(d["id"])
        for n in range(1, (d["paginas"] or 1) + 1):
            info = rot.get(n, {})
            n_arch = info.get("n", n)                                      # número de página en el archivo recibido
            c = fijos.get(n) or almacen.texto_cache(f"{d['huella']}:{n_arch}")
            origen = {"pdf": "texto del PDF", "ocr": "OCR", "office": "texto del archivo"}.get(info.get("origen") or (c or {}).get("origen"), "")
            conf = info.get("confianza")
            out.append(f"--- Página {n}" + (f" (pág. {n_arch} del archivo recibido)" if n_arch != n or d.get("padre_id") else "") + f" · {origen}" + (f" · lectura {round(conf * 100)} %" if conf is not None and origen == "OCR" else "") + " ---")
            out.append((c["texto"].strip() if c and c["texto"] else "[Sin texto guardado para esta página.]"))
            out.append("")
    return destino, out
