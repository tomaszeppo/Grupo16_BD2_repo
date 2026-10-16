from app.adapters.base import operacion
from app.config.settings import Settings
from app.errors import ApiError, DependenciaNoDisponible, DependenciaTimeout

FUENTE = "mongodb"
_PROYECCION_JUGADOR = {"_id": 0, "nombre": 1, "apellido": 1, "dorsal": 1, "posicion": 1, "equipo": 1}


def _traducir(exc: Exception) -> ApiError | None:
    try:
        from pymongo.errors import ExecutionTimeout, NetworkTimeout, PyMongoError
    except ImportError:
        return None
    if isinstance(exc, (NetworkTimeout, ExecutionTimeout)):
        return DependenciaTimeout(FUENTE)
    if isinstance(exc, PyMongoError):
        return DependenciaNoDisponible(FUENTE)
    return None


class MongoAdapter:
    """Colecciones `equipos` y `jugadores` de la base `fixture2030` (patrones del Hito 4)."""

    fuente = FUENTE

    def __init__(self, settings: Settings):
        self._s = settings
        self._client = None

    def _db(self):
        if self._client is None:
            from pymongo import MongoClient

            ms = int(self._s.timeout_segundos * 1000)
            opciones = {"serverSelectionTimeoutMS": ms, "connectTimeoutMS": ms, "socketTimeoutMS": ms}
            if self._s.mongo_user:
                opciones.update(username=self._s.mongo_user, password=self._s.mongo_password, authSource="admin")
            self._client = MongoClient(self._s.mongo_host, self._s.mongo_port, **opciones)
        return self._client[self._s.mongo_db]

    @staticmethod
    def _filtro(codigo: str, posicion: str | None) -> dict:
        filtro = {"equipo": codigo}  # índice sobre jugadores.equipo
        if posicion:
            filtro["posicion"] = posicion
        return filtro

    def obtener_equipo(self, codigo: str) -> dict | None:
        with operacion(FUENTE, "obtener_equipo", _traducir):  # índice único sobre equipos.codigo
            return self._db().equipos.find_one({"codigo": codigo}, {"_id": 0, "codigo": 1, "nombre": 1})

    def contar_jugadores(self, codigo: str, posicion: str | None) -> int:
        with operacion(FUENTE, "contar_jugadores", _traducir):
            return self._db().jugadores.count_documents(self._filtro(codigo, posicion))

    def listar_jugadores(self, codigo: str, posicion: str | None, limit: int, offset: int) -> list[dict]:
        with operacion(FUENTE, "listar_jugadores", _traducir):
            cursor = (
                self._db()
                .jugadores.find(self._filtro(codigo, posicion), _PROYECCION_JUGADOR)
                .sort([("apellido", 1), ("nombre", 1), ("dorsal", 1)])
                .skip(offset)
                .limit(limit)
            )
            return list(cursor)

    def ping(self) -> None:
        with operacion(FUENTE, "ping", _traducir):
            self._db().command("ping")
