# Fin de cada ciclo de revision (pedido del usuario): las fotos/video ya examinados se borran tambien del PC;
# solo queda el informe de hallazgos (capturas/informes/AAAAMMDD-HHMM.txt, escrito al revisar).
import os, shutil, glob
local = os.path.join(os.path.dirname(os.path.abspath(__file__)), "capturas", "ps5")
antes = sum(len(fs) for _, _, fs in os.walk(local)) if os.path.isdir(local) else 0
shutil.rmtree(local, ignore_errors=True)
os.makedirs(local, exist_ok=True)
print("revision limpiada:", antes, "archivos borrados del PC; informes en", os.path.join(os.path.dirname(local), "informes"))
