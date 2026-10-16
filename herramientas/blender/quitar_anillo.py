# Borra el resto del pedestal que quitar_base.py deja a veces: un anillo delgado y ancho pegado al suelo
# (vertices por debajo de <alto_rel> del alto y mas lejos que <radio> del centro), y apoya el modelo en z=0.
# Uso: blender --background --python quitar_anillo.py -- entrada.glb salida.glb [alto_rel=0.045] [radio=0.6]
import bpy, bmesh, sys
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1:]
entrada, salida = args[0], args[1]
alto_rel = float(args[2]) if len(args) > 2 else 0.045
radio = float(args[3]) if len(args) > 3 else 0.6
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=entrada)
m = next(o for o in bpy.data.objects if o.type == "MESH")
bm = bmesh.new()
bm.from_mesh(m.data)
zs = [v.co.z for v in bm.verts]
z0, alto = min(zs), max(zs) - min(zs)
cx = sum(v.co.x for v in bm.verts) / len(bm.verts)
cy = sum(v.co.y for v in bm.verts) / len(bm.verts)
fuera = [v for v in bm.verts if v.co.z < z0 + alto_rel * alto and ((v.co.x - cx) ** 2 + (v.co.y - cy) ** 2) ** 0.5 > radio]
bmesh.ops.delete(bm, geom=fuera, context="VERTS")
# piezas sueltas que quedaron colgando del anillo: se van tambien (las islas muy chicas)
bm.verts.ensure_lookup_table()
bm.to_mesh(m.data)
bm.free()
zmin = min(v.co.z for v in m.data.vertices)
for v in m.data.vertices:
    v.co.z -= zmin
print("ANILLO QUITADO: %d vertices" % len(fuera))
bpy.ops.export_scene.gltf(filepath=salida, export_format="GLB", export_yup=True)
print("LISTO", salida)
