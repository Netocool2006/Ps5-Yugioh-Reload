# Vacia /data/homebrew/<TITLE_ID>/ en la PS5 por FTP, dejando la carpeta (ShadowMountPlus la usa de origen).
# Solo borra dentro de esa carpeta; se niega con cualquier otra ruta. Uso: python -I vaciar_titulo_ps5.py PPSA77001
import ftplib, posixpath, re, sys
titulo = sys.argv[1]
assert re.fullmatch(r"PPSA\d{5}", titulo), titulo
raiz = "/data/homebrew/" + titulo

# freno: con un juego abierto (un proceso eboot.bin) no se toca nada; lectura de Payload Manager (solo lectura)
import json, urllib.request
PS5_IP = open(__import__("os").path.join(__import__("os").path.dirname(__import__("os").path.abspath(__file__)), "consola_ip.txt")).read().strip()   # IP de la consola: archivo local (no va al repo)
procesos = json.loads(urllib.request.urlopen("http://%s:8084/processes_list" % PS5_IP, timeout=10).read())
procesos = procesos if isinstance(procesos, list) else procesos.get("processes", [])
abiertos = [p for p in procesos if str(p.get("name", "")).lower() == "eboot.bin"]
if abiertos and "--forzar" not in sys.argv:
    sys.exit("hay un juego abierto en la PS5 (%s): cierralo antes de actualizar" % abiertos)

ftp = ftplib.FTP()
ftp.connect(PS5_IP, 2121, timeout=30)
ftp.login("anonymous", "codex")


def listar(d):
    ftp.cwd(d)
    filas = []
    ftp.retrlines("LIST", filas.append)
    for f in filas:
        partes = f.split(None, 8)
        if len(partes) < 9 or partes[8] in (".", ".."):
            continue
        yield partes[0].startswith("d"), posixpath.join(d, partes[8])


def orden(cmd):
    # ftpsrv contesta 226 al borrar (no 250): vale cualquier 2xx
    r = ftp.sendcmd(cmd)
    if not r.startswith("2"):
        raise ftplib.error_reply(r)


def vaciar(d):
    n = 0
    for es_dir, ruta in list(listar(d)):
        assert ruta.startswith(raiz + "/"), ruta
        if es_dir:
            n += vaciar(ruta)
            orden("RMD " + ruta)
        else:
            orden("DELE " + ruta)
            n += 1
    return n


print("borrados", vaciar(raiz), "archivos dentro de", raiz)
print("queda:", list(listar(raiz)))
ftp.quit()
