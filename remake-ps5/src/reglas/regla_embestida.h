// Regla 5b del Excel (y la que usa el motor si una regla no esta escrita todavia): "los que no tienen nada de armas
// y no son hechiceros atacan con embestida de bestia; efecto de golpe duro; defensa: cierran los ojos y reciben el
// impacto; derrota: caer derrotado al piso". Es tambien el MODELO para escribir las demas reglas.
// Kuriboh usa esta regla: va de frente al rival (todo el avance es sobre s.hacia), salta y choca.
#pragma once
#include "combate_api.h"

namespace combate {

struct ReglaEmbestida : Regla {
	const char* nombre() const override { return "embestida"; }

	static constexpr float PI = 3.14159265f;
	static constexpr float SALTA = 1.05f;   // termina de agazaparse y salta (llega al rival en IMPACTO)

	// distancia que recorre hasta quedar frente al rival
	static float llega(const Situacion& s) { return glm::max(0.0f, glm::length(s.rival - s.base) - 0.9f * s.ancho); }

	// se agazapa (hacia atras, aplastado), salta en arco de frente al rival, choca (se aplasta contra el), rebota
	// hacia atras y vuelve a su carta con dos saltitos
	void atacar(const Situacion& s, Pose& p) const override
	{
		const float t = s.t;
		const float agazapa = suave(0.2f, SALTA, t) * (1.0f - suave(SALTA, SALTA + 0.12f, t));
		const float ida = suave(SALTA, IMPACTO, t);
		const float choque = suave(IMPACTO - 0.05f, IMPACTO, t) * (1.0f - suave(IMPACTO + 0.05f, IMPACTO + 0.3f, t));
		const float rebote = suave(IMPACTO, IMPACTO + 0.35f, t);
		const float vuelta = suave(IMPACTO + 0.45f, IMPACTO + 1.45f, t);
		const float alto = glm::clamp(0.35f * s.alto, 0.35f, 0.8f);   // altura del salto
		// avance de frente: va hasta el rival, el golpe lo echa un poco atras y luego regresa
		const float adelante = llega(s) * ida - 0.45f * rebote;
		p.desplazar += s.hacia * (adelante * (1.0f - vuelta) - 0.3f * agazapa);
		// salto en arco a la ida, saltito al rebotar y dos saltitos al volver
		float y = -0.1f * agazapa + alto * sinf(PI * ida) * (1.0f - rebote);
		y += 0.25f * sinf(PI * rebote) * (1.0f - vuelta);
		y += 0.18f * fabsf(sinf(2.0f * PI * vuelta));
		p.desplazar.y += y;
		// se inclina hacia atras al agazaparse, hacia el rival en el salto; se aplasta al tomar impulso y al chocar
		p.inclinar += -0.25f * agazapa + 0.35f * ida * (1.0f - rebote) - 0.2f * sinf(PI * rebote) * (1.0f - vuelta);
		p.aplastar *= (1.0f - 0.15f * agazapa) * (1.0f - 0.18f * choque);
		p.escala *= 1.0f + 0.06f * choque;
		p.brillo += 0.8f * agazapa + 0.4f * sinf(PI * ida);
	}

	// golpe duro: destello y chispas en el pecho del rival al chocar; polvo (humo color tierra) al despegar y al
	// caer frente al rival
	void efecto(const Situacion& s, glm::vec3, glm::vec3 hasta, Pincel& pincel) const override
	{
		const glm::vec3 tierra(0.42f, 0.33f, 0.24f);
		polvo(s, s.base, s.t - SALTA, 0.6f, tierra, pincel);
		polvo(s, s.base + s.hacia * llega(s), s.t - IMPACTO, 0.9f, tierra, pincel);
		const float u = s.t - IMPACTO;
		if (u < 0.0f || u > 0.6f) {
			return;
		}
		const float k = 1.0f - u / 0.6f;
		pincel.bola(hasta, (0.3f + 0.9f * u) * s.ancho * 0.5f, s.halo, 0.35f * k);
		pincel.bola(hasta, 0.18f * k, s.nucleo, 1.5f * k);
		for (int i = 0; i < 8; i++) {
			const float a = 6.2832f * i / 8.0f + azar(s.semilla + i);
			const glm::vec3 dir(cosf(a), 0.3f * azar(s.semilla * 3u + i), sinf(a));
			pincel.tramo(hasta + dir * (0.2f + 0.8f * u), hasta + dir * (0.35f + 1.2f * u), 0.03f * k, s.nucleo, 0.9f * k);
		}
	}

	// cierra los ojos y recibe el impacto: se encoge un poco, retrocede y tiembla
	void defender(const Situacion& s, Pose& p) const override
	{
		const float cubre = suave(CUBRE, CUBRE + 0.2f, s.t);
		const float u = glm::max(0.0f, s.t - IMPACTO);
		p.ojos = cubre;
		p.escala *= 1.0f - 0.06f * cubre;
		p.desplazar -= s.hacia * 0.5f * suave(0.0f, 0.25f, u);
		p.inclinar -= 0.28f * suave(0.0f, 0.2f, u);
		p.girar += 0.24f * sinf(u * 18.0f) * expf(-u * 3.0f);
	}

	// cae de espaldas como el Guardian (lejos del atacante) y se desintegra
	void derrota(const Situacion& s, Pose& p) const override { caerDeEspaldas(s, p); }

	// polvo cuando la espalda azota la mesa
	void efectoDerrota(const Situacion& s, glm::vec3 donde, Pincel& pincel) const override
	{
		const float azota = MUERE + (s.vuela ? 0.45f : 0.0f) + 0.7f;
		polvo(s, glm::vec3(donde.x, 0.0f, donde.z) - s.hacia * (0.4f * s.alto), s.t - azota, 1.0f, glm::vec3(0.42f, 0.33f, 0.24f), pincel);
	}

	// nube de polvo a ras de mesa que se abre y se disipa (u = segundos desde que nace; 8 bocanadas de humo)
	static void polvo(const Situacion& s, glm::vec3 suelo, float u, float tam, glm::vec3 color, Pincel& pincel)
	{
		if (u < 0.0f || u > 1.0f) {
			return;
		}
		const float q = 1.0f - suave(0.3f, 1.0f, u);
		const float abre = suave(0.0f, 0.8f, u);
		for (int i = 0; i < 8; i++) {
			const float a = 6.2832f * i / 8.0f + azar(s.semilla * 29u + i);
			const glm::vec3 afuera(cosf(a), 0.0f, sinf(a));
			const glm::vec3 c = glm::vec3(suelo.x, 0.0f, suelo.z) + afuera * ((0.25f + 0.6f * abre) * s.ancho * tam) +
				glm::vec3(0.0f, 0.1f + 0.25f * abre * tam, 0.0f);
			pincel.humo(c, (0.12f + 0.25f * abre) * glm::min(s.ancho, 2.0f) * tam, color * (0.8f + 0.4f * azar(s.semilla + 7u * i)), 0.55f * q);
		}
	}
};

} // namespace combate
