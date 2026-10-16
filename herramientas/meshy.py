# Cliente de la API de Meshy para Yugi Reload. Clave en herramientas/claves/meshy_api.txt (nunca se imprime).
# Cuida los creditos: cada trabajo creado se anota en <carpeta>/meshy_estado.json y, si se vuelve a pedir el mismo
# paso, se retoma ese trabajo (nunca se crea otro ni se paga dos veces); los resultados se descargan al terminar
# (Meshy los borra a los 3 dias).
# Uso:
#   python -I meshy.py saldo
#   python -I meshy.py biblioteca <salida.json>                       (gratis: todas las animaciones)
#   python -I meshy.py modelo <carpeta> <img1> [img2..img4] [--pose a-pose] [--tris 30000] [--geo2k] [--tex4k] [--con-luz] [--objeto]
#   python -I meshy.py esqueleto <carpeta> [--alto 1.8] [--tipo biped|quadruped]
#   python -I meshy.py animar <carpeta> <nombre> <id1,id2,...>
import base64, json, mimetypes, os, sys, time, urllib.error, urllib.request

API = "https://api.meshy.ai/openapi"
CLAVE = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "claves", "meshy_api.txt"),
             encoding="utf-8-sig").read().strip()


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def llamar(metodo, ruta, cuerpo=None):
    datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
    req = urllib.request.Request(API + ruta, data=datos, method=metodo,
                                 headers={"Authorization": "Bearer " + CLAVE, "Content-Type": "application/json"})
    for intento in range(6):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if metodo == "GET" and (e.code == 429 or e.code >= 500):
                time.sleep(int(e.headers.get("Retry-After", 5)))
                continue
            sys.exit("Meshy %s %s -> HTTP %d: %s" % (metodo, ruta, e.code, e.read().decode("utf-8", "replace")[:500]))
        except urllib.error.URLError:
            if metodo == "GET":
                time.sleep(5)
                continue
            raise
    sys.exit("Meshy no responde: " + ruta)


def data_uri(ruta):
    tipo = mimetypes.guess_type(ruta)[0] or "image/png"
    return "data:%s;base64,%s" % (tipo, base64.b64encode(open(ruta, "rb").read()).decode())


def estado(carpeta):
    p = os.path.join(carpeta, "meshy_estado.json")
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}


def guardar(carpeta, est):
    with open(os.path.join(carpeta, "meshy_estado.json"), "w", encoding="utf-8") as f:
        json.dump(est, f, indent=2, ensure_ascii=False)


def esperar(ruta):
    while True:
        t = llamar("GET", ruta)
        if t["status"] == "SUCCEEDED":
            log("listo", ruta, "| creditos usados:", t.get("consumed_credits"))
            return t
        if t["status"] in ("FAILED", "CANCELED"):
            sys.exit("Meshy %s %s: %s" % (ruta, t["status"], (t.get("task_error") or {}).get("message")))
        log(ruta, t["status"], "%s%%" % t.get("progress", 0))
        time.sleep(10)


def bajar(url, destino):
    urllib.request.urlretrieve(url, destino)
    log("descargado", destino, "%.1f MB" % (os.path.getsize(destino) / 1e6))


def paso(carpeta, clave, ruta_crear, cuerpo, ruta_tarea):
    """Crea el trabajo una sola vez (o retoma el anotado) y espera a que termine."""
    est = estado(carpeta)
    if clave not in est:
        tid = llamar("POST", ruta_crear, cuerpo)["result"]
        est[clave] = tid
        guardar(carpeta, est)
        log("trabajo creado", clave, tid)
    else:
        log("retomando", clave, est[clave])
    return esperar(ruta_tarea + "/" + est[clave])


cmd = sys.argv[1]
if cmd == "saldo":
    print(llamar("GET", "/v1/balance"))
elif cmd == "biblioteca":
    todo = llamar("GET", "/v1/animations/library")   # la biblioteca entera en una sola respuesta
    json.dump(todo, open(sys.argv[2], "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(len(todo), "animaciones ->", sys.argv[2])
elif cmd == "modelo":
    carpeta = sys.argv[2]
    imgs = [a for a in sys.argv[3:] if not a.startswith("--") and os.path.isfile(a)]
    pose = sys.argv[sys.argv.index("--pose") + 1] if "--pose" in sys.argv else "a-pose"
    tris = int(sys.argv[sys.argv.index("--tris") + 1]) if "--tris" in sys.argv else 30000
    cuerpo = {"image_urls": [data_uri(i) for i in imgs], "ai_model": "latest", "pose_mode": pose,
              "topology": "triangle", "target_polycount": tris, "should_remesh": True, "should_texture": True,
              "texture_resolution": "4k" if "--tex4k" in sys.argv else "2k",
              # --con-luz: conserva las sombras pintadas de la imagen (mas relieve y detalle aparente)
              "remove_lighting": "--con-luz" not in sys.argv, "name": os.path.basename(carpeta.rstrip("/\\"))}
    if pose == "ninguna":
        cuerpo.pop("pose_mode")                   # monstruos que no se animan con esqueleto humano
    if "--geo2k" in sys.argv:
        cuerpo["geometry_resolution"] = "2k"      # +5 creditos: geometria mas fina
    if "--objeto" in sys.argv:
        # objeto sin personaje (armas): malla limpia y liviana para el juego, sin pose
        cuerpo.pop("pose_mode")
        cuerpo.pop("should_remesh")
        cuerpo.pop("remove_lighting")
        cuerpo.update({"model_type": "smart-topology", "ai_model": "meshy-t2.5", "target_polycount": min(tris, 8000),
                       "texture_resolution": "2k"})
    if len(imgs) > 1:
        t = paso(carpeta, "modelo", "/v1/multi-image-to-3d", cuerpo, "/v1/multi-image-to-3d")
    else:
        cuerpo["image_url"] = cuerpo.pop("image_urls")[0]
        t = paso(carpeta, "modelo", "/v1/image-to-3d", cuerpo, "/v1/image-to-3d")
    bajar(t["model_urls"]["glb"], os.path.join(carpeta, "meshy_modelo.glb"))
    if t.get("thumbnail_url"):
        bajar(t["thumbnail_url"], os.path.join(carpeta, "meshy_miniatura.png"))
elif cmd == "esqueleto":
    carpeta = sys.argv[2]
    alto = float(sys.argv[sys.argv.index("--alto") + 1]) if "--alto" in sys.argv else 1.8
    tipo = sys.argv[sys.argv.index("--tipo") + 1] if "--tipo" in sys.argv else "biped"
    est = estado(carpeta)
    cuerpo = {"height_meters": alto, "animation_type": tipo}
    if "--glb" in sys.argv:
        # un GLB retocado en el PC (p. ej. sin la base de la figura) en vez del modelo de Meshy tal cual
        g = sys.argv[sys.argv.index("--glb") + 1]
        cuerpo["model_url"] = "data:model/gltf-binary;base64," + base64.b64encode(open(g, "rb").read()).decode()
    else:
        cuerpo["input_task_id"] = est["modelo"]
    t = paso(carpeta, "esqueleto", "/v1/rigging", cuerpo, "/v1/rigging")
    bajar(t["result"]["rigged_character_glb_url"], os.path.join(carpeta, "meshy_esqueleto.glb"))
elif cmd == "animar":
    carpeta, nombre = sys.argv[2], sys.argv[3]
    ids = [int(x) for x in sys.argv[4].split(",")]
    est = estado(carpeta)
    t = paso(carpeta, "animacion_" + nombre, "/v1/animations",
             {"rig_task_id": est["esqueleto"], "action_ids": ids, "post_process": {"operation_type": "change_fps", "fps": 30}},
             "/v1/animations")
    bajar(t["result"]["animation_glb_url"], os.path.join(carpeta, "meshy_anim_%s.glb" % nombre))
else:
    sys.exit("comando desconocido: " + cmd)
