from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query, Response

from app.deps import get_comentarios_service
from app.schemas.comentarios import ComentarioCreado, NuevoComentario, PaginaComentarios, PaisQuery, VentanaQuery
from app.schemas.comunes import IdPartido, LimitQuery
from app.schemas.errores import respuestas
from app.services.comentarios import ComentariosService

router = APIRouter(tags=["Cassandra · Comentarios"])


@router.get(
    "/partidos/{partido_id}/comentarios",
    response_model=PaginaComentarios,
    summary="Leer comentarios de un partido para un país y una ventana de 30 minutos",
    responses=respuestas(),
)
def listar_comentarios(
    partido_id: IdPartido,
    pais: PaisQuery,
    ventana: VentanaQuery,
    limit: LimitQuery = 20,
    cursor: Annotated[str | None, Query(description="Cursor devuelto como `next_cursor`", max_length=2048)] = None,
    svc: ComentariosService = Depends(get_comentarios_service),
):
    """Lectura por la partición completa `(partido_id, pais, ventana)`; nunca recorre otras particiones.
    Una partición sin comentarios es un 200 con `items` vacío (válido)."""
    return svc.listar(partido_id, pais, ventana, limit, cursor)


@router.post(
    "/partidos/{partido_id}/comentarios",
    response_model=ComentarioCreado,
    status_code=201,
    summary="Registrar un comentario (idempotente por Idempotency-Key)",
    responses={
        200: {"model": ComentarioCreado, "description": "Repetición idempotente: devuelve el comentario ya guardado"},
        **respuestas(404, 409),
    },
)
def crear_comentario(
    partido_id: IdPartido,
    cuerpo: NuevoComentario,
    response: Response,
    idempotency_key: Annotated[
        str,
        Header(
            alias="Idempotency-Key", min_length=8, max_length=64, pattern=r"^[A-Za-z0-9_-]+$",
            description="Clave generada por el cliente; reintentar con la misma clave no duplica el comentario",
        ),
    ],
    svc: ComentariosService = Depends(get_comentarios_service),
):
    """Escritura. El partido debe existir en Neo4j. `ventana` y `creado_en` los fija el servidor en el primer intento.
    201 = alta; 200 = reintento con la misma clave (mismo `comentario_id`); 409 = clave usada para otro partido o país."""
    comentario, creado = svc.crear(partido_id, idempotency_key, cuerpo.model_dump())
    response.status_code = 201 if creado else 200
    return comentario
