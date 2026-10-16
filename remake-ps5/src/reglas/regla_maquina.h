// Regla 5 del Excel: "las maquinas deben atacar con su arma a distancia; si no poseen arma, ataque directo con
// punos al adversario. Efecto: maquina sacando chispas. Defensa: cruzar los brazos. Derrota: explosion de fuego".
// Casi todas las maquinas del juego tienen arma integrada (tanques, canones, robots con laser): aqui va el ataque A
// DISTANCIA. La variante SIN arma (punos al adversario) queda pendiente: se decidira luego si es otra regla
// ("maquina_punos") o un indicador en la Situacion; por ahora toda maquina dispara.
#pragma once
#include "combate_api.h"

namespace combate {

struct ReglaMaquina : Regla {
	const char* nombre() const override { return "maquina"; }

	// disparos: el primero (grande) sale un poco antes de SUELTA para llegar justo en IMPACTO; luego 2 mas chicos
	static constexpr int DISPAROS = 3;
	static constexpr float VUELO = 0.1f;   // s que tarda el proyectil en llegar (rapido)
	static float salida(int i) { return i == 0 ? IMPACTO - VUELO : SUELTA + 0.4f * i; }   // 1.55, 2.05, 2.45
	static float fuerza(int i) { return i == 0 ? 1.0f : 0.45f; }

	// retroceso de un disparo: sube de golpe al salir y se recupera en ~0.45 s
	static float retroceso(float t, float t0)
	{
		return suave(t0, t0 + 0.05f, t) * (1.0f - suave(t0 + 0.08f, t0 + 0.55f, t));
	}

	// se planta y apunta (leve giro de ajuste), vibra el motor mientras carga, retrocede fuerte en el disparo
	// grande y con golpes cortos en los otros dos
	void atacar(const Situacion& s, Pose& p) const override
	{
		const float ajuste = suave(0.2f, 0.6f, s.t) * (1.0f - suave(0.9f, 1.3f, s.t));
		p.girar += 0.12f * sinf(6.0f * s.t) * ajuste;   // corrige la punteria de lado a lado

		// vibracion de motor desde 0.3 s, mas fuerte al acercarse el disparo, se apaga al terminar
		const float motor = suave(0.3f, SUELTA, s.t) * (1.0f - suave(FIN_EFECTO, FIN_EFECTO + 0.3f, s.t));
		p.desplazar.x += 0.012f * motor * sinf(s.t * 71.0f);
		p.desplazar.z += 0.012f * motor * sinf(s.t * 83.0f + 1.3f);
		p.desplazar.y += 0.008f * motor * sinf(s.t * 97.0f);
		p.brillo += 0.6f * suave(0.3f, SUELTA, s.t) * (1.0f - suave(SUELTA, SUELTA + 0.2f, s.t));

		float atras = 0.0f, cabeceo = 0.0f;
		for (int i = 0; i < DISPAROS; i++) {
			const float r = retroceso(s.t, salida(i));
			atras += (i == 0 ? 0.3f : 0.1f) * r;
			cabeceo += (i == 0 ? 0.22f : 0.07f) * r;
		}
		p.desplazar -= s.hacia * atras;
		p.inclinar -= cabeceo;
	}

	// el canon: adelante y a media altura
	glm::vec3 origen(const Situacion& s) const override
	{
		return s.base + s.hacia * (0.5f * s.ancho) + glm::vec3(0.0f, 0.55f * s.alto, 0.0f);
	}

	// chispas de metal en abanico (rebotan hacia atras y a los lados, caen por gravedad)
	static void chispas(glm::vec3 donde, glm::vec3 dir, float u, float vida, int n, uint32_t semilla,
		float grande, Pincel& pincel)
	{
		if (u < 0.0f || u > vida) {
			return;
		}
		const float k = 1.0f - u / vida;
		glm::vec3 lado = glm::cross(dir, glm::vec3(0.0f, 1.0f, 0.0f));
		lado = glm::length(lado) > 0.01f ? glm::normalize(lado) : glm::vec3(1.0f, 0.0f, 0.0f);
		const glm::vec3 g(0.0f, -9.8f, 0.0f);
		for (int i = 0; i < n; i++) {
			const uint32_t h = semilla * 97u + (uint32_t)i * 13u;
			const glm::vec3 sale = glm::normalize(-dir * (0.3f + 0.7f * azar(h)) + lado * (2.0f * azar(h + 1u) - 1.0f) * 1.2f +
				glm::vec3(0.0f, 0.2f + 0.9f * azar(h + 2u), 0.0f));
			const glm::vec3 v = sale * (3.0f + 4.0f * azar(h + 3u)) * grande;
			glm::vec3 a = donde + v * u + 0.5f * g * u * u;
			a.y = glm::max(a.y, 0.02f);
			const glm::vec3 vel = v + g * u;
			glm::vec3 b = a - vel * 0.025f;   // estela corta en la direccion del movimiento
			b.y = glm::max(b.y, 0.02f);
			const glm::vec3 color = glm::mix(glm::vec3(1.0f, 0.8f, 0.35f), glm::vec3(1.0f, 1.0f, 0.9f), azar(h + 4u));
			pincel.tramo(a, b, 0.012f * grande, color, 1.4f * k);
		}
	}

	// disparo de canon/laser: chispitas electricas mientras carga, fogonazo en la boca, proyectil rapido con estela
	// y en el impacto una explosion chica con chispas de metal
	void efecto(const Situacion& s, glm::vec3 desde, glm::vec3 hasta, Pincel& pincel) const override
	{
		// carga: chispitas electricas sobre el canon
		const float carga = suave(0.3f, 0.6f, s.t) * (1.0f - suave(salida(0) - 0.05f, salida(0), s.t));
		if (carga > 0.01f) {
			const uint32_t paso = (uint32_t)(s.t * 20.0f);   // cambia de forma 20 veces por segundo
			for (int i = 0; i < 2; i++) {
				const uint32_t h = s.semilla * 31u + paso * 7u + (uint32_t)i;
				const glm::vec3 d(azar(h) - 0.5f, azar(h + 1u) - 0.3f, azar(h + 2u) - 0.5f);
				pincel.relampago(desde, desde + d * (0.5f * carga), h, 0.08f, 0.6f, 0);
			}
			pincel.bola(desde, 0.1f + 0.08f * carga, s.halo, 0.4f * carga);
		}

		glm::vec3 dir = hasta - desde;
		const float largo = glm::length(dir);
		dir = largo > 0.001f ? dir / largo : s.hacia;

		for (int i = 0; i < DISPAROS; i++) {
			const float t0 = salida(i);
			const float f = fuerza(i);
			const float u = s.t - t0;
			if (u < 0.0f) {
				continue;
			}
			// fogonazo en la boca del canon
			if (u < 0.15f) {
				const float k = 1.0f - u / 0.15f;
				pincel.bola(desde + dir * 0.1f, (0.25f + 0.2f * f) * (0.6f + 0.4f * k), s.halo, 0.6f * k);
				pincel.bola(desde + dir * 0.05f, 0.12f * f * k + 0.03f, s.nucleo, 1.8f * k);
			}
			// proyectil con estela
			if (u < VUELO) {
				const float a = u / VUELO;
				const glm::vec3 c = desde + dir * (largo * a);
				const glm::vec3 cola = desde + dir * (largo * glm::max(0.0f, a - 0.35f));
				pincel.tramo(cola, c, 0.06f * f + 0.02f, s.halo, 0.5f);
				pincel.tramo(cola, c, 0.02f * f + 0.01f, s.nucleo, 1.3f);
				pincel.bola(c, 0.12f * f + 0.05f, s.halo, 0.6f);
				pincel.bola(c, 0.05f * f + 0.03f, s.nucleo, 1.6f);
			}
			// impacto: explosion chica + chispas de metal
			const float v = u - VUELO;
			const float dura = 0.35f + 0.15f * f;
			if (v >= 0.0f && v < dura) {
				const float k = 1.0f - v / dura;
				pincel.bola(hasta, (0.25f + 1.2f * v) * (0.5f + 0.5f * f) * s.ancho * 0.5f, s.halo, 0.45f * k);
				pincel.bola(hasta, (0.2f + 0.3f * v) * (0.5f + 0.5f * f), glm::vec3(1.0f, 0.7f, 0.3f), 0.6f * k);
				pincel.bola(hasta, 0.15f * f * k + 0.04f, s.nucleo, 1.8f * k);
			}
			chispas(hasta, dir, v, i == 0 ? 0.6f : 0.4f, i == 0 ? 28 : 14, s.semilla + (uint32_t)i, i == 0 ? 1.0f : 0.75f,
				pincel);
		}
	}

	// "cruzar los brazos" en una figura rigida: se agacha, gira de costado para cubrirse y retrocede con cada golpe
	void defender(const Situacion& s, Pose& p) const override
	{
		const float cubre = suave(CUBRE, CUBRE + 0.2f, s.t);
		p.aplastar *= 1.0f - 0.1f * cubre;
		p.girar += 0.35f * cubre;
		float atras = 0.0f, sacude = 0.0f;
		for (int i = 0; i < DISPAROS; i++) {
			const float u = s.t - (salida(i) + VUELO);
			if (u < 0.0f) {
				continue;
			}
			atras += (i == 0 ? 0.4f : 0.12f) * suave(0.0f, 0.2f, u);
			sacude += fuerza(i) * sinf(u * 22.0f) * expf(-u * 5.0f);
		}
		p.desplazar -= s.hacia * atras;
		p.inclinar -= 0.2f * suave(IMPACTO, IMPACTO + 0.2f, s.t) + 0.05f * sacude;
		p.girar += 0.12f * sacude;
	}

	// explosion de fuego: tiembla cada vez mas, revienta (salta un poco), se vuelca y se desintegra rapido
	void derrota(const Situacion& s, Pose& p) const override
	{
		const float u = s.t - MUERE;
		const float explota = MUERE + 0.3f;
		const float tiembla = suave(MUERE, explota, s.t) * (1.0f - suave(explota, explota + 0.4f, s.t));
		p.desplazar.x += 0.05f * tiembla * sinf(u * 63.0f);
		p.desplazar.z += 0.05f * tiembla * sinf(u * 77.0f + 0.7f);
		p.girar += 0.08f * tiembla * sinf(u * 51.0f);
		p.desplazar -= s.hacia * (0.5f + 0.4f * suave(explota, explota + 0.5f, s.t));
		const float salto = glm::clamp((s.t - explota) / 0.5f, 0.0f, 1.0f);
		p.desplazar.y += 0.35f * sinf(3.14159f * salto);
		p.inclinar -= 0.3f * suave(explota, explota + 0.4f, s.t);
		p.caer = 0.9f * suave(explota, explota + 0.6f, s.t);
		p.brillo += 1.5f * suave(explota - 0.1f, explota, s.t) * (1.0f - suave(explota, explota + 0.5f, s.t));
		p.desintegrar = suave(MUERE + 0.35f, MUERE + 1.3f, s.t);
	}

	// bola de fuego que crece y se apaga en ~1 s, anillo de fragmentos que salen y caen, y humo tenue al final
	void efectoDerrota(const Situacion& s, glm::vec3 donde, Pincel& pincel) const override
	{
		const float u = s.t - (MUERE + 0.3f);
		if (u < 0.0f || u > 2.2f) {
			return;
		}
		const glm::vec3 naranja(1.0f, 0.45f, 0.1f), amarillo(1.0f, 0.8f, 0.3f), blanco(1.0f, 0.97f, 0.9f);
		const float tam = glm::max(s.alto, s.ancho);

		// bola de fuego
		if (u < 1.0f) {
			const float crece = suave(0.0f, 0.35f, u);
			const float k = 1.0f - suave(0.3f, 1.0f, u);
			const glm::vec3 c = donde + glm::vec3(0.0f, 0.4f * u, 0.0f);   // sube un poco al arder
			pincel.bola(c, (0.25f + 0.45f * crece) * tam, naranja, 0.45f * k);
			pincel.bola(c, (0.15f + 0.3f * crece) * tam, amarillo, 0.8f * k);
			pincel.bola(c, (0.06f + 0.1f * crece) * tam * (0.4f + 0.6f * k), blanco, 1.8f * k);
			// lenguas de fuego alrededor
			for (int i = 0; i < 6; i++) {
				const uint32_t h = s.semilla * 53u + (uint32_t)i * 5u;
				const float a = 6.2832f * i / 6.0f + azar(h);
				const glm::vec3 d(cosf(a), 0.4f + 0.6f * azar(h + 1u), sinf(a));
				pincel.bola(c + d * (0.3f * tam * crece), (0.1f + 0.12f * azar(h + 2u)) * tam, naranja, 0.5f * k);
			}
		}

		// fragmentos y chispas en abanico, caen por gravedad
		if (u < 1.4f) {
			const float k = 1.0f - u / 1.4f;
			const glm::vec3 g(0.0f, -9.8f, 0.0f);
			for (int i = 0; i < 32; i++) {
				const uint32_t h = s.semilla * 71u + (uint32_t)i * 11u;
				const float a = 6.2832f * i / 32.0f + 0.3f * azar(h);
				const glm::vec3 sale = glm::normalize(glm::vec3(cosf(a), 0.3f + 1.0f * azar(h + 1u), sinf(a)));
				const glm::vec3 v = sale * (3.0f + 4.0f * azar(h + 2u));
				glm::vec3 p = donde + v * u + 0.5f * g * u * u;
				p.y = glm::max(p.y, 0.03f);
				glm::vec3 q = p - (v + g * u) * 0.03f;
				q.y = glm::max(q.y, 0.03f);
				const glm::vec3 color = glm::mix(naranja, blanco, azar(h + 3u));
				pincel.tramo(p, q, 0.02f, color, 1.3f * k);
			}
		}

		// humo tenue al final
		if (u > 0.5f) {
			const float k = suave(0.5f, 0.9f, u) * (1.0f - suave(1.5f, 2.2f, u));
			for (int i = 0; i < 6; i++) {
				const uint32_t h = s.semilla * 19u + (uint32_t)i * 3u;
				const glm::vec3 d(azar(h) - 0.5f, 0.0f, azar(h + 1u) - 0.5f);
				const glm::vec3 c = donde + d * tam * 0.6f + glm::vec3(0.0f, 0.3f + 0.8f * (u - 0.5f) * (0.6f + 0.4f * azar(h + 2u)), 0.0f);
				pincel.bola(c, (0.12f + 0.15f * (u - 0.5f)) * tam * 0.5f, glm::vec3(0.35f, 0.33f, 0.3f), 0.03f * k);   // tenue: suma luz
			}
		}
	}
};

} // namespace combate
