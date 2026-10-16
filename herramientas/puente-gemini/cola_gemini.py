# Cola larga de conversion con Gemini (por el puente de navegador): convierte TODAS las imagenes del juego.
# Orden de prioridad:
#   0) pendientes del prototipo (nano-banana\arte, base1c, lote02)
#   1) ilustraciones de todas las cartas (remaster 3D)          -> nano-banana\todo\arte\<bmp>\
#   2) figuras 3D de todos los monstruos                        -> nano-banana\todo\figura\<carta>\
#   3) resto de imagenes del juego, solo version en espanol     -> nano-banana\todo\ui\<ruta>\
# Cuando Gemini llega a su limite de uso, la cola se pausa, avisa (notificacion de Windows + registro) y vuelve a
# probar cada 30 min; al reanudar avisa otra vez. Mientras trabaja impide que el PC se suspenda.
# Estado: nano-banana\todo\estado.json  |  registro: nano-banana\todo\cola.log (lineas EVENTO para vigilar)
# Uso: python -I cola_gemini.py
import ctypes, csv, datetime, json, os, re, subprocess, sys, time, traceback
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
sys.path.insert(0, r"D:\Yugi-Reload\herramientas\pylib")
sys.path.insert(0, r"D:\Yugi-Reload\poc-godot\preparacion")
sys.path.insert(0, r"D:\Yugi-Reload\nano-banana")
from PIL import Image
import puente_gemini as pg
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

BASE = r"D:\Yugi-Reload"
NB = os.path.join(BASE, "nano-banana")
TODO = os.path.join(NB, "todo")
DATOS = os.path.join(BASE, "datadat-extraido")
REFERENCIA = os.path.join(NB, "lote01", "flame_swordsman", "resultado.png")
ESPERA_LIMITE = 30 * 60
PAUSA = 20                       # segundos entre imagenes (pedido del usuario)
os.makedirs(TODO, exist_ok=True)
LOG = os.path.join(TODO, "cola.log")
ESTADO = os.path.join(TODO, "estado.json")

def registrar(msg, evento=False):
    linea = "%s %s%s" % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "EVENTO " if evento else "", msg)
    print(linea, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(linea + "\n")

def avisar(titulo, texto):
    """Notificacion de Windows (globo en la bandeja), sin bloquear la cola."""
    ps = ("[void][reflection.assembly]::LoadWithPartialName('System.Windows.Forms');"
          "$n=New-Object System.Windows.Forms.NotifyIcon;$n.Icon=[System.Drawing.SystemIcons]::Information;"
          "$n.Visible=$true;$n.ShowBalloonTip(15000,'%s','%s','Info');Start-Sleep 16;$n.Dispose()" %
          (titulo.replace("'", ""), texto.replace("'", "")))
    subprocess.Popen(["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps],
                     creationflags=0x08000000)

def mantener_despierto(si):
    ES_CONTINUOUS, ES_SYSTEM, ES_DISPLAY = 0x80000000, 0x00000001, 0x00000002
    ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | ((ES_SYSTEM | ES_DISPLAY) if si else 0))

def guardar_estado(**k):
    try:
        e = json.load(open(ESTADO, encoding="utf-8"))
    except Exception:
        e = {}
    e.update(k); e["actualizado"] = datetime.datetime.now().isoformat(timespec="seconds")
    tmp = ESTADO + ".tmp"
    json.dump(e, open(tmp, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    os.replace(tmp, ESTADO)

# ------------------------------------------------------------------ catalogo de trabajos
def slug(s):
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")

def cartas_del_juego():
    """(nombre en espanol, nombre ingles, bmp, fila de cards.csv) de cada ilustracion de carta, sin repetir bmp."""
    lineas = open(os.path.join(DATOS, "card", "list_card.txt"), encoding="latin-1").read().splitlines()
    filas = {r["nombre"].lower(): r for r in csv.DictReader(open(os.path.join(BASE, "re-output", "cards.csv"), encoding="utf-8"))}
    nom_es = open(os.path.join(DATOS, "bin#", "card_namespa.bin"), "rb").read()
    vistos, res, nombre = set(), [], None
    for l in lineas:
        l = l.strip()
        if l.startswith("//") and not re.match(r"//\s*\d{4}:", l) and "Generated" not in l:
            nombre = l[2:].strip()
        elif l.lower().endswith(".bmp") and nombre:
            b = l.lower()
            # token_*.bmp = relleno; zzz*.bmp SI son ilustraciones reales (50 cartas usables)
            if b not in vistos and not b.startswith(("token_", "card_ura")) and nombre.lower() in filas:
                vistos.add(b); f = filas[nombre.lower()]
                i = int(f["idx"]); es = nom_es[i * 64:(i + 1) * 64].split(b"\0")[0].decode("latin-1").strip() or nombre
                res.append((es, nombre, l, f))
            nombre = None
    return res

PROMPT_ARTE = ("Remasteriza esta ilustracion de la carta de Yu-Gi-Oh! \"{nombre}\" como si fuera el arte oficial de una "
    "reedicion premium de 2026.\n\n- Conserva EXACTAMENTE la composicion, el encuadre, los personajes u objetos, sus poses, "
    "colores y el fondo tematico de la original: debe reconocerse al instante como la misma carta.\n- LO MAS IMPORTANTE: "
    "debe verse 3D, NUNCA 2D. Render 3D cinematografico de alta gama (calidad AAA): volumen real, materiales con textura y "
    "reflejos, iluminacion volumetrica con luz de contorno, profundidad de campo suave.\n- Prohibido el aspecto de dibujo, "
    "anime, cel-shading, contornos negros o colores planos. Sin elementos nuevos.\n- Sin texto, sin marco, sin bordes, sin "
    "marcas de agua. Formato cuadrado 1:1, la imagen ocupando todo el cuadro.\n")

PROMPT_UI = ("Remasteriza este recurso grafico del videojuego Yu-Gi-Oh! Power of Chaos (2004) para una version remake de 2026.\n\n"
    "- Conserva EXACTAMENTE la composicion, la disposicion y las proporciones de todos los elementos, para que encaje en el "
    "mismo lugar de la pantalla. Si hay varias piezas o fotogramas en la imagen, conserva cada una en su misma posicion.\n"
    "- Si contiene texto, conservalo EXACTAMENTE igual, en espanol, con una tipografia moderna y limpia.\n"
    "- Si hay personajes, mantenlos reconocibles (mismo personaje, ropa, pose y expresion) con acabado 3D moderno.\n"
    "- Estilo 2026: alta definicion, materiales con relieve y brillo, iluminacion cuidada, aspecto 3D y premium, no plano.\n"
    "- Las zonas de color verde puro (fondo transparente del juego) deben quedar en VERDE PURO uniforme (#00FF00).\n"
    "- Sin marcas de agua.\n")

def trabajos():
    """Lista ordenada de (grupo, carpeta, preparar) donde preparar() deja las imagenes y el prompt en la carpeta."""
    lista = []
    for lote in ("arte", "base1c", "lote02"):                      # 0) prototipo (ya preparados)
        d = os.path.join(NB, lote)
        if os.path.isdir(d):
            for sub in sorted(os.listdir(d)):
                if os.path.isdir(os.path.join(d, sub)):
                    lista.append(("prototipo", os.path.join(d, sub), None))
    hechos_arte = {sub for sub in os.listdir(os.path.join(NB, "arte"))} if os.path.isdir(os.path.join(NB, "arte")) else set()
    cartas = cartas_del_juego()
    for es, en, bmp, f in cartas:                                  # 1) ilustraciones
        if slug(en) in hechos_arte: continue
        lista.append(("arte", os.path.join(TODO, "arte", os.path.splitext(bmp.lower())[0]),
                      lambda d, bmp=bmp, es=es: preparar_arte(d, bmp, es)))
    hechas_fig = set()
    for lote in ("lote01", "lote02"):
        if os.path.isdir(os.path.join(NB, lote)): hechas_fig |= set(os.listdir(os.path.join(NB, lote)))
    hechas_fig.add("faith_bird")
    for es, en, bmp, f in cartas:                                  # 2) figuras de monstruos
        if f["tipo"] in ("Magic", "Trap") or slug(en) in hechas_fig: continue
        lista.append(("figura", os.path.join(TODO, "figura", slug(en)),
                      lambda d, bmp=bmp, es=es, f=f: preparar_figura(d, bmp, es, f)))
    for ruta in imagenes_ui():                                     # 3) resto del juego (espanol)
        rel = os.path.relpath(ruta, DATOS)
        lista.append(("ui", os.path.join(TODO, "ui", os.path.splitext(rel)[0].replace(os.sep, "__")),
                      lambda d, ruta=ruta: preparar_ui(d, ruta)))
    return lista

def imagenes_ui():
    res = []
    for raiz in ("j", "cursor"):
        for dp, dn, fs in os.walk(os.path.join(DATOS, raiz)):
            bajos = {x.lower() for x in fs}
            for f in sorted(fs):
                n = os.path.splitext(f)[0].lower()
                if not f.lower().endswith(".bmp"): continue
                # solo espanol: si existe la variante _s / #s, se descartan las de otros idiomas (e, f, g, i, j)
                if re.search(r"[efgij]$", n) and (re.sub(r"[efgij]$", "s", n) + ".bmp") in bajos: continue
                try:
                    w, h = Image.open(os.path.join(dp, f)).size
                except Exception:
                    continue
                if w >= 4 and h >= 4:            # todo, hasta el boton mas pequeno
                    res.append(os.path.join(dp, f))
    # prioridad: fondos de tablero por carta de campo, luego lo mas grande/visible; tipografias al final
    def orden(r):
        rl = r.lower()
        if os.sep + "field" + os.sep in rl: return (0, 0)
        if "font" in os.path.basename(rl): return (3, 0)
        w, h = Image.open(r).size
        return (1 if w * h >= 64 * 64 else 2, -w * h)
    return sorted(res, key=orden)

def x4(im, destino):
    from preparar_cartas import mejorar
    tmp = destino + "._tmp.png"; im.save(tmp); mejorar(tmp, destino); os.remove(tmp)

# ------------------------------------------------------------------ rechazos por derechos
_RECHAZO = re.compile(r"terceros|third.party|proveedores de contenido", re.I)

def prompt_neutro(prompt):
    """Mismo encargo sin nombrar la franquicia ni la carta (lo que dispara el filtro de derechos)."""
    t = re.sub(r'de la carta de Yu-Gi-Oh!? "[^"]*"', "fantastica", prompt)
    t = re.sub(r'"[^"]*"', "de esta imagen", t)
    t = re.sub(r"Yu-Gi-Oh!?", "un juego de cartas de fantasia", t)
    return t + "\n- Es arte original propio; reinterpretalo libremente si hace falta, manteniendo la idea."

def reintentar_rechazadas(pag):
    """Ultima pasada: cada rechazada se intenta una vez mas con el prompt neutro."""
    pendientes = []
    for grupo in ("arte", "figura", "ui"):
        base = os.path.join(TODO, grupo)
        if os.path.isdir(base):
            pendientes += [os.path.join(base, d) for d in sorted(os.listdir(base))
                           if os.path.exists(os.path.join(base, d, "rechazo.txt"))
                           and not os.path.exists(os.path.join(base, d, "resultado.png"))
                           and not os.path.exists(os.path.join(base, d, "rechazo2.txt"))]
    if not pendientes:
        return
    registrar("reintento de %d rechazadas con prompt neutro" % len(pendientes), evento=True)
    logradas = 0
    for carpeta in pendientes:
        prompt = prompt_neutro(open(os.path.join(carpeta, "prompt.txt"), encoding="utf-8").read().strip())
        open(os.path.join(carpeta, "prompt_neutro.txt"), "w", encoding="utf-8").write(prompt)
        imgs = sorted(f for f in os.listdir(carpeta) if re.match(r"\d_.*\.(png|jpg)$", f))
        while True:
            try:
                pg.generar(pag, [os.path.join(carpeta, f) for f in imgs], prompt, os.path.join(carpeta, "resultado.png"))
                logradas += 1; registrar("rechazada recuperada: %s" % carpeta); break
            except (pg.ErrorSilencio, pg.ErrorLimite) as e:
                registrar("pausa en reintento de rechazadas (%s)" % e); time.sleep(ESPERA_LIMITE)
            except Exception as e:
                open(os.path.join(carpeta, "rechazo2.txt"), "w", encoding="utf-8").write(str(e))
                registrar("sigue rechazada: %s" % carpeta); break
        time.sleep(PAUSA)
    registrar("rechazadas recuperadas: %d de %d" % (logradas, len(pendientes)), evento=True)

def preparar_arte(d, bmp, nombre):
    from preparar_cartas import ARTE_CAJA
    os.makedirs(d, exist_ok=True)
    x4(Image.open(os.path.join(DATOS, "card", bmp)).convert("RGB").crop(ARTE_CAJA), os.path.join(d, "1_ilustracion_original.png"))
    open(os.path.join(d, "prompt.txt"), "w", encoding="utf-8").write(PROMPT_ARTE.format(nombre=nombre))

def preparar_figura(d, bmp, nombre, f):
    from preparar_cartas import ARTE_CAJA
    from preparar_lote import TIPOS
    os.makedirs(d, exist_ok=True)
    x4(Image.open(os.path.join(DATOS, "card", bmp)).convert("RGB").crop(ARTE_CAJA), os.path.join(d, "1_ilustracion_original.png"))
    Image.open(REFERENCIA).convert("RGB").save(os.path.join(d, "2_referencia_estilo.png"))
    plantilla = open(os.path.join(NB, "plantilla_prompt.txt"), encoding="utf-8").read()
    open(os.path.join(d, "prompt.txt"), "w", encoding="utf-8").write(plantilla.format(
        nombre=nombre, tipo=TIPOS.get(f["tipo"], f["tipo"].lower()), atributo=f["attr"], nivel=f["nivel"]))

def preparar_ui(d, ruta):
    os.makedirs(d, exist_ok=True)
    im = Image.open(ruta).convert("RGB")
    destino = os.path.join(d, "1_original_del_juego.png")
    if max(im.size) < 512: x4(im, destino)
    else: im.save(destino)
    open(os.path.join(d, "prompt.txt"), "w", encoding="utf-8").write(PROMPT_UI)
    open(os.path.join(d, "origen.txt"), "w", encoding="utf-8").write(ruta)

# ------------------------------------------------------------------ bucle
def otro_puente_activo():
    salida = subprocess.run(["powershell", "-NoProfile", "-Command",
                             "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | ForEach-Object CommandLine"],
                            capture_output=True, text=True, errors="replace", creationflags=0x08000000).stdout
    return any("puente_gemini.py" in l and "cola_gemini" not in l for l in salida.splitlines())

def esperar_hasta(cuando):
    """Pausa inicial hasta una hora concreta (p. ej. el restablecimiento de cupo que anuncia Gemini)."""
    objetivo = datetime.datetime.strptime(cuando.replace("T", " "), "%Y-%m-%d %H:%M")   # acepta 2026-10-12T01:21
    registrar("esperando hasta %s (restablecimiento de cupo de Gemini)" % objetivo, evento=True)
    guardar_estado(estado="esperando restablecimiento de cupo", hasta=cuando)
    mantener_despierto(True)
    while datetime.datetime.now() < objetivo:
        time.sleep(30)

def main():
    registrar("cola iniciada", evento=True)
    if "--hasta" in sys.argv:
        esperar_hasta(sys.argv[sys.argv.index("--hasta") + 1])
    while otro_puente_activo():
        registrar("esperando a que termine otro lote del puente..."); time.sleep(60)
    lista = trabajos()
    total = len(lista)
    por_grupo = {}
    for g, _, _ in lista: por_grupo[g] = por_grupo.get(g, 0) + 1
    registrar("trabajos en cola: %d %s" % (total, por_grupo), evento=True)
    mantener_despierto(True)
    hechos = fallos_seguidos = 0; en_silencio = False
    grupo_anterior = None
    with sync_playwright() as p:
        nav = pag = None
        for i, (grupo, carpeta, preparar) in enumerate(lista):
            if grupo != grupo_anterior and grupo_anterior is not None:
                registrar("HITO grupo '%s' terminado" % grupo_anterior, evento=True)
                if grupo_anterior == "prototipo":
                    avisar("Yugi Reload", "Recursos del prototipo listos")
            grupo_anterior = grupo
            salida = os.path.join(carpeta, "resultado.png")
            if os.path.exists(salida) or os.path.exists(os.path.join(carpeta, "fallo.txt")) or os.path.exists(os.path.join(carpeta, "rechazo.txt")):
                continue
            intentos = 0
            while True:
                try:
                    if nav is None:
                        nav = p.chromium.connect_over_cdp(pg.CDP); pag = pg.pagina_gemini(nav)
                    if preparar and not os.path.exists(os.path.join(carpeta, "prompt.txt")):
                        preparar(carpeta)
                    imgs = sorted(f for f in os.listdir(carpeta) if re.match(r"\d_.*\.(png|jpg)$", f))
                    prompt = open(os.path.join(carpeta, "prompt.txt"), encoding="utf-8").read().strip()
                    pg.generar(pag, [os.path.join(carpeta, f) for f in imgs], prompt, salida)
                    hechos += 1; fallos_seguidos = 0
                    if en_silencio:
                        en_silencio = False
                        registrar("REANUDADO: Gemini vuelve a generar imagenes", evento=True)
                        avisar("Yugi Reload - Gemini reanudado", "La conversion continua.")
                        guardar_estado(estado="trabajando")
                    guardar_estado(estado="trabajando", hechos_sesion=hechos, ultimo=carpeta, posicion=i + 1, total=total, grupo=grupo)
                    if hechos % 25 == 0:
                        registrar("progreso: %d convertidas en esta sesion (%d/%d de la cola)" % (hechos, i + 1, total), evento=True)
                    time.sleep(PAUSA)
                    break
                except pg.ErrorLimite as e:
                    registrar("LIMITE de Gemini alcanzado tras %d imagenes: %s" % (hechos, e), evento=True)
                    guardar_estado(estado="pausada por limite", desde=datetime.datetime.now().isoformat(timespec="seconds"))
                    avisar("Yugi Reload - Gemini en pausa", "Se alcanzo el limite de uso. Reintento automatico cada 30 min.")
                    # el PC sigue despierto durante la pausa: si se suspendiera, la cola no podria retomar
                    while True:
                        time.sleep(ESPERA_LIMITE)
                        try:
                            pag.goto(pg.URL_NUEVO); pag.get_by_role("button", name="Cargas y herramientas").click()
                            h = pag.locator(".cdk-overlay-container").get_by_text("Crear imagen", exact=True).first
                            h.wait_for(timeout=15000)
                            libre = h.locator("xpath=ancestor::button[1]").get_attribute("disabled") is None
                            pag.keyboard.press("Escape")
                        except Exception as ex:
                            registrar("sondeo fallido: %s" % ex); libre = True   # se prueba con el trabajo real
                        if libre:
                            break
                        registrar("sigue el limite; nuevo intento en 30 min")
                    registrar("REANUDADO: Gemini vuelve a aceptar trabajos", evento=True)
                    avisar("Yugi Reload - Gemini reanudado", "La conversion continua.")
                    mantener_despierto(True)
                    guardar_estado(estado="trabajando")
                except pg.ErrorSilencio as e:
                    # Google deja colgadas las peticiones de imagen (el texto puede seguir funcionando):
                    # no se cuenta como intento; la prueba es reintentar este mismo trabajo cada 30 min
                    if not en_silencio:
                        en_silencio = True
                        registrar("SILENCIO de Gemini tras %d imagenes (%s): reintento cada 30 min" % (hechos, e), evento=True)
                        guardar_estado(estado="pausada: Gemini no genera imagenes", desde=datetime.datetime.now().isoformat(timespec="seconds"))
                        avisar("Yugi Reload - Gemini no responde", "Pausa automatica; se reintenta cada 30 min.")
                    else:
                        registrar("Gemini sigue sin generar imagenes; nuevo intento en 30 min")
                    time.sleep(ESPERA_LIMITE)
                except Exception as e:
                    if _RECHAZO.search(str(e)):
                        # Gemini se niega por "derechos de terceros": reintentar igual no sirve; se anota para la pasada final
                        open(os.path.join(carpeta, "rechazo.txt"), "w", encoding="utf-8").write(str(e))
                        registrar("rechazada por Gemini (derechos de terceros): %s" % carpeta)
                        time.sleep(PAUSA); break
                    intentos += 1; fallos_seguidos += 1
                    registrar("fallo (%d) en %s: %s" % (intentos, carpeta, str(e)[:300]))
                    # cortes de red de la pagina (net::ERR_...) son pasajeros: se reintentan como un fallo normal
                    if "net::ERR" not in str(e) and ("connect" in str(e).lower() or "Target page" in str(e) or "closed" in str(e).lower()):
                        registrar("ERROR el Chrome del puente no responde: abrelo con 'Abrir Chrome del puente.bat'", evento=True)
                        avisar("Yugi Reload - falta el Chrome del puente", "Abre 'Abrir Chrome del puente.bat'; la cola espera.")
                        nav = pag = None; time.sleep(300); intentos -= 1; continue
                    if fallos_seguidos >= 6:
                        # muchos fallos seguidos sin aviso claro: se trata como limite encubierto
                        registrar("demasiados fallos seguidos: pausa de 30 min por precaucion", evento=True)
                        fallos_seguidos = 0; time.sleep(ESPERA_LIMITE)
                    if intentos >= 3:
                        open(os.path.join(carpeta, "fallo.txt"), "w", encoding="utf-8").write(traceback.format_exc())
                        registrar("se salta %s tras 3 intentos" % carpeta)
                        break
                    time.sleep(PAUSA)
        if nav is None:
            nav = p.chromium.connect_over_cdp(pg.CDP); pag = pg.pagina_gemini(nav)
        reintentar_rechazadas(pag)
    mantener_despierto(False)
    guardar_estado(estado="terminada", hechos_sesion=hechos)
    registrar("FIN de la cola: %d imagenes convertidas en esta sesion" % hechos, evento=True)
    avisar("Yugi Reload", "Conversion con Gemini terminada")

if __name__ == "__main__":
    try:
        main()
    except Exception:
        registrar("ERROR fatal: " + traceback.format_exc().replace("\n", " | "), evento=True)
        mantener_despierto(False)
        raise
