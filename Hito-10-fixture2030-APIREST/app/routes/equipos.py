from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.deps import get_equipos_service
from app.schemas.comunes import CodigoEquipo, LimitQuery
from app.schemas.equipos import Equipo, PaginaJugadores, Posicion
from app.schemas.errores import respuestas
from app.services.equipos import EquiposService

router = APIRouter(prefix="/equipos", tags=["MongoDB · Equipos y jugadores"])


@router.get("/{codigo}", response_model=Equipo, summary="Obtener un equipo por código", responses=respuestas(404))
def obtener_equipo(codigo: CodigoEquipo, svc: EquiposService = Depends(get_equipos_service)):
    """Caso de uso: un hincha o la app consulta la ficha de una selección. Lectura por índice único `codigo`."""
    return svc.obtener_equipo(codigo)


@router.get(
    "/{codigo}/jugadores",
    response_model=PaginaJugadores,
    summary="Listar los jugadores de un equipo (paginado)",
    responses=respuestas(404),
)
def listar_jugadores(
    codigo: CodigoEquipo,
    posicion: Annotated[Posicion | None, Query(description="Filtra por posición")] = None,
    limit: LimitQuery = 20,
    offset: Annotated[int, Query(ge=0, description="Cantidad de jugadores a saltear")] = 0,
    svc: EquiposService = Depends(get_equipos_service),
):
    """Orden alfabético por apellido. Equipo inexistente → 404; equipo sin coincidencias → 200 con `items` vacío."""
    return svc.listar_jugadores(codigo, posicion, limit, offset)
