import uuid
from datetime import datetime

from app.adapters.base import operacion
from app.config.settings import Settings
from app.errors import ApiError, Conflicto, DependenciaNoDisponible, DependenciaTimeout

FUENTE = "cassandra"
NAMESPACE_IDEMPOTENCIA = uuid.UUID("6f1c2d4e-8a3b-4c7d-9e0f-1a2b3c4d5e6f")

_COLS = "comentario_id, usuario_id, usuario_nombre, contenido, likes, estado_moderacion, creado_en"
CQL_LISTAR = f"SELECT {_COLS} FROM comentarios_por_partido_pais WHERE partido_id = %s AND pais = %s AND ventana = %s"
CQL_LEER = (
    f"SELECT {_COLS} FROM comentarios_por_partido_pais "
    "WHERE partido_id = %s AND pais = %s AND ventana = %s AND creado_en = %s AND comentario_id = %s"
)
CQL_IDEMP_INSERT = (
    "INSERT INTO comentarios_idempotencia (clave, partido_id, pais, ventana, creado_en, comentario_id) "
    "VALUES (%s, %s, %s, %s, %s, %s) IF NOT EXISTS"
)
CQL_IDEMP_LEER = (
    "SELECT partido_id, pais, ventana, creado_en, comentario_id FROM comentarios_idempotencia WHERE clave = %s"
)
CQL_INS_COMENTARIO = (
    "INSERT INTO comentarios_por_partido_pais (partido_id, pais, ventana, creado_en, comentario_id, usuario_id, "
    "usuario_nombre, contenido, likes, estado_moderacion) "
    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 0, 'PUBLICADO') IF NOT EXISTS"
)
CQL_INS_LIKES = (
    "INSERT INTO comentarios_por_likes_partido_pais (partido_id, pais, ventana, likes, creado_en, comentario_id, "
    "usuario_nombre, contenido) VALUES (%s, %s, %s, 0, %s, %s, %s, %s) IF NOT EXISTS"
)


def _traducir(exc: Exception) -> ApiError | None:
    try:
        from cassandra import DriverException, OperationTimedOut, ReadTimeout, RequestExecutionException, WriteTimeout
        from cassandra.cluster import NoHostAvailable
    except ImportError:
        return None
    if isinstance(exc, (OperationTimedOut, ReadTimeout, WriteTimeout)):
        return DependenciaTimeout(FUENTE)
    if isinstance(exc, (NoHostAvailable, DriverException, RequestExecutionException)):
        return DependenciaNoDisponible(FUENTE)
    return None


def _iso(dt: datetime) -> str:
    return dt.replace(tzinfo=None).isoformat(timespec="milliseconds") + "Z"


def _item(fila) -> dict:
    return {
        "comentario_id": str(fila.comentario_id),
        "usuario_id": fila.usuario_id,
        "usuario_nombre": fila.usuario_nombre,
        "contenido": fila.contenido,
        "likes": fila.likes,
        "estado_moderacion": fila.estado_moderacion,
        "creado_en": _iso(fila.creado_en),
    }


class CassandraAdapter:
    """Keyspace `fixture2030`. Toda lectura usa la partición completa (partido_id, pais, ventana)."""

    fuente = FUENTE

    def __init__(self, settings: Settings):
        self._s = settings
        self._cluster = None
        self._session = None

    def _sesion(self):
        if self._session is None:
            from cassandra.cluster import Cluster

            t = self._s.timeout_segundos
            cluster = Cluster(
                [self._s.cassandra_host], port=self._s.cassandra_port, connect_timeout=t, protocol_version=4
            )
            try:
                sesion = cluster.connect(self._s.cassandra_keyspace)
            except Exception:
                cluster.shutdown()
                raise
            sesion.default_timeout = t
            self._cluster, self._session = cluster, sesion
        return self._session

    def listar(self, partido_id, pais, ventana: datetime, limit: int, paging_state: bytes | None):
        from cassandra.query import SimpleStatement

        with operacion(FUENTE, "listar_comentarios", _traducir):
            rs = self._sesion().execute(
                SimpleStatement(CQL_LISTAR, fetch_size=limit), (partido_id, pais, ventana), paging_state=paging_state
            )
            return [_item(f) for f in rs.current_rows], rs.paging_state

    def registrar(
        self, *, clave, partido_id, pais, ventana, creado_en, usuario_id, usuario_nombre, contenido
    ) -> tuple[dict, bool]:
        comentario_id = uuid.uuid5(NAMESPACE_IDEMPOTENCIA, clave)
        with operacion(FUENTE, "registrar_comentario", _traducir):
            s = self._sesion()
            fila = s.execute(CQL_IDEMP_INSERT, (clave, partido_id, pais, ventana, creado_en, comentario_id)).one()
            if not fila[0]:  # [applied] = False: la clave ya existía; se reutilizan ventana y creado_en originales
                previo = s.execute(CQL_IDEMP_LEER, (clave,)).one()
                if previo is None or (previo.partido_id, previo.pais) != (partido_id, pais):
                    raise Conflicto("La Idempotency-Key ya se usó para otro comentario.")
                ventana, creado_en, comentario_id = previo.ventana, previo.creado_en, previo.comentario_id
            # IF NOT EXISTS: un reintento (o una caída entre las dos escrituras) completa lo que falte sin duplicar.
            s.execute(
                CQL_INS_COMENTARIO,
                (partido_id, pais, ventana, creado_en, comentario_id, usuario_id, usuario_nombre, contenido),
            )
            s.execute(CQL_INS_LIKES, (partido_id, pais, ventana, creado_en, comentario_id, usuario_nombre, contenido))
            guardado = s.execute(CQL_LEER, (partido_id, pais, ventana, creado_en, comentario_id)).one()
            resultado = {**_item(guardado), "partido_id": partido_id, "pais": pais, "ventana": _iso(ventana)}
            return resultado, bool(fila[0])  # True si esta llamada creó el comentario; False si fue un reintento

    def ping(self) -> None:
        with operacion(FUENTE, "ping", _traducir):
            self._sesion().execute("SELECT release_version FROM system.local")
