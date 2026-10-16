from app.adapters.base import operacion
from app.config.settings import Settings
from app.errors import ApiError, DependenciaNoDisponible, DependenciaTimeout

FUENTE = "redis"


def _traducir(exc: Exception) -> ApiError | None:
    try:
        from redis.exceptions import RedisError
        from redis.exceptions import TimeoutError as RedisTimeout
    except ImportError:
        return None
    if isinstance(exc, RedisTimeout):
        return DependenciaTimeout(FUENTE)
    if isinstance(exc, RedisError):
        return DependenciaNoDisponible(FUENTE)
    return None


def clave_sesion(usuario_id: str) -> str:
    return f"f2030:sesion:{usuario_id}"  # namespace del Hito 7; la clave se arma solo con un id ya validado


class RedisAdapter:
    fuente = FUENTE

    def __init__(self, settings: Settings):
        self._s = settings
        self._r = None

    def _cli(self):
        if self._r is None:
            import redis

            t = self._s.timeout_segundos
            self._r = redis.Redis(
                host=self._s.redis_host, port=self._s.redis_port, password=self._s.redis_password or None,
                socket_timeout=t, socket_connect_timeout=t, decode_responses=True,
            )
        return self._r

    def obtener_sesion(self, usuario_id: str) -> dict | None:
        with operacion(FUENTE, "obtener_sesion", _traducir):
            pipe = self._cli().pipeline()
            pipe.hgetall(clave_sesion(usuario_id))
            pipe.ttl(clave_sesion(usuario_id))
            datos, ttl = pipe.execute()
            if not datos:  # clave inexistente o expirada (Redis disponible)
                return None
            return {**datos, "ttl": ttl if ttl >= 0 else None}

    def invalidar_sesion(self, usuario_id: str) -> bool:
        with operacion(FUENTE, "invalidar_sesion", _traducir):
            return self._cli().delete(clave_sesion(usuario_id)) == 1

    def ping(self) -> None:
        with operacion(FUENTE, "ping", _traducir):
            self._cli().ping()
