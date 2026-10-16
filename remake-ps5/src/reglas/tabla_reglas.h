// GENERADO por herramientas/tabla_reglas.py desde remake/diseno/reglas_combate.json: no editar a mano.
// Regla de combate de cada carta del remake (Excel reglas-yugi.xlsx del usuario), color de su efecto y si vuela.
#pragma once

namespace combate {

struct ReglaCarta { const char* carta; const char* regla; float halo[3], nucleo[3]; bool vuela; };

const ReglaCarta TABLA_REGLAS[] = {
	{ "baby_dragon", "dragon", { 1.60f, 0.55f, 0.10f }, { 1.00f, 0.84f, 0.77f }, true },   // Baby Dragon (Dragon, WIND)
	{ "celtic_guardian", "arma_mano", { 1.20f, 0.70f, 0.25f }, { 0.94f, 0.86f, 0.79f }, false },   // Celtic Guardian (Warrior, EARTH)
	{ "flame_swordsman", "arma_mano", { 1.60f, 0.45f, 0.08f }, { 1.00f, 0.82f, 0.76f }, false },   // Flame Swordsman (Warrior, FIRE)
	{ "harpie_lady", "animal_aire", { 0.25f, 1.40f, 0.45f }, { 0.79f, 0.97f, 0.82f }, false },   // Harpie Lady (WingedBeast, WIND)
	{ "kuriboh", "embestida", { 0.55f, 0.18f, 1.50f }, { 0.84f, 0.78f, 0.98f }, false },   // Kuriboh (Fiend, DARK)
	{ "mask_of_darkness", "espiritu", { 0.55f, 0.18f, 1.50f }, { 0.84f, 0.78f, 0.98f }, false },   // Mask of Darkness (Fiend, DARK)
	{ "oni_tank_t_34", "maquina", { 1.20f, 0.70f, 0.25f }, { 0.94f, 0.86f, 0.79f }, false },   // Oni Tank T-34 (Machine, EARTH)
	{ "time_wizard", "mistico", { 1.40f, 1.10f, 0.30f }, { 0.97f, 0.92f, 0.80f }, false },   // Time Wizard (Spellcaster, LIGHT)
	{ "faith_bird", "animal_aire", { 0.25f, 1.40f, 0.45f }, { 0.79f, 0.97f, 0.82f }, true },   // Faith Bird (WingedBeast, WIND)
	{ "red_eyes", "dragon", { 1.60f, 0.35f, 0.08f }, { 1.00f, 0.80f, 0.76f }, true },   // Red-Eyes B. Dragon (Dragon, DARK)
	{ "blue_eyes", "dragon", { 0.60f, 0.85f, 1.60f }, { 0.84f, 0.88f, 1.00f }, true },   // Blue-Eyes White Dragon (Dragon, LIGHT)
	{ "dark_magician", "mistico", { 0.18f, 0.45f, 1.60f }, { 0.78f, 0.82f, 1.00f }, false },   // Dark Magician (Spellcaster, DARK)
	{ "summoned_skull", "demonio", { 0.45f, 0.60f, 1.60f }, { 0.82f, 0.84f, 1.00f }, false },   // Summoned Skull (Fiend, DARK)
	{ "gaia", "arma_mano", { 1.20f, 0.70f, 0.25f }, { 0.94f, 0.86f, 0.79f }, false },   // Gaia The Fierce Knight (Warrior, EARTH)
	{ "dark_magician_girl", "mistico", { 0.55f, 0.18f, 1.50f }, { 0.84f, 0.78f, 0.98f }, false },   // Dark Magician Girl (Spellcaster, DARK)
};

} // namespace combate
