# Parsea el indice de Data.dat (formato KCEJYUGI) y lista sus archivos
import struct, sys

path = sys.argv[1]
out = sys.argv[2]

def unswap(b):
    # nombres ofuscados con nibbles invertidos
    return bytes(((x & 0x0F) << 4) | (x >> 4) for x in b)

with open(path, "rb") as f:
    magic = f.read(8)
    assert magic == b"KCEJYUGI", magic
    count = struct.unpack("<I", f.read(4))[0]
    entries = []
    for _ in range(count):
        raw = f.read(268)
        name = unswap(raw[:256]).split(b"\x00")[0].decode("latin-1")
        off, usize, csize = struct.unpack("<III", raw[256:268])
        entries.append((name, off, usize, csize))

with open(out, "w", encoding="utf-8") as f:
    f.write("total\t%d\n" % count)
    for name, off, usize, csize in entries:
        f.write("%s\toff=%d\tsize=%d\tstored=%d\n" % (name, off, usize, csize))
print("entradas:", count)
