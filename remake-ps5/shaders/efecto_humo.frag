#version 450
// Yugi Reload - humo o polvo: nube suave con ruido que se arremolina; transparente (alfa premultiplicado),
// puede ser oscura: tapa lo de atras en vez de sumar luz. Un poco mas clara del lado del sol.
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
	vec4 a;          // centro, radio
	vec4 b;          // color, opacidad
	vec4 c;          // x: tipo, y: semilla
} vfx;

layout (location = 0) in vec2 inUV;
layout (location = 1) in vec3 inPosMundo;
layout (location = 2) flat in vec3 inEjeX;
layout (location = 3) flat in vec3 inEjeY;

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
	vec2 p = inUV;
	// remolino lento: gira el muestreo segun la semilla y el tiempo
	float giro = s * 6.28 + t * 0.25 * (s > 0.5 ? 1.0 : -1.0);
	mat2 rot = mat2(cos(giro), -sin(giro), sin(giro), cos(giro));
	vec2 q = rot * p;
	float n1 = fbm(q * 1.7 + vec2(s * 31.0, s * 17.0) + vec2(0.0, -t * 0.30));
	float n2 = fbm(q * 3.9 + vec2(s * 13.0, 4.0) + vec2(t * 0.20, -t * 0.45));
	float d = length(p) + (n1 - 0.5) * 0.75;
	float densidad = 1.0 - smoothstep(0.15, 0.95, d);
	densidad *= smoothstep(0.15, 0.65, 0.55 * n1 + 0.6 * n2);
	float alfa = clamp(vfx.b.w * densidad * 1.4, 0.0, 1.0);
	// iluminacion: mas claro hacia el sol, mas oscuro en el centro espeso
	vec3 dir = normalize(p.x * inEjeX + p.y * inEjeY + 0.6 * cross(inEjeX, inEjeY));
	float luz = 0.70 + 0.35 * dot(dir, normalize(ubo.haciaSol.xyz)) - 0.15 * densidad;
	vec3 color = vfx.b.rgb * luz;
	outColor = vec4(color * alfa, alfa);
}
