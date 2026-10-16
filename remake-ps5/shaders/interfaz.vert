#version 450
// Interfaz del duelo (interfaz.h): cada vertice ya viene en espacio de recorte (la CPU arma los quads: en pixeles
// de pantalla con w = 1, o proyectados desde el tablero 3D con su w, asi la interpolacion es correcta en perspectiva)
layout(location = 0) in vec4 inPos;
layout(location = 1) in vec2 inUV;
layout(location = 2) in vec2 inLocal;
layout(location = 3) in vec4 inColor;
layout(location = 4) in vec4 inColor2;
layout(location = 5) in vec4 inForma;
layout(location = 6) in vec4 inExtra;

layout(location = 0) out vec2 outUV;
layout(location = 1) out vec2 outLocal;
layout(location = 2) out vec4 outColor;
layout(location = 3) out vec4 outColor2;
layout(location = 4) out vec4 outForma;
layout(location = 5) out vec4 outExtra;

void main()
{
	outUV = inUV;
	outLocal = inLocal;
	outColor = inColor;
	outColor2 = inColor2;
	outForma = inForma;
	outExtra = inExtra;
	gl_Position = inPos;
}
