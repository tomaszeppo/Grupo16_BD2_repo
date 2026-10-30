# Alternativa relacional del flujo de consulta

Para `GET /partidos/{id}`, una alternativa normalizada usa Equipo(codigo PK, nombre),
Estadio(id PK, nombre, ciudad), Partido(id PK, fecha, fase, estadio_id FK) y
Participacion(partido_id FK, equipo_codigo FK, rol, PK(partido_id,equipo_codigo)).
Resultado(partido_id PK/FK, ganador, perdedor, goles, origen) conserva los datos simulados.
El índice de Partido.id y el de Participacion(partido_id,equipo_codigo) acotan los joins.

Neo4j representa el acceso por relaciones `PARTICIPA_EN` y `SE_JUEGA_EN`; SQL usa joins
por claves. Ambos pueden conservar integridad e índices, con costos distintos según
patrón de acceso, volumen, profundidad y escrituras. Para este recorrido corto no hay
una ventaja de rendimiento demostrada de ninguno de los motores.

Esta comparación es conceptual. El esquema de Data Mart responde otra pregunta
(agregación de comentarios) y no equivale a medir el endpoint contra una base SQL.
Si se decide comparar tiempos, habrá que implementar ambas alternativas, cargar el mismo
dataset y controlar hardware, conexiones, caché, concurrencia y método de medición.

