# Esfera de energia para los ataques del juego de PS5: icosfera de radio 1 con un degradado violeta-rosa
# (el juego la dibuja emisiva y la escala). Uso: blender --background --python crear_esfera.py -- <salida.glb>
import bpy, os, sys
salida = sys.argv[sys.argv.index("--") + 1]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=4, radius=1.0)
ob = bpy.context.active_object
bpy.ops.object.shade_smooth()
ob.data.uv_layers.new(name="UVMap")
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.uv.sphere_project()
bpy.ops.object.mode_set(mode="OBJECT")
W = 64
img = bpy.data.images.new("T_esfera", W, W)
px = []
for y in range(W):
    t = y / (W - 1)
    c = (0.55 + 0.45 * t, 0.25 + 0.35 * t, 1.0)
    px += [*c, 1.0] * W
img.pixels = px
img.filepath_raw = os.path.join(os.path.dirname(salida), "esfera.png")
img.file_format = "PNG"
img.save()
mat = bpy.data.materials.new("M_esfera")
mat.use_nodes = True
tx = mat.node_tree.nodes.new("ShaderNodeTexImage")
tx.image = img
mat.node_tree.links.new(tx.outputs["Color"], mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"])
ob.data.materials.append(mat)
bpy.ops.export_scene.gltf(filepath=salida, export_format="GLB", export_yup=True, export_image_format="AUTO")
print("ESFERA", salida, os.path.getsize(salida))
