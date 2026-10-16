/*
 * Yugi Reload - el tablero del duelo de prueba en PS5, con Vulkan (RADV de PS5_Vulkan).
 *
 * Hecho sobre el ejemplo inicial de PS5 Vulkan Template (Mihawk, MIT). Dibuja:
 *  - el tablero (tapete de Gemini y cartas), un solo glTF armado por Blender
 *    (herramientas/blender/escena_tablero.py -> models/yugi/tablero.glb);
 *  - cada monstruo 3D con su propio glTF (models/yugi/<carta>.glb) en la matriz que Blender
 *    escribe en escena.h, vivo: respira, flota y se balancea, con un contorno holografico;
 *    Kuriboh ademas mueve el pelo y da saltitos;
 *  - un ataque con personajes de verdad: el Mago Oscuro y el Guardian Celta son modelos de Meshy con
 *    esqueleto y animaciones (models/yugi/<carta>_anim.glb), con su arma en la mano derecha (baculo.glb,
 *    espada.glb). El Mago se gira hacia el Guardian, carga el hechizo y dispara un rayo azul desde la
 *    punta del baculo; el Guardian se cubre con la espada, no lo aguanta y cae de espaldas, se
 *    desintegra y vuelve a aparecer. Corte de camara, destello y temblor. Cada 12 s, o con la X;
 *  - sombras del sol (mapa de 4096 con PCF) y la camara de juego de Unreal (CamaraJuego).
 * Coordenadas: las del remake (x derecha, y arriba, z hacia el jugador; 1 unidad = 1 m).
 * OPTIONS muestra u oculta la ventana de ajustes.
 * Fotos de la consola: si existe /app0/capturas.txt, guarda la pantalla real en /app0/capturas/NN.ppm en reposo
 * y en varios momentos del primer ataque (o en los segundos del ataque que diga el archivo, uno por linea), y
 * sigue funcionando; una linea "video N" ademas graba el primer ataque a N cuadros por segundo en
 * /app0/capturas/video/NNNN.jpg. Se bajan por FTP de /data/homebrew/PPSA77001/capturas/ (fotos_ps5.py).
 * Inspeccion: con la linea "inspeccion", despues del primer ataque la camara se acerca a cada monstruo (de frente y
 * a +-40 grados) y repite el ataque dos veces, de cerca del Mago y de cerca del Guardian, sacando fotos JPG
 * (capturas/insp_*.jpg) para revisar cada personaje en detalle.
 * Cierre sin manos: con la linea "cerrar_al_terminar" en capturas.txt el juego sale solo (de forma normal) al
 * terminar de grabar el primer ataque; y si aparece /app0/cerrar.txt, lo borra y sale.
 */

#include "vulkanexamplebase.h"
#include "VulkanglTFModel.h"
#include "platform.h"
#include "escena.h"
#include "reglas/combate_api.h"
#include "reglas/tabla_reglas.h"
#include "reglas/todas.h"
#include "interfaz.h"   // HUD del duelo (LP, visor, fases, manos, puntero): rama interfaz-duelo
#include <fstream>
#include <iterator>
#include <sstream>
#include <sys/stat.h>
#include <unistd.h>

namespace {
constexpr uint32_t TAM_SOMBRA = 4096;
constexpr VkFormat FORMATO_SOMBRA = VK_FORMAT_D32_SFLOAT;
constexpr size_t NUM_MONSTRUOS = sizeof(MONSTRUOS) / sizeof(MONSTRUOS[0]);
// CamaraJuego de Unreal: ue(0,12.8,6.4) -> ue(0,-0.6,0), campo de vision horizontal de 62 grados
// el tablero se agrando x1.4 (escena_tablero.py ESCALA_TABLERO, mas espacio entre monstruos): la camara se
// aleja en la misma proporcion
constexpr float ESCALA_TABLERO = 1.4f;
// (un poco mas: que las columnas de los extremos no queden cortadas con el vaiven de la camara)
const glm::vec3 OJO = glm::vec3(0.0f, 6.4f, 12.8f) * (ESCALA_TABLERO * 1.08f);
const glm::vec3 OBJETIVO = glm::vec3(0.0f, 0.0f, -0.6f) * ESCALA_TABLERO;
constexpr float FOV_HORIZONTAL = 62.0f;
// hacia el sol: arriba, a la izquierda y hacia la camara (las sombras caen atras a la derecha)
const glm::vec3 HACIA_SOL = glm::normalize(glm::vec3(-0.45f, 1.0f, 0.55f));
// el ataque
constexpr float CADA_ATAQUE = 12.0f;   // s entre ataques automaticos
constexpr float DURACION_ATAQUE = 8.8f;
// los personajes con esqueleto (Meshy): miden 1.8 m; en el tablero, como los demas monstruos (2.6 m)
constexpr float ESCALA_PERSONAJE = 2.6f / 1.8f;
// sus animaciones, en el orden del archivo (meshy.py animar ... 89,125,129,102 y 0,178,182,189)
enum { MAGO_GUARDIA = 0, MAGO_HECHIZO_CARGADO = 1, MAGO_HECHIZO = 2, MAGO_GOLPE = 3 };
enum { GUARDIAN_REPOSO = 0, GUARDIAN_DEFENSA = 1, GUARDIAN_MUERE = 2 };   // 0,148,189
// momentos del ataque (s): el rayo sale (y llega: es instantaneo), el Guardian se cubre, el rayo se apaga,
// el Guardian empieza a caer
constexpr float T_SUELTA = 1.65f, T_IMPACTO = 1.65f, T_CUBRE = 1.45f, T_FIN_RAYO = 2.9f, T_MUERE = 2.55f;
// la defensa se congela en su punto de mas cobertura; la muerte empieza ya cayendo (se salta el inicio de pie)
constexpr float DEFENSA_MAX = 0.5f, MUERE_DESDE = 0.65f;
// los magos (dark_magician_anim.glb, dark_magician_girl_anim.glb): clip 0 = Idle 3 (243), clip 1 = dying_backwards
// (189, la misma caida del Guardian; pedido del usuario: "debe caer como el Warrior")
constexpr uint32_t CLIP_REPOSO_MAGO = 0, CLIP_MUERE_MAGO = 1;
// armas: largo en metros del personaje (1.8 m) y punto de agarre (0 abajo .. 1 arriba del modelo)
constexpr float LARGO_BACULO = 1.65f, AGARRE_BACULO = 0.55f;
constexpr float LARGO_ESPADA = 1.05f, AGARRE_ESPADA = 0.12f;
// de la muneca al centro del puno cerrado (m, en el personaje de 1.8 m)
constexpr float PUNO = 0.075f;
// Mago Oscuro fijo (modelo de Meshy desde su figura original, con el baculo agarrado en el mismo modelo): se dibuja
// como los demas monstruos (sin esqueleto); el rayo sale del ojo del baculo, medido en Blender (glTF del modelo)
constexpr bool MAGO_FIJO = false;
// Mago con esqueleto y el baculo DENTRO de su modelo (Gemini pose A con baculo -> Meshy; arma_a_mano.py lo dejo
// rigido en LeftHand): no se dibuja el baculo suelto, y el rayo sale de su punta siguiendo ese hueso
constexpr bool BACULO_EN_MODELO = true;
// Lanzadores de conjuros con baculo (plantilla "mago"; cada ataque le toca al siguiente). Cada uno: modelo de
// Meshy con esqueleto y el baculo como hueso propio (arma_a_mano.py nuevo:Baculo). lado = +1 si el baculo esta
// del lado +x del modelo (lo agarra LeftHand), -1 si esta del lado -x (RightHand); punta (adorno, de ahi sale la
// magia) y pie del baculo en reposo (glTF); cuanto se levantan el cuello y la cabeza (la guardia los baja)
struct DatosLanzador { const char* carta; const char* archivo; float lado; glm::vec3 punta, pie; float cuello, cabeza; glm::vec3 halo, nucleo; };
const DatosLanzador LANZADORES[] = {
	{ "dark_magician", "dark_magician_anim.glb", 1.0f, { 0.3873f, 1.7372f, 0.1786f }, { 0.3757f, 0.4257f, 0.1647f }, -8.0f, -14.0f, { 0.18f, 0.45f, 1.6f }, { 0.85f, 0.92f, 1.0f } },   // azul (pedido del usuario)
	{ "dark_magician_girl", "dark_magician_girl_anim.glb", -1.0f, { -0.3309f, 1.3761f, 0.1470f }, { -0.2706f, 0.4436f, 0.1660f }, -8.0f, -14.0f, { 0.55f, 0.18f, 1.5f }, { 0.92f, 0.82f, 1.0f } },   // morado (el suyo)
};
constexpr size_t NUM_LANZADORES = sizeof(LANZADORES) / sizeof(LANZADORES[0]);
// El baculo es un hueso propio ("Baculo", arma_a_mano.py nuevo:Baculo) que mueve el juego, y las DOS manos lo
// agarran: los brazos llegan a el por cinematica inversa (la animacion solo mueve el cuerpo y las piernas).
// La mano derecha del modelo esta abierta (sin huesos de dedos): va con la palma apoyada en el baculo, los dedos a
// lo largo de el. SEPARA_MANOS: del puno izquierdo a la palma derecha, bajando por el baculo (m); LADO_PALMA: de
// que lado del baculo queda la palma (grados alrededor del baculo, 0 = del lado derecho del Mago)
constexpr float SEPARA_MANOS = 0.25f, LADO_PALMA = 0.0f, SIGNO_PALMA = -1.0f;
constexpr bool GUARDIAN_FIJO = false;   // con esqueleto: cae como una persona (el fijo caia "como muneco")
const glm::vec3 PUNTA_MAGO{ 0.7499f, 0.2707f, 0.4223f };
// ojos de Kuriboh en coordenadas de su modelo (glTF), medidos con rayos sobre la textura: centro y radio
const glm::vec4 OJO_KURIBOH_A{ -0.1050f, 0.5560f, 0.3450f, 0.085f };   // Kuriboh v3 (TRELLIS en Colab, 2026-10-16): medir_ojos.py 30,35,110
// Enfrentamientos (motor de reglas, Excel del usuario): quien ataca a quien. Los "en juego" se turnan en la PS5;
// todos se pueden ver en el PC con YUGI_DUELO=n. Los personajes con esqueleto (Mago, Maga, Guardian) usan su
// codigo propio; los demas, su regla (reglas/regla_*.h, por la tabla generada desde reglas_combate.json)
struct Enfrentamiento { const char* atacante; const char* objetivo; bool enJuego; };
const Enfrentamiento ENFRENTAMIENTOS[] = {
	{ "dark_magician", "celtic_guardian", true },
	{ "dark_magician_girl", "celtic_guardian", true },
	{ "red_eyes", "celtic_guardian", false },
	{ "baby_dragon", "celtic_guardian", false },
	{ "kuriboh", "celtic_guardian", false },
	{ "dark_magician", "red_eyes", false },
	{ "dark_magician_girl", "baby_dragon", false },
	{ "dark_magician", "kuriboh", false },
	{ "red_eyes", "dark_magician", false },        // regla 3: el mistico se defiende con el baculo
	{ "kuriboh", "dark_magician_girl", false },
};
constexpr size_t NUM_ENFRENTAMIENTOS = sizeof(ENFRENTAMIENTOS) / sizeof(ENFRENTAMIENTOS[0]);
const glm::vec4 OJO_KURIBOH_B{ 0.1220f, 0.5500f, 0.3380f, 0.085f };

float suave(float a, float b, float x)
{
	const float t = glm::clamp((x - a) / (b - a), 0.0f, 1.0f);
	return t * t * (3.0f - 2.0f * t);
}

int indice(const char* carta)
{
	for (size_t i = 0; i < NUM_MONSTRUOS; i++) {
		if (strcmp(MONSTRUOS[i].carta, carta) == 0) {
			return (int)i;
		}
	}
	return -1;
}
}

class VulkanExample : public VulkanExampleBase
{
public:
	vkglTF::Model tablero;
	vkglTF::Model esfera;
	vkglTF::Model guardian;   // con esqueleto y animaciones (Meshy)
	vkglTF::Model baculo, espada, rayo;
	// cada arma va pegada al hueso de la mano derecha: agarre = de la mano (en reposo) al arma
	// cada arma va en la mano derecha: sigue la POSICION de la mano, y su direccion la decide el juego segun el
	// momento (si siguiera el giro de la muneca, el baculo quedaba al reves al levantar los brazos)
	struct Arma { vkglTF::Model* modelo; vkglTF::Node* mano; vkglTF::Node* antebrazo; glm::mat4 agarre; } armaMago{}, armaGuardian{};
	std::array<vkglTF::Model, NUM_MONSTRUOS> monstruos;
	// baculo a dos manos (en reposo, coordenadas del modelo del Mago): donde agarra el puno izquierdo, eje del
	// baculo, y la posicion y el giro que deben tener las dos munecas respecto del baculo
	struct DosManos {
		vkglTF::Node* baculo{ nullptr };
		glm::vec3 agarre{ 0.0f }, eje{ 0.0f, 1.0f, 0.0f };
		glm::vec3 munecaIzq{ 0.0f }, munecaDer{ 0.0f };
		glm::quat giroIzq{}, giroDer{};
	};
	// relBaculo: el baculo respecto de la mano que lo agarra (se toma en vida; al morir el baculo sigue a esa mano)
	struct Lanzador { const DatosLanzador* datos{ nullptr }; int indice{ -1 }; vkglTF::Model modelo; DosManos manos; glm::mat4 relBaculo{ 1.0f }; };
	std::array<Lanzador, NUM_LANZADORES> lanzadores;
	size_t cual{ 0 };   // el que ataca ahora; cada ataque pasa al siguiente (el primero es el segundo de la lista)

	// Ajustes (ventana de la plantilla, OPTIONS)
	bool animar{ true };
	bool respirar{ true };
	bool ataquesSolos{ true };
	float brilloHolo{ 0.55f };
	float tiempo{ 0.0f };

	// El ataque: quien ataca, a quien, y desde cuando (< 0: no hay ataque en curso)
	int atacante{ indice("dark_magician") };
	int objetivo{ indice("celtic_guardian") };
	const int guardianIdx{ indice("celtic_guardian") };
	size_t duelo{ 0 };   // el enfrentamiento en curso (ENFRENTAMIENTOS)
	const int kuriboh{ indice("kuriboh") };
	float tAtaque{ -1.0f };
	struct pad mando{};      // la lectura anterior del control (para ver que se acaba de apretar)
	float proximoAtaque{ 4.0f };
	interfaz::Interfaz interfazDuelo;   // todo lo que rodea al tablero (interfaz.h)

	// fotos de la consola a pedido (capturas.txt)
	std::string carpetaCapturas;          // vacia: sin fotos
	std::vector<float> momentosCaptura;   // segundos dentro del primer ataque
	size_t siguienteCaptura{ 0 };
	bool fotoReposo{ false };
	float videoFps{ 0.0f };               // 0: sin video
	bool cerrarAlTerminar{ false };       // salir solo al terminar de grabar el primer ataque
	float tSalida{ -1.0f };               // cuando se pidio salir (se espera a que terminen de escribirse las fotos)
	// inspeccion: 0 espera el primer ataque, 1 primeros planos, 2 ataque desde el Mago, 3 desde el Guardian, 4 fin
	bool inspeccion{ false };
	int faseInsp{ 0 }, pasoInsp{ 0 }, cuadrosInsp{ 0 };
	size_t fotoAtaqueInsp{ 0 };
	bool camInsp{ false };
	glm::vec3 ojoInsp{ 0.0f }, miraInsp{ 0.0f };
	float revisarCerrar{ 0.0f };          // proxima revision de cerrar.txt
	int cuadroVideo{ 0 };
	int ataquesVistos{ 0 };

	struct UniformData {
		glm::mat4 proyeccion;
		glm::mat4 vista;
		glm::mat4 luz;          // mundo -> espacio del mapa de sombras
		glm::vec4 haciaSol;
		glm::vec4 camara;
		glm::vec4 pantalla;     // ancho, alto, tiempo, destello
	} uniformData;
	std::array<vks::Buffer, maxConcurrentFrames> uniformBuffers;

	struct Empuje {
		glm::mat4 modelo;
		glm::vec4 efecto;       // x: holograma, y: especular, z: desintegracion 0..1, w: emisivo
		glm::vec4 vida;         // x, y: base del monstruo en el mundo (x, z), z: respiracion, w: pelo
		glm::vec4 ojoA{ 0.0f }; // ojos con parpado (coordenadas del modelo): centro y radio (0: sin parpados)
		glm::vec4 ojoB{ 0.0f }; // centro del otro ojo y cuanto esta cerrado (0 abierto, 1 cerrado)
	};

	struct {
		VkImage imagen{ VK_NULL_HANDLE };
		VkDeviceMemory memoria{ VK_NULL_HANDLE };
		VkImageView vista{ VK_NULL_HANDLE };
		VkSampler muestreador{ VK_NULL_HANDLE };
	} sombra;

	struct {
		VkPipeline escena{ VK_NULL_HANDLE };
		VkPipeline sombra{ VK_NULL_HANDLE };
		VkPipeline escenaEsqueleto{ VK_NULL_HANDLE };
		VkPipeline efectos{ VK_NULL_HANDLE };      // rayos, chispas y resplandores: suman luz
		VkPipeline sombraEsqueleto{ VK_NULL_HANDLE };
	} pipelines;
	VkPipelineLayout pipelineLayout{ VK_NULL_HANDLE };
	VkPipelineLayout pipelineLayoutEsqueleto{ VK_NULL_HANDLE };   // + set 2: matrices de los huesos (vkglTF)
	VkDescriptorSetLayout descriptorSetLayout{ VK_NULL_HANDLE };
	std::array<VkDescriptorSet, maxConcurrentFrames> descriptorSets{};

	VulkanExample() : VulkanExampleBase()
	{
		title = "Yugi Reload";
		settings.overlay = false;
		apiVersion = VK_API_VERSION_1_3;
		useDynamicRendering = true;
		requiresStencil = true;
		deviceCreatepNextChain = &baseDynamicRenderingFeatures;
	}

	~VulkanExample()
	{
		if (device) {
			vkDestroyPipeline(device, pipelines.escena, nullptr);
			vkDestroyPipeline(device, pipelines.sombra, nullptr);
			vkDestroyPipeline(device, pipelines.escenaEsqueleto, nullptr);
			vkDestroyPipeline(device, pipelines.efectos, nullptr);
			vkDestroyPipeline(device, pipelines.sombraEsqueleto, nullptr);
			vkDestroyPipelineLayout(device, pipelineLayout, nullptr);
			vkDestroyPipelineLayout(device, pipelineLayoutEsqueleto, nullptr);
			vkDestroyDescriptorSetLayout(device, descriptorSetLayout, nullptr);
			vkDestroySampler(device, sombra.muestreador, nullptr);
			vkDestroyImageView(device, sombra.vista, nullptr);
			vkDestroyImage(device, sombra.imagen, nullptr);
			vkFreeMemory(device, sombra.memoria, nullptr);
			for (auto& buffer : uniformBuffers) {
				buffer.destroy();
			}
		}
	}

	void getEnabledFeatures() override
	{
		if (deviceFeatures.samplerAnisotropy) {
			enabledFeatures.samplerAnisotropy = VK_TRUE;
		}
	}

	void loadAssets()
	{
		const uint32_t flags = vkglTF::FileLoadingFlags::PreTransformVertices;
		tablero.loadFromFile(getAssetPath() + "models/yugi/tablero.glb", vulkanDevice, queue, flags);
		esfera.loadFromFile(getAssetPath() + "models/yugi/esfera.glb", vulkanDevice, queue, flags);
		// sin pre-transformar: el esqueleto mueve los vertices en el shader
		for (size_t k = 0; k < NUM_LANZADORES; k++) {
			lanzadores[k].datos = &LANZADORES[k];
			lanzadores[k].indice = indice(LANZADORES[k].carta);
			lanzadores[k].modelo.loadFromFile(getAssetPath() + "models/yugi/" + LANZADORES[k].archivo, vulkanDevice, queue, 0);
			prepararDosManos(lanzadores[k]);
		}
		elegirDuelo(0);   // el primer ataque (que empieza solo) tambien sortea su rayo y su color
		guardian.loadFromFile(getAssetPath() + "models/yugi/celtic_guardian_anim.glb", vulkanDevice, queue, 0);
		baculo.loadFromFile(getAssetPath() + "models/yugi/baculo.glb", vulkanDevice, queue, flags);
		espada.loadFromFile(getAssetPath() + "models/yugi/espada.glb", vulkanDevice, queue, flags);
		rayo.loadFromFile(getAssetPath() + "models/yugi/rayo.glb", vulkanDevice, queue, flags);
		// baculo de pie junto a la mano (punta arriba); espada hacia adelante y abajo, lista para cubrirse
		// baculo de pie (punta arriba); espada hacia adelante y abajo
		armaMago = empunar(lanzadores[0].modelo, baculo, LARGO_BACULO, AGARRE_BACULO, glm::vec3(0.0f, 1.0f, 0.12f));
		armaGuardian = empunar(guardian, espada, LARGO_ESPADA, AGARRE_ESPADA, glm::vec3(0.0f, -0.55f, 1.0f));
		for (size_t i = 0; i < NUM_MONSTRUOS; i++) {
			monstruos[i].loadFromFile(getAssetPath() + "models/yugi/" + MONSTRUOS[i].carta + ".glb", vulkanDevice, queue, flags);
		}
	}

	static glm::quat giroGlobal(vkglTF::Node* n)
	{
		glm::mat3 m(n->getMatrix());
		for (int c = 0; c < 3; c++) {
			m[c] = glm::normalize(m[c]);
		}
		return glm::normalize(glm::quat_cast(m));
	}

	static glm::vec3 posGlobal(vkglTF::Node* n) { return glm::vec3(n->getMatrix()[3]); }

	// gira un hueso "delta" en el mundo del modelo (cambia su giro local; los hijos lo siguen)
	static void girarGlobal(vkglTF::Node* n, const glm::quat& delta)
	{
		const glm::quat padre = n->parent ? giroGlobal(n->parent) : glm::quat(1.0f, 0.0f, 0.0f, 0.0f);
		n->rotation = glm::normalize(glm::inverse(padre) * delta * padre * n->rotation);
	}

	// Pose de reposo del baculo a dos manos: el puno izquierdo ya lo agarra en el modelo; la mano derecha es la
	// izquierda espejada (x -> -x), girada alrededor del baculo y bajada SEPARA_MANOS
	void prepararDosManos(Lanzador& l)
	{
		DosManos& dosManos = l.manos;
		const glm::vec3 PUNTA_BACULO_REPOSO = l.datos->punta, PIE_BACULO_REPOSO = l.datos->pie;
		const float ladoBaculo = l.datos->lado;
		dosManos.baculo = l.modelo.nodeFromName("Baculo");
		// "izq" = la mano que ya agarra el baculo en el modelo (la del lado del baculo)
		vkglTF::Node* izq = l.modelo.nodeFromName(ladoBaculo > 0.0f ? "LeftHand" : "RightHand");
		if (!dosManos.baculo || !izq) {
			return;
		}
		dosManos.eje = glm::normalize(PUNTA_BACULO_REPOSO - PIE_BACULO_REPOSO);
		dosManos.munecaIzq = posGlobal(izq);
		dosManos.giroIzq = giroGlobal(izq);
		const glm::vec3 dedos = dosManos.giroIzq * glm::vec3(0.0f, 1.0f, 0.0f);
		const glm::vec3 puno = dosManos.munecaIzq + dedos * PUNO;
		dosManos.agarre = PIE_BACULO_REPOSO + dosManos.eje * glm::dot(puno - PIE_BACULO_REPOSO, dosManos.eje);
		float lado = LADO_PALMA, separa = SEPARA_MANOS, signo = SIGNO_PALMA;
#if defined(PS5_HOST_REFERENCE)
		if (const char* v = getenv("YUGI_LADO_PALMA")) {
			lado = (float)atof(v);
		}
		if (const char* v = getenv("YUGI_SEPARA")) {
			separa = (float)atof(v);
		}
		if (const char* v = getenv("YUGI_SIGNO_PALMA")) {
			signo = (float)atof(v);
		}
#endif
		// marco de la mano derecha: Y (dedos) a lo largo del baculo hacia el adorno; la palma mira al baculo
		const glm::vec3 haciaBaculo = glm::angleAxis(glm::radians(lado), dosManos.eje) * glm::vec3(ladoBaculo, 0.0f, 0.0f);
		const glm::vec3 y = dosManos.eje;
		// la palma es la cara z de la mano (en el modelo de Meshy)
		const glm::vec3 z = glm::normalize(signo * (haciaBaculo - y * glm::dot(haciaBaculo, y)));
		const glm::vec3 x = glm::cross(y, z);
		dosManos.giroDer = glm::normalize(glm::quat_cast(glm::mat3(x, y, z)));
		// la palma (8 cm de la muneca hacia los dedos) toca el baculo desde su lado (3 cm del eje)
		const glm::vec3 lugar = dosManos.agarre - dosManos.eje * separa;
		dosManos.munecaDer = lugar - y * 0.08f - glm::normalize(haciaBaculo - y * glm::dot(haciaBaculo, y)) * 0.03f;
	}

	// Cinematica inversa de dos huesos: hombro -> codo -> muneca. Lleva la muneca a "objetivo" (el codo queda en
	// el plano que senala "polo") y deja la mano con el giro dado (en el mundo del modelo)
	static void brazoHacia(vkglTF::Model& mago, const char* hombro, const char* codo, const char* mano, glm::vec3 objetivo, const glm::quat& giroMano, glm::vec3 polo)
	{
		vkglTF::Node* h = mago.nodeFromName(hombro);
		vkglTF::Node* c = mago.nodeFromName(codo);
		vkglTF::Node* m = mago.nodeFromName(mano);
		if (!h || !c || !m) {
			return;
		}
		const glm::vec3 S = posGlobal(h), E = posGlobal(c), W = posGlobal(m);
		const float a = glm::length(E - S), b = glm::length(W - E);
		const glm::vec3 t = objetivo - S;
		const float d = glm::clamp(glm::length(t), fabsf(a - b) + 1e-3f, a + b - 1e-3f);
		const glm::vec3 dir = glm::normalize(t);
		glm::vec3 pv = polo - S;
		pv -= dir * glm::dot(pv, dir);
		pv = glm::length(pv) > 1e-5f ? glm::normalize(pv) : glm::vec3(0.0f, -1.0f, 0.0f);
		const float cosA = glm::clamp((a * a + d * d - b * b) / (2.0f * a * d), -1.0f, 1.0f);
		const glm::vec3 codoNuevo = S + dir * (a * cosA) + pv * (a * sqrtf(1.0f - cosA * cosA));
		girarGlobal(h, glm::quat(glm::normalize(E - S), glm::normalize(codoNuevo - S)));
		const glm::vec3 E2 = posGlobal(c), W2 = posGlobal(m);
		girarGlobal(c, glm::quat(glm::normalize(W2 - E2), glm::normalize(objetivo - E2)));
		const glm::quat padre = giroGlobal(m->parent);
		m->rotation = glm::normalize(glm::inverse(padre) * giroMano);
	}

	// El baculo segun el momento del ataque (en el mundo del modelo): en guardia, de pie frente al pecho; al cargar
	// lo levanta y lo echa atras; al soltar la magia apunta al rival (el pecho ya mira al rival) y despues vuelve.
	// Todo con transiciones suaves (sin saltos). Las dos manos van al baculo por cinematica inversa
	void posarBaculo(Lanzador& l, bool ataca)
	{
		DosManos& dosManos = l.manos;
		vkglTF::Model& mago = l.modelo;
		const float sx = l.datos->lado;   // el lado del baculo (las poses de abajo son para el baculo a la izquierda)
		if (!dosManos.baculo) {
			return;
		}
		const float frente = frentePecho(l.indice);
		const glm::quat yaw = glm::angleAxis(frente, glm::vec3(0.0f, 1.0f, 0.0f));
		vkglTF::Node* pecho = mago.nodeFromName("Spine02");
		const glm::vec3 centro = pecho ? posGlobal(pecho) : glm::vec3(0.0f, 1.1f, 0.0f);
		float carga = 0.0f, suelta = 0.0f, cubre = 0.0f;
		if (!ataca && hayAtaque() && l.indice == objetivo) {
			// Excel regla 3, defensa: "interponer su baculo para evitar el ataque": lo cruza horizontal frente al
			// pecho, a dos manos, hasta que no aguanta el golpe y cae
			cubre = suave(T_CUBRE - 0.35f, T_CUBRE, tAtaque) * (1.0f - suave(T_MUERE, T_MUERE + 0.3f, tAtaque));
		}
		if (ataca) {
			// el golpe hacia adelante dura 0.4 s (mas rapido se veia como un salto)
			carga = suave(0.2f, T_SUELTA - 0.35f, tAtaque) * (1.0f - suave(T_SUELTA - 0.3f, T_SUELTA + 0.1f, tAtaque));
			suelta = suave(T_SUELTA - 0.3f, T_SUELTA + 0.1f, tAtaque) * (1.0f - suave(T_FIN_RAYO, T_FIN_RAYO + 0.9f, tAtaque));
		}
		const float quieto = 1.0f - carga - suelta - cubre;
		// direccion del baculo y lugar del puno izquierdo, en el marco del pecho (x a la izquierda del Mago, z al frente)
		const glm::vec3 dirLocal = glm::normalize(glm::vec3(0.12f, 1.0f, 0.18f) * quieto + glm::vec3(0.05f, 1.0f, -0.35f) * carga +
		                                          glm::vec3(0.0f, 0.45f, 1.0f) * suelta + glm::vec3(-1.0f, 0.18f, 0.05f) * cubre);
		const glm::vec3 punoLocal = glm::vec3(0.10f, 0.04f, 0.22f) * quieto + glm::vec3(0.08f, 0.16f, 0.18f) * carga +
		                            glm::vec3(0.06f, 0.10f, 0.30f) * suelta + glm::vec3(0.26f, 0.12f, 0.36f) * cubre;
		const glm::vec3 espejo(sx, 1.0f, 1.0f);
		const glm::vec3 dir = yaw * (dirLocal * espejo);
		const glm::vec3 punoObjetivo = centro + yaw * (punoLocal * espejo);
		// baculo: primero girado como el pecho, luego inclinado de su eje de reposo a la direccion pedida
		const glm::quat giro = glm::normalize(glm::quat(yaw * dosManos.eje, dir) * yaw);
		const glm::mat4 M = glm::translate(glm::mat4(1.0f), punoObjetivo) * glm::mat4_cast(giro) * glm::translate(glm::mat4(1.0f), -dosManos.agarre);
		// el hueso cuelga de la raiz (escala 0.01): su matriz local compensa esa escala
		vkglTF::Node* raiz = dosManos.baculo->parent;
		dosManos.baculo->translation = glm::vec3(0.0f);
		dosManos.baculo->rotation = glm::quat(1.0f, 0.0f, 0.0f, 0.0f);
		dosManos.baculo->scale = glm::vec3(1.0f);
		dosManos.baculo->matrix = (raiz ? glm::inverse(raiz->getMatrix()) : glm::mat4(1.0f)) * M;
		// los codos hacia afuera, abajo y un poco atras
		const glm::vec3 codoIzq = posGlobal(mago.nodeFromName("LeftForeArm")) + yaw * glm::vec3(0.25f, -0.2f, -0.15f);
		const glm::vec3 codoDer = posGlobal(mago.nodeFromName("RightForeArm")) + yaw * glm::vec3(-0.25f, -0.2f, -0.15f);
		// la mano del lado del baculo va a su agarre; la otra, mas abajo
		const bool izqAgarra = sx > 0.0f;
		brazoHacia(mago, "LeftArm", "LeftForeArm", "LeftHand", glm::vec3(M * glm::vec4(izqAgarra ? dosManos.munecaIzq : dosManos.munecaDer, 1.0f)),
		           giro * (izqAgarra ? dosManos.giroIzq : dosManos.giroDer), codoIzq);
		brazoHacia(mago, "RightArm", "RightForeArm", "RightHand", glm::vec3(M * glm::vec4(izqAgarra ? dosManos.munecaDer : dosManos.munecaIzq, 1.0f)),
		           giro * (izqAgarra ? dosManos.giroDer : dosManos.giroIzq), codoDer);
#if defined(PS5_HOST_REFERENCE)
		if (getenv("YUGI_DEPURA")) {
			auto p = [&](const char* n) { return posGlobal(mago.nodeFromName(n)); };
			const glm::vec3 objD = glm::vec3(M * glm::vec4(dosManos.munecaDer, 1.0f)), objI = glm::vec3(M * glm::vec4(dosManos.munecaIzq, 1.0f));
			const glm::vec3 punta = glm::vec3(M * glm::vec4(l.datos->punta, 1.0f));
			fprintf(stderr, "[dep] t=%.2f frente=%.0f hombroD=(%.2f %.2f %.2f) objD=(%.2f %.2f %.2f) llegaD=(%.2f %.2f %.2f) objI=(%.2f %.2f %.2f) llegaI=(%.2f %.2f %.2f) punta=(%.2f %.2f %.2f) pecho=(%.2f %.2f %.2f)\n",
			       tAtaque, glm::degrees(frente), p("RightArm").x, p("RightArm").y, p("RightArm").z, objD.x, objD.y, objD.z,
			       p("RightHand").x, p("RightHand").y, p("RightHand").z, objI.x, objI.y, objI.z, p("LeftHand").x, p("LeftHand").y, p("LeftHand").z,
			       punta.x, punta.y, punta.z, centro.x, centro.y, centro.z);
			fflush(stderr);
		}
#endif
	}

	// Un arma (modelo vertical, punta arriba) agarrada por el puno izquierdo (el que esta cerrado en los modelos de
	// Meshy): en la pose de reposo se coloca dentro del puno, con su eje en la direccion dada, y desde ahi queda
	// PEGADA al hueso de la mano (sigue su posicion y su giro en cada animacion, como un objeto agarrado de verdad)
	Arma empunar(vkglTF::Model& personaje, vkglTF::Model& arma, float largo, float agarre, glm::vec3 eje)
	{
		Arma a{ &arma, personaje.nodeFromName("LeftHand"), personaje.nodeFromName("LeftForeArm"), glm::mat4(1.0f) };
		if (!a.mano || !a.antebrazo) {
			return a;
		}
		const glm::mat4 manoReposo = a.mano->getMatrix();
		const glm::vec3 muneca = glm::vec3(manoReposo[3]);
		const glm::vec3 brazo = glm::normalize(muneca - glm::vec3(a.antebrazo->getMatrix()[3]));
		const glm::vec3 puno = muneca + brazo * PUNO;
		const float alto = glm::max(arma.dimensions.max.y - arma.dimensions.min.y, 1e-3f);
		const glm::mat4 deseado = glm::translate(glm::mat4(1.0f), puno) *
		                          glm::mat4_cast(glm::quat(glm::vec3(0.0f, 1.0f, 0.0f), glm::normalize(eje))) *
		                          glm::scale(glm::mat4(1.0f), glm::vec3(largo / alto)) *
		                          glm::translate(glm::mat4(1.0f), glm::vec3(0.0f, -(arma.dimensions.min.y + agarre * alto), 0.0f));
		a.agarre = glm::inverse(manoReposo) * deseado;
		return a;
	}

	glm::vec3 posicionHueso(vkglTF::Node* hueso, const glm::mat4& personaje) const
	{
		return hueso ? glm::vec3(personaje * hueso->getMatrix()[3]) : glm::vec3(personaje[3]);
	}

	// El baculo va en el puno del Mago pero siempre de pie (si siguiera el giro de la muneca quedaba horizontal en
	// la guardia de combate): se toma el punto de agarre y la escala del arma en la mano y se endereza; al atacar se
	// inclina hacia el Guardian
	glm::mat4 baculoDePie(const glm::mat4& enMano) const
	{
		const float alto = baculo.dimensions.max.y - baculo.dimensions.min.y;
		const float yAgarre = baculo.dimensions.min.y + AGARRE_BACULO * alto;
		const glm::vec3 agarre = glm::vec3(enMano * glm::vec4(0.0f, yAgarre, 0.0f, 1.0f));
		const float esc = glm::length(glm::vec3(enMano[1]));
		const glm::vec3 frente = hayAtaque() ? glm::normalize(base(objetivo) - base(atacante)) : glm::vec3(0.0f, 0.0f, 1.0f);
		const glm::vec3 reposo = glm::normalize(glm::vec3(0.0f, 1.0f, 0.0f) + 0.1f * frente);
		const glm::vec3 apunta = glm::normalize(frente + glm::vec3(0.0f, 0.6f, 0.0f));
		const float k = hayAtaque() ? suave(0.6f, T_SUELTA, tAtaque) * (1.0f - suave(T_FIN_RAYO, T_FIN_RAYO + 0.6f, tAtaque)) : 0.0f;
		const glm::vec3 dir = glm::normalize(glm::mix(reposo, apunta, k));
		return glm::translate(glm::mat4(1.0f), agarre) * glm::mat4_cast(glm::quat(glm::vec3(0.0f, 1.0f, 0.0f), dir)) *
		       glm::scale(glm::mat4(1.0f), glm::vec3(esc)) * glm::translate(glm::mat4(1.0f), glm::vec3(0.0f, -yAgarre, 0.0f));
	}

	// Punta de un arma que es parte del modelo con esqueleto (rigida en un hueso): su posicion de reposo llevada por
	// ese hueso (hueso actual * union inversa del hueso * punta en reposo), en el mundo
	glm::vec3 puntaArma(vkglTF::Model& modelo, const char* hueso, const glm::vec3& reposo, const glm::mat4& personaje) const
	{
		for (vkglTF::Skin* piel : modelo.skins) {
			for (size_t k = 0; k < piel->joints.size(); k++) {
				if (piel->joints[k]->name == hueso) {
					return glm::vec3(personaje * piel->joints[k]->getMatrix() * piel->inverseBindMatrices[k] * glm::vec4(reposo, 1.0f));
				}
			}
		}
		return glm::vec3(personaje * glm::vec4(reposo, 1.0f));
	}

	// donde esta el arma ahora (en el mundo): pegada a la mano en su pose actual
	glm::mat4 matrizArma(const Arma& a, const glm::mat4& personaje) const
	{
		return personaje * (a.mano ? a.mano->getMatrix() : glm::mat4(1.0f)) * a.agarre;
	}


	void prepararSombra()
	{
		VkImageCreateInfo imagen = vks::initializers::imageCreateInfo();
		imagen.imageType = VK_IMAGE_TYPE_2D;
		imagen.format = FORMATO_SOMBRA;
		imagen.extent = { TAM_SOMBRA, TAM_SOMBRA, 1 };
		imagen.mipLevels = 1;
		imagen.arrayLayers = 1;
		imagen.samples = VK_SAMPLE_COUNT_1_BIT;
		imagen.tiling = VK_IMAGE_TILING_OPTIMAL;
		imagen.usage = VK_IMAGE_USAGE_DEPTH_STENCIL_ATTACHMENT_BIT | VK_IMAGE_USAGE_SAMPLED_BIT;
		VK_CHECK_RESULT(vkCreateImage(device, &imagen, nullptr, &sombra.imagen));
		VkMemoryRequirements requisitos;
		vkGetImageMemoryRequirements(device, sombra.imagen, &requisitos);
		VkMemoryAllocateInfo memoria = vks::initializers::memoryAllocateInfo();
		memoria.allocationSize = requisitos.size;
		memoria.memoryTypeIndex = vulkanDevice->getMemoryType(requisitos.memoryTypeBits, VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT);
		VK_CHECK_RESULT(vkAllocateMemory(device, &memoria, nullptr, &sombra.memoria));
		VK_CHECK_RESULT(vkBindImageMemory(device, sombra.imagen, sombra.memoria, 0));

		VkImageViewCreateInfo vista = vks::initializers::imageViewCreateInfo();
		vista.viewType = VK_IMAGE_VIEW_TYPE_2D;
		vista.format = FORMATO_SOMBRA;
		vista.subresourceRange = { VK_IMAGE_ASPECT_DEPTH_BIT, 0, 1, 0, 1 };
		vista.image = sombra.imagen;
		VK_CHECK_RESULT(vkCreateImageView(device, &vista, nullptr, &sombra.vista));

		// Comparacion por hardware y filtro lineal: cada lectura ya promedia 4 vecinos
		VkSamplerCreateInfo muestreador = vks::initializers::samplerCreateInfo();
		muestreador.magFilter = VK_FILTER_LINEAR;
		muestreador.minFilter = VK_FILTER_LINEAR;
		muestreador.mipmapMode = VK_SAMPLER_MIPMAP_MODE_NEAREST;
		muestreador.addressModeU = VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_BORDER;
		muestreador.addressModeV = VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_BORDER;
		muestreador.addressModeW = VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_BORDER;
		muestreador.borderColor = VK_BORDER_COLOR_FLOAT_OPAQUE_WHITE;
		muestreador.compareEnable = VK_TRUE;
		muestreador.compareOp = VK_COMPARE_OP_LESS_OR_EQUAL;
		muestreador.maxLod = 1.0f;
		VK_CHECK_RESULT(vkCreateSampler(device, &muestreador, nullptr, &sombra.muestreador));
	}

	void setupDescriptors()
	{
		std::vector<VkDescriptorPoolSize> poolSizes = {
			vks::initializers::descriptorPoolSize(VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER, maxConcurrentFrames),
			vks::initializers::descriptorPoolSize(VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER, maxConcurrentFrames),
		};
		VkDescriptorPoolCreateInfo descriptorPoolInfo = vks::initializers::descriptorPoolCreateInfo(poolSizes, maxConcurrentFrames);
		VK_CHECK_RESULT(vkCreateDescriptorPool(device, &descriptorPoolInfo, nullptr, &descriptorPool));
		// Set 0: uniformes del cuadro y mapa de sombras. Set 1: textura de color de cada material (vkglTF)
		const std::vector<VkDescriptorSetLayoutBinding> setLayoutBindings = {
			vks::initializers::descriptorSetLayoutBinding(VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER, VK_SHADER_STAGE_VERTEX_BIT | VK_SHADER_STAGE_FRAGMENT_BIT, 0),
			vks::initializers::descriptorSetLayoutBinding(VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER, VK_SHADER_STAGE_FRAGMENT_BIT, 1),
		};
		VkDescriptorSetLayoutCreateInfo descriptorLayout = vks::initializers::descriptorSetLayoutCreateInfo(setLayoutBindings);
		VK_CHECK_RESULT(vkCreateDescriptorSetLayout(device, &descriptorLayout, nullptr, &descriptorSetLayout));
		VkDescriptorSetAllocateInfo allocInfo = vks::initializers::descriptorSetAllocateInfo(descriptorPool, &descriptorSetLayout, 1);
		VkDescriptorImageInfo mapaSombra = vks::initializers::descriptorImageInfo(sombra.muestreador, sombra.vista, VK_IMAGE_LAYOUT_DEPTH_STENCIL_READ_ONLY_OPTIMAL);
		for (size_t i = 0; i < uniformBuffers.size(); i++) {
			VK_CHECK_RESULT(vkAllocateDescriptorSets(device, &allocInfo, &descriptorSets[i]));
			std::array<VkWriteDescriptorSet, 2> writes = {
				vks::initializers::writeDescriptorSet(descriptorSets[i], VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER, 0, &uniformBuffers[i].descriptor),
				vks::initializers::writeDescriptorSet(descriptorSets[i], VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER, 1, &mapaSombra),
			};
			vkUpdateDescriptorSets(device, static_cast<uint32_t>(writes.size()), writes.data(), 0, nullptr);
		}
	}

	void preparePipelines()
	{
		const std::array<VkDescriptorSetLayout, 2> setLayouts = { descriptorSetLayout, vkglTF::descriptorSetLayoutImage };
		VkPipelineLayoutCreateInfo pipelineLayoutCreateInfo = vks::initializers::pipelineLayoutCreateInfo(setLayouts.data(), static_cast<uint32_t>(setLayouts.size()));
		VkPushConstantRange empuje = vks::initializers::pushConstantRange(VK_SHADER_STAGE_VERTEX_BIT | VK_SHADER_STAGE_FRAGMENT_BIT, sizeof(Empuje), 0);
		pipelineLayoutCreateInfo.pushConstantRangeCount = 1;
		pipelineLayoutCreateInfo.pPushConstantRanges = &empuje;
		VK_CHECK_RESULT(vkCreatePipelineLayout(device, &pipelineLayoutCreateInfo, nullptr, &pipelineLayout));

		VkPipelineInputAssemblyStateCreateInfo inputAssemblyState = vks::initializers::pipelineInputAssemblyStateCreateInfo(VK_PRIMITIVE_TOPOLOGY_TRIANGLE_LIST, 0, VK_FALSE);
		// Sin descarte de caras: los modelos no son cerrados y el sombreado ilumina las dos caras
		VkPipelineRasterizationStateCreateInfo rasterizationState = vks::initializers::pipelineRasterizationStateCreateInfo(VK_POLYGON_MODE_FILL, VK_CULL_MODE_NONE, VK_FRONT_FACE_COUNTER_CLOCKWISE, 0);
		VkPipelineColorBlendAttachmentState blendAttachmentState = vks::initializers::pipelineColorBlendAttachmentState(0xf, VK_FALSE);
		VkPipelineColorBlendStateCreateInfo colorBlendState = vks::initializers::pipelineColorBlendStateCreateInfo(1, &blendAttachmentState);
		VkPipelineDepthStencilStateCreateInfo depthStencilState = vks::initializers::pipelineDepthStencilStateCreateInfo(VK_TRUE, VK_TRUE, VK_COMPARE_OP_LESS_OR_EQUAL);
		VkPipelineViewportStateCreateInfo viewportState = vks::initializers::pipelineViewportStateCreateInfo(1, 1, 0);
		VkPipelineMultisampleStateCreateInfo multisampleState = vks::initializers::pipelineMultisampleStateCreateInfo(VK_SAMPLE_COUNT_1_BIT, 0);
		std::vector<VkDynamicState> dynamicStateEnables = { VK_DYNAMIC_STATE_VIEWPORT, VK_DYNAMIC_STATE_SCISSOR };
		VkPipelineDynamicStateCreateInfo dynamicState = vks::initializers::pipelineDynamicStateCreateInfo(dynamicStateEnables);
		std::array<VkPipelineShaderStageCreateInfo, 2> shaderStages = {
			loadShader(getShadersPath() + "yugireload/escena.vert.spv", VK_SHADER_STAGE_VERTEX_BIT),
			loadShader(getShadersPath() + "yugireload/escena.frag.spv", VK_SHADER_STAGE_FRAGMENT_BIT),
		};
		VkPipelineRenderingCreateInfo renderingCreateInfo{
			.sType = VK_STRUCTURE_TYPE_PIPELINE_RENDERING_CREATE_INFO,
			.colorAttachmentCount = 1,
			.pColorAttachmentFormats = &swapChain.colorFormat,
			.depthAttachmentFormat = depthFormat,
			.stencilAttachmentFormat = depthFormat,
		};
		VkGraphicsPipelineCreateInfo pipelineCI{
			.sType = VK_STRUCTURE_TYPE_GRAPHICS_PIPELINE_CREATE_INFO,
			.pNext = &renderingCreateInfo,
			.stageCount = static_cast<uint32_t>(shaderStages.size()),
			.pStages = shaderStages.data(),
			.pVertexInputState = vkglTF::Vertex::getPipelineVertexInputState({ vkglTF::VertexComponent::Position, vkglTF::VertexComponent::Normal, vkglTF::VertexComponent::UV }),
			.pInputAssemblyState = &inputAssemblyState,
			.pViewportState = &viewportState,
			.pRasterizationState = &rasterizationState,
			.pMultisampleState = &multisampleState,
			.pDepthStencilState = &depthStencilState,
			.pColorBlendState = &colorBlendState,
			.pDynamicState = &dynamicState,
			.layout = pipelineLayout,
		};
		VK_CHECK_RESULT(vkCreateGraphicsPipelines(device, pipelineCache, 1, &pipelineCI, nullptr, &pipelines.escena));
		{
			// efectos: mezcla aditiva (ONE + ONE) y sin escribir profundidad (se ven a traves unos de otros)
			VkPipelineColorBlendAttachmentState suma = blendAttachmentState;
			suma.blendEnable = VK_TRUE;
			suma.srcColorBlendFactor = VK_BLEND_FACTOR_ONE;
			suma.dstColorBlendFactor = VK_BLEND_FACTOR_ONE;
			suma.colorBlendOp = VK_BLEND_OP_ADD;
			suma.srcAlphaBlendFactor = VK_BLEND_FACTOR_ONE;
			suma.dstAlphaBlendFactor = VK_BLEND_FACTOR_ONE;
			suma.alphaBlendOp = VK_BLEND_OP_ADD;
			VkPipelineColorBlendStateCreateInfo mezclaSuma = vks::initializers::pipelineColorBlendStateCreateInfo(1, &suma);
			VkPipelineDepthStencilStateCreateInfo sinEscribir = depthStencilState;
			sinEscribir.depthWriteEnable = VK_FALSE;
			VkGraphicsPipelineCreateInfo efectosCI = pipelineCI;
			efectosCI.pColorBlendState = &mezclaSuma;
			efectosCI.pDepthStencilState = &sinEscribir;
			VK_CHECK_RESULT(vkCreateGraphicsPipelines(device, pipelineCache, 1, &efectosCI, nullptr, &pipelines.efectos));
		}

		// Mapa de sombras: solo profundidad, con desplazamiento para evitar el "acne". Usa la misma
		// entrada de vertices que la escena (posicion y normal: la respiracion y el pelo las usan)
		VkPipelineRenderingCreateInfo renderingSombra{
			.sType = VK_STRUCTURE_TYPE_PIPELINE_RENDERING_CREATE_INFO,
			.colorAttachmentCount = 0,
			.depthAttachmentFormat = FORMATO_SOMBRA,
		};
		VkPipelineColorBlendStateCreateInfo sinColor = vks::initializers::pipelineColorBlendStateCreateInfo(0, nullptr);
		rasterizationState.depthBiasEnable = VK_TRUE;
		rasterizationState.depthBiasConstantFactor = 1.25f;
		rasterizationState.depthBiasSlopeFactor = 1.75f;
		VkPipelineShaderStageCreateInfo etapaSombra = loadShader(getShadersPath() + "yugireload/sombra.vert.spv", VK_SHADER_STAGE_VERTEX_BIT);
		pipelineCI.pNext = &renderingSombra;
		pipelineCI.stageCount = 1;
		pipelineCI.pStages = &etapaSombra;
		pipelineCI.pVertexInputState = vkglTF::Vertex::getPipelineVertexInputState({ vkglTF::VertexComponent::Position, vkglTF::VertexComponent::Normal });
		pipelineCI.pColorBlendState = &sinColor;
		VK_CHECK_RESULT(vkCreateGraphicsPipelines(device, pipelineCache, 1, &pipelineCI, nullptr, &pipelines.sombra));

		// Personajes con esqueleto: el mismo dibujo, con huesos (set 2 = matrices de cada malla, de vkglTF)
		const std::array<VkDescriptorSetLayout, 3> setsEsqueleto = { descriptorSetLayout, vkglTF::descriptorSetLayoutImage, vkglTF::descriptorSetLayoutUbo };
		VkPipelineLayoutCreateInfo layoutEsqueleto = vks::initializers::pipelineLayoutCreateInfo(setsEsqueleto.data(), static_cast<uint32_t>(setsEsqueleto.size()));
		layoutEsqueleto.pushConstantRangeCount = 1;
		layoutEsqueleto.pPushConstantRanges = &empuje;
		VK_CHECK_RESULT(vkCreatePipelineLayout(device, &layoutEsqueleto, nullptr, &pipelineLayoutEsqueleto));
		pipelineCI.layout = pipelineLayoutEsqueleto;
		VkPipelineShaderStageCreateInfo etapaSombraEsq = loadShader(getShadersPath() + "yugireload/sombra_esqueleto.vert.spv", VK_SHADER_STAGE_VERTEX_BIT);
		pipelineCI.pStages = &etapaSombraEsq;
		pipelineCI.pVertexInputState = vkglTF::Vertex::getPipelineVertexInputState({ vkglTF::VertexComponent::Position, vkglTF::VertexComponent::Normal, vkglTF::VertexComponent::Joint0, vkglTF::VertexComponent::Weight0 });
		VK_CHECK_RESULT(vkCreateGraphicsPipelines(device, pipelineCache, 1, &pipelineCI, nullptr, &pipelines.sombraEsqueleto));
		rasterizationState.depthBiasEnable = VK_FALSE;
		std::array<VkPipelineShaderStageCreateInfo, 2> etapasEsq = {
			loadShader(getShadersPath() + "yugireload/escena_esqueleto.vert.spv", VK_SHADER_STAGE_VERTEX_BIT),
			loadShader(getShadersPath() + "yugireload/escena.frag.spv", VK_SHADER_STAGE_FRAGMENT_BIT),
		};
		pipelineCI.pNext = &renderingCreateInfo;
		pipelineCI.stageCount = 2;
		pipelineCI.pStages = etapasEsq.data();
		pipelineCI.pVertexInputState = vkglTF::Vertex::getPipelineVertexInputState({ vkglTF::VertexComponent::Position, vkglTF::VertexComponent::Normal, vkglTF::VertexComponent::UV, vkglTF::VertexComponent::Joint0, vkglTF::VertexComponent::Weight0 });
		pipelineCI.pColorBlendState = &colorBlendState;
		VK_CHECK_RESULT(vkCreateGraphicsPipelines(device, pipelineCache, 1, &pipelineCI, nullptr, &pipelines.escenaEsqueleto));
	}

	void prepareUniformBuffers()
	{
		for (auto& buffer : uniformBuffers) {
			VK_CHECK_RESULT(vulkanDevice->createBuffer(VK_BUFFER_USAGE_UNIFORM_BUFFER_BIT, VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT, &buffer, sizeof(UniformData), &uniformData));
			VK_CHECK_RESULT(buffer.map());
		}
	}

	glm::vec3 base(int i) const
	{
		return glm::vec3(MONSTRUOS[i].x, 0.0f, MONSTRUOS[i].z);
	}

	// ------------------------------------------------------------------ el ataque, momento a momento
	bool hayAtaque() const { return tAtaque >= 0.0f && atacante >= 0 && objetivo >= 0; }
	// cuanto se eleva el atacante al cargar (0..1)
	float elevacion() const { return hayAtaque() ? suave(0.3f, T_SUELTA, tAtaque) * (1.0f - suave(T_SUELTA, T_SUELTA + 0.5f, tAtaque)) : 0.0f; }
	// desintegracion del objetivo: 0 entero, 1 desaparecido
	float desintegracion() const
	{
		return hayAtaque() ? suave(5.3f, 6.3f, tAtaque) * (1.0f - suave(7.4f, 8.2f, tAtaque)) : 0.0f;
	}
	float destello() const { return hayAtaque() && tAtaque > T_IMPACTO ? 0.13f * expf(-(tAtaque - T_IMPACTO) * 12.0f) : 0.0f; }
	// grosor del rayo (0: apagado): nace rapido, vibra mientras dura y se apaga
	float rayoActivo() const
	{
		if (!hayAtaque() || tAtaque < T_SUELTA || tAtaque > T_FIN_RAYO) {
			return 0.0f;
		}
		return suave(T_SUELTA, T_SUELTA + 0.12f, tAtaque) * (1.0f - suave(T_FIN_RAYO - 0.35f, T_FIN_RAYO, tAtaque)) *
		       (0.85f + 0.15f * sinf(tAtaque * 70.0f));
	}
	// la esfera: posicion y tamano (0 si no se ve)
	bool esferaEnElAire(glm::vec3& pos, float& tam) const
	{
		if (!hayAtaque() || tAtaque < 0.5f || tAtaque > T_IMPACTO) {
			return false;
		}
		// nace entre las manos del Mago (delante del pecho, mirando al Guardian) y vuela en arco hasta su pecho
		const glm::vec3 hacia = glm::normalize(base(objetivo) - base(atacante));
		const glm::vec3 carga = base(atacante) + hacia * 0.9f + glm::vec3(0.0f, 2.1f, 0.0f);
		const glm::vec3 destino = base(objetivo) + glm::vec3(0.0f, 1.6f, 0.0f);
		if (tAtaque < T_SUELTA) {
			pos = carga;
			tam = 0.4f * suave(0.5f, T_SUELTA, tAtaque) * (1.0f + 0.12f * sinf(tAtaque * 30.0f));
		} else {
			const float u = suave(T_SUELTA, T_IMPACTO, tAtaque);
			pos = glm::mix(carga, destino, u) + glm::vec3(0.0f, 1.0f * sinf(3.14159f * u), 0.0f);
			tam = 0.4f;
		}
		return true;
	}

	void updateUniformBuffers()
	{
		const float aspecto = (float)width / (float)height;
		const float fovVertical = 2.0f * atanf(tanf(glm::radians(FOV_HORIZONTAL) * 0.5f) / aspecto);
		uniformData.proyeccion = glm::perspectiveRH(fovVertical, aspecto, 0.1f, 80.0f);
		uniformData.proyeccion[1][1] *= -1.0f; // Vulkan: Y de la pantalla hacia abajo
		// el tablero se corre a la derecha de la columna de la interfaz (LP, visor, fases)
		uniformData.proyeccion = interfazDuelo.ajustarProyeccion(uniformData.proyeccion, (float)width, (float)height);
		glm::vec3 ojo = OJO;
		glm::vec3 mira = OBJETIVO;
		if (respirar) {
			// la camara respira: un vaiven lento de lado a lado y un poco de altura
			ojo.x += sinf(tiempo * 0.21f) * 0.7f;
			ojo.y += sinf(tiempo * 0.13f) * 0.25f;
		}
		if (hayAtaque()) {
			// corte de cine: de costado al duelo (perpendicular a la linea entre los dos, del lado de la camara)
			// y a media altura, para que los dos se vean a tamano parecido y la accion cruce la pantalla
			const float cine = suave(0.0f, 0.8f, tAtaque) * (1.0f - suave(7.2f, 8.6f, tAtaque));
			const glm::vec3 duelo = base(objetivo) - base(atacante);
			glm::vec3 costado = glm::normalize(glm::vec3(-duelo.z, 0.0f, duelo.x));
			if (costado.z < 0.0f) {
				costado = -costado;   // del lado del jugador (donde esta la camara normal)
			}
			const glm::vec3 medio = glm::mix(base(atacante), base(objetivo), 0.6f) + glm::vec3(0.0f, 1.3f, 0.0f);
			// por encima del hombro del atacante, del costado con la vista mas despejada: se prueban los dos y gana el
			// que deja mas lejos de la linea camara-duelo al monstruo mas cercano (antes solo esquivaba a Kuriboh y,
			// con el tablero x1.4, las alas de Ojos Rojos tapaban los ataques del Mago)
			const glm::vec3 detras = -glm::normalize(duelo);
			// con un atacante grande (dragon con alas de 5 m) la camara se aleja y sube segun su tamano
			const combate::Situacion sa = situacion(atacante);
			// y con uno chico (Kuriboh) baja, para que no quede cortado abajo de la pantalla
			const bool grande = esRigido(atacante);
			const float lejania = grande ? glm::max(4.6f, 1.1f * sa.ancho + 2.2f) : 4.6f;
			const float altura = grande ? glm::clamp(0.9f * sa.alto + 1.0f, 2.2f, 6.0f) : 3.2f;
			auto candidato = [&](glm::vec3 lado) {
				return base(atacante) + glm::normalize(detras * 1.0f + lado * 1.1f) * lejania + glm::vec3(0.0f, altura, 0.0f);
			};
			auto despeje = [&](glm::vec3 o) {
				float minimo = 1e9f;
				for (size_t i = 0; i < NUM_MONSTRUOS; i++) {
					if ((int)i == atacante || (int)i == objetivo) {
						continue;
					}
					const glm::vec3 p = base(i) + glm::vec3(0.0f, 1.5f, 0.0f);
					const glm::vec3 ab = medio - o;
					const float t = glm::clamp(glm::dot(p - o, ab) / glm::dot(ab, ab), 0.0f, 1.0f);
					// se descuenta el ancho del monstruo (las alas de Ojos Rojos llegan lejos de su centro)
					const glm::vec3 tam = monstruos[i].dimensions.size;
					const float radio = 0.5f * glm::max(tam.x, tam.z) * glm::length(glm::vec3(matrizMonstruo(i)[0]));
					minimo = glm::min(minimo, glm::length(p - (o + ab * t)) - radio);
				}
				return minimo;
			};
			const glm::vec3 lejos = despeje(candidato(costado)) > despeje(candidato(-costado)) ? costado : -costado;
			const glm::vec3 ojoCine = candidato(lejos);
			ojo = glm::mix(ojo, ojoCine, cine);
			mira = glm::mix(mira, medio, cine);
			// sacudida de la camara en el impacto
			ojo += glm::vec3(sinf(tAtaque * 71.0f), cosf(tAtaque * 53.0f), 0.0f) * 0.15f * destello();
		}
		if (camInsp) {
			ojo = ojoInsp;
			mira = miraInsp;
		}
#if defined(PS5_HOST_REFERENCE)
		// vista previa en el PC: camara fija cerca del Mago; YUGI_CAM_MAGO = grados alrededor de el (0 = desde el
		// rival, de frente durante el ataque; 90 = de costado)
		// YUGI_CAM_CARTA = numero de monstruo: la camara se acerca a el por la linea de la camara normal (como lo ve
		// el jugador, de cerca)
		if (const char* v = getenv("YUGI_CAM_CARTA")) {
			const int i = atoi(v);
			mira = base(i) + glm::vec3(0.0f, 1.5f, 0.0f);
			ojo = mira + glm::normalize(OJO - mira) * 4.0f;
		}
		if (const char* v = getenv("YUGI_CAM_MAGO")) {
			const float a = glm::radians((float)atof(v));
			const glm::vec3 h = glm::normalize(base(objetivo) - base(atacante));
			const glm::vec3 l = glm::normalize(glm::cross(glm::vec3(0.0f, 1.0f, 0.0f), h));
			mira = base(atacante) + glm::vec3(0.0f, 1.25f, 0.0f);
			ojo = mira + (h * cosf(a) + l * sinf(a)) * 3.2f + glm::vec3(0.0f, 0.5f, 0.0f);
		}
#endif
		uniformData.vista = glm::lookAtRH(ojo, mira, glm::vec3(0.0f, 1.0f, 0.0f));

		// Sol: proyeccion ortografica que cubre la mesa (19.5 x 14.7 m) y los monstruos
		const glm::mat4 vistaSol = glm::lookAtRH(HACIA_SOL * (20.0f * ESCALA_TABLERO), glm::vec3(0.0f), glm::vec3(0.0f, 0.0f, -1.0f));
		const glm::mat4 proySol = glm::orthoRH(-13.5f * ESCALA_TABLERO, 13.5f * ESCALA_TABLERO, -12.0f * ESCALA_TABLERO, 12.0f * ESCALA_TABLERO, 1.0f, 45.0f * ESCALA_TABLERO);
		uniformData.luz = proySol * vistaSol;
		uniformData.haciaSol = glm::vec4(HACIA_SOL, 0.0f);
		uniformData.camara = glm::vec4(ojo, 1.0f);
		uniformData.pantalla = glm::vec4((float)width, (float)height, tiempo, destello());
		memcpy(uniformBuffers[currentBuffer].mapped, &uniformData, sizeof(uniformData));
	}

	// Kuriboh parpadea: cada 2.5 a 4.5 s (a veces dos veces seguidas), y cierra fuerte los ojos del susto en el impacto
	float parpado() const
	{
#if defined(PS5_HOST_REFERENCE)
		// solo en el PC, para fotografiar el parpado: YUGI_PARPADO=0..1 lo deja fijo
		if (const char* fijo = getenv("YUGI_PARPADO")) {
			return (float)atof(fijo);
		}
#endif
		if (!animar) {
			return 0.0f;
		}
		if (hayAtaque() && tAtaque > T_IMPACTO - 0.05f && tAtaque < T_IMPACTO + 0.65f) {
			return 1.0f;
		}
		const float periodo = 3.5f;
		const float n = floorf(tiempo / periodo);
		const float azar = glm::fract(sinf(n * 12.9898f) * 43758.5453f);
		const float u = tiempo - n * periodo - azar;   // momento dentro de este parpadeo
		auto uno = [](float x) {                        // cierra en 0.07 s, abre en 0.11 s
			if (x < 0.0f || x > 0.18f) {
				return 0.0f;
			}
			return x < 0.07f ? x / 0.07f : 1.0f - (x - 0.07f) / 0.11f;
		};
		return glm::max(uno(u), azar > 0.6f ? uno(u - 0.28f) : 0.0f);
	}

	// Salto de Kuriboh con cuerpo firme: se agacha, sale inclinado hacia adelante, cae y amortigua
	void saltoKuriboh(float u, glm::vec3& desplazar, float& inclinar) const
	{
		if (u < 0.18f) {                       // se agacha y se echa atras
			const float a = sinf(3.14159f * u / 0.18f * 0.5f);
			desplazar.y -= 0.06f * a;
			inclinar = glm::radians(-6.0f) * a;
		} else if (u < 0.68f) {                // en el aire, inclinado hacia adelante
			const float a = (u - 0.18f) / 0.5f;
			desplazar.y += 0.42f * sinf(3.14159f * a);
			inclinar = glm::radians(8.0f) * sinf(3.14159f * a);
		} else if (u < 0.9f) {                 // aterriza y rebota un poco
			const float a = (u - 0.68f) / 0.22f;
			desplazar.y -= 0.05f * sinf(3.14159f * a);
			inclinar = glm::radians(-3.0f) * sinf(3.14159f * a);
		}
	}

	// Matriz del monstruo i en este instante: la de Blender, flotando y balanceandose sobre su carta,
	// y lo que le toque del ataque (elevarse al cargar, temblar y retroceder al recibir el golpe)
	glm::mat4 matrizMonstruo(size_t i, combate::Pose* salida = nullptr) const
	{
		const MonstruoEscena& m = MONSTRUOS[i];
		const glm::mat4 matriz = glm::make_mat4(m.matriz);
		const glm::vec3 centro = base((int)i);
		glm::vec3 desplazar{ 0.0f };
		// de frente al monitor (la camara), con un balanceo leve
		const glm::vec3 haciaCamara = OJO - centro;
		const float frente = atan2f(haciaCamara.x, haciaCamara.z);
		float giro = frente;
		float inclinar = 0.0f;   // hacia adelante (+) o atras (-), alrededor de la base
		if (animar) {
			const float fase = (float)i * 1.7f;
			desplazar.y = 0.06f * (0.5f + 0.5f * sinf(tiempo * 1.6f + fase));
			giro = frente + glm::radians(4.0f) * sinf(tiempo * 0.55f + fase);
			if ((int)i == kuriboh) {
				// un salto cada 4.2 s, y uno de susto con el impacto (sin el balanceo ni el flotar de los demas)
				desplazar.y = 0.015f * sinf(tiempo * 2.0f);
				giro = frente + glm::radians(6.0f) * sinf(tiempo * 0.7f);
				saltoKuriboh(fmodf(tiempo, 4.2f), desplazar, inclinar);
				if (hayAtaque() && (int)i != atacante && (int)i != objetivo && tAtaque > T_IMPACTO && tAtaque < T_IMPACTO + 0.9f) {
					saltoKuriboh(tAtaque - T_IMPACTO, desplazar, inclinar);
				}
			}
		}
		// Movimiento de cuerpo entero, sin esqueleto (la figura nunca se deforma). "hacia" apunta al rival;
		// inclinarse es girar alrededor del eje horizontal perpendicular a esa direccion, desde la base
		glm::vec3 hacia{ 0.0f, 0.0f, 1.0f };
		float inclinarDuelo = 0.0f;   // + hacia el rival, - hacia atras
		float caer = 0.0f;            // 0 de pie .. 90 grados tendido de lado
		if (hayAtaque() && ((int)i == atacante || (int)i == objetivo)) {
			hacia = glm::normalize(base((int)i == atacante ? objetivo : atacante) - centro);
		}
		// el ataque: lo decide la regla del monstruo (reglas/regla_*.h); al final todo vuelve a su lugar
		combate::Pose pose;
		if (hayAtaque() && esRigido((int)i) && ((int)i == atacante || (int)i == objetivo)) {
			const combate::Situacion st = situacion((int)i);
			const combate::Regla& r = reglaDe((int)i);
			if ((int)i == atacante) {
				r.atacar(st, pose);
			} else if (tAtaque >= combate::MUERE) {
				r.derrota(st, pose);
			} else if (tAtaque >= combate::CUBRE) {
				r.defender(st, pose);
			}
			const float vuelve = 1.0f - suave(combate::VUELVE, combate::VUELVE + 0.8f, tAtaque);
			desplazar += pose.desplazar * vuelve;
			inclinarDuelo += pose.inclinar * vuelve;
			giro += pose.girar * vuelve;
			caer = pose.caer * vuelve;
			pose.escala = 1.0f + (pose.escala - 1.0f) * vuelve;
			pose.aplastar = 1.0f + (pose.aplastar - 1.0f) * vuelve;
			pose.desintegrar *= vuelve;
		}
		if (salida) {
			*salida = pose;
		}
		const glm::vec3 lado = glm::normalize(glm::cross(glm::vec3(0.0f, 1.0f, 0.0f), hacia));
		// al caer de lado gira sobre el borde de su base (no se hunde en la mesa)
		const glm::vec3 bisagra = lado * (0.35f * (caer > 0.0f ? 1.0f : 0.0f));
		return glm::translate(glm::mat4(1.0f), centro + desplazar) *
		       glm::translate(glm::mat4(1.0f), bisagra) * glm::rotate(glm::mat4(1.0f), -caer, hacia) * glm::translate(glm::mat4(1.0f), -bisagra) *
		       glm::rotate(glm::mat4(1.0f), inclinarDuelo, lado) *
		       glm::rotate(glm::mat4(1.0f), giro, glm::vec3(0.0f, 1.0f, 0.0f)) *
		       glm::rotate(glm::mat4(1.0f), inclinar, glm::vec3(1.0f, 0.0f, 0.0f)) *
		       glm::scale(glm::mat4(1.0f), glm::vec3(pose.escala, pose.escala * pose.aplastar, pose.escala)) *
		       glm::translate(glm::mat4(1.0f), -centro) * matriz;
	}

	// Pose de los dos personajes en este instante (animacion y segundo dentro de ella)
	static void posar(vkglTF::Model& modelo, uint32_t clip, float t, bool repetir)
	{
		const vkglTF::Animation& a = modelo.animations[clip];
		const float largo = a.end - a.start;
		t = repetir ? fmodf(t, largo) : glm::min(t, largo - 0.001f);
		modelo.updateAnimation(clip, a.start + glm::max(t, 0.0f));
	}

	void actualizarPersonajes()
	{
		for (Lanzador& l : lanzadores) {
			if (muereLanzador(l)) {
				posar(l.modelo, CLIP_MUERE_MAGO, tAtaque - T_MUERE, false);   // cae de espaldas, como el Guardian
			} else {
				posar(l.modelo, CLIP_REPOSO_MAGO, tiempo, true);
			}
		}
		if (!hayAtaque() || objetivo != guardianIdx || tAtaque >= 7.4f) {
			posar(guardian, GUARDIAN_REPOSO, tiempo, true);
		} else {
			if (tAtaque < T_CUBRE) {
				posar(guardian, GUARDIAN_REPOSO, tiempo, true);
			} else if (tAtaque < T_MUERE) {
				posar(guardian, GUARDIAN_DEFENSA, glm::min(tAtaque - T_CUBRE, DEFENSA_MAX), false);   // se cubre y aguanta
			} else {
				posar(guardian, GUARDIAN_MUERE, MUERE_DESDE + (tAtaque - T_MUERE), false);   // no lo aguanta: cae y queda tendido
			}
		}
		// la guardia de combate le baja la cabeza al Mago: se la levanta para que mire al frente
		// el Guardian tambien levanta la cabeza hacia la camara (menos mientras se cubre y cae)
		const float erguido = hayAtaque() && objetivo == guardianIdx ? 1.0f - suave(T_CUBRE - 0.5f, T_CUBRE, tAtaque) * (1.0f - suave(7.4f, 8.2f, tAtaque)) : 1.0f;
		erguir(guardian, "neck", -8.0f * erguido);
		erguir(guardian, "Head", -14.0f * erguido);
		for (vkglTF::Node* n : guardian.nodes) {
			n->update();
		}
		for (Lanzador& l : lanzadores) {
			const bool ataca = hayAtaque() && l.indice == atacante;
			posarLanzador(l, ataca);
		}
	}

	bool muereLanzador(const Lanzador& l) const
	{
		return hayAtaque() && l.indice == objetivo && tAtaque >= T_MUERE && tAtaque < 7.4f;
	}

	// muriendo: la animacion mueve todo el cuerpo y los brazos (sin IK); el baculo va pegado a la mano que lo agarraba
	void baculoEnLaMano(Lanzador& l)
	{
		vkglTF::Node* mano = l.modelo.nodeFromName(l.datos->lado > 0.0f ? "LeftHand" : "RightHand");
		vkglTF::Node* b = l.manos.baculo;
		if (!mano || !b) {
			return;
		}
		vkglTF::Node* raiz = b->parent;
		b->translation = glm::vec3(0.0f);
		b->rotation = glm::quat(1.0f, 0.0f, 0.0f, 0.0f);
		b->scale = glm::vec3(1.0f);
		b->matrix = (raiz ? glm::inverse(raiz->getMatrix()) : glm::mat4(1.0f)) * mano->getMatrix() * l.relBaculo;
	}

	void posarLanzador(Lanzador& l, bool ataca)
	{
		vkglTF::Model& mago = l.modelo;
		if (muereLanzador(l)) {
			baculoEnLaMano(l);
			for (vkglTF::Node* n : mago.nodes) {
				n->update();
			}
			return;
		}
		float cuello = l.datos->cuello, cabeza = l.datos->cabeza;
#if defined(PS5_HOST_REFERENCE)
		if (const char* v = getenv("YUGI_CUELLO")) {
			cuello = (float)atof(v);
		}
		if (const char* v = getenv("YUGI_CABEZA")) {
			cabeza = (float)atof(v);
		}
#endif
		erguir(mago, "neck", cuello);
		erguir(mago, "Head", cabeza);
		if (ataca) {
			const float carga = suave(0.2f, T_SUELTA - 0.35f, tAtaque) * (1.0f - suave(T_SUELTA - 0.3f, T_SUELTA + 0.1f, tAtaque));
			const float impulso = suave(T_SUELTA - 0.3f, T_SUELTA + 0.1f, tAtaque) * (1.0f - suave(T_FIN_RAYO, T_FIN_RAYO + 0.9f, tAtaque));
			if (vkglTF::Node* torso = mago.nodeFromName("Spine01")) {
				const glm::vec3 lado = glm::angleAxis(frentePecho(l.indice), glm::vec3(0.0f, 1.0f, 0.0f)) * glm::vec3(1.0f, 0.0f, 0.0f);
				girarGlobal(torso, glm::angleAxis(glm::radians(-12.0f * carga + 10.0f * impulso), lado));
			}
		}
		posarBaculo(l, ataca);
		// en vida se recuerda como esta el baculo respecto de su mano (para cuando caiga)
		if (vkglTF::Node* mano = mago.nodeFromName(l.datos->lado > 0.0f ? "LeftHand" : "RightHand")) {
			if (vkglTF::Node* b = l.manos.baculo) {
				vkglTF::Node* raiz = b->parent;
				const glm::mat4 M = (raiz ? raiz->getMatrix() : glm::mat4(1.0f)) * b->matrix;
				l.relBaculo = glm::inverse(mano->getMatrix()) * M;
			}
		}
		for (vkglTF::Node* n : mago.nodes) {
			n->update();
		}
	}

	static void erguir(vkglTF::Model& modelo, const char* hueso, float grados)
	{
		if (vkglTF::Node* n = modelo.nodeFromName(hueso)) {
			n->rotation = glm::normalize(n->rotation * glm::angleAxis(glm::radians(grados), glm::vec3(1.0f, 0.0f, 0.0f)));
		}
	}

	// Personaje en su carta: de frente a la camara; durante el ataque, girado hacia el otro
	// Hacia donde mira el pecho del personaje en su pose actual (en el plano, en coordenadas del modelo):
	// perpendicular a la linea de hombro a hombro. Asi el giro hacia el rival corrige lo que la animacion
	// gira el cuerpo (algunas lo ponen de lado), para cualquier rival en cualquier carta.
	bool esLanzador(int i) const
	{
		for (const Lanzador& l : lanzadores) {
			if (l.indice == i) {
				return true;
			}
		}
		return false;
	}

	const vkglTF::Model& modeloDe(int i) const
	{
		for (const Lanzador& l : lanzadores) {
			if (l.indice == i) {
				return l.modelo;
			}
		}
		return guardian;
	}

	float frentePecho(int i) const
	{
		const vkglTF::Model& m = modeloDe(i);
		vkglTF::Node* der = const_cast<vkglTF::Model&>(m).nodeFromName("RightArm");
		vkglTF::Node* izq = const_cast<vkglTF::Model&>(m).nodeFromName("LeftArm");
		if (!der || !izq) {
			return 0.0f;
		}
		const glm::vec3 r = glm::vec3(der->getMatrix()[3]) - glm::vec3(izq->getMatrix()[3]);
		const glm::vec3 f = glm::cross(glm::vec3(0.0f, 1.0f, 0.0f), r);   // de frente, en +Z cuando esta derecho
		return atan2f(f.x, f.z);
	}

	glm::mat4 matrizPersonaje(int i, int otro) const
	{
		// de frente al monitor (la camara) en reposo; al atacar se da la vuelta de frente al rival y despues
		// vuelve. Siempre descontando lo que la animacion gira el pecho (para que quede de frente, no de lado)
		const glm::vec3 c = OJO - base(i);
		float giro = atan2f(c.x, c.z) - frentePecho(i);
		if (hayAtaque() && (i == atacante || i == objetivo)) {
			const glm::vec3 d = base(otro) - base(i);
			const float mirar = atan2f(d.x, d.z) - frentePecho(i);
			const float dif = remainderf(mirar - giro, 2.0f * glm::pi<float>());   // por el lado mas corto
			giro += dif * suave(0.0f, 0.6f, tAtaque) * (1.0f - suave(7.4f, 8.2f, tAtaque));
		}
		glm::mat4 caida(1.0f);
		if (hayAtaque() && i == objetivo && esLanzador(i)) {
			// Excel regla 3, derrota: "caer derrotado al piso", como el Guardian: retrocede con el golpe y cae de espaldas
			const glm::vec3 hacia = glm::normalize(base(otro) - base(i));
			const glm::vec3 lado = glm::normalize(glm::cross(glm::vec3(0.0f, 1.0f, 0.0f), hacia));
			const float vuelve = 1.0f - suave(7.4f, 8.2f, tAtaque);
			const float retro = suave(T_IMPACTO, T_IMPACTO + 0.25f, tAtaque) * vuelve;
			(void)lado;   // la caida la hace la animacion dying_backwards (clip 1); aqui solo el empujon del golpe
			caida = glm::translate(glm::mat4(1.0f), -hacia * 0.45f * retro);
		}
		return glm::translate(glm::mat4(1.0f), base(i) + glm::vec3(0.0f, 0.04f, 0.0f)) * caida *
		       glm::rotate(glm::mat4(1.0f), giro, glm::vec3(0.0f, 1.0f, 0.0f)) *
		       glm::scale(glm::mat4(1.0f), glm::vec3(ESCALA_PERSONAJE));
	}

	void dibujarNodoEsqueleto(VkCommandBuffer cmd, vkglTF::Node* nodo, bool imagenes)
	{
		if (nodo->mesh) {
			vkCmdBindDescriptorSets(cmd, VK_PIPELINE_BIND_POINT_GRAPHICS, pipelineLayoutEsqueleto, 2, 1, &nodo->mesh->uniformBuffer.descriptorSet, 0, nullptr);
			for (vkglTF::Primitive* p : nodo->mesh->primitives) {
				if (imagenes) {
					vkCmdBindDescriptorSets(cmd, VK_PIPELINE_BIND_POINT_GRAPHICS, pipelineLayoutEsqueleto, 1, 1, &p->material.descriptorSet, 0, nullptr);
				}
				vkCmdDrawIndexed(cmd, p->indexCount, 1, p->firstIndex, 0, 0);
			}
		}
		for (vkglTF::Node* hijo : nodo->children) {
			dibujarNodoEsqueleto(cmd, hijo, imagenes);
		}
	}

	void dibujarEsqueleto(VkCommandBuffer cmd, vkglTF::Model& modelo, const glm::mat4& matriz, glm::vec4 efecto, bool imagenes)
	{
		const Empuje empuje{ matriz, efecto, glm::vec4(0.0f) };
		vkCmdPushConstants(cmd, pipelineLayoutEsqueleto, VK_SHADER_STAGE_VERTEX_BIT | VK_SHADER_STAGE_FRAGMENT_BIT, 0, sizeof(Empuje), &empuje);
		const VkDeviceSize desde = 0;
		vkCmdBindVertexBuffers(cmd, 0, 1, &modelo.vertices.buffer, &desde);
		vkCmdBindIndexBuffer(cmd, modelo.indices.buffer, 0, VK_INDEX_TYPE_UINT32);
		for (vkglTF::Node* nodo : modelo.nodes) {
			dibujarNodoEsqueleto(cmd, nodo, imagenes);
		}
	}

	void dibujar(VkCommandBuffer cmd, vkglTF::Model& modelo, const glm::mat4& matriz, glm::vec4 efecto, glm::vec4 vida, bool imagenes,
	             glm::vec4 ojoA = glm::vec4(0.0f), glm::vec4 ojoB = glm::vec4(0.0f))
	{
		const Empuje empuje{ matriz, efecto, vida, ojoA, ojoB };
		vkCmdPushConstants(cmd, pipelineLayout, VK_SHADER_STAGE_VERTEX_BIT | VK_SHADER_STAGE_FRAGMENT_BIT, 0, sizeof(Empuje), &empuje);
		modelo.draw(cmd, imagenes ? vkglTF::RenderFlags::BindImages : 0, pipelineLayout);
	}

	void dibujarTodo(VkCommandBuffer cmd, bool imagenes)
	{
		dibujar(cmd, tablero, glm::mat4(1.0f), glm::vec4(0.0f, 0.35f, 0.0f, 0.0f), glm::vec4(0.0f), imagenes);
		for (size_t i = 0; i < NUM_MONSTRUOS; i++) {
			if ((!MAGO_FIJO && esLanzador((int)i)) || (!GUARDIAN_FIJO && (int)i == guardianIdx)) {
				continue;   // son los personajes con esqueleto, se dibujan despues
			}
			combate::Pose pose;
			const glm::mat4 mm = matrizMonstruo(i, &pose);
			const float dis = (int)i == objetivo && hayAtaque() ? pose.desintegrar : 0.0f;
			if (dis >= 0.999f || (!imagenes && dis > 0.5f)) {
				continue; // desaparecido (y sin sombra mientras se deshace)
			}
			const bool esKuriboh = (int)i == kuriboh;
			// sin deformar la malla (se veia como gelatina): todo el movimiento es del cuerpo entero
			const glm::vec4 vida(MONSTRUOS[i].x, MONSTRUOS[i].z, 0.0f, 0.0f);
			// el atacante brilla mas mientras carga
			const float holo = brilloHolo + pose.brillo;
			const float ojos = pose.ojos >= 0.0f ? glm::max(pose.ojos, parpado()) : parpado();
			dibujar(cmd, monstruos[i], mm, glm::vec4(holo, 0.6f, dis, 0.0f), vida, imagenes,
			        esKuriboh ? OJO_KURIBOH_A : glm::vec4(0.0f), esKuriboh ? glm::vec4(glm::vec3(OJO_KURIBOH_B), ojos) : glm::vec4(0.0f));
		}
		// las armas, en la mano de cada personaje
		if (atacante >= 0 && objetivo >= 0) {
			const glm::mat4 enMano = esLanzador(atacante) ? baculoDePie(matrizArma(armaMago, matrizPersonaje(atacante, objetivo))) : glm::mat4(1.0f);
			if (!MAGO_FIJO && !BACULO_EN_MODELO && esLanzador(atacante)) {
				dibujar(cmd, baculo, enMano, glm::vec4(brilloHolo + 1.2f * elevacion(), 0.7f, 0.0f, 0.0f), glm::vec4(0.0f), imagenes);
			}
			const float dis = objetivo == guardianIdx ? desintegracion() : 0.0f;
			const glm::mat4 guardianM = matrizPersonaje(guardianIdx, rivalDe(guardianIdx));
			const glm::mat4 espadaM = matrizArma(armaGuardian, guardianM);
			if (!GUARDIAN_FIJO && dis < 0.999f && (imagenes || dis < 0.5f)) {
				dibujar(cmd, espada, espadaM, glm::vec4(brilloHolo, 0.9f, dis, 0.0f), glm::vec4(0.0f), imagenes);
			}
			// el centro de la hoja de la espada: ahi pega el rayo mientras el Guardian se cubre
			const float largoEspada = espada.dimensions.max.y - espada.dimensions.min.y;
			const glm::vec3 hoja = glm::vec3(espadaM * glm::vec4(0.0f, espada.dimensions.min.y + 0.62f * largoEspada, 0.0f, 1.0f));
			// la punta del baculo carga energia azul y de ahi sale el rayo hasta el pecho del Guardian
			// la punta del baculo: en el Mago fijo, el ojo del baculo de su propio modelo; si no, la del baculo suelto
			const glm::vec3 punta = !esLanzador(atacante) ? origenRegla()
			                      : BACULO_EN_MODELO ? extremoHaciaRival()
			                      : MAGO_FIJO ? glm::vec3(matrizMonstruo((size_t)atacante) * glm::vec4(PUNTA_MAGO, 1.0f))
			                                  : glm::vec3(enMano * glm::vec4(0.0f, baculo.dimensions.max.y, 0.0f, 1.0f));
			// el rayo y sus chispas se dibujan al final, con la mezcla aditiva (dibujarEfectos)
			efPunta = punta;
			efDestino = objetivo != guardianIdx ? destinoRegla()
			            : GUARDIAN_FIJO ? glm::vec3(matrizMonstruo((size_t)objetivo) * glm::vec4(0.0f, 0.35f, 0.15f, 1.0f))
			                            : glm::mix(base(objetivo) + glm::vec3(0.0f, 1.55f, 0.0f), hoja,
			                                       suave(T_CUBRE, T_CUBRE + 0.25f, tAtaque) * (1.0f - suave(T_MUERE, T_MUERE + 0.3f, tAtaque)));
			vkCmdBindPipeline(cmd, VK_PIPELINE_BIND_POINT_GRAPHICS, imagenes ? pipelines.escena : pipelines.sombra);
		}
		// personajes con esqueleto
		if (atacante >= 0 && objetivo >= 0) {
			vkCmdBindPipeline(cmd, VK_PIPELINE_BIND_POINT_GRAPHICS, imagenes ? pipelines.escenaEsqueleto : pipelines.sombraEsqueleto);
			vkCmdBindDescriptorSets(cmd, VK_PIPELINE_BIND_POINT_GRAPHICS, pipelineLayoutEsqueleto, 0, 1, &descriptorSets[currentBuffer], 0, nullptr);
			const float holoMago = brilloHolo + 1.2f * elevacion();
			if (!MAGO_FIJO) {
				for (Lanzador& l : lanzadores) {
					const bool ataca = l.indice == atacante;
					const float disL = l.indice == objetivo ? desintegracion() : 0.0f;
					if (disL >= 0.999f || (!imagenes && disL > 0.5f)) {
						continue;
					}
					dibujarEsqueleto(cmd, l.modelo, matrizPersonaje(l.indice, rivalDe(l.indice)),
					                 glm::vec4(ataca ? holoMago : brilloHolo, 0.6f, disL, 0.0f), imagenes);
				}
			}
			const float dis = objetivo == guardianIdx ? desintegracion() : 0.0f;
			if (!GUARDIAN_FIJO && dis < 0.999f && (imagenes || dis < 0.5f)) {
				dibujarEsqueleto(cmd, guardian, matrizPersonaje(guardianIdx, rivalDe(guardianIdx)), glm::vec4(brilloHolo, 0.6f, dis, 0.0f), imagenes);
			}
		}
		if (imagenes && atacante >= 0 && objetivo >= 0) {
			dibujarEfectos(cmd);
		}
	}

	// ---------------------------------------------------------------- rayo electrico
	glm::vec3 efPunta{ 0.0f }, efDestino{ 0.0f };
	// Regla 3 del Excel del usuario (reglas-yugi.xlsx): los misticos lanzan 1 de 5 rayos al azar en cada ataque.
	// El color depende de QUIEN lo lanza (Mago azul, Maga morado; los demas: remake/diseno/reglas_combate.json,
	// "color_magia", sacado de su figura). La lluvia de estrellas no le gusto al usuario: la reemplazan los anillos
	enum TipoRayo { RAYO_ELECTRICO, RAYO_ESFERA, RAYO_LASER, RAYO_ANILLOS, RAYO_ESPIRAL, NUM_TIPOS_RAYO };
	int tipoRayo{ RAYO_ELECTRICO };
	uint32_t numAtaque{ 0 };
	glm::vec3 colHalo{ 0.18f, 0.45f, 1.6f }, colNucleo{ 0.85f, 0.92f, 1.0f };

	// al empezar cada ataque: sortea el rayo (distinto del anterior) y toma el color de magia del atacante.
	// YUGI_RAYO=0..4 lo fija (pruebas en el PC)
	void sortearRayo()
	{
		numAtaque++;
		const int previo = tipoRayo;
		tipoRayo = (int)(azar(numAtaque * 7919u + (uint32_t)(tiempo * 1000.0f)) * (float)NUM_TIPOS_RAYO) % NUM_TIPOS_RAYO;
		if (tipoRayo == previo) {
			tipoRayo = (tipoRayo + 1) % NUM_TIPOS_RAYO;
		}
		if (const char* f = getenv("YUGI_RAYO")) {
			tipoRayo = atoi(f) % NUM_TIPOS_RAYO;
		}
		colHalo = lanzadores[cual].datos->halo;
		colNucleo = lanzadores[cual].datos->nucleo;
	}

	static float azar(uint32_t n)
	{
		n = (n << 13u) ^ n;
		n = n * (n * n * 15731u + 789221u) + 1376312589u;
		return (float)(n & 0x7fffffffu) / 2147483647.0f;   // 0..1
	}

	// el extremo del baculo (adorno o punta afilada) que el Mago tiene levantado: de ahi sale la magia. Solo cambia
	// de extremo si el otro queda claramente mas alto (25 cm), para que el origen del rayo no salte
	bool usarPie{ false };
	glm::vec3 extremoHaciaRival()
	{
		const glm::mat4 m = matrizPersonaje(atacante, objetivo);
		const glm::vec3 a = puntaArma(lanzadores[cual].modelo, "Baculo", lanzadores[cual].datos->punta, m);
		const glm::vec3 b = puntaArma(lanzadores[cual].modelo, "Baculo", lanzadores[cual].datos->pie, m);
		if (!usarPie && b.y > a.y + 0.25f) {
			usarPie = true;
		} else if (usarPie && a.y > b.y + 0.25f) {
			usarPie = false;
		}
		return usarPie ? b : a;
	}

	// un tramo de rayo: cilindro de "desde" a "hasta"; brillo = intensidad, radio en metros
	void tramo(VkCommandBuffer cmd, glm::vec3 desde, glm::vec3 hasta, float radio, glm::vec3 color, float brillo)
	{
		const glm::vec3 d = hasta - desde;
		const float largo = glm::length(d);
		if (largo < 1e-4f) {
			return;
		}
		const glm::mat4 m = glm::translate(glm::mat4(1.0f), desde) * glm::mat4_cast(glm::quat(glm::vec3(0.0f, 1.0f, 0.0f), d / largo)) *
		                    glm::scale(glm::mat4(1.0f), glm::vec3(radio, largo, radio));
		// efecto.w = brillo; vida.xyz = color; vida.w = 1: modo resplandor (centro brillante, bordes suaves)
		dibujar(cmd, rayo, m, glm::vec4(0.0f, 0.0f, 0.0f, brillo), glm::vec4(color, 1.0f), true);
	}

	void bola(VkCommandBuffer cmd, glm::vec3 centro, float radio, glm::vec3 color, float brillo)
	{
		dibujar(cmd, esfera, glm::scale(glm::translate(glm::mat4(1.0f), centro), glm::vec3(radio)),
		        glm::vec4(0.0f, 0.0f, 0.0f, brillo), glm::vec4(color, 1.0f), true);
	}

	// Rayo quebrado de a hasta b: zigzag que cambia de forma ~25 veces por segundo, con ramas que se abren.
	// Cada tramo se dibuja dos veces: un nucleo fino casi blanco y un resplandor ancho azul.
	void relampago(VkCommandBuffer cmd, glm::vec3 a, glm::vec3 b, uint32_t semilla, float amplitud, float grosor, int ramas)
	{
		const int N = 16;
		const glm::vec3 d = b - a;
		const float largo = glm::length(d);
		const glm::vec3 eje = d / glm::max(largo, 1e-4f);
		glm::vec3 p1 = glm::normalize(glm::cross(eje, glm::vec3(0.0f, 1.0f, 0.0f)) + glm::vec3(1e-4f));
		const glm::vec3 p2 = glm::normalize(glm::cross(eje, p1));
		glm::vec3 pts[N + 1];
		for (int k = 0; k <= N; k++) {
			const float f = (float)k / N;
			const float env = sinf(3.14159f * f);   // quieto en los extremos
			const float ox = (azar(semilla * 97u + k * 13u) - 0.5f) * 2.0f;
			const float oy = (azar(semilla * 131u + k * 7u + 5u) - 0.5f) * 2.0f;
			pts[k] = a + d * f + (p1 * ox + p2 * oy) * amplitud * largo * env;
		}
		const glm::vec3 nucleo = colNucleo, halo = colHalo;
		for (int k = 0; k < N; k++) {
			tramo(cmd, pts[k], pts[k + 1], 0.055f * grosor, halo, 0.28f);
			tramo(cmd, pts[k], pts[k + 1], 0.022f * grosor, nucleo, 1.6f);
		}
		for (int r = 0; r < ramas; r++) {
			const int k = 2 + (int)(azar(semilla * 31u + r * 17u) * (N - 4));
			const glm::vec3 desvio = glm::normalize(eje * 0.6f + (p1 * (azar(semilla + r * 3u) - 0.5f) + p2 * (azar(semilla + r * 5u + 1u) - 0.5f)) * 2.2f);
			const float l = largo * (0.08f + 0.12f * azar(semilla * 7u + r));
			relampagoSimple(cmd, pts[k], pts[k] + desvio * l, semilla * 3u + r, grosor * 0.6f);
		}
	}

	void relampagoSimple(VkCommandBuffer cmd, glm::vec3 a, glm::vec3 b, uint32_t semilla, float grosor)
	{
		const int N = 5;
		const glm::vec3 d = b - a;
		const glm::vec3 eje = glm::normalize(d);
		const glm::vec3 p1 = glm::normalize(glm::cross(eje, glm::vec3(0.0f, 1.0f, 0.0f)) + glm::vec3(1e-4f));
		const glm::vec3 p2 = glm::normalize(glm::cross(eje, p1));
		glm::vec3 prev = a;
		for (int k = 1; k <= N; k++) {
			const float f = (float)k / N;
			glm::vec3 q = a + d * f;
			if (k < N) {
				q += (p1 * (azar(semilla * 11u + k) - 0.5f) + p2 * (azar(semilla * 19u + k) - 0.5f)) * glm::length(d) * 0.35f;
			}
			tramo(cmd, prev, q, 0.04f * grosor, colHalo, 0.25f);
			tramo(cmd, prev, q, 0.018f * grosor, colNucleo, 1.2f);
			prev = q;
		}
	}

	// ---------------------------------------------------------------- motor de reglas (Excel del usuario)
	bool esRigido(int i) const { return i >= 0 && !esLanzador(i) && i != guardianIdx; }
	int rivalDe(int i) const { return i == atacante ? objetivo : i == objetivo ? atacante : objetivo; }

	const combate::ReglaCarta* datosRegla(int i) const
	{
		if (i < 0) {
			return nullptr;
		}
		for (const combate::ReglaCarta& r : combate::TABLA_REGLAS) {
			if (strcmp(r.carta, MONSTRUOS[i].carta) == 0) {
				return &r;
			}
		}
		return nullptr;
	}

	const combate::Regla& reglaDe(int i) const
	{
		const combate::ReglaCarta* d = datosRegla(i);
#if defined(PS5_HOST_REFERENCE)
		// solo en el PC, para ver una regla con un modelo que ya esta en el tablero: YUGI_REGLA=kuriboh:maquina
		if (const char* v = getenv("YUGI_REGLA")) {
			const char* dos = strchr(v, ':');
			if (dos && (size_t)(dos - v) == strlen(MONSTRUOS[i].carta) && strncmp(v, MONSTRUOS[i].carta, dos - v) == 0) {
				return combate::reglaPorNombre(dos + 1);
			}
		}
#endif
		return combate::reglaPorNombre(d ? d->regla : "embestida");
	}

	combate::Situacion situacion(int i) const
	{
		combate::Situacion st;
		st.t = tAtaque;
		st.base = base(i);
		st.rival = base(rivalDe(i));
		st.hacia = glm::normalize(st.rival - st.base + glm::vec3(1e-4f, 0.0f, 0.0f));
		if (esRigido(i)) {
			const glm::vec3 tam = monstruos[i].dimensions.size;
			const float esc = glm::length(glm::vec3(glm::make_mat4(MONSTRUOS[i].matriz)[0]));
			st.alto = tam.y * esc;
			st.ancho = glm::max(tam.x, tam.z) * esc;
		} else {
			st.alto = 2.6f;
			st.ancho = 1.0f;
		}
		const combate::ReglaCarta* d = datosRegla(i);
		st.vuela = d && d->vuela;
		st.semilla = numAtaque * 977u + (uint32_t)i;
		st.halo = d ? glm::vec3(d->halo[0], d->halo[1], d->halo[2]) : colHalo;
		st.nucleo = d ? glm::vec3(d->nucleo[0], d->nucleo[1], d->nucleo[2]) : colNucleo;
		return st;
	}

	// de donde sale el ataque de un monstruo sin esqueleto (sigue a su cuerpo)
	glm::vec3 origenRegla() const
	{
		combate::Pose pa;
		matrizMonstruo((size_t)atacante, &pa);
		return reglaDe(atacante).origen(situacion(atacante)) + pa.desplazar;
	}

	// a donde llega: el pecho del atacado (un mago con esqueleto, o un monstruo sin esqueleto donde este ahora)
	glm::vec3 destinoRegla() const
	{
		if (!esRigido(objetivo)) {
			return base(objetivo) + glm::vec3(0.0f, 1.55f, 0.0f);
		}
		combate::Pose po;
		matrizMonstruo((size_t)objetivo, &po);
		return base(objetivo) + po.desplazar + glm::vec3(0.0f, 0.6f * situacion(objetivo).alto, 0.0f);
	}

	struct PincelVk : combate::Pincel {
		VulkanExample* v;
		VkCommandBuffer c;
		PincelVk(VulkanExample* v_, VkCommandBuffer c_) : v(v_), c(c_) {}
		void tramo(glm::vec3 a, glm::vec3 b, float r, glm::vec3 col, float br) override { v->tramo(c, a, b, r, col, br); }
		void bola(glm::vec3 p, float r, glm::vec3 col, float br) override { v->bola(c, p, r, col, br); }
		void relampago(glm::vec3 a, glm::vec3 b, uint32_t sem, float amp, float gr, int ramas) override { v->relampago(c, a, b, sem, amp, gr, ramas); }
	};

	void dibujarEfectosRegla(VkCommandBuffer cmd)
	{
		PincelVk pincel(this, cmd);
		const glm::vec3 halo0 = colHalo, nucleo0 = colNucleo;
		if (esRigido(atacante)) {
			const combate::Situacion st = situacion(atacante);
			colHalo = st.halo;
			colNucleo = st.nucleo;
			reglaDe(atacante).efecto(st, efPunta, efDestino, pincel);
		}
		if (esRigido(objetivo) && tAtaque >= combate::MUERE) {
			const combate::Situacion so = situacion(objetivo);
			colHalo = so.halo;
			colNucleo = so.nucleo;
			combate::Pose po;
			matrizMonstruo((size_t)objetivo, &po);
			reglaDe(objetivo).efectoDerrota(so, base(objetivo) + po.desplazar + glm::vec3(0.0f, 0.4f * so.alto, 0.0f), pincel);
		}
		colHalo = halo0;
		colNucleo = nucleo0;
	}

	// prepara el enfrentamiento n: quien ataca a quien; a los magos les sortea el rayo
	void elegirDuelo(size_t n)
	{
		duelo = n % NUM_ENFRENTAMIENTOS;
		atacante = indice(ENFRENTAMIENTOS[duelo].atacante);
		objetivo = indice(ENFRENTAMIENTOS[duelo].objetivo);
		usarPie = false;
		for (size_t k = 0; k < NUM_LANZADORES; k++) {
			if (lanzadores[k].indice == atacante) {
				cual = k;
			}
		}
		if (esLanzador(atacante)) {
			sortearRayo();
		} else {
			numAtaque++;
		}
	}

	// el siguiente enfrentamiento de los que estan en juego (o el fijo de YUGI_DUELO en el PC)
	size_t siguienteDuelo() const
	{
#if defined(PS5_HOST_REFERENCE)
		if (const char* v = getenv("YUGI_DUELO")) {
			return (size_t)atoi(v) % NUM_ENFRENTAMIENTOS;
		}
		if (const char* l = getenv("YUGI_LANZADOR")) {
			return (size_t)atoi(l) % 2;
		}
#endif
		for (size_t k = 1; k <= NUM_ENFRENTAMIENTOS; k++) {
			const size_t n = (duelo + k) % NUM_ENFRENTAMIENTOS;
			if (ENFRENTAMIENTOS[n].enJuego) {
				return n;
			}
		}
		return 0;
	}

	void dibujarEfectos(VkCommandBuffer cmd)
	{
		if (!hayAtaque()) {
			return;
		}
		vkCmdBindPipeline(cmd, VK_PIPELINE_BIND_POINT_GRAPHICS, pipelines.efectos);
		vkCmdBindDescriptorSets(cmd, VK_PIPELINE_BIND_POINT_GRAPHICS, pipelineLayout, 0, 1, &descriptorSets[currentBuffer], 0, nullptr);
		dibujarEfectosRegla(cmd);
		if (!esLanzador(atacante)) {
			return;   // el ataque de un monstruo sin esqueleto lo dibuja su regla
		}
		const uint32_t paso = (uint32_t)(tAtaque * 25.0f);   // la forma del rayo cambia 25 veces por segundo
		// carga: un nucleo que late en la punta, con chispas electricas a su alrededor
		const float carga = suave(0.4f, T_SUELTA, tAtaque) * (1.0f - suave(T_FIN_RAYO - 0.2f, T_FIN_RAYO + 0.3f, tAtaque));
		if (carga > 0.0f) {
			const float lat = 1.0f + 0.25f * sinf(tAtaque * 38.0f);
			bola(cmd, efPunta, 0.30f * carga * lat, colHalo, 0.35f);
			bola(cmd, efPunta, 0.10f * carga * lat, colNucleo, 1.4f);
			for (int k = 0; k < 4; k++) {
				const glm::vec3 dir = glm::normalize(glm::vec3(azar(paso * 5u + k) - 0.5f, azar(paso * 7u + k + 9u) - 0.5f, azar(paso * 3u + k + 4u) - 0.5f));
				relampagoSimple(cmd, efPunta, efPunta + dir * 0.45f * carga, paso * 13u + k, 0.8f);
			}
		}
		// la esfera viaja ANTES de soltar: llega al rival justo en T_SUELTA, cuando el rival recibe el golpe
		if (tipoRayo == RAYO_ESFERA) {
			const float viaje = suave(T_SUELTA - 0.35f, T_SUELTA, tAtaque);
			if (viaje > 0.0f && viaje < 1.0f) {
				const glm::vec3 p = glm::mix(efPunta, efDestino, viaje);
				const float lat = 1.0f + 0.2f * sinf(tAtaque * 40.0f);
				bola(cmd, p, 0.34f * lat, colHalo, 0.4f);
				bola(cmd, p, 0.13f * lat, colNucleo, 1.6f);
				for (int k = 1; k <= 6; k++) {   // estela
					const glm::vec3 q = glm::mix(efPunta, efDestino, glm::max(0.0f, viaje - 0.05f * k));
					bola(cmd, q, 0.2f * (1.0f - k / 7.0f), colHalo, 0.25f);
				}
			}
		}
		// el rayo
		const float grosor = rayoActivo();
		if (grosor > 0.0f) {
			const glm::vec3 d = efDestino - efPunta;
			const float largo = glm::length(d);
			const glm::vec3 eje = d / glm::max(largo, 1e-4f);
			const glm::vec3 p1 = glm::normalize(glm::cross(eje, glm::vec3(0.0f, 1.0f, 0.0f)) + glm::vec3(1e-4f));
			const glm::vec3 p2 = glm::normalize(glm::cross(eje, p1));
			if (tipoRayo == RAYO_ELECTRICO) {
				relampago(cmd, efPunta, efDestino, paso + 1u, 0.06f, grosor, 3);
				relampago(cmd, efPunta, efDestino, paso * 7u + 3u, 0.09f, grosor * 0.55f, 1);   // un segundo hilo mas fino
			} else if (tipoRayo == RAYO_LASER) {
				// haz recto y grueso que late; anillos que corren por el haz hacia el rival
				const float lat = 1.0f + 0.15f * sinf(tAtaque * 55.0f);
				tramo(cmd, efPunta, efDestino, 0.16f * grosor * lat, colHalo, 0.3f);
				tramo(cmd, efPunta, efDestino, 0.06f * grosor * lat, colNucleo, 1.7f);
				for (int k = 0; k < 5; k++) {
					const float f = fmodf(tAtaque * 2.2f + k * 0.2f, 1.0f);
					bola(cmd, efPunta + d * f, 0.11f * grosor, colHalo, 0.5f);
				}
			} else if (tipoRayo == RAYO_ESPIRAL) {
				// dos hilos de energia que giran uno alrededor del otro hasta el rival
				const int N = 28;
				for (int h = 0; h < 2; h++) {
					glm::vec3 prev = efPunta;
					for (int k = 1; k <= N; k++) {
						const float f = (float)k / N;
						const float a = f * 6.2832f * 3.0f + tAtaque * 9.0f + h * 3.1416f;
						const float r = 0.22f * sinf(3.1416f * f) * grosor;
						const glm::vec3 q = efPunta + d * f + (p1 * cosf(a) + p2 * sinf(a)) * r;
						tramo(cmd, prev, q, 0.05f * grosor, colHalo, 0.35f);
						tramo(cmd, prev, q, 0.018f * grosor, colNucleo, 1.3f);
						prev = q;
					}
				}
			} else if (tipoRayo == RAYO_ANILLOS) {
				// ondas de energia en forma de aro que salen del baculo una tras otra y crecen al llegar al rival,
				// unidas por un hilo fino
				tramo(cmd, efPunta, efDestino, 0.03f * grosor, colHalo, 0.35f);
				const int SEG = 18;
				for (int k = 0; k < 4; k++) {
					const float f = fmodf(tAtaque * 1.6f + k * 0.25f, 1.0f);
					const glm::vec3 c = efPunta + d * f;
					const float r = (0.12f + 0.38f * f) * grosor;
					const float brillo = 1.0f - 0.6f * f;
					glm::vec3 prev = c + p1 * r;
					for (int q = 1; q <= SEG; q++) {
						const float a = 6.2832f * q / SEG;
						const glm::vec3 pt = c + (p1 * cosf(a) + p2 * sinf(a)) * r;
						tramo(cmd, prev, pt, 0.05f * grosor, colHalo, 0.4f * brillo);
						tramo(cmd, prev, pt, 0.018f * grosor, colNucleo, 1.3f * brillo);
						prev = pt;
					}
				}
			}
			// impacto: resplandor y chispas que saltan
			const float lat = 1.0f + 0.3f * sinf(tAtaque * 47.0f);
			bola(cmd, efDestino, 0.45f * grosor * lat, colHalo, 0.3f);
			bola(cmd, efDestino, 0.14f * grosor * lat, colNucleo, 1.5f);
			for (int k = 0; k < 6; k++) {
				const glm::vec3 dir = glm::normalize(glm::vec3(azar(paso * 23u + k) - 0.5f, azar(paso * 29u + k + 2u) - 0.2f, azar(paso * 31u + k + 6u) - 0.5f));
				relampagoSimple(cmd, efDestino, efDestino + dir * (0.35f + 0.35f * azar(paso + k * 41u)), paso * 17u + k, 0.7f);
			}
		}
	}

	void prepararCapturas()
	{
#if !defined(PS5_HOST_REFERENCE)
		const std::string raiz = getAssetPath() + "../";
		std::ifstream pedido(raiz + "capturas.txt");
		if (!pedido) {
			return;
		}
		// pase de un solo uso: el archivo lo deja el ciclo automatico justo antes de abrir el juego; se borra al
		// leerlo, asi una apertura manual posterior arranca normal (sin fotos ni cierre automatico)
		std::string contenido((std::istreambuf_iterator<char>(pedido)), std::istreambuf_iterator<char>());
		pedido.close();
		remove((raiz + "capturas.txt").c_str());
		std::istringstream pedidoTexto(contenido);
		std::string palabra;
		while (pedidoTexto >> palabra) {
			if (palabra == "video") {
				pedidoTexto >> videoFps;
			} else if (palabra == "cerrar_al_terminar") {
				cerrarAlTerminar = true;
			} else if (palabra == "inspeccion") {
				inspeccion = true;
			} else {
				momentosCaptura.push_back((float)atof(palabra.c_str()));
			}
		}
		if (momentosCaptura.empty() && videoFps <= 0.0f) {
			momentosCaptura = { 0.3f, 1.2f, 1.9f, 2.3f, 3.2f, 4.6f, 6.0f };
		}
		carpetaCapturas = raiz + "capturas/";
		mkdir(carpetaCapturas.c_str(), 0777);
		chmod(carpetaCapturas.c_str(), 0777);
		if (videoFps > 0.0f) {
			mkdir((carpetaCapturas + "video").c_str(), 0777);
			chmod((carpetaCapturas + "video").c_str(), 0777);
		}
#endif
	}

	// pide a la base que copie la pantalla de este cuadro (la escribe en submitFrame)
	void sacarFoto(const std::string& nombre)
	{
		ps5.screenshotPath = carpetaCapturas + nombre + ".ppm";
		ps5.capturaPedida = true;
	}

	// Salida sin manos: cerrar.txt en la carpeta del juego (se borra), o el fin de la grabacion pedida
	void revisarCierre()
	{
#if !defined(PS5_HOST_REFERENCE)
		if (cerrarAlTerminar && ataquesVistos >= 1 && !hayAtaque() && (!inspeccion || faseInsp >= 4)) {
			// se espera un poco: las ultimas fotos se escriben en otro hilo
			if (tSalida < 0.0f) {
				tSalida = tiempo;
			} else if (tiempo - tSalida > 2.5f) {
				quit = true;
			}
			return;
		}
		if (tiempo >= revisarCerrar) {
			revisarCerrar = tiempo + 1.0f;
			const std::string pedido = getAssetPath() + "../cerrar.txt";
			if (access(pedido.c_str(), F_OK) == 0) {
				remove(pedido.c_str());
				quit = true;
			}
		}
#endif
	}

	void fotoJpg(const char* nombre)
	{
		ps5.screenshotPath = carpetaCapturas + nombre + ".jpg";
		ps5.capturaPedida = true;
	}

	void inspeccionar()
	{
		if (!inspeccion || carpetaCapturas.empty() || faseInsp >= 4) {
			return;
		}
		if (faseInsp == 0) {
			if (ataquesVistos >= 1 && !hayAtaque()) {
				faseInsp = 1;
				pasoInsp = cuadrosInsp = 0;
				ataquesSolos = false;
			}
			return;
		}
		if (faseInsp == 1) {
			static const int angulos[3] = { 0, 40, -40 };
			if (pasoInsp >= (int)NUM_MONSTRUOS * 3) {
				faseInsp = 2;
				tAtaque = 0.0f;
				ataquesVistos++;
				fotoAtaqueInsp = 0;
				return;
			}
			const int i = pasoInsp / 3;
			const float a = glm::radians((float)angulos[pasoInsp % 3]);
			const bool chico = i == kuriboh;
			// de cerca: el monstruo llena la pantalla (los 4 cuadrantes de la revision muestran cabeza, manos,
			// cuerpo y pies)
			const float dist = chico ? 2.1f : 3.0f;
			miraInsp = base(i) + glm::vec3(0.0f, chico ? 0.75f : 1.3f, 0.0f);
			ojoInsp = miraInsp + glm::vec3(sinf(a) * dist, dist * 0.18f, cosf(a) * dist);
			camInsp = true;
			if (++cuadrosInsp == 5) {
				char n[64];
				snprintf(n, sizeof(n), "insp_%s_%+03d", MONSTRUOS[i].carta, angulos[pasoInsp % 3]);
				fotoJpg(n);
			} else if (cuadrosInsp > 6) {
				cuadrosInsp = 0;
				pasoInsp++;
			}
			return;
		}
		// 2 y 3: el ataque otra vez, con la camara cerca del Mago (2) o del Guardian (3), de frente y un poco de lado
		const int quien = faseInsp == 2 ? atacante : objetivo;
		const int otro = faseInsp == 2 ? objetivo : atacante;
		const glm::vec3 hacia = glm::normalize(base(otro) - base(quien));
		const glm::vec3 lado = glm::normalize(glm::cross(glm::vec3(0.0f, 1.0f, 0.0f), hacia));
		miraInsp = base(quien) + glm::vec3(0.0f, 1.5f, 0.0f);
		ojoInsp = miraInsp + hacia * 0.8f + lado * 3.0f + glm::vec3(0.0f, 0.5f, 0.0f);   // de costado: el rayo cruza la pantalla
		camInsp = true;
		static const float momentos[] = { 0.3f, 1.0f, 1.5f, 1.8f, 2.2f, 2.7f, 3.2f, 3.8f, 4.6f };
		if (hayAtaque() && fotoAtaqueInsp < 9 && tAtaque >= momentos[fotoAtaqueInsp]) {
			char n[64];
			snprintf(n, sizeof(n), "insp_ataque_%s_%.1fs", faseInsp == 2 ? "mago" : "guardian", momentos[fotoAtaqueInsp]);
			fotoAtaqueInsp++;
			fotoJpg(n);
		}
		if (!hayAtaque()) {
			if (faseInsp == 2) {
				faseInsp = 3;
				tAtaque = 0.0f;
				ataquesVistos++;
				fotoAtaqueInsp = 0;
			} else {
				faseInsp = 4;
				camInsp = false;
			}
		}
	}

	void revisarCapturas()
	{
		if (carpetaCapturas.empty()) {
			return;
		}
		if (!fotoReposo && tiempo > 2.5f) {
			fotoReposo = true;
			sacarFoto("00_reposo");
		} else if (ataquesVistos == 1 && hayAtaque() && siguienteCaptura < momentosCaptura.size() &&
		           tAtaque >= momentosCaptura[siguienteCaptura]) {
			char nombre[32];
			snprintf(nombre, sizeof(nombre), "%02d_ataque_%.1fs", (int)siguienteCaptura + 1, momentosCaptura[siguienteCaptura]);
			siguienteCaptura++;
			sacarFoto(nombre);
		} else if (videoFps > 0.0f && ataquesVistos == 1 && hayAtaque() && tAtaque >= cuadroVideo / videoFps) {
			// un cuadro de video (JPG): el cuadro N corresponde al segundo N / fps del ataque
			char nombre[48];
			snprintf(nombre, sizeof(nombre), "video/%04d", cuadroVideo);
			cuadroVideo = (int)(tAtaque * videoFps) + 1;
			ps5.screenshotPath = carpetaCapturas + nombre + ".jpg";
			ps5.capturaPedida = true;
		}
	}

	void prepare() override
	{
		VulkanExampleBase::prepare();
#if defined(PS5_HOST_REFERENCE)
		if (getenv("YUGI_ATAQUE_YA")) {
			proximoAtaque = 0.3f;   // videos en el PC: el ataque empieza enseguida
		}
#endif
		prepararCapturas();
		loadAssets();
		prepararSombra();
		prepareUniformBuffers();
		setupDescriptors();
		preparePipelines();
		interfazDuelo.preparar(vulkanDevice, queue, swapChain.colorFormat, depthFormat, pipelineCache, getAssetPath(), getShadersPath());
		prepared = true;
	}

	void pasadaSombra(VkCommandBuffer cmd)
	{
		const VkImageSubresourceRange rango{ VK_IMAGE_ASPECT_DEPTH_BIT, 0, 1, 0, 1 };
		vks::tools::insertImageMemoryBarrier(cmd, sombra.imagen,
			VK_ACCESS_SHADER_READ_BIT, VK_ACCESS_DEPTH_STENCIL_ATTACHMENT_WRITE_BIT,
			VK_IMAGE_LAYOUT_UNDEFINED, VK_IMAGE_LAYOUT_DEPTH_ATTACHMENT_OPTIMAL,
			VK_PIPELINE_STAGE_FRAGMENT_SHADER_BIT, VK_PIPELINE_STAGE_EARLY_FRAGMENT_TESTS_BIT | VK_PIPELINE_STAGE_LATE_FRAGMENT_TESTS_BIT,
			rango);
		VkRenderingAttachmentInfo profundidad{
			.sType = VK_STRUCTURE_TYPE_RENDERING_ATTACHMENT_INFO,
			.imageView = sombra.vista,
			.imageLayout = VK_IMAGE_LAYOUT_DEPTH_ATTACHMENT_OPTIMAL,
			.loadOp = VK_ATTACHMENT_LOAD_OP_CLEAR,
			.storeOp = VK_ATTACHMENT_STORE_OP_STORE,
			.clearValue = { .depthStencil = { 1.0f, 0 } },
		};
		VkRenderingInfo info{
			.sType = VK_STRUCTURE_TYPE_RENDERING_INFO,
			.renderArea = { { 0, 0 }, { TAM_SOMBRA, TAM_SOMBRA } },
			.layerCount = 1,
			.pDepthAttachment = &profundidad,
		};
		vkCmdBeginRendering(cmd, &info);
		VkViewport viewport = vks::initializers::viewport((float)TAM_SOMBRA, (float)TAM_SOMBRA, 0.0f, 1.0f);
		vkCmdSetViewport(cmd, 0, 1, &viewport);
		VkRect2D scissor = vks::initializers::rect2D(TAM_SOMBRA, TAM_SOMBRA, 0, 0);
		vkCmdSetScissor(cmd, 0, 1, &scissor);
		vkCmdBindDescriptorSets(cmd, VK_PIPELINE_BIND_POINT_GRAPHICS, pipelineLayout, 0, 1, &descriptorSets[currentBuffer], 0, nullptr);
		vkCmdBindPipeline(cmd, VK_PIPELINE_BIND_POINT_GRAPHICS, pipelines.sombra);
		dibujarTodo(cmd, false);
		vkCmdEndRendering(cmd);
		vks::tools::insertImageMemoryBarrier(cmd, sombra.imagen,
			VK_ACCESS_DEPTH_STENCIL_ATTACHMENT_WRITE_BIT, VK_ACCESS_SHADER_READ_BIT,
			VK_IMAGE_LAYOUT_DEPTH_ATTACHMENT_OPTIMAL, VK_IMAGE_LAYOUT_DEPTH_STENCIL_READ_ONLY_OPTIMAL,
			VK_PIPELINE_STAGE_EARLY_FRAGMENT_TESTS_BIT | VK_PIPELINE_STAGE_LATE_FRAGMENT_TESTS_BIT, VK_PIPELINE_STAGE_FRAGMENT_SHADER_BIT,
			rango);
	}

	void buildCommandBuffer()
	{
		VkCommandBuffer cmd = drawCmdBuffers[currentBuffer];
		VkCommandBufferBeginInfo cmdBufInfo = vks::initializers::commandBufferBeginInfo();
		VK_CHECK_RESULT(vkBeginCommandBuffer(cmd, &cmdBufInfo));
		pasadaSombra(cmd);
		beginDynamicRendering(cmd);
		VkViewport viewport = vks::initializers::viewport((float)width, (float)height, 0.0f, 1.0f);
		vkCmdSetViewport(cmd, 0, 1, &viewport);
		VkRect2D scissor = vks::initializers::rect2D(width, height, 0, 0);
		vkCmdSetScissor(cmd, 0, 1, &scissor);
		vkCmdBindDescriptorSets(cmd, VK_PIPELINE_BIND_POINT_GRAPHICS, pipelineLayout, 0, 1, &descriptorSets[currentBuffer], 0, nullptr);
		vkCmdBindPipeline(cmd, VK_PIPELINE_BIND_POINT_GRAPHICS, pipelines.escena);
		dibujarTodo(cmd, true);
		interfazDuelo.dibujar(cmd, currentBuffer, uniformData.proyeccion * uniformData.vista, (float)width, (float)height);
		drawUI(cmd);
		endDynamicRendering(cmd);
		VK_CHECK_RESULT(vkEndCommandBuffer(cmd));
	}

	void avanzarAtaque()
	{
		// la X lanza un ataque (si la ventana de ajustes no esta abierta: ahi la X es su boton)
		pad_player(0, &mando);
		const bool equis = (mando.pressed & PAD_CROSS) && !ui.visible;
		if (!hayAtaque() && (equis || (ataquesSolos && tiempo >= proximoAtaque))) {
			elegirDuelo(siguienteDuelo());
			tAtaque = 0.0f;
			ataquesVistos++;
		} else if (hayAtaque()) {
			tAtaque += frameTimer;
			if (tAtaque > DURACION_ATAQUE) {
				tAtaque = -1.0f;
				proximoAtaque = tiempo + CADA_ATAQUE - DURACION_ATAQUE;
			}
		}
	}

	void render() override
	{
		if (!prepared) {
			return;
		}
		VulkanExampleBase::prepareFrame();
		tiempo += frameTimer;
		avanzarAtaque();
		interfazDuelo.actualizar(mando, frameTimer, !ui.visible);   // el puntero (cruceta/palanca; no usa X ni OPTIONS)
		revisarCapturas();
		inspeccionar();
		revisarCierre();
		actualizarPersonajes();
		updateUniformBuffers();
		buildCommandBuffer();
		VulkanExampleBase::submitFrame();
	}

	void OnUpdateUIOverlay(vks::UIOverlay *overlay) override
	{
		if (overlay->header("Ajustes")) {
			overlay->checkBox("Animar monstruos", &animar);
			overlay->checkBox("Camara que respira", &respirar);
			overlay->checkBox("Ataques automaticos", &ataquesSolos);
			overlay->sliderFloat("Brillo holografico", &brilloHolo, 0.0f, 1.5f);
			if (overlay->button("Atacar ahora") && !hayAtaque()) {
				tAtaque = 0.0f;
			}
			if (overlay->button("Salir")) {
				quit = true;
			}
		}
	}
};

VULKAN_EXAMPLE_MAIN()
