# Limpia e instala en el remake los modelos que salen de TRELLIS (Colab): quita el pedestal de la figura
# (quitar_base -> quitar_anillo -> quitar_tapa_gris), deja el material mate (TRELLIS lo deja metalico), ajusta el
# color a la luz del juego (aclarar_textura 1.2 1.0 1.45, como Kuriboh) y lo copia a
# nano-banana/modelos3d/<carta>/modelo_final.glb y remake-ps5/assets/models/yugi/<carta>.glb.
# Uso: python -I instalar_trellis.py <carpeta con <carta>.glb> [carta ...]
import glob, os, shutil, subprocess, sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BLENDER = r"D:\tools\blender-5.2.2\blender.exe"
H = os.path.join(BASE, "herramientas")


def blender(script, *args):
    r = subprocess.run([BLENDER, "--background", "--python", os.path.join(H, "blender", script), "--", *args],
                       capture_output=True, text=True)
    if r.returncode != 0 or not os.path.exists(args[1]):
        raise RuntimeError("%s fallo:\n%s" % (script, r.stdout[-800:] + r.stderr[-800:]))


def instalar(origen, carta):
    tmp = os.path.join(os.path.dirname(origen), "_tmp_" + carta)
    os.makedirs(tmp, exist_ok=True)
    a, b, c, d, e = (os.path.join(tmp, n) for n in ("1.glb", "2.glb", "3.glb", "4.glb", "5.glb"))
    blender("quitar_base.py", origen, a)
    blender("quitar_anillo.py", a, b)
    subprocess.run([sys.executable, "-I", os.path.join(H, "quitar_tapa_gris.py"), b, c, "0.06"], check=True, capture_output=True)
    blender("aclarar_textura.py", c, d, "1.2", "1.0", "1.45")
    subprocess.run([sys.executable, "-I", os.path.join(H, "material_mate.py"), d, e], check=True, capture_output=True)
    destino = os.path.join(BASE, "nano-banana", "modelos3d", carta)
    os.makedirs(destino, exist_ok=True)
    if os.path.exists(os.path.join(destino, "modelo_final.glb")):
        shutil.copy2(os.path.join(destino, "modelo_final.glb"), os.path.join(destino, "modelo_final_anterior.glb"))
    shutil.copy2(e, os.path.join(destino, "modelo_final.glb"))
    shutil.copy2(e, os.path.join(BASE, "remake-ps5", "assets", "models", "yugi", carta + ".glb"))
    shutil.rmtree(tmp)
    print("instalado", carta, "%.1f MB" % (os.path.getsize(e) / 1e6) if os.path.exists(e) else "")


carpeta = sys.argv[1]
cartas = sys.argv[2:] or [os.path.splitext(os.path.basename(f))[0] for f in sorted(glob.glob(os.path.join(carpeta, "*.glb")))]
for k in cartas:
    instalar(os.path.join(carpeta, k + ".glb"), k)
