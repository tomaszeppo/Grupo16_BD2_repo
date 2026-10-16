import re
from datetime import datetime

from app.adapters.base import operacion
from app.config.settings import Settings
from app.errors import ApiError, DependenciaNoDisponible, DependenciaTimeout, ValidacionError

FUENTE = "influxdb"
_RE_PARTIDO = re.compile(r"^P-\d{2,3}$")
_RE_EQUIPO = re.compile(r"^[A-Z]{3}$")
_INTERVALOS = {"1m": "1 minute", "5m": "5 minutes"}


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def construir_sql(
    partido_id: str, desde: datetime, hasta: datetime, equipo: str | None, agregacion: str, limite: int
) -> str:
    """SQL fijo. Los únicos valores variables pasaron por regex/tipos estrictos (defensa en profundidad: se revalida acá)."""
    if not _RE_PARTIDO.fullmatch(partido_id) or (equipo is not None and not _RE_EQUIPO.fullmatch(equipo)):
        raise ValidacionError("Identificador de partido o equipo inválido.")
    filtro = f"partido_id = '{partido_id}' AND time >= '{_iso(desde)}' AND time < '{_iso(hasta)}'"
    if equipo:
        filtro += f" AND equipo_id = '{equipo}'"
    if agregacion == "raw":
        return (
            "SELECT time, equipo_id, fuente, posesion_pct, pases_completados, tiros, recuperaciones, velocidad_kmh "
            f"FROM estadisticas_partido WHERE {filtro} ORDER BY time, equipo_id, fuente LIMIT {int(limite)}"
        )
    intervalo = _INTERVALOS[agregacion]
    return (
        f"SELECT DATE_BIN(INTERVAL '{intervalo}', time, TIMESTAMP '1970-01-01T00:00:00Z') AS ventana, "
        "equipo_id, fuente, "
        "AVG(posesion_pct) AS posesion_pct_prom, SUM(pases_completados) AS pases_completados, SUM(tiros) AS tiros, "
        "SUM(recuperaciones) AS recuperaciones, AVG(velocidad_kmh) AS velocidad_kmh_prom, "
        "MAX(velocidad_kmh) AS velocidad_kmh_max "
        f"FROM estadisticas_partido WHERE {filtro} GROUP BY 1, 2, 3 ORDER BY 1, 2, 3 LIMIT {int(limite)}"
    )


def _traducir(exc: Exception) -> ApiError | None:
    try:
        import httpx
    except ImportError:
        return None
    if isinstance(exc, httpx.ConnectTimeout):
        return DependenciaNoDisponible(FUENTE)
    if isinstance(exc, httpx.TimeoutException):
        return DependenciaTimeout(FUENTE)
    if isinstance(exc, httpx.HTTPError):
        return DependenciaNoDisponible(FUENTE)
    return None


def _z(valor):
    if isinstance(valor, str) and re.match(r"^\d{4}-\d{2}-\d{2}T[\d:.]+$", valor):
        return valor.split(".")[0] + "Z"
    return valor


class InfluxAdapter:
    """InfluxDB 3 Core por HTTP (`/api/v3/query_sql`). Base `fixture2030_metrics`, tabla `estadisticas_partido`."""

    fuente = FUENTE

    def __init__(self, settings: Settings):
        self._s = settings
        self._http = None

    def _cli(self):
        if self._http is None:
            import httpx

            t = self._s.timeout_segundos
            self._http = httpx.Client(
                base_url=self._s.influx_url,
                timeout=httpx.Timeout(t),
                headers={"Authorization": f"Bearer {self._s.influx_token}"},
            )
        return self._http

    def consultar(self, sql: str) -> list[dict]:
        resp = self._cli().post("/api/v3/query_sql", json={"db": self._s.influx_db, "q": sql, "format": "json"})
        if resp.status_code != 200:  # credencial inválida, base inexistente, error del servidor: nunca [] ni el detalle
            raise DependenciaNoDisponible(FUENTE)
        return resp.json()

    def consultar_estadisticas(self, partido_id, desde, hasta, equipo, agregacion, limite) -> list[dict]:
        sql = construir_sql(partido_id, desde, hasta, equipo, agregacion, limite)
        with operacion(FUENTE, f"estadisticas_{agregacion}", _traducir):
            filas = self.consultar(sql)
        return [{k: _z(v) for k, v in fila.items()} for fila in filas]

    def ping(self) -> None:
        with operacion(FUENTE, "ping", _traducir):
            resp = self._cli().get("/ping")
            if resp.status_code != 200:
                raise DependenciaNoDisponible(FUENTE)
