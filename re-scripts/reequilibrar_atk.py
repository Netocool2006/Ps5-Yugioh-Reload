# Baja el ATK medio de los mazos de la biblioteca al techo de los originales (1467) sin romper su identidad:
# cambia los monstruos de nivel <=4 mas fuertes por otros intermedios de la misma tribu/atributo,
# respeta 3 copias (main + side), no toca tributos, fusiones ni side. Respaldo previo de cada mazo cambiado.
# Uso: python -I reequilibrar_atk.py [--simular]
import csv, os, random, shutil, struct, sys, time, zlib

BASE = r"D:\Yugi-Reload"
BIB = os.path.join(BASE, "biblioteca")
TECHO = 1467
SIMULAR = "--simular" in sys.argv

cartas = {int(r["id"]): r for r in csv.DictReader(open(os.path.join(BASE, "re-output", "cards.csv"), encoding="utf-8"))}
def es_mon(c): return c["tipo"] not in ("Magic", "Trap")
def atk(i): return int(cartas[i]["atk"])
def nivel(i): return int(cartas[i]["nivel"] or 0)

# reemplazos posibles: monstruos jugables (con edicion: CARD_Pack & 7) de nivel <= 4, una entrada por nombre (id != 0)
PACK = open(os.path.join(BASE, "datadat-extraido", "bin#", "card_pack.bin"), "rb").read()
candidatos = {}
for i, c in cartas.items():
    pk = int.from_bytes(PACK[2 * int(c["idx"]):2 * int(c["idx"]) + 2], "little") if c["idx"].isdigit() else 0
    if i == 0 or not pk & 7 or not es_mon(c) or c["tipo"] in ("Divino", "Especial") or c["clase"] not in ("Normal", "Efecto"):
        continue
    if int(c["nivel"] or 0) <= 4 and 900 <= int(c["atk"]) <= 1400:
        candidatos.setdefault(c["nombre"], i)
candidatos = sorted(candidatos.values())

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
    return sum(atk(x) for x in mons) / len(mons)

def filtro_familia(arq, quitado):
    q = cartas[quitado]
    if arq.startswith("tribal "):
        t = arq.split(" ", 1)[1]
        return lambda c: c["tipo"] == t
    if arq.startswith("atributo "):
        a = arq.split(" ", 1)[1]
        return lambda c: c["attr"] == a
    return lambda c: c["tipo"] == q["tipo"] or c["attr"] == q["attr"]

def reequilibrar(nombre, arq, m, s):
    rng = random.Random(zlib.crc32(nombre.encode()))
    m = list(m); cambios = []
    for _ in range(40):
        if promedio(m) <= TECHO:
            break
        bajos = [x for x in m if es_mon(cartas[x]) and nivel(x) <= 4]
        if not bajos:
            break
        quitar = max(bajos, key=lambda x: (atk(x), x))
        copias = {}
        for x in m + s:
            copias[cartas[x]["nombre"]] = copias.get(cartas[x]["nombre"], 0) + 1
        copias[cartas[quitar]["nombre"]] -= 1
        fam = filtro_familia(arq, quitar)
        pool = [i for i in candidatos if atk(i) < atk(quitar) and copias.get(cartas[i]["nombre"], 0) < 3]
        propios = [i for i in pool if fam(cartas[i])]
        elegibles = propios or pool
        if not elegibles:
            break
        efecto = [i for i in elegibles if cartas[i]["clase"] == "Efecto"]
        elegibles = efecto or elegibles
        nuevo = rng.choice(elegibles)
        m[m.index(quitar)] = nuevo
        cambios.append((cartas[quitar]["nombre"], atk(quitar), cartas[nuevo]["nombre"], atk(nuevo), bool(propios)))
    return m, cambios

def main():
    nums = list(csv.DictReader(open(os.path.join(BASE, "launcher", "biblioteca_numeros.csv"), encoding="utf-8")))
    resp = os.path.join(BASE, "respaldo-biblioteca", "atk_" + time.strftime("%Y%m%d_%H%M%S"))
    tocados = fuera_familia = 0; informe = []
    for r in nums:
        p = os.path.join(BIB, r["archivo"])
        hdr, m, f, s = leer(p)
        antes = promedio(m)
        if antes <= TECHO:
            continue
        nuevo, cambios = reequilibrar(r["archivo"], r["arquetipo"], m, s)
        despues = promedio(nuevo)
        fuera_familia += sum(1 for c in cambios if not c[4])
        informe.append("%-30s %-22s %4.0f -> %4.0f | %s" % (r["archivo"], r["arquetipo"], antes, despues,
                       "; ".join("%s(%d)->%s(%d)" % c[:4] for c in cambios)))
        if not SIMULAR:
            os.makedirs(resp, exist_ok=True)
            shutil.copy2(p, resp)
            escribir(p, hdr, nuevo, f, s)
        tocados += 1
    out = os.path.join(BASE, "re-output", "reequilibrio_atk.txt")
    open(out, "w", encoding="utf-8").write("\n".join(informe))
    print("%s %d mazos | cambios fuera de su familia: %d | detalle: %s%s" % (
        "simulados" if SIMULAR else "reequilibrados", tocados, fuera_familia, out,
        "" if SIMULAR else " | respaldo: " + resp))

if __name__ == "__main__":
    main()
