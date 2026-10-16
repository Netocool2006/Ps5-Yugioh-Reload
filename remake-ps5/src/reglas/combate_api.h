// Contrato de las reglas de combate de Yugi Reload (Excel del usuario reglas-yugi.xlsx, Hoja2; prioridad y
// propuestas en remake/diseno/reglas_combate.json). Cada regla vive en su propio archivo regla_<nombre>.h y solo
// usa esta interfaz: asi varias reglas se escriben en paralelo sin tocar yugireload.cpp.
//
// Una regla dice, para un monstruo SIN esqueleto (figura rigida: nunca se deforma, solo se mueve entero):
//  - atacar:   como se mueve su cuerpo mientras ataca (cargar, lanzarse, volver);
//  - efecto:   lo que dibuja su ataque (fuego, agua, chispas...) con el Pincel (luz aditiva);
//  - defender: como recibe el golpe (cerrar los ojos = encogerse y temblar, alas al frente = girar y cubrirse...);
//  - derrota:  como queda derrotado (caer, diluirse, explotar...) y su efecto.
// Los personajes con esqueleto (Mago, Maga, Guardian) siguen con su codigo propio en yugireload.cpp.
//
// Tiempos del ataque (s desde que empieza; ver T_* en yugireload.cpp): el atacante carga de 0.2 a SUELTA, el golpe
// llega en IMPACTO, el efecto dura hasta FIN_EFECTO, el defensor cae en MUERE, se desintegra de DESAPARECE a
// DESAPARECE+1 y todo vuelve a su lugar entre VUELVE y FIN.
#pragma once
#include <cmath>
#include <cstdint>
#include <glm/glm.hpp>

namespace combate {

constexpr float SUELTA = 1.65f, IMPACTO = 1.65f, CUBRE = 1.45f, FIN_EFECTO = 2.9f, MUERE = 2.55f;
constexpr float DESAPARECE = 5.3f, VUELVE = 7.4f, FIN = 8.8f;

// 0 en x<=a, 1 en x>=b, curva suave entre medio
inline float suave(float a, float b, float x)
{
	const float t = glm::clamp((x - a) / (b - a), 0.0f, 1.0f);
	return t * t * (3.0f - 2.0f * t);
}

// numero pseudoaleatorio estable 0..1 (misma semilla, mismo numero)
inline float azar(uint32_t n)
{
	n = (n << 13u) ^ n;
	n = n * (n * n * 15731u + 789221u) + 1376312589u;
	return (float)(n & 0x7fffffffu) / 2147483647.0f;
}

// Lo que el motor le cuenta a la regla en cada cuadro
struct Situacion {
	float t{ 0.0f };                        // segundos desde que empezo el ataque (0..FIN)
	glm::vec3 base{ 0.0f };                 // centro de la carta del monstruo (y = 0, la mesa)
	glm::vec3 rival{ 0.0f };                // centro de la carta del rival
	glm::vec3 hacia{ 0.0f, 0.0f, 1.0f };    // direccion horizontal hacia el rival (normalizada)
	float alto{ 2.6f };                     // altura del monstruo en el juego (m)
	float ancho{ 1.5f };                    // ancho del monstruo (m)
	bool vuela{ false };                    // volador (alas): ataca y se defiende en el aire
	uint32_t semilla{ 0 };                  // cambia en cada ataque (para variar chispas, gotas...)
	glm::vec3 halo{ 1.0f }, nucleo{ 1.0f }; // color de su efecto (de quien ataca; ver color_magia / elemento)
};

// Como queda el cuerpo en este instante, sumado a su pose de reposo (flotar y mirar al monitor)
struct Pose {
	glm::vec3 desplazar{ 0.0f };   // m, en el mundo
	float inclinar{ 0.0f };        // radianes: + hacia el rival, - hacia atras (gira desde la base)
	float girar{ 0.0f };           // radianes alrededor del eje vertical, extra
	float caer{ 0.0f };            // radianes: 0 de pie .. ~1.55 tendido de costado
	float escala{ 1.0f };          // 1 normal; <1 encogido (cerrar los ojos / cubrirse), >1 inflado
	float aplastar{ 1.0f };        // 1 normal; <1 mas bajo (se aplasta al recibir o al diluirse)
	float desintegrar{ 0.0f };     // 0..1: el shader lo deshace en particulas (lo usa la derrota)
	float brillo{ 0.0f };          // holograma extra (cargar energia)
	float ojos{ -1.0f };           // parpado de los que tienen ojos medidos: -1 no tocar, 0 abiertos, 1 cerrados
};

// Lo que una regla puede dibujar (luz aditiva: resplandor suave con centro brillante)
struct Pincel {
	virtual ~Pincel() = default;
	// cilindro luminoso de a hasta b (radio en m; brillo ~0.3 halo, ~1.5 nucleo)
	virtual void tramo(glm::vec3 a, glm::vec3 b, float radio, glm::vec3 color, float brillo) = 0;
	// esfera luminosa
	virtual void bola(glm::vec3 centro, float radio, glm::vec3 color, float brillo) = 0;
	// rayo electrico quebrado de a hasta b (amplitud ~0.06 del largo, grosor ~1, ramas 0..3)
	virtual void relampago(glm::vec3 a, glm::vec3 b, uint32_t semilla, float amplitud, float grosor, int ramas) = 0;
};

// Una regla (implementa lo que necesite; lo que no, queda como el cuerpo en reposo)
struct Regla {
	virtual ~Regla() = default;
	virtual const char* nombre() const = 0;
	// el cuerpo del atacante
	virtual void atacar(const Situacion&, Pose&) const {}
	// de donde sale el ataque a distancia (boca, canon, manos...); por defecto: frente del pecho
	virtual glm::vec3 origen(const Situacion& s) const { return s.base + s.hacia * (0.35f * s.ancho) + glm::vec3(0.0f, 0.7f * s.alto, 0.0f); }
	// el efecto del ataque, de "desde" (origen) a "hasta" (pecho del rival)
	virtual void efecto(const Situacion&, glm::vec3 /*desde*/, glm::vec3 /*hasta*/, Pincel&) const {}
	// el cuerpo del defensor desde CUBRE hasta MUERE (recibe el golpe)
	virtual void defender(const Situacion&, Pose&) const {}
	// el cuerpo del derrotado desde MUERE hasta VUELVE (luego el motor lo devuelve a su lugar)
	virtual void derrota(const Situacion&, Pose&) const {}
	// efecto de la derrota (agua que se riega, explosion de fuego...) en la posicion del derrotado
	virtual void efectoDerrota(const Situacion&, glm::vec3 /*donde*/, Pincel&) const {}
};

} // namespace combate
