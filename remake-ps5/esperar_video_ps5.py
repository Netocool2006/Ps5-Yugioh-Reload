# Espera (hasta 3 h) a que el juego termine de grabar el video del ataque en la PS5 (capturas/video/*.jpg deja de
# crecer) y entonces corre fotos_ps5.py (baja, arma hojas y MP4, y borra en la consola). Solo lee por FTP hasta ahi.
import ftplib, subprocess, sys, time, os
PS5_IP = open(__import__("os").path.join(__import__("os").path.dirname(__import__("os").path.abspath(__file__)), "consola_ip.txt")).read().strip()   # IP de la consola: archivo local (no va al repo)
fin = time.time() + 3 * 3600
anterior, quieto = -1, 0
while time.time() < fin:
    n = 0
    try:
        f = ftplib.FTP(); f.connect(PS5_IP, 2121, timeout=20); f.login("anonymous", "codex")
        filas = []
        try:
            f.cwd("/data/homebrew/PPSA77001/capturas/video"); f.retrlines("LIST", filas.append)
        except ftplib.error_perm:
            pass
        f.quit()
        n = sum(1 for x in filas if x.endswith(".jpg"))
    except Exception:
        pass
    quieto = quieto + 1 if (n == anterior and n > 0) else 0
    anterior = n
    if n > 0 and quieto >= 2:
        print("VIDEO GRABADO:", n, "cuadros", flush=True)
        subprocess.run([sys.executable, "-I", os.path.join(os.path.dirname(os.path.abspath(__file__)), "fotos_ps5.py")], check=True)
        break
    time.sleep(10)
else:
    print("NO LLEGO VIDEO en 3 horas")
