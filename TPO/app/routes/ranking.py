from fastapi import APIRouter, Depends

from app.deps import get_ranking_service, usuario_actual
from app.schemas.comunes import Limite, PartidoId, ProdeId, UsuarioId
from app.services.ranking import RankingService

router = APIRouter(tags=["MongoDB · Prode"])


@router.get("/ranking", summary="Primeros puestos del prode general")
def ranking_general(limit: Limite = 20, svc: RankingService = Depends(get_ranking_service)) -> dict:
    return {"fuente": svc.fuente, "ranking": svc.top(limit)}


@router.get("/ranking/usuarios/{usuario_id}", summary="Puesto de un usuario en el prode general")
def posicion_de_usuario(usuario_id: UsuarioId, svc: RankingService = Depends(get_ranking_service)) -> dict:
    return {"fuente": svc.fuente, "usuario_id": usuario_id, **svc.posicion(usuario_id)}


@router.get("/ranking/historico/{partido_id}", summary="Ranking tal como quedó al cerrar un partido")
def ranking_historico(partido_id: PartidoId, svc: RankingService = Depends(get_ranking_service)) -> dict:
    foto = svc.historico(partido_id)
    return {"fuente": "mongodb", "partido": partido_id, "generado_en": foto["generado_en"],
            "total_usuarios": foto["total_usuarios"], "ranking": foto["primeros"]}


@router.get("/prodes/{prode_id}/tabla", summary="Tabla de posiciones de un prode privado")
def tabla_de_prode(prode_id: ProdeId, actual: str = Depends(usuario_actual),
                   svc: RankingService = Depends(get_ranking_service)) -> dict:
    prode, tabla = svc.tabla_de_prode(prode_id, actual)
    return {"fuente": svc.fuente, "prode": {"id": prode["id"], "nombre": prode["nombre"]}, "tabla": tabla}
