// Regla 6 del Excel: "los dragones atacan a distancia con rafaga de fuego; efecto de fuego fuerte de dragon.
// Defensa: doblan sus alas hacia el frente. Derrota: caer derrotado al piso".
// El dragon es rigido (solo Pose): se eleva, echa la cabeza atras mientras junta el fuego en la boca y al soltar
// la rafaga el aliento lo empuja; NO se lanza contra el rival. El color del fuego es el de quien ataca (halo/nucleo).
#pragma once
#include "combate_api.h"

namespace combate {

struct ReglaDragon : Regla {
	const char* nombre() const override { return "dragon"; }

	// se eleva, echa el cuerpo atras cargando el fuego, sopla (empujon del aliento) y vuelve
	void atacar(const Situacion& s, Pose& p) const override
	{
		const float sube = suave(0.2f, 1.0f, s.t) * (1.0f - suave(FIN_EFECTO, FIN_EFECTO + 0.8f, s.t));
		const float carga = suave(0.2f, SUELTA, s.t) * (1.0f - suave(SUELTA, SUELTA + 0.12f, s.t));
		const float sopla = suave(SUELTA, SUELTA + 0.12f, s.t) * (1.0f - suave(FIN_EFECTO - 0.3f, FIN_EFECTO + 0.3f, s.t));
		const float u = glm::max(0.0f, s.t - SUELTA);
		p.desplazar.y += (s.vuela ? 0.6f : 0.12f) * sube + 0.04f * sinf(s.t * 2.5f) * sube;
		p.inclinar += -0.28f * carga + 0.16f * sopla;
		p.desplazar -= s.hacia * (0.08f * carga + 0.3f * sopla);              // retroceso del aliento
		p.girar += 0.025f * sinf(u * 37.0f) * sopla;                          // vibra mientras escupe fuego
		p.escala *= 1.0f + 0.04f * carga;                                      // toma aire
		p.brillo += 1.1f * carga + 0.4f * sopla;
	}

	// la boca: adelante y arriba del cuerpo (el motor ya suma pose.desplazar)
	glm::vec3 origen(const Situacion& s) const override
	{
		return s.base + s.hacia * (0.45f * s.ancho) + glm::vec3(0.0f, 0.75f * s.alto, 0.0f);
	}

	// rafaga de fuego: bolas que laten en la boca al cargar, chorro turbulento hasta el rival y llamas al llegar
	void efecto(const Situacion& s, glm::vec3 desde, glm::vec3 hasta, Pincel& pincel) const override
	{
		const glm::vec3 blanco(1.0f, 0.97f, 0.9f);
		const glm::vec3 calor = glm::mix(s.halo, s.nucleo, 0.5f);
		const float escala = glm::clamp(s.alto / 3.0f, 0.6f, 1.5f);

		// carga: el fuego se junta y late en la boca (hasta que sale la rafaga)
		const float junta = suave(0.6f, SUELTA - 0.1f, s.t) * (1.0f - suave(SUELTA, SUELTA + 0.25f, s.t));
		if (junta > 0.0f) {
			const float late = 0.75f + 0.25f * sinf(s.t * 22.0f);
			pincel.bola(desde, 0.45f * escala * junta * late, s.halo, 0.3f * junta);
			pincel.bola(desde, 0.16f * escala * junta * late, glm::mix(s.nucleo, blanco, 0.4f), 1.5f * junta);
			for (int i = 0; i < 6; i++) {
				const float a = 6.2832f * i / 6.0f + s.t * (2.0f + azar(s.semilla + 40u + i));
				const float r = (0.25f + 0.15f * sinf(s.t * 9.0f + i)) * escala * (1.2f - junta);
				const glm::vec3 c = desde + glm::vec3(cosf(a) * r, 0.6f * sinf(a * 1.3f) * r, sinf(a) * r);
				pincel.bola(c, 0.07f * escala * junta, calor, 0.9f * junta);
			}
		}

		// chorro: de SUELTA a FIN_EFECTO
		const glm::vec3 eje = hasta - desde;
		const float largo = glm::length(eje);
		if (s.t < SUELTA || s.t > FIN_EFECTO + 0.6f || largo < 0.01f) {
			return;
		}
		const glm::vec3 dir = eje / largo;
		glm::vec3 lado = glm::cross(dir, glm::vec3(0.0f, 1.0f, 0.0f));
		lado = glm::length(lado) > 0.01f ? glm::normalize(lado) : glm::vec3(1.0f, 0.0f, 0.0f);
		const glm::vec3 arriba = glm::cross(lado, dir);
		const float u = s.t - SUELTA;
		const float frente = suave(0.0f, 0.2f, u);                            // la punta avanza hasta el rival
		const float cola = suave(FIN_EFECTO - 0.4f, FIN_EFECTO + 0.15f, s.t); // la cola se suelta de la boca al final
		const float fuerza = suave(0.0f, 0.1f, u) * (1.0f - suave(FIN_EFECTO - 0.1f, FIN_EFECTO + 0.5f, s.t));

		if (fuerza > 0.0f && frente > cola) {
			// columna continua de luz (halo ancho y nucleo fino)
			const glm::vec3 a = desde + eje * cola, b = desde + eje * frente;
			pincel.tramo(a, b, 0.32f * escala, s.halo, 0.25f * fuerza);
			pincel.tramo(a, b, 0.09f * escala, glm::mix(s.nucleo, blanco, 0.3f), 1.2f * fuerza);
			if (cola < 0.05f) {
				pincel.bola(desde, 0.3f * escala, glm::mix(s.nucleo, blanco, 0.5f), 1.4f * fuerza);   // boca encendida
			}
		}

		// llamarada: bolas que viajan de la boca al rival con turbulencia
		for (int i = 0; i < 80; i++) {
			const bool centro = i < 32;
			const float r0 = azar(s.semilla + 100u + i);
			const float r1 = azar(s.semilla * 7u + 200u + i);
			const float r2 = azar(s.semilla * 13u + 300u + i);
			const float vel = centro ? 2.4f + 0.8f * r1 : 1.7f + 0.7f * r1;   // vueltas por segundo a lo largo del chorro
			const float f = r0 + u * vel - floorf(r0 + u * vel);              // 0 boca .. 1 rival
			if (f > frente || f < cola) {
				continue;
			}
			const float cono = (centro ? 0.12f : 0.25f) + (centro ? 0.25f : 0.75f) * f;   // se abre hacia el rival
			const float a = r2 * 6.2832f + s.t * (4.0f + 3.0f * r1) + f * 5.0f;
			const float giro = cono * escala * (centro ? 0.5f : 1.0f) * (0.4f + 0.6f * r1);
			const glm::vec3 turb = lado * (cosf(a) * giro + 0.08f * sinf(s.t * 17.0f + i)) + arriba * (sinf(a) * giro + 0.12f * f * escala);
			const glm::vec3 c = desde + eje * f + turb;
			const float apaga = (1.0f - 0.5f * f) * fuerza * suave(0.0f, 0.05f, f) * (1.0f - suave(0.92f, 1.0f, f) * 0.6f);
			if (centro) {
				const glm::vec3 col = glm::mix(glm::mix(s.nucleo, blanco, 0.45f), calor, f);
				pincel.bola(c, (0.14f + 0.12f * f) * escala, col, 1.3f * apaga);
			} else {
				const glm::vec3 col = glm::mix(calor, s.halo, glm::clamp(0.3f + f, 0.0f, 1.0f));
				pincel.bola(c, (0.2f + 0.35f * f) * escala, col, 0.3f * apaga);
			}
		}

		// estallido y llamas en el rival
		const float v = s.t - (SUELTA + 0.15f);
		if (v > 0.0f) {
			const float arde = suave(0.0f, 0.1f, v) * (1.0f - suave(FIN_EFECTO - SUELTA - 0.3f, FIN_EFECTO - SUELTA + 0.45f, v));
			if (arde > 0.0f) {
				const float late = 0.85f + 0.15f * sinf(s.t * 19.0f);
				pincel.bola(hasta, (0.6f + 0.3f * suave(0.0f, 0.4f, v)) * escala * late, s.halo, 0.35f * arde);
				pincel.bola(hasta, 0.25f * escala * late, glm::mix(s.nucleo, blanco, 0.4f), 1.5f * arde);
				for (int i = 0; i < 16; i++) {
					const float r0 = azar(s.semilla + 500u + i);
					const float r1 = azar(s.semilla * 5u + 600u + i);
					const float vida = 0.55f + 0.35f * r1;
					const float q = (v + r0 * vida) / vida - floorf((v + r0 * vida) / vida);   // 0..1 vida de la llama
					const float a = 6.2832f * (i / 16.0f) + r0;
					const float sal = (0.2f + 0.9f * q) * escala;
					const glm::vec3 c = hasta + glm::vec3(cosf(a) * sal * 0.7f, 1.2f * q * escala, sinf(a) * sal * 0.7f) - dir * 0.2f * escala;
					pincel.bola(c, (0.2f - 0.12f * q) * escala, glm::mix(calor, s.halo, q), (1.0f - q) * 0.9f * arde);
				}
			}
		}
	}

	// dobla las alas al frente: gira de costado, se encoge, se echa atras, retrocede con el fuego y tiembla
	void defender(const Situacion& s, Pose& p) const override
	{
		const float cubre = suave(CUBRE, CUBRE + 0.2f, s.t);
		const float u = glm::max(0.0f, s.t - IMPACTO);
		const float quema = suave(0.0f, 0.1f, u) * (1.0f - suave(FIN_EFECTO - IMPACTO - 0.3f, FIN_EFECTO - IMPACTO + 0.3f, u));
		p.ojos = 1.0f;
		p.girar += 0.5f * cubre + 0.05f * sinf(u * 31.0f) * quema;
		p.escala *= 1.0f - 0.1f * cubre;
		p.inclinar -= 0.15f * cubre + 0.12f * suave(0.0f, 0.2f, u);
		p.desplazar -= s.hacia * 0.55f * suave(0.0f, 0.4f, u);
		p.desplazar.y += 0.03f * sinf(u * 43.0f) * quema;
	}

	// cae al piso (si vuela, primero baja del aire), se tumba de costado con un rebote y se desintegra
	void derrota(const Situacion& s, Pose& p) const override
	{
		p.ojos = 1.0f;
		p.desplazar -= s.hacia * 0.55f;
		float empieza = MUERE;
		if (s.vuela) {
			p.desplazar.y -= 0.5f * suave(MUERE, MUERE + 0.35f, s.t);
			empieza += 0.25f;
		}
		p.caer = 1.52f * suave(empieza, empieza + 0.55f, s.t);
		const float r = s.t - (empieza + 0.55f);
		if (r > 0.0f && r < 0.35f) {
			p.caer -= 0.12f * sinf(3.14159f * r / 0.35f);
		}
		p.desintegrar = suave(DESAPARECE, DESAPARECE + 1.0f, s.t);
	}

	// brasas al caer
	void efectoDerrota(const Situacion& s, glm::vec3 donde, Pincel& pincel) const override
	{
		const float u = s.t - (MUERE + 0.6f);
		if (u < 0.0f || u > 2.5f) {
			return;
		}
		const float k = suave(0.0f, 0.15f, u) * (1.0f - suave(1.6f, 2.5f, u));
		const glm::vec3 brasa(1.0f, 0.45f, 0.12f);
		// (sin humo: los efectos suman luz y el humo gris se veia como manchas blancas)
		for (int i = 0; i < 12; i++) {
			const float r0 = azar(s.semilla + 800u + i);
			const float r1 = azar(s.semilla * 3u + 900u + i);
			const float a = 6.2832f * r0;
			const float sal = (0.3f + 0.6f * r1) * s.ancho * 0.3f;
			const glm::vec3 c = donde + glm::vec3(cosf(a) * sal, 0.1f + u * (0.4f + 0.5f * r1), sinf(a) * sal);
			const float chispa = 0.6f + 0.4f * sinf(s.t * 13.0f + i * 2.1f);
			pincel.bola(c, 0.05f, brasa, 0.8f * k * chispa * (1.0f - 0.3f * r1));
		}
	}
};

} // namespace combate
