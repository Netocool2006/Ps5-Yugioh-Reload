#version 450
// Yugi Reload - textura de color, sol calido con sombras suaves, cielo frio de relleno, brillo
// especular y, en los monstruos, un contorno holografico que late. Se ilumina en espacio lineal:
// la textura y la pantalla son UNORM con valores sRGB, asi que se decodifica al entrar y se
// codifica al salir.
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
layout (set = 0, binding = 1) uniform sampler2DShadow mapaSombra;
layout (set = 1, binding = 0) uniform sampler2D colorBase;

layout (location = 0) in vec3 inPosMundo;
layout (location = 1) in vec3 inNormal;
layout (location = 2) in vec2 inUV;
layout (location = 3) in vec3 inPosModelo;

layout (location = 0) out vec4 outColor;

float azar(vec3 p)
{
	return fract(sin(dot(p, vec3(127.1, 311.7, 74.7))) * 43758.5453);
}

// ruido de valor 3D suave (0..1)
float ruido(vec3 p)
{
	vec3 i = floor(p);
	vec3 f = fract(p);
	f = f * f * (3.0 - 2.0 * f);
	return mix(mix(mix(azar(i), azar(i + vec3(1, 0, 0)), f.x), mix(azar(i + vec3(0, 1, 0)), azar(i + vec3(1, 1, 0)), f.x), f.y),
	           mix(mix(azar(i + vec3(0, 0, 1)), azar(i + vec3(1, 0, 1)), f.x), mix(azar(i + vec3(0, 1, 1)), azar(i + vec3(1, 1, 1)), f.x), f.y), f.z);
}

float sombra(vec3 posMundo, float nl)
{
	vec4 p = ubo.luz * vec4(posMundo, 1.0);
	p.xyz /= p.w;
	vec2 uv = p.xy * 0.5 + 0.5;
	if (any(lessThan(uv, vec2(0.0))) || any(greaterThan(uv, vec2(1.0))) || p.z > 1.0) {
		return 1.0;
	}
	float sesgo = mix(0.0015, 0.0004, nl);
	vec2 texel = 1.0 / vec2(textureSize(mapaSombra, 0));
	float suma = 0.0;
	for (int y = -1; y <= 1; y++) {
		for (int x = -1; x <= 1; x++) {
			suma += texture(mapaSombra, vec3(uv + vec2(x, y) * texel * 1.5, p.z - sesgo));
		}
	}
	return suma / 9.0;
}

void main()
{
	// desintegracion: se borran los puntos bajo el umbral; cerca del umbral, un borde encendido
	float dis = empuje.efecto.z;
	float patron = ruido(inPosMundo * 5.0) * 0.7 + ruido(inPosMundo * 13.0) * 0.3;
	if (dis > 0.0 && patron < dis * 1.05) {
		discard;
	}
	vec3 n = normalize(inNormal);
	vec3 v = normalize(ubo.camara.xyz - inPosMundo);
	if (dot(n, v) < 0.0) {
		n = -n; // las dos caras de las superficies finas
	}
	vec3 l = normalize(ubo.haciaSol.xyz);
	vec3 albedo = pow(texture(colorBase, inUV).rgb, vec3(2.2));
	// parpados: una piel del color del pelo baja sobre cada ojo desde arriba, con el borde oscuro y curvo
	if (empuje.ojoA.w > 0.0 && empuje.ojoB.w > 0.0) {
		float r = empuje.ojoA.w;
		for (int k = 0; k < 2; k++) {
			vec3 c = k == 0 ? empuje.ojoA.xyz : empuje.ojoB.xyz;
			vec3 d = inPosModelo - c;
			if (length(d) < r) {
				float x = d.x / r;
				float borde = r * (1.0 - 2.05 * empuje.ojoB.w) - 0.25 * r * x * x;
				if (d.y > borde) {
					// piel con pelo: mechones finos verticales (ruido estirado) y algo de variacion
					float pelo = ruido(vec3(inPosModelo.x * 90.0, inPosModelo.y * 14.0, inPosModelo.z * 90.0)) * 0.6 + ruido(inPosModelo * 35.0) * 0.4;
					albedo = pow(vec3(0.40, 0.27, 0.18) * (0.55 + 0.75 * pelo), vec3(2.2));
				} else if (d.y > borde - 0.018) {
					albedo = pow(vec3(0.12, 0.07, 0.05), vec3(2.2));
				}
			}
		}
	}

	float nl = max(dot(n, l), 0.0);
	float s = sombra(inPosMundo, nl);
	vec3 sol = vec3(1.0, 0.93, 0.82) * 2.4 * nl * s;
	// relleno: cielo frio desde arriba, rebote calido de la mesa desde abajo
	vec3 relleno = mix(vec3(0.10, 0.08, 0.07), vec3(0.32, 0.38, 0.52), n.y * 0.5 + 0.5);
	float brillo = pow(max(dot(n, normalize(l + v)), 0.0), 48.0) * empuje.efecto.y * nl * s;
	vec3 color = albedo * (sol + relleno) + brillo * vec3(1.0, 0.95, 0.85);

	// contorno holografico de los monstruos (azul cian), late despacio
	if (empuje.efecto.x > 0.0) {
		float borde = pow(1.0 - max(dot(n, v), 0.0), 3.0);
		float latido = 0.75 + 0.25 * sin(ubo.pantalla.z * 2.2);
		color += borde * latido * empuje.efecto.x * vec3(0.25, 0.65, 1.0);
	}

	if (dis > 0.0) {
		float borde = 1.0 - smoothstep(0.0, 0.08, patron - dis * 1.05);
		color += borde * vec3(3.0, 1.2, 0.3);
	}
	// la esfera de energia: brilla por si misma
	if (empuje.efecto.w > 0.0 && empuje.vida.w > 0.5) {
		// resplandor de efectos (mezcla aditiva): brilla en el centro y se desvanece hacia los bordes
		float centro = pow(abs(dot(normalize(inNormal), v)), 1.6);
		color = empuje.vida.xyz * empuje.efecto.w * centro;
	} else if (empuje.efecto.w > 0.0) {
		vec3 tinte = dot(empuje.vida.xyz, empuje.vida.xyz) > 0.0 ? empuje.vida.xyz : vec3(1.0);
		color = (albedo * 2.2 * empuje.efecto.w + albedo * pow(1.0 - max(dot(n, v), 0.0), 2.0) * 2.0) * tinte;
	}
	// destello del impacto
	color += vec3(1.0, 0.85, 1.0) * ubo.pantalla.w;

	// tono filmico suave y viñeta
	color = vec3(1.0) - exp(-color * 1.15);
	vec2 q = gl_FragCoord.xy / ubo.pantalla.xy - 0.5;
	color *= 1.0 - 0.35 * dot(q, q) * 2.0;
	// gamma: los efectos tenues (polvo, humo; brillo < 0.2) salen casi lineales, si no la gamma los vuelve
	// manchas blancas al sumarse; los rayos y destellos (brillo >= 0.2) quedan como siempre
	float gamma = 1.0 / 2.2;
	if (empuje.efecto.w > 0.0 && empuje.vida.w > 0.5) {
		gamma = mix(1.0, 1.0 / 2.2, smoothstep(0.04, 0.2, empuje.efecto.w));
	}
	outColor = vec4(pow(clamp(color, 0.0, 1.0), vec3(gamma)), 1.0);
}
