# Resumen del avance de la cola de Gemini (para el usuario).
import json, os, sys
sys.stdout.reconfigure(encoding="utf-8")
NB = r"D:\Yugi-Reload\nano-banana"
TODO = os.path.join(NB, "todo")

def contar(carpeta):
    if not os.path.isdir(carpeta): return 0, 0, 0
    subs = [os.path.join(carpeta, s) for s in os.listdir(carpeta) if os.path.isdir(os.path.join(carpeta, s))]
    hechos = sum(os.path.exists(os.path.join(s, "resultado.png")) for s in subs)
    fallos = sum(os.path.exists(os.path.join(s, "fallo.txt")) or
                 (os.path.exists(os.path.join(s, "rechazo.txt")) and not os.path.exists(os.path.join(s, "resultado.png"))) for s in subs)
    return hechos, fallos, len(subs)

try:
    e = json.load(open(os.path.join(TODO, "estado.json"), encoding="utf-8"))
except Exception:
    e = {}
print("=== Conversion con Gemini ===")
print("Estado: %s   (actualizado %s)" % (e.get("estado", "?"), e.get("actualizado", "?")))
if e.get("estado") == "pausada por limite":
    print("En pausa desde %s: se reintenta sola cada 30 minutos." % e.get("desde", "?"))
print("Posicion en la cola: %s de %s   (grupo: %s)" % (e.get("posicion", "?"), e.get("total", "?"), e.get("grupo", "?")))
print()
for nombre, carpeta, total in (("Ilustraciones de cartas", os.path.join(TODO, "arte"), 697),
                               ("Figuras 3D de monstruos", os.path.join(TODO, "figura"), 452),
                               ("Resto del juego (espanol)", os.path.join(TODO, "ui"), 985)):
    h, f, _ = contar(carpeta)
    print("%-28s %4d / %d convertidas   (%d fallidas)" % (nombre, h, total, f))
print()
import re
rech = []
for g in ("arte", "figura", "ui"):
    base = os.path.join(TODO, g)
    if not os.path.isdir(base): continue
    for d in sorted(os.listdir(base)):
        c = os.path.join(base, d)
        if os.path.exists(os.path.join(c, "rechazo.txt")):
            try: nombre = re.search(r'"([^"]+)"', open(os.path.join(c, "prompt.txt"), encoding="utf-8").read()).group(1)
            except Exception: nombre = "?"
            if os.path.exists(os.path.join(c, "resultado.png")): estado = "recuperada con prompt neutro"
            elif os.path.exists(os.path.join(c, "rechazo2.txt")): estado = "rechazada dos veces"
            else: estado = "se reintenta al final de la cola"
            rech.append("  %-7s %-8s %-34s %s" % (g, d, nombre, estado))
print("Rechazadas por Gemini (derechos de terceros): %d" % len(rech))
for r in rech: print(r)
print()
print("Ultimos eventos:")
try:
    lineas = [l for l in open(os.path.join(TODO, "cola.log"), encoding="utf-8") if "EVENTO" in l]
    for l in lineas[-8:]:
        print("  " + l.strip()[:150])
except Exception:
    pass
