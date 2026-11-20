"""Partido en vivo: una conexión abierta por espectador (SSE), como en una plataforma de streaming.

Por la conexión llegan los comentarios de la tribuna elegida, el estado del partido y la audiencia. Además,
la conexión abierta es la señal de que alguien está mirando:

- Al abrirse, la sesión entra en `audiencia:{partido}:{pais}` (conjunto ordenado de Redis, puntaje = hora de
  la última señal) y el usuario en `unicos:{partido}:{pais}` (HyperLogLog). Se guarda un resumen del token,
  no el token.
- Mientras sigue abierta, se refresca cada `presencia_refresco_segundos`. Quien cuenta (el simulador, cada
  minuto) toma solo lo refrescado en los últimos `presencia_vencimiento_segundos`: si un proceso de la API
  muere sin avisar, sus espectadores dejan de contar a los pocos segundos.
- Al cerrarse, sale del conjunto.

Cada proceso tiene UNA suscripción de Redis compartida por todas sus conexiones: se suscribe a un canal con
el primer interesado y se desuscribe con el último. Así un comentario que entró por otro proceso llega igual.
"""
import asyncio
import hashlib
import json
import time

from app import metricas
from app.errors import ApiError, DependenciaNoDisponible
from app.observability import logger

TAMANO_COLA = 200  # por conexión; un espectador lento pierde lo más viejo, no frena a los demás


def miembro_de(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()[:16]


def _evento(tipo: str, datos: dict) -> str:
    return f"event: {tipo}\ndata: {json.dumps(datos, ensure_ascii=False)}\n\n"


class Transmision:
    def __init__(self, redis, settings):
        self._redis = redis
        self._refresco = settings.presencia_refresco_segundos
        self._latido = settings.vivo_latido_segundos
        self._colas: dict[str, set[asyncio.Queue]] = {}
        self._pubsub = None
        self._lector: asyncio.Task | None = None
        self._candado: asyncio.Lock | None = None
        self.conexiones = 0

    # --- suscripción compartida ---
    async def _anotar(self, cola: asyncio.Queue, canales: list[str]) -> None:
        self._candado = self._candado or asyncio.Lock()
        async with self._candado:
            if self._pubsub is None:
                self._pubsub = await self._redis.suscriptor()
            nuevos = [c for c in canales if c not in self._colas]
            for canal in canales:
                self._colas.setdefault(canal, set()).add(cola)
            if nuevos:
                try:
                    await self._pubsub.subscribe(*nuevos)
                except Exception:
                    for canal in canales:
                        self._sacar(cola, canal)
                    raise
            if self._lector is None or self._lector.done():
                self._lector = asyncio.create_task(self._leer())

    def _sacar(self, cola, canal) -> bool:
        colas = self._colas.get(canal)
        if colas is None:
            return False
        colas.discard(cola)
        if colas:
            return False
        del self._colas[canal]
        return True

    async def _borrar(self, cola: asyncio.Queue, canales: list[str]) -> None:
        vacios = [canal for canal in canales if self._sacar(cola, canal)]
        if vacios and self._pubsub is not None:
            try:
                await self._pubsub.unsubscribe(*vacios)
            except Exception:  # la suscripción se rehace con el próximo espectador
                logger.warning("vivo desuscripcion_fallida canales=%s", len(vacios))

    async def _leer(self) -> None:
        while self._colas:
            try:
                mensaje = await self._pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.warning("vivo lectura_fallida")
                await asyncio.sleep(1)
                continue
            if not mensaje or mensaje.get("type") != "message":
                continue
            for cola in list(self._colas.get(mensaje["channel"], ())):
                self.entregar(cola, mensaje["data"])

    @staticmethod
    def entregar(cola: asyncio.Queue, dato) -> None:
        while True:
            try:
                cola.put_nowait(dato)
                return
            except asyncio.QueueFull:
                cola.get_nowait()
                metricas.VIVO_DESCARTADOS.inc()

    # --- una conexión ---
    async def escuchar(self, partido_id: str, pais: str, alcance: str, token: str, usuario_id: str):
        """Genera el texto SSE de una conexión hasta que el cliente se va."""
        miembro = miembro_de(token)
        clave = f"audiencia:{partido_id}:{pais}"
        canal_chat = f"chat:{partido_id}:todos" if alcance == "todos" else f"chat:{partido_id}:{pais}"
        canales = [canal_chat, f"estado:{partido_id}"]
        cola: asyncio.Queue = asyncio.Queue(maxsize=TAMANO_COLA)
        try:
            await self._anotar(cola, canales)
            await self._redis.amarcar(clave, miembro, time.time())
            await self._redis.aagregar(f"paises:{partido_id}", pais, f"unicos:{partido_id}:{pais}", usuario_id)
        except ApiError as exc:
            await self._borrar(cola, canales)
            yield _evento("error", {"codigo": exc.codigo, "mensaje": exc.mensaje})
            return
        self.conexiones += 1
        metricas.VIVO_CONEXIONES.inc()
        try:
            yield "retry: 3000\n\n"
            reloj = asyncio.get_running_loop().time
            ultimo_refresco = ultimo_envio = reloj()
            while True:
                espera = max(0.0, min(ultimo_refresco + self._refresco, ultimo_envio + self._latido) - reloj())
                try:
                    dato = await asyncio.wait_for(cola.get(), timeout=espera)
                except asyncio.TimeoutError:
                    dato = None
                if reloj() - ultimo_refresco >= self._refresco:
                    await self._redis.amarcar(clave, miembro, time.time())
                    ultimo_refresco = reloj()
                if dato is not None:
                    for trozo in self._traducir(dato, pais):
                        yield trozo
                    ultimo_envio = reloj()
                elif reloj() - ultimo_envio >= self._latido:
                    yield ": latido\n\n"
                    ultimo_envio = reloj()
        except DependenciaNoDisponible as exc:
            yield _evento("error", {"codigo": exc.codigo, "mensaje": exc.mensaje})
        finally:
            self.conexiones -= 1
            metricas.VIVO_CONEXIONES.dec()
            await self._borrar(cola, canales)
            try:
                await self._redis.aquitar(clave, miembro)
            except Exception:  # si Redis no está, la marca vence sola en `presencia_vencimiento_segundos`
                pass

    def _traducir(self, dato, pais: str):
        try:
            mensaje = json.loads(dato)
        except (TypeError, ValueError):
            return
        tipo = mensaje.get("tipo")
        if tipo == "comentario":
            if mensaje.get("enviado_en"):
                metricas.VIVO_ENTREGA.observe(max(0.0, time.time() - mensaje["enviado_en"]))
            yield _evento("comentario", mensaje)
        elif tipo == "estado":
            audiencia = mensaje.pop("audiencia", None)
            yield _evento("estado", mensaje)
            if audiencia:
                yield _evento("audiencia", {"total": audiencia.get("total", 0), "pais": pais,
                                            "mi_pais": audiencia.get("por_pais", {}).get(pais, 0)})
