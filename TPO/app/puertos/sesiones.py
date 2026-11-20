"""Puerto de sesiones: quién hace el pedido.

La sesión vive en Redis: `sesion:{token}` → id del usuario, con 24 horas de vida que se renuevan con cada uso.
El token llega por el encabezado `X-Sesion` o por la cookie `sesion` (la conexión en vivo del navegador no
puede mandar encabezados propios). Si Redis no responde, el pedido falla con 503: no hay vuelta a confiar en
lo que mande el cliente.

Simplificación de laboratorio: los usuarios no tienen contraseña; abrir una sesión es elegir un usuario.
"""
import secrets
from typing import Protocol

from app.errors import NoAutorizado, NoEncontrado

PREFIJO = "sesion:"


class SesionesPort(Protocol):
    def usuario_de(self, credencial: str | None) -> str:
        """Devuelve el id del usuario o lanza NoAutorizado."""


class SesionesRedis:
    def __init__(self, redis, mongo, ttl_seg: int):
        self._redis = redis
        self._mongo = mongo
        self._ttl = ttl_seg

    def crear(self, usuario_id: str) -> str:
        if not self._mongo.existe_usuario(usuario_id):
            raise NoEncontrado(f"No existe el usuario {usuario_id}.")
        token = secrets.token_urlsafe(32)
        self._redis.guardar(PREFIJO + token, usuario_id, self._ttl)
        return token

    def usuario_de(self, credencial: str | None) -> str:
        # Un token ajeno al formato no se consulta: no tiene sentido ir a Redis con cualquier cosa.
        if not credencial or len(credencial) > 100:
            raise NoAutorizado("Falta la sesión o venció. Abrí una con POST /sesiones.")
        usuario = self._redis.leer_renovando(PREFIJO + credencial, self._ttl)
        if usuario is None:
            raise NoAutorizado("Falta la sesión o venció. Abrí una con POST /sesiones.")
        return usuario

    def cerrar(self, token: str | None) -> None:
        if token:
            self._redis.borrar(PREFIJO + token)
