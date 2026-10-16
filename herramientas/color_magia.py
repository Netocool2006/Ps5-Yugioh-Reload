# Color de la magia de cada mistico (regla 3): depende de QUIEN la lanza (pedido del usuario 2026-10-16: "el
# Mago Oscuro azul, la Maga el color que tiene..."). Analisis de imagen de su figura de Gemini
# (nano-banana/todo/figura/<carta>/resultado.png, fondo negro) o, si no hay, de la ilustracion de la carta: se toman
# los pixeles brillantes y saturados (destellos, gemas, adornos magicos) y se busca el tono dominante, pesando mas los
# mas luminosos. Los casos que conozco de la carta/serie mandan sobre el analisis ("conocimiento").
# Escribe "color_magia" en remake/diseno/reglas_combate.json. Uso: python -I color_magia.py
import colorsys, json, os, re
import numpy as np
from PIL import Image

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIG = os.path.join(BASE, "nano-banana", "todo", "figura")
CARD = os.path.join(BASE, "datadat-extraido", "card")
RUTA = os.path.join(BASE, "remake", "diseno", "reglas_combate.json")

# color de magia conocido (RGB 0-1 del halo): lo dijo el usuario o es el de la carta/serie
CONOCIDO = {
    "dark_magician": ((0.18, 0.45, 1.6), "usuario: azul"),
    "dark_magician_girl": ((0.55, 0.18, 1.5), "usuario: el que ya tiene (morado)"),
    "magician_of_black_chaos": ((0.5, 0.1, 0.9), "serie: magia del caos negra-morada"),
    "time_wizard": ((1.4, 1.1, 0.3), "carta: ruleta del tiempo dorada"),
    "water_magician": ((0.12, 0.55, 1.6), "carta: magia de agua"),
    "fire_sorcerer": ((1.6, 0.45, 0.08), "carta: hechicero de fuego"),
    "flame_manipulator": ((1.6, 0.45, 0.08), "carta: manipula llamas"),
    "exodia_the_forbidden_one": ((1.4, 1.0, 0.25), "serie: Exodia ataca con energia dorada"),
}
# revision visual de las figuras (como lo ve una persona), 2026-10-16: corrige donde el analisis automatico se
# confundio con adornos dorados, piel o fondos
DORADO, VIOLETA, VERDE, CELESTE, ROJO, ROSA = (1.4, 1.05, 0.3), (0.75, 0.2, 1.5), (0.3, 1.5, 0.35), (0.3, 1.2, 1.6), (1.6, 0.25, 0.2), (1.6, 0.35, 1.0)
VISUAL = {
    "ancient_elf": VIOLETA, "ceremonial_bell": DORADO, "cosmo_queen": VIOLETA, "dancing_elf": CELESTE,
    "doma_the_angel_of_silence": VERDE, "empress_judge": DORADO, "fairy_s_gift": VERDE, "gemini_elf": CELESTE,
    "hoshiningen": DORADO, "invitation_to_a_dark_sleep": VIOLETA, "jinzo": ROJO, "jowgen_the_spiritualist": VIOLETA,
    "kycoo_the_ghost_destroyer": VIOLETA, "left_arm_of_the_forbidden_one": DORADO, "left_leg_of_the_forbidden_one": DORADO,
    "right_arm_of_the_forbidden_one": DORADO, "right_leg_of_the_forbidden_one": DORADO, "lord_of_d": VIOLETA,
    "magical_ghost": VERDE, "magician_of_faith": DORADO, "mysterious_puppeteer": VIOLETA, "mystic_lamp": DORADO,
    "relinquished": VERDE, "saggi_the_dark_clown": VIOLETA, "senju_of_the_thousand_hands": DORADO,
    "shining_angel": DORADO, "shining_friendship": VERDE, "sorcerer_of_the_doomed": VIOLETA,
    "spirit_of_the_breeze": VERDE, "thousand_eyes_restrict": VIOLETA, "dark_eyes_illusionist": VIOLETA,
    "the_stern_mystic": DORADO, "mystical_elf": DORADO, "fairy_guardian": ROSA, "lady_of_faith": ROSA,
}
for _k, _c in VISUAL.items():
    CONOCIDO.setdefault(_k, (_c, "revision visual de la figura"))


def ilustracion(nombre):
    lineas = open(os.path.join(CARD, "list_card.txt"), encoding="latin-1").read().splitlines()
    actual = None
    for l in lineas:
        l = l.strip()
        if l.startswith("//") and not re.match(r"//\s*\d{4}:", l):
            actual = l[2:].strip()
        elif l.lower().endswith(".bmp") and actual == nombre:
            im = Image.open(os.path.join(CARD, l)).convert("RGB")
            w, h = im.size
            return im.crop((int(w * 0.12), int(h * 0.19), int(w * 0.88), int(h * 0.71)))  # recuadro del arte
    return None


def tono_magico(im):
    a = np.asarray(im.convert("RGB").resize((256, 256)), dtype=np.float32) / 255.0
    px = a.reshape(-1, 3)
    mx, mn = px.max(1), px.min(1)
    sat = (mx - mn) / np.maximum(mx, 1e-6)
    sel = (mx > 0.35) & (sat > 0.45)
    if sel.sum() < 50:
        return None
    hsv = np.array([colorsys.rgb_to_hsv(*p) for p in px[sel]])
    # piel y pelo rubio (naranja claro poco saturado) no cuentan como magia
    piel = (hsv[:, 0] > 0.02) & (hsv[:, 0] < 0.12) & (hsv[:, 1] < 0.65)
    hsv = hsv[~piel]
    if len(hsv) < 50:
        return None
    peso = hsv[:, 2] ** 3 * hsv[:, 1]          # lo mas luminoso y saturado pesa mas (destellos)
    hist, bordes = np.histogram(hsv[:, 0], bins=24, range=(0, 1), weights=peso)
    hist = hist + 0.5 * (np.roll(hist, 1) + np.roll(hist, -1))   # tono circular, suaviza vecinos
    # el dorado/naranja de adornos y joyas (15-50 grados) es comun en casi todas las figuras: solo gana si no hay
    # otro tono con al menos el 45 % de su fuerza
    centros = (bordes[:-1] + bordes[1:]) / 2
    dorado = (centros * 360 > 12) & (centros * 360 < 50)
    otros = np.where(dorado, 0, hist)
    b = int(otros.argmax()) if otros.max() >= 0.45 * hist.max() else int(hist.argmax())
    h = (bordes[b] + bordes[b + 1]) / 2
    r, g, bl = colorsys.hsv_to_rgb(h, 0.85, 1.0)
    return (round(float(r) * 1.6, 2), round(float(g) * 1.6, 2), round(float(bl) * 1.6, 2)), float(h)


def main():
    d = json.load(open(RUTA, encoding="utf-8"))
    for k, c in d["cartas"].items():
        if c["regla"] != "mistico":
            continue
        if k in CONOCIDO:
            col, fuente = CONOCIDO[k]
        elif c["atributo"] in ("FIRE", "WATER"):
            # fuego y agua: la magia es de su elemento (la Dama Asesina de las Llamas lanza fuego, no azul)
            col = (1.6, 0.45, 0.08) if c["atributo"] == "FIRE" else (0.12, 0.55, 1.6)
            fuente = "elemento %s (su magia es de %s)" % (c["atributo"], "fuego" if c["atributo"] == "FIRE" else "agua")
        else:
            ruta = os.path.join(FIG, k, "resultado.png")
            im = Image.open(ruta) if os.path.exists(ruta) else ilustracion(c["nombre"])
            r = tono_magico(im) if im is not None else None
            if r:
                col, h = r
                fuente = ("figura" if os.path.exists(ruta) else "ilustracion") + " (tono %d grados)" % round(h * 360)
            else:
                col, fuente = None, "sin datos: color del elemento"
        if col:
            nucleo = tuple(round(min(1.0, 0.75 + 0.25 * x / 1.6), 2) for x in col)
            c["color_magia"] = {"halo": list(col), "nucleo": list(nucleo), "fuente": fuente}
        else:
            c.pop("color_magia", None)
    json.dump(d, open(RUTA, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    for k, c in sorted(d["cartas"].items()):
        if c["regla"] == "mistico":
            m = c.get("color_magia")
            print("%-36s %-6s %s" % (c["nombre"][:36], c["atributo"], "%s  [%s]" % (m["halo"], m["fuente"]) if m else "elemento"))


main()
