class ApiError(Exception):
    status_code = 500
    codigo = "ERROR_INTERNO"

    def __init__(self, mensaje: str = "Error interno del servidor.", *, fuente: str | None = None, detalle=None):
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.fuente = fuente
        self.detalle = detalle


class ValidacionError(ApiError):
    status_code = 422
    codigo = "VALIDACION"


class NoEncontrado(ApiError):
    status_code = 404
    codigo = "NO_ENCONTRADO"


class SesionNoVigente(NoEncontrado):
    codigo = "SESION_NO_VIGENTE"


class Conflicto(ApiError):
    status_code = 409
    codigo = "CONFLICTO"


class DependenciaNoDisponible(ApiError):
    status_code = 503
    codigo = "DEPENDENCIA_NO_DISPONIBLE"

    def __init__(self, fuente: str):
        super().__init__(f"La fuente '{fuente}' no está disponible en este momento.", fuente=fuente)


class DependenciaTimeout(ApiError):
    status_code = 504
    codigo = "DEPENDENCIA_TIMEOUT"

    def __init__(self, fuente: str):
        super().__init__(f"La fuente '{fuente}' no respondió dentro del tiempo permitido.", fuente=fuente)


def cuerpo_error(codigo: str, mensaje: str, request_id: str, detalle=None) -> dict:
    error = {"codigo": codigo, "mensaje": mensaje, "request_id": request_id}
    if detalle:
        error["detalle"] = detalle
    return {"error": error}
