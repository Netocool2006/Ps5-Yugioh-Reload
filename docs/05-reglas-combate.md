# 05 · Reglas de combate

Las reglas vienen de un **Excel del dueño del proyecto** (`reglas-yugi.xlsx`). Para cada clase de
monstruo dice cómo **ataca**, qué **efecto** tiene, cómo se **defiende** y cómo queda **derrotado**.

## Las reglas

| # | Quién | Ataque | Efecto | Defensa | Derrota |
|---|---|---|---|---|---|
| 1 | Con arma de mano | Golpe con su arma | Golpe fuerte | Pone el arma al frente | Cae al piso |
| 2 | Con arma de fuego / arco | Proyectil a distancia | Explosión | Cruza los brazos | Cae al piso |
| 3 | Místicos (magos, hadas, brujas…) | Rayo desde su arma o sus manos, **1 de 5 al azar** | Hechizo | Interpone el báculo; sin báculo, brazos en X | Cae al piso |
| 4 | De agua (atributo AGUA) | Ráfaga de agua | Agua regada | Cierra los ojos | **Se diluye en agua** |
| 5 | Máquinas | Su arma a distancia; sin arma, puñetazos | Chispas | Cruza los brazos | **Explosión de fuego** |
| 5b | Sin arma ni magia | Embestida de bestia | Golpe duro | Cierra los ojos y recibe el golpe | Cae al piso |
| 6 | Dragones | Ráfaga de fuego a distancia | Fuego fuerte | **Dobla las alas al frente** | Cae al piso |
| 7 | Insectos voladores | Embestida por aire | — | Cierra los ojos | **Cae y se destruye** |
| 8 | Insectos de tierra | Embestida por tierra | — | Cierra los ojos | Cae al piso |
| 9 | Rocas | Cuerpo a cuerpo | Demolición de rocas | Cierra los ojos | Cae al piso |
| 10 | Animales voladores | Embestida por aire | — | Cierra los ojos | Cae y se destruye |
| 11 | Animales de tierra | Embestida por tierra | — | Cierra los ojos | Cae al piso |
| ★ | **Manda sobre todas** | Si tiene arma, **ataca con su arma** | | | |

**Prioridad** cuando un monstruo cumple varias reglas: **arma > místico > máquina > dragón > agua >
el resto**. Por ejemplo, el Mago del Agua es místico y lanza un rayo de agua.

**Propuestas** (no están en el Excel; esperan revisión): demonio (zarpazo; se desvanece en humo oscuro),
zombi (se desmorona en polvo y huesos), piro (llamarada), trueno (descarga eléctrica), planta (latigazo
de lianas; se marchita), espíritu y objeto.

### Cuántos monstruos tiene cada regla

Místico 95 · arma de mano 78 · agua 44 · embestida 36 · máquina 36 · animal de tierra 32 · dragón 28 ·
demonio 27 · animal de aire 23 · insecto de tierra 22 · roca 15 · objeto 11 · trueno 10 · zombi 10 ·
espíritu 9 · insecto de aire 8 · piro 8 · arma de fuego 4.

## El color del efecto: depende de quién ataca

- **Mago Oscuro: azul. Maga Oscura: morado** (lo pidió el dueño del proyecto).
- Para los **95 místicos**, el color sale de **analizar su figura**: se buscan los tonos brillantes y
  saturados (destellos, gemas, adornos mágicos) y se descartan los dorados de la ropa y la piel.
  Después hubo una **revisión a ojo de las 87 figuras** con 35 correcciones. Los de fuego lanzan fuego y
  los de agua, agua.
- Los dragones usan el color conocido de su ataque: Ojos Rojos rojo-naranja, Ojos Azules blanco-azul.

## Los 5 rayos de los místicos

1. **Eléctrico**: el rayo quebrado del Mago Oscuro.
2. **Esfera de energía**: viaja con estela y estalla en el rival.
3. **Láser**: haz recto y grueso que late.
4. **Anillos de energía**: aros que salen del báculo y crecen al llegar.
5. **Espiral**: dos hilos que giran uno alrededor del otro.

(Una "lluvia de estrellas" se probó y se descartó.)

## El motor de reglas

- Cada regla vive en **su propio archivo** (`reglas/regla_<nombre>.h`) y sigue un contrato común
  (`combate_api.h`):
  - `atacar`: el movimiento del cuerpo al atacar;
  - `origen`: de dónde sale el ataque (boca, cañón...);
  - `efecto`: lo que se dibuja;
  - `defender`, `derrota` y `efectoDerrota`.
- Los monstruos sin esqueleto **nunca se deforman**: solo se mueven enteros (desplazarse, inclinarse,
  girar, caer, encogerse, aplastarse, desintegrarse).
- Una tabla generada desde la clasificación dice qué regla usa cada carta.
- Gracias a eso, **varias reglas se escribieron en paralelo** y se integraron sin pisarse. Ya están
  programadas embestida, dragón, animal de tierra y de aire, insecto de tierra y de aire, máquina, agua
  y roca, además de los místicos y el guerrero con espada, que tienen esqueleto.
- **Enfrentamientos de prueba**: cualquier monstruo contra cualquier otro (Ojos Rojos contra el Guardián,
  Mago contra Ojos Rojos, Ojos Rojos contra el Mago...). Cada regla se revisa en video antes de aprobarse.
