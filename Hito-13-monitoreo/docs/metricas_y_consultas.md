# Métricas y consultas

## Configuración de Prometheus

| Punto | Valor | Por qué |
|---|---|---|
| Intervalo de recolección | 5 s (`scrape_interval`), evaluación de reglas cada 5 s | Los picos de la demo duran segundos. En el Hito 12, las corridas de 4 a 11 s habrían quedado con uno o ningún punto a 15 s. Cuesta el triple de muestras que con 15 s |
| Timeout de recolección | 4 s | El colector de disponibilidad espera como máximo 2 s a cada base, así que la recolección de la API termina en unos 2 s aunque una base esté caída (medido: 2,03 s durante la caída de Redis) |
| Retención | 15 días (`--storage.tsdb.retention.time=15d`) | Alcanza para el laboratorio y la defensa. Para el torneo completo habría que guardar más, o resumir en series por minuto |
| Archivo | [`prometheus.yml`](../prometheus.yml), reglas en [`prometheus/reglas-o-alertas.yml`](../prometheus/reglas-o-alertas.yml) | |

### Jobs, destinos y etiquetas

| Job | Destino | Componente observado | Etiquetas fijas | Tipo |
|---|---|---|---|---|
| `api` | `api_metricas:8001/metrics` | API integrada y, a través de ella, las seis bases | `componente=api-fixture`, `tipo=aplicacion` | aplicación |
| `redis` | `redis_exporter:9121` | Redis (sesiones) | `componente=redis`, `tipo=infraestructura` | infraestructura |
| `mongodb` | `mongodb_exporter:9216` | MongoDB (equipos y jugadores) | `componente=mongodb`, `tipo=infraestructura` | infraestructura |
| `prometheus` | `localhost:9090` | El propio Prometheus | `componente=prometheus`, `tipo=monitoreo` | monitoreo |

Cómo validar un destino UP y qué hacer si está DOWN: [inventario de componentes](inventario_de_componentes.md#cómo-validar-que-un-destino-está-up).

### Validar la configuración

```powershell
docker run --rm -v "${PWD}\prometheus.yml:/etc/prometheus/prometheus.yml:ro" -v "${PWD}\prometheus:/etc/prometheus/reglas:ro" --entrypoint promtool prom/prometheus:v3.5.0 check config /etc/prometheus/prometheus.yml
```

Resultado esperado: `SUCCESS` para el archivo y `SUCCESS: 4 rules found` para las reglas.

## Qué se mide directo, qué viene de un exportador y qué está propuesto

| Origen | Métricas | Cómo se obtienen |
|---|---|---|
| **Medido en la API** (aplicación) | `fixture2030_http_requests_total{endpoint, metodo, codigo}`, `fixture2030_http_request_duration_seconds{endpoint, metodo}`, `fixture2030_dependencia_duracion_seconds{fuente, operacion, resultado}`, `fixture2030_comentarios_creados_total{pais}`, `fixture2030_dependencia_disponible{fuente}` | Código propio en [`api_instrumentada/`](../api_instrumentada). Envuelve funciones del Hito 10 al arrancar, sin editarlas |
| **Medido en la API** (infraestructura del proceso) | `process_cpu_seconds_total`, `process_resident_memory_bytes` con `job="api"` | Colector de proceso de `prometheus_client` (lee `/proc` dentro del contenedor) |
| **Exportador** | `redis_*` (memoria, límite, comandos, claves vencidas y expulsadas), `mongodb_*` (operaciones por tipo, conexiones) | `redis_exporter` y `mongodb_exporter` |
| **Propuesto, no implementado** | Métricas internas de Cassandra (JMX), Neo4j (edición Enterprise), InfluxDB e IRIS; CPU y memoria por contenedor (cAdvisor) | Ver [limitaciones](limitaciones_y_evidencia.md) |
| **Inferido** | Que un 503 en `/sesiones` se debe a Redis | Se cruza la subida de 503 con `fixture2030_dependencia_disponible{fuente="redis"} == 0` en el mismo período |

### Cómo se instrumentó sin tocar el Hito 10

- **Pedidos HTTP:** un middleware registrado después del del Hito 10, así que también cuenta los 504 que genera su tiempo máximo. La etiqueta `endpoint` es la **plantilla** de la ruta (`/partidos/{partido_id}/comentarios`), nunca la URL real. Si la URL no corresponde a ninguna ruta, se agrupa en `sin_ruta`. Así no se crea una serie por partido o por intento raro.
- **Duración por base:** cada adaptador del Hito 10 ya pasa por `operacion(fuente, nombre, traducir)`. Al arrancar, ese nombre se reemplaza en cada módulo de adaptador por una versión que llama a la original y además mide. Si la operación falla, se registra con `resultado="error"` y la excepción sigue su camino como antes.
- **Comentarios por país:** se envuelve `ComentariosService.crear`. Solo suma cuando el comentario es nuevo; un reintento con la misma `Idempotency-Key` devuelve `creado=False` y no cuenta.
- **Etiquetas prohibidas:** usuario, partido, `request_id`, `Idempotency-Key`. Con 3 millones de usuarios, una etiqueta por usuario crearía millones de series por métrica.

Los tests de [`tests/test_instrumentacion.py`](../tests/test_instrumentacion.py) cubren estos casos sin bases reales.

## Consultas PromQL explicadas

### 1. Pedidos por segundo, por endpoint

```promql
sum by (endpoint, metodo) (rate(fixture2030_http_requests_total[1m]))
```

- **Qué mide:** cuántos pedidos atiende la API por segundo en cada endpoint.
- **Unidad:** pedidos por segundo (`req/s`).
- **Período:** promedio del último minuto (`[1m]`, unas 12 muestras a 5 s).
- **Cómo leerlo:** en el pico de la demo, `POST /partidos/{partido_id}/comentarios` llegó a unos 50 pedidos/s, que es la tasa que configuramos en el generador. Con una ventana de 1 minuto, una ráfaga de 60 s se ve como una subida en rampa, no como un escalón.

### 2. Proporción de errores del servidor

```promql
(sum(rate(fixture2030_http_requests_total{codigo=~"5.."}[1m])) or vector(0))
  / sum(rate(fixture2030_http_requests_total[1m]))
```

- **Qué mide:** qué fracción de los pedidos termina en 5xx.
- **Unidad:** proporción (se muestra en %).
- **Período:** último minuto.
- **Umbral:** 5% sostenido 1 minuto dispara `ErroresServidorAltos`.
- `or vector(0)` evita que el panel quede vacío cuando no hubo ningún 5xx.

### 3. p99 de crear un comentario

```promql
histogram_quantile(0.99, sum by (le) (
  rate(fixture2030_http_request_duration_seconds_bucket{endpoint="/partidos/{partido_id}/comentarios", metodo="POST"}[1m])))
```

- **Qué mide:** el tiempo por debajo del cual quedan el 99% de las altas de comentarios.
- **Unidad:** segundos.
- **Período:** último minuto.
- **Precisión:** se calcula desde el histograma, sumando los rangos (5, 10, 25, 50, 100, 250, 500 ms; 1, 2,5, 5 s) antes de calcular el percentil. Así se puede sumar entre instancias, pero el resultado se interpola dentro del rango. Con pocos pedidos en el minuto, un solo pedido lento empuja el valor hacia el borde superior de su rango.

### 4. Duración p95 de cada base vista desde la API

```promql
histogram_quantile(0.95, sum by (le, fuente) (rate(fixture2030_dependencia_duracion_seconds_bucket[1m])))
```

- **Qué mide:** el tiempo de cada operación del adaptador contra cada base, con la misma vara para las seis.
- **Unidad:** segundos.
- **Período:** último minuto.
- **Para qué sirve:** responde "¿el problema está en la API o en la base?". Si sube la duración HTTP y una base también sube, la demora está en esa base; si sube la duración HTTP y ninguna base sube, está en la API.

### 5. Comentarios nuevos por segundo, por país

```promql
sum by (pais) (rate(fixture2030_comentarios_creados_total[1m]))
```

- **Unidad:** comentarios por segundo.
- **Período:** último minuto.
- **Cómo leerlo:** en la demo, cada uno de los cuatro países llegó a unos 12,5/s: 50/s repartidos en cuatro, menos lo que suaviza la ventana.

## Panel de Grafana

Descripción de cada panel y cómo se carga: [grafana/README.md](../grafana/README.md).
