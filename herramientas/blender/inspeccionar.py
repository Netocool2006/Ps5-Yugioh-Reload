# Uso: blender --background --python inspeccionar.py -- modelo.glb
import bpy, sys
ruta = sys.argv[sys.argv.index("--") + 1]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=ruta)
for o in bpy.context.scene.objects:
    if o.type != "MESH": print("OBJ", o.name, o.type); continue
    m = o.data
    print("MALLA", o.name, "verts", len(m.vertices), "caras", len(m.polygons), "uv", [u.name for u in m.uv_layers],
          "colores", [c.name for c in m.color_attributes], "dims", tuple(round(x, 3) for x in o.dimensions))
    for s in o.material_slots:
        mt = s.material
        imgs = [n.image.name + " %dx%d" % tuple(n.image.size) for n in mt.node_tree.nodes if n.type == "TEX_IMAGE" and n.image] if mt and mt.use_nodes else []
        print("  MAT", mt.name if mt else None, imgs)
