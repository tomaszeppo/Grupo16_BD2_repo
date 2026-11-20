from typing import Literal

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from app.deps import espectador, get_transmision
from app.schemas.comunes import PartidoId
from app.services.vivo import Transmision

router = APIRouter(tags=["Redis · En vivo"])


@router.get("/partidos/{partido_id}/vivo", summary="Seguir el partido en vivo (eventos del servidor)",
            response_class=StreamingResponse)
async def vivo(partido_id: PartidoId, alcance: Literal["pais", "todos"] = Query("pais"),
               quien: dict = Depends(espectador), transmision: Transmision = Depends(get_transmision)):
    """Conexión abierta mientras se mira el partido. Envía `comentario`, `estado` y `audiencia`, y un latido.

    Requiere sesión (encabezado X-Sesion o cookie). Mientras está abierta, cuenta como un espectador del país
    del usuario. `alcance=todos` trae los comentarios de todas las tribunas.
    """
    flujo = transmision.escuchar(partido_id, quien["pais"], alcance, quien["token"], quien["usuario_id"])
    return StreamingResponse(flujo, media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
