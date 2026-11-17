"""Tipos de parámetros compartidos por las rutas. La validación de formato ocurre antes de tocar una base."""
from typing import Annotated, Literal

from fastapi import Path, Query

from app.dominio import ids

PartidoId = Annotated[str, Path(pattern=ids.ID_PARTIDO, description="Identificador del partido, por ejemplo P-03")]
UsuarioId = Annotated[str, Path(pattern=ids.ID_USUARIO, description="Identificador del usuario, por ejemplo U0000001")]
CodigoEquipo = Annotated[str, Path(pattern=ids.CODIGO_EQUIPO, description="Código FIFA de tres letras")]
EventoId = Annotated[str, Path(pattern=ids.ID_EVENTO)]
ProdeId = Annotated[str, Path(pattern=ids.ID_PRODE)]

Limite = Annotated[int, Query(ge=1, le=100, description="Cantidad máxima de resultados")]
Desplazamiento = Annotated[int, Query(ge=0, le=100000)]

Fase = Literal["Fase de grupos", "Dieciseisavos", "Octavos", "Cuartos", "Semifinal", "Tercer puesto", "Final"]
Estado = Literal["Programado", "En juego", "Finalizado"]
TipoDeEvento = Literal["Inicio", "Pase", "Tiro", "Gol", "Falta", "Tarjeta amarilla", "Tarjeta roja", "Cambio", "Final"]
