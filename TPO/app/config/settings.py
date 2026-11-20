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

    influx_url: str = "http://influxdb:8181"
    influx_db: str = "fixture2030_metrics"
    influx_raw_db: str = "fixture2030_raw"
    influx_resumen_db: str = "fixture2030_resumenes"
    influx_token: str = ""

    calendario_ttl_segundos: float = 30.0  # 0 = consultar Neo4j en cada pronóstico (solo para comparar en las pruebas)
    prode_max_integrantes: int = 100
    admin_clave: str = ""  # vacía = administración deshabilitada
    simulador_api_url: str = "http://127.0.0.1:8010"
    pronosticos_hasta_inicio_real: bool = False
    simulador_comentarios_por_region_segundo: int = 4
    redis_enabled: bool = False
    redis_url: str = "redis://redis:6379/0"
    redis_lote: int = 500
    redis_persistencia_demora_segundos: int = 15
    puntuacion_toma_vencida_segundos: float = 120.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
