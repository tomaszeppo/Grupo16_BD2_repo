# Correcciones del Hito 10

## Devolución del profesor

> La entrega está muy completa y bien evidenciada, pero deben reducir la reingeniería de los datos previos: para integrar la API crean instancias nuevas de las seis bases, cambian identificadores de partido y agregan una tabla Cassandra de idempotencia. Eso dificulta demostrar integración real de los hitos existentes. Conviene consumir los modelos previos tal como fueron entregados y limitar los cambios al mínimo necesario para exponerlos por API.

## A tener en cuenta

Los tres puntos señalados están documentados en [cambios_en_las_bases.md](cambios_en_las_bases.md):

| Punto observado | Qué hace hoy el hito | Dirección de la corrección |
|---|---|---|
| Instancias nuevas de las seis bases | Compose propio (`fixture2030-api`) con volúmenes y datos de ejemplo propios | Conectar la API a las bases de los Hitos 4 a 9 con sus datos tal como se entregaron |
| Identificadores de partido cambiados | Se unificó el partido como `P-01`…`P-08` en Neo4j, Cassandra, InfluxDB e IRIS | Usar los identificadores originales de cada hito (`P001`, `ARG-FRA`, `M001`, etc.) y resolver la correspondencia en la API si hace falta |
| Tabla Cassandra `comentarios_idempotencia` | Tabla nueva para que los reintentos no dupliquen comentarios al cruzar el borde de la ventana | Quitarla y usar solo las tablas del Hito 6; documentar el caso límite de duplicación |

Criterio general: consumir los modelos previos como fueron entregados y limitar los cambios al mínimo necesario para exponerlos por API.
