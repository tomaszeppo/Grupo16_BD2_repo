"""Métricas propias de la API. Las etiquetas son de cardinalidad baja: nunca usuario, partido ni request_id."""
from prometheus_client import CollectorRegistry, Counter, Histogram, ProcessCollector

REGISTRO = CollectorRegistry()
# CPU y memoria del proceso de la API (métricas de infraestructura del propio servicio; solo Linux).
PROCESO = ProcessCollector(registry=REGISTRO)

# Rangos en segundos: separan respuestas de pocos ms, las de cientos de ms y los timeouts del Hito 10.
RANGOS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5)

HTTP_PEDIDOS = Counter(
    "fixture2030_http_requests_total",
    "Pedidos HTTP atendidos por la API, por plantilla de ruta, método y código de respuesta.",
    ["endpoint", "metodo", "codigo"],
    registry=REGISTRO,
)
HTTP_DURACION = Histogram(
    "fixture2030_http_request_duration_seconds",
    "Duración de cada pedido HTTP medida en la API.",
    ["endpoint", "metodo"],
    buckets=RANGOS,
    registry=REGISTRO,
)
BASE_DURACION = Histogram(
    "fixture2030_dependencia_duracion_seconds",
    "Duración de cada operación de la API contra una base, medida desde la API.",
    ["fuente", "operacion", "resultado"],
    buckets=RANGOS,
    registry=REGISTRO,
)
COMENTARIOS_CREADOS = Counter(
    "fixture2030_comentarios_creados_total",
    "Comentarios nuevos guardados en Cassandra (los reintentos idempotentes no cuentan), por país de la audiencia.",
    ["pais"],
    registry=REGISTRO,
)
