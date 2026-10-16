# Aisla la causa de "DUELO INDIVIDUAL -> Construccion de Deck": juego limpio + una inyeccion + clics.
# Uso: python -I aislar.py nada|diales|tabla|ambos
import os, subprocess, sys, time
sys.path.insert(0, r"D:\Yugi-Reload\launcher"); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import yugi_reload as yr, control, flujo

modo = sys.argv[1]
subprocess.run(["taskkill", "/F", "/IM", "Joey_Pc.exe"], capture_output=True)
time.sleep(1)
p = subprocess.Popen([yr.EXE, "-win", "-speedy"], cwd=yr.APP)
j = flujo.Juego(p); time.sleep(6)
if modo in ("diales", "ambos"):
    print("diales:", yr.aplicar_diales(j.mem, -100, 500))
if modo in ("tabla", "ambos"):
    print("tabla:", yr.escribir_tabla(j.mem, [0, 1, 2, 3, 4] + list(range(100, 135))))
print("menu:", flujo.ir_a_menu_principal(j))
control.clic(j.hwnd, 400, 340); time.sleep(2.0)
print("tras MODO DUELO:", flujo.que_pantalla(j.hwnd, "aislar_%s_1" % modo)[0])
control.clic(j.hwnd, 400, 342); time.sleep(2.5)
print("tras DUELO INDIVIDUAL:", flujo.que_pantalla(j.hwnd, "aislar_%s_2" % modo)[0])
j.cerrar(); p.kill()
