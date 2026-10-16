from typing import Literal

from pydantic import BaseModel, Field

Posicion = Literal["Portero", "Defensa", "Centrocampista", "Delantero"]


class Equipo(BaseModel):
    codigo: str = Field(examples=["ARG"])
    nombre: str = Field(examples=["Argentina"])


class Jugador(BaseModel):
    nombre: str
    apellido: str
    dorsal: int
    posicion: Posicion
    equipo: str = Field(description="Código del equipo (referencia a equipos.codigo)")


class PaginaJugadores(BaseModel):
    equipo: str
    total: int = Field(description="Total de jugadores que cumplen el filtro")
    limit: int
    offset: int
    items: list[Jugador]
