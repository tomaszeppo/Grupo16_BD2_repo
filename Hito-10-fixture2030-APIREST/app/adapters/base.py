import time
from collections.abc import Callable
from contextlib import contextmanager

from app.errors import ApiError
from app.observability import logger, request_id_var


@contextmanager
def operacion(fuente: str, nombre: str, traducir: Callable[[Exception], ApiError | None]):
    """Mide la operación contra una fuente, la loguea (sin cuerpos ni secretos) y traduce errores del driver."""
    inicio = time.perf_counter()
    resultado = "ok"
    try:
        yield
    except ApiError as exc:
        resultado = exc.codigo.lower()
        raise
    except Exception as exc:
        traducido = traducir(exc)
        if traducido is None:
            resultado = "error_inesperado"
            raise
        resultado = traducido.codigo.lower()
        raise traducido from exc
    finally:
        logger.info(
            "dependencia=%s operacion=%s resultado=%s duracion_ms=%.1f request_id=%s",
            fuente,
            nombre,
            resultado,
            (time.perf_counter() - inicio) * 1000,
            request_id_var.get(),
        )
