# Busca un valor u16/u32 en la region .data/.bss del juego (0x5EB000-0xA5A000).
# Uso: python -I buscar_valor.py VALOR [VALOR2 ...]  -> direcciones donde aparece cada valor
import os, struct, sys
sys.path.insert(0, r"D:\Yugi-Reload\launcher")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import yugi_reload as yr
from sesion import pid_juego

INI, FIN = 0x5EB000, 0xA5A000
pid = pid_juego()
m = yr.Memoria(pid)
datos = bytearray()
paso = 0x10000
for a in range(INI, FIN, paso):
    b = m.leer(a, min(paso, FIN - a))
    datos += b if b else b"\0" * min(paso, FIN - a)
m.cerrar()
for v in map(int, sys.argv[1:]):
    pat = struct.pack("<H", v)
    hits = [INI + i for i in range(0, len(datos) - 1, 2) if datos[i:i + 2] == pat]
    print("valor %d: %d coincidencias alineadas" % (v, len(hits)))
    print("  " + " ".join("0x%X" % h for h in hits[:60]))
