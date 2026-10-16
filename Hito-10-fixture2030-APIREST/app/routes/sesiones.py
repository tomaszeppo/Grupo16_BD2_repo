from fastapi import APIRouter, Depends, Response

from app.deps import get_sesiones_service
from app.schemas.comunes import IdUsuario
from app.schemas.errores import respuestas
from app.schemas.sesiones import Sesion
from app.services.sesiones import SesionesService

router = APIRouter(tags=["Redis · Sesiones"])


@router.get(
    "/sesiones/{usuario_id}",
    response_model=Sesion,
    summary="Consultar la sesión vigente de un usuario",
    responses=respuestas(404),
)
def obtener_sesion(usuario_id: IdUsuario, svc: SesionesService = Depends(get_sesiones_service)):
    """`GET` de la clave `f2030:sesion:{usuario}`. Clave inexistente, expirada o sesión CERRADA → 404 `SESION_NO_VIGENTE`.
    Redis caído → 503 (nunca se confunde con sesión ausente)."""
    return svc.obtener(usuario_id)


@router.delete(
    "/sesiones/{usuario_id}",
    status_code=204,
    summary="Invalidar la sesión de un usuario",
    responses=respuestas(),
)
def invalidar_sesion(usuario_id: IdUsuario, svc: SesionesService = Depends(get_sesiones_service)):
    """`DEL` de la clave. Idempotente: repetirlo (o invalidar una sesión inexistente) devuelve 204 igual."""
    svc.invalidar(usuario_id)
    return Response(status_code=204)
