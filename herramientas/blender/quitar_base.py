# Quita la base/pedestal redondo de una figura (los modelos hechos desde figura.png la traen): busca desde abajo
# la altura donde la seccion deja de ser el disco ancho (empiezan los pies), borra todo lo de abajo y apoya el
# modelo en z=0. Uso: blender --background --python quitar_base.py -- entrada.glb salida.glb
import bpy, bmesh, sys
from mathutils import Vector

a = sys.argv[sys.argv.index("--") + 1:]
entrada, salida = a[0], a[1]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=entrada)
ob = next(o for o in bpy.context.scene.objects if o.type == "MESH")
bpy.context.view_layer.objects.active = ob
ob.select_set(True)
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
me = ob.data
zs = [v.co.z for v in me.vertices]
lo, hi = min(zs), max(zs)
alto = hi - lo
N = 200
radios = []
for k in range(N):
    z0, z1 = lo + alto * k / N, lo + alto * (k + 1) / N
    pts = [v.co for v in me.vertices if z0 <= v.co.z < z1]
    if not pts:
        radios.append(0.0)
        continue
    cx = sum(p.x for p in pts) / len(pts)
    cy = sum(p.y for p in pts) / len(pts)
    radios.append(max(((p.x - cx) ** 2 + (p.y - cy) ** 2) ** 0.5 for p in pts))
disco = max(radios[:N // 10])
corte = None
for k in range(1, N // 4):
    if radios[k] < disco * 0.55 and radios[k - 1] >= disco * 0.55:
        corte = lo + alto * (k + 0.5) / N
        break
if corte is None:
    print("SIN BASE: no se encontro un disco abajo; se deja igual")
else:
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z < corte], context="VERTS")
    bm.to_mesh(me)
    bm.free()
    nuevo = min(v.co.z for v in me.vertices)
    for v in me.vertices:
        v.co.z -= nuevo
    print("BASE QUITADA: corte a %.1f%% del alto" % (100 * (corte - lo) / alto))
bpy.ops.export_scene.gltf(filepath=salida, export_format="GLB", export_image_format="JPEG", export_jpeg_quality=92)
print("LISTO", salida)
