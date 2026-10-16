/*
 * Yugi Reload - la interfaz del duelo (todo lo que rodea al tablero), dibujada 100% por codigo en la GPU.
 *
 * ESTILO "VIDRIO DE NEON 2026" (propio, sin arte de Gemini ni del juego original):
 *  - Paneles de vidrio oscuro translucido (azul noche) con sombra suave, bisel de luz arriba y un borde fino del
 *    color del duenno; dos destellos recorren el contorno sin parar (cian = jugador, carmesi = rival).
 *  - Tipografia moderna libre (OFL): Chakra Petch para numeros (LP, ATK/DEF, fases, contadores) y Rajdhani para
 *    textos; texto SDF (stb_truetype) nitido a cualquier tamano, con halo y contorno.
 *  - Acentos: dorado para lo que se elige y la fase activa; cian/carmesi para cada lado; color por atributo.
 *  - Micro-animaciones con resortes: el recuadro dorado vuela de un objetivo a otro, la carta elegida se levanta,
 *    el visor gira la carta al cambiar y se inclina en 3D; los LP ruedan, dejan una estela de danno que se
 *    vacia, sacuden el panel y sueltan chispas.
 *  - FX: chispas doradas que salen del recuadro, polvo de luz en el visor, foil holografico y destello en la cara
 *    de la carta, dorso propio dibujado por shader (rejilla hexagonal, anillos que giran, rombo de luz).
 *  - El campo 3D se desplaza a la derecha (lente desplazada) para dejar la columna izquierda libre, como el juego
 *    de PC: LP rival arriba, visor + texto de la carta, LP jugador abajo, columna de fases, manos arriba y abajo.
 * Referencias de tecnica: SDF de rectangulos redondeados (Inigo Quilez), texto SDF (stb_truetype), foil tipo
 * Balatro/Master Duel reinterpretado; todo el codigo es propio.
 */
#pragma once

#include <algorithm>
#include <array>
#include <cmath>
#include <fstream>
#include <iterator>
#include <string>
#include <unordered_map>
#include <vector>

#define STB_TRUETYPE_IMPLEMENTATION
#define STBTT_STATIC
#include "stb_truetype.h"
#include "stb_image.h"   // la implementacion ya esta en la base (VulkanglTFModel.cpp)

namespace interfaz {

enum Tipo { PANEL = 0, TEXTO, IMAGEN, DORSO, MARCO, PARTICULA, BARRA, ESTRELLA, ZONA, LINEA, FLECHA, LADO_MAZO, ORBE, FONDO };

struct Vertice {
	glm::vec4 pos;      // espacio de recorte
	glm::vec2 uv;
	glm::vec2 local;
	glm::vec4 color, color2, forma, extra;
};

constexpr float TAM_BASE = 52.0f;     // alto en px de los glifos del atlas
constexpr int RELLENO_SDF = 8;
constexpr int ATLAS = 2048;
constexpr uint32_t MAX_VERTICES = 120000;
constexpr float ESCALA = 1.4f;        // ESCALA_TABLERO del juego
// medidas de referencia (pantalla de 1080 de alto)
constexpr float MARGEN = 22.0f, COL_X = 22.0f, COL_ANCHO = 400.0f;
constexpr float FASES_X = 436.0f, FASES_ANCHO = 64.0f;
constexpr float CAMPO_X = 512.0f;     // desde aqui a la derecha se ve el tablero

// paleta
const glm::vec4 VIDRIO{ 0.026f, 0.038f, 0.072f, 0.86f };
const glm::vec4 CIAN{ 0.30f, 0.86f, 1.0f, 1.0f };
const glm::vec4 CARMESI{ 1.0f, 0.27f, 0.42f, 1.0f };
const glm::vec4 ORO{ 1.0f, 0.78f, 0.32f, 1.0f };
const glm::vec4 BLANCO{ 0.94f, 0.97f, 1.0f, 1.0f };
const glm::vec4 GRIS{ 0.62f, 0.69f, 0.80f, 1.0f };
const glm::vec4 NADA{ 0.0f };

// zonas del tablero (remake/diseno/tablero.json; en el juego x1.4)
struct Zona { const char* id; float x, z; const char* tipo; };
static const Zona ZONAS[] = {
	{ "jugador_monstruo_0", -5.4f, 2.2f, "monstruo" }, { "jugador_magia_0", -5.4f, 5.5f, "magia" },
	{ "jugador_monstruo_1", -2.7f, 2.2f, "monstruo" }, { "jugador_magia_1", -2.7f, 5.5f, "magia" },
	{ "jugador_monstruo_2", 0.0f, 2.2f, "monstruo" }, { "jugador_magia_2", 0.0f, 5.5f, "magia" },
	{ "jugador_monstruo_3", 2.7f, 2.2f, "monstruo" }, { "jugador_magia_3", 2.7f, 5.5f, "magia" },
	{ "jugador_monstruo_4", 5.4f, 2.2f, "monstruo" }, { "jugador_magia_4", 5.4f, 5.5f, "magia" },
	{ "jugador_campo", -8.2f, 2.2f, "campo" }, { "jugador_fusion", -8.2f, 5.5f, "fusion" },
	{ "jugador_cementerio", 8.2f, 2.2f, "cementerio" }, { "jugador_mazo", 8.2f, 5.5f, "mazo" },
	{ "rival_monstruo_0", 5.4f, -2.2f, "monstruo" }, { "rival_magia_0", 5.4f, -5.5f, "magia" },
	{ "rival_monstruo_1", 2.7f, -2.2f, "monstruo" }, { "rival_magia_1", 2.7f, -5.5f, "magia" },
	{ "rival_monstruo_2", 0.0f, -2.2f, "monstruo" }, { "rival_magia_2", 0.0f, -5.5f, "magia" },
	{ "rival_monstruo_3", -2.7f, -2.2f, "monstruo" }, { "rival_magia_3", -2.7f, -5.5f, "magia" },
	{ "rival_monstruo_4", -5.4f, -2.2f, "monstruo" }, { "rival_magia_4", -5.4f, -5.5f, "magia" },
	{ "rival_campo", 8.2f, -2.2f, "campo" }, { "rival_fusion", 8.2f, -5.5f, "fusion" },
	{ "rival_cementerio", -8.2f, -2.2f, "cementerio" }, { "rival_mazo", -8.2f, -5.5f, "mazo" },
};
constexpr size_t NUM_ZONAS = sizeof(ZONAS) / sizeof(ZONAS[0]);
constexpr float ZONA_ANCHO = 1.16f * ESCALA, ZONA_ALTO = 1.62f * ESCALA;
constexpr float CARTA_ANCHO = 1.0f * ESCALA, CARTA_ALTO = 1.45f * ESCALA;

// el duelo de prueba (el mismo de herramientas/blender/escena_tablero.py CAMPO)
struct Ocupa { const char* zona; const char* carta; bool bocaAbajo; };
static const Ocupa CAMPO_PRUEBA[] = {
	{ "jugador_monstruo_0", "baby_dragon", false }, { "jugador_monstruo_1", "red_eyes", false },
	{ "jugador_monstruo_2", "dark_magician", false }, { "jugador_monstruo_3", "kuriboh", false },
	{ "jugador_monstruo_4", "dark_magician_girl", false },
	{ "rival_monstruo_0", "celtic_guardian", false }, { "rival_monstruo_1", "oni_tank_t_34", false },
	{ "rival_monstruo_2", "summoned_skull", false }, { "rival_monstruo_3", "deepsea_shark", false },
	{ "rival_monstruo_4", "stone_ogre_grotto", false },
	{ "jugador_magia_0", "swords_of_revealing_light", false }, { "jugador_magia_1", "", true },
	{ "jugador_magia_3", "", true }, { "rival_magia_1", "mirror_force", false },
	{ "rival_magia_2", "", true }, { "rival_magia_4", "", true },
	{ "jugador_campo", "sogen", false }, { "jugador_fusion", "flame_swordsman", false },
};
static const char* const MANO_JUGADOR[] = { "blue_eyes", "gaia", "pot_of_greed", "monster_reborn", "trap_hole", "time_wizard" };
constexpr int NUM_MANO_J = 6, NUM_MANO_R = 5;
static const char* const FASES[] = { "DP", "SP", "M1", "BP", "M2", "EP" };
static const char* const NOMBRE_FASE[] = { "ROBO", "ESPERA", "PRINCIPAL 1", "BATALLA", "PRINCIPAL 2", "FINAL" };

struct Glifo { float u0, v0, u1, v1, xoff, yoff, w, h, avance; };
struct Fuente {
	stbtt_fontinfo info{};
	std::vector<unsigned char> datos;
	float escala{ 1.0f }, ascenso{ 0.0f };
	std::unordered_map<int, Glifo> glifos;
};
enum { F_NUMEROS = 0, F_TITULO, F_TEXTO, NUM_FUENTES };

struct CartaUI {
	std::string id, nombre, clase, atributo, tipo, desc;
	int nivel{ 0 }, atk{ 0 }, def{ 0 };
	vks::Texture2D cara, mini;
	VkDescriptorSet setCara{ VK_NULL_HANDLE }, setMini{ VK_NULL_HANDLE };
	bool lista{ false };
};

struct Chispa { glm::vec2 pos, vel; float vida, dur, tam; glm::vec3 color; float cruz; };

struct Vida {
	int valor{ 8000 };
	float mostrado{ 8000.0f }, fantasma{ 8000.0f };
	float tGolpe{ 99.0f };
	int ultimoDanio{ 0 };
};

// lo que se elige con el puntero
enum Clase { MANO_J = 0, MANO_R, EN_ZONA };
struct Objetivo { Clase clase; int indice; glm::vec2 pantalla; };

inline std::vector<int> utf8(const std::string& s)
{
	std::vector<int> r;
	for (size_t i = 0; i < s.size();) {
		const unsigned char c = (unsigned char)s[i];
		int cp = c, n = 1;
		if (c >= 0xF0) { cp = c & 0x07; n = 4; }
		else if (c >= 0xE0) { cp = c & 0x0F; n = 3; }
		else if (c >= 0xC0) { cp = c & 0x1F; n = 2; }
		for (int k = 1; k < n && i + k < s.size(); k++) {
			cp = (cp << 6) | ((unsigned char)s[i + k] & 0x3F);
		}
		r.push_back(cp);
		i += n;
	}
	return r;
}

inline std::string mayusculas(const std::string& s)
{
	std::string r = s;
	for (char& c : r) {
		if (c >= 'a' && c <= 'z') c = (char)(c - 32);
	}
	return r;
}

class Interfaz {
public:
	// ---------------------------------------------------------------------------------------------- preparar
	void preparar(vks::VulkanDevice* d, VkQueue q, VkFormat formatoColor, VkFormat formatoProf, VkPipelineCache cache,
	              const std::string& assets, const std::string& shaders)
	{
		disp = d;
		dev = d->logicalDevice;
		cola = q;
		rutaAssets = assets;
		leerEntorno();
		cargarCartas();
		crearAtlas();
		crearDescriptores();
		crearPipelines(formatoColor, formatoProf, cache, shaders);
		for (auto& b : vertices) {
			VK_CHECK_RESULT(disp->createBuffer(VK_BUFFER_USAGE_VERTEX_BUFFER_BIT, VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT,
			                                   &b, MAX_VERTICES * sizeof(Vertice)));
			VK_CHECK_RESULT(b.map());
		}
		v.reserve(MAX_VERTICES);
		listo = true;
	}

	~Interfaz()
	{
		if (!dev) {
			return;
		}
		vkDeviceWaitIdle(dev);
		for (auto& b : vertices) {
			b.destroy();
		}
		for (CartaUI& c : cartas) {
			if (c.lista) {
				c.cara.destroy();
				c.mini.destroy();
			}
		}
		atlas.destroy();
		vkDestroySampler(dev, muestreador, nullptr);
		vkDestroyPipeline(dev, p2d, nullptr);
		vkDestroyPipeline(dev, p3d, nullptr);
		vkDestroyPipelineLayout(dev, layout, nullptr);
		vkDestroyDescriptorSetLayout(dev, layoutSet, nullptr);
		vkDestroyDescriptorPool(dev, pool, nullptr);
	}

	// El tablero se corre a la derecha de la columna izquierda (lente desplazada en el espacio de recorte):
	// x' = k x + dx w, y' = k y + dy w. Se aplica a la proyeccion de la escena (y la interfaz usa la misma)
	glm::mat4 ajustarProyeccion(const glm::mat4& proy, float ancho, float alto) const
	{
		const float s = alto / 1080.0f;
		const float izq = CAMPO_X * s;
		const float k = (ancho - izq) / ancho * zoom;
		const float cx = ((izq + ancho) * 0.5f) / ancho * 2.0f - 1.0f;
		glm::mat4 m(1.0f);
		m[0][0] = k;
		m[1][1] = k;
		m[3][0] = cx;
		m[3][1] = desplazaY;
		return m * proy;
	}

	// LP nuevos de un lado (animacion de danno o curacion)
	void cambiarLP(bool rival, int lp)
	{
		Vida& vi = rival ? vidaR : vidaJ;
		lp = glm::clamp(lp, 0, 99999);
		if (lp < vi.valor) {
			vi.tGolpe = 0.0f;
			vi.ultimoDanio = vi.valor - lp;
			vi.fantasma = glm::max(vi.fantasma, vi.mostrado);
			estallar(rival);
		}
		vi.valor = lp;
	}

	// ---------------------------------------------------------------------------------------------- cada cuadro
	// lee el control (ya leido por el juego en "mando"); libre = false cuando la ventana de ajustes tiene el control
	void actualizar(const struct pad& mando, float dt, bool libre)
	{
		if (!listo) {
			return;
		}
		dt = glm::clamp(dt, 0.0f, 0.1f);
		t += dt;
		demo();
		if (libre && !fijo) {
			glm::vec2 dir{ 0.0f };
			if (mando.pressed & PAD_LEFT) dir = { -1, 0 };
			if (mando.pressed & PAD_RIGHT) dir = { 1, 0 };
			if (mando.pressed & PAD_UP) dir = { 0, -1 };
			if (mando.pressed & PAD_DOWN) dir = { 0, 1 };
			// cruceta mantenida: repite
			const uint32_t cruz = mando.held & (PAD_LEFT | PAD_RIGHT | PAD_UP | PAD_DOWN);
			if (cruz && cruz == cruzAntes) {
				repetir -= dt;
				if (repetir <= 0.0f) {
					repetir = 0.13f;
					if (cruz & PAD_LEFT) dir = { -1, 0 };
					if (cruz & PAD_RIGHT) dir = { 1, 0 };
					if (cruz & PAD_UP) dir = { 0, -1 };
					if (cruz & PAD_DOWN) dir = { 0, 1 };
				}
			} else {
				repetir = 0.38f;
			}
			cruzAntes = cruz;
			// palanca izquierda: un paso al inclinarla, y repite si se mantiene
			const glm::vec2 palanca{ mando.left_x, mando.left_y };
			if (glm::length(palanca) > 0.6f) {
				palancaT -= dt;
				if (palancaT <= 0.0f) {
					dir = fabsf(palanca.x) > fabsf(palanca.y) ? glm::vec2(glm::sign(palanca.x), 0.0f) : glm::vec2(0.0f, glm::sign(palanca.y));
					palancaT = palancaSuelta ? 0.38f : 0.14f;
					palancaSuelta = false;
				}
			} else if (glm::length(palanca) < 0.3f) {
				palancaT = 0.0f;
				palancaSuelta = true;
			}
			if (dir != glm::vec2(0.0f)) {
				mover(dir);
			}
		}
		animarVidas(dt);
		animarChispas(dt);
		// la carta del visor gira al cambiar lo elegido
		const int sel = seleccion;
		if (sel != selVisor) {
			if (giroVisor < 0.0f) {
				giroVisor = 0.0f;
				selNueva = sel;
			}
		}
		if (giroVisor >= 0.0f) {
			giroVisor += dt / 0.38f;
			if (giroVisor >= 0.5f && selVisor != selNueva) {
				selVisor = selNueva;
				tTexto = 0.0f;
			}
			if (giroVisor >= 1.0f) {
				giroVisor = -1.0f;
			}
		}
		tTexto += dt;
		// manos: la elegida se levanta; la mano con el puntero sube un poco entera
		for (int k = 0; k < NUM_MANO_J; k++) {
			resorte(elevaJ[k], velJ[k], objetivos.size() > (size_t)seleccion && objetivos[seleccion].clase == MANO_J && objetivos[seleccion].indice == k ? 1.0f : 0.0f, dt);
		}
		for (int k = 0; k < NUM_MANO_R; k++) {
			resorte(elevaR[k], velR[k], objetivos.size() > (size_t)seleccion && objetivos[seleccion].clase == MANO_R && objetivos[seleccion].indice == k ? 1.0f : 0.0f, dt);
		}
		const Clase c = objetivos.empty() ? EN_ZONA : objetivos[seleccion].clase;
		resorte(focoJ, velFocoJ, c == MANO_J ? 1.0f : 0.0f, dt);
		resorte(focoR, velFocoR, c == MANO_R ? 1.0f : 0.0f, dt);
		dtCuadro = dt;
	}

	// arma todo y lo graba en el comando (despues de la escena 3D, en la misma pasada: usa su profundidad)
	void dibujar(VkCommandBuffer cmd, uint32_t cuadro, const glm::mat4& vistaProy, float ancho, float alto)
	{
		if (!listo) {
			return;
		}
		W = ancho;
		H = alto;
		s = alto / 1080.0f;
		vp = vistaProy;
		v.clear();
		lotes.clear();
		construirObjetivos();
		construir();
		const size_t n = glm::min(v.size(), (size_t)MAX_VERTICES);
		memcpy(vertices[cuadro].mapped, v.data(), n * sizeof(Vertice));
		const glm::vec4 pantalla(W, H, t, s);
		VkDeviceSize desde = 0;
		vkCmdBindVertexBuffers(cmd, 0, 1, &vertices[cuadro].buffer, &desde);
		VkPipeline actual = VK_NULL_HANDLE;
		for (size_t i = 0; i < lotes.size(); i++) {
			const uint32_t fin = i + 1 < lotes.size() ? lotes[i + 1].desde : (uint32_t)n;
			if (lotes[i].desde >= fin || lotes[i].desde >= n) {
				continue;
			}
			const VkPipeline p = lotes[i].en3D ? p3d : p2d;
			if (p != actual) {
				vkCmdBindPipeline(cmd, VK_PIPELINE_BIND_POINT_GRAPHICS, p);
				vkCmdPushConstants(cmd, layout, VK_SHADER_STAGE_VERTEX_BIT | VK_SHADER_STAGE_FRAGMENT_BIT, 0, sizeof(glm::vec4), &pantalla);
				actual = p;
			}
			vkCmdBindDescriptorSets(cmd, VK_PIPELINE_BIND_POINT_GRAPHICS, layout, 0, 1, &lotes[i].set, 0, nullptr);
			vkCmdDraw(cmd, fin - lotes[i].desde, 1, lotes[i].desde, 0);
		}
	}

private:
	vks::VulkanDevice* disp{ nullptr };
	VkDevice dev{ VK_NULL_HANDLE };
	VkQueue cola{ VK_NULL_HANDLE };
	std::string rutaAssets;
	bool listo{ false };
	VkDescriptorPool pool{ VK_NULL_HANDLE };
	VkDescriptorSetLayout layoutSet{ VK_NULL_HANDLE };
	VkPipelineLayout layout{ VK_NULL_HANDLE };
	VkPipeline p2d{ VK_NULL_HANDLE }, p3d{ VK_NULL_HANDLE };
	VkSampler muestreador{ VK_NULL_HANDLE };
	vks::Texture2D atlas;
	VkDescriptorSet setAtlas{ VK_NULL_HANDLE };
	std::array<vks::Buffer, maxConcurrentFrames> vertices;
	std::array<Fuente, NUM_FUENTES> fuentes;
	std::vector<CartaUI> cartas;

	std::vector<Vertice> v;
	struct Lote { VkDescriptorSet set; bool en3D; uint32_t desde; };
	std::vector<Lote> lotes;

	float W{ 1920 }, H{ 1080 }, s{ 1 }, t{ 0 }, dtCuadro{ 0.016f };
	glm::mat4 vp{ 1.0f };

	// puntero
	std::vector<Objetivo> objetivos;
	int seleccion{ 0 };
	std::string pedido{ "jugador_mano_0" };   // lo elegido por nombre (se resuelve al armar los objetivos)
	bool fijo{ false }, recorrido{ false };
	uint32_t cruzAntes{ 0 };
	float repetir{ 0.38f }, palancaT{ 0.0f };
	bool palancaSuelta{ true };
	// recuadro dorado: esquinas (recorte) y forma, con resorte
	std::array<glm::vec4, 4> marco{}, velMarco{};
	glm::vec4 formaMarco{ 0.0f }, velForma{ 0.0f };   // medio ancho, medio alto, grosor, halo
	bool marcoListo{ false };
	bool marcoEn3D{ false };
	float llegada{ 0.0f };
	float emitir{ 0.0f };
	// manos
	float elevaJ[NUM_MANO_J]{}, velJ[NUM_MANO_J]{}, elevaR[NUM_MANO_R]{}, velR[NUM_MANO_R]{};
	float focoJ{ 0 }, velFocoJ{ 0 }, focoR{ 0 }, velFocoR{ 0 };
	// visor
	int selVisor{ -1 }, selNueva{ 0 };
	float giroVisor{ -1.0f }, tTexto{ 0.0f };
	// partida
	Vida vidaJ, vidaR;
	int fase{ 3 };
	int mazoJ{ 34 }, mazoR{ 35 }, cementerioJ{ 0 }, cementerioR{ 0 };
	std::vector<Chispa> chispas;
	uint32_t semilla{ 1234567u };
	// pruebas en el PC
	float zoom{ 0.71f }, desplazaY{ -0.17f };
	int lpPedidoR{ -1 }, lpPedidoJ{ -1 };
	bool lpHecho{ false };

	float azar()
	{
		semilla = semilla * 1664525u + 1013904223u;
		return (float)(semilla >> 8) / 16777216.0f;
	}

	static void resorte(float& x, float& vel, float meta, float dt, float k = 260.0f, float amort = 0.72f)
	{
		const float a = (meta - x) * k - vel * 2.0f * sqrtf(k) * amort;
		vel += a * dt;
		x += vel * dt;
	}

	// ------------------------------------------------------------------------------------------ recursos
	void leerEntorno()
	{
#if defined(PS5_HOST_REFERENCE)
		if (const char* p = getenv("YUGI_PUNTERO")) {
			if (strcmp(p, "recorrido") == 0) {
				recorrido = true;
			} else {
				pedido = p;
			}
			fijo = true;
		}
		if (const char* l = getenv("YUGI_LP")) {
			sscanf(l, "%d,%d", &lpPedidoR, &lpPedidoJ);
		}
		if (const char* f = getenv("YUGI_FASE")) {
			for (int i = 0; i < 6; i++) {
				if (strcmp(f, FASES[i]) == 0) fase = i;
			}
		}
		if (const char* z = getenv("YUGI_UI_ZOOM")) zoom = (float)atof(z);
		if (const char* y = getenv("YUGI_UI_DY")) desplazaY = (float)atof(y);
#endif
	}

	void demo()
	{
		if (recorrido) {
			static const char* const PASOS[] = { "jugador_mano_0", "jugador_mano_2", "jugador_monstruo_2", "jugador_monstruo_1",
			                                     "rival_monstruo_0", "rival_magia_1", "rival_mano_2", "rival_mazo",
			                                     "jugador_fusion", "jugador_mazo", "jugador_mano_4" };
			const int n = sizeof(PASOS) / sizeof(PASOS[0]);
			pedido = PASOS[(int)(t / 1.3f) % n];
		}
		if (!lpHecho && lpPedidoR >= 0 && t > 1.2f) {
			cambiarLP(true, lpPedidoR);
			lpHecho = true;
		}
		if (lpPedidoJ >= 0 && t > 2.8f && vidaJ.valor != lpPedidoJ && vidaJ.tGolpe > 50.0f) {
			cambiarLP(false, lpPedidoJ);
		}
	}

	int buscarCarta(const std::string& id) const
	{
		for (size_t i = 0; i < cartas.size(); i++) {
			if (cartas[i].id == id) return (int)i;
		}
		return -1;
	}

	void cargarCartas()
	{
		std::ifstream f(rutaAssets + "ui/cartas_ui.txt");
		std::string linea;
		while (std::getline(f, linea)) {
			std::vector<std::string> c;
			size_t a = 0, b;
			while ((b = linea.find('|', a)) != std::string::npos) {
				c.push_back(linea.substr(a, b - a));
				a = b + 1;
			}
			c.push_back(linea.substr(a));
			if (c.size() < 9) continue;
			CartaUI k;
			k.id = c[0]; k.nombre = c[1]; k.clase = c[2]; k.atributo = c[3]; k.tipo = c[4];
			k.nivel = atoi(c[5].c_str()); k.atk = atoi(c[6].c_str()); k.def = atoi(c[7].c_str()); k.desc = c[8];
			cartas.push_back(std::move(k));
		}
		for (CartaUI& k : cartas) {
			k.lista = cargarImagen(rutaAssets + "ui/cara_" + k.id + ".png", k.cara) &&
			          cargarImagen(rutaAssets + "ui/mini_" + k.id + ".png", k.mini);
		}
	}

	bool cargarImagen(const std::string& ruta, vks::Texture2D& tex)
	{
		int w, h, n;
		stbi_uc* px = stbi_load(ruta.c_str(), &w, &h, &n, 4);
		if (!px) {
			fprintf(stderr, "[interfaz] falta %s\n", ruta.c_str());
			return false;
		}
		tex.fromBuffer(px, (VkDeviceSize)w * h * 4, VK_FORMAT_R8G8B8A8_UNORM, w, h, disp, cola, VK_FILTER_LINEAR);
		stbi_image_free(px);
		return true;
	}

	bool cargarFuente(Fuente& f, const std::string& ruta, std::vector<uint8_t>& px, int& cx, int& cy, int& fila)
	{
		std::ifstream a(ruta, std::ios::binary);
		if (!a) {
			fprintf(stderr, "[interfaz] falta la fuente %s\n", ruta.c_str());
			return false;
		}
		f.datos.assign(std::istreambuf_iterator<char>(a), std::istreambuf_iterator<char>());
		if (!stbtt_InitFont(&f.info, f.datos.data(), stbtt_GetFontOffsetForIndex(f.datos.data(), 0))) {
			return false;
		}
		f.escala = stbtt_ScaleForPixelHeight(&f.info, TAM_BASE);
		int asc, desc, gap;
		stbtt_GetFontVMetrics(&f.info, &asc, &desc, &gap);
		f.ascenso = asc * f.escala;
		std::vector<int> lista;
		for (int c = 32; c < 127; c++) lista.push_back(c);
		for (int c = 160; c < 256; c++) lista.push_back(c);
		for (int c : { 0x2014, 0x2022, 0x2026, 0x2605, 0x25B2, 0x25BC }) lista.push_back(c);
		for (int c : lista) {
			if (c != 32 && stbtt_FindGlyphIndex(&f.info, c) == 0) continue;
			int adv, lsb;
			stbtt_GetCodepointHMetrics(&f.info, c, &adv, &lsb);
			Glifo g{};
			g.avance = adv * f.escala;
			int w = 0, h = 0, xo = 0, yo = 0;
			unsigned char* sdf = stbtt_GetCodepointSDF(&f.info, f.escala, c, RELLENO_SDF, 128, 128.0f / RELLENO_SDF, &w, &h, &xo, &yo);
			if (sdf) {
				if (cx + w + 2 > ATLAS) {
					cx = 1;
					cy += fila + 2;
					fila = 0;
				}
				if (cy + h + 2 <= ATLAS) {
					for (int y = 0; y < h; y++) {
						memcpy(&px[(size_t)(cy + y) * ATLAS + cx], &sdf[y * w], w);
					}
					g.u0 = (float)cx / ATLAS; g.v0 = (float)cy / ATLAS;
					g.u1 = (float)(cx + w) / ATLAS; g.v1 = (float)(cy + h) / ATLAS;
					g.xoff = (float)xo; g.yoff = (float)yo; g.w = (float)w; g.h = (float)h;
					cx += w + 2;
					fila = std::max(fila, h);
				}
				stbtt_FreeSDF(sdf, nullptr);
			}
			f.glifos[c] = g;
		}
		return true;
	}

	void crearAtlas()
	{
		std::vector<uint8_t> px((size_t)ATLAS * ATLAS, 0);
		int cx = 1, cy = 1, fila = 0;
		const std::string d = rutaAssets + "ui/fuentes/";
		cargarFuente(fuentes[F_NUMEROS], d + "ChakraPetch-Bold.ttf", px, cx, cy, fila);
		cargarFuente(fuentes[F_TITULO], d + "Rajdhani-Bold.ttf", px, cx, cy, fila);
		cargarFuente(fuentes[F_TEXTO], d + "Rajdhani-SemiBold.ttf", px, cx, cy, fila);
		atlas.fromBuffer(px.data(), px.size(), VK_FORMAT_R8_UNORM, ATLAS, ATLAS, disp, cola, VK_FILTER_LINEAR);
	}

	VkDescriptorSet nuevoSet(vks::Texture2D& tex)
	{
		VkDescriptorSetAllocateInfo info = vks::initializers::descriptorSetAllocateInfo(pool, &layoutSet, 1);
		VkDescriptorSet set;
		VK_CHECK_RESULT(vkAllocateDescriptorSets(dev, &info, &set));
		VkDescriptorImageInfo img{ muestreador, tex.view, VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL };
		VkWriteDescriptorSet w = vks::initializers::writeDescriptorSet(set, VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER, 0, &img);
		vkUpdateDescriptorSets(dev, 1, &w, 0, nullptr);
		return set;
	}

	void crearDescriptores()
	{
		VkSamplerCreateInfo m = vks::initializers::samplerCreateInfo();
		m.magFilter = m.minFilter = VK_FILTER_LINEAR;
		m.mipmapMode = VK_SAMPLER_MIPMAP_MODE_LINEAR;
		m.addressModeU = m.addressModeV = m.addressModeW = VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_EDGE;
		m.maxLod = 1.0f;
		m.maxAnisotropy = 1.0f;
		VK_CHECK_RESULT(vkCreateSampler(dev, &m, nullptr, &muestreador));
		const uint32_t total = 1 + 2 * (uint32_t)cartas.size() + 2;
		std::vector<VkDescriptorPoolSize> tam = { vks::initializers::descriptorPoolSize(VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER, total) };
		VkDescriptorPoolCreateInfo pi = vks::initializers::descriptorPoolCreateInfo(tam, total);
		VK_CHECK_RESULT(vkCreateDescriptorPool(dev, &pi, nullptr, &pool));
		const std::vector<VkDescriptorSetLayoutBinding> b = {
			vks::initializers::descriptorSetLayoutBinding(VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER, VK_SHADER_STAGE_FRAGMENT_BIT, 0),
		};
		VkDescriptorSetLayoutCreateInfo li = vks::initializers::descriptorSetLayoutCreateInfo(b);
		VK_CHECK_RESULT(vkCreateDescriptorSetLayout(dev, &li, nullptr, &layoutSet));
		setAtlas = nuevoSet(atlas);
		for (CartaUI& k : cartas) {
			if (k.lista) {
				k.setCara = nuevoSet(k.cara);
				k.setMini = nuevoSet(k.mini);
			}
		}
	}

	void crearPipelines(VkFormat formatoColor, VkFormat formatoProf, VkPipelineCache cache, const std::string& shaders)
	{
		VkPushConstantRange empuje = vks::initializers::pushConstantRange(VK_SHADER_STAGE_VERTEX_BIT | VK_SHADER_STAGE_FRAGMENT_BIT, sizeof(glm::vec4), 0);
		VkPipelineLayoutCreateInfo pl = vks::initializers::pipelineLayoutCreateInfo(&layoutSet, 1);
		pl.pushConstantRangeCount = 1;
		pl.pPushConstantRanges = &empuje;
		VK_CHECK_RESULT(vkCreatePipelineLayout(dev, &pl, nullptr, &layout));

		VkVertexInputBindingDescription enlace{ 0, sizeof(Vertice), VK_VERTEX_INPUT_RATE_VERTEX };
		const std::array<VkVertexInputAttributeDescription, 7> atributos = { {
			{ 0, 0, VK_FORMAT_R32G32B32A32_SFLOAT, offsetof(Vertice, pos) },
			{ 1, 0, VK_FORMAT_R32G32_SFLOAT, offsetof(Vertice, uv) },
			{ 2, 0, VK_FORMAT_R32G32_SFLOAT, offsetof(Vertice, local) },
			{ 3, 0, VK_FORMAT_R32G32B32A32_SFLOAT, offsetof(Vertice, color) },
			{ 4, 0, VK_FORMAT_R32G32B32A32_SFLOAT, offsetof(Vertice, color2) },
			{ 5, 0, VK_FORMAT_R32G32B32A32_SFLOAT, offsetof(Vertice, forma) },
			{ 6, 0, VK_FORMAT_R32G32B32A32_SFLOAT, offsetof(Vertice, extra) },
		} };
		VkPipelineVertexInputStateCreateInfo entrada = vks::initializers::pipelineVertexInputStateCreateInfo();
		entrada.vertexBindingDescriptionCount = 1;
		entrada.pVertexBindingDescriptions = &enlace;
		entrada.vertexAttributeDescriptionCount = (uint32_t)atributos.size();
		entrada.pVertexAttributeDescriptions = atributos.data();
		VkPipelineInputAssemblyStateCreateInfo ensamble = vks::initializers::pipelineInputAssemblyStateCreateInfo(VK_PRIMITIVE_TOPOLOGY_TRIANGLE_LIST, 0, VK_FALSE);
		VkPipelineRasterizationStateCreateInfo raster = vks::initializers::pipelineRasterizationStateCreateInfo(VK_POLYGON_MODE_FILL, VK_CULL_MODE_NONE, VK_FRONT_FACE_COUNTER_CLOCKWISE, 0);
		// alfa premultiplicado: lo opaco tapa, los brillos (alfa 0) solo suman luz
		VkPipelineColorBlendAttachmentState mezcla = vks::initializers::pipelineColorBlendAttachmentState(0xf, VK_TRUE);
		mezcla.srcColorBlendFactor = VK_BLEND_FACTOR_ONE;
		mezcla.dstColorBlendFactor = VK_BLEND_FACTOR_ONE_MINUS_SRC_ALPHA;
		mezcla.colorBlendOp = VK_BLEND_OP_ADD;
		mezcla.srcAlphaBlendFactor = VK_BLEND_FACTOR_ONE;
		mezcla.dstAlphaBlendFactor = VK_BLEND_FACTOR_ONE_MINUS_SRC_ALPHA;
		mezcla.alphaBlendOp = VK_BLEND_OP_ADD;
		VkPipelineColorBlendStateCreateInfo mezclaCI = vks::initializers::pipelineColorBlendStateCreateInfo(1, &mezcla);
		VkPipelineDepthStencilStateCreateInfo sinProf = vks::initializers::pipelineDepthStencilStateCreateInfo(VK_FALSE, VK_FALSE, VK_COMPARE_OP_ALWAYS);
		VkPipelineDepthStencilStateCreateInfo conProf = vks::initializers::pipelineDepthStencilStateCreateInfo(VK_TRUE, VK_FALSE, VK_COMPARE_OP_LESS_OR_EQUAL);
		VkPipelineViewportStateCreateInfo vista = vks::initializers::pipelineViewportStateCreateInfo(1, 1, 0);
		VkPipelineMultisampleStateCreateInfo muestras = vks::initializers::pipelineMultisampleStateCreateInfo(VK_SAMPLE_COUNT_1_BIT, 0);
		std::vector<VkDynamicState> dinamicos = { VK_DYNAMIC_STATE_VIEWPORT, VK_DYNAMIC_STATE_SCISSOR };
		VkPipelineDynamicStateCreateInfo dinamico = vks::initializers::pipelineDynamicStateCreateInfo(dinamicos);
		VkShaderModule mv = vks::tools::loadShader((shaders + "yugireload/interfaz.vert.spv").c_str(), dev);
		VkShaderModule mf = vks::tools::loadShader((shaders + "yugireload/interfaz.frag.spv").c_str(), dev);
		std::array<VkPipelineShaderStageCreateInfo, 2> etapas{};
		etapas[0] = { VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO, nullptr, 0, VK_SHADER_STAGE_VERTEX_BIT, mv, "main", nullptr };
		etapas[1] = { VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO, nullptr, 0, VK_SHADER_STAGE_FRAGMENT_BIT, mf, "main", nullptr };
		VkPipelineRenderingCreateInfo render{
			.sType = VK_STRUCTURE_TYPE_PIPELINE_RENDERING_CREATE_INFO,
			.colorAttachmentCount = 1,
			.pColorAttachmentFormats = &formatoColor,
			.depthAttachmentFormat = formatoProf,
			.stencilAttachmentFormat = formatoProf,
		};
		VkGraphicsPipelineCreateInfo ci{
			.sType = VK_STRUCTURE_TYPE_GRAPHICS_PIPELINE_CREATE_INFO,
			.pNext = &render,
			.stageCount = 2,
			.pStages = etapas.data(),
			.pVertexInputState = &entrada,
			.pInputAssemblyState = &ensamble,
			.pViewportState = &vista,
			.pRasterizationState = &raster,
			.pMultisampleState = &muestras,
			.pDepthStencilState = &sinProf,
			.pColorBlendState = &mezclaCI,
			.pDynamicState = &dinamico,
			.layout = layout,
		};
		VK_CHECK_RESULT(vkCreateGraphicsPipelines(dev, cache, 1, &ci, nullptr, &p2d));
		ci.pDepthStencilState = &conProf;
		VK_CHECK_RESULT(vkCreateGraphicsPipelines(dev, cache, 1, &ci, nullptr, &p3d));
		vkDestroyShaderModule(dev, mv, nullptr);
		vkDestroyShaderModule(dev, mf, nullptr);
	}

	// ------------------------------------------------------------------------------------------ primitivas
	void usar(VkDescriptorSet set, bool en3D)
	{
		if (lotes.empty() || lotes.back().set != set || lotes.back().en3D != en3D) {
			lotes.push_back({ set, en3D, (uint32_t)v.size() });
		}
	}

	glm::vec4 recorte(glm::vec2 px) const { return glm::vec4(px.x / W * 2.0f - 1.0f, px.y / H * 2.0f - 1.0f, 0.0f, 1.0f); }
	glm::vec4 proyectar(glm::vec3 p) const { return vp * glm::vec4(p, 1.0f); }
	glm::vec2 aPantalla(glm::vec4 c) const
	{
		const float w = glm::max(c.w, 1e-4f);
		return glm::vec2((c.x / w * 0.5f + 0.5f) * W, (c.y / w * 0.5f + 0.5f) * H);
	}

	// un quad: esquinas 0 arriba-izq, 1 arriba-der, 2 abajo-der, 3 abajo-izq
	void quad(const glm::vec4 c[4], const glm::vec2 l[4], const glm::vec2 uv[4], glm::vec4 col, glm::vec4 col2, glm::vec4 forma, glm::vec4 extra)
	{
		if (v.size() + 6 > MAX_VERTICES) {
			return;
		}
		static const int orden[6] = { 0, 1, 2, 0, 2, 3 };
		for (int i : orden) {
			v.push_back({ c[i], uv[i], l[i], col, col2, forma, extra });
		}
	}

	// rectangulo en pantalla (px), girado "ang" alrededor de su centro; margen = cuanto sobra para brillos/sombra
	void rect(glm::vec2 centro, glm::vec2 tam, float ang, float margen, Tipo tipo, glm::vec4 col, glm::vec4 col2, float radio,
	          glm::vec4 extra, glm::vec2 uv0 = glm::vec2(0.0f), glm::vec2 uv1 = glm::vec2(1.0f))
	{
		const glm::vec2 m = tam * 0.5f + glm::vec2(margen);
		const glm::vec2 l[4] = { { -m.x, -m.y }, { m.x, -m.y }, { m.x, m.y }, { -m.x, m.y } };
		const float ca = cosf(ang), sa = sinf(ang);
		glm::vec4 c[4];
		glm::vec2 uv[4];
		for (int i = 0; i < 4; i++) {
			const glm::vec2 q{ l[i].x * ca - l[i].y * sa, l[i].x * sa + l[i].y * ca };
			c[i] = recorte(centro + q);
			const glm::vec2 f = (l[i] + tam * 0.5f) / glm::max(tam, glm::vec2(1e-3f));
			uv[i] = glm::mix(uv0, uv1, f);
		}
		quad(c, l, uv, col, col2, glm::vec4(tam * 0.5f, radio, (float)tipo), extra);
	}

	void caja(float x, float y, float w, float h, float margen, Tipo tipo, glm::vec4 col, glm::vec4 col2, float radio, glm::vec4 extra)
	{
		rect(glm::vec2(x + w * 0.5f, y + h * 0.5f), glm::vec2(w, h), 0.0f, margen, tipo, col, col2, radio, extra);
	}

	// rectangulo con inclinacion 3D (perspectiva real: w varia por esquina)
	void rectInclinado(glm::vec2 centro, glm::vec2 tam, float angY, float angX, float margen, Tipo tipo, glm::vec4 col, glm::vec4 col2,
	                   float radio, glm::vec4 extra, glm::vec2 uv0 = glm::vec2(0.0f), glm::vec2 uv1 = glm::vec2(1.0f))
	{
		const glm::vec2 m = tam * 0.5f + glm::vec2(margen);
		const glm::vec2 l[4] = { { -m.x, -m.y }, { m.x, -m.y }, { m.x, m.y }, { -m.x, m.y } };
		const float f = 1600.0f * s;
		const glm::mat3 giro = glm::mat3(glm::rotate(glm::mat4(1.0f), angY, glm::vec3(0, 1, 0)) * glm::rotate(glm::mat4(1.0f), angX, glm::vec3(1, 0, 0)));
		glm::vec4 c[4];
		glm::vec2 uv[4];
		for (int i = 0; i < 4; i++) {
			const glm::vec3 q = giro * glm::vec3(l[i], 0.0f);
			const float w = (f + q.z) / f;
			const glm::vec4 r = recorte(centro + glm::vec2(q) / w);
			c[i] = glm::vec4(r.x * w, r.y * w, 0.0f, w);
			uv[i] = glm::mix(uv0, uv1, (l[i] + tam * 0.5f) / glm::max(tam, glm::vec2(1e-3f)));
		}
		quad(c, l, uv, col, col2, glm::vec4(tam * 0.5f, radio, (float)tipo), extra);
	}

	// rectangulo tendido sobre el tablero (y = altura), local en cm
	void rectSuelo(glm::vec3 centro, glm::vec2 tam, float margen, Tipo tipo, glm::vec4 col, glm::vec4 col2, float radio, glm::vec4 extra)
	{
		const glm::vec2 m = tam * 0.5f + glm::vec2(margen);
		const glm::vec2 l[4] = { { -m.x, -m.y }, { m.x, -m.y }, { m.x, m.y }, { -m.x, m.y } };
		glm::vec4 c[4];
		glm::vec2 uv[4];
		glm::vec2 lc[4];
		for (int i = 0; i < 4; i++) {
			c[i] = proyectar(centro + glm::vec3(l[i].x, 0.0f, l[i].y));
			uv[i] = (l[i] + tam * 0.5f) / glm::max(tam, glm::vec2(1e-3f));
			lc[i] = l[i] * 100.0f;
		}
		quad(c, lc, uv, col, col2, glm::vec4(tam * 50.0f, radio, (float)tipo), extra);
	}

	float medir(int fu, const std::string& txt, float tam, float espaciado = 0.0f) const
	{
		const Fuente& f = fuentes[fu];
		const float k = tam / TAM_BASE;
		float x = 0.0f;
		const std::vector<int> cps = utf8(txt);
		for (size_t i = 0; i < cps.size(); i++) {
			auto g = f.glifos.find(cps[i]);
			if (g == f.glifos.end()) continue;
			x += g->second.avance * k + espaciado * s;
			if (i + 1 < cps.size()) {
				x += stbtt_GetCodepointKernAdvance(&f.info, cps[i], cps[i + 1]) * f.escala * k;
			}
		}
		return x;
	}

	// texto con la base en y; alin 0 izq, 1 centro, 2 der; extra: halo, contorno, degradado
	float texto(int fu, const std::string& txt, float x, float y, float tam, glm::vec4 col, glm::vec4 col2 = NADA,
	            glm::vec3 ex = glm::vec3(0.0f), int alin = 0, float espaciado = 0.0f)
	{
		usar(setAtlas, false);
		const Fuente& f = fuentes[fu];
		const float k = tam / TAM_BASE;
		const float ancho = medir(fu, txt, tam, espaciado);
		if (alin == 1) x -= ancho * 0.5f;
		if (alin == 2) x -= ancho;
		const std::vector<int> cps = utf8(txt);
		const float arriba = y - tam * 0.72f;
		for (size_t i = 0; i < cps.size(); i++) {
			auto it = f.glifos.find(cps[i]);
			if (it == f.glifos.end()) continue;
			const Glifo& g = it->second;
			if (g.w > 0.0f) {
				const float x0 = x + g.xoff * k, y0 = y + g.yoff * k, x1 = x0 + g.w * k, y1 = y0 + g.h * k;
				auto ly = [&](float py) { return (py - arriba) / (tam * 0.72f) * 2.0f - 1.0f; };
				const glm::vec4 c[4] = { recorte({ x0, y0 }), recorte({ x1, y0 }), recorte({ x1, y1 }), recorte({ x0, y1 }) };
				const glm::vec2 l[4] = { { 0, ly(y0) }, { 0, ly(y0) }, { 0, ly(y1) }, { 0, ly(y1) } };
				const glm::vec2 uv[4] = { { g.u0, g.v0 }, { g.u1, g.v0 }, { g.u1, g.v1 }, { g.u0, g.v1 } };
				quad(c, l, uv, col, col2, glm::vec4(0, 0, 0, (float)TEXTO), glm::vec4(ex, 0.0f));
			}
			x += g.avance * k + espaciado * s;
			if (i + 1 < cps.size()) {
				x += stbtt_GetCodepointKernAdvance(&f.info, cps[i], cps[i + 1]) * f.escala * k;
			}
		}
		return ancho;
	}

	// parrafo con cortes de linea por palabras; devuelve cuantas lineas uso
	int parrafo(int fu, const std::string& txt, float x, float y, float tam, float ancho, float interlinea, int maxLineas, glm::vec4 col)
	{
		std::vector<std::string> palabras;
		size_t a = 0, b;
		while ((b = txt.find(' ', a)) != std::string::npos) {
			palabras.push_back(txt.substr(a, b - a));
			a = b + 1;
		}
		palabras.push_back(txt.substr(a));
		std::string linea;
		int n = 0;
		for (size_t i = 0; i <= palabras.size(); i++) {
			const std::string prueba = i < palabras.size() ? (linea.empty() ? palabras[i] : linea + " " + palabras[i]) : linea;
			if (i == palabras.size() || (medir(fu, prueba, tam) > ancho && !linea.empty())) {
				if (n == maxLineas - 1 && i < palabras.size()) {
					linea += "…";
					texto(fu, linea, x, y + n * interlinea, tam, col);
					return n + 1;
				}
				texto(fu, linea, x, y + n * interlinea, tam, col);
				n++;
				linea = i < palabras.size() ? palabras[i] : "";
			} else {
				linea = prueba;
			}
		}
		return n;
	}

	// ------------------------------------------------------------------------------------------ puntero
	const Zona* zonaPorId(const std::string& id) const
	{
		for (const Zona& z : ZONAS) {
			if (id == z.id) return &z;
		}
		return nullptr;
	}

	glm::vec3 centroZona(int i) const { return glm::vec3(ZONAS[i].x * ESCALA, 0.0f, ZONAS[i].z * ESCALA); }

	// mano del jugador: centro, giro y escala de la carta k
	void cartaManoJ(int k, glm::vec2& c, float& ang, float& esc) const
	{
		const float cx = (CAMPO_X * s + W) * 0.5f;
		const float m = (NUM_MANO_J - 1) * 0.5f;
		const float d = (float)k - m;
		const float e = elevaJ[k];
		c = glm::vec2(cx + d * 128.0f * s, H - (52.0f + 34.0f * focoJ) * s + d * d * 4.0f * s - e * 70.0f * s);
		ang = glm::radians(d * 3.2f) * (1.0f - e);
		esc = 1.0f + 0.14f * e;
	}

	void cartaManoR(int k, glm::vec2& c, float& ang, float& esc) const
	{
		const float cx = (CAMPO_X * s + W) * 0.5f;
		const float m = (NUM_MANO_R - 1) * 0.5f;
		const float d = (float)k - m;
		const float e = elevaR[k];
		c = glm::vec2(cx - d * 100.0f * s, (14.0f + 26.0f * focoR) * s - d * d * 3.0f * s + e * 40.0f * s);
		ang = glm::radians(180.0f - d * 3.0f) ;
		esc = 1.0f + 0.1f * e;
	}

	std::string idObjetivo(const Objetivo& o) const
	{
		if (o.clase == MANO_J) return "jugador_mano_" + std::to_string(o.indice);
		if (o.clase == MANO_R) return "rival_mano_" + std::to_string(o.indice);
		return ZONAS[o.indice].id;
	}

	void construirObjetivos()
	{
		objetivos.clear();
		for (int k = 0; k < NUM_MANO_J; k++) {
			glm::vec2 c; float a, e;
			cartaManoJ(k, c, a, e);
			objetivos.push_back({ MANO_J, k, glm::vec2(c.x, H - 60.0f * s) });
		}
		for (int k = 0; k < NUM_MANO_R; k++) {
			glm::vec2 c; float a, e;
			cartaManoR(k, c, a, e);
			objetivos.push_back({ MANO_R, k, glm::vec2(c.x, 40.0f * s) });
		}
		for (int i = 0; i < (int)NUM_ZONAS; i++) {
			objetivos.push_back({ EN_ZONA, i, aPantalla(proyectar(centroZona(i))) });
		}
		seleccion = 0;
		for (size_t i = 0; i < objetivos.size(); i++) {
			if (idObjetivo(objetivos[i]) == pedido) {
				seleccion = (int)i;
			}
		}
	}

	// navegacion espacial: el objetivo mas cercano en la direccion pedida (penaliza el desvio)
	void mover(glm::vec2 dir)
	{
		if (objetivos.empty()) return;
		const glm::vec2 p = objetivos[seleccion].pantalla;
		float mejor = 1e9f;
		int elegido = -1;
		for (size_t i = 0; i < objetivos.size(); i++) {
			if ((int)i == seleccion) continue;
			const glm::vec2 d = objetivos[i].pantalla - p;
			const float avance = glm::dot(d, dir);
			if (avance < 12.0f * s) continue;
			const float desvio = fabsf(d.x * dir.y - d.y * dir.x);
			const float puntos = avance + desvio * 2.2f;
			if (puntos < mejor) {
				mejor = puntos;
				elegido = (int)i;
			}
		}
		if (elegido >= 0) {
			pedido = idObjetivo(objetivos[elegido]);
			seleccion = elegido;
		}
	}

	// ------------------------------------------------------------------------------------------ animacion
	void animarVidas(float dt)
	{
		for (Vida* vi : { &vidaJ, &vidaR }) {
			vi->tGolpe += dt;
			// los numeros ruedan hacia el valor nuevo (rapido al principio, frenando al final)
			const float dif = (float)vi->valor - vi->mostrado;
			vi->mostrado += dif * (1.0f - expf(-dt * 3.2f));
			if (fabsf(dif) < 1.0f) vi->mostrado = (float)vi->valor;
			// la estela del danno espera 0.7 s y se vacia
			if (vi->tGolpe > 0.7f) {
				vi->fantasma += (vi->mostrado - vi->fantasma) * (1.0f - expf(-dt * 2.6f));
			}
			if (vi->fantasma < vi->mostrado) vi->fantasma = vi->mostrado;
		}
	}

	void chispa(glm::vec2 pos, glm::vec2 vel, float dur, float tam, glm::vec3 col, float cruz = 0.0f)
	{
		if (chispas.size() < 900) {
			chispas.push_back({ pos, vel, 0.0f, dur, tam, col, cruz });
		}
	}

	void animarChispas(float dt)
	{
		for (Chispa& c : chispas) {
			c.vida += dt;
			c.pos += c.vel * dt;
			c.vel *= expf(-dt * 1.6f);
			c.vel.y -= 18.0f * dt * s;
		}
		chispas.erase(std::remove_if(chispas.begin(), chispas.end(), [](const Chispa& c) { return c.vida >= c.dur; }), chispas.end());
	}

	void estallar(bool rival)
	{
		const glm::vec2 c(COL_X * s + 150.0f * s, (rival ? 80.0f : 1004.0f) * s);
		const glm::vec3 col = rival ? glm::vec3(1.0f, 0.4f, 0.35f) : glm::vec3(1.0f, 0.5f, 0.3f);
		for (int i = 0; i < 70; i++) {
			const float a = azar() * 6.2832f;
			const float r = (60.0f + 260.0f * azar()) * s;
			chispa(c + glm::vec2(azar() - 0.5f, azar() - 0.5f) * glm::vec2(200.0f, 40.0f) * s, glm::vec2(cosf(a), sinf(a) * 0.6f) * r,
			       0.5f + 0.8f * azar(), (2.0f + 4.0f * azar()) * s, glm::mix(col, glm::vec3(1.0f, 0.9f, 0.6f), azar()), azar() > 0.7f ? 1.0f : 0.0f);
		}
	}

	// ------------------------------------------------------------------------------------------ armar el cuadro
	void construir()
	{
		dibujarTablero3D();
		dibujarEtiquetasTablero();
		dibujarManoRival();
		dibujarManoJugador();
		dibujarColumna();
		dibujarFases();
		dibujarMarco();
		dibujarChispas();
	}

	// lo que hay en una zona del duelo de prueba
	const Ocupa* ocupante(const char* zona) const
	{
		for (const Ocupa& o : CAMPO_PRUEBA) {
			if (strcmp(o.zona, zona) == 0) return &o;
		}
		return nullptr;
	}

	glm::vec4 colorZona(const std::string& tipo) const
	{
		if (tipo == "fusion") return glm::vec4(0.72f, 0.42f, 1.0f, 1.0f);
		if (tipo == "cementerio") return glm::vec4(0.62f, 0.75f, 0.95f, 1.0f);
		if (tipo == "mazo") return CIAN;
		return glm::vec4(0.45f, 1.0f, 0.75f, 1.0f);
	}

	void dibujarTablero3D()
	{
		usar(setAtlas, true);
		// fondo: un quad a toda pantalla en la profundidad maxima (z = w): solo pinta donde la escena no dibujo
		{
			const glm::vec2 m(W * 0.5f, H * 0.5f);
			const glm::vec4 c[4] = { { -1, -1, 1, 1 }, { 1, -1, 1, 1 }, { 1, 1, 1, 1 }, { -1, 1, 1, 1 } };
			const glm::vec2 l[4] = { { -m.x, -m.y }, { m.x, -m.y }, { m.x, m.y }, { -m.x, m.y } };
			const glm::vec2 uv[4] = {};
			quad(c, l, uv, NADA, NADA, glm::vec4(m, 0.0f, (float)FONDO), glm::vec4(0.0f));
		}
		// marcas animadas de las zonas especiales (fusion, cementerio, mazo, campo)
		for (int i = 0; i < (int)NUM_ZONAS; i++) {
			const std::string tipo = ZONAS[i].tipo;
			if (tipo == "monstruo" || tipo == "magia") continue;
			const glm::vec4 c = colorZona(tipo);
			rectSuelo(centroZona(i) + glm::vec3(0.0f, 0.02f, 0.0f), glm::vec2(ZONA_ANCHO, ZONA_ALTO) * 1.04f, 0.25f, ZONA, c,
			          glm::vec4(glm::vec3(c) * 0.25f, 1.0f), 10.0f, glm::vec4(6.0f, tipo == "mazo" ? 0.6f : 0.35f, 0.85f, 0.0f));
		}
		// pilas de los mazos: cantos apilados y el dorso propio arriba
		for (int lado = 0; lado < 2; lado++) {
			const Zona* z = zonaPorId(lado ? "rival_mazo" : "jugador_mazo");
			const int n = lado ? mazoR : mazoJ;
			const glm::vec3 c(z->x * ESCALA, 0.0f, z->z * ESCALA);
			const float alto = 0.016f * n;
			const glm::vec2 m(CARTA_ANCHO * 0.5f, CARTA_ALTO * 0.5f);
			const glm::vec3 esq[4] = { c + glm::vec3(-m.x, 0, -m.y), c + glm::vec3(m.x, 0, -m.y), c + glm::vec3(m.x, 0, m.y), c + glm::vec3(-m.x, 0, m.y) };
			const glm::vec4 canto(0.82f, 0.86f, 0.95f, 1.0f), sombra(0.12f, 0.14f, 0.22f, 1.0f);
			for (int k = 0; k < 4; k++) {
				const glm::vec3 a = esq[k], b = esq[(k + 1) % 4];
				const glm::vec4 cc[4] = { proyectar(a + glm::vec3(0, alto, 0)), proyectar(b + glm::vec3(0, alto, 0)), proyectar(b), proyectar(a) };
				const glm::vec2 l[4] = { {}, {}, {}, {} };
				const glm::vec2 uv[4] = { { 0, 1 }, { 1, 1 }, { 1, 0 }, { 0, 0 } };
				quad(cc, l, uv, canto, sombra, glm::vec4(0, 0, 0, (float)LADO_MAZO), glm::vec4((float)n * 0.5f, 0, 0, 0));
			}
			rectSuelo(c + glm::vec3(0.0f, alto + 0.002f, 0.0f), glm::vec2(CARTA_ANCHO, CARTA_ALTO), 0.0f, DORSO,
			          lado ? CARMESI : CIAN, ORO, 6.0f, glm::vec4(lado * 2.0f, 0, 0, 0));
		}
		// el recuadro dorado sobre el tablero (con profundidad: los monstruos lo tapan)
		if (marcoEn3D && llegada > 0.9f) {
			marcoQuad(true);
		}
	}

	// etiqueta flotante de una zona: una pastilla de vidrio con el nombre y el numero en una sola linea
	void etiqueta(glm::vec2 p, const std::string& titulo, const std::string& numero, glm::vec4 col)
	{
		const float tt = 14.0f * s, tn = 20.0f * s;
		const float wt = medir(F_TITULO, titulo, tt, 2.0f), wn = medir(F_NUMEROS, numero, tn);
		const float w = wt + wn + 34.0f * s, h = 30.0f * s;
		const float x = p.x - w * 0.5f, y = p.y - h;
		caja(x, y, w, h, 10.0f * s, PANEL, glm::vec4(0.02f, 0.03f, 0.06f, 0.7f), col, 15.0f * s, glm::vec4(1.2f * s, 0.8f, 0.0f, 8.0f * s));
		texto(F_TITULO, titulo, x + 13.0f * s, y + 20.0f * s, tt, glm::vec4(glm::vec3(col), 1.0f), NADA, glm::vec3(0.0f), 0, 2.0f);
		texto(F_NUMEROS, numero, x + w - 12.0f * s, y + 22.0f * s, tn, BLANCO, col, glm::vec3(0.5f, 0.0f, 0.0f), 2);
	}

	void dibujarEtiquetasTablero()
	{
		for (int i = 0; i < (int)NUM_ZONAS; i++) {
			const std::string tipo = ZONAS[i].tipo;
			if (tipo != "mazo" && tipo != "fusion" && tipo != "cementerio") continue;
			const bool rival = strncmp(ZONAS[i].id, "rival", 5) == 0;
			const glm::vec4 c = colorZona(tipo);
			// la etiqueta flota sobre el borde lejano de la zona (o sobre la pila del mazo)
			const float alto = tipo == "mazo" ? 0.016f * (rival ? mazoR : mazoJ) + 0.25f : 0.25f;
			const glm::vec2 p = aPantalla(proyectar(centroZona(i) + glm::vec3(0.0f, alto, -ZONA_ALTO * 0.5f)));
			std::string titulo, numero;
			if (tipo == "mazo") {
				titulo = "MAZO";
				numero = std::to_string(rival ? mazoR : mazoJ);
			} else if (tipo == "fusion") {
				titulo = "FUSIÓN";
				numero = rival ? "0" : "1";
			} else {
				titulo = "CEMENTERIO";
				numero = std::to_string(rival ? cementerioR : cementerioJ);
			}
			etiqueta(p, titulo, numero, c);
		}
	}

	void dibujarManoRival()
	{
		for (int k = 0; k < NUM_MANO_R; k++) {
			glm::vec2 c; float a, e;
			cartaManoR(k, c, a, e);
			const glm::vec2 tam = glm::vec2(120.0f, 174.0f) * s * e;
			rect(c, tam, a, 18.0f * s, PANEL, glm::vec4(0, 0, 0, 0.5f), NADA, 9.0f * s, glm::vec4(0, 0, 0, 12.0f * s));
			rect(c, tam, a, 0.0f, DORSO, CARMESI, ORO, 9.0f * s, glm::vec4((float)k, 0, 0, 0));
		}
	}

	void dibujarManoJugador()
	{
		int sel = -1;
		if (!objetivos.empty() && objetivos[seleccion].clase == MANO_J) sel = objetivos[seleccion].indice;
		auto una = [&](int k) {
			const int ci = buscarCarta(MANO_JUGADOR[k]);
			glm::vec2 c; float a, e;
			cartaManoJ(k, c, a, e);
			const glm::vec2 tam = glm::vec2(150.0f, 218.0f) * s * e;
			usar(setAtlas, false);
			rect(c, tam, a, 22.0f * s, PANEL, glm::vec4(0, 0, 0, 0.55f), NADA, 10.0f * s, glm::vec4(0, 0, 0, 14.0f * s));
			if (ci >= 0 && cartas[ci].lista) {
				usar(cartas[ci].setMini, false);
				const float u = 0.5f / cartas[ci].mini.width, vv = 0.5f / cartas[ci].mini.height;
				rect(c, tam, a, 0.0f, IMAGEN, glm::vec4(glm::vec3(k == sel ? 1.08f : 0.92f), 1.0f), glm::vec4(0.6f, 0.8f, 1.0f, 1.0f), 8.0f * s,
				     glm::vec4(k == sel ? 0.55f : 0.15f, k == sel ? 1.0f : 0.25f, k * 0.17f, 0), glm::vec2(u, vv), glm::vec2(1.0f - u, 1.0f - vv));
			} else {
				rect(c, tam, a, 0.0f, DORSO, CIAN, ORO, 8.0f * s, glm::vec4((float)k, 0, 0, 0));
			}
		};
		for (int k = 0; k < NUM_MANO_J; k++) {
			if (k != sel) una(k);
		}
		if (sel >= 0) una(sel);
	}

	// panel de LP: etiqueta, numero que rueda con degradado y halo, barra con estela de danno
	void panelLP(float y, bool rival)
	{
		const Vida& vi = rival ? vidaR : vidaJ;
		const glm::vec4 acento = rival ? CARMESI : CIAN;
		const float golpe = expf(-vi.tGolpe * 2.2f);
		const float sac = golpe * 4.0f * s;
		const float x = COL_X * s + sinf(vi.tGolpe * 60.0f) * sac;
		const float w = COL_ANCHO * s, h = 112.0f * s;
		const glm::vec4 vid = glm::mix(VIDRIO, glm::vec4(0.35f, 0.04f, 0.06f, 0.8f), golpe * 0.8f);
		caja(x, y, w, h, 24.0f * s, PANEL, vid, glm::mix(acento, glm::vec4(1, 0.3f, 0.3f, 1), golpe), 14.0f * s,
		     glm::vec4(1.4f * s, 0.9f, rival ? -0.11f : 0.11f, 16.0f * s));
		// etiqueta del lado
		texto(F_TITULO, rival ? "RIVAL" : "JUGADOR", x + 22.0f * s, y + 30.0f * s, 19.0f * s, acento, NADA, glm::vec3(0.0f), 0, 3.0f);
		rect(glm::vec2(x + w - 46.0f * s, y + 24.0f * s), glm::vec2(48.0f, 22.0f) * s, 0.0f, 6.0f * s, PANEL, glm::vec4(glm::vec3(acento) * 0.25f, 0.9f),
		     acento, 11.0f * s, glm::vec4(1.0f * s, 1.0f, 0.0f, 0.0f));
		texto(F_NUMEROS, "LP", x + w - 46.0f * s, y + 31.0f * s, 15.0f * s, BLANCO, NADA, glm::vec3(0.0f), 1, 1.0f);
		// numero
		char num[16];
		snprintf(num, sizeof(num), "%d", (int)roundf(vi.mostrado));
		const glm::vec4 arriba = glm::mix(BLANCO, glm::vec4(1.0f, 0.55f, 0.5f, 1.0f), golpe);
		const glm::vec4 abajo = glm::mix(acento, glm::vec4(1.0f, 0.2f, 0.2f, 1.0f), golpe);
		texto(F_NUMEROS, num, x + 20.0f * s, y + 84.0f * s, 52.0f * s, arriba, abajo, glm::vec3(0.55f + 0.25f * golpe, 0.0f, 0.85f), 0, 2.0f);
		// danno flotante
		if (vi.tGolpe < 1.6f && vi.ultimoDanio > 0) {
			char d[16];
			snprintf(d, sizeof(d), "-%d", vi.ultimoDanio);
			const float a = 1.0f - suave(1.0f, 1.6f, vi.tGolpe);
			texto(F_NUMEROS, d, x + w - 24.0f * s, y + (80.0f - 30.0f * suave(0.0f, 1.6f, vi.tGolpe)) * s, 26.0f * s,
			      glm::vec4(1.0f, 0.45f, 0.4f, a), glm::vec4(1.0f, 0.2f, 0.1f, a), glm::vec3(0.9f, 0.1f, 0.0f), 2);
		}
		// barra
		const float bx = x + 20.0f * s, bw = w - 40.0f * s;
		caja(bx, y + 94.0f * s, bw, 9.0f * s, 8.0f * s, BARRA, glm::vec4(glm::vec3(acento) * 0.75f, 1.0f), glm::mix(acento, BLANCO, 0.35f), 4.5f * s,
		     glm::vec4(glm::clamp(vi.mostrado / 8000.0f, 0.0f, 1.0f), glm::clamp(vi.fantasma / 8000.0f, 0.0f, 1.0f), golpe, 0.0f));
	}

	static float suave(float a, float b, float x)
	{
		const float u = glm::clamp((x - a) / (b - a), 0.0f, 1.0f);
		return u * u * (3.0f - 2.0f * u);
	}

	struct Contenido { int carta{ -1 }; bool dorso{ false }; bool rival{ false }; std::string titulo, subtitulo, texto; glm::vec4 color{ CIAN }; };

	Contenido contenidoDe(int sel) const
	{
		Contenido r;
		if (sel < 0 || sel >= (int)objetivos.size()) return r;
		const Objetivo& o = objetivos[sel];
		if (o.clase == MANO_J) {
			r.carta = buscarCarta(MANO_JUGADOR[o.indice]);
			return r;
		}
		if (o.clase == MANO_R) {
			r.dorso = true;
			r.rival = true;
			r.titulo = "MANO DEL RIVAL";
			r.subtitulo = std::to_string(NUM_MANO_R) + " cartas ocultas";
			r.texto = "El rival guarda estas cartas boca abajo. Su contenido se revelara cuando las juegue.";
			r.color = CARMESI;
			return r;
		}
		const Zona& z = ZONAS[o.indice];
		const bool rival = strncmp(z.id, "rival", 5) == 0;
		const std::string tipo = z.tipo;
		r.rival = rival;
		r.color = rival ? CARMESI : CIAN;
		const Ocupa* oc = ocupante(z.id);
		if (tipo == "mazo") {
			const int n = rival ? mazoR : mazoJ;
			r.dorso = true;
			r.titulo = rival ? "MAZO DEL RIVAL" : "TU MAZO";
			r.subtitulo = std::to_string(n) + " cartas restantes";
			r.texto = "Al comenzar cada turno se roba la carta de arriba. Si no quedan cartas para robar, el duelo se pierde.";
			return r;
		}
		if (tipo == "fusion") {
			if (oc && oc->carta[0]) {
				r.carta = buscarCarta(oc->carta);
				return r;
			}
			r.titulo = "ZONA DE FUSIÓN";
			r.subtitulo = "Sin monstruos de fusión";
			r.texto = "Aqui esperan los monstruos de fusion hasta que se invoquen con Polimerizacion.";
			r.color = colorZona("fusion");
			return r;
		}
		if (tipo == "cementerio") {
			r.titulo = rival ? "CEMENTERIO DEL RIVAL" : "TU CEMENTERIO";
			r.subtitulo = "Vacío";
			r.texto = "Las cartas destruidas, usadas o descartadas terminan aqui, boca arriba.";
			r.color = colorZona("cementerio");
			return r;
		}
		if (oc) {
			if (oc->bocaAbajo || !oc->carta[0]) {
				r.dorso = true;
				r.titulo = "CARTA BOCA ABAJO";
				r.subtitulo = rival ? "Colocada por el rival" : "Colocada por ti";
				r.texto = rival ? "Una magia o trampa oculta. Cuidado al atacar." : "Tu carta colocada, lista para activarse.";
				return r;
			}
			r.carta = buscarCarta(oc->carta);
			return r;
		}
		r.titulo = tipo == "monstruo" ? "ZONA DE MONSTRUO" : tipo == "magia" ? "ZONA DE MAGIA Y TRAMPA" : "ZONA DE CAMPO";
		r.subtitulo = "Vacía";
		r.texto = rival ? "Zona del rival sin cartas." : "Puedes colocar una carta aqui.";
		return r;
	}

	glm::vec4 colorAtributo(const std::string& a) const
	{
		if (a == "OSCURIDAD") return glm::vec4(0.70f, 0.42f, 1.0f, 1.0f);
		if (a == "LUZ") return glm::vec4(1.0f, 0.90f, 0.45f, 1.0f);
		if (a == "TIERRA") return glm::vec4(0.90f, 0.62f, 0.32f, 1.0f);
		if (a == "AGUA") return glm::vec4(0.35f, 0.65f, 1.0f, 1.0f);
		if (a == "FUEGO") return glm::vec4(1.0f, 0.42f, 0.22f, 1.0f);
		if (a == "VIENTO") return glm::vec4(0.45f, 1.0f, 0.62f, 1.0f);
		if (a == "MAGIA") return glm::vec4(0.25f, 0.95f, 0.75f, 1.0f);
		if (a == "TRAMPA") return glm::vec4(1.0f, 0.38f, 0.72f, 1.0f);
		return GRIS;
	}

	void dibujarColumna()
	{
		panelLP(MARGEN * s, true);
		panelLP((1080.0f - MARGEN - 112.0f) * s, false);
		// visor
		const float x = COL_X * s, y = 148.0f * s, w = COL_ANCHO * s, h = 784.0f * s;
		const Contenido c = contenidoDe(selVisor >= 0 ? selVisor : seleccion);
		const CartaUI* k = c.carta >= 0 ? &cartas[c.carta] : nullptr;
		const glm::vec4 acento = k ? colorAtributo(k->atributo) : c.color;
		caja(x, y, w, h, 26.0f * s, PANEL, VIDRIO, glm::mix(CIAN, acento, 0.5f), 16.0f * s, glm::vec4(1.4f * s, 0.8f, 0.07f, 18.0f * s));
		// polvo de luz que sube dentro del visor
		if (azar() < dtCuadro * 9.0f) {
			chispa(glm::vec2(x + (30.0f + azar() * (COL_ANCHO - 60.0f)) * s, y + (440.0f + 40.0f * azar()) * s), glm::vec2(0.0f, -(20.0f + 30.0f * azar()) * s),
			       2.5f + 2.0f * azar(), (1.5f + 2.0f * azar()) * s, glm::vec3(acento) * 0.8f);
		}
		// carta: se inclina un poco en 3D y gira al cambiar
		const glm::vec2 centro(x + w * 0.5f, y + 233.0f * s);
		const glm::vec2 tam = glm::vec2(297.0f, 430.0f) * s;
		const float flip = giroVisor >= 0.0f ? (giroVisor < 0.5f ? giroVisor : giroVisor - 1.0f) * glm::pi<float>() : 0.0f;
		const float angY = glm::radians(7.0f) * sinf(t * 0.6f) + flip;
		const float angX = glm::radians(3.5f) * sinf(t * 0.45f + 1.0f);
		usar(setAtlas, false);
		rect(centro, tam * 1.35f, 0.0f, 0.0f, PARTICULA, glm::vec4(glm::vec3(acento) * 0.22f, 1.0f), NADA, 0.0f, glm::vec4(0.0f));
		rectInclinado(centro + glm::vec2(0.0f, 10.0f * s), tam, angY, angX, 26.0f * s, PANEL, glm::vec4(0, 0, 0, 0.7f), NADA, 12.0f * s, glm::vec4(0, 0, 0, 18.0f * s));
		if (k && k->lista) {
			usar(k->setCara, false);
			const float u = 0.5f / k->cara.width, vv = 0.5f / k->cara.height;
			rectInclinado(centro, tam, angY, angX, 0.0f, IMAGEN, glm::vec4(1.0f), acento, 10.0f * s,
			              glm::vec4(0.55f, 1.0f, (float)c.carta * 0.13f, 0.0f), glm::vec2(u, vv), glm::vec2(1.0f - u, 1.0f - vv));
		} else if (c.dorso) {
			rectInclinado(centro, tam, angY, angX, 0.0f, DORSO, c.rival ? CARMESI : CIAN, ORO, 10.0f * s, glm::vec4(0.0f));
		} else {
			// zona vacia: holograma del contorno
			rectInclinado(centro, tam * 0.92f, angY, angX, 20.0f * s, ZONA, acento, acento, 12.0f * s, glm::vec4(2.5f * s, 0.5f, 1.0f, 0.0f));
		}
		usar(setAtlas, false);
		// escaneo holografico: una linea de luz barre la carta recien elegida
		if (tTexto < 0.6f) {
			const float u = tTexto / 0.6f;
			const float yy = centro.y - tam.y * 0.5f + tam.y * u;
			rect(glm::vec2(centro.x, yy), glm::vec2(tam.x * 1.15f, 4.0f * s), 0.0f, 10.0f * s, LINEA, glm::vec4(glm::vec3(acento) * 1.3f, 1.0f - u), NADA, 0.0f,
			     glm::vec4(0.0f));
		}
		// texto (entra deslizando)
		const float a = suave(0.0f, 0.28f, tTexto);
		const float dx = (1.0f - a) * 14.0f * s;
		const float tx = x + 24.0f * s + dx, tw = w - 48.0f * s;
		float ty = y + 498.0f * s;
		auto alfa = [&](glm::vec4 col) { return glm::vec4(glm::vec3(col), col.a * a); };
		if (k) {
			std::string nombre = k->nombre;
			float tn = 33.0f * s;
			while (medir(F_TITULO, nombre, tn) > tw && tn > 18.0f * s) tn -= 1.0f * s;
			texto(F_TITULO, nombre, tx, ty, tn, alfa(BLANCO), alfa(acento), glm::vec3(0.35f, 0.0f, 0.0f));
			ty += 30.0f * s;
			const bool monstruo = k->clase != "magia" && k->clase != "trampa";
			if (monstruo) {
				for (int i = 0; i < k->nivel; i++) {
					rect(glm::vec2(tx + (10.0f + i * 23.0f) * s, ty - 6.0f * s), glm::vec2(11.0f * s), 0.0f, 10.0f * s, ESTRELLA,
					     alfa(glm::vec4(1.0f, 0.86f, 0.35f, 1.0f)), alfa(glm::vec4(1.0f, 0.55f, 0.15f, 1.0f)), 0.0f, glm::vec4(0.8f, 0, 0, 0));
				}
			}
			// atributo: ficha y nombre (a la derecha)
			const float aw = medir(F_TITULO, k->atributo, 17.0f * s, 2.0f);
			rect(glm::vec2(tx + tw - aw - 18.0f * s, ty - 6.0f * s), glm::vec2(20.0f * s), 0.0f, 10.0f * s, ORBE, alfa(acento),
			     glm::vec4(glm::vec3(acento) * 0.35f, 1.0f), 0.0f, glm::vec4(0.8f, 0.9f, 0, 0));
			texto(F_TITULO, k->atributo, tx + tw, ty, 17.0f * s, alfa(acento), NADA, glm::vec3(0.0f), 2, 2.0f);
			ty += 32.0f * s;
			std::string tipo = "[ " + k->tipo;
			if (k->clase == "efecto") tipo += " / Efecto";
			if (k->clase == "fusion") tipo += " / Fusión";
			tipo += " ]";
			texto(F_TEXTO, tipo, tx, ty, 23.0f * s, alfa(glm::vec4(0.72f, 0.86f, 1.0f, 1.0f)));
			if (monstruo) {
				ty += 38.0f * s;
				texto(F_TITULO, "ATK", tx, ty - 3.0f * s, 17.0f * s, alfa(GRIS), NADA, glm::vec3(0.0f), 0, 2.0f);
				texto(F_NUMEROS, std::to_string(k->atk), tx + 40.0f * s, ty, 28.0f * s, alfa(glm::vec4(1.0f, 0.93f, 0.7f, 1.0f)), alfa(ORO), glm::vec3(0.45f, 0.0f, 0.8f));
				texto(F_TITULO, "DEF", tx + tw * 0.52f, ty - 3.0f * s, 17.0f * s, alfa(GRIS), NADA, glm::vec3(0.0f), 0, 2.0f);
				texto(F_NUMEROS, std::to_string(k->def), tx + tw * 0.52f + 42.0f * s, ty, 28.0f * s, alfa(glm::vec4(0.8f, 0.95f, 1.0f, 1.0f)), alfa(CIAN), glm::vec3(0.45f, 0.0f, 0.8f));
			}
			ty += 22.0f * s;
			rect(glm::vec2(x + w * 0.5f, ty), glm::vec2(tw, 3.0f * s), 0.0f, 6.0f * s, LINEA, alfa(acento), NADA, 0.0f, glm::vec4(2.0f, 0.3f, 0, 0));
			ty += 30.0f * s;
			parrafo(F_TEXTO, k->desc, tx, ty, 23.0f * s, tw, 27.0f * s, (int)((y + h - 18.0f * s - ty) / (27.0f * s)) + 1, alfa(glm::vec4(0.82f, 0.86f, 0.93f, 1.0f)));
		} else {
			texto(F_TITULO, c.titulo, tx, ty, 28.0f * s, alfa(BLANCO), alfa(c.color), glm::vec3(0.35f, 0.0f, 0.0f));
			ty += 34.0f * s;
			texto(F_TEXTO, c.subtitulo, tx, ty, 22.0f * s, alfa(c.color));
			ty += 22.0f * s;
			rect(glm::vec2(x + w * 0.5f, ty), glm::vec2(tw, 3.0f * s), 0.0f, 6.0f * s, LINEA, alfa(c.color), NADA, 0.0f, glm::vec4(2.0f, 0.3f, 0, 0));
			ty += 32.0f * s;
			parrafo(F_TEXTO, c.texto, tx, ty, 23.0f * s, tw, 27.0f * s, 8, alfa(glm::vec4(0.82f, 0.86f, 0.93f, 1.0f)));
		}
	}

	void dibujarFases()
	{
		const float cx = (FASES_X + FASES_ANCHO * 0.5f) * s;
		const float paso = 82.0f * s;
		const float y0 = 540.0f * s - paso * 2.5f;
		// riel vertical de luz
		usar(setAtlas, false);
		rect(glm::vec2(cx, 540.0f * s), glm::vec2(paso * 5.6f, 2.0f * s), glm::half_pi<float>(), 8.0f * s, LINEA, glm::vec4(0.35f, 0.75f, 1.0f, 0.55f),
		     NADA, 0.0f, glm::vec4(3.0f, 0.0f, 0, 0));
		texto(F_TITULO, "FASE", cx, y0 - 76.0f * s, 14.0f * s, GRIS, NADA, glm::vec3(0.0f), 1, 3.0f);
		texto(F_TITULO, NOMBRE_FASE[fase], cx, y0 - 52.0f * s, 17.0f * s, ORO, NADA, glm::vec3(0.5f, 0.0f, 0.0f), 1, 1.5f);
		for (int i = 0; i < 6; i++) {
			const float y = y0 + i * paso;
			const bool activa = i == fase;
			const float pulso = 0.8f + 0.2f * sinf(t * 4.0f);
			if (activa) {
				rect(glm::vec2(cx, y), glm::vec2(70.0f * s), 0.0f, 30.0f * s, PARTICULA, glm::vec4(glm::vec3(ORO) * 0.45f * pulso, 1.0f), NADA, 0.0f, glm::vec4(0.0f));
				rect(glm::vec2(cx, y), glm::vec2(58.0f * s), 0.0f, 22.0f * s, ORBE, ORO, glm::vec4(0.55f, 0.36f, 0.08f, 1.0f), 0.0f, glm::vec4(1.4f * pulso, 1.0f, 0, 0));
				rect(glm::vec2(cx, y), glm::vec2(62.0f * s), t * 0.8f, 12.0f * s, MARCO, ORO, ORO, 31.0f * s, glm::vec4(2.0f * s, 6.0f * s, 1.0f, 0.0f));
				texto(F_NUMEROS, FASES[i], cx, y + 7.5f * s, 19.0f * s, glm::vec4(1.0f, 0.98f, 0.9f, 1.0f), NADA, glm::vec3(0.0f, 0.12f, 0.0f), 1);
			} else {
				const bool pasada = i < fase;
				rect(glm::vec2(cx, y), glm::vec2(50.0f * s), 0.0f, 16.0f * s, ORBE, pasada ? glm::vec4(0.35f, 0.75f, 1.0f, 0.9f) : glm::vec4(0.4f, 0.5f, 0.65f, 0.8f),
				     glm::vec4(0.03f, 0.05f, 0.1f, 1.0f), 0.0f, glm::vec4(pasada ? 0.4f : 0.15f, 0.85f, 0, 0));
				texto(F_NUMEROS, FASES[i], cx, y + 6.5f * s, 16.0f * s, pasada ? glm::vec4(0.75f, 0.9f, 1.0f, 1.0f) : GRIS, NADA, glm::vec3(0.0f), 1);
			}
		}
	}

	// el recuadro dorado: metas segun lo elegido; las esquinas vuelan con resorte
	void metaMarco(std::array<glm::vec4, 4>& c, glm::vec4& forma, bool& en3D)
	{
		const Objetivo& o = objetivos[seleccion];
		en3D = false;
		if (o.clase == MANO_J || o.clase == MANO_R) {
			glm::vec2 cc; float a, e;
			glm::vec2 tam;
			if (o.clase == MANO_J) {
				cartaManoJ(o.indice, cc, a, e);
				tam = glm::vec2(150.0f, 218.0f) * s * e;
			} else {
				cartaManoR(o.indice, cc, a, e);
				tam = glm::vec2(120.0f, 174.0f) * s * e;
			}
			const glm::vec2 m = tam * 0.5f + glm::vec2(7.0f * s);
			const glm::vec2 l[4] = { { -m.x, -m.y }, { m.x, -m.y }, { m.x, m.y }, { -m.x, m.y } };
			for (int i = 0; i < 4; i++) {
				const glm::vec2 q{ l[i].x * cosf(a) - l[i].y * sinf(a), l[i].x * sinf(a) + l[i].y * cosf(a) };
				c[i] = recorte(cc + q);
			}
			forma = glm::vec4(m, 3.5f * s, 14.0f * s);
			return;
		}
		en3D = true;
		const glm::vec3 z = centroZona(o.indice) + glm::vec3(0.0f, 0.2f, 0.0f);
		const glm::vec2 m = glm::vec2(ZONA_ANCHO, ZONA_ALTO) * 0.56f;
		const glm::vec3 esq[4] = { z + glm::vec3(-m.x, 0, -m.y), z + glm::vec3(m.x, 0, -m.y), z + glm::vec3(m.x, 0, m.y), z + glm::vec3(-m.x, 0, m.y) };
		for (int i = 0; i < 4; i++) c[i] = proyectar(esq[i]);
		forma = glm::vec4(m * 100.0f, 12.0f, 26.0f);
	}

	void marcoQuad(bool en3D, float intensidad = 1.0f)
	{
		usar(setAtlas, en3D);
		// margen para el halo: se extiende la geometria (en el espacio de las esquinas) un 14%
		glm::vec4 c[4];
		const glm::vec4 centro = (marco[0] + marco[1] + marco[2] + marco[3]) * 0.25f;
		const float ext = 1.0f + 2.2f * formaMarco.w / glm::max(glm::min(formaMarco.x, formaMarco.y), 1.0f);
		for (int i = 0; i < 4; i++) c[i] = centro + (marco[i] - centro) * ext;
		const glm::vec2 m = glm::vec2(formaMarco) * ext;
		const glm::vec2 l[4] = { { -m.x, -m.y }, { m.x, -m.y }, { m.x, m.y }, { -m.x, m.y } };
		const glm::vec2 uv[4] = {};
		quad(c, l, uv, ORO, ORO, glm::vec4(formaMarco.x, formaMarco.y, formaMarco.z * 2.5f, (float)MARCO),
		     glm::vec4(formaMarco.z, formaMarco.w, intensidad, 0.0f));
	}

	void dibujarMarco()
	{
		if (objetivos.empty()) return;
		std::array<glm::vec4, 4> meta;
		glm::vec4 forma;
		bool en3D;
		metaMarco(meta, forma, en3D);
		if (!marcoListo) {
			marco = meta;
			formaMarco = forma;
			marcoListo = true;
		}
		const float dt = dtCuadro;
		float dist = 0.0f;
		for (int i = 0; i < 4; i++) {
			for (int k = 0; k < 4; k++) {
				resorte(marco[i][k], velMarco[i][k], meta[i][k], dt, 220.0f, 0.8f);
			}
			dist = glm::max(dist, glm::length(aPantalla(marco[i]) - aPantalla(meta[i])));
		}
		for (int k = 0; k < 4; k++) resorte(formaMarco[k], velForma[k], forma[k], dt, 220.0f, 0.8f);
		marcoEn3D = en3D;
		llegada = dist < 6.0f * s ? glm::min(1.0f, llegada + dt * 6.0f) : 0.0f;
		if (!(en3D && llegada > 0.9f)) {
			marcoQuad(false);
		} else {
			marcoQuad(false, 0.45f);   // lo que tapan los monstruos se ve como un fantasma (rayos X)
		}
		// chispas doradas que nacen en el borde
		glm::vec2 p[4];
		for (int i = 0; i < 4; i++) p[i] = aPantalla(marco[i]);
		emitir += dt * 34.0f;
		while (emitir >= 1.0f) {
			emitir -= 1.0f;
			const int lado = (int)(azar() * 4.0f) % 4;
			const glm::vec2 q = glm::mix(p[lado], p[(lado + 1) % 4], azar());
			chispa(q, glm::vec2((azar() - 0.5f) * 30.0f, -(30.0f + 50.0f * azar())) * s, 0.6f + 0.7f * azar(), (1.6f + 2.4f * azar()) * s,
			       glm::mix(glm::vec3(1.0f, 0.75f, 0.25f), glm::vec3(1.0f, 0.95f, 0.7f), azar()), azar() > 0.8f ? 1.0f : 0.0f);
		}
		// el puntero: flecha que flota sobre lo elegido
		glm::vec2 arriba = p[0];
		for (int i = 1; i < 4; i++) {
			if (p[i].y < arriba.y) arriba = p[i];
		}
		const glm::vec2 centro = (p[0] + p[1] + p[2] + p[3]) * 0.25f;
		const float bob = sinf(t * 4.0f) * 6.0f * s;
		const bool rivalMano = objetivos[seleccion].clase == MANO_R;
		const glm::vec2 punta = rivalMano ? glm::vec2(centro.x, glm::max(glm::max(p[0].y, p[1].y), glm::max(p[2].y, p[3].y)) + (30.0f * s - bob))
		                                  : glm::vec2(centro.x, arriba.y - 30.0f * s + bob);
		usar(setAtlas, false);
		rect(punta, glm::vec2(34.0f * s), rivalMano ? glm::pi<float>() : 0.0f, 14.0f * s, FLECHA, ORO, glm::vec4(1.0f, 0.97f, 0.8f, 1.0f), 0.0f, glm::vec4(0.0f));
	}

	void dibujarChispas()
	{
		usar(setAtlas, false);
		for (const Chispa& c : chispas) {
			if (c.tam <= 0.0f) continue;
			const float u = c.vida / c.dur;
			const float a = glm::min(u * 6.0f, 1.0f) * (1.0f - u) * (1.0f - u);
			const float tam = c.tam * (1.0f + c.cruz * 2.5f);
			rect(c.pos, glm::vec2(tam * 2.0f), 0.0f, tam * 2.0f, PARTICULA, glm::vec4(c.color * 1.4f, a), NADA, 0.0f, glm::vec4(c.cruz, 0, 0, 0));
		}
	}
};

}   // namespace interfaz
