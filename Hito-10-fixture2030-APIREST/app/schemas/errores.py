from pydantic import BaseModel


class ErrorDetalle(BaseModel):
    campo: str
    motivo: str


class ErrorCuerpo(BaseModel):
    codigo: str
    mensaje: str
    request_id: str
    detalle: list[ErrorDetalle] | None = None


class ErrorRespuesta(BaseModel):
    error: ErrorCuerpo


_DESCRIPCIONES = {
    404: "Recurso inexistente",
    409: "Conflicto de negocio: el estado actual no permite la operación",
    422: "Parámetro, cabecera o cuerpo inválido (se rechaza antes de consultar la fuente)",
    500: "Error interno (el detalle técnico queda solo en los logs)",
    503: "Dependencia no disponible",
    504: "La dependencia no respondió dentro del timeout",
}


def respuestas(*extra: int) -> dict:
    codigos = sorted({422, 500, 503, 504, *extra})
    return {c: {"model": ErrorRespuesta, "description": _DESCRIPCIONES[c]} for c in codigos}
