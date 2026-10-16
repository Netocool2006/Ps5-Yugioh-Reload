# Control simple del escritorio (pedido por el usuario para operar AccuRig): capturas, traer una ventana al frente,
# clics, doble clic, arrastrar, escribir texto y teclas. Coordenadas en pixeles de pantalla (1920x1080).
# Uso: python -I pantalla.py foto [salida.png]
#      python -I pantalla.py frente <parte del titulo>
#      python -I pantalla.py clic X Y | doble X Y | derecho X Y | arrastrar X1 Y1 X2 Y2
#      python -I pantalla.py escribir "texto" | tecla enter|tab|esc|ctrl+a ...
import ctypes, sys, time
from ctypes import wintypes
from PIL import ImageGrab

u = ctypes.windll.user32
u.SetProcessDPIAware()
SALIDA = r"D:\Docker\compartido\pantalla.png"
TECLAS = {"enter": 0x0D, "tab": 0x09, "esc": 0x1B, "ctrl": 0x11, "alt": 0x12, "shift": 0x10, "a": 0x41, "v": 0x56,
          "c": 0x43, "s": 0x53, "o": 0x4F, "backspace": 0x08, "delete": 0x2E, "up": 0x26, "down": 0x28, "left": 0x25,
          "right": 0x27, "f": 0x46, "e": 0x45}


def mover(x, y):
    u.SetCursorPos(int(x), int(y))
    time.sleep(0.05)


def boton(abajo, arriba, x, y):
    mover(x, y)
    u.mouse_event(abajo, 0, 0, 0, 0)
    time.sleep(0.05)
    u.mouse_event(arriba, 0, 0, 0, 0)


def tecla(nombre):
    partes = nombre.lower().split("+")
    for p in partes:
        u.keybd_event(TECLAS[p], 0, 0, 0)
        time.sleep(0.03)
    for p in reversed(partes):
        u.keybd_event(TECLAS[p], 0, 2, 0)
        time.sleep(0.03)


def escribir(texto):
    # por el portapapeles (respeta tildes y barras) y ctrl+v
    import subprocess
    subprocess.run(["powershell", "-NoProfile", "-Command", "Set-Clipboard -Value @'\n" + texto + "\n'@"], check=True)
    time.sleep(0.2)
    tecla("ctrl+v")


def frente(parte):
    encontradas = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def cada(h, _):
        n = u.GetWindowTextLengthW(h)
        if n and u.IsWindowVisible(h):
            b = ctypes.create_unicode_buffer(n + 1)
            u.GetWindowTextW(h, b, n + 1)
            if parte.lower() in b.value.lower():
                encontradas.append((h, b.value))
        return True

    u.EnumWindows(cada, 0)
    if not encontradas:
        sys.exit("no hay ventana con '%s'" % parte)
    h, t = encontradas[0]
    u.ShowWindow(h, 3)            # maximizada
    u.SetWindowPos(h, -1, 0, 0, 0, 0, 0x0001 | 0x0002)   # siempre encima mientras se opera
    u.keybd_event(0x12, 0, 0, 0)  # alt: permite SetForegroundWindow
    u.SetForegroundWindow(h)
    u.keybd_event(0x12, 0, 2, 0)
    if c == "frente":
        print("al frente:", t)


c = sys.argv[1]
# con YUGI_VENTANA=<titulo>, cada accion trae antes esa ventana al frente (las terminales se ponen encima)
import os
if os.environ.get("YUGI_VENTANA") and c not in ("frente",):
    frente(os.environ["YUGI_VENTANA"])
    time.sleep(0.3)
if c == "foto":
    time.sleep(0.4)
    ImageGrab.grab().save(sys.argv[2] if len(sys.argv) > 2 else SALIDA)
    print("foto lista")
elif c == "frente":
    frente(" ".join(sys.argv[2:]))
elif c == "clic":
    boton(2, 4, sys.argv[2], sys.argv[3])
elif c == "doble":
    boton(2, 4, sys.argv[2], sys.argv[3]); time.sleep(0.08); boton(2, 4, sys.argv[2], sys.argv[3])
elif c == "derecho":
    boton(8, 16, sys.argv[2], sys.argv[3])
elif c == "arrastrar":
    mover(sys.argv[2], sys.argv[3]); u.mouse_event(2, 0, 0, 0, 0)
    x1, y1, x2, y2 = map(int, sys.argv[2:6])
    for k in range(1, 21):
        mover(x1 + (x2 - x1) * k / 20, y1 + (y2 - y1) * k / 20)
    u.mouse_event(4, 0, 0, 0, 0)
elif c == "escribir":
    escribir(sys.argv[2])
elif c == "tecla":
    tecla(sys.argv[2])
