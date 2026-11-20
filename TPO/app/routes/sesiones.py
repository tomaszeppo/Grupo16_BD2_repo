from fastapi import APIRouter, Depends, Response

from app.config.settings import Settings
from app.deps import credencial, get_sesiones, get_settings, get_usuarios_service
from app.puertos.sesiones import SesionesRedis
from app.schemas.sesiones import SesionNueva
from app.services.usuarios import UsuariosService

router = APIRouter(tags=["Redis · Sesiones"])
COOKIE = "sesion"


@router.post("/sesiones", status_code=201, summary="Entrar con un usuario")
def crear_sesion(cuerpo: SesionNueva, response: Response, sesiones: SesionesRedis = Depends(get_sesiones),
                 usuarios: UsuariosService = Depends(get_usuarios_service),
                 settings: Settings = Depends(get_settings)) -> dict:
    """Devuelve el token y además lo deja en una cookie que el navegador manda solo (HttpOnly)."""
    token = sesiones.crear(cuerpo.usuario_id)
    response.set_cookie(COOKIE, token, max_age=settings.sesion_ttl_segundos, httponly=True, samesite="strict",
                        path="/")
    return {"fuente": "redis", "token": token, "usuario": usuarios.obtener(cuerpo.usuario_id)}


@router.delete("/sesiones/actual", status_code=204, summary="Salir")
def cerrar_sesion(response: Response, token: str | None = Depends(credencial),
                  sesiones: SesionesRedis = Depends(get_sesiones)) -> Response:
    sesiones.cerrar(token)
    response.status_code = 204
    response.delete_cookie(COOKIE, path="/", httponly=True, samesite="strict")
    return response
