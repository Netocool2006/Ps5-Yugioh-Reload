# Revision exhaustiva de un monstruo en el PC (ciclo oficial, paso 3): 8 angulos a alta resolucion, primeros planos
# de cabeza, manos y del extremo superior (punta del arma), y si el GLB trae animaciones, una hoja de cuadros por
# cada una. Todo sale en <carpeta>/revision/ como PNG; luego revisar_cuadrantes divide cada toma en 4 ampliados.
# Uso: blender --background --python revision_exhaustiva.py -- <modelo.glb> <carpeta_salida> [tam=1200]
import bpy, math, os, sys
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1:]
ruta, salida = args[0], args[1]
TAM = int(args[2]) if len(args) > 2 else 1200
os.makedirs(salida, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
esc = bpy.context.scene
bpy.ops.import_scene.gltf(filepath=ruta)
mallas = [o for o in esc.objects if o.type == "MESH"]
arm = next((o for o in esc.objects if o.type == "ARMATURE"), None)
acciones = sorted(bpy.data.actions, key=lambda a: a.name)


def caja():
    bpy.context.view_layer.update()
    deps = bpy.context.evaluated_depsgraph_get()
    pts = []
    for o in mallas:
        ev = o.evaluated_get(deps)
        me = ev.to_mesh()
        pts += [ev.matrix_world @ me.vertices[i].co for i in range(0, len(me.vertices), 7)]
        ev.to_mesh_clear()
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return lo, hi, pts


cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
esc.collection.objects.link(cam)
cam.data.lens = 50
esc.camera = cam
for rx, rz, e in ((50, -25, 2.6), (60, 155, 1.1), (20, 90, 0.6)):
    sol = bpy.data.objects.new("sol", bpy.data.lights.new("sol", "SUN"))
    sol.data.energy = e
    sol.rotation_euler = (math.radians(rx), 0, math.radians(rz))
    esc.collection.objects.link(sol)
esc.world = bpy.data.worlds.new("mundo")
esc.world.use_nodes = True
esc.world.node_tree.nodes["Background"].inputs[0].default_value = (0.30, 0.30, 0.34, 1)
esc.render.engine = "BLENDER_EEVEE"
esc.render.resolution_x = esc.render.resolution_y = TAM


def foto(nombre, objetivo, radio, angulo, altura=0.15):
    t = math.radians(angulo)
    d = radio / math.tan(math.radians(18))
    cam.location = objetivo + Vector((math.sin(t), -math.cos(t), altura)).normalized() * d
    cam.rotation_euler = (objetivo - cam.location).to_track_quat("-Z", "Y").to_euler()
    esc.render.filepath = os.path.join(salida, nombre + ".png")
    bpy.ops.render.render(write_still=True)


# pose de reposo (primer cuadro de la primera animacion, o sin animacion)
if arm and acciones:
    arm.animation_data.action = acciones[0]
    esc.frame_set(int(acciones[0].frame_range[0]))
lo, hi, pts = caja()
centro, alto = (lo + hi) / 2, hi.z - lo.z
radio = max((hi - lo).length / 2, 1e-3) * 1.05
for a in (0, 45, 90, 135, 180, 225, 270, 315):
    foto("ang_%03d" % a, centro, radio, a)
foto("ang_arriba", centro, radio, 20, altura=1.6)
# primeros planos: cabeza (franja superior), extremo superior (punta del arma o cuernos), manos (franja media)
cabeza = Vector((centro.x, centro.y, lo.z + alto * 0.84))
foto("cerca_cabeza_frente", cabeza, alto * 0.16, 0)
foto("cerca_cabeza_34", cabeza, alto * 0.16, 35)
alto_pt = max(pts, key=lambda p: p.z)
foto("cerca_punta", alto_pt - Vector((0, 0, alto * 0.08)), alto * 0.14, 15)
for lado, nombre in ((-1, "izq"), (1, "der")):
    extremo = max(pts, key=lambda p: lado * p.x if abs(p.z - (lo.z + alto * 0.5)) < alto * 0.3 else -1e9)
    foto("cerca_mano_" + nombre, extremo, alto * 0.13, -30 * lado)
    foto("cerca_mano_%s_atras" % nombre, extremo, alto * 0.13, 180 + 30 * lado)

# hojas de animacion: 8 cuadros por animacion, vista 3/4
if arm:
    esc.render.resolution_x = esc.render.resolution_y = 480
    for acc in acciones:
        arm.animation_data.action = acc
        ini, fin = acc.frame_range
        for k in range(8):
            esc.frame_set(int(round(ini + (fin - ini) * k / 7)))
            foto("anim_%s_%d" % (acc.name, k), centro, radio * 1.15, 30)
print("REVISION", salida, "| animaciones:", [a.name for a in acciones])
