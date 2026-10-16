# Oscurece y contrasta la textura de color de un GLB (p. ej. el Dragon Negro de Ojos Rojos que Meshy dejo gris);
# conserva los tonos rojos (ojos). Uso: blender --background --python oscurecer_textura.py -- entrada.glb salida.glb [factor=0.32]
import bpy, sys, numpy as np
a = sys.argv[sys.argv.index("--") + 1:]
entrada, salida = a[0], a[1]
k = float(a[2]) if len(a) > 2 else 0.32
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=entrada)
hechas = set()
for m in bpy.data.materials:
    if not m.use_nodes:
        continue
    for n in m.node_tree.nodes:
        if n.type == "TEX_IMAGE" and n.image and n.image.name not in hechas:
            enlaces = [l for l in m.node_tree.links if l.from_node == n and l.to_socket.name == "Base Color"]
            if not enlaces:
                continue
            im = n.image
            w, h = im.size
            px = np.array(im.pixels[:], dtype=np.float32).reshape(h, w, 4)
            rgb = px[:, :, :3]
            rojo = (rgb[:, :, 0] > rgb[:, :, 1] * 1.6) & (rgb[:, :, 0] > 0.3)
            oscuro = np.clip((rgb * k) ** 1.15, 0, 1)
            rgb[:] = np.where(rojo[:, :, None], rgb, oscuro)
            im.pixels.foreach_set(px.ravel())
            im.pack()
            hechas.add(im.name)
            print("OSCURECIDA", im.name, w, h)
bpy.ops.export_scene.gltf(filepath=salida, export_format="GLB", export_image_format="JPEG", export_jpeg_quality=92)
print("LISTO", salida)
