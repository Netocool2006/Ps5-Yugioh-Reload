#version 450
// Yugi Reload - efectos "de verdad" (fuego, agua, charco, humo): un cuadrado de 2 triangulos sin vertices
// (sale de gl_VertexIndex) que se orienta segun el tipo:
//   0 fuego:   alargado de la base a la punta y girado sobre ese eje para mirar a la camara
//   1 liquido: mirando a la camara (el fragmento lo convierte en una gota esferica)
//   2 charco:  plano sobre la mesa
//   3 humo:    mirando a la camara
//   4 tramo de chorro de agua: de una gota a la siguiente (a: centro y radio, b: el otro centro y radio)
layout (set = 0, binding = 0) uniform UBO
{
	mat4 proyeccion;
	mat4 vista;
	mat4 luz;
	vec4 haciaSol;
	vec4 camara;
	vec4 pantalla;   // ancho, alto, tiempo, destello
} ubo;
layout (push_constant) uniform Vfx
{
	vec4 a;          // fuego: base, ancho; los demas: centro, radio
	vec4 b;          // fuego: punta, intensidad; los demas: color, opacidad
	vec4 c;          // x: tipo, y: semilla (0..1); tramo de chorro: z opacidad, w tapas (1 inicio, 2 fin)
	vec4 d;          // tramo de chorro: color
	vec4 e;          // tramo de chorro: la gota anterior (si no hay, la misma de "a")
	vec4 f;          // tramo de chorro: la gota siguiente (si no hay, la misma de "b")
} vfx;

layout (location = 0) out vec2 outUV;
layout (location = 1) out vec3 outPosMundo;
layout (location = 2) flat out vec3 outEjeX;
layout (location = 3) flat out vec3 outEjeY;

const vec2 ESQUINAS[6] = vec2[](vec2(-1.0, -1.0), vec2(1.0, -1.0), vec2(1.0, 1.0),
                                vec2(-1.0, -1.0), vec2(1.0, 1.0), vec2(-1.0, 1.0));

void main()
{
	vec2 q = ESQUINAS[gl_VertexIndex];
	int tipo = int(vfx.c.x + 0.5);
	vec3 pos;
	vec3 ex, ey;
	if (tipo == 0) {
		// la lengua: de h=-0.12 (bajo la base) a h=1.35 (humo sobre la punta); x en anchos medios con margen
		vec3 eje = vfx.b.xyz - vfx.a.xyz;
		float largo = max(length(eje), 1e-3);
		vec3 dir = eje / largo;
		vec3 medio = 0.5 * (vfx.a.xyz + vfx.b.xyz);
		vec3 aCam = normalize(ubo.camara.xyz - medio);
		vec3 lado = cross(dir, aCam);
		lado = length(lado) > 1e-3 ? normalize(lado) : vec3(1.0, 0.0, 0.0);
		float h = mix(-0.12, 1.35, 0.5 * q.y + 0.5);
		float x = q.x * 1.4;
		pos = vfx.a.xyz + dir * largo * h + lado * x * 0.5 * vfx.a.w;
		ex = lado;
		ey = dir;
		outUV = vec2(x, h);
	} else if (tipo == 4) {
		// tramo de chorro: como el fuego, girado sobre su eje hacia la camara, con media tapa en cada punta
		vec3 eje = vfx.b.xyz - vfx.a.xyz;
		float largo = max(length(eje), 1e-3);
		vec3 dir = eje / largo;
		vec3 aCam = normalize(ubo.camara.xyz - 0.5 * (vfx.a.xyz + vfx.b.xyz));
		vec3 lado = cross(dir, aCam);
		lado = length(lado) > 1e-3 ? normalize(lado) : vec3(1.0, 0.0, 0.0);
		float r = max(vfx.a.w, vfx.b.w) * 1.15;
		float ext = r / largo;
		float h = mix(-ext, 1.0 + ext, 0.5 * q.y + 0.5);
		pos = vfx.a.xyz + eje * h + lado * q.x * r;
		ex = lado;
		ey = dir;
		outUV = vec2(q.x * r, h);   // x en metros, y a lo largo (0..1 entre las dos gotas)
	} else if (tipo == 2) {
		float r = vfx.a.w * 1.2;
		pos = vfx.a.xyz + vec3(q.x * r, 0.0, q.y * r);
		ex = vec3(1.0, 0.0, 0.0);
		ey = vec3(0.0, 0.0, 1.0);
		outUV = q * 1.2;
	} else {
		float k = tipo == 1 ? 1.1 : 1.0;
		vec3 aCam = normalize(ubo.camara.xyz - vfx.a.xyz);
		vec3 der = cross(vec3(0.0, 1.0, 0.0), aCam);
		der = length(der) > 1e-3 ? normalize(der) : vec3(1.0, 0.0, 0.0);
		vec3 arr = cross(aCam, der);
		pos = vfx.a.xyz + (q.x * der + q.y * arr) * vfx.a.w * k;
		ex = der;
		ey = arr;
		outUV = q * k;
	}
	outPosMundo = pos;
	outEjeX = ex;
	outEjeY = ey;
	gl_Position = ubo.proyeccion * ubo.vista * vec4(pos, 1.0);
}
