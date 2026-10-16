# Analisis archivo por archivo de Yu-Gi-Oh! Power of Chaos - Joey the Passion.
# Recorre cada entrada de Data.dat (indice + firma de contenido), Voice.dat, Region.dat,
# system.dat, Deck.ydc y el PE del ejecutable. Salida: re-output\analisis\*.txt + log DEBUG.
# Uso: python -I analisis_total.py
import collections, hashlib, logging, os, struct, sys, time

BASE = r"D:\Yugi-Reload"
APP = os.path.join(BASE, "juego-extraido", "app")
SALIDA = os.path.join(BASE, "re-output", "analisis")
os.makedirs(SALIDA, exist_ok=True)

log = logging.getLogger("analisis")
log.setLevel(logging.DEBUG)
_fh = logging.FileHandler(os.path.join(SALIDA, "analisis_%s.log" % time.strftime("%Y%m%d_%H%M%S")), encoding="utf-8")
_fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)-7s] %(funcName)s | %(message)s"))
log.addHandler(_fh)
_ch = logging.StreamHandler(sys.stdout); _ch.setLevel(logging.INFO)
log.addHandler(_ch)

def swap(bs):
    return bytes(((x & 0x0F) << 4) | (x >> 4) for x in bs)

def lzss(src, usize):
    """LZSS de Data.dat: ventana 4096 iniciada en CEROS (no 0x20 como el LZSS clasico), r = 0xFEE.
    Verificado contra datadat_extract.py (bateria D10)."""
    win = bytearray(4096); r = 0xFEE
    out = bytearray(); i = 0; flags = 0
    while len(out) < usize and i < len(src):
        flags >>= 1
        if not flags & 0x100:
            flags = src[i] | 0xFF00; i += 1
            if i >= len(src): break
        if flags & 1:
            c = src[i]; i += 1
            out.append(c); win[r] = c; r = (r + 1) & 0xFFF
        else:
            if i + 1 >= len(src): break
            a, b = src[i], src[i + 1]; i += 2
            pos = a | ((b & 0xF0) << 4); ln = (b & 0x0F) + 3
            for k in range(ln):
                c = win[(pos + k) & 0xFFF]
                out.append(c); win[r] = c; r = (r + 1) & 0xFFF
    return bytes(out[:usize])

FIRMAS = [
    (b"BM", "BMP"), (b"\x89PNG", "PNG"), (b"\xff\xd8\xff", "JPEG"), (b"RIFF", "RIFF(WAV/AVI)"),
    (b"OggS", "OGG"), (b"DDS ", "DDS"), (b"MZ", "PE/DLL"), (b"KCEJYUGI", "contenedor KCEJ"),
    (b"\x00\x00\x02\x00", "TGA"), (b"\x00\x00\x0a\x00", "TGA-RLE"), (b"GIF8", "GIF"),
    (b"<", "texto/XML"), (b"\x01\xcc\xcc\xcc", "YDC"), (b"\x01\x00\x00\x00", "YDC/bin"),
]

def firma(d):
    for mag, nom in FIRMAS:
        if d.startswith(mag): return nom
    if d and all(32 <= c < 127 or c in (9, 10, 13) for c in d[:64]): return "texto"
    return "bin:" + d[:4].hex()

def leer_indice(path):
    f = open(path, "rb")
    if f.read(8) != b"KCEJYUGI": raise ValueError("firma invalida: " + path)
    n = struct.unpack("<I", f.read(4))[0]
    ents = []
    for i in range(n):
        raw = f.read(268)
        nombre = swap(raw[:256]).split(b"\x00")[0].decode("latin-1")
        off, us, st = struct.unpack("<III", raw[256:268])
        ents.append((nombre, off, us, st))
    return f, ents

def analizar_datadat(path, etiqueta):
    f, ents = leer_indice(path)
    tam = os.path.getsize(path)
    log.info("[%s] %s: %d entradas, %d bytes", etiqueta, path, len(ents), tam)
    por_carpeta = collections.Counter(); por_ext = collections.Counter()
    por_firma = collections.Counter(); comp = 0; problemas = []
    bytes_ext = collections.Counter()
    filas = []
    for i, (nom, off, us, st) in enumerate(ents):
        partes = nom.lower().split("\\")
        carpeta = "\\".join(partes[:-1]) or "(raiz)"
        ext = os.path.splitext(partes[-1])[1] or "(sin ext)"
        por_carpeta[carpeta] += 1; por_ext[ext] += 1; bytes_ext[ext] += us
        if off + st > tam:
            problemas.append("entrada %d %s fuera de rango (off=%d st=%d)" % (i, nom, off, st)); continue
        f.seek(off); cab = f.read(min(st, 512))
        if us != st:
            comp += 1
            try:
                f.seek(off); cab = lzss(f.read(min(st, 2048)), min(us, 512))
            except Exception as e:
                problemas.append("LZSS fallo en %s: %s" % (nom, e))
        fi = firma(cab)
        por_firma[(ext, fi)] += 1
        filas.append("%5d  %-48s off=%-10d usize=%-9d stored=%-9d %s %s" %
                     (i, nom, off, us, st, "LZSS" if us != st else "raw ", fi))
        log.debug("entrada %d %s off=%d us=%d st=%d firma=%s", i, nom, off, us, st, fi)
    open(os.path.join(SALIDA, "datadat_%s_entradas.txt" % etiqueta), "w", encoding="utf-8").write("\n".join(filas))
    with open(os.path.join(SALIDA, "datadat_%s_resumen.txt" % etiqueta), "w", encoding="utf-8") as w:
        w.write("%s\nentradas=%d comprimidas(LZSS)=%d bytes=%d\n\n" % (path, len(ents), comp, tam))
        w.write("== por carpeta ==\n")
        for k, v in sorted(por_carpeta.items()): w.write("  %-40s %5d\n" % (k, v))
        w.write("\n== por extension (cantidad, bytes descomprimidos) ==\n")
        for k, v in por_ext.most_common(): w.write("  %-12s %5d  %12d\n" % (k, v, bytes_ext[k]))
        w.write("\n== extension x firma de contenido ==\n")
        for (e, fi), v in sorted(por_firma.items()): w.write("  %-12s %-22s %5d\n" % (e, fi, v))
        w.write("\n== problemas (%d) ==\n" % len(problemas))
        for p in problemas: w.write("  " + p + "\n")
    for p in problemas: log.error(p)
    log.info("[%s] carpetas=%d extensiones=%d comprimidas=%d problemas=%d",
             etiqueta, len(por_carpeta), len(por_ext), comp, len(problemas))
    f.close()
    return ents

def analizar_pe(path):
    d = open(path, "rb").read()
    pe = struct.unpack("<I", d[0x3C:0x40])[0]
    maquina, nsec = struct.unpack("<HH", d[pe + 4:pe + 8])
    opt = pe + 24
    magic = struct.unpack("<H", d[opt:opt + 2])[0]
    entry = struct.unpack("<I", d[opt + 16:opt + 20])[0]
    base = struct.unpack("<I", d[opt + 28:opt + 32])[0]
    dllch = struct.unpack("<H", d[opt + 70:opt + 72])[0]
    ndirs = struct.unpack("<I", d[opt + 92:opt + 96])[0]
    dirs = [struct.unpack("<II", d[opt + 96 + 8 * k:opt + 104 + 8 * k]) for k in range(ndirs)]
    secs = []
    so = opt + struct.unpack("<H", d[pe + 20:pe + 22])[0]
    for k in range(nsec):
        s = d[so + 40 * k:so + 40 * k + 40]
        secs.append((s[:8].rstrip(b"\0").decode(), *struct.unpack("<IIII", s[8:24]),
                     struct.unpack("<I", s[36:40])[0]))
    def rva2off(rva):
        for nom, vs, va, rs, ro, ch in secs:
            if va <= rva < va + max(vs, rs): return rva - va + ro
        return None
    lineas = ["PE %s maquina=0x%X magic=0x%X entry=0x%X base=0x%X DllCharacteristics=0x%04X (ASLR=%s)" %
              (path, maquina, magic, base + entry, base, dllch, bool(dllch & 0x40)), "", "== secciones =="]
    for nom, vs, va, rs, ro, ch in secs:
        lineas.append("  %-8s VA=0x%08X vsize=0x%07X rawoff=0x%07X rawsize=0x%07X flags=0x%08X" %
                      (nom, base + va, vs, ro, rs, ch))
    # importaciones
    lineas.append(""); lineas.append("== importaciones ==")
    irva = dirs[1][0]; io = rva2off(irva); total = 0
    while io is not None:
        oft, ts, fc, nrva, ft = struct.unpack("<IIIII", d[io:io + 20])
        if nrva == 0: break
        dll = d[rva2off(nrva):].split(b"\0")[0].decode()
        funcs = []; to = rva2off(oft or ft)
        while to is not None:
            v = struct.unpack("<I", d[to:to + 4])[0]
            if v == 0: break
            if v & 0x80000000: funcs.append("#%d" % (v & 0xFFFF))
            else: funcs.append(d[rva2off(v) + 2:].split(b"\0")[0].decode())
            to += 4
        total += len(funcs)
        lineas.append("  %s (%d): %s" % (dll, len(funcs), ", ".join(funcs)))
        log.debug("import %s: %d funciones", dll, len(funcs))
        io += 20
    # cadenas ASCII >= 6 con su VA
    lineas.append(""); lineas.append("== cadenas relevantes (rutas, formatos, claves) ==")
    claves = (b"data", b".ydc", b".dat", b"Software", b"%", b"Joey", b"Konami", b"KONAMI", b".bmp", b".wav",
              b".ogg", b"Common", b"system", b"Deck", b"Region", b"Voice", b".tga", b".png", b"Direct", b"\\")
    cur = bytearray(); ini = 0; n_cad = 0
    for i, c in enumerate(d):
        if 32 <= c < 127:
            if not cur: ini = i
            cur.append(c)
        else:
            if len(cur) >= 6 and any(k in cur for k in claves):
                va = None
                for nom, vs, vva, rs, ro, ch in secs:
                    if ro <= ini < ro + rs: va = base + vva + (ini - ro)
                lineas.append("  0x%08X %s" % (va or 0, cur.decode()))
                n_cad += 1
            cur = bytearray()
    open(os.path.join(SALIDA, "exe_pe.txt"), "w", encoding="utf-8").write("\n".join(lineas))
    log.info("[exe] secciones=%d importaciones=%d cadenas relevantes=%d ASLR=%s",
             len(secs), total, n_cad, bool(dllch & 0x40))

def analizar_pequenos():
    out = []
    r = open(os.path.join(APP, "Region.dat"), "rb").read()
    out.append("Region.dat: %d byte(s) = %s" % (len(r), r.hex()))
    dk = open(os.path.join(APP, "Deck.ydc"), "rb").read()
    n = struct.unpack("<H", dk[8:10])[0]
    out.append("Deck.ydc: %d B, header=%s, main=%d" % (len(dk), dk[:8].hex(), n))
    sd = os.path.join(BASE, "juego-extraido", "Yu-Gi-Oh! Power of Chaos Common", "system.dat")
    if os.path.exists(sd):
        s = open(sd, "rb").read()
        out.append("system.dat: %d B sha1=%s" % (len(s), hashlib.sha1(s).hexdigest()))
        out.append("  primeros 64: " + s[:64].hex(" "))
        nz = sum(1 for b in s if b)
        out.append("  bytes no nulos: %d (%.0f%%)" % (nz, 100.0 * nz / len(s)))
        # histograma de bloques de 256
        for k in range(0, len(s), 256):
            bl = s[k:k + 256]
            out.append("  bloque 0x%04X: no-nulos=%3d  %s" % (k, sum(1 for b in bl if b), bl[:24].hex(" ")))
    v = os.path.join(APP, "Voice.dat")
    with open(v, "rb") as f:
        cab = f.read(64)
    out.append("Voice.dat: %d B cabecera=%s" % (os.path.getsize(v), cab.hex(" ")))
    if cab.startswith(b"KCEJYUGI"):
        f, ents = leer_indice(v)
        exts = collections.Counter(os.path.splitext(e[0].lower())[1] for e in ents)
        out.append("  contenedor KCEJ con %d entradas: %s" % (len(ents), dict(exts)))
        for e in ents[:15]: out.append("   %s us=%d st=%d" % (e[0], e[2], e[3]))
        f.close()
    open(os.path.join(SALIDA, "archivos_pequenos.txt"), "w", encoding="utf-8").write("\n".join(out))
    for o in out[:6]: log.info(o)

if __name__ == "__main__":
    t0 = time.time()
    analizar_datadat(os.path.join(APP, "Data.dat.original"), "original")
    analizar_datadat(os.path.join(APP, "Data.dat"), "sesion")
    analizar_pe(os.path.join(APP, "Joey_Pc.exe"))
    analizar_pequenos()
    log.info("analisis completo en %.1f s -> %s", time.time() - t0, SALIDA)
