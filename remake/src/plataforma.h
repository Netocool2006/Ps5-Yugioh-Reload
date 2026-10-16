// Capa de plataforma (lo unico que cambia entre Windows/Shadow y PS5): rutas y arranque.
#pragma once
#include <string>
#include "raylib.h"

#if defined(_WIN32)
// Portatiles con dos GPU (Optimus/AMD): pide la grafica dedicada en vez de la integrada.
extern "C" {
__declspec(dllexport) unsigned long NvOptimusEnablement = 1;
__declspec(dllexport) int AmdPowerXpressRequestHighPerformance = 1;
}
#endif

// Carpeta de recursos: en PC esta junto al ejecutable (bin\..\recursos).
inline std::string RutaRecursos() {
#if defined(__PROSPERO__)
    return "/app0/recursos/";   // PS5 homebrew: carpeta del titulo (pendiente de validar en consola)
#else
    return std::string(GetApplicationDirectory()) + "../recursos/";
#endif
}
