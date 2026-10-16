# Puente a Gemini (Nano Banana) por navegador: usa la web de Gemini en el Chrome del puente (perfil propio en D:,
# sesion iniciada a mano) como lo haria una persona: chat nuevo -> "Crear imagen" -> sube las imagenes -> pega el
# prompt -> espera el resultado -> lo descarga a tamano completo. Sin API ni claves: usa la suscripcion.
# Requisito: "Abrir Chrome del puente.bat" abierto (puerto local 9333).
#
# Uso:  python -I puente_gemini.py --img entrada.png [--img referencia.png] --prompt-file prompt.txt --out salida.png
#       python -I puente_gemini.py --video --img figura.png --prompt-file prompt.txt --out salida.mp4   (Veo)
#       python -I puente_gemini.py --lote CARPETA  (cada subcarpeta: imagenes 1_*.png 2_*.png..., prompt.txt -> resultado.png)
import argparse, glob, logging, os, random, sys, time
sys.path.insert(0, r"D:\Yugi-Reload\herramientas\pylib")
sys.stdout.reconfigure(encoding="utf-8")
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

BASE = os.path.dirname(os.path.abspath(__file__))
DEPURACION = os.path.join(BASE, "depuracion")
CDP = "http://127.0.0.1:9333"
URL_NUEVO = "https://gemini.google.com/app"
ESPERA_MAX = 240          # segundos maximos por imagen
PAUSA_ENTRE = (20, 20)    # pausa entre imagenes de un lote (segundos, elegida por el usuario)

os.makedirs(DEPURACION, exist_ok=True)
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(message)s",
                    handlers=[logging.FileHandler(os.path.join(BASE, "puente.log"), encoding="utf-8"),
                              logging.StreamHandler(sys.stdout)])
log = logging.getLogger("puente")
logging.getLogger("asyncio").setLevel(logging.WARNING)

class ErrorPuente(Exception):
    pass

class ErrorSilencio(ErrorPuente):
    """Gemini acepta el envio pero no contesta nada (bloqueo temporal encubierto)."""

class ErrorLimite(ErrorPuente):
    """Gemini no deja generar mas por ahora (cupo agotado): hay que esperar, no reintentar en bucle."""
    pass

import re as _re
_LIMITE = _re.compile(r"l[ií]mite|limit|cuota|quota|m[aá]s tarde|later|alcanzaste|alcanzado|reached|"
                      r"no puedo (crear|generar) m[aá]s|try again|vuelve a intentar", _re.I)

def foto(pag, nombre):
    ruta = os.path.join(DEPURACION, time.strftime("%H%M%S_") + nombre + ".png")
    try:
        pag.screenshot(path=ruta); log.debug("captura %s", ruta)
    except Exception as e:
        log.debug("no se pudo capturar %s: %s", nombre, e)

def pagina_gemini(nav):
    for ctx in nav.contexts:
        for pg in ctx.pages:
            if "gemini.google.com" in pg.url:
                return pg
    pg = nav.contexts[0].new_page(); pg.goto(URL_NUEVO); return pg

ESPERA_VIDEO = 900        # Veo tarda bastante mas que una imagen

def imagenes_respuesta(pag, video=False):
    """Imagenes (o videos) generados visibles en las respuestas del modelo (src unicos)."""
    if video:
        return pag.evaluate("""() => [...document.querySelectorAll('model-response video, model-response video source')]
            .map(v => v.currentSrc || v.src).filter(s => s)""")
    return pag.evaluate("""() => [...document.querySelectorAll('model-response img, generated-image img, single-image img')]
        .filter(i => i.naturalWidth >= 256 && i.offsetParent !== null).map(i => i.src)""")

def generar(pag, imagenes, prompt, salida, video=False):
    log.info("== generar %s (%s) con %d imagen(es)", os.path.basename(salida), "video" if video else "imagen", len(imagenes))
    pag.goto(URL_NUEVO); pag.wait_for_load_state("domcontentloaded")
    editor = pag.locator("div.ql-editor[contenteditable=true]").first
    editor.wait_for(timeout=30000)
    # herramienta "Crear imagen" (Nano Banana) o "Crear video" (Veo)
    # desde "Gemini 4" la pagina tarda en llenar el menu: si sale vacio se cierra y se vuelve a abrir
    nombre_h = "Crear video" if video else "Crear imagen"
    herramienta = pag.locator(".cdk-overlay-container").get_by_text(nombre_h, exact=True).first
    for intento in range(4):
        pag.get_by_role("button", name="Cargas y herramientas").click()
        try:
            herramienta.wait_for(timeout=15000)
            break
        except Exception:
            if intento == 3:
                raise
            log.debug("menu de herramientas vacio, reintento %d", intento + 1)
            pag.keyboard.press("Escape")
            time.sleep(5)
    if herramienta.locator("xpath=ancestor::button[1]").get_attribute("disabled") is not None:
        pag.keyboard.press("Escape")
        raise ErrorLimite("la herramienta '%s' esta deshabilitada (cupo agotado?)" % nombre_h)
    herramienta.click()
    time.sleep(1.0)
    # subir las imagenes (entrada + referencias)
    for ruta in imagenes:
        pag.get_by_role("button", name="Cargas y herramientas").click()
        with pag.expect_file_chooser(timeout=15000) as fc:
            pag.locator(".cdk-overlay-container").get_by_text("Subir archivos", exact=True).first.click()
        fc.value.set_files(os.path.abspath(ruta))
        log.debug("subida %s", ruta)
        time.sleep(2.0)
    previas = set(imagenes_respuesta(pag, video))
    editor.click()
    pag.keyboard.insert_text(prompt)
    # el boton de enviar aparece con texto y queda bloqueado mientras suben los adjuntos: se espera a que se habilite
    enviar = pag.locator("button[aria-label*='Enviar'], button.send-button").first
    t0 = time.time()
    while time.time() - t0 < 60:
        if enviar.count() and enviar.is_enabled() and enviar.get_attribute("aria-disabled") != "true":
            break
        time.sleep(1)
    log.debug("adjuntos listos en %.0f s", time.time() - t0)
    foto(pag, "adjuntos")
    enviar.click()
    espera = ESPERA_VIDEO if video else ESPERA_MAX
    log.info("prompt enviado; esperando el %s (max %d s)", "video" if video else "resultado", espera)
    t0 = time.time(); nueva = None; ultimo_log = 0
    while time.time() - t0 < espera:
        time.sleep(3)
        nuevas = [s for s in imagenes_respuesta(pag, video) if s not in previas]
        detener = pag.locator("button[aria-label*='Detener'], button[aria-label*='Stop']").count()
        if nuevas and (video or not detener):
            nueva = nuevas[-1]; break
        if time.time() - t0 > 90 and not pag.locator("model-response").count():
            foto(pag, "silencio")
            raise ErrorSilencio("Gemini no responde nada a los 90 s (peticion colgada)")
        if time.time() - ultimo_log > 60:
            ultimo_log = time.time(); foto(pag, "esperando")
            log.debug("esperando %.0f s...", time.time() - t0)
    if not nueva:
        foto(pag, "sin_resultado")
        texto = pag.locator("model-response").last.inner_text() if pag.locator("model-response").count() else ""
        if _LIMITE.search(texto):
            raise ErrorLimite("Gemini indica limite: " + texto[:300])
        if not texto.strip():
            raise ErrorSilencio("Gemini no devolvio nada en %d s" % espera)
        raise ErrorPuente("Gemini no devolvio %s en %d s. Respuesta: %s" % ("video" if video else "imagen", espera, texto[:400]))
    log.info("%s recibido en %.0f s", "video" if video else "resultado", time.time() - t0)
    time.sleep(5 if video else 2)
    foto(pag, "resultado")
    descargar(pag, nueva, salida, video)
    return salida

def responde(pag, espera=90):
    """Sondeo barato: un chat de texto. True si Gemini contesta algo."""
    pag.goto(URL_NUEVO); pag.wait_for_load_state("domcontentloaded")
    editor = pag.locator("div.ql-editor[contenteditable=true]").first
    editor.wait_for(timeout=30000); editor.click()
    pag.keyboard.insert_text("Responde solo con la palabra: ok")
    time.sleep(1); pag.keyboard.press("Enter")
    t0 = time.time()
    while time.time() - t0 < espera:
        time.sleep(3)
        r = pag.locator("model-response")
        if r.count() and r.last.inner_text().strip():
            return True
    return False

def descargar(pag, src, salida, video=False):
    os.makedirs(os.path.dirname(os.path.abspath(salida)), exist_ok=True)
    # 1) boton de descarga a tamano completo de la propia web
    img = (pag.locator("model-response video").last if video else
           pag.locator("model-response img[src='%s'], generated-image img[src='%s']" % (src, src)).last)
    try:
        img.hover(); time.sleep(0.8)
        boton = pag.locator("button[aria-label*='Descargar'], button[aria-label*='Download']").last
        with pag.expect_download(timeout=60000) as dl:
            boton.click()
        dl.value.save_as(salida)
        log.info("descargada (tamano completo) -> %s", salida)
        return
    except Exception as e:
        log.warning("descarga por boton fallo (%s); se toma la imagen mostrada", e)
    # 2) respaldo: los bytes de la imagen mostrada, leidos dentro de la pagina (misma sesion)
    datos = pag.evaluate("""async (src) => { const r = await fetch(src); const b = new Uint8Array(await r.arrayBuffer());
        let s = ''; for (let i = 0; i < b.length; i += 32768) s += String.fromCharCode(...b.subarray(i, i + 32768)); return btoa(s); }""", src)
    import base64
    open(salida, "wb").write(base64.b64decode(datos))
    log.info("descargada (imagen mostrada) -> %s", salida)

def trabajos_de_lote(carpeta):
    for sub in sorted(glob.glob(os.path.join(carpeta, "*", ""))):
        prompt = os.path.join(sub, "prompt.txt")
        imgs = sorted(glob.glob(os.path.join(sub, "[0-9]_*.*")))
        if os.path.exists(prompt) and imgs:
            yield imgs, open(prompt, encoding="utf-8").read().strip(), os.path.join(sub, "resultado.png")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--img", action="append", default=[])
    ap.add_argument("--prompt-file"); ap.add_argument("--out")
    ap.add_argument("--lote"); ap.add_argument("--rehacer", action="store_true", help="en lote, regenera aunque exista resultado")
    ap.add_argument("--video", action="store_true", help="usa 'Crear video' (Veo) en vez de 'Crear imagen'")
    a = ap.parse_args()
    trabajos = list(trabajos_de_lote(a.lote)) if a.lote else [(a.img, open(a.prompt_file, encoding="utf-8").read().strip(), a.out)]
    with sync_playwright() as p:
        try:
            nav = p.chromium.connect_over_cdp(CDP)
        except Exception:
            log.error("no encuentro el Chrome del puente: abre 'Abrir Chrome del puente.bat' e inicia sesion en Gemini")
            return 2
        pag = pagina_gemini(nav)
        ok = 0
        for i, (imgs, prompt, out) in enumerate(trabajos):
            if os.path.exists(out) and not a.rehacer:
                log.info("ya existe %s: se salta", out); continue
            try:
                generar(pag, imgs, prompt, out, a.video); ok += 1
            except (ErrorPuente, PWTimeout) as e:
                log.error("fallo %s: %s", out, e); foto(pag, "error")
            if i < len(trabajos) - 1:
                time.sleep(random.uniform(*PAUSA_ENTRE))
        log.info("listo: %d/%d imagenes", ok, len(trabajos))
        nav.close()
    return 0 if ok == len(trabajos) else 1

if __name__ == "__main__":
    sys.exit(main())
