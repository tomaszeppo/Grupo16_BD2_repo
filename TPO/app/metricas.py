"""Métricas de la API en formato de Prometheus (GET /metrics).

Son métricas de aplicación: lo que la API ve de sí misma y de cada operación contra una base. Las métricas
internas de las bases (memoria, conexiones, replicación) salen de sus exportadores, no de acá.

Con varios procesos de uvicorn cada uno lleva sus contadores; `PROMETHEUS_MULTIPROC_DIR` hace que
/metrics devuelva la suma de todos, sin importar cuál responda.
"""
import os
import time

from fastapi import Request
from prometheus_client import REGISTRY, CollectorRegistry, Counter, Gauge, Histogram, generate_latest, multiprocess

_TIEMPOS_PEDIDO = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10)
_TIEMPOS_BASE = (0.001, 0.0025, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 3)
_TIEMPOS_PUNTUACION = (0.01, 0.05, 0.1, 0.5, 1, 5, 10, 30, 60, 300)

PEDIDOS = Counter("prode_api_pedidos_total", "Pedidos atendidos por la API", ["metodo", "ruta", "estado"])
DURACION_PEDIDO = Histogram("prode_api_duracion_segundos", "Tiempo de respuesta de la API, en segundos",
                            ["metodo", "ruta"], buckets=_TIEMPOS_PEDIDO)
OPERACIONES = Counter("prode_base_operaciones_total", "Operaciones de la API contra una base",
                      ["base", "operacion", "resultado"])
DURACION_OPERACION = Histogram("prode_base_duracion_segundos", "Duración de cada operación contra una base, en segundos",
                               ["base", "operacion"], buckets=_TIEMPOS_BASE)
DURACION_PUNTUACION = Histogram("prode_puntuacion_duracion_segundos",
                                "Duración de cada paso de la puntuación de un partido, en segundos",
                                ["paso"], buckets=_TIEMPOS_PUNTUACION)
PRONOSTICOS_PUNTUADOS = Counter("prode_puntuacion_pronosticos_total", "Pronósticos puntuados al cerrar partidos")
# Cada proceso tiene su copia del calendario: se informa la más vieja y si alguna quedó desactualizada.
CALENDARIO_ANTIGUEDAD = Gauge("prode_calendario_antiguedad_segundos",
                              "Segundos desde que este proceso renovó su copia del calendario",
                              multiprocess_mode="livemax")
CALENDARIO_DESACTUALIZADO = Gauge("prode_calendario_desactualizado",
                                  "1 si la copia del calendario no se pudo renovar desde Neo4j (o no se cargó aún)",
                                  multiprocess_mode="livemax")

CASSANDRA_CAMBIO_REGION = Counter("prode_cassandra_cambio_region_total",
                                  "Operaciones de Cassandra atendidas por la otra región porque la propia no respondió",
                                  ["desde", "hacia"])

VIVO_COMENTARIOS = Counter("prode_vivo_comentarios_total", "Comentarios por origen y resultado",
                           ["origen", "resultado"])

VIVO_CONEXIONES = Gauge("prode_vivo_conexiones", "Conexiones en vivo abiertas (suma de todos los procesos)",
                        multiprocess_mode="livesum")
VIVO_ENTREGA = Histogram("prode_vivo_entrega_segundos",
                         "Desde que se publica un comentario hasta que sale por cada conexión, en segundos",
                         buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5))
VIVO_DESCARTADOS = Counter("prode_vivo_descartados_total",
                           "Mensajes descartados porque la conexión de un espectador no daba abasto")

SIN_RUTA = "(sin ruta)"  # pedidos a direcciones que no existen: una sola etiqueta, no una por dirección


def registrar_operacion(base: str, operacion: str, resultado: str, segundos: float) -> None:
    OPERACIONES.labels(base, operacion, resultado).inc()
    DURACION_OPERACION.labels(base, operacion).observe(segundos)


def registrar_paso_de_puntuacion(paso: str, segundos: float, pronosticos: int | None = None) -> None:
    DURACION_PUNTUACION.labels(paso).observe(segundos)
    if pronosticos:
        PRONOSTICOS_PUNTUADOS.inc(pronosticos)


def texto_de_metricas() -> str:
    if os.environ.get("PROMETHEUS_MULTIPROC_DIR"):
        registro = CollectorRegistry()
        multiprocess.MultiProcessCollector(registro)
    else:
        registro = REGISTRY
    return generate_latest(registro).decode()


def instrumentar(app) -> None:
    """Cuenta y cronometra cada pedido por la plantilla de su ruta (/partidos/{partido_id}), nunca por la ruta real."""

    @app.middleware("http")
    async def medir(request: Request, call_next):
        if request.url.path == "/metrics":
            return await call_next(request)
        inicio = time.perf_counter()
        estado = 500
        try:
            respuesta = await call_next(request)
            estado = respuesta.status_code
            return respuesta
        finally:
            ruta = getattr(request.scope.get("route"), "path", SIN_RUTA)
            PEDIDOS.labels(request.method, ruta, str(estado)).inc()
            DURACION_PEDIDO.labels(request.method, ruta).observe(time.perf_counter() - inicio)
