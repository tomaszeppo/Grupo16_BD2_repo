"""Reglas de puntuación del prode, sin base de datos.

Esta función es la definición. La puntuación real corre dentro de MongoDB (una actualización del lado
del servidor, ver MongoAdapter.puntuar_pronosticos) y las pruebas de integración comparan documento por
documento contra lo que devuelve esta función.
"""
from dataclasses import dataclass
from datetime import datetime

PUNTOS_EXACTO = 3
PUNTOS_GANADOR = 1
TOPE_ANTICIPACION = 432000  # 5 días en segundos: cargar todo meses antes no vale más que hacerlo 5 días antes


@dataclass(frozen=True)
class Puntaje:
    puntos: int
    exacto: bool
    tiempo_seg: int  # desempate: cuánto antes del horario programado estaba cargado el pronóstico final
    anulado: bool  # se cargó cuando el partido ya había empezado: no cuenta


def _signo(local: int, visitante: int) -> int:
    return (local > visitante) - (local < visitante)


def calcular(goles_local: int, goles_visitante: int, real_local: int, real_visitante: int,
             cargado_en: datetime, inicio_programado: datetime, inicio_real: datetime) -> Puntaje:
    if cargado_en >= inicio_real:
        return Puntaje(0, False, 0, True)
    exacto = (goles_local, goles_visitante) == (real_local, real_visitante)
    acierto = _signo(goles_local, goles_visitante) == _signo(real_local, real_visitante)
    # Segundos completos, igual que $dateDiff con unidad "second" en MongoDB.
    anticipacion = int(inicio_programado.timestamp()) - int(cargado_en.timestamp())
    anticipacion = min(TOPE_ANTICIPACION, max(0, anticipacion))
    if exacto:
        return Puntaje(PUNTOS_EXACTO, True, anticipacion, False)
    if acierto:
        return Puntaje(PUNTOS_GANADOR, False, anticipacion // 2, False)
    return Puntaje(0, False, 0, False)
