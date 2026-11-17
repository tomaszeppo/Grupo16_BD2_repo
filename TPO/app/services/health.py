from concurrent.futures import ThreadPoolExecutor

from app.errors import ApiError


class HealthService:
    def __init__(self, adaptadores: dict, calendario=None):
        self._adaptadores = adaptadores
        self._calendario = calendario

    def dependencias(self) -> dict:
        def chequear(item):
            nombre, adaptador = item
            try:
                adaptador.ping()
                return nombre, {"estado": "ok", "detalle": None}
            except ApiError as exc:
                return nombre, {"estado": "caida", "detalle": exc.mensaje}

        with ThreadPoolExecutor(max_workers=max(1, len(self._adaptadores))) as pool:
            salida = dict(pool.map(chequear, self._adaptadores.items()))
        if self._calendario is not None:
            self._calendario.refrescar()  # así el estado informado no depende de que alguien haya pronosticado recién
            salida["calendario"] = self._calendario.estado()
        return salida
