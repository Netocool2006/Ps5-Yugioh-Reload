# Mide los ojos de un monstruo fijo (para el parpadeo del juego): busca en la cara de adelante (+z) los vertices
# cuyo color de textura es el del ojo (por defecto el morado de la pupila de Kuriboh), los separa en izquierdo y
# derecho e imprime centro y radio de cada uno en coordenadas del modelo (glTF), listos para OJO_KURIBOH_A/B.
# Uso: python -I medir_ojos.py modelo.glb [r,g,b del ojo = 95,55,165] [tolerancia = 70]
import io, json, struct, sys
import numpy as np
from PIL import Image

ruta = sys.argv[1]
ref = np.array([float(v) for v in (sys.argv[2] if len(sys.argv) > 2 else "95,55,165").split(",")]) / 255.0
tol = (float(sys.argv[3]) if len(sys.argv) > 3 else 70.0) / 255.0
b = open(ruta, "rb").read()
n = struct.unpack_from("<I", b, 12)[0]
j = json.loads(b[20:20 + n])
binoff = 20 + n + 8


def vista(i, k):
    a = j["accessors"][i]
    bv = j["bufferViews"][a["bufferView"]]
    return np.frombuffer(b, np.float32, a["count"] * k, binoff + bv.get("byteOffset", 0) + a.get("byteOffset", 0)).reshape(-1, k)


p = j["meshes"][0]["primitives"][0]
pos = vista(p["attributes"]["POSITION"], 3)
uv = vista(p["attributes"]["TEXCOORD_0"], 2)
img = j["images"][j["textures"][j["materials"][p["material"]]["pbrMetallicRoughness"]["baseColorTexture"]["index"]]["source"]]
bv = j["bufferViews"][img["bufferView"]]
tex = np.array(Image.open(io.BytesIO(b[binoff + bv.get("byteOffset", 0):binoff + bv.get("byteOffset", 0) + bv["byteLength"]])).convert("RGB")) / 255.0
H, W, _ = tex.shape
c = tex[np.clip((uv[:, 1] * H).astype(int), 0, H - 1), np.clip((uv[:, 0] * W).astype(int), 0, W - 1)]
frente = pos[:, 2] > np.percentile(pos[:, 2], 60)
ojo = (np.linalg.norm(c - ref, axis=1) < tol) & frente
print("vertices de ojo:", ojo.sum(), "| modelo min", pos.min(0).round(3), "max", pos.max(0).round(3))
for nombre, lado in (("A (x<0)", pos[:, 0] < 0), ("B (x>0)", pos[:, 0] > 0)):
    q = pos[ojo & lado]
    if len(q) < 5:
        print(nombre, "no encontrado")
        continue
    centro = np.median(q, axis=0)
    q = q[np.linalg.norm(q - centro, axis=1) < 3 * np.median(np.linalg.norm(q - centro, axis=1)) + 1e-6]
    centro = q.mean(0)
    radio = np.percentile(np.linalg.norm(q[:, :2] - centro[:2], axis=1), 95)
    print("ojo %s: glm::vec4{ %.4ff, %.4ff, %.4ff, %.3ff }  (%d vertices)" % (nombre, *centro, radio, len(q)))
