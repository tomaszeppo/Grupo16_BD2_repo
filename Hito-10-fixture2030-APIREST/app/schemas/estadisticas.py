from typing import Annotated, Literal

from fastapi import Query
from pydantic import BaseModel, Field

Agregacion = Literal["raw", "1m", "5m"]
DesdeQuery = Annotated[
    str,
    Query(description="Inicio (inclusive), ISO-8601 con zona. Ej: 2030-06-15T18:30:00Z", examples=["2030-06-15T18:30:00Z"]),
]
HastaQuery = Annotated[
    str,
    Query(description="Fin (exclusivo), ISO-8601 con zona; hasta - desde ≤ 120 min", examples=["2030-06-15T18:40:00Z"]),
]


class PuntoRaw(BaseModel):
    time: str
    equipo_id: str
    fuente: str
    posesion_pct: float
    pases_completados: int
    tiros: int
    recuperaciones: int
    velocidad_kmh: float


class PuntoAgregado(BaseModel):
    ventana: str = Field(description="Inicio del intervalo (DATE_BIN)")
    equipo_id: str
    fuente: str
    posesion_pct_prom: float
    pases_completados: int = Field(description="SUM del intervalo")
    tiros: int = Field(description="SUM del intervalo")
    recuperaciones: int = Field(description="SUM del intervalo")
    velocidad_kmh_prom: float
    velocidad_kmh_max: float


class Estadisticas(BaseModel):
    partido_id: str
    agregacion: Agregacion
    desde: str
    hasta: str
    max_puntos: int
    truncado: bool = Field(description="true si había más puntos que max_puntos; reducir la ventana o agregar")
    puntos: list[PuntoAgregado | PuntoRaw]
