from app.errors import Conflicto, NoEncontrado
from app.reloj import Reloj


class PronosticosService:
    """Un pronóstico por usuario y partido, que se puede corregir hasta que el partido empieza.

    Siempre se valida contra la copia del calendario: Neo4j no está en el camino de cada pronóstico. En el
    laboratorio (`hasta_inicio_real`) se admite pronosticar pasado el horario previsto, hasta que el partido
    se pone en juego. Si otro proceso todavía no se enteró del inicio y acepta un pronóstico tardío, la
    puntuación lo anula: compara la hora de carga con el inicio real (ver docs/decisiones.md).
    """

    def __init__(self, mongo, calendario, reloj: Reloj, hasta_inicio_real: bool = False):
        self._mongo = mongo
        self._calendario = calendario
        self._reloj = reloj
        self._hasta_inicio_real = hasta_inicio_real

    def guardar(self, usuario_id: str, partido_id: str, goles_local: int, goles_visitante: int) -> tuple[dict, bool]:
        partido = self._calendario.partido(partido_id)
        if partido is None:
            raise NoEncontrado(f"No existe el partido {partido_id}.")
        if partido["local"] is None or partido["visitante"] is None:
            raise Conflicto("Todavía no están definidos los equipos de este partido.")
        if partido["estado"] != "Programado":
            raise Conflicto("El partido ya empezó: no se puede cargar ni corregir el pronóstico.")
        ahora = self._reloj()
        if not self._hasta_inicio_real and ahora >= partido["fecha_hora"]:
            raise Conflicto("Ya pasó el horario de inicio del partido: no se puede cargar ni corregir el pronóstico.")
        return self._mongo.guardar_pronostico(usuario_id, partido_id, goles_local, goles_visitante, ahora)

    def del_partido(self, usuario_id: str, partido_id: str) -> dict | None:
        return self._mongo.obtener_pronostico(usuario_id, partido_id)

    def de_usuario(self, usuario_id: str, limit: int, offset: int) -> tuple[list[dict], int]:
        return self._mongo.pronosticos_de(usuario_id, limit, offset)
