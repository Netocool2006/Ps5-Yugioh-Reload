#!/usr/bin/env bash
# Espera (hasta 3 h) a que el juego este cerrado en la PS5 y entonces actualiza PPSA77001 (vaciar + subir).
cd "$(dirname "$0")"
for i in $(seq 1 1080); do
    if python -I vaciar_titulo_ps5.py PPSA77001 > /tmp/vaciar.log 2>&1; then
        cat /tmp/vaciar.log
        python -I subir_ps5.py "D:/Docker/compartido/ps5/PPSA77001" 2>&1 | grep -v "igual, se salta" | tail -2 || true
        python -I subir_ps5.py "D:/Docker/compartido/ps5/PPSA77001" 2>&1 | tail -1
        echo "SUBIDO"; exit 0
    fi
    sleep 10
done
echo "EL JUEGO SIGUIO ABIERTO 3 HORAS"
