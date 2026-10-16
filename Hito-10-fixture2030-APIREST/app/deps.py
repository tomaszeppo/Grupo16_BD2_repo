"""Proveedores de dependencias: adaptadores singleton (conexión perezosa) y servicios."""
from functools import lru_cache

from app.adapters.mongo import MongoAdapter
from app.config.settings import get_settings
from app.services.equipos import EquiposService


@lru_cache
def get_mongo() -> MongoAdapter:
    return MongoAdapter(get_settings())


def get_equipos_service() -> EquiposService:
    return EquiposService(get_mongo())
from app.adapters.neo4j import Neo4jAdapter  # noqa: E402
from app.services.partidos import PartidosService  # noqa: E402


@lru_cache
def get_neo4j() -> Neo4jAdapter:
    return Neo4jAdapter(get_settings())


def get_partidos_service() -> PartidosService:
    return PartidosService(get_neo4j())
from app.adapters.cassandra import CassandraAdapter  # noqa: E402
from app.services.comentarios import ComentariosService  # noqa: E402


@lru_cache
def get_cassandra() -> CassandraAdapter:
    return CassandraAdapter(get_settings())


def get_comentarios_service() -> ComentariosService:
    return ComentariosService(get_cassandra(), get_neo4j())
from app.adapters.redis import RedisAdapter  # noqa: E402
from app.services.sesiones import SesionesService  # noqa: E402


@lru_cache
def get_redis() -> RedisAdapter:
    return RedisAdapter(get_settings())


def get_sesiones_service() -> SesionesService:
    return SesionesService(get_redis())
from app.adapters.influx import InfluxAdapter  # noqa: E402
from app.services.estadisticas import EstadisticasService  # noqa: E402


@lru_cache
def get_influx() -> InfluxAdapter:
    return InfluxAdapter(get_settings())


def get_estadisticas_service() -> EstadisticasService:
    return EstadisticasService(get_influx(), get_settings())
from app.adapters.iris import IrisAdapter  # noqa: E402
from app.services.partidos_iris import PartidosIrisService  # noqa: E402


@lru_cache
def get_iris() -> IrisAdapter:
    return IrisAdapter(get_settings())


def get_partidos_iris_service() -> PartidosIrisService:
    return PartidosIrisService(get_iris())
