# Analiza la cabecera de los .ydc para descubrir si el u32 es checksum
import glob, os, struct, sys

paths = sorted(glob.glob(r"D:\Yugi-Reload\datadat-extraido\j\file\*.ydc"))
paths.append(r"D:\Yugi-Reload\juego-extraido\app\Deck.ydc")

for path in paths:
    d = open(path, "rb").read()
    hdr = d[:10]
    u32 = struct.unpack("<I", d[4:8])[0]
    n = struct.unpack("<H", d[8:10])[0]
    main = struct.unpack("<%dH" % n, d[10:10+n*2])
    p = 10 + n*2
    nf = struct.unpack("<H", d[p:p+2])[0] if p+2 <= len(d) else 0
    fus = struct.unpack("<%dH" % nf, d[p+2:p+2+nf*2]) if nf else ()
    cand = {
        "suma_main": sum(main) & 0xFFFFFFFF,
        "suma_todo": (sum(main)+sum(fus)) & 0xFFFFFFFF,
        "suma_bytes": sum(d[8:]) & 0xFFFFFFFF,
        "n": n, "nf": nf, "len": len(d),
    }
    match = [k for k, v in cand.items() if v == u32]
    print("%-14s hdr=%s u32=%-10d n=%-3d nf=%-3d %s" % (
        os.path.basename(path), hdr.hex(), u32, n, nf,
        ("MATCH: " + ",".join(match)) if match else
        "cands: sm=%d st=%d sb=%d" % (cand["suma_main"], cand["suma_todo"], cand["suma_bytes"])))
