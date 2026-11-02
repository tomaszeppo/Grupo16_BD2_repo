# Evidencia

Corrida final del 30/10/2026, de 22:25 a 22:31 hora de Argentina (01:25 a 01:31 UTC del 31/10), sobre el commit `c7eed72` con los cambios de este hito todavía sin commitear. Notebook con Windows y Docker Desktop, un nodo por base.

| Archivo | Qué registra |
|---|---|
| [`prometheus_targets_20261030_215545.json`](prometheus_targets_20261030_215545.json) | Los 4 destinos en UP y las seis bases en 1, al dejar el monitoreo andando |
| [`resultados_sin_secretos/pico_comentarios_20261030_222612_resumen.json`](resultados_sin_secretos/pico_comentarios_20261030_222612_resumen.json) | Pico de 3.000 comentarios: tasa real, respuestas, reparto por país y verificación en Cassandra |
| [`resultados_sin_secretos/pico_comentarios_20261030_222612.jsonl`](resultados_sin_secretos/pico_comentarios_20261030_222612.jsonl) | Cada uno de los 3.000 pedidos: país, código, id del comentario, ventana y duración en el cliente |
| [`estado_partido_20261030_222740.json`](estado_partido_20261030_222740.json) | Transiciones de `P-05` en IRIS, incluido el rechazo de volver atrás (409) |
| [`prueba_de_falla_20261030_223027.json`](prueba_de_falla_20261030_223027.json) | Caída de Redis: estado antes, a los 15 s, al final y después; alertas; tráfico de fondo |
| [`dashboards/demo_20261030_223042_todo/`](dashboards/demo_20261030_223042_todo) | Captura de los 15 paneles de Grafana entre 22:25:42 y 22:30:42, y `series_prometheus.json` con las series crudas de las consultas principales |
| [`recoleccion_api_falla_preliminar.json`](recoleccion_api_falla_preliminar.json) | Duración de cada recolección de la API durante la primera prueba de falla (hasta 3,99 s): motivó la corrección del colector de disponibilidad |
| [`corridas_previas/`](corridas_previas/README.md) | Las dos corridas anteriores y por qué no son la evidencia final |

## Cifras calculadas a partir de estos archivos

- **Percentiles del cliente en el pico** (p50 11,85 ms, p95 13,93 ms, p99 20,91 ms, máximo 180,98 ms): del campo `duracion_ms` de los 3.000 pedidos del `.jsonl`, por rango más cercano.
- **Máximos por base y por país:** de `series_prometheus.json`, tomando el mayor valor de cada serie en la ventana.

## Para leer las capturas

- El primer minuto de la ventana (22:25:42 a 22:26:30) muestra a Redis con duraciones cercanas a 5 s. No es parte de la demo: a las 22:24 detuvimos Redis unos segundos a mano para medir cuánto tardaba `/metrics` con el colector corregido, y la ventana de 1 minuto de las consultas arrastra ese efecto.
- Las sesiones se sembraron de nuevo a las 22:25, justo antes de la corrida, porque vencen a los 30 minutos sin uso.

## Qué no se versiona

Nada de esta carpeta contiene contraseñas, tokens ni URI con credenciales. Los JSON tienen ids de comentarios sintéticos, códigos de respuesta y `request_id` de pedidos de laboratorio. Las capturas muestran solo los paneles, sin la barra de usuario de Grafana.
