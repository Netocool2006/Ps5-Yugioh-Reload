// Regla 4 del Excel (monstruos de atributo agua): "tirar una rafaga de agua; efecto de agua regada; defensa: solo
// cerrar los ojos; derrota: diluirse en agua". Ataca A DISTANCIA: no se mueve hasta el rival, le tira un chorro.
// El agua es AGUA DE VERDAD (Pincel::liquido y Pincel::charco): volumenes con transparencia y reflejo, azul mar.
#pragma once
#include "combate_api.h"

namespace combate {

struct ReglaAgua : Regla {
	const char* nombre() const override { return "agua"; }

	// gravedad de las gotas (m/s2)
	static constexpr float GRAVEDAD = 9.8f;

	// color del agua: azul mar; si el halo es azulado se le mezcla un poco (si no, es agua igual: azul mar)
	static glm::vec3 colorAgua(const Situacion& s)
	{
		const glm::vec3 mar(0.08f, 0.38f, 0.72f);
		if (s.halo.b > s.halo.r && s.halo.b > 0.01f) {
			return glm::mix(mar, s.halo / glm::max(1.0f, s.halo.b), 0.3f);
		}
		return mar;
	}
	static glm::vec3 colorEspuma() { return glm::vec3(0.85f, 0.95f, 1.0f); }

	// se echa atras cargando (ondula con un vaiven chico), en SUELTA empuja adelante y sostiene el chorro
	void atacar(const Situacion& s, Pose& p) const override
	{
		const float carga = suave(0.2f, SUELTA - 0.15f, s.t) * (1.0f - suave(SUELTA - 0.15f, SUELTA + 0.05f, s.t));
		const float empuje = suave(SUELTA - 0.15f, SUELTA + 0.1f, s.t) * (1.0f - suave(FIN_EFECTO, FIN_EFECTO + 0.5f, s.t));
		const float sostiene = suave(SUELTA, SUELTA + 0.2f, s.t) * (1.0f - suave(FIN_EFECTO - 0.2f, FIN_EFECTO, s.t));
		p.desplazar += s.hacia * (0.15f * empuje - 0.22f * carga);
		p.desplazar.y += 0.05f * sinf(s.t * 8.0f) * carga;          // ondula como una ola
		p.inclinar += -0.15f * carga + 0.14f * empuje;
		p.girar += 0.05f * sinf(s.t * 5.0f) * carga;
		p.desplazar -= s.hacia * 0.015f * sinf(s.t * 35.0f) * sostiene;   // retiembla con la fuerza del chorro
		p.brillo += 0.4f * carga + 0.1f * sostiene;
		p.aleteo = 1.0f + 1.2f * (carga + sostiene);
	}

	// la rafaga sale del frente, a media-alta altura
	glm::vec3 origen(const Situacion& s) const override
	{
		return s.base + s.hacia * (0.4f * s.ancho) + glm::vec3(0.0f, 0.65f * s.alto, 0.0f);
	}

	// rafaga de agua (volumenes de agua que viajan ondulando, espuma y gotas que caen) y agua regada en el rival
	// (borbotones contra el pecho, salpicadura en abanico y charco que se forma bajo el)
	void efecto(const Situacion& s, glm::vec3 desde, glm::vec3 hasta, Pincel& pincel) const override
	{
		const float inicio = 0.7f;
		if (s.t < inicio || s.t > FIN_EFECTO + 1.8f) {
			return;
		}
		const glm::vec3 agua = colorAgua(s);
		const glm::vec3 espuma = colorEspuma();
		const glm::vec3 arriba(0.0f, 1.0f, 0.0f);
		glm::vec3 lado = glm::cross(s.hacia, arriba);
		lado = glm::length(lado) > 0.01f ? glm::normalize(lado) : glm::vec3(1.0f, 0.0f, 0.0f);
		const glm::vec3 recorrido = hasta - desde;
		const float largo = glm::max(0.01f, glm::length(recorrido));
		const glm::vec3 dir = recorrido / largo;
		const float grueso = glm::max(0.22f, 0.12f * s.ancho);   // rafaga gruesa tambien en los monstruos chicos

		// carga: el agua se arremolina en la boca
		const float junta = suave(inicio, SUELTA - 0.1f, s.t) * (1.0f - suave(SUELTA, SUELTA + 0.15f, s.t));
		if (junta > 0.0f) {
			pincel.liquido(desde, grueso * (0.6f + 0.15f * sinf(s.t * 12.0f)) * junta, agua, 0.8f * junta);
			for (int i = 0; i < 6; i++) {
				const float a = 6.2832f * i / 6.0f + s.t * 6.0f;
				const float r = grueso * (1.6f - 0.8f * junta);
				const glm::vec3 c = desde + (lado * cosf(a) + arriba * sinf(a)) * r;
				pincel.liquido(c, 0.35f * grueso * junta, i % 2 ? espuma : agua, 0.7f * junta);
			}
		}

		if (s.t < SUELTA - 0.1f) {
			return;
		}
		const float u = s.t - (SUELTA - 0.1f);
		const float frente = suave(0.0f, 0.25f, u);                          // la punta del chorro viaja al rival
		const float cola = suave(FIN_EFECTO - 0.3f, FIN_EFECTO + 0.2f, s.t);  // al final se corta en la boca
		const float apaga = 1.0f - suave(FIN_EFECTO - 0.1f, FIN_EFECTO + 0.35f, s.t);
		const float ondaFase = azar(s.semilla) * 6.0f;

		// el chorro: muchos volumenes de agua que fluyen de la boca al rival, ondulando y engrosandose
		if (apaga > 0.0f && frente > cola) {
			const int VOLUMENES = 34;
			const float corre = fmodf(s.t * 3.0f, 1.0f);
			for (int i = 0; i < VOLUMENES; i++) {
				const float x = (i + corre) / (float)VOLUMENES;
				if (x > frente || x < cola) {
					continue;
				}
				const float onda = sinf(x * 14.0f - s.t * 22.0f + ondaFase);
				const float onda2 = cosf(x * 9.0f - s.t * 17.0f);
				const glm::vec3 c = desde + recorrido * x + (lado * onda + arriba * onda2) * (0.045f * s.ancho * x);
				const float r = grueso * (0.55f + 0.5f * x) * (0.9f + 0.1f * onda);
				const float borde = suave(0.0f, 0.05f, frente - x);           // la punta se afina
				pincel.liquido(c, r * (0.5f + 0.5f * borde), agua, 0.75f * apaga);
			}
			// remolinos: volumenes chicos que giran alrededor del chorro (turbulencia)
			for (int i = 0; i < 10; i++) {
				const float x = fmodf(azar(s.semilla + 31u * i) + s.t * 2.2f, 1.0f);
				if (x > frente || x < cola) {
					continue;
				}
				const float a = 6.2832f * azar(s.semilla + 7u * i) + s.t * 9.0f;
				const glm::vec3 c = desde + recorrido * x + (lado * cosf(a) + arriba * sinf(a)) * grueso * (0.7f + 0.5f * x) +
					lado * (0.045f * s.ancho * x * sinf(x * 14.0f - s.t * 22.0f + ondaFase));
				pincel.liquido(c, grueso * (0.25f + 0.2f * azar(s.semilla + 13u * i)), agua, 0.6f * apaga);
			}
			// espuma: en la boca y en la punta del chorro
			for (int i = 0; i < 6; i++) {
				const float a = s.t * 15.0f + i * 1.05f;
				const float x = i < 3 ? glm::max(cola, 0.02f * i) : glm::max(cola, frente - 0.03f * (i - 3));
				const glm::vec3 c = desde + recorrido * x + (lado * cosf(a) + arriba * sinf(a)) * (0.45f * grueso);
				pincel.liquido(c, grueso * (0.25f + 0.08f * sinf(a * 1.3f)), espuma, 0.65f * apaga);
			}
		}

		// gotas que se separan del chorro y caen con gravedad
		const float ciclo = 0.6f;
		for (int i = 0; i < 14; i++) {
			const float fase = (s.t - SUELTA) / ciclo + azar(s.semilla + 101u * i);
			const float vuelta = floorf(fase);
			const float edad = (fase - vuelta) * ciclo;
			const float nace = s.t - edad;
			if (nace < SUELTA || nace > FIN_EFECTO) {
				continue;
			}
			const uint32_t n = s.semilla + 97u * i + 7919u * (uint32_t)(vuelta + 50.0f);
			const float x = 0.1f + 0.85f * azar(n);
			const glm::vec3 sale = desde + recorrido * x;
			const float costado = (azar(n + 1u) < 0.5f ? -1.0f : 1.0f) * (0.4f + 0.7f * azar(n + 2u));
			const glm::vec3 vel = dir * 1.5f + lado * costado + arriba * (0.4f + 0.8f * azar(n + 3u));
			glm::vec3 c = sale + vel * edad;
			c.y -= 0.5f * GRAVEDAD * edad * edad;
			if (c.y < 0.02f) {
				continue;
			}
			pincel.liquido(c, (0.03f + 0.03f * azar(n + 4u)) * s.ancho, agua, 0.8f * (1.0f - 0.5f * edad / ciclo));
		}

		if (s.t < IMPACTO) {
			return;
		}
		// golpe del agua en el pecho: borbotones que revientan contra el rival
		const float v = s.t - IMPACTO;
		if (apaga > 0.0f) {
			for (int i = 0; i < 4; i++) {
				const float a = 6.2832f * i / 4.0f + s.t * 7.0f;
				const glm::vec3 c = hasta - dir * 0.15f + (lado * cosf(a) + arriba * sinf(a)) * grueso * (0.6f + 0.3f * sinf(s.t * 13.0f + i));
				pincel.liquido(c, grueso * (0.6f + 0.4f * expf(-v * 4.0f)), i % 2 ? espuma : agua, 0.7f * apaga);
			}
		}
		// salpicadura: agua que sale en abanico del rival y cae
		const float ciclo2 = 0.75f;
		for (int i = 0; i < 20; i++) {
			const float fase = v / ciclo2 + azar(s.semilla + 211u * i);
			const float vuelta = floorf(fase);
			const float edad = (fase - vuelta) * ciclo2;
			const float nace = s.t - edad;
			if (nace < IMPACTO || nace > FIN_EFECTO) {
				continue;
			}
			const uint32_t n = s.semilla + 193u * i + 6007u * (uint32_t)(vuelta + 50.0f);
			const float a = (azar(n) - 0.5f) * 2.8f;                               // abanico de ~160 grados
			const glm::vec3 afuera = s.hacia * cosf(a) + lado * sinf(a);
			const glm::vec3 vel = afuera * (1.0f + 1.6f * azar(n + 1u)) + arriba * (1.6f + 1.8f * azar(n + 2u));
			glm::vec3 c = hasta + vel * edad;
			c.y -= 0.5f * GRAVEDAD * edad * edad;
			if (c.y < 0.02f) {
				continue;
			}
			const float k = 1.0f - 0.6f * edad / ciclo2;
			const float r = (0.04f + 0.05f * azar(n + 3u)) * s.ancho * (1.0f - 0.4f * edad / ciclo2);
			pincel.liquido(c, r, i % 4 == 0 ? espuma : agua, 0.85f * k);
		}
		// charco que se forma bajo el rival, se expande y se seca
		const float abre = suave(IMPACTO + 0.1f, FIN_EFECTO + 0.9f, s.t);
		const float seca = suave(IMPACTO + 0.1f, IMPACTO + 0.4f, s.t) * (1.0f - suave(FIN_EFECTO + 0.3f, FIN_EFECTO + 1.8f, s.t));
		if (seca > 0.0f) {
			pincel.charco(glm::vec3(hasta.x, 0.0f, hasta.z), s.ancho * (0.2f + 0.9f * abre), agua, 0.85f * seca);
		}
	}

	// solo cierra los ojos: un estremecimiento minimo y un retroceso corto con el impacto
	void defender(const Situacion& s, Pose& p) const override
	{
		const float cubre = suave(CUBRE, CUBRE + 0.2f, s.t);
		const float u = glm::max(0.0f, s.t - IMPACTO);
		p.ojos = cubre;
		p.escala *= 1.0f - 0.02f * cubre;
		p.desplazar -= s.hacia * 0.2f * suave(0.0f, 0.3f, u);
		p.girar += 0.06f * sinf(u * 22.0f) * expf(-u * 4.0f);
	}

	// se diluye: tiembla, se aplasta y se ensancha hundiendose en su propio charco y al final se deshace
	void derrota(const Situacion& s, Pose& p) const override
	{
		const float k = suave(MUERE, MUERE + 1.6f, s.t);
		const float tiembla = suave(MUERE, MUERE + 0.2f, s.t) * (1.0f - k);
		p.ojos = 1.0f;
		p.aplastar *= 1.0f - 0.95f * k;                                       // hasta 0.05
		p.escala *= 1.0f + 0.15f * k;
		p.desplazar.y -= 0.1f * k + s.vuelo * suave(MUERE, MUERE + 0.5f, s.t);   // si flota, baja al charco
		p.desplazar.y += 0.03f * sinf(s.t * 9.0f) * tiembla;
		p.girar += 0.04f * sinf(s.t * 7.0f) * tiembla;
		p.aleteo = 1.0f - k;
		p.desintegrar = suave(MUERE + 1.4f, MUERE + 2.4f, s.t);
	}

	// el agua se escurre por los costados, gotea, y deja un charco grande que se queda y se seca lento
	void efectoDerrota(const Situacion& s, glm::vec3 donde, Pincel& pincel) const override
	{
		const float u = s.t - MUERE;
		if (u < 0.0f || s.t > VUELVE) {
			return;
		}
		const glm::vec3 agua = colorAgua(s);
		const glm::vec3 espuma = colorEspuma();
		const glm::vec3 piso(donde.x, 0.0f, donde.z);
		const float k = suave(MUERE, MUERE + 1.6f, s.t);                       // cuanto se diluyo
		const float alto = s.alto * (1.0f - 0.95f * k);                        // altura del cuerpo que queda

		// charco grande que crece mientras se diluye, se queda y se seca lento
		const float abre = suave(MUERE, MUERE + 2.0f, s.t);
		const float seca = suave(MUERE, MUERE + 0.3f, s.t) * (1.0f - suave(DESAPARECE - 0.3f, VUELVE, s.t));
		if (seca > 0.0f) {
			pincel.charco(piso, s.ancho * (0.35f + 1.05f * abre), agua, 0.9f * seca);
		}

		// agua que se escurre por los costados del cuerpo (baja pegada a el y se abre al llegar al piso)
		const float escurre = suave(MUERE, MUERE + 0.25f, s.t) * (1.0f - suave(MUERE + 1.6f, MUERE + 2.4f, s.t));
		if (escurre > 0.0f) {
			for (int i = 0; i < 16; i++) {
				const float r0 = azar(s.semilla + 401u * i + 3u);
				const float q = fmodf(u * (0.9f + 0.5f * r0) + r0, 1.0f);       // 0 arriba .. 1 en el piso
				const float a = 6.2832f * (i / 16.0f) + 0.3f * r0;
				const glm::vec3 afuera(cosf(a), 0.0f, sinf(a));
				const float radio = s.ancho * (0.4f + 0.15f * k) + 0.35f * s.ancho * q * q;
				const glm::vec3 c = piso + afuera * radio + glm::vec3(0.0f, glm::max(0.03f, alto * 0.8f * (1.0f - q)), 0.0f);
				pincel.liquido(c, (0.06f + 0.05f * (1.0f - q)) * s.ancho, i % 5 == 0 ? espuma : agua, 0.8f * escurre);
			}
		}

		// gotas que saltan y caen al charco
		const float ciclo = 0.5f;
		for (int i = 0; i < 10; i++) {
			const float fase = u / ciclo + azar(s.semilla + 503u * i);
			const float vuelta = floorf(fase);
			const float edad = (fase - vuelta) * ciclo;
			if (u - edad > 2.2f) {
				continue;
			}
			const uint32_t n = s.semilla + 389u * i + 4111u * (uint32_t)(vuelta + 50.0f);
			const float a = 6.2832f * azar(n);
			const glm::vec3 afuera(cosf(a), 0.0f, sinf(a));
			const float sale = glm::max(0.05f, s.alto * (0.15f + 0.5f * azar(n + 1u)) * (1.0f - 0.9f * k));
			glm::vec3 c = piso + afuera * (0.45f * s.ancho + 0.7f * edad) + glm::vec3(0.0f, sale + 1.2f * edad, 0.0f);
			c.y -= 0.5f * GRAVEDAD * edad * edad;
			if (c.y < 0.02f) {
				continue;
			}
			pincel.liquido(c, 0.035f * s.ancho, agua, 0.8f * (1.0f - 0.5f * edad / ciclo));
		}
	}
};

} // namespace combate
