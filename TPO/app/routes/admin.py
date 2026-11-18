from fastapi import APIRouter, BackgroundTasks, Depends, Response

from app.deps import get_partidos_admin_service, get_puntuacion_service, requiere_admin
from app.schemas.admin import CambioDeEstado, EquiposDelPartido, EventoNuevo, ResultadoFinal
from app.schemas.comunes import PartidoId
from app.services.partidos_admin import PartidosAdminService
from app.services.puntuacion import PuntuacionService

router = APIRouter(tags=["Administración"], dependencies=[Depends(requiere_admin)])


@router.get("/administracion/acceso", summary="Validar clave de administración")
def validar_acceso() -> dict:
    return {"autorizado": True}


@router.post("/partidos/{partido_id}/estado", summary="Poner un partido en juego")
def cambiar_estado(partido_id: PartidoId, cuerpo: CambioDeEstado,
                   svc: PartidosAdminService = Depends(get_partidos_admin_service)) -> dict:
    """Fija el inicio real y cierra los pronósticos. Repetirlo no cambia nada."""
    return {"fuente": "neo4j", "partido": svc.poner_en_juego(partido_id)}


@router.post("/partidos/{partido_id}/equipos", summary="Definir los equipos de un partido de eliminatorias")
def asignar_equipos(partido_id: PartidoId, cuerpo: EquiposDelPartido,
                    svc: PartidosAdminService = Depends(get_partidos_admin_service)) -> dict:
    return {"fuente": "neo4j", "partido": svc.asignar_equipos(partido_id, cuerpo.local, cuerpo.visitante)}


@router.post("/partidos/{partido_id}/eventos", summary="Cargar una jugada",
             responses={201: {"description": "Jugada nueva"}, 200: {"description": "La jugada ya estaba cargada"}})
def registrar_evento(partido_id: PartidoId, cuerpo: EventoNuevo, respuesta: Response,
                     svc: PartidosAdminService = Depends(get_partidos_admin_service)) -> dict:
    evento, es_alta = svc.registrar_evento(partido_id, cuerpo.model_dump())
    respuesta.status_code = 201 if es_alta else 200
    return {"fuente": "neo4j", "partido": partido_id, "evento": evento}


@router.post("/partidos/{partido_id}/resultado", status_code=202, summary="Cerrar un partido y puntuar")
def cerrar_partido(partido_id: PartidoId, cuerpo: ResultadoFinal, tareas: BackgroundTasks,
                   svc: PuntuacionService = Depends(get_puntuacion_service)) -> dict:
    """Registra el resultado y responde enseguida; la puntuación corre después.

    El avance se consulta en GET /partidos/{id}/puntuacion. Repetir el pedido con el mismo marcador no
    vuelve a sumar puntos y sirve para retomar una puntuación que quedó a medias.
    """
    resultado = svc.cerrar(partido_id, cuerpo.goles_local, cuerpo.goles_visitante, cuerpo.clasificado)
    tareas.add_task(svc.ejecutar, partido_id)
    return {"fuente": "mongodb", "partido": partido_id, **_publicar(resultado)}


@router.get("/partidos/{partido_id}/puntuacion", summary="Avance de la puntuación de un partido")
def estado_de_puntuacion(partido_id: PartidoId, svc: PuntuacionService = Depends(get_puntuacion_service)) -> dict:
    return {"fuente": "mongodb", "partido": partido_id, **_publicar(svc.estado(partido_id))}


def _publicar(resultado: dict) -> dict:
    return {"resultado": {k: resultado[k] for k in ("goles_local", "goles_visitante", "clasificado", "cerrado_en")},
            "puntuacion": {k: resultado["puntuacion"].get(k)
                           for k in ("estado", "pasos", "pronosticos", "iniciada_en", "terminada_en")}}
