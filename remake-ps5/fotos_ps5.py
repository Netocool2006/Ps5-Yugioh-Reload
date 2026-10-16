# Ciclo de fotos de la consola: baja las fotos que el juego guardo en /data/homebrew/<TITULO>/capturas/ (las saca
# si existe capturas.txt), las convierte a PNG en remake-ps5/capturas/ps5/ (reemplaza las del ciclo anterior) con
# un mosaico, y BORRA las de la PS5 para no llenarla de basura. Solo toca esa carpeta del juego.
# Uso: python -I fotos_ps5.py [PPSA77001] [--no-borrar]
import ftplib, glob, os, re, sys
from PIL import Image
PS5_IP = open(__import__("os").path.join(__import__("os").path.dirname(__import__("os").path.abspath(__file__)), "consola_ip.txt")).read().strip()   # IP de la consola: archivo local (no va al repo)

titulo = next((a for a in sys.argv[1:] if re.fullmatch(r"PPSA\d{5}", a)), "PPSA77001")
remoto = "/data/homebrew/%s/capturas" % titulo
local = os.path.join(os.path.dirname(os.path.abspath(__file__)), "capturas", "ps5")
os.makedirs(local, exist_ok=True)
for viejo in glob.glob(os.path.join(local, "*.png")) + glob.glob(os.path.join(local, "*.mp4")) + glob.glob(os.path.join(local, "*.jpg")):
    try:
        os.remove(viejo)
    except OSError:
        pass

ftp = ftplib.FTP()
ftp.connect(PS5_IP, 2121, timeout=60)
ftp.login("anonymous", "codex")
ftp.cwd(remoto)
filas = []
ftp.retrlines("LIST", filas.append)
nombres = sorted(f.split(None, 8)[8] for f in filas if f.endswith(".ppm"))
# fotos de inspeccion (JPG): se bajan tal cual y se borran en la PS5
insp = sorted(f.split(None, 8)[8] for f in filas if f.endswith(".jpg"))
for n in insp:
    with open(os.path.join(local, n), "wb") as o:
        ftp.retrbinary("RETR " + n, o.write)
    if "--no-borrar" not in sys.argv:
        r = ftp.sendcmd("DELE %s/%s" % (remoto, n))
        assert r.startswith("2"), r
for n in nombres:
    tmp = os.path.join(local, n)
    with open(tmp, "wb") as o:
        ftp.retrbinary("RETR " + n, o.write)
    Image.open(tmp).save(tmp[:-4] + ".png")
    os.remove(tmp)
    if "--no-borrar" not in sys.argv:
        r = ftp.sendcmd("DELE %s/%s" % (remoto, n))   # ftpsrv contesta 226
        assert r.startswith("2"), r
# video: capturas/video/NNNN.jpg (si el juego lo grabo) -> capturas/ps5/video/, MP4 para el usuario y hojas de
# cuadros para revisar; tambien se borran en la PS5
# cada video en su carpeta nueva; las de ciclos anteriores se borran si Windows lo permite (alguna puede
# quedar tomada por otro programa un rato)
import shutil, time as _t
for vieja in glob.glob(os.path.join(local, "video*")):
    if os.path.isdir(vieja):
        shutil.rmtree(vieja, ignore_errors=True)
carpeta_video = os.path.join(local, "video_" + _t.strftime("%H%M%S"))
cuadros = []
try:
    ftp.cwd(remoto + "/video")
    filas_v = []
    ftp.retrlines("LIST", filas_v.append)
    cuadros = sorted(f.split(None, 8)[8] for f in filas_v if f.endswith(".jpg"))
except ftplib.error_perm:
    pass
if cuadros:
    os.makedirs(carpeta_video, exist_ok=True)
    for n in cuadros:
        with open(os.path.join(carpeta_video, n), "wb") as o:
            ftp.retrbinary("RETR " + n, o.write)
        if "--no-borrar" not in sys.argv:
            r = ftp.sendcmd("DELE %s/video/%s" % (remoto, n))
            assert r.startswith("2"), r
ftp.quit()
if cuadros:
    import subprocess
    fps = 10   # el que pidio capturas.txt ("video N"); se lee de la consola
    try:
        lineas = []
        ftp2 = ftplib.FTP(); ftp2.connect(PS5_IP, 2121, timeout=30); ftp2.login("anonymous", "codex")
        ftp2.retrlines("RETR /data/homebrew/%s/capturas.txt" % titulo, lineas.append); ftp2.quit()
        for l in lineas:
            if l.strip().startswith("video"):
                fps = float(l.split()[1])
    except Exception:
        pass
    r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", "%g" % fps, "-start_number", str(int(cuadros[0][:4])),
                        "-i", os.path.join(carpeta_video, "%04d.jpg"), "-c:v", "libx264", "-pix_fmt", "yuv420p",
                        os.path.join(local, "video_ps5.mp4")], capture_output=True, text=True)
    if r.returncode != 0:
        print("aviso: no se pudo armar el MP4 (los cuadros si quedaron):", r.stderr.strip()[:300])
    # hojas de cuadros: 4 columnas x 4 filas de 480x270, con el segundo de cada cuadro
    from PIL import ImageDraw
    por_hoja = 16
    for h in range(0, len(cuadros), por_hoja):
        grupo = cuadros[h:h + por_hoja]
        hoja = Image.new("RGB", (4 * 480, 4 * 270))
        for i, n in enumerate(grupo):
            im = Image.open(os.path.join(carpeta_video, n)).resize((480, 270))
            ImageDraw.Draw(im).text((8, 6), "%.1f s" % (int(n[:4]) / fps), fill=(255, 255, 0))
            hoja.paste(im, ((i % 4) * 480, (i // 4) * 270))
        hoja.save(os.path.join(local, "video_hoja_%02d.png" % (h // por_hoja + 1)))
    print(len(cuadros), "cuadros de video -> video_ps5.mp4 y", (len(cuadros) + por_hoja - 1) // por_hoja, "hojas")
if nombres:
    ims = [Image.open(os.path.join(local, n[:-4] + ".png")).resize((960, 540)) for n in nombres]
    filas_m = (len(ims) + 1) // 2
    m = Image.new("RGB", (1920, 540 * filas_m))
    for i, im in enumerate(ims):
        m.paste(im, ((i % 2) * 960, (i // 2) * 540))
    m.save(os.path.join(local, "mosaico_ps5.png"))
print(len(nombres), "fotos ->", local, "| borradas en la PS5:", "no" if "--no-borrar" in sys.argv else "si")

# hojas de inspeccion: una por personaje (sus 3 angulos) y una por cada ataque repetido de cerca
if insp:
    from PIL import ImageDraw
    grupos = {}
    for n in insp:
        clave = "_".join(n.split("_")[:3]) if n.startswith("insp_ataque_") else n.rsplit("_", 1)[0]
        grupos.setdefault(clave, []).append(n)
    for clave, ns in grupos.items():
        cols = 3
        filas_h = (len(ns) + cols - 1) // cols
        hoja = Image.new("RGB", (cols * 960, filas_h * 540))
        for i, n in enumerate(ns):
            im = Image.open(os.path.join(local, n)).resize((960, 540))
            ImageDraw.Draw(im).text((10, 8), n[:-4], fill=(255, 255, 0))
            hoja.paste(im, ((i % cols) * 960, (i // cols) * 540))
        hoja.save(os.path.join(local, "hoja_%s.png" % clave))
    print(len(insp), "fotos de inspeccion ->", len(grupos), "hojas")

# cuadrantes (pedido del usuario, en cada ciclo): cada foto se divide en 4 bloques y cada bloque se amplia al
# doble, para revisar los detalles (caras, manos, armas) bloque por bloque
cuadr = os.path.join(local, "cuadrantes")
import shutil as _sh
_sh.rmtree(cuadr, ignore_errors=True)
os.makedirs(cuadr, exist_ok=True)
todas = [os.path.join(local, n[:-4] + ".png") for n in nombres] + [os.path.join(local, n) for n in insp]
for ruta in todas:
    im = Image.open(ruta).convert("RGB")
    w, h = im.size
    base_n = os.path.splitext(os.path.basename(ruta))[0]
    for k, (x, y) in enumerate(((0, 0), (w // 2, 0), (0, h // 2), (w // 2, h // 2)), 1):
        im.crop((x, y, x + w // 2, y + h // 2)).resize((w, h), Image.LANCZOS).save(os.path.join(cuadr, "%s_q%d.png" % (base_n, k)))
print(len(todas), "fotos ->", 4 * len(todas), "cuadrantes ampliados en", cuadr)
