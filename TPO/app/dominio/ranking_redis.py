"""Codificación del orden del TPO para un sorted set de Redis.

El torneo tiene como máximo 128 partidos y 3 puntos por partido. La anticipación
acumulada no supera 128 * 432000 segundos. El resultado cabe exactamente en un
double de Redis; el identificador invertido conserva el desempate ascendente.
"""
import re

MAX_PARTIDOS = 128
MAX_TIEMPO = MAX_PARTIDOS * 432000
MULT_EXACTOS = 100_000_000
MULT_PUNTOS = 100_000_000_000


def codificar_puntaje(puntos: int, exactos: int, tiempo_seg: int) -> int:
    valores = (puntos, exactos, tiempo_seg)
    if any(type(n) is not int for n in valores):
        raise ValueError("Los componentes del ranking deben ser enteros.")
    if not (0 <= puntos <= 3 * MAX_PARTIDOS and 0 <= exactos <= MAX_PARTIDOS
            and 0 <= tiempo_seg <= MAX_TIEMPO):
        raise ValueError("Componentes del ranking fuera de los límites del torneo.")
    return puntos * MULT_PUNTOS + exactos * MULT_EXACTOS + tiempo_seg


def miembro_redis(usuario_id: str) -> str:
    if not re.fullmatch(r"U\d{7}", usuario_id):
        raise ValueError("Identificador de usuario inválido.")
    return f"{9_999_999 - int(usuario_id[1:]):07d}"


def usuario_de_miembro(miembro: str) -> str:
    if not re.fullmatch(r"\d{7}", miembro):
        raise ValueError("Miembro de ranking inválido.")
    return f"U{9_999_999 - int(miembro):07d}"
