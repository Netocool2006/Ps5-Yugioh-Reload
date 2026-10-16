# Identifica que mazo cargo la CPU leyendo sus zonas de duelo en memoria.
# Bloque por lado: 0xA55D64 + lado*0xD44. Contadores (bytes) en +4 mano, +5 mazo, +6 cementerio,
# +7 mazo de fusion. Listas de u32 (idx interno = v & 0xFFF; bit 12 = propietario):
#   mano 0xA56434, mazo 0xA56574, fusion 0xA566B4, cementerio 0xA566F0 (relativas al lado 0).
# El lado del jugador se detecta comparando con Deck.ydc (en duelo real el jugador es el lado 1).
import collections, csv, glob, os, struct, sys
sys.path.insert(0, r"D:\Yugi-Reload\launcher")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import yugi_reload as yr

BASE = r"D:\Yugi-Reload"
BLOQUE, TAM = 0xA55D64, 0xD44
LISTAS = {"mano": (0xA56434, 4), "mazo": (0xA56574, 5), "cementerio": (0xA566F0, 6), "fusion": (0xA566B4, 7)}

def cargar_cartas():
    return {int(r["idx"]): int(r["id"]) for r in
            csv.DictReader(open(os.path.join(BASE, "re-output", "cards.csv"), encoding="utf-8"))}

def leer_ydc(path):
    d = open(path, "rb").read()
    n = struct.unpack("<H", d[8:10])[0]
    main = list(struct.unpack("<%dH" % n, d[10:10 + n * 2]))
    p = 10 + n * 2
    nf = struct.unpack("<H", d[p:p + 2])[0]
    fus = list(struct.unpack("<%dH" % nf, d[p + 2:p + 2 + nf * 2]))
    return main, fus

def mazos_conocidos():
    out = {}
    for m in csv.DictReader(open(os.path.join(BASE, "launcher", "biblioteca_numeros.csv"), encoding="utf-8")):
        out[int(m["numero"])] = (m["archivo"], m["arquetipo"], *leer_ydc(os.path.join(BASE, "biblioteca", m["archivo"])))
    for p in glob.glob(os.path.join(BASE, "datadat-extraido", "j", "file", "cpu_0*.ydc")):
        out[int(os.path.basename(p)[4:7])] = (os.path.basename(p), "original", *leer_ydc(p))
    return out

def zonas(mem, lado, idx2id):
    base = BLOQUE + lado * TAM
    cont = mem.leer(base + 4, 4)
    res = {}
    for nombre, (dir0, off_cont) in LISTAS.items():
        n = cont[off_cont - 4]
        raw = mem.leer(dir0 + lado * TAM, max(1, n) * 4)
        vals = struct.unpack("<%dI" % max(1, n), raw)[:n]
        res[nombre] = [idx2id.get(v & 0xFFF, -(v & 0xFFF)) for v in vals]
    return res

def lado_jugador(mem, idx2id, deck=os.path.join(yr.APP, "Deck.ydc")):
    principal = collections.Counter(leer_ydc(deck)[0])
    mejor = None
    for lado in (0, 1):
        z = zonas(mem, lado, idx2id)
        c = collections.Counter(z["mano"] + z["mazo"] + z["cementerio"])
        sc = sum((c & principal).values())
        if mejor is None or sc > mejor[0]:
            mejor = (sc, lado)
    return mejor[1]

def identificar(mem, lado, top=3):
    idx2id = cargar_cartas()
    z = zonas(mem, lado, idx2id)
    vistos = collections.Counter(z["mano"] + z["mazo"] + z["cementerio"])
    fus_vistas = collections.Counter(z["fusion"])
    res = []
    for num, (arch, arq, main, fus) in mazos_conocidos().items():
        inter = sum((collections.Counter(main) & vistos).values())
        inter_f = sum((collections.Counter(fus) & fus_vistas).values())
        exacto = collections.Counter(main) == vistos and collections.Counter(fus) == fus_vistas
        res.append((inter / max(1, len(main)), inter, len(main), exacto, inter_f, len(fus), num, arch, arq))
    res.sort(key=lambda r: (r[3], r[0], r[4]), reverse=True)
    return res[:top], z

if __name__ == "__main__":
    from sesion import pid_juego
    m = yr.Memoria(pid_juego())
    try:
        idx2id = cargar_cartas()
        lj = lado_jugador(m, idx2id)
        print("lado del jugador: %d  -> CPU = lado %d" % (lj, 1 - lj))
        top, z = identificar(m, 1 - lj)
        print("CPU: mano=%d mazo=%d cementerio=%d fusion=%d" % tuple(len(z[k]) for k in ("mano", "mazo", "cementerio", "fusion")))
        for frac, inter, n, exacto, inf, nf, num, arch, arq in top:
            print("   cpu_%03d %-28s %-22s main %d/%d %s fusion %d/%d" %
                  (num, arch, arq, inter, n, "EXACTO" if exacto else "", inf, nf))
        tabla = yr.leer_tabla(m)
        print("tabla viva:", tabla)
    finally:
        m.cerrar()
