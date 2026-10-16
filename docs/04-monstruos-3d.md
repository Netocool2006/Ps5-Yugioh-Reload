# 04 · Monstruos 3D

## Ciclo de producción

| Paso | Qué se hace | Costo |
|---|---|---|
| 1. Arte → Gemini | La ilustración original de la carta se convierte en una **figura 3D de frente** (`figura.png`). Si ya existe, se reutiliza | Gratis |
| 2. Figura → TRELLIS | **TRELLIS** (Microsoft, código abierto) genera el modelo con textura en una GPU L4 de Google Colab Pro (~3 min) | Gratis (~0,08 unidades de Colab) |
| 3. Limpieza en el PC | Quitar el pedestal, material mate (TRELLIS lo deja metálico), color ajustado a la luz del juego, medir ojos para el parpadeo | Gratis |
| 4. ¿Se mueve? | Humanoides: esqueleto y animaciones con **Meshy** (~8 créditos) o una plantilla existente. El resto: movimiento por código | 0 a ~8 créditos |
| 5. Al juego | Tamaño lógico, carta, escena regenerada (de ahí sale la escala real) | Gratis |
| 6. Revisión | Video, 8 ángulos y acercamientos en 4 bloques | Gratis |
| 7. PS5 | Solo cuando se pide | — |

Antes todo se hacía con Meshy (~35-45 créditos por monstruo) y no alcanzaba para los 496. Con TRELLIS
en Colab, los monstruos fijos no cuestan nada y los que se mueven, unos 8 créditos.

### Lecciones del primer monstruo hecho con TRELLIS (Kuriboh)

- TRELLIS no escribe `metallicFactor`, y en glTF eso significa metal: el pelo salía gris metálico.
- La escala de cada monstruo sale de las medidas de su modelo: al cambiar un modelo, **hay que
  regenerar la escena**.
- El color no se ve igual en Blender que con la luz del juego: se ajusta mirando el juego.

## Las 16 plantillas

Como en los estudios grandes: **un esqueleto y un juego de movimientos por familia de cuerpo**, no uno
por monstruo. Cada uno de los 496 monstruos usables tiene su plantilla.

| Plantilla | Monstruos | Se mueve con | Ejemplo |
|---|---|---|---|
| Luchador (puños/garras) | 83 | Esqueleto Meshy | Calavera Convocada |
| Hechicero sin arma | 63 | Esqueleto Meshy | Elfa Mística, Jinzo |
| Volador con alas | 59 | Código | Ojos Rojos, Bebé Dragón ✅ |
| Guerrero con espada | 48 | Esqueleto Meshy | Guardián Celta ✅ |
| Criatura pequeña | 34 | Código | Kuriboh ✅ |
| Cuadrúpedo | 33 | Código | Colmillo Plateado |
| Máquina | 31 | Código | Tanque Oni |
| Objeto o estructura | 30 | Código | Jarra de Transformación |
| Guerrero con arma larga | 26 | Esqueleto Meshy | Asaltante con Hacha |
| Espíritu flotante | 20 | Código | Máscara de la Oscuridad |
| Serpiente o gusano | 18 | Código | Serpiente Siniestra |
| Bicho de tierra | 17 | Código | Escarabajo Hércules |
| Lanzador con báculo | 13 | Esqueleto Meshy + báculo | Mago Oscuro, Maga Oscura ✅ |
| Acuático | 12 | Código | Gran Tiburón Blanco |
| Jinete o centauro | 5 | Código | Gaia el Caballero Feroz |
| Tirador | 4 | Esqueleto Meshy | Arquera Amazona |

✅ = la plantilla ya existe y se reutiliza. Hay 29 monstruos marcados "revisar": su plantilla se
confirma mirando su figura antes de producirlos.

Con esto, los esqueletos de los 237 humanoides cuestan unos 1 900 créditos de Meshy. La generación
del modelo con TRELLIS es gratis.
