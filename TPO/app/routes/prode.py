from fastapi import APIRouter, Depends, Response

from app.deps import (get_equipos_service, get_prodes_service, get_pronosticos_service, get_usuarios_service,
                      usuario_actual)
from app.errors import Prohibido
from app.schemas.comunes import CodigoEquipo, Desplazamiento, Limite, PartidoId, UsuarioId
from app.schemas.prode import Posicion, ProdeNuevo, PronosticoCuerpo, UnirseAProde, UsuarioNuevo
from app.services.prodes import ProdesService
from app.services.pronosticos import PronosticosService
from app.services.usuarios import EquiposService, UsuariosService

router = APIRouter(tags=["MongoDB · Prode"])
equipos_router = APIRouter(tags=["MongoDB · Equipos"])
FUENTE = "mongodb"


def _solo_propio(usuario_id: str, actual: str) -> None:
    if usuario_id != actual:
        raise Prohibido("Solo se pueden consultar los datos del propio usuario.")


@router.post("/usuarios", status_code=201, summary="Registrar un usuario")
def crear_usuario(cuerpo: UsuarioNuevo, svc: UsuariosService = Depends(get_usuarios_service)) -> dict:
    return {"fuente": FUENTE, "usuario": svc.crear(cuerpo.nombre, cuerpo.pais)}


@router.get("/usuarios/{usuario_id}", summary="Datos de un usuario")
def obtener_usuario(usuario_id: UsuarioId, svc: UsuariosService = Depends(get_usuarios_service)) -> dict:
    return {"fuente": FUENTE, "usuario": svc.obtener(usuario_id)}


@router.post("/prodes", status_code=201, summary="Crear un prode privado")
def crear_prode(cuerpo: ProdeNuevo, actual: str = Depends(usuario_actual),
                svc: ProdesService = Depends(get_prodes_service)) -> dict:
    return {"fuente": FUENTE, "prode": svc.crear(cuerpo.nombre, actual)}


@router.post("/prodes/unirse", summary="Unirse a un prode privado con su código de invitación")
def unirse_a_prode(cuerpo: UnirseAProde, actual: str = Depends(usuario_actual),
                   svc: ProdesService = Depends(get_prodes_service)) -> dict:
    resultado, prode = svc.unirse(cuerpo.codigo, actual)
    return {"fuente": FUENTE, "resultado": resultado, "prode": prode}


@router.get("/usuarios/{usuario_id}/prodes", summary="Prodes privados del usuario")
def prodes_de_usuario(usuario_id: UsuarioId, actual: str = Depends(usuario_actual),
                      svc: ProdesService = Depends(get_prodes_service)) -> dict:
    _solo_propio(usuario_id, actual)
    return {"fuente": FUENTE, "prodes": svc.de_usuario(usuario_id)}


@router.put("/partidos/{partido_id}/pronostico", summary="Cargar o corregir el pronóstico de un partido",
            responses={201: {"description": "Pronóstico nuevo"}, 200: {"description": "Pronóstico corregido"}})
def guardar_pronostico(partido_id: PartidoId, cuerpo: PronosticoCuerpo, respuesta: Response,
                       actual: str = Depends(usuario_actual),
                       svc: PronosticosService = Depends(get_pronosticos_service)) -> dict:
    """Un solo pronóstico por usuario y partido, válido para el prode general y para todos sus prodes privados."""
    pronostico, es_alta = svc.guardar(actual, partido_id, cuerpo.goles_local, cuerpo.goles_visitante)
    respuesta.status_code = 201 if es_alta else 200
    return {"fuente": FUENTE, "pronostico": pronostico}


@router.get("/usuarios/{usuario_id}/pronosticos", summary="Pronósticos del usuario")
def pronosticos_de_usuario(usuario_id: UsuarioId, limit: Limite = 100, offset: Desplazamiento = 0,
                           actual: str = Depends(usuario_actual),
                           svc: PronosticosService = Depends(get_pronosticos_service)) -> dict:
    _solo_propio(usuario_id, actual)
    pronosticos, total = svc.de_usuario(usuario_id, limit, offset)
    return {"fuente": FUENTE, "total": total, "pronosticos": pronosticos}


@equipos_router.get("/equipos", summary="Los 48 equipos con su grupo")
def listar_equipos(svc: EquiposService = Depends(get_equipos_service)) -> dict:
    return {"fuente": FUENTE, "equipos": svc.listar()}


@equipos_router.get("/equipos/{codigo}/jugadores", summary="Plantel de un equipo")
def listar_jugadores(codigo: CodigoEquipo, posicion: Posicion | None = None, limit: Limite = 50,
                     offset: Desplazamiento = 0, svc: EquiposService = Depends(get_equipos_service)) -> dict:
    jugadores, total = svc.jugadores(codigo, posicion, limit, offset)
    return {"fuente": FUENTE, "equipo": codigo, "total": total, "jugadores": jugadores}
