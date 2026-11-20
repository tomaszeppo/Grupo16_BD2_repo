"""Pruebas contra las bases reales. Corren dentro de la red del Compose:

    docker compose run --rm -e PERMITIR_REINICIO=1 herramientas python -m pytest tests/integration -q

MongoDB: usan una base aparte (`prode2030_pruebas`), no tocan la del laboratorio.
Neo4j: la edición comunitaria tiene una sola base, así que BORRAN el grafo y lo vuelven a cargar.
Por eso piden PERMITIR_REINICIO=1, y después hay que correr `python -m seed.run` otra vez.
"""
import os

# Estas pruebas cubren el camino de MongoDB (puntuación y ranking) y el cierre de pronósticos a la hora
# programada. El Compose activa el ranking en Redis y los pronósticos hasta el inicio real; el camino de Redis
# tiene sus propias pruebas en tests/redis_integration.
os.environ["REDIS_ENABLED"] = "false"
os.environ["PRONOSTICOS_HASTA_INICIO_REAL"] = "false"
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.adapters.mongo import MongoAdapter
from app.adapters.neo4j import Neo4jAdapter
from app.adapters.redis import RedisAdapter
from app.config.settings import Settings
from tests.apoyo import armar_app
from seed import cargar_mongo, cargar_neo4j, datos

INICIO = datetime(2030, 6, 13, 15, 0, tzinfo=timezone.utc)
COLECCIONES = ["usuarios", "prodes", "pronosticos", "resultados", "puntajes", "rankings_historicos",
               "equipos", "jugadores", "contadores"]


def pytest_collection_modifyitems(config, items):
    if os.environ.get("PERMITIR_REINICIO") == "1":
        return
    motivo = pytest.mark.skip(reason="borran el grafo de Neo4j: correr con PERMITIR_REINICIO=1 (ver tests/integration/conftest.py)")
    for item in items:
        if "integration" in str(item.fspath):
            item.add_marker(motivo)


@pytest.fixture(scope="session")
def ajustes():
    base = Settings()
    # Redis: base 1 para las pruebas, la 0 es la del laboratorio.
    redis_url = base.redis_url.rsplit("/", 1)[0] + "/1"
    return Settings(mongo_db="prode2030_pruebas", admin_clave="clave-de-prueba", timeout_segundos=10, redis_url=redis_url)


@pytest.fixture(scope="session")
def mongo(ajustes):
    return MongoAdapter(ajustes)


@pytest.fixture(scope="session")
def neo4j(ajustes):
    return Neo4jAdapter(ajustes)


@pytest.fixture(scope="session")
def redis_real(ajustes):
    adaptador = RedisAdapter(ajustes)
    adaptador.cli.flushdb()
    return adaptador


@pytest.fixture(scope="session")
def fixture_datos():
    return datos.generar(INICIO)


@pytest.fixture
def bases_limpias(mongo, neo4j):
    for nombre in COLECCIONES:
        mongo.db.drop_collection(nombre)
    with neo4j._drv().session(database="neo4j") as sesion:  # sin el tope de 3 s de los pedidos de la API
        sesion.run("MATCH (n) DETACH DELETE n").consume()


@pytest.fixture
def cargado(bases_limpias, mongo, neo4j, fixture_datos):
    """Las dos bases recién cargadas con el fixture de laboratorio."""
    cargar_mongo.preparar(mongo.db)
    cargar_mongo.cargar(mongo.db, fixture_datos)
    cargar_neo4j.cargar(neo4j._drv(), "neo4j", fixture_datos)
    return fixture_datos


class RelojFijo:
    def __init__(self, instante: datetime):
        self.instante = instante

    def __call__(self) -> datetime:
        return self.instante


@pytest.fixture
def reloj():
    """Un día antes del primer partido sin jugar: todo el fixture está abierto a pronósticos."""
    return RelojFijo(datetime(2030, 6, 12, 15, 0, tzinfo=timezone.utc))


@pytest.fixture
def app(ajustes, mongo, neo4j, reloj, cargado, redis_real):
    return armar_app(ajustes, mongo, neo4j, reloj, redis_real)


@pytest.fixture
def cliente(app):
    return TestClient(app, raise_server_exceptions=False)


ADMIN = {"X-Admin-Clave": "clave-de-prueba"}
