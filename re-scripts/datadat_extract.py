# Extrae todos los archivos de Data.dat (formato KCEJYUGI, nombres nibble-swap, LZSS)
import os, struct, sys

src, dstdir = sys.argv[1], sys.argv[2]

def unswap(b):
    return bytes(((x & 0x0F) << 4) | (x >> 4) for x in b)

def lzss(data, expected):
    N, THRESHOLD = 4096, 2
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
            length = (hi & 0x0F) + THRESHOLD + 1
            for k in range(length):
                c = window[(pos + k) % N]
                out.append(c); window[r] = c; r = (r + 1) % N
    return bytes(out)

with open(src, "rb") as f:
    assert f.read(8) == b"KCEJYUGI"
    count = struct.unpack("<I", f.read(4))[0]
    entries = []
    for _ in range(count):
        raw = f.read(268)
        name = unswap(raw[:256]).split(b"\x00")[0].decode("latin-1")
        off, usize, csize = struct.unpack("<III", raw[256:268])
        entries.append((name, off, usize, csize))

    errores = 0
    for n, (name, off, usize, csize) in enumerate(entries):
        f.seek(off)
        data = f.read(csize)
        if usize != csize:
            data = lzss(data, usize)
            if len(data) != usize:
                print("TAMANO RARO:", name, len(data), "esperado", usize)
                errores += 1
        rel = name.replace("\\", "/")
        dest = os.path.join(dstdir, rel)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "wb") as g:
            g.write(data)
        if n % 500 == 0:
            print("%d/%d" % (n, count))
    print("listo:", count, "archivos,", errores, "errores")
