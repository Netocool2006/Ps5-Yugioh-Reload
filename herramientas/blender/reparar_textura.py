# Arregla la textura de un monstruo optimizado (modelos3d/<carta>/modelo_opt.glb). La textura vino de proyectar
# la imagen de Gemini SOLO de frente: la espalda y los costados escondidos repiten el frente (caras pegadas en la
# espalda, colores estirados). Este script:
#  1. marca que partes de la malla se veian desde el frente (el primer impacto de un rayo desde la camara);
#  2. a las que no se veian les pone el color de sus vecinas visibles, difundido por la malla (sin caras atras);
#  3. opcional --espejo: copia una zona reflejada (p. ej. el ojo que falta) desde el otro lado de la cara;
#  4. hornea todo en una textura nueva y exporta modelos3d/<carta>/modelo_final.glb (el original no se toca).
# Uso: blender --background --python reparar_textura.py -- <carta> [--espejo x0 cx cy cz radio] [--tex 2048]
#   --espejo: plano de simetria x = x0 y centro/radio (coordenadas del modelo, glTF: x, y arriba, z al frente)
#   de la zona a rellenar con su reflejo.
#   --ojo ex ez rx rz x2: copia el ojo visto de frente en (ex, ez) (Blender: x, z; semiancho rx, semialto rz)
#   al punto x2 a la misma altura, con la pupila mirando igual: el segundo ojo que Gemini dejo escondido.
#   Un sexto valor opcional escala el ojo copiado (el ojo lejano se ve mas chico).
import bpy, bmesh, math, os, sys, time
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

args = sys.argv[sys.argv.index("--") + 1:]
CARTA = args[0]
DIR = os.path.join(r"D:\Yugi-Reload\nano-banana\modelos3d", CARTA)
TEX = int(args[args.index("--tex") + 1]) if "--tex" in args else 2048
ESPEJO = [float(v) for v in args[args.index("--espejo") + 1:args.index("--espejo") + 6]] if "--espejo" in args else None
OJO = [float(v) for v in args[args.index("--ojo") + 1:args.index("--ojo") + 7]] if "--ojo" in args else None
t0 = time.time()


def log(*a):
    print("REP", "%5.1fs" % (time.time() - t0), *a, flush=True)


bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=os.path.join(DIR, "modelo_opt.glb"))
ob = next(o for o in bpy.context.scene.objects if o.type == "MESH")
for o in list(bpy.context.scene.objects):
    if o is not ob:
        bpy.data.objects.remove(o)
# el importador deja los datos en coordenadas de Blender (z arriba, el frente hacia -y) y la matriz en identidad
ob.parent = None
ob.matrix_world.identity()
me = ob.data
img = next(n.image for n in ob.active_material.node_tree.nodes if n.type == "TEX_IMAGE")
W, H = img.size
tex = np.array(img.pixels[:], dtype=np.float32).reshape(H, W, 4)[:, :, :3]
log("malla", len(me.vertices), "vertices | textura", W, "x", H)

# color de cada vertice: promedio de la textura en sus esquinas (loops)
nv = len(me.vertices)
uv = np.zeros((len(me.loops), 2), dtype=np.float32)
me.uv_layers.active.data.foreach_get("uv", uv.ravel())
lv = np.zeros(len(me.loops), dtype=np.int64)
me.loops.foreach_get("vertex_index", lv)
px = np.clip((uv[:, 0] * W).astype(int), 0, W - 1)
py = np.clip((uv[:, 1] * H).astype(int), 0, H - 1)
col_loop = tex[py, px]
col = np.zeros((nv, 3), dtype=np.float32)
cnt = np.zeros(nv, dtype=np.float32)
np.add.at(col, lv, col_loop)
np.add.at(cnt, lv, 1)
col /= np.maximum(cnt, 1)[:, None]

# visible desde el frente: normal hacia -y y nada delante al lanzar un rayo hacia -y
co = np.zeros((nv, 3), dtype=np.float32)
me.vertices.foreach_get("co", co.ravel())
nor = np.zeros((nv, 3), dtype=np.float32)
me.vertices.foreach_get("normal", nor.ravel())
bm = bmesh.new()
bm.from_mesh(me)
arbol = BVHTree.FromBMesh(bm)
tam = float(np.linalg.norm(co.max(0) - co.min(0)))
visible = np.zeros(nv, dtype=np.float32)
for i in range(nv):
    if nor[i, 1] > -0.05:
        continue
    origen = Vector(co[i]) + Vector((0, -1, 0)) * tam * 1e-3
    golpe = arbol.ray_cast(origen, Vector((0, -1, 0)), tam * 3)
    if golpe[0] is None:
        visible[i] = 1.0
log("visibles desde el frente", int(visible.sum()), "de", nv)

# vecinos por aristas
ed = np.zeros((len(me.edges), 2), dtype=np.int64)
me.edges.foreach_get("vertices", ed.ravel())
a, b = ed[:, 0], ed[:, 1]
grado = np.zeros(nv, dtype=np.float32)
np.add.at(grado, a, 1)
np.add.at(grado, b, 1)


def promedio_vecinos(valores):
    s = np.zeros_like(valores)
    np.add.at(s, a, valores[b])
    np.add.at(s, b, valores[a])
    return s / np.maximum(grado, 1)[:, None] if valores.ndim == 2 else s / np.maximum(grado, 1)


# mascara suave: 1 en lo visible, 0 en lo escondido, con una transicion corta solo en el limite
mascara = visible.copy()
for _ in range(2):
    mascara = 0.5 * mascara + 0.5 * promedio_vecinos(mascara)
mascara = np.clip((mascara - 0.15) / 0.5, 0.0, 1.0)

# relleno: cada punto escondido toma el color de los 12 puntos visibles mas cercanos en el espacio (asi llega
# tambien a las piezas sueltas, como los mechones de pelo); despues se suaviza un poco solo lo escondido
from mathutils.kdtree import KDTree
vis_idx = np.nonzero(visible > 0)[0]
kd = KDTree(len(vis_idx))
for k, i in enumerate(vis_idx):
    kd.insert(Vector(co[i]), k)
kd.balance()
relleno = col.copy()
for i in np.nonzero(visible < 0.5)[0]:
    cerca = kd.find_n(Vector(co[i]), 12)
    w = np.array([1.0 / (d + tam * 0.01) for _, _, d in cerca], dtype=np.float32)
    c = np.array([col[vis_idx[k]] for _, k, _ in cerca], dtype=np.float32)
    relleno[i] = (c * w[:, None]).sum(0) / w.sum()
escondido = visible < 0.5
for _ in range(8):
    suave = promedio_vecinos(relleno)
    relleno[escondido] = 0.5 * relleno[escondido] + 0.5 * suave[escondido]
# promediar apaga el color: se le devuelve saturacion, y un poco mas oscuro atras (sin la luz del frente)
lum = relleno @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
relleno[escondido] = np.clip(lum[escondido, None] + (relleno[escondido] - lum[escondido, None]) * 1.35, 0, 1) * 0.9
log("relleno difundido")

for nombre, datos in (("relleno", relleno), ("mascara", np.repeat(mascara[:, None], 3, 1))):
    at = me.color_attributes.new(nombre, "FLOAT_COLOR", "POINT")
    rgba = np.concatenate([datos, np.ones((nv, 1), dtype=np.float32)], 1)
    at.data.foreach_set("color", rgba.astype(np.float32).ravel())

# material de horneado: textura original donde se veia, relleno donde no
mat = ob.active_material
nt = mat.node_tree
nodo_tex = next(n for n in nt.nodes if n.type == "TEX_IMAGE")
salida = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
att_r = nt.nodes.new("ShaderNodeVertexColor")
att_r.layer_name = "relleno"
att_m = nt.nodes.new("ShaderNodeVertexColor")
att_m.layer_name = "mascara"
mezcla = nt.nodes.new("ShaderNodeMix")
mezcla.data_type = "RGBA"
nt.links.new(att_m.outputs["Color"], mezcla.inputs["Factor"])
nt.links.new(att_r.outputs["Color"], mezcla.inputs[6])        # A: relleno
nt.links.new(nodo_tex.outputs["Color"], mezcla.inputs[7])     # B: textura
emision = nt.nodes.new("ShaderNodeEmission")
nt.links.new(mezcla.outputs[2], emision.inputs["Color"])
nt.links.new(emision.outputs["Emission"], salida.inputs["Surface"])

nueva = bpy.data.images.new("T_" + CARTA + "_final", TEX, TEX, alpha=False)
destino = nt.nodes.new("ShaderNodeTexImage")
destino.image = nueva
nt.nodes.active = destino
esc = bpy.context.scene
esc.render.engine = "CYCLES"
esc.cycles.device = "CPU"
esc.cycles.samples = 1
esc.render.bake.margin = 8
for o in esc.objects:
    o.select_set(o is ob)
bpy.context.view_layer.objects.active = ob
bpy.ops.object.bake(type="EMIT")
log("horneado", TEX, "x", TEX)
base = np.array(nueva.pixels[:], dtype=np.float32).reshape(TEX, TEX, 4)

if ESPEJO:
    # zona reflejada: una copia espejada en x = x0 se hornea sobre el original, y se mezcla solo en la esfera
    x0, cx, cy, cz, radio = ESPEJO
    espejo = ob.copy()
    espejo.data = ob.data.copy()
    esc.collection.objects.link(espejo)
    espejo.data.materials.clear()
    m2 = mat.copy()
    espejo.data.materials.append(m2)
    espejo.location = (2 * x0, 0, 0)
    espejo.scale = (-1, 1, 1)
    bpy.context.view_layer.update()
    for o in esc.objects:
        o.select_set(True)
    bpy.context.view_layer.objects.active = ob
    esc.render.bake.use_selected_to_active = True
    esc.render.bake.cage_extrusion = 0.02 * tam
    esc.render.bake.max_ray_distance = 0.05 * tam
    bpy.ops.object.bake(type="EMIT")
    reflejo = np.array(nueva.pixels[:], dtype=np.float32).reshape(TEX, TEX, 4)
    # mascara de la esfera, horneada con la posicion de cada punto de la superficie
    esc.render.bake.use_selected_to_active = False
    for o in esc.objects:
        o.select_set(o is ob)
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    dist = nt.nodes.new("ShaderNodeVectorMath")
    dist.operation = "DISTANCE"
    dist.inputs[1].default_value = (cx, -cz, cy)  # glTF -> Blender
    rango = nt.nodes.new("ShaderNodeMapRange")
    rango.inputs["From Min"].default_value = radio * 0.7
    rango.inputs["From Max"].default_value = radio
    rango.inputs["To Min"].default_value = 1.0
    rango.inputs["To Max"].default_value = 0.0
    nt.links.new(geo.outputs["Position"], dist.inputs[0])
    nt.links.new(dist.outputs["Value"], rango.inputs["Value"])
    nt.links.new(rango.outputs["Result"], emision.inputs["Color"])
    bpy.ops.object.bake(type="EMIT")
    zona = np.array(nueva.pixels[:], dtype=np.float32).reshape(TEX, TEX, 4)[:, :, :1]
    base = base * (1 - zona) + reflejo * zona
    base[:, :, 3] = 1.0
    bpy.data.objects.remove(espejo)
    log("zona reflejada en x =", x0, "alrededor de", (cx, cy, cz), "radio", radio)

if OJO:
    ex, ez, rx, rz, x2 = OJO[:5]
    k = OJO[5] if len(OJO) > 5 else 1.0  # tamano del ojo copiado respecto al original
    # el parche: el ojo existente visto de frente (rayos desde -y), con el doble de margen
    from mathutils.geometry import barycentric_transform
    bm.faces.ensure_lookup_table()
    tri = bm.copy()
    bmesh.ops.triangulate(tri, faces=tri.faces[:])
    tri.faces.ensure_lookup_table()
    uvl = tri.loops.layers.uv.active
    arbol_t = BVHTree.FromBMesh(tri)
    N = 256
    parche = np.zeros((N, N, 4), dtype=np.float32)
    parche[:, :, 3] = 1.0
    for j in range(N):
        for i in range(N):
            x = ex - 2 * rx + 4 * rx * (i + 0.5) / N
            z = ez - 2 * rz + 4 * rz * (j + 0.5) / N
            loc, _, fi, _ = arbol_t.ray_cast(Vector((x, -tam * 3, z)), Vector((0, 1, 0)), tam * 6)
            if loc is None:
                continue
            f = tri.faces[fi]
            p3 = [l.vert.co for l in f.loops]
            pu = [Vector((*l[uvl].uv, 0)) for l in f.loops]
            u = barycentric_transform(loc, *p3, *pu)
            parche[j, i, :3] = tex[min(H - 1, max(0, int(u.y * H))), min(W - 1, max(0, int(u.x * W)))]
    imp = bpy.data.images.new("parche_ojo", N, N)
    imp.pixels.foreach_set(parche.ravel())
    imp.pack()
    # se proyecta de frente (a lo largo de y), sin reflejar (reflejado, las pupilas se cruzaban), en (x2, ez)
    for n in list(nt.nodes):
        if n not in (salida, emision, destino):
            nt.nodes.remove(n)
    nt.nodes.active = destino
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(geo.outputs["Position"], sep.inputs[0])

    def operar(op, a_, b_):
        n = nt.nodes.new("ShaderNodeMath")
        n.operation = op
        for k, v in enumerate((a_, b_)):
            if isinstance(v, float):
                n.inputs[k].default_value = v
            else:
                nt.links.new(v, n.inputs[k])
        return n.outputs[0]

    u = operar("ADD", operar("DIVIDE", operar("SUBTRACT", sep.outputs["X"], x2), 4 * rx * k), 0.5)
    v = operar("ADD", operar("DIVIDE", operar("SUBTRACT", sep.outputs["Z"], ez), 4 * rz * k), 0.5)
    comb = nt.nodes.new("ShaderNodeCombineXYZ")
    nt.links.new(u, comb.inputs["X"])
    nt.links.new(v, comb.inputs["Y"])
    tp = nt.nodes.new("ShaderNodeTexImage")
    tp.image = imp
    tp.extension = "EXTEND"
    nt.links.new(comb.outputs[0], tp.inputs["Vector"])
    nt.links.new(tp.outputs["Color"], emision.inputs["Color"])
    bpy.ops.object.bake(type="EMIT")
    color_ojo = np.array(nueva.pixels[:], dtype=np.float32).reshape(TEX, TEX, 4)
    # mascara: elipse suave alrededor de (x2, ez), solo en caras que miran a la camara (normal hacia -y)
    du = operar("DIVIDE", operar("SUBTRACT", sep.outputs["X"], x2), rx * 1.5 * k)
    dv = operar("DIVIDE", operar("SUBTRACT", sep.outputs["Z"], ez), rz * 1.5 * k)
    r2 = operar("ADD", operar("MULTIPLY", du, du), operar("MULTIPLY", dv, dv))
    borde = nt.nodes.new("ShaderNodeMapRange")
    borde.inputs["From Min"].default_value = 0.55
    borde.inputs["From Max"].default_value = 1.0
    borde.inputs["To Min"].default_value = 1.0
    borde.inputs["To Max"].default_value = 0.0
    nt.links.new(r2, borde.inputs["Value"])
    sepn = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(geo.outputs["Normal"], sepn.inputs[0])
    frente = nt.nodes.new("ShaderNodeMapRange")
    frente.inputs["From Min"].default_value = 0.0
    frente.inputs["From Max"].default_value = -0.3
    nt.links.new(sepn.outputs["Y"], frente.inputs["Value"])
    nt.links.new(operar("MULTIPLY", borde.outputs["Result"], frente.outputs["Result"]), emision.inputs["Color"])
    bpy.ops.object.bake(type="EMIT")
    zona = np.array(nueva.pixels[:], dtype=np.float32).reshape(TEX, TEX, 4)[:, :, :1]
    log("ojo: zona max %.3f, texeles >0.5: %d, parche medio %s" % (float(zona.max()), int((zona > 0.5).sum()), parche[:, :, :3].mean((0, 1))))
    base = base * (1 - zona) + color_ojo * zona
    base[:, :, 3] = 1.0
    log("segundo ojo: copia de (%.3f, %.3f) en x = %.3f" % (ex, ez, x2))

nueva.pixels.foreach_set(base.ravel())
nueva.filepath_raw = os.path.join(DIR, "textura_final.png")
nueva.file_format = "PNG"
nueva.save()

# material final como el original (base color + rugosidad 0.55), sin atributos de horneado
for n in list(nt.nodes):
    if n.type not in ("BSDF_PRINCIPLED", "OUTPUT_MATERIAL"):
        nt.nodes.remove(n)
bsdf = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None) or nt.nodes.new("ShaderNodeBsdfPrincipled")
bsdf.inputs["Roughness"].default_value = 0.55
bsdf.inputs["Metallic"].default_value = 0.0
tx = nt.nodes.new("ShaderNodeTexImage")
tx.image = nueva
nt.links.new(tx.outputs["Color"], bsdf.inputs["Base Color"])
nt.links.new(bsdf.outputs["BSDF"], salida.inputs["Surface"])
for nombre in ("relleno", "mascara"):
    me.color_attributes.remove(me.color_attributes[nombre])
ruta = os.path.join(DIR, "modelo_final.glb")
bpy.ops.export_scene.gltf(filepath=ruta, export_format="GLB", export_yup=True, use_selection=False,
                          export_image_format="JPEG", export_jpeg_quality=92)
log("listo", ruta, "%.1f MB" % (os.path.getsize(ruta) / 1e6))
