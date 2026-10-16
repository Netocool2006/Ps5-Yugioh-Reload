# 02 · Las cartas

## Cuántas cartas tiene el juego

| | Monstruos | Magias | Trampas | Dioses | Total |
|---|---|---|---|---|---|
| **Cartas distintas en los archivos** | 795 | 195 | 105 | 3 | **1 098** |
| ✅ Usables por el jugador | 496 | 172 | 100 | — | **768** |
| ❌ No usables (las mete la biblioteca de la CPU) | 269 | 19 | 5 | — | 293 |
| ❌ No usables (no las usa nadie) | 30 | 4 | — | 3 | 37 |

- La base de datos tiene **1 110 espacios**: 12 cartas aparecen 2 o 3 veces, como versiones con otra
  ilustración (por ejemplo, el Mago Oscuro aparece 3 veces).
- La **lista de cartas del juego marca 771**: son los espacios usables, que sin repetir dan **768**.
- **Las 771 tienen su ilustración.** Las imágenes `zzz*.bmp` también son arte real (por ejemplo, el
  Dragón Definitivo de Ojos Azules); solo las `token_*.bmp` son relleno.

## Las 330 entradas basura

En la tabla de ediciones (`CARD_Pack`), las 330 no usables valen **0**: no salen en ningún sobre ni en
la lista. Tienen nombre, ATK, DEF y tipo de cartas reales (*Black Luster Soldier*, *Kaiser Dragon*,
*Slifer the Sky Dragon*...), pero:

- **ninguna tiene ilustración**: el juego muestra la imagen del **Slime Token**, con su etiqueta
  `[AQUA/TOKEN]` y ATK 500 / DEF 500;
- si se meten en un mazo, el juego las **expulsa**;
- 4 de ellas sí son tokens de verdad: Slime, Sheep, Insect Monster y Kuriboh Token.

Lo más probable es que Konami usara **una sola base de datos para los tres Power of Chaos** (Yugi the
Destiny, Kaiba the Revenge y Joey the Passion) y que cada juego activara solo su parte, con el arte de
sus propias cartas. Es una suposición; no está comprobada con los otros dos juegos.

### Qué se hizo con ellas

La biblioteca de mazos de la CPU del mod las había usado: 293 cartas, en 2 715 lugares de 531 mazos. En
un duelo se veían como Slime Token pero pegaban con sus datos reales (un "Slime Token" con 3 000 de ATK).
El 16-oct-2026 se quitaron todas y se cambiaron por cartas reales parecidas. Ver
[01 · Mod para PC](01-mod-pc.md#5-limpieza-de-cartas-basura-16-oct-2026).

## Para el remake 3D

Cuentan **los 496 monstruos usables**. Cada uno está clasificado en una plantilla de cuerpo y una regla
de combate (ver [04](04-monstruos-3d.md) y [05](05-reglas-combate.md)). Las 272 magias y trampas van como
cartas planas con efectos.
