#version 450
// Yugi Reload - (personajes con esqueleto) posicion en el mundo (con la "vida" de los monstruos), normal y UV de cada vertice.
layout (set = 0, binding = 0) uniform UBO
{
	mat4 proyeccion;
	mat4 vista;
	mat4 luz;
	vec4 haciaSol;
	vec4 camara;
	vec4 pantalla;   // ancho, alto, tiempo, destello
} ubo;
layout (push_constant) uniform Empuje
{
	mat4 modelo;
	vec4 efecto;     // x: holograma, y: especular, z: desintegracion, w: emisivo
	vec4 vida;       // x, y: base en el mundo (x, z), z: respiracion, w: pelo
	vec4 ojoA;       // ojo con parpado (coordenadas del modelo): centro, radio (0: sin parpados)
	vec4 ojoB;       // el otro ojo: centro, cuanto esta cerrado (0..1)
} empuje;
layout (set = 2, binding = 0) uniform Huesos
{
	mat4 matriz;           // la del nodo de la malla
	mat4 hueso[64];        // cada hueso: su pose actual por su matriz de union inversa
	float cantidad;
} huesos;

// "Vida": respira (se ensancha y se achata alrededor de su base) y, si tiene pelo, lo mueve
vec3 vivir(vec3 mundo, vec3 normalMundo)
{
	if (empuje.vida.z == 0.0 && empuje.vida.w == 0.0) {
		return mundo;
	}
	float t = ubo.pantalla.z;
	vec3 base = vec3(empuje.vida.x, 0.0, empuje.vida.y);
	vec3 rel = mundo - base;
	float r = sin(t * 2.3 + empuje.vida.x) * empuje.vida.z;
	rel.xz *= 1.0 + r;
	rel.y *= 1.0 - 0.6 * r;
	float alto = clamp(rel.y / 1.6, 0.0, 1.0);
	float ola = sin(t * 6.0 + dot(mundo, vec3(9.1, 7.3, 8.7))) + 0.5 * sin(t * 9.7 + dot(mundo, vec3(-5.3, 11.1, 4.2)));
	rel += normalMundo * empuje.vida.w * ola * alto;
	return base + rel;
}

layout (location = 0) in vec3 inPos;
layout (location = 1) in vec3 inNormal;
layout (location = 2) in vec2 inUV;
layout (location = 3) in vec4 inHuesos;
layout (location = 4) in vec4 inPesos;

layout (location = 0) out vec3 outPosMundo;
layout (location = 1) out vec3 outNormal;
layout (location = 2) out vec2 outUV;
layout (location = 3) out vec3 outPosModelo;

void main()
{
	mat4 piel = inPesos.x * huesos.hueso[int(inHuesos.x)] + inPesos.y * huesos.hueso[int(inHuesos.y)] +
	            inPesos.z * huesos.hueso[int(inHuesos.z)] + inPesos.w * huesos.hueso[int(inHuesos.w)];
	mat4 local = empuje.modelo * huesos.matriz * piel;
	vec3 normalMundo = normalize(mat3(local) * inNormal);
	vec3 mundo = (local * vec4(inPos, 1.0)).xyz;
	outPosMundo = mundo;
	outNormal = normalMundo;
	outUV = inUV;
	outPosModelo = inPos;
	gl_Position = ubo.proyeccion * ubo.vista * vec4(mundo, 1.0);
}
