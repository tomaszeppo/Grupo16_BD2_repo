import time

import pytest

from app.adapters.cassandra import CassandraAdapter
from app.adapters.influx import InfluxAdapter
from app.adapters.iris import IrisAdapter
from app.adapters.mongo import MongoAdapter
from app.adapters.neo4j import Neo4jAdapter
from app.adapters.redis import RedisAdapter
from app.config.settings import Settings
from app.errors import DependenciaNoDisponible, DependenciaTimeout

pytestmark = pytest.mark.drivers

CASOS = [
    ("mongodb", MongoAdapter, lambda a: a.obtener_equipo("ARG")),
    ("neo4j", Neo4jAdapter, lambda a: a.obtener_partido("P-01")),
    ("cassandra", CassandraAdapter, lambda a: a.ping()),
    ("redis", RedisAdapter, lambda a: a.obtener_sesion("U001")),
    ("influxdb", InfluxAdapter, lambda a: a.ping()),
    ("iris", IrisAdapter, lambda a: a.obtener_partido("P-01")),
]


@pytest.mark.parametrize("nombre,clase,accion", CASOS, ids=[c[0] for c in CASOS])
def test_fuente_inaccesible_da_error_controlado_y_acotado(nombre, clase, accion):
    s = Settings(
        _env_file=None, timeout_segundos=1.0,
        mongo_host="127.0.0.1", mongo_port=1, neo4j_uri="bolt://127.0.0.1:1",
        cassandra_host="127.0.0.1", cassandra_port=1, redis_host="127.0.0.1", redis_port=1,
        influx_url="http://127.0.0.1:1", iris_host="127.0.0.1", iris_port=1,
    )
    inicio = time.perf_counter()
    with pytest.raises((DependenciaNoDisponible, DependenciaTimeout)) as e:
        accion(clase(s))
    assert time.perf_counter() - inicio < 10, "la request no debe quedar esperando indefinidamente"
    assert e.value.fuente == nombre
    assert "127.0.0.1" not in str(e.value)  # el mensaje al consumidor no filtra hosts internos
