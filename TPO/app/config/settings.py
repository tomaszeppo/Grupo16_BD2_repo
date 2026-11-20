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
    chat_segundos_entre_comentarios: float = 5.0  # modo lento, por usuario
    presencia_refresco_segundos: float = 5.0  # cada cuánto una conexión en vivo renueva su presencia
    presencia_vencimiento_segundos: float = 15.0  # sin renovar en este tiempo, deja de contar
    vivo_latido_segundos: float = 15.0  # mensaje vacío para que nada corte una conexión callada

    cassandra_america: str = "cassandra_america"  # nodo de contacto de cada datacenter
    cassandra_europa: str = "cassandra_europa"
    cassandra_puerto: int = 9042

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
    redis_enabled: bool = False  # solo el ranking en Redis; sesiones y vivo usan Redis siempre
    redis_lote: int = 500
    redis_persistencia_demora_segundos: int = 15
    puntuacion_toma_vencida_segundos: float = 120.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
