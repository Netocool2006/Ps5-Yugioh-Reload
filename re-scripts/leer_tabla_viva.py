# Lee la tabla de seleccion de mazos del proceso Joey_Pc.exe en vivo
import ctypes, struct, subprocess, sys
from ctypes import wintypes

salida = subprocess.check_output(["tasklist", "/FI", "IMAGENAME eq Joey_Pc.exe", "/FO", "CSV"]).decode("latin-1")
pid = None
for linea in salida.splitlines()[1:]:
    partes = linea.strip('"').split('","')
    if len(partes) > 1:
        pid = int(partes[1])
if not pid:
    sys.exit("Joey_Pc.exe no esta corriendo")

k32 = ctypes.windll.kernel32
h = k32.OpenProcess(0x0010 | 0x0400, False, pid)  # VM_READ | QUERY
buf = ctypes.create_string_buffer(160)
leido = ctypes.c_size_t()
ok = k32.ReadProcessMemory(h, ctypes.c_void_p(0x5DB158), buf, 160, ctypes.byref(leido))
if not ok:
    sys.exit("ReadProcessMemory fallo: %d" % k32.GetLastError())
vals = struct.unpack("<40I", buf.raw)
print("PID", pid)
for nv in range(1, 8):
    fila = vals[nv*5:(nv+1)*5]
    print("nivel %d: %s %s" % (nv, list(fila), "<- BIBLIOTECA" if any(v >= 100 for v in fila) else "(original)"))
