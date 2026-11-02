"""Factory para uvicorn: `uvicorn api_instrumentada.main:create_app --factory`."""
from fastapi import FastAPI, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from api_instrumentada import instrumentar
from api_instrumentada.metricas import REGISTRO

_colector = None


def create_app() -> FastAPI:
    global _colector
    from app import deps
    from app.main import create_app as create_app_hito10

    instrumentar.instrumentar_adaptadores()
    instrumentar.instrumentar_comentarios()
    if _colector is None:
        _colector = instrumentar.ColectorDisponibilidad(lambda: {
            "mongodb": deps.get_mongo(), "neo4j": deps.get_neo4j(), "cassandra": deps.get_cassandra(),
            "redis": deps.get_redis(), "influxdb": deps.get_influx(), "iris": deps.get_iris(),
        })
        REGISTRO.register(_colector)

    app = create_app_hito10()
    # Se registra después del middleware del Hito 10, así que queda por fuera y mide también sus 504.
    app.middleware("http")(instrumentar.middleware_http)

    @app.get("/metrics", include_in_schema=False)
    def metrics() -> Response:
        return Response(generate_latest(REGISTRO), media_type=CONTENT_TYPE_LATEST)

    return app
