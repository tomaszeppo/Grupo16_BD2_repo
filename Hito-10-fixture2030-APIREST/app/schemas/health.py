from typing import Literal

from pydantic import BaseModel


class EstadoFuente(BaseModel):
    estado: Literal["ok", "caida"]
    latencia_ms: float


class Health(BaseModel):
    estado: Literal["ok", "degradado"]
    fuentes: dict[str, EstadoFuente]
