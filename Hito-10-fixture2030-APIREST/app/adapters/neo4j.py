from app.adapters.base import operacion
from app.config.settings import Settings
from app.errors import ApiError, DependenciaNoDisponible, DependenciaTimeout

FUENTE = "neo4j"

# Cypher fijo y parametrizado: el cliente nunca aporta texto de consulta, solo el valor de $id / $limit.
CYPHER_PARTIDO = """
MATCH (p:Partido {id: $id})
OPTIONAL MATCH (p)-[:SE_JUEGA_EN]->(est:Estadio)
OPTIONAL MATCH (eq:Equipo)-[:PARTICIPA_EN]->(p)
WITH p, est, eq ORDER BY eq.codigo
RETURN p.id AS id, p.fecha AS fecha, p.fase AS fase,
       est {.id, .nombre, .ciudad} AS estadio,
       collect(eq {.codigo, .nombre}) AS equipos,
       p.equipoGanador AS ganador, p.equipoPerdedor AS perdedor,
       p.golesGanador AS goles_ganador, p.golesPerdedor AS goles_perdedor,
       p.origenResultado AS origen
"""

CYPHER_EVENTOS = """
MATCH (p:Partido {id: $id})
OPTIONAL MATCH (ev:Evento)-[:OCURRE_EN]->(p)
WITH p, ev ORDER BY ev.minuto, ev.id
LIMIT $limit
RETURN p.id AS partido, collect(ev {.id, .tipo, .minuto}) AS eventos
"""


def _traducir(exc: Exception) -> ApiError | None:
    try:
        from neo4j.exceptions import DriverError, Neo4jError
    except ImportError:
        return None
    if "TimedOut" in str(getattr(exc, "code", "")):
        return DependenciaTimeout(FUENTE)
    if isinstance(exc, (DriverError, Neo4jError)):
        return DependenciaNoDisponible(FUENTE)
    return None


class Neo4jAdapter:
    """Grafo del Hito 5: Equipo, Partido, Estadio, Evento y sus relaciones."""

    fuente = FUENTE

    def __init__(self, settings: Settings):
        self._s = settings
        self._driver = None

    def _drv(self):
        if self._driver is None:
            from neo4j import GraphDatabase

            t = self._s.timeout_segundos
            self._driver = GraphDatabase.driver(
                self._s.neo4j_uri,
                auth=(self._s.neo4j_user, self._s.neo4j_password),
                connection_timeout=t,
                connection_acquisition_timeout=t,
                max_transaction_retry_time=t,
            )
        return self._driver

    def _leer(self, cypher: str, **params) -> list[dict]:
        from neo4j import unit_of_work

        @unit_of_work(timeout=self._s.timeout_segundos)  # timeout de la transacción (el servidor la aborta al vencer)
        def trabajo(tx):
            return [r.data() for r in tx.run(cypher, **params)]

        with self._drv().session(database=self._s.neo4j_db) as sesion:
            return sesion.execute_read(trabajo)

    def obtener_partido(self, partido_id: str) -> dict | None:
        with operacion(FUENTE, "obtener_partido", _traducir):
            filas = self._leer(CYPHER_PARTIDO, id=partido_id)
            return filas[0] if filas else None

    def listar_eventos(self, partido_id: str, limit: int) -> list[dict] | None:
        with operacion(FUENTE, "listar_eventos", _traducir):
            filas = self._leer(CYPHER_EVENTOS, id=partido_id, limit=limit)
            return filas[0]["eventos"] if filas else None

    def ping(self) -> None:
        with operacion(FUENTE, "ping", _traducir):
            self._drv().verify_connectivity()
