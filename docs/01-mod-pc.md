# 01 · Mod del juego original para PC

*Yu-Gi-Oh! Power of Chaos: Joey the Passion* (2004) es un ejecutable de 32 bits (`Joey_Pc.exe`) y un
contenedor de datos (`Data.dat`, ~320 MB). El mod no reemplaza el juego: le agrega mazos al contenedor y,
mientras se juega, ajusta en memoria cómo decide la CPU.

## 1. Ingeniería inversa

- Herramienta: **Ghidra** con extensiones y scripts propios, para buscar qué rutina hace cada cosa.
- Resultado: un **mapa del juego** con archivos, formato de `Data.dat`, formato de mazos `.ydc`,
  partida guardada, parámetros de línea de comandos, direcciones de memoria de la IA y flujo de pantallas.
- Hallazgos clave:
  - **`Data.dat`** (`KCEJYUGI`): índice de 3 592 entradas que **debe ir ordenado por nombre**, porque el
    juego busca con búsqueda binaria; algunas entradas van comprimidas con LZSS.
  - **Mazos `.ydc`**: cabecera + mazo principal + fusiones + side, con los ids de carta.
  - **58 mazos de la CPU**: 21 `cpu_0XY` (por nivel) + 37 `ful_*` (torneo).
  - **Tabla de rivales de la CPU** en memoria: 35 entradas (7 niveles × 5 mazos).
  - **Diales de la IA** en memoria: umbral para decidir si ataca y ATK mínimo para invocar en ataque.
  - **Partida** (`system.dat`): cifrado propio de 9 bits, descifrado para poder desbloquear la colección.
  - Parámetros del ejecutable: `-win` (ventana), `-speedy` (60 FPS), idiomas, etc.

## 2. Biblioteca de mazos: de 58 a 604 rivales

Se generaron **546 mazos nuevos** con un generador propio (`deck_gen.py`) y se inyectaron en `Data.dat`
como `cpu_100` … `cpu_645`, sin tocar los originales.

| Familia | Mazos | Idea |
|---|---|---|
| Tribales | 304 | Un tipo de monstruo: dragones, guerreros, magos, máquinas... |
| Variantes de los originales | 116 | Los mazos de Konami con otras cartas de su misma familia |
| Por atributo | 54 | Oscuridad, luz, fuego, agua, viento, tierra |
| Caos (draft) | 21 | Mezclas al azar con un poco de lógica |
| Temáticos | 51 | Exodia, muro-trampas, quemadura, control de mano, curación, flip-sorpresa |

Cada mazo tiene un **tier de dificultad** de 0 a 3: 103, 157, 158 y 128 mazos, respectivamente.
Además se **reequilibraron**: ningún mazo pasa el ATK medio de 1 467, que es el techo de los mazos
originales de Konami. Se ajustaron 197 cambiando monstruos por otros de su misma familia.

## 3. Lanzador v3: una CPU con personalidad

El lanzador (`yugi_reload.py`) prepara el `Data.dat` de la sesión, abre el juego y lo vigila:

- **7 temperamentos**, sorteados por duelo y fijos hasta que el duelo termina:

| Temperamento | Cómo juega |
|---|---|
| Agresivo | Acepta intercambios y ataques arriesgados; invoca cualquier cosa |
| Tortuga | Solo ataca con margen claro; solo invoca en ataque monstruos fuertes |
| Pirómano | Intercambia 1 por 1: quiere vaciarte el campo para quemar |
| Tramposo | Prudente al invocar; deja que sus flips y trampas trabajen |
| Clásico | La IA original, intacta |
| Caótico | Diales al azar en cada duelo |
| Legendario | Resiste mientras arma su combo |

- **Nivel elástico:** si ganas seguido, los rivales suben de tier; si pierdes, bajan.
- **Torneo rebarajado:** los 37 mazos de torneo se reemplazan en cada sesión por mazos de la biblioteca
  del tier que corresponde.
- **Respeta las opciones del jugador:** la opción del menú "todo el set / solo Joey" se registra y se
  respeta. Una versión anterior la revertía; se corrigió y se verificó en un duelo real.

## 4. Colección desbloqueable

`Desbloquear cartas.bat` deja las **771 cartas del juego ×3** en la colección. No toca el mazo ni la
opción "todo el set / solo Joey". Quedan fuera los dioses egipcios y las cartas promocionales, que el
juego no deja usar.

## 5. Limpieza de cartas basura (16-oct-2026)

Los mazos nuevos de la CPU tenían **2 715 entradas basura** en 531 mazos: cartas sin edición que el juego
dibuja como *Slime Token* pero que pelean con sus datos (ver [02 · Las cartas](02-cartas.md)). Se
cambiaron por cartas reales de las 771, de la misma tribu o atributo, nivel y fuerza parecidos, sin
pasar de 3 copias ni del techo de ATK. Hubo respaldo previo, simulacro y reconstrucción del contenedor,
y los generadores ya no pueden volver a meterlas.

## 6. Batería de pruebas (116 casos)

| Grupo | Qué prueba |
|---|---|
| D · Datos | El contenedor, los índices, las cartas |
| M · Mazos | Tamaños, copias, fusiones en su zona, **cero cartas basura**, cobertura ≥ 700 cartas |
| L · Lanzador | Sorteos, nivel elástico, temperamentos, parámetros |
| S · Memoria simulada | Escrituras de la tabla y los diales, restauración exacta |
| P · Partida | Cifrado, desbloqueo idempotente, respeta las opciones del jugador |
| V · Proceso vivo | El juego real arrancado: tabla, diales y memoria |
| G · Frontend | **Duelos reales jugados solos** por el menú: carga exacta de mazos, fusiones, torneo, salida limpia |
| R · Restauración | Deja la partida del jugador como estaba |

Último resultado: **93/93** sin el juego abierto, y **4/4** en frontend (duelo completo, mazo
`caos_00` exacto, mazo con fusiones y restauración).
