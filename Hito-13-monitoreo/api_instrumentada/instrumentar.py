"""Puntos de medición agregados en el arranque, envolviendo funciones del Hito 10 en lugar de editarlas."""
import importlib
import time
from concurrent.futures import ThreadPoolExecutor, wait
from contextlib import contextmanager
from functools import wraps

from prometheus_client.core import GaugeMetricFamily

from api_instrumentada.metricas import BASE_DURACION, COMENTARIOS_CREADOS, HTTP_DURACION, HTTP_PEDIDOS

ADAPTADORES = ("mongo", "neo4j", "cassandra", "redis", "influx", "iris")
FUENTES = ("mongodb", "neo4j", "cassandra", "redis", "influxdb", "iris")
_MARCA = "_fixture2030_instrumentado"


def envolver_operacion(original):
    """Devuelve un reemplazo de app.adapters.base.operacion que además registra la duración por base."""
    if getattr(original, _MARCA, False):
        return original

    @contextmanager
    def operacion(fuente, nombre, traducir):
        inicio = time.perf_counter()
        resultado = "ok"
        try:
            with original(fuente, nombre, traducir):
                yield
        except BaseException:
            resultado = "error"
            raise
        finally:
            BASE_DURACION.labels(fuente, nombre, resultado).observe(time.perf_counter() - inicio)

    setattr(operacion, _MARCA, True)
    return operacion


def instrumentar_adaptadores() -> None:
    """Cada adaptador importó `operacion` por nombre, así que se reemplaza en cada módulo."""
    for nombre in ADAPTADORES:
        modulo = importlib.import_module(f"app.adapters.{nombre}")
        modulo.operacion = envolver_operacion(modulo.operacion)


def instrumentar_comentarios() -> None:
    from app.services.comentarios import ComentariosService

    original = ComentariosService.crear
    if getattr(original, _MARCA, False):
        return

    @wraps(original)
    def crear(self, partido_id, clave, datos):
        comentario, creado = original(self, partido_id, clave, datos)
        if creado:
            COMENTARIOS_CREADOS.labels(datos["pais"]).inc()
        return comentario, creado

    setattr(crear, _MARCA, True)
    ComentariosService.crear = crear


class ColectorDisponibilidad:
    """Publica 1/0 por base haciendo el mismo ping que GET /health, en paralelo y con tiempo límite propio.

    Una base colgada no puede demorar /metrics más que `limite_segundos`: si no respondió a tiempo cuenta como 0.
    Así la recolección de la API no pasa el scrape_timeout de Prometheus justo cuando una base se cae.
    """

    def __init__(self, adaptadores_factory, limite_segundos: float = 2.0):
        self._factory = adaptadores_factory
        self._limite = limite_segundos

    def collect(self):
        familia = GaugeMetricFamily(
            "fixture2030_dependencia_disponible",
            "1 si la base respondió el ping dentro del tiempo límite en esta recolección, 0 si no.",
            labels=["fuente"],
        )
        disponibles = {}
        try:
            adaptadores = self._factory()
        except Exception:
            adaptadores = {}
        if adaptadores:
            pool = ThreadPoolExecutor(max_workers=len(adaptadores))
            futuros = {pool.submit(a.ping): nombre for nombre, a in adaptadores.items()}
            terminados, _ = wait(futuros, timeout=self._limite)
            for futuro in terminados:
                disponibles[futuros[futuro]] = futuro.exception() is None
            # No se espera a los pings colgados: terminan solos al vencer el timeout del driver.
            pool.shutdown(wait=False)
        for fuente in sorted(set(FUENTES) | set(adaptadores)):
            familia.add_metric([fuente], 1.0 if disponibles.get(fuente) else 0.0)
        yield familia


async def middleware_http(request, call_next):
    if request.url.path == "/metrics":
        return await call_next(request)
    inicio = time.perf_counter()
    codigo = 500
    try:
        respuesta = await call_next(request)
        codigo = respuesta.status_code
        return respuesta
    finally:
        # La ruta se resuelve dentro de call_next; sin ruta (404 de FastAPI) se agrupa para no crear una serie por URL.
        ruta = request.scope.get("route")
        endpoint = getattr(ruta, "path", None) or "sin_ruta"
        HTTP_PEDIDOS.labels(endpoint, request.method, str(codigo)).inc()
        HTTP_DURACION.labels(endpoint, request.method).observe(time.perf_counter() - inicio)
