from fastapi import FastAPI

from app.manejadores import registrar_manejadores
from app.observability import configurar_logging, request_id_middleware

DESCRIPCION = (
    "API REST integrada del Fixture Mundial 2030. Cada endpoint resuelve un caso de uso concreto contra "
    "la fuente NoSQL que corresponde (MongoDB, Neo4j, Cassandra, Redis, InfluxDB, IRIS). "
    "No acepta consultas libres. Todos los errores usan el formato {error:{codigo,mensaje,request_id}}."
)

TAGS = [
    {"name": "MongoDB · Equipos y jugadores", "description": "Información documental."},
    {"name": "Neo4j · Partidos y eventos", "description": "Relaciones partido–equipo–estadio–evento."},
    {"name": "Cassandra · Comentarios", "description": "Lectura por partición y alta idempotente."},
    {"name": "Redis · Sesiones", "description": "Estado temporal con TTL."},
    {"name": "InfluxDB · Estadísticas", "description": "Series temporales acotadas por ventana."},
    {"name": "IRIS · Partido (objetos)", "description": "Entidad compleja y transición de estado validada."},
    {"name": "Sistema", "description": "Salud de la API y de sus dependencias."},
]


def create_app() -> FastAPI:
    configurar_logging()
    app = FastAPI(
        title="Fixture 2030 — API integrada",
        version="1.0.0",
        description=DESCRIPCION,
        servers=[{"url": "http://localhost:8000", "description": "Local (notebook o contenedor, puerto 8000)"}],
        openapi_tags=TAGS,
    )
    app.middleware("http")(request_id_middleware)
    registrar_manejadores(app)

    from app.routes import comentarios, equipos, estadisticas, health, partidos_grafo, partidos_iris, sesiones

    app.include_router(equipos.router)
    app.include_router(partidos_grafo.router)
    app.include_router(comentarios.router)
    app.include_router(sesiones.router)
    app.include_router(estadisticas.router)
    app.include_router(partidos_iris.router)
    app.include_router(health.router)
    return app
