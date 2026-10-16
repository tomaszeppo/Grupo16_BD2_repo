from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.errors import ApiError, cuerpo_error


def _rid(request: Request) -> str:
    return getattr(request.state, "request_id", "-")


def _respuesta(status: int, codigo: str, mensaje: str, request: Request, detalle=None) -> JSONResponse:
    return JSONResponse(status_code=status, content=cuerpo_error(codigo, mensaje, _rid(request), detalle))


def registrar_manejadores(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api_error(request: Request, exc: ApiError):
        return _respuesta(exc.status_code, exc.codigo, exc.mensaje, request, exc.detalle)

    @app.exception_handler(RequestValidationError)
    async def _validacion(request: Request, exc: RequestValidationError):
        detalle = [{"campo": ".".join(str(p) for p in e["loc"]), "motivo": e["msg"]} for e in exc.errors()]
        return _respuesta(422, "VALIDACION", "Los parámetros de la solicitud no son válidos.", request, detalle)

    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, exc: StarletteHTTPException):
        codigo = {404: "NO_ENCONTRADO", 405: "METODO_NO_PERMITIDO"}.get(exc.status_code, "ERROR_HTTP")
        return _respuesta(exc.status_code, codigo, str(exc.detail), request)
