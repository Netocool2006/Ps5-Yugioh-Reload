# Paso 3 del ciclo: arma las hojas de revision a partir de las fotos de revision_exhaustiva.py:
#  - hoja_angulos.png (8 angulos + arriba), hoja_cerca.png (primeros planos), hoja_anim_<nombre>.png (8 cuadros)
#  - cuadrantes/<foto>_q1..q4.png: cada toma de angulo/primer plano dividida en 4 y ampliada al doble
# Uso: python -I revision_cuadrantes.py <carpeta revision>
import glob, os, sys
from PIL import Image, ImageDraw

d = sys.argv[1]


def hoja(nombres, salida, cols, tam):
    if not nombres:
        return
    filas = (len(nombres) + cols - 1) // cols
    h = Image.new("RGB", (cols * tam, filas * tam), (40, 40, 44))
    for i, n in enumerate(nombres):
        im = Image.open(n).convert("RGB").resize((tam, tam))
        ImageDraw.Draw(im).text((6, 4), os.path.basename(n)[:-4], fill=(255, 255, 0))
        h.paste(im, ((i % cols) * tam, (i // cols) * tam))
    h.save(salida)


fotos = sorted(glob.glob(os.path.join(d, "*.png")))
fotos = [f for f in fotos if not os.path.basename(f).startswith("hoja_")]
hoja([f for f in fotos if os.path.basename(f).startswith("ang_")], os.path.join(d, "hoja_angulos.png"), 3, 600)
hoja([f for f in fotos if os.path.basename(f).startswith("cerca_")], os.path.join(d, "hoja_cerca.png"), 4, 500)
anims = sorted({os.path.basename(f).rsplit("_", 1)[0] for f in fotos if os.path.basename(f).startswith("anim_")})
for a in anims:
    hoja(sorted(glob.glob(os.path.join(d, a + "_*.png"))), os.path.join(d, "hoja_%s.png" % a), 4, 400)
cuadr = os.path.join(d, "cuadrantes")
os.makedirs(cuadr, exist_ok=True)
n = 0
for f in fotos:
    b = os.path.basename(f)
    if not (b.startswith("ang_") or b.startswith("cerca_")):
        continue
    im = Image.open(f).convert("RGB")
    w, h = im.size
    for k, (x, y) in enumerate(((0, 0), (w // 2, 0), (0, h // 2), (w // 2, h // 2)), 1):
        im.crop((x, y, x + w // 2, y + h // 2)).resize((w, h), Image.LANCZOS).save(os.path.join(cuadr, "%s_q%d.png" % (b[:-4], k)))
        n += 1
print("hojas listas;", n, "cuadrantes en", cuadr, "| animaciones:", anims)
