"""Regiones del laboratorio. Cada país pertenece a una: los comentarios de sus hinchas se escriben y leen en
el datacenter de Cassandra de esa región (ver docs/arquitectura_regiones.md).

Simplificación de laboratorio: hay dos regiones. Los países de África, Asia y Oceanía quedan en Europa.
"""
AMERICA = frozenset({"ARG", "BRA", "URU", "COL", "ECU", "PAR", "CHI", "PER",
                     "MEX", "USA", "CAN", "CRC", "PAN", "JAM"})
REGIONES = ("america", "europa")


def region_de(pais: str) -> str:
    return "america" if pais in AMERICA else "europa"


def otra(region: str) -> str:
    return "europa" if region == "america" else "america"
