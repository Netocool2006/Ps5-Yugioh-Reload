# Pinta la forma 3D de Hunyuan (sin textura) con la figura de Gemini, proyectada de frente.
# La orientacion se elige sola: el eje/sentido cuya silueta coincide mejor con la transparencia de la figura.
import os, sys
sys.path.insert(0, r"D:\Yugi-Reload\herramientas\pylib")
sys.stdout.reconfigure(encoding="utf-8")
import numpy as np, trimesh
from PIL import Image

CARTAS = r"D:\Yugi-Reload\remake\recursos\cartas"
M3D = r"D:\Yugi-Reload\nano-banana\modelos3d"

def silueta(p2, n=128):
    lo, hi = p2.min(0), p2.max(0)
    q = ((p2 - lo) / (hi - lo + 1e-9) * (n - 1)).astype(int)
    m = np.zeros((n, n), bool); m[n - 1 - q[:, 1], q[:, 0]] = True     # fila 0 = arriba
    return m

def mascara(img, n=128):
    a = np.asarray(img.split()[-1]) > 40
    ys, xs = np.nonzero(a)
    a = a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    return np.asarray(Image.fromarray(a).resize((n, n), Image.NEAREST)), (xs.min(), ys.min(), xs.max() + 1, ys.max() + 1)

def procesar(carta):
    malla = trimesh.load(os.path.join(M3D, carta, "forma.glb"), force="mesh")
    img = Image.open(os.path.join(CARTAS, carta, "figura.png")).convert("RGBA")
    ref, caja = mascara(img)
    v = malla.vertices
    # Hunyuan entrega Y arriba, pero el frente puede mirar a cualquier lado: se prueba girando sobre Y cada 15 grados
    # y gana la vista cuya silueta (y proporcion) mas se parece a la figura de Gemini
    from scipy.ndimage import binary_closing
    a_img = (caja[2] - caja[0]) / (caja[3] - caja[1])
    mejor = None
    for grados in range(0, 360, 15):
        R = trimesh.transformations.rotation_matrix(np.radians(grados), [0, 1, 0])[:3, :3]
        vr = malla.vertices @ R.T
        p2 = vr[:, :2]
        ext = p2.max(0) - p2.min(0)
        s2 = binary_closing(silueta(p2), iterations=2)
        iou = (s2 & ref).sum() / max((s2 | ref).sum(), 1)
        nota = iou - 0.5 * abs(np.log((ext[0] / ext[1]) / a_img))
        if mejor is None or nota > mejor[0]:
            mejor = (nota, grados, iou)
    nota, grados, iou = mejor
    malla.apply_transform(trimesh.transformations.rotation_matrix(np.radians(grados), [0, 1, 0]))
    v = malla.vertices
    h, vv, sh, sv = 0, 1, 1, 1
    p2 = v[:, :2].copy()
    lo, hi = p2.min(0), p2.max(0)
    t = (p2 - lo) / (hi - lo)
    W, H = img.size
    x0, y0, x1, y1 = caja
    u = (x0 + t[:, 0] * (x1 - x0)) / W
    w = 1.0 - (y0 + (1 - t[:, 1]) * (y1 - y0)) / H                       # V de glTF: 0 abajo
    # fuera la geometria inventada fuera de la silueta (telones/placas que Hunyuan pega detras)
    from scipy.ndimage import binary_dilation
    alfa = binary_dilation(np.asarray(img.split()[-1]) > 40, iterations=12)
    px = np.clip((u * W).astype(int), 0, W - 1); py = np.clip(((1 - w) * H).astype(int), 0, H - 1)
    dentro = alfa[py, px]
    quedan = dentro[malla.faces].any(1)
    antes = len(malla.faces)
    malla.update_faces(quedan); malla.remove_unreferenced_vertices()
    piezas = sorted(malla.split(only_watertight=False), key=lambda m: -len(m.faces))
    malla = trimesh.util.concatenate([m for m in piezas if len(m.faces) > 0.01 * len(piezas[0].faces)])
    v = malla.vertices
    p2 = np.stack([v[:, 0] * sh, v[:, 1]], 1)
    t = (p2 - lo) / (hi - lo)
    u = (x0 + t[:, 0] * (x1 - x0)) / W
    w = 1.0 - (y0 + (1 - t[:, 1]) * (y1 - y0)) / H
    print("  %s: %d -> %d caras (fuera de la silueta: %d)" % (carta, antes, len(malla.faces), antes - quedan.sum()))
    textura = img.convert("RGB")
    # rellena el fondo transparente con el color del borde para que las orillas no salgan negras
    a = np.asarray(img.split()[-1])
    rgb = np.asarray(textura).copy()
    from scipy.ndimage import distance_transform_edt
    _, (iy, ix) = distance_transform_edt(a < 40, return_indices=True)
    rgb = rgb[iy, ix]
    textura = Image.fromarray(rgb)
    mat = trimesh.visual.material.PBRMaterial(baseColorTexture=textura, metallicFactor=0.0, roughnessFactor=0.55)
    malla.visual = trimesh.visual.TextureVisuals(uv=np.stack([u, w], 1), material=mat)
    # ya quedo con Y arriba y el frente hacia +Z
    salida = os.path.join(M3D, carta, "modelo.glb")
    malla.export(salida)
    print("%-14s silueta %.2f  giro %d  caras=%d -> %s" % (carta, iou, grados, len(malla.faces), salida))

if __name__ == "__main__":
    for c in sys.argv[1:] or sorted(os.listdir(M3D)):
        procesar(c)
