#!/usr/bin/env bash
# Ciclo completo sin manos (autorizado por el usuario durante el desarrollo):
#   espera a que el juego este cerrado -> sube D:/Docker/compartido/ps5/PPSA77001 -> carga yugictl si hace falta ->
#   abre el juego -> espera a que el juego SE CIERRE SOLO (capturas.txt debe traer cerrar_al_terminar), maximo 6 min
#   -> baja fotos/video/inspeccion, arma hojas y cuadrantes, y borra todo en la PS5 (fotos_ps5.py).
# Nunca espera algo que quiza no llegue: el fin del ciclo lo marca el cierre del juego o el tope de tiempo.
cd "$(dirname "$0")"
for i in $(seq 1 60); do
    python -I vaciar_titulo_ps5.py PPSA77001 > /tmp/vaciar.log 2>&1 && break
    sleep 10
done
cat /tmp/vaciar.log
python -I subir_ps5.py "D:/Docker/compartido/ps5/PPSA77001" 2>&1 | tail -1
python -I subir_ps5.py "D:/Docker/compartido/ps5/PPSA77001" 2>&1 | tail -1
sleep 15   # que ShadowMountPlus vea la carpeta actualizada
python -I yugictl/yugictl_cliente.py abrir --cargar
sleep 20   # que arranque
for i in $(seq 1 34); do
    estado=$(python -I yugictl/yugictl_cliente.py status 2>&1 | tail -1)
    [[ $estado == "ok idle"* ]] && { echo "el juego se cerro solo"; break; }
    sleep 10
done
[[ $estado == "ok idle"* ]] || echo "AVISO: el juego no se cerro en 6 minutos; se bajan igual las fotos"
python -I fotos_ps5.py
echo "CICLO TERMINADO (revisar, escribir informe y luego: python -I limpiar_revision.py)"
