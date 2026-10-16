# Abre (sin enviar nada) el menu "+" y el selector de modo de Gemini y lista sus opciones.
import os, sys, time
sys.path.insert(0, r"D:\Yugi-Reload\herramientas\pylib")
sys.stdout.reconfigure(encoding="utf-8")
from playwright.sync_api import sync_playwright

SALIDA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "exploracion")
OPCIONES = "[role=menuitem], [role=menuitemradio], [role=option], mat-option, .mat-mdc-menu-item, button"

def listar(pag, nombre):
    time.sleep(1.2)
    pag.screenshot(path=os.path.join(SALIDA, nombre + ".png"))
    capa = pag.locator(".cdk-overlay-container")
    for e in capa.locator(OPCIONES).all():
        if e.is_visible():
            print("  -", (e.get_attribute("aria-label") or "").strip(), "|", e.inner_text().strip().replace("\n", " / ")[:80])

with sync_playwright() as p:
    nav = p.chromium.connect_over_cdp("http://127.0.0.1:9333")
    pag = next(pg for c in nav.contexts for pg in c.pages if "gemini.google.com" in pg.url)
    print("menu '+' (Cargas y herramientas):")
    pag.get_by_role("button", name="Cargas y herramientas").click()
    listar(pag, "menu_mas")
    pag.keyboard.press("Escape"); time.sleep(0.5)
    print("selector de modo:")
    pag.locator("button[aria-label^='Abrir el selector de modo']").click()
    listar(pag, "menu_modo")
    pag.keyboard.press("Escape")
    nav.close()
