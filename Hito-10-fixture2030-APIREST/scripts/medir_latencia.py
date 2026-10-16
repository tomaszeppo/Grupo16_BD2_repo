"""Mide latencia de extremo a extremo (cliente → API → base) de un GET por módulo. Uso: python scripts/medir_latencia.py [N]"""
import platform
import statistics
import sys
import time

import httpx

BASE = "http://127.0.0.1:8000"
V = "2030-06-15T18:30:00Z"
CASOS = {
    "mongodb   GET /equipos/ARG": "/equipos/ARG",
    "neo4j     GET /partidos/P-01": "/partidos/P-01",
    "cassandra GET comentarios": f"/partidos/P-01/comentarios?pais=ARG&ventana={V}&limit=20",
    "redis     GET /sesiones/U001": "/sesiones/U001",
    "influxdb  GET estadisticas 5min/1m": f"/partidos/P-01/estadisticas?desde={V}&hasta=2030-06-15T18:35:00Z&agregacion=1m",
    "iris      GET detalle": "/partidos/P-01/detalle",
}


def main(n: int) -> None:
    print(f"Entorno: {platform.platform()} · cliente Python {platform.python_version()} · API y las 6 bases en Docker (1 nodo cada una)")
    print(f"Método: {n} requests secuenciales por endpoint tras 5 de calentamiento; latencia medida en el cliente (httpx); "
          "datos de la siembra (P-01..P-08); un solo cliente, sin carga concurrente")
    with httpx.Client(base_url=BASE, timeout=15) as c:
        for nombre, ruta in CASOS.items():
            for _ in range(5):
                c.get(ruta)
            tiempos, errores = [], 0
            for _ in range(n):
                t = time.perf_counter()
                r = c.get(ruta)
                tiempos.append((time.perf_counter() - t) * 1000)
                errores += r.status_code != 200
            tiempos.sort()
            print(f"{nombre:<38} p50={statistics.median(tiempos):7.1f} ms  p95={tiempos[int(n * 0.95) - 1]:7.1f} ms  "
                  f"max={tiempos[-1]:7.1f} ms  errores={errores}/{n}")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 50)
