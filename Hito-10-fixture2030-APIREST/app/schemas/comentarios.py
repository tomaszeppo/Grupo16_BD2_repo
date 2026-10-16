from datetime import datetime
from typing import Annotated

from fastapi import Query
from pydantic import BaseModel, ConfigDict, Field

PaisQuery = Annotated[
    str, Query(pattern=r"^[A-Z]{3}$", description="País de la audiencia (código FIFA)", examples=["ARG"])
]
VentanaQuery = Annotated[
    datetime,
    Query(
        description="Inicio de la ventana de 30 minutos (ISO-8601 con zona, minuto :00 o :30, p.ej. "
        "2030-06-15T18:30:00Z). Es parte de la clave de partición `(partido_id, pais, ventana)`.",
        examples=["2030-06-15T18:30:00Z"],
    ),
]


class ComentarioItem(BaseModel):
    comentario_id: str
    usuario_id: str
    usuario_nombre: str
    contenido: str
    likes: int
    estado_moderacion: str
    creado_en: str


class PaginaComentarios(BaseModel):
    partido_id: str
    pais: str
    ventana: str
    limit: int
    items: list[ComentarioItem] = Field(description="Más recientes primero (clustering creado_en DESC)")
    next_cursor: str | None = Field(description="Cursor opaco para pedir la página siguiente; null si no hay más")


class NuevoComentario(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pais: str = Field(pattern=r"^[A-Z]{3}$", examples=["ARG"])
    usuario_id: str = Field(pattern=r"^U\d{3,6}$", examples=["U001"])
    usuario_nombre: str = Field(min_length=1, max_length=60, examples=["Facundo"])
    contenido: str = Field(min_length=1, max_length=280, examples=["¡Vamos Argentina!"])


class ComentarioCreado(ComentarioItem):
    partido_id: str
    pais: str
    ventana: str
