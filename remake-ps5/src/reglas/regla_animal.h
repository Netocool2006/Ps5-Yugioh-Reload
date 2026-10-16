// Reglas de los animales e insectos del Excel (filas 7, 8, 10 y 11). Todos atacan con embestida y se defienden
// cerrando los ojos; cambian segun vayan por tierra o por aire:
//  - insectos de aire (fila 7):  "ataca con embestida; efecto embestida aerea; defensa cierran los ojos y reciben
//    impacto; derrota cae al suelo y se destruye".
//  - insectos de tierra (fila 8): "embestida via tierra; defensa cierran los ojos y reciben impacto; derrota caer
//    derrotado al piso".
//  - animales de aire (fila 10): "atacan por aire con embestida; defensa cierran los ojos; derrota cae al suelo y
//    se destruye".
//  - animales de tierra (fila 11): "atacan con embestida; efecto embestida de tierra; defensa cierran los ojos;
//    derrota caer derrotado al piso".
// Son figuras rigidas: solo se mueven enteras con la Pose, nunca se deforman.
#pragma once
#include "combate_api.h"

namespace combate {

namespace animal_detalle {

constexpr float PI = 3.14159265f;

// eje horizontal perpendicular a "hacia" (para temblar de lado y dibujar anillos)
inline glm::vec3 ladoDe(const Situacion& s)
{
	const glm::vec3 l = glm::cross(glm::vec3(0.0f, 1.0f, 0.0f), s.hacia);
	const float n = glm::length(l);
	return n > 1e-4f ? l / n : glm::vec3(1.0f, 0.0f, 0.0f);
}

// cuanto avanza hasta quedar frente al rival (llega a ~0.9 de su ancho)
inline float alcance(const Situacion& s)
{
	return glm::max(0.0f, glm::length(s.rival - s.base) - 0.9f * s.ancho);
}

// donde esta el cuerpo (su base) en el instante t, segun la funcion de ataque "mover"
template <class F>
glm::vec3 posicionEn(const Situacion& s, float t, F mover)
{
	Situacion c = s;
	c.t = t;
	Pose q;
	mover(c, q);
	return s.base + q.desplazar;
}

// color de tierra levantada, con un toque del color de quien ataca
inline glm::vec3 colorTierra(const Situacion& s)
{
	return glm::mix(glm::vec3(0.55f, 0.40f, 0.24f), s.halo, 0.2f);
}

// destello y chispas del choque (como la embestida), en el pecho del rival
inline void golpe(const Situacion& s, glm::vec3 hasta, Pincel& pincel, int chispas)
{
	const float u = s.t - IMPACTO;
	if (u < 0.0f || u > 0.6f) {
		return;
	}
	const float k = 1.0f - u / 0.6f;
	pincel.bola(hasta, (0.3f + 0.9f * u) * s.ancho * 0.5f, s.halo, 0.35f * k);
	pincel.bola(hasta, 0.18f * k, s.nucleo, 1.5f * k);
	for (int i = 0; i < chispas; i++) {
		const float a = 6.2832f * i / (float)chispas + azar(s.semilla + i);
		const glm::vec3 dir(cosf(a), 0.3f * azar(s.semilla * 3u + i), sinf(a));
		pincel.tramo(hasta + dir * (0.2f + 0.8f * u), hasta + dir * (0.35f + 1.2f * u), 0.03f * k, s.nucleo, 0.9f * k);
	}
}

// ---------------------------------------------------------------- tierra

struct EstiloTierra {
	float arranca;    // s: termina de agazaparse y sale corriendo (llega en IMPACTO)
	float salto;      // m: altura de cada brinco
	float brincos;    // brincos en la carrera de ida (1 = un salto largo de bestia)
	float vibra;      // m: temblor de patitas mientras corre (0 = nada)
};
constexpr EstiloTierra TIERRA_ANIMAL{ 1.0f, 0.5f, 1.0f, 0.0f };
constexpr EstiloTierra TIERRA_INSECTO{ 1.2f, 0.12f, 4.0f, 0.025f };

// se agazapa, corre/salta pegado al suelo hasta el rival, choca, rebota y vuelve a su carta
inline void atacarTierra(const Situacion& s, Pose& p, const EstiloTierra& e)
{
	const float agazapa = suave(0.2f, e.arranca, s.t) * (1.0f - suave(e.arranca, e.arranca + 0.2f, s.t));
	const float ida = suave(e.arranca, IMPACTO, s.t);
	const float vuelta = suave(IMPACTO + 0.25f, IMPACTO + 1.2f, s.t);
	const float rebote = sinf(PI * suave(IMPACTO, IMPACTO + 0.25f, s.t));
	const float corre = sinf(PI * ida) + sinf(PI * vuelta);
	p.desplazar += s.hacia * (alcance(s) * ida * (1.0f - vuelta) - 0.25f * agazapa - 0.2f * rebote * (1.0f - vuelta));
	const float brincoIda = fabsf(sinf(PI * e.brincos * ida)) * (1.0f - vuelta);
	const float brincoVuelta = 0.4f * fabsf(sinf(PI * (e.brincos + 1.0f) * vuelta));
	p.desplazar.y += -0.1f * agazapa + e.salto * (brincoIda + brincoVuelta);
	// patitas: vibracion rapida de lado y de giro
	const float vib = e.vibra * (corre + 0.5f * agazapa);
	p.desplazar += ladoDe(s) * (vib * sinf(s.t * 83.0f));
	p.girar += 2.0f * vib * sinf(s.t * 61.0f);
	p.inclinar += -0.2f * agazapa + 0.3f * ida * (1.0f - vuelta);
	p.aplastar *= 1.0f - 0.08f * agazapa;
	p.brillo += 0.8f * agazapa;
}

// polvo que levanta al correr (bolas tenues color tierra cerca del suelo, detras de el) + golpe del choque
template <class F>
void efectoTierra(const Situacion& s, glm::vec3 hasta, Pincel& pincel, F mover)
{
	const glm::vec3 tierra = colorTierra(s);
	const glm::vec3 lado = ladoDe(s);
	const float paso = 0.03f;
	for (int i = 0; i < 12; i++) {
		const float edad = 0.06f * i;
		const float te = s.t - edad;
		if (te < 0.9f || te > IMPACTO + 1.3f) {
			continue;
		}
		const glm::vec3 a = posicionEn(s, te, mover);
		const glm::vec3 b = posicionEn(s, te - paso, mover);
		const float rapidez = glm::length(glm::vec2(a.x - b.x, a.z - b.z)) / paso;
		const float k = glm::clamp(rapidez / 4.0f, 0.0f, 1.0f) * (1.0f - edad / 0.72f);
		if (k <= 0.01f) {
			continue;
		}
		const float r = (0.06f + 0.25f * edad) * glm::min(s.ancho, 2.0f) * 0.6f;   // polvo chico y tenue (suma luz)
		for (int j = 0; j < 2; j++) {
			const float signo = j == 0 ? -1.0f : 1.0f;
			const float abre = (0.25f + 0.6f * edad) * s.ancho * (0.6f + 0.4f * azar(s.semilla + 31u * i + j));
			const glm::vec3 c = glm::vec3(a.x, 0.08f + 0.35f * edad, a.z) + lado * (signo * abre);
			pincel.bola(c, r, tierra, 0.05f * k);
		}
	}
	golpe(s, hasta, pincel, 8);
	// tierra que salta del suelo al chocar
	const float u = s.t - IMPACTO;
	if (u >= 0.0f && u < 0.7f) {
		const float k = 1.0f - u / 0.7f;
		const glm::vec3 suelo(hasta.x, 0.06f, hasta.z);
		for (int i = 0; i < 6; i++) {
			const float a = 6.2832f * i / 6.0f + azar(s.semilla * 5u + i);
			const glm::vec3 c = suelo + glm::vec3(cosf(a), 0.0f, sinf(a)) * ((0.3f + 1.2f * u) * s.ancho * 0.5f) + glm::vec3(0.0f, 0.3f * u, 0.0f);
			pincel.bola(c, 0.15f + 0.3f * u, tierra, 0.2f * k);
		}
	}
}

// cae derrotado al piso (de costado, con un rebote) y se desintegra
inline void derrotaTierra(const Situacion& s, Pose& p)
{
	p.ojos = 1.0f;
	p.escala *= 0.93f;
	p.desplazar -= s.hacia * 0.5f;
	p.caer = 1.5f * suave(MUERE, MUERE + 0.55f, s.t);
	const float r = s.t - (MUERE + 0.55f);
	if (r > 0.0f && r < 0.35f) {
		p.caer -= 0.12f * sinf(PI * r / 0.35f);
	}
	p.desintegrar = suave(DESAPARECE, DESAPARECE + 1.0f, s.t);
}

// polvo al azotar contra el piso
inline void efectoDerrotaTierra(const Situacion& s, glm::vec3 donde, Pincel& pincel)
{
	const float u = s.t - (MUERE + 0.5f);
	if (u < 0.0f || u > 0.9f) {
		return;
	}
	const float k = 1.0f - u / 0.9f;
	const glm::vec3 tierra = colorTierra(s);
	const glm::vec3 suelo(donde.x, 0.06f, donde.z);
	for (int i = 0; i < 8; i++) {
		const float a = 6.2832f * i / 8.0f + azar(s.semilla * 11u + i);
		const float r = (0.3f + 1.0f * u) * glm::max(s.alto, s.ancho) * 0.4f;
		const glm::vec3 c = suelo + glm::vec3(cosf(a), 0.0f, sinf(a)) * r + glm::vec3(0.0f, 0.25f * u, 0.0f);
		pincel.bola(c, 0.08f + 0.15f * u, tierra, 0.06f * k);
	}
}

// ---------------------------------------------------------------- aire

struct EstiloAire {
	float zumbido;   // m: vibracion rapida de las alas de insecto (0 = nada)
	float aleteo;    // m: subir y bajar lento de las alas de animal
};
constexpr EstiloAire AIRE_ANIMAL{ 0.0f, 0.07f };
constexpr EstiloAire AIRE_INSECTO{ 0.025f, 0.0f };

// altura a la que sube antes de la picada (1.2 .. 1.8 m)
inline float alturaVuelo(const Situacion& s)
{
	return 1.2f + 0.6f * azar(s.semilla * 7u + 3u);
}

// sube, se lanza en picada en arco hasta el rival (llega en IMPACTO), rebota y vuelve volando
inline void atacarAire(const Situacion& s, Pose& p, const EstiloAire& e)
{
	const float sube = suave(0.2f, 1.0f, s.t);
	const float ida = suave(1.0f, IMPACTO, s.t);
	const float vuelta = suave(IMPACTO + 0.2f, IMPACTO + 1.5f, s.t);
	const float rebote = sinf(PI * suave(IMPACTO, IMPACTO + 0.45f, s.t));
	const float h = alturaVuelo(s);
	const float choque = 0.25f;   // m: altura del cuerpo al chocar
	p.desplazar += s.hacia * (alcance(s) * ida * (1.0f - vuelta) - 0.35f * sube * (1.0f - ida) - 0.3f * rebote * (1.0f - vuelta));
	const float yIda = glm::mix(h * sube, choque, powf(ida, 1.6f));
	p.desplazar.y += yIda * (1.0f - vuelta) + 0.5f * rebote * (1.0f - vuelta) + 0.6f * h * sinf(PI * vuelta);
	// en el aire: aleteo lento (animal) o zumbido rapido (insecto)
	const float vuelo = sube * (1.0f - vuelta) + sinf(PI * vuelta);
	p.desplazar.y += (e.aleteo * sinf(s.t * 9.0f) + e.zumbido * sinf(s.t * 71.0f)) * vuelo;
	p.desplazar += ladoDe(s) * (e.zumbido * sinf(s.t * 53.0f) * vuelo);
	p.girar += 1.5f * e.zumbido * sinf(s.t * 47.0f) * vuelo;
	p.inclinar += -0.25f * sube * (1.0f - ida) + 0.7f * ida * (1.0f - suave(IMPACTO, IMPACTO + 0.3f, s.t)) - 0.3f * rebote * (1.0f - vuelta);
	p.brillo += 0.6f * sube * (1.0f - ida);
}

// estela de aire siguiendo la picada + destello y anillo de viento al chocar
template <class F>
void efectoAire(const Situacion& s, glm::vec3 hasta, Pincel& pincel, F mover)
{
	const glm::vec3 centro(0.0f, 0.45f * s.alto, 0.0f);
	const float paso = 0.035f;
	for (int i = 0; i < 12; i++) {
		const float edad = paso * i;
		const float te = s.t - edad;
		if (te < 0.9f || te > IMPACTO + 1.6f) {
			continue;
		}
		const glm::vec3 a = posicionEn(s, te, mover) + centro;
		const glm::vec3 b = posicionEn(s, te - paso, mover) + centro;
		const float rapidez = glm::length(a - b) / paso;
		const float k = glm::clamp(rapidez / 5.0f, 0.0f, 1.0f) * (1.0f - edad / (12.0f * paso));
		if (k <= 0.01f) {
			continue;
		}
		const float r = (0.1f + 0.5f * edad) * glm::min(s.ancho, 2.0f) * 0.5f;
		pincel.tramo(a, b, r, s.halo, 0.3f * k);
		pincel.tramo(a, b, 0.25f * r, s.nucleo, 0.6f * k);
	}
	golpe(s, hasta, pincel, 4);
	// anillo de viento que se abre alrededor del golpe
	const float u = s.t - IMPACTO;
	if (u >= 0.0f && u < 0.5f) {
		const float k = 1.0f - u / 0.5f;
		const glm::vec3 lado = ladoDe(s);
		const glm::vec3 arriba(0.0f, 1.0f, 0.0f);
		const float r = (0.3f + 1.6f * u) * s.ancho * 0.5f;
		const int n = 10;
		for (int i = 0; i < n; i++) {
			const float a0 = 6.2832f * i / (float)n, a1 = 6.2832f * (i + 1) / (float)n;
			const glm::vec3 p0 = hasta + (lado * cosf(a0) + arriba * sinf(a0)) * r;
			const glm::vec3 p1 = hasta + (lado * cosf(a1) + arriba * sinf(a1)) * r;
			pincel.tramo(p0, p1, 0.04f * k, s.halo, 0.5f * k);
		}
	}
}

// caida libre del derrotado volador: altura actual y "toca" = segundos tras MUERE en que toca el suelo
inline float caidaAire(const Situacion& s, float* toca)
{
	const float y0 = s.vuela ? 0.45f : 0.0f;   // si se defendia en el aire, cae desde ahi
	const float v = 1.6f, g = 6.4f;            // el golpe lo levanta un poco y luego se desploma
	const float tc = (v + sqrtf(v * v + 2.0f * g * y0)) / g;
	if (toca) {
		*toca = tc;
	}
	const float u = glm::clamp(s.t - MUERE, 0.0f, tc);
	return glm::max(0.0f, y0 + v * u - 0.5f * g * u * u);
}

// se desploma dando vueltas y al tocar el suelo se rompe (desintegracion rapida)
inline void derrotaAire(const Situacion& s, Pose& p)
{
	float tc = 0.5f;
	const float y = caidaAire(s, &tc);
	const float u = s.t - MUERE;
	const float cayendo = suave(0.0f, tc, u);
	p.ojos = 1.0f;
	p.escala *= 0.93f;
	p.desplazar -= s.hacia * (0.5f + 0.4f * cayendo);
	p.desplazar.y += y;
	p.girar += 2.0f * PI * 0.85f * cayendo;   // da casi una vuelta entera al caer
	p.caer = 1.3f * cayendo;
	p.inclinar += 0.4f * sinf(PI * cayendo);
	p.aplastar *= 1.0f - 0.12f * sinf(PI * suave(tc, tc + 0.2f, u));
	p.desintegrar = suave(MUERE + tc - 0.05f, MUERE + tc + 0.6f, s.t);
}

// al romperse contra el suelo: destello y fragmentos que saltan en abanico y caen
inline void efectoDerrotaAire(const Situacion& s, glm::vec3 donde, Pincel& pincel)
{
	float tc = 0.5f;
	caidaAire(s, &tc);
	const float w = s.t - (MUERE + tc);
	if (w < 0.0f || w > 1.2f) {
		return;
	}
	const float k = 1.0f - w / 1.2f;
	const glm::vec3 suelo(donde.x, 0.05f, donde.z);
	const glm::vec3 sale = suelo + glm::vec3(0.0f, 0.2f * s.alto, 0.0f);
	if (w < 0.35f) {
		const float kd = 1.0f - w / 0.35f;
		pincel.bola(sale, (0.3f + 1.5f * w) * s.ancho * 0.5f, s.halo, 0.5f * kd);
		pincel.bola(sale, 0.2f * kd, s.nucleo, 1.6f * kd);
	}
	const float g = 9.0f;
	for (int i = 0; i < 16; i++) {
		const float a = 6.2832f * i / 16.0f + 0.4f * azar(s.semilla * 13u + i);
		const float vh = 1.0f + 1.5f * azar(s.semilla * 17u + i);
		const float vy = 2.0f + 2.0f * azar(s.semilla * 19u + i);
		const glm::vec3 dirH(cosf(a), 0.0f, sinf(a));
		glm::vec3 pos = sale + dirH * (vh * w) + glm::vec3(0.0f, vy * w - 0.5f * g * w * w, 0.0f);
		pos.y = glm::max(pos.y, 0.03f);
		const glm::vec3 vel = dirH * vh + glm::vec3(0.0f, vy - g * w, 0.0f);
		const glm::vec3 col = (i & 1) ? s.nucleo : s.halo;
		const float r = 0.035f + 0.03f * azar(s.semilla * 23u + i);
		pincel.bola(pos, r, col, 1.0f * k);
		pincel.tramo(pos, pos - vel * 0.05f, 0.4f * r, s.halo, 0.4f * k);
	}
}

// ---------------------------------------------------------------- defensa (todos)

// cierra los ojos y recibe el impacto: se encoge, retrocede y tiembla (el volador se defiende en el aire)
inline void defenderCierraOjos(const Situacion& s, Pose& p, bool enAire)
{
	const float cubre = suave(CUBRE, CUBRE + 0.2f, s.t);
	const float u = glm::max(0.0f, s.t - IMPACTO);
	p.ojos = cubre;
	p.escala *= 1.0f - 0.07f * cubre;
	if (enAire) {
		p.desplazar.y += 0.45f * suave(CUBRE, CUBRE + 0.3f, s.t);
	}
	p.desplazar -= s.hacia * 0.5f * suave(0.0f, 0.25f, u);
	p.inclinar -= 0.28f * suave(0.0f, 0.2f, u);
	const float tiembla = expf(-u * 3.0f) * (u > 0.0f ? 1.0f : 0.0f);
	p.girar += 0.24f * sinf(u * 18.0f) * tiembla;
	p.desplazar += ladoDe(s) * (0.04f * sinf(u * 37.0f) * tiembla);
}

} // namespace animal_detalle

// ---------------------------------------------------------------- las cuatro reglas

struct ReglaAnimalTierra : Regla {
	const char* nombre() const override { return "animal_tierra"; }
	static void mover(const Situacion& s, Pose& p) { animal_detalle::atacarTierra(s, p, animal_detalle::TIERRA_ANIMAL); }
	void atacar(const Situacion& s, Pose& p) const override { mover(s, p); }
	void efecto(const Situacion& s, glm::vec3, glm::vec3 hasta, Pincel& pincel) const override { animal_detalle::efectoTierra(s, hasta, pincel, mover); }
	void defender(const Situacion& s, Pose& p) const override { animal_detalle::defenderCierraOjos(s, p, false); }
	void derrota(const Situacion& s, Pose& p) const override { animal_detalle::derrotaTierra(s, p); }
	void efectoDerrota(const Situacion& s, glm::vec3 donde, Pincel& pincel) const override { animal_detalle::efectoDerrotaTierra(s, donde, pincel); }
};

struct ReglaInsectoTierra : Regla {
	const char* nombre() const override { return "insecto_tierra"; }
	static void mover(const Situacion& s, Pose& p) { animal_detalle::atacarTierra(s, p, animal_detalle::TIERRA_INSECTO); }
	void atacar(const Situacion& s, Pose& p) const override { mover(s, p); }
	void efecto(const Situacion& s, glm::vec3, glm::vec3 hasta, Pincel& pincel) const override { animal_detalle::efectoTierra(s, hasta, pincel, mover); }
	void defender(const Situacion& s, Pose& p) const override { animal_detalle::defenderCierraOjos(s, p, false); }
	void derrota(const Situacion& s, Pose& p) const override { animal_detalle::derrotaTierra(s, p); }
	void efectoDerrota(const Situacion& s, glm::vec3 donde, Pincel& pincel) const override { animal_detalle::efectoDerrotaTierra(s, donde, pincel); }
};

struct ReglaAnimalAire : Regla {
	const char* nombre() const override { return "animal_aire"; }
	static void mover(const Situacion& s, Pose& p) { animal_detalle::atacarAire(s, p, animal_detalle::AIRE_ANIMAL); }
	void atacar(const Situacion& s, Pose& p) const override { mover(s, p); }
	void efecto(const Situacion& s, glm::vec3, glm::vec3 hasta, Pincel& pincel) const override { animal_detalle::efectoAire(s, hasta, pincel, mover); }
	void defender(const Situacion& s, Pose& p) const override { animal_detalle::defenderCierraOjos(s, p, s.vuela); }
	void derrota(const Situacion& s, Pose& p) const override { animal_detalle::derrotaAire(s, p); }
	void efectoDerrota(const Situacion& s, glm::vec3 donde, Pincel& pincel) const override { animal_detalle::efectoDerrotaAire(s, donde, pincel); }
};

struct ReglaInsectoAire : Regla {
	const char* nombre() const override { return "insecto_aire"; }
	static void mover(const Situacion& s, Pose& p) { animal_detalle::atacarAire(s, p, animal_detalle::AIRE_INSECTO); }
	void atacar(const Situacion& s, Pose& p) const override { mover(s, p); }
	void efecto(const Situacion& s, glm::vec3, glm::vec3 hasta, Pincel& pincel) const override { animal_detalle::efectoAire(s, hasta, pincel, mover); }
	void defender(const Situacion& s, Pose& p) const override { animal_detalle::defenderCierraOjos(s, p, s.vuela); }
	void derrota(const Situacion& s, Pose& p) const override { animal_detalle::derrotaAire(s, p); }
	void efectoDerrota(const Situacion& s, glm::vec3 donde, Pincel& pincel) const override { animal_detalle::efectoDerrotaAire(s, donde, pincel); }
};

} // namespace combate
