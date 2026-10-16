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
	float vuelo{ 0.0f };                    // altura a la que flota en reposo (m; 0 si no vuela). El motor ya la
	                                        // suma a su cuerpo: la regla solo agrega lo que suba o baje de mas
	bool ladoRival{ false };                // esta del lado del rival (los ataques siempre cruzan el tablero)
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
	float aleteo{ 1.0f };          // voladores con alas: velocidad del aleteo (1 normal, 2-3 al atacar, 0 quietas)
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

	// ---- efectos "de verdad" (no son luz pura: fuego con forma, agua y humo con transparencia) ----
	// FUEGO: una lengua de fuego que va de "base" a "punta" (llamarada con ruido animado: blanco-amarillo en el
	// nucleo, naranja, rojo y humo en los bordes y la punta). ancho en m; intensidad 0..1; semilla para variar.
	// Para una llamarada larga: varias lenguas seguidas o superpuestas
	virtual void llama(glm::vec3 base, glm::vec3 punta, float ancho, float intensidad, uint32_t semilla)
	{
		bola(punta, ancho * 0.5f, glm::vec3(1.6f, 0.5f, 0.1f), 0.4f * intensidad);   // respaldo si no hay fuego real
		(void)base; (void)semilla;
	}
	// AGUA: volumen de agua (gota, borbotón o tramo de chorro) con transparencia, reflejo y brillo especular.
	// color = tinte del agua (ej. azul mar); opacidad 0..1
	virtual void liquido(glm::vec3 centro, float radio, glm::vec3 color, float opacidad)
	{
		bola(centro, radio, color, 0.3f * opacidad);
	}
	// CHARCO: lamina de agua plana sobre la mesa (y del centro = altura de la mesa), con ondas
	virtual void charco(glm::vec3 centro, float radio, glm::vec3 color, float opacidad)
	{
		(void)centro; (void)radio; (void)color; (void)opacidad;
	}
	// HUMO o POLVO: nube suave con transparencia (puede ser oscura: no suma luz)
	virtual void humo(glm::vec3 centro, float radio, glm::vec3 color, float opacidad)
	{
		(void)centro; (void)radio; (void)color; (void)opacidad;
	}
};

// Caer derrotado "como el Guardian" (regla del usuario): de ESPALDAS, lejos del atacante: el golpe lo empuja,
// se le doblan las piernas (se hunde un poco), cae hacia atras, rebota en la mesa y se queda tendido; luego se
// desintegra. Si vuela, primero cae al suelo. Usar en derrota() de cualquier regla salvo que la regla diga otra cosa
inline void caerDeEspaldas(const Situacion& s, Pose& p, float desde = MUERE)
{
	const float t = s.t;
	const float baja = s.vuela ? suave(desde, desde + 0.45f, t) : 0.0f;   // primero cae al suelo
	const float t0 = desde + (s.vuela ? 0.45f : 0.0f);
	p.desplazar.y -= s.vuelo * baja;
	p.desplazar -= s.hacia * (0.5f + 0.35f * suave(t0, t0 + 0.6f, t));      // el golpe lo empuja hacia atras
	const float doblar = suave(t0, t0 + 0.25f, t);
	p.aplastar *= 1.0f - 0.08f * doblar * (1.0f - suave(t0 + 0.3f, t0 + 0.6f, t));   // se le doblan las piernas
	float atras = 1.5f * suave(t0 + 0.12f, t0 + 0.7f, t);                    // cae de espaldas
	const float r = t - (t0 + 0.7f);
	if (r > 0.0f && r < 0.35f) {
		atras -= 0.12f * sinf(3.14159f * r / 0.35f);                         // rebota en la mesa
	}
	p.inclinar -= atras;
	p.desplazar.y -= 0.12f * suave(t0 + 0.4f, t0 + 0.7f, t);
	p.ojos = 1.0f;
	p.aleteo = 1.0f - suave(t0, t0 + 0.4f, t);
	p.desintegrar = suave(DESAPARECE, DESAPARECE + 1.0f, t);
}

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
