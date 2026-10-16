from app.adapters.base import operacion
from app.config.settings import Settings
from app.errors import ApiError, Conflicto, DependenciaNoDisponible, DependenciaTimeout, NoEncontrado

FUENTE = "iris"

SQL_PARTIDO = (
    "SELECT ID, Codigo, EquipoLocal, EquipoVisitante, FechaHora, Sede, Estado FROM Fixture.Partido WHERE Codigo = ?"
)
SQL_EVENTOS = "SELECT TOP 200 Tipo, Minuto, Descripcion, JugadorCodigo FROM Fixture.Evento WHERE Partido = ? ORDER BY Minuto"


class IrisAdapter:
    """Clases persistentes `Fixture.Partido` y `Fixture.Evento` (Hito 9), namespace configurable (por defecto USER)."""

    fuente = FUENTE

    def __init__(self, settings: Settings):
        self._s = settings
        self._conexion = None

    def _traducir(self, exc: Exception) -> ApiError | None:
        self._conexion = None  # fuerza reconexión en el próximo intento
        if isinstance(exc, TimeoutError):
            return DependenciaTimeout(FUENTE)
        if isinstance(exc, (OSError, RuntimeError)) or type(exc).__module__.split(".")[0] in ("iris", "intersystems_iris"):
            return DependenciaNoDisponible(FUENTE)
        return None

    def _conn(self):
        if self._conexion is None:
            import iris

            self._conexion = iris.connect(
                self._s.iris_host, self._s.iris_port, self._s.iris_namespace,
                self._s.iris_user, self._s.iris_password, timeout=max(1, round(self._s.timeout_segundos)),
            )
        return self._conexion

    def obtener_partido(self, codigo: str) -> dict | None:
        with operacion(FUENTE, "obtener_partido", self._traducir):
            cur = self._conn().cursor()
            cur.execute(SQL_PARTIDO, [codigo])
            fila = cur.fetchone()
            if fila is None:
                return None
            fila = tuple(fila)  # las DataRow del driver quedan ligadas al cursor: se copian antes de reutilizarlo
            cur.execute(SQL_EVENTOS, [fila[0]])
            eventos = [
                {"tipo": r[0], "minuto": r[1], "descripcion": r[2] or None, "jugador_codigo": r[3] or None}
                for r in (tuple(x) for x in cur.fetchall())
            ]
            return {
                "codigo": fila[1], "equipo_local": fila[2], "equipo_visitante": fila[3],
                "fecha_hora": str(fila[4]).replace(" ", "T"), "sede": fila[5], "estado": fila[6], "eventos": eventos,
            }

    def cambiar_estado(self, codigo: str, nuevo: str) -> None:
        with operacion(FUENTE, "cambiar_estado", self._traducir):
            import iris

            cur = self._conn().cursor()
            cur.execute("SELECT ID, Estado FROM Fixture.Partido WHERE Codigo = ?", [codigo])
            fila = cur.fetchone()
            if fila is None:
                raise NoEncontrado(f"No existe el partido '{codigo}'.")
            fila = tuple(fila)
            api = iris.createIRIS(self._conn())
            partido = api.classMethodObject("Fixture.Partido", "%OpenId", fila[0])
            if not partido.invoke("CambiarEstado", nuevo):  # la regla de transición vive en la clase del Hito 9
                raise Conflicto(f"El partido '{codigo}' no puede pasar de '{fila[1]}' a '{nuevo}'.")
            if partido.invoke("%Save") != 1:
                raise ApiError("No se pudo guardar el cambio de estado.")

    def ping(self) -> None:
        with operacion(FUENTE, "ping", self._traducir):
            cur = self._conn().cursor()
            cur.execute("SELECT 1")
            cur.fetchone()
