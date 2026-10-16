# Convierte figuras (PNG con transparencia) en modelos 3D .glb con TRELLIS (Hugging Face, gratis, sin GPU local).
#   python -I imagen_a_3d.py kuriboh dark_magician ...
import os, shutil, sys, time
sys.path.insert(0, r"D:\Yugi-Reload\herramientas\pylib")
sys.stdout.reconfigure(encoding="utf-8")
from gradio_client import Client, handle_file

CARTAS = r"D:\Yugi-Reload\remake\recursos\cartas"
SALIDA = r"D:\Yugi-Reload\nano-banana\modelos3d"

def convertir(cliente, carta):
    img = os.path.join(CARTAS, carta, "figura.png")
    destino = os.path.join(SALIDA, carta)
    os.makedirs(destino, exist_ok=True)
    t0 = time.time()
    cliente.predict(api_name="/start_session")
    previa = cliente.predict(handle_file(img), api_name="/preprocess_image")
    video, glb, _ = cliente.predict(previa, [], 0, 7.5, 12, 3.0, 12, "stochastic", 0.9, 2048,
                                    api_name="/generate_and_extract_glb")
    shutil.copy(glb, os.path.join(destino, "modelo.glb"))
    if isinstance(video, dict) and video.get("video"):
        shutil.copy(video["video"], os.path.join(destino, "giro.mp4"))
    print("ok %s en %.0f s -> %s" % (carta, time.time() - t0, destino))

if __name__ == "__main__":
    c = Client("trellis-community/TRELLIS", verbose=False)
    for carta in sys.argv[1:]:
        try:
            convertir(c, carta)
        except Exception as e:
            print("fallo %s: %s" % (carta, str(e)[:300]))
