#!/usr/bin/env bash
# Copia el juego (D:\Yugi-Reload\remake-ps5, que llega como /compartido/yugi-src) al titulo PPSA77001 de la
# plantilla Vulkan dentro del contenedor arch-ps5, aplica los arreglos a la base (parche_base.py) y compila los
# shaders. Uso: bash sincronizar.sh
set -euo pipefail
# YUGI_SRC: carpeta remake-ps5 a compilar (la de una rama/agente); YUGI_ASSETS: modelos (no van al repo)
src=${YUGI_SRC:-/compartido/yugi-src}
assets=${YUGI_ASSETS:-/compartido/yugi-src/assets}
t=/work/PS5_YugiReload
cp "$src/src/yugireload.cpp" "$t/examples/yugireload/yugireload.cpp"
cp "$src/escena/escena.h" "$t/examples/yugireload/escena.h"
# interfaz del duelo (HUD): su codigo y stb_truetype (texto SDF)
cp "$src/src/interfaz.h" "$t/examples/yugireload/interfaz.h"
cp "$src/third_party/stb_truetype.h" "$t/examples/yugireload/stb_truetype.h"
# reglas de combate (motor de reglas del Excel del usuario): un archivo por regla
rm -rf "$t/examples/yugireload/reglas" && mkdir -p "$t/examples/yugireload/reglas"
cp "$src"/src/reglas/*.h "$t/examples/yugireload/reglas/"
rm -f "$t"/shaders/glsl/yugireload/model.*
cp "$src"/shaders/*.vert "$src"/shaders/*.frag "$t/shaders/glsl/yugireload/"
for s in "$t"/shaders/glsl/yugireload/*.vert "$t"/shaders/glsl/yugireload/*.frag; do
    glslangValidator -V --target-env vulkan1.3 "$s" -o "$s.spv" > /tmp/glslang.log || { cat /tmp/glslang.log; exit 1; }
done
# arreglos a la base: .glb binarios, huesos uint8 de Meshy, fotos y video de la consola a pedido
cp "$src/third_party/stb_image_write.h" "$t/ps5/src/stb_image_write.h"
python3 "$src/parche_base.py" "$t"
mkdir -p "$t/ps5/assets/models/yugi"
cp "$assets"/models/yugi/*.glb "$t/ps5/assets/models/yugi/"
# interfaz: caras de las cartas y sus datos (preparar_ui.py, no van al repo) y las fuentes libres (OFL, en el repo)
rm -rf "$t/ps5/assets/ui" && mkdir -p "$t/ps5/assets/ui/fuentes"
cp "$assets"/ui/*.png "$assets"/ui/cartas_ui.txt "$t/ps5/assets/ui/"
cp "$src"/third_party/fuentes/* "$t/ps5/assets/ui/fuentes/"
python3 - "$t/ps5/assets.json" <<'PY'
import json, sys
p = sys.argv[1]
d = json.load(open(p))
d["assets"] = [a for a in d["assets"] if a["path"] not in ("models/ps5/lantern", "models/yugi", "ui")]
d["assets"].append({"path": "ui", "from": "file", "source": "ps5/assets/ui",
    "used_by": ["yugireload"], "title": "Interfaz del duelo: caras de cartas, datos y fuentes (Chakra Petch, Rajdhani)",
    "author": "Yugi Reload; fuentes: The Chakra Petch Project Authors, Indian Type Foundry", "licence": "Uso personal; fuentes OFL-1.1",
    "url": "https://github.com/google/fonts/tree/main/ofl"})
d["assets"].append({"path": "models/yugi", "from": "file", "source": "ps5/assets/models/yugi",
    "used_by": ["yugireload"], "title": "Tablero, cartas y monstruos de Yugi Reload",
    "author": "Yugi Reload (proyecto personal: Gemini, Hunyuan3D, Meshy y Blender)", "licence": "Uso personal",
    "url": "-"})
json.dump(d, open(p, "w"), indent=2, ensure_ascii=False)
PY
cp "${assets%/assets}/sce_sys/icon0.png" "$t/ps5/sce_sys/icon0.png"   # el icono no va al repo
echo "sincronizado en $t"
