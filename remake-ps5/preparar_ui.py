# Prepara lo que necesita la interfaz del duelo (interfaz.h) y que no va al repo: la cara de cada carta en dos
# tamanos (visor y mano) y una tabla de texto con sus datos (nombre, nivel, atributo, tipo, ATK/DEF, descripcion).
# Lee remake/recursos/cartas (cartas.json + <id>/cara.png + <id>/descripcion.txt) y escribe en <salida>:
#   cara_<id>.png (360 px de ancho), mini_<id>.png (180 px), cartas_ui.txt (UTF-8, una carta por linea, campos con |)
# Uso: python -I preparar_ui.py <recursos/cartas> <salida> [<salida2> ...]
import json, os, shutil, sys
from PIL import Image

TIPOS = {"Dragon": "Dragón", "Warrior": "Guerrero", "Spellcaster": "Lanzador de Conjuros", "Fiend": "Demonio",
         "WingedBeast": "Bestia Alada", "Machine": "Máquina", "Rock": "Roca", "Fish": "Pez", "Beast": "Bestia",
         "SeaSerpent": "Serpiente Marina", "Zombie": "Zombi", "Aqua": "Aqua", "Pyro": "Piro", "Thunder": "Trueno",
         "Insect": "Insecto", "Plant": "Planta", "Reptile": "Reptil", "Dinosaur": "Dinosaurio",
         "BeastWarrior": "Guerrero-Bestia", "Fairy": "Hada", "Magic": "Carta Mágica", "Trap": "Carta de Trampa"}
ATRIBUTOS = {"DARK": "OSCURIDAD", "LIGHT": "LUZ", "EARTH": "TIERRA", "WATER": "AGUA", "FIRE": "FUEGO",
             "WIND": "VIENTO", "-": "MAGIA"}

origen, salidas = sys.argv[1], sys.argv[2:]
cartas = json.load(open(os.path.join(origen, "cartas.json"), encoding="utf-8"))
primera = salidas[0]
os.makedirs(primera, exist_ok=True)
lineas = []
for c in cartas:
    cid = c["id"]
    cara = Image.open(os.path.join(origen, cid, "cara.png")).convert("RGB")
    for nombre, ancho in (("cara", 360), ("mini", 180)):
        alto = round(cara.height * ancho / cara.width)
        cara.resize((ancho, alto), Image.LANCZOS).convert("RGBA").save(os.path.join(primera, f"{nombre}_{cid}.png"), optimize=True)
    desc = open(os.path.join(origen, cid, "descripcion.txt"), encoding="utf-8").read().strip().replace("\n", " ").replace("|", "/")
    atributo = "TRAMPA" if c["clase"] == "trampa" else ATRIBUTOS.get(c["atributo"], c["atributo"])
    if c["clase"] == "magia":
        atributo = "MAGIA"
    lineas.append("|".join(str(v) for v in (cid, c["nombre"], c["clase"], atributo, TIPOS.get(c["tipo"], c["tipo"]),
                                           c["nivel"], c["atk"], c["def"], desc)))
open(os.path.join(primera, "cartas_ui.txt"), "w", encoding="utf-8", newline="\n").write("\n".join(lineas) + "\n")
for otra in salidas[1:]:
    os.makedirs(otra, exist_ok=True)
    for f in os.listdir(primera):
        shutil.copy2(os.path.join(primera, f), os.path.join(otra, f))
print(len(cartas), "cartas ->", ", ".join(salidas))
