# El esqueleto automatico de Meshy reparte el arma entre la mano, el hombro y las piernas (se dobla al moverse).
# Esto reasigna los vertices del arma 100 % al hueso de la mano que la agarra, para que se mueva como un objeto
# rigido. El arma se reconoce por color de textura (p. ej. verde) y por un lado del cuerpo (x > umbral o x < -umbral).
# Escribe el GLB corregido e imprime la punta del arma (posicion de reposo, glTF) para el juego.
# Uso: python -I arma_a_mano.py entrada.glb salida.glb <hueso_mano> <color: verde|gris|y:<hasta>:<desde>> <lado: +|-> [umbral_x=0.12]
# Con hueso "nuevo:<Nombre>" el arma no va a ninguna mano: se crea un hueso propio (hijo de la raiz del esqueleto,
# en reposo con su matriz global = identidad) y el juego lo mueve libremente (p. ej. el baculo agarrado a dos manos,
# con los brazos llevados hasta el por cinematica inversa)
import io, json, struct, sys
import numpy as np
from PIL import Image

entrada, salida, hueso, color, lado = sys.argv[1:6]
umbral = float(sys.argv[6]) if len(sys.argv) > 6 else 0.12
b = bytearray(open(entrada, "rb").read())
n = struct.unpack_from("<I", b, 12)[0]
j = json.loads(bytes(b[20:20 + n]))
binoff = 20 + n + 8
TIPOS = {5126: np.float32, 5125: np.uint32, 5123: np.uint16, 5121: np.uint8}
CANT = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}


def vista(i):
    a = j["accessors"][i]
    bv = j["bufferViews"][a["bufferView"]]
    t = TIPOS[a["componentType"]]
    k = CANT[a["type"]]
    off = binoff + bv.get("byteOffset", 0) + a.get("byteOffset", 0)
    paso = bv.get("byteStride", 0) or np.dtype(t).itemsize * k
    assert paso == np.dtype(t).itemsize * k, "datos intercalados no soportados"
    return np.frombuffer(b, t, a["count"] * k, off).reshape(a["count"], k), off, t, k


p = j["meshes"][0]["primitives"][0]
pos = vista(p["attributes"]["POSITION"])[0]
uv = vista(p["attributes"]["TEXCOORD_0"])[0]
jo, jo_off, jo_t, _ = vista(p["attributes"]["JOINTS_0"])
w, w_off, w_t, _ = vista(p["attributes"]["WEIGHTS_0"])
img = j["images"][0]
bv = j["bufferViews"][img["bufferView"]]
ini = binoff + bv.get("byteOffset", 0)
tex = np.array(Image.open(io.BytesIO(bytes(b[ini:ini + bv["byteLength"]]))).convert("RGB")) / 255.0
H, W, _ = tex.shape
c = tex[np.clip((uv[:, 1] * H).astype(int), 0, H - 1), np.clip((uv[:, 0] * W).astype(int), 0, W - 1)]
if color.startswith("y:"):
    # arma del mismo color que la ropa: se reconoce por sus tramos sueltos, por debajo y por encima del brazo
    # (y:<hasta>:<desde>, en metros del modelo)
    _, y_bajo, y_alto = color.split(":")
    es_color = (pos[:, 1] < float(y_bajo)) | (pos[:, 1] > float(y_alto))
elif color == "verde":
    es_color = (c[:, 1] > c[:, 0] + 0.12) & (c[:, 1] > c[:, 2] + 0.03)
else:  # gris metalico (espadas): poco saturado y claro
    es_color = (c.max(1) - c.min(1) < 0.08) & (c.mean(1) > 0.45)
es_lado = pos[:, 0] > umbral if lado == "+" else pos[:, 0] < -umbral
semilla = es_color & es_lado
if color.startswith("y:"):
    # arma vertical: solo lo que esta cerca de su eje (el pelo o la capa del mismo lado quedan fuera)
    abajo = semilla & (pos[:, 1] < float(y_bajo))
    centro_xz = np.median(pos[abajo][:, [0, 2]], axis=0)
    semilla &= np.linalg.norm(pos[:, [0, 2]] - centro_xz, axis=1) < 0.07
# el arma completa: todo lo que cae dentro de su "cilindro" (eje por analisis de componentes principales de los
# vertices de su color), asi entran tambien las franjas o adornos de otro color del mango
q = pos[semilla]
centro = q.mean(0)
eje = np.linalg.svd(q - centro)[2][0]
t = (q - centro) @ eje
radio_q = np.linalg.norm((q - centro) - np.outer(t, eje), axis=1)
radio = np.percentile(radio_q, 98) + 0.012
tt = (pos - centro) @ eje
dist = np.linalg.norm((pos - centro) - np.outer(tt, eje), axis=1)
arma = (dist <= radio) & (tt >= t.min() - 0.01) & (tt <= t.max() + 0.01)
if color.startswith("y:"):
    # los adornos de los extremos (espirales, pomos) son mas anchos que el palo: radio doble en sus ultimos 15 cm
    extremo = (tt < t.min() + 0.15) | (tt > t.max() - 0.15)
    arma |= extremo & (dist <= 2 * radio) & (tt >= t.min() - 0.04) & (tt <= t.max() + 0.04)
print("eje del arma", eje.round(3), "| radio %.3f m | largo %.2f m" % (radio, t.max() - t.min()))
sk = j["skins"][0]
if hueso.startswith("nuevo:"):
    # hueso nuevo hijo del nodo raiz de la escena; su escala anula la de la raiz -> global identidad en reposo
    raiz = j["scenes"][0]["nodes"][0]
    esc = j["nodes"][raiz].get("scale", [1, 1, 1])
    assert "rotation" not in j["nodes"][raiz] and "translation" not in j["nodes"][raiz], "raiz con giro/traslado"
    j["nodes"].append({"name": hueso[6:], "scale": [1 / e for e in esc]})
    j["nodes"][raiz].setdefault("children", []).append(len(j["nodes"]) - 1)
    # su matriz inversa de enlace (identidad) va al final del bloque binario
    ibm = j["accessors"][sk["inverseBindMatrices"]]
    datos = np.frombuffer(b, np.float32, ibm["count"] * 16, binoff + j["bufferViews"][ibm["bufferView"]].get("byteOffset", 0) + ibm.get("byteOffset", 0))
    nuevo = np.concatenate([datos, np.eye(4, dtype=np.float32).ravel()]).tobytes()
    fin = j["buffers"][0]["byteLength"]
    fin += (-fin) % 4
    j["bufferViews"].append({"buffer": 0, "byteOffset": fin, "byteLength": len(nuevo)})
    ibm2 = dict(ibm, bufferView=len(j["bufferViews"]) - 1, count=ibm["count"] + 1)
    ibm2.pop("byteOffset", None)
    j["accessors"].append(ibm2)
    sk["inverseBindMatrices"] = len(j["accessors"]) - 1
    sk["joints"].append(len(j["nodes"]) - 1)
    agregado = (fin, nuevo)
else:
    agregado = None
nombres = [j["nodes"][i]["name"] for i in sk["joints"]]
h = nombres.index(hueso[6:] if agregado else hueso)
jo2 = np.array(jo, copy=True)
w2 = np.array(w, copy=True)
jo2[arma] = [h, 0, 0, 0]
w2[arma] = [1, 0, 0, 0]
b[jo_off:jo_off + jo2.nbytes] = jo2.astype(jo_t).tobytes()
b[w_off:w_off + w2.nbytes] = w2.astype(w_t).tobytes()
if agregado:
    binario = bytearray(b[binoff:binoff + struct.unpack_from("<I", b, 20 + n)[0]])
    fin, nuevo = agregado
    binario = binario[:fin] + bytes(fin - len(binario[:fin])) + nuevo
    binario += bytes((-len(binario)) % 4)
    j["buffers"][0]["byteLength"] = len(binario)
    js = json.dumps(j, separators=(",", ":")).encode()
    js += b" " * ((-len(js)) % 4)
    b = bytearray(struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(js) + 8 + len(binario)) +
                  struct.pack("<II", len(js), 0x4E4F534A) + js + struct.pack("<II", len(binario), 0x004E4942) + binario)
open(salida, "wb").write(b)
pa = pos[arma]
punta = pa[pa[:, 1].argmax()]
print("arma: %d vertices reasignados a %s | punta (reposo glTF) = (%.4f, %.4f, %.4f)" % (arma.sum(), hueso, *punta))
pie = pa[pa[:, 1].argmin()]
print("otro extremo (reposo glTF) = (%.4f, %.4f, %.4f)" % tuple(pie))
