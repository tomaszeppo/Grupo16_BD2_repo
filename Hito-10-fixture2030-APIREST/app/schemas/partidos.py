from pydantic import BaseModel, Field


class EquipoParticipante(BaseModel):
    codigo: str
    nombre: str


class EstadioOut(BaseModel):
    id: str
    nombre: str
    ciudad: str


class Resultado(BaseModel):
    ganador: str
    perdedor: str
    goles_ganador: int
    goles_perdedor: int
    origen: str = Field(description="SIMULADO: marcadores de demostración, no oficiales")


class PartidoGrafo(BaseModel):
    id: str = Field(examples=["P-01"])
    fecha: str
    fase: str
    estadio: EstadioOut | None
    equipos: list[EquipoParticipante] = Field(description="Equipos que PARTICIPA_EN el partido, ordenados por código")
    resultado: Resultado | None = None


class EventoPartido(BaseModel):
    id: str
    tipo: str
    minuto: int


class EventosPartido(BaseModel):
    partido_id: str
    limit: int
    items: list[EventoPartido]
