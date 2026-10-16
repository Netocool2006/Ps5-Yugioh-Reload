# Rayo de energia para los ataques del juego de PS5: cilindro de radio 1 que va de y=0 a y=1 (el juego lo escala
# y lo orienta entre el arma y el objetivo) con un degradado blanco -> azul electrico alrededor (el centro claro).
# Uso: blender --background --python crear_rayo.py -- <salida.glb>
import bpy, math, os, sys
salida = sys.argv[sys.argv.index("--") + 1]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=1.0, depth=1.0, location=(0, 0, 0.5))
ob = bpy.context.active_object
bpy.ops.object.transform_apply(location=True)
bpy.ops.object.shade_smooth()
# el exportador pasa z de Blender a y de glTF: el cilindro queda de y=0 a y=1
ob.data.uv_layers.new(name="UVMap")
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.uv.cylinder_project()
bpy.ops.object.mode_set(mode="OBJECT")
W = 64
img = bpy.data.images.new("T_rayo", W, W)
px = []
for y in range(W):
    for x in range(W):
        t = abs(x / (W - 1) - 0.5) * 2          # 0 en el medio de la textura, 1 en los bordes
        c = (0.55 + 0.45 * (1 - t), 0.8 + 0.2 * (1 - t), 1.0)
        px += [*c, 1.0]
img.pixels = px
img.filepath_raw = os.path.join(os.path.dirname(salida), "rayo.png")
img.file_format = "PNG"
img.save()
mat = bpy.data.materials.new("M_rayo")
mat.use_nodes = True
tx = mat.node_tree.nodes.new("ShaderNodeTexImage")
tx.image = img
mat.node_tree.links.new(tx.outputs["Color"], mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"])
ob.data.materials.append(mat)
bpy.ops.export_scene.gltf(filepath=salida, export_format="GLB", export_yup=True, export_image_format="AUTO")
print("RAYO", salida, os.path.getsize(salida))
