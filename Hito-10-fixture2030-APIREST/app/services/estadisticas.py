from datetime import datetime, timedelta, timezone

from app.config.settings import Settings
from app.errors import ValidacionError


def _parsear(valor: str, campo: str) -> datetime:
    try:
        dt = datetime.fromisoformat(valor.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValidacionError(f"'{campo}' no es una fecha ISO-8601 válida.") from exc
    if dt.tzinfo is None:
        raise ValidacionError(f"'{campo}' debe incluir zona horaria (ej. 2030-06-15T18:30:00Z).")
    return dt.astimezone(timezone.utc).replace(tzinfo=None, microsecond=0)


class EstadisticasService:
    def __init__(self, repo, settings: Settings):
        self._repo = repo
        self._s = settings

    def obtener(self, partido_id: str, desde: str, hasta: str, equipo: str | None, agregacion: str) -> dict:
        d, h = _parsear(desde, "desde"), _parsear(hasta, "hasta")
        if h <= d:
            raise ValidacionError("'hasta' debe ser posterior a 'desde'.")
        if h - d > timedelta(minutes=self._s.influx_max_ventana_minutos):
            raise ValidacionError(f"La ventana no puede superar {self._s.influx_max_ventana_minutos} minutos.")
        tope = self._s.influx_max_puntos
        filas = self._repo.consultar_estadisticas(partido_id, d, h, equipo, agregacion, tope + 1)
        return {
            "partido_id": partido_id, "agregacion": agregacion,
            "desde": d.isoformat() + "Z", "hasta": h.isoformat() + "Z",
            "max_puntos": tope, "truncado": len(filas) > tope, "puntos": filas[:tope],
        }
