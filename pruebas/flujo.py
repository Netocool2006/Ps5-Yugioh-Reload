# Navegacion del juego para pruebas: reconoce pantallas (recortes de referencia) y senales de memoria.
import logging, os, struct, sys, time
from PIL import Image
sys.path.insert(0, r"D:\Yugi-Reload\launcher")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import control
import yugi_reload as yr

log = logging.getLogger("yugi.flujo")
REF = os.path.join(os.path.dirname(os.path.abspath(__file__)), "referencias")
LP_CPU, LP_JUG = 0xA55D64, 0xA56AA8   # duelo real: lado 0 = CPU, lado 1 = jugador
LADO_CPU, LADO_JUG = 0, 1

# (referencia, caja de recorte en coordenadas logicas 800x600). Cajas elegidas para DISTINGUIR:
# el menu principal (tablas marron, letra blanca) y el submenu (tablas doradas, letra negra) se
# parecian en gris; ahora se compara color por canal sobre la primera tabla.
PANTALLAS = {
    "menu_principal": ("menu_principal.png", (205, 322, 595, 362)),
    "submenu_duelo": ("submenu_duelo.png", (205, 322, 595, 362)),
    "janken": ("janken.png", (225, 282, 580, 322)),                  # texto "Selecciona tu mano"
    "primero_segundo": ("primero_segundo.png", (290, 385, 510, 520)),  # texto "SEGUNDO EN JUGAR"
    "primero_segundo#hover": ("primero_segundo_hover.png", (290, 385, 510, 520)),  # con PRIMERO resaltado
    "construccion_deck": ("construccion_deck.png", (0, 0, 210, 85)),       # PELIGROSA: solo salir por ATRAS
    "demo": ("demo.png", (585, 558, 792, 594)),  # solo la palabra DEMOSTRACION
    "opciones": ("opciones.png", (300, 300, 510, 340)),                    # PELIGROSA: salir con Esc
    "dialogo_repeticion": ("has_ganado_repeticion.png", (240, 405, 560, 470)),  # "¿Quieres guardar...?"
    "robar_otra": ("robar_otra.png", (240, 470, 570, 522)),  # "¿Quieres robar otra carta?" (tras rachas)
    "intercambiar_cartas": ("intercambiar_cartas.png", (10, 15, 205, 70)),  # entre rondas de TORNEO (side deck)
    "retrato_inicio": ("retrato_inicio.png", (20, 330, 330, 600)),  # figura de Joey (el texto cambia)
}
PELIGROSAS = {"construccion_deck": ("clic", (110, 570)),  # boton ATRAS
              "opciones": ("tecla", "esc")}
# pantallas que piden una respuesta concreta (siempre la que no altera nada)
RESPUESTAS = {"dialogo_repeticion": (460, 497),   # NO guardar repeticion
              "robar_otra": (460, 545),           # NO robar carta extra
              "intercambiar_cartas": (110, 570)}  # ATRAS: seguir el torneo sin cambiar el side deck
CLIC_NEUTRO = (720, 180)  # alambrada arriba a la derecha: no hace nada en el menu y avanza demo/retratos
UMBRAL, MARGEN = 0.10, 0.03
UMBRAL_PANTALLA = {"demo": 0.07}  # el rincon de la demo se parece al tablero de un duelo real
_cache = {}

def _ref(nombre):
    if nombre not in _cache:
        archivo, caja = PANTALLAS[nombre]
        im = Image.open(os.path.join(REF, archivo)).convert("RGB")
        if im.size != (800, 600):
            im = im.crop((0, 0, 800, 600))
        _cache[nombre] = im.crop(caja)
    return _cache[nombre]

def dif_color(a, b):
    """Diferencia media por canal RGB (0..1) sobre version reducida."""
    a = a.resize((64, 32)); b = b.resize((64, 32))
    pa, pb = a.load(), b.load()
    tot = 0
    for x in range(64):
        for y in range(32):
            ra, ga, ba_ = pa[x, y]; rb, gb, bb = pb[x, y]
            tot += abs(ra - rb) + abs(ga - gb) + abs(ba_ - bb)
    return tot / (64 * 32 * 3 * 255.0)

def puntuar(img):
    if img.size != (800, 600):
        img = img.crop((0, 0, 800, 600))
    return sorted((dif_color(img.convert("RGB").crop(caja), _ref(n)), n) for n, (_, caja) in PANTALLAS.items())

def clasificar(img):
    """(nombre o None, mejor_dif, segunda_dif). Las variantes 'x#y' cuentan como la pantalla x."""
    p = puntuar(img)
    d1, n1 = p[0]
    n1 = n1.split("#")[0]
    d2 = next((d for d, n in p[1:] if n.split("#")[0] != n1), 1.0)  # variantes no compiten entre si
    return (n1 if d1 < UMBRAL_PANTALLA.get(n1, UMBRAL) and d2 - d1 >= MARGEN else None), d1, d2

def que_pantalla(hwnd, etiqueta="estado"):
    ruta, img = control.captura(hwnd, etiqueta)
    if img is None:
        return None, None, ruta
    nombre, d1, d2 = clasificar(img)
    log.debug("pantalla: %s | mejor %.3f, segunda %.3f | %s", nombre, d1, d2, ruta)
    if nombre in PELIGROSAS:
        tipo, arg = PELIGROSAS[nombre]
        log.error("pantalla PELIGROSA detectada (%s): se sale con %s %s sin tocar nada mas", nombre, tipo, arg)
        control.clic(hwnd, *arg) if tipo == "clic" else control.tecla(arg)
        time.sleep(2.0)
    return nombre, img, ruta

class Juego:
    """Envoltura del proceso vivo: ventana + memoria."""
    def __init__(self, proc):
        self.proc = proc
        self.hwnd = control.ventana_de(proc.pid, 40)
        control.HWND_JUEGO[0] = self.hwnd
        self.mem = yr.Memoria(proc.pid)

    def vivo(self):
        return self.proc.poll() is None

    def lp(self):
        return yr.leer_lp(self.mem)  # [CPU, jugador]

    def contadores(self, lado):
        raw = self.mem.leer(0xA55D64 + lado * 0xD44 + 4, 4)
        return {"mano": raw[0], "mazo": raw[1], "cementerio": raw[2], "fusion": raw[3]} if raw else None

    def nivel_motor(self):
        raw = self.mem.leer(yr.ADDR_DIFICULTAD, 2)
        return raw[0], raw[1]  # nivel (0xA54DB3), modo torneo (0xA54DB4)

    def duelo_activo(self):
        lp = self.lp()
        c, j = self.contadores(LADO_CPU), self.contadores(LADO_JUG)
        if not c or not j:
            return False
        return lp == [8000, 8000] and c["mazo"] > 20 and j["mazo"] > 20 and c["mano"] >= 5 and j["mano"] >= 5

    def poner_lp(self, lado_addr, valor):
        return self.mem.escribir(lado_addr, struct.pack("<H", valor), "LP=%d (prueba)" % valor)

    def cerrar(self):
        self.mem.cerrar()

def esperar(cond, timeout, paso=0.5, desc=""):
    fin = time.time() + timeout
    while time.time() < fin:
        try:
            if cond():
                return True
        except Exception as e:
            log.debug("esperar(%s): %s", desc, e)
        time.sleep(paso)
    log.warning("timeout (%.0fs) esperando: %s", timeout, desc)
    return False

def duelo_en_curso(j):
    lp = j.lp(); c, u = j.contadores(LADO_CPU), j.contadores(LADO_JUG)
    return bool(c and u and lp[0] and lp[1] and lp[0] <= 8000 and lp[1] <= 8000 and c["mazo"] > 0 and u["mazo"] > 0)

def ir_a_menu_principal(j, timeout=90, clic=CLIC_NEUTRO):
    fin = time.time() + timeout
    cerrado = False
    while time.time() < fin and j.vivo():
        if not cerrado and duelo_en_curso(j) and que_pantalla(j.hwnd, "duelo_abierto")[0] is None:
            log.warning("quedo un duelo a medias: se termina (LP CPU = 0) para volver al menu")
            j.poner_lp(LP_CPU, 0); cerrado = True; time.sleep(3)
        p, img, _ = que_pantalla(j.hwnd, "hacia_menu")
        if p == "menu_principal":
            return True
        control.clic(j.hwnd, *RESPUESTAS.get(p, clic))
        time.sleep(1.8)
    return False

def iniciar_duelo(j, modo="individual", timeout=120):
    """Desde el menu principal hasta el primer turno. Devuelve (ok, pasos)."""
    pasos = []
    if not ir_a_menu_principal(j):
        return False, ["no se llego al menu principal"]
    p = None
    for intento in range(3):  # clic verificado: nada de Enter a ciegas sobre el menu principal
        control.clic(j.hwnd, 400, 340); time.sleep(2.0)
        p, _, _ = que_pantalla(j.hwnd, "tras_modo_duelo")
        if p == "submenu_duelo":
            break
    pasos.append("submenu=%s" % p)
    if p != "submenu_duelo":
        return False, pasos
    y = 342 if modo == "individual" else 392
    control.clic(j.hwnd, 400, y); time.sleep(2.0)
    fin = time.time() + timeout
    desconocidas = 0
    while time.time() < fin and j.vivo():
        if j.duelo_activo():
            pasos.append("duelo activo")
            return True, pasos
        p, _, _ = que_pantalla(j.hwnd, "camino_duelo")
        desconocidas = desconocidas + 1 if p is None else 0
        if p == "janken":
            control.clic(j.hwnd, 200, 450); pasos.append("janken: piedra")
        elif p == "primero_segundo":
            control.clic(j.hwnd, 400, 150); pasos.append("eligio primero")
        elif p == "retrato_inicio":
            control.tecla("enter"); pasos.append("retrato: enter")
        elif p == "submenu_duelo":
            control.clic(j.hwnd, 400, y); pasos.append("submenu: clic de nuevo")
        elif p in ("menu_principal", "construccion_deck", "opciones"):
            pasos.append("pantalla inesperada: %s" % p)
            return False, pasos
        else:
            pasos.append("pantalla desconocida (espera)")
            if desconocidas >= 12:  # ~20 s sin reconocer nada: abortar en vez de pulsar a ciegas
                pasos.append("abortado: demasiadas pantallas desconocidas")
                return False, pasos
        time.sleep(1.6)
    return False, pasos

def terminar_duelo(j, vig, ganar=True, timeout=60):
    """Fuerza el final por LP y vuelve al menu. Devuelve (resultado_detectado, llego_menu)."""
    antes = len(vig.resultados)
    j.poner_lp(LP_CPU if ganar else LP_JUG, 0)
    detectado = esperar(lambda: len(vig.resultados) > antes, timeout, 0.5, "resultado en el vigilante")
    time.sleep(2.0)
    llego = False
    fin = time.time() + 90
    while time.time() < fin and j.vivo():
        p, _, _ = que_pantalla(j.hwnd, "post_duelo")
        if p == "menu_principal":
            llego = True
            break
        if p in RESPUESTAS:
            control.clic(j.hwnd, *RESPUESTAS[p])
        else:
            control.clic(j.hwnd, *CLIC_NEUTRO)  # avanza recompensa/retratos; inocuo si ya es el menu
        time.sleep(2.0)
    return (vig.resultados[-1] if detectado else None), llego
