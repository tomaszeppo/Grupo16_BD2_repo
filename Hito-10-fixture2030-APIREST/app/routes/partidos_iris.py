from fastapi import APIRouter, Depends

from app.deps import get_partidos_iris_service
from app.schemas.comunes import IdPartido
from app.schemas.errores import respuestas
from app.schemas.iris import CambioEstado, PartidoIris
from app.services.partidos_iris import PartidosIrisService

router = APIRouter(tags=["IRIS · Partido (objetos)"])


@router.get(
    "/partidos/{partido_id}/detalle",
    response_model=PartidoIris,
    summary="Detalle del partido con sus eventos (objetos IRIS)",
    responses=respuestas(404),
)
def detalle_partido(partido_id: IdPartido, svc: PartidosIrisService = Depends(get_partidos_iris_service)):
    """Lee `Fixture.Partido` y sus `Fixture.Evento` hijos. El id interno de IRIS no se expone: la clave pública es `codigo`."""
    return svc.detalle(partido_id)


@router.post(
    "/partidos/{partido_id}/estado",
    response_model=PartidoIris,
    summary="Cambiar el estado del partido (transición validada)",
    responses=respuestas(404, 409),
)
def cambiar_estado(
    partido_id: IdPartido, cuerpo: CambioEstado, svc: PartidosIrisService = Depends(get_partidos_iris_service)
):
    """Flujo permitido: Programado → En juego → Finalizado (regla `CambiarEstado` de la clase). Transición inválida → 409.
    Idempotente: pedir el estado en el que ya está devuelve 200 sin escribir."""
    return svc.cambiar_estado(partido_id, cuerpo.estado)
