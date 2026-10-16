# Reglas de combate de los monstruos (ataque, efecto, defensa y derrota) a partir del Excel del usuario
# D:\Yugi-Reload\reglas-yugi.xlsx (Hoja2) y sus respuestas del 2026-10-16:
#  - prioridad: arma > mistico > maquina > dragon > agua > resto (insecto, roca, animal, embestida);
#  - "agua" = atributo WATER de la carta;
#  - el arma manda, cada una a su modo: de mano = cuerpo a cuerpo, de fuego/arco = proyectil, baculo = rayo;
#  - lo que el Excel no cubre (zombi, demonio, planta, piro, trueno...) lo propongo yo: "propuesta": true;
#  - el elemento (atributo) da el color del efecto.
# Lee remake/diseno/plantillas.json (cuerpo de cada monstruo) y escribe remake/diseno/reglas_combate.json.
# Uso: python -I reglas_combate.py
import csv, json, os, collections

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIS = os.path.join(BASE, "remake", "diseno")

CAER = "cae derrotado al piso"
OJOS = "cierra los ojos y recibe el impacto"
REGLAS = {
    # --- del Excel (Hoja2) ---
    "arma_mano": {"excel": 1, "ataque": "golpe con su arma (espada, hacha, lanza...) cuerpo a cuerpo", "efecto": "golpe fuerte",
                  "defensa": "pone su arma por delante", "derrota": CAER},
    "arma_fuego": {"excel": 2, "ataque": "dispara un proyectil desde su arma, a distancia", "efecto": "explosion",
                   "defensa": "cruza los brazos", "derrota": CAER},
    "mistico": {"excel": 3, "ataque": "rayo desde su arma (baculo, varita) o desde las manos; 1 de 5 rayos al azar en cada ataque",
                "efecto": "efecto de hechizo", "defensa": "interpone su baculo/arma; si no tiene, cruza los brazos en X",
                "derrota": CAER},
    "agua": {"excel": 4, "ataque": "rafaga de agua", "efecto": "agua regada", "defensa": "cierra los ojos",
             "derrota": "se diluye en agua"},
    "maquina": {"excel": 5, "ataque": "ataca a distancia con su arma; si no tiene, punetazos directos",
                "efecto": "chispas de maquina", "defensa": "cruza los brazos (o se cubre con su blindaje)",
                "derrota": "explosion de fuego"},
    "embestida": {"excel": "5b", "ataque": "embestida de bestia", "efecto": "golpe duro", "defensa": OJOS, "derrota": CAER},
    "dragon": {"excel": 6, "ataque": "rafaga de fuego a distancia", "efecto": "fuego fuerte de dragon",
               "defensa": "dobla sus alas hacia el frente", "derrota": CAER},
    "insecto_aire": {"excel": 7, "ataque": "embestida por aire", "efecto": "embestida aerea", "defensa": OJOS,
                     "derrota": "cae al suelo y se destruye"},
    "insecto_tierra": {"excel": 8, "ataque": "embestida por tierra", "efecto": "embestida por tierra", "defensa": OJOS,
                       "derrota": CAER},
    "roca": {"excel": 9, "ataque": "golpe cuerpo a cuerpo", "efecto": "demolicion de rocas", "defensa": OJOS, "derrota": CAER},
    "animal_aire": {"excel": 10, "ataque": "embestida por aire", "efecto": "embestida aerea", "defensa": OJOS,
                    "derrota": "cae al suelo y se destruye"},
    "animal_tierra": {"excel": 11, "ataque": "embestida por tierra", "efecto": "embestida por tierra", "defensa": OJOS,
                      "derrota": CAER},
    # --- propuestas mias (no estan en el Excel): revisar con el usuario ---
    "piro": {"propuesta": True, "ataque": "llamarada desde el cuerpo o las manos", "efecto": "fuego",
             "defensa": OJOS, "derrota": "se consume en llamas"},
    "trueno": {"propuesta": True, "ataque": "descarga electrica a distancia", "efecto": "rayos y chispas azules",
               "defensa": OJOS, "derrota": "se apaga entre chispas y cae"},
    "zombi": {"propuesta": True, "ataque": "embestida/zarpazo de no-muerto", "efecto": "golpe duro con humo oscuro",
              "defensa": OJOS, "derrota": "se desmorona en polvo y huesos"},
    "demonio": {"propuesta": True, "ataque": "zarpazo o embestida", "efecto": "golpe duro con llamas oscuras",
                "defensa": "cruza los brazos", "derrota": "se desvanece en humo oscuro"},
    "planta": {"propuesta": True, "ataque": "latigazo de lianas o espinas", "efecto": "hojas y espinas",
               "defensa": OJOS, "derrota": "se marchita y cae"},
    "espiritu": {"propuesta": True, "ataque": "se lanza atravesando al rival / suelta energia", "efecto": "estela de energia",
                 "defensa": "se encoge y parpadea", "derrota": "se desvanece en luz"},
    "objeto": {"propuesta": True, "ataque": "tiembla y lanza energia (o se abre y muerde)", "efecto": "destello",
               "defensa": "tiembla", "derrota": "se rompe en pedazos"},
}

RAYOS_MISTICOS = ["rayo electrico desde la punta (el del Mago Oscuro)", "esfera de energia que viaja y estalla",
                  "haz continuo (laser) que empuja al rival", "lluvia de destellos/estrellas sobre el rival",
                  "espiral arcana que envuelve al rival"]
COLOR_ELEMENTO = {"WATER": "azul agua", "FIRE": "rojo/naranja fuego", "WIND": "verde remolino", "EARTH": "marron/polvo",
                  "LIGHT": "dorado/blanco", "DARK": "morado/negro"}

# arma de cada monstruo segun su cuerpo (plantilla) y casos conocidos de su carta
ARMA_PLANTILLA = {"lanzador_baculo": "baculo", "guerrero_espada": "mano", "guerrero_arma_larga": "mano",
                  "tirador": "fuego", "jinete": "mano"}  # jinetes: lanza/hacha (Gaia, Rabid Horseman)
SIN_ARMA = {"Dokurorider"}  # jinete en moto, sin arma
# maquinas sin arma (pelean con su cuerpo): punetazos/mordidas; el resto de maquinas disparan
MAQUINA_SIN_ARMA = {"Steel Ogre Grotto #1", "Steel Ogre Grotto #2", "Giga-Tech Wolf", "Spikebot", "Mechanicalchaser",
                    "Mechanical Snail", "Metal Fish", "Kinetic Soldier", "Cyber-Tech Alligator"}


def decidir(c, attr):
    """(regla, arma, motivo) por la prioridad acordada: arma > mistico > maquina > dragon > agua > resto."""
    p, t = c["plantilla"], c["tipo"]
    arma = "ninguna" if c["nombre"] in SIN_ARMA else ARMA_PLANTILLA.get(p, "ninguna")
    if t == "Machine" and arma == "ninguna":
        arma = "ninguna" if c["nombre"] in MAQUINA_SIN_ARMA else "integrada"
    if arma == "mano":
        return "arma_mano", arma, "tiene arma de mano"
    if arma == "fuego":
        return "arma_fuego", arma, "tiene arma de fuego o arco"
    if arma == "baculo" or p == "lanzador_manos" or t in ("Spellcaster", "Fairy"):
        return "mistico", arma, "mistico (mago, hada, bruja...)"
    if t == "Machine":
        return "maquina", arma, "maquina"
    if t == "Dragon":
        return "dragon", arma, "dragon"
    if attr == "WATER":
        return "agua", arma, "atributo agua"
    if p == "criatura_pequena" and t not in ("Insect", "Rock"):
        return "embestida", arma, "criatura pequena (Kuriboh): embestida"
    if t == "Insect":
        return ("insecto_aire" if p == "volador_alado" else "insecto_tierra"), arma, "insecto"
    if t == "Rock":
        return "roca", arma, "roca"
    if t in ("Beast", "WingedBeast", "Dinosaur", "Reptile", "BeastWarrior", "Fish", "SeaSerpent", "Aqua"):
        aire = p == "volador_alado" or t == "WingedBeast"  # Harpie Lady: humanoide con alas, ataca volando
        return ("animal_aire" if aire else "animal_tierra"), arma, "animal"
    if t == "Pyro":
        return "piro", arma, "piro (propuesta)"
    if t == "Thunder":
        return "trueno", arma, "trueno (propuesta)"
    if t == "Zombie":
        return "zombi", arma, "zombi (propuesta)"
    if t == "Plant":
        return ("objeto" if p == "objeto" else "planta"), arma, "planta (propuesta)"
    if t == "Fiend":
        if p == "espiritu":
            return "espiritu", arma, "espiritu (propuesta)"
        if p == "objeto":
            return "objeto", arma, "objeto (propuesta)"
        if p == "volador_alado":
            return "animal_aire", arma, "demonio volador como animal de aire"
        return "demonio", arma, "demonio (propuesta)"
    if p == "espiritu":
        return "espiritu", arma, "espiritu (propuesta)"
    if p == "objeto":
        return "objeto", arma, "objeto (propuesta)"
    return "embestida", arma, "sin arma ni magia: embestida (regla 5b)"


def main():
    plant = json.load(open(os.path.join(DIS, "plantillas.json"), encoding="utf-8"))
    attr = {r["nombre"]: r["attr"] for r in csv.DictReader(open(os.path.join(BASE, "re-output", "cards.csv"), encoding="utf-8"))}
    cartas = {}
    for k, c in plant["cartas"].items():
        a = attr.get(c["nombre"], "")
        regla, arma, motivo = decidir(c, a)
        cartas[k] = {"nombre": c["nombre"], "tipo": c["tipo"], "atributo": a, "cuerpo": c["plantilla"], "arma": arma,
                     "regla": regla, "motivo": motivo, "color_efecto": COLOR_ELEMENTO.get(a, "-"),
                     **({"propuesta": True} if REGLAS[regla].get("propuesta") else {}),
                     **({"revisar": True} if c.get("revisar") else {})}
    cuenta = collections.Counter(c["regla"] for c in cartas.values())
    for r in REGLAS:
        REGLAS[r]["monstruos"] = cuenta.get(r, 0)
    json.dump({"_nota": "Reglas de combate (Excel reglas-yugi.xlsx Hoja2 + respuestas del usuario 2026-10-16). "
               "Prioridad: arma > mistico > maquina > dragon > agua > resto. 'propuesta' = regla mia, no del Excel. "
               "Generado por herramientas/reglas_combate.py",
               "prioridad": ["arma", "mistico", "maquina", "dragon", "agua", "insecto/roca/animal", "propuestas", "embestida"],
               "rayos_misticos": RAYOS_MISTICOS, "color_por_elemento": COLOR_ELEMENTO, "reglas": REGLAS, "cartas": cartas},
              open(os.path.join(DIS, "reglas_combate.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    for r, n in cuenta.most_common():
        print("  %-15s %3d %s" % (r, n, "(propuesta)" if REGLAS[r].get("propuesta") else "(Excel %s)" % REGLAS[r]["excel"]))
    print("total", len(cartas))


main()
