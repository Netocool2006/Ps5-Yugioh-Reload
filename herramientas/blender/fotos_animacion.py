# Hoja de fotos de las animaciones de un personaje (GLB con esqueleto y varias animaciones, p. ej. de Meshy):
# una fila por animacion con N cuadros repartidos en su duracion, vista de tres cuartos.
# Uso: blender --background --python fotos_animacion.py -- <modelo.glb> <salida.png> [cuadros=6] [tam=300]
import bpy, math, os, sys, tempfile
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1:]
ruta, salida = args[0], args[1]
N = int(args[2]) if len(args) > 2 else 6
TAM = int(args[3]) if len(args) > 3 else 300

bpy.ops.wm.read_factory_settings(use_empty=True)
esc = bpy.context.scene
bpy.ops.import_scene.gltf(filepath=ruta)
arm = next(o for o in esc.objects if o.type == "ARMATURE")
acciones = sorted(bpy.data.actions, key=lambda a: a.name)
print("ANIMACIONES", [a.name for a in acciones])

cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
esc.collection.objects.link(cam)
cam.data.type = "ORTHO"
cam.data.ortho_scale = 3.2
esc.camera = cam
t = math.radians(30)
cam.location = Vector((math.sin(t) * 8, -math.cos(t) * 8, 1.6))
cam.rotation_euler = (Vector((0, 0, 0.9)) - cam.location).to_track_quat("-Z", "Y").to_euler()
for rx, rz, e in ((50, -25, 2.5), (60, 155, 1.0)):
    sol = bpy.data.objects.new("sol", bpy.data.lights.new("sol", "SUN"))
    sol.data.energy = e
    sol.rotation_euler = (math.radians(rx), 0, math.radians(rz))
    esc.collection.objects.link(sol)
esc.world = bpy.data.worlds.new("mundo")
esc.world.use_nodes = True
esc.world.node_tree.nodes["Background"].inputs[0].default_value = (0.3, 0.3, 0.34, 1)
esc.render.engine = "BLENDER_EEVEE"
esc.render.resolution_x = esc.render.resolution_y = TAM

hoja = bpy.data.images.new("hoja", TAM * N, TAM * len(acciones))
pix = [0.0] * (TAM * N * TAM * len(acciones) * 4)
if arm.animation_data is None:
    arm.animation_data_create()
for tr in list(arm.animation_data.nla_tracks):
    arm.animation_data.nla_tracks.remove(tr)
for fila, acc in enumerate(acciones):
    arm.animation_data.action = acc
    if hasattr(arm.animation_data, "action_slot") and acc.slots:
        arm.animation_data.action_slot = acc.slots[0]
    ini, fin = acc.frame_range
    for k in range(N):
        esc.frame_set(int(round(ini + (fin - ini) * k / max(N - 1, 1))))
        p = os.path.join(tempfile.gettempdir(), "anim_%d_%d.png" % (fila, k))
        esc.render.filepath = p
        bpy.ops.render.render(write_still=True)
        im = bpy.data.images.load(p)
        src = list(im.pixels)
        fila_y = len(acciones) - 1 - fila   # la primera animacion arriba
        for y in range(TAM):
            ini_px = ((fila_y * TAM + y) * TAM * N + k * TAM) * 4
            pix[ini_px:ini_px + TAM * 4] = src[y * TAM * 4:(y + 1) * TAM * 4]
        bpy.data.images.remove(im)
    print("FILA", fila, acc.name, "cuadros", ini, "-", fin)
hoja.pixels = pix
hoja.filepath_raw = salida
hoja.file_format = "PNG"
hoja.save()
print("HOJA", salida)
