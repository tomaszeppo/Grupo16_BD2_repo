from app.errors import Conflicto, NoEncontrado
from app.reloj import Reloj


class PronosticosService:
    """Un pronóstico por usuario y partido, que se puede corregir hasta que el partido empieza.

    El partido se valida contra la copia del calendario y no contra Neo4j: así el pico de pronósticos
    solo escribe en MongoDB.
    """

    def __init__(self, mongo, calendario, reloj: Reloj):
        self._mongo = mongo
        self._calendario = calendario
        self._reloj = reloj

    def guardar(self, usuario_id: str, partido_id: str, goles_local: int, goles_visitante: int) -> tuple[dict, bool]:
        partido = self._calendario.partido(partido_id)
        if partido is None:
            raise NoEncontrado(f"No existe el partido {partido_id}.")
        if partido["local"] is None or partido["visitante"] is None:
            raise Conflicto("Todavía no están definidos los equipos de este partido.")
        if partido["estado"] != "Programado":
            raise Conflicto("El partido ya empezó: no se puede cargar ni corregir el pronóstico.")
        ahora = self._reloj()
        if ahora >= partido["fecha_hora"]:
            raise Conflicto("Ya pasó el horario de inicio del partido: no se puede cargar ni corregir el pronóstico.")
        return self._mongo.guardar_pronostico(usuario_id, partido_id, goles_local, goles_visitante, ahora)

    def de_usuario(self, usuario_id: str, limit: int, offset: int) -> tuple[list[dict], int]:
        return self._mongo.pronosticos_de(usuario_id, limit, offset)
