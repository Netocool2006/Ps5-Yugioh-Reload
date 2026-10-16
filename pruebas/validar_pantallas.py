# Valida el reconocedor de pantallas contra capturas etiquetadas a mano (exito = 100%).
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image
import flujo

ESPERADO = {
    "075003_titulo2": "demo", "075022_lp1": "demo", "075030_menu1": "demo",
    "075059_menu2": "menu_principal", "075120_mododuelo": "menu_principal", "080149_post3": "menu_principal",
    "075400_si_click": "submenu_duelo", "075411_individual": "submenu_duelo", "075443_individual3": "submenu_duelo",
    "075503_ind_enter": "retrato_inicio",
    "075515_duelo_ini": "janken", "075528_tras_janken": "janken", "075635_jk_despues": "janken", "075719_jk_space": "janken",
    "075729_jk_clic_piedra": "primero_segundo", "075801_duelo_campo2": "primero_segundo",
    "075843_pr1": "primero_segundo", "075744_duelo_campo": "primero_segundo",
    "075854_pr2": None, "080139_post2": None,
    "081259_camino_duelo": "construccion_deck", "082454_camino_duelo": None, "090706_o2": "opciones", "080029_lp0": "dialogo_repeticion", "090702_o1": "menu_principal", "091637_post_duelo": "robar_otra", "100736_hacia_menu": "intercambiar_cartas", "080046_post_win": None,
}
bien = 0
for k, e in ESPERADO.items():
    n, d1, d2 = flujo.clasificar(Image.open(os.path.join(flujo.REF, "..", "capturas", k + ".png")).convert("RGB"))
    bien += n == e
    print("%-22s esperado=%-17s obtenido=%-17s %.3f / %.3f %s" % (k, e, n, d1, d2, "" if n == e else "<<< ERROR"))
print("aciertos %d/%d" % (bien, len(ESPERADO)))
sys.exit(0 if bien == len(ESPERADO) else 1)
