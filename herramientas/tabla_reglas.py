# Genera remake-ps5/src/reglas/tabla_reglas.h: la regla de combate, el color de su efecto y si vuela, para cada
# carta del remake (remake/recursos/cartas/cartas.json), desde remake/diseno/reglas_combate.json (Excel del usuario).
# Uso: python -I tabla_reglas.py
import json, os, re

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REG = json.load(open(os.path.join(BASE, "remake", "diseno", "reglas_combate.json"), encoding="utf-8"))
CARTAS = json.load(open(os.path.join(BASE, "remake", "recursos", "cartas", "cartas.json"), encoding="utf-8"))
CARTAS = CARTAS if isinstance(CARTAS, list) else CARTAS.get("cartas", [])
# color del ataque de quien lo lanza, conocido de la carta/serie (pedido del usuario: el color depende de quien ataca)
CONOCIDO = {"red_eyes": (1.6, 0.35, 0.08), "blue_eyes": (0.6, 0.85, 1.6), "baby_dragon": (1.6, 0.55, 0.1),
            "summoned_skull": (0.45, 0.6, 1.6), "flame_swordsman": (1.6, 0.45, 0.08)}
COLOR = {"WATER": (0.12, 0.55, 1.6), "FIRE": (1.6, 0.45, 0.08), "WIND": (0.25, 1.4, 0.45), "EARTH": (1.2, 0.7, 0.25),
         "LIGHT": (1.4, 1.1, 0.35), "DARK": (0.55, 0.18, 1.5)}


def slug(s):
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


filas = []
for c in CARTAS:
    k = slug(c.get("nombre_en", c["id"]))
    r = REG["cartas"].get(k) or REG["cartas"].get(c["id"])
    if not r:
        print("sin regla:", c["id"], k)
        continue
    m = r.get("color_magia")
    halo = CONOCIDO.get(c["id"]) or (tuple(m["halo"]) if m else COLOR.get(r["atributo"], (1.0, 1.0, 1.0)))
    nucleo = tuple(m["nucleo"]) if m else tuple(round(min(1.0, 0.75 + 0.25 * x / 1.6), 2) for x in halo)
    filas.append('\t{ "%s", "%s", { %.2ff, %.2ff, %.2ff }, { %.2ff, %.2ff, %.2ff }, %s },   // %s (%s, %s)'
                 % (c["id"], r["regla"], *halo, *nucleo, "true" if r["cuerpo"] == "volador_alado" else "false",
                    r["nombre"], r["tipo"], r["atributo"]))
salida = os.path.join(BASE, "remake-ps5", "src", "reglas", "tabla_reglas.h")
open(salida, "w", encoding="utf-8").write(
    "// GENERADO por herramientas/tabla_reglas.py desde remake/diseno/reglas_combate.json: no editar a mano.\n"
    "// Regla de combate de cada carta del remake (Excel reglas-yugi.xlsx del usuario), color de su efecto y si vuela.\n"
    "#pragma once\n\nnamespace combate {\n\nstruct ReglaCarta { const char* carta; const char* regla; float halo[3], nucleo[3]; bool vuela; };\n\n"
    "const ReglaCarta TABLA_REGLAS[] = {\n" + "\n".join(filas) + "\n};\n\n} // namespace combate\n")
print(len(filas), "cartas ->", salida)
