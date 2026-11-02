# Grafana

El datasource y el panel se cargan solos al iniciar el contenedor, desde estos archivos. No hay que configurar nada a mano.

- [`provisioning/datasources/prometheus.yml`](provisioning/datasources/prometheus.yml): Prometheus como fuente por defecto (uid `prometheus-fixture`).
- [`provisioning/dashboards/fixture2030.yml`](provisioning/dashboards/fixture2030.yml): carga los paneles de `dashboards/` en la carpeta "Fixture 2030". No se pueden editar desde la interfaz: el panel válido es el del repositorio.
- [`dashboards/fixture2030.json`](dashboards/fixture2030.json): panel "Fixture 2030 — Plataforma" (uid `fixture2030`).

Acceso: http://127.0.0.1:3000, usuario `admin`, contraseña de `GRAFANA_ADMIN_PASSWORD` en el `.env` del hito. Rango por defecto: últimos 30 minutos, actualización cada 5 s. Cada panel tiene una descripción (icono "i") que dice qué mide, de dónde sale y qué ventana usa.

## Paneles

| Id | Panel | Unidad | Para qué |
|---|---|---|---|
| 1 | Bases: ¿responden a la API? | estado | Vista rápida: verde o rojo por base |
| 12 | Destinos de Prometheus (up) | estado | Si un job cae, sus paneles quedan sin datos |
| 15 | Disponibilidad de cada base en el tiempo | estado | Cuándo empezó y terminó una falla |
| 2 | Pedidos por segundo, por endpoint | pedidos/s | Volumen de la API |
| 3 | Respuestas no exitosas por código | pedidos/s | 503 (base caída), 504 (tiempo máximo), 409, 4xx |
| 9 | Proporción de respuestas 5xx | % | Con la línea del umbral de la alerta (5%) |
| 4 | Duración p95 y p99 por endpoint | s | Tiempo de respuesta medido en la API |
| 5 | Comentarios nuevos por segundo, por país | comentarios/s | El pico después de un gol, por audiencia |
| 6 | p99 de crear comentario | s | Con la línea del umbral experimental (500 ms) |
| 7 | Duración p95 de cada base, vista desde la API | s | Comparación entre las seis bases con la misma medida |
| 10 | MongoDB: operaciones por segundo | ops/s | Exportador |
| 8 | Redis: memoria usada frente al límite | bytes | Exportador; si llega al límite, se expulsan sesiones |
| 11 | Redis: comandos, claves vencidas y expulsadas | ops/s | Exportador |
| 13 | API: CPU del proceso | fracción de núcleo | Recursos de la API (límite del contenedor: 1 núcleo) |
| 14 | API: memoria del proceso | bytes | Recursos de la API (límite: 512 MiB) |

Los percentiles y las tasas usan una ventana de 1 minuto: con la recolección cada 5 s son unas 12 muestras. Una ventana más corta saltaría más; una más larga suavizaría los picos de pocos segundos. Las consultas de cada panel están explicadas en [métricas y consultas](../docs/metricas_y_consultas.md).
