from datetime import date

from fastapi import APIRouter, Depends

from app.config.settings import Settings
from app.deps import get_fixture_service, get_settings
from app.schemas.comunes import CodigoEquipo, Estado, EventoId, Fase, Limite, PartidoId
from app.services.fixture import FixtureService

router = APIRouter(tags=["Neo4j · Fixture y partidos"])
FUENTE = "neo4j"


@router.get("/partidos", summary="Fixture, con filtros por fase, fecha y estado")
def listar_partidos(fase: Fase | None = None, fecha: date | None = None, estado: Estado | None = None,
                    svc: FixtureService = Depends(get_fixture_service), settings: Settings = Depends(get_settings)) -> dict:
    """Sale de la copia del calendario que guarda cada proceso de la API; `antiguedad_segundos` dice de cuándo es."""
    partidos, antiguedad = svc.listar(fase, fecha, estado)
    return {"fuente": FUENTE, "antiguedad_segundos": antiguedad, "total": len(partidos), "partidos": partidos,
            "pronosticos_hasta_inicio_real": settings.pronosticos_hasta_inicio_real}


@router.get("/partidos/{partido_id}", summary="Un partido con sus equipos y su estadio")
def obtener_partido(partido_id: PartidoId, svc: FixtureService = Depends(get_fixture_service),
                    settings: Settings = Depends(get_settings)) -> dict:
    return {"fuente": FUENTE, "partido": svc.partido(partido_id),
            "pronosticos_hasta_inicio_real": settings.pronosticos_hasta_inicio_real}


@router.get("/partidos/{partido_id}/eventos", summary="Jugadas del partido, en orden")
def listar_eventos(partido_id: PartidoId, limit: Limite = 100,
                   svc: FixtureService = Depends(get_fixture_service)) -> dict:
    return {"fuente": FUENTE, "partido": partido_id, "eventos": svc.eventos(partido_id, limit)}


@router.get("/partidos/{partido_id}/eventos/{evento_id}/cadena", summary="Las jugadas que llevaron a una jugada")
def cadena_de_evento(partido_id: PartidoId, evento_id: EventoId,
                     svc: FixtureService = Depends(get_fixture_service)) -> dict:
    """Recorre hacia atrás la relación INFLUYE_EN: por ejemplo, el pase y el tiro que terminaron en un gol."""
    return {"fuente": FUENTE, "partido": partido_id, "cadena": svc.cadena(partido_id, evento_id)}


@router.get("/equipos/{codigo}/camino", summary="Partidos de un equipo y lo que le queda hasta la final")
def camino_de_equipo(codigo: CodigoEquipo, svc: FixtureService = Depends(get_fixture_service)) -> dict:
    return {"fuente": FUENTE, **svc.camino(codigo)}


@router.get("/estadisticas/participacion-en-goles", summary="Jugadores que más participaron en goles")
def participacion_en_goles(limit: Limite = 10, svc: FixtureService = Depends(get_fixture_service)) -> dict:
    """Cuenta al que hizo el gol y a quienes protagonizaron una jugada que llevó a él."""
    return {"fuente": FUENTE, "jugadores": svc.participacion_en_goles(limit)}
