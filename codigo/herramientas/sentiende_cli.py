# -*- coding: utf-8 -*-
"""Probar el motor desde la línea de órdenes, sin pantallas (para las pruebas en el equipo de Joan).

  python sentiende_cli.py --raiz D:\\PruebasSentiende procesar C:\\ruta\\nomina.pdf C:\\ruta\\dni.jpg
  python sentiende_cli.py --raiz D:\\PruebasSentiende estado
  python sentiende_cli.py --raiz D:\\PruebasSentiende expediente --nombre Iván --apellidos "Morales Gil" --dni 12345678Z --finalidad hipotecario
  python sentiende_cli.py --raiz D:\\PruebasSentiende emparejar 3 --expediente 1 [--comun] [--tipo nomina]
  python sentiende_cli.py --raiz D:\\PruebasSentiende limbo 4
  python sentiende_cli.py --raiz D:\\PruebasSentiende checklist 1
  python sentiende_cli.py --raiz D:\\PruebasSentiende avisos
"""
import argparse, json, sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AQUI))
from sentiende import VERSION
from sentiende.motor import Motor, MotorError

def main():
    ap = argparse.ArgumentParser(description=f"Sentiende {VERSION} · pruebas del motor")
    ap.add_argument("--raiz", required=True, help="Carpeta raíz de pruebas (se crean dentro Entrada, Doc_original, …)")
    ap.add_argument("--variante", default=str(AQUI / "variantes" / "sefinancia"))
    sub = ap.add_subparsers(dest="orden", required=True)
    p = sub.add_parser("procesar"); p.add_argument("archivos", nargs="+")
    sub.add_parser("estado")
    p = sub.add_parser("sugerir", help="personas leídas y expedientes que coinciden"); p.add_argument("doc", type=int)
    p = sub.add_parser("expediente"); p.add_argument("--nombre"); p.add_argument("--apellidos", default=""); p.add_argument("--desde", type=int, help="crear la persona con el nombre y DNI leídos en este documento")
    p.add_argument("--dni"); p.add_argument("--finalidad", default="hipotecario")
    p = sub.add_parser("emparejar"); p.add_argument("doc", type=int); p.add_argument("--expediente", type=int, required=True)
    p.add_argument("--comun", action="store_true", help="documento de todo el expediente"); p.add_argument("--tipo")
    p = sub.add_parser("limbo"); p.add_argument("doc", type=int)
    p = sub.add_parser("checklist"); p.add_argument("expediente", type=int)
    sub.add_parser("avisos")
    sub.add_parser("temporales", help="qué ocupa la memoria temporal")
    p = sub.add_parser("vaciar", help="vaciar datos temporales"); p.add_argument("que", choices=["trabajo", "trabajo-todo", "textos"])
    p = sub.add_parser("textos", help="rehacer el registro de texto"); p.add_argument("expediente", type=int, nargs="?")
    a = ap.parse_args()
    try:
        m = Motor(a.raiz, a.variante)
    except MotorError as e:
        print("No se puede arrancar:", e); return 2
    print(f"Sentiende {VERSION} · {m.variante.nombre} {m.variante.version} · {m.variante.compat.mensaje}\n")
    try:
        return ejecutar(m, a)
    except MotorError as e:
        print("No se ha podido:", e); return 1

def ejecutar(m, a):
    if a.orden == "procesar":
        lote, ids = m.recibir(a.archivos)
        m.procesar(lote)
        return mostrar_estado(m, lote)
    if a.orden == "estado":
        return mostrar_estado(m)
    if a.orden == "sugerir":
        for p in m.personas_leidas(a.doc):
            print(f"Leído en el documento: {p['completo']} · DNI {p.get('dni') or '—'} ({p['por']})")
        for s in m.sugerencias(a.doc):
            print(f"Coincide con {s['persona']['nombre']} {s['persona']['apellido1']} por {s['por']} · expedientes: " + (", ".join(f"{e['id']} {e['nombre']}" for e in s["expedientes"]) or "ninguno"))
        return 0
    if a.orden == "expediente":
        if a.desde:
            pid = m.persona_desde_documento(a.desde)
        else:
            if not a.nombre:
                print("Indica --nombre o --desde DOC"); return 1
            ap1, _, ap2 = a.apellidos.partition(" ")
            pid = m.nueva_persona(a.nombre, ap1, ap2, a.dni)
        eid = m.crear_expediente(pid, a.finalidad)
        e = m.almacen.expediente(eid)
        print(f"Expediente {eid}: {e['nombre']} · carpeta {e['carpeta']}"); return 0
    if a.orden == "emparejar":
        d = m.emparejar(a.doc, a.expediente, de_expediente=a.comun, tipo=a.tipo)
        print(f"Guardado: {d['ruta_final']}\nOriginal: {d['ruta_original_final']}"); return 0
    if a.orden == "limbo":
        d = m.al_limbo(a.doc); print(f"Al Limbo: {d['ruta_final']}"); return 0
    if a.orden == "checklist":
        from sentiende import checklist
        r = checklist.evaluar(m.variante, m.almacen, a.expediente)
        print(f"Checklist {r['finalidad']}: {r['recibidos']} de {r['total']}")
        for f in r["filas"]:
            print(f"  [{f['estado']:<10}] {f['documento']:<35} {f['quien']:<22} {f['detalle']}")
        return 0
    if a.orden == "temporales":
        t = m.temporales()
        print(f"Copia de trabajo: {t['trabajo_archivos']} archivos, {t['trabajo_bytes'] / 1e6:.1f} MB · sin uso: {t['trabajo_sin_uso']} ({t['trabajo_sin_uso_bytes'] / 1e6:.1f} MB) · documentos en proceso: {t['en_proceso']}")
        print(f"Memoria de textos: {t['textos_paginas']} páginas, {t['textos_bytes'] / 1e6:.2f} MB"); return 0
    if a.orden == "vaciar":
        n = m.vaciar_textos() if a.que == "textos" else m.vaciar_trabajo(todo=a.que == "trabajo-todo")
        print(f"Vaciado: {n}"); return 0
    if a.orden == "textos":
        for r in m.regenerar_textos(a.expediente):
            print("Rehecho:", r)
        return 0
    if a.orden == "avisos":
        for av in m.almacen.avisos_cliente():
            print(f"Avisos Cliente · expediente {av['expediente_id']}: {av['mensaje']}")
        for e in m.almacen.eventos():
            if e["nivel"] in ("se", "cliente", "revision"):
                print(f"{e['fecha']} · {'Avisos Se' if e['nivel'] == 'se' else 'Avisos Cliente' if e['nivel'] == 'cliente' else 'Revisar'} · doc {e['documento_id']}: {e['mensaje']}")
        return 0

def mostrar_estado(m, lote=None):
    for d in m.estado(lote):
        conf = f"{round((d['confianza'] or 0) * 100)} %" if d["tipo"] else ""
        print(f"#{d['id']:<3} {d['archivo'][:34]:<34} fase {d['fase']:>2} {d['fase_nombre']:<13} {d['estado']:<17} {d['tipo'] or '—':<14} {conf:>5}  {d['motivo'] or ''}")
        for k, v in d["donde"].items():
            if v:
                print(f"      {k}: {v}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
