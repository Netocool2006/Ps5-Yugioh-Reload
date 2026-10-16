#version 450
// Interfaz del duelo (interfaz.h): todo se dibuja con campos de distancia (SDF) por pixel, sin texturas de arte:
// paneles de vidrio con borde de luz que recorre el contorno, texto SDF (atlas de stb_truetype), barras de LP,
// estrellas, la cara de la carta con brillo holografico, el dorso dibujado por codigo, el recuadro dorado del
// puntero, particulas y marcas de zona del tablero. Salida con alfa premultiplicado (los brillos solo suman luz).
layout(set = 0, binding = 0) uniform sampler2D textura;
layout(push_constant) uniform Empuje { vec4 pantalla; } p;   // ancho, alto, tiempo, escala (alto / 1080)

layout(location = 0) in vec2 uv;
layout(location = 1) in vec2 local;     // coordenadas del quad respecto de su centro (px, o cm en el tablero)
layout(location = 2) in vec4 color;
layout(location = 3) in vec4 color2;
layout(location = 4) in vec4 forma;     // xy: medio ancho/alto del rectangulo, z: radio de esquina, w: tipo
layout(location = 5) in vec4 extra;     // parametros de cada tipo

layout(location = 0) out vec4 salida;

const float PI = 3.14159265;
const int PANEL = 0, TEXTO = 1, IMAGEN = 2, DORSO = 3, MARCO = 4, PARTICULA = 5, BARRA = 6, ESTRELLA = 7,
          ZONA = 8, LINEA = 9, FLECHA = 10, LADO_MAZO = 11, ORBE = 12, FONDO = 13;

float caja(vec2 q, vec2 b, float r)
{
	vec2 d = abs(q) - b + r;
	return length(max(d, 0.0)) + min(max(d.x, d.y), 0.0) - r;
}

float azar(vec2 q) { return fract(sin(dot(q, vec2(12.9898, 78.233))) * 43758.5453); }

// recorrido del contorno 0..1 (por angulo, normalizado al rectangulo)
float recorrido(vec2 q, vec2 b) { return atan(q.y / max(b.y, 1e-3), q.x / max(b.x, 1e-3)) / (2.0 * PI) + 0.5; }

// destello que viaja por el contorno con estela: s = recorrido, c = cabeza
float cometa(float s, float c, float largo)
{
	float d = fract(c - s);           // distancia detras de la cabeza
	return exp(-d / largo) * step(d, 0.999) + exp(-(1.0 - d) * 400.0);
}

float estrella5(vec2 q, float r, float rf)
{
	const vec2 k1 = vec2(0.809016994375, -0.587785252292);
	const vec2 k2 = vec2(-k1.x, k1.y);
	q.x = abs(q.x);
	q -= 2.0 * max(dot(k1, q), 0.0) * k1;
	q -= 2.0 * max(dot(k2, q), 0.0) * k2;
	q.x = abs(q.x);
	q.y -= r;
	vec2 ba = rf * vec2(-k1.y, k1.x) - vec2(0, 1);
	float h = clamp(dot(q, ba) / dot(ba, ba), 0.0, r);
	return length(q - ba * h) * sign(q.y * ba.x - q.x * ba.y);
}

vec4 sobre(vec4 arriba, vec4 abajo) { return arriba + abajo * (1.0 - arriba.a); }

void main()
{
	const int tipo = int(forma.w + 0.5);
	const float t = p.pantalla.z;
	const float esc = p.pantalla.w;
	const vec2 b = forma.xy;
	vec4 r = vec4(0.0);

	if (tipo == PANEL) {
		// vidrio oscuro: sombra suave, relleno con degradado y grano, linea de luz arriba, borde fino y un destello
		// que recorre el contorno (extra: x borde, y brillo del borde, z velocidad del destello, w sombra)
		float d = caja(local, b, forma.z);
		float aa = max(fwidth(d), 1e-3);
		float sombra = color.a * 0.55 * exp(-max(d, 0.0) / max(extra.w, 1.0)) * (1.0 - smoothstep(-aa, aa, -d));
		r = vec4(0.0, 0.0, 0.0, sombra * step(0.001, extra.w));
		float dentro = 1.0 - smoothstep(-aa, aa, d);
		vec2 n = local / b;
		vec3 base = color.rgb * mix(1.35, 0.7, n.y * 0.5 + 0.5);
		base += color2.rgb * 0.05 * (1.0 - length(n - vec2(-0.6, -0.9)) * 0.6);   // reflejo frio arriba a la izquierda
		base += (azar(floor(local / (1.5 * esc)) + floor(t * 20.0)) - 0.5) * 0.012;            // grano del vidrio
		base += 0.012 * sin(local.y / esc * 1.6 + t * 2.0);                                     // lineas de barrido muy sutiles
		r = sobre(vec4(base * color.a * dentro, color.a * dentro), r);
		// linea de luz superior (vidrio biselado)
		float bisel = exp(-abs(d + 2.0 * esc) / (0.8 * esc)) * smoothstep(0.2, -0.9, n.y) * dentro;
		r.rgb += vec3(1.0) * 0.10 * bisel;
		// borde y luz que recorre el contorno
		float bw = extra.x;
		float borde = 1.0 - smoothstep(bw * 0.5 - aa, bw * 0.5 + aa, abs(d + bw * 0.5));
		float s = recorrido(local, b);
		float luz = cometa(s, t * extra.z, 0.10) + cometa(s, t * extra.z + 0.5, 0.10);
		float bordeBrillo = extra.y * (0.35 + 0.4 * (0.5 - 0.5 * n.y));
		r.rgb += color2.rgb * borde * (bordeBrillo + 1.6 * luz * step(0.001, abs(extra.z)));
		r.a = max(r.a, borde * 0.6);
		// halo exterior del destello
		r.rgb += color2.rgb * luz * step(0.001, abs(extra.z)) * 0.5 * exp(-max(d, 0.0) / (6.0 * esc)) * step(0.0, d);
	} else if (tipo == TEXTO) {
		// texto SDF: borde nitido a cualquier tamano, contorno oscuro opcional y halo de color (extra: x halo,
		// y contorno, z degradado vertical)
		float d = texture(textura, uv).r;
		float w = max(fwidth(d) * 0.75, 1e-3);
		float a = smoothstep(0.5 - w, 0.5 + w, d);
		vec3 c = color.rgb;
		if (extra.z > 0.0) {
			float v = clamp(local.y * 0.5 + 0.5, 0.0, 1.0);   // 0 arriba .. 1 abajo de la linea
			c = mix(c, color2.rgb, v * extra.z);
		}
		float contorno = extra.y > 0.0 ? smoothstep(0.5 - extra.y - w, 0.5 - extra.y + w, d) : 0.0;
		float halo = extra.x * smoothstep(0.08, 0.5, d) * (1.0 - a);
		vec3 haloCol = extra.z > 0.0 ? color.rgb : color2.rgb;
		r = vec4(c * a, a) * color.a;
		r = sobre(r, vec4(0.0, 0.0, 0.0, contorno * 0.85 * color.a));
		r.rgb += haloCol * halo * 0.9 * color.a;
		r.a = max(r.a, halo * 0.35 * color.a);
	} else if (tipo == IMAGEN) {
		// la cara de la carta: esquinas redondeadas, brillo holografico (foil) que cambia con el angulo y el
		// tiempo, y un destello diagonal que la cruza cada pocos segundos (extra: x foil, y destello, z fase)
		float d = caja(local, b, forma.z);
		float aa = max(fwidth(d), 1e-3);
		float a = 1.0 - smoothstep(-aa, aa, d);
		vec3 c = texture(textura, uv).rgb;
		vec2 n = local / b;
		float lum = dot(c, vec3(0.299, 0.587, 0.114));
		vec3 arco = 0.5 + 0.5 * cos(2.0 * PI * (vec3(0.0, 0.33, 0.67) + dot(n, vec2(0.55, 0.35)) * 0.9 + t * 0.12 + extra.z));
		float patron = 0.6 + 0.4 * sin((n.x - n.y) * 18.0 + t * 1.3);
		c += arco * extra.x * (0.10 + 0.30 * lum) * patron;
		float s = n.x * 0.6 + n.y * 0.4;
		float fase = fract(t * 0.22 + extra.z) * 4.0 - 1.6;
		c += vec3(1.0, 0.97, 0.9) * exp(-pow((s - fase) * 5.0, 2.0)) * 0.55 * extra.y;
		c *= color.rgb;
		// borde fino de luz
		float borde = exp(-abs(d) / (1.2 * esc));
		c += color2.rgb * borde * 0.6;
		r = vec4(c, 1.0) * a * color.a;
	} else if (tipo == DORSO) {
		// dorso propio, dibujado aqui: indigo profundo, rejilla hexagonal tenue, anillos que giran, un rombo de luz
		// en el centro y un filete dorado (color: acento frio, color2: dorado; extra.x fase)
		float d = caja(local, b, forma.z);
		float aa = max(fwidth(d), 1e-3);
		float a = 1.0 - smoothstep(-aa, aa, d);
		vec2 n = local / b.y;   // proporcion real
		vec3 c = mix(vec3(0.035, 0.03, 0.10), vec3(0.09, 0.05, 0.20), 1.0 - length(n) * 0.8);
		// rejilla hexagonal
		vec2 h = n * 9.0;
		vec2 rr = vec2(1.0, 1.732);
		vec2 ha = mod(h, rr) - rr * 0.5, hb = mod(h - rr * 0.5, rr) - rr * 0.5;
		vec2 g = dot(ha, ha) < dot(hb, hb) ? ha : hb;
		float hex = max(abs(g.x), dot(abs(g), normalize(vec2(1.0, 1.732))));
		c += color.rgb * 0.10 * smoothstep(0.44, 0.5, hex) * (0.6 + 0.4 * sin(t * 1.5 + n.y * 6.0 + extra.x));
		// anillos
		float rad = length(n);
		float ang = atan(n.y, n.x);
		float anillo1 = exp(-abs(rad - 0.42) * 90.0) * (0.55 + 0.45 * step(0.0, sin(ang * 12.0 + t * 0.8 + extra.x)));
		float anillo2 = exp(-abs(rad - 0.30) * 120.0) * (0.5 + 0.5 * step(0.0, sin(ang * 6.0 - t * 1.3)));
		c += color.rgb * (anillo1 * 0.9 + anillo2 * 0.7);
		// rombo central
		float rombo = abs(n.x) + abs(n.y) * 0.7 - 0.17;
		c += color2.rgb * (exp(-abs(rombo) * 60.0) * 1.2 + exp(-max(rombo, 0.0) * 14.0) * 0.25 * (0.8 + 0.2 * sin(t * 3.0)));
		c += vec3(1.0, 0.95, 0.8) * exp(-length(n) * 30.0) * 0.8;
		// filete dorado interior y borde
		float filete = exp(-abs(caja(local, b - b.y * 0.07, forma.z * 0.6)) / (0.9 * esc));
		c += color2.rgb * filete * 0.7;
		c += color2.rgb * exp(-abs(d) / (1.0 * esc)) * 0.5;
		r = vec4(c, 1.0) * a * color.a;
	} else if (tipo == MARCO) {
		// recuadro dorado del puntero: aro con degradado de oro, dos destellos con estela que recorren el borde,
		// esquinas reforzadas, pulso y halo (extra: x grosor, y radio del halo, z intensidad 0..1)
		float d = caja(local, b, forma.z);
		float aa = max(fwidth(d), 1e-3);
		float grosor = extra.x;
		float aro = 1.0 - smoothstep(grosor * 0.5 - aa, grosor * 0.5 + aa, abs(d));
		vec2 q = abs(local) - (b - vec2(min(b.x, b.y) * 0.32));
		float esquina = step(0.0, q.x) * step(0.0, q.y);
		float aroEsq = 1.0 - smoothstep(grosor * 1.1 - aa, grosor * 1.1 + aa, abs(d - grosor * 0.6));
		aro = max(aro, aroEsq * esquina);
		float s = recorrido(local, b);
		vec3 oro = mix(vec3(1.0, 0.70, 0.18), vec3(1.0, 0.94, 0.62), 0.5 + 0.5 * sin(s * 4.0 * PI + t * 2.5));
		float pulso = 0.8 + 0.2 * sin(t * 5.0);
		float luz = cometa(s, t * 0.42, 0.16) + cometa(s, t * 0.42 + 0.5, 0.16);
		vec3 c = oro * aro * (0.95 + 1.2 * luz) * pulso;
		float halo = exp(-abs(d) / max(extra.y, 1e-3)) * (0.35 * pulso + 0.9 * luz);
		c += oro * halo * 0.9;
		// velo dorado interior que barre de abajo arriba
		float dentro = 1.0 - smoothstep(-aa, aa, d);
		float barrido = exp(-pow((local.y / b.y + 1.0 - fract(t * 0.6) * 2.4) * 3.0, 2.0));
		c += oro * dentro * (0.035 + 0.08 * barrido);
		r = vec4(c * extra.z, clamp(aro * 0.9 + halo * 0.2, 0.0, 1.0) * extra.z);
	} else if (tipo == PARTICULA) {
		// chispa: nucleo suave y cruz de luz; solo suma luz
		float rr = length(local) / max(b.x, 1e-3);
		float nucleo = exp(-rr * rr * 7.0);
		float cruz = (exp(-abs(local.x) / b.x * 18.0) * exp(-abs(local.y) / b.x * 2.5) +
		              exp(-abs(local.y) / b.x * 18.0) * exp(-abs(local.x) / b.x * 2.5)) * extra.x;
		r = vec4(color.rgb * (nucleo + cruz) * color.a, 0.0);
	} else if (tipo == BARRA) {
		// barra de LP: canal oscuro, relleno con degradado, marcas cada 500 LP, brillo que corre, borde que se
		// enciende en la punta y "fantasma" del dano reciente (extra: x relleno 0..1, y fantasma 0..1, z destello)
		float d = caja(local, b, forma.z);
		float aa = max(fwidth(d), 1e-3);
		float dentro = 1.0 - smoothstep(-aa, aa, d);
		float x = local.x / b.x * 0.5 + 0.5;
		float y = local.y / b.y;
		vec3 c = vec3(0.02, 0.025, 0.05);
		float lleno = step(x, extra.x);
		float fantasma = step(extra.x, x) * step(x, extra.y);
		vec3 relleno = mix(color.rgb, color2.rgb, x) * (1.15 - 0.45 * (y * 0.5 + 0.5));
		relleno += vec3(1.0) * 0.22 * exp(-pow((y + 0.55) * 3.0, 2.0));                      // brillo de tubo
		float corre = exp(-pow((x - fract(t * 0.35) * 1.4 + 0.2) * 9.0, 2.0)) * lleno;
		relleno += vec3(1.0) * 0.35 * corre;
		c = mix(c, relleno, lleno);
		c = mix(c, vec3(1.0, 0.45, 0.35) * (1.2 + extra.z), fantasma * 0.9);
		float marcas = step(0.5, fract(x * 16.0 + 0.5)) * 0.0 + (1.0 - smoothstep(0.0, 0.004, abs(fract(x * 16.0 + 0.5) - 0.5) - 0.465));
		c *= 1.0 - 0.35 * marcas;
		float punta = exp(-abs(x - extra.x) * b.x * 2.0 / (3.0 * esc)) * step(0.001, extra.x);
		c += color2.rgb * punta * 1.4;
		c += vec3(1.0, 0.6, 0.5) * extra.z * dentro * 0.5;
		float borde = exp(-abs(d) / (0.8 * esc));
		c += color2.rgb * borde * 0.35;
		float halo = exp(-max(d, 0.0) / (5.0 * esc)) * step(0.0, d) * 0.25;
		r = vec4(c * dentro, dentro) * color.a;
		r.rgb += color2.rgb * halo * (0.5 + extra.z);
	} else if (tipo == ESTRELLA) {
		float d = estrella5(local * vec2(1.0, -1.0), b.x, 0.45);
		float aa = max(fwidth(d), 1e-3);
		float a = 1.0 - smoothstep(-aa, aa, d);
		vec3 c = mix(color.rgb, color2.rgb, clamp(local.y / b.x * 0.5 + 0.5, 0.0, 1.0));
		r = vec4(c * a, a) * color.a;
		r.rgb += color.rgb * exp(-max(d, 0.0) / (3.0 * esc)) * step(0.0, d) * 0.6 * color.a * extra.x;
	} else if (tipo == ZONA) {
		// marca de zona en el tablero: contorno de trazos que corre, esquinas y velo interior
		// (extra: x grosor, y velocidad de los trazos, z intensidad)
		float d = caja(local, b, forma.z);
		float aa = max(fwidth(d), 1e-3);
		float aro = 1.0 - smoothstep(extra.x * 0.5 - aa, extra.x * 0.5 + aa, abs(d));
		float s = recorrido(local, b);
		float trazos = smoothstep(0.35, 0.45, fract(s * 28.0 - t * extra.y)) * smoothstep(0.95, 0.85, fract(s * 28.0 - t * extra.y));
		vec2 q = abs(local) - (b - vec2(min(b.x, b.y) * 0.22));
		float esquina = step(0.0, q.x) * step(0.0, q.y);
		float aroEsq = 1.0 - smoothstep(extra.x * 1.2 - aa, extra.x * 1.2 + aa, abs(d + extra.x));
		float dentro = 1.0 - smoothstep(-aa, aa, d);
		float velo = dentro * (0.10 + 0.08 * sin(t * 2.0 + local.y * 0.05));
		float halo = exp(-abs(d) / (extra.x * 3.0)) * 0.35;
		vec3 c = color.rgb * (aro * trazos * 1.2 + aroEsq * esquina * 1.8 + halo) + color2.rgb * velo;
		r = vec4(c * extra.z, clamp((aro * trazos + aroEsq * esquina) * 0.8 + velo, 0.0, 1.0) * extra.z * color.a);
	} else if (tipo == LINEA) {
		// linea de luz horizontal que se desvanece en los extremos (separadores, rieles)
		float fx = 1.0 - smoothstep(0.55, 1.0, abs(local.x / b.x));
		float nucleo = exp(-abs(local.y) / max(b.y * 0.25, 1e-3));
		float brillo = exp(-abs(local.y) / max(b.y, 1e-3)) * 0.4;
		float corre = 1.0 + extra.x * exp(-pow((local.x / b.x - (fract(t * 0.3 + extra.y) * 2.6 - 1.3)) * 4.0, 2.0));
		r = vec4(color.rgb * (nucleo + brillo) * fx * corre * color.a, nucleo * fx * color.a * 0.5);
	} else if (tipo == FLECHA) {
		// el puntero: punta de flecha dorada hacia abajo, con halo
		vec2 q = local / b.x;
		q.x = abs(q.x);
		float d = max(q.x * 0.866 + q.y * 0.5, -q.y) - 0.42;
		float hueco = max(q.x * 0.866 + (q.y + 0.35) * 0.5, -(q.y + 0.35)) - 0.30;
		d = max(d, -hueco);
		float aa = max(fwidth(d), 1e-3);
		float a = 1.0 - smoothstep(-aa, aa, d);
		vec3 c = mix(color2.rgb, color.rgb, clamp(-q.y + 0.4, 0.0, 1.0));
		r = vec4(c * a, a);
		r.rgb += color.rgb * exp(-max(d, 0.0) * 9.0) * step(0.0, d) * 0.7;
		r *= color.a;
	} else if (tipo == LADO_MAZO) {
		// costado de la pila del mazo: cantos de carta apilados (v: 0 abajo .. 1 arriba en uv.y) con luz
		float capas = extra.x;
		float v = uv.y;
		float linea = 0.5 + 0.5 * cos(v * capas * 2.0 * PI);
		vec3 c = mix(color2.rgb, color.rgb, 0.55 + 0.45 * linea);
		c *= 0.55 + 0.45 * v;
		c += color.rgb * exp(-(1.0 - v) * 25.0) * 0.6;
		r = vec4(c, 1.0) * color.a;
	} else if (tipo == ORBE) {
		// ficha redonda (atributo, fases): disco de vidrio con aro de color y halo (extra: x halo, y relleno)
		float d = length(local) - b.x;
		float aa = max(fwidth(d), 1e-3);
		float a = 1.0 - smoothstep(-aa, aa, d);
		float aro = exp(-abs(d + 1.2 * esc) / (0.9 * esc));
		vec3 c = color2.rgb * mix(1.2, 0.5, local.y / b.x * 0.5 + 0.5) * extra.y;
		c += color.rgb * aro * 1.2;
		r = vec4(c * a, a * max(extra.y, 0.35)) * color.a;
		r.rgb += color.rgb * exp(-max(d, 0.0) / (5.0 * esc)) * step(0.0, d) * extra.x * color.a;
	} else if (tipo == FONDO) {
		// fondo del vacio alrededor del tablero (solo donde la escena no dibujo nada: prueba de profundidad en 1.0):
		// noche azul con un brillo central, dos auroras lentas (cian y carmesi), rejilla hexagonal tenue y polvo de
		// estrellas que titila
		vec2 q = local / b;
		vec2 e = q * vec2(0.85, 1.4) - vec2(0.08, 0.05);
		vec3 c = mix(vec3(0.006, 0.010, 0.026), vec3(0.030, 0.050, 0.110), exp(-dot(e, e) * 1.4));
		float a1 = exp(-pow((q.y + 0.62 + 0.07 * sin(q.x * 3.0 + t * 0.21)) * 6.0, 2.0)) * (0.55 + 0.45 * sin(q.x * 2.2 - t * 0.17));
		float a2 = exp(-pow((q.y - 0.78 + 0.05 * sin(q.x * 2.4 - t * 0.15 + 1.7)) * 7.0, 2.0)) * (0.55 + 0.45 * sin(q.x * 1.7 + t * 0.13 + 2.0));
		c += vec3(0.10, 0.45, 0.70) * a1 * 0.16 + vec3(0.70, 0.12, 0.30) * a2 * 0.09;
		vec2 h = local / (46.0 * esc);
		vec2 rr = vec2(1.0, 1.732);
		vec2 ha = mod(h, rr) - rr * 0.5, hb = mod(h - rr * 0.5, rr) - rr * 0.5;
		vec2 g = dot(ha, ha) < dot(hb, hb) ? ha : hb;
		float hex = max(abs(g.x), dot(abs(g), normalize(vec2(1.0, 1.732))));
		float onda = 0.5 + 0.5 * sin(length(q * vec2(1.6, 1.0)) * 7.0 - t * 0.6);
		c += vec3(0.20, 0.55, 0.85) * smoothstep(0.46, 0.5, hex) * 0.035 * onda;
		vec2 celda = floor(local / (34.0 * esc));
		float z = azar(celda);
		if (z > 0.9) {
			vec2 centro = (celda + 0.2 + 0.6 * vec2(azar(celda + 3.1), azar(celda + 7.7))) * 34.0 * esc;
			float d = length(local - centro) / esc;
			float tit = 0.4 + 0.6 * pow(0.5 + 0.5 * sin(t * (0.8 + 2.0 * z) + z * 40.0), 3.0);
			c += mix(vec3(0.5, 0.8, 1.0), vec3(1.0, 0.85, 0.6), azar(celda + 1.3)) * exp(-d * d * 0.5) * tit * 0.55;
		}
		r = vec4(c, 1.0);
	}
	salida = r;
}
