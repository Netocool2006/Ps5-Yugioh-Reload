# Render de revision de un monstruo desde 4 angulos (frente, 3/4, lado, espalda), para ver texturas mal
# proyectadas, huecos o piezas raras. Frente = glTF +Z = Blender -Y.
# Uso: blender --background --python revisar_modelo.py -- salida.png modelo.glb [tamano=520]
import bpy, math, sys
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1:]
salida, ruta = args[0], args[1]
TAM = int(args[2]) if len(args) > 2 else 520
ANGULOS = [0, 40, 90, 180]   # grados alrededor del modelo, 0 = de frente

bpy.ops.wm.read_factory_settings(use_empty=True)
esc = bpy.context.scene
bpy.ops.import_scene.gltf(filepath=ruta)
mallas = [o for o in esc.objects if o.type == "MESH"]
puntos = [o.matrix_world @ Vector(c) for o in mallas for c in o.bound_box]
lo = Vector((min(p.x for p in puntos), min(p.y for p in puntos), min(p.z for p in puntos)))
hi = Vector((max(p.x for p in puntos), max(p.y for p in puntos), max(p.z for p in puntos)))
centro = (lo + hi) / 2
radio = max((hi - lo).length / 2, 1e-3)

cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
esc.collection.objects.link(cam)
cam.data.type = "ORTHO"
cam.data.ortho_scale = radio * 2.1
esc.camera = cam
# luz pareja de frente y arriba, que no esconda nada
for rx, rz, e in ((50, -25, 2.5), (60, 155, 1.2)):
    sol = bpy.data.objects.new("sol", bpy.data.lights.new("sol", "SUN"))
    sol.data.energy = e
    sol.rotation_euler = (math.radians(rx), 0, math.radians(rz))
    esc.collection.objects.link(sol)
esc.world = bpy.data.worlds.new("mundo")
esc.world.use_nodes = True
esc.world.node_tree.nodes["Background"].inputs[0].default_value = (0.32, 0.32, 0.36, 1)
esc.render.engine = "BLENDER_EEVEE"
esc.render.resolution_x = TAM
esc.render.resolution_y = TAM

import os, tempfile
piezas = []
for i, a in enumerate(ANGULOS):
    t = math.radians(a)
    cam.location = centro + Vector((math.sin(t), -math.cos(t), 0.15)).normalized() * radio * 4
    cam.rotation_euler = (centro - cam.location).to_track_quat("-Z", "Y").to_euler()
    p = os.path.join(tempfile.gettempdir(), "revisar_%d.png" % i)
    esc.render.filepath = p
    bpy.ops.render.render(write_still=True)
    piezas.append(p)

# las 4 vistas en una tira
final = bpy.data.images.new("tira", TAM * len(piezas), TAM)
pix = [0.0] * (TAM * len(piezas) * TAM * 4)
for k, p in enumerate(piezas):
    im = bpy.data.images.load(p)
    src = list(im.pixels)
    for y in range(TAM):
        fila = src[y * TAM * 4:(y + 1) * TAM * 4]
        ini = (y * TAM * len(piezas) + k * TAM) * 4
        pix[ini:ini + TAM * 4] = fila
final.pixels = pix
final.filepath_raw = salida
final.file_format = "PNG"
final.save()
print("REVISION", salida)
