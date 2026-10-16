# Dragon Negro de Ojos Rojos hecho en Blender desde cero (sin Hunyuan): esqueleto de aristas con el modificador
# Skin + subdivision para el cuerpo, membranas de alas, puas, garras, dientes y ojos; materiales por codigo
# (escamas negras con brillo violeta, membrana roja oscura, ojos rojos) horneados a una textura de 2048.
# Sale nano-banana/modelos3d/red_eyes/modelo_final.glb (frente = glTF +Z, como los demas monstruos).
# Uso: blender --background --python crear_ojos_rojos.py -- [vista_previa.png]
import bpy, bmesh, math, os, sys
from mathutils import Vector, Matrix

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
PREVIA = args[0] if args else None
DIR = r"D:\Yugi-Reload\nano-banana\modelos3d\red_eyes"
TEX = 2048

bpy.ops.wm.read_factory_settings(use_empty=True)
esc = bpy.context.scene
piezas = []


def material(nombre, color, rugosidad=0.5, ruido=0.0, color2=None, escala=40.0, emision=0.0):
    """Material de color con variacion de escamas (ruido + voronoi) entre color y color2."""
    mat = bpy.data.materials.new(nombre)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = rugosidad
    if color2 is None:
        bsdf.inputs["Base Color"].default_value = (*color, 1)
    else:
        coord = nt.nodes.new("ShaderNodeTexCoord")
        vor = nt.nodes.new("ShaderNodeTexVoronoi")
        vor.inputs["Scale"].default_value = escala
        nt.links.new(coord.outputs["Object"], vor.inputs["Vector"])
        ruid = nt.nodes.new("ShaderNodeTexNoise")
        ruid.inputs["Scale"].default_value = escala * 0.15
        nt.links.new(coord.outputs["Object"], ruid.inputs["Vector"])
        mezcla_f = nt.nodes.new("ShaderNodeMath")
        mezcla_f.operation = "MULTIPLY_ADD"
        nt.links.new(vor.outputs["Distance"], mezcla_f.inputs[0])
        mezcla_f.inputs[1].default_value = 1.0 - ruido
        nt.links.new(ruid.outputs["Fac"], mezcla_f.inputs[2])
        rampa = nt.nodes.new("ShaderNodeValToRGB")
        rampa.color_ramp.elements[0].color = (*color, 1)
        rampa.color_ramp.elements[1].color = (*color2, 1)
        nt.links.new(mezcla_f.outputs[0], rampa.inputs["Fac"])
        nt.links.new(rampa.outputs["Color"], bsdf.inputs["Base Color"])
    if emision:
        bsdf.inputs["Emission Color"].default_value = (*color, 1)
        bsdf.inputs["Emission Strength"].default_value = emision
    return mat


ESCAMAS = material("Escamas", (0.012, 0.011, 0.016), 0.3, 0.45, (0.075, 0.065, 0.09), 55.0)
VIENTRE = material("Vientre", (0.05, 0.04, 0.045), 0.45, 0.3, (0.13, 0.1, 0.1), 25.0)
MEMBRANA = material("Membrana", (0.04, 0.006, 0.01), 0.55, 0.5, (0.17, 0.02, 0.03), 6.0)
HUESO = material("Hueso", (0.22, 0.21, 0.23), 0.3, 0.2, (0.45, 0.43, 0.44), 12.0)
OJO = material("Ojo", (1.0, 0.08, 0.03), 0.2, emision=2.0)


def esqueleto(nombre, cadenas, mat, subdiv=2):
    """cadenas: listas de (punto, radio) unidas en orden; puntos repetidos se unen (ramas)."""
    me = bpy.data.meshes.new(nombre)
    bm = bmesh.new()
    vistos = {}
    radios = {}
    for cadena in cadenas:
        prev = None
        for p, r in cadena:
            clave = tuple(round(c, 4) for c in p)
            if clave not in vistos:
                vistos[clave] = bm.verts.new(p)
                radios[clave] = r
            v = vistos[clave]
            if prev is not None and bm.edges.get((prev, v)) is None:
                bm.edges.new((prev, v))
            prev = v
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(nombre, me)
    esc.collection.objects.link(ob)
    skin = ob.modifiers.new("piel", "SKIN")
    sv = me.skin_vertices[0].data
    claves = list(vistos.keys())
    for i, v in enumerate(me.vertices):
        clave = tuple(round(c, 4) for c in v.co)
        r = radios[clave]
        sv[i].radius = (r, r)
    sv[0].use_root = True
    sub = ob.modifiers.new("suave", "SUBSURF")
    sub.levels = subdiv
    sub.render_levels = subdiv
    me.materials.append(mat)
    piezas.append(ob)
    return ob


def cono(nombre, base, punta, radio, mat, vertices=8, curva=0.0):
    """Pua/garra/cuerno: cono de base a punta, curvado hacia 'curva' (desplazamiento de la punta)."""
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=vertices, radius1=radio, radius2=0.0, depth=1.0)
    me = bpy.data.meshes.new(nombre)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(nombre, me)
    esc.collection.objects.link(ob)
    base, punta = Vector(base), Vector(punta)
    eje = punta - base
    ob.location = (base + punta) / 2
    ob.rotation_mode = "QUATERNION"
    ob.rotation_quaternion = eje.to_track_quat("Z", "Y")
    ob.scale = (1, 1, eje.length)
    me.materials.append(mat)
    piezas.append(ob)
    return ob


def esfera(nombre, centro, radios, mat):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=10, location=centro)
    ob = bpy.context.active_object
    ob.name = nombre
    ob.scale = radios
    ob.data.materials.append(mat)
    piezas.append(ob)
    return ob


def espejo(p):
    return (-p[0], p[1], p[2])


# ------------------------------------------------------------------ cuerpo (frente hacia -y, z arriba)
pelvis, pecho = (0, 0.12, 0.95), (0, -0.02, 1.38)
cuello = [(0, -0.08, 1.62), (0, -0.16, 1.86), (0, -0.28, 2.05)]
nuca = (0, -0.38, 2.14)
cadenas = [
    [(pelvis, 0.30), (pecho, 0.27)] + [(c, r) for c, r in zip(cuello, (0.17, 0.14, 0.12))] + [(nuca, 0.12)],
    # cola: baja por detras y se curva hacia un lado
    [(pelvis, 0.30), ((0, 0.45, 0.72), 0.2), ((0.12, 0.85, 0.42), 0.14), ((0.38, 1.15, 0.24), 0.09),
     ((0.72, 1.3, 0.18), 0.05), ((1.02, 1.32, 0.24), 0.02)],
]
for lado in (1, -1):
    s = lambda p: (p[0] * lado, p[1], p[2])
    cadenas += [
        # pierna trasera: cadera, rodilla adelante, tobillo atras, pie adelante
        [(pelvis, 0.30), (s((0.24, 0.1, 0.85)), 0.2), (s((0.36, -0.18, 0.55)), 0.15), (s((0.33, 0.12, 0.2)), 0.09),
         (s((0.35, -0.12, 0.05)), 0.08)],
        # brazo: hombro, codo, mano adelante
        [(pecho, 0.27), (s((0.22, -0.08, 1.36)), 0.12), (s((0.42, -0.24, 1.12)), 0.08), (s((0.36, -0.46, 1.16)), 0.06)],
    ]
cadenas = [[(p, r * 1.18) for p, r in c] for c in cadenas]
cuerpo = esqueleto("Cuerpo", cadenas, ESCAMAS)

# cabeza: craneo alargado hacia adelante y mandibula entreabierta
cabeza = esqueleto("Cabeza", [
    [(nuca, 0.13), ((0, -0.52, 2.16), 0.13), ((0, -0.72, 2.12), 0.09), ((0, -0.9, 2.07), 0.055)],
], ESCAMAS)
mandibula = esqueleto("Mandibula", [
    [((0, -0.42, 2.07), 0.09), ((0, -0.62, 2.0), 0.07), ((0, -0.84, 1.95), 0.04)],
], VIENTRE)
# vientre: placas claras en el frente del pecho y cuello
vientre = esqueleto("Vientre", [
    [((0, -0.2, 1.05), 0.17), ((0, -0.24, 1.35), 0.17), ((0, -0.22, 1.62), 0.11), ((0, -0.3, 1.86), 0.08)],
], VIENTRE)

for lado in (1, -1):
    s = lambda p: (p[0] * lado, p[1], p[2])
    # ojos rojos a los lados del craneo, y cejas con cuernos hacia atras
    esfera("Ojo", s((0.085, -0.6, 2.2)), (0.035, 0.05, 0.025), OJO)
    cono("Ceja", s((0.08, -0.56, 2.24)), s((0.13, -0.38, 2.36)), 0.035, ESCAMAS)
    cono("CuernoA", s((0.08, -0.42, 2.24)), s((0.2, -0.05, 2.5)), 0.05, HUESO)
    cono("CuernoB", s((0.11, -0.4, 2.14)), s((0.3, -0.1, 2.24)), 0.04, HUESO)
    cono("Mejilla", s((0.1, -0.46, 2.06)), s((0.24, -0.3, 1.98)), 0.03, ESCAMAS)
    # dientes
    for k, y in enumerate((-0.86, -0.78, -0.7, -0.62)):
        cono("Diente", s((0.035, y, 2.04)), s((0.04, y - 0.01, 1.98)), 0.012, HUESO, 6)
    # garras de los pies (tres) y de las manos (tres)
    for k in (-1, 0, 1):
        cono("GarraPie", s((0.35 + 0.07 * k, -0.15, 0.05)), s((0.36 + 0.1 * k, -0.33, 0.01)), 0.035, HUESO, 6)
        cono("GarraMano", s((0.36 + 0.035 * k, -0.48, 1.16)), s((0.38 + 0.05 * k, -0.6, 1.08)), 0.018, HUESO, 6)
    # puas de codos y hombros
    cono("PuaCodo", s((0.44, -0.2, 1.12)), s((0.62, -0.05, 1.05)), 0.04, HUESO)
    cono("PuaHombro", s((0.22, 0.02, 1.48)), s((0.42, 0.18, 1.7)), 0.06, HUESO)

    # ------------------------------------------------------------ ala: huesos (Skin) + membrana
    raiz = s((0.16, 0.18, 1.5))
    codo = s((0.55, 0.36, 2.05))
    muneca = s((0.88, 0.34, 2.52))
    dedos = [s((1.38, 0.46, 2.28)), s((1.32, 0.52, 1.78)), s((1.12, 0.48, 1.28)), s((0.78, 0.4, 0.98))]
    esqueleto("AlaHueso", [[(raiz, 0.07), (codo, 0.06), (muneca, 0.05)]] +
              [[(muneca, 0.05), (d, 0.018)] for d in dedos], ESCAMAS, 1)
    cono("PuaAla", muneca, s((1.0, 0.25, 2.8)), 0.05, HUESO)
    # membrana: abanico entre el brazo del ala, los dedos y el lomo, con borde festoneado entre dedos
    bm = bmesh.new()
    vm = bm.verts.new(muneca)
    borde = [codo] + dedos + [s((0.45, 0.32, 1.0)), raiz]
    puntos = []
    for i in range(len(borde) - 1):
        a, b = Vector(borde[i]), Vector(borde[i + 1])
        puntos.append(a)
        if 1 <= i <= len(dedos):
            # festón: el borde se mete hacia la muneca entre dedo y dedo
            medio = (a + b) / 2
            puntos.append(medio + (Vector(muneca) - medio) * 0.28)
    puntos.append(Vector(borde[-1]))
    vs = [bm.verts.new(p) for p in puntos]
    for i in range(len(vs) - 1):
        bm.faces.new((vm, vs[i], vs[i + 1]))
    me = bpy.data.meshes.new("Membrana")
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new("Membrana", me)
    esc.collection.objects.link(ob)
    sub = ob.modifiers.new("suave", "SUBSURF")
    sub.levels = 2
    sol = ob.modifiers.new("grosor", "SOLIDIFY")
    sol.thickness = 0.015
    me.materials.append(MEMBRANA)
    piezas.append(ob)

# puas del lomo y la cola
lomo = [(0, 0.2, 1.1), (0, 0.15, 1.35), (0, 0.06, 1.6), (0, -0.02, 1.84), (0, -0.14, 2.04), (0, 0.42, 0.85),
        (0, 0.72, 0.6), (0.14, 1.0, 0.42), (0.45, 1.23, 0.32)]
for i, p in enumerate(lomo):
    h = 0.18 if i < 5 else 0.13 - 0.02 * (i - 5)
    cono("PuaLomo", p, (p[0], p[1] + h * 0.9, p[2] + h * 0.6), 0.05 if i < 5 else 0.04, HUESO)

# ------------------------------------------------------------------ unir, aplicar y texturizar
bpy.ops.object.select_all(action="DESELECT")
for ob in piezas:
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    for m in list(ob.modifiers):
        bpy.ops.object.modifier_apply(modifier=m.name)
bpy.context.view_layer.objects.active = piezas[0]
bpy.ops.object.join()
dragon = bpy.context.active_object
dragon.name = "red_eyes"
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
for p in dragon.data.polygons:
    p.use_smooth = True
print("DRAGON caras", len(dragon.data.polygons))

dragon.data.uv_layers.new(name="UVMap")
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.uv.smart_project(angle_limit=1.15, island_margin=0.003)
bpy.ops.object.mode_set(mode="OBJECT")

img = bpy.data.images.new("T_red_eyes", TEX, TEX, alpha=False)
for mat in dragon.data.materials:
    nodo = mat.node_tree.nodes.new("ShaderNodeTexImage")
    nodo.image = img
    mat.node_tree.nodes.active = nodo
esc.render.engine = "CYCLES"
esc.cycles.device = "CPU"
esc.cycles.samples = 1
esc.render.bake.margin = 6
bpy.ops.object.bake(type="DIFFUSE", pass_filter={"COLOR"})
os.makedirs(DIR, exist_ok=True)
img.filepath_raw = os.path.join(DIR, "textura_final.png")
img.file_format = "PNG"
img.save()

# un solo material con la textura horneada (el juego solo lee el color base)
final = bpy.data.materials.new("M_red_eyes")
final.use_nodes = True
bsdf = final.node_tree.nodes["Principled BSDF"]
bsdf.inputs["Roughness"].default_value = 0.4
tx = final.node_tree.nodes.new("ShaderNodeTexImage")
tx.image = img
final.node_tree.links.new(tx.outputs["Color"], bsdf.inputs["Base Color"])
dragon.data.materials.clear()
dragon.data.materials.append(final)
ruta = os.path.join(DIR, "modelo_final.glb")
bpy.ops.export_scene.gltf(filepath=ruta, export_format="GLB", export_yup=True, use_selection=False,
                          export_image_format="JPEG", export_jpeg_quality=92)
print("LISTO", ruta, "%.1f MB" % (os.path.getsize(ruta) / 1e6))
