// Regla 9 del Excel (monstruos de roca): "ataque cuerpo a cuerpo; efecto de demolicion de rocas; defensa: cierran los
// ojos y reciben impacto; derrota: caer derrotado al piso". Es pesado: se mueve lento, a pasos, y golpea fuerte.
#pragma once
#include "combate_api.h"

namespace combate {

struct ReglaRoca : Regla {
	const char* nombre() const override { return "roca"; }

	static constexpr float GRAVEDAD = 9.8f;
	static constexpr float ARRANCA = 0.9f;   // empieza a caminar
	static constexpr float PASO = 0.25f;     // duracion de cada paso (3 pasos: llega en IMPACTO)

	// cuanto avanzo hacia el rival (0..1) en el instante t
	static float avance(float t) { return suave(ARRANCA, IMPACTO, t); }
	// distancia que recorre hasta quedar frente al rival
	static float llega(const Situacion& s) { return glm::max(0.0f, glm::length(s.rival - s.base) - 0.9f * s.ancho); }

	// se balancea hacia atras (lento, pesado), camina con pasos pesados hasta el rival, golpea y vuelve
	void atacar(const Situacion& s, Pose& p) const override
	{
		const float atras = suave(0.2f, ARRANCA, s.t) * (1.0f - suave(ARRANCA, ARRANCA + 0.4f, s.t));
		const float ida = avance(s.t);
		const float golpe = suave(IMPACTO - 0.15f, IMPACTO, s.t) * (1.0f - suave(IMPACTO + 0.2f, IMPACTO + 0.7f, s.t));
		const float vuelta = suave(IMPACTO + 0.5f, IMPACTO + 1.6f, s.t);
		p.desplazar += s.hacia * (llega(s) * ida * (1.0f - vuelta) - 0.15f * atras);
		// pasos pesados: sube un poco entre paso y paso y cae seco en cada pisada
		const float paso = (s.t - ARRANCA) / PASO;
		if (paso > 0.0f && paso < 3.0f) {
			p.desplazar.y += 0.08f * fabsf(sinf(3.14159f * paso));
			p.girar += 0.05f * sinf(3.14159f * paso);
		}
		// vuelve a su carta con pasos mas cortos
		const float pasoVuelta = (s.t - (IMPACTO + 0.5f)) / 0.37f;
		if (pasoVuelta > 0.0f && pasoVuelta < 3.0f) {
			p.desplazar.y += 0.05f * fabsf(sinf(3.14159f * pasoVuelta));
		}
		p.inclinar += -0.22f * atras + 0.5f * golpe;
		p.aplastar *= 1.0f - 0.05f * atras;
		p.brillo += 0.4f * atras;
	}

	// polvo en cada pisada y demolicion de rocas al golpear (trozos de piedra, nube de polvo y destello corto)
	void efecto(const Situacion& s, glm::vec3, glm::vec3 hasta, Pincel& pincel) const override
	{
		const glm::vec3 arriba(0.0f, 1.0f, 0.0f);
		const glm::vec3 lado = glm::normalize(glm::cross(s.hacia, arriba));
		const glm::vec3 polvo(0.55f, 0.5f, 0.43f);

		// polvo de las pisadas (al final de cada paso)
		for (int k = 1; k <= 3; k++) {
			const float pisa = ARRANCA + PASO * k;
			const float e = s.t - pisa;
			if (e < 0.0f || e > 0.5f) {
				continue;
			}
			const float q = 1.0f - e / 0.5f;
			const glm::vec3 pie = s.base + s.hacia * (llega(s) * avance(pisa));
			for (int i = 0; i < 4; i++) {
				const float a = 6.2832f * i / 4.0f + azar(s.semilla + 17u * k + i);
				const glm::vec3 afuera(cosf(a), 0.0f, sinf(a));
				pincel.bola(pie + afuera * (0.35f * s.ancho + 0.8f * e) + arriba * (0.08f + 0.2f * e),
					(0.06f + 0.15f * e) * s.ancho * 0.5f, polvo, 0.04f * q);   // polvo tenue (suma luz)
			}
		}

		const float u = s.t - IMPACTO;
		if (u < 0.0f || u > 1.6f) {
			return;
		}
		// destello corto del choque
		if (u < 0.25f) {
			const float k = 1.0f - u / 0.25f;
			pincel.bola(hasta, (0.3f + 0.8f * u) * s.ancho * 0.5f, s.halo, 0.3f * k);
			pincel.bola(hasta, 0.15f * k, glm::vec3(1.0f, 0.95f, 0.85f), 1.3f * k);
		}
		// nube de polvo que se expande y se va
		const float nube = 1.0f - suave(0.4f, 1.6f, u);
		for (int i = 0; i < 10; i++) {
			const float a = 6.2832f * i / 10.0f + azar(s.semilla + 53u * i);
			const glm::vec3 afuera = s.hacia * (0.6f * cosf(a) + 0.4f) + lado * sinf(a);
			const glm::vec3 punto = hasta + afuera * (0.2f + 1.0f * suave(0.0f, 1.2f, u)) * s.ancho * 0.6f +
				arriba * (0.3f * u - 0.25f * azar(s.semilla + 59u * i));
			pincel.bola(punto, (0.1f + 0.22f * suave(0.0f, 1.0f, u)) * s.ancho * 0.5f, polvo, 0.035f * nube);
		}
		// trozos de roca disparados en abanico que caen con gravedad y quedan en el piso
		for (int i = 0; i < 24; i++) {
			const uint32_t n = s.semilla + 131u * i;
			const float a = (azar(n) - 0.5f) * 2.8f;
			const glm::vec3 afuera = s.hacia * cosf(a) + lado * sinf(a);
			const glm::vec3 vel = afuera * (1.0f + 2.2f * azar(n + 1u)) + arriba * (1.2f + 2.6f * azar(n + 2u));
			const float r = (0.025f + 0.045f * azar(n + 3u)) * s.ancho;
			glm::vec3 punto = hasta + vel * u;
			punto.y -= 0.5f * GRAVEDAD * u * u;
			if (punto.y < r) {
				// toco el piso: se queda ahi (sin seguir avanzando)
				const float tPiso = (vel.y + sqrtf(glm::max(0.0f, vel.y * vel.y + 2.0f * GRAVEDAD * (hasta.y - r)))) / GRAVEDAD;
				punto = hasta + vel * tPiso;
				punto.y = r;
			}
			const float gris = 0.8f + 0.4f * azar(n + 4u);
			const glm::vec3 piedra = glm::vec3(0.5f, 0.44f, 0.36f) * gris;
			pincel.bola(punto, r, piedra, (0.25f + 0.25f * azar(n + 5u)) * (1.0f - suave(1.1f, 1.6f, u)));
		}
	}

	// cierra los ojos y recibe el impacto: es duro, se encoge poco, retrocede corto y tiembla
	void defender(const Situacion& s, Pose& p) const override
	{
		const float cubre = suave(CUBRE, CUBRE + 0.2f, s.t);
		const float u = glm::max(0.0f, s.t - IMPACTO);
		const glm::vec3 lado = glm::normalize(glm::cross(s.hacia, glm::vec3(0.0f, 1.0f, 0.0f)));
		p.ojos = cubre;
		p.escala *= 1.0f - 0.03f * cubre;
		p.desplazar -= s.hacia * 0.25f * suave(0.0f, 0.2f, u);
		p.desplazar += lado * 0.04f * sinf(u * 40.0f) * expf(-u * 4.0f);
		p.inclinar -= 0.12f * suave(0.0f, 0.2f, u);
	}

	// cae de costado al piso con un golpe seco (rebote corto) y se desintegra
	void derrota(const Situacion& s, Pose& p) const override
	{
		p.ojos = 1.0f;
		p.desplazar -= s.hacia * 0.3f;
		p.caer = 1.5f * suave(MUERE, MUERE + 0.45f, s.t);
		const float r = s.t - (MUERE + 0.45f);
		if (r > 0.0f && r < 0.2f) {
			p.caer -= 0.06f * sinf(3.14159f * r / 0.2f);
		}
		p.desintegrar = suave(DESAPARECE, DESAPARECE + 1.0f, s.t);
	}

	// polvo y algunas piedritas al caer al piso
	void efectoDerrota(const Situacion& s, glm::vec3 donde, Pincel& pincel) const override
	{
		const float u = s.t - (MUERE + 0.45f);
		if (u < 0.0f || u > 1.5f) {
			return;
		}
		const glm::vec3 arriba(0.0f, 1.0f, 0.0f);
		const glm::vec3 polvo(0.55f, 0.5f, 0.43f);
		const float q = 1.0f - suave(0.4f, 1.5f, u);
		for (int i = 0; i < 12; i++) {
			const float a = 6.2832f * i / 12.0f + azar(s.semilla + 211u * i);
			const glm::vec3 afuera(cosf(a), 0.0f, sinf(a));
			const glm::vec3 punto = donde + afuera * (0.5f * s.ancho + 1.2f * suave(0.0f, 1.2f, u)) + arriba * (0.1f + 0.3f * u);
			pincel.bola(punto, (0.08f + 0.2f * suave(0.0f, 1.0f, u)) * s.ancho * 0.5f, polvo, 0.035f * q);
		}
		for (int i = 0; i < 6; i++) {
			const uint32_t n = s.semilla + 307u * i;
			const float a = 6.2832f * azar(n);
			const glm::vec3 vel = glm::vec3(cosf(a), 0.0f, sinf(a)) * (0.8f + 1.2f * azar(n + 1u)) + arriba * (1.0f + 1.0f * azar(n + 2u));
			const float r = 0.03f * s.ancho;
			glm::vec3 punto = donde + glm::vec3(0.0f, r, 0.0f) + vel * u;
			punto.y -= 0.5f * GRAVEDAD * u * u;
			if (punto.y < r) {
				const float tPiso = 2.0f * vel.y / GRAVEDAD;
				punto = donde + vel * tPiso;
				punto.y = r;
			}
			pincel.bola(punto, r, glm::vec3(0.5f, 0.44f, 0.36f), 0.3f * q);
		}
	}
};

} // namespace combate
