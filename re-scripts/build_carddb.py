# Construye cards.csv y descifra los mazos .ydc de la CPU
import csv, glob, os, struct, sys

base = sys.argv[1]          # carpeta datadat-extraido
outdir = sys.argv[2]        # carpeta de salida

bins = os.path.join(base, "bin#")
names = open(os.path.join(bins, "card_nameeng.bin"), "rb").read()
prop = open(os.path.join(bins, "card_prop.bin"), "rb").read()
cid = open(os.path.join(bins, "card_id.bin"), "rb").read()
N = len(prop) // 4

TIPOS = {1:"Dragon",2:"Zombie",3:"Fiend",4:"Pyro",5:"SeaSerpent",6:"Rock",7:"Machine",
         8:"Fish",9:"Dinosaur",10:"Insect",11:"Beast",12:"BeastWarrior",13:"Plant",14:"Aqua",15:"Warrior",
         16:"WingedBeast",17:"Fairy",18:"Spellcaster",19:"Thunder",20:"Reptile",
         21:"Trap",22:"Magic",23:"Especial",24:"Divino",25:"Ritual?"}
ATTRS = {0:"-",1:"LIGHT",2:"DARK",3:"WATER",4:"FIRE",5:"EARTH",6:"WIND",7:"DIVINE"}
CLASES = {0:"Normal",1:"Efecto",2:"Fusion",3:"Ritual"}

def nm(i):
    return names[i*64:(i+1)*64].split(b"\x00")[0].decode("latin-1")

cards = {}      # idx -> dict
por_id = {}     # id externo -> idx
for i in range(N):
    v = struct.unpack("<I", prop[i*4:i*4+4])[0]
    ext = struct.unpack("<H", cid[i*2:i*2+2])[0]
    c = dict(idx=i, id=ext, nombre=nm(i),
             atk=((v>>9)&0x1FF)*10, defn=(v&0x1FF)*10,
             nivel=(v>>25)&0xF, tipo=TIPOS.get((v>>20)&0x1F, str((v>>20)&0x1F)),
             attr=ATTRS.get((v>>29)&0x7, str((v>>29)&0x7)),
             clase=CLASES.get((v>>18)&0x3, str((v>>18)&0x3)))
    cards[i] = c
    if ext != 0xFFFF:
        por_id[ext] = i

os.makedirs(outdir, exist_ok=True)
with open(os.path.join(outdir, "cards.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["idx","id","nombre","atk","defn","nivel","tipo","attr","clase"])
    w.writeheader()
    for i in range(N):
        if cards[i]["nombre"]:
            w.writerow(cards[i])

def leer_ydc(path):
    d = open(path, "rb").read()
    n = struct.unpack("<H", d[8:10])[0]
    main = struct.unpack("<%dH" % n, d[10:10+n*2])
    p = 10 + n*2
    nf = struct.unpack("<H", d[p:p+2])[0] if p+2 <= len(d) else 0
    fus = struct.unpack("<%dH" % nf, d[p+2:p+2+nf*2]) if nf else ()
    return main, fus

def nombre_id(e):
    i = por_id.get(e)
    return cards[i]["nombre"] if i is not None else ("??id=%d" % e)

with open(os.path.join(outdir, "mazos_cpu.txt"), "w", encoding="utf-8") as f:
    for path in sorted(glob.glob(os.path.join(base, "j", "file", "*.ydc"))):
        main, fus = leer_ydc(path)
        f.write("\n=== %s (%d cartas + %d fusion) ===\n" % (os.path.basename(path), len(main), len(fus)))
        conteo = {}
        for e in main:
            conteo[e] = conteo.get(e, 0) + 1
        for e in sorted(conteo, key=lambda x: -conteo[x]):
            i = por_id.get(e)
            c = cards.get(i)
            if c and c["tipo"] not in ("Magic", "Trap"):
                extra = " %d/%d Lv%d %s %s %s" % (c["atk"], c["defn"], c["nivel"], c["tipo"], c["attr"], c["clase"])
            elif c:
                extra = " [%s]" % c["tipo"]
            else:
                extra = ""
            f.write("  x%d %-42s%s\n" % (conteo[e], nombre_id(e), extra))
        if fus:
            f.write("  -- fusiones: %s\n" % ", ".join(nombre_id(e) for e in fus))

print("cards.csv:", sum(1 for i in range(N) if cards[i]['nombre']), "cartas con nombre de", N)
print("verificacion deck inicial: 528 =", nombre_id(528), "| 531 =", nombre_id(531), "| 77 =", nombre_id(77))
