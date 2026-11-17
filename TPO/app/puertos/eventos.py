"""Puerto de eventos: a quién se le avisa cada jugada que se carga.

Hoy nadie escucha. Cuando esté InfluxDB, alcanza con una clase que cumpla `PublicadorEventos` y escriba el
punto de la serie, y cambiar el proveedor en app/deps.py. Si el publicador falla, la jugada igual queda
guardada en Neo4j: el aviso es secundario. Ver docs/como_sumar_una_base.md.
"""
from typing import Protocol


class PublicadorEventos(Protocol):
    def publicar(self, partido_id: str, evento: dict) -> None:
        """Recibe la jugada recién guardada: id, tipo, minuto, orden, jugador e influido_por."""


class SinPublicador:
    def publicar(self, partido_id: str, evento: dict) -> None:
        return None
