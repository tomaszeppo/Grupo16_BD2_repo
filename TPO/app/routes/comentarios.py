from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, Query, Response

from app.deps import get_comentarios_service, usuario_actual
from app.errors import ValidacionError
from app.schemas.comentarios import NuevoComentario
from app.schemas.comunes import PartidoId
from app.services.comentarios import ComentariosService

router = APIRouter(tags=["Cassandra · Comentarios"])
FUENTE = "cassandra"
Pais = Query(None, pattern="^[A-Z]{3}$", description="Tribuna de un país, por ejemplo ARG")


@router.post("/partidos/{partido_id}/comentarios", status_code=201, summary="Comentar en la tribuna de mi país")
def publicar(partido_id: PartidoId, cuerpo: NuevoComentario, response: Response,
             usuario_id: str = Depends(usuario_actual),
             svc: ComentariosService = Depends(get_comentarios_service)) -> dict:
    """201 si es nuevo; 200 si es un reintento con el mismo comentario_id; 429 en modo lento."""
    comentario, repetido = svc.publicar(partido_id, usuario_id, cuerpo.comentario_id, cuerpo.contenido)
    if repetido:
        response.status_code = 200
    return {"fuente": FUENTE, **comentario}


@router.get("/partidos/{partido_id}/comentarios", summary="Historial de comentarios, del más nuevo al más viejo")
def historial(partido_id: PartidoId, pais: str | None = Pais,
              alcance: Literal["pais", "todos"] = Query("pais"),
              antes_de: datetime | None = Query(None, description="Para seguir: el valor `siguiente` de la página anterior"),
              limit: int = Query(20, ge=1, le=100),
              svc: ComentariosService = Depends(get_comentarios_service)) -> dict:
    if alcance == "pais" and not pais:
        raise ValidacionError("Indicá el país (pais=ARG) o pedí todos (alcance=todos).")
    pagina = svc.historial(partido_id, pais if alcance == "pais" else None, antes_de, limit)
    return {"fuente": FUENTE, "partido_id": partido_id, "pais": pais if alcance == "pais" else None, **pagina}


@router.get("/partidos/{partido_id}/comentarios/recientes", summary="Últimos 20 comentarios de un país")
def recientes(partido_id: PartidoId, pais: str = Query(pattern="^[A-Z]{3}$"),
              svc: ComentariosService = Depends(get_comentarios_service)) -> dict:
    return {"fuente": FUENTE, "partido_id": partido_id, "pais": pais, **svc.historial(partido_id, pais, None, 20)}
