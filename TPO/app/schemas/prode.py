from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, StringConstraints

from app.dominio import ids

Nombre = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=60)]
Goles = Annotated[StrictInt, Field(ge=0, le=20)]
Posicion = Literal["Arquero", "Defensor", "Mediocampista", "Delantero"]


class _Cuerpo(BaseModel):
    model_config = ConfigDict(extra="forbid")


class UsuarioNuevo(_Cuerpo):
    nombre: Nombre
    pais: str = Field(pattern=ids.CODIGO_EQUIPO, description="Código FIFA del país del usuario")


class ProdeNuevo(_Cuerpo):
    nombre: Nombre


class UnirseAProde(_Cuerpo):
    codigo: str = Field(pattern=r"^[0-9A-F]{8}$", description="Código de invitación de 8 caracteres")


class PronosticoCuerpo(_Cuerpo):
    goles_local: Goles
    goles_visitante: Goles
