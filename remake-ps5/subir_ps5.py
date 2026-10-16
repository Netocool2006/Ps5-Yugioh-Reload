# Sube una carpeta de titulo (dist/<TITLE_ID>) a /data/homebrew/<TITLE_ID>/ de la PS5 por el FTP de ftpsrv (2121).
# Mismo cuidado que el deploy de la plantilla, sin el payload de control: cada archivo sube con nombre oculto
# ".upload" y reemplaza al destino solo al terminar; eboot.bin y sce_sys/param.json van al final; los que ya estan
# con el mismo tamano se saltan (salvo eboot.bin). Nunca borra nada ni toca otra ruta.
# Uso: python -I subir_ps5.py <carpeta PPSAxxxxx> [--simular]
import ftplib, os, posixpath, sys
PS5_IP = open(__import__("os").path.join(__import__("os").path.dirname(__import__("os").path.abspath(__file__)), "consola_ip.txt")).read().strip()   # IP de la consola: archivo local (no va al repo)

PS5, PUERTO = PS5_IP, 2121
carpeta = os.path.abspath(sys.argv[1])
simular = "--simular" in sys.argv
titulo = os.path.basename(carpeta)
assert titulo.startswith("PPSA") and len(titulo) == 9, titulo
destino = "/data/homebrew/" + titulo

archivos = []
for raiz, _, nombres in os.walk(carpeta):
    for n in nombres:
        archivos.append(os.path.relpath(os.path.join(raiz, n), carpeta).replace("\\", "/"))
ultimos = ["eboot.bin", "sce_sys/param.json"]
assert all(u in archivos for u in ultimos), "faltan eboot.bin o sce_sys/param.json"
archivos = sorted(a for a in archivos if a not in ultimos) + ultimos
print("destino ftp://%s:%d%s/ -> %d archivos, %.1f MB" % (PS5, PUERTO, destino, len(archivos),
      sum(os.path.getsize(os.path.join(carpeta, a)) for a in archivos) / 1e6))
if simular:
    print("simulacion: no se conecto a la consola")
    sys.exit(0)

ftp = ftplib.FTP()
ftp.connect(PS5, PUERTO, timeout=30)
ftp.login("anonymous", "codex")
ftp.voidcmd("TYPE I")
hechas = set()


def asegurar(ruta):
    partes = ruta.strip("/").split("/")
    for i in range(1, len(partes) + 1):
        d = "/" + "/".join(partes[:i])
        if d in hechas:
            continue
        try:
            ftp.mkd(d)
        except ftplib.error_perm:
            pass  # ya existe
        hechas.add(d)


def es_self(ruta):
    """SELF de PS4/PS5 (eboot.bin, .prx): firma 4F 15 3D 1D o 54 14 F5 EE."""
    with open(ruta, "rb") as f:
        return f.read(4) in (b"\x4f\x15\x3d\x1d", b"\x54\x14\xf5\xee")


def tam_remoto(ruta):
    try:
        return ftp.size(ruta)
    except ftplib.all_errors:
        return None


for i, a in enumerate(archivos, 1):
    local = os.path.join(carpeta, a)
    remoto = posixpath.join(destino, a)
    asegurar(posixpath.dirname(remoto))
    tam = os.path.getsize(local)
    if a != "eboot.bin" and not es_self(local) and tam_remoto(remoto) == tam:
        print("[%d/%d] igual, se salta: %s" % (i, len(archivos), a))
        continue
    temporal = posixpath.join(posixpath.dirname(remoto), "." + posixpath.basename(remoto) + ".upload")
    with open(local, "rb") as f:
        ftp.storbinary("STOR " + temporal, f, blocksize=1 << 20)
    remoto_tam = tam_remoto(temporal)
    if es_self(local):
        # ftpsrv descifra al vuelo los SELF al leerlos (SIZE/RETR dan el ELF de dentro, mas grande): basta con
        # que exista y no este vacio (el libc.prx del hola mundo, que funciona, se ve igual)
        if not remoto_tam:
            sys.exit("%s no quedo en la consola: se detiene" % a)
    elif remoto_tam != tam:
        sys.exit("tamano distinto tras subir %s: se detiene" % a)
    ftp.rename(temporal, remoto)
    print("[%d/%d] %s (%.1f MB)" % (i, len(archivos), a, tam / 1e6))

presentes = []  # ftpsrv no conoce NLST: se usa LIST
ftp.cwd(destino)
ftp.retrlines("LIST", presentes.append)
ftp.quit()
assert any(p.endswith("eboot.bin") for p in presentes), "eboot.bin no aparece en la consola"
print("listo:", destino)
