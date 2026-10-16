# Desbloquea todas las cartas en la partida (system.dat): 3 copias de cada carta real + marca de "vista".
# No toca que cartas tienes puestas en tu mazo. Hace respaldo con fecha antes de escribir.
# Uso: python -I desbloquear_cartas.py [--copias N] [--incluir-dioses] [--prueba RUTA_SALIDA]
import csv, logging, os, shutil, struct, subprocess, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import partida_poc as pp

BASE = r"D:\Yugi-Reload"
SAVE = os.path.join(BASE, "juego-extraido", "Yu-Gi-Oh! Power of Chaos Common", "system.dat")
RESPALDOS = os.path.join(BASE, "respaldo-partida")
CARTAS = os.path.join(BASE, "re-output", "cards.csv")

log = logging.getLogger("yugi.desbloqueo")

def juego_abierto():
    out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq Joey_Pc.exe", "/NH"], capture_output=True, text=True).stdout
    return "Joey_Pc.exe" in out

def desbloquear(arch, copias=3, incluir_dioses=False):
    """Devuelve (archivo_nuevo, resumen). Lanza ValueError si el save no es valido."""
    plano = pp.decodificar(arch)
    prefijo, cuerpo = plano[:8], bytearray(plano[8:8 + pp.TAM_PLANO])
    if not pp.suma_ok(bytes(cuerpo)):
        raise ValueError("system.dat no supera la suma de control: no se modifica")
    validos = {}
    for r in csv.DictReader(open(CARTAS, encoding="utf-8")):
        if not incluir_dioses and r["tipo"] in ("Divino", "Especial"):
            continue
        validos[int(r["idx"])] = r["nombre"]
    col = pp.coleccion(bytes(cuerpo))
    antes = (sum(1 for v in col if v & 0xFF), sum(v & 0xFF for v in col))
    for idx in range(pp.N_CARTAS):
        if idx not in validos:
            continue
        v = col[idx]
        poseidas = max(v & 0xFF, copias)
        v = (v & 0xFF00) | poseidas | 0x4000  # conserva bits de mazo (8-13), marca vista
        struct.pack_into("<H", cuerpo, pp.COLECCION + idx * 2, v)
    # 0xA54DB4 es la opcion del menu "todo el set / solo Joey": es del jugador y NO se toca (el lanzador hace
    # que la CPU use la tabla inyectada en ambos modos). Se marca la partida como inicializada (0xA54DB1=1)
    # para que el juego no recalcule esa opcion por su cuenta al cargar (FUN_005bee30).
    o = 0xA54DAE - 0xA53CC0  # dae, ganador, racha, inicializado, db2, nivel, FUL
    if cuerpo[o + 3] == 0:
        cuerpo[o + 4] = cuerpo[o + 5] = 1  # lo que haria el propio juego en la primera carga (nivel 1)
    cuerpo[o + 3] = 1
    cuerpo = bytearray(pp.recalcular_suma(bytes(cuerpo)))
    nuevo = pp.codificar(prefijo + bytes(cuerpo) + plano[8 + pp.TAM_PLANO:], len(arch))
    nuevo[:4] = pp.cabecera(nuevo, pp.TAM_PLANO)
    # verificacion de ida y vuelta antes de devolver nada
    eco = pp.decodificar(bytes(nuevo))
    if eco[:8] != prefijo or not pp.suma_ok(eco[8:8 + pp.TAM_PLANO]) or eco[8:8 + pp.TAM_PLANO] != bytes(cuerpo):
        raise ValueError("la verificacion de ida y vuelta fallo: no se escribe")
    col2 = pp.coleccion(eco[8:])
    despues = (sum(1 for v in col2 if v & 0xFF), sum(v & 0xFF for v in col2))
    mazo_igual = all((a & 0x3F00) == (b & 0x3F00) for a, b in zip(col, col2))
    return bytes(nuevo), {"antes": antes, "despues": despues, "cartas_validas": len(validos), "mazo_intacto": mazo_igual}

def main(argv):
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    copias = int(argv[argv.index("--copias") + 1]) if "--copias" in argv else 3
    dioses = "--incluir-dioses" in argv
    salida = argv[argv.index("--prueba") + 1] if "--prueba" in argv else SAVE
    if salida == SAVE and juego_abierto():
        print("Cierra el juego antes de desbloquear (si esta abierto, al guardar recargaria la partida vieja).")
        return 2
    arch = open(SAVE, "rb").read()
    nuevo, r = desbloquear(arch, copias, dioses)
    if salida == SAVE:
        os.makedirs(RESPALDOS, exist_ok=True)
        bk = os.path.join(RESPALDOS, "system_antes_desbloqueo_%s.dat" % time.strftime("%Y%m%d_%H%M%S"))
        shutil.copy2(SAVE, bk)
        print("respaldo:", bk)
    tmp = salida + ".tmp"
    open(tmp, "wb").write(nuevo)
    os.replace(tmp, salida)  # reemplazo atomico: nunca queda un system.dat a medio escribir
    print("cartas poseidas: %d -> %d | copias: %d -> %d | mazo actual intacto: %s" %
          (r["antes"][0], r["despues"][0], r["antes"][1], r["despues"][1], "si" if r["mazo_intacto"] else "NO"))
    print("escrito:", salida)
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
