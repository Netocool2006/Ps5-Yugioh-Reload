# Explora (sin enviar nada) por que "Crear video" aparece deshabilitado: captura el menu y su aviso.
import os, sys, time
sys.path.insert(0, r"D:\Yugi-Reload\herramientas\pylib")
sys.stdout.reconfigure(encoding="utf-8")
from playwright.sync_api import sync_playwright

SALIDA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "exploracion")
with sync_playwright() as p:
    nav = p.chromium.connect_over_cdp("http://127.0.0.1:9333")
    pag = next(pg for c in nav.contexts for pg in c.pages if "gemini.google.com" in pg.url)
    pag.bring_to_front()
    pag.goto("https://gemini.google.com/app"); time.sleep(3)
    pag.get_by_role("button", name="Cargas y herramientas").click(); time.sleep(1)
    item = pag.locator(".cdk-overlay-container").get_by_text("Crear video", exact=True).first
    boton = item.locator("xpath=ancestor::button[1]")
    print("aria:", boton.get_attribute("aria-label"), "| disabled:", boton.get_attribute("disabled"), boton.get_attribute("aria-disabled"))
    print("texto del item:", boton.inner_text().strip().replace("\n", " / "))
    item.hover(force=True); time.sleep(1.5)
    print("avisos:", [t.inner_text() for t in pag.locator(".mdc-tooltip, [role=tooltip], .mat-mdc-tooltip").all()])
    pag.screenshot(path=os.path.join(SALIDA, "menu_video.png"), timeout=60000)
    pag.keyboard.press("Escape")
    nav.close()
