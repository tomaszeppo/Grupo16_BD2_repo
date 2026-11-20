from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Toda la configuración llega por variables de entorno o por un .env local (no versionado)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    timeout_segundos: float = 3.0
    deadline_segundos: float = 10.0  # tope por pedido: vencido, la API responde 504 sin esperar a la base
    max_limit: int = 100

    # Fuera de Docker solo se puede hablar con un nodo por conexión directa (ver README).
    mongo_uri: str = "mongodb://localhost:27217/?directConnection=true"
    mongo_db: str = "prode2030"

    neo4j_uri: str = "bolt://localhost:7688"
    neo4j_user: str = "neo4j"
    neo4j_password: str = ""
    neo4j_db: str = "neo4j"

    redis_url: str = "redis://localhost:6380/0"
    redis_password: str = ""
    redis_replica_url: str = "redis://localhost:6381/0"
    sesion_ttl_segundos: int = 86400  # se renueva con cada uso

    cassandra_america: str = "cassandra_america"  # nodo de contacto de cada datacenter
    cassandra_europa: str = "cassandra_europa"
    cassandra_puerto: int = 9042

    influx_url: str = "http://influxdb:8181"
    influx_db: str = "fixture2030_metrics"
    influx_token: str = ""

    calendario_ttl_segundos: float = 30.0  # 0 = consultar Neo4j en cada pronóstico (solo para comparar en las pruebas)
    prode_max_integrantes: int = 100
    admin_clave: str = ""  # vacía = administración deshabilitada
    puntuacion_toma_vencida_segundos: float = 120.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
