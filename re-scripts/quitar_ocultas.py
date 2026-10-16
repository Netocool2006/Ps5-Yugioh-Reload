# Quita de los mazos de la biblioteca CPU las cartas ocultas (CARD_Pack & 7 == 0: sin edicion, sin ilustracion; el
# juego las dibuja como "Slime Token" pero pelean con sus datos) y pone en su lugar cartas reales de las 771:
#  - monstruo -> monstruo jugable (Normal/Efecto) de la misma tribu (si no, mismo atributo), mismo rango de nivel
#    (<=4, 5-6, 7+) y ATK lo mas cercano sin pasarse (no sube el ATK medio del mazo);
#  - fusion -> fusion jugable, misma tribu o atributo, ATK cercano; magia -> magia; trampa -> trampa;
#  - respeta 3 copias por nombre (main + side) y el techo de ATK medio 1467 de reequilibrar_atk.py.
# Respaldo previo de cada mazo cambiado. Decision del usuario 2026-10-16 ("procede a arreglarlo").
# Uso: python -I quitar_ocultas.py [--simular]
import csv, os, random, shutil, struct, sys, time, zlib

BASE = r"D:\Yugi-Reload"
BIB = os.path.join(BASE, "biblioteca")
TECHO = 1467
SIMULAR = "--simular" in sys.argv

filas = [r for r in csv.DictReader(open(os.path.join(BASE, "re-output", "cards.csv"), encoding="utf-8")) if r["idx"].isdigit()]
cartas = {int(r["id"]): r for r in filas}
pack = open(os.path.join(BASE, "datadat-extraido", "bin#", "card_pack.bin"), "rb").read()
def usable(c): return int.from_bytes(pack[2 * int(c["idx"]):2 * int(c["idx"]) + 2], "little") & 7
def es_mon(c): return c["tipo"] not in ("Magic", "Trap")
def atk(i): return int(cartas[i]["atk"] or 0)
def nivel(i): return int(cartas[i]["nivel"] or 0)
def rango(n): return 0 if n <= 4 else 1 if n <= 6 else 2

oculta = {i for i, c in cartas.items() if not usable(c)}
# reemplazos: una entrada por nombre, solo cartas jugables y normales (sin dioses, tokens ni rituales)
pool = {}
for i, c in cartas.items():
    if (i == 0 or i in oculta or c["tipo"] in ("Divino", "Especial") or "Token" in c["nombre"]
            or "Forbidden One" in c["nombre"]):  # las piezas de Exodia no sirven sueltas
        continue
    pool.setdefault(c["nombre"], i)
pool = sorted(pool.values())
MON = [i for i in pool if es_mon(cartas[i]) and cartas[i]["clase"] in ("Normal", "Efecto")]
FUS = [i for i in pool if es_mon(cartas[i]) and cartas[i]["clase"] == "Fusion"]
MAG = [i for i in pool if cartas[i]["tipo"] == "Magic" and "Ritual" not in cartas[i]["nombre"]]  # sin rituales sueltos
TRA = [i for i in pool if cartas[i]["tipo"] == "Trap"]

def leer(p):
    d = open(p, "rb").read(); n = struct.unpack("<H", d[8:10])[0]; m = list(struct.unpack("<%dH" % n, d[10:10 + 2 * n]))
    q = 10 + 2 * n; nf = struct.unpack("<H", d[q:q + 2])[0]; f = list(struct.unpack("<%dH" % nf, d[q + 2:q + 2 + 2 * nf]))
    q += 2 + 2 * nf; ns = struct.unpack("<H", d[q:q + 2])[0]; s = list(struct.unpack("<%dH" % ns, d[q + 2:q + 2 + 2 * ns]))
    return d[:8], m, f, s

def escribir(p, hdr, m, f, s):
    out = hdr + struct.pack("<H", len(m)) + struct.pack("<%dH" % len(m), *m)
    out += struct.pack("<H", len(f)) + (struct.pack("<%dH" % len(f), *f) if f else b"")
    out += struct.pack("<H", len(s)) + (struct.pack("<%dH" % len(s), *s) if s else b"")
    open(p, "wb").write(out)

def promedio(m):
    mons = [x for x in m if es_mon(cartas[x])]
    return sum(atk(x) for x in mons) / len(mons) if mons else 0

def elegir(quitar, lista, copias, rng, arq):
    q = cartas[quitar]
    libres = [i for i in lista if copias.get(cartas[i]["nombre"], 0) < 3]
    if not libres:
        return None, False
    if not es_mon(q):  # magia o trampa: cualquiera de su clase, sorteo estable
        return rng.choice(libres), True
    t = arq.split(" ", 1)[1] if arq.startswith("tribal ") else q["tipo"]
    a = arq.split(" ", 1)[1] if arq.startswith("atributo ") else q["attr"]
    if q["clase"] != "Fusion":
        libres = [i for i in libres if rango(nivel(i)) == rango(nivel(quitar))] or libres
    # la tribu solo vale si tiene alguien de fuerza parecida (hasta +150 de ATK): las tribus chicas (Rock,
    # BeastWarrior) no tienen jugables debiles y subirian el ATK del mazo; entonces se usa el mismo atributo
    for fam in ([i for i in libres if cartas[i]["tipo"] == t], [i for i in libres if cartas[i]["attr"] == a], libres):
        if fam and (fam is libres or any(atk(i) <= atk(quitar) + 150 for i in fam)):
            debajo = [i for i in fam if atk(i) <= atk(quitar)] or fam
            mejor = min(debajo, key=lambda i: (abs(atk(i) - atk(quitar)), i))
            cerca = [i for i in debajo if abs(atk(i) - atk(mejor)) <= 100]
            return rng.choice(cerca), fam is not libres
    return None, False

def arreglar(nombre, arq, m, f, s):
    rng = random.Random(zlib.crc32(("ocultas" + nombre).encode()))
    m, f, s = list(m), list(f), list(s)
    cambios = []
    for lista_mazo in (m, f, s):
        for k, x in enumerate(lista_mazo):
            if x not in oculta:
                continue
            copias = {}
            for y in m + s:
                if y not in oculta:
                    copias[cartas[y]["nombre"]] = copias.get(cartas[y]["nombre"], 0) + 1
            c = cartas[x]
            # primero el tipo: en cards.csv hay trampas con clase "Fusion" (Shadow Spell, Call of the Dark)
            fuente = MAG if c["tipo"] == "Magic" else TRA if c["tipo"] == "Trap" else FUS if c["clase"] == "Fusion" else MON
            nuevo, en_familia = elegir(x, fuente, copias, rng, arq)
            if nuevo is None:
                raise SystemExit("sin reemplazo para %s en %s" % (c["nombre"], nombre))
            lista_mazo[k] = nuevo
            cambios.append((c["nombre"], cartas[nuevo]["nombre"], en_familia))
    return m, f, s, cambios

def main():
    nums = {r["archivo"]: r for r in csv.DictReader(open(os.path.join(BASE, "launcher", "biblioteca_numeros.csv"), encoding="utf-8"))}
    resp = os.path.join(BASE, "respaldo-biblioteca", "ocultas_" + time.strftime("%Y%m%d_%H%M%S"))
    tocados = total = fuera = sube = 0; informe = []
    for archivo in sorted(os.listdir(BIB)):
        if not archivo.endswith(".ydc"):
            continue
        p = os.path.join(BIB, archivo)
        hdr, m, f, s = leer(p)
        if not any(x in oculta for x in m + f + s):
            continue
        arq = nums.get(archivo, {}).get("arquetipo", "")
        antes = promedio(m)
        m2, f2, s2, cambios = arreglar(archivo, arq, m, f, s)
        despues = promedio(m2)
        assert not any(x in oculta for x in m2 + f2 + s2)
        assert len(m2) == len(m) and len(f2) == len(f) and len(s2) == len(s)
        if despues > max(antes, TECHO) + 0.5:
            sube += 1
        total += len(cambios); fuera += sum(1 for c in cambios if not c[2])
        informe.append("%-30s %-22s ATK %4.0f -> %4.0f | %s" % (archivo, arq, antes, despues,
                       "; ".join("%s -> %s" % c[:2] for c in cambios)))
        if not SIMULAR:
            os.makedirs(resp, exist_ok=True)
            shutil.copy2(p, resp)
            escribir(p, hdr, m2, f2, s2)
        tocados += 1
    out = os.path.join(BASE, "re-output", "quitar_ocultas.txt")
    open(out, "w", encoding="utf-8").write("\n".join(informe))
    print("%s %d mazos, %d cartas cambiadas | fuera de su familia: %d | mazos que pasan el techo de ATK: %d | detalle: %s%s"
          % ("simulados" if SIMULAR else "arreglados", tocados, total, fuera, sube, out,
             "" if SIMULAR else " | respaldo: " + resp))

if __name__ == "__main__":
    main()
