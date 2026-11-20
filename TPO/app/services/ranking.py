from app.errors import NoEncontrado, Prohibido


def _orden(fila: dict) -> tuple:
    return (-fila["puntos"], -fila["exactos"], -fila["tiempo_seg"], fila["usuario_id"])


class RankingService:
    """Tablas de posiciones. El ranking general sale del puerto de ranking (Redis o MongoDB, según la configuración)."""

    def __init__(self, ranking, mongo):
        self._ranking = ranking
        self._mongo = mongo

    @property
    def fuente(self) -> str:
        return self._ranking.nombre

    def top(self, limit: int) -> list[dict]:
        return self._ranking.top(limit)

    def posicion(self, usuario_id: str) -> dict:
        posicion = self._ranking.posicion(usuario_id)
        if posicion is None:
            raise NoEncontrado(f"El usuario {usuario_id} todavía no tiene puntaje.")
        return posicion

    def historico(self, partido_id: str) -> dict:
        foto = self._mongo.obtener_foto(partido_id)
        if foto is None:
            raise NoEncontrado(f"No hay ranking guardado para el partido {partido_id}.")
        return foto

    def tabla_de_prode(self, prode_id: str, usuario_id: str) -> tuple[dict, list[dict]]:
        """La tabla de un prode privado se arma al pedirla con los puntajes de sus integrantes (hasta 100).

        No hay un ranking guardado por prode: así cerrar un partido cuesta una escritura por usuario y no
        una por cada prode de cada usuario.
        """
        prode = self._mongo.obtener_prode(prode_id)
        if prode is None:
            raise NoEncontrado(f"No existe el prode {prode_id}.")
        if usuario_id not in prode["integrantes"]:
            raise Prohibido("Solo los integrantes pueden ver la tabla del prode.")
        filas = sorted(self._ranking.puntajes_de(prode["integrantes"]), key=_orden)
        return prode, [{"puesto": n, **f} for n, f in enumerate(filas, start=1)]

    def con_pronosticos_del_partido(self, tabla: list[dict], partido_id: str) -> list[dict]:
        pronosticos = self._mongo.pronosticos_del_partido(partido_id, [fila["usuario_id"] for fila in tabla])
        return [{**fila, "pronostico": pronosticos.get(fila["usuario_id"])} for fila in tabla]
