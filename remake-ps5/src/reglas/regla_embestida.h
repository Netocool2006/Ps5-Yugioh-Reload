// Regla 5b del Excel (y la que usa el motor si una regla no esta escrita todavia): "los que no tienen nada de armas
// y no son hechiceros atacan con embestida de bestia; efecto de golpe duro; defensa: cierran los ojos y reciben el
// impacto; derrota: caer derrotado al piso". Es tambien el MODELO para escribir las demas reglas.
#pragma once
#include "combate_api.h"

namespace combate {

struct ReglaEmbestida : Regla {
	const char* nombre() const override { return "embestida"; }

	// se agazapa hacia atras, se lanza contra el rival (llega en IMPACTO), rebota y vuelve a su carta
	void atacar(const Situacion& s, Pose& p) const override
	{
		const float agazapa = suave(0.2f, 1.1f, s.t) * (1.0f - suave(1.1f, 1.3f, s.t));
		const float ida = suave(1.1f, IMPACTO, s.t);
		const float vuelta = suave(IMPACTO + 0.25f, IMPACTO + 1.2f, s.t);
		const float distancia = glm::length(s.rival - s.base);
		const float llega = glm::max(0.0f, distancia - 0.9f * s.ancho);   // hasta quedar frente al rival
		p.desplazar += s.hacia * (llega * ida * (1.0f - vuelta) - 0.25f * agazapa);
		p.desplazar.y += -0.08f * agazapa + 0.35f * sinf(3.14159f * ida) * (1.0f - vuelta);   // salto corto
		p.inclinar += -0.2f * agazapa + 0.3f * ida * (1.0f - vuelta);
		p.aplastar *= 1.0f - 0.08f * agazapa;
		p.brillo += 0.8f * agazapa;
	}

	// golpe duro: destello blanco y anillo de polvo en el pecho del rival, justo al chocar
	void efecto(const Situacion& s, glm::vec3, glm::vec3 hasta, Pincel& pincel) const override
	{
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

	// cae derrotado al piso (de costado, con un rebote) y se desintegra
	void derrota(const Situacion& s, Pose& p) const override
	{
		p.ojos = 1.0f;
		p.desplazar -= s.hacia * 0.5f;
		p.caer = 1.54f * suave(MUERE, MUERE + 0.55f, s.t);
		const float r = s.t - (MUERE + 0.55f);
		if (r > 0.0f && r < 0.35f) {
			p.caer -= 0.12f * sinf(3.14159f * r / 0.35f);
		}
		p.desintegrar = suave(DESAPARECE, DESAPARECE + 1.0f, s.t);
	}
};

} // namespace combate
