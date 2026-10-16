# Arreglos a la base de PS5 Vulkan Template que necesita Yugi Reload (los aplica sincronizar.sh en cada copia;
# cada uno se aplica una sola vez y falla en voz alta si la base cambio y ya no encaja).
# Uso: python3 parche_base.py <carpeta del titulo>
import sys
from pathlib import Path

t = Path(sys.argv[1])


def parchear(archivo, marca, viejo, nuevo):
    p = t / archivo
    s = p.read_text(encoding="utf-8")
    if marca in s:
        return
    if viejo not in s:
        sys.exit("parche_base: %s ya no tiene el texto esperado (%s...)" % (archivo, viejo[:60]))
    p.write_text(s.replace(viejo, nuevo, 1), encoding="utf-8")


# 1) vkglTF solo leia glTF de texto: los .glb (Blender, Meshy) se leen como binarios
parchear("base/VulkanglTFModel.cpp", "LoadBinaryFromFile",
         "bool fileLoaded = gltfContext.LoadASCIIFromFile(&gltfModel, &error, &warning, filename);",
         "bool fileLoaded = filename.size() > 4 && filename.compare(filename.size() - 4, 4, \".glb\") == 0\n"
         "\t\t? gltfContext.LoadBinaryFromFile(&gltfModel, &error, &warning, filename)\n"
         "\t\t: gltfContext.LoadASCIIFromFile(&gltfModel, &error, &warning, filename);")

# 2) JOINTS_0 en uint8 (Meshy): vkglTF los leia siempre como uint16 (indices basura -> el shader se salia del
#    arreglo de huesos)
parchear("base/VulkanglTFModel.cpp", "juntas16",
         '\t\t\t\tif (primitive.attributes.find("JOINTS_0") != primitive.attributes.end()) {\n',
         "\t\t\t\tstd::vector<uint16_t> juntas16;   // JOINTS_0 en uint8 (Meshy) pasado a uint16\n"
         '\t\t\t\tif (primitive.attributes.find("JOINTS_0") != primitive.attributes.end()) {\n')
parchear("base/VulkanglTFModel.cpp", "juntas16.assign",
         "\t\t\t\t\tbufferJoints = reinterpret_cast<const uint16_t *>(&(model.buffers[jointView.buffer].data[jointAccessor.byteOffset + jointView.byteOffset]));\n",
         "\t\t\t\t\tbufferJoints = reinterpret_cast<const uint16_t *>(&(model.buffers[jointView.buffer].data[jointAccessor.byteOffset + jointView.byteOffset]));\n"
         "\t\t\t\t\tif (jointAccessor.componentType == TINYGLTF_COMPONENT_TYPE_UNSIGNED_BYTE) {\n"
         "\t\t\t\t\t\tconst uint8_t *b8 = reinterpret_cast<const uint8_t *>(bufferJoints);\n"
         "\t\t\t\t\t\tjuntas16.assign(b8, b8 + jointAccessor.count * 4);\n"
         "\t\t\t\t\t\tbufferJoints = juntas16.data();\n"
         "\t\t\t\t\t}\n")

# 3) fotos de la consola a pedido: la base solo copiaba la pantalla en el ultimo cuadro de una corrida de prueba
#    (y terminaba); ps5.capturaPedida pide una copia en cualquier cuadro sin terminar el programa
parchear("base/vulkanexamplebase.h", "capturaPedida",
         "\t\tstd::string screenshotPath;\n",
         "\t\tstd::string screenshotPath;\n"
         "\t\t/** @brief Yugi Reload: copiar la pantalla de este cuadro a screenshotPath sin terminar el programa */\n"
         "\t\tbool capturaPedida = false;\n")
parchear("base/vulkanexamplebase.cpp", "capturaPedida",
         "|| ps5Recording()) {\n\t\tpresentWait = ps5CaptureSwapchainImage(presentWait);\n",
         "|| ps5Recording() || ps5.capturaPedida) {\n\t\tpresentWait = ps5CaptureSwapchainImage(presentWait);\n"
         "\t\tps5.capturaPedida = false;\n")
# 4) cuadros de video: si la ruta termina en .jpg, la imagen se comprime a JPG (stb_image_write, dominio
#    publico) en otro hilo, para no frenar el juego (unos 200 KB en vez de 6 MB por cuadro)
parchear("ps5/src/example_ps5.cpp", "stb_image_write.h",
         "#include ",
         "#include <thread>\n#define STB_IMAGE_WRITE_IMPLEMENTATION\n#include \"stb_image_write.h\"\n#include ")
parchear("ps5/src/example_ps5.cpp", "stbi_write_jpg(",
         "\tFILE *file = fopen(ps5.screenshotPath.c_str(), \"wb\");\n",
         "\tif (ps5.screenshotPath.size() > 4 && ps5.screenshotPath.compare(ps5.screenshotPath.size() - 4, 4, \".jpg\") == 0) {\n"
         "\t\t// Yugi Reload: cuadro de video en JPG, comprimido en otro hilo\n"
         "\t\tstd::thread([ruta = ps5.screenshotPath, w = outWidth, h = outHeight, datos = std::move(rgb)]() {\n"
         "\t\t\tstbi_write_jpg(ruta.c_str(), (int)w, (int)h, 3, datos.data(), 82);\n"
         "\t\t\tchmod(ruta.c_str(), 0666);\n"
         "\t\t}).detach();\n"
         "\t\treturn ps5CaptureComplete;\n"
         "\t}\n"
         "\tFILE *file = fopen(ps5.screenshotPath.c_str(), \"wb\");\n")
# 5) videos rapidos en el PC (solo la vista previa): YUGI_ANCHO/YUGI_ALTO cambian la resolucion (4K por defecto)
#    y YUGI_FPS el paso fijo de la corrida de prueba (60 por defecto)
parchear("base/vulkanexamplebase.cpp", "YUGI_ANCHO",
         "\twidth = 3840;\n\theight = 2160;\n",
         "\twidth = 3840;\n\theight = 2160;\n"
         "#if defined(PS5_HOST_REFERENCE)\n"
         "\tif (const char *a = getenv(\"YUGI_ANCHO\")) { width = (uint32_t)atoi(a); }\n"
         "\tif (const char *a = getenv(\"YUGI_ALTO\")) { height = (uint32_t)atoi(a); }\n"
         "#endif\n")
parchear("base/vulkanexamplebase.cpp", "YUGI_FPS",
         "\t\t\tframeTimer = 1.0f / 60.0f;\n",
         "\t\t\tframeTimer = 1.0f / 60.0f;\n"
         "#if defined(PS5_HOST_REFERENCE)\n"
         "\t\t\tif (const char *f = getenv(\"YUGI_FPS\")) { frameTimer = 1.0f / (float)atof(f); }\n"
         "#endif\n")
print("parche_base: listo")
