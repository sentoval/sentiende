# -*- coding: utf-8 -*-
"""3.1.2 · Parecido entre hojas sueltas (fotos o escaneos de una página) del mismo lote (Joan, 17/11 18:17).

Para cada par de hojas se suman puntos por señales independientes:
- cómo se hizo: mismo móvil y hora casi igual (EXIF), nombres de archivo seguidos (IMG_0012 → IMG_0013),
  mismo tamaño de imagen;
- cómo se ve: color del papel y de la tinta, márgenes, cabecera o logotipo;
- qué dice: misma entidad, mismo número de póliza/contrato/cuenta, mismo DNI, apartados seguidos
  («3. …» → «4. …») y frase que sigue en la hoja siguiente.
Nunca se proponen juntas dos hojas reconocidas con claridad como tipos distintos, ni dos de una serie
(recibos, nóminas…) de meses distintos.

De momento SOLO SE PROPONE (Joan: «me parece bien, pero anótalo, automatizarlo en un futuro»):
- 60 % o más: en el Centro de revisión sale «¿Son el mismo documento? (NN %)» con el motivo y «Unir páginas»;
- por debajo del 60 %: nada.
Lo que Joan hace (unir, o «No, son distintos») se apunta por señal y ajusta el peso de cada una (tabla
`parecido_aprendido`): las señales que aciertan pesan más y las que fallan, menos. Sin IA."""
import json, re
from pathlib import Path

UMBRAL_PROPUESTA = 60
IMAGENES = (".jpg", ".jpeg", ".png", ".tif", ".tiff", ".heic", ".webp", ".bmp")

PUNTOS = {   # señal: (puntos, texto para Joan)
    "captura": (30, "mismo móvil y hora casi igual"),
    "captura_cerca": (15, "mismo móvil, con poco tiempo entre fotos"),
    "nombre_seguido": (20, "nombres de archivo seguidos"),
    "tamano": (10, "mismo tamaño de imagen"),
    "papel": (10, "mismo color de papel"),
    "tinta": (5, "mismo color de tinta"),
    "margenes": (10, "mismos márgenes"),
    "cabecera": (10, "misma cabecera"),
    "entidad": (10, "misma entidad"),
    "identificador": (25, "mismo número de póliza, contrato o cuenta"),
    "dni": (15, "mismo DNI"),
    "apartados": (25, "los apartados siguen"),
    "frase": (10, "la frase sigue en la otra hoja"),
}

ESQUEMA = """CREATE TABLE IF NOT EXISTS parecido_aprendido(senal TEXT PRIMARY KEY, aciertos INTEGER DEFAULT 0, fallos INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS parecido_descartes(a INTEGER, b INTEGER, PRIMARY KEY(a, b));"""


def _numero_nombre(nombre):
    """('IMG-20261117-WA', 12) de «IMG-20261117-WA0012.jpg»: el último grupo de cifras del nombre."""
    stem = Path(nombre or "").stem
    m = re.search(r"^(.*?)(\d{1,6})(\D*)$", stem)
    return (m.group(1).upper() + "#" + m.group(3).upper(), int(m.group(2))) if m else (None, None)


def _exif(ruta):
    try:
        from PIL import Image
        with Image.open(ruta) as im:
            ex = im.getexif()
            fecha = ex.get(36867) or ex.get(306)
            try:
                fecha = fecha or ex.get_ifd(0x8769).get(36867)
            except Exception:
                pass
            return {"modelo": str(ex.get(272) or "").strip() or None, "fecha": str(fecha) if fecha else None, "tam": list(im.size)}
    except Exception:
        return {}


def _segundos(f):
    m = re.match(r"(\d{4}):(\d\d):(\d\d) (\d\d):(\d\d):(\d\d)", f or "")
    if not m:
        return None
    import datetime
    return datetime.datetime(*map(int, m.groups())).timestamp()


def _visual(img):
    """Papel, tinta, márgenes y cabecera de una hoja (en una miniatura en gris y color)."""
    import numpy as np
    im = img.convert("RGB")
    im.thumbnail((400, 400))
    a = np.asarray(im).astype(int)
    g = a.mean(axis=2)
    claro = g >= np.percentile(g, 60)
    oscuro = g <= min(np.percentile(g, 8), g[claro].mean() - 60 if claro.any() else 128)
    papel = [int(x) for x in np.median(a[claro], axis=0)] if claro.any() else None
    tinta = [int(x) for x in np.median(a[oscuro], axis=0)] if oscuro.sum() > 30 else None
    margenes = None
    if oscuro.sum() > 30:
        ys, xs = np.where(oscuro)
        h, w = g.shape
        margenes = [round(xs.min() / w, 3), round(ys.min() / h, 3), round(1 - xs.max() / w, 3), round(1 - ys.max() / h, 3)]
    # cabecera: huella media (aHash 16x4) de la franja de arriba
    from PIL import Image
    h = im.height
    franja = im.crop((0, 0, im.width, max(4, int(h * 0.15)))).convert("L").resize((16, 4), Image.BILINEAR)
    v = np.asarray(franja).astype(int)
    cab = "".join("1" if x > v.mean() else "0" for x in v.flatten())
    return {"papel": papel, "tinta": tinta, "margenes": margenes, "cabecera": cab}


def _texto(t):
    from .extraer import norm
    from .separar import secciones
    T = norm(t or "")
    ids = {x for x in re.findall(r"\b\d{9,20}\b", re.sub(r"(?<=\d)[ .\-](?=\d)", "", T))}
    dnis = set(re.findall(r"\b[XYZ]?\d{7,8}[A-Z]\b", T))
    ids -= {d[:-1] for d in dnis}
    lineas = [l.strip() for l in (t or "").split("\n") if len(l.strip()) > 3]
    return {"ids": sorted(ids), "dnis": sorted(dnis), "secs": secciones(t or ""),
            "fin": lineas[-1][-1:] if lineas else "", "inicio": lineas[0][:1] if lineas else ""}


class Parecido:
    def __init__(self, motor):
        self.m = motor
        self.cache = {}
        self.m.almacen.db.executescript(ESQUEMA)

    # ------------------------------------------------------------ firma de cada hoja
    def firma(self, d):
        clave = (d["id"], d["actualizado"])
        if clave in self.cache:
            return self.cache[clave]
        f = {"id": d["id"], "lote": d["lote_id"], "tipo": d["tipo"], "conf": d["confianza"] or 0, "entidad": d["entidad"],
             "nombre": _numero_nombre(d["nombre_recibido"]), "mes": None}
        datos = d["datos"] or {}
        f["mes"] = (datos.get("periodo") or datos.get("emision") or "")[:7] or None
        if (d["extension"] or "").lower() in IMAGENES and Path(d["ruta_original"] or "").exists():
            f["exif"] = _exif(d["ruta_original"])
        else:
            f["exif"] = {}
        img = None
        try:
            from PIL import Image
            r = next((x for x in d["rotaciones"] or [] if x.get("imagen") and Path(x["imagen"]).exists()), None)
            if r:
                img = Image.open(r["imagen"])
            elif (d["extension"] or "").lower() in IMAGENES and Path(d["ruta_original"] or "").exists():
                from PIL import ImageOps
                img = ImageOps.exif_transpose(Image.open(d["ruta_original"]))
            elif (d["extension"] or "").lower() == ".pdf" and Path(d["ruta_original"] or "").exists():
                from .lectura import imagen_pdf
                img = imagen_pdf(d["ruta_original"], 1, dpi=60)
        except Exception:
            img = None
        f["visual"] = _visual(img) if img is not None else {}
        fijos = self.m.almacen.textos_de(d["id"])
        texto = "\n".join(t["texto"] or "" for t in fijos.values()) if fijos else self.m._texto(d)
        f["texto"] = _texto(texto)
        self.cache[clave] = f
        return f

    # ------------------------------------------------------------ comparar dos hojas
    def senales(self, a, b):
        """Señales que comparten a y b (en el orden a → b). None si no pueden ser el mismo documento."""
        from .contexto import EN_SERIE
        if a["tipo"] and b["tipo"] and a["tipo"] != b["tipo"] and a["conf"] >= 0.75 and b["conf"] >= 0.75:
            return None
        if a["tipo"] == b["tipo"] and a["tipo"] in EN_SERIE and a["mes"] and b["mes"] and a["mes"] != b["mes"]:
            return None
        s = []
        ea, eb = a["exif"], b["exif"]
        ta, tb = _segundos(ea.get("fecha")), _segundos(eb.get("fecha"))
        if ea.get("modelo") and ea.get("modelo") == eb.get("modelo") and ta and tb:
            if abs(ta - tb) <= 300:
                s.append("captura")
            elif abs(ta - tb) <= 1800:
                s.append("captura_cerca")
        (pa, na), (pb, nb) = a["nombre"], b["nombre"]
        if pa and pa == pb and na is not None and nb is not None and 0 < abs(nb - na) <= 3:
            s.append("nombre_seguido")
        if ea.get("tam") and eb.get("tam") and sorted(ea["tam"]) == sorted(eb["tam"]):
            s.append("tamano")
        va, vb = a["visual"], b["visual"]
        dist = lambda x, y: sum(abs(i - j) for i, j in zip(x, y)) / 3
        if va.get("papel") and vb.get("papel") and dist(va["papel"], vb["papel"]) < 12:
            s.append("papel")
        if va.get("tinta") and vb.get("tinta") and dist(va["tinta"], vb["tinta"]) < 18:
            s.append("tinta")
        if va.get("margenes") and vb.get("margenes") and sum(abs(i - j) for i, j in zip(va["margenes"], vb["margenes"])) < 0.08:
            s.append("margenes")
        if va.get("cabecera") and vb.get("cabecera") and sum(x != y for x, y in zip(va["cabecera"], vb["cabecera"])) <= 8 \
                and va["cabecera"].count("1") not in (0, 64):
            s.append("cabecera")
        if a["entidad"] and a["entidad"] == b["entidad"]:
            s.append("entidad")
        xa, xb = a["texto"], b["texto"]
        if set(xa["ids"]) & set(xb["ids"]):
            s.append("identificador")
        if set(xa["dnis"]) & set(xb["dnis"]):
            s.append("dni")
        if xa["secs"] and xb["secs"] and xa["secs"][-1] < xb["secs"][0] <= xa["secs"][-1] + 2:
            s.append("apartados")
        if xa["fin"] and xa["fin"] not in ".:!?»)" and xb["inicio"].islower():
            s.append("frase")
        return s

    def pesos(self):
        out = {}
        for r in self.m.almacen.db.execute("SELECT * FROM parecido_aprendido"):
            out[r["senal"]] = max(0.5, min(1.5, (r["aciertos"] + 2) / (r["fallos"] + 2)))
        return out

    def puntuar(self, senales, pesos=None):
        pesos = self.pesos() if pesos is None else pesos
        return min(99, round(sum(PUNTOS[x][0] * pesos.get(x, 1.0) for x in senales)))

    # ------------------------------------------------------------ propuestas
    def propuestas(self, docs):
        """docs: hojas sueltas que esperan revisión. Devuelve grupos {documentos, porcentaje, motivos} ≥ umbral,
        con las hojas en el orden más probable (hora de la foto o número del nombre)."""
        a = self.m.almacen
        descartes = {(r[0], r[1]) for r in a.db.execute("SELECT a, b FROM parecido_descartes")}
        pesos = self.pesos()
        por_lote = {}
        for d in docs:
            por_lote.setdefault(d["lote_id"], []).append(self.firma(d))
        grupos = []
        for lote, fs in por_lote.items():
            if len(fs) < 2:
                continue
            fs.sort(key=lambda f: (_segundos(f["exif"].get("fecha")) or 0, f["nombre"][1] or 0, f["id"]))
            padre = {f["id"]: f["id"] for f in fs}
            def raiz(x):
                while padre[x] != x:
                    x = padre[x]
                return x
            pares = {}
            for i, f in enumerate(fs):
                for g in fs[i + 1:]:
                    if (min(f["id"], g["id"]), max(f["id"], g["id"])) in descartes:
                        continue
                    s = self.senales(f, g)
                    if s is None:
                        continue
                    pct = self.puntuar(s, pesos)
                    if pct >= UMBRAL_PROPUESTA:
                        pares[(f["id"], g["id"])] = (pct, s)
                        padre[raiz(g["id"])] = raiz(f["id"])
            juntos = {}
            for f in fs:
                juntos.setdefault(raiz(f["id"]), []).append(f["id"])
            for ids in juntos.values():
                if len(ids) < 2:
                    continue
                internos = [v for k, v in pares.items() if k[0] in ids and k[1] in ids]
                pct = min(p for p, _ in internos)
                motivos = []
                for _, s in internos:
                    for x in s:
                        if PUNTOS[x][1] not in motivos:
                            motivos.append(PUNTOS[x][1])
                grupos.append({"lote": lote, "documentos": ids, "porcentaje": pct, "motivos": motivos,
                               "senales": sorted({x for _, s in internos for x in s})})
        return grupos

    # ------------------------------------------------------------ aprender de Joan
    def aprender(self, ids, acierto):
        """Joan ha unido estas hojas (acierto=True) o ha dicho «No, son distintos» (False)."""
        a = self.m.almacen
        docs = [a.documento(int(i)) for i in ids]
        fs = [self.firma(d) for d in docs if d]
        vistas = set()
        for i, f in enumerate(fs):
            for g in fs[i + 1:]:
                vistas |= set(self.senales(f, g) or [])
                if not acierto:
                    a.db.execute("INSERT OR IGNORE INTO parecido_descartes VALUES(?, ?)", (min(f["id"], g["id"]), max(f["id"], g["id"])))
        col = "aciertos" if acierto else "fallos"
        for x in vistas:
            a.db.execute(f"INSERT INTO parecido_aprendido(senal, {col}) VALUES(?, 1) ON CONFLICT(senal) DO UPDATE SET {col} = {col} + 1", (x,))
        a.db.commit()
        return sorted(vistas)
