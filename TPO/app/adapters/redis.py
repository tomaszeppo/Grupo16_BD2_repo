"""Redis: sesiones, presencia en los partidos en vivo, reparto de comentarios entre procesos y contadores.

Los métodos son genéricos (no saben de sesiones ni de comentarios) para que los use cualquier servicio,
incluido el ranking. El cliente sincrónico sirve a las rutas comunes y al simulador; el asincrónico, a la
conexión en vivo, que no puede bloquear el proceso.
"""
from app.adapters.base import operacion
from app.config.settings import Settings
from app.errors import ApiError, DependenciaNoDisponible, DependenciaTimeout

FUENTE = "redis"


def _traducir(exc: Exception) -> ApiError | None:
    from redis import exceptions

    if isinstance(exc, exceptions.TimeoutError):
        return DependenciaTimeout(FUENTE)
    if isinstance(exc, exceptions.RedisError):
        return DependenciaNoDisponible(FUENTE)
    return None


class RedisAdapter:
    fuente = FUENTE

    def __init__(self, settings: Settings):
        self._s = settings
        self._cli = None
        self._acli = None

    def _opciones(self) -> dict:
        t = self._s.timeout_segundos
        return {"password": self._s.redis_password or None, "socket_timeout": t, "socket_connect_timeout": t,
                "decode_responses": True}

    @property
    def cli(self):
        if self._cli is None:
            import redis

            self._cli = redis.Redis.from_url(self._s.redis_url, **self._opciones())
        return self._cli

    @property
    def acli(self):
        if self._acli is None:
            import redis.asyncio as aredis

            # Sin tiempo de espera de lectura: la suscripción queda esperando mensajes indefinidamente.
            opciones = {**self._opciones(), "socket_timeout": None}
            self._acli = aredis.Redis.from_url(self._s.redis_url, **opciones)
        return self._acli

    # --- sincrónico ---
    def ping(self) -> None:
        with operacion(FUENTE, "ping", _traducir):
            self.cli.ping()

    def guardar(self, clave: str, valor: str, ttl_seg: int) -> None:
        with operacion(FUENTE, "guardar", _traducir):
            self.cli.set(clave, valor, ex=int(ttl_seg))

    def guardar_varios(self, pares: dict[str, str], ttl_seg: int) -> None:
        """Muchas claves en un solo viaje (lo usa el generador de carga para crear sesiones)."""
        with operacion(FUENTE, "guardar_varios", _traducir):
            tubo = self.cli.pipeline(transaction=False)
            for clave, valor in pares.items():
                tubo.set(clave, valor, ex=int(ttl_seg))
            tubo.execute()

    def reservar(self, clave: str, valor: str, ttl_seg: float) -> bool:
        """Escribe solo si la clave no existe. Devuelve si la escribió."""
        with operacion(FUENTE, "reservar", _traducir):
            return bool(self.cli.set(clave, valor, nx=True, px=int(ttl_seg * 1000)))

    def leer(self, clave: str) -> str | None:
        with operacion(FUENTE, "leer", _traducir):
            return self.cli.get(clave)

    def leer_renovando(self, clave: str, ttl_seg: int) -> str | None:
        with operacion(FUENTE, "leer_renovando", _traducir):
            return self.cli.getex(clave, ex=int(ttl_seg))

    def borrar(self, *claves: str) -> None:
        if not claves:
            return
        with operacion(FUENTE, "borrar", _traducir):
            self.cli.delete(*claves)

    def incrementar(self, clave: str) -> int:
        with operacion(FUENTE, "incrementar", _traducir):
            return int(self.cli.incr(clave))

    def tomar_y_borrar(self, clave: str) -> int:
        with operacion(FUENTE, "tomar_y_borrar", _traducir):
            valor = self.cli.getdel(clave)
        return int(valor) if valor is not None else 0

    def agregar_a_conjunto(self, clave: str, miembro: str) -> None:
        with operacion(FUENTE, "agregar_a_conjunto", _traducir):
            self.cli.sadd(clave, miembro)

    def miembros(self, clave: str) -> set[str]:
        with operacion(FUENTE, "miembros", _traducir):
            return set(self.cli.smembers(clave))

    def marcar(self, clave: str, miembro: str, puntaje: float) -> None:
        with operacion(FUENTE, "marcar", _traducir):
            self.cli.zadd(clave, {miembro: puntaje})

    def quitar(self, clave: str, miembro: str) -> None:
        with operacion(FUENTE, "quitar", _traducir):
            self.cli.zrem(clave, miembro)

    def contar_desde(self, clave: str, minimo: float) -> int:
        """Borra los miembros con puntaje menor a `minimo` y cuenta los que quedan."""
        with operacion(FUENTE, "contar_desde", _traducir):
            tubo = self.cli.pipeline()
            tubo.zremrangebyscore(clave, "-inf", f"({minimo}")
            tubo.zcard(clave)
            return int(tubo.execute()[1])

    def agregar_unico(self, clave: str, miembro: str) -> None:
        with operacion(FUENTE, "agregar_unico", _traducir):
            self.cli.pfadd(clave, miembro)

    def contar_unicos(self, clave: str) -> int:
        with operacion(FUENTE, "contar_unicos", _traducir):
            return int(self.cli.pfcount(clave))

    def publicar(self, canal: str, mensaje: str) -> None:
        with operacion(FUENTE, "publicar", _traducir):
            self.cli.publish(canal, mensaje)

    # --- asincrónico (conexión en vivo) ---
    async def suscriptor(self):
        """Una suscripción nueva. La conexión en vivo usa una sola por proceso."""
        return self.acli.pubsub(ignore_subscribe_messages=True)

    async def asuscribir(self, pubsub, *canales: str) -> None:
        with operacion(FUENTE, "suscribir", _traducir):
            await pubsub.subscribe(*canales)

    async def adesuscribir(self, pubsub, *canales: str) -> None:
        with operacion(FUENTE, "desuscribir", _traducir):
            await pubsub.unsubscribe(*canales)

    async def aleer(self, pubsub, timeout: float):
        """Próximo mensaje de la suscripción, o None si no llegó ninguno en `timeout` segundos."""
        try:
            return await pubsub.get_message(ignore_subscribe_messages=True, timeout=timeout)
        except Exception as exc:  # sin `operacion`: se llama sin pausa y llenaría las métricas de esperas vacías
            raise (_traducir(exc) or exc) from exc

    async def amarcar(self, clave: str, miembro: str, puntaje: float) -> None:
        with operacion(FUENTE, "marcar", _traducir):
            await self.acli.zadd(clave, {miembro: puntaje})

    async def aquitar(self, clave: str, miembro: str) -> None:
        with operacion(FUENTE, "quitar", _traducir):
            await self.acli.zrem(clave, miembro)

    async def aagregar(self, clave_conjunto: str, miembro: str, clave_unicos: str, usuario: str) -> None:
        """Al conectarse: suma el país al partido y el usuario a los únicos, en un solo viaje."""
        with operacion(FUENTE, "registrar_espectador", _traducir):
            tubo = self.acli.pipeline()
            tubo.sadd(clave_conjunto, miembro)
            tubo.pfadd(clave_unicos, usuario)
            await tubo.execute()
