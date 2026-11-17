from fastapi import APIRouter, Depends, Response
from prometheus_client import CONTENT_TYPE_LATEST

from app import metricas
from app.deps import get_calendario, get_health_service
from app.services.health import HealthService

router = APIRouter(tags=["Sistema"])


@router.get("/health", summary="La API está viva")
def health() -> dict:
    return {"estado": "ok"}


@router.get("/health/dependencias", summary="Estado de cada base y de la copia del calendario")
def dependencias(svc: HealthService = Depends(get_health_service)) -> dict:
    """Responde 200 siempre que la API esté viva; el cuerpo dice qué dependencia no contesta."""
    return svc.dependencias()


@router.get("/metrics", summary="Métricas para Prometheus")
def metrics(calendario=Depends(get_calendario)) -> Response:
    """Pedidos, latencia y errores por ruta; duración de cada operación contra cada base; puntuación; calendario."""
    estado = calendario.estado()
    metricas.CALENDARIO_DESACTUALIZADO.set(1 if estado["desactualizado"] else 0)
    metricas.CALENDARIO_ANTIGUEDAD.set(estado["antiguedad_segundos"] or 0)
    return Response(metricas.texto_de_metricas(), media_type=CONTENT_TYPE_LATEST)
