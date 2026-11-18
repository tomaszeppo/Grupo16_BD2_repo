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
                headers={"Authorization": f"Bearer {self._s.influx_token}"} if self._s.influx_token else {},
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

    def guardar_minuto(self, partido_id: str, minuto: int, local: str, visitante: str, instante, goles_minuto=None, acciones_minuto=None):
        """Dos muestras: posesión instantánea y acciones del minuto simulado."""
        import math
        if not _RE_PARTIDO.fullmatch(partido_id) or not _RE_EQUIPO.fullmatch(local) or not _RE_EQUIPO.fullmatch(visitante):
            raise ValidacionError("Identificador de partido o equipo inválido.")
        posesion = round(50 + 9 * math.sin(minuto / 8), 1)
        timestamp = int(instante.timestamp() * 1_000_000_000)
        lineas = []
        for lado, equipo, pct in ((0, local, posesion), (1, visitante, round(100 - posesion, 1))):
            acciones = acciones_minuto[lado] if acciones_minuto is not None else {}
            pases = max(0 if minuto == 0 else 3 + (minuto + lado * 2) % 5, acciones.get("Pase", 0))
            gol = (goles_minuto[lado] if goles_minuto is not None else int(minuto == (23 if lado == 0 else 75)))
            tiros = max(int(minuto > 0 and minuto % (8 + lado) == 0), gol + acciones.get("Tiro", 0))
            intentados = pases + (int(minuto % 3 == lado) if minuto else 0)
            tiros_arco = max(int(bool(tiros) and minuto % 2 == lado), gol)
            faltas = max(int(minuto > 0 and minuto % (11 + lado) == 0), acciones.get("Falta", 0))
            corners = int(bool(tiros) and minuto % 3 == lado)
            lineas.append(f"estadisticas_partido,partido_id={partido_id},equipo_id={equipo},fuente=simulacion "
                          f"minuto={minuto}i,posesion_pct={pct},pases_completados={pases}i,"
                          f"pases_intentados={intentados}i,tiros={tiros}i,tiros_arco={tiros_arco}i,"
                          f"faltas={faltas}i,corners={corners}i,goles={gol}i {timestamp}")
        with operacion(FUENTE, "guardar_minuto", _traducir):
            respuesta = self._cli().post("/api/v3/write_lp", params={"db": self._s.influx_db, "precision": "nanosecond"},
                                         content="\n".join(lineas) + "\n")
            if respuesta.status_code not in (200, 204):
                raise DependenciaNoDisponible(FUENTE)

    def resumen_partido(self, partido_id: str) -> list[dict]:
        if not _RE_PARTIDO.fullmatch(partido_id):
            raise ValidacionError("Identificador de partido inválido.")
        base = ("SELECT equipo_id, AVG(posesion_pct) AS posesion_pct, SUM(tiros) AS tiros, "
                "SUM(pases_completados) AS pases_completados, MAX(minuto) AS minuto ")
        nuevos = (", SUM(tiros_arco) AS tiros_arco, SUM(faltas) AS faltas, SUM(corners) AS corners, "
                  "SUM(pases_intentados) AS pases_intentados, COUNT(tiros_arco) AS muestras_detalladas, "
                  "COUNT(*) AS muestras ")
        filtro = ("FROM estadisticas_partido "
                  f"WHERE partido_id = '{partido_id}' AND fuente = 'simulacion' GROUP BY equipo_id ORDER BY equipo_id")
        with operacion(FUENTE, "resumen_partido", _traducir):
            try:
                return self.consultar(base + nuevos + filtro)
            except DependenciaNoDisponible:
                # Las instalaciones antiguas pueden no tener todavía las columnas nuevas.
                return self.consultar(base + filtro)

    def muestras_partido(self, partido_id: str) -> list[dict]:
        """Muestras por equipo y minuto que sustentan el resumen histórico."""
        if not _RE_PARTIDO.fullmatch(partido_id):
            raise ValidacionError("Identificador de partido inválido.")
        sql = ("SELECT equipo_id, minuto, posesion_pct, tiros, tiros_arco, pases_completados, "
               "pases_intentados, faltas, corners, goles, time FROM estadisticas_partido "
               f"WHERE partido_id = '{partido_id}' AND fuente = 'simulacion' ORDER BY equipo_id, minuto LIMIT 500")
        with operacion(FUENTE, "muestras_partido", _traducir):
            return self.consultar(sql)
