#version 450
// Yugi Reload - agua: gota/chorro (tipo 1, esfera falsa que ondula) y charco (tipo 2, lamina sobre la mesa
// con ondas). Transparente (alfa premultiplicado): lo de atras se ve oscurecido y tenido de azul (refraccion
// falsa), los bordes reflejan el cielo (fresnel) y el sol deja un brillo especular.
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
	vec4 c;          // x: tipo, y: semilla; tramo de chorro: z opacidad, w tapas (1 inicio, 2 fin)
	vec4 d;          // tramo de chorro: color
	vec4 e;          // tramo de chorro: la gota anterior (si no hay, la misma de "a")
	vec4 f;          // tramo de chorro: la gota siguiente (si no hay, la misma de "b")
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
	for (int i = 0; i < 4; i++) {
		s += k * ruido(p);
		p = p * 2.03 + vec2(17.1, 9.2);
		k *= 0.5;
	}
	return s;
}

// lo que refleja el agua: cielo claro en el horizonte, azul arriba, mesa oscura abajo
vec3 entorno(vec3 r)
{
	vec3 horizonte = vec3(0.85, 0.92, 1.00);
	vec3 cenit = vec3(0.40, 0.62, 0.95);
	vec3 suelo = vec3(0.10, 0.11, 0.12);
	return r.y > 0.0 ? mix(horizonte, cenit, pow(r.y, 0.6)) : mix(horizonte * 0.55, suelo, min(-r.y * 3.0, 1.0));
}

void main()
{
	float t = ubo.pantalla.z;
	float s = vfx.c.y;
	int tipo = int(vfx.c.x + 0.5);
	vec3 tinte = tipo == 4 ? vfx.d.rgb : vfx.b.rgb;
	float opacidad = tipo == 4 ? vfx.c.z : vfx.b.w;
	vec3 L = normalize(ubo.haciaSol.xyz);
	vec3 v = normalize(ubo.camara.xyz - inPosMundo);
	vec3 n;
	float mascara;
	float grueso;   // cuanta agua se atraviesa (0..1)
	float vetas = 0.0;
	float causticas = 0.0;
	if (tipo == 4) {
		// tramo de chorro: tubo (cilindro falso) con tapa redonda solo en las puntas del chorro
		vec3 eje = vfx.b.xyz - vfx.a.xyz;
		float largo = max(length(eje), 1e-3);
		float h = inUV.y;
		int tapas = int(vfx.c.w + 0.5);
		// en las uniones el corte va por la bisectriz entre los dos tramos: sin huecos ni bandas dobles
		vec3 dirT = eje / largo;
		if ((tapas & 1) == 0) {
			vec3 corte = normalize(normalize(vfx.a.xyz - vfx.e.xyz + dirT * 1e-4) + dirT);
			if (dot(inPosMundo - vfx.a.xyz, corte) < 0.0) {
				discard;
			}
		}
		if ((tapas & 2) == 0) {
			vec3 corte = normalize(normalize(vfx.f.xyz - vfx.b.xyz + dirT * 1e-4) + dirT);
			if (dot(inPosMundo - vfx.b.xyz, corte) > 0.0) {
				discard;
			}
		}
		float r = mix(vfx.a.w, vfx.b.w, clamp(h, 0.0, 1.0));
		// el grosor tiembla con el agua que corre (ruido del mundo: continuo entre tramos)
		vec3 dirR = eje / largo;
		float aLoLargo = dot(inPosMundo, dirR);   // continuo entre tramos (el chorro se curva poco)
		r *= 1.0 + 0.30 * (fbm(vec2(aLoLargo * 3.5 - t * 6.0, s * 7.0 + inUV.x * 0.5)) - 0.45);
		float fuera = h < 0.0 && (tapas & 1) != 0 ? -h * largo : (h > 1.0 && (tapas & 2) != 0 ? (h - 1.0) * largo : 0.0);
		float d = length(vec2(inUV.x, fuera)) / r;
		if (d > 1.0) {
			discard;
		}
		mascara = 1.0 - smoothstep(0.88, 1.0, d);
		float z = sqrt(max(1.0 - d * d, 0.0));
		vec3 dir = eje / largo;
		vec3 frente = cross(inEjeX, dir);
		if (dot(frente, v) < 0.0) {
			frente = -frente;
		}
		n = normalize((inUV.x / r) * inEjeX + (h < 0.0 ? -fuera : fuera) / r * dir + z * frente);
		vec3 q = inPosMundo * 6.0 - dir * t * 5.0;
		n = normalize(n + 0.45 * vec3(ruido(q.xy) - 0.5, ruido(q.yz + 3.0) - 0.5, ruido(q.zx + 7.0) - 0.5));
		grueso = z;
		// vetas que corren a lo largo del chorro (brillos alargados)
		vetas = smoothstep(0.55, 0.85, fbm(vec2(aLoLargo * 2.0 - t * 7.0, inUV.x / r * 2.2 + s * 3.0)));
	} else if (tipo == 1) {
		// gota: borde que tiembla y esfera falsa
		vec2 p = inUV;
		float ang = atan(p.y, p.x);
		float w = 1.0 - 0.10 * ruido(vec2(cos(ang), sin(ang)) * 1.8 + vec2(t * 2.7 + s * 50.0, s * 30.0));
		float d = length(p) / w;
		if (d > 1.0) {
			discard;
		}
		// borde blando: las gotas vecinas se funden en un chorro continuo (sin cuentas de collar)
		mascara = 1.0 - smoothstep(0.45, 1.0, d);
		float z = sqrt(max(1.0 - d * d, 0.0));
		vec3 aCam = cross(inEjeX, inEjeY);
		n = normalize((p.x / w) * inEjeX + (p.y / w) * inEjeY + z * aCam);
		// ondulacion de la superficie
		vec3 q = inPosMundo * 7.0 + vec3(s * 20.0);
		n = normalize(n + 0.35 * vec3(ruido(q.xy + t * 2.6) - 0.5, ruido(q.yz - t * 2.2) - 0.5, ruido(q.zx + t * 3.1) - 0.5));
		grueso = z;
	} else {
		// charco: borde irregular y ondas concentricas que salen del centro, mas gotitas que caen
		vec2 p = inUV;
		float d = length(p) + 0.32 * (fbm(p * 1.6 + vec2(s * 40.0, s * 17.0)) - 0.45);
		if (d > 1.0) {
			discard;
		}
		mascara = 1.0 - smoothstep(0.86, 1.0, d);
		vec2 m = (inPosMundo.xz - vfx.a.xz);   // metros desde el centro
		float dist = length(m);
		vec2 radial = m / max(dist, 1e-3);
		// ondas del centro: pendiente = derivada de la altura
		float pend = 0.30 * cos(dist * 24.0 - t * 7.0) * exp(-dist * 0.9 / max(vfx.a.w, 0.2));
		vec2 g = radial * pend;
		// gotas que caen y dejan anillos
		for (int k = 0; k < 4; k++) {
			float per = 1.3 + 0.37 * float(k);
			float fase = t / per + float(k) * 0.31 + s;
			float ciclo = floor(fase);
			float edad = fract(fase) * per;
			vec2 c = (vec2(azar(vec2(ciclo, float(k) + s)), azar(vec2(float(k) * 3.1, ciclo + 7.0))) - 0.5) * 1.2 * vfx.a.w;
			vec2 dm = m - c;
			float dd = length(dm);
			float anillo = dd - edad * 0.55;
			float amp = 0.55 * exp(-anillo * anillo * 900.0) * (1.0 - smoothstep(0.0, per, edad));
			g += (dm / max(dd, 1e-3)) * amp * sin(anillo * 70.0);
		}
		// rizos finos del viento
		vec2 rq = inPosMundo.xz * 9.0;
		g += 0.10 * vec2(ruido(rq + vec2(t * 0.8, 0.0)) - 0.5, ruido(rq.yx - vec2(0.0, t * 0.7)) - 0.5);
		n = normalize(vec3(-g.x, 1.0, -g.y));
		// causticas: red de lineas de luz que se mueve (lo que delata el agua sobre el fondo)
		vec2 cq = inPosMundo.xz * 2.2 + g * 2.0;
		float c1 = fbm(cq + vec2(t * 0.35, t * 0.20));
		float c2 = fbm(cq * 1.15 + vec2(-t * 0.28, t * 0.31) + 5.0);
		causticas = 1.0 - smoothstep(0.0, 0.045, abs(c1 - c2));
		grueso = 1.0 - smoothstep(0.5, 1.0, d);   // en el borde hay menos agua
	}
	float nv = max(dot(n, v), 0.0);
	// fresnel exagerado: la mesa es oscura y el agua tiene que leerse como agua
	float fresnel = 0.22 + 0.78 * pow(1.0 - nv, 3.0);
	vec3 r = reflect(-v, n);
	float rl = max(dot(r, L), 0.0);
	float especular = pow(rl, 180.0) * 4.0 + pow(rl, 30.0) * 0.6;
	// brillo del cielo en la parte de arriba (lo que hace que se lea como liquido sobre la mesa oscura)
	especular += 0.35 * smoothstep(0.55, 0.95, n.y) * (tipo != 2 ? 1.0 : 0.0);
	// cuerpo del agua: oscurece y tine lo de atras; mas espeso, mas color
	vec3 cuerpo = tinte * (0.45 + 0.35 * grueso);
	// luz que atraviesa el agua (del lado contrario al sol): un brillo turquesa suave
	cuerpo += vec3(0.25, 0.65, 0.75) * 0.6 * pow(max(dot(-n, L) * 0.5 + 0.5, 0.0), 3.0) * grueso;
	vec3 color = mix(cuerpo, entorno(r), fresnel);
	// espuma: vetas blancas que corren con el agua
	float espuma = smoothstep(0.55, 0.85, fbm(inPosMundo.xz * 4.0 + inPosMundo.y * 3.0 + vec2(t * 1.7, -t * 1.3) + s * 9.0)) * 0.55;
	color = mix(color, vec3(0.92, 0.96, 1.0), espuma * (tipo != 2 ? 1.0 : 0.25));
	color += vec3(0.85, 0.95, 1.0) * vetas * 0.55 + vec3(0.55, 0.85, 1.0) * causticas * 0.35 * grueso;
	float alfa = opacidad * mix(0.50 + 0.25 * grueso, 1.0, fresnel) * mascara;
	if (tipo != 2) {
		// gota o chorro: el centro deja ver lo de atras (tenido); los brillos los ponen el fresnel y el sol
		alfa = opacidad * (0.30 + 0.20 * grueso + 0.55 * fresnel + espuma * 0.5 + vetas * 0.3) * mascara;
	}
	vec3 salida = color * alfa + vec3(1.0, 0.97, 0.90) * especular * opacidad * mascara;
	outColor = vec4(salida, clamp(alfa, 0.0, 1.0));
}
