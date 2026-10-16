# Imagen -> modelo 3D con textura usando TRELLIS.2 de Microsoft (espacio gratuito de Hugging Face, sin cuenta;
# cupo diario de GPU limitado). Uso: python trellis.py <imagen.png> <salida.glb> [triangulos=120000] [resolucion=1024]
# (con PYTHONPATH=herramientas/pylib para gradio_client)
import shutil, sys, time
from gradio_client import Client, handle_file

imagen, salida = sys.argv[1], sys.argv[2]
TRIS = int(sys.argv[3]) if len(sys.argv) > 3 else 120000
RES = sys.argv[4] if len(sys.argv) > 4 else "1024"
t0 = time.time()


def log(*a):
    print("TRELLIS %5.0fs" % (time.time() - t0), *a, flush=True)


c = Client("microsoft/TRELLIS.2", verbose=False)
c.predict(api_name="/start_session")
prep = c.predict(handle_file(imagen), api_name="/preprocess_image")
log("imagen preparada (sin fondo)")
c.predict(handle_file(prep["path"] if isinstance(prep, dict) else prep), 0, RES, api_name="/image_to_3d")
log("modelo 3D generado, resolucion", RES)
glb, descarga = c.predict(TRIS, 2048, api_name="/extract_glb")
ruta = descarga if isinstance(descarga, str) else (descarga or {}).get("path") or glb
shutil.copy(ruta, salida)
log("listo", salida)
