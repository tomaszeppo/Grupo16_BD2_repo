from fastapi import APIRouter, Depends

from app.deps import get_partidos_mongo_service
from app.schemas.comunes import IdPartido
from app.schemas.errores import respuestas
from app.schemas.partido_detalle import CambioEstado, PartidoDetalle
from app.services.partidos_mongo import PartidosMongoService

router = APIRouter(tags=["MongoDB · Detalle del partido"])


@router.get(
    "/partidos/{partido_id}/detalle",
    response_model=PartidoDetalle,
    summary="Detalle persistente del partido con sus eventos",
    responses=respuestas(404),
)
def detalle_partido(partido_id: IdPartido, svc: PartidosMongoService = Depends(get_partidos_mongo_service)):
    return svc.detalle(partido_id)


@router.post(
    "/partidos/{partido_id}/estado",
    response_model=PartidoDetalle,
    summary="Cambiar el estado del partido (transición validada)",
    responses=respuestas(404, 409),
)
def cambiar_estado(
    partido_id: IdPartido, cuerpo: CambioEstado, svc: PartidosMongoService = Depends(get_partidos_mongo_service)
):
    """Transiciones: Programado → En juego → Finalizado. Repetir el estado actual no escribe."""
    return svc.cambiar_estado(partido_id, cuerpo.estado)
