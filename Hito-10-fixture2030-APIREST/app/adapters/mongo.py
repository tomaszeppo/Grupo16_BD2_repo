from app.adapters.base import operacion
from app.config.settings import Settings
from app.errors import ApiError, Conflicto, DependenciaNoDisponible, DependenciaTimeout, NoEncontrado

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
    """Colecciones documentales `equipos`, `jugadores` y `partidos` de `fixture2030`."""

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

    def obtener_partido_detalle(self, codigo: str) -> dict | None:
        with operacion(FUENTE, "obtener_partido_detalle", _traducir):
            return self._db().partidos.find_one({"codigo": codigo}, {"_id": 0})

    def cambiar_estado_partido(self, codigo: str, nuevo: str) -> None:
        transiciones = {("Programado", "En juego"), ("En juego", "Finalizado")}
        with operacion(FUENTE, "cambiar_estado_partido", _traducir):
            partidos = self._db().partidos
            actual = partidos.find_one({"codigo": codigo}, {"_id": 0, "estado": 1})
            if actual is None:
                raise NoEncontrado(f"No existe el partido '{codigo}'.")
            estado_actual = actual["estado"]
            if estado_actual == nuevo:
                return
            if (estado_actual, nuevo) not in transiciones:
                raise Conflicto(f"El partido '{codigo}' no puede pasar de '{estado_actual}' a '{nuevo}'.")

            resultado = partidos.update_one(
                {"codigo": codigo, "estado": estado_actual},
                {"$set": {"estado": nuevo}},
            )
            if resultado.modified_count:
                return

            actual = partidos.find_one({"codigo": codigo}, {"_id": 0, "estado": 1})
            if actual is None:
                raise NoEncontrado(f"No existe el partido '{codigo}'.")
            if actual["estado"] == nuevo:
                return
            raise Conflicto(f"El partido '{codigo}' cambió de estado antes de guardar la transición.")

    def avance_simulacion(self, codigo: str, minuto: int, local: int, visitante: int) -> None:
        with operacion(FUENTE, "avance_simulacion", _traducir):
            resultado = self._db().partidos.update_one(
                {"codigo": codigo, "estado": "En juego", "$or": [
                    {"minuto": {"$exists": False}}, {"minuto": {"$lte": minuto}}]},
                {"$set": {"minuto": minuto, "marcador": {"local": local, "visitante": visitante}}},
            )
            if not resultado.matched_count:
                raise Conflicto("El partido no está en juego o el minuto retrocede.")

    def ping(self) -> None:
        with operacion(FUENTE, "ping", _traducir):
            self._db().command("ping")
