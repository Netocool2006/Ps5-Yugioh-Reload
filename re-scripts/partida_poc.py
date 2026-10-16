# Lectura/escritura de system.dat (partida de Power of Chaos), formato descifrado del exe:
#  - Cada byte b se codifica como c = b^5 mod 299 (RSA de juguete, n=13*23) en 9 bits; grupos de 8 bytes
#    ocupan 9 bytes (valor i en el bit 9*i, little-endian)            -> FUN_00439c90 / FUN_00439c00
#  - Cabecera de 4 bytes: suma por 4 carriles (bytes 4+k, 8+k, ...) con semillas 7D 13 8A BB, negada
#                                                                       -> FUN_00439e50
#  - Contenido descifrado (0x1188 bytes) = bloque de memoria 0xA53CC0; coleccion = u16 por carta en +0x0C
#    (bits 0-7 copias poseidas, 8-9 en main, 10-11 en side, 12-13 en fusion, 0x4000 vista);
#    magic 0xFBA5 en +0x1182 y suma de control en +0x1184 (suma de 0x8C2 u16 + chk = 0)  -> FUN_005be100
import struct

N, E, D = 299, 5, 53
SEMILLAS = (0x7D, 0x13, 0x8A, 0xBB)
TAM_PLANO = 0x1188
COLECCION, N_CARTAS = 0x0C, 1115

def _cifrar_byte(b): return pow(b, E, N)
def _descifrar_val(c): return pow(c, D, N)

def cabecera(datos, n):
    carriles = list(SEMILLAS)
    for k in range(4):
        for i in range(4 + k, n, 4):
            carriles[k] = (carriles[k] + datos[i]) & 0xFF
    return bytes((-x) & 0xFF for x in carriles)

TAM_ARCHIVO = 5062  # 4 + 9 * ceil((8 + 0x1188) / 8)

def decodificar(arch):
    if len(arch) != TAM_ARCHIVO:
        raise ValueError("system.dat mide %d bytes (deberia medir %d): archivo incompleto o danado" % (len(arch), TAM_ARCHIVO))
    grupos = (len(arch) - 4) // 9
    out = bytearray()
    for g in range(grupos):
        blo = int.from_bytes(arch[4 + 9 * g: 13 + 9 * g], "little")
        for i in range(8):
            c = (blo >> (9 * i)) & 0x1FF
            out.append(_descifrar_val(c) & 0xFF)
    return bytes(out)

def codificar(plano, tam_archivo):
    grupos = (tam_archivo - 4) // 9
    plano = plano + bytes(grupos * 8 - len(plano))
    out = bytearray(4)
    for g in range(grupos):
        blo = 0
        for i in range(8):
            blo |= _cifrar_byte(plano[8 * g + i]) << (9 * i)
        out += blo.to_bytes(9, "little")
    return out

def suma_ok(plano):
    s = sum(struct.unpack("<%dH" % 0x8C3, plano[:0x8C3 * 2])) & 0xFFFF
    return plano[0x1182:0x1184] == b"\xa5\xfb" and s == 0

def recalcular_suma(plano):
    p = bytearray(plano)
    p[0x1182:0x1184] = b"\xa5\xfb"
    s = sum(struct.unpack("<%dH" % 0x8C2, bytes(p[:0x8C2 * 2]))) & 0xFFFF
    p[0x1184:0x1186] = struct.pack("<H", (-s) & 0xFFFF)
    return bytes(p)

def coleccion(plano):
    return list(struct.unpack("<%dH" % N_CARTAS, plano[COLECCION:COLECCION + N_CARTAS * 2]))
