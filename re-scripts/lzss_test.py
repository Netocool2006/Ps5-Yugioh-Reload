# Prueba variantes de LZSS contra un archivo de Data.dat con tamano conocido
import sys

path = sys.argv[1]
off, stored, expected = int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])

with open(path, "rb") as f:
    f.seek(off)
    data = f.read(stored)

def lzss(data, N=4096, F=18, THRESHOLD=2, init=0x20, startpos=None, lsb_first=True):
    if startpos is None:
        startpos = N - F
    window = bytearray([init]) * 1 * 0 + bytearray([init] * N)
    r = startpos
    out = bytearray()
    i = 0
    flags = 0
    nbits = 0
    while i < len(data):
        if nbits == 0:
            flags = data[i]; i += 1; nbits = 8
        bit = (flags & 1) if lsb_first else (flags & 0x80)
        if lsb_first:
            flags >>= 1
        else:
            flags = (flags << 1) & 0xFF
        nbits -= 1
        if bit:  # literal
            if i >= len(data): break
            c = data[i]; i += 1
            out.append(c)
            window[r] = c; r = (r + 1) % N
        else:  # backref
            if i + 1 >= len(data): break
            lo, hi = data[i], data[i+1]; i += 2
            pos = lo | ((hi & 0xF0) << 4)
            length = (hi & 0x0F) + THRESHOLD + 1
            for k in range(length):
                c = window[(pos + k) % N]
                out.append(c)
                window[r] = c; r = (r + 1) % N
    return bytes(out)

for lsb in (True, False):
    for init in (0x20, 0x00):
        res = lzss(data, init=init, lsb_first=lsb)
        tag = "lsb=%s init=%#x" % (lsb, init)
        print(tag, "-> len", len(res), "(esperado %d)" % expected)
        if len(res) == expected:
            print("  MATCH! primeros 200 bytes:")
            print("  ", repr(res[:200]))
