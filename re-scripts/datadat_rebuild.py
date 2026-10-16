# Reconstruye Data.dat desde cero permitiendo ANADIR archivos nuevos al indice.
# Copia las entradas originales tal cual (comprimidas o no) y agrega las nuevas sin comprimir.
# Uso: python -I datadat_rebuild.py <original> <salida> <csv nuevos: nombre_interno;ruta_local>
import os, struct, sys

orig, out, lista = sys.argv[1], sys.argv[2], sys.argv[3]

def swap(bs):
    return bytes(((x & 0x0F) << 4) | (x >> 4) for x in bs)

nuevos = []  # (nombre_interno, ruta)
for linea in open(lista, encoding="utf-8"):
    linea = linea.strip()
    if not linea: continue
    nombre, ruta = linea.split(";", 1)
    nuevos.append((nombre, ruta))

with open(orig, "rb") as f:
    assert f.read(8) == b"KCEJYUGI"
    count = struct.unpack("<I", f.read(4))[0]
    entradas = []
    for _ in range(count):
        raw = f.read(268)
        name = swap(raw[:256]).split(b"\x00")[0].decode("latin-1")
        off, usize, csize = struct.unpack("<III", raw[256:268])
        entradas.append([name, off, usize, csize])

    existentes = {e[0].lower() for e in entradas}
    nuevos = [(n.lower(), r) for n, r in nuevos if n.lower() not in existentes]

    total = count + len(nuevos)
    tam_indice = 12 + total * 268
    with open(out, "wb") as g:
        g.write(b"KCEJYUGI")
        g.write(struct.pack("<I", total))
        g.write(b"\x00" * (total * 268))  # hueco del indice, se rellena al final
        indice = []
        # entradas originales: copia los bytes almacenados tal cual
        for name, off, usize, csize in entradas:
            f.seek(off)
            data = f.read(csize)
            indice.append((name, g.tell(), usize, csize))
            g.write(data)
        # nuevas: sin comprimir (usize == stored)
        for name, ruta in nuevos:
            data = open(ruta, "rb").read()
            indice.append((name, g.tell(), len(data), len(data)))
            g.write(data)
        # El juego busca en el indice con busqueda BINARIA: debe quedar ordenado por nombre
        # (bytes en minusculas, como el original). Si las nuevas se anexan al final, son invisibles.
        indice.sort(key=lambda e: e[0].lower().encode("latin-1"))
        g.seek(12)
        for name, off, usize, csize in indice:
            nb = name.encode("latin-1")[:255]
            g.write(swap(nb + b"\x00" * (256 - len(nb))))
            g.write(struct.pack("<III", off, usize, csize))
print("reconstruido: %d originales + %d nuevos = %d entradas" % (count, len(nuevos), total))
