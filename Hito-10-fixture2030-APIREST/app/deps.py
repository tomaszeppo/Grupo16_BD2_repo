"""Proveedores de dependencias: adaptadores singleton (conexión perezosa) y servicios."""
from functools import lru_cache

from app.adapters.cassandra import CassandraAdapter
from app.adapters.influx import InfluxAdapter
from app.adapters.mongo import MongoAdapter
from app.adapters.neo4j import Neo4jAdapter
from app.adapters.redis import RedisAdapter
from app.config.settings import get_settings
from app.services.comentarios import ComentariosService
from app.services.equipos import EquiposService
from app.services.estadisticas import EstadisticasService
from app.services.health import HealthService
from app.services.partidos import PartidosService
from app.services.partidos_mongo import PartidosMongoService
from app.services.sesiones import SesionesService


@lru_cache
def get_mongo() -> MongoAdapter:
    return MongoAdapter(get_settings())


@lru_cache
def get_neo4j() -> Neo4jAdapter:
    return Neo4jAdapter(get_settings())


@lru_cache
def get_cassandra() -> CassandraAdapter:
    return CassandraAdapter(get_settings())


@lru_cache
def get_redis() -> RedisAdapter:
    return RedisAdapter(get_settings())


@lru_cache
def get_influx() -> InfluxAdapter:
    return InfluxAdapter(get_settings())


def get_equipos_service() -> EquiposService:
    return EquiposService(get_mongo())


def get_partidos_service() -> PartidosService:
    return PartidosService(get_neo4j())


def get_comentarios_service() -> ComentariosService:
    return ComentariosService(get_cassandra(), get_neo4j())


def get_sesiones_service() -> SesionesService:
    return SesionesService(get_redis())


def get_estadisticas_service() -> EstadisticasService:
    return EstadisticasService(get_influx(), get_settings())


def get_partidos_mongo_service() -> PartidosMongoService:
    return PartidosMongoService(get_mongo())


def get_health_service() -> HealthService:
    return HealthService(
        {
            "mongodb": get_mongo(), "neo4j": get_neo4j(), "cassandra": get_cassandra(),
            "redis": get_redis(), "influxdb": get_influx(),
        }
    )
