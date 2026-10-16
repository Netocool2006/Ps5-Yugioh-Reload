# Render de comprobacion de uno o varios .glb lado a lado (frente = glTF +Z = Blender -Y).
# Uso: blender --background --python vista_previa.py -- salida.png modelo1.glb [modelo2.glb ...]
import bpy, math, sys
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1:]
salida, modelos = args[0], args[1:]
bpy.ops.wm.read_factory_settings(use_empty=True)
esc = bpy.context.scene
x = 0.0
for ruta in modelos:
    antes = set(esc.objects)
    bpy.ops.import_scene.gltf(filepath=ruta)
    nuevos = [o for o in esc.objects if o not in antes and o.type == "MESH"]
    puntos = [o.matrix_world @ Vector(c) for o in nuevos for c in o.bound_box]
    lo = Vector((min(p.x for p in puntos), min(p.y for p in puntos), min(p.z for p in puntos)))
    hi = Vector((max(p.x for p in puntos), max(p.y for p in puntos), max(p.z for p in puntos)))
    s = 2.0 / max(hi.z - lo.z, 1e-6)
    raiz = [o for o in esc.objects if o not in antes and o.parent is None]
    for o in raiz:
        o.scale = o.scale * s
        o.location = (o.location - Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z))) * s + Vector((x, 0, 0))
    x += 2.6
ancho = x - 2.6
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
esc.collection.objects.link(cam)
cam.data.type = "ORTHO"
cam.data.ortho_scale = max(ancho + 2.4, 2.6)
cam.location = (ancho / 2, -10, 1.0)
cam.rotation_euler = (math.radians(90), 0, 0)
esc.camera = cam
sol = bpy.data.objects.new("sol", bpy.data.lights.new("sol", "SUN"))
sol.data.energy = 3.0
sol.rotation_euler = (math.radians(50), math.radians(10), math.radians(-25))
esc.collection.objects.link(sol)
esc.world = bpy.data.worlds.new("mundo")
esc.world.use_nodes = True
esc.world.node_tree.nodes["Background"].inputs[0].default_value = (0.35, 0.35, 0.4, 1)
esc.render.engine = "BLENDER_EEVEE"
esc.render.resolution_x = int(560 * len(modelos))
esc.render.resolution_y = 600
esc.render.filepath = salida
bpy.ops.render.render(write_still=True)
print("PREVIA", salida)
