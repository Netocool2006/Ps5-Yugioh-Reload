# Prueba en duelo real de las cartas Divino/Especial (dioses promocionales 0/0, nivel 0).
# Lado CPU: mazo de prueba inyectado como cpu_645 SOLO en el Data.dat de la sesion (se regenera al lanzar).
# Lado jugador: Deck.ydc temporal con los dioses. Partida y mazo se respaldan y restauran al final.
import csv, hashlib, json, logging, os, random, shutil, struct, subprocess, sys, threading, time
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, r"D:\Yugi-Reload\launcher"); sys.path.insert(0, AQUI)
import yugi_reload as yr, control, flujo, mazo_cpu

BASE = r"D:\Yugi-Reload"
SAVE = os.path.join(BASE, "juego-extraido", "Yu-Gi-Oh! Power of Chaos Common", "system.dat")
DECK = os.path.join(yr.APP, "Deck.ydc")
SELLO = time.strftime("%Y%m%d_%H%M%S")
lg = logging.getLogger("yugi"); lg.setLevel(logging.DEBUG); lg.handlers.clear()
fh = logging.FileHandler(os.path.join(AQUI, "logs", "dioses_%s.log" % SELLO), encoding="utf-8")
fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)-7s] %(name)s %(funcName)s | %(message)s")); lg.addHandler(fh)
DIOSES = [1910, 1911, 1912, 1903]  # Obelisk, Slifer, Ra, Glory of the King's Hand (ids externos)
car = {int(r["id"]): r for r in csv.DictReader(open(os.path.join(BASE, "re-output", "cards.csv"), encoding="utf-8"))}
res = {}

def out(k, v):
    res[k] = v; print("%-48s %s" % (k, v), flush=True); lg.info("%s = %s", k, v)

def ydc(main, fus=(), side=()):
    return (b"\x01\xcc\xcc\xcc" + struct.pack("<f", 1.0) + struct.pack("<H", len(main)) + struct.pack("<%dH" % len(main), *main)
            + struct.pack("<H", len(fus)) + (struct.pack("<%dH" % len(fus), *fus) if fus else b"")
            + struct.pack("<H", len(side)))

def mazo_prueba():
    base = mazo_cpu.leer_ydc(os.path.join(BASE, "datadat-extraido", "j", "file", "cpu_000.ydc"))[0]
    relleno = [x for x in base if car[x]["tipo"] not in ("Magic", "Trap")][:20] + [x for x in base if car[x]["tipo"] in ("Magic", "Trap")][:8]
    return [d for d in DIOSES for _ in range(3)] + relleno  # 12 + 28 = 40

def inyectar_cpu_645(data):
    with open(yr.DESTINO, "r+b") as f:
        f.read(8); n = struct.unpack("<I", f.read(4))[0]
        for i in range(n):
            f.seek(12 + i * 268); nom = yr.swap(f.read(256)).split(b"\0")[0].decode("latin-1")
            if nom.lower() == "j\\file\\cpu_645.ydc":
                f.seek(0, 2); off = f.tell(); f.write(data)
                f.seek(12 + i * 268 + 256); f.write(struct.pack("<III", off, len(data), len(data)))
                return True
    return False

def zonas_campo(j, lado):
    vals = []
    for z in range(11):
        raw = j.mem.leer(0xA55D74 + lado * 0xD44 + z * 0x90, 4)
        v = struct.unpack("<I", raw)[0] & 0xFFF if raw else 0
        vals.append(v)
    return vals  # idx internos: 0-4 monstruos, 5-10 magia/trampa

IDX_DIOS = {int(r["idx"]) for r in car.values() if int(r["id"]) in DIOSES}

def duelo(j, vig, etiqueta, turnos=3):
    ok, pasos = flujo.iniciar_duelo(j)
    out("%s: duelo iniciado" % etiqueta, ok)
    if not ok: return
    for lado, quien in ((flujo.LADO_CPU, "CPU"), (flujo.LADO_JUG, "jugador")):
        z = mazo_cpu.zonas(j.mem, lado, mazo_cpu.cargar_cartas())
        out("%s: dioses en mano %s" % (etiqueta, quien), sum(1 for x in z["mano"] if x in DIOSES))
    vistos_campo = set()
    for t in range(turnos):
        control.clic(j.hwnd, 234, 490); time.sleep(3)
        for _ in range(3):
            if j.contadores(flujo.LADO_JUG)["mano"] > 6:
                control.clic(j.hwnd, 315, 565); time.sleep(2.5)
        time.sleep(10)
        control.captura(j.hwnd, "dioses_%s_t%d" % (etiqueta, t))
        for lado in (0, 1):
            vistos_campo |= {(lado, x) for x in zonas_campo(j, lado) if x in IDX_DIOS}
        if not j.vivo(): break
    out("%s: juego vivo tras %d turnos" % (etiqueta, turnos), j.vivo())
    out("%s: dioses que llegaron al campo (lado, idx)" % etiqueta, sorted(vistos_campo))
    out("%s: LP [CPU, jugador]" % etiqueta, j.lp())
    antes = os.path.getsize(SAVE)
    j.poner_lp(flujo.LP_CPU, 0)
    for k in range(12):  # seguir la secuencia de fin de duelo capturando cada pantalla y el tamano del save
        time.sleep(1.5)
        ruta, img = control.captura(j.hwnd, "dioses_%s_fin%02d" % (etiqueta, k))
        nombre = flujo.clasificar(img)[0] if img is not None else None
        out("%s: fin %02d pantalla=%s tam system.dat" % (etiqueta, k, nombre), os.path.getsize(SAVE))
        if nombre == "menu_principal": break
        control.clic(j.hwnd, *flujo.RESPUESTAS.get(nombre, flujo.CLIC_NEUTRO))
    out("%s: tam system.dat antes/despues del duelo" % etiqueta, (antes, os.path.getsize(SAVE)))

def dioses_en_mazo(arch):
    """El mazo activo se reconstruye al cargar desde los bits 'en main' (8-9) de la coleccion: se ponen a 3
    en los 4 tipos de carta Divino/Especial y se quitan 12 copias de otras cartas del mazo (40 en total)."""
    import partida_poc as pp
    pl = bytearray(pp.decodificar(arch)); base = 8 + pp.COLECCION
    def get(i): return struct.unpack_from("<H", pl, base + i * 2)[0]
    def put(i, v): struct.pack_into("<H", pl, base + i * 2, v)
    quitar = 12
    for i in range(pp.N_CARTAS):
        if quitar == 0: break
        if i in IDX_DIOS: continue
        v = get(i); m = (v >> 8) & 3
        while m and quitar:
            m -= 1; quitar -= 1
        put(i, (v & ~0x300) | (m << 8))
    for i in IDX_DIOS:
        v = get(i); put(i, (v & ~0x3FF) | 3 | (3 << 8) | 0x4000)  # 3 poseidas, 3 en main, vista
    pl[8:8 + pp.TAM_PLANO] = pp.recalcular_suma(bytes(pl[8:8 + pp.TAM_PLANO]))
    out = pp.codificar(bytes(pl), len(arch)); out[:4] = pp.cabecera(out, pp.TAM_PLANO)
    col = pp.coleccion(pp.decodificar(bytes(out))[8:])
    print("mazo guardado: %d cartas en main, dioses en main: %s" % (sum((v >> 8) & 3 for v in col), [(col[i] >> 8) & 3 for i in sorted(IDX_DIOS)]))
    return bytes(out)

def sesion(etiqueta, nums, forzar_cpu):
    p = subprocess.Popen([yr.EXE, "-win", "-speedy"], cwd=yr.APP)
    try:
        sel = yr.Selector(nums, 0.0, rng=random.Random(5))
        vig = yr.Vigilante(p, sel, {"nivel": 0.0, "resultados": []}, ruta_historial=os.path.join(AQUI, "logs", "h_dioses.json"), refresco=1.0)
        if forzar_cpu:
            vig.forzada = [0, 1, 2, 3, 4] + [645] * 35
        threading.Thread(target=vig.correr, daemon=True).start()
        j = flujo.Juego(p); time.sleep(5)
        duelo(j, vig, etiqueta)
        out("%s: errores del vigilante" % etiqueta, vig.errores)
        # cerrar como un usuario (SALIR): matar el proceso puede cortar system.dat a medio escribir
        flujo.ir_a_menu_principal(j); control.clic(j.hwnd, 400, 540)
        flujo.esperar(lambda: p.poll() is not None, 30, desc="cierre por SALIR")
        vig.detener.set(); j.cerrar()
    finally:
        if p.poll() is None:
            lg.warning("el juego no cerro por SALIR: se termina a la fuerza"); p.terminate(); p.wait(20)

def main():
    bk = os.path.join(BASE, "respaldo-partida", "dioses_" + SELLO); os.makedirs(bk, exist_ok=True)
    shutil.copy2(SAVE, bk); shutil.copy2(DECK, os.path.join(bk, "Deck_original.ydc"))
    subprocess.run(["taskkill", "/F", "/IM", "Joey_Pc.exe"], capture_output=True)
    nums = yr.cargar_numerados(); prueba = mazo_prueba()
    out("mazo de prueba (12 dioses/Glory + 28)", len(prueba))
    try:
        # A) CPU con los dioses, tu mazo normal
        yr.parchear_fuls(nums, 0.0)
        out("A: inyectado como cpu_645 en Data.dat de sesion", inyectar_cpu_645(ydc(prueba)))
        sesion("A_cpu", nums, True)
        if "--solo-a" in sys.argv: return
        # B) tu mazo con los dioses + partida temporal que los posee
        sys.path.insert(0, os.path.join(BASE, "re-scripts")); import desbloquear_cartas as dc
        con_dioses = dc.desbloquear(open(SAVE, "rb").read(), 3, incluir_dioses=True)[0]  # leer ANTES de abrir en "wb"
        con_dioses = dioses_en_mazo(con_dioses)
        open(SAVE, "wb").write(con_dioses)
        open(DECK, "wb").write(ydc(prueba))
        yr.parchear_fuls(nums, 0.0)
        sesion("B_jugador", nums, False)
    finally:
        subprocess.run(["taskkill", "/F", "/IM", "Joey_Pc.exe"], capture_output=True)
        shutil.copy2(os.path.join(bk, "system.dat"), SAVE)
        shutil.copy2(os.path.join(bk, "Deck_original.ydc"), DECK)
        yr.parchear_fuls(yr.cargar_numerados(), 0.0)  # Data.dat de sesion limpio otra vez
        sha = lambda f: hashlib.sha1(open(f, "rb").read()).hexdigest()
        out("partida restaurada", sha(SAVE) == sha(os.path.join(bk, "system.dat")))
        out("Deck.ydc restaurado", sha(DECK) == sha(os.path.join(bk, "Deck_original.ydc")))
        json.dump(res, open(os.path.join(AQUI, "logs", "dioses_%s.json" % SELLO), "w"), indent=1, default=str)

if __name__ == "__main__":
    main()
