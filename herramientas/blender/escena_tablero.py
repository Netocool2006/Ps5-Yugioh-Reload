# Arma el tablero del duelo de prueba (el mismo de Unreal) como UNA escena glTF para el juego de PS5 (Vulkan):
# tapete de Gemini, cartas con su cara o dorso y los monstruos 3D optimizados (modelo_opt.glb) de pie en su zona.
# Coordenadas del remake: x derecha, y arriba, z hacia el jugador (1 unidad = 1 m) -> Blender (x, -z, y);
# el exportador glTF (+Y arriba) las devuelve tal cual: glTF = (x, y, z) del remake.
# Uso: blender --background --python escena_tablero.py -- <salida.glb> [vista_previa.png]
import bpy, bmesh, json, math, os, sys
from mathutils import Matrix, Vector

args = sys.argv[sys.argv.index("--") + 1:]
SALIDA = args[0]
PREVIA = args[1] if len(args) > 1 else None
REC = r"D:\Yugi-Reload\remake\recursos"
DIS = r"D:\Yugi-Reload\remake\diseno"
MODELOS = r"D:\Yugi-Reload\nano-banana\modelos3d"
TEMP = os.path.join(os.path.dirname(os.path.abspath(SALIDA)), "texturas")
# todo el tablero (tapete, casillas y cartas) se agranda por igual: mas espacio entre los monstruos (que no le
# caigan encima a la carta vecina) sin deformar el diseno de Gemini; los monstruos NO crecen con el
ESCALA_TABLERO = 1.4
ESCALA_REAL = 2.6 / 1.8   # metros "reales" (humano 1.8 m) -> juego (igual que ESCALA_PERSONAJE en el juego)
ANCHO_MAX_MODELO = 2.3 * ESCALA_TABLERO  # m: que no invada la columna vecina
CARTA = (1.0 * ESCALA_TABLERO, 1.45 * ESCALA_TABLERO)     # m
GROSOR = 0.035
W0 = {}                 # matriz con que el importador deja cada monstruo (la conversion glTF -> Blender)

CAMPO = [  # (zona, carta, modo): el mismo duelo de prueba de construir_tablero.py
    ("jugador_monstruo_0", "baby_dragon", "ataque"), ("jugador_monstruo_1", "red_eyes", "ataque"),
    ("jugador_monstruo_2", "dark_magician", "ataque"), ("jugador_monstruo_3", "kuriboh", "defensa"),
    ("jugador_monstruo_4", "dark_magician_girl", "ataque"),
    ("rival_monstruo_0", "celtic_guardian", "ataque"), ("rival_monstruo_1", "oni_tank_t_34", "ataque"),
    ("rival_monstruo_2", "summoned_skull", "ataque"), ("rival_monstruo_3", "deepsea_shark", "ataque"),
    ("rival_monstruo_4", "stone_ogre_grotto", "ataque"),
    ("jugador_magia_0", "swords_of_revealing_light", "arriba"), ("jugador_magia_1", "", "abajo"),
    ("jugador_magia_3", "", "abajo"), ("rival_magia_1", "mirror_force", "arriba"),
    ("rival_magia_2", "", "abajo"), ("rival_magia_4", "", "abajo"),
    ("jugador_campo", "sogen", "arriba"),
]
# Campo B (solo pruebas en el PC, YUGI_CAMPO=B): otros monstruos del rival para probar sus reglas
if os.environ.get("YUGI_CAMPO") == "B":
    CAMPO = [c for c in CAMPO if not c[0].startswith("rival_monstruo")] + [
        ("rival_monstruo_0", "celtic_guardian", "ataque"), ("rival_monstruo_1", "blue_eyes", "ataque"),
        ("rival_monstruo_2", "silver_fang", "ataque"), ("rival_monstruo_3", "faith_bird", "ataque"),
        ("rival_monstruo_4", "", "abajo_def")]


def bl(x, z, y=0.0):
    """Punto del remake -> Blender."""
    return Vector((x, -z, y))


def textura(ruta, nombre, ancho):
    """Copia reducida en JPEG (el GLB pesa menos y la PS5 la decodifica igual)."""
    os.makedirs(TEMP, exist_ok=True)
    destino = os.path.join(TEMP, nombre + ".jpg")
    im = bpy.data.images.load(ruta)
    w, h = im.size
    if w > ancho:
        im.scale(ancho, round(h * ancho / w))
    im.filepath_raw = destino
    im.file_format = "JPEG"
    bpy.context.scene.render.image_settings.quality = 90
    im.save()
    bpy.data.images.remove(im)
    return destino


def material(nombre, imagen=None, color=(0.02, 0.016, 0.012), rugosidad=0.5):
    mat = bpy.data.materials.new(nombre)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = rugosidad
    bsdf.inputs["Metallic"].default_value = 0.0
    nodo = mat.node_tree.nodes.new("ShaderNodeTexImage")
    if imagen:
        nodo.image = bpy.data.images.load(imagen)
    else:
        # el juego de PS5 (vkglTF) solo usa la textura del material: el color liso va como imagen de 4x4
        os.makedirs(TEMP, exist_ok=True)
        im = bpy.data.images.new(nombre, 4, 4)
        im.pixels = [*color, 1.0] * 16
        im.filepath_raw = os.path.join(TEMP, nombre + ".png")
        im.file_format = "PNG"
        im.save()
        nodo.image = im
    mat.node_tree.links.new(nodo.outputs["Color"], bsdf.inputs["Base Color"])
    return mat


def caja(nombre, ancho, fondo, alto, centro, mat_arriba, mat_canto, giro=0.0):
    """Caja con la cara de arriba texturizada (UV 0..1, la parte de arriba de la imagen hacia el fondo)."""
    me = bpy.data.meshes.new(nombre)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=(ancho, fondo, alto), verts=bm.verts)
    uv = bm.loops.layers.uv.new("UVMap")
    for f in bm.faces:
        if f.normal.z > 0.9:
            f.material_index = 0
            for lp in f.loops:
                lp[uv].uv = (lp.vert.co.x / ancho + 0.5, lp.vert.co.y / fondo + 0.5)
        else:
            f.material_index = 1
    bm.to_mesh(me)
    bm.free()
    me.materials.append(mat_arriba)
    me.materials.append(mat_canto)
    ob = bpy.data.objects.new(nombre, me)
    bpy.context.collection.objects.link(ob)
    ob.location = centro
    ob.rotation_euler = (0.0, 0.0, giro)
    return ob


def importar_modelo(carta):
    # modelo_final.glb: el arreglado en Blender (reparar_textura.py / crear_ojos_rojos.py); si no, el optimizado
    ruta = os.path.join(MODELOS, carta, "modelo_final.glb")
    if not os.path.exists(ruta):
        ruta = os.path.join(MODELOS, carta, "modelo_opt.glb")
    if not os.path.exists(ruta):
        return None
    antes = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=ruta)
    nuevos = [o for o in bpy.data.objects if o not in antes]
    malla = next(o for o in nuevos if o.type == "MESH")
    for o in nuevos:
        if o is not malla:
            bpy.data.objects.remove(o)
    malla.parent = None
    malla.name = "Monstruo_" + carta
    bpy.context.view_layer.update()
    W0[malla.name] = malla.matrix_world.copy()
    return malla


bpy.ops.wm.read_factory_settings(use_empty=True)
lay = json.load(open(os.path.join(DIS, "tablero.json"), encoding="utf-8"))
lay["ancho"] *= ESCALA_TABLERO
lay["alto"] *= ESCALA_TABLERO
for _z in lay["zonas"]:
    _z["x"] *= ESCALA_TABLERO
    _z["z"] *= ESCALA_TABLERO
# altura logica de cada monstruo (remake/diseno/tamanos.json; si no esta, por su tipo y nivel)
TAM = json.load(open(os.path.join(DIS, "tamanos.json"), encoding="utf-8"))
META = {c["id"]: c for c in json.load(open(os.path.join(REC, "cartas", "cartas.json"), encoding="utf-8"))}


def alto_juego(carta):
    if carta in TAM["cartas"]:
        real = TAM["cartas"][carta]
    else:
        c = META.get(carta, {})
        real = TAM["por_tipo"].get(c.get("tipo"), 1.8) * (0.85 + 0.03 * c.get("nivel", 4))
        real = min(max(real, 0.4), 3.2)
    return real * ESCALA_REAL
zonas = {z["id"]: z for z in lay["zonas"]}

canto = material("M_Canto", color=(0.02, 0.016, 0.012))
mesa = material("M_Tablero", textura(os.path.join(REC, "ui", "tablero.png"), "tablero", 2048), rugosidad=0.75)
dorso = material("M_Dorso", textura(os.path.join(REC, "ui", "dorso.png"), "dorso", 512), rugosidad=0.3)
caras = {}

# mesa: el tapete arriba, un canto oscuro de 30 cm alrededor y por debajo
caja("Mesa", lay["ancho"], lay["alto"], 0.02, bl(0, 0, -0.01), mesa, canto)
caja("MesaBase", lay["ancho"] + 0.3, lay["alto"] + 0.3, 0.3, bl(0, 0, -0.17), canto, canto)

for zona, carta, modo in CAMPO:
    z = zonas[zona]
    rival = z["lado"] == "rival"
    girada = modo in ("defensa", "abajo_def")
    boca_abajo = modo in ("abajo", "abajo_def")
    if boca_abajo or not carta:
        mat = dorso
    else:
        if carta not in caras:
            caras[carta] = material("M_Cara_" + carta,
                                    textura(os.path.join(REC, "cartas", carta, "cara.png"), "cara_" + carta, 512),
                                    rugosidad=0.25)
        mat = caras[carta]
    giro = math.radians((180 if rival else 0) + (90 if girada else 0))
    caja("Carta_" + zona, CARTA[0], CARTA[1], GROSOR, bl(z["x"], z["z"], GROSOR / 2 + 0.002), mat, canto, giro)

    if carta and not boca_abajo and z["tipo"] == "monstruo":
        m = importar_modelo(carta)
        if not m:
            continue  # sin modelo 3D: solo la carta (nada de figuras planas)
        bpy.context.view_layer.update()
        esquinas = [m.matrix_world @ Vector(c) for c in m.bound_box]
        alto = max(c.z for c in esquinas) - min(c.z for c in esquinas)
        ancho = max(max(c.x for c in esquinas) - min(c.x for c in esquinas),
                    max(c.y for c in esquinas) - min(c.y for c in esquinas))
        esc = min(alto_juego(carta) / max(alto, 1e-3), TAM.get("ancho_max", {}).get(carta, ANCHO_MAX_MODELO) / max(ancho, 1e-3)) * (0.8 if girada else 1.0)
        # sin giro propio: el frente del modelo (glTF +Z) mira a la camara, tambien el del rival (se ve de frente)
        m.scale = (esc, esc, esc)
        bpy.context.view_layer.update()
        esquinas = [m.matrix_world @ Vector(c) for c in m.bound_box]
        cx = (max(c.x for c in esquinas) + min(c.x for c in esquinas)) / 2
        cy = (max(c.y for c in esquinas) + min(c.y for c in esquinas)) / 2
        m.location += bl(z["x"], z["z"], GROSOR + 0.05) - Vector((cx, cy, min(c.z for c in esquinas)))

bpy.context.view_layer.update()
os.makedirs(os.path.dirname(os.path.abspath(SALIDA)), exist_ok=True)
# el tablero (mesa y cartas) va en un GLB; cada monstruo se dibuja aparte con su modelo_opt.glb y la matriz
# que se escribe en escena.h (asi el juego puede animarlos uno por uno)
monstruos = [o for o in bpy.data.objects if o.name.startswith("Monstruo_")]
for o in bpy.data.objects:
    o.select_set(o.type == "MESH" and o not in monstruos)
bpy.ops.export_scene.gltf(filepath=SALIDA, export_format="GLB", export_yup=True, export_apply=True,
                          use_selection=True, export_image_format="JPEG", export_jpeg_quality=90,
                          export_cameras=False, export_lights=False)
print("ESCENA", SALIDA, "%.1f MB" % (os.path.getsize(SALIDA) / 1e6),
      "| objetos", len([o for o in bpy.data.objects if o.type == "MESH"]) - len(monstruos), "+", len(monstruos), "monstruos")

# Blender (x, y, z) -> glTF (x, z, -y). Los datos de la malla importada siguen en glTF (el importador pone la
# conversion en la matriz del objeto, W0), asi que: mundo_glTF = conv * M_blender * W0^-1 * conv^-1 * vertice_glTF
conv = Matrix(((1, 0, 0, 0), (0, 0, 1, 0), (0, -1, 0, 0), (0, 0, 0, 1)))
lineas = ["// Generado por herramientas/blender/escena_tablero.py: no editar a mano.",
          "// Matriz de cada monstruo (columnas, glTF: x derecha, y arriba, z hacia el jugador) y su archivo.",
          "#pragma once", "struct MonstruoEscena { const char *carta; float matriz[16]; float x, z; bool rival; };",
          "static const MonstruoEscena MONSTRUOS[] = {"]
for m in monstruos:
    M = conv @ m.matrix_world @ W0[m.name].inverted() @ conv.inverted()
    col = [M[f][c] for c in range(4) for f in range(4)]
    carta = m.name[len("Monstruo_"):]
    zona = next(z for zid, c, _ in CAMPO if c == carta for z in [zonas[zid]])
    lineas.append('\t{ "%s", { %s }, %.3ff, %.3ff, %s },' % (carta, ", ".join("%.6ff" % v for v in col),
                                                            zona["x"], zona["z"], "true" if zona["lado"] == "rival" else "false"))
lineas.append("};")
with open(os.path.join(os.path.dirname(os.path.abspath(SALIDA)), "escena.h"), "w", encoding="utf-8") as f:
    f.write("\n".join(lineas) + "\n")
print("CABECERA escena.h con", len(monstruos), "monstruos")

if PREVIA:
    # misma toma que CamaraJuego de Unreal: ue(0,12.8,6.4) -> ue(0,-0.6,0), fov horizontal 62
    esc = bpy.context.scene
    cam = bpy.data.objects.new("Camara", bpy.data.cameras.new("Camara"))
    esc.collection.objects.link(cam)
    cam.location = bl(0, 12.8, 6.4)
    cam.rotation_euler = (bl(0, -0.6, 0) - cam.location).to_track_quat("-Z", "Y").to_euler()
    cam.data.sensor_fit = "HORIZONTAL"
    cam.data.angle = math.radians(62)
    esc.camera = cam
    sol = bpy.data.objects.new("Sol", bpy.data.lights.new("Sol", "SUN"))
    sol.data.energy = 3.2
    sol.rotation_euler = (math.radians(40), 0, math.radians(35))
    esc.collection.objects.link(sol)
    esc.world = bpy.data.worlds.new("Mundo")
    esc.world.use_nodes = True
    esc.world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.6
    esc.render.engine = "BLENDER_EEVEE"
    esc.render.resolution_x, esc.render.resolution_y = 1600, 900
    esc.render.filepath = PREVIA
    bpy.ops.render.render(write_still=True)
    print("PREVIA", PREVIA)
