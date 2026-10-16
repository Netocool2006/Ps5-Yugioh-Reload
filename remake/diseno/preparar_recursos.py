# Recursos de cartas para el remake (Base 1). Por carta, en remake\recursos\cartas\<id>\:
#   arte.png        ilustracion de la carta (ventana de arte, mejorada x4) para la cara de la carta
#   figura.png      figura 3D de Gemini sin fondo (RGBA)          -> monstruo de pie sobre la zona
#   profundidad.png mapa de profundidad de la figura (Depth Anything V2) -> relieve y animacion
# y remake\recursos\cartas\cartas.json con los datos (nombre, ATK/DEF, nivel, tipo, atributo, efecto).
import csv, json, os, sys
sys.path.insert(0, r"D:\Yugi-Reload\herramientas\pylib")
sys.path.insert(0, r"D:\Yugi-Reload\poc-godot\preparacion")
sys.path.insert(0, r"D:\Yugi-Reload\nano-banana")
import numpy as np
import onnxruntime as ort
from PIL import Image, ImageFilter
from procesar_fotos_usuario import fondo_conectado, profundidad, UMBRAL_NEGRO
from preparar_cartas import ARTE_CAJA, mejorar
from preparar_lote import ilustraciones

BASE = r"D:\Yugi-Reload"
NB = os.path.join(BASE, "nano-banana")
FOTOS = os.path.join(BASE, "poc-godot", "preparacion", "fotos_usuario")
DESTINO = os.path.join(BASE, "remake", "recursos", "cartas")
TAM_FIGURA = 1024

CARTAS = [  # (id, nombre exacto en cards.csv, figura 3D)
    ("baby_dragon", "Baby Dragon", os.path.join(NB, "lote01", "baby_dragon", "resultado.png")),
    ("celtic_guardian", "Celtic Guardian", os.path.join(NB, "lote01", "celtic_guardian", "resultado.png")),
    ("flame_swordsman", "Flame Swordsman", os.path.join(NB, "lote01", "flame_swordsman", "resultado.png")),
    ("harpie_lady", "Harpie Lady", os.path.join(NB, "lote01", "harpie_lady", "resultado.png")),
    ("kuriboh", "Kuriboh", os.path.join(NB, "lote01", "kuriboh", "resultado.png")),
    ("mask_of_darkness", "Mask of Darkness", os.path.join(NB, "lote01", "mask_of_darkness", "resultado.png")),
    ("oni_tank_t_34", "Oni Tank T-34", os.path.join(NB, "lote01", "oni_tank_t_34", "resultado.png")),
    ("time_wizard", "Time Wizard", os.path.join(NB, "lote01", "time_wizard", "resultado.png")),
    ("faith_bird", "Faith Bird", os.path.join(NB, "prueba", "faithbird", "resultado.png")),
    # rehechos por Gemini (lote02) a peticion del usuario, con el mismo proceso que el resto
    ("red_eyes", "Red-Eyes B. Dragon", os.path.join(NB, "lote02", "red_eyes_b_dragon", "resultado.png")),
    ("blue_eyes", "Blue-Eyes White Dragon", os.path.join(NB, "lote02", "blue_eyes_white_dragon", "resultado.png")),
    ("dark_magician", "Dark Magician", os.path.join(NB, "lote02", "dark_magician", "resultado.png")),
    ("summoned_skull", "Summoned Skull", os.path.join(NB, "lote02", "summoned_skull", "resultado.png")),
    ("gaia", "Gaia The Fierce Knight", os.path.join(NB, "lote02", "gaia_the_fierce_knight", "resultado.png")),
    # magias y trampas: sin figura
    ("swords_of_revealing_light", "Swords of Revealing Light", None), ("mirror_force", "Mirror Force", None),
    ("pot_of_greed", "Pot of Greed", None), ("monster_reborn", "Monster Reborn", None), ("trap_hole", "Trap Hole", None),
    ("sogen", "Sogen", None), ("dark_hole", "Dark Hole", None),
]
CAMPO = {"Sogen"}                      # magias de campo
ARTE_GEMINI = os.path.join(NB, "arte")   # ilustraciones remasterizadas por Gemini (si existen, se usan)

def descripcion(idx):
    """Texto en espanol de la carta, tal cual lo trae el juego (card_descspa.bin indexado por card_indxspa.bin)."""
    b = os.path.join(BASE, "datadat-extraido", "bin#")
    ind = open(os.path.join(b, "card_indxspa.bin"), "rb").read(); desc = open(os.path.join(b, "card_descspa.bin"), "rb").read()
    o = int.from_bytes(ind[idx * 4:idx * 4 + 4], "little")
    return desc[o:desc.index(b"\0", o)].decode("latin-1").strip()

def nombre_es(idx):
    """Nombre oficial en espanol que trae el juego (card_namespa.bin, registros de 64 bytes)."""
    b = open(os.path.join(BASE, "datadat-extraido", "bin#", "card_namespa.bin"), "rb").read()
    return b[idx * 64:(idx + 1) * 64].split(b"\0")[0].decode("latin-1").strip()

def slug(s):
    import re
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")

def figura_sin_fondo(ruta):
    img = Image.open(ruta).convert("RGB")
    img.thumbnail((TAM_FIGURA, TAM_FIGURA), Image.LANCZOS)
    fondo, brillo = fondo_conectado(img)
    a = (~fondo).astype(np.float32)
    a = np.asarray(Image.fromarray((a * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.6))).astype(np.float32) / 255.0
    a = np.maximum(a, np.clip((brillo.astype(np.float32) - UMBRAL_NEGRO) / 40.0, 0, 1) * (a > 0.02))
    rgba = img.copy(); rgba.putalpha(Image.fromarray((a * 255).astype(np.uint8)))
    # recorte ajustado a la figura (con un margen) para que el motor la apoye bien sobre la zona
    ys, xs = np.nonzero(a > 0.1)
    m = 12
    caja = (max(0, xs.min() - m), max(0, ys.min() - m), min(img.width, xs.max() + m), min(img.height, ys.max() + m))
    return rgba.crop(caja), img.crop(caja), a[caja[1]:caja[3], caja[0]:caja[2]]

def main():
    mapa = ilustraciones()
    datos = {r["nombre"]: r for r in csv.DictReader(open(os.path.join(BASE, "re-output", "cards.csv"), encoding="utf-8"))}
    s_depth = ort.InferenceSession(os.path.join(BASE, "herramientas", "modelos", "depth-anything-v2-small.onnx"),
                                   providers=["CPUExecutionProvider"])
    meta = []
    for cid, nombre, fig in CARTAS:
        d = datos[nombre]; dest = os.path.join(DESTINO, cid); os.makedirs(dest, exist_ok=True)
        gem = os.path.join(ARTE_GEMINI, slug(nombre), "resultado.png")
        if os.path.exists(gem):
            Image.open(gem).convert("RGB").save(os.path.join(dest, "arte.png")); origen_arte = "gemini"
        else:
            tmp = os.path.join(dest, "_tmp.png")
            Image.open(os.path.join(BASE, "datadat-extraido", "card", mapa[nombre.lower()])).convert("RGB").crop(ARTE_CAJA).save(tmp)
            mejorar(tmp, os.path.join(dest, "arte.png")); os.remove(tmp); origen_arte = "original x4"
        tipo_t = d["tipo"]
        clase = "magia" if tipo_t == "Magic" else "trampa" if tipo_t == "Trap" else \
                "fusion" if d["clase"] == "Fusion" else "efecto" if d["clase"] != "Normal" else "normal"
        figura_px = [0, 0]
        if fig and (os.path.exists(fig) or os.path.exists(os.path.join(dest, "figura.png"))):   # figura pendiente: se omite
            if not os.path.exists(os.path.join(dest, "figura.png")):
                rgba, rgb, a = figura_sin_fondo(fig)
                rgba.save(os.path.join(dest, "figura.png"))
                dv = np.asarray(profundidad(s_depth, rgb)).astype(np.float32) / 255.0
                Image.fromarray((dv * a * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(2)).save(os.path.join(dest, "profundidad.png"))
            figura_px = list(Image.open(os.path.join(dest, "figura.png")).size)
        open(os.path.join(dest, "descripcion.txt"), "w", encoding="utf-8").write(descripcion(int(d["idx"])))
        meta.append({"id": cid, "nombre": nombre_es(int(d["idx"])) or nombre, "nombre_en": nombre, "atk": int(d["atk"]), "def": int(d["defn"]), "nivel": int(d["nivel"]),
                     "tipo": d["tipo"], "atributo": d["attr"], "efecto": d["clase"] != "Normal", "clase": clase,
                     "campo": nombre in CAMPO, "figura_px": figura_px})
        print("ok %-26s %-7s arte %-11s figura %s" % (cid, clase, origen_arte, figura_px), flush=True)
    json.dump(meta, open(os.path.join(DESTINO, "cartas.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)

if __name__ == "__main__":
    main()
