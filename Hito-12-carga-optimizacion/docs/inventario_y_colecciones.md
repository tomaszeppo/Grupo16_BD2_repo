# Inventario de solo lectura

Captura UTC: 2026-10-29T22:45:37.960566+00:00. Commit de referencia: `f0b228ea6f747fd81b5dc89b30604a0f5ae6319a`.
Las cifras son una instantánea del laboratorio H10; no certifican la integración final H12.

| Motor | Lo observado |
|---|---|
| MongoDB | equipos: 16; jugadores: 80. codigo de equipo tiene índice único; jugadores por equipo/dorsal no tiene índice único compuesto en este laboratorio |
| Neo4j | 16 Equipo, 8 Estadio, 8 Partido (P-01..P-08), 5 Evento; índices consultados ONLINE |
| Cassandra | comentarios_por_partido_pais, comentarios_por_likes_partido_pais, comentarios_idempotencia. Muestra P-01/ARG/2030-06-15 18:30 UTC: 5 filas; no se contó todo el motor |
| Redis | 3 claves de sesión con TTL al capturar; cero claves f2030:h12:*. TTL cambia con el tiempo y una sesión puede expirar normalmente |
| InfluxDB | 4.800 puntos en estadisticas_partido; information_schema también devuelve tablas del sistema, no todas son tablas del negocio |
| IRIS | Fixture.Partido: 8; Fixture.Evento: 2 |

Detalle de lectura: `inventario_solo_lectura_20261029.json`. Contenedores: `contenedores_20261029.jsonl`.

## Colección Postman

Original: **38 requests**, métodos `{"GET": 28, "POST": 8, "DELETE": 2}`. Se revisó su contenido;
no se ejecutó completa porque incluye creación de comentarios, invalidación de sesiones y cambios
de estado IRIS. La copia preparada para H12 solo tiene 9 GET. No es un test de carga.

## Desajustes a resolver

- Los P001..P032 de H5 no pasan la validación actual de la API (`^P-\d{2,3}$`).
- La rama de correcciones cambia modelos y datos: no se puede cambiar de base/commit sin adaptar el consumo.
- El script de caché H7 menciona MongoDB como fuente; el flujo elegido H12 consulta partidos en Neo4j.
  Hay que corregir la autoridad al implementar, no tomar ese script como caché ya integrada.
- El laboratorio mantiene comentarios_idempotencia; la devolución del profesor pide reducir reingeniería.
  No se tocó esa tabla: la corrección debe diseñarse sin borrar datos.
- Solo hay 8 partidos en el laboratorio. Las 32 referencias de H5 son archivos preparados, no nuevos nodos cargados.

## Procedencia

Se revisaron README y decisiones de los módulos, cargas y modelos originales, API/adaptadores/validaciones,
OpenAPI, colección Postman, datos seed, observabilidad, evidencia histórica, mapa H12 y devoluciones del profesor.
La evidencia de H10/H11 preexistente no se atribuye a corridas de esta preparación.
