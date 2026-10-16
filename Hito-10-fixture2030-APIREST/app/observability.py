import contextvars
import logging
import re
import time
import uuid

from fastapi import Request
from fastapi.responses import JSONResponse

from app.errors import cuerpo_error

logger = logging.getLogger("fixture2030")
request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")
_RID_VALIDO = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


def configurar_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


async def request_id_middleware(request: Request, call_next):
    candidato = request.headers.get("X-Request-ID", "")
    rid = candidato if _RID_VALIDO.fullmatch(candidato) else uuid.uuid4().hex
    request.state.request_id = rid
    token = request_id_var.set(rid)
    inicio = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception("error_inesperado metodo=%s ruta=%s request_id=%s", request.method, request.url.path, rid)
        response = JSONResponse(
            status_code=500, content=cuerpo_error("ERROR_INTERNO", "Error interno del servidor.", rid)
        )
    finally:
        request_id_var.reset(token)
    response.headers["X-Request-ID"] = rid
    logger.info(
        "request metodo=%s ruta=%s status=%s duracion_ms=%.1f request_id=%s",
        request.method,
        request.url.path,
        response.status_code,
        (time.perf_counter() - inicio) * 1000,
        rid,
    )
    return response
