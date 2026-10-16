# Hoja de revision de un video del PC: fotogramas en los segundos dados, recortados (zona x0,y0,x1,y1) y ampliados.
# Uso: python -I hoja_video.py video.mp4 salida.png x0,y0,x1,y1 t1 t2 t3 ...
import subprocess, sys, tempfile, os
from PIL import Image, ImageDraw

video, salida, zona = sys.argv[1:4]
tiempos = sys.argv[4:]
x0, y0, x1, y1 = map(int, zona.split(","))
ancho = 420
alto = int(ancho * (y1 - y0) / (x1 - x0))
cols = min(4, len(tiempos))
filas = (len(tiempos) + cols - 1) // cols
hoja = Image.new("RGB", (ancho * cols, alto * filas), "white")
with tempfile.TemporaryDirectory() as tmp:
    for k, t in enumerate(tiempos):
        f = os.path.join(tmp, "f.png")
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", t, "-i", video, "-frames:v", "1", f], check=True)
        c = Image.open(f).convert("RGB").crop((x0, y0, x1, y1)).resize((ancho, alto), Image.LANCZOS)
        hoja.paste(c, ((k % cols) * ancho, (k // cols) * alto))
        ImageDraw.Draw(hoja).text(((k % cols) * ancho + 6, (k // cols) * alto + 6), t + " s", fill="yellow")
hoja.save(salida)
print(salida)
