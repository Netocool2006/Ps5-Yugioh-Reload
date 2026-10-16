// Regla 6 del Excel: "los dragones atacan a distancia con rafaga de fuego; efecto de fuego fuerte de dragon.
// Defensa: doblan sus alas hacia el frente. Derrota: caer derrotado al piso".
// El dragon es rigido (solo Pose): vuela (el motor ya suma s.vuelo y aletea), se eleva un poco mas, echa la cabeza
// atras mientras junta el fuego en la boca y al soltar la llamarada el aliento lo empuja; NO se lanza contra el rival.
// El fuego es FUEGO DE VERDAD (Pincel::llama); los de ataque azulado (Ojos Azules) sueltan un rayo de luz blanco-azul.
// Derrota: cae de ESPALDAS como el Guardian (caerDeEspaldas: si vuela, primero cae al suelo).
#pragma once
#include "combate_api.h"

namespace combate {

struct ReglaDragon : Regla {
	const char* nombre() const override { return "dragon"; }

	// su ataque es luz (Ojos Azules: halo azulado) y no fuego
	static bool esLuz(const Situacion& s) { return s.halo.b > s.halo.r; }

	// se eleva, echa el cuerpo atras cargando el fuego, sopla (empujon del aliento) y vuelve; aletea mas rapido
	void atacar(const Situacion& s, Pose& p) const override
	{
		const float sube = suave(0.2f, 1.0f, s.t) * (1.0f - suave(FIN_EFECTO, FIN_EFECTO + 0.8f, s.t));
		const float carga = suave(0.2f, SUELTA, s.t) * (1.0f - suave(SUELTA, SUELTA + 0.12f, s.t));
		const float sopla = suave(SUELTA, SUELTA + 0.12f, s.t) * (1.0f - suave(FIN_EFECTO - 0.3f, FIN_EFECTO + 0.3f, s.t));
		const float u = glm::max(0.0f, s.t - SUELTA);
		p.desplazar.y += (s.vuela ? 0.35f : 0.12f) * sube + 0.04f * sinf(s.t * 2.5f) * sube;
		p.inclinar += -0.28f * carga + 0.16f * sopla;
		p.desplazar -= s.hacia * (0.08f * carga + 0.3f * sopla);              // retroceso del aliento
		p.girar += 0.025f * sinf(u * 37.0f) * sopla;                          // vibra mientras escupe fuego
		p.escala *= 1.0f + 0.04f * carga;                                      // toma aire
		p.brillo += 0.6f * carga + 0.2f * sopla;
		p.aleteo = 1.0f + 1.6f * sube + 0.6f * carga;                          // bate las alas para sostenerse
	}

	// la boca: adelante y arriba del cuerpo (el motor ya suma pose.desplazar)
	glm::vec3 origen(const Situacion& s) const override
	{
		return s.base + s.hacia * (0.45f * s.ancho) + glm::vec3(0.0f, 0.75f * s.alto, 0.0f);
	}

	void efecto(const Situacion& s, glm::vec3 desde, glm::vec3 hasta, Pincel& pincel) const override
	{
		const glm::vec3 eje = hasta - desde;
		const float largo = glm::length(eje);
		if (largo < 0.01f) {
			return;
		}
		const glm::vec3 dir = eje / largo;
		glm::vec3 lado = glm::cross(dir, glm::vec3(0.0f, 1.0f, 0.0f));
		lado = glm::length(lado) > 0.01f ? glm::normalize(lado) : glm::vec3(1.0f, 0.0f, 0.0f);
		const glm::vec3 arriba = glm::cross(lado, dir);
		const float escala = glm::clamp(s.alto / 3.0f, 0.6f, 1.5f);
		if (esLuz(s)) {
			rayoLuz(s, desde, hasta, dir, lado, arriba, escala, pincel);
		} else {
			llamarada(s, desde, hasta, dir, lado, arriba, escala, pincel);
		}
	}

	// dobla las alas al frente: gira de costado, se encoge, se echa atras, retrocede con el golpe y tiembla
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
		p.aleteo = 1.0f - 0.7f * cubre;                                        // las alas quedan cerradas al frente
	}

	// cae de espaldas como el Guardian (si vuela, primero cae al suelo) y se desintegra
	void derrota(const Situacion& s, Pose& p) const override
	{
		caerDeEspaldas(s, p);
	}

	// brasas que saltan y humo que sube mientras cae
	void efectoDerrota(const Situacion& s, glm::vec3 donde, Pincel& pincel) const override
	{
		const float u = s.t - MUERE;
		if (u < 0.0f || u > 3.0f) {
			return;
		}
		const float k = suave(0.0f, 0.15f, u) * (1.0f - suave(2.0f, 3.0f, u));
		const glm::vec3 brasa = glm::mix(glm::vec3(1.0f, 0.45f, 0.12f), s.nucleo, 0.25f);
		for (int i = 0; i < 16; i++) {
			const float r0 = azar(s.semilla + 800u + i);
			const float r1 = azar(s.semilla * 3u + 900u + i);
			const float vida = 0.8f + 0.6f * r1;
			const float fase = (u + r0 * vida) / vida;
			const float q = fase - floorf(fase);                                 // 0..1 vida de la brasa
			const float a = 6.2832f * r0 + 2.0f * floorf(fase);
			const float sal = (0.2f + 0.8f * q) * s.ancho * 0.4f;
			glm::vec3 c = donde + glm::vec3(cosf(a) * sal, 0.1f + 1.6f * q * (0.6f + 0.4f * r1), sinf(a) * sal);
			c.y -= 1.2f * q * q;
			c.y = glm::max(c.y, 0.03f);
			const float chispa = 0.6f + 0.4f * sinf(s.t * 13.0f + i * 2.1f);
			pincel.bola(c, 0.04f + 0.03f * (1.0f - q), brasa, 0.9f * k * chispa * (1.0f - q));
		}
		const glm::vec3 gris(0.16f, 0.14f, 0.13f);
		for (int i = 0; i < 6; i++) {
			const float r0 = azar(s.semilla + 950u + i);
			const float q = fmodf(u * 0.45f + r0, 1.0f);
			const glm::vec3 c = donde + glm::vec3((r0 - 0.5f) * s.ancho * 0.6f, 0.2f + 1.8f * q, (azar(s.semilla + 960u + i) - 0.5f) * s.ancho * 0.6f);
			pincel.humo(c, (0.25f + 0.5f * q) * s.ancho * 0.5f, gris, 0.45f * k * (1.0f - q));
		}
	}

private:
	// FUEGO DE VERDAD: carga en la boca, cadena de lenguas que crece desde la boca hasta el rival, brasas, humo en
	// las puntas y llamas que envuelven al rival
	static void llamarada(const Situacion& s, glm::vec3 desde, glm::vec3 hasta, glm::vec3 dir, glm::vec3 lado,
		glm::vec3 arriba, float escala, Pincel& pincel)
	{
		const glm::vec3 eje = hasta - desde;
		const float largo = glm::length(eje);
		const glm::vec3 brasa = glm::mix(glm::vec3(1.0f, 0.5f, 0.12f), glm::mix(s.halo, s.nucleo, 0.5f), 0.25f);
		const glm::vec3 gris(0.16f, 0.14f, 0.13f);

		// carga: lenguitas que se encienden y lamen la boca
		const float junta = suave(0.6f, SUELTA - 0.1f, s.t) * (1.0f - suave(SUELTA, SUELTA + 0.2f, s.t));
		if (junta > 0.0f) {
			for (int i = 0; i < 6; i++) {
				const float r0 = azar(s.semilla + 40u + i);
				const float a = 6.2832f * (i / 6.0f + r0) + s.t * (3.0f + 2.0f * r0);
				const glm::vec3 sale = dir * 0.6f + arriba * (0.5f + 0.4f * sinf(s.t * 7.0f + i)) + lado * cosf(a) * 0.5f;
				const float alto = (0.2f + 0.12f * sinf(s.t * 11.0f + 2.0f * i)) * escala * junta;
				pincel.llama(desde, desde + sale * alto, 0.1f * escala * junta, 0.5f + 0.5f * junta, s.semilla + 50u + i);
			}
			for (int i = 0; i < 4; i++) {
				const float q = fmodf(s.t * 1.5f + azar(s.semilla + 60u + i), 1.0f);
				const glm::vec3 c = desde + arriba * (0.1f + 0.4f * q) * escala + lado * (azar(s.semilla + 70u + i) - 0.5f) * 0.3f;
				pincel.bola(c, 0.03f * escala, brasa, 0.8f * junta * (1.0f - q));
			}
		}

		if (s.t < SUELTA || s.t > FIN_EFECTO + 0.8f) {
			return;
		}
		const float u = s.t - SUELTA;
		const float frente = suave(0.0f, 0.3f, u);                            // la llamarada crece de la boca al rival
		const float cola = suave(FIN_EFECTO - 0.35f, FIN_EFECTO + 0.3f, s.t); // al final se suelta de la boca
		const float fuerza = suave(0.0f, 0.08f, u) * (1.0f - suave(FIN_EFECTO - 0.1f, FIN_EFECTO + 0.6f, s.t));

		// la cadena: lenguas encadenadas que cubren el chorro (cada una con su semilla, mas anchas hacia el rival)
		const int CADENA = 14;
		if (fuerza > 0.0f && frente > cola) {
			for (int i = 0; i < CADENA; i++) {
				const float f0 = glm::mix(cola, frente, i / (float)CADENA);
				const float f1 = glm::mix(cola, frente, glm::min(1.0f, (i + 1.6f) / (float)CADENA));
				const float t0 = s.t * 9.0f + i * 1.7f;
				const glm::vec3 temb0 = (lado * sinf(t0) + arriba * cosf(t0 * 1.3f)) * (0.05f + 0.18f * f0) * escala;
				const glm::vec3 temb1 = (lado * sinf(t0 + 1.1f) + arriba * cosf(t0 * 1.3f + 0.8f)) * (0.05f + 0.18f * f1) * escala;
				const glm::vec3 a = desde + eje * f0 + temb0;
				const glm::vec3 b = desde + eje * f1 + temb1 + arriba * 0.08f * f1 * escala;   // el fuego sube un poco
				const float ancho = (0.18f + 0.7f * f0) * escala;
				pincel.llama(a, b, ancho, fuerza * (1.0f - 0.25f * f0), s.semilla * 31u + 1000u + i);
			}
		}

		// lenguas sueltas que viajan por el chorro (turbulencia): cada una nace en la boca y avanza
		for (int i = 0; i < 24; i++) {
			const float r0 = azar(s.semilla + 100u + i);
			const float r1 = azar(s.semilla * 7u + 200u + i);
			const float r2 = azar(s.semilla * 13u + 300u + i);
			const float vel = 1.6f + 1.0f * r1;
			const float fase = r0 + u * vel;
			const float f = fase - floorf(fase);                                 // 0 boca .. 1 rival
			if (f > frente || f < cola) {
				continue;
			}
			const float abre = (0.1f + 0.45f * f) * escala;
			const float a = r2 * 6.2832f + s.t * (4.0f + 3.0f * r1) + f * 5.0f;
			const glm::vec3 turb = lado * cosf(a) * abre * (0.4f + 0.6f * r1) + arriba * (sinf(a) * abre * 0.6f + 0.15f * f * escala);
			const glm::vec3 c = desde + eje * f + turb;
			const float tramo = (0.12f + 0.12f * r2) * largo * glm::min(1.0f, f * 4.0f + 0.2f);
			const glm::vec3 punta = c + dir * tramo + arriba * 0.15f * f * escala;
			const float apaga = fuerza * suave(0.0f, 0.06f, f) * (1.0f - 0.4f * suave(0.85f, 1.0f, f));
			pincel.llama(c, punta, (0.15f + 0.55f * f) * escala, apaga, s.semilla * 17u + 2000u + i + 97u * (uint32_t)floorf(fase));
		}

		// brasas chicas que escapan del chorro
		for (int i = 0; i < 20; i++) {
			const float r0 = azar(s.semilla + 400u + i);
			const float r1 = azar(s.semilla * 3u + 450u + i);
			const float vida = 0.6f + 0.5f * r1;
			const float fase = (u + r0 * vida) / vida;
			const float q = fase - floorf(fase);
			const float nace = s.t - q * vida;
			if (nace < SUELTA || nace > FIN_EFECTO) {
				continue;
			}
			const uint32_t n = s.semilla + 461u * i + 7919u * (uint32_t)floorf(fase);
			const float x = glm::max(cola, frente * azar(n));
			const float a = 6.2832f * azar(n + 1u);
			glm::vec3 c = desde + eje * x + (lado * cosf(a) + arriba * sinf(a)) * (0.3f + 0.6f * q) * escala + dir * 0.8f * q;
			c.y += 0.6f * q - 0.5f * q * q;
			pincel.bola(c, 0.025f + 0.025f * (1.0f - q), brasa, 1.1f * (1.0f - q) * fuerza);
		}

		// humo que sale de las puntas de la llamarada y sube
		const float humea = glm::min(1.0f, fuerza + 0.6f * suave(FIN_EFECTO - 0.2f, FIN_EFECTO + 0.2f, s.t) * (1.0f - suave(FIN_EFECTO + 0.2f, FIN_EFECTO + 0.8f, s.t)));
		for (int i = 0; i < 8; i++) {
			const float r0 = azar(s.semilla + 700u + i);
			const float q = fmodf(u * 0.9f + r0, 1.0f);
			const float x = glm::clamp(frente * (0.5f + 0.5f * azar(s.semilla + 710u + i)), 0.0f, 1.0f);
			const glm::vec3 c = desde + eje * x + arriba * (0.4f + 1.4f * q) * escala + lado * (r0 - 0.5f) * escala;
			pincel.humo(c, (0.25f + 0.5f * q) * escala, gris, 0.4f * humea * (1.0f - q) * frente);
		}

		// llamas que envuelven al rival
		const float v = s.t - (SUELTA + 0.25f);
		if (v > 0.0f) {
			const float arde = suave(0.0f, 0.15f, v) * (1.0f - suave(FIN_EFECTO - SUELTA - 0.2f, FIN_EFECTO - SUELTA + 0.6f, v));
			if (arde > 0.0f) {
				const glm::vec3 pie(hasta.x, glm::max(0.0f, hasta.y - 0.6f * s.alto), hasta.z);
				for (int i = 0; i < 12; i++) {
					const float r0 = azar(s.semilla + 500u + i);
					const float r1 = azar(s.semilla * 5u + 600u + i);
					const float a = 6.2832f * (i / 12.0f) + r0 + 0.4f * sinf(s.t * 3.0f + i);
					const float radio = (0.35f + 0.25f * r1) * s.ancho * 0.5f;
					const float altura = s.alto * (0.15f + 0.85f * (i % 3) / 3.0f);
					const glm::vec3 b = pie + glm::vec3(cosf(a) * radio, altura, sinf(a) * radio);
					const float lame = (0.5f + 0.35f * sinf(s.t * 8.0f + 2.3f * i)) * escala;
					pincel.llama(b, b + glm::vec3(0.0f, lame, 0.0f) - dir * 0.15f * escala, (0.35f + 0.2f * r1) * escala, arde, s.semilla * 11u + 3000u + i);
				}
				for (int i = 0; i < 4; i++) {
					const float q = fmodf(v * 0.6f + azar(s.semilla + 650u + i), 1.0f);
					const glm::vec3 c = hasta + lado * (azar(s.semilla + 660u + i) - 0.5f) * s.ancho + glm::vec3(0.0f, (0.4f + 1.5f * q) * escala, 0.0f);
					pincel.humo(c, (0.3f + 0.5f * q) * escala, gris, 0.45f * arde * (1.0f - q));
				}
			}
		}
	}

	// LUZ (Ojos Azules): carga de luz blanca-azul en la boca, rayo recto con nucleo blanco y destello en el rival
	static void rayoLuz(const Situacion& s, glm::vec3 desde, glm::vec3 hasta, glm::vec3 dir, glm::vec3 lado,
		glm::vec3 arriba, float escala, Pincel& pincel)
	{
		const glm::vec3 blanco(1.0f, 0.98f, 1.0f);
		const glm::vec3 azul = glm::mix(glm::vec3(0.45f, 0.7f, 1.0f), s.halo, 0.4f);
		const glm::vec3 nucleo = glm::mix(blanco, s.nucleo, 0.25f);

		const float junta = suave(0.6f, SUELTA - 0.1f, s.t) * (1.0f - suave(SUELTA, SUELTA + 0.25f, s.t));
		if (junta > 0.0f) {
			const float late = 0.75f + 0.25f * sinf(s.t * 22.0f);
			pincel.bola(desde, 0.45f * escala * junta * late, azul, 0.3f * junta);
			pincel.bola(desde, 0.16f * escala * junta * late, nucleo, 1.5f * junta);
			for (int i = 0; i < 6; i++) {
				const float a = 6.2832f * i / 6.0f + s.t * (2.0f + azar(s.semilla + 40u + i));
				const float r = (0.3f + 0.15f * sinf(s.t * 9.0f + i)) * escala * (1.2f - junta);
				const glm::vec3 c = desde + lado * (cosf(a) * r) + arriba * (sinf(a) * r);
				pincel.tramo(c, glm::mix(c, desde, 0.6f), 0.02f * escala, nucleo, 0.9f * junta);   // luz que se junta
			}
		}

		if (s.t < SUELTA || s.t > FIN_EFECTO + 0.6f) {
			return;
		}
		const glm::vec3 eje = hasta - desde;
		const float u = s.t - SUELTA;
		const float frente = suave(0.0f, 0.15f, u);
		const float cola = suave(FIN_EFECTO - 0.3f, FIN_EFECTO + 0.15f, s.t);
		const float fuerza = suave(0.0f, 0.08f, u) * (1.0f - suave(FIN_EFECTO - 0.1f, FIN_EFECTO + 0.5f, s.t));
		if (fuerza > 0.0f && frente > cola) {
			const glm::vec3 a = desde + eje * cola, b = desde + eje * frente;
			const float late = 0.9f + 0.1f * sinf(s.t * 31.0f);
			pincel.tramo(a, b, 0.42f * escala * late, azul, 0.22f * fuerza);
			pincel.tramo(a, b, 0.2f * escala * late, glm::mix(azul, blanco, 0.5f), 0.5f * fuerza);
			pincel.tramo(a, b, 0.07f * escala, blanco, 1.6f * fuerza);
			if (cola < 0.05f) {
				pincel.bola(desde, 0.35f * escala, nucleo, 1.4f * fuerza);
			}
			// pulsos de energia que corren por el rayo
			for (int i = 0; i < 10; i++) {
				const float f = fmodf(azar(s.semilla + 100u + i) + u * 2.5f, 1.0f);
				if (f > frente || f < cola) {
					continue;
				}
				pincel.bola(desde + eje * f, (0.18f + 0.1f * sinf(s.t * 20.0f + i)) * escala, azul, 0.5f * fuerza);
			}
		}
		// destello en el rival y chispas de luz
		const float v = s.t - (SUELTA + 0.15f);
		if (v > 0.0f) {
			const float pega = suave(0.0f, 0.1f, v) * (1.0f - suave(FIN_EFECTO - SUELTA - 0.3f, FIN_EFECTO - SUELTA + 0.45f, v));
			if (pega > 0.0f) {
				const float late = 0.85f + 0.15f * sinf(s.t * 19.0f);
				pincel.bola(hasta, (0.7f + 0.3f * suave(0.0f, 0.4f, v)) * escala * late, azul, 0.35f * pega);
				pincel.bola(hasta, 0.3f * escala * late, blanco, 1.6f * pega);
				for (int i = 0; i < 10; i++) {
					const float q = fmodf(v * 1.6f + azar(s.semilla + 500u + i), 1.0f);
					const float a = 6.2832f * azar(s.semilla + 510u + i);
					const glm::vec3 sale = lado * cosf(a) + arriba * sinf(a) - dir * 0.5f;
					pincel.tramo(hasta + sale * (0.3f + 0.9f * q) * escala, hasta + sale * (0.45f + 1.3f * q) * escala, 0.025f, blanco, pega * (1.0f - q));
				}
			}
		}
	}
};

} // namespace combate
