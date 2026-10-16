// Registro de las reglas de combate: cada regla nueva se agrega aqui (su include y su linea en reglaPorNombre).
// Las que todavia no estan escritas (las propuestas: demonio, zombi, piro, trueno, planta, espiritu, objeto) usan
// la embestida (regla 5b del Excel) hasta que el usuario las apruebe.
#pragma once
#include <cstring>
#include "combate_api.h"
#include "regla_embestida.h"
#include "regla_dragon.h"
#include "regla_animal.h"
#include "regla_maquina.h"
#include "regla_agua.h"
#include "regla_roca.h"

namespace combate {

inline const Regla& reglaPorNombre(const char* nombre)
{
	static const ReglaEmbestida embestida;
	static const ReglaDragon dragon;
	static const ReglaAnimalTierra animalTierra;
	static const ReglaAnimalAire animalAire;
	static const ReglaInsectoTierra insectoTierra;
	static const ReglaInsectoAire insectoAire;
	static const ReglaMaquina maquina;
	static const ReglaAgua agua;
	static const ReglaRoca roca;
	const Regla* todas[] = { &dragon, &animalTierra, &animalAire, &insectoTierra, &insectoAire, &maquina, &agua, &roca };
	for (const Regla* r : todas) {
		if (nombre && strcmp(nombre, r->nombre()) == 0) {
			return *r;
		}
	}
	return embestida;
}

} // namespace combate
