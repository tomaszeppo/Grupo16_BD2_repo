from collections.abc import Callable
from datetime import datetime, timezone

Reloj = Callable[[], datetime]


def ahora() -> datetime:
    """Hora actual en UTC. Todo el proyecto guarda y compara fechas en UTC."""
    return datetime.now(timezone.utc)


def get_reloj() -> Reloj:
    return ahora
