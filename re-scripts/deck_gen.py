# Generador de biblioteca de mazos para la CPU (Yugi Reload, Fase A+)
# Produce .ydc validos (main + fusiones + side deck) balanceados por tier,
# replicando el sobre de los mazos originales: ~22 mon / ~11 mag / ~8 trampas,
# ATK prom 1300-1500, dificultad via densidad de monstruos de efecto.
# Uso: python -I deck_gen.py <cards.csv> <dir decks originales> <dir salida>
import csv, glob, os, random, struct, sys, zlib

CSV, ORIG, OUT = sys.argv[1], sys.argv[2], sys.argv[3]

def semilla(*partes):
    """Semilla estable entre ejecuciones (hash() de Python cambia en cada proceso)."""
    return zlib.crc32(repr(partes).encode("utf-8"))

# ---------- base de cartas ----------
cartas = list(csv.DictReader(open(CSV, encoding="utf-8")))
# solo las 771 jugables (CARD_Pack & 7 != 0): las ocultas no tienen ilustracion y el juego las dibuja como Slime
# Token (se quitaron de la biblioteca el 2026-10-16 con quitar_ocultas.py; aqui no deben volver a entrar)
_pack = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(CSV))), "datadat-extraido", "bin#", "card_pack.bin"), "rb").read()
cartas = [c for c in cartas if c["idx"].isdigit() and int.from_bytes(_pack[2 * int(c["idx"]):2 * int(c["idx"]) + 2], "little") & 7]
for c in cartas:
    c["id"] = int(c["id"]); c["atk"] = int(c["atk"]); c["defn"] = int(c["defn"])
    c["nivel"] = int(c["nivel"])
por_nombre = {}           # nombre -> carta canonica (primer id); artes alternativos agrupados
por_id = {}
for c in cartas:
    por_id[c["id"]] = c
    prev = por_nombre.get(c["nombre"])
    # id 0 es centinela (ningun mazo original lo usa): preferimos cualquier entrada con id != 0
    if prev is None or (prev["id"] == 0 and c["id"] != 0):
        por_nombre[c["nombre"]] = c
por_nombre_min = {k.lower(): v for k, v in por_nombre.items()}

def idd(nombre):
    c = por_nombre.get(nombre) or por_nombre_min.get(nombre.lower())  # "Call Of The Haunted" en el juego
    return c["id"] if c else None

faltantes = set()
def ids(nombres):
    r = []
    for n in nombres:
        i = idd(n)
        if i is None: faltantes.add(n)
        else: r.append(i)
    return r

# ---------- pools ----------
EXCLUIR_TIPOS = {"Divino", "Especial"}
def es_monstruo(c):
    return c["tipo"] not in ("Magic", "Trap") and c["tipo"] not in EXCLUIR_TIPOS
def jugable_main(c):
    return es_monstruo(c) and c["clase"] in ("Normal", "Efecto")

monstruos = [c for c in por_nombre.values() if jugable_main(c)]
TRIBUS = ["Dragon","Zombie","Fiend","Pyro","SeaSerpent","Rock","Machine","Fish","Dinosaur",
          "Insect","Beast","BeastWarrior","Plant","Aqua","Warrior","WingedBeast","Fairy",
          "Spellcaster","Thunder","Reptile"]
ATTRS = ["LIGHT","DARK","WATER","FIRE","EARTH","WIND"]

# ---------- staples curados (se validan contra el csv en runtime) ----------
REMOCION = ids(["Fissure","Dark Hole","Raigeki","Tribute to The Doomed","Monster Reborn",
                "Change of Heart","Snatch Steal","Premature Burial","Nobleman of Crossout",
                "Smashing Ground","Hammer Shot","Soul Exchange","Brain Control"])
PODER = ids(["Pot of Greed","Graceful Charity","Card Destruction","Heavy Storm",
             "Mystical Space Typhoon","Harpie's Feather Duster","Swords of Revealing Light",
             "Scapegoat","Giant Trunade","De-Spell","Remove Trap"])
EQUIPOS_GEN = ids(["Axe of Despair","Malevolent Nuzzler","Black Pendant","Horn of the Unicorn",
                   "United We Stand","Mage Power","Fairy Meteor Crush","Big Bang Shot"])
QUEMA = ids(["Ookazi","Tremendous Fire","Hinotama","Final Flame","Sparks","Restructer Revolution",
             "Just Desserts","Ceasefire","Secret Barrel","Chain Energy","Wave-Motion Cannon","Meteor of Destruction"])
CURA = ids(["Dian Keto the Cure Master","Red Medicine","Mooyan Curry","Soul of the Pure",
            "Goblin's Secret Remedy","Rain of Mercy"])
TRAMPAS_T0 = ids(["Trap Hole","Reinforcements","Castle Walls","Enchanted Javelin","Waboku",
                  "Ultimate Offering","House of Adhesive Tape","Eatgaboon","Fake Trap","Jar of Greed"])
TRAMPAS_T1 = ids(["Trap Hole","Waboku","Magic Jammer","Seven Tools of the Bandit","Dust Tornado",
                  "Robbin' Goblin","Shadow of Eyes","Gravity Bind","Jar of Greed","Backup Soldier"])
TRAMPAS_T2 = ids(["Mirror Force","Magic Cylinder","Call of the Haunted","Torrential Tribute",
                  "Trap Hole","Waboku","Magic Jammer","Seven Tools of the Bandit","Dust Tornado",
                  "Gravity Bind","Imperial Order","Solemn Judgment","Magical Hats","Mirror Wall"])
FLIPS = ids(["Man-Eater Bug","Hane-Hane","Penguin Soldier","Magician of Faith","Mask of Darkness",
             "Needle Worm","Cyber Jar","Morphing Jar","Big Eye","4-Starred Ladybug of Doom",
             "Princess of Tsurugi","Dream Clown","Wall of Illusion"])
BUSCADORES = ids(["Witch of the Black Forest","Sangan","Mystic Tomato","Shining Angel","Giant Rat",
                  "Mother Grizzly","UFO Turtle","Nimble Momonga","Flying Kamakiri #1"])
MUROS = ids(["Mystical Elf","Giant Soldier of Stone","Labyrinth Wall","Millennium Shield",
             "Big Shield Gardna","Island Turtle","Prevent Rat","Blocker","Earthbound Spirit","Spirit of the Harp"])
EXODIA = ids(["Exodia the Forbidden One","Right Arm of the Forbidden One","Left Arm of the Forbidden One",
              "Right Leg of the Forbidden One","Left Leg of the Forbidden One"])
QUEMA_MON = ids(["Fire Princess","Cannon Soldier","Catapult Turtle","Lava Battleguard","Burning Beast"])
CURA_MON = ids(["Cure Mermaid","Marie the Fallen One","Hysteric Fairy","Fire Princess","Dancing Fairy"])
MANO = ids(["White Magical Hat","Robbin' Goblin","Card Destruction","Drop Off","Delinquent Duo","The Forceful Sentry"])
CAMPOS = {"Fiend":"Yami","Spellcaster":"Yami","Warrior":"Sogen","BeastWarrior":"Sogen",
          "Aqua":"Umi","Fish":"Umi","SeaSerpent":"Umi","Thunder":"Mountain","Dragon":"Mountain",
          "WingedBeast":"Mountain","Beast":"Forest","Plant":"Forest","Insect":"Forest",
          "Zombie":"Wasteland","Dinosaur":"Wasteland","Rock":"Wasteland","Machine":None,
          "Fairy":"Sanctuary?","Pyro":"Molten Destruction","Reptile":"Wasteland"}
EQUIPO_TRIBU = {"Dragon":"Dragon Treasure","Zombie":"Violet Crystal","Fiend":"Sword of Dark Destruction",
                "Spellcaster":"Book of Secret Arts","Machine":"Machine Conversion Factory",
                "Insect":"Laser Cannon Armor","Beast":"Beast Fangs","Fairy":"Silver Bow and Arrow",
                "WingedBeast":"Follow Wind","Aqua":"Power of Kaishin","Warrior":"Legendary Sword",
                "Dinosaur":"Raise Body Heat","Pyro":"Burning Spear","Fish":"Power of Kaishin"}

# ritual spells y piezas sueltas fuera de pools genericos
def pool_tribu(tipo, max_lv=4, min_atk=0):
    return [c for c in monstruos if c["tipo"] == tipo and c["nivel"] <= max_lv and c["atk"] >= min_atk]
def pool_attr(attr, max_lv=4):
    return [c for c in monstruos if c["attr"] == attr and c["nivel"] <= max_lv]

def mejores(pool, n, rng, efecto_bias=0.0, excl=()):
    # ordena por ATK con algo de ruido; efecto_bias sube monstruos de efecto
    def score(c):
        s = max(c["atk"], c["defn"] * 0.7) + rng.uniform(0, 260)
        if c["clase"] == "Efecto": s += efecto_bias
        return s
    cand = [c for c in pool if c["id"] not in excl]
    cand.sort(key=score, reverse=True)
    return cand[:n]

# ---------- construccion de un mazo ----------
TIER_CFG = {  # (atk_cap_lv4, efecto_bias, trampas_pool, n_removal, n_poder)
    0: (1600, -150, TRAMPAS_T0, 1, 1),
    1: (1750,  100, TRAMPAS_T1, 2, 2),
    2: (1900,  300, TRAMPAS_T2, 3, 3),
    3: (1900,  500, TRAMPAS_T2, 3, 4),
}
ATK_PROM_MAX = {0: 1400, 1: 1427, 2: 1427, 3: 1427}  # techo + 40 de tolerancia <= 1467 (max. de los originales)

def normalizar_atk(main, conteo, rng, tier, pool):
    # si el promedio de ATK de los monstruos excede el techo del tier,
    # cambia los mas fuertes por opciones medias del mismo pool
    objetivo = ATK_PROM_MAX[tier]
    medios = [c for c in pool if c["atk"] <= objetivo and c["nivel"] <= 4]
    if not medios:
        medios = [c for c in monstruos if c["atk"] <= objetivo and c["nivel"] <= 4]
    for _ in range(60):
        mons = [i for i in main if por_id[i]["tipo"] not in ("Magic", "Trap")]
        prom = sum(por_id[i]["atk"] for i in mons) / max(1, len(mons))
        if prom <= objetivo + 40: break
        # quita el monstruo de nivel<=4 mas fuerte (no toca tributos: son pocos y legales)
        bajos = [i for i in mons if por_id[i]["nivel"] <= 4]
        if not bajos: break
        peor = max(bajos, key=lambda i: por_id[i]["atk"])
        main.remove(peor)
        conteo[por_id[peor]["nombre"]] -= 1
        rng.shuffle(medios)
        for c in medios:
            if conteo.get(c["nombre"], 0) < 3:
                main.append(c["id"])
                conteo[c["nombre"]] = conteo.get(c["nombre"], 0) + 1
                break

def armar(rng, tier, base_mons, tribu=None):
    atk_cap, ebias, trampas_pool, n_rem, n_pod = TIER_CFG[tier]
    base_mons = [c for c in base_mons if c["atk"] <= atk_cap]
    nm = rng.randint(21, 24)
    main = []          # lista de ids (con repeticion <=3 por nombre)
    conteo = {}
    def add(cid, maxrep=3):
        c = por_id.get(cid)
        if not c: return False
        k = c["nombre"]
        if conteo.get(k, 0) >= maxrep or len(main) >= 45: return False
        # tope de 3 monstruos de tributo (los originales llevan 2-3)
        if c["tipo"] not in ("Magic", "Trap") and c["nivel"] >= 5:
            if sum(1 for i in main if por_id[i]["tipo"] not in ("Magic","Trap") and por_id[i]["nivel"] >= 5) >= 3:
                return False
        conteo[k] = conteo.get(k, 0) + 1
        main.append(cid); return True
    # tributos primero: asi los iconos de la tribu (p.ej. Blue-Eyes) entran antes del tope de 3
    grandes = [c for c in monstruos if (tribu is None or c["tipo"] == tribu) and c["nivel"] >= 5]
    if not grandes: grandes = [c for c in monstruos if c["nivel"] >= 5]
    for c in mejores(grandes, 2 if tier < 2 else 3, rng, ebias):
        add(c["id"])
    # nucleo: mejores de la tribu, 2-3 copias de los top
    nucleo = mejores(base_mons, 14, rng, ebias)
    for j, c in enumerate(nucleo):
        add(c["id"])
        if j < 4 and rng.random() < 0.75: add(c["id"])
        if j < 2 and rng.random() < 0.5: add(c["id"])
        if sum(1 for i in main if por_id[i]["tipo"] not in ("Magic","Trap")) >= nm - 4: break
    # flips/buscadores para dar juego
    extra = FLIPS + BUSCADORES if tier >= 1 else FLIPS
    rng.shuffle(extra)
    while sum(1 for i in main if por_id[i]["tipo"] not in ("Magic","Trap")) < nm and extra:
        add(extra.pop())
    # magias
    objetivo_mag = rng.randint(10, 12)
    mags = []
    mags += rng.sample(REMOCION, min(n_rem, len(REMOCION)))
    mags += rng.sample(PODER, min(n_pod, len(PODER)))
    if tribu and EQUIPO_TRIBU.get(tribu):
        e = idd(EQUIPO_TRIBU[tribu])
        if e: mags += [e, e]
    if tribu and CAMPOS.get(tribu):
        f = idd(CAMPOS[tribu])
        if f: mags.append(f)
    relleno_mag = EQUIPOS_GEN + CURA + (QUEMA if tier >= 1 else [])
    rng.shuffle(relleno_mag)
    for m in mags + relleno_mag:
        if sum(1 for i in main if por_id[i]["tipo"] == "Magic") >= objetivo_mag: break
        add(m, maxrep=2)
    # trampas
    objetivo_trp = rng.randint(7, 9)
    tp = list(trampas_pool); rng.shuffle(tp)
    for t in tp * 2:
        if sum(1 for i in main if por_id[i]["tipo"] == "Trap") >= objetivo_trp: break
        add(t, maxrep=2)
    # ajuste final de tamano 40-45
    while len(main) < 40:
        c = rng.choice(base_mons or monstruos)
        add(c["id"])
    normalizar_atk(main, conteo, rng, tier, base_mons)
    return main, conteo

def armar_side(rng, tier, conteo_main, tribu=None):
    _, _, trampas_pool, _, _ = TIER_CFG[tier]
    side = []
    cands = (REMOCION + CURA + FLIPS + MUROS + trampas_pool +
             (pool_tribu(tribu) and [c["id"] for c in mejores(pool_tribu(tribu), 6, rng)] or []))
    rng.shuffle(cands)
    cnt = dict(conteo_main)
    for cid in cands:
        if len(side) >= 15: break
        c = por_id.get(cid)
        if not c: continue
        if cnt.get(c["nombre"], 0) >= 3: continue
        cnt[c["nombre"]] = cnt.get(c["nombre"], 0) + 1
        side.append(cid)
    return side

def escribir_ydc(path, header8, main, fus, side):
    with open(path, "wb") as f:
        f.write(header8)
        f.write(struct.pack("<H", len(main)))
        f.write(struct.pack("<%dH" % len(main), *main))
        f.write(struct.pack("<H", len(fus)))
        if fus: f.write(struct.pack("<%dH" % len(fus), *fus))
        f.write(struct.pack("<H", len(side)))
        if side: f.write(struct.pack("<%dH" % len(side), *side))

# header float por tier (tomados de los originales)
HDR = {0: bytes.fromhex("01000000c6c6873e"), 1: bytes.fromhex("01fc12004f57443f"),
       2: bytes.fromhex("01cccccc38e87c40"), 3: bytes.fromhex("01ccccccef6a9b40")}
# ojo: en el original los floats bajos = mazos dificiles ful_3*; mantenemos por slot al parchear,
# este header solo es relleno valido.

os.makedirs(OUT, exist_ok=True)
manifest = []

def emitir(nombre, tier, main, fus, side, arquetipo):
    path = os.path.join(OUT, nombre + ".ydc")
    escribir_ydc(path, HDR[tier], main, fus, side)
    mons = sum(1 for i in main if por_id[i]["tipo"] not in ("Magic","Trap"))
    atks = [por_id[i]["atk"] for i in main if por_id[i]["tipo"] not in ("Magic","Trap")]
    manifest.append(dict(archivo=nombre + ".ydc", tier=tier, arquetipo=arquetipo,
                         n=len(main), mon=mons, atk_prom=int(sum(atks)/max(1,len(atks))),
                         fus=len(fus), side=len(side)))

random.seed(20261010)

# 1) tribales: 20 tribus x 4 tiers x 4 variantes
for tribu in TRIBUS:
    pool = pool_tribu(tribu)
    if len(pool) < 12:  # tribus de nivel alto (Dragon): admite hasta lv6 en el nucleo
        pool = pool_tribu(tribu, max_lv=6)
    if len(pool) < 12: continue
    for tier in range(4):
        for v in range(4):
            rng = random.Random(semilla(tribu, tier, v))
            main, cnt = armar(rng, tier, pool, tribu)
            side = armar_side(rng, tier, cnt, tribu)
            emitir("trb_%s_t%d_v%d" % (tribu.lower(), tier, v), tier, main, [], side, "tribal " + tribu)

# 2) por atributo: 6 attrs x tiers 1-3 x 2 variantes
for attr in ATTRS:
    pool = pool_attr(attr)
    for tier in (1, 2, 3):
        for v in range(3):
            rng = random.Random(semilla(attr, tier, v))
            main, cnt = armar(rng, tier, pool)
            side = armar_side(rng, tier, cnt)
            emitir("atr_%s_t%d_v%d" % (attr.lower(), tier, v), tier, main, [], side, "atributo " + attr)

# 3) estrategias
def deck_estrategia(nombre, tier, rng, mons_fijos, mags_extra, trps_extra, arquetipo):
    atk_cap, ebias, trampas_pool, n_rem, n_pod = TIER_CFG[tier]
    main = []; conteo = {}
    def add(cid, maxrep=3):
        c = por_id.get(cid)
        if not c: return False
        k = c["nombre"]
        if conteo.get(k, 0) >= maxrep or len(main) >= 45: return False
        conteo[k] = conteo.get(k, 0) + 1; main.append(cid); return True
    for cid in mons_fijos: add(cid)
    relleno = mejores([c for c in monstruos if c["atk"] <= atk_cap and c["nivel"] <= 4], 30, rng, ebias)
    while sum(1 for i in main if por_id[i]["tipo"] not in ("Magic","Trap")) < 21 and relleno:
        add(relleno.pop(0)["id"])
    for m in mags_extra + rng.sample(REMOCION, min(n_rem, len(REMOCION))) + rng.sample(PODER, min(n_pod, len(PODER))):
        add(m, maxrep=3 if m in QUEMA else 2)
    tp = trps_extra + trampas_pool
    for t in tp:
        if sum(1 for i in main if por_id[i]["tipo"] == "Trap") >= 9: break
        add(t, maxrep=2)
    while len(main) < 40 and relleno:
        add(relleno.pop(0)["id"])
    normalizar_atk(main, conteo, rng, tier, monstruos)
    side = armar_side(rng, tier, conteo)
    emitir(nombre, tier, main, [], side, arquetipo)

for tier in (1, 2, 3):
    for v in range(3):
        rng = random.Random(semilla("estr", tier, v))
        deck_estrategia("est_quema_t%d_v%d" % (tier, v), tier, rng,
                        QUEMA_MON * 2 + CURA_MON, QUEMA * 2, [], "quemadura")
        deck_estrategia("est_muro_t%d_v%d" % (tier, v), tier, rng,
                        MUROS * 2 + FLIPS, ids(["Swords of Revealing Light","Messenger of Peace","Dark Hole"]) * 2,
                        ids(["Gravity Bind","Waboku","Mirror Wall"]) * 2, "muro-trampas")
        deck_estrategia("est_mano_t%d_v%d" % (tier, v), tier, rng,
                        MANO + BUSCADORES, ids(["Card Destruction"]) * 2, ids(["Robbin' Goblin","Drop Off"]) * 2, "control de mano")
        deck_estrategia("est_flip_t%d_v%d" % (tier, v), tier, rng,
                        FLIPS * 2, ids(["Swords of Revealing Light","Book of Taiyou"]) * 2, [], "flip-sorpresa")
        deck_estrategia("est_cura_t%d_v%d" % (tier, v), tier, rng,
                        CURA_MON * 3, CURA * 2, ids(["Solemn Wishes","Gift of The Mystical Elf"]) * 2, "curacion")

# exodia (tier 2-3)
for tier in (2, 3):
    for v in range(3):
        rng = random.Random(semilla("exo", tier, v))
        deck_estrategia("est_exodia_t%d_v%d" % (tier, v), tier, rng,
                        EXODIA + MUROS + BUSCADORES,
                        ids(["Pot of Greed","Graceful Charity","Jar of Greed","Swords of Revealing Light"]) * 2,
                        ids(["Waboku","Gravity Bind","Jar of Greed","Backup Soldier"]) * 2, "Exodia")

# 4) variantes de los 58 originales (conservan fusiones y rituales correctos)
def leer_ydc_full(path):
    d = open(path, "rb").read()
    n = struct.unpack("<H", d[8:10])[0]
    main = list(struct.unpack("<%dH" % n, d[10:10+n*2]))
    p = 10 + n*2
    nf = struct.unpack("<H", d[p:p+2])[0]
    fus = list(struct.unpack("<%dH" % nf, d[p+2:p+2+nf*2])) if nf else []
    p += 2 + nf*2
    n3 = struct.unpack("<H", d[p:p+2])[0]
    side = list(struct.unpack("<%dH" % n3, d[p+2:p+2+n3*2])) if n3 else []
    return d[:8], main, fus, side

def tier_de(fn):
    # cpu_0XY: el tier es el segundo digito (cpu_000-004 t0, cpu_010-015 t1, cpu_020-029 t2)
    if fn.startswith("cpu_0"): return min(int(fn[5]), 3)
    if fn.startswith("ful_"): return int(fn[4])
    return 1

for path in sorted(glob.glob(os.path.join(ORIG, "*.ydc"))):
    fn = os.path.basename(path)[:-4]
    hdr, main, fus, side0 = leer_ydc_full(path)
    tier = tier_de(fn)
    mats = set()
    for c in main:
        cc = por_id.get(c)
        if cc and cc["clase"] in ("Fusion", "Ritual"): mats.add(c)
    for v in range(2):
        rng = random.Random(semilla(fn, v))
        # conserva nucleo (60%): fusiones, rituales, y cartas aleatorias; re-rolea el resto
        nucleo = [c for c in main if c in mats] + [c for c in main if c not in mats and rng.random() < 0.6]
        conteo = {}
        nuevo = []
        for c in nucleo:
            cc = por_id.get(c)
            k = cc["nombre"] if cc else str(c)
            conteo[k] = conteo.get(k, 0) + 1
            nuevo.append(c)
        atk_cap, ebias, trampas_pool, _, _ = TIER_CFG[tier]
        rel_m = mejores([c for c in monstruos if c["atk"] <= atk_cap and c["nivel"] <= 4], 24, rng, ebias)
        rel_x = rng.sample(REMOCION + PODER + CURA, 8) + rng.sample(trampas_pool, min(5, len(trampas_pool)))
        objetivo = len(main)
        fuentes = rel_m + [por_id[i] for i in rel_x if i in por_id]
        fi = 0
        while len(nuevo) < objetivo and fi < len(fuentes):
            c = fuentes[fi]; fi += 1
            k = c["nombre"]
            if conteo.get(k, 0) >= 3: continue
            conteo[k] = conteo.get(k, 0) + 1
            nuevo.append(c["id"])
        normalizar_atk(nuevo, conteo, rng, tier, monstruos)
        rng2 = random.Random(semilla(fn, v, "s"))
        if side0:
            # el side heredado cuenta para el limite de 3 copias (main + side), como en los originales
            side, usados_side = [], dict(conteo)
            for e in side0:
                k = por_id[e]["nombre"] if e in por_id else e
                if usados_side.get(k, 0) >= 3: continue
                usados_side[k] = usados_side.get(k, 0) + 1
                side.append(e)
        else:
            side = armar_side(rng2, tier, conteo)
        nombre = "var_%s_v%d" % (fn, v)
        escribir_ydc(os.path.join(OUT, nombre + ".ydc"), hdr, nuevo, fus, side)
        mons = sum(1 for i in nuevo if i in por_id and por_id[i]["tipo"] not in ("Magic","Trap"))
        atks = [por_id[i]["atk"] for i in nuevo if i in por_id and por_id[i]["tipo"] not in ("Magic","Trap")]
        manifest.append(dict(archivo=nombre + ".ydc", tier=tier, arquetipo="variante " + fn,
                             n=len(nuevo), mon=mons, atk_prom=int(sum(atks)/max(1,len(atks))),
                             fus=len(fus), side=len(side)))

# 5) familia "caos": drafts con las cartas que ningun otro mazo uso (cobertura total del pool)
usadas = set()
for m in manifest:
    d = open(os.path.join(OUT, m["archivo"]), "rb").read()
    n = struct.unpack("<H", d[8:10])[0]
    usadas.update(por_id[e]["nombre"] for e in struct.unpack("<%dH" % n, d[10:10+n*2]) if e in por_id)
for path in glob.glob(os.path.join(ORIG, "*.ydc")):
    _, main0, fus0, side0 = leer_ydc_full(path)
    usadas.update(por_id[e]["nombre"] for e in main0 + fus0 + side0 if e in por_id)

sin_usar_mon = [c for c in monstruos if c["nombre"] not in usadas and c["nivel"] <= 6]
sin_usar_mag = [c for c in por_nombre.values() if c["tipo"] == "Magic" and c["nombre"] not in usadas
                and "Ritual" not in c["nombre"]]
sin_usar_trp = [c for c in por_nombre.values() if c["tipo"] == "Trap" and c["nombre"] not in usadas]
rngc = random.Random(777)
rngc.shuffle(sin_usar_mon); rngc.shuffle(sin_usar_mag); rngc.shuffle(sin_usar_trp)
ci = 0
while len(sin_usar_mon) >= 8:
    tier = ci % 2  # solo tiers 0-1: son drafts sin sinergia
    main = []; conteo = {}
    trib = 0
    objetivo_mon = rngc.randint(22, 24)
    pendientes = []
    while sum(1 for i in main if por_id[i]["tipo"] not in ("Magic","Trap")) < objetivo_mon and sin_usar_mon:
        c = sin_usar_mon.pop()
        if c["nivel"] >= 5:
            if trib >= 3:
                pendientes.append(c)  # vuelve al fondo para otro mazo caos
                continue
            trib += 1
        main.append(c["id"]); conteo[c["nombre"]] = 1
    sin_usar_mon = pendientes + sin_usar_mon
    # respaldo: si el pool de ineditas se agoto, completa con monstruos comunes lv<=4
    respaldo = [c for c in monstruos if c["nivel"] <= 4 and c["atk"] <= 1450]
    rngc.shuffle(respaldo)
    for c in respaldo:
        if sum(1 for i in main if por_id[i]["tipo"] not in ("Magic","Trap")) >= objetivo_mon: break
        if conteo.get(c["nombre"], 0) >= 2: continue
        main.append(c["id"]); conteo[c["nombre"]] = conteo.get(c["nombre"], 0) + 1
    nmag = 0
    while nmag < 10:
        c = sin_usar_mag.pop() if sin_usar_mag else por_id[rngc.choice(CURA + REMOCION)]
        if conteo.get(c["nombre"], 0) >= 2: continue
        main.append(c["id"]); conteo[c["nombre"]] = conteo.get(c["nombre"], 0) + 1; nmag += 1
    ntrp = 0
    while ntrp < 8:
        c = sin_usar_trp.pop() if sin_usar_trp else por_id[rngc.choice(TRAMPAS_T0)]
        if conteo.get(c["nombre"], 0) >= 2: continue
        main.append(c["id"]); conteo[c["nombre"]] = conteo.get(c["nombre"], 0) + 1; ntrp += 1
    normalizar_atk(main, conteo, rngc, tier, monstruos)
    side = armar_side(rngc, tier, conteo)
    emitir("caos_%02d" % ci, tier, main, [], side, "caos (draft)")
    ci += 1

# manifest
with open(os.path.join(OUT, "manifest.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["archivo","tier","arquetipo","n","mon","atk_prom","fus","side"])
    w.writeheader()
    for m in manifest: w.writerow(m)

print("mazos generados:", len(manifest))
from collections import Counter
print("por tier:", dict(Counter(m["tier"] for m in manifest)))
if faltantes:
    print("nombres no encontrados en el juego (%d):" % len(faltantes), "; ".join(sorted(faltantes)[:25]))
