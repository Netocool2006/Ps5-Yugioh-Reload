# Mide el efecto de los diales de IA usando la demo del titulo (CPU contra CPU, sin tocar nada).
# Por cada configuracion: juego limpio, diales aplicados, muestreo de memoria cada 0.1 s durante N minutos.
# Metricas: invocaciones (zona de monstruo 0 -> carta), monstruos que dejan el campo, eventos y total de dano,
# duelos completados. Uso: python -I medir_personalidades.py [minutos_por_bloque] [rondas]
import json, logging, os, shutil, statistics, struct, subprocess, sys, time
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, r"D:\Yugi-Reload\launcher"); sys.path.insert(0, AQUI)
import yugi_reload as yr

MIN = float(sys.argv[1]) if len(sys.argv) > 1 else 4.0
RONDAS = int(sys.argv[2]) if len(sys.argv) > 2 else 2
CONFIGS = {"agresivo": yr.DIALES["agresivo"], "original": (None, None), "tortuga": yr.DIALES["tortuga"]}
SAVE = os.path.join(r"D:\Yugi-Reload\juego-extraido", "Yu-Gi-Oh! Power of Chaos Common", "system.dat")
SELLO = time.strftime("%Y%m%d_%H%M%S")
lg = logging.getLogger("yugi"); lg.setLevel(logging.DEBUG); lg.handlers.clear()
fh = logging.FileHandler(os.path.join(AQUI, "logs", "personalidades_%s.log" % SELLO), encoding="utf-8")
fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)-7s] %(funcName)s | %(message)s")); lg.addHandler(fh)

def leer_estado(m):
    lp = yr.leer_lp(m)
    zonas = []
    for lado in (0, 1):
        z = []
        for k in range(5):
            raw = m.leer(0xA55D74 + lado * 0xD44 + k * 0x90, 4)
            z.append((struct.unpack("<I", raw)[0] & 0xFFF) if raw else 0)
        zonas.append(z)
    return lp, zonas

def bloque(nombre, diales, minutos):
    subprocess.run(["taskkill", "/F", "/IM", "Joey_Pc.exe"], capture_output=True); time.sleep(1)
    p = subprocess.Popen([yr.EXE, "-win", "-speedy", "-nosound"], cwd=yr.APP)
    time.sleep(4)
    m = yr.Memoria(p.pid)
    ok = yr.aplicar_diales(m, *diales)
    lg.info("bloque %s diales=%s aplicados=%s", nombre, diales, ok)
    met = {"invocaciones": 0, "salen_del_campo": 0, "golpes": 0, "dano": 0, "duelos": 0, "muestras": 0, "secuencia": []}
    previo = None; en_duelo = False; fin = time.time() + minutos * 60
    while time.time() < fin and p.poll() is None:
        lp, zonas = leer_estado(m)
        met["muestras"] += 1
        if previo:
            plp, pz = previo
            if lp == [8000, 8000] and plp != [8000, 8000]:
                met["duelos"] += 1 if en_duelo else 0; en_duelo = True
            for lado in (0, 1):
                for k in range(5):
                    if pz[lado][k] == 0 and zonas[lado][k]: met["invocaciones"] += 1; met["secuencia"].append(("inv", zonas[lado][k]))
                    if pz[lado][k] and zonas[lado][k] == 0: met["salen_del_campo"] += 1
                d = plp[lado] - lp[lado]
                if 0 < d <= 8000 and lp[lado] <= 8000:
                    met["golpes"] += 1; met["dano"] += d; met["secuencia"].append(("dano", d))
            if any(x == 0 for x in lp) and en_duelo:
                met["duelos"] += 1; en_duelo = False
        previo = (lp, zonas)
        time.sleep(0.1)
    vivo = p.poll() is None
    m.cerrar(); p.kill(); p.wait(10)
    met["vivo_al_final"] = vivo
    met["firma_secuencia"] = hash(tuple(met["secuencia"][:60]))
    del met["secuencia"]
    lg.info("resultado %s: %s", nombre, met)
    return met

def main():
    bk = os.path.join(r"D:\Yugi-Reload\respaldo-partida", "personalidades_" + SELLO); os.makedirs(bk, exist_ok=True)
    shutil.copy2(SAVE, bk)
    res = {k: [] for k in CONFIGS}
    try:
        for r in range(RONDAS):
            for nombre, diales in CONFIGS.items():
                met = bloque(nombre, diales, MIN)
                res[nombre].append(met)
                print("ronda %d %-9s %s" % (r + 1, nombre, {k: v for k, v in met.items() if k != "muestras"}), flush=True)
    finally:
        subprocess.run(["taskkill", "/F", "/IM", "Joey_Pc.exe"], capture_output=True)
        igual = open(SAVE, "rb").read() == open(os.path.join(bk, "system.dat"), "rb").read()
        if not igual: shutil.copy2(os.path.join(bk, "system.dat"), SAVE)
        print("partida sin cambios durante la medicion:", igual, "(restaurada)" if not igual else "")
    print("\nPROMEDIO POR MINUTO (%s min x %d rondas por configuracion)" % (MIN, RONDAS))
    for nombre, lst in res.items():
        tot = lambda k: sum(x[k] for x in lst)
        mins = MIN * len(lst)
        print("%-9s invocaciones %5.2f | salen del campo %5.2f | golpes %5.2f | dano %7.0f | duelos completos %d" % (
            nombre, tot("invocaciones") / mins, tot("salen_del_campo") / mins, tot("golpes") / mins, tot("dano") / mins, tot("duelos")))
    json.dump(res, open(os.path.join(AQUI, "logs", "personalidades_%s.json" % SELLO), "w"), indent=1)

if __name__ == "__main__":
    main()
