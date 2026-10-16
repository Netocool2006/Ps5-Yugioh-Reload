#version 450
// Yugi Reload - una lengua de fuego procedural: turbulencia fractal que sube, forma que se afina hacia la
// punta, nucleo blanco-amarillo, naranja, rojo y humo oscuro en la punta. Sale con alfa premultiplicado:
// el fuego casi solo suma luz (alfa bajo) y el humo tapa lo de atras.
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
	vec4 a;
	vec4 b;
	vec4 c;
} vfx;

layout (location = 0) in vec2 inUV;   // x: -1.4..1.4 (1 = medio ancho), y: altura (0 base, 1 punta)

layout (location = 0) out vec4 outColor;

float azar(vec2 p)
{
	p = fract(p * vec2(123.34, 456.21));
	p += dot(p, p + 45.32);
	return fract(p.x * p.y);
}

float ruido(vec2 p)
{
	vec2 i = floor(p);
	vec2 f = fract(p);
	vec2 u = f * f * (3.0 - 2.0 * f);
	return mix(mix(azar(i), azar(i + vec2(1.0, 0.0)), u.x), mix(azar(i + vec2(0.0, 1.0)), azar(i + vec2(1.0, 1.0)), u.x), u.y);
}

float fbm(vec2 p)
{
	float s = 0.0;
	float k = 0.5;
	for (int i = 0; i < 5; i++) {
		s += k * ruido(p);
		p = p * 2.03 + vec2(17.1, 9.2);
		k *= 0.5;
	}
	return s;
}

void main()
{
	float t = ubo.pantalla.z;
	float s = vfx.c.y;
	float intensidad = vfx.b.w;
	float x = inUV.x;
	float h = inUV.y;
	float hc = clamp(h, 0.0, 1.0);
	vec2 sem = vec2(s * 37.7, s * 19.3);
	// turbulencia que sube (dos escalas)
	float n1 = fbm(vec2(x * 0.9, h * 1.5 - t * 2.0) + sem);
	float n2 = fbm(vec2(x * 2.6, h * 3.6 - t * 3.9) + sem * 1.7 + 5.0);
	// la lengua se mece de lado, mas cuanto mas arriba
	float xs = x + (n1 - 0.5) * 1.6 * hc + 0.22 * sin(t * 4.3 + s * 40.0 + h * 3.0) * hc * hc;
	// perfil: redondeado abajo, en punta arriba
	float radio = 0.95 * pow(max(1.0 - h, 0.0), 0.65) * smoothstep(-0.12, 0.08, h);
	float f = 1.0 - abs(xs) / max(radio, 1e-3);
	f += (n2 - 0.5) * 1.2 * (0.35 + hc);       // bordes deshilachados en lenguas sueltas
	f -= 0.35 * hc * hc;
	float parpadeo = 0.88 + 0.12 * sin(t * 17.0 + s * 31.0) * sin(t * 7.3 + s * 11.0);
	float calor = clamp(f * 1.15, 0.0, 1.0) * (1.0 - 0.45 * hc);
	vec3 col = vec3(0.40, 0.02, 0.0);
	col = mix(col, vec3(0.95, 0.20, 0.01), smoothstep(0.03, 0.25, calor));
	col = mix(col, vec3(1.00, 0.50, 0.06), smoothstep(0.25, 0.50, calor));
	col = mix(col, vec3(1.00, 0.82, 0.35), smoothstep(0.50, 0.75, calor));
	col = mix(col, vec3(1.00, 0.98, 0.85), smoothstep(0.78, 0.98, calor));
	float brillo = smoothstep(0.0, 0.22, f) * intensidad * parpadeo;
	vec3 luz = col * brillo * 1.15;
	// humo: sobre la punta y en los bordes de arriba; oscuro, tapa (no suma luz)
	float nh = fbm(vec2(x * 1.3, h * 1.8 - t * 1.1) + sem + 3.0);
	float zona = smoothstep(0.45, 0.95, h) * (1.0 - smoothstep(1.05, 1.35, h)) * (1.0 - smoothstep(0.5, 1.35, abs(x)));
	float humo = zona * smoothstep(-0.9, -0.1, f) * (1.0 - smoothstep(-0.05, 0.25, f)) * smoothstep(0.38, 0.75, nh) * 0.35 * intensidad;
	vec3 colHumo = vec3(0.07, 0.06, 0.055);
	float alfa = humo + brillo * 0.22 * (1.0 - calor);
	outColor = vec4(luz + colHumo * humo, clamp(alfa, 0.0, 1.0));
}
