# Herramienta de exploracion sobre el juego en ejecucion.
# Uso: python -I sesion.py <cmd> [args]   cmds: shot NOMBRE | key TECLA [N] | click X Y | mem | foco
#      Varios comandos encadenados con ";" en un solo argumento: "key down;key enter;shot menu"
import logging, os, struct, subprocess, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, r"D:\Yugi-Reload\launcher")
import control
import yugi_reload as yr

LOGS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(LOGS, exist_ok=True)
lg = logging.getLogger("yugi")
lg.setLevel(logging.DEBUG)
fh = logging.FileHandler(os.path.join(LOGS, "sesion_%s.log" % time.strftime("%Y%m%d")), encoding="utf-8")
fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)-7s] %(name)s %(funcName)s | %(message)s"))
lg.addHandler(fh)

def pid_juego():
    out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq Joey_Pc.exe", "/FO", "CSV", "/NH"],
                         capture_output=True, text=True).stdout
    for ln in out.splitlines():
        if "Joey_Pc.exe" in ln:
            return int(ln.split('","')[1])
    return None

def volcar_mem(pid):
    m = yr.Memoria(pid)
    try:
        est = yr.leer_estado(m)
        tabla = yr.leer_tabla(m)
        ataque = m.leer(yr.DIAL_ATAQUE, 9); invocar = m.leer(yr.DIAL_INVOCAR, 5)
        lp = yr.leer_lp(m)
        flag_ful = m.leer(0xA54DB4, 1)
        print("estado:", est, "| modo ful:", flag_ful.hex() if flag_ful else None)
        print("LP candidatos:", lp)
        print("dial ataque:", ataque.hex() if ataque else None, "| dial invocar:", invocar.hex() if invocar else None)
        print("tabla:", tabla)
    finally:
        m.cerrar()

def main():
    pid = pid_juego()
    if not pid:
        print("el juego no esta en ejecucion"); return 1
    hwnd = control.ventana_de(pid, 5)
    control.HWND_JUEGO[0] = hwnd
    print("pid", pid, "hwnd", hwnd, "titulo", repr(control.titulo(hwnd)) if hwnd else None,
          "cliente", control.rect_cliente(hwnd) if hwnd else None)
    for cmd in " ".join(sys.argv[1:]).split(";"):
        p = cmd.split()
        if not p: continue
        lg.debug("cmd %s", p)
        if p[0] == "shot":
            print("captura:", control.captura(hwnd, p[1] if len(p) > 1 else "shot")[0])
        elif p[0] == "key":
            control.enfocar(hwnd)
            for _ in range(int(p[2]) if len(p) > 2 else 1):
                control.tecla(p[1], pausa=0.35)
        elif p[0] == "click":
            control.enfocar(hwnd)
            control.clic(hwnd, int(p[1]), int(p[2]))
        elif p[0] == "wait":
            time.sleep(float(p[1]))
        elif p[0] == "mem":
            volcar_mem(pid)
        elif p[0] == "foco":
            print("foco:", control.enfocar(hwnd))
    return 0

if __name__ == "__main__":
    sys.exit(main())
