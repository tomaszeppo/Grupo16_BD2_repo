# Alertas y umbrales

Las cuatro reglas están en [`prometheus/reglas-o-alertas.yml`](../prometheus/reglas-o-alertas.yml) y se ven en http://127.0.0.1:9090/alerts. No configuramos Alertmanager: en el laboratorio alcanza con ver el estado de cada alerta en Prometheus. Para el torneo, Alertmanager se encargaría de avisar por correo o chat y de agrupar avisos repetidos.

Criterio general: alertamos por lo que siente el usuario (base caída, errores, lentitud) o por quedarnos ciegos. Lo que no implica una decisión, como "CPU alta" a secas, queda en el panel para diagnosticar, no como alerta.

Quién atiende cada alerta: en el torneo, la **guardia de plataforma** (quien opera la API y el despliegue) o la **guardia de datos** (quien administra las bases). En el laboratorio somos los tres integrantes.

## BaseNoDisponible

| Campo | Valor |
|---|---|
| Métrica evaluada | `fixture2030_dependencia_disponible` (ping de la API a cada base, cada 5 s) |
| Condición | `== 0` para alguna `fuente` |
| Duración mínima | 30 s (6 recolecciones seguidas sin respuesta) |
| Severidad | crítica |
| Componente afectado | La base indicada en la etiqueta `fuente` |
| Impacto en el Fixture | Los endpoints de esa base responden 503. Si es Redis, nadie puede validar su sesión; si es Cassandra, no se puede comentar; si es Neo4j, tampoco se puede comentar, porque el alta valida el partido ahí. El resto sigue funcionando |
| Acción | Guardia de datos: `docker ps` y logs del contenedor de esa base; comprobar la red `fixture2030_net`. Mientras tanto, la API ya responde degradada con 503 y no hay que tocarla |
| Por qué el umbral | Razonado. 30 s evitan avisar por un reinicio rápido o una recolección perdida, y es poco tiempo frente a un partido de 90 minutos. En la prueba de falla pasó a "pendiente" a los 15 s de detener Redis y a "disparada" antes de volver a iniciarlo ([evidencia](../evidencia/prueba_de_falla_20261030_223027.json)) |

## DestinoCaido

| Campo | Valor |
|---|---|
| Métrica evaluada | `up` (la genera Prometheus por cada destino) |
| Condición | `== 0` |
| Duración mínima | 30 s |
| Severidad | alta |
| Componente afectado | El job indicado: `api`, `redis`, `mongodb` o `prometheus` |
| Impacto en el Fixture | No afecta a los usuarios directamente, pero el monitoreo queda ciego en esa parte. Si el job es `api`, puede ser que la API entera esté caída: mirar también `BaseNoDisponible` y los 5xx |
| Acción | Guardia de plataforma: leer la columna de error en http://127.0.0.1:9090/targets y seguir la tabla de [qué hacer si un destino está DOWN](inventario_de_componentes.md#si-un-destino-está-down) |
| Por qué el umbral | Razonado, con el mismo criterio que la anterior. Monitoreo ciego en plena final es un riesgo en sí mismo. En la prueba de falla, el job `redis` también quedó DOWN (el exportador no llega a Redis dentro del timeout) y la alerta pasó a pendiente junto con `BaseNoDisponible`: dos caminos distintos confirmaron la misma caída ([evidencia](../evidencia/prueba_de_falla_20261030_223027.json)) |

## ErroresServidorAltos

| Campo | Valor |
|---|---|
| Métrica evaluada | `fixture2030_http_requests_total` por código |
| Condición | Más del 5% de los pedidos del último minuto terminan en 5xx |
| Duración mínima | 1 min |
| Severidad | alta |
| Componente afectado | API, o la base que esté detrás (se distingue con el panel de errores por código y el de duración por base) |
| Impacto en el Fixture | 1 de cada 20 pedidos falla: comentarios que no se guardan, sesiones que no se validan, partidos que no cargan |
| Acción | Guardia de plataforma: ver qué código domina (503 = base caída, 504 = tiempo máximo excedido) y en qué endpoint; si es 503, pasar a guardia de datos con la base que marque `BaseNoDisponible` |
| Por qué el umbral | **Experimental.** Partimos del objetivo de disponibilidad del Hito 3 (99,99%), que para un minuto suelto es demasiado estricto y alertaría por cualquier error aislado. 5% sostenido un minuto separa una falla real de errores sueltos. En la prueba de falla quedó "pendiente" sin llegar a dispararse: los pedidos a Redis tardaban unos 5 s en devolver 503, así que hubo pocos errores por minuto frente al resto del tráfico (ver [limitaciones](limitaciones_y_evidencia.md#mejora-transversal-propuesta)) |

## LatenciaComentariosAlta

| Campo | Valor |
|---|---|
| Métrica evaluada | `fixture2030_http_request_duration_seconds` de `POST /partidos/{partido_id}/comentarios` |
| Condición | p99 del último minuto por encima de 500 ms |
| Duración mínima | 1 min |
| Severidad | media |
| Componente afectado | Alta de comentarios: Neo4j (valida el partido) y Cassandra (guarda) |
| Impacto en el Fixture | En el pico después de un gol, 1 de cada 100 comentarios tarda más de medio segundo en confirmarse |
| Acción | Guardia de datos: panel "Duración p95 de cada base" para ver si la demora es de Neo4j o de Cassandra. Si ninguna sube, revisar CPU y memoria de la API |
| Por qué el umbral | **Experimental.** El Hito 3 fija como objetivo menos de 100 ms para el p95 de las consultas críticas. Para el p99 tomamos 500 ms, que es el borde de un rango del histograma y deja margen sobre lo medido: en el pico de la demo, el cliente vio un p99 de 20,91 ms en los 3.000 comentarios (calculado del campo `duracion_ms` de [cada pedido](../evidencia/resultados_sin_secretos/pico_comentarios_20261030_222612.jsonl); ver [evidencia](../evidencia/README.md)). El p99 calculado por Prometheus llegó a 0,242 s, por la interpolación dentro del rango de 100 a 250 ms (ver [métricas](metricas_y_consultas.md#3-p99-de-crear-un-comentario)). Hay que ajustarlo con tráfico real |
