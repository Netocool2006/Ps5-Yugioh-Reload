# Verifica Data.dat.full: compara entradas contra la extraccion original y decodifica los nuevos mazos
import os, random, struct, sys

full = r"D:\Yugi-Reload\juego-extraido\app\Data.dat.full"
extr = r"D:\Yugi-Reload\datadat-extraido"

def unswap(b):
    return bytes(((x & 0x0F) << 4) | (x >> 4) for x in b)

def lzss(data, expected):
    N = 4096
    window = bytearray(N)
    r = N - 18
    out = bytearray()
    i = 0
    flags, nbits = 0, 0
    while i < len(data) and len(out) < expected:
        if nbits == 0:
            flags = data[i]; i += 1; nbits = 8
        bit = flags & 1
        flags >>= 1; nbits -= 1
        if bit:
            if i >= len(data): break
            c = data[i]; i += 1
            out.append(c); window[r] = c; r = (r + 1) % N
        else:
            if i + 1 >= len(data): break
            lo, hi = data[i], data[i+1]; i += 2
            pos = lo | ((hi & 0xF0) << 4)
            length = (hi & 0x0F) + 3
            for k in range(length):
                c = window[(pos + k) % N]
                out.append(c); window[r] = c; r = (r + 1) % N
    return bytes(out)

f = open(full, "rb")
assert f.read(8) == b"KCEJYUGI"
count = struct.unpack("<I", f.read(4))[0]
entradas = []
for _ in range(count):
    raw = f.read(268)
    name = unswap(raw[:256]).split(b"\x00")[0].decode("latin-1")
    off, usize, csize = struct.unpack("<III", raw[256:268])
    entradas.append((name, off, usize, csize))
print("entradas:", count)

# muestra aleatoria de 120 originales comparadas byte a byte con la extraccion
rng = random.Random(1)
originales = [e for e in entradas if not e[0].lower().startswith("j\\file\\cpu_1") and
              not e[0].lower().startswith("j\\file\\cpu_2") and not e[0].lower().startswith("j\\file\\cpu_3")
              or e[0].lower() in ("j\\file\\cpu_000.ydc",)]
orig_set = [e for e in entradas if int(e[0][11:14]) < 100] if False else None
muestra = rng.sample(entradas[:3592], 120)
mal = 0
for name, off, usize, csize in muestra:
    f.seek(off)
    data = f.read(csize)
    if usize != csize:
        data = lzss(data, usize)
    ruta = os.path.join(extr, name.replace("\\", "/"))
    esperado = open(ruta, "rb").read()
    if data != esperado:
        mal += 1
        print("DIFIERE:", name)
print("muestra originales: 120 comparadas,", mal, "diferencias")

# los 546 nuevos: decodifica como mazo
nuevos = entradas[3592:]
mal2 = 0
for name, off, usize, csize in nuevos:
    f.seek(off)
    d = f.read(csize)
    try:
        n = struct.unpack("<H", d[8:10])[0]
        p = 10 + n*2
        nf = struct.unpack("<H", d[p:p+2])[0]
        p += 2 + nf*2
        n3 = struct.unpack("<H", d[p:p+2])[0]
        assert p + 2 + n3*2 == len(d) and 40 <= n <= 45
    except Exception as ex:
        mal2 += 1
        print("NUEVO MAL:", name, ex)
print("nuevos: %d verificados, %d mal" % (len(nuevos), mal2))
print("primero:", nuevos[0][0], "| ultimo:", nuevos[-1][0])
