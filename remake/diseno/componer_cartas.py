# Compone la cara de cada carta: marco de Gemini + ilustracion + nombre + estrellas + atributo + tipo + ATK/DEF.
# Los datos se escriben con codigo (sin erratas); el aspecto lo pone el marco remasterizado por Gemini.
# Tambien exporta los datos en texto plano para el motor C++ (sin dependencias de JSON):
#   recursos\cartas\cartas.txt   id|nombre|atk|def|nivel|efecto|figura_w|figura_h|clase
#   recursos\ui\tablero.txt      id x z   (geometria compartida con el tapete de Gemini)
import json, os, sys
sys.path.insert(0, r"D:\Yugi-Reload\herramientas\pylib")
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

R = r"D:\Yugi-Reload\remake\recursos"
UI, CARTAS, FUENTES = os.path.join(R, "ui"), os.path.join(R, "cartas"), os.path.join(R, "fuentes")
W, H = 744, 1078
# geometria del marco (0..1), medida sobre los marcos de Gemini
NOMBRE = (0.065, 0.045, 0.80, 0.115)
ATRIBUTO = (0.885, 0.077, 0.048)              # centro x, y, radio (en anchos de carta)
ESTRELLAS_Y = 0.162
VENTANA = (0.121, 0.204, 0.879, 0.707)
TEXTO = (0.065, 0.765, 0.935, 0.945)
COLOR_ATRIBUTO = {"DARK": (120, 60, 160), "LIGHT": (235, 200, 70), "FIRE": (220, 60, 40), "WATER": (50, 120, 220),
                  "WIND": (60, 170, 90), "EARTH": (140, 100, 60)}
TIPOS = {"WingedBeast": "Bestia Alada", "BeastWarrior": "Guerrero-Bestia", "SeaSerpent": "Serpiente Marina",
         "Spellcaster": "Lanzador de Conjuros", "Machine": "Máquina", "Dragon": "Dragón", "Warrior": "Guerrero",
         "Fiend": "Demonio", "Zombie": "Zombi", "Fairy": "Hada", "Beast": "Bestia", "Insect": "Insecto",
         "Dinosaur": "Dinosaurio", "Reptile": "Reptil", "Aqua": "Aqua", "Fish": "Pez", "Pyro": "Piro",
         "Rock": "Roca", "Plant": "Planta", "Thunder": "Trueno"}

def fuente(nombre, tam, peso):
    f = ImageFont.truetype(os.path.join(FUENTES, nombre), tam)
    try:
        f.set_variation_by_axes([peso])
    except Exception:
        pass
    return f

def caja(r):
    return int(r[0] * W), int(r[1] * H), int(r[2] * W), int(r[3] * H)

def texto_ajustado(d, xy, ancho_max, texto, archivo, tam, peso, color, sombra=True):
    while tam > 10:
        f = fuente(archivo, tam, peso)
        if d.textlength(texto, font=f) <= ancho_max:
            break
        tam -= 2
    if sombra:
        d.text((xy[0] + 2, xy[1] + 2), texto, font=f, fill=(0, 0, 0, 140), anchor="lm")
    d.text(xy, texto, font=f, fill=color, anchor="lm")

def estrella(d, cx, cy, r):
    pts = []
    for k in range(10):
        a = -np.pi / 2 + k * np.pi / 5
        rr = r if k % 2 == 0 else r * 0.45
        pts.append((cx + rr * np.cos(a), cy + rr * np.sin(a)))
    d.polygon([(x + 2, y + 2) for x, y in pts], fill=(60, 20, 0, 150))
    d.polygon(pts, fill=(235, 90, 25), outline=(255, 215, 120), width=3)
    d.ellipse([cx - r * 0.18, cy - r * 0.18, cx + r * 0.18, cy + r * 0.18], fill=(255, 230, 160))

def componer(c, marco):
    lienzo = marco.copy().convert("RGBA")
    # ilustracion: cubre la ventana negra
    x0, y0, x1, y1 = caja(VENTANA)
    arte = Image.open(os.path.join(CARTAS, c["id"], "arte.png")).convert("RGB")
    arte = arte.resize((x1 - x0, y1 - y0), Image.LANCZOS)
    lienzo.paste(arte, (x0, y0))
    d = ImageDraw.Draw(lienzo, "RGBA")
    # nombre
    nx0, ny0, nx1, ny1 = caja(NOMBRE)
    texto_ajustado(d, (nx0 + 14, (ny0 + ny1) // 2), nx1 - nx0 - 28, c["nombre"], "Cinzel.ttf", 46, 800, (25, 18, 10))
    # atributo: el circulo del marco tenido con el color del atributo y su inicial
    ax, ay, ar = ATRIBUTO[0] * W, ATRIBUTO[1] * H, ATRIBUTO[2] * W
    clave = {"magia": "MAGIA", "trampa": "TRAMPA"}.get(c["clase"], c["atributo"])
    icono = os.path.join(UI, "iconos", clave + ".png")
    if os.path.exists(icono):   # emblema remasterizado por Gemini
        ic = Image.open(icono).convert("RGBA"); lado = int(ar * 2.1)
        ic = ic.resize((lado, int(lado * ic.height / ic.width)), Image.LANCZOS)
        lienzo.alpha_composite(ic, (int(ax - ic.width / 2), int(ay - ic.height / 2)))
    else:
        col = COLOR_ATRIBUTO.get(c["atributo"], (150, 150, 150))
        d.ellipse([ax - ar * 0.78, ay - ar * 0.78, ax + ar * 0.78, ay + ar * 0.78], fill=col + (230,))
        d.text((ax, ay), c["atributo"][:1], font=fuente("Cinzel.ttf", int(ar * 1.1), 900), fill=(255, 255, 255), anchor="mm")
    monstruo = c["clase"] not in ("magia", "trampa")
    tx0, ty0, tx1, ty1 = caja(TEXTO)
    if monstruo:
        # estrellas de nivel, alineadas a la derecha como en la carta clasica
        r = 0.028 * W; paso = 2.25 * r
        img_est = os.path.join(UI, "estrella.png")
        if os.path.exists(img_est):   # estrella remasterizada por Gemini
            est = Image.open(img_est).convert("RGBA"); lado = int(r * 2.3)
            est = est.resize((lado, int(lado * est.height / est.width)), Image.LANCZOS)
            for k in range(c["nivel"]):
                cx = VENTANA[2] * W - r - k * paso
                lienzo.alpha_composite(est, (int(cx - est.width / 2), int(ESTRELLAS_Y * H - est.height / 2)))
        else:
            for k in range(c["nivel"]):
                estrella(d, VENTANA[2] * W - r - k * paso, ESTRELLAS_Y * H, r)
        extra = " / Fusión" if c["clase"] == "fusion" else " / Efecto" if c["efecto"] else ""
        tipo = "[ %s%s ]" % (TIPOS.get(c["tipo"], c["tipo"]), extra)
    else:
        sub = "de Campo" if c.get("campo") else ""
        etiqueta = "[ CARTA %s %s ]" % ("MÁGICA" if c["clase"] == "magia" else "DE TRAMPA", sub)
        d.text(((VENTANA[0] + VENTANA[2]) / 2 * W, ESTRELLAS_Y * H), etiqueta.replace("  ", " "), font=fuente("Cinzel.ttf", 30, 800),
               fill=(25, 18, 10), anchor="mm")
        tipo = None
    y = ty0 + 30
    if tipo:
        texto_ajustado(d, (tx0 + 22, y), tx1 - tx0 - 44, tipo, "Cinzel.ttf", 30, 700, (40, 28, 16), sombra=False)
        y += 30
    # descripcion del juego, ajustada a la caja (se reduce la letra si no cabe)
    desc = open(os.path.join(CARTAS, c["id"], "descripcion.txt"), encoding="utf-8").read()
    alto_max = (ty1 - 70 if monstruo else ty1 - 18) - y
    for tam in (27, 25, 23, 21, 19, 17):
        f = fuente("RobotoCondensed.ttf", tam, 450)
        lineas = envolver(d, desc, f, tx1 - tx0 - 44)
        if len(lineas) * (tam + 3) <= alto_max: break
    for ln in lineas:
        d.text((tx0 + 22, y), ln, font=f, fill=(30, 22, 14), anchor="la"); y += tam + 3
    if monstruo:
        d.line([(tx0 + 20, ty1 - 62), (tx1 - 20, ty1 - 62)], fill=(60, 40, 20, 160), width=2)
        stats = "ATK / %d     DEF / %d" % (c["atk"], c["def"])
        d.text((tx1 - 24, ty1 - 32), stats, font=fuente("RobotoCondensed.ttf", 40, 800), fill=(25, 18, 10), anchor="rm")
    return lienzo.convert("RGB")

def envolver(d, texto, f, ancho):
    lineas, actual = [], ""
    for p in texto.split():
        prueba = (actual + " " + p).strip()
        if d.textlength(prueba, font=f) <= ancho: actual = prueba
        else: lineas.append(actual); actual = p
    if actual: lineas.append(actual)
    return lineas

def main():
    marcos = {k: Image.open(os.path.join(UI, "marco_%s.png" % k)).resize((W, H), Image.LANCZOS)
              for k in ("normal", "efecto", "fusion", "magia", "trampa") if os.path.exists(os.path.join(UI, "marco_%s.png" % k))}
    meta = json.load(open(os.path.join(CARTAS, "cartas.json"), encoding="utf-8"))
    lineas = []
    for c in meta:
        clase = c["clase"] if c["clase"] in marcos else ("efecto" if c["efecto"] else "normal")
        cara = componer(c, marcos[clase])
        cara.save(os.path.join(CARTAS, c["id"], "cara.png"))
        lineas.append("|".join(str(v) for v in (c["id"], c["nombre"], c["atk"], c["def"], c["nivel"], int(c["efecto"]),
                                                 *c["figura_px"], c["clase"])))
    open(os.path.join(CARTAS, "cartas.txt"), "w", encoding="utf-8").write("\n".join(lineas) + "\n")
    Image.open(os.path.join(UI, "dorso.png")).resize((W, H), Image.LANCZOS).save(os.path.join(UI, "dorso.png"))
    tab = json.load(open(r"D:\Yugi-Reload\remake\diseno\tablero.json", encoding="utf-8"))
    open(os.path.join(UI, "tablero.txt"), "w").write("".join("%s %.3f %.3f\n" % (z["id"], z["x"], z["z"]) for z in tab["zonas"]))
    print(len(meta), "caras compuestas")

if __name__ == "__main__":
    main()
