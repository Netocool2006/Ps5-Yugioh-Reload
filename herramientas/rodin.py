# Imagen -> modelo 3D con Hyper3D Rodin (la misma API y la clave de prueba gratuita que usa el complemento
# blender-mcp: https://github.com/ahujasid/blender-mcp). Sube la imagen, espera el trabajo y baja el .glb.
# Uso: python -I rodin.py <imagen.png> <salida.glb> [--tier Sketch|Regular] [--tapose]
#   --tapose: pide el personaje en pose T/A (para ponerle esqueleto y animarlo)
import json, mimetypes, os, sys, time, urllib.request, uuid

API = "https://hyperhuman.deemos.com/api/v2"
CLAVE = os.environ.get("RODIN_API_KEY", "vibecoding")   # clave de prueba del complemento blender-mcp
imagen, salida = sys.argv[1], sys.argv[2]
tier = sys.argv[sys.argv.index("--tier") + 1] if "--tier" in sys.argv else "Regular"
tapose = "--tapose" in sys.argv


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def pedir(ruta, cuerpo=None, tipo="application/json"):
    req = urllib.request.Request(API + ruta, data=cuerpo, method="POST",
                                 headers={"Authorization": "Bearer " + CLAVE, "Content-Type": tipo})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode("utf-8"))


# multipart a mano (sin dependencias)
borde = uuid.uuid4().hex
partes = []
campos = [("tier", tier), ("mesh_mode", "Quad" if tier != "Sketch" else "Raw"), ("texture_mode", "high"),
          ("geometry_file_format", "glb"), ("material", "PBR")]
if tapose:
    campos.append(("TAPose", "true"))
for k, v in campos:
    partes.append(f'--{borde}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
with open(imagen, "rb") as f:
    datos = f.read()
partes.append((f'--{borde}\r\nContent-Disposition: form-data; name="images"; filename="{os.path.basename(imagen)}"\r\n'
               f'Content-Type: {mimetypes.guess_type(imagen)[0] or "image/png"}\r\n\r\n').encode() + datos + b"\r\n")
partes.append(f"--{borde}--\r\n".encode())
r = pedir("/rodin", b"".join(partes), "multipart/form-data; boundary=" + borde)
if "uuid" not in r:
    sys.exit("Rodin no acepto el trabajo: %s" % r)
tarea, suscripcion = r["uuid"], r["jobs"]["subscription_key"]
log("trabajo", tarea, "| tier", tier, "| TAPose", tapose)

while True:
    time.sleep(10)
    estados = [j["status"] for j in pedir("/status", json.dumps({"subscription_key": suscripcion}).encode())["jobs"]]
    log("estado", estados)
    if all(e == "Done" for e in estados):
        break
    if any(e == "Failed" for e in estados):
        sys.exit("Rodin fallo: %s" % estados)

lista = pedir("/download", json.dumps({"task_uuid": tarea}).encode())["list"]
glb = next(i for i in lista if i["name"].endswith(".glb"))
os.makedirs(os.path.dirname(os.path.abspath(salida)), exist_ok=True)
urllib.request.urlretrieve(glb["url"], salida)
log("listo", salida, "%.1f MB" % (os.path.getsize(salida) / 1e6), "| archivos:", [i["name"] for i in lista])
