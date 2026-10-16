# Bateria de pruebas de Yugi Reload: datos, mazos, lanzador, memoria simulada, proceso vivo y frontend.
# Uso: python -I bateria.py [--solo offline|vivo] [--casos D01,G05,...]
# Salida: pruebas\logs\bateria_<fecha>.log (DEBUG exhaustivo), resultados_<fecha>.json, informe_<fecha>.md
import collections, csv, glob, hashlib, json, logging, math, os, random, shutil, struct, subprocess
import sys, tempfile, threading, time, traceback
sys.path.insert(0, r"D:\Yugi-Reload\launcher")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import yugi_reload as yr

BASE = r"D:\Yugi-Reload"
AQUI = os.path.dirname(os.path.abspath(__file__))
SELLO = time.strftime("%Y%m%d_%H%M%S")
LOGS = os.path.join(AQUI, "logs"); os.makedirs(LOGS, exist_ok=True)
RUTA_LOG = os.path.join(LOGS, "bateria_%s.log" % SELLO)

raiz = logging.getLogger("yugi")
raiz.setLevel(logging.DEBUG); raiz.handlers.clear()
_fh = logging.FileHandler(RUTA_LOG, encoding="utf-8")
_fh.setFormatter(logging.Formatter("%(asctime)s.%(msecs)03d [%(levelname)-7s] [%(threadName)s] %(name)s "
                                   "%(funcName)s:%(lineno)d | %(message)s", "%H:%M:%S"))
raiz.addHandler(_fh)
log = logging.getLogger("yugi.bateria")

def consola(msg):
    print(msg, flush=True)
    log.info(msg)

# ---------------------------------------------------------------- marco
class Fallo(Exception):
    pass

class Ctx:
    def __init__(self, caso):
        self.caso, self.subs = caso, []
    def sub(self, nombre, ok, detalle=""):
        ok = bool(ok)
        self.subs.append({"sub": nombre, "ok": ok, "detalle": str(detalle)[:400]})
        log.log(logging.DEBUG if ok else logging.ERROR, "[%s] %s %s | %s", self.caso.id, "OK  " if ok else "FALLA",
                nombre, detalle)
        return ok

class Caso:
    def __init__(self, id, nombre, cat, fn, fase):
        self.id, self.nombre, self.cat, self.fn, self.fase = id, nombre, cat, fn, fase

REGISTRO = []
def caso(id, nombre, cat, fase="offline"):
    def deco(fn):
        REGISTRO.append(Caso(id, nombre, cat, fn, fase))
        return fn
    return deco

# ---------------------------------------------------------------- datos compartidos
class Datos:
    _c = {}
    @classmethod
    def get(cls, k, f):
        if k not in cls._c:
            t0 = time.time(); cls._c[k] = f()
            log.debug("dato compartido '%s' cargado en %.2fs", k, time.time() - t0)
        return cls._c[k]

def indice(path):
    with open(path, "rb") as f:
        mag = f.read(8); n = struct.unpack("<I", f.read(4))[0]
        ents = []
        for i in range(n):
            raw = f.read(268)
            nom = yr.swap(raw[:256]).split(b"\x00")[0].decode("latin-1")
            ents.append((nom,) + struct.unpack("<III", raw[256:268]))
    return mag, ents

def leer_entrada(path, ent):
    with open(path, "rb") as f:
        f.seek(ent[1]); return f.read(ent[3])

def cartas():
    return {int(r["id"]): r for r in csv.DictReader(open(os.path.join(BASE, "re-output", "cards.csv"), encoding="utf-8"))}

def parse_ydc(d):
    n = struct.unpack("<H", d[8:10])[0]; m = list(struct.unpack("<%dH" % n, d[10:10 + 2 * n])); q = 10 + 2 * n
    nf = struct.unpack("<H", d[q:q + 2])[0]; fu = list(struct.unpack("<%dH" % nf, d[q + 2:q + 2 + 2 * nf])); q += 2 + 2 * nf
    ns = struct.unpack("<H", d[q:q + 2])[0]; si = list(struct.unpack("<%dH" % ns, d[q + 2:q + 2 + 2 * ns])); q += 2 + 2 * ns
    return {"hdr": d[:8], "main": m, "fus": fu, "side": si, "resto": len(d) - q}

def biblioteca():
    out = {}
    for p in sorted(glob.glob(os.path.join(BASE, "biblioteca", "*.ydc"))):
        out[os.path.basename(p)] = parse_ydc(open(p, "rb").read())
    return out

def originales():
    return {os.path.basename(p): parse_ydc(open(p, "rb").read())
            for p in sorted(glob.glob(os.path.join(BASE, "datadat-extraido", "j", "file", "*.ydc")))}

def numerados():
    return yr.cargar_numerados()

ORIG = os.path.join(yr.APP, "Data.dat.original")
FULL = yr.FULL

# ================================================================ D: integridad de Data.dat
@caso("D01", "Data.dat.original: firma y conteo", "Datos")
def _(c):
    mag, ents = Datos.get("idx_orig", lambda: indice(ORIG))
    c.sub("firma KCEJYUGI", mag == b"KCEJYUGI", mag)
    c.sub("3592 entradas", len(ents) == 3592, len(ents))

@caso("D02", "Data.dat.full: firma y conteo", "Datos")
def _(c):
    mag, ents = Datos.get("idx_full", lambda: indice(FULL))
    c.sub("firma", mag == b"KCEJYUGI"); c.sub("4138 entradas", len(ents) == 4138, len(ents))

@caso("D03", "Data.dat.full: todas las entradas dentro del archivo", "Datos")
def _(c):
    _, ents = Datos.get("idx_full", lambda: indice(FULL)); tam = os.path.getsize(FULL)
    malas = [e[0] for e in ents if e[1] + e[3] > tam or e[1] < 12 + 268 * len(ents)]
    c.sub("offset+stored dentro y despues del indice", not malas, malas[:5])

@caso("D04", "Las 3592 entradas originales son identicas en .full (todas, por nombre)", "Datos")
def _(c):
    _, eo = Datos.get("idx_orig", lambda: indice(ORIG)); _, ef = Datos.get("idx_full", lambda: indice(FULL))
    pf = {e[0].lower(): e for e in ef}
    faltan = [a[0] for a in eo if a[0].lower() not in pf]
    meta = [a[0] for a in eo if a[0].lower() in pf and pf[a[0].lower()][2:] != a[2:]]
    difs = 0
    with open(ORIG, "rb") as fo, open(FULL, "rb") as ff:
        for a in eo:
            b = pf.get(a[0].lower())
            if not b: continue
            fo.seek(a[1]); ff.seek(b[1])
            if fo.read(a[3]) != ff.read(b[3]): difs += 1
    c.sub("ninguna original falta", not faltan, faltan[:3])
    c.sub("usize/stored iguales", not meta, meta[:3])
    c.sub("bytes almacenados iguales en las 3592", difs == 0, difs)

@caso("D16", "Indice ordenado por nombre (el juego usa busqueda binaria) - regresion", "Datos")
def _(c):
    for etiqueta, ruta in (("original", ORIG), ("full", FULL), ("sesion", yr.DESTINO)):
        _, e = indice(ruta)
        malos = sum(1 for a, b in zip(e, e[1:]) if a[0].lower().encode("latin-1") > b[0].lower().encode("latin-1"))
        c.sub("%s ordenado" % etiqueta, malos == 0, "%d pares desordenados" % malos)

@caso("D05", "Sin nombres duplicados en .full", "Datos")
def _(c):
    _, ef = Datos.get("idx_full", lambda: indice(FULL))
    dup = [k for k, v in collections.Counter(e[0].lower() for e in ef).items() if v > 1]
    c.sub("nombres unicos (sin distinguir mayusculas)", not dup, dup[:5])

@caso("D06", "Entradas nuevas: cpu_100..cpu_645 sin comprimir", "Datos")
def _(c):
    _, ef = Datos.get("idx_full", lambda: indice(FULL))
    _, eo = Datos.get("idx_orig", lambda: indice(ORIG))
    orig_n = set(e[0].lower() for e in eo)
    nuevas = [e for e in ef if e[0].lower() not in orig_n]
    esperados = ["j\\file\\cpu_%03d.ydc" % n for n in range(100, 646)]
    c.sub("546 nuevas", len(nuevas) == 546, len(nuevas))
    c.sub("nombres esperados", sorted(e[0].lower() for e in nuevas) == esperados)
    c.sub("todas raw (usize == stored)", all(e[2] == e[3] for e in nuevas))

@caso("D07", "Cada mazo embebido es identico al archivo de la biblioteca", "Datos")
def _(c):
    _, ef = Datos.get("idx_full", lambda: indice(FULL)); nums = Datos.get("num", numerados)
    por_nombre = {e[0].lower(): e for e in ef}; malos = []
    for m in nums:
        e = por_nombre.get("j\\file\\cpu_%03d.ydc" % m["numero"])
        if not e or leer_entrada(FULL, e) != open(os.path.join(BASE, "biblioteca", m["archivo"]), "rb").read():
            malos.append(m["numero"])
    c.sub("546 identicos", not malos, malos[:8])

@caso("D08", "Data.dat de sesion: 37 ful_* parcheados con cabecera original", "Datos")
def _(c):
    _, es = indice(yr.DESTINO); tam = os.path.getsize(yr.DESTINO)
    fuls = [e for e in es if "\\ful_" in e[0].lower()]
    c.sub("37 slots ful", len(fuls) == 37, len(fuls))
    malos_hdr, malos_lugar = [], []
    for e in fuls:
        nuevo = leer_entrada(yr.DESTINO, e)
        orig = open(os.path.join(yr.SLOTS_DIR, e[0].split("\\")[-1].lower()), "rb").read()
        if nuevo[:8] != orig[:8]: malos_hdr.append(e[0])
        if e[1] < os.path.getsize(FULL): malos_lugar.append(e[0])
        parse_ydc(nuevo)
    c.sub("cabecera de 8 B del slot preservada", not malos_hdr, malos_hdr[:3])
    c.sub("datos anexados al final (despues de .full)", not malos_lugar, malos_lugar[:3])
    c.sub("fin del archivo coherente", max(e[1] + e[3] for e in es) == tam)

@caso("D09", "Data.dat de sesion: el resto de entradas igual a .full", "Datos")
def _(c):
    _, es = indice(yr.DESTINO); _, ef = Datos.get("idx_full", lambda: indice(FULL))
    difs = [a[0] for a, b in zip(es, ef) if "\\ful_" not in a[0].lower() and a != b]
    c.sub("4101 entradas sin cambios", not difs, difs[:5])

@caso("D10", "LZSS: las 205 entradas comprimidas descomprimen al tamano declarado", "Datos")
def _(c):
    sys.path.insert(0, os.path.join(BASE, "re-scripts"))
    import analisis_total as at
    _, eo = Datos.get("idx_orig", lambda: indice(ORIG))
    comp = [e for e in eo if e[2] != e[3]]
    c.sub("205 comprimidas", len(comp) == 205, len(comp))
    malas = []
    for e in comp:
        d = at.lzss(leer_entrada(ORIG, e), e[2])
        if len(d) != e[2]: malas.append((e[0], len(d), e[2]))
    c.sub("todas al tamano exacto", not malas, malas[:3])
    ref = os.path.join(BASE, "datadat-extraido", "bin#", "card_nameeng.bin")
    e = next(x for x in comp if x[0].lower().endswith("card_nameeng.bin"))
    if os.path.exists(ref):
        c.sub("card_nameeng.bin identico al extraido", at.lzss(leer_entrada(ORIG, e), e[2]) == open(ref, "rb").read())

@caso("D11", "Nombres internos sin caracteres de control (regresion del bug \\f)", "Datos")
def _(c):
    _, ef = Datos.get("idx_full", lambda: indice(FULL))
    malos = [e[0] for e in ef if any(ord(ch) < 32 for ch in e[0])]
    c.sub("ningun nombre con control", not malos, malos[:3])
    c.sub("separador '\\\\' en carpetas", all("/" not in e[0] for e in ef))

@caso("D12", "lista_nuevos.txt coherente con .full", "Datos")
def _(c):
    lineas = [l.split(";") for l in open(os.path.join(yr.LAUNCHER, "lista_nuevos.txt"), encoding="utf-8").read().splitlines() if l]
    _, ef = Datos.get("idx_full", lambda: indice(FULL))
    c.sub("546 lineas", len(lineas) == 546, len(lineas))
    nombres = set(e[0].lower() for e in ef)
    c.sub("todas las lineas existen en el indice", all(l[0].lower() in nombres for l in lineas))
    c.sub("rutas locales existen", all(os.path.exists(l[1]) for l in lineas))

@caso("D13", "biblioteca_numeros.csv valido", "Datos")
def _(c):
    nums = Datos.get("num", numerados)
    ns = [m["numero"] for m in nums]
    c.sub("546 filas", len(nums) == 546, len(nums))
    c.sub("numeros 100..645 unicos", sorted(ns) == list(range(100, 646)))
    c.sub("archivos existen", all(os.path.exists(os.path.join(BASE, "biblioteca", m["archivo"])) for m in nums))
    c.sub("tiers 0-3", all(0 <= m["tier"] <= 3 for m in nums))

@caso("D14", "manifest.csv coherente con la biblioteca", "Datos")
def _(c):
    man = list(csv.DictReader(open(os.path.join(BASE, "biblioteca", "manifest.csv"), encoding="utf-8")))
    arch = set(os.path.basename(p) for p in glob.glob(os.path.join(BASE, "biblioteca", "*.ydc")))
    col = next(k for k in man[0] if "arch" in k.lower() or "file" in k.lower())
    c.sub("una fila por mazo", set(r[col] for r in man) == arch, len(man))

@caso("D15", "Archivos auxiliares del juego presentes y legibles", "Datos")
def _(c):
    for n in ("Joey_Pc.exe", "Voice.dat", "Region.dat", "Deck.ydc"):
        p = os.path.join(yr.APP, n)
        c.sub(n, os.path.exists(p) and os.path.getsize(p) > 0, os.path.getsize(p) if os.path.exists(p) else None)
    c.sub("Deck.ydc parsea", parse_ydc(open(os.path.join(yr.APP, "Deck.ydc"), "rb").read())["resto"] == 0)

# ================================================================ M: reglas de la biblioteca
def _bib(): return Datos.get("bib", biblioteca)
def _car(): return Datos.get("car", cartas)
def _es_mon(r): return r["tipo"] not in ("Magic", "Trap")

@caso("M01", "Los 546 mazos parsean sin bytes sobrantes", "Mazos")
def _(c):
    b = _bib(); c.sub("546 archivos", len(b) == 546, len(b))
    c.sub("sin bytes sobrantes", all(d["resto"] == 0 for d in b.values()))

@caso("M02", "Tamano del mazo principal 40-45 (rango de los originales)", "Mazos")
def _(c):
    malos = {k: len(d["main"]) for k, d in _bib().items() if not 40 <= len(d["main"]) <= 45}
    c.sub("todos en rango", not malos, list(malos.items())[:5])

@caso("M03", "Maximo 3 copias por nombre (artes alternos agrupados)", "Mazos")
def _(c):
    car = _car(); malos = []
    for k, d in _bib().items():
        cnt = collections.Counter(car[x]["nombre"] for x in d["main"] + d["side"] if x in car)
        if cnt and max(cnt.values()) > 3: malos.append((k, cnt.most_common(1)))
    c.sub("ningun nombre con mas de 3", not malos, malos[:3])

@caso("M04", "Ningun mazo usa el id centinela 0", "Mazos")
def _(c):
    c.sub("sin id 0", not [k for k, d in _bib().items() if 0 in d["main"] + d["fus"] + d["side"]])

@caso("M05", "Sin dioses egipcios ni cartas especiales", "Mazos")
def _(c):
    car = _car()
    malos = [k for k, d in _bib().items() for x in d["main"] + d["fus"] + d["side"]
             if x in car and car[x]["tipo"] in ("Divino", "Especial")]
    c.sub("ninguna", not malos, malos[:3])

@caso("M06", "Todos los ids existen en la base de cartas", "Mazos")
def _(c):
    car = _car()
    malos = [(k, x) for k, d in _bib().items() for x in d["main"] + d["fus"] + d["side"] if x not in car]
    c.sub("ids conocidos", not malos, malos[:5])

@caso("M07", "Sin monstruos de fusion en el mazo principal", "Mazos")
def _(c):
    car = _car()
    malos = [(k, car[x]["nombre"]) for k, d in _bib().items() for x in d["main"]
             if x in car and _es_mon(car[x]) and car[x]["clase"] == "Fusion"]
    orig = [(k, car[x]["nombre"]) for k, d in Datos.get("orig", originales).items() for x in d["main"]
            if x in car and _es_mon(car[x]) and car[x]["clase"] == "Fusion"]
    c.sub("biblioteca sin fusiones en main", not malos, malos[:3])
    c.sub("(referencia) originales tampoco", not orig, orig[:3])

@caso("M08", "El mazo de fusion solo contiene monstruos de fusion", "Mazos")
def _(c):
    car = _car()
    malos = [(k, x) for k, d in _bib().items() for x in d["fus"] if not (x in car and car[x]["clase"] == "Fusion")]
    c.sub("solo fusiones", not malos, malos[:3])

@caso("M09", "Side deck con ids validos y <= 15", "Mazos")
def _(c):
    car = _car()
    c.sub("side <= 15", all(len(d["side"]) <= 15 for d in _bib().values()))
    c.sub("ids validos", all(x in car for d in _bib().values() for x in d["side"]))

@caso("M10", "Cabecera: byte 0x01 y float de fuerza finito", "Mazos")
def _(c):
    malos = []
    for k, d in _bib().items():
        f = struct.unpack("<f", d["hdr"][4:8])[0]
        if d["hdr"][0] != 1 or not math.isfinite(f): malos.append(k)
    c.sub("cabeceras validas", not malos, malos[:3])

@caso("M11", "ATK medio de monstruos <= 1467 (maximo de los mazos originales)", "Mazos")
def _(c):
    car = _car(); malos = []
    for k, d in _bib().items():
        atks = [int(car[x]["atk"]) for x in d["main"] if x in car and _es_mon(car[x])]
        prom = sum(atks) / max(1, len(atks))
        if prom > 1467: malos.append((k, round(prom)))
    c.sub("ningun mazo por encima de 1467", not malos, malos[:5])

@caso("M12", "Maximo 7 monstruos de tributo (nivel >= 5)", "Mazos")
def _(c):
    car = _car()
    malos = [(k, n) for k, d in _bib().items()
             for n in [sum(1 for x in d["main"] if x in car and _es_mon(car[x]) and int(car[x]["nivel"] or 0) >= 5)] if n > 7]
    c.sub("<= 7", not malos, malos[:5])

@caso("M13", "Al menos 19 monstruos (minimo de los originales)", "Mazos")
def _(c):
    car = _car()
    malos = [(k, n) for k, d in _bib().items() for n in [sum(1 for x in d["main"] if x in car and _es_mon(car[x]))] if n < 19]
    c.sub(">= 19", not malos, malos[:5])

@caso("M14", "Al menos 8 magicas+trampas", "Mazos")
def _(c):
    car = _car()
    malos = [(k, n) for k, d in _bib().items() for n in [sum(1 for x in d["main"] if x in car and not _es_mon(car[x]))] if n < 8]
    c.sub(">= 8", not malos, malos[:5])

@caso("M15", "Biblioteca sin cartas ocultas y cobertura >= 700 de las 768 jugables", "Mazos")
def _(c):
    # ocultas = CARD_Pack & 7 == 0 (sin edicion ni ilustracion, el juego las dibuja como Slime Token); se quitaron
    # el 2026-10-16 con re-scripts/quitar_ocultas.py. Antes el umbral era >= 1000 nombres contando las ocultas.
    car = _car()
    pack = open(os.path.join(BASE, "datadat-extraido", "bin#", "card_pack.bin"), "rb").read()
    oculta = {i for i, r in car.items() if r["idx"].isdigit()
              and not int.from_bytes(pack[2 * int(r["idx"]):2 * int(r["idx"]) + 2], "little") & 7}
    todas = [x for d in _bib().values() for x in d["main"] + d["fus"] + d.get("side", [])]
    c.sub("ninguna carta oculta", not any(x in oculta for x in todas), sorted({car[x]["nombre"] for x in todas if x in oculta})[:5])
    usados = set(car[x]["nombre"] for x in todas if x in car)
    c.sub(">= 700 nombres", len(usados) >= 700, len(usados))

@caso("M16", "Distribucion por tier esperada {0:103,1:157,2:158,3:128}", "Mazos")
def _(c):
    cnt = collections.Counter(m["tier"] for m in Datos.get("num", numerados))
    c.sub("distribucion", dict(cnt) == {0: 103, 1: 157, 2: 158, 3: 128}, dict(cnt))

@caso("M17", "Cada temperamento tiene mazos (y cuantos por tier)", "Mazos")
def _(c):
    nums = Datos.get("num", numerados)
    for g in yr.GRUPOS:
        por_t = collections.Counter(m["tier"] for m in nums if m["grupo"] == g)
        c.sub("%s presente" % g, sum(por_t.values()) > 0, dict(sorted(por_t.items())))

@caso("M18", "Blue-Eyes aparece con id 2000 (no con el centinela)", "Mazos")
def _(c):
    con = [k for k, d in _bib().items() if 2000 in d["main"]]
    c.sub("hay mazos con Blue-Eyes (2000)", len(con) > 0, len(con))

@caso("M19", "Mazos Exodia contienen las 5 piezas", "Mazos")
def _(c):
    car = _car(); nums = Datos.get("num", numerados)
    piezas = {"Exodia the Forbidden One", "Right Arm of the Forbidden One", "Left Arm of the Forbidden One",
              "Right Leg of the Forbidden One", "Left Leg of the Forbidden One"}
    ex = [m["archivo"] for m in nums if m["arquetipo"] == "Exodia"]
    c.sub("hay mazos Exodia", len(ex) > 0, len(ex))
    for k in ex:
        nombres = set(car[x]["nombre"] for x in _bib()[k]["main"] if x in car)
        c.sub(k, piezas <= nombres, sorted(piezas - nombres))

@caso("M20", "Sin mazos duplicados exactos", "Mazos")
def _(c):
    firmas = collections.Counter(tuple(sorted(d["main"])) + ("|",) + tuple(sorted(d["fus"])) for d in _bib().values())
    c.sub("todos distintos", max(firmas.values()) == 1, max(firmas.values()))

# ================================================================ L: lanzador (unitarias)
@caso("L01", "swap es involucion en los 256 bytes", "Lanzador")
def _(c):
    b = bytes(range(256)); c.sub("swap(swap(x)) == x", yr.swap(yr.swap(b)) == b)
    c.sub("ejemplo 0x4A -> 0xA4", yr.swap(b"\x4a") == b"\xa4")

@caso("L02", "tier_de para slots cpu_0XY y ful_N", "Lanzador")
def _(c):
    c.sub("cpu_000..004 -> 0", all(yr.tier_de("cpu_%03d" % i) == 0 for i in range(5)))
    c.sub("cpu_010..015 -> 1", all(yr.tier_de("cpu_%03d" % i) == 1 for i in range(10, 16)))
    c.sub("cpu_020..029 -> 2", all(yr.tier_de("cpu_%03d" % i) == 2 for i in range(20, 30)))
    c.sub("ful_3exo -> 3", yr.tier_de("ful_3exo") == 3)

def _tmp(nombre):
    d = tempfile.mkdtemp(prefix="yr_"); return os.path.join(d, nombre)

@caso("L03", "cargar_historial sin archivo -> nivel 0", "Lanzador")
def _(c):
    h = yr.cargar_historial(_tmp("no_existe.json"))
    c.sub("nivel 0", h["nivel"] == 0.0, h); c.sub("lista vacia", h["resultados"] == [])

@caso("L04", "cargar_historial con JSON corrupto -> reinicio", "Lanzador")
def _(c):
    p = _tmp("h.json"); open(p, "w").write("{esto no es json")
    h = yr.cargar_historial(p); c.sub("nivel 0", h["nivel"] == 0.0, h)

@caso("L05", "cargar_historial acota nivel a [-1, 2]", "Lanzador")
def _(c):
    for v, esp in ((9.5, 2.0), (-7, -1.0), (0.68, 0.68)):
        p = _tmp("h.json"); json.dump({"nivel": v, "resultados": []}, open(p, "w"))
        c.sub("nivel %s -> %s" % (v, esp), abs(yr.cargar_historial(p)["nivel"] - esp) < 1e-9)

@caso("L06", "cargar_historial con tipo invalido (lista) -> reinicio", "Lanzador")
def _(c):
    p = _tmp("h.json"); json.dump([1, 2, 3], open(p, "w"))
    c.sub("nivel 0", yr.cargar_historial(p)["nivel"] == 0.0)

@caso("L07", "registrar_resultado: +0.34 / -0.34", "Lanzador")
def _(c):
    p = _tmp("h.json"); h = {"nivel": 0.0, "resultados": []}
    c.sub("victoria +0.34", abs(yr.registrar_resultado(h, "g", p) - 0.34) < 1e-9)
    c.sub("derrota vuelve a 0", abs(yr.registrar_resultado(h, "p", p)) < 1e-9)
    c.sub("persistido", json.load(open(p))["resultados"] == ["g", "p"])

@caso("L08", "registrar_resultado: tope superior 2.0", "Lanzador")
def _(c):
    p = _tmp("h.json"); h = {"nivel": 1.9, "resultados": []}
    for _ in range(5): yr.registrar_resultado(h, "g", p)
    c.sub("== 2.0", h["nivel"] == 2.0, h["nivel"])

@caso("L09", "registrar_resultado: tope inferior -1.0", "Lanzador")
def _(c):
    p = _tmp("h.json"); h = {"nivel": -0.5, "resultados": []}
    for _ in range(5): yr.registrar_resultado(h, "p", p)
    c.sub("== -1.0", h["nivel"] == -1.0, h["nivel"])

@caso("L10", "registrar_resultado: escritura atomica", "Lanzador")
def _(c):
    p = _tmp("h.json"); h = {"nivel": 0.0, "resultados": []}
    for i in range(20): yr.registrar_resultado(h, "g" if i % 2 else "p", p)
    c.sub("sin .tmp residual", not os.path.exists(p + ".tmp"))
    c.sub("JSON valido con 20 resultados", len(json.load(open(p))["resultados"]) == 20)

@caso("L11", "perfil_jugador con Deck.ydc real", "Lanzador")
def _(c):
    dom, atk = yr.perfil_jugador()
    c.sub("ATK promedio plausible", 500 < atk < 3000, atk)
    c.sub("dominante None o tipo valido", dom is None or isinstance(dom, str), dom)

@caso("L12", "perfil_jugador con mazo inexistente no lanza excepcion", "Lanzador")
def _(c):
    c.sub("(None, 0)", yr.perfil_jugador(_tmp("no.ydc")) == (None, 0))

@caso("L13", "peso(): multiplicadores", "Lanzador")
def _(c):
    c.sub("sin dominante = 1", yr.peso({"arquetipo": "quemadura"}, None, 1600) == 1.0)
    c.sub("quemadura vs ATK alto = 2.2", abs(yr.peso({"arquetipo": "quemadura"}, "Warrior", 1600) - 2.2) < 1e-9)
    c.sub("espejo tribal = 1.5", abs(yr.peso({"arquetipo": "tribal Warrior"}, "Warrior", 1000) - 1.5) < 1e-9)
    c.sub("control de mano = 1.6", abs(yr.peso({"arquetipo": "control de mano"}, "Warrior", 1000) - 1.6) < 1e-9)

@caso("L14", "grupo_de: cada arquetipo de la biblioteca cae en su temperamento", "Lanzador")
def _(c):
    arqs = sorted(set(m["arquetipo"] for m in Datos.get("num", numerados)))
    for a in arqs:
        g = yr.grupo_de(a)
        esperado_agresivo = a.startswith("tribal") or a.startswith("atributo")
        c.sub(a, g in yr.GRUPOS and (g != "agresivo" or esperado_agresivo), g)

def _sel(nivel=0.0, seed=1):
    return yr.Selector(Datos.get("num", numerados), nivel, rng=random.Random(seed))

@caso("L15", "Tabla: 40 valores, indices 0-4 = 0..4", "Lanzador")
def _(c):
    s = _sel()
    for t in yr.GRUPOS:
        tb = s.tabla(t); c.sub(t, len(tb) == 40 and tb[:5] == [0, 1, 2, 3, 4], tb[:6])

@caso("L16", "Tabla: todos los numeros existen en Data.dat.full", "Lanzador")
def _(c):
    _, ef = Datos.get("idx_full", lambda: indice(FULL))
    validos = set(int(e[0][-7:-4]) for e in ef if e[0].lower().startswith("j\\file\\cpu_"))
    s = _sel(); malos = []
    for i in range(300):
        for x in s.tabla(s.sortear_temperamento())[5:]:
            if x not in validos: malos.append(x)
    c.sub("300 tablas sin numeros invalidos", not malos, malos[:5])

@caso("L17", "Tabla: tier correcto por nivel con nivel elastico -1/0/1/2", "Lanzador")
def _(c):
    nums = {m["numero"]: m for m in Datos.get("num", numerados)}
    for nv_el in (-1.0, 0.0, 1.0, 2.0):
        s = _sel(nv_el, 7); fuera = 0; total = 0
        for _ in range(100):
            tb = s.tabla(s.sortear_temperamento())
            for nv in range(1, 8):
                esp = max(0, min(3, yr.NIVEL_A_TIER[nv] + int(round(nv_el))))
                for x in tb[nv * 5:nv * 5 + 5]:
                    if x in nums:
                        total += 1; fuera += abs(nums[x]["tier"] - esp) > 1
        c.sub("nivel %+.0f: tier dentro de +-1" % nv_el, fuera == 0, "%d/%d fuera" % (fuera, total))

@caso("L18", "Tabla: coherencia de temperamento en los niveles donde es elegible", "Lanzador")
def _(c):
    nums = {m["numero"]: m for m in Datos.get("num", numerados)}; s = _sel(0.0, 3)
    for t in yr.GRUPOS:
        tot = ok = 0
        for nv in range(1, 8):
            if t not in s.elegibles(nv): continue
            for _ in range(40):
                for x in s.tabla(t)[nv * 5:nv * 5 + 5]:
                    if x in nums: tot += 1; ok += nums[x]["grupo"] == t
        c.sub(t, tot > 0 and ok / tot >= 0.8, "%.0f%% coherente (%d entradas)" % (100.0 * ok / max(1, tot), tot))

@caso("L31", "Sorteo consciente del nivel: solo temperamentos elegibles", "Lanzador")
def _(c):
    s = _sel(0.0, 21)
    for nv in range(0, 8):
        ok = s.elegibles(nv); vistos = set(s.sortear_temperamento(nv) for _ in range(400))
        c.sub("nivel %d -> %s" % (nv, ",".join(sorted(vistos))), vistos <= set(ok) and len(ok) >= 3, ok)
    c.sub("legendario no sale en nivel 1", "legendario" not in s.elegibles(1))

@caso("L19", "Tabla: tasa de nostalgia ~10%", "Lanzador")
def _(c):
    s = _sel(0.0, 11); tot = orig = 0
    for _ in range(1000):
        for x in s.tabla(s.sortear_temperamento())[5:]:
            tot += 1; orig += x < 100
    tasa = orig / tot
    c.sub("entre 8% y 12%", 0.08 <= tasa <= 0.12, "%.2f%%" % (100 * tasa))

@caso("L20", "Tabla: sin repetidos en una fila cuando el pool alcanza (regresion)", "Lanzador")
def _(c):
    s = _sel(0.0, 5); rep = filas = 0
    for _ in range(300):
        tb = s.tabla(s.sortear_temperamento())
        for nv in range(1, 8):
            fila = [x for x in tb[nv * 5:nv * 5 + 5] if x >= 100]
            filas += 1; rep += len(fila) != len(set(fila))
    c.sub("filas con repetidos <= 2%", rep / filas <= 0.02, "%d de %d" % (rep, filas))

@caso("L21", "Sorteo de temperamentos proporcional a los pesos", "Lanzador")
def _(c):
    s = _sel(0.0, 99); cnt = collections.Counter(s.sortear_temperamento() for _ in range(20000))
    tot = sum(yr.PESOS_GRUPO)
    for g, w in zip(yr.GRUPOS, yr.PESOS_GRUPO):
        c.sub(g, abs(cnt[g] / 20000 - w / tot) < 0.015, "%.3f vs %.3f" % (cnt[g] / 20000, w / tot))

@caso("L22", "Diales por temperamento segun la tabla DIALES", "Lanzador")
def _(c):
    s = _sel()
    for g in yr.GRUPOS:
        if g != "caotico": c.sub(g, s.diales(g) == yr.DIALES[g], s.diales(g))

@caso("L23", "Diales del caotico dentro de rango", "Lanzador")
def _(c):
    s = _sel(0.0, 4); vals = [s.diales("caotico") for _ in range(500)]
    c.sub("umbral en [-128,127]", all(-128 <= u <= 127 for u, a in vals))
    c.sub("ATK en lista", all(a in (300, 500, 700, 900, 1100, 1300, 1600) for u, a in vals))
    c.sub("varian entre duelos", len(set(vals)) > 50, len(set(vals)))

@caso("L24", "bytes_ataque: codificacion correcta para -128..127", "Lanzador")
def _(c):
    malos = []
    for u in range(-128, 128):
        b = yr.bytes_ataque(u)
        if len(b) != 9 or b[:4] != bytes.fromhex("66894502") or b[4:6] != b"\x83\xf8" or \
           struct.unpack("<b", b[6:7])[0] != u or b[7:] != b"\x7f\x1b":
            malos.append(u)
    c.sub("256 umbrales correctos", not malos, malos[:5])

@caso("L25", "bytes_ataque(None) y bytes_invocar(None) == bytes del exe en disco", "Lanzador")
def _(c):
    d = open(yr.EXE, "rb").read()
    c.sub("dial ataque original", d[yr.DIAL_ATAQUE - 0x400000:][:9] == yr.bytes_ataque(None))
    c.sub("dial invocar original", d[yr.DIAL_INVOCAR - 0x400000:][:5] == yr.bytes_invocar(None))

@caso("L26", "bytes_invocar codifica el inmediato", "Lanzador")
def _(c):
    for v in (0, 500, 900, 1400, 3000, 65535):
        b = yr.bytes_invocar(v); c.sub(str(v), len(b) == 5 and b[0] == 0x3D and struct.unpack("<I", b[1:])[0] == v)

@caso("L27", "parchear_fuls a destino temporal: 37 aplicados y determinista", "Lanzador")
def _(c):
    d1, d2 = _tmp("a.dat"), _tmp("b.dat"); s1, s2 = _tmp("s1.txt"), _tmp("s2.txt")
    n = yr.parchear_fuls(Datos.get("num", numerados), 0.0, rng=random.Random(42), destino=d1, ruta_sel=s1)
    yr.parchear_fuls(Datos.get("num", numerados), 0.0, rng=random.Random(42), destino=d2, ruta_sel=s2)
    c.sub("37 aplicados", n == 37, n)
    c.sub("misma semilla -> misma seleccion", open(s1).read() == open(s2).read())
    for p in (d1, d2): os.remove(p)

@caso("L28", "parchear_fuls: ningun mazo repetido entre slots", "Lanzador")
def _(c):
    d, s = _tmp("a.dat"), _tmp("s.txt")
    yr.parchear_fuls(Datos.get("num", numerados), 1.0, rng=random.Random(8), destino=d, ruta_sel=s)
    usados = [l.split("<-")[1].split("(")[0].strip() for l in open(s, encoding="utf-8").read().splitlines()]
    c.sub("37 distintos", len(usados) == 37 and len(set(usados)) == 37, len(set(usados)))
    os.remove(d)

@caso("L29", "main --solo-parchear y paso de argumentos con --", "Lanzador")
def _(c):
    r = subprocess.run([sys.executable, "-I", os.path.join(yr.LAUNCHER, "yugi_reload.py"), "--solo-parchear", "--", "-win"],
                       capture_output=True, text=True, timeout=600, cwd=yr.LAUNCHER)
    c.sub("codigo 0", r.returncode == 0, r.returncode)
    c.sub("salida informa 37 ful", "rebarajados: 37" in r.stdout, r.stdout[-300:])
    c.sub("sin traceback", "Traceback" not in r.stderr, r.stderr[-300:])

@caso("L30", "main sin Data.dat.full devuelve 2", "Lanzador")
def _(c):
    viejo, viejo_cfg = yr.FULL, yr.configurar_log
    yr.FULL = _tmp("no_hay_full.dat")
    yr.configurar_log = lambda consola=True: RUTA_LOG  # que main() no reemplace el log de la bateria
    try:
        c.sub("codigo 2", yr.main(["--solo-parchear"]) == 2)
    finally:
        yr.FULL, yr.configurar_log = viejo, viejo_cfg

# ================================================================ S: memoria simulada
class MemFalsa:
    """Imita Memoria sobre un diccionario de bytes; permite inyectar estados y fallos."""
    def __init__(self, pid=0):
        self.b = {}; self.falla_lectura = False; self.escrituras = []
        exe = open(yr.EXE, "rb").read()
        self.poner(yr.DIAL_ATAQUE, exe[yr.DIAL_ATAQUE - 0x400000:][:9])
        self.poner(yr.DIAL_INVOCAR, exe[yr.DIAL_INVOCAR - 0x400000:][:5])
        self.poner(yr.RUTA_CPU, exe[yr.RUTA_CPU - 0x400000:][:6])
        self.poner(yr.TABLA_CPU, struct.pack("<40I", *range(40)))
        self.poner(yr.ADDR_GANADOR, bytes(5))
        for a in yr.ADDR_LP: self.poner(a, b"\x40\x1f")
    def poner(self, a, data):
        for i, x in enumerate(data): self.b[a + i] = x
    def leer(self, a, n):
        if self.falla_lectura: return None
        return bytes(self.b.get(a + i, 0) for i in range(n))
    def escribir(self, a, data, etiqueta=""):
        self.poner(a, data); self.escrituras.append((a, bytes(data), etiqueta)); return True
    def cerrar(self): pass
    def estado(self, g, r, n):
        self.poner(yr.ADDR_GANADOR, bytes([g, r, 0, 0, n]))

class ProcFalso:
    pid = 0
    def __init__(self): self.vivo = True
    def poll(self): return None if self.vivo else 0

def _vigilante(mem):
    h = {"nivel": 0.0, "resultados": []}
    v = yr.Vigilante(ProcFalso(), _sel(0.0, 2), h, ruta_historial=_tmp("h.json"),
                     memoria_factory=lambda pid: mem, espera_inicial=0.0, refresco=0.05)
    t = threading.Thread(target=v.correr, name="vig-falso", daemon=True); t.start()
    time.sleep(0.3)
    return v, t

def _parar(v, t):
    v.detener.set(); v.proc.vivo = False; t.join(3)

@caso("S01", "aplicar_diales sobre codigo original", "Memoria simulada")
def _(c):
    m = MemFalsa(); ok = yr.aplicar_diales(m, -100, 500)
    c.sub("devuelve True", ok); c.sub("ataque", m.leer(yr.DIAL_ATAQUE, 9) == yr.bytes_ataque(-100))
    c.sub("invocar", m.leer(yr.DIAL_INVOCAR, 5) == yr.bytes_invocar(500))

@caso("S02", "aplicar_diales sobre un parche previo", "Memoria simulada")
def _(c):
    m = MemFalsa(); yr.aplicar_diales(m, -100, 500); ok = yr.aplicar_diales(m, 127, 1400)
    c.sub("re-parcheo aceptado", ok); c.sub("valor nuevo", m.leer(yr.DIAL_ATAQUE, 9) == yr.bytes_ataque(127))

@caso("S03", "aplicar_diales rechaza bytes desconocidos", "Memoria simulada")
def _(c):
    m = MemFalsa(); m.poner(yr.DIAL_ATAQUE, b"\x90" * 9); m.poner(yr.DIAL_INVOCAR, b"\x90" * 5)
    n0 = len(m.escrituras); ok = yr.aplicar_diales(m, -100, 500)
    c.sub("devuelve False", not ok); c.sub("no escribio nada", len(m.escrituras) == n0)

@caso("S04", "aplicar_diales(None, None) restaura el original exacto", "Memoria simulada")
def _(c):
    m = MemFalsa(); orig = (m.leer(yr.DIAL_ATAQUE, 9), m.leer(yr.DIAL_INVOCAR, 5))
    yr.aplicar_diales(m, -128, 0); yr.aplicar_diales(m, None, None)
    c.sub("identico", (m.leer(yr.DIAL_ATAQUE, 9), m.leer(yr.DIAL_INVOCAR, 5)) == orig)

@caso("S05", "escribir_tabla / leer_tabla ida y vuelta", "Memoria simulada")
def _(c):
    m = MemFalsa(); t = [0, 1, 2, 3, 4] + list(range(100, 135))
    c.sub("escritura", yr.escribir_tabla(m, t)); c.sub("lectura igual", yr.leer_tabla(m) == t)

@caso("L32", "escribir_tabla no toca la tabla FUL vecina (regresion)", "Memoria simulada")
def _(c):
    m = MemFalsa(); cola = bytes(range(0xA0, 0xB4)); m.poner(yr.TABLA_CPU, cola)
    yr.escribir_tabla(m, [0, 1, 2, 3, 4] + list(range(200, 235)))
    c.sub("20 bytes de 0x5DB158 intactos", m.leer(yr.TABLA_CPU, 20) == cola)
    c.sub("primera direccion escrita = 0x5DB16C", min(a for a, d, e in m.escrituras if "tabla" in e) == 0x5DB16C)
    c.sub("se escriben 140 bytes", all(len(d) == 140 for a, d, e in m.escrituras if "tabla" in e))

@caso("S06", "Vigilante: victoria detectada", "Memoria simulada")
def _(c):
    m = MemFalsa(); v, t = _vigilante(m); m.estado(1, 1, 1); time.sleep(0.4); _parar(v, t)
    c.sub("registro 'g'", v.resultados == ["g"], v.resultados); c.sub("nivel +0.34", abs(v.hist["nivel"] - 0.34) < 1e-9)

@caso("S07", "Vigilante: derrota detectada", "Memoria simulada")
def _(c):
    m = MemFalsa(); v, t = _vigilante(m); m.estado(2, 1, 1); time.sleep(0.4); _parar(v, t)
    c.sub("registro 'p'", v.resultados == ["p"], v.resultados)

@caso("S08", "Vigilante: victorias seguidas con cambio de nivel y racha a 0", "Memoria simulada")
def _(c):
    m = MemFalsa(); v, t = _vigilante(m)
    for est in ((1, 0, 2), (1, 0, 3), (1, 0, 4)):
        m.estado(*est); time.sleep(0.3)
    _parar(v, t)
    c.sub("3 victorias", v.resultados == ["g", "g", "g"], v.resultados)

@caso("S09", "Vigilante: sin cambios de estado no registra", "Memoria simulada")
def _(c):
    m = MemFalsa(); m.estado(1, 3, 2); v, t = _vigilante(m); time.sleep(0.5); _parar(v, t)
    c.sub("nada registrado", v.resultados == [], v.resultados)

@caso("S10", "Vigilante: ganador 0 se ignora", "Memoria simulada")
def _(c):
    m = MemFalsa(); v, t = _vigilante(m); m.estado(0, 5, 1); time.sleep(0.4); _parar(v, t)
    c.sub("nada registrado", v.resultados == [])

@caso("S11", "Vigilante: tras cada duelo re-sortea y reescribe tabla y diales", "Memoria simulada")
def _(c):
    m = MemFalsa(); v, t = _vigilante(m); n0 = len(m.escrituras); m.estado(1, 1, 1); time.sleep(0.4); _parar(v, t)
    etiquetas = [e[2] for e in m.escrituras[n0:]]
    c.sub("reescribio tabla", any("tabla" in e for e in etiquetas), etiquetas)
    c.sub("reescribio diales", sum("dial" in e for e in etiquetas) >= 2, etiquetas)
    c.sub("tabla en memoria = tabla actual", yr.leer_tabla(m) == v.tabla_actual)

@caso("S12", "Vigilante: tabla alterada por fuera se restaura", "Memoria simulada")
def _(c):
    m = MemFalsa(); v, t = _vigilante(m); m.poner(yr.TABLA_CPU, struct.pack("<40I", *([7] * 40))); time.sleep(0.4); _parar(v, t)
    c.sub("restaurada", yr.leer_tabla(m) == v.tabla_actual)

@caso("S13", "Vigilante: fallos de lectura no rompen el bucle", "Memoria simulada")
def _(c):
    m = MemFalsa(); v, t = _vigilante(m); m.falla_lectura = True; time.sleep(0.3); m.falla_lectura = False
    m.estado(1, 1, 1); time.sleep(0.4); _parar(v, t)
    c.sub("sigue vivo y detecta despues", v.resultados == ["g"], v.resultados); c.sub("sin errores contados", v.errores == 0, v.errores)

@caso("S14", "Memoria(pid inexistente) lanza OSError controlado", "Memoria simulada")
def _(c):
    try:
        yr.Memoria(4); c.sub("lanzo OSError", False, "no lanzo")
    except OSError as e:
        c.sub("lanzo OSError", True, e)

# ================================================================ P: partida guardada (sobre copias)
sys.path.insert(0, os.path.join(BASE, "re-scripts"))
import partida_poc as pp
import desbloquear_cartas as dc
SAVE_REAL = os.path.join(BASE, "juego-extraido", "Yu-Gi-Oh! Power of Chaos Common", "system.dat")

def _save():
    return open(SAVE_REAL, "rb").read()

@caso("P01", "Codec del save: decodificar + recodificar reproduce el archivo exacto", "Partida")
def _(c):
    f = _save(); p = pp.decodificar(f)
    n = pp.codificar(p, len(f)); n[:4] = pp.cabecera(n, pp.TAM_PLANO)
    c.sub("ida y vuelta byte a byte", bytes(n) == f, len(f))
    c.sub("cabecera recalculada == archivo", pp.cabecera(f, pp.TAM_PLANO) == f[:4], f[:4].hex())

@caso("P02", "Save actual: magic 0xFBA5 y suma de control validos", "Partida")
def _(c):
    p = pp.decodificar(_save())
    c.sub("suma OK", pp.suma_ok(p[8:8 + pp.TAM_PLANO]))
    c.sub("prefijo ID de 8 bytes no vacio", any(p[:8]), p[:8].hex())

@caso("P03", "RSA de juguete: los 256 bytes cifran y descifran (e=5, d=53, n=299)", "Partida")
def _(c):
    c.sub("biyeccion 0..255", all(pp._descifrar_val(pp._cifrar_byte(b)) == b for b in range(256)))
    c.sub("todos caben en 9 bits", all(pp._cifrar_byte(b) < 512 for b in range(256)))

@caso("P04", "Desbloqueo sobre copia: 3 copias, vistas, mazo intacto, verificado", "Partida")
def _(c):
    antes = pp.coleccion(pp.decodificar(_save())[8:])
    nuevo, r = dc.desbloquear(_save(), 3)
    col = pp.coleccion(pp.decodificar(nuevo)[8:])
    c.sub(">= 1100 cartas con copias", r["despues"][0] >= 1100, r["despues"])
    c.sub("mazo actual intacto (bits 8-13)", r["mazo_intacto"])
    c.sub("suma valida", pp.suma_ok(pp.decodificar(nuevo)[8:8 + pp.TAM_PLANO]))
    # las copias extra ganadas en duelos se respetan; el desbloqueo nunca pasa de max(original, 3)
    c.sub("ninguna carta pierde copias ni supera max(original, 3)",
          all(a & 0xFF <= d & 0xFF <= max(a & 0xFF, 3) for a, d in zip(antes, col)))

@caso("P05", "Desbloqueo idempotente (aplicarlo dos veces da lo mismo)", "Partida")
def _(c):
    uno, _ = dc.desbloquear(_save(), 3); dos, _ = dc.desbloquear(uno, 3)
    c.sub("identico", uno == dos)

@caso("P06", "Desbloqueo excluye dioses egipcios y 'Glory of the King's Hand' por defecto", "Partida")
def _(c):
    car = {int(r["idx"]): r for r in csv.DictReader(open(os.path.join(BASE, "re-output", "cards.csv"), encoding="utf-8"))}
    col = pp.coleccion(pp.decodificar(dc.desbloquear(_save(), 3)[0])[8:])
    excl = [i for i, r in car.items() if r["tipo"] in ("Divino", "Especial")]
    c.sub("no se regalan", all((col[i] & 0xFF) == (pp.coleccion(pp.decodificar(_save())[8:])[i] & 0xFF) for i in excl), excl)

def _save_con_ful(arch, valor):
    """Partida con la opcion 'todo el set' (0xA54DB4) fijada, como la guarda el menu de opciones."""
    plano = pp.decodificar(arch); cuerpo = bytearray(plano[8:8 + pp.TAM_PLANO])
    cuerpo[0xA54DB4 - 0xA53CC0] = valor
    cuerpo = pp.recalcular_suma(bytes(cuerpo))
    nuevo = pp.codificar(plano[:8] + cuerpo + plano[8 + pp.TAM_PLANO:], len(arch))
    nuevo[:4] = pp.cabecera(nuevo, pp.TAM_PLANO)
    return bytes(nuevo)

@caso("P08", "Desbloqueo respeta la opcion 'todo el set / solo Joey' del jugador", "Partida")
def _(c):
    o = 0xA54DAE - 0xA53CC0
    for valor in (0, 1):
        p = pp.decodificar(dc.desbloquear(_save_con_ful(_save(), valor), 3)[0])[8:]
        c.sub("FUL=%d se conserva" % valor, p[o + 6] == valor, p[o + 6])
        c.sub("inicializado (0xA54DB1) = 1: el juego no lo recalcula", p[o + 3] == 1, p[o + 3])

@caso("S16", "Ruta del mazo CPU: con 'todo el set' la CPU sigue usando la tabla inyectada", "Memoria simulada")
def _(c):
    m = MemFalsa()
    c.sub("el exe trae el JE original en 0x44BC08", m.leer(yr.RUTA_CPU, 6) == yr.RUTA_CPU_ORIGINAL, m.leer(yr.RUTA_CPU, 6).hex())
    v, t = _vigilante(m); m.poner(yr.ADDR_MODO_FUL, bytes([1])); time.sleep(0.3); _parar(v, t)
    c.sub("el vigilante lo cambia por JMP", m.leer(yr.RUTA_CPU, 6) == yr.RUTA_CPU_SIEMPRE, m.leer(yr.RUTA_CPU, 6).hex())
    c.sub("la opcion del jugador sigue en 'todo el set'", m.leer(yr.ADDR_MODO_FUL, 1) == bytes([1]))
    c.sub("sin errores de inyeccion", v.errores == 0, v.errores)
    c.sub("idempotente", yr.aplicar_ruta_cpu(m) and m.leer(yr.RUTA_CPU, 6) == yr.RUTA_CPU_SIEMPRE)
    c.sub("--ful-original restaura el JE", yr.aplicar_ruta_cpu(m, False) and m.leer(yr.RUTA_CPU, 6) == yr.RUTA_CPU_ORIGINAL)
    m.poner(yr.RUTA_CPU, b"\x90" * 6)
    c.sub("bytes desconocidos: no parchea", not yr.aplicar_ruta_cpu(m) and m.leer(yr.RUTA_CPU, 6) == b"\x90" * 6)

@caso("S15","Vigilante: respeta la opcion 'todo el set' (modo FUL) del jugador y solo la registra", "Memoria simulada")
def _(c):
    m = MemFalsa(); v, t = _vigilante(m); m.poner(yr.ADDR_MODO_FUL, bytes([1])); time.sleep(0.4)
    c.sub("0xA54DB4 sigue en 1 (no se revierte)", m.leer(yr.ADDR_MODO_FUL, 1) == bytes([1]))
    c.sub("el vigilante registra el cambio", v.modo_ful == 1, v.modo_ful)
    m.poner(yr.ADDR_MODO_FUL, bytes([0])); time.sleep(0.4); _parar(v, t)
    c.sub("vuelta a 'solo Joey' registrada", v.modo_ful == 0, v.modo_ful)

@caso("P09", "Save truncado (juego cerrado a medio guardar) se rechaza con mensaje claro", "Partida")
def _(c):
    try:
        dc.desbloquear(_save()[:5053], 3); c.sub("rechazado", False, "no lanzo")
    except ValueError as e:
        c.sub("rechazado con ValueError", "incompleto" in str(e), e)

@caso("P07", "Desbloqueo rechaza un save corrupto sin escribir", "Partida")
def _(c):
    f = bytearray(_save()); f[200] ^= 0x55
    try:
        dc.desbloquear(bytes(f), 3); c.sub("rechazado", False, "no lanzo")
    except ValueError as e:
        c.sub("rechazado", True, e)

# ================================================================ V/G: proceso vivo y frontend
class Sesion:
    """Juego real lanzado por la bateria con los mismos componentes del lanzador."""
    j = None
    @classmethod
    def iniciar(cls):
        import control, flujo
        cls.control, cls.flujo = control, flujo
        cls.ruta_hist = _tmp("historial_pruebas.json")
        cls.hist = {"nivel": 0.0, "resultados": []}
        cls.nums = Datos.get("num", numerados)
        cls.n_ful = yr.parchear_fuls(cls.nums, 0.0, rng=random.Random(2026))
        cls.proc = subprocess.Popen([yr.EXE, "-win", "-speedy"], cwd=yr.APP)
        log.info("juego de pruebas lanzado pid=%d", cls.proc.pid)
        cls.sel = yr.Selector(cls.nums, 0.0, rng=random.Random(77))
        cls.vig = yr.Vigilante(cls.proc, cls.sel, cls.hist, ruta_historial=cls.ruta_hist, refresco=1.0)
        threading.Thread(target=cls.vig.correr, name="vigilante", daemon=True).start()
        cls.j = flujo.Juego(cls.proc)
        time.sleep(4)
        cls.duelos = []
    @classmethod
    def cerrar(cls):
        if cls.j:
            cls.vig.detener.set()
            try: cls.j.cerrar()
            except Exception: pass
            if cls.proc.poll() is None:
                cls.proc.terminate(); cls.proc.wait(20)

def _necesita_sesion():
    if Sesion.j is None:
        Sesion.iniciar()
    if not Sesion.j.vivo():
        raise Fallo("el juego no esta en ejecucion")
    return Sesion

@caso("V01", "El juego arranca y aparece la ventana YUGIOHAPPLICATION", "Proceso vivo", "vivo")
def _(c):
    s = _necesita_sesion()
    c.sub("proceso vivo", s.j.vivo(), s.proc.pid)
    c.sub("ventana encontrada", bool(s.j.hwnd), s.j.hwnd)
    c.sub("titulo", s.control.titulo(s.j.hwnd) == "Yu-Gi-Oh! Power of Chaos", s.control.titulo(s.j.hwnd))

@caso("V02", "La tabla viva es la del vigilante", "Proceso vivo", "vivo")
def _(c):
    s = _necesita_sesion(); viva = yr.leer_tabla(s.j.mem)
    c.sub("igual", viva == s.vig.tabla_actual, viva[:12] if viva else None)

@caso("V03", "Los diales vivos corresponden al temperamento anunciado", "Proceso vivo", "vivo")
def _(c):
    s = _necesita_sesion(); u, a = s.vig.diales_actuales
    c.sub("ataque", s.j.mem.leer(yr.DIAL_ATAQUE, 9) == yr.bytes_ataque(u), (s.vig.temperamento, u))
    c.sub("invocar", s.j.mem.leer(yr.DIAL_INVOCAR, 5) == yr.bytes_invocar(a), a)

@caso("V04", ".text fuera de los parches conocidos (diales, ruta CPU) identico al exe; ruta CPU parcheada", "Proceso vivo", "vivo")
def _(c):
    s = _necesita_sesion(); d = open(yr.EXE, "rb").read()
    for ini, fin in ((0x5B0000, 0x5B3000), (0x44B000, 0x44D000)):
        vivo = bytearray(s.j.mem.leer(ini, fin - ini)); disco = bytearray(d[ini - 0x400000:fin - 0x400000])
        for a, n in ((yr.DIAL_ATAQUE, 9), (yr.DIAL_INVOCAR, 5), (yr.RUTA_CPU, 6)):
            if ini <= a < fin:
                vivo[a - ini:a - ini + n] = disco[a - ini:a - ini + n]
        difs = sum(1 for x, y in zip(vivo, disco) if x != y)
        c.sub("0x%X-0x%X" % (ini, fin), difs == 0, "%d bytes distintos" % difs)
    c.sub("ruta CPU = JMP (tabla inyectada tambien con 'todo el set')", s.j.mem.leer(yr.RUTA_CPU, 6) == yr.RUTA_CPU_SIEMPRE)

@caso("V05", "Proteccion de memoria restaurada tras parchear", "Proceso vivo", "vivo")
def _(c):
    import ctypes
    from ctypes import wintypes
    class MBI(ctypes.Structure):
        _fields_ = [("BaseAddress", ctypes.c_void_p), ("AllocationBase", ctypes.c_void_p), ("AllocationProtect", wintypes.DWORD),
                    ("RegionSize", ctypes.c_size_t), ("State", wintypes.DWORD), ("Protect", wintypes.DWORD), ("Type", wintypes.DWORD)]
    s = _necesita_sesion(); k = ctypes.windll.kernel32
    k.VirtualQueryEx.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.POINTER(MBI), ctypes.c_size_t]
    for a, esperadas, n in ((yr.TABLA_CPU, (0x02,), ".rdata tabla"), (yr.DIAL_ATAQUE, (0x20,), ".text dial")):
        mbi = MBI(); k.VirtualQueryEx(s.j.mem.h, a, ctypes.byref(mbi), ctypes.sizeof(mbi))
        c.sub(n, mbi.Protect in esperadas, "0x%X" % mbi.Protect)

@caso("V06", "Memoria de trabajo del juego razonable", "Proceso vivo", "vivo")
def _(c):
    s = _necesita_sesion()
    out = subprocess.run(["tasklist", "/FI", "PID eq %d" % s.proc.pid, "/FO", "CSV", "/NH"], capture_output=True, text=True).stdout
    kb = int(out.split('","')[-1].replace('"', "").replace(" K", "").replace(".", "").replace(",", "").strip() or 0)
    c.sub("< 400 MB", 0 < kb < 400000, "%d KB" % kb)

@caso("V07", "La tabla no se re-sortea sin duelo de por medio", "Proceso vivo", "vivo")
def _(c):
    s = _necesita_sesion(); a = yr.leer_tabla(s.j.mem); time.sleep(4); b = yr.leer_tabla(s.j.mem)
    c.sub("estable", a == b)

@caso("V08", "Lecturas de estado y LP funcionan en vivo", "Proceso vivo", "vivo")
def _(c):
    s = _necesita_sesion(); e = yr.leer_estado(s.j.mem); lp = s.j.lp()
    c.sub("estado legible", e is not None, e); c.sub("LP legibles", None not in lp, lp)

@caso("V09", "Data.dat en uso es el de la sesion (37 ful parcheados)", "Proceso vivo", "vivo")
def _(c):
    s = _necesita_sesion(); c.sub("37 aplicados", s.n_ful == 37, s.n_ful)
    c.sub("Data.dat mas grande que .full", os.path.getsize(yr.DESTINO) > os.path.getsize(FULL))

@caso("V10", "El vigilante no registro errores hasta ahora", "Proceso vivo", "vivo")
def _(c):
    s = _necesita_sesion(); c.sub("0 errores", s.vig.errores == 0, s.vig.errores); c.sub("ciclos > 0", s.vig.ciclos > 0, s.vig.ciclos)

@caso("V11", "Tabla FUL del proceso identica al exe (no la pisa la inyeccion)", "Proceso vivo", "vivo")
def _(c):
    s = _necesita_sesion(); d = open(yr.EXE, "rb").read()
    ini, fin = 0x5DB080, 0x5DB16C  # conteos + 49 punteros de sufijo
    c.sub("0x5DB080-0x5DB16C igual al disco", s.j.mem.leer(ini, fin - ini) == d[ini - 0x400000:fin - 0x400000])

def _duelo(c, ganar, forzar=None, modo="individual"):
    """Un duelo completo por frontend. Devuelve dict con lo observado."""
    s = _necesita_sesion(); f = s.flujo; import mazo_cpu
    if forzar is not None:
        tabla = [0, 1, 2, 3, 4] + [forzar] * 35
        s.vig.forzada = tabla; s.vig.tabla_actual = list(tabla); yr.escribir_tabla(s.j.mem, tabla)
    tabla = list(s.vig.tabla_actual); temp, diales = s.vig.temperamento, s.vig.diales_actuales
    ok, pasos = f.iniciar_duelo(s.j, modo)
    c.sub("duelo iniciado por frontend", ok, pasos[-6:])
    if not ok:
        s.control.captura(s.j.hwnd, "fallo_inicio")
        raise Fallo("no se pudo iniciar el duelo")
    nivel, torneo = s.j.nivel_motor()
    top, z = mazo_cpu.identificar(s.j.mem, f.LADO_CPU)
    s.control.captura(s.j.hwnd, "duelo_%s" % c.caso.id)
    r = {"nivel": nivel, "torneo": torneo, "tabla": tabla, "temp": temp, "diales": diales, "top": top, "z": z}
    resultado, menu = f.terminar_duelo(s.j, s.vig, ganar)
    r["resultado"], r["menu"] = resultado, menu
    s.duelos.append(r)
    return r

def _check_fila(c, r):
    nv = max(1, min(7, r["nivel"]))
    fila = r["tabla"][nv * 5:nv * 5 + 5]
    mejor = r["top"][0]
    c.sub("mazo CPU identificado EXACTO", mejor[3], "cpu_%03d %s (%d/%d)" % (mejor[6], mejor[7], mejor[1], mejor[2]))
    c.sub("mazo pertenece a la fila del nivel %d" % nv, mejor[6] in fila, "fila=%s" % fila)

for _i, _ganar in enumerate([True, False, True, True, False, True]):
    def _mk(i=_i, ganar=_ganar):
        @caso("G%02d" % (i + 1), "Duelo individual %d por frontend (%s forzada)" % (i + 1, "victoria" if ganar else "derrota"),
              "Frontend", "gui")
        def _(c):
            s = _necesita_sesion(); antes = list(s.vig.resultados); temp_antes = s.vig.temperamento
            r = _duelo(c, ganar)
            _check_fila(c, r)
            c.sub("resultado detectado automaticamente", r["resultado"] == ("g" if ganar else "p"), r["resultado"])
            c.sub("historial persistido", json.load(open(s.ruta_hist))["resultados"] == s.vig.resultados)
            c.sub("volvio al menu principal", r["menu"])
            u, a = s.vig.diales_actuales
            c.sub("diales vivos = nuevo temperamento (%s)" % s.vig.temperamento,
                  s.j.mem.leer(yr.DIAL_ATAQUE, 9) == yr.bytes_ataque(u) and s.j.mem.leer(yr.DIAL_INVOCAR, 5) == yr.bytes_invocar(a))
            c.sub("tabla viva = nueva tabla", yr.leer_tabla(s.j.mem) == s.vig.tabla_actual)
            c.sub("se agrego exactamente un resultado", len(s.vig.resultados) == len(antes) + 1)
    _mk()

def _buscar(pred):
    for m in Datos.get("num", numerados):
        d = _bib()[m["archivo"]]
        if pred(m, d): return m
    return None

def _caso_forzado(id, nombre, pred, extra=None):
    @caso(id, nombre, "Frontend", "gui")
    def _(c):
        m = _buscar(pred)
        if not c.sub("existe un mazo candidato", m is not None): return
        s = _necesita_sesion()
        try:
            r = _duelo(c, True, forzar=m["numero"])
        finally:
            s.vig.forzada = None
        mejor = r["top"][0]
        c.sub("cargo exactamente cpu_%03d (%s)" % (m["numero"], m["archivo"]), mejor[3] and mejor[6] == m["numero"],
              "cpu_%03d %d/%d" % (mejor[6], mejor[1], mejor[2]))
        c.sub("el juego sigue vivo", s.j.vivo())
        if extra: extra(c, m, r)

def _chk_fusion(c, m, r):
    esperado = sorted(_bib()[m["archivo"]]["fus"]); visto = sorted(r["z"]["fusion"])
    c.sub("mazo de fusion de la CPU coincide", esperado == visto, "%s vs %s" % (esperado[:5], visto[:5]))

_caso_forzado("G07", "Mazo con Blue-Eyes (id 2000) carga sin problemas", lambda m, d: 2000 in d["main"])
_caso_forzado("G08", "Mazo 'caos (draft)' carga exacto", lambda m, d: m["arquetipo"] == "caos (draft)")
_caso_forzado("G09", "Mazo Exodia carga exacto", lambda m, d: m["arquetipo"] == "Exodia")
_caso_forzado("G10", "Mazo con fusiones: zona de fusion correcta", lambda m, d: len(d["fus"]) >= 3, _chk_fusion)
_caso_forzado("G11", "Mazo tier 3 (el mas fuerte) carga exacto", lambda m, d: m["tier"] == 3 and m["grupo"] == "agresivo")
_caso_forzado("G12", "Mazo 'muro-trampas' (tortuga) carga exacto", lambda m, d: m["arquetipo"] == "muro-trampas")

@caso("G13", "Turnos de la CPU con diales extremos (humo): el juego no se cae", "Frontend", "gui")
def _(c):
    s = _necesita_sesion(); f = s.flujo
    ok, pasos = f.iniciar_duelo(s.j); c.sub("duelo iniciado", ok, pasos[-4:])
    if not ok: raise Fallo("sin duelo")
    for u, a in ((-128, 0), (127, 3000)):
        c.sub("diales %d/%d aplicados" % (u, a), yr.aplicar_diales(s.j.mem, u, a))
        lp0 = s.j.lp(); cpu0 = s.j.contadores(f.LADO_CPU)
        for turno in range(2):
            s.control.clic(s.j.hwnd, 234, 490); time.sleep(3)  # EP: terminar turno
            for _ in range(3):  # limite de 7 cartas: el juego pide "Descarta de tu mano"
                if s.j.contadores(f.LADO_JUG)["mano"] > 6:
                    s.control.clic(s.j.hwnd, 315, 565); time.sleep(2.5)
            time.sleep(10)  # la CPU juega su turno
            s.control.captura(s.j.hwnd, "humo_%d_%d" % (u, turno))
        c.sub("vivo tras 2 turnos con %d/%d" % (u, a), s.j.vivo())
        c.sub("la CPU actuo (mano/campo/LP cambiaron)", s.j.contadores(f.LADO_CPU) != cpu0 or s.j.lp() != lp0,
              "%s -> %s, LP %s -> %s" % (cpu0, s.j.contadores(f.LADO_CPU), lp0, s.j.lp()))
    yr.aplicar_diales(s.j.mem, *s.vig.diales_actuales)
    res, menu = f.terminar_duelo(s.j, s.vig, True)
    c.sub("fin de duelo detectado", res == "g", res); c.sub("menu", menu)

@caso("G14", "Modo TORNEO: arranca, la CPU usa la tabla inyectada y el modo FUL sigue en 0", "Frontend", "gui")
def _(c):
    s = _necesita_sesion(); f = s.flujo; import mazo_cpu
    tabla = list(s.vig.tabla_actual)
    ok, pasos = f.iniciar_duelo(s.j, "torneo")
    c.sub("duelo de torneo iniciado por frontend", ok, pasos[-5:])
    if not ok: raise Fallo("sin duelo de torneo")
    nivel, ful = s.j.nivel_motor()
    top, z = mazo_cpu.identificar(s.j.mem, f.LADO_CPU); mejor = top[0]
    nv = max(1, min(7, nivel))
    c.sub("modo FUL = 0", ful == 0, ful)
    c.sub("mazo CPU EXACTO y en la fila del nivel %d" % nv, mejor[3] and mejor[6] in tabla[nv * 5:nv * 5 + 5],
          "cpu_%03d %s" % (mejor[6], mejor[7]))
    rondas = 0
    for _ in range(4):  # el torneo puede encadenar rondas: se cierran todas
        res, menu = f.terminar_duelo(s.j, s.vig, True, timeout=40)
        rondas += 1
        if menu: break
        if f.duelo_en_curso(s.j) or f.esperar(lambda: s.j.duelo_activo(), 30, desc="siguiente ronda"):
            continue
    c.sub("vuelve al menu principal tras el torneo", f.ir_a_menu_principal(s.j, 120), "%d ronda(s)" % rondas)

@caso("G21", "Opcion 'todo el set' (modo FUL=1): la CPU juega con un mazo de la tabla inyectada", "Frontend", "gui")
def _(c):
    s = _necesita_sesion(); f = s.flujo; import mazo_cpu
    # el juego recarga la partida del disco al empezar el duelo: la opcion se guarda en system.dat (como el menu)
    # y tambien en memoria. R01 restaura la partida original al final de la bateria.
    previo = s.j.mem.leer(yr.ADDR_MODO_FUL, 1)
    nuevo = _save_con_ful(_save(), 1)
    with open(SAVE_REAL + ".tmp", "wb") as fh: fh.write(nuevo)
    os.replace(SAVE_REAL + ".tmp", SAVE_REAL)
    s.j.mem.escribir(yr.ADDR_MODO_FUL, b"\x01", "prueba G21: opcion 'todo el set'")
    try:
        tabla = list(s.vig.tabla_actual)
        ok, pasos = f.iniciar_duelo(s.j, "individual")
        c.sub("duelo individual iniciado con 'todo el set'", ok, pasos[-5:])
        if not ok: raise Fallo("sin duelo")
        nivel, ful = s.j.nivel_motor()
        c.sub("modo FUL = 1 durante el duelo", ful == 1, ful)
        top, z = mazo_cpu.identificar(s.j.mem, f.LADO_CPU); mejor = top[0]
        nv = max(1, min(7, nivel))
        c.sub("mazo CPU EXACTO de la biblioteca y en la fila del nivel %d" % nv,
              mejor[3] and mejor[6] in tabla[nv * 5:nv * 5 + 5], "cpu_%03d %s" % (mejor[6], mejor[7]))
        res, menu = f.terminar_duelo(s.j, s.vig, True)
        c.sub("fin de duelo y vuelta al menu", res == "g" and menu, (res, menu))
    finally:
        if previo: s.j.mem.escribir(yr.ADDR_MODO_FUL, previo, "prueba G21: opcion restaurada")

@caso("G15", "Variedad: los duelos usaron mazos y temperamentos distintos", "Frontend", "gui")
def _(c):
    s = _necesita_sesion(); normales = [d for d in s.duelos if d["torneo"] == 0]
    mazos = [d["top"][0][6] for d in normales]; temps = [d["temp"] for d in normales]
    c.sub(">= 6 duelos jugados", len(s.duelos) >= 6, len(s.duelos))
    c.sub("mazos distintos >= 70%", len(set(mazos)) >= 0.7 * max(1, len(mazos)), mazos)
    c.sub("al menos 2 temperamentos", len(set(temps)) >= 2, temps)

@caso("G16", "Historial de pruebas coherente con los duelos", "Frontend", "gui")
def _(c):
    s = _necesita_sesion(); h = json.load(open(s.ruta_hist))
    c.sub("resultados iguales", h["resultados"] == s.vig.resultados, h["resultados"])
    esperado = 0.0
    for r in h["resultados"]: esperado = max(-1.0, min(2.0, esperado + (0.34 if r == "g" else -0.34)))
    c.sub("nivel recalculado coincide", abs(h["nivel"] - esperado) < 1e-6, (h["nivel"], esperado))

@caso("G17", "Salir por el menu cierra el juego limpio", "Frontend", "gui")
def _(c):
    s = _necesita_sesion(); f = s.flujo
    c.sub("menu principal", f.ir_a_menu_principal(s.j))
    s.control.clic(s.j.hwnd, 400, 540)
    c.sub("proceso termina", f.esperar(lambda: s.proc.poll() is not None, 30, desc="cierre"))
    c.sub("codigo 0", s.proc.poll() == 0, s.proc.poll())
    c.sub("vigilante sin errores", s.vig.errores == 0, s.vig.errores)
    Sesion.j = None

@caso("G18", "Lanzador real por linea de comandos: arranque, inyeccion y salida", "Frontend", "gui")
def _(c):
    import control, flujo
    hist_real = yr.HISTORIAL; copia = None
    if os.path.exists(hist_real):
        copia = _tmp("hist_copia.json"); shutil.copy(hist_real, copia)
    subprocess.run(["taskkill", "/F", "/IM", "Joey_Pc.exe"], capture_output=True)  # el juego no admite 2 instancias
    time.sleep(2)
    p = subprocess.Popen([sys.executable, "-I", "-u", os.path.join(yr.LAUNCHER, "yugi_reload.py"), "--", "-win", "-speedy"],
                         cwd=yr.LAUNCHER, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, text=True)
    try:
        pid = None
        fin = time.time() + 120
        while time.time() < fin and pid is None:
            out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq Joey_Pc.exe", "/FO", "CSV", "/NH"], capture_output=True, text=True).stdout
            pid = next((int(l.split('","')[1]) for l in out.splitlines() if "Joey_Pc" in l), None)
            time.sleep(1)
        c.sub("juego lanzado por el lanzador", pid is not None, pid)
        class P:  # envoltura minima para flujo.Juego
            def __init__(s, pid): s.pid = pid
            def poll(s):
                o = subprocess.run(["tasklist", "/FI", "PID eq %d" % s.pid, "/NH"], capture_output=True, text=True).stdout
                return None if str(s.pid) in o else 0
        time.sleep(8)
        j = flujo.Juego(P(pid))
        c.sub("diales aplicados por el lanzador", j.mem.leer(yr.DIAL_ATAQUE, 6)[:4] == bytes.fromhex("66894502")
              or j.mem.leer(yr.DIAL_ATAQUE, 9) == yr.ATAQUE_ORIGINAL)
        t = yr.leer_tabla(j.mem); c.sub("tabla inyectada (numeros >= 100)", any(x >= 100 for x in t[5:]), t[5:12])
        c.sub("menu principal", flujo.ir_a_menu_principal(j))
        control.clic(j.hwnd, 400, 540); j.cerrar()
        out, _ = p.communicate(timeout=60)
        c.sub("lanzador termina con codigo 0", p.returncode == 0, p.returncode)
        c.sub("consola: inyeccion verificada", "tabla verificada" in out, out[-400:])
        c.sub("consola: sin Traceback", "Traceback" not in out)
    finally:
        if p.poll() is None: p.kill()
        if copia: shutil.copy(copia, hist_real)
        elif os.path.exists(hist_real): os.remove(hist_real)

@caso("G19", "Logs del lanzador: sin ERROR ni excepciones en la ultima sesion", "Frontend", "gui")
def _(c):
    ult = sorted(glob.glob(os.path.join(yr.LOG_DIR, "sesion_*.log")))[-1]
    txt = open(ult, encoding="utf-8").read()
    c.sub(os.path.basename(ult), "[ERROR" not in txt and "Traceback" not in txt, len(txt.splitlines()))

@caso("G20", "Log de la bateria: el vigilante escribio cada escritura de memoria", "Frontend", "gui")
def _(c):
    txt = open(RUTA_LOG, encoding="utf-8").read()
    c.sub("hay escrituras de tabla registradas", txt.count("tabla CPU") > 5, txt.count("tabla CPU"))
    c.sub("hay escrituras de diales registradas", txt.count("dial ataque") > 5, txt.count("dial ataque"))

# ================================================================ R: restauracion
@caso("R01", "Restaurar la partida al estado previo a la bateria (system.dat + Deck.ydc + registro)", "Restauracion", "final")
def _(c):
    bk = RESPALDO_RUN[0]
    if not c.sub("hay respaldo de esta ejecucion", bk and os.path.isdir(bk), bk): return
    destino = os.path.join(BASE, "juego-extraido", "Yu-Gi-Oh! Power of Chaos Common", "system.dat")
    sha = lambda p: hashlib.sha1(open(p, "rb").read()).hexdigest()
    shutil.copy(os.path.join(bk, "system.dat"), destino)
    c.sub("system.dat == estado previo", sha(destino) == sha(os.path.join(bk, "system.dat")), sha(destino))
    shutil.copy(os.path.join(bk, "Deck.ydc"), os.path.join(yr.APP, "Deck.ydc"))  # el juego reescribe la cabecera/orden
    c.sub("Deck.ydc == estado previo", sha(os.path.join(yr.APP, "Deck.ydc")) == sha(os.path.join(bk, "Deck.ydc")))
    r = subprocess.run(["reg", "import", os.path.join(bk, "konami.reg")], capture_output=True, text=True)
    c.sub("registro reimportado", r.returncode == 0, r.stderr.strip())
    hist_bk = os.path.join(bk, "historial.json")
    if os.path.exists(hist_bk): shutil.copy(hist_bk, yr.HISTORIAL)
    elif os.path.exists(yr.HISTORIAL): os.remove(yr.HISTORIAL)
    c.sub("historial.json restaurado", os.path.exists(yr.HISTORIAL) == os.path.exists(hist_bk))

RESPALDO_RUN = [None]

def respaldar_partida():
    """Copia de la partida tal como esta ANTES de esta ejecucion (R01 la restaura al final)."""
    bk = os.path.join(BASE, "respaldo-partida", "bateria_" + SELLO)
    os.makedirs(bk, exist_ok=True)
    shutil.copy2(os.path.join(BASE, "juego-extraido", "Yu-Gi-Oh! Power of Chaos Common", "system.dat"), bk)
    shutil.copy2(os.path.join(yr.APP, "Deck.ydc"), bk)
    if os.path.exists(yr.HISTORIAL): shutil.copy2(yr.HISTORIAL, bk)
    subprocess.run(["reg", "export", r"HKCU\Software\Classes\VirtualStore\MACHINE\SOFTWARE\WOW6432Node\KONAMI",
                    os.path.join(bk, "konami.reg"), "/y"], capture_output=True)
    RESPALDO_RUN[0] = bk
    log.info("partida respaldada antes de la bateria en %s", bk)

# ================================================================ ejecucion
def correr(seleccion=None, fases=("offline", "vivo", "gui", "final")):
    res = []
    casos = [k for k in REGISTRO if k.fase in fases and (not seleccion or k.id in seleccion)]
    consola("Bateria Yugi Reload: %d casos | log: %s" % (len(casos), RUTA_LOG))
    if any(k.fase in ("vivo", "gui", "final") for k in casos):
        respaldar_partida()
    try:
        for k in casos:
            ctx = Ctx(k); t0 = time.time(); err = None
            log.info("===== %s %s [%s]", k.id, k.nombre, k.cat)
            try:
                k.fn(ctx)
            except Exception as e:
                err = "%s: %s" % (type(e).__name__, e)
                log.error("[%s] excepcion:\n%s", k.id, traceback.format_exc())
                ctx.sub("sin excepcion", False, err)
            ok = bool(ctx.subs) and all(s["ok"] for s in ctx.subs)
            res.append({"id": k.id, "nombre": k.nombre, "cat": k.cat, "ok": ok, "seg": round(time.time() - t0, 1),
                        "subcasos": ctx.subs})
            consola("%s %-4s %-72s %3d sub  %5.1fs" % ("PASA " if ok else "FALLA", k.id, k.nombre[:72],
                                                       len(ctx.subs), time.time() - t0))
    finally:
        Sesion.cerrar()
    json.dump(res, open(os.path.join(LOGS, "resultados_%s.json" % SELLO), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    escribir_informe(res)
    return res

def escribir_informe(res):
    pasan = sum(r["ok"] for r in res); subs = sum(len(r["subcasos"]) for r in res)
    subs_ok = sum(s["ok"] for r in res for s in r["subcasos"])
    L = ["# Informe de la bateria (%s)" % SELLO, "",
         "Casos: %d/%d pasan · Subcasos: %d/%d pasan" % (pasan, len(res), subs_ok, subs), ""]
    for cat in dict.fromkeys(r["cat"] for r in res):
        rs = [r for r in res if r["cat"] == cat]
        L.append("## %s (%d/%d)" % (cat, sum(r["ok"] for r in rs), len(rs)))
        for r in rs:
            L.append("- %s **%s** %s (%d subcasos, %.1fs)" % ("✅" if r["ok"] else "❌", r["id"], r["nombre"],
                                                         len(r["subcasos"]), r["seg"]))
            for s in r["subcasos"]:
                if not s["ok"]:
                    L.append("    - ❌ %s — %s" % (s["sub"], s["detalle"]))
        L.append("")
    open(os.path.join(LOGS, "informe_%s.md" % SELLO), "w", encoding="utf-8").write("\n".join(L))
    consola("RESUMEN: %d/%d casos, %d/%d subcasos | informe_%s.md" % (pasan, len(res), subs_ok, subs, SELLO))

if __name__ == "__main__":
    sel = None; fases = ("offline", "vivo", "gui", "final")
    if "--casos" in sys.argv: sel = set(sys.argv[sys.argv.index("--casos") + 1].split(","))
    if "--solo" in sys.argv: fases = tuple(sys.argv[sys.argv.index("--solo") + 1].split(","))
    r = correr(sel, fases)
    sys.exit(0 if all(x["ok"] for x in r) else 1)
