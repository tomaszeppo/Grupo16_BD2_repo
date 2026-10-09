# Decisiones de diseño — Módulo de grafos (Hito 5)

## Problema relacional

Del Hito 1 en adelante veníamos arrastrando preguntas que un documento aislado no responde bien: quién enfrenta a quién, qué jugador convirtió un gol y en qué partido, qué equipos terminan compartiendo estadio y fecha aunque nunca se crucen en la cancha. Esas son justo las preguntas que un grafo resuelve recorriendo relaciones en vez de haciendo cruces manuales entre colecciones.

## Por qué Neo4j y no ampliar el módulo documental

En el Hito 2 ya habíamos elegido Documental (MongoDB) para Equipos, Jugadores, Partidos y Eventos. Ese módulo sigue en pie (Hito 4) y sigue siendo el lugar correcto para los datos completos de cada entidad. Lo que agrega este hito no es duplicar esos datos, sino la capa de relaciones entre ellos: quién juega contra quién, dónde, y quién protagonizó qué evento. Eso es exactamente lo que Mongo no resuelve bien sin *lookups* manuales, y lo que un grafo resuelve de forma nativa.

## Consistencia de identificadores con el Hito 4

Los códigos de equipo (`ARG`, `BRA`, ...) y de jugador (`ARG-10`, ...) son los mismos que se generaron en el módulo de Mongo, para poder reconocer la misma entidad en los dos módulos (RF5). No hay ninguna conexión técnica entre las dos bases — es solo que ambas usan el mismo criterio de identificación.

## Por qué el modelo quedó tan liviano

Al principio el modelo tenía más propiedades por nodo (nombre, fecha de nacimiento, capacidad del estadio, etc.). Se sacó todo lo que no participaba de ninguna relación ni era candidato a convertirse en una: ese tipo de dato descriptivo ya vive en el módulo documental, y cargarlo dos veces en dos tecnologías distintas no le suma nada al propósito de este módulo, que es representar vínculos, no repetir el catálogo completo. El detalle de qué se sacó de cada nodo y por qué está en `modelo_grafo.md`.

## Correspondencia con la Clase 5

Los nombres y direcciones de `PERTENECE_A` y `DISPUTA` copian exactamente los que usa la práctica guiada de la Clase 5 (`(jugador)-[:PERTENECE_A]->(equipo)`, `(partido)-[:DISPUTA]->(equipo)`), para no inventar una convención propia donde la cátedra ya definió una. `OCURRE_EN` y `PROTAGONISTA_DE` sí son nombres propios, porque la práctica de la clase no llega a modelar eventos deportivos.

## Datos cargados

64 equipos, 1.536 jugadores (24 por equipo) y 10 sedes (estadios reales del fixture de prueba) se generan por completo desde Cypher, sin archivos externos — todo con `MERGE`, así que correr la carga de nuevo no duplica nada (RNF4). La fase y la fecha de cada partido y el tipo y el minuto de cada evento se escriben con `ON CREATE SET`: si se corrigen después con el CRUD, una recarga no los vuelve al valor de la carga. Se comprobó cargando dos veces (mismos conteos de nodos y relaciones) y recargando luego del CRUD (`docs/evidencia/`). Los partidos son los 32 del fixture de la fase de grupos (con sus enfrentamientos, fechas y estadios), con resultado simulado marcado como tal en `origenResultado`, porque el fixture de prueba no tiene resultados oficiales. Los eventos son una muestra menor todavía: goles y tarjetas de ejemplo en los primeros 5 partidos, alcanza para probar los recorridos pedidos sin necesitar los 127 partidos reales del torneo.

## Consulta de análisis (RF9)

Se eligió un recorrido de camino variable (`-[*1..4]-`) en vez de un algoritmo de Graph Data Science (PageRank, Dijkstra) porque la Clase 5 no llega a instalar el plugin de GDS en la práctica guiada — solo lo menciona en la teoría. El camino que se encuentra (Argentina y Escocia (`SCO`), sin partido entre sí, conectados en 4 saltos por compartir el estadio `EST001` en partidos distintos) muestra información que no es evidente mirando los partidos como documentos aislados: dos selecciones pueden terminar compartiendo estadio y ventana de fechas sin jugar entre sí, algo relevante por ejemplo para planificar logística o seguridad del operativo.

## Qué no llegamos a resolver en este hito

- La muestra de eventos es chica (10 eventos en 5 partidos); no alcanza para un análisis de centralidad interesante (por ejemplo, "qué jugador participó de más eventos") con estos datos.
- No se probó qué pasa si dos partidos de la muestra terminan compartiendo la misma fecha y sede a la vez (colisión de programación) — quedaría para un hito de validación de reglas de negocio.
