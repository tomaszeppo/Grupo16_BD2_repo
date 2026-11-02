# Inventario de componentes

Qué se monitorea de cada parte de la plataforma y cómo. La columna "Mecanismo" separa lo que **medimos nosotros desde la API**, lo que viene de un **exportador** y lo que queda **propuesto** sin implementar. Una base figura como monitoreada solo si hay una métrica que lo respalda en `evidencia/`.

## Componentes de la plataforma

| Componente | Modelo | Función en el Fixture | Acceso | Mecanismo de monitoreo | Métricas seleccionadas | Riesgo que se busca ver | Limitaciones |
|---|---|---|---|---|---|---|---|
| API integrada (instrumentada) | — (FastAPI) | Única puerta de entrada: cada endpoint consulta solo la base que corresponde | `127.0.0.1:8001`, `/metrics` | **Medido** por la propia API (`job="api"`) | `fixture2030_http_requests_total`, `fixture2030_http_request_duration_seconds`, CPU y memoria del proceso | Errores 5xx, respuestas lentas, saturación del proceso | Una sola instancia; no mide la red entre el usuario y la API |
| MongoDB | Documental | Fichas de equipos y planteles (`/equipos`) | `mongodb:27017` (red interna) | **Medido** desde la API (disponibilidad y duración) + **exportador** de Percona (`job="mongodb"`) | `fixture2030_dependencia_disponible{fuente="mongodb"}`, duración p95, `mongodb_op_counters_total`, `mongodb_connections` | Base caída, lecturas lentas, conexiones agotadas | El exportador lee estadísticas del servidor, no de cada consulta |
| Neo4j | Grafo | Partidos, equipos, estadios y eventos (`/partidos`); valida el partido antes de cada comentario | `neo4j:7687` | **Medido** desde la API | disponibilidad, duración p95 por operación | Que una demora en Neo4j frene la creación de comentarios | Sin exportador: el endpoint de métricas de Neo4j es de la edición Enterprise y usamos `neo4j:5` Community. Métricas internas (caché de páginas, transacciones): **propuesto** |
| Cassandra | Columnar (tabla ancha) | Comentarios por partido, país y ventana de 30 min | `cassandra:9042` | **Medido** desde la API | disponibilidad, duración p95, `fixture2030_comentarios_creados_total{pais}` | Escrituras lentas durante un pico después de un gol | Sin exportador: Cassandra publica por JMX y no sumamos el agente. Latencia interna, compactaciones y estado de nodos: **propuesto** |
| Redis | Clave-valor en memoria | Sesiones con TTL de 30 min (`/sesiones`) | `redis:6379` | **Medido** desde la API + **exportador** `redis_exporter` (`job="redis"`) | disponibilidad, duración p95, `redis_memory_used_bytes` frente a `redis_memory_max_bytes`, comandos/s, claves vencidas y expulsadas | Caída (usuarios sin sesión), memoria llena (expulsión de sesiones) | Instancia única; no hay réplica que monitorear |
| InfluxDB 3 Core | Series temporales | Estadísticas de partido por ventana (`/estadisticas`) | `influxdb:8181` | **Medido** desde la API | disponibilidad, duración p95 | Consultas lentas sobre ventanas grandes | No configuramos su endpoint de métricas internas: **propuesto** |
| IRIS | Objetos (multimodelo) | Partido como entidad compleja y su máquina de estados (`/detalle`, `/estado`) | `iris:1972` | **Medido** desde la API | disponibilidad, duración p95 | Cambios de estado rechazados o lentos | IRIS tiene un endpoint de métricas propio (`/api/monitor/metrics`) que no habilitamos: **propuesto** |

## Componentes del monitoreo

| Componente | Función | Acceso | Cómo se vigila | Riesgo |
|---|---|---|---|---|
| Prometheus v3.5.0 | Recolecta cada 5 s, guarda series, evalúa alertas | `127.0.0.1:9090` | Se recolecta a sí mismo (`job="prometheus"`) | Si cae, el panel queda sin datos nuevos y no hay alertas |
| Grafana 12.1.1 | Panel "Fixture 2030 — Plataforma" | `127.0.0.1:3000` | Visual: si no carga, se consulta Prometheus directo | No guarda datos; perderlo no pierde métricas |
| redis_exporter v1.75.0 | Traduce `INFO` de Redis a métricas | interno `:9121` | `up{job="redis"}` | Si cae, se pierden las métricas internas de Redis, no la disponibilidad medida desde la API |
| mongodb_exporter 0.44.0 | Traduce `serverStatus` de MongoDB | interno `:9216` | `up{job="mongodb"}` | Igual que el anterior, para MongoDB |
| grafana-image-renderer v4.0.10 | Solo para guardar capturas de paneles como evidencia | interno `:8081` | No se monitorea | Sin él no hay capturas automáticas |

## Cómo se mide la disponibilidad de las seis bases

Cada vez que Prometheus lee `/metrics` (cada 5 s), la API hace a las seis bases, en paralelo, el mismo ping que usa `GET /health`, y publica `fixture2030_dependencia_disponible{fuente}` con 1 (respondió) o 0 (no respondió). Es una medición directa desde el punto de vista de la API. Cada ping tiene 2 s como máximo: una base que no contesta en ese tiempo cuenta como caída, y así la recolección nunca se acerca al `scrape_timeout` de 4 s. Lo cambiamos después de la primera prueba de falla, donde la recolección llegó a 3,99 s ([limitaciones](limitaciones_y_evidencia.md#corrección-que-salió-de-la-primera-corrida)). El costo es una consulta mínima por base cada 5 s.

## Cómo validar que un destino está UP

1. `& .\scripts\verificar_targets.ps1`: todos los destinos tienen que figurar `up` y las seis bases con 1.
2. O en el navegador: http://127.0.0.1:9090/targets, cada job en verde con "Last scrape" de hace menos de 5 s.
3. En Grafana, el panel "Destinos de Prometheus (up)" muestra un recuadro verde por job.

Evidencia de la primera verificación: [`evidencia/prometheus_targets_20261030_215545.json`](../evidencia/prometheus_targets_20261030_215545.json) (4 destinos UP, seis bases en 1).

## Si un destino está DOWN

| Job | Primero mirar | Causa habitual |
|---|---|---|
| `api` | `docker logs fixture2030-monitoreo-api_metricas-1` | Falta el `.env` del Hito 10 o las bases no están levantadas (la API no arranca sin la red `fixture2030_net`) |
| `redis` | `docker logs fixture2030-monitoreo-redis_exporter-1` | Contraseña de Redis cambiada en el `.env` del Hito 10 sin recrear el exportador |
| `mongodb` | `docker logs fixture2030-monitoreo-mongodb_exporter-1` | `docker compose` ejecutado sin los dos `--env-file` (el exportador no recibe la contraseña) |
| `prometheus` | `docker logs fixture2030-monitoreo-prometheus-1` | Error en `prometheus.yml` o en las reglas: validar con `promtool` (ver [métricas y consultas](metricas_y_consultas.md#validar-la-configuración)) |

En todos los casos, la columna "Error" de http://127.0.0.1:9090/targets dice qué falló en la última recolección: conexión rechazada, timeout o respuesta inválida. Si el destino está UP pero una base aparece en 0, el problema está en la base, no en el monitoreo: `docker ps` en la carpeta del Hito 10 y los logs de ese contenedor.
