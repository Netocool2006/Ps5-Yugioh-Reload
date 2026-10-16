# Forma 3D de una figura de Gemini con Hunyuan3D-2.1 (Hugging Face, GPU gratis): modelos3d\<carta>\forma.glb
# Despues: texturizar_3d.py <carta> la pinta con la figura y deja modelo.glb para Unreal.
#   python -I hunyuan_3d.py celtic_guardian gaia ...
import os, shutil, sys, time
sys.path.insert(0, r"D:\Yugi-Reload\herramientas\pylib")
sys.stdout.reconfigure(encoding="utf-8")
from gradio_client import Client, handle_file

CARTAS = r"D:\Yugi-Reload\remake\recursos\cartas"
SALIDA = r"D:\Yugi-Reload\nano-banana\modelos3d"

if __name__ == "__main__":
    c = Client("tencent/Hunyuan3D-2.1", verbose=False)
    for carta in sys.argv[1:]:
        t = time.time()
        try:
            r = c.predict(handle_file(os.path.join(CARTAS, carta, "figura.png")), None, None, None, None,
                          30, 5.0, 1234, 256, False, 8000, False, api_name="/shape_generation")
            d = os.path.join(SALIDA, carta)
            os.makedirs(d, exist_ok=True)
            glb = r[0]["value"] if isinstance(r[0], dict) else r[0]   # gr.File puede venir como {"value": ruta}
            shutil.copy(glb, os.path.join(d, "forma.glb"))
            print("ok %s en %.0f s" % (carta, time.time() - t), flush=True)
        except Exception as e:
            print("fallo %s: %s" % (carta, repr(e)[:300]), flush=True)
