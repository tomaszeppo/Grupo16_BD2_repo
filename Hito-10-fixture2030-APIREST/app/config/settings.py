from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Toda la configuración llega por variables de entorno o por un .env local (no versionado)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    timeout_segundos: float = 3.0
    max_limit: int = 100
    influx_max_puntos: int = 500
    influx_max_ventana_minutos: int = 120

    mongo_host: str = "localhost"
    mongo_port: int = 27017
    mongo_user: str = ""
    mongo_password: str = ""
    mongo_db: str = "fixture2030"

    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = ""
    neo4j_db: str = "neo4j"

    cassandra_host: str = "localhost"
    cassandra_port: int = 9042
    cassandra_keyspace: str = "fixture2030"

    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str = ""

    influx_url: str = "http://localhost:8181"
    influx_db: str = "fixture2030_metrics"
    influx_token: str = ""

    iris_host: str = "localhost"
    iris_port: int = 1972
    iris_namespace: str = "USER"
    iris_user: str = "fixture"
    iris_password: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
