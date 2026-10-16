from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Estado = Literal["Programado", "En juego", "Finalizado"]


class EventoIris(BaseModel):
    tipo: str
    minuto: int
    descripcion: str | None = None
    jugador_codigo: str | None = None


class PartidoIris(BaseModel):
    codigo: str = Field(examples=["P-01"])
    equipo_local: str
    equipo_visitante: str
    fecha_hora: str
    sede: str
    estado: Estado
    eventos: list[EventoIris] = Field(description="Hijos de la relación padre-hijo Fixture.Partido → Fixture.Evento")


class CambioEstado(BaseModel):
    model_config = ConfigDict(extra="forbid")

    estado: Estado
