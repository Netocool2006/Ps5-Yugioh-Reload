// Regla 4 del Excel (monstruos de atributo agua): "tirar una rafaga de agua; efecto de agua regada; defensa: solo
// cerrar los ojos; derrota: diluirse en agua". Ataca A DISTANCIA: no se mueve hasta el rival, le tira un chorro.
#pragma once
#include "combate_api.h"

namespace combate {

struct ReglaAgua : Regla {
	const char* nombre() const override { return "agua"; }

	// gravedad de las gotas (m/s2)
	static constexpr float GRAVEDAD = 9.8f;

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
		p.brillo += 0.7f * carga + 0.3f * sostiene;
	}

	// la rafaga sale del frente, a media-alta altura
	glm::vec3 origen(const Situacion& s) const override
	{
		return s.base + s.hacia * (0.4f * s.ancho) + glm::vec3(0.0f, 0.65f * s.alto, 0.0f);
	}

	// rafaga de agua (chorro turbulento con gotas que caen) y agua regada en el rival (salpicadura y charco)
	void efecto(const Situacion& s, glm::vec3 desde, glm::vec3 hasta, Pincel& pincel) const override
	{
		const float inicio = SUELTA - 0.25f;
		if (s.t < inicio || s.t > FIN_EFECTO + 1.6f) {
			return;
		}
		const glm::vec3 arriba(0.0f, 1.0f, 0.0f);
		const glm::vec3 lado = glm::normalize(glm::cross(s.hacia, arriba));
		const glm::vec3 recorrido = hasta - desde;
		const float largo = glm::max(0.01f, glm::length(recorrido));
		const glm::vec3 dir = recorrido / largo;
		const float frente = suave(inicio, IMPACTO, s.t);                     // la punta del chorro viaja al rival
		const float apaga = 1.0f - suave(FIN_EFECTO - 0.3f, FIN_EFECTO, s.t);
		const float grueso = glm::max(0.22f, 0.12f * s.ancho);   // rafaga gruesa tambien en los monstruos chicos

		// el chorro: tramos que ondulan (halo grueso + nucleo fino) y bolas que viajan por adentro
		if (apaga > 0.0f) {
			const int TRAMOS = 12;
			glm::vec3 previo = desde;
			for (int i = 1; i <= TRAMOS; i++) {
				const float x = frente * i / (float)TRAMOS;
				const float onda = sinf(x * 14.0f - s.t * 22.0f + azar(s.semilla) * 6.0f);
				const float onda2 = cosf(x * 9.0f - s.t * 17.0f);
				const glm::vec3 punto = desde + recorrido * x + (lado * onda + arriba * onda2) * (0.035f * s.ancho * x);
				const float r = grueso * (0.7f + 0.6f * x) * (0.85f + 0.15f * onda);
				pincel.tramo(previo, punto, r, s.halo, 0.35f * apaga);
				pincel.tramo(previo, punto, 0.2f * r, s.nucleo, 0.8f * apaga);   // nucleo fino: que domine el color del agua
				previo = punto;
			}
			// bolas de agua que corren por el chorro (turbulencia)
			for (int i = 0; i < 14; i++) {
				const float x = fmodf(azar(s.semilla + 31u * i) + s.t * 2.2f, 1.0f) * frente;
				const glm::vec3 temblor = lado * (azar(s.semilla + 7u * i) - 0.5f) + arriba * (azar(s.semilla + 11u * i) - 0.5f);
				const glm::vec3 punto = desde + recorrido * x + temblor * (grueso * 1.4f) +
					lado * (0.035f * s.ancho * x * sinf(x * 14.0f - s.t * 22.0f));
				pincel.bola(punto, grueso * (0.3f + 0.3f * azar(s.semilla + 13u * i)), s.halo, 0.35f * apaga);   // del color del agua, no blancas
			}
			// espuma blanca en la boca
			for (int i = 0; i < 4; i++) {
				const float a = s.t * 15.0f + i * 1.57f;
				const glm::vec3 punto = desde + dir * (0.05f * i) + (lado * cosf(a) + arriba * sinf(a)) * (0.5f * grueso);
				pincel.bola(punto, grueso * (0.35f + 0.1f * sinf(a * 1.3f)), s.nucleo, 0.4f * apaga);
			}
		}

		// gotas que se separan del chorro y caen en parabola a los lados
		const float ciclo = 0.6f;
		for (int i = 0; i < 10; i++) {
			const float fase = (s.t - SUELTA) / ciclo + azar(s.semilla + 101u * i);
			const float vuelta = floorf(fase);
			const float edad = (fase - vuelta) * ciclo;
			const float nace = s.t - edad;
			if (nace < SUELTA || nace > FIN_EFECTO) {
				continue;
			}
			const uint32_t n = s.semilla + 97u * i + 7919u * (uint32_t)(vuelta + 50.0f);
			const float x = 0.15f + 0.8f * azar(n);
			const glm::vec3 sale = desde + recorrido * x;
			const float costado = (azar(n + 1u) < 0.5f ? -1.0f : 1.0f) * (0.5f + 0.8f * azar(n + 2u));
			const glm::vec3 vel = dir * 1.5f + lado * costado + arriba * (0.6f + 0.9f * azar(n + 3u));
			glm::vec3 punto = sale + vel * edad;
			punto.y -= 0.5f * GRAVEDAD * edad * edad;
			if (punto.y < 0.02f) {
				continue;
			}
			pincel.bola(punto, 0.035f * s.ancho, s.halo, 0.7f * (1.0f - edad / ciclo));
		}

		if (s.t < IMPACTO) {
			return;
		}
		// agua regada: salpicadura en abanico detras del rival mientras pega el chorro
		const float ciclo2 = 0.7f;
		for (int i = 0; i < 14; i++) {
			const float fase = (s.t - IMPACTO) / ciclo2 + azar(s.semilla + 211u * i);
			const float vuelta = floorf(fase);
			const float edad = (fase - vuelta) * ciclo2;
			const float nace = s.t - edad;
			if (nace < IMPACTO || nace > FIN_EFECTO) {
				continue;
			}
			const uint32_t n = s.semilla + 193u * i + 6007u * (uint32_t)(vuelta + 50.0f);
			const float a = (azar(n) - 0.5f) * 2.6f;                               // abanico de ~150 grados
			const glm::vec3 afuera = s.hacia * cosf(a) + lado * sinf(a);
			const glm::vec3 vel = afuera * (1.2f + 1.5f * azar(n + 1u)) + arriba * (1.8f + 1.6f * azar(n + 2u));
			glm::vec3 punto = hasta + vel * edad;
			punto.y -= 0.5f * GRAVEDAD * edad * edad;
			if (punto.y < 0.02f) {
				continue;
			}
			const float k = 1.0f - edad / ciclo2;
			pincel.bola(punto, (0.03f + 0.03f * azar(n + 3u)) * s.ancho, i % 3 == 0 ? s.nucleo : s.halo, 0.8f * k);
		}
		// golpe del agua en el pecho
		const float u = s.t - IMPACTO;
		if (apaga > 0.0f) {
			pincel.bola(hasta, (0.35f + 0.05f * sinf(s.t * 25.0f)) * s.ancho * 0.5f, s.halo, 0.3f * apaga);
			pincel.bola(hasta, 0.12f * s.ancho, s.nucleo, (0.9f + 0.6f * expf(-u * 6.0f)) * apaga);
		}
		// charco plano que se expande en el piso bajo el rival y se desvanece
		const float abre = suave(IMPACTO, FIN_EFECTO + 0.8f, s.t);
		const float seca = 1.0f - suave(FIN_EFECTO, FIN_EFECTO + 1.6f, s.t);
		if (seca > 0.0f) {
			charco(glm::vec3(hasta.x, 0.02f, hasta.z), s.ancho * (0.25f + 0.85f * abre), s, s.t, seca, pincel);
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

	// se diluye en agua: se aplasta, se ensancha, se hunde y se deshace
	void derrota(const Situacion& s, Pose& p) const override
	{
		const float k = suave(MUERE, MUERE + 1.5f, s.t);
		p.ojos = 1.0f;
		p.aplastar *= 1.0f - 0.95f * k;
		p.escala *= 1.0f + 0.15f * k;
		p.desplazar.y -= 0.12f * k;
		p.desplazar += glm::vec3(0.0f, 0.02f * sinf(s.t * 6.0f) * (1.0f - k), 0.0f) * suave(MUERE, MUERE + 0.2f, s.t);
		p.desintegrar = suave(MUERE + 0.8f, MUERE + 1.8f, s.t);
	}

	// agua que se riega: gotas que caen del cuerpo y un charco que se expande y se desvanece
	void efectoDerrota(const Situacion& s, glm::vec3 donde, Pincel& pincel) const override
	{
		const float u = s.t - MUERE;
		if (u < 0.0f || s.t > DESAPARECE + 1.0f) {
			return;
		}
		const glm::vec3 arriba(0.0f, 1.0f, 0.0f);
		// gotas que se escurren del cuerpo mientras se diluye
		const float ciclo = 0.5f;
		for (int i = 0; i < 14; i++) {
			const float fase = u / ciclo + azar(s.semilla + 401u * i);
			const float vuelta = floorf(fase);
			const float edad = (fase - vuelta) * ciclo;
			if (u - edad > 1.6f) {
				continue;
			}
			const uint32_t n = s.semilla + 389u * i + 4111u * (uint32_t)(vuelta + 50.0f);
			const float a = 6.2832f * azar(n);
			const glm::vec3 afuera(cosf(a), 0.0f, sinf(a));
			const float alto = s.alto * (0.2f + 0.6f * azar(n + 1u)) * (1.0f - suave(MUERE, MUERE + 1.5f, s.t - edad) * 0.9f);
			glm::vec3 punto = donde + afuera * (0.45f * s.ancho + 0.6f * edad) + arriba * (alto + 0.8f * edad);
			punto.y -= 0.5f * GRAVEDAD * edad * edad;
			if (punto.y < 0.02f) {
				continue;
			}
			pincel.bola(punto, 0.04f * s.ancho, i % 4 == 0 ? s.nucleo : s.halo, 0.7f * (1.0f - edad / ciclo));
		}
		// charco que crece y luego se seca
		const float abre = suave(MUERE, MUERE + 2.0f, s.t);
		const float seca = suave(MUERE, MUERE + 0.3f, s.t) * (1.0f - suave(DESAPARECE - 0.5f, DESAPARECE + 1.0f, s.t));
		if (seca > 0.0f) {
			charco(glm::vec3(donde.x, 0.02f, donde.z), s.ancho * (0.3f + 1.0f * abre), s, s.t, seca, pincel);
		}
	}

private:
	// anillo plano de agua en el piso (tramos formando un circulo) con un brillo tenue en el medio
	static void charco(glm::vec3 centro, float radio, const Situacion& s, float t, float fuerza, Pincel& pincel)
	{
		const int LADOS = 16;
		for (int i = 0; i < LADOS; i++) {
			const float a0 = 6.2832f * i / (float)LADOS;
			const float a1 = 6.2832f * (i + 1) / (float)LADOS;
			const float r0 = radio * (1.0f + 0.05f * sinf(a0 * 3.0f + t * 4.0f));
			const float r1 = radio * (1.0f + 0.05f * sinf(a1 * 3.0f + t * 4.0f));
			pincel.tramo(centro + glm::vec3(cosf(a0) * r0, 0.0f, sinf(a0) * r0),
				centro + glm::vec3(cosf(a1) * r1, 0.0f, sinf(a1) * r1), 0.03f, s.halo, 0.45f * fuerza);
		}
		pincel.bola(centro, 0.6f * radio, s.halo, 0.08f * fuerza);
		pincel.bola(centro, 0.25f * radio, s.nucleo, 0.12f * fuerza);
	}
};

} // namespace combate
