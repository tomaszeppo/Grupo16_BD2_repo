from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.config.settings import Settings
from seed import datos
from tests.apoyo import armar_app
from tests.falsos import CassandraFalso, MongoFalso, Neo4jFalso, RedisFalso

INICIO = datetime(2030, 6, 13, 15, 0, tzinfo=timezone.utc)  # hora de P-03
ADMIN = {"X-Admin-Clave": "clave-de-prueba"}


class RelojFijo:
    def __init__(self, instante: datetime):
        self.instante = instante

    def __call__(self) -> datetime:
        return self.instante


@pytest.fixture
def settings():
    # Valores explícitos: las pruebas no dependen de las variables de entorno del contenedor donde corran.
    return Settings(_env_file=None, admin_clave="clave-de-prueba", pronosticos_hasta_inicio_real=False,
                    redis_enabled=False)


@pytest.fixture
def reloj():
    """Un día antes del primer partido sin jugar: todo el fixture está abierto a pronósticos."""
    return RelojFijo(datetime(2030, 6, 12, 15, 0, tzinfo=timezone.utc))


@pytest.fixture
def mongo():
    return MongoFalso()


@pytest.fixture
def neo4j():
    return Neo4jFalso(datos.generar(INICIO))


@pytest.fixture
def redis():
    return RedisFalso()


@pytest.fixture
def cassandra():
    return CassandraFalso()


@pytest.fixture
def app(settings, mongo, neo4j, reloj, redis, cassandra):
    return armar_app(settings, mongo, neo4j, reloj, redis, cassandra)


@pytest.fixture
def cliente(app):
    return TestClient(app, raise_server_exceptions=False)
