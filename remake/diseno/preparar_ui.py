# Recursos de interfaz de Gemini (lote base1b) -> remake\recursos\ui\
#   espada.png, boton_off.png, boton_on.png, panel_carta.png, panel_lp.png : RGBA (fondo negro quitado)
#   explosion.png : RGB sobre negro (el motor la dibuja en modo aditivo, el negro no se ve)
#   marco_magia.png, marco_trampa.png, marco_fusion.png : marcos de carta (mismo recorte que los otros marcos)
# Procesa solo lo que Gemini ya haya entregado.
import os, sys
sys.path.insert(0, r"D:\Yugi-Reload\herramientas\pylib")
sys.path.insert(0, r"D:\Yugi-Reload\poc-godot\preparacion")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from PIL import Image, ImageFilter
from procesar_fotos_usuario import fondo_conectado, UMBRAL_NEGRO
from preparar_marcos import recortar_carta, ANCHO_CARTA

NB = r"D:\Yugi-Reload\nano-banana\base1b"
UI = r"D:\Yugi-Reload\remake\recursos\ui"

def sin_fondo(img):
    fondo, brillo = fondo_conectado(img)
    a = (~fondo).astype(np.float32)
    a = np.asarray(Image.fromarray((a * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.2))).astype(np.float32) / 255
    a = np.maximum(a, np.clip((brillo.astype(np.float32) - UMBRAL_NEGRO) / 40.0, 0, 1) * (a > 0.02))
    rgba = img.copy(); rgba.putalpha(Image.fromarray((a * 255).astype(np.uint8)))
    ys, xs = np.nonzero(a > 0.1)
    return rgba.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))

def borrar_corchetes(c):
    """Gemini dibujo '[ ]' en la franja del tipo; el texto lo pone el compositor, asi que se tapan con un bloque de marmol vecino."""
    a = np.asarray(c.convert("L")).astype(np.int16)
    y0, y1, x0, x1 = 140, 200, 120, c.width - 60      # solo el interior de la franja (sin tocar los bordes dorados)
    oscuro = a[y0:y1, x0:x1] < 50
    cols = np.where(oscuro.sum(0) > 6)[0] + x0
    if not len(cols):
        return
    grupos, ini = [], cols[0]                          # cada corchete = grupo de columnas contiguas
    for p, q in zip(cols[:-1], cols[1:]):
        if q - p > 3: grupos.append((ini, p)); ini = q
    grupos.append((ini, cols[-1]))
    for g0, g1 in grupos:
        filas = np.where(oscuro[:, g0 - x0:g1 - x0 + 1].any(1))[0] + y0
        bx0, bx1, by0, by1 = g0 - 5, g1 + 6, filas.min() - 5, filas.max() + 6
        dx = -(bx1 - bx0 + 12) if g0 > c.width / 2 else (bx1 - bx0 + 12)   # bloque limpio hacia el centro
        parche = c.crop((bx0 + dx, by0, bx1 + dx, by1))
        m = Image.new("L", parche.size, 0)
        from PIL import ImageDraw
        ImageDraw.Draw(m).rectangle([2, 2, parche.width - 3, parche.height - 3], fill=255)
        c.paste(parche, (bx0, by0), m.filter(ImageFilter.GaussianBlur(2)))

def resultado(nombre):
    r = os.path.join(NB, nombre, "resultado.png")
    return Image.open(r).convert("RGB") if os.path.exists(r) else None

def main():
    hecho = []
    for nombre in ("espada", "panel_carta", "panel_lp"):
        im = resultado(nombre)
        if im:
            s = sin_fondo(im)
            if nombre == "panel_carta":  # tamano de pantalla: el motor lo estira por 9 partes sin deformar el marco
                s = s.resize((420, int(s.height * 420 / s.width)), Image.LANCZOS)
            s.save(os.path.join(UI, nombre + ".png")); hecho.append(nombre)
    im = resultado("boton_fase")
    if im:  # dos botones lado a lado: izquierda apagado, derecha encendido
        w = im.width
        sin_fondo(im.crop((0, 0, w // 2, im.height))).save(os.path.join(UI, "boton_off.png"))
        sin_fondo(im.crop((w // 2, 0, w, im.height))).save(os.path.join(UI, "boton_on.png"))
        hecho.append("boton_fase")
    im = resultado("explosion")
    if im:
        a = np.asarray(im).max(2)
        ys, xs = np.nonzero(a > 20)
        cx, cy = (xs.min() + xs.max()) // 2, (ys.min() + ys.max()) // 2
        r = max(xs.max() - xs.min(), ys.max() - ys.min()) // 2 + 10
        im.crop((cx - r, cy - r, cx + r, cy + r)).resize((1024, 1024), Image.LANCZOS).save(os.path.join(UI, "explosion.png"))
        hecho.append("explosion")
    for nombre in ("marco_magia", "marco_trampa", "marco_fusion"):
        r = os.path.join(NB, nombre, "resultado.png")
        if os.path.exists(r):
            c = recortar_carta(r).resize((ANCHO_CARTA, int(ANCHO_CARTA * 1.45)), Image.LANCZOS)
            borrar_corchetes(c)
            c.save(os.path.join(UI, nombre + ".png")); hecho.append(nombre)
    # lote base1c: tapete ampliado, iconos de atributo (8 en fila) y estrella de nivel
    c = r"D:\Yugi-Reload\nano-banana\base1c"
    r = os.path.join(c, "tablero", "resultado.png")
    if os.path.exists(r):
        Image.open(r).convert("RGB").save(os.path.join(UI, "tablero.png")); hecho.append("tablero ampliado")
    r = os.path.join(c, "iconos", "resultado.png")
    if os.path.exists(r):
        im = Image.open(r).convert("RGB"); a = np.asarray(im).max(2) > 30
        cols = np.where(a.any(0))[0]
        grupos, ini = [], cols[0]          # columnas con contenido separadas por huecos negros = un icono cada una
        for x0, x1 in zip(cols[:-1], cols[1:]):
            if x1 - x0 > 6: grupos.append((ini, x0 + 1)); ini = x1
        grupos.append((ini, cols[-1] + 1))
        grupos = [g for g in grupos if g[1] - g[0] > im.width * 0.04]
        os.makedirs(os.path.join(UI, "iconos"), exist_ok=True)
        nombres = ["LIGHT", "DARK", "WATER", "FIRE", "EARTH", "WIND", "MAGIA", "TRAMPA"]
        if len(grupos) == 8:
            for (x0, x1), n in zip(grupos, nombres):
                sin_fondo(im.crop((x0, 0, x1, im.height))).save(os.path.join(UI, "iconos", n + ".png"))
            hecho.append("iconos")
        else:
            # Gemini los dibujo pegados (y a veces sobre blanco): 8 celdas iguales + mascara circular
            from PIL import ImageDraw
            paso = im.width / 8
            for k, n in enumerate(nombres):
                celda = im.crop((int(k * paso), 0, int((k + 1) * paso), im.height)).convert("RGBA")
                lado = min(celda.size); m = Image.new("L", celda.size, 0)
                cx, cy, r = celda.width / 2, celda.height / 2, lado / 2 * 0.97
                ImageDraw.Draw(m).ellipse([cx - r, cy - r, cx + r, cy + r], fill=255)
                celda.putalpha(m.filter(ImageFilter.GaussianBlur(2)))
                celda.crop((int(cx - r), int(cy - r), int(cx + r), int(cy + r))).save(os.path.join(UI, "iconos", n + ".png"))
            hecho.append("iconos (por celdas)")
    r = os.path.join(c, "estrella", "resultado.png")
    if os.path.exists(r):
        sin_fondo(Image.open(r).convert("RGB")).save(os.path.join(UI, "estrella.png")); hecho.append("estrella")
    print("ui:", ", ".join(hecho) or "nada todavia")

if __name__ == "__main__":
    main()
