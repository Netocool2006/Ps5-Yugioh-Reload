# Deja mate los materiales de un GLB: TRELLIS no escribe metallicFactor y en glTF eso vale 1 (metal), y en el
# juego el pelo sale gris metalico. Pone metallicFactor 0, roughnessFactor <rugosidad> y doubleSided como Meshy.
# Uso: python -I material_mate.py entrada.glb salida.glb [rugosidad=0.8]
import json, struct, sys

entrada, salida = sys.argv[1:3]
rug = float(sys.argv[3]) if len(sys.argv) > 3 else 0.8
b = open(entrada, "rb").read()
n = struct.unpack_from("<I", b, 12)[0]
j = json.loads(b[20:20 + n])
resto = b[20 + n:]  # cabecera y datos del bloque binario, sin cambios
for m in j["materials"]:
    pbr = m.setdefault("pbrMetallicRoughness", {})
    pbr["metallicFactor"] = 0.0
    pbr["roughnessFactor"] = rug
    pbr.pop("metallicRoughnessTexture", None)
    m["doubleSided"] = True
js = json.dumps(j, separators=(",", ":")).encode()
js += b" " * ((-len(js)) % 4)
cab = struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(js) + len(resto)) + struct.pack("<II", len(js), 0x4E4F534A)
open(salida, "wb").write(cab + js + resto)
print("materiales mate:", len(j["materials"]))
