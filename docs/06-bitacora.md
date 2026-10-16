# 06 · Bitácora

## 10–11 oct 2026 · El mod del juego original
- Ingeniería inversa con Ghidra; mapa del juego (contenedor, mazos, partida, memoria de la IA).
- Generador de mazos: **546 mazos nuevos** inyectados en `Data.dat` (de 58 a 604 rivales).
- Lanzador v3: 7 temperamentos, nivel elástico, torneo rebarajado, diales de la IA en memoria.
- Partida descifrada: colección desbloqueable sin forzar las opciones del jugador.
- Reequilibrio: ningún mazo pasa el ATK medio de 1 467 (197 ajustados).
- Batería de pruebas con duelos reales jugados solos.
- Primeras pruebas "estilo 2026" con Godot y con raylib.

## 12 oct · Gemini, Unreal y los primeros modelos 3D
- Cola automática de Gemini: arte, figuras 3D e interfaz, todo en español.
- Prueba en Unreal Engine 5: gustó la cámara de cine, que se adoptó como cámara de juego.
- Primeros modelos 3D (Kuriboh, Mago Oscuro, Bebé Dragón, Ojos Rojos).

## 13–14 oct · PS5 con Vulkan
- "Hola mundo" en la PS5 y luego el tablero completo con **Vulkan** (homebrew `PPSA77001`).
- Blender sin ventana para limpiar y optimizar modelos.

## 15 oct · Personajes con esqueleto
- Mago Oscuro con el báculo a dos manos por cinemática inversa y rayo eléctrico desde la punta.
- **Maga Oscura** hecha en ~16 min con la plantilla del Mago.
- Todos de frente al jugador; se dan vuelta para atacar.
- Tablero ×1.4 y **tamaños lógicos** para todas las cartas; Kuriboh rehecho.

## 16 oct · TRELLIS, plantillas, cartas y reglas de combate
- **TRELLIS en Google Colab**: monstruos 3D gratis. Kuriboh hecho con TRELLIS y subido a la PS5.
- **16 plantillas** y clasificación de los 496 monstruos usables.
- Conteo exacto de cartas (1 110 / 1 098 / 771) y descubrimiento de las 330 entradas basura.
- **Limpieza de los mazos de la CPU**: 2 715 cartas basura cambiadas por reales; 93/93 pruebas y 4/4
  duelos de frontend.
- **Excel de reglas de combate** interpretado: 19 reglas, prioridad y color según quién ataca.
- Místicos: 5 rayos al azar (eléctrico, esfera, láser, anillos, espiral) y defensa con el báculo.
- **Motor de reglas** con un archivo por regla; dragón, animales, insectos, máquina, agua y roca escritos
  en paralelo e integrados.
