# Gira un modelo alrededor del eje vertical (para que su frente quede en glTF +Z, mirando a la camara del juego).
# TRELLIS a veces deja la figura de espaldas o de lado. Uso: blender --background --python girar_modelo.py --
# entrada.glb salida.glb <grados>
import bpy, math, sys

a = sys.argv[sys.argv.index("--") + 1:]
entrada, salida, grados = a[0], a[1], float(a[2])
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=entrada)
# se gira cada raiz (puede ser un nodo vacio del que cuelga la malla) alrededor del eje vertical del mundo
from mathutils import Matrix
giro = Matrix.Rotation(math.radians(grados), 4, "Z")   # Blender Z = arriba
for o in bpy.data.objects:
    if o.parent is None:
        o.matrix_world = giro @ o.matrix_world
bpy.ops.export_scene.gltf(filepath=salida, export_format="GLB", export_yup=True, export_image_format="JPEG", export_jpeg_quality=92)
print("GIRADO", grados, salida)
