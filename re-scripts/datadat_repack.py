# Parchea Data.dat: reemplaza archivos internos por versiones nuevas.
# Los reemplazos se guardan SIN comprimir (usize == stored => el motor los lee tal cual)
# y se anexan al final del archivo, actualizando solo su entrada del indice.
# Uso: python -I datadat_repack.py <Data.dat original> <Data.dat salida> <carpeta mods>
import os, shutil, struct, sys

orig, out, modsdir = sys.argv[1], sys.argv[2], sys.argv[3]

def swap(bs):  # nibble-swap, es involucion: sirve para codificar y decodificar
    return bytes(((x & 0x0F) << 4) | (x >> 4) for x in bs)

mods = {}
for root, _, files in os.walk(modsdir):
    for fn in files:
        p = os.path.join(root, fn)
        rel = os.path.relpath(p, modsdir).replace("/", "\\")
        mods[rel.lower()] = p
if not mods:
    sys.exit("no hay archivos en " + modsdir)

if os.path.abspath(orig) != os.path.abspath(out):
    print("copiando base...")
    shutil.copyfile(orig, out)

with open(out, "r+b") as f:
    assert f.read(8) == b"KCEJYUGI"
    count = struct.unpack("<I", f.read(4))[0]
    base = 12
    crudos = 0
    aplicados = set()
    for i in range(count):
        f.seek(base + i * 268)
        raw = f.read(268)
        name = swap(raw[:256]).split(b"\x00")[0].decode("latin-1")
        off, usize, csize = struct.unpack("<III", raw[256:268])
        if usize == csize:
            crudos += 1
        key = name.lower()
        if key in mods:
            data = open(mods[key], "rb").read()
            f.seek(0, 2)
            newoff = f.tell()
            f.write(data)
            f.seek(base + i * 268 + 256)
            f.write(struct.pack("<III", newoff, len(data), len(data)))
            aplicados.add(key)
            print("parcheado: %s  %d bytes @ 0x%x (antes %d/%d @ 0x%x)"
                  % (name, len(data), newoff, usize, csize, off))
    print("entradas ya crudas en el original: %d de %d" % (crudos, count))
    faltan = set(mods) - aplicados
    if faltan:
        print("AVISO, no estaban en el indice:", sorted(faltan))
    print("mods aplicados: %d de %d" % (len(aplicados), len(mods)))
