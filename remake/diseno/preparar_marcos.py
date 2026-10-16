# Recorta los recursos de Gemini (tablero, dorso, marcos) y mide la geometria de los marcos de carta:
# ventana de la ilustracion (negro puro), barra del nombre y caja de texto, en coordenadas 0..1 de la carta.
# Salida: remake\recursos\ui\{tablero,dorso,marco_normal,marco_efecto}.png + marcos.json
import json, os, sys
sys.path.insert(0, r"D:\Yugi-Reload\herramientas\pylib")
import numpy as np
from PIL import Image
from scipy import ndimage

NB = r"D:\Yugi-Reload\nano-banana\base1"
UI = r"D:\Yugi-Reload\remake\recursos\ui"
ANCHO_CARTA = 744          # carta en textura: 744 x 1080 (proporcion 1:1.45)

def recortar_carta(ruta):
    im = Image.open(ruta).convert("RGB"); a = np.asarray(im).astype(np.int16)
    fondo = a.max(2) < 18
    # la carta es el objeto grande no-negro; su caja exterior
    filas = np.where((~fondo).mean(1) > 0.3)[0]; cols = np.where((~fondo).mean(0) > 0.3)[0]
    caja = (cols.min(), filas.min(), cols.max() + 1, filas.max() + 1)
    return im.crop(caja)

def medir(carta):
    a = np.asarray(carta).astype(np.int16); h, w = a.shape[:2]
    negro = a.max(2) < 20
    etiquetas, n = ndimage.label(negro)
    tam = ndimage.sum(np.ones_like(etiquetas), etiquetas, range(1, n + 1))
    ventana = None
    for idx in np.argsort(tam)[::-1]:
        sl = ndimage.find_objects((etiquetas == idx + 1).astype(int))[0]
        y0, y1, x0, x1 = sl[0].start, sl[0].stop, sl[1].start, sl[1].stop
        if x0 > w * 0.03 and x1 < w * 0.97 and y0 > h * 0.05:   # interior (no el fondo que rodea las esquinas)
            ventana = (x0 / w, y0 / h, x1 / w, y1 / h); break
    # barra del nombre: franja horizontal clara entre el borde superior y la ventana; caja de texto: debajo
    claro = a.mean(2) > 120
    def franja(y_ini, y_fin):
        ys = [y for y in range(int(y_ini * h), int(y_fin * h)) if claro[y, int(w * 0.2):int(w * 0.8)].mean() > 0.9]
        return (min(ys) / h, (max(ys) + 1) / h) if ys else None
    nombre = franja(0.0, ventana[1])
    texto = franja(ventana[3], 1.0)
    return {"ventana": ventana, "nombre_y": nombre, "texto_y": texto}

def main():
    os.makedirs(UI, exist_ok=True)
    Image.open(os.path.join(NB, "tablero", "resultado.png")).convert("RGB").save(os.path.join(UI, "tablero.png"))
    geo = {}
    for nombre in ("dorso", "marco_normal", "marco_efecto"):
        c = recortar_carta(os.path.join(NB, nombre, "resultado.png"))
        print(nombre, "carta recortada", c.size, "proporcion %.3f" % (c.height / c.width))
        c = c.resize((ANCHO_CARTA, int(ANCHO_CARTA * 1.45)), Image.LANCZOS)
        c.save(os.path.join(UI, nombre + ".png"))
        if nombre.startswith("marco"):
            geo[nombre] = medir(c); print("  ", geo[nombre])
    json.dump(geo, open(os.path.join(UI, "marcos.json"), "w"), indent=1)

if __name__ == "__main__":
    main()
