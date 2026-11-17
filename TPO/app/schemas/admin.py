from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt

from app.dominio import ids
from app.schemas.comunes import TipoDeEvento


class _Cuerpo(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CambioDeEstado(_Cuerpo):
    estado: Literal["En juego"]


class EquiposDelPartido(_Cuerpo):
    local: str = Field(pattern=ids.CODIGO_EQUIPO)
    visitante: str = Field(pattern=ids.CODIGO_EQUIPO)


IdEvento = Annotated[str, Field(pattern=ids.ID_EVENTO)]


class EventoNuevo(_Cuerpo):
    id: IdEvento = Field(description="Lo elige quien carga la jugada; repetir el mismo id no la duplica")
    tipo: TipoDeEvento
    minuto: Annotated[StrictInt, Field(ge=0, le=130)]
    orden: Annotated[StrictInt, Field(ge=0, le=999)] = Field(description="Desempata jugadas del mismo minuto")
    jugador: str | None = Field(None, pattern=r"^J-[A-Z]{3}-\d{2}$")
    influido_por: list[IdEvento] = Field(default_factory=list, max_length=10,
                                         description="Jugadas anteriores del mismo partido que llevaron a esta")


class ResultadoFinal(_Cuerpo):
    goles_local: Annotated[StrictInt, Field(ge=0, le=30)]
    goles_visitante: Annotated[StrictInt, Field(ge=0, le=30)]
    clasificado: str | None = Field(None, pattern=ids.CODIGO_EQUIPO,
                                    description="Solo en eliminatorias empatadas: el equipo que pasa de ronda")
