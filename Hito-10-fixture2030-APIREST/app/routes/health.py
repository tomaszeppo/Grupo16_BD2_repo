from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.deps import get_health_service
from app.schemas.health import Health
from app.services.health import HealthService

router = APIRouter(tags=["Sistema"])


@router.get(
    "/health",
    response_model=Health,
    summary="Estado de la API y de cada dependencia",
    responses={503: {"model": Health, "description": "Al menos una dependencia no responde (el cuerpo indica cuál)"}},
)
def health(svc: HealthService = Depends(get_health_service)):
    """Hace un `ping` acotado por timeout a cada fuente. Nunca devuelve 200 si alguna está caída."""
    estado = svc.estado()
    if estado["estado"] != "ok":
        return JSONResponse(status_code=503, content=estado)
    return estado
