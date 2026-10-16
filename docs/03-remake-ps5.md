# 03 · Remake para PS5

## La idea

El duelo como en la serie: **cartas planas sobre la mesa y el monstruo en 3D, de pie encima de su
carta**. Los monstruos miran al jugador en reposo, se dan vuelta de frente al rival para atacar y
vuelven a su lugar. Todo se ve a 60/120 FPS en una PS5 con homebrew.

## Tecnología

| Pieza | Qué se usa |
|---|---|
| Gráficos | **Vulkan** sobre la plantilla *PS5 Vulkan Template* (MIT) |
| Lenguaje | C++17 |
| Compilación | Contenedor Docker con la cadena de PS5 homebrew; la misma fuente compila una **vista previa para PC** |
| Título en la consola | `PPSA77001` (homebrew), subido por FTP |
| Escena | Blender sin ventana arma el tablero (`tablero.glb`) y la posición y escala de cada monstruo (`escena.h`) |

Se probaron antes **Godot** (descartado: no existe para PS5 homebrew), **raylib/OpenGL** y **Unreal
Engine 5** (gustó la cámara de cine; su exportación a PS5 depende de material no oficial, que se
descartó). Quedó Vulkan.

## Qué hay en pantalla

- **Tablero ×1.4**, con mucho espacio entre cartas para que los monstruos no se pisen al caer.
- **Tapete, dorsos y marcos** generados con Gemini. Nada se copia del juego original.
- **Monstruos en 3D** con un contorno holográfico; flotan, respiran y se balancean. Kuriboh parpadea y
  da saltitos.
- **Tamaños lógicos** según una tabla de alturas: humano 1,8 m, Ojos Rojos 2,9 m, Bebé Dragón 1,2 m,
  Kuriboh 0,75 m. Las cartas sin dato usan una regla por tipo y nivel.
- **Sombras del sol** con un mapa de 4096.
- **Cámara de juego** tomada de la prueba en Unreal, con **cortes de cine en cada ataque**. La cámara
  elige el costado con la vista más despejada (cuenta el ancho real de cada monstruo) y se aleja con los
  atacantes grandes.

## Personajes con esqueleto

- **Mago Oscuro y Maga Oscura**: modelos con esqueleto. El báculo es un hueso propio que **sujetan con
  las dos manos** por cinemática inversa. Guardia, carga del hechizo hacia atrás, el báculo apunta al
  rival y vuelve, sin saltos.
  - **5 rayos**, uno al azar en cada ataque: eléctrico, esfera de energía, láser, anillos de energía y
    espiral.
  - **Defensa**: cruzan el báculo horizontal frente al pecho. **Derrota**: caen de espaldas y se
    desintegran.
- **Guardián Celta**: espada en la mano; se cubre con ella, no aguanta, cae y se desintegra.
- Los demás monstruos son **figuras rígidas**, que nunca se deforman, y se mueven con las
  [reglas de combate](05-reglas-combate.md).

## Flujo de trabajo

1. Se cambia el código o un modelo en el PC.
2. Se compila la PS5 y la vista previa de PC en Docker.
3. **Video corto en el PC** (960×540, VLC) y revisión visual, como lo ve una persona.
4. Solo cuando se pide: se vacía la carpeta del título en la consola, se sube por FTP y se verifica.
   Hay un freno que no sube si el juego está abierto.
