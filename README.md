# Yugi Reload

**Proyecto personal de nostalgia** sobre *Yu-Gi-Oh! Power of Chaos: Joey the Passion* (Konami, 2004).
Tiene dos partes:

1. **El mod del juego original para PC**: más rivales, una CPU con personalidad, una dificultad que se
   adapta al jugador y la colección completa, sin tocar el juego más de lo necesario.
2. **El remake para PS5** (homebrew): un tablero 3D moderno estilo serie, con Vulkan, donde **los
   monstruos aparecen en 3D de pie sobre su carta**, se mueven y pelean entre ellos.

> Proyecto sin fines de lucro y sin distribución. **Este repositorio no incluye nada de Konami**: ni el
> juego, ni sus imágenes, ni sus datos. Para usar el mod hace falta tener el juego original.
> Yu-Gi-Oh! © Kazuki Takahashi / Konami.

---

## Objetivo

Revivir el *Power of Chaos* con el que crecimos y llevarlo a 2026:

- **En PC:** que el juego original se sienta nuevo. Más de 600 rivales distintos, una CPU que cambia
  de forma de jugar en cada duelo y una dificultad que sube o baja según cómo te va.
- **En PS5:** un remake con el mismo duelo, pero con monstruos en 3D que atacan, se defienden y caen
  según cómo es cada carta (un mago lanza magia, un dragón escupe fuego, una máquina dispara, un
  monstruo de agua lanza una ráfaga de agua...).

## En números

| | Juego original | Con Yugi Reload |
|---|---|---|
| Mazos rivales de la CPU | **58** (21 por nivel + 37 de torneo) | **604** (58 originales + **546 nuevos**) |
| Formas de jugar de la CPU | 1 (siempre igual) | **7 temperamentos**: agresivo, tortuga, pirómano, tramposo, clásico, caótico y legendario |
| Dificultad | Fija por nivel del juego | **4 niveles de mazo (tiers 0-3)** y **nivel elástico**: sube si ganas seguido, baja si pierdes |
| Torneo (mazos `ful_*`) | Siempre los mismos 37 | **Se rebarajan en cada sesión** desde la biblioteca |
| Colección | Se desbloquea jugando | Opción de desbloquear las 771 cartas (×3), **sin forzar** la opción "todo el set / solo Joey" del jugador |
| Cartas basura en mazos CPU | 0 | **0**: se quitaron las 2 715 entradas basura que se habían colado (ver [cartas](docs/02-cartas.md)) |
| Pruebas automáticas | — | **116 casos** (datos, mazos, lanzador, memoria, proceso vivo, frontend y restauración) |
| Monstruos en 3D | — | **8 con modelo 3D** (6 ya en el tablero: Mago Oscuro, Maga Oscura, Guardián Celta, Kuriboh, Bebé Dragón y Ojos Rojos) y **496 clasificados** para producir |
| Reglas de combate 3D | — | **19 reglas** (12 del Excel de reglas del proyecto + 7 propuestas a revisar) y un **motor de reglas** con 11 ya programadas |

## Cartas del juego

| | Cartas |
|---|---|
| Espacios en la base de datos del juego | 1 110 (hay 12 repetidas) |
| **Cartas distintas** | **1 098** |
| **Cartas del juego (lo que el jugador puede juntar)** | **771** (768 sin repetir): 496 monstruos, 172 magias, 100 trampas. **Todas con ilustración** |
| Entradas basura del desarrollador | 330: nombre real, pero sin edición ni ilustración (el juego las dibuja como *Slime Token*) |

Detalle en [docs/02-cartas.md](docs/02-cartas.md).

## Documentación

| Documento | De qué trata |
|---|---|
| [01 · Mod del juego para PC](docs/01-mod-pc.md) | Ingeniería inversa, lanzador, biblioteca de 546 mazos, temperamentos, nivel elástico, desbloqueo y pruebas |
| [02 · Las cartas](docs/02-cartas.md) | 1 110 / 1 098 / 771 explicado, las entradas basura y cómo se limpiaron |
| [03 · Remake PS5](docs/03-remake-ps5.md) | Motor Vulkan, tablero, cámara, personajes con esqueleto y despliegue a la consola |
| [04 · Monstruos 3D](docs/04-monstruos-3d.md) | Ciclo de producción: arte → Gemini → TRELLIS/Meshy → Blender → juego, y las 16 plantillas |
| [05 · Reglas de combate](docs/05-reglas-combate.md) | El Excel de reglas, la prioridad, las 19 reglas, el motor y los 5 rayos de los místicos |
| [06 · Bitácora](docs/06-bitacora.md) | Lo que se hizo, día por día |

## Estado (octubre de 2026)

- ✅ **Mod de PC** funcionando: lanzador v3, 546 mazos nuevos, 7 temperamentos, nivel elástico,
  colección desbloqueable, mazos de la CPU sin cartas basura, 93/93 pruebas sin el juego abierto y
  pruebas de frontend jugando duelos reales.
- ✅ **Remake en PS5** corriendo en la consola: tablero 3D, monstruos en 3D de frente al jugador,
  ataques con cámara de cine, Mago y Maga Oscura con báculo a dos manos y 5 rayos.
- ✅ **Producción de monstruos 3D gratis** con TRELLIS en Google Colab (Kuriboh ya en la PS5).
- 🔄 **Reglas de combate**: motor listo; dragón, animales, insectos, máquina, agua, roca y místicos
  programados y en revisión visual.
- ⏳ Pendiente: revisar las 7 reglas propuestas (demonio, zombi, piro, trueno, planta, espíritu y objeto),
  producir el resto de los 496 monstruos y el duelo completo en el remake.

## Cómo se trabaja

- Todo lo visual se revisa **como lo ve una persona**: videos cortos en el PC, tomas desde varios
  ángulos y acercamientos en 4 bloques. A la PS5 solo se sube cuando el dueño del proyecto lo pide.
- Una regla o plantilla a la vez: se hace, se prueba y se aprueba, y luego se reutiliza.
- Todas las herramientas viven en el disco D: y corren sin ventanas ni intervención.
