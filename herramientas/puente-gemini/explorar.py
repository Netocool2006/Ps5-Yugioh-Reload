# Exploracion de la pagina de Gemini en el Chrome del puente: captura y elementos interactivos.
import json, os, sys
sys.path.insert(0, r"D:\Yugi-Reload\herramientas\pylib")
from playwright.sync_api import sync_playwright

SALIDA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "exploracion")
os.makedirs(SALIDA, exist_ok=True)
with sync_playwright() as p:
    nav = p.chromium.connect_over_cdp("http://127.0.0.1:9333")
    pag = next(pg for c in nav.contexts for pg in c.pages if "gemini.google.com" in pg.url)
    print("url:", pag.url, "| titulo:", pag.title())
    pag.screenshot(path=os.path.join(SALIDA, "pagina.png"))
    elems = pag.evaluate("""() => [...document.querySelectorAll('button, a, [contenteditable=true], textarea, input, [role=button]')]
        .filter(e => e.offsetParent !== null)
        .map(e => ({tag: e.tagName, aria: e.getAttribute('aria-label'), texto: (e.innerText||'').trim().slice(0,40),
                    cls: (e.className||'').toString().slice(0,60), tipo: e.getAttribute('type'), mat: e.getAttribute('mattooltip')}))""")
    json.dump(elems, open(os.path.join(SALIDA, "elementos.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    for e in elems:
        print(e["tag"], "|", e["aria"], "|", e["texto"].replace("\n", " "), "|", e["cls"][:40])
    nav.close()  # solo cierra la conexion, no el navegador
