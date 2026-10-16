# Quita la tapa del pedestal que queda entre los pies de una figura (Meshy desde figura.png): los triangulos que
# tocan vertices de color gris oscuro por debajo de <alto_rel> del alto se anulan (sus 3 indices iguales), sin
# cambiar el tamano del archivo. Uso: python -I quitar_tapa_gris.py entrada.glb salida.glb [alto_rel=0.04]
import io, json, struct, sys
import numpy as np
from PIL import Image

entrada, salida = sys.argv[1:3]
alto_rel = float(sys.argv[3]) if len(sys.argv) > 3 else 0.04
b = bytearray(open(entrada, "rb").read())
n = struct.unpack_from("<I", b, 12)[0]
j = json.loads(bytes(b[20:20 + n]))
off = 20 + n + 8
TIPOS = {5126: np.float32, 5125: np.uint32, 5123: np.uint16}


def vista(i, k):
    a = j["accessors"][i]
    bv = j["bufferViews"][a["bufferView"]]
    t = TIPOS[a["componentType"]]
    o = off + bv.get("byteOffset", 0) + a.get("byteOffset", 0)
    return np.frombuffer(bytes(b), t, a["count"] * k, o).reshape(-1, k), o, t


p = j["meshes"][0]["primitives"][0]
pos = vista(p["attributes"]["POSITION"], 3)[0]
uv = vista(p["attributes"]["TEXCOORD_0"], 2)[0]
ind, ind_off, ind_t = vista(p["indices"], 1)
img = j["images"][j["textures"][j["materials"][p["material"]]["pbrMetallicRoughness"]["baseColorTexture"]["index"]]["source"]]
bv = j["bufferViews"][img["bufferView"]]
tex = np.array(Image.open(io.BytesIO(bytes(b[off + bv.get("byteOffset", 0):off + bv.get("byteOffset", 0) + bv["byteLength"]]))).convert("RGB")) / 255.0
H, W, _ = tex.shape
c = tex[np.clip((uv[:, 1] * H).astype(int), 0, H - 1), np.clip((uv[:, 0] * W).astype(int), 0, W - 1)]
y0, alto = pos[:, 1].min(), pos[:, 1].max() - pos[:, 1].min()
gris = (pos[:, 1] < y0 + alto_rel * alto) & (c.max(1) - c.min(1) < 0.08) & (c.mean(1) < 0.35)
tri = ind.reshape(-1, 3).copy()
malos = gris[tri].any(1)
tri[malos] = tri[malos][:, :1]
b[ind_off:ind_off + tri.nbytes] = tri.astype(ind_t).tobytes()
open(salida, "wb").write(b)
print("tapa gris: %d vertices, %d triangulos anulados de %d" % (gris.sum(), malos.sum(), len(tri)))
