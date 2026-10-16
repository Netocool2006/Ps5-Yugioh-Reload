# Control del PC para pruebas de frontend: ventana del juego, capturas, teclado y raton.
# Teclado por scancode (SendInput KEYEVENTF_SCANCODE) porque el juego lee DirectInput.
import ctypes, logging, os, time
from ctypes import wintypes
from PIL import ImageGrab

log = logging.getLogger("yugi.control")
u32 = ctypes.windll.user32
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)  # coordenadas fisicas reales
except Exception:
    u32.SetProcessDPIAware()

CAPTURAS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "capturas")
os.makedirs(CAPTURAS, exist_ok=True)

SCAN = {"enter": 0x1C, "esc": 0x01, "space": 0x39, "up": 0x48, "down": 0x50, "left": 0x4B,
        "right": 0x4D, "z": 0x2C, "x": 0x2D, "c": 0x2E, "a": 0x1E, "s": 0x1F, "tab": 0x0F,
        "f1": 0x3B, "f2": 0x3C, "y": 0x15, "n": 0x31, "1": 0x02, "2": 0x03, "3": 0x04}
EXTENDIDAS = {"up", "down", "left", "right"}

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD), ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.c_size_t)]
class MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG), ("mouseData", wintypes.DWORD),
                ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.c_size_t)]
class _U(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT), ("mi", MOUSEINPUT), ("pad", ctypes.c_byte * 32)]
class INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("u", _U)]

def _enviar(*inputs):
    arr = (INPUT * len(inputs))(*inputs)
    n = u32.SendInput(len(inputs), arr, ctypes.sizeof(INPUT))
    if n != len(inputs):
        log.error("SendInput envio %d de %d (err=%d)", n, len(inputs), ctypes.GetLastError())
    return n == len(inputs)

class FocoPerdido(RuntimeError):
    pass

HWND_JUEGO = [None]

def exigir_foco():
    """Nunca mandar entrada a otra ventana (p.ej. la terminal)."""
    h = HWND_JUEGO[0]
    if h is None:
        raise FocoPerdido("HWND del juego no registrado")
    if u32.GetForegroundWindow() != h:
        enfocar(h)
        if u32.GetForegroundWindow() != h:
            log.error("la ventana activa no es el juego (activa=%s, juego=%s): entrada cancelada",
                      u32.GetForegroundWindow(), h)
            raise FocoPerdido("el juego no tiene el foco")

def tecla(nombre, pausa=0.12, mantener=0.06):
    exigir_foco()
    sc = SCAN[nombre]
    flags = 0x0008 | (0x0001 if nombre in EXTENDIDAS else 0)  # SCANCODE | EXTENDEDKEY
    abajo = INPUT(type=1); abajo.u.ki = KEYBDINPUT(0, sc, flags, 0, 0)
    arriba = INPUT(type=1); arriba.u.ki = KEYBDINPUT(0, sc, flags | 0x0002, 0, 0)
    ok = _enviar(abajo); time.sleep(mantener); ok &= _enviar(arriba)
    log.debug("tecla %s (sc=0x%02X) %s", nombre, sc, "ok" if ok else "FALLO")
    time.sleep(pausa)
    return ok

WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

def ventana_de(pid, timeout=30.0):
    fin = time.time() + timeout
    while time.time() < fin:
        encontradas = []
        def cb(hwnd, _):
            p = wintypes.DWORD()
            u32.GetWindowThreadProcessId(hwnd, ctypes.byref(p))
            if p.value == pid and u32.IsWindowVisible(hwnd):
                encontradas.append(hwnd)
            return True
        u32.EnumWindows(WNDENUMPROC(cb), 0)
        if encontradas:
            def clase(h):
                b = ctypes.create_unicode_buffer(128); u32.GetClassNameW(h, b, 128); return b.value
            def area(h):
                r = wintypes.RECT(); u32.GetClientRect(h, ctypes.byref(r)); return r.right * r.bottom
            info = [(h, clase(h), titulo(h), area(h)) for h in encontradas]
            log.debug("ventanas visibles del pid %d: %s", pid, info)
            principales = [h for h, c, t, a in info if c == "YUGIOHAPPLICATION"]
            if principales:
                return principales[0]
            return max(encontradas, key=area)
        time.sleep(0.5)
    log.error("no aparecio ventana visible para pid %d en %.0fs", pid, timeout)
    return None

def titulo(hwnd):
    buf = ctypes.create_unicode_buffer(256)
    u32.GetWindowTextW(hwnd, buf, 256)
    return buf.value

def rect_cliente(hwnd):
    r = wintypes.RECT()
    u32.GetClientRect(hwnd, ctypes.byref(r))
    p = wintypes.POINT(0, 0)
    u32.ClientToScreen(hwnd, ctypes.byref(p))
    return (p.x, p.y, p.x + r.right, p.y + r.bottom)

def enfocar(hwnd):
    # SIN el truco de pulsar ALT: el juego en ventana tiene barra de menu (IDR_MENU) y un ALT suelto
    # la pone en "modo menu", que se traga el siguiente clic. Se usa AttachThreadInput.
    if u32.GetForegroundWindow() == hwnd:
        return True
    k32 = ctypes.windll.kernel32
    fg = u32.GetForegroundWindow()
    t_fg = u32.GetWindowThreadProcessId(fg, None)
    t_yo = k32.GetCurrentThreadId()
    unido = bool(u32.AttachThreadInput(t_yo, t_fg, True)) if t_fg and t_fg != t_yo else False
    u32.ShowWindow(hwnd, 9)  # SW_RESTORE
    u32.BringWindowToTop(hwnd)
    ok = bool(u32.SetForegroundWindow(hwnd))
    if unido:
        u32.AttachThreadInput(t_yo, t_fg, False)
    time.sleep(0.3)
    act = u32.GetForegroundWindow() == hwnd
    log.debug("enfocar hwnd=%s attach=%s SetForegroundWindow=%s activa=%s", hwnd, unido, ok, act)
    return act

gdi = ctypes.windll.gdi32

def _printwindow(hwnd):
    """Contenido de la ventana aunque otra (terminal 'siempre encima') la tape."""
    from PIL import Image
    r = wintypes.RECT()
    u32.GetClientRect(hwnd, ctypes.byref(r))
    w, h = r.right, r.bottom
    hdc = u32.GetDC(hwnd)
    mdc = gdi.CreateCompatibleDC(hdc)
    bmp = gdi.CreateCompatibleBitmap(hdc, w, h)
    gdi.SelectObject(mdc, bmp)
    ok = u32.PrintWindow(hwnd, mdc, 3)  # PW_CLIENTONLY | PW_RENDERFULLCONTENT
    class BMI(ctypes.Structure):
        _fields_ = [("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG), ("biHeight", wintypes.LONG),
                    ("biPlanes", wintypes.WORD), ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
                    ("biSizeImage", wintypes.DWORD), ("a", wintypes.LONG), ("b", wintypes.LONG),
                    ("c", wintypes.DWORD), ("d", wintypes.DWORD)]
    bmi = BMI(ctypes.sizeof(BMI), w, -h, 1, 32, 0, 0, 0, 0, 0, 0)
    buf = ctypes.create_string_buffer(w * h * 4)
    gdi.GetDIBits(mdc, bmp, 0, h, buf, ctypes.byref(bmi), 0)
    gdi.DeleteObject(bmp); gdi.DeleteDC(mdc); u32.ReleaseDC(hwnd, hdc)
    img = Image.frombuffer("RGB", (w, h), buf, "raw", "BGRX", 0, 1)
    return img, bool(ok)

def captura(hwnd, nombre):
    if not u32.IsWindow(hwnd):
        log.warning("captura %s: la ventana %s ya no existe (juego cerrado)", nombre, hwnd)
        return None, None
    r = wintypes.RECT(); u32.GetClientRect(hwnd, ctypes.byref(r))
    if r.right <= 0 or r.bottom <= 0:
        log.warning("captura %s: ventana sin area cliente (cerrandose/minimizada)", nombre)
        return None, None
    img, ok = _printwindow(hwnd)
    metodo = "PrintWindow"
    if ok and img.size != (800, 600) and img.width >= 800 and img.crop((800, 0, img.width, img.height)).getbbox() is None:
        img = img.crop((0, 0, 800, 600))  # el juego dibuja a 800x600 logicos; el resto es relleno negro
    if not ok or img.getbbox() is None:  # fallo o imagen totalmente negra
        img = ImageGrab.grab(bbox=rect_cliente(hwnd), all_screens=True)
        metodo = "ImageGrab (respaldo)"
    ruta = os.path.join(CAPTURAS, "%s_%s.png" % (time.strftime("%H%M%S"), nombre))
    img.save(ruta)
    log.debug("captura %s via %s %dx%d -> %s", nombre, metodo, img.width, img.height, ruta)
    return ruta, img

def mover(sx, sy):
    """Movimiento absoluto real (genera eventos de entrada, a diferencia de SetCursorPos)."""
    vw, vh = u32.GetSystemMetrics(0), u32.GetSystemMetrics(1)
    m = INPUT(type=0)
    m.u.mi = MOUSEINPUT(int(sx * 65535 / (vw - 1)), int(sy * 65535 / (vh - 1)), 0, 0x0001 | 0x8000, 0, 0)
    return _enviar(m)

def clic(hwnd, x, y, pausa=0.3):
    """x,y en coordenadas LOGICAS del juego (800x600, las de las capturas); se escalan por DPI."""
    exigir_foco()
    x0, y0, x1, y1 = rect_cliente(hwnd)
    esc_x, esc_y = (x1 - x0) / 800.0, (y1 - y0) / 600.0
    sx, sy = x0 + int(round(x * esc_x)), y0 + int(round(y * esc_y))
    # El juego lee la posicion con GetCursorPos y los botones con DirectInput (no por WM_LBUTTON*),
    # asi que el clic debe ser entrada real (SendInput). Antes se exige que bajo ese punto exacto
    # este la ventana del juego: si fuera otra (la terminal), el clic le robaria el foco o algo peor.
    pt = wintypes.POINT(sx, sy)
    debajo = u32.GetAncestor(u32.WindowFromPoint(pt), 2)
    if debajo != hwnd:
        log.error("bajo (%d,%d) hay otra ventana (%s), no el juego (%s): clic cancelado", sx, sy, debajo, hwnd)
        raise FocoPerdido("otra ventana tapa el punto del clic")
    mover(sx + 25, sy + 18); time.sleep(0.12)
    mover(sx, sy); time.sleep(0.25)  # hover con movimiento real: el juego muestrea por frame
    # El juego guarda el boton desde WM_LBUTTONDOWN/UP y TAMBIEN desde WM_MOUSEMOVE (wParam & MK_LBUTTON),
    # asi que se mantiene pulsado ~0.4 s (varios frames) y se refuerza con WM_MOUSEMOVE+MK_LBUTTON.
    lp = (int(y) << 16) | (int(x) & 0xFFFF)  # el juego no es DPI-aware: coordenadas logicas
    a = INPUT(type=0); a.u.mi = MOUSEINPUT(0, 0, 0, 0x0002, 0, 0)  # LEFTDOWN
    b = INPUT(type=0); b.u.mi = MOUSEINPUT(0, 0, 0, 0x0004, 0, 0)  # LEFTUP
    ok = _enviar(a)
    for _ in range(4):
        time.sleep(0.1)
        u32.PostMessageW(hwnd, 0x0200, 0x0001, lp)  # WM_MOUSEMOVE con MK_LBUTTON
    ok &= _enviar(b)
    log.debug("clic logico(%d,%d) pantalla(%d,%d) via SendInput %s", x, y, sx, sy, "ok" if ok else "FALLO")
    time.sleep(pausa)
    return ok

def diferencia(img_a, img_b):
    """fraccion de pixeles distintos (muestreo) para saber si la pantalla cambio."""
    a = img_a.convert("L").resize((160, 120)); b = img_b.convert("L").resize((160, 120))
    pa, pb = a.load(), b.load()
    dif = sum(1 for x in range(160) for y in range(120) if abs(pa[x, y] - pb[x, y]) > 24)
    return dif / (160 * 120)
