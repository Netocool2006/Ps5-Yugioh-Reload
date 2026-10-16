// Regla 5 del Excel: "las maquinas deben atacar con su arma a distancia; si no poseen arma, ataque directo con
// punos al adversario. Efecto: maquina sacando chispas. Defensa: cruzar los brazos. Derrota: explosion de fuego".
// Casi todas las maquinas del juego tienen arma integrada (tanques, canones, robots con laser): aqui va el ataque A
// DISTANCIA. La variante SIN arma (punos al adversario) queda pendiente: se decidira luego si es otra regla
// ("maquina_punos") o un indicador en la Situacion; por ahora toda maquina dispara.
//
// Como los magos (5 rayos), la maquina usa 1 de 5 armas al azar en cada ataque:
//  0 CANON:    proyectil pesado con fogonazo y humo en la boca; explosion de fuego en el rival
//  1 RAFAGA:   ametralladora / laser pulsado desde dos bocas alternadas: muchos disparos cortos con chispas
//  2 LASER:    rayo continuo que barre el cuerpo del rival, lo quema y saca chispas sin parar
//  3 MISILES:  4 misiles que salen en arco con estela de humo y explotan con fuego uno tras otro
//  4 RIEL:     carga electrica larga, disparo de railgun instantaneo con relampagos y ondas de choque
// Rayos con el color de quien ataca (s.halo / s.nucleo); las explosiones con llama() (fuego de verdad).
// YUGI_ARMA=0..4 fija el arma (pruebas en el PC).
#pragma once
#include <cstdlib>
#include "combate_api.h"

namespace combate {

struct ReglaMaquina : Regla {
	const char* nombre() const override { return "maquina"; }

	enum Arma { CANON, RAFAGA, LASER, MISILES, RIEL, NUM_ARMAS };

	// el motor arma la semilla como numAtaque * 977 + indice del monstruo: dividiendo por 977 sale el mismo numero
	// para el atacante y el defensor, asi el defensor sabe que arma lo golpea (rafaga = muchos golpecitos, etc.)
	static int arma(const Situacion& s)
	{
		if (const char* f = getenv("YUGI_ARMA")) {
			return abs(atoi(f)) % NUM_ARMAS;
		}
		const uint32_t ataque = s.semilla / 977u;
		return (int)(azar(ataque * 7919u + 31u) * (float)NUM_ARMAS) % NUM_ARMAS;
	}

	// ---------------------------------------------------------------- disparos de cada arma
	static constexpr float VUELO_MISIL = 0.6f;   // s que tarda un misil en llegar
	static constexpr float DISPARA_RIEL = IMPACTO - 0.03f;

	struct Disparo {
		float sale, llega, fuerza;
	};
	static int numDisparos(int a)
	{
		switch (a) {
		case RAFAGA: return 10;
		case LASER: return 5;
		case MISILES: return 4;
		default: return 1;
		}
	}
	// cuando sale y cuando llega cada disparo (el primero llega siempre en IMPACTO)
	static Disparo disparo(int a, int i)
	{
		switch (a) {
		case CANON: return { IMPACTO - 0.15f, IMPACTO, 1.0f };
		case RAFAGA: {
			const float t0 = IMPACTO - 0.08f + 0.09f * (float)i;   // 10 tiros en ~0.9 s
			return { t0, t0 + 0.08f, 0.22f };
		}
		case LASER: return { IMPACTO - 0.15f + 0.2f * (float)i, IMPACTO + 0.2f * (float)i, i == 0 ? 0.6f : 0.25f };   // quemaduras
		case MISILES: {
			const float t0 = IMPACTO - VUELO_MISIL + 0.15f * (float)i;
			return { t0, t0 + VUELO_MISIL, 0.55f };
		}
		default: return { DISPARA_RIEL, IMPACTO, 1.3f };
		}
	}

	// retroceso de un disparo: sube de golpe en "subida" s y se recupera hasta "baja" s despues de salir
	static float retroceso(float t, float t0, float subida, float baja)
	{
		return suave(t0, t0 + subida, t) * (1.0f - suave(t0 + subida + 0.02f, t0 + baja, t));
	}

	// ---------------------------------------------------------------- cuerpo del atacante (rigido: solo se mueve)
	void atacar(const Situacion& s, Pose& p) const override
	{
		const int a = arma(s);
		const float t = s.t;

		// vibracion de motor desde 0.3 s, mas fuerte al acercarse el disparo, se apaga al terminar
		const float motor = suave(0.3f, SUELTA, t) * (1.0f - suave(FIN_EFECTO, FIN_EFECTO + 0.3f, t));
		const float vib = a == RIEL ? 0.022f : 0.012f;
		p.desplazar.x += vib * motor * sinf(t * 71.0f);
		p.desplazar.z += vib * motor * sinf(t * 83.0f + 1.3f);
		p.desplazar.y += 0.7f * vib * motor * sinf(t * 97.0f);
		p.brillo += (a == RIEL ? 1.3f : 0.6f) * suave(0.3f, SUELTA, t) * (1.0f - suave(SUELTA, SUELTA + 0.2f, t));

		float atras = 0.0f, cabeceo = 0.0f;
		switch (a) {
		case CANON: {
			// un solo golpe muy fuerte: se va atras, cabecea y se asienta sobre la mesa
			const float r = retroceso(t, disparo(a, 0).sale, 0.04f, 0.75f);
			atras = 0.4f * r;
			cabeceo = 0.28f * r;
			p.aplastar *= 1.0f - 0.04f * r;
			break;
		}
		case RAFAGA: {
			// empuje sostenido mientras dispara y un golpecito por cada tiro
			const float sostiene = suave(IMPACTO - 0.1f, IMPACTO, t) * (1.0f - suave(2.45f, 2.75f, t));
			atras = 0.07f * sostiene;
			cabeceo = 0.035f * sostiene;
			for (int i = 0; i < numDisparos(a); i++) {
				const float r = retroceso(t, disparo(a, i).sale, 0.02f, 0.09f);
				atras += 0.035f * r;
				cabeceo += 0.025f * r;
			}
			break;
		}
		case LASER: {
			// empuje continuo y temblor fino mientras el rayo esta encendido
			const float haz = suave(IMPACTO - 0.15f, IMPACTO, t) * (1.0f - suave(2.45f, 2.65f, t));
			atras = 0.13f * haz;
			cabeceo = 0.06f * haz;
			p.desplazar.x += 0.01f * haz * sinf(t * 121.0f);
			p.desplazar.z += 0.01f * haz * sinf(t * 137.0f + 0.4f);
			break;
		}
		case MISILES: {
			// levanta el lanzador (se echa atras) antes de soltar y patea con cada misil
			const float apunta = suave(0.5f, 1.0f, t) * (1.0f - suave(2.1f, 2.6f, t));
			cabeceo = 0.08f * apunta;
			for (int i = 0; i < numDisparos(a); i++) {
				const float r = retroceso(t, disparo(a, i).sale, 0.03f, 0.35f);
				atras += 0.07f * r;
				cabeceo += 0.06f * r;
			}
			break;
		}
		default: {
			// railgun: se agazapa mientras carga y el disparo lo arroja hacia atras con un saltito
			const float carga = suave(0.4f, 1.55f, t) * (1.0f - suave(DISPARA_RIEL, DISPARA_RIEL + 0.06f, t));
			p.aplastar *= 1.0f - 0.05f * carga;
			p.desplazar.y -= 0.04f * carga;
			const float r = retroceso(t, DISPARA_RIEL, 0.03f, 0.95f);
			atras = 0.6f * r;
			cabeceo = 0.36f * r;
			p.desplazar.y += 0.1f * r * (1.0f - suave(DISPARA_RIEL + 0.05f, DISPARA_RIEL + 0.4f, t));
			break;
		}
		}
		p.desplazar -= s.hacia * atras;
		p.inclinar -= cabeceo;
	}

	// el arma: adelante y a media altura
	glm::vec3 origen(const Situacion& s) const override
	{
		return s.base + s.hacia * (0.5f * s.ancho) + glm::vec3(0.0f, 0.55f * s.alto, 0.0f);
	}

	// ---------------------------------------------------------------- piezas de dibujo
	// lado horizontal de una direccion
	static glm::vec3 ladoDe(glm::vec3 dir)
	{
		const glm::vec3 l = glm::cross(dir, glm::vec3(0.0f, 1.0f, 0.0f));
		return glm::length(l) > 0.01f ? glm::normalize(l) : glm::vec3(1.0f, 0.0f, 0.0f);
	}

	// chispas de metal en abanico (rebotan hacia atras y a los lados, caen por gravedad)
	static void chispas(glm::vec3 donde, glm::vec3 dir, float u, float vida, int n, uint32_t semilla, float grande,
		Pincel& pincel)
	{
		if (u < 0.0f || u > vida) {
			return;
		}
		const float k = 1.0f - u / vida;
		const glm::vec3 lado = ladoDe(dir);
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

	// explosion de fuego: fogonazo blanco breve, resplandor naranja y "llamas" lenguas que crecen hacia afuera y arriba
	static void explosion(glm::vec3 c, float tam, float u, float dura, int llamas, uint32_t semilla, Pincel& pincel)
	{
		if (u < 0.0f || u > dura) {
			return;
		}
		const float crece = suave(0.0f, 0.3f * dura, u);
		const float k = 1.0f - suave(0.35f * dura, dura, u);
		if (u < 0.12f) {
			const float f = 1.0f - u / 0.12f;
			pincel.bola(c, tam * (0.35f + 0.3f * f), glm::vec3(1.0f, 0.95f, 0.8f), 2.2f * f);
		}
		pincel.bola(c, tam * (0.3f + 0.4f * crece), glm::vec3(1.0f, 0.45f, 0.1f), 0.35f * k);
		for (int i = 0; i < llamas; i++) {
			const uint32_t h = semilla * 53u + (uint32_t)i * 7u;
			const float ang = 6.2832f * (float)i / (float)llamas + azar(h);
			const glm::vec3 d = glm::normalize(glm::vec3(cosf(ang), 0.5f + 1.0f * azar(h + 1u), sinf(ang)));
			const glm::vec3 base = c + d * (0.08f * tam);
			const glm::vec3 punta = c + d * ((0.25f + 0.75f * crece) * tam) + glm::vec3(0.0f, 0.5f * u * tam, 0.0f);
			pincel.llama(base, punta, tam * (0.25f + 0.3f * crece), k, h);
		}
	}

	// anillo de bolitas alrededor de un eje (onda de choque)
	static void anillo(glm::vec3 c, glm::vec3 eje, float radio, int n, glm::vec3 color, float tam, float brillo, Pincel& pincel)
	{
		const glm::vec3 l = ladoDe(eje);
		const glm::vec3 arriba = glm::cross(l, eje);
		for (int i = 0; i < n; i++) {
			const float ang = 6.2832f * (float)i / (float)n;
			pincel.bola(c + (l * cosf(ang) + arriba * sinf(ang)) * radio, tam, color, brillo);
		}
	}

	// chispitas electricas sobre el arma mientras carga ("maquina sacando chispas")
	static void cargaChispas(const Situacion& s, glm::vec3 desde, float hasta, Pincel& pincel)
	{
		const float carga = suave(0.3f, 0.6f, s.t) * (1.0f - suave(hasta - 0.05f, hasta, s.t));
		if (carga < 0.01f) {
			return;
		}
		const uint32_t paso = (uint32_t)(s.t * 20.0f);   // cambia de forma 20 veces por segundo
		for (int i = 0; i < 2; i++) {
			const uint32_t h = s.semilla * 31u + paso * 7u + (uint32_t)i;
			const glm::vec3 d(azar(h) - 0.5f, azar(h + 1u) - 0.3f, azar(h + 2u) - 0.5f);
			pincel.relampago(desde, desde + d * (0.5f * carga), h, 0.08f, 0.6f, 0);
		}
		pincel.bola(desde, 0.1f + 0.08f * carga, s.halo, 0.4f * carga);
	}

	// ---------------------------------------------------------------- el ataque
	void efecto(const Situacion& s, glm::vec3 desde, glm::vec3 hasta, Pincel& pincel) const override
	{
		glm::vec3 dir = hasta - desde;
		const float largo = glm::length(dir);
		dir = largo > 0.001f ? dir / largo : s.hacia;
		switch (arma(s)) {
		case CANON: efectoCanon(s, desde, hasta, dir, largo, pincel); break;
		case RAFAGA: efectoRafaga(s, desde, hasta, dir, largo, pincel); break;
		case LASER: efectoLaser(s, desde, hasta, dir, pincel); break;
		case MISILES: efectoMisiles(s, desde, hasta, dir, largo, pincel); break;
		default: efectoRiel(s, desde, hasta, dir, largo, pincel); break;
		}
	}

	// 0 CANON: fogonazo con lengua de fuego y humo en la boca, bala pesada en arco bajo, explosion de fuego + chispas
	static void efectoCanon(const Situacion& s, glm::vec3 desde, glm::vec3 hasta, glm::vec3 dir, float largo, Pincel& pincel)
	{
		const Disparo d = disparo(CANON, 0);
		cargaChispas(s, desde, d.sale, pincel);
		const float u = s.t - d.sale;
		if (u < 0.0f) {
			return;
		}
		const float vuelo = d.llega - d.sale;
		if (u < 0.18f) {   // fogonazo y lengua de fuego en la boca
			const float k = 1.0f - u / 0.18f;
			pincel.bola(desde + dir * 0.15f, 0.5f * (0.6f + 0.4f * k), s.halo, 0.7f * k);
			pincel.bola(desde + dir * 0.08f, 0.2f * k + 0.04f, s.nucleo, 2.0f * k);
			pincel.llama(desde, desde + dir * (0.4f + 0.6f * suave(0.0f, 0.06f, u)), 0.35f, k, s.semilla * 3u + 1u);
		}
		if (u < 1.4f) {   // humo del disparo que sube desde la boca
			const float k = suave(0.0f, 0.1f, u) * (1.0f - suave(0.5f, 1.4f, u));
			for (int i = 0; i < 2; i++) {
				const glm::vec3 c = desde + dir * (0.2f + 0.25f * (float)i) + glm::vec3(0.0f, 0.35f * u * (1.0f + 0.5f * (float)i), 0.0f);
				pincel.humo(c, 0.15f + 0.3f * u, glm::vec3(0.4f, 0.38f, 0.36f), 0.55f * k);
			}
		}
		if (u < vuelo) {   // bala pesada con estela
			const float a = u / vuelo;
			const glm::vec3 arco(0.0f, 0.12f * largo * a * (1.0f - a), 0.0f);
			const glm::vec3 c = desde + dir * (largo * a) + arco;
			const glm::vec3 cola = desde + dir * (largo * glm::max(0.0f, a - 0.4f));
			pincel.tramo(cola, c, 0.09f, s.halo, 0.5f);
			pincel.tramo(cola, c, 0.03f, s.nucleo, 1.3f);
			pincel.bola(c, 0.17f, s.halo, 0.7f);
			pincel.bola(c, 0.08f, s.nucleo, 1.8f);
		}
		const float v = s.t - d.llega;   // impacto
		const float tam = 0.9f * glm::max(s.ancho, 1.0f);
		explosion(hasta, tam, v, 0.9f, 5, s.semilla, pincel);
		if (v >= 0.0f && v < 0.3f) {
			pincel.bola(hasta, 0.6f * tam * (0.4f + 2.0f * v), s.halo, 0.5f * (1.0f - v / 0.3f));
		}
		chispas(hasta, dir, v, 0.75f, 30, s.semilla, 1.1f, pincel);
		if (v > 0.25f && v < 1.25f) {   // humo oscuro de la explosion
			const float k = suave(0.25f, 0.45f, v) * (1.0f - suave(0.8f, 1.25f, v));
			for (int i = 0; i < 3; i++) {
				const uint32_t h = s.semilla * 17u + (uint32_t)i;
				const glm::vec3 c = hasta + glm::vec3(azar(h) - 0.5f, 0.3f + 0.7f * v, azar(h + 1u) - 0.5f) * tam * 0.6f;
				pincel.humo(c, (0.25f + 0.35f * v) * tam, glm::vec3(0.12f, 0.11f, 0.1f), 0.6f * k);
			}
		}
	}

	// 1 RAFAGA: dos bocas alternadas, trazadoras cortas, cada tiro da en un punto distinto del cuerpo con chispas
	static void efectoRafaga(const Situacion& s, glm::vec3 desde, glm::vec3 hasta, glm::vec3 dir, float largo, Pincel& pincel)
	{
		cargaChispas(s, desde, disparo(RAFAGA, 0).sale, pincel);
		const glm::vec3 lado = ladoDe(dir);
		for (int i = 0; i < numDisparos(RAFAGA); i++) {
			const Disparo d = disparo(RAFAGA, i);
			const float u = s.t - d.sale;
			if (u < 0.0f) {
				break;
			}
			const uint32_t h = s.semilla * 41u + (uint32_t)i * 5u;
			const glm::vec3 boca = desde + lado * (i % 2 == 0 ? 0.12f : -0.12f) * s.ancho;
			const glm::vec3 blanco = hasta + lado * ((azar(h) - 0.5f) * 0.6f * s.ancho) +
				glm::vec3(0.0f, (azar(h + 1u) - 0.5f) * 0.35f * s.alto, 0.0f);
			if (u < 0.05f) {   // fogonazo de la boca
				const float k = 1.0f - u / 0.05f;
				pincel.bola(boca + dir * 0.08f, 0.22f, s.halo, 0.7f * k);
				pincel.bola(boca + dir * 0.05f, 0.07f, s.nucleo, 2.0f * k);
			}
			const float vuelo = d.llega - d.sale;
			if (u < vuelo) {   // trazadora corta
				const glm::vec3 ruta = blanco - boca;
				const float a = u / vuelo;
				const glm::vec3 c = boca + ruta * a;
				const glm::vec3 cola = boca + ruta * glm::max(0.0f, a - 0.25f * glm::min(1.0f, 4.0f / glm::max(largo, 0.1f)));
				pincel.tramo(cola, c, 0.05f, s.halo, 0.6f);
				pincel.tramo(cola, c, 0.016f, s.nucleo, 1.6f);
			}
			const float v = s.t - d.llega;   // impacto: destello chico y chispas
			if (v >= 0.0f && v < 0.1f) {
				const float k = 1.0f - v / 0.1f;
				pincel.bola(blanco, 0.2f, s.halo, 0.6f * k);
				pincel.bola(blanco, 0.06f, glm::vec3(1.0f, 0.95f, 0.8f), 1.8f * k);
			}
			chispas(blanco, dir, v, 0.35f, 7, h, 0.75f, pincel);
		}
	}

	// punto que barre el laser sobre el cuerpo del rival en el instante t
	static glm::vec3 barrido(const Situacion& s, glm::vec3 hasta, glm::vec3 lado, float t)
	{
		const float w = glm::max(0.0f, t - IMPACTO);
		return hasta + lado * (0.45f * s.ancho * sinf(w * 4.5f)) + glm::vec3(0.0f, 0.18f * s.alto * sinf(w * 2.3f + 0.5f) - 0.05f * s.alto, 0.0f);
	}

	// 2 LASER: haz continuo que crece hasta el rival, barre de lado a lado, lo quema (llama) y saca chispas sin parar
	static void efectoLaser(const Situacion& s, glm::vec3 desde, glm::vec3 hasta, glm::vec3 dir, Pincel& pincel)
	{
		const float enciende = IMPACTO - 0.15f, apaga = 2.5f;
		cargaChispas(s, desde, enciende, pincel);
		const glm::vec3 lado = ladoDe(dir);
		const float on = suave(enciende, enciende + 0.05f, s.t) * (1.0f - suave(apaga - 0.1f, apaga, s.t));
		if (on > 0.001f) {
			const glm::vec3 e = barrido(s, hasta, lado, s.t);
			const glm::vec3 punta = glm::mix(desde, e, suave(enciende, IMPACTO, s.t));
			const float tiembla = 1.0f + 0.15f * sinf(s.t * 63.0f);
			pincel.tramo(desde, punta, 0.14f * on * tiembla, s.halo, 0.45f);
			pincel.tramo(desde, punta, 0.055f * on, s.nucleo, 1.5f);
			pincel.tramo(desde, punta, 0.018f * on, glm::vec3(1.0f), 2.0f);
			pincel.bola(desde, 0.25f * on * tiembla, s.halo, 0.7f);
			pincel.bola(desde, 0.09f * on, s.nucleo, 2.0f);
			// pulsos de energia que corren por el haz
			for (int i = 0; i < 4; i++) {
				const float f = glm::fract(s.t * 3.0f + 0.25f * (float)i);
				pincel.bola(glm::mix(desde, punta, f), 0.1f * on, s.nucleo, 0.9f);
			}
			if (s.t >= IMPACTO) {   // donde quema: resplandor y fuego
				pincel.bola(e, 0.35f * on * tiembla, s.halo, 0.7f);
				pincel.bola(e, 0.12f * on, glm::vec3(1.0f, 0.95f, 0.85f), 2.0f);
				pincel.llama(e - dir * 0.05f, e - dir * 0.25f + glm::vec3(0.0f, 0.45f, 0.0f), 0.3f * s.ancho * on, 0.85f * on,
					s.semilla * 7u + (uint32_t)(s.t * 8.0f));
			}
		}
		// chispas: una rafaguita cada 0.04 s desde donde estaba el haz en ese momento
		for (int b = 0; b < 22; b++) {
			const float tb = IMPACTO + 0.04f * (float)b;
			if (tb > apaga - 0.05f) {
				break;
			}
			chispas(barrido(s, hasta, lado, tb), dir, s.t - tb, 0.3f, 4, s.semilla * 13u + (uint32_t)b, 0.7f, pincel);
		}
		// humo de lo quemado al apagarse
		const float hu = s.t - IMPACTO;
		if (hu > 0.2f && hu < 1.35f) {
			const float k = suave(0.2f, 0.4f, hu) * (1.0f - suave(0.9f, 1.35f, hu));
			for (int i = 0; i < 2; i++) {
				const glm::vec3 c = barrido(s, hasta, lado, IMPACTO + 0.3f + 0.4f * (float)i) + glm::vec3(0.0f, 0.4f * hu, 0.0f);
				pincel.humo(c, 0.2f + 0.25f * hu, glm::vec3(0.15f, 0.14f, 0.13f), 0.45f * k);
			}
		}
	}

	// curva de un misil (bezier: sale del lanzador, sube en arco abierto hacia su lado y cae sobre el rival)
	static glm::vec3 rutaMisil(const Situacion& s, glm::vec3 desde, glm::vec3 hasta, glm::vec3 lado, float largo, int i, float a)
	{
		const float off = (float)i - 1.5f;
		const float q = a * (0.55f + 0.45f * a);   // acelera
		const glm::vec3 p0 = desde + lado * (0.08f * off);
		const glm::vec3 p2 = hasta + lado * (0.12f * off * s.ancho) + glm::vec3(0.0f, 0.15f * (azar(s.semilla + (uint32_t)i) - 0.5f) * s.alto, 0.0f);
		const glm::vec3 c = 0.5f * (p0 + p2) + lado * (0.14f * off * largo) +
			glm::vec3(0.0f, (0.3f + 0.15f * azar(s.semilla * 3u + (uint32_t)i)) * largo, 0.0f);
		return (1.0f - q) * (1.0f - q) * p0 + 2.0f * (1.0f - q) * q * c + q * q * p2;
	}

	// 3 MISILES: 4 misiles en arco con estela de humo y fuego de escape; cada uno revienta con llama y chispas
	static void efectoMisiles(const Situacion& s, glm::vec3 desde, glm::vec3 hasta, glm::vec3 dir, float largo, Pincel& pincel)
	{
		cargaChispas(s, desde, disparo(MISILES, 0).sale, pincel);
		const glm::vec3 lado = ladoDe(dir);
		constexpr int BOCANADAS = 8;
		for (int i = 0; i < numDisparos(MISILES); i++) {
			const Disparo d = disparo(MISILES, i);
			const float u = s.t - d.sale;
			if (u < 0.0f) {
				break;
			}
			const uint32_t h = s.semilla * 59u + (uint32_t)i * 9u;
			if (u < 0.1f) {   // destello al salir
				const float k = 1.0f - u / 0.1f;
				pincel.bola(rutaMisil(s, desde, hasta, lado, largo, i, 0.0f), 0.3f, glm::vec3(1.0f, 0.6f, 0.2f), 1.0f * k);
			}
			// estela de humo: bocanadas que quedan donde paso el misil, crecen y se disipan
			for (int j = 0; j < BOCANADAS; j++) {
				const float aj = ((float)j + 0.5f) / (float)BOCANADAS;
				const float edad = u - aj * VUELO_MISIL;
				if (edad < 0.0f || edad > 0.9f) {
					continue;
				}
				const glm::vec3 c = rutaMisil(s, desde, hasta, lado, largo, i, aj) + glm::vec3(0.0f, 0.25f * edad, 0.0f);
				pincel.humo(c, 0.08f + 0.28f * edad, glm::vec3(0.6f, 0.58f, 0.55f), 0.5f * (1.0f - edad / 0.9f));
			}
			if (u < VUELO_MISIL) {   // el misil: cuerpo, punta brillante y fuego de escape
				const float a = u / VUELO_MISIL;
				const glm::vec3 p = rutaMisil(s, desde, hasta, lado, largo, i, a);
				glm::vec3 tg = rutaMisil(s, desde, hasta, lado, largo, i, glm::min(1.0f, a + 0.03f)) - p;
				tg = glm::length(tg) > 0.0001f ? glm::normalize(tg) : dir;
				pincel.tramo(p - tg * 0.28f, p, 0.045f, s.halo, 0.6f);
				pincel.bola(p, 0.07f, s.nucleo, 1.6f);
				pincel.llama(p - tg * 0.28f, p - tg * 0.7f, 0.14f, 0.9f, h);
			}
			const float v = s.t - d.llega;   // impacto
			explosion(rutaMisil(s, desde, hasta, lado, largo, i, 1.0f), 0.55f * glm::max(s.ancho, 1.0f), v, 0.7f, 3, h, pincel);
			chispas(rutaMisil(s, desde, hasta, lado, largo, i, 1.0f), dir, v, 0.6f, 12, h, 0.9f, pincel);
		}
	}

	// 4 RIEL: carga electrica larga (relampagos y anillos que corren por el canon), disparo instantaneo con
	// relampagos alrededor del haz, ondas de choque en la boca y en el rival, chispas a montones
	static void efectoRiel(const Situacion& s, glm::vec3 desde, glm::vec3 hasta, glm::vec3 dir, float largo, Pincel& pincel)
	{
		(void)largo;
		const float carga = suave(0.3f, 1.4f, s.t) * (1.0f - suave(DISPARA_RIEL - 0.02f, DISPARA_RIEL + 0.02f, s.t));
		if (carga > 0.01f) {
			const uint32_t paso = (uint32_t)(s.t * 24.0f);
			for (int i = 0; i < 3; i++) {
				const uint32_t h = s.semilla * 37u + paso * 11u + (uint32_t)i;
				const glm::vec3 d(azar(h) - 0.5f, azar(h + 1u) - 0.4f, azar(h + 2u) - 0.5f);
				pincel.relampago(desde - dir * (0.3f * azar(h + 3u)), desde + d * (0.8f * carga), h, 0.1f, 0.8f, 1);
			}
			// anillos que corren por el canon hacia la boca
			for (int j = 0; j < 4; j++) {
				const float f = glm::fract(s.t * (1.0f + 3.0f * carga) + 0.25f * (float)j);
				anillo(desde - dir * (0.5f * (1.0f - f)), dir, 0.12f + 0.05f * carga, 4, s.halo, 0.05f, 0.9f * carga * f, pincel);
			}
			pincel.bola(desde, 0.15f + 0.3f * carga, s.halo, 0.6f * carga);
			pincel.bola(desde, 0.05f + 0.08f * carga, s.nucleo, 1.8f * carga);
		}
		const float u = s.t - DISPARA_RIEL;
		if (u < 0.0f) {
			return;
		}
		if (u < 0.45f) {   // el haz: grueso al salir, se adelgaza y se apaga
			const float k = 1.0f - u / 0.45f;
			pincel.tramo(desde, hasta, 0.3f * k + 0.04f, s.halo, 0.6f * k);
			pincel.tramo(desde, hasta, 0.09f * k + 0.015f, s.nucleo, 1.8f * k);
			pincel.tramo(desde, hasta, 0.025f * k + 0.005f, glm::vec3(1.0f), 2.5f * k);
			if (u < 0.3f) {
				const uint32_t paso = (uint32_t)(u * 30.0f);
				for (int i = 0; i < 2; i++) {
					pincel.relampago(desde, hasta, s.semilla * 5u + paso * 3u + (uint32_t)i, 0.05f, 1.4f * k + 0.3f, 2);
				}
			}
		}
		if (u < 0.4f) {   // ondas de choque en la boca y en el rival
			const float k = 1.0f - u / 0.4f;
			anillo(desde + dir * (0.2f + 0.6f * u), dir, 0.15f + 3.0f * u, 10, s.halo, 0.08f, 0.8f * k, pincel);
			anillo(hasta - dir * 0.1f, dir, 0.25f + 4.0f * u, 10, s.nucleo, 0.1f, 0.9f * k, pincel);
		}
		const float v = s.t - IMPACTO;
		if (v >= 0.0f && v < 0.25f) {   // destello del impacto
			const float k = 1.0f - v / 0.25f;
			pincel.bola(hasta, (0.5f + 1.5f * v) * s.ancho, s.halo, 0.6f * k);
			pincel.bola(hasta, 0.3f * k + 0.05f, glm::vec3(1.0f, 0.97f, 0.9f), 2.5f * k);
		}
		explosion(hasta, 0.5f * glm::max(s.ancho, 1.0f), v - 0.03f, 0.6f, 2, s.semilla * 11u, pincel);
		chispas(hasta, dir, v, 0.85f, 40, s.semilla * 3u, 1.35f, pincel);
	}

	// ---------------------------------------------------------------- defensa
	// "cruzar los brazos" en una figura rigida: se agacha, gira de costado para cubrirse y recibe cada golpe del arma
	// (la rafaga lo sacude muchas veces poco; el canon y el riel una vez fuerte; el laser lo hace temblar sin parar)
	void defender(const Situacion& s, Pose& p) const override
	{
		const int a = arma(s);
		const float cubre = suave(CUBRE, CUBRE + 0.2f, s.t);
		p.aplastar *= 1.0f - 0.1f * cubre;
		p.escala *= 1.0f - 0.04f * cubre;
		p.girar += 0.35f * cubre;
		float atras = 0.0f, sacude = 0.0f;
		for (int i = 0; i < numDisparos(a); i++) {
			const Disparo d = disparo(a, i);
			const float u = s.t - d.llega;
			if (u < 0.0f) {
				break;
			}
			atras += 0.35f * d.fuerza * suave(0.0f, 0.15f, u);
			sacude += d.fuerza * sinf(u * 24.0f) * expf(-u * 6.0f);
		}
		if (a == LASER) {   // el rayo encima: tiembla mientras dura
			const float haz = suave(IMPACTO, IMPACTO + 0.05f, s.t) * (1.0f - suave(2.4f, 2.5f, s.t));
			p.desplazar.x += 0.015f * haz * sinf(s.t * 113.0f);
			p.desplazar.z += 0.015f * haz * sinf(s.t * 127.0f + 0.9f);
		}
		p.desplazar -= s.hacia * glm::min(atras, 0.6f);
		p.inclinar -= 0.2f * suave(IMPACTO, IMPACTO + 0.2f, s.t) + 0.05f * sacude;
		p.girar += 0.12f * sacude;
		p.brillo += 0.3f * glm::min(1.0f, glm::abs(sacude));
	}

	// ---------------------------------------------------------------- derrota
	static constexpr float EXPLOTA = MUERE + 0.35f;   // 2.9 s
	static constexpr float SALTO = 0.75f;             // s en el aire tras reventar

	// estruendo: se hincha y tiembla cada vez mas (se recalienta), REVIENTA: salta por el aire dando media vuelta
	// hacia atras, cae de espaldas con un golpe seco y rebote, sigue sacudiendose con explosiones secundarias y se
	// desintegra entre el humo
	void derrota(const Situacion& s, Pose& p) const override
	{
		cuerpoDerrota(s, s.t, p);
	}

	static void cuerpoDerrota(const Situacion& s, float t, Pose& p)
	{
		const float u = t - MUERE;
		const float pre = suave(MUERE, EXPLOTA, t);
		const float tiembla = pre * (1.0f - suave(EXPLOTA, EXPLOTA + 0.3f, t));
		p.desplazar.x += 0.07f * tiembla * sinf(u * 63.0f);
		p.desplazar.z += 0.07f * tiembla * sinf(u * 77.0f + 0.7f);
		p.girar += 0.1f * tiembla * sinf(u * 51.0f);
		p.escala *= 1.0f + 0.06f * tiembla;   // se hincha entero (rigido) antes de reventar
		p.ojos = 1.0f;
		p.aleteo = 1.0f - pre;

		// salto por la explosion: arco alto, empujado lejos del rival, media vuelta hacia atras
		const float x = glm::clamp((t - EXPLOTA) / SALTO, 0.0f, 1.0f);
		const float alto = 0.25f * glm::max(s.alto, 1.0f);
		p.desplazar.y += alto * sinf(3.14159f * x) - s.vuelo * suave(EXPLOTA, EXPLOTA + SALTO, t);
		p.desplazar -= s.hacia * (0.4f * pre + 0.9f * suave(EXPLOTA, EXPLOTA + SALTO + 0.2f, t));
		p.girar += 0.5f * suave(EXPLOTA, EXPLOTA + SALTO, t);
		float atras = 1.5f * suave(EXPLOTA + 0.05f, EXPLOTA + SALTO, t);
		const float r = t - (EXPLOTA + SALTO);
		if (r > 0.0f && r < 0.35f) {   // golpe contra la mesa: rebote y aplastado seco
			atras -= 0.14f * sinf(3.14159f * r / 0.35f);
			p.desplazar.y += 0.1f * sinf(3.14159f * r / 0.35f);
			p.aplastar *= 1.0f - 0.07f * sinf(3.14159f * r / 0.35f);
		}
		p.inclinar -= atras;
		p.desplazar.y -= 0.12f * suave(EXPLOTA + 0.4f, EXPLOTA + SALTO, t);

		// explosiones secundarias ya en el suelo: sacudidas
		for (int i = 0; i < 2; i++) {
			const float ts = t - secundaria(i);
			if (ts > 0.0f) {
				const float k = expf(-ts * 7.0f);
				p.desplazar.y += 0.05f * k * glm::abs(sinf(ts * 30.0f));
				p.girar += 0.04f * k * sinf(ts * 41.0f);
			}
		}
		p.brillo += 2.0f * suave(EXPLOTA - 0.15f, EXPLOTA, t) * (1.0f - suave(EXPLOTA, EXPLOTA + 0.5f, t)) + 0.8f * pre * (1.0f - pre);
		p.desintegrar = suave(EXPLOTA + 1.6f, DESAPARECE + 0.6f, t);
	}
	static float secundaria(int i) { return EXPLOTA + (i == 0 ? 0.95f : 1.5f); }

	// explosion grande: chispazos antes de reventar; fogonazo blanco enorme y onda de choque sobre la mesa
	// (estruendo); bola de fuego con lenguas que crecen; lluvia de chispas y brasas que caen; dos explosiones
	// secundarias en el suelo; fuego que queda ardiendo y humo negro que sube
	void efectoDerrota(const Situacion& s, glm::vec3 donde, Pincel& pincel) const override
	{
		// el motor pasa donde esta el cuerpo AHORA (salta y cae): la explosion principal queda donde revento
		Pose ahora, alli;
		cuerpoDerrota(s, s.t, ahora);
		cuerpoDerrota(s, EXPLOTA, alli);
		const glm::vec3 centro = donde - ahora.desplazar + alli.desplazar;
		glm::vec3 suelo = donde;   // donde quedo tirado (sobre la mesa)
		suelo.y = 0.15f;

		const float u = s.t - EXPLOTA;
		const float tam = glm::max(s.alto, s.ancho);
		const glm::vec3 blanco(1.0f, 0.97f, 0.9f), amarillo(1.0f, 0.8f, 0.3f), naranja(1.0f, 0.45f, 0.1f);

		if (u < 0.0f) {   // se recalienta: chispazos que saltan del cuerpo
			const float k = suave(-0.35f, 0.0f, u);
			const uint32_t paso = (uint32_t)(s.t * 15.0f);
			for (int i = 0; i < 2; i++) {
				const uint32_t h = s.semilla * 29u + paso * 5u + (uint32_t)i;
				const glm::vec3 d(azar(h) - 0.5f, azar(h + 1u) - 0.2f, azar(h + 2u) - 0.5f);
				pincel.relampago(donde, donde + d * (0.6f * tam * k), h, 0.1f, 0.8f, 1);
			}
			chispas(donde, -s.hacia, glm::fract(s.t * 4.0f) * 0.25f, 0.25f, 8, s.semilla + paso / 4u, 0.8f, pincel);
			pincel.bola(donde, 0.3f * tam * k, naranja, 0.5f * k);
			return;
		}
		if (u > 3.6f) {
			return;
		}

		// fogonazo: enorme, blanco y muy breve
		if (u < 0.2f) {
			const float k = 1.0f - u / 0.2f;
			pincel.bola(centro, (0.8f + 1.2f * u) * tam, blanco, 3.0f * k);
			pincel.bola(centro, (0.5f + 2.5f * u) * tam, amarillo, 1.5f * k);
		}
		// onda de choque sobre la mesa
		if (u < 0.45f) {
			const float k = 1.0f - u / 0.45f;
			const glm::vec3 piso(centro.x, 0.08f, centro.z);
			anillo(piso, glm::vec3(0.0f, 1.0f, 0.0f), 0.4f * tam + 7.0f * u, 16, amarillo, 0.12f + 0.2f * u, 0.9f * k, pincel);
		}
		// bola de fuego: 7 lenguas que crecen hacia afuera y una columna que sube
		if (u < 1.7f) {
			const float crece = suave(0.0f, 0.35f, u);
			const float k = 1.0f - suave(0.6f, 1.7f, u);
			const glm::vec3 c = centro + glm::vec3(0.0f, 0.5f * u, 0.0f);
			pincel.bola(c, (0.4f + 0.6f * crece) * tam, naranja, 0.5f * k);
			for (int i = 0; i < 7; i++) {
				const uint32_t h = s.semilla * 53u + (uint32_t)i * 5u;
				const float ang = 6.2832f * (float)i / 7.0f + azar(h);
				const glm::vec3 d = glm::normalize(glm::vec3(cosf(ang), 0.3f + 0.9f * azar(h + 1u), sinf(ang)));
				pincel.llama(c + d * (0.1f * tam), c + d * ((0.35f + 0.9f * crece) * tam) + glm::vec3(0.0f, 0.4f * u * tam, 0.0f),
					(0.35f + 0.4f * crece) * tam, k, h);
			}
			for (int i = 0; i < 2; i++) {
				pincel.llama(c - glm::vec3(0.0f, 0.2f * tam, 0.0f), c + glm::vec3(0.0f, (0.6f + 1.2f * crece) * tam, 0.0f),
					(0.5f - 0.15f * (float)i) * tam, k, s.semilla * 7u + (uint32_t)i);
			}
		}
		// lluvia de chispas (finas, rapidas) y brasas (mas gruesas, duran mas): salen en todas direcciones y caen
		{
			const glm::vec3 g(0.0f, -9.8f, 0.0f);
			for (int i = 0; i < 72; i++) {
				const uint32_t h = s.semilla * 71u + (uint32_t)i * 11u;
				const bool brasa = i >= 60;
				const float vida = brasa ? 2.2f : 0.9f + 0.9f * azar(h + 4u);
				if (u > vida) {
					continue;
				}
				const float k = 1.0f - u / vida;
				const float ang = 6.2832f * (float)i / 72.0f + 0.5f * azar(h);
				const glm::vec3 sale = glm::normalize(glm::vec3(cosf(ang), 0.25f + 1.3f * azar(h + 1u), sinf(ang)));
				const glm::vec3 v = sale * (brasa ? 2.5f + 2.5f * azar(h + 2u) : 4.0f + 7.0f * azar(h + 2u));
				glm::vec3 a = centro + v * u + 0.5f * g * u * u;
				a.y = glm::max(a.y, 0.03f);
				glm::vec3 b = a - (v + g * u) * (brasa ? 0.02f : 0.035f);
				b.y = glm::max(b.y, 0.03f);
				const glm::vec3 color = brasa ? naranja : glm::mix(amarillo, blanco, azar(h + 3u));
				pincel.tramo(a, b, brasa ? 0.035f : 0.014f, color, (brasa ? 1.0f : 1.5f) * k);
			}
		}
		// explosiones secundarias en el suelo, cada una con su fogonazo, fuego y chispas
		for (int i = 0; i < 2; i++) {
			const float v = s.t - secundaria(i);
			const uint32_t h = s.semilla * 13u + (uint32_t)i * 101u;
			const glm::vec3 c = suelo + glm::vec3(azar(h) - 0.5f, 0.1f, azar(h + 1u) - 0.5f) * tam * 0.5f;
			explosion(c, 0.45f * tam, v, 0.6f, 2, h, pincel);
			chispas(c, -s.hacia, v, 0.55f, 10, h, 1.0f, pincel);
		}
		// lo que queda ardiendo en la mesa
		if (u > SALTO && u < 3.0f) {
			const float k = suave(SALTO, SALTO + 0.3f, u) * (1.0f - suave(2.2f, 3.0f, u));
			for (int i = 0; i < 2; i++) {
				const glm::vec3 b = suelo + s.hacia * ((float)i - 0.5f) * 0.4f * tam;
				pincel.llama(b, b + glm::vec3(0.0f, (0.5f + 0.15f * sinf(s.t * 9.0f + (float)i)) * tam, 0.0f), 0.3f * tam, 0.8f * k,
					s.semilla * 19u + (uint32_t)i);
			}
		}
		// humo negro que sube y se ensancha
		if (u > 0.35f) {
			const float k = suave(0.35f, 0.8f, u) * (1.0f - suave(2.6f, 3.6f, u));
			for (int i = 0; i < 10; i++) {
				const uint32_t h = s.semilla * 19u + (uint32_t)i * 3u;
				const float edad = u - 0.35f - 0.12f * (float)i;
				if (edad < 0.0f) {
					continue;
				}
				const glm::vec3 d(azar(h) - 0.5f, 0.0f, azar(h + 1u) - 0.5f);
				const glm::vec3 c = glm::mix(centro, suelo, glm::min(1.0f, u / SALTO)) + d * tam * (0.5f + 0.3f * edad) +
					glm::vec3(0.0f, 0.3f * tam + 0.9f * edad * (0.6f + 0.4f * azar(h + 2u)), 0.0f);
				pincel.humo(c, (0.25f + 0.3f * edad) * tam * 0.6f, glm::vec3(0.06f, 0.055f, 0.05f), 0.75f * k);
			}
		}
	}
};

} // namespace combate
