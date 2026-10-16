#!/usr/bin/env bash
# Compila la vista previa de PC de UNA rama y graba un video, por turno (candado): varios agentes pueden
# programar en paralelo y probar sin pisarse la compilacion del contenedor.
# Uso (dentro del contenedor arch-ps5):
#   bash /compartido/wt/<rama>/remake-ps5/probar_rama.sh /compartido/wt/<rama>/remake-ps5 <salida.mp4> <segundos> [VAR=valor ...]
# Ejemplo: ... probar_rama.sh /compartido/wt/vfx/remake-ps5 /compartido/videos_vfx/fuego.mp4 9 YUGI_DUELO=2
# Sin <salida.mp4> ("-") solo compila. La PS5 se compila tambien (build.sh) para detectar errores de la consola.
set -euo pipefail
src=$1; salida=$2; segundos=${3:-9}; shift 3 || true
exec 9>/compartido/.compilar.lock
flock 9
cd /work/PS5_YugiReload
YUGI_SRC="$src" bash "$src/sincronizar.sh" > /tmp/sincronizar.log 2>&1 || { cat /tmp/sincronizar.log; exit 1; }
bash ps5/tools/build.sh > /tmp/build.log 2>&1 || { grep -E "error" /tmp/build.log | head -30; exit 1; }
ninja -C build/ps5-host ps5-samples-host > /tmp/host.log 2>&1 || { grep -E "error" /tmp/host.log | head -30; exit 1; }
grep -E "warning:" /tmp/build.log /tmp/host.log | grep -v "unused-command-line" | head -10 || true
echo "COMPILADO $src"
if [[ "$salida" != "-" ]]; then
	mkdir -p "$(dirname "$salida")"
	env "$@" bash /compartido/video_pc.sh "$segundos" "$salida" | tail -1
fi
