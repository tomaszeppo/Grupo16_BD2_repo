"""Puerto de sesiones: quién hace el pedido.

Hoy la API confía en el encabezado X-Usuario-Id y solo verifica que el usuario exista. Es acceso de
laboratorio, no autenticación. Cuando esté Redis, alcanza con otra clase que cumpla `SesionesPort`
(validando el identificador de sesión contra Redis) y cambiar el proveedor en app/deps.py: rutas y
servicios no se tocan. Ver docs/como_sumar_una_base.md.
"""
from typing import Protocol

from app.dominio.ids import es_id_usuario
from app.errors import NoAutorizado


class SesionesPort(Protocol):
    def usuario_de(self, credencial: str | None) -> str:
        """Devuelve el id del usuario o lanza NoAutorizado."""


class SesionesPorEncabezado:
    def __init__(self, mongo):
        self._mongo = mongo

    def usuario_de(self, credencial: str | None) -> str:
        if not credencial or not es_id_usuario(credencial) or not self._mongo.existe_usuario(credencial):
            raise NoAutorizado("Falta el encabezado X-Usuario-Id o no corresponde a un usuario registrado.")
        return credencial
