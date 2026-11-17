from datetime import date

from app.errors import NoEncontrado


class FixtureService:
    """Lecturas del fixture. Todo sale de Neo4j, que gobierna calendario, equipos de cada partido y jugadas.

    El listado se sirve desde la copia en memoria del calendario (hasta 30 segundos de atraso); el detalle
    de un partido y sus jugadas se consultan a Neo4j en el momento.
    """

    def __init__(self, neo4j, calendario):
        self._neo4j = neo4j
        self._calendario = calendario

    def listar(self, fase: str | None, fecha: date | None, estado: str | None) -> tuple[list[dict], float | None]:
        partidos = self._calendario.listar(fase, fecha, estado)
        return partidos, self._calendario.estado()["antiguedad_segundos"]

    def partido(self, partido_id: str) -> dict:
        partido = self._neo4j.obtener_partido(partido_id)
        if partido is None:
            raise NoEncontrado(f"No existe el partido {partido_id}.")
        return partido

    def eventos(self, partido_id: str, limit: int) -> list[dict]:
        eventos = self._neo4j.listar_eventos(partido_id, limit)
        if eventos is None:
            raise NoEncontrado(f"No existe el partido {partido_id}.")
        return eventos

    def cadena(self, partido_id: str, evento_id: str) -> list[dict]:
        cadena = self._neo4j.cadena_de_evento(partido_id, evento_id)
        if cadena is None:
            raise NoEncontrado(f"No existe la jugada {evento_id} en el partido {partido_id}.")
        return cadena

    def camino(self, codigo: str) -> dict:
        camino = self._neo4j.camino_de_equipo(codigo)
        if camino is None:
            raise NoEncontrado(f"No existe el equipo {codigo}.")
        return camino

    def participacion_en_goles(self, limit: int) -> list[dict]:
        return self._neo4j.participacion_en_goles(limit)
