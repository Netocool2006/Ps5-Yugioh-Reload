# Geometria unica del tablero (unidades de mundo; 1 carta = 1.0 x 1.45) y esquema guia para Gemini.
# El mismo JSON lo lee el juego, asi el tapete generado y las zonas del motor coinciden.
import json, os, sys
sys.path.insert(0, r"D:\Yugi-Reload\herramientas\pylib")
from PIL import Image, ImageDraw

AQUI = os.path.dirname(os.path.abspath(__file__))
ANCHO, ALTO = 19.2, 14.4          # tablero 4:3 (x de -9.6 a 9.6, z de -7.2 a 7.2; z positivo = lado del jugador)
CARTA = (1.0, 1.45)
ZONA = (1.16, 1.62)               # marco de zona un poco mayor que la carta
COLS = [-5.4, -2.7, 0.0, 2.7, 5.4]   # mucho aire entre cartas: las figuras 3D son anchas y no deben pisarse
LATERAL = 8.2
FILA_MONSTRUO, FILA_MAGIA = 2.2, 5.5

def zonas():
    z = []
    for lado, s in (("jugador", 1), ("rival", -1)):
        for i, x in enumerate(COLS):
            z.append({"id": "%s_monstruo_%d" % (lado, i), "lado": lado, "tipo": "monstruo", "x": x * s, "z": FILA_MONSTRUO * s})
            z.append({"id": "%s_magia_%d" % (lado, i), "lado": lado, "tipo": "magia", "x": x * s, "z": FILA_MAGIA * s})
        z.append({"id": lado + "_campo", "lado": lado, "tipo": "campo", "x": -LATERAL * s, "z": FILA_MONSTRUO * s})
        z.append({"id": lado + "_fusion", "lado": lado, "tipo": "fusion", "x": -LATERAL * s, "z": FILA_MAGIA * s})
        z.append({"id": lado + "_cementerio", "lado": lado, "tipo": "cementerio", "x": LATERAL * s, "z": FILA_MONSTRUO * s})
        z.append({"id": lado + "_mazo", "lado": lado, "tipo": "mazo", "x": LATERAL * s, "z": FILA_MAGIA * s})
    return z

def a_pixeles(x, z, w, h):
    return (x + ANCHO / 2) / ANCHO * w, (z + ALTO / 2) / ALTO * h

def esquema(w=1600, h=1200):
    im = Image.new("RGB", (w, h), (8, 10, 16))
    d = ImageDraw.Draw(im)
    d.line([(0, h / 2), (w, h / 2)], fill=(200, 200, 220), width=3)       # linea central
    for zn in zonas():
        cx, cy = a_pixeles(zn["x"], zn["z"], w, h)
        zw, zh = ZONA[0] / ANCHO * w, ZONA[1] / ALTO * h
        col = (60, 170, 255) if zn["lado"] == "jugador" else (255, 80, 70)
        if zn["tipo"] in ("magia", "fusion", "mazo"):
            col = tuple(int(c * 0.7) for c in col)
        d.rectangle([cx - zw / 2, cy - zh / 2, cx + zw / 2, cy + zh / 2], outline=col, width=5)
    return im

if __name__ == "__main__":
    datos = {"ancho": ANCHO, "alto": ALTO, "carta": CARTA, "zona": ZONA, "zonas": zonas()}
    json.dump(datos, open(os.path.join(AQUI, "tablero.json"), "w", encoding="utf-8"), indent=1)
    esquema().save(os.path.join(AQUI, "tablero_esquema.png"))
    print(len(datos["zonas"]), "zonas")
