import asyncio
import contextvars
import logging
import os
import re
import time
import uuid

from fastapi import Request
from fastapi.responses import JSONResponse

from app.errors import cuerpo_error

logger = logging.getLogger("prode2030")
request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")
_RID_VALIDO = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


def configurar_logging() -> None:
    logging.basicConfig(level=os.environ.get("LOG_NIVEL", "INFO").upper(), format="%(asctime)s %(levelname)s %(name)s %(message)s")


_FLUJO_EN_VIVO = re.compile(r"^/partidos/[^/]+/vivo$")


def es_flujo_en_vivo(path: str) -> bool:
    """La conexión en vivo dura todo el partido: no se le aplica el tope de duración por pedido."""
    return bool(_FLUJO_EN_VIVO.match(path))


def crear_middleware(deadline_segundos: float, sin_tope=es_flujo_en_vivo):
    """Middleware de correlación (X-Request-ID), log de cada request y tope duro de duración."""

    async def request_id_middleware(request: Request, call_next):
        candidato = request.headers.get("X-Request-ID", "")
        rid = candidato if _RID_VALIDO.fullmatch(candidato) else uuid.uuid4().hex
        request.state.request_id = rid
        token = request_id_var.set(rid)
        inicio = time.perf_counter()
        try:
            if sin_tope(request.url.path):
                response = await call_next(request)
                response.headers["X-Request-ID"] = rid
                return response
            tarea = asyncio.ensure_future(call_next(request))
            # asyncio.wait (no wait_for): al vencer, no espera a que termine el hilo bloqueado en el driver.
            hechas, _ = await asyncio.wait({tarea}, timeout=deadline_segundos)
            if not hechas:
                tarea.cancel()
                logger.error("deadline_excedido metodo=%s ruta=%s request_id=%s", request.method, request.url.path, rid)
                response = JSONResponse(
                    status_code=504,
                    content=cuerpo_error(
                        "DEPENDENCIA_TIMEOUT", "La operación excedió el tiempo máximo permitido.", rid
                    ),
                )
            else:
                response = tarea.result()
        except Exception:
            logger.exception("error_inesperado metodo=%s ruta=%s request_id=%s", request.method, request.url.path, rid)
            response = JSONResponse(
                status_code=500, content=cuerpo_error("ERROR_INTERNO", "Error interno del servidor.", rid)
            )
        finally:
            request_id_var.reset(token)
        response.headers["X-Request-ID"] = rid
        logger.log(
            logging.DEBUG if response.status_code < 400 else logging.WARNING,
            "request metodo=%s ruta=%s status=%s duracion_ms=%.1f request_id=%s",
            request.method,
            request.url.path,
            response.status_code,
            (time.perf_counter() - inicio) * 1000,
            rid,
        )
        return response

    return request_id_middleware
