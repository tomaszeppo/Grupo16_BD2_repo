from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.deps import get_estadisticas_service
from app.schemas.comunes import IdPartido
from app.schemas.errores import respuestas
from app.schemas.estadisticas import Agregacion, DesdeQuery, Estadisticas, HastaQuery
from app.services.estadisticas import EstadisticasService

router = APIRouter(tags=["InfluxDB · Estadísticas"])


@router.get(
    "/partidos/{partido_id}/estadisticas",
    response_model=Estadisticas,
    summary="Estadísticas temporales de un partido (ventana acotada y agregación)",
    responses=respuestas(),
)
def obtener_estadisticas(
    partido_id: IdPartido,
    desde: DesdeQuery,
    hasta: HastaQuery,
    equipo: Annotated[str | None, Query(pattern=r"^[A-Z]{3}$", description="Filtra por equipo (tag equipo_id)")] = None,
    agregacion: Annotated[
        Agregacion,
        Query(description="raw = puntos crudos; 1m/5m = ventanas (AVG/SUM/MAX según la semántica del campo)"),
    ] = "1m",
    svc: EstadisticasService = Depends(get_estadisticas_service),
):
    """Siempre acotado por partido y por intervalo (máx. 120 min) y limitado a 500 puntos (`truncado`).
    Sin puntos en el intervalo → 200 con `puntos` vacío; InfluxDB caído o credencial inválida → 503/504."""
    return svc.obtener(partido_id, desde, hasta, equipo, agregacion)
