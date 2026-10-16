from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.deps import get_partidos_service
from app.schemas.comunes import IdPartido
from app.schemas.errores import respuestas
from app.schemas.partidos import EventosPartido, PartidoGrafo
from app.services.partidos import PartidosService

router = APIRouter(tags=["Neo4j · Partidos y eventos"])


@router.get(
    "/partidos/{partido_id}",
    response_model=PartidoGrafo,
    summary="Obtener un partido con equipos y estadio",
    responses=respuestas(404),
)
def obtener_partido(partido_id: IdPartido, svc: PartidosService = Depends(get_partidos_service)):
    """Recorre `(Equipo)-[:PARTICIPA_EN]->(Partido)-[:SE_JUEGA_EN]->(Estadio)` con Cypher parametrizado."""
    return svc.obtener_partido(partido_id)


@router.get(
    "/partidos/{partido_id}/eventos",
    response_model=EventosPartido,
    summary="Eventos de un partido",
    responses=respuestas(404),
)
def listar_eventos(
    partido_id: IdPartido,
    limit: Annotated[int, Query(ge=1, le=200, description="Máximo de eventos (1–200)")] = 50,
    svc: PartidosService = Depends(get_partidos_service),
):
    """Recorre `(Evento)-[:OCURRE_EN]->(Partido)` ordenado por minuto. Partido inexistente → 404; sin eventos → 200 vacío."""
    return svc.listar_eventos(partido_id, limit)
