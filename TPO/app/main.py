from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.config.settings import Settings, get_settings
from app.manejadores import registrar_manejadores
from app.metricas import instrumentar
from app.observability import configurar_logging, crear_middleware

DESCRIPCION = (
    "API del prode del Mundial 2030. Cada endpoint resuelve un caso de uso contra la base que gobierna ese dato: "
    "MongoDB para el prode y Neo4j para el fixture y los partidos. No acepta consultas libres. "
    "Todos los errores usan el formato {error:{codigo,mensaje,request_id}}."
)

TAGS = [
    {"name": "Neo4j · Fixture y partidos", "description": "Calendario, jugadas y recorridos del grafo."},
    {"name": "MongoDB · Prode", "description": "Usuarios, prodes, pronósticos y ranking."},
    {"name": "MongoDB · Equipos", "description": "Catálogo de equipos y planteles."},
    {"name": "Administración", "description": "Operación del partido para la demostración. Requiere X-Admin-Clave."},
    {"name": "Sistema", "description": "Salud y métricas."},
]


@asynccontextmanager
async def _arranque(app: FastAPI):
    from app.deps import precalentar

    precalentar()
    yield


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configurar_logging()
    app = FastAPI(title="Prode Mundial 2030", version="1.0.0", description=DESCRIPCION, openapi_tags=TAGS,
                  lifespan=_arranque)
    app.middleware("http")(crear_middleware(settings.deadline_segundos))
    registrar_manejadores(app)
    instrumentar(app)

    from app.routes import admin, fixture, health, prode, ranking

    app.include_router(fixture.router)
    app.include_router(prode.router)
    app.include_router(ranking.router)
    app.include_router(admin.router)
    app.include_router(prode.equipos_router)
    app.include_router(health.router)

    # Interfaz de demostración: archivos estáticos servidos por la misma API (mismo origen, sin CORS).
    @app.get("/", include_in_schema=False)
    def raiz() -> RedirectResponse:
        return RedirectResponse("/demo/")

    app.mount("/demo", StaticFiles(directory=Path(__file__).resolve().parent.parent / "ui", html=True), name="demo")
    return app
