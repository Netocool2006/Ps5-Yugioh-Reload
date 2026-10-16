# Optimiza un modelo de Hunyuan3D ya pintado (modelos3d/<carta>/modelo.glb) para Unreal y PS5:
# limpia restos sueltos, baja los triangulos, hace UVs nuevas y hornea la textura de la malla original
# sobre la nueva. Sale modelos3d/<carta>/modelo_opt.glb con la misma orientacion (frente = glTF +Z).
# Uso: blender --background --python optimizar_modelo.py -- <carta> [triangulos=30000] [textura=2048]
import bpy, bmesh, os, sys, time

args = sys.argv[sys.argv.index("--") + 1:]
CARTA = args[0]
TRIS = int(args[1]) if len(args) > 1 else 30000
TEX = int(args[2]) if len(args) > 2 else 2048
DIR = os.path.join(r"D:\Yugi-Reload\nano-banana\modelos3d", CARTA)
t0 = time.time()

def log(*a):
    print("OPT", "%5.1fs" % (time.time() - t0), *a, flush=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=os.path.join(DIR, "modelo.glb"))
alta = next(o for o in bpy.context.scene.objects if o.type == "MESH")
# sin padres ni transformaciones: todo queda en los vertices
for o in list(bpy.context.scene.objects):
    o.select_set(o == alta)
bpy.context.view_layer.objects.active = alta
bpy.ops.object.parent_clear(type="CLEAR_KEEP_TRANSFORM")
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
for o in list(bpy.context.scene.objects):
    if o != alta:
        bpy.data.objects.remove(o)
alta.name = "alta"
log("original", len(alta.data.polygons), "caras")

# copia que se simplifica
baja = alta.copy()
baja.data = alta.data.copy()
baja.name = "baja"
bpy.context.collection.objects.link(baja)

bm = bmesh.new()
bm.from_mesh(baja.data)
bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
bm.to_mesh(baja.data)
bm.free()

mod = baja.modifiers.new("simplificar", "DECIMATE")
mod.ratio = min(1.0, TRIS / max(len(baja.data.polygons), 1))
for o in bpy.context.scene.objects:
    o.select_set(o == baja)
bpy.context.view_layer.objects.active = baja
bpy.ops.object.modifier_apply(modifier=mod.name)
log("simplificada", len(baja.data.polygons), "caras")

# restos sueltos: se quedan solo las piezas con al menos 1 % de las caras
bm = bmesh.new()
bm.from_mesh(baja.data)
bm.faces.ensure_lookup_table()
vistas, piezas = set(), []
for f in bm.faces:
    if f.index in vistas:
        continue
    pieza, pila = [], [f]
    vistas.add(f.index)
    while pila:
        c = pila.pop()
        pieza.append(c)
        for e in c.edges:
            for g in e.link_faces:
                if g.index not in vistas:
                    vistas.add(g.index)
                    pila.append(g)
    piezas.append(pieza)
minimo = max(20, len(bm.faces) // 100)
sobran = [f for p in piezas if len(p) < minimo for f in p]
bmesh.ops.delete(bm, geom=sobran, context="FACES")
bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
bm.to_mesh(baja.data)
bm.free()
log("piezas", len(piezas), "-> quitadas", len([p for p in piezas if len(p) < minimo]), "| quedan", len(baja.data.polygons), "caras")

for p in baja.data.polygons:
    p.use_smooth = True

# UVs nuevas
while baja.data.uv_layers:
    baja.data.uv_layers.remove(baja.data.uv_layers[0])
baja.data.uv_layers.new(name="UVMap")
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.uv.smart_project(angle_limit=1.15, island_margin=0.004)
bpy.ops.object.mode_set(mode="OBJECT")
log("UVs listas")

# material nuevo con la imagen donde se hornea
img = bpy.data.images.new("T_" + CARTA, TEX, TEX, alpha=False)
mat = bpy.data.materials.new("M_" + CARTA)
mat.use_nodes = True
nt = mat.node_tree
bsdf = nt.nodes["Principled BSDF"]
bsdf.inputs["Roughness"].default_value = 0.55   # igual que el original de Hunyuan
nodo = nt.nodes.new("ShaderNodeTexImage")
nodo.image = img
nt.links.new(nodo.outputs["Color"], bsdf.inputs["Base Color"])
nt.nodes.active = nodo
baja.data.materials.clear()
baja.data.materials.append(mat)

# horneado: color difuso de la malla original sobre la simplificada
esc = bpy.context.scene
esc.render.engine = "CYCLES"
esc.cycles.device = "CPU"
esc.cycles.samples = 1
esc.render.bake.use_selected_to_active = True
esc.render.bake.cage_extrusion = 0.01 * max(alta.dimensions)
esc.render.bake.max_ray_distance = 0.03 * max(alta.dimensions)
esc.render.bake.margin = 8
for o in esc.objects:
    o.select_set(True)
bpy.context.view_layer.objects.active = baja
bpy.ops.object.bake(type="DIFFUSE", pass_filter={"COLOR"})
log("textura horneada", TEX, "x", TEX)

ruta_tex = os.path.join(DIR, "textura_opt.png")
img.filepath_raw = ruta_tex
img.file_format = "PNG"
img.save()

bpy.data.objects.remove(alta)
salida = os.path.join(DIR, "modelo_opt.glb")
for o in esc.objects:
    o.select_set(o == baja)
bpy.ops.export_scene.gltf(filepath=salida, use_selection=True, export_format="GLB",
                          export_image_format="JPEG", export_jpeg_quality=92, export_yup=True)
log("listo", salida, "%.1f MB" % (os.path.getsize(salida) / 1e6), "| caras", len(baja.data.polygons))
