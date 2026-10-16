# Yugi Reload v3 - mazo distinto por duelo + personalidad de decision por temperamento.
#
# Como funciona:
#  - Data.dat.full = Data.dat original + los 546 mazos de la biblioteca como cpu_100..cpu_645.
#  - El motor elige mazo con: indice = rng%5 + nivel*5 sobre una tabla de 40 numeros de mazo
#    en VA 0x5db158 (.rdata, sin ASLR). El lanzador reescribe esa tabla en el proceso vivo.
#  - Cada duelo tiene UN temperamento (agresivo, tortuga, ...) que se congela hasta que el duelo
#    termina: define la familia de mazos de la tabla y dos diales de la IA parcheados en memoria:
#      * umbral de ataque (0x5B12C2): dano neto minimo para considerar favorable un ataque.
#      * ATK minimo para invocar en ataque (0x5B154B): original 900.
#  - Los 37 mazos tematicos ful_* se rebarajan por sesion (su tabla usa punteros a strings).
#  - Dificultad elastica (historial.json, se guarda al terminar cada duelo) y sesgo segun Deck.ydc.
#  - Log exhaustivo en launcher\logs\ (DEBUG: cada lectura/escritura de memoria y decision).
# Uso: python -I yugi_reload.py [--solo-parchear] [--puro] [--clasico] [--sin-diales] [--ful-original] [-- args del juego]
#      --ful-original: con la opcion "todo el set" la CPU usa los mazos FUL_ de Konami (sin la tabla inyectada)
#      args del juego (descubiertos en el exe): -win -speedy -fps -nosound -16/-24/-32 -Lspa/-Leng/...
import csv, ctypes, glob, json, logging, os, random, shutil, struct, subprocess, sys, threading, time
from ctypes import wintypes

BASE = r"D:\Yugi-Reload"
APP = os.path.join(BASE, "juego-extraido", "app")
EXE = os.path.join(APP, "Joey_Pc.exe")
ORIGINAL = os.path.join(APP, "Data.dat.original")
FULL = os.path.join(APP, "Data.dat.full")
DESTINO = os.path.join(APP, "Data.dat")
BIBLIOTECA = os.path.join(BASE, "biblioteca")
SLOTS_DIR = os.path.join(BASE, "datadat-extraido", "j", "file")
LAUNCHER = os.path.join(BASE, "launcher")
HISTORIAL = os.path.join(LAUNCHER, "historial.json")
LOG_SEL = os.path.join(LAUNCHER, "ultima_seleccion.txt")
LOG_DIR = os.path.join(LAUNCHER, "logs")
CARDS_CSV = os.path.join(BASE, "re-output", "cards.csv")
NUMEROS_CSV = os.path.join(LAUNCHER, "biblioteca_numeros.csv")

TABLA_CPU = 0x5DB158        # base del motor: indice = rng%5 + nivel*5 (niveles 1-7 -> indices 5..39)
TABLA_INI = TABLA_CPU + 5 * 4  # 0x5DB16C: SOLO se escriben los indices 5..39 (35 u32).
# Los indices 0-4 (0x5DB158-0x5DB16B) nunca los lee el motor de la CPU y NO son de esta tabla: son las
# ultimas entradas de la tabla de punteros FUL (0x5DB0A8, 7x7) del nivel 9 de torneo (3EXO, 3FUS,
# 3GRV, 3HND). Escribirlos rompe el modo torneo en rango maximo.
FUL_COLA = (TABLA_CPU, 20)
REFRESCO = 3.0              # segundos entre ciclos de vigilancia
ADDR_GANADOR = 0xA54DAF     # 1 = gano el jugador el ultimo duelo, 2 = gano la CPU
ADDR_RACHA = 0xA54DB0       # racha del mismo resultado (se pone a 0 cuando el juego cambia de nivel)
ADDR_DIFICULTAD = 0xA54DB3  # nivel 1-7 que el propio juego sube/baja con tus rachas
ADDR_MODO_FUL = 0xA54DB4   # opcion "todo el set" (1) / "solo Joey" (0); con 1 la CPU usa solo mazos ful_* (se respeta)
ADDR_LP = (0xA55D64, 0xA55D64 + 0xD44)  # LP u16 por lado; en duelo real lado 0 = CPU, lado 1 = jugador

# --- diales de la IA (parches de codigo en memoria; el .exe en disco no se toca) ---
DIAL_ATAQUE = 0x5B12C2
ATAQUE_ORIGINAL = bytes.fromhex("6685c066894502 7f1b".replace(" ", ""))   # TEST AX,AX; MOV [EBP+2],AX; JG +1b
def bytes_ataque(umbral):
    """MOV [EBP+2],AX; CMP EAX,imm8; JG +1b  (misma longitud, mismo destino de salto)."""
    if umbral is None:
        return ATAQUE_ORIGINAL
    return bytes.fromhex("66894502") + bytes([0x83, 0xF8, umbral & 0xFF]) + bytes.fromhex("7f1b")

DIAL_INVOCAR = 0x5B154B
INVOCAR_ORIGINAL = bytes.fromhex("3d84030000")                           # CMP EAX,0x384 (900)
def bytes_invocar(atk_min):
    if atk_min is None:
        return INVOCAR_ORIGINAL
    return b"\x3d" + struct.pack("<I", atk_min)

# temperamento -> (umbral de ataque, ATK minimo para invocar en ataque); None = codigo original
DIALES = {
    "agresivo":   (-100, 500),   # acepta intercambios y ataques arriesgados; invoca cualquier cosa
    "tortuga":    (127, 1400),   # solo ataca con margen claro; solo invoca en ataque monstruos fuertes
    "piromano":   (-1, 900),     # intercambia 1x1 (quiere vaciar tu campo para quemar)
    "tramposo":   (0, 1200),     # prudente al invocar, deja que sus flips/trampas hagan el trabajo
    "clasico":    (None, None),  # IA original intacta
    "caotico":    "azar",        # diales aleatorios por duelo
    "legendario": (60, 1300),    # resiste mientras arma su combo
}

GRUPOS = ["agresivo", "tortuga", "piromano", "tramposo", "clasico", "caotico", "legendario"]
PESOS_GRUPO = [4, 2, 2, 2, 2, 1, 1]
NIVEL_A_TIER = {1: 0, 2: 0, 3: 1, 4: 1, 5: 2, 6: 2, 7: 3}
CLASICOS = {1: [0, 1, 2, 3, 4], 2: [3, 4, 10, 11, 12], 3: [10, 11, 12, 13, 14],
            4: [13, 14, 15, 20, 21], 5: [20, 21, 22, 23, 24], 6: [23, 24, 25, 26, 27],
            7: [25, 26, 27, 28, 29]}

log = logging.getLogger("yugi")

def configurar_log(consola=True):
    os.makedirs(LOG_DIR, exist_ok=True)
    ruta = os.path.join(LOG_DIR, time.strftime("sesion_%Y%m%d_%H%M%S.log"))
    log.setLevel(logging.DEBUG)
    log.handlers.clear()
    fh = logging.FileHandler(ruta, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter("%(asctime)s.%(msecs)03d [%(levelname)-7s] [%(threadName)s] "
                                      "%(funcName)s:%(lineno)d | %(message)s", "%Y-%m-%d %H:%M:%S"))
    log.addHandler(fh)
    if consola:
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logging.INFO)
        ch.setFormatter(logging.Formatter("%(message)s"))
        log.addHandler(ch)
    # podar logs viejos: conservar los 40 mas recientes
    viejos = sorted(glob.glob(os.path.join(LOG_DIR, "sesion_*.log")))[:-40]
    for v in viejos:
        try: os.remove(v)
        except OSError: pass
    return ruta

def swap(bs):
    return bytes(((x & 0x0F) << 4) | (x >> 4) for x in bs)

def tier_de(fn):
    if fn.startswith("cpu_0"): return min(int(fn[5]), 3)
    if fn.startswith("ful_"): return int(fn[4])
    return 1

def leer_main(path):
    d = open(path, "rb").read()
    n = struct.unpack("<H", d[8:10])[0]
    return list(struct.unpack("<%dH" % n, d[10:10 + n * 2]))

# ---------- historial / dificultad elastica ----------
def cargar_historial(ruta=HISTORIAL):
    try:
        h = json.load(open(ruta, encoding="utf-8"))
        if not isinstance(h, dict): raise ValueError("historial no es un objeto")
        h.setdefault("resultados", [])
        h["nivel"] = max(-1.0, min(2.0, float(h.get("nivel", 0.0))))
        log.debug("historial cargado: nivel=%+.2f, %d resultados", h["nivel"], len(h["resultados"]))
        return h
    except FileNotFoundError:
        log.debug("sin historial previo: nivel 0")
    except Exception as e:
        log.warning("historial ilegible (%s): se reinicia a nivel 0", e)
    return {"nivel": 0.0, "resultados": []}

def registrar_resultado(h, r, ruta=HISTORIAL):
    antes = h["nivel"]
    h["resultados"].append(r)
    h["nivel"] = max(-1.0, min(2.0, h["nivel"] + (0.34 if r == "g" else -0.34)))
    tmp = ruta + ".tmp"
    json.dump(h, open(tmp, "w", encoding="utf-8"), indent=1)
    os.replace(tmp, ruta)  # escritura atomica
    log.debug("resultado '%s' registrado: nivel %+.2f -> %+.2f (%s)", r, antes, h["nivel"], ruta)
    return h["nivel"]

# ---------- sesgo adaptativo ----------
def perfil_jugador(deck=os.path.join(APP, "Deck.ydc")):
    try:
        por_id = {int(r["id"]): r for r in csv.DictReader(open(CARDS_CSV, encoding="utf-8"))}
        tipos, atks, desconocidas = {}, [], 0
        for e in leer_main(deck):
            c = por_id.get(e)
            if not c:
                desconocidas += 1
                continue
            if c["tipo"] in ("Magic", "Trap"): continue
            tipos[c["tipo"]] = tipos.get(c["tipo"], 0) + 1
            atks.append(int(c["atk"]))
        dom = max(tipos, key=tipos.get) if tipos else None
        log.debug("perfil del jugador: tipos=%s atk_prom=%.0f ids_desconocidos=%d",
                  tipos, sum(atks) / max(1, len(atks)), desconocidas)
        if dom and tipos[dom] < 9: dom = None
        return dom, sum(atks) / max(1, len(atks))
    except Exception as e:
        log.warning("no pude leer el perfil del jugador (%s): sin sesgo", e)
        return None, 0

def peso(m, dominante, atk_prom):
    w = 1.0
    if dominante:
        if atk_prom >= 1400 and m["arquetipo"] in ("muro-trampas", "quemadura", "flip-sorpresa", "curacion"):
            w *= 2.2
        if m["arquetipo"] == "control de mano":
            w *= 1.6
        if m["arquetipo"] == "tribal " + dominante:
            w *= 1.5
    return w

def grupo_de(arq):
    if arq == "quemadura": return "piromano"
    if arq in ("muro-trampas", "curacion"): return "tortuga"
    if arq in ("flip-sorpresa", "control de mano"): return "tramposo"
    if arq == "caos (draft)": return "caotico"
    if arq == "Exodia": return "legendario"
    if arq.startswith("variante"): return "clasico"
    return "agresivo"  # tribales y atributos: beatdown directo

def cargar_numerados(ruta=NUMEROS_CSV):
    nums = list(csv.DictReader(open(ruta, encoding="utf-8")))
    for m in nums:
        m["numero"] = int(m["numero"]); m["tier"] = int(m["tier"])
        m["grupo"] = grupo_de(m["arquetipo"])
    log.debug("biblioteca numerada: %d mazos (%s)", len(nums),
              {g: sum(1 for m in nums if m["grupo"] == g) for g in GRUPOS})
    return nums

class Selector:
    """Arma la tabla de 40 numeros y los diales para un temperamento."""
    def __init__(self, numerados, nivel, dominante=None, atk_prom=0, rng=None):
        self.numerados = numerados
        self.por_num = {m["numero"]: m for m in numerados}
        self.por_tier = {t: [m for m in numerados if m["tier"] == t] for t in range(4)}
        self.nivel = nivel
        self.dominante, self.atk_prom = dominante, atk_prom
        self.rng = rng or random.Random()

    def tier_para(self, nivel_juego):
        nv = max(1, min(7, nivel_juego or 1))  # el motor trata el nivel 0 como 1
        return max(0, min(3, NIVEL_A_TIER[nv] + int(round(self.nivel))))

    def elegibles(self, nivel_juego):
        """Temperamentos con >= 5 mazos propios cerca del tier del nivel actual. Sin esto un
        'legendario' (solo mazos Exodia, tiers 2-3) en nivel bajo se rellenaba con mazos ajenos."""
        t = self.tier_para(nivel_juego)
        return [g for g in GRUPOS
                if sum(1 for m in self.numerados if m["grupo"] == g and abs(m["tier"] - t) <= 1) >= 5]

    def sortear_temperamento(self, nivel_juego=None):
        grupos, pesos = GRUPOS, PESOS_GRUPO
        if nivel_juego is not None:
            ok = self.elegibles(nivel_juego)
            if ok:
                grupos = [g for g in GRUPOS if g in ok]
                pesos = [w for g, w in zip(GRUPOS, PESOS_GRUPO) if g in ok]
            log.debug("nivel del juego %s -> tier %d, temperamentos elegibles: %s",
                      nivel_juego, self.tier_para(nivel_juego), grupos)
        return self.rng.choices(grupos, weights=pesos, k=1)[0]

    def diales(self, temperamento):
        d = DIALES[temperamento]
        if d == "azar":
            return (self.rng.randint(-128, 127), self.rng.choice([300, 500, 700, 900, 1100, 1300, 1600]))
        return d

    def tabla(self, temperamento):
        tabla = [0, 1, 2, 3, 4]  # indices 0-4: nunca se leen (nivel >= 1)
        for nv in range(1, 8):
            t = max(0, min(3, NIVEL_A_TIER[nv] + int(round(self.nivel))))
            pool = [m for m in self.por_tier[t] if m["grupo"] == temperamento]
            origen = "tier exacto"
            if len(pool) < 5:
                pool = [m for m in self.numerados if m["grupo"] == temperamento and abs(m["tier"] - t) <= 1]
                origen = "tier +-1"
            if len(pool) < 5:
                pool = self.por_tier[t] or self.numerados
                origen = "cualquier temperamento (pool pequeno)"
            fila = []
            disponibles = list(pool)  # muestreo ponderado SIN reemplazo: 5 candidatos distintos si se puede
            for _ in range(5):
                if self.rng.random() < 0.10:  # 10%: mazo original de nostalgia
                    fila.append(self.rng.choice(CLASICOS[nv]))
                else:
                    if not disponibles:
                        disponibles = list(pool)
                    pesos = [peso(m, self.dominante, self.atk_prom) for m in disponibles]
                    el = self.rng.choices(disponibles, weights=pesos, k=1)[0]
                    disponibles.remove(el)
                    fila.append(el["numero"])
            log.debug("tabla nivel %d -> tier %d (%s, pool %d): %s", nv, t, origen, len(pool),
                      ", ".join(self.describir(x) for x in fila))
            tabla += fila
        return tabla

    def describir(self, numero):
        m = self.por_num.get(numero)
        if m: return "cpu_%03d=%s[%s]" % (numero, m["archivo"], m["arquetipo"])
        return "cpu_%03d=original" % numero

# ---------- memoria del proceso ----------
k32 = ctypes.windll.kernel32
k32.OpenProcess.restype = wintypes.HANDLE
k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
k32.VirtualProtectEx.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_size_t, wintypes.DWORD,
                                 ctypes.POINTER(wintypes.DWORD)]
k32.WriteProcessMemory.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_char_p, ctypes.c_size_t,
                                   ctypes.POINTER(ctypes.c_size_t)]
k32.ReadProcessMemory.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t,
                                  ctypes.POINTER(ctypes.c_size_t)]
k32.FlushInstructionCache.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_size_t]
k32.CloseHandle.argtypes = [wintypes.HANDLE]
PAGE_EXECUTE_READWRITE = 0x40
PROCESS_VM = 0x0008 | 0x0010 | 0x0020 | 0x0400  # VM_OPERATION | VM_READ | VM_WRITE | QUERY_INFORMATION

class Memoria:
    def __init__(self, pid):
        self.pid = pid
        self.h = k32.OpenProcess(PROCESS_VM, False, pid)
        if not self.h:
            raise OSError("OpenProcess(pid=%d) fallo, GetLastError=%d" % (pid, k32.GetLastError()))
        log.debug("proceso %d abierto, handle=%s", pid, self.h)

    def leer(self, addr, n):
        buf = ctypes.create_string_buffer(n)
        leido = ctypes.c_size_t()
        if k32.ReadProcessMemory(self.h, addr, buf, n, ctypes.byref(leido)) and leido.value == n:
            return buf.raw
        log.debug("ReadProcessMemory(0x%X, %d) fallo: leidos=%d err=%d", addr, n, leido.value, k32.GetLastError())
        return None

    def escribir(self, addr, data, etiqueta=""):
        old = wintypes.DWORD()
        if not k32.VirtualProtectEx(self.h, addr, len(data), PAGE_EXECUTE_READWRITE, ctypes.byref(old)):
            log.error("VirtualProtectEx(0x%X) fallo err=%d %s", addr, k32.GetLastError(), etiqueta)
            return False
        escrito = ctypes.c_size_t()
        ok = k32.WriteProcessMemory(self.h, addr, data, len(data), ctypes.byref(escrito))
        restaurar = wintypes.DWORD()
        k32.VirtualProtectEx(self.h, addr, len(data), old.value, ctypes.byref(restaurar))
        k32.FlushInstructionCache(self.h, addr, len(data))
        eco = self.leer(addr, len(data))
        bien = bool(ok) and escrito.value == len(data) and eco == data
        nivel_log = logging.DEBUG if bien else logging.ERROR
        log.log(nivel_log, "escribir 0x%X %s (%d B, prot 0x%X): %s | eco=%s %s", addr, etiqueta, len(data),
                old.value, data.hex() if len(data) <= 16 else "%s..." % data[:16].hex(),
                "OK" if bien else "FALLO", "" if bien else "err=%d" % k32.GetLastError())
        return bien

    def cerrar(self):
        if self.h:
            k32.CloseHandle(self.h)
            log.debug("handle del proceso %d cerrado", self.pid)
            self.h = None

def escribir_tabla(mem, nums):
    """nums: 40 valores (indices 0-4 son marcadores y no se escriben)."""
    assert len(nums) == 40
    cola_antes = mem.leer(*FUL_COLA)
    ok = mem.escribir(TABLA_INI, struct.pack("<35I", *nums[5:]), "tabla CPU")
    if mem.leer(*FUL_COLA) != cola_antes:
        log.error("la escritura de la tabla altero la tabla FUL vecina (0x%X)", FUL_COLA[0])
        return False
    return ok

def leer_tabla(mem):
    """Devuelve 40 valores con los 5 marcadores [0..4] delante, para indexar igual que el motor."""
    raw = mem.leer(TABLA_INI, 140)
    return [0, 1, 2, 3, 4] + list(struct.unpack("<35I", raw)) if raw else None

def aplicar_diales(mem, umbral, atk_min):
    """Verifica que el codigo sea el original o un parche nuestro antes de tocarlo."""
    ok = True
    actual = mem.leer(DIAL_ATAQUE, 9)
    if actual is None or not (actual == ATAQUE_ORIGINAL or (actual[:6] == bytes.fromhex("66894502" "83f8")
                                                              and actual[7:] == bytes.fromhex("7f1b"))):
        log.error("dial ataque: bytes inesperados en 0x%X (%s); NO se parchea", DIAL_ATAQUE,
                  actual.hex() if actual else None)
        ok = False
    else:
        ok &= mem.escribir(DIAL_ATAQUE, bytes_ataque(umbral), "dial ataque umbral=%s" % umbral)
    actual = mem.leer(DIAL_INVOCAR, 5)
    if actual is None or actual[0] != 0x3D:
        log.error("dial invocar: bytes inesperados en 0x%X (%s); NO se parchea", DIAL_INVOCAR,
                  actual.hex() if actual else None)
        ok = False
    else:
        ok &= mem.escribir(DIAL_INVOCAR, bytes_invocar(atk_min), "dial invocar atk_min=%s" % atk_min)
    return ok

# --- ruta del mazo CPU (FUN_0044bbe0): con la opcion "todo el set" el juego cargaria FUL_<nombre>.ydc
# de una lista fija de Konami; el JE pasa a JMP para que use siempre la tabla CPU_ inyectada.
# Solo afecta al mazo de la CPU: la opcion sigue valiendo para todo lo demas (menu, progresion, guardado).
RUTA_CPU = 0x44BC08
RUTA_CPU_ORIGINAL = bytes.fromhex("0f840e010000")   # JE 0x44BD1C (rama "solo Joey")
RUTA_CPU_SIEMPRE = bytes.fromhex("e90f01000090")    # JMP 0x44BD1C; NOP

def aplicar_ruta_cpu(mem, siempre_tabla=True):
    deseado = RUTA_CPU_SIEMPRE if siempre_tabla else RUTA_CPU_ORIGINAL
    actual = mem.leer(RUTA_CPU, 6)
    if actual == deseado:
        return True
    if actual not in (RUTA_CPU_ORIGINAL, RUTA_CPU_SIEMPRE):
        log.error("ruta CPU: bytes inesperados en 0x%X (%s); NO se parchea", RUTA_CPU, actual.hex() if actual else None)
        return False
    return mem.escribir(RUTA_CPU, deseado, "ruta CPU %s" % ("siempre tabla inyectada" if siempre_tabla else "original"))

def leer_estado(mem):
    raw = mem.leer(ADDR_GANADOR, 5)
    if not raw: return None
    return {"ganador": raw[0], "racha": raw[1], "nivel_juego": raw[4]}

def leer_lp(mem):
    vals = []
    for a in ADDR_LP:
        raw = mem.leer(a, 2)
        vals.append(struct.unpack("<H", raw)[0] if raw else None)
    return vals

# ---------- vigilancia por duelo ----------
class Vigilante:
    def __init__(self, proc, selector, historial, usar_diales=True, ruta_historial=HISTORIAL,
                 memoria_factory=None, espera_inicial=2.5, refresco=REFRESCO):
        self.proc, self.sel, self.hist = proc, selector, historial
        self.usar_diales = usar_diales
        self.ruta_historial = ruta_historial
        self.memoria_factory = memoria_factory or Memoria
        self.espera_inicial, self.refresco = espera_inicial, refresco
        self.forzada = None  # tabla fija (pruebas): si no es None, se usa en vez de la sorteada
        self.resultados = []
        self.temperamento = None
        self.diales_actuales = None
        self.tabla_actual = None
        self.ciclos = 0
        self.modo_ful = 0  # ultimo valor visto de la opcion "todo el set" (solo para registrarlo)
        self.ruta_tabla = True  # False (--ful-original): con "todo el set" la CPU usa los mazos FUL_ de Konami
        self.errores = 0
        self.detener = threading.Event()

    def nuevo_duelo(self, mem, motivo):
        self.sel.nivel = self.hist["nivel"]
        est = leer_estado(mem)
        self.temperamento = self.sel.sortear_temperamento(est["nivel_juego"] if est else None)
        self.tabla_actual = list(self.forzada) if self.forzada else self.sel.tabla(self.temperamento)
        self.diales_actuales = self.sel.diales(self.temperamento) if self.usar_diales else (None, None)
        log.info("proximo rival: %s (diales: umbral ataque=%s, ATK min invocar=%s) [%s]",
                 self.temperamento.upper(), *self.diales_actuales, motivo)
        ok_t = escribir_tabla(mem, self.tabla_actual)
        ok_d = aplicar_diales(mem, *self.diales_actuales)
        ok_r = aplicar_ruta_cpu(mem, self.ruta_tabla)
        if not ok_t: self.errores += 1
        if not ok_d: self.errores += 1
        if not ok_r: self.errores += 1
        return ok_t and ok_d and ok_r

    def correr(self):
        try:
            mem = self.memoria_factory(self.proc.pid)
        except OSError as e:
            log.error("no pude abrir el proceso para inyectar: %s; solo variedad por sesion", e)
            return
        try:
            time.sleep(self.espera_inicial)  # deja que el exe termine de inicializar
            self.nuevo_duelo(mem, "inicio de sesion")
            eco = leer_tabla(mem)
            log.info("inyeccion activa: tabla %s", "verificada" if eco == self.tabla_actual else "NO verificada")
            previo = leer_estado(mem)
            log.debug("estado inicial: %s lp=%s", previo, leer_lp(mem))
            while self.proc.poll() is None and not self.detener.is_set():
                self.ciclos += 1
                # el juego no escribe la tabla, pero se reescribe por si algo la restaurara
                eco = leer_tabla(mem)
                if eco is not None and eco != self.tabla_actual:
                    log.warning("la tabla en memoria cambio por fuera; se reescribe")
                    escribir_tabla(mem, self.tabla_actual)
                # la opcion "todo el set / solo Joey" es del jugador: solo se registra, nunca se revierte
                ful = mem.leer(ADDR_MODO_FUL, 1)
                if ful and ful[0] != self.modo_ful:
                    self.modo_ful = ful[0]
                    if ful[0] and not self.ruta_tabla:
                        log.warning("modo FUL activo (opcion 'todo el set') con --ful-original: la CPU usa los "
                                    "mazos FUL_ de Konami (personalidades sin efecto)")
                    else:
                        log.info("opcion de cartas: %s (la CPU sigue usando la tabla inyectada)",
                                 "todo el set" if ful[0] else "solo Joey")
                est = leer_estado(mem)
                if est is None:
                    log.debug("ciclo %d: no se pudo leer el estado (proceso cerrando?)", self.ciclos)
                elif previo is not None and est != previo and est["ganador"] in (1, 2):
                    r = "g" if est["ganador"] == 1 else "p"
                    self.resultados.append(r)
                    niv = registrar_resultado(self.hist, r, self.ruta_historial)
                    log.info("duelo terminado: %s contra %s (nivel del juego %d, racha %d) | nivel elastico %+.2f",
                             "GANASTE" if r == "g" else "perdiste", self.temperamento,
                             est["nivel_juego"], est["racha"], niv)
                    log.debug("transicion de estado %s -> %s", previo, est)
                    self.nuevo_duelo(mem, "tras duelo %d" % len(self.resultados))
                if self.ciclos % 10 == 1:
                    log.debug("ciclo %d: estado=%s lp=%s temperamento=%s", self.ciclos, est, leer_lp(mem),
                              self.temperamento)
                if est is not None:
                    previo = est
                self.detener.wait(self.refresco)
        except Exception:
            log.exception("error en el hilo de vigilancia")
            self.errores += 1
        finally:
            mem.cerrar()
            log.debug("vigilancia terminada: %d ciclos, %d resultados, %d errores",
                      self.ciclos, len(self.resultados), self.errores)

# ---------- parcheo por sesion: ful_* (tabla de strings, no numerica) ----------
def parchear_fuls(numerados, nivel, dominante=None, atk_prom=0, rng=None, destino=DESTINO, ruta_sel=LOG_SEL):
    rng = rng or random.Random()
    shutil.copyfile(FULL, destino)
    log.debug("copiado %s -> %s (%d B)", FULL, destino, os.path.getsize(destino))
    mods, usados, lineas = {}, set(), []
    for slot_path in sorted(glob.glob(os.path.join(SLOTS_DIR, "ful_*.ydc"))):
        fn = os.path.basename(slot_path)[:-4]
        t = max(0, min(3, tier_de(fn) + int(round(nivel))))
        cand = [m for m in numerados if m["tier"] == t and m["archivo"] not in usados]
        if not cand:
            cand = [m for m in numerados if abs(m["tier"] - t) <= 1 and m["archivo"] not in usados]
        el = rng.choices(cand, weights=[peso(m, dominante, atk_prom) for m in cand], k=1)[0]
        usados.add(el["archivo"])
        hdr = open(slot_path, "rb").read(8)
        cuerpo = open(os.path.join(BIBLIOTECA, el["archivo"]), "rb").read()[8:]
        mods["j\\file\\%s.ydc" % fn] = hdr + cuerpo
        lineas.append("%-14s <- %-28s (tier %s, %s)" % (fn, el["archivo"], el["tier"], el["arquetipo"]))
        log.debug("slot %s (tier %d) <- %s [%s]", fn, t, el["archivo"], el["arquetipo"])
    aplicados = 0
    with open(destino, "r+b") as f:
        if f.read(8) != b"KCEJYUGI":
            raise ValueError("Data.dat sin firma KCEJYUGI")
        count = struct.unpack("<I", f.read(4))[0]
        for i in range(count):
            f.seek(12 + i * 268)
            raw = f.read(268)
            name = swap(raw[:256]).split(b"\x00")[0].decode("latin-1")
            data = mods.get(name.lower())
            if data:
                f.seek(0, 2)
                off = f.tell()
                f.write(data)
                f.seek(12 + i * 268 + 256)
                f.write(struct.pack("<III", off, len(data), len(data)))
                aplicados += 1
    open(ruta_sel, "w", encoding="utf-8").write("\n".join(sorted(lineas)))
    log.debug("ful_* aplicados: %d de %d", aplicados, len(mods))
    return aplicados

# ---------- main ----------
def main(argv):
    ruta_log = configurar_log()
    args_juego = argv[argv.index("--") + 1:] if "--" in argv else []  # p.ej. -- -win -speedy
    argv = argv[:argv.index("--")] if "--" in argv else argv
    solo_parchear = "--solo-parchear" in argv
    puro = "--puro" in argv
    clasico = "--clasico" in argv
    sin_diales = "--sin-diales" in argv
    log.debug("argv=%s python=%s pid=%d", argv, sys.version.split()[0], os.getpid())
    if not os.path.exists(FULL):
        log.error("falta Data.dat.full: ejecuta antes datadat_rebuild.py")
        return 2
    hist = cargar_historial()
    dominante, atk_prom = (None, 0) if puro else perfil_jugador()
    numerados = cargar_numerados()
    log.info("Yugi Reload v3 | nivel elastico %+.1f%s | log: %s", hist["nivel"],
             " | sesgo vs " + dominante if dominante else "", ruta_log)
    log.info("preparando Data.dat de la sesion...")
    n = parchear_fuls(numerados, hist["nivel"], dominante, atk_prom)
    log.info("mazos tematicos (ful_*) rebarajados: %d | biblioteca en cpu_100-645: %d mazos", n, len(numerados))
    if solo_parchear:
        return 0
    log.info("lanzando el juego...")
    proc = subprocess.Popen([EXE] + args_juego, cwd=APP)
    log.debug("juego lanzado pid=%d args=%s", proc.pid, args_juego)
    vig = None
    if not clasico:
        sel = Selector(numerados, hist["nivel"], dominante, atk_prom)
        vig = Vigilante(proc, sel, hist, usar_diales=not sin_diales)
        vig.ruta_tabla = "--ful-original" not in argv
        threading.Thread(target=vig.correr, name="vigilante", daemon=True).start()
    codigo = proc.wait()
    log.info("el juego se cerro (codigo %s)", codigo)
    if vig:
        vig.detener.set()
        if vig.resultados:
            log.info("resultados de la sesion: %s | nivel elastico ahora %+.2f",
                     " ".join(vig.resultados), hist["nivel"])
            return 0
    try:
        r = input("No detecte duelos. ¿Como te fue? g=ganaste, p=perdiste, enter=saltar: ").strip().lower()
    except EOFError:
        r = ""
    if r in ("g", "p"):
        log.info("nivel elastico ahora: %+.2f", registrar_resultado(hist, r))
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
