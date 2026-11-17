from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

EstadoPartido = Literal["Programado", "En juego", "Finalizado"]


class EventoDetalle(BaseModel):
    tipo: str
    minuto: int
    descripcion: str | None = None
    jugador_codigo: str | None = None


class PartidoDetalle(BaseModel):
    codigo: str = Field(examples=["P-01"])
    equipo_local: str
    equipo_visitante: str
    fecha_hora: str
    sede: str
    estado: EstadoPartido
    eventos: list[EventoDetalle]


class CambioEstado(BaseModel):
    model_config = ConfigDict(extra="forbid")

    estado: EstadoPartido
