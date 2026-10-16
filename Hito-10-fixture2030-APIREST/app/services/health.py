import time
from concurrent.futures import ThreadPoolExecutor

from app.errors import ApiError


class HealthService:
    def __init__(self, adaptadores: dict):
        self._adaptadores = adaptadores

    def estado(self) -> dict:
        def chequear(item):
            nombre, adaptador = item
            inicio = time.perf_counter()
            try:
                adaptador.ping()
                ok = True
            except ApiError:
                ok = False
            return nombre, {
                "estado": "ok" if ok else "caida",
                "latencia_ms": round((time.perf_counter() - inicio) * 1000, 1),
            }

        with ThreadPoolExecutor(max_workers=max(1, len(self._adaptadores))) as pool:
            fuentes = dict(pool.map(chequear, self._adaptadores.items()))
        todas_ok = all(f["estado"] == "ok" for f in fuentes.values())
        return {"estado": "ok" if todas_ok else "degradado", "fuentes": fuentes}
