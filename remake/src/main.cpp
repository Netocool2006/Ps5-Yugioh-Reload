// Yugi Reload 2026 - Base 1 (escenario completo): tablero lleno en ambos lados, panel de carta a la derecha,
// barra de fases, LP, turno, contadores, monstruos en ataque/defensa/boca abajo, trampa activandose,
// espada de ataque y monstruo explotando. Sin reglas ni movimiento de juego todavia: es una "foto" de un duelo.
//
// Controles: raton sobre una carta (mano o campo) = se muestra en el panel derecho | F1 = FPS | F12 = captura
// Argumentos: --captura RUTA.png [--cuadros N] [--hover I]
#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <map>
#include <sstream>
#include <string>
#include <vector>
#include "raylib.h"
#include "raymath.h"
#include "rlgl.h"
#include "plataforma.h"

// ------------------------------------------------------------------ datos
struct Carta {
    std::string id, nombre, clase, descripcion;
    int atk = 0, def = 0, nivel = 0;
    bool efecto = false, tieneFigura = false;
    float aspecto = 1.0f;
    Texture2D cara{}, figura{}, prof{};
    Material mat{};
};

struct Zona { float x = 0, z = 0; };

enum Modo { ATAQUE, DEFENSA, BOCA_ABAJO, BOCA_ABAJO_DEF, BOCA_ARRIBA };
enum Estado { NORMAL, ATACANDO, OBJETIVO, EXPLOTANDO, ACTIVANDO };

struct EnCampo {
    std::string zona, carta;
    Modo modo = ATAQUE;
    Estado estado = NORMAL;
    float aparece = 0.0f;
};

struct Pila { std::string zona, arriba; int cantidad; };   // mazo, cementerio, fusion

static std::map<std::string, Carta> cartas;
static std::map<std::string, Zona> zonas;
static std::string R;

static const float ALTO_FIGURA = 3.3f;
static const float INCLINACION = 30.0f;

static bool EsRival(const std::string& zona) { return zona.rfind("rival", 0) == 0; }

static Texture2D CargarTextura(const std::string& ruta) {
    if (!FileExists(ruta.c_str())) return Texture2D{};
    Texture2D t = LoadTexture(ruta.c_str());
    GenTextureMipmaps(&t);
    SetTextureFilter(t, TEXTURE_FILTER_TRILINEAR);
    return t;
}

static std::string LeerTexto(const std::string& ruta) {
    std::ifstream f(ruta);
    std::stringstream ss; ss << f.rdbuf();
    return ss.str();
}

static void CargarZonas() {
    std::ifstream f(R + "ui/tablero.txt");
    std::string id; float x, z;
    while (f >> id >> x >> z) zonas[id] = {x, z};
}

static void CargarCartas(Shader sh) {
    std::ifstream f(R + "cartas/cartas.txt");
    std::string linea;
    while (std::getline(f, linea)) {
        if (linea.empty()) continue;
        std::vector<std::string> c;
        std::stringstream ss(linea); std::string campo;
        while (std::getline(ss, campo, '|')) c.push_back(campo);
        if (c.size() < 9) continue;
        Carta k;
        k.id = c[0]; k.nombre = c[1]; k.atk = std::atoi(c[2].c_str()); k.def = std::atoi(c[3].c_str());
        k.nivel = std::atoi(c[4].c_str()); k.efecto = c[5] == "1"; k.clase = c[8];
        float fw = (float)std::atof(c[6].c_str()), fh = (float)std::atof(c[7].c_str());
        std::string d = R + "cartas/" + k.id + "/";
        k.cara = CargarTextura(d + "cara.png");
        k.descripcion = LeerTexto(d + "descripcion.txt");
        k.tieneFigura = fw > 0 && fh > 0;
        if (k.tieneFigura) {
            k.aspecto = fw / fh;
            k.figura = CargarTextura(d + "figura.png");
            if (!k.figura.id) k.tieneFigura = false;   // figura aun no generada: solo se ve la carta
            k.prof = LoadTexture((d + "profundidad.png").c_str());
            SetTextureFilter(k.prof, TEXTURE_FILTER_BILINEAR);
            k.mat = LoadMaterialDefault();
            k.mat.shader = sh;
            k.mat.maps[MATERIAL_MAP_DIFFUSE].texture = k.figura;
            k.mat.maps[MATERIAL_MAP_SPECULAR].texture = k.prof;
        }
        cartas[k.id] = k;
    }
}

static Mesh MallaFigura(int res) {
    Mesh m{};
    int n = (res + 1) * (res + 1);
    m.vertexCount = n; m.triangleCount = res * res * 2;
    m.vertices = (float*)MemAlloc(n * 3 * sizeof(float));
    m.texcoords = (float*)MemAlloc(n * 2 * sizeof(float));
    m.normals = (float*)MemAlloc(n * 3 * sizeof(float));
    m.indices = (unsigned short*)MemAlloc(m.triangleCount * 3 * sizeof(unsigned short));
    for (int j = 0; j <= res; j++)
        for (int i = 0; i <= res; i++) {
            int v = j * (res + 1) + i;
            float u = (float)i / res, h = (float)j / res;
            m.vertices[v * 3 + 0] = u - 0.5f; m.vertices[v * 3 + 1] = h; m.vertices[v * 3 + 2] = 0.0f;
            m.texcoords[v * 2 + 0] = u; m.texcoords[v * 2 + 1] = 1.0f - h;
            m.normals[v * 3 + 0] = 0; m.normals[v * 3 + 1] = 0; m.normals[v * 3 + 2] = 1;
        }
    int k = 0;
    for (int j = 0; j < res; j++)
        for (int i = 0; i < res; i++) {
            unsigned short a = j * (res + 1) + i, b = a + 1, c = a + (res + 1), d = c + 1;
            m.indices[k++] = a; m.indices[k++] = b; m.indices[k++] = d;
            m.indices[k++] = a; m.indices[k++] = d; m.indices[k++] = c;
        }
    UploadMesh(&m, false);
    return m;
}

// ------------------------------------------------------------------ escena
struct Escena {
    Model mesa{};
    Mesh cartaPlana{};
    Material matCarta{};
    Mesh figura{};
    Shader shFigura{};
    int locTiempo = -1, locFase = -1, locRelieve = -1, locAparicion = -1;
    Texture2D dorso{}, sombra{}, brillo{}, espada{}, explosion{}, botonOff{}, botonOn{}, panelCarta{}, panelLp{};
    Font fNombre{}, fNum{};
    std::vector<EnCampo> campo;
    std::vector<Pila> pilas;
    std::vector<std::string> manoJugador;
    int manoRival = 4;
    int lpJugador = 6400, lpRival = 4300, turno = 5, faseActiva = 3;
    Texture2D fondoCampo{};   // paisaje de la magia de campo activa (como en el original)
};

static void DibujarCartaTumbada(Escena& e, Texture2D tex, float x, float z, bool rival, float alto = 0.012f,
                                bool girada = false, Color tinte = WHITE) {
    e.matCarta.maps[MATERIAL_MAP_DIFFUSE].texture = tex;
    e.matCarta.maps[MATERIAL_MAP_DIFFUSE].color = tinte;
    float rot = (rival ? PI : 0.0f) + (girada ? PI / 2 : 0.0f);
    // canto de la carta (grosor real), apenas mas grande que la cara y por debajo de ella
    rlPushMatrix();
    rlTranslatef(x, alto - 0.018f, z);
    rlRotatef(rot * RAD2DEG, 0, 1, 0);
    DrawCube({0, 0, 0}, 1.02f, 0.035f, 1.47f, {22, 18, 14, 255});
    rlPopMatrix();
    DrawMesh(e.cartaPlana, e.matCarta, MatrixMultiply(MatrixRotateY(rot), MatrixTranslate(x, alto, z)));
    e.matCarta.maps[MATERIAL_MAP_DIFFUSE].color = WHITE;
}

// carta levantada (trampa activandose): de pie e inclinada hacia la camara, con halo
static void DibujarCartaLevantada(Escena& e, Texture2D tex, float x, float z, float t, Color halo) {
    float pulso = 0.75f + 0.25f * sinf(t * 4.0f);
    Matrix m = MatrixMultiply(MatrixMultiply(MatrixRotateX(-68.0f * DEG2RAD), MatrixRotateY(PI)),
                              MatrixTranslate(x, 0.82f, z));
    // halo detras de la carta
    rlSetBlendMode(BLEND_ADDITIVE);
    e.matCarta.maps[MATERIAL_MAP_DIFFUSE].texture = e.brillo;
    e.matCarta.maps[MATERIAL_MAP_DIFFUSE].color = Fade(halo, pulso);
    DrawMesh(e.cartaPlana, e.matCarta, MatrixMultiply(MatrixScale(2.1f, 1.0f, 1.6f),
             MatrixMultiply(MatrixMultiply(MatrixRotateX(-68.0f * DEG2RAD), MatrixRotateY(PI)), MatrixTranslate(x, 0.80f, z - 0.05f))));
    rlSetBlendMode(BLEND_ALPHA);
    e.matCarta.maps[MATERIAL_MAP_DIFFUSE].texture = tex;
    e.matCarta.maps[MATERIAL_MAP_DIFFUSE].color = WHITE;
    DrawMesh(e.cartaPlana, e.matCarta, m);
}

static void DibujarSombra(Escena& e, float x, float z, float ancho) {
    rlSetTexture(e.sombra.id);
    rlBegin(RL_QUADS);
    rlColor4ub(0, 0, 0, 170);
    float w = ancho * 0.55f, d = 0.38f, y = 0.03f;
    rlTexCoord2f(0, 0); rlVertex3f(x - w, y, z - d);
    rlTexCoord2f(0, 1); rlVertex3f(x - w, y, z + d);
    rlTexCoord2f(1, 1); rlVertex3f(x + w, y, z + d);
    rlTexCoord2f(1, 0); rlVertex3f(x + w, y, z - d);
    rlEnd();
    rlSetTexture(0);
}

static void DibujarFigura(Escena& e, Carta& c, float x, float z, float t, float aparicion, float fase, float escala, Color tinte) {
    float h = ALTO_FIGURA * escala, w = h * c.aspecto, relieve = 0.45f;
    SetShaderValue(e.shFigura, e.locTiempo, &t, SHADER_UNIFORM_FLOAT);
    SetShaderValue(e.shFigura, e.locFase, &fase, SHADER_UNIFORM_FLOAT);
    SetShaderValue(e.shFigura, e.locRelieve, &relieve, SHADER_UNIFORM_FLOAT);
    SetShaderValue(e.shFigura, e.locAparicion, &aparicion, SHADER_UNIFORM_FLOAT);
    c.mat.maps[MATERIAL_MAP_DIFFUSE].color = tinte;
    Matrix m = MatrixMultiply(MatrixMultiply(MatrixScale(w, h, h * 0.35f), MatrixRotateX(-INCLINACION * DEG2RAD)),
                              MatrixTranslate(x, 0.04f, z));
    DrawMesh(e.figura, c.mat, m);
}

// ---- 3D limitado al area del campo (como BeginMode3D pero con viewport propio)
static void Begin3DArea(Camera3D cam, Rectangle vp) {
    rlDrawRenderBatchActive();
    rlViewport((int)vp.x, (int)(GetScreenHeight() - vp.y - vp.height), (int)vp.width, (int)vp.height);
    rlMatrixMode(RL_PROJECTION); rlPushMatrix(); rlLoadIdentity();
    double cerca = 1.0, arriba = cerca * tan(cam.fovy * 0.5 * DEG2RAD), lado = arriba * (vp.width / vp.height);
    rlFrustum(-lado, lado, -arriba, arriba, cerca, 120.0);   // planos ajustados: buena precision de profundidad
    rlMatrixMode(RL_MODELVIEW); rlLoadIdentity();
    Matrix vista = MatrixLookAt(cam.position, cam.target, cam.up);
    rlMultMatrixf(MatrixToFloat(vista));
    rlEnableDepthTest();
}
static void End3DArea() {
    rlDrawRenderBatchActive();
    rlMatrixMode(RL_PROJECTION); rlPopMatrix();
    rlMatrixMode(RL_MODELVIEW); rlLoadIdentity();
    rlViewport(0, 0, GetRenderWidth(), GetRenderHeight());
    rlDisableDepthTest();
}

static void DibujarCarta2D(Texture2D tex, Vector2 centro, float alto, float rot, Color tinte = WHITE) {
    float ancho = alto / 1.45f;
    Rectangle src = {0, 0, (float)tex.width, (float)tex.height};
    Rectangle dst = {centro.x, centro.y, ancho, alto};
    DrawTexturePro(tex, src, {dst.x + 6, dst.y + 9, ancho, alto}, {ancho / 2, alto / 2}, rot, Fade(BLACK, 0.45f));
    DrawTexturePro(tex, src, dst, {ancho / 2, alto / 2}, rot, tinte);
}

static void TextoCentrado(Font f, const char* s, Vector2 c, float tam, Color col, bool contorno = true) {
    Vector2 m = MeasureTextEx(f, s, tam, 1);
    Vector2 p = {c.x - m.x / 2, c.y - m.y / 2};
    if (contorno)
        for (int dx = -2; dx <= 2; dx += 2)
            for (int dy = -2; dy <= 2; dy += 2) DrawTextEx(f, s, {p.x + dx, p.y + dy}, tam, 1, Fade(BLACK, 0.75f));
    DrawTextEx(f, s, p, tam, 1, col);
}

// texto con ajuste de linea dentro de un ancho (UTF-8 por palabras)
static float TextoParrafo(Font f, const std::string& s, Vector2 p, float ancho, float tam, Color col) {
    std::stringstream ss(s); std::string palabra, linea;
    float y = p.y;
    while (ss >> palabra) {
        std::string prueba = linea.empty() ? palabra : linea + " " + palabra;
        if (MeasureTextEx(f, prueba.c_str(), tam, 0.5f).x > ancho && !linea.empty()) {
            DrawTextEx(f, linea.c_str(), {p.x, y}, tam, 0.5f, col); y += tam * 1.18f; linea = palabra;
        } else linea = prueba;
    }
    if (!linea.empty()) { DrawTextEx(f, linea.c_str(), {p.x, y}, tam, 0.5f, col); y += tam * 1.18f; }
    return y;
}

static void Panel(Texture2D tex, Rectangle r, Color borde) {
    if (tex.id) {   // 9 partes: el marco no se deforma al estirar el panel
        int b = tex.width / 9;
        NPatchInfo np = {{0, 0, (float)tex.width, (float)tex.height}, b, b, b, b, NPATCH_NINE_PATCH};
        DrawTextureNPatch(tex, np, r, {0, 0}, 0, WHITE);
    }
    else {
        DrawRectangleRounded(r, 0.08f, 8, Fade({8, 12, 22, 255}, 0.88f));
        DrawRectangleRoundedLinesEx(r, 0.08f, 8, 2.0f, borde);
    }
}

static void PanelLP(Escena& e, const char* quien, int lp, Rectangle r, Color acento) {
    if (e.panelLp.id) {   // placa de Gemini: corazon a la izquierda, vidrio a la derecha (se respeta su proporcion)
        r.height = r.width * e.panelLp.height / (float)e.panelLp.width;
        DrawTexturePro(e.panelLp, {0, 0, (float)e.panelLp.width, (float)e.panelLp.height}, r, {0, 0}, 0, WHITE);
        DrawTextEx(e.fNombre, quien, {r.x + r.width * 0.42f, r.y - r.height * 0.42f}, r.height * 0.36f, 1, Fade(acento, 0.95f));
        TextoCentrado(e.fNum, TextFormat("LP  %d", lp), {r.x + r.width * 0.70f, r.y + r.height * 0.52f}, r.height * 0.56f, RAYWHITE);
        return;
    }
    Panel(e.panelLp, r, acento);
    TextoCentrado(e.fNombre, quien, {r.x + r.width * 0.60f, r.y + r.height * 0.30f}, r.height * 0.24f, Fade(acento, 0.95f));
    TextoCentrado(e.fNum, TextFormat("LP %d", lp), {r.x + r.width * 0.60f, r.y + r.height * 0.64f}, r.height * 0.44f, RAYWHITE);
}

static void BarraFases(Escena& e, float x, float y0, float y1) {
    const char* fases[6] = {"DP", "SP", "M1", "BP", "M2", "EP"};
    float paso = (y1 - y0) / 6.0f, alto = paso * 0.88f, ancho = alto * 0.62f;
    for (int i = 0; i < 6; i++) {
        bool on = i == e.faseActiva;
        Rectangle r = {x - ancho / 2, y0 + i * paso, ancho, alto};
        Texture2D t = on ? e.botonOn : e.botonOff;
        if (t.id) DrawTexturePro(t, {0, 0, (float)t.width, (float)t.height}, r, {0, 0}, 0, WHITE);
        else {
            DrawRectangleRounded(r, 0.3f, 6, on ? Color{40, 140, 255, 230} : Color{20, 30, 50, 220});
            DrawRectangleRoundedLinesEx(r, 0.3f, 6, 2, on ? SKYBLUE : Fade(SKYBLUE, 0.4f));
        }
        TextoCentrado(e.fNombre, fases[i], {r.x + r.width / 2, r.y + r.height / 2}, alto * 0.32f,
                      on ? WHITE : Fade(RAYWHITE, 0.55f));
    }
}

static const char* NombreFase(int f) {
    static const char* n[6] = {"FASE DE ROBO", "FASE DE RESERVA", "FASE PRINCIPAL 1", "FASE DE BATALLA",
                               "FASE PRINCIPAL 2", "FASE FINAL"};
    return n[f];
}

int main(int argc, char** argv) {
    std::string rutaCaptura; int cuadrosCaptura = 150, hoverForzado = -1; bool verFpsArg = false;
    for (int i = 1; i < argc; i++) {
        if (!strcmp(argv[i], "--captura") && i + 1 < argc) rutaCaptura = argv[++i];
        else if (!strcmp(argv[i], "--fps")) verFpsArg = true;
        else if (!strcmp(argv[i], "--cuadros") && i + 1 < argc) cuadrosCaptura = std::atoi(argv[++i]);
        else if (!strcmp(argv[i], "--hover") && i + 1 < argc) hoverForzado = std::atoi(argv[++i]);
    }
    SetConfigFlags(FLAG_MSAA_4X_HINT | FLAG_VSYNC_HINT | FLAG_WINDOW_RESIZABLE);
    InitWindow(1600, 900, "Yugi Reload 2026 - Base 1");
    SetTargetFPS(60);
    R = RutaRecursos();

    Escena e;
    e.shFigura = LoadShader((R + "../shaders/figura.vs").c_str(), (R + "../shaders/figura.fs").c_str());
    e.shFigura.locs[SHADER_LOC_MAP_SPECULAR] = GetShaderLocation(e.shFigura, "texture1");
    e.locTiempo = GetShaderLocation(e.shFigura, "tiempo");
    e.locFase = GetShaderLocation(e.shFigura, "fase");
    e.locRelieve = GetShaderLocation(e.shFigura, "relieve");
    e.locAparicion = GetShaderLocation(e.shFigura, "aparicion");
    CargarZonas();
    CargarCartas(e.shFigura);

    e.mesa = LoadModelFromMesh(GenMeshPlane(19.2f, 14.4f, 1, 1));
    e.mesa.materials[0].maps[MATERIAL_MAP_DIFFUSE].texture = CargarTextura(R + "ui/tablero.png");
    e.cartaPlana = GenMeshPlane(1.0f, 1.45f, 1, 1);
    e.matCarta = LoadMaterialDefault();
    e.figura = MallaFigura(96);
    e.dorso = CargarTextura(R + "ui/dorso.png");
    e.espada = CargarTextura(R + "ui/espada.png");
    e.explosion = CargarTextura(R + "ui/explosion.png");
    e.botonOff = CargarTextura(R + "ui/boton_off.png");
    e.botonOn = CargarTextura(R + "ui/boton_on.png");
    e.panelCarta = CargarTextura(R + "ui/panel_carta.png");
    e.panelLp = CargarTextura(R + "ui/panel_lp.png");
    Image gs = GenImageGradientRadial(128, 128, 0.0f, WHITE, BLANK);
    e.sombra = LoadTextureFromImage(gs); e.brillo = LoadTextureFromImage(gs); UnloadImage(gs);
    std::vector<int> cps;
    for (int c = 32; c < 256; c++) cps.push_back(c);
    e.fNombre = LoadFontEx((R + "fuentes/Cinzel.ttf").c_str(), 64, cps.data(), (int)cps.size());
    e.fNum = LoadFontEx((R + "fuentes/RobotoCondensed.ttf").c_str(), 64, cps.data(), (int)cps.size());
    SetTextureFilter(e.fNombre.texture, TEXTURE_FILTER_BILINEAR);
    SetTextureFilter(e.fNum.texture, TEXTURE_FILTER_BILINEAR);

    // ---- "foto" de un duelo en el turno 5, fase de batalla: Dark Magician ataca a Summoned Skull,
    //      el rival responde con Mirror Force y Celtic Guardian esta siendo destruido.
    e.campo = {
        {"jugador_monstruo_0", "baby_dragon", ATAQUE, NORMAL, 0.2f},
        {"jugador_monstruo_1", "red_eyes", ATAQUE, NORMAL, 0.4f},
        {"jugador_monstruo_2", "dark_magician", ATAQUE, ATACANDO, 0.6f},
        {"jugador_monstruo_3", "kuriboh", DEFENSA, NORMAL, 0.8f},
        {"jugador_monstruo_4", "", BOCA_ABAJO_DEF, NORMAL, 0},
        {"rival_monstruo_0", "celtic_guardian", ATAQUE, EXPLOTANDO, 0.3f},
        {"rival_monstruo_1", "gaia", ATAQUE, NORMAL, 0.5f},
        {"rival_monstruo_2", "summoned_skull", ATAQUE, OBJETIVO, 0.7f},
        {"rival_monstruo_3", "oni_tank_t_34", DEFENSA, NORMAL, 0.9f},
        {"rival_monstruo_4", "", BOCA_ABAJO_DEF, NORMAL, 0},
        {"jugador_magia_0", "swords_of_revealing_light", BOCA_ARRIBA, NORMAL, 0},
        {"jugador_magia_1", "", BOCA_ABAJO, NORMAL, 0},
        {"jugador_magia_3", "", BOCA_ABAJO, NORMAL, 0},
        {"jugador_campo", "sogen", BOCA_ARRIBA, NORMAL, 0},
        {"rival_magia_0", "mirror_force", BOCA_ARRIBA, ACTIVANDO, 0},
        {"rival_magia_2", "", BOCA_ABAJO, NORMAL, 0},
        {"rival_magia_4", "", BOCA_ABAJO, NORMAL, 0},
    };
    e.pilas = {
        {"jugador_mazo", "", 12}, {"rival_mazo", "", 10}, {"jugador_fusion", "", 4}, {"rival_fusion", "", 3},
        {"jugador_cementerio", "pot_of_greed", 4}, {"rival_cementerio", "dark_hole", 5},
    };
    e.manoJugador = {"blue_eyes", "flame_swordsman", "monster_reborn", "faith_bird", "trap_hole", "harpie_lady"};
    const int cuentaMazo[2] = {28, 25}, cuentaCem[2] = {4, 5};
    for (auto& c : e.campo)   // magia de campo boca arriba: su ilustracion (remasterizada por Gemini) cubre el tablero
        if (c.zona.find("_campo") != std::string::npos && !c.carta.empty() && c.modo == BOCA_ARRIBA)
            e.fondoCampo = CargarTextura(R + "cartas/" + c.carta + "/arte.png");

    Camera3D cam{};
    cam.position = {0.0f, 17.6f, 11.4f}; cam.target = {0.0f, 0.0f, 0.75f};
    cam.up = {0, 1, 0}; cam.fovy = 44.0f; cam.projection = CAMERA_PERSPECTIVE;
    bool verFps = verFpsArg; int cuadro = 0;
    float t0 = (float)GetTime();

    while (!WindowShouldClose()) {
        float t = (float)GetTime() - t0;
        float sx = (float)GetScreenWidth(), sy = (float)GetScreenHeight();
        if (IsKeyPressed(KEY_F1)) verFps = !verFps;
        Vector2 raton = GetMousePosition();
        // distribucion del juego original: columna izquierda (LP, carta, LP), columna de fases y campo
        float colIzq = sx * 0.18f, colFases = sy * 0.085f;
        Rectangle vp = {colIzq + colFases, 0, sx - colIzq - colFases, sy};
        float centroTablero = vp.x + vp.width / 2;
        auto P = [&](Vector3 w) {
            Vector2 q = GetWorldToScreenEx(w, cam, (int)vp.width, (int)vp.height);
            return Vector2{q.x + vp.x, q.y + vp.y};
        };

        // ---- mano del jugador
        int n = (int)e.manoJugador.size(), hover = -1;
        float altoMano = sy * 0.24f;
        std::vector<Vector2> pos(n); std::vector<float> rot(n);
        for (int i = 0; i < n; i++) {
            float k = (n > 1) ? (float)i / (n - 1) - 0.5f : 0.0f;
            pos[i] = {centroTablero + k * altoMano * 0.72f * (n - 1), sy - altoMano * 0.05f + fabsf(k) * altoMano * 0.04f};
            rot[i] = k * 8.0f;
        }
        for (int i = n - 1; i >= 0; i--) {
            Rectangle r = {pos[i].x - altoMano / 2.9f, pos[i].y - altoMano / 2, altoMano / 1.45f, altoMano};
            if (CheckCollisionPointRec(raton, r)) { hover = i; break; }
        }
        if (hoverForzado >= 0 && hoverForzado < n) hover = hoverForzado;
        std::string vista = hover >= 0 ? e.manoJugador[hover] : "";
        if (vista.empty())
            for (auto& c : e.campo) {
                if (c.carta.empty()) continue;
                Zona z = zonas[c.zona];
                Vector2 p = P({z.x, cartas[c.carta].tieneFigura ? 0.9f : 0.0f, z.z});
                if (fabsf(raton.x - p.x) < sy * 0.055f && fabsf(raton.y - p.y) < sy * 0.11f) vista = c.carta;
            }
        if (vista.empty()) vista = "dark_magician";

        BeginDrawing();
        ClearBackground({6, 8, 14, 255});
        DrawRectangleGradientV(0, 0, (int)sx, (int)sy, {14, 18, 34, 255}, {4, 5, 9, 255});
        Begin3DArea(cam, vp);
        DrawModel(e.mesa, {0, 0, 0}, 1.0f, WHITE);
        if (e.fondoCampo.id) {   // el paisaje del campo tine el tablero; los marcos de neon siguen viendose
            rlDisableDepthMask();
            e.matCarta.maps[MATERIAL_MAP_DIFFUSE].texture = e.fondoCampo;
            e.matCarta.maps[MATERIAL_MAP_DIFFUSE].color = Fade(WHITE, 0.30f);
            DrawMesh(e.cartaPlana, e.matCarta, MatrixMultiply(MatrixScale(19.2f, 1.0f, 14.4f / 1.45f), MatrixTranslate(0, 0.006f, 0)));
            e.matCarta.maps[MATERIAL_MAP_DIFFUSE].color = WHITE;
            rlEnableDepthMask();
        }
        {   // foco central: la mesa se ilumina en el centro y cae hacia los bordes
            rlDisableDepthMask();
            BeginBlendMode(BLEND_ADDITIVE);
            e.matCarta.maps[MATERIAL_MAP_DIFFUSE].texture = e.brillo;
            float pulso = 0.85f + 0.15f * sinf(t * 0.7f);
            e.matCarta.maps[MATERIAL_MAP_DIFFUSE].color = Fade({110, 140, 200, 255}, 0.35f * pulso);
            DrawMesh(e.cartaPlana, e.matCarta, MatrixMultiply(MatrixScale(16.0f, 1.0f, 8.5f), MatrixTranslate(0, 0.004f, 0)));
            e.matCarta.maps[MATERIAL_MAP_DIFFUSE].color = WHITE;
            EndBlendMode();
            rlEnableDepthMask();
        }
        // pilas con grosor (mazo, fusion, cementerio)
        for (auto& p : e.pilas) {
            Zona z = zonas[p.zona]; bool rv = EsRival(p.zona);
            for (int k = 0; k < p.cantidad; k++) {
                bool ultima = k == p.cantidad - 1 && !p.arriba.empty();
                DibujarCartaTumbada(e, ultima ? cartas[p.arriba].cara : e.dorso, z.x + (k % 2) * 0.012f, z.z, rv, 0.012f + k * 0.012f);
            }
        }
        // cartas en zonas
        for (auto& c : e.campo) {
            Zona z = zonas[c.zona]; bool rv = EsRival(c.zona);
            if (c.estado == ACTIVANDO) continue;
            bool def = c.modo == DEFENSA || c.modo == BOCA_ABAJO_DEF;
            Texture2D tex = (c.modo == BOCA_ABAJO || c.modo == BOCA_ABAJO_DEF || c.carta.empty()) ? e.dorso : cartas[c.carta].cara;
            Color tinte = c.estado == EXPLOTANDO ? Color{255, 150, 110, 255} : WHITE;
            DibujarCartaTumbada(e, tex, z.x, z.z, rv, 0.014f, def, tinte);
        }
        // figuras: rival primero (mas lejos), luego jugador
        for (int pasada = 0; pasada < 2; pasada++)
            for (size_t i = 0; i < e.campo.size(); i++) {
                auto& c = e.campo[i];
                if (c.carta.empty() || !cartas[c.carta].tieneFigura || EsRival(c.zona) != (pasada == 0)) continue;
                if (c.modo != ATAQUE && c.modo != DEFENSA) continue;
                Zona z = zonas[c.zona];
                Carta& k = cartas[c.carta];
                bool def = c.modo == DEFENSA;
                float esc = def ? 0.8f : 1.0f;
                Color tinte = def ? Color{150, 190, 255, 255} : WHITE;
                if (c.estado == EXPLOTANDO) tinte = {255, 170, 120, 150};
                if (c.estado == OBJETIVO) tinte = {255, 225, 225, 255};
                DibujarSombra(e, z.x, z.z, ALTO_FIGURA * esc * k.aspecto);
                {   // aura en el suelo: la carta "sostiene" a su monstruo
                    rlDisableDepthMask(); BeginBlendMode(BLEND_ADDITIVE);
                    Color au = EsRival(c.zona) ? Color{255, 90, 70, 255} : Color{70, 170, 255, 255};
                    float pul = 0.7f + 0.3f * sinf(t * 2.2f + (float)i);
                    e.matCarta.maps[MATERIAL_MAP_DIFFUSE].texture = e.brillo;
                    e.matCarta.maps[MATERIAL_MAP_DIFFUSE].color = Fade(au, 0.55f * pul);
                    DrawMesh(e.cartaPlana, e.matCarta, MatrixMultiply(MatrixScale(2.4f, 1.0f, 1.5f), MatrixTranslate(z.x, 0.035f, z.z)));
                    e.matCarta.maps[MATERIAL_MAP_DIFFUSE].color = WHITE;
                    EndBlendMode(); rlEnableDepthMask();
                }
                float ap = Clamp((t - c.aparece) / 1.2f, 0.0f, 1.0f);
                DibujarFigura(e, k, z.x, z.z - 0.05f, t, ap * ap * (3 - 2 * ap), (float)i * 1.7f, esc, tinte);
            }
        // motas de luz que flotan sobre el tablero
        BeginBlendMode(BLEND_ADDITIVE);
        SetRandomSeed(42);
        for (int m = 0; m < 70; m++) {
            float bx = GetRandomValue(-950, 950) / 100.0f, bz = GetRandomValue(-700, 700) / 100.0f;
            float vel = GetRandomValue(20, 60) / 100.0f, ph = GetRandomValue(0, 628) / 100.0f;
            float y = fmodf(t * vel * 0.4f + ph, 4.0f);
            float a = sinf(y / 4.0f * PI) * 0.55f;
            Color col = bz > 0 ? Color{120, 200, 255, 255} : Color{255, 140, 120, 255};
            DrawBillboard(cam, e.brillo, {bx + 0.3f * sinf(t * 0.5f + ph), 0.2f + y, bz}, 0.16f, Fade(col, a));
        }
        EndBlendMode();
        // trampa activandose (de pie, con halo)
        for (auto& c : e.campo)
            if (c.estado == ACTIVANDO) {
                Zona z = zonas[c.zona];
                DibujarCartaLevantada(e, cartas[c.carta].cara, z.x, z.z, t, EsRival(c.zona) ? Color{255, 80, 120, 255} : SKYBLUE);
            }
        End3DArea();

        // ---- etiquetas ATK/DEF bajo cada monstruo boca arriba
        for (auto& c : e.campo) {
            if (c.carta.empty() || (c.modo != ATAQUE && c.modo != DEFENSA)) continue;
            Carta& k = cartas[c.carta];
            Zona z = zonas[c.zona];
            Vector2 p = P({z.x, 0.0f, z.z + (EsRival(c.zona) ? -1.0f : 1.0f)});
            const char* atk = TextFormat("%d", k.atk);
            const char* def = TextFormat("%d", k.def);
            float tam = sy * 0.024f;
            std::string s = std::string(atk) + " / " + def;
            Vector2 m = MeasureTextEx(e.fNum, s.c_str(), tam, 1);
            DrawRectangleRounded({p.x - m.x / 2 - 8, p.y - m.y / 2 - 2, m.x + 16, m.y + 4}, 0.5f, 6, Fade(BLACK, 0.65f));
            float x0 = p.x - m.x / 2;
            Color ca = c.modo == ATAQUE ? Color{255, 215, 90, 255} : Fade(RAYWHITE, 0.55f);
            Color cd = c.modo == DEFENSA ? Color{120, 200, 255, 255} : Fade(RAYWHITE, 0.55f);
            DrawTextEx(e.fNum, atk, {x0, p.y - m.y / 2}, tam, 1, ca);
            float wa = MeasureTextEx(e.fNum, (std::string(atk) + " / ").c_str(), tam, 1).x;
            DrawTextEx(e.fNum, " / ", {x0 + MeasureTextEx(e.fNum, atk, tam, 1).x, p.y - m.y / 2}, tam, 1, Fade(RAYWHITE, 0.6f));
            DrawTextEx(e.fNum, def, {x0 + wa, p.y - m.y / 2}, tam, 1, cd);
        }
        // ---- contadores de mazo y cementerio
        for (int lado = 0; lado < 2; lado++) {
            const char* pre = lado == 0 ? "jugador_" : "rival_";
            for (int q = 0; q < 2; q++) {
                Zona z = zonas[std::string(pre) + (q == 0 ? "mazo" : "cementerio")];
                Vector2 p = P({z.x, 0.2f, z.z});
                int v = q == 0 ? cuentaMazo[lado] : cuentaCem[lado];
                DrawCircleV(p, sy * 0.022f, Fade(BLACK, 0.7f));
                DrawCircleLinesV(p, sy * 0.022f, lado == 0 ? SKYBLUE : Color{255, 110, 100, 255});
                TextoCentrado(e.fNum, TextFormat("%d", v), p, sy * 0.026f, RAYWHITE, false);
            }
        }
        // ---- espada de ataque: de Dark Magician hacia Summoned Skull
        {
            EnCampo *atac = nullptr, *obj = nullptr;
            for (auto& c : e.campo) { if (c.estado == ATACANDO) atac = &c; if (c.estado == OBJETIVO) obj = &c; }
            if (atac && obj) {
                Zona za = zonas[atac->zona], zo = zonas[obj->zona];
                Vector2 a = P({za.x, 1.5f, za.z}), b = P({zo.x, 1.2f, zo.z});
                Vector2 dir = Vector2Normalize(Vector2Subtract(b, a));
                float ang = atan2f(dir.y, dir.x) * RAD2DEG + 90.0f;
                float k = 0.68f + 0.04f * sinf(t * 3.0f);
                Vector2 pz = Vector2Lerp(a, b, k);
                BeginBlendMode(BLEND_ADDITIVE);
                for (int s = 0; s < 14; s++) {    // estela de energia
                    float u = k * s / 14.0f;
                    DrawCircleV(Vector2Lerp(a, b, u), sy * (0.006f + 0.010f * s / 14.0f), Fade({90, 170, 255, 255}, 0.08f + 0.05f * s / 14.0f));
                }
                DrawTexturePro(e.brillo, {0, 0, (float)e.brillo.width, (float)e.brillo.height},
                               {pz.x, pz.y, sy * 0.22f, sy * 0.22f}, {sy * 0.11f, sy * 0.11f}, 0, Fade({120, 190, 255, 255}, 0.7f));
                EndBlendMode();
                float hs = sy * 0.15f;
                if (e.espada.id) {
                    float ws = hs * e.espada.width / (float)e.espada.height;
                    DrawTexturePro(e.espada, {0, 0, (float)e.espada.width, (float)e.espada.height},
                                   {pz.x, pz.y, ws, hs}, {ws / 2, hs / 2}, ang, WHITE);
                } else {
                    DrawTriangle({pz.x + dir.x * hs / 2, pz.y + dir.y * hs / 2}, {pz.x - dir.y * 10, pz.y + dir.x * 10},
                                 {pz.x + dir.y * 10, pz.y - dir.x * 10}, RAYWHITE);
                }
            }
        }
        // ---- explosion sobre el monstruo destruido
        for (auto& c : e.campo)
            if (c.estado == EXPLOTANDO) {
                Zona z = zonas[c.zona];
                Vector2 p = P({z.x, 0.9f, z.z});
                float tam = sy * 0.25f * (1.0f + 0.04f * sinf(t * 9.0f));
                BeginBlendMode(BLEND_ADDITIVE);
                if (e.explosion.id)
                    DrawTexturePro(e.explosion, {0, 0, (float)e.explosion.width, (float)e.explosion.height},
                                   {p.x, p.y, tam, tam}, {tam / 2, tam / 2}, t * 8.0f, WHITE);
                else DrawTexturePro(e.brillo, {0, 0, (float)e.brillo.width, (float)e.brillo.height},
                                    {p.x, p.y, tam, tam}, {tam / 2, tam / 2}, 0, {255, 200, 110, 255});
                SetRandomSeed(7);
                for (int s = 0; s < 46; s++) {     // chispas y fragmentos de carta
                    float ang = GetRandomValue(0, 628) / 100.0f, dist = tam * GetRandomValue(25, 75) / 100.0f;
                    float vida = fmodf(t * 0.8f + s * 0.137f, 1.0f);
                    Vector2 q = {p.x + cosf(ang) * dist * (0.6f + vida * 0.6f), p.y + sinf(ang) * dist * (0.6f + vida * 0.6f)};
                    if (s % 3 == 0) DrawRectanglePro({q.x, q.y, sy * 0.012f, sy * 0.017f}, {0, 0}, ang * 60 + t * 200, Fade({255, 240, 200, 255}, 1 - vida));
                    else DrawCircleV(q, sy * 0.004f * (1.5f - vida), Fade({255, 190, 90, 255}, 1 - vida));
                }
                EndBlendMode();
            }

        // ---- vineteado del campo (bordes mas oscuros, foco al centro)
        {
            Color osc = Fade(BLACK, 0.55f);
            DrawRectangleGradientH((int)vp.x, 0, (int)(vp.width * 0.10f), (int)sy, osc, BLANK);
            DrawRectangleGradientH((int)(vp.x + vp.width * 0.90f), 0, (int)(vp.width * 0.10f) + 1, (int)sy, BLANK, osc);
            DrawRectangleGradientV((int)vp.x, 0, (int)vp.width, (int)(sy * 0.12f), osc, BLANK);
        }
        // ---- mano del rival (dorsos arriba)
        for (int i = 0; i < e.manoRival; i++) {
            float k = (float)i / (e.manoRival - 1) - 0.5f;
            DibujarCarta2D(e.dorso, {centroTablero + k * sy * 0.13f * (e.manoRival - 1), -sy * 0.01f}, sy * 0.19f, 180.0f);
        }
        // ---- mano del jugador
        for (int i = 0; i < n; i++)
            if (i != hover) DibujarCarta2D(cartas[e.manoJugador[i]].cara, pos[i], altoMano, rot[i]);
        if (hover >= 0) {
            float a = altoMano * 1.18f;
            DibujarCarta2D(cartas[e.manoJugador[hover]].cara, {pos[hover].x, sy - a * 0.50f}, a, 0.0f);
        }

        // ---- columna izquierda: LP del rival arriba, carta seleccionada con su texto, LP del jugador abajo
        {
            float m = 10, anchoLp = colIzq - 2 * m;
            float altoLp = e.panelLp.id ? anchoLp * e.panelLp.height / (float)e.panelLp.width : sy * 0.08f;
            Rectangle rc = {m, m + altoLp + sy * 0.035f, colIzq - 2 * m, sy - 2 * (m + altoLp + sy * 0.035f)};
            Panel(e.panelCarta, rc, Fade(SKYBLUE, 0.7f));
            PanelLP(e, "RIVAL", e.lpRival, {m, m + sy * 0.03f, anchoLp, altoLp}, {255, 90, 80, 255});
            PanelLP(e, "TÚ", e.lpJugador, {m, sy - m - altoLp, anchoLp, altoLp}, {80, 190, 255, 255});
            Carta& k = cartas[vista];
            float altoC = std::min(rc.height * 0.52f, (rc.width * 0.80f) * 1.45f);
            DibujarCarta2D(k.cara, {rc.x + rc.width / 2, rc.y + rc.height * 0.05f + altoC / 2}, altoC, 0.0f);
            float y = rc.y + rc.height * 0.05f + altoC + rc.height * 0.025f, mx = rc.x + rc.width * 0.12f, ancho = rc.width * 0.76f;
            float tt = sy * 0.021f;
            float tn = tt * 1.15f;
            while (tn > tt * 0.6f && MeasureTextEx(e.fNombre, k.nombre.c_str(), tn, 1).x > ancho) tn -= 1.0f;
            DrawTextEx(e.fNombre, k.nombre.c_str(), {mx, y}, tn, 1, {255, 225, 140, 255});
            y += tt * 1.5f;
            std::string tipo = k.clase == "magia" ? "Carta Mágica" : k.clase == "trampa" ? "Carta de Trampa"
                             : TextFormat("Nivel %d  ·  ATK %d  ·  DEF %d", k.nivel, k.atk, k.def);
            DrawTextEx(e.fNum, tipo.c_str(), {mx, y}, tt, 1, Fade(SKYBLUE, 0.95f));
            y += tt * 1.5f;
            DrawLineEx({mx, y}, {mx + ancho, y}, 1.5f, Fade(SKYBLUE, 0.4f));
            TextoParrafo(e.fNum, k.descripcion, {mx, y + tt * 0.5f}, ancho, tt * 0.95f, Fade(RAYWHITE, 0.88f));
        }
        // ---- columna de fases (entre la columna izquierda y el campo, como el original)
        BarraFases(e, colIzq + colFases * 0.5f, sy * 0.12f, sy * 0.88f);
        // ---- turno y fase: discreto, arriba a la derecha del campo
        {
            const char* s1 = TextFormat("TURNO %d  ·  %s", e.turno, NombreFase(e.faseActiva));
            float tam = sy * 0.022f;
            Vector2 mm = MeasureTextEx(e.fNombre, s1, tam, 2);
            Rectangle r = {sx - mm.x - 44, sy * 0.012f, mm.x + 32, mm.y + 12};
            DrawRectangleRounded(r, 0.5f, 8, Fade({10, 14, 26, 255}, 0.85f));
            DrawRectangleRoundedLinesEx(r, 0.5f, 8, 2, Fade({120, 190, 255, 255}, 0.8f));
            DrawTextEx(e.fNombre, s1, {r.x + 16, r.y + 6}, tam, 2, {255, 225, 140, 255});
        }
        if (verFps) DrawFPS((int)vp.x + 10, 10);
        EndDrawing();

        cuadro++;
        if (IsKeyPressed(KEY_F12) || (!rutaCaptura.empty() && cuadro == cuadrosCaptura)) {
            Image img = LoadImageFromScreen();
            std::string ruta = rutaCaptura.empty() ? R + "../capturas/captura.png" : rutaCaptura;
            ExportImage(img, ruta.c_str());
            UnloadImage(img);
            if (!rutaCaptura.empty()) break;
        }
    }
    CloseWindow();
    return 0;
}
