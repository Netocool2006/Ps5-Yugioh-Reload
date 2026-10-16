# Catalogo de plantillas (arquetipos) de monstruos y clasificacion de los 496 monstruos usables (466 con ilustracion), como hacen
# los estudios: un esqueleto y un juego de movimientos por familia de cuerpo, no uno por monstruo. La clasificacion
# es por como se ve cada monstruo en su carta (conocimiento de las cartas); "revisar" = confirmar con su figura.png
# antes de producirlo. Escribe remake/diseno/plantillas.json. Uso: python -I clasificar_plantillas.py
import csv, json, os, re, collections

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PLANTILLAS = {
    "lanzador_baculo": {
        "nombre": "Lanzador con baculo", "ejemplo": "Mago Oscuro, Maga Oscura",
        "cuerpo": "humanoide con baculo, cetro o varita", "esqueleto": "Meshy (humanoide) + hueso Baculo propio",
        "reposo": "Idle 3 de frente al monitor, cabeza alzada, baculo a dos manos",
        "ataque": "gira hacia el rival, carga el baculo atras y lanza rayo electrico desde la punta",
        "herramientas": "arma_a_mano.py nuevo:Baculo; LANZADORES[] en yugireload.cpp",
        "creditos": 8, "hecha": True},
    "guerrero_espada": {
        "nombre": "Guerrero con espada", "ejemplo": "Guardian Celta",
        "cuerpo": "humanoide con espada, sable o arma corta de una mano (con o sin escudo)",
        "esqueleto": "Meshy (humanoide), arma pegada a la mano",
        "reposo": "de frente al monitor, cabeza alzada", "ataque": "corre/salta y da un tajo; se cubre y cae al perder",
        "herramientas": "arma_a_mano.py <mano> gris", "creditos": 8, "hecha": True},
    "guerrero_arma_larga": {
        "nombre": "Guerrero con arma larga o pesada", "ejemplo": "Asaltante con Hacha, Buey de Batalla",
        "cuerpo": "humanoide con hacha, lanza, martillo, maza, guadana o latigo (a dos manos)",
        "esqueleto": "Meshy (humanoide) + hueso de arma propio (como el baculo)",
        "reposo": "de frente, arma en guardia", "ataque": "golpe de arriba abajo o estocada a dos manos",
        "herramientas": "arma_a_mano.py nuevo:<Arma>", "creditos": 8, "hecha": False},
    "tirador": {
        "nombre": "Tirador (arco o arma de fuego)", "ejemplo": "Arquera Amazona",
        "cuerpo": "humanoide con arco, ballesta o arma de fuego", "esqueleto": "Meshy (humanoide)",
        "reposo": "de frente, arma baja", "ataque": "apunta y dispara un proyectil con estela",
        "herramientas": "arma_a_mano.py; proyectil por codigo", "creditos": 8, "hecha": False},
    "lanzador_manos": {
        "nombre": "Hechicero sin arma", "ejemplo": "Elfa Mistica, Jinzo",
        "cuerpo": "humanoide que ataca con magia de las manos (hadas, brujas, espiritus con cuerpo)",
        "esqueleto": "Meshy (humanoide)", "reposo": "de frente, manos juntas o abiertas",
        "ataque": "extiende las manos y lanza una esfera o rayo de energia",
        "herramientas": "efecto de rayo de crear_rayo.py", "creditos": 8, "hecha": False},
    "luchador": {
        "nombre": "Luchador cuerpo a cuerpo", "ejemplo": "Craneo Convocado, Hombre Karate",
        "cuerpo": "humanoide o monstruo de dos patas que pega con punos o garras",
        "esqueleto": "Meshy (humanoide)", "reposo": "de frente, guardia",
        "ataque": "avanza y da un punetazo o zarpazo", "herramientas": "-", "creditos": 8, "hecha": False},
    "jinete": {
        "nombre": "Jinete o centauro", "ejemplo": "Gaia el Caballero Feroz",
        "cuerpo": "jinete sobre montura, o centauro", "esqueleto": "sin esqueleto (cuerpo rigido)",
        "reposo": "de frente, la montura respira", "ataque": "carga en linea recta con la lanza al frente y vuelve",
        "herramientas": "movimientos por codigo", "creditos": 0, "hecha": False},
    "volador_alado": {
        "nombre": "Volador con alas", "ejemplo": "Dragon Negro de Ojos Rojos, Bebe Dragon",
        "cuerpo": "dragones, aves, murcielagos e insectos voladores", "esqueleto": "sin esqueleto (rigido)",
        "reposo": "flota con vaiven suave, de frente", "ataque": "se eleva y lanza aliento o rayo por la boca, o embiste en picada",
        "herramientas": "movimientos por codigo (como Ojos Rojos)", "creditos": 0, "hecha": True},
    "cuadrupedo": {
        "nombre": "Cuadrupedo o bestia de tierra", "ejemplo": "Colmillo Plateado, dinosaurios",
        "cuerpo": "bestias de cuatro patas, dinosaurios, tortugas", "esqueleto": "sin esqueleto (rigido)",
        "reposo": "respira y mira al monitor", "ataque": "se agazapa, salta y muerde/embiste",
        "herramientas": "movimientos por codigo", "creditos": 0, "hecha": False},
    "serpentino": {
        "nombre": "Serpiente, gusano o anguila", "ejemplo": "Serpiente Siniestra",
        "cuerpo": "cuerpo largo sin patas (serpientes marinas, gusanos, larvas)",
        "esqueleto": "sin esqueleto; ondulacion por shader de vertices",
        "reposo": "se mece como una cobra", "ataque": "se echa atras y lanza la cabeza al rival",
        "herramientas": "movimientos por codigo", "creditos": 0, "hecha": False},
    "criatura_pequena": {
        "nombre": "Criatura pequena", "ejemplo": "Kuriboh",
        "cuerpo": "bolitas, mascotas y criaturas chicas de cuerpo redondo", "esqueleto": "sin esqueleto (rigido)",
        "reposo": "de frente, rebota, parpadea", "ataque": "salta y choca contra el rival",
        "herramientas": "medir_ojos.py para el parpadeo", "creditos": 0, "hecha": True},
    "bicho_rastrero": {
        "nombre": "Bicho de tierra", "ejemplo": "Escarabajo Hercules",
        "cuerpo": "insectos, aranas y crustaceos que caminan", "esqueleto": "sin esqueleto (rigido)",
        "reposo": "vibra y mueve un poco", "ataque": "corre rapido al rival y pica/pellizca",
        "herramientas": "movimientos por codigo", "creditos": 0, "hecha": False},
    "acuatico": {
        "nombre": "Acuatico flotante", "ejemplo": "Gran Tiburon Blanco, Medusa",
        "cuerpo": "peces, pulpos y medusas", "esqueleto": "sin esqueleto (rigido)",
        "reposo": "flota y nada en el sitio", "ataque": "se lanza en embestida y vuelve",
        "herramientas": "movimientos por codigo", "creditos": 0, "hecha": False},
    "maquina": {
        "nombre": "Maquina", "ejemplo": "Tanque Oni T-34",
        "cuerpo": "tanques, robots no humanoides, canones y naves", "esqueleto": "sin esqueleto (rigido)",
        "reposo": "zumbido: vibracion leve y luces", "ataque": "retroceso y disparo de canon o laser",
        "herramientas": "movimientos por codigo", "creditos": 0, "hecha": False},
    "espiritu": {
        "nombre": "Espiritu flotante", "ejemplo": "Mascara de la Oscuridad, Alma Hinotama",
        "cuerpo": "fantasmas, llamas, nubes, cabezas o mascaras que flotan", "esqueleto": "sin esqueleto (rigido)",
        "reposo": "flota, late y brilla", "ataque": "se lanza atravesando al rival o suelta energia",
        "herramientas": "movimientos por codigo", "creditos": 0, "hecha": False},
    "objeto": {
        "nombre": "Objeto o estructura", "ejemplo": "Jarra de Transformacion, Muro del Laberinto",
        "cuerpo": "jarras, cofres, muros, rocas, plantas fijas, estatuas, huevos",
        "esqueleto": "sin esqueleto (rigido)", "reposo": "quieto con un brillo o temblor",
        "ataque": "tiembla y lanza energia, o se abre y muerde", "herramientas": "movimientos por codigo",
        "creditos": 0, "hecha": False},
}

# codigo corto -> plantilla
P = {"LB": "lanzador_baculo", "GE": "guerrero_espada", "GA": "guerrero_arma_larga", "AR": "tirador",
     "LM": "lanzador_manos", "LC": "luchador", "JI": "jinete", "VA": "volador_alado", "CU": "cuadrupedo",
     "SE": "serpentino", "CP": "criatura_pequena", "BI": "bicho_rastrero", "AF": "acuatico", "MA": "maquina",
     "EF": "espiritu", "OB": "objeto"}

# nombre de la carta -> codigo; con "?" al final = revisar con su figura antes de producirlo
CLASE = """
Ameba=CP Aqua Spirit=LM Armored Starfish=CP Beastking of the Swamps=LC Boneheimer=AF Catapult Turtle=CU
Crab Turtle=CU Fire Kraken=AF Flying Penguin=VA Frog The Jam=CP Giant Red Seasnake=SE
Giant Turtle Who Feeds on Flames=CU High Tide Gyojin=LC Humanoid Slime=LC Humanoid Worm Drake=LC Hyosube=LC
Island Turtle=CU Jellyfish=AF Liquid Beast=CU? Maryokutai=EF? Octoberser=AF? Ooguchi=AF Penguin Knight=GE?
Penguin Soldier=CP? Psychic Kappa=LM Red Archery Girl=AR Revival Jam=CP Roaring Ocean Snake=SE Star Boy=CP
Suijin=LM The Furious Sea King=GA Toon Mermaid=AR? Turtle Bird=VA Turtle Tiger=CU Turu-Purun=CP
Twin Long Rods #2=SE Water Magician=LM Water Omotics=LM Weather Report=CP? Yado Karu=BI
Ancient One of the Deep Forest=CU Bazoo the Soul-Eater=LC Bubonic Vermin=CU Dark Gray=CU Dark Zebra=CU
Flower Wolf=CU Frenzied Panda=LC? Fusionist=CP Gazelle the King of Mythical Beasts=CU Giant Rat=CU Hane-Hane=CP
Larvas=CP? Leogun=CU Little Chimera=CU Milus Radiant=CP Mystic Horseman=JI Mystical Sheep #1=CU
Mystical Sheep #2=CU Nimble Momonga=CP Pale Beast=LC Prevent Rat=CU Silver Fang=CU
The All-Seeing White Tiger=CU The Wicked Worm Beast=SE
Battle Ox=GA Battle Steer=GA Beaver Warrior=GE Boar Soldier=GA Garnecia Elefantis=GA Garoozis=GA
Hitotsu-Me Giant=LC Lady Panther=GA Mother Grizzly=LC Rabid Horseman=JI Tiger Axe=GA
Crawling Dragon #2=CU Gilasaurus=CU Mad Sword Beast=CU Mammoth Graveyard=CU Two-Headed King Rex=CU
Two-Mouth Darkruler=CU Uraby=CU
B. Skull Dragon=VA Baby Dragon=VA Blackland Fire Dragon=VA Blue-Eyes Toon Dragon=VA Blue-Eyes White Dragon=VA
Crawling Dragon=CU Curse of Dragon=VA Darkfire Dragon=VA Gaia the Dragon Champion=JI Harpie's Pet Dragon=VA
Hyozanryu=VA Lesser Dragon=VA Manga Ryu-Ran=VA Mikazukinoyaiba=VA One-Eyed Shield Dragon=VA Parrot Dragon=VA
Petit Dragon=CP Red-Eyes B. Dragon=VA Ryu-Ran=VA Seiyaryu=VA Serpent Night Dragon=SE Sky Dragon=VA
Thousand Dragon=VA Tri-Horned Dragon=VA Tyhone #2=VA Winged Dragon, Guardian of the Fortress #1=VA Yamadron=SE
Banisher of the Light=LB Bio-Mage=LM Dancing Elf=LM Dancing Fairy=LM Dark Witch=GA
Doma The Angel of Silence=LM Fairy Guardian=LM Goddess of Whim=LM Goddess with the Third Eye=LM Hoshiningen=CP
Hysteric Fairy=LM Kotodama=EF Ocubeam=EF Petit Angel=CP Ray & Temperature=CP Senju of the Thousand Hands=LM
Shining Abyss=LM Shining Angel=LM Shining Friendship=CP Soul of Purity and Light=LM Spirit of the Breeze=LM
Spirit of the Harp=LM St. Joan=GE The Forgiving Maiden=LM Wingweaver=LM
Ancient Brain=LC? Baron of the Fiend Sword=GE Bickuribox=OB Big Eye=EF Bite Shoes=CP Castle of Dark Illusions=OB
Claw Reacher=LC Crass Clown=LC Dark King of the Abyss=LC Dark Necrofear=LC Dokuroyaiba=EF Dragon Seeker=LC
Earthbound Spirit=EF Feral Imp=LC Flash Assailant=LC? Giant Germ=EF Grand Tiki Elder=LM Headless Knight=GE
Hiro's Shadow Scout=CP King Fog=EF King of Yamimakai=LM Kiseitai=SE Kuriboh=CP
La Jinn the Mystical Genie of the Lamp=LM Man-Eating Treasure Chest=OB Marie the Fallen One=LM
Mask of Darkness=EF Meda Bat=VA Melchid the Four-Face Beast=LC Morinphen=LC Mystic Clown=LC Nuvia the Wicked=LC
Reaper of the Cards=GA Ryu-Kishin Powered=LC Sangan=CP Souls of the Forgotten=EF Spear Cretin=GA
Summoned Skull=LC Tainted Wisdom=EF Terra the Terrible=LC The Bistro Butcher=GE The Earl of Demise=GE
The Gross Ghost of Fled Dreams=EF The Masked Beast=LC The Portrait's Secret=OB Three-Headed Geedo=LC
Toon Summoned Skull=LC Trial of Nightmare=LC? Ushi Oni=LC Versago the Destroyer=LC Wall of Illusion=OB
Whiptail Crow=VA Witty Phantom=LC Zoa=LC
7 Colored Fish=AF Amphibian Beast=LC Bottom Dweller=LC Cure Mermaid=LM Deepsea Shark=AF Enchanting Mermaid=LM
Flying Fish=AF Great White=AF Misairuzame=AF Root Water=LC Tongyo=AF Wow Warrior=LC
4-Starred Ladybug of Doom=BI Basic Insect=BI Bladefly=VA Bombardment Beetle=BI Cockroach Knight=GE
Cocoon of Evolution=OB Drill Bug=BI Empress Mantis=VA Flying Kamakiri #1=VA Flying Kamakiri #2=VA Giant Flea=BI
Girochin Kuwagata=BI Great Moth=VA Hercules Beetle=BI Hunter Spider=BI Insect Soldiers of the Sky=VA
Jirai Gumo=BI Killer Needle=VA Kumootoko=BI Kuwagata Alpha=BI Kwagar Hercules=BI Larvae Moth=SE Leghul=SE
Man-Eater Bug=BI Minar=BI? Needle Worm=SE Parasite Paracide=BI Petit Moth=SE
Barrel Dragon=MA Blast Juggler=MA Cannon Soldier=MA Cyber Falcon=MA Cyber Saurus=MA
Cyber Soldier of Darkworld=MA Dharma Cannon=MA Disk Magician=MA Gadget Soldier=MA Giga-Tech Wolf=MA Gradius=MA
Ground Attacker Bugroth=MA Guardian of the Throne Room=MA Jinzo=LM Jinzo #7=LM Labyrinth Tank=MA
Launcher Spider=MA Mechanical Snail=MA Mechanicalchaser=MA Megasonic Eye=MA Metal Dragon=MA Metal Fish=MA
Metalzoa=MA Oni Tank T-34=MA Overdrive=MA Patrol Robo=MA Red-Eyes Black Metal Dragon=VA Slot Machine=MA
Spikebot=MA Steel Ogre Grotto #1=LC Steel Ogre Grotto #2=LC Steel Scorpion=MA UFO Turtle=MA
Bean Soldier=GE Darkworld Thorns=OB Dreamsprite=LM Firegrass=OB Green Phantom King=LB? Griggle=CP Man Eater=OB
Mystic Tomato=CP Queen of Autumn Leaves=LM Rainbow Flower=OB Trent=OB
Charubin the Fire Knight=GA Darkfire Soldier #1=GE Darkfire Soldier #2=GE Dragon Piper=LM Fire Princess=LM
Fireyarou=EF Flame Cerebrus=CU Flame Champion=LC Flame Dancer=LM Hinotama Soul=EF Jigen Bakudan=OB
Lady Assailant of Flames=LM Mr. Volcano=LC Spirit of Flames=LC? Twin-Headed Fire Dragon=VA
Ancient Lizard Warrior=LC Armored Lizard=CU Drooling Lizard=CU Sinister Serpent=SE Worm Drake=SE
Alpha The Magnet Warrior=GE Beta The Magnet Warrior=LC Gamma The Magnet Warrior=LC Cyber Jar=OB
Destroyer Golem=LC Dissolverock=OB Giant Soldier of Stone=LC Labyrinth Wall=OB Morphing Jar=OB
Morphing Jar #2=OB Muka Muka=CP Rock Ogre Grotto #1=LC Sand Stone=OB? Spherous Lady=OB? Stone Ogre Grotto=LC
The Rock Spirit=GE The Statue of Easter Island=OB Valkyrion the Magna Warrior=GE
Spike Seadra=SE Takriminos=SE
Ancient Elf=LB Aqua Madoor=LM Ceremonial Bell=OB? Cosmo Queen=LB Dark Elf=LM Dark Magician=LB
Dark Magician Girl=LB Exodia the Forbidden One=LC Fairy's Gift=LM Fire Sorcerer=LM Flame Manipulator=LM
Gemini Elf=LM Illusionist Faceless Mage=LM Invitation to a Dark Sleep=LM? Jowgen the Spiritualist=LM Kazejin=EF
Kycoo the Ghost Destroyer=LM Lady of Faith=LB Left Arm of the Forbidden One=OB Left Leg of the Forbidden One=OB
Lord of D.=LM Magician of Faith=LB Maha Vailo=LM Maiden of the Moonlight=LM Masked Sorcerer=LM
Musician King=LM Mystic Lamp=CP Mystical Elf=LM Nemuriko=LM Neo the Magic Swordsman=GE Relinquished=LC
Right Arm of the Forbidden One=OB Right Leg of the Forbidden One=OB Saggi the Dark Clown=LM Skull Knight=GE
Sorcerer of the Doomed=LB Summoner of Illusions=LM The Stern Mystic=LM The Unhappy Maiden=LM
Thousand-Eyes Idol=OB Thousand-Eyes Restrict=EF Time Wizard=LB White Magical Hat=LM
Witch of the Black Forest=LM Witch's Apprentice=LB
Electric Lizard=CU Electric Snake=SE Kaminari Attack=EF Lightning Conger=SE Mega Thunderball=EF
Oscillo Hero #2=LC Sanga of the Thunder=LC The Immortal of Thunder=LC Thunder Dragon=VA Tripwire Beast=CU
Twin-Headed Thunder Dragon=VA
Amazon Archer=AR Ansatsu=GE Armaill=GE Armed Ninja=GE Axe Raider=GA Beautiful Headhuntress=GA Buster Blader=GE
Celtic Guardian=GE Crimson Sentry=GA Deepsea Warrior=GE Dragoness the Wicked Knight=GE Dream Clown=LC
Empress Judge=LB Flame Swordsman=GE Gaia The Fierce Knight=JI Gate Guardian=LC Gearfried the Iron Knight=GE
Giltia the D. Knight=GA Goblin Attack Force=GA? Guardian of the Labyrinth=GA Hard Armor=LC Hayabusa Knight=GE
Hibikime=LM Hungry Burger=CP Invader of the Throne=GE Judge Man=GA Kagemusha of the Blue Flame=GE
Karate Man=LC Karbonala Warrior=LC Kojikocy=GE Lava Battleguard=GA M-Warrior #1=GE M-Warrior #2=GE
Masaki the Legendary Swordsman=GE Millennium Shield=OB Monster Egg=CP Mushroom Man #2=CP
Mysterious Puppeteer=LM Oscillo Hero=LC Performance of Sword=GE? Princess of Tsurugi=GE
Protector of the Throne=GE? Queen's Double=GE Science Soldier=AR Skull Guardian=GE Skull Mariner=GE?
Sonic Maid=GA? Stuffed Animal=CP Succubus Knight=GE Supply=CP Swamp Battleguard=GA Sword Hunter=GE
Swordsman of Landstar=GE Swordstalker=GE The Fiend Megacyber=LC The Judgement Hand=LC
The Last Warrior from Another Planet=LC The Legendary Fisherman=GA The Little Swordsman of Aile=GE
The Unfriendly Amazon=LC Trap Master=LC Wall Shadow=LC Warrior of Tradition=GE
Wodan the Resident of the Forest=GA Zombyra the Dark=LC
Blue-Winged Crown=VA Dark Bat=VA Faith Bird=VA Fiend Reflection #2=VA Garuda the Wind Spirit=VA Harpie Lady=LC
Harpie Lady Sisters=LC Harpie's Brother=LC Kurama=VA Niwatori=VA Peacock=VA Punished Eagle=VA Queen Bird=VA
Skull Red Bird=VA Sonic Bird=VA Spirit of the Books=VA Takuhee=VA Tornado Bird=VA Tyhone=VA
Winged Dragon, Guardian of the Fortress #2=VA
Armored Zombie=GE Corroding Shark=AF Dokurorider=JI Dragon Zombie=VA Flame Ghost=EF Magical Ghost=LM
Pumpking the King of Ghosts=EF Red-Moon Baby=CP Shadow Ghoul=LC Skull Servant=LC The 13th Grave=LC
Three-Legged Zombies=LC Yaranzo=OB
Alligator's Sword=GE Alligator's Sword Dragon=VA Ancient Lamp=OB Battle Warrior=LC Beast of Gilfer=LC Berfomet=LC
Big Shield Gardna=LC? Blast Sphere=OB Blue-Eyes Ultimate Dragon=VA Chimera the Flying Mythical Beast=VA
Copycat=LM Cyber-Stein=MA Cyber-Tech Alligator=MA Dark-Eyes Illusionist=LM Dimensional Warrior=LC
Dunames Dark Witch=GA Electromagnetic Bagworm=SE Greenkappa=LC? Insect Queen=BI Kinetic Soldier=LC?
Machine King=LC Magician of Black Chaos=LB Panther Warrior=GE Perfectly Ultimate Great Moth=VA Rigras Leever=CP?
Rocket Warrior=MA Skelengel=CP Slate Warrior=LC Total Defense Shogun=GE? Vorse Raider=GA
"""


def slug(s):
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


def main():
    clase = {}
    for m in re.finditer(r"(.+?)=([A-Z]{2})(\?)?(?=\s|$)", " ".join(CLASE.split("\n")).strip()):
        clase[m.group(1).strip()] = (P[m.group(2)], bool(m.group(3)))
    card = os.path.join(BASE, "datadat-extraido", "card")
    con_arte, nombre = set(), None
    for l in open(os.path.join(card, "list_card.txt"), encoding="latin-1").read().splitlines():
        l = l.strip()
        if l.startswith("//") and not re.match(r"//\s*\d{4}:", l) and "Generated" not in l:
            nombre = l[2:].strip()
        elif l.lower().endswith(".bmp") and nombre:
            if not l.lower().startswith("token_"):  # token_*.bmp = relleno; zzz*.bmp si son arte
                con_arte.add(nombre.lower())
            nombre = None
    # cartas que el jugador puede usar (las 771 "con edicion": CARD_Pack & 7 != 0, un uint16 por idx)
    pack = open(os.path.join(BASE, "datadat-extraido", "bin#", "card_pack.bin"), "rb").read()
    usable = lambda r: int.from_bytes(pack[2 * int(r["idx"]):2 * int(r["idx"]) + 2], "little") & 7
    filas = [r for r in csv.DictReader(open(os.path.join(BASE, "re-output", "cards.csv"), encoding="utf-8"))
             if r["idx"].isdigit()]
    cartas, faltan = {}, []
    for r in filas:
        if r["tipo"] in ("Magic", "Trap") or not usable(r) or slug(r["nombre"]) in cartas:
            continue
        if r["nombre"] not in clase:
            faltan.append(r["nombre"])
            continue
        p, rev = clase[r["nombre"]]
        cartas[slug(r["nombre"])] = {"nombre": r["nombre"], "tipo": r["tipo"], "nivel": int(r["nivel"] or 0),
                                     "plantilla": p, **({"revisar": True} if rev else {}),
                                     **({} if r["nombre"].lower() in con_arte else {"sin_arte": True})}
    hechos = os.listdir(os.path.join(BASE, "nano-banana", "modelos3d"))
    for k, c in cartas.items():
        if k in hechos or k in ("dark_magician", "dark_magician_girl", "celtic_guardian", "kuriboh", "baby_dragon"):
            c["modelo_hecho"] = True
    cuenta = collections.Counter(c["plantilla"] for c in cartas.values())
    for p in PLANTILLAS:
        PLANTILLAS[p]["monstruos"] = cuenta.get(p, 0)
    salida = os.path.join(BASE, "remake", "diseno", "plantillas.json")
    json.dump({"_nota": "Plantillas de monstruos (arquetipos) y la de cada carta. 'revisar' = confirmar con su "
               "figura.png antes de producirlo. Magias y trampas: cartas planas con efectos (sin 3D). "
               "Generado por herramientas/clasificar_plantillas.py",
               "plantillas": PLANTILLAS, "cartas": cartas}, open(salida, "w", encoding="utf-8"),
              indent=1, ensure_ascii=False)
    print("monstruos:", len(cartas), "| a revisar:", sum(1 for c in cartas.values() if c.get("revisar")),
          "| sin clasificar:", faltan)
    for p, n in cuenta.most_common():
        print("  %-22s %3d  %s" % (p, n, "Meshy %d cr" % PLANTILLAS[p]["creditos"] if PLANTILLAS[p]["creditos"] else "0 cr"))
    print("creditos Meshy para los que se mueven:", sum(PLANTILLAS[c["plantilla"]]["creditos"] for c in cartas.values()))


main()
