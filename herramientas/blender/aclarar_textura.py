# Aclara la textura de color de un GLB (TRELLIS la deja mas oscura que Meshy por la luz horneada): multiplica por
# <ganancia> y levanta las sombras con <gamma> < 1. Uso: blender --background --python aclarar_textura.py --
# entrada.glb salida.glb [ganancia=1.35] [gamma=0.85] [saturacion=1.0]
# (Kuriboh TRELLIS 2026-10-16: 1.8 1.0 1.15 lo igualo al de Meshy en el juego: brillo 0.17 -> 0.31)
import bpy, sys, numpy as np
a = sys.argv[sys.argv.index("--") + 1:]
entrada, salida = a[0], a[1]
g = float(a[2]) if len(a) > 2 else 1.35
gamma = float(a[3]) if len(a) > 3 else 0.85
sat = float(a[4]) if len(a) > 4 else 1.0
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=entrada)
hechas = set()
for m in bpy.data.materials:
    if not m.use_nodes:
        continue
    for n in m.node_tree.nodes:
        if n.type == "TEX_IMAGE" and n.image and n.image.name not in hechas:
            if not any(l.from_node == n and l.to_socket.name == "Base Color" for l in m.node_tree.links):
                continue
            im = n.image
            w, h = im.size
            px = np.array(im.pixels[:], dtype=np.float32).reshape(h, w, 4)
            rgb = px[:, :, :3]
            gris = rgb.mean(2, keepdims=True)
            rgb = gris + (rgb - gris) * sat
            px[:, :, :3] = np.clip(rgb * g, 0, 1) ** gamma
            im.pixels.foreach_set(px.ravel())
            im.pack()
            hechas.add(im.name)
            print("ACLARADA", im.name, w, h)
bpy.ops.export_scene.gltf(filepath=salida, export_format="GLB", export_image_format="JPEG", export_jpeg_quality=92)
print("LISTO", salida)
