"""Proveedores de dependencias. Los adaptadores son únicos por proceso y se conectan al primer uso.

Para sumar una base se toca este archivo: se agrega su adaptador y se cambia el proveedor del puerto que
corresponda (`get_sesiones`, `get_ranking`, `get_publicador_eventos`). Ver docs/como_sumar_una_base.md.
"""
import hmac
from functools import lru_cache

from fastapi import Cookie, Depends, Header

from app.adapters.mongo import MongoAdapter
from app.adapters.cassandra import CassandraAdapter, salud_por_region
from app.adapters.influx import InfluxAdapter
from app.adapters.neo4j import Neo4jAdapter
from app.adapters.redis import RedisAdapter
from app.config.settings import Settings
from app.config.settings import get_settings as _settings
from app.errors import NoAutorizado
from app.puertos.eventos import PublicadorEventos, SinPublicador
from app.puertos.ranking import RankingMongo, RankingPort
from app.puertos.sesiones import SesionesPort, SesionesRedis
from app.reloj import Reloj, ahora
from app.services.calendario import Calendario
from app.services.fixture import FixtureService
from app.services.health import HealthService
from app.services.partidos_admin import PartidosAdminService
from app.services.prodes import ProdesService
from app.services.pronosticos import PronosticosService
from app.services.puntuacion import PuntuacionService
from app.services.ranking import RankingService
from app.services.usuarios import EquiposService, UsuariosService


# Los proveedores que solo arman o devuelven un objeto son `async def` a propósito: FastAPI manda cada
# dependencia `def` a un hilo aparte, y un pedido de pronóstico encadena siete u ocho. Como `async def` se
# resuelven en el momento, sin ese salto. Quedan como `def` solo los que hablan con una base (por ejemplo
# `usuario_actual`), porque eso sí bloquea y tiene que ir a un hilo.


# --- piezas únicas por proceso ---
@lru_cache
def _mongo() -> MongoAdapter:
    return MongoAdapter(_settings())


@lru_cache
def _influx() -> InfluxAdapter:
    return InfluxAdapter(_settings())


@lru_cache
def _neo4j() -> Neo4jAdapter:
    return Neo4jAdapter(_settings())


@lru_cache
def _redis() -> RedisAdapter:
    return RedisAdapter(_settings())


@lru_cache
def _cassandra() -> CassandraAdapter:
    return CassandraAdapter(_settings())


@lru_cache
def _calendario() -> Calendario:
    return Calendario(_neo4j(), _settings().calendario_ttl_segundos, ahora)


# --- bases ---
async def get_settings() -> Settings:
    return _settings()


async def get_reloj() -> Reloj:
    return ahora


async def get_mongo() -> MongoAdapter:
    return _mongo()


async def get_influx() -> InfluxAdapter:
    return _influx()


async def get_neo4j() -> Neo4jAdapter:
    return _neo4j()


async def get_redis() -> RedisAdapter:
    return _redis()


async def get_cassandra() -> CassandraAdapter:
    return _cassandra()


async def get_calendario() -> Calendario:
    return _calendario()


# --- puertos: acá se enchufan Redis e InfluxDB ---
async def get_sesiones(redis=Depends(get_redis), mongo=Depends(get_mongo),
                       settings: Settings = Depends(get_settings)) -> SesionesPort:
    """Sesiones en Redis (ver app/puertos/sesiones.py)."""
    return SesionesRedis(redis, mongo, settings.sesion_ttl_segundos)


async def get_ranking(mongo=Depends(get_mongo)) -> RankingPort:
    """Hoy: colección `puntajes` de MongoDB. Con Redis: devolver la implementación sobre el conjunto ordenado."""
    return RankingMongo(mongo)


async def get_publicador_eventos() -> PublicadorEventos:
    """Hoy: nadie escucha las jugadas. Con InfluxDB: devolver la implementación que escribe la serie."""
    return SinPublicador()


# --- quién hace el pedido ---
async def credencial(x_sesion: str | None = Header(None, description="Token de la sesión (POST /sesiones)"),
                     sesion: str | None = Cookie(None, include_in_schema=False)) -> str | None:
    """El encabezado manda; si no está, la cookie que dejó POST /sesiones."""
    return x_sesion or sesion


def usuario_actual(token: str | None = Depends(credencial), sesiones: SesionesPort = Depends(get_sesiones)) -> str:
    return sesiones.usuario_de(token)


def sesion_actual(token: str | None = Depends(credencial),
                  sesiones: SesionesPort = Depends(get_sesiones)) -> tuple[str, str]:
    """(token, usuario). La usa la conexión en vivo para contar espectadores por sesión."""
    return token, sesiones.usuario_de(token)


async def requiere_admin(x_admin_clave: str | None = Header(None, description="Clave de administración"),
                   settings: Settings = Depends(get_settings)) -> None:
    esperada = settings.admin_clave
    # compare_digest tarda lo mismo acierte o no: el tiempo de respuesta no ayuda a adivinar la clave
    if not esperada or not x_admin_clave or not hmac.compare_digest(x_admin_clave.encode(), esperada.encode()):
        raise NoAutorizado("Falta el encabezado X-Admin-Clave o no es correcto.")


# --- servicios ---
async def get_health_service(mongo=Depends(get_mongo), neo4j=Depends(get_neo4j), redis=Depends(get_redis),
                             cassandra=Depends(get_cassandra), calendario=Depends(get_calendario)) -> HealthService:
    return HealthService({"mongodb": mongo, "neo4j": neo4j, "redis": redis, **salud_por_region(cassandra)},
                         calendario)


async def get_fixture_service(neo4j=Depends(get_neo4j), calendario=Depends(get_calendario)) -> FixtureService:
    return FixtureService(neo4j, calendario)


async def get_usuarios_service(mongo=Depends(get_mongo), reloj=Depends(get_reloj)) -> UsuariosService:
    return UsuariosService(mongo, reloj)


async def get_equipos_service(mongo=Depends(get_mongo)) -> EquiposService:
    return EquiposService(mongo)


async def get_prodes_service(mongo=Depends(get_mongo), reloj=Depends(get_reloj),
                       settings: Settings = Depends(get_settings)) -> ProdesService:
    return ProdesService(mongo, reloj, settings.prode_max_integrantes)


async def get_pronosticos_service(mongo=Depends(get_mongo), calendario=Depends(get_calendario),
                            reloj=Depends(get_reloj)) -> PronosticosService:
    return PronosticosService(mongo, calendario, reloj)


async def get_partidos_admin_service(neo4j=Depends(get_neo4j), calendario=Depends(get_calendario),
                               reloj=Depends(get_reloj),
                               publicador=Depends(get_publicador_eventos)) -> PartidosAdminService:
    return PartidosAdminService(neo4j, calendario, reloj, publicador)


async def get_puntuacion_service(mongo=Depends(get_mongo), neo4j=Depends(get_neo4j), calendario=Depends(get_calendario),
                           reloj=Depends(get_reloj), ranking=Depends(get_ranking),
                           settings: Settings = Depends(get_settings)) -> PuntuacionService:
    return PuntuacionService(mongo, neo4j, calendario, reloj, ranking, settings.puntuacion_toma_vencida_segundos)


async def get_ranking_service(ranking=Depends(get_ranking), mongo=Depends(get_mongo)) -> RankingService:
    return RankingService(ranking, mongo)


def precalentar() -> None:
    """Abre las conexiones y deja cargada la copia del calendario al arrancar cada proceso.

    Sin esto, el primer pedido de cada proceso pagaba la conexión a Neo4j y la compilación de las consultas,
    y podía pasarse del tiempo de espera. Corre en un hilo aparte: si una base no está, la API arranca igual.
    """
    import threading

    from app.observability import logger

    def trabajo() -> None:
        pasos = (
            ("mongodb", lambda: _mongo().ping()),
            ("redis", lambda: _redis().ping()),
            ("calendario", lambda: _calendario().refrescar()),
            ("neo4j", lambda: _neo4j().preparar_consultas()),
        )
        for nombre, paso in pasos:
            for _ in range(3):  # recién levantado, Neo4j puede tardar más que el tiempo de espera normal
                try:
                    paso()
                    break
                except Exception as exc:
                    logger.warning("precalentamiento paso=%s resultado=%s", nombre, type(exc).__name__)

    threading.Thread(target=trabajo, daemon=True, name="precalentar").start()
