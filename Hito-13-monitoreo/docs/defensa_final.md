# Defensa final: cómo vamos a mostrar el sistema

La defensa es sobre las bases y las decisiones de arquitectura. Swagger, Grafana y el panel técnico son el medio para mostrar que lo que explicamos es lo que está construido. No usamos diapositivas: la explicación va sobre el repositorio, Swagger (http://127.0.0.1:8001/docs), el panel técnico (http://127.0.0.1:8085) y Grafana. Las tres demos se pueden correr juntas con el botón "Simular situaciones" del panel técnico (ver el [README](../README.md#repetir-la-demostración)); la vista del hincha (http://127.0.0.1:8086) sirve para mostrar qué base hay detrás de cada pantalla.

## Orden de la exposición (20 minutos, 3 integrantes)

| Bloque | Qué mostramos | Con qué |
|---|---|---|
| Problema y decisión general | Qué pide el Fixture 2030 y por qué no una sola base | [Decisiones de arquitectura](decisiones_de_arquitectura.md), primera sección |
| Recorrido por las bases | Qué guarda cada una y por qué; cómo pasó del diseño del Hito 3 a lo construido | Swagger: un pedido por base (equipo en MongoDB, partido en Neo4j, sesión en Redis, estadísticas en InfluxDB, detalle en IRIS) |
| Distribución y consistencia | Partición, réplicas propuestas y qué pasa si se cae cada una | Decisiones de arquitectura, tablas por base |
| Demo 1: pico de comentarios | 3.000 comentarios de cuatro países, verificados en Cassandra sin faltantes ni duplicados | Script de la prueba controlada + Grafana (pedidos, comentarios por país, duración por base) |
| Demo 2: estado del partido | Transición validada en IRIS, incluido el rechazo de volver atrás | Swagger o script, momento "estado" |
| Demo 3: falla de Redis | Redis cae, las sesiones dan 503, el resto sigue andando; Grafana lo muestra y la alerta se dispara; Redis vuelve | Script, momento "falla" + panel de disponibilidad en el tiempo + http://127.0.0.1:9090/alerts |
| Cierre | Qué medimos y qué no, la mejora que proponemos y qué haríamos en el TP final | [Limitaciones y evidencia](limitaciones_y_evidencia.md), [proyecto final planteado](proyecto_final_planteado.md) |

Los comandos de la demo son los de la sección "Repetir la demostración" del [README](../README.md).

## Si algo falla durante la defensa

La demo depende de Docker y de la notebook. Si un servicio no levanta o la conexión falla, mostramos la evidencia ya guardada de la misma prueba: las 15 capturas del panel en [`evidencia/dashboards/demo_20261030_223042_todo/`](../evidencia/dashboards/demo_20261030_223042_todo), los registros JSON de la prueba de falla y del cambio de estado, y el resumen del pico de comentarios. Así se puede contar la misma historia sin depender del entorno en vivo.
