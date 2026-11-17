"""Puerto de ranking: de dónde sale la tabla de posiciones.

Hoy sale de la colección `puntajes` de MongoDB. Saber el puesto de un usuario ahí obliga a contar cuántos
tienen mejor puntaje (ver docs/rendimiento.md); un conjunto ordenado de Redis lo resuelve directo. Para
pasarlo a Redis: una clase que cumpla `RankingPort`, que en `partido_puntuado` lea de MongoDB los puntajes
nuevos de ese partido y los escriba con ZADD, y cambiar el proveedor en app/deps.py. MongoDB sigue siendo
la fuente de verdad: si Redis se pierde, se reconstruye desde `puntajes`.

Orden del ranking: puntos, resultados exactos, tiempo acumulado (todos de mayor a menor) y, a igualdad
total, id de usuario. El sorteo final queda para la implementación de Redis.
"""
from typing import Protocol


class RankingPort(Protocol):
    nombre: str  # se informa en el campo "fuente" de las respuestas

    def top(self, limit: int) -> list[dict]:
        """Filas {puesto, usuario_id, nombre, puntos, exactos, tiempo_seg}."""

    def posicion(self, usuario_id: str) -> dict | None:
        """{puesto, puntos, exactos, tiempo_seg, total_usuarios} o None si no tiene puntaje."""

    def puntajes_de(self, usuario_ids: list[str]) -> list[dict]:
        """Puntajes de un grupo de usuarios (tabla de un prode privado), sin ordenar."""

    def partido_puntuado(self, partido_id: str) -> None:
        """Aviso de que `puntajes` ya tiene sumado ese partido."""


class RankingMongo:
    nombre = "mongodb"

    def __init__(self, mongo):
        self._mongo = mongo

    def top(self, limit: int) -> list[dict]:
        return self._mongo.top_puntajes(limit)

    def posicion(self, usuario_id: str) -> dict | None:
        return self._mongo.posicion_en_puntajes(usuario_id)

    def puntajes_de(self, usuario_ids: list[str]) -> list[dict]:
        return self._mongo.puntajes_de(usuario_ids)

    def partido_puntuado(self, partido_id: str) -> None:
        return None  # el ranking se lee directo de `puntajes`: no hay nada que propagar
