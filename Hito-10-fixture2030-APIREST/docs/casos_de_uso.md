# Casos de uso

Cada endpoint responde a un caso de uso del Fixture 2030. Consumidores: la app de hinchas, el back-office de operación y los analistas.

| # | Caso de uso | Consumidor | Entrada | Fuente | Salida | Si no existe | Si la dependencia cae | Tipo | Criterio de éxito |
|---|---|---|---|---|---|---|---|---|---|
| CU1 | Consultar una selección | App | `codigo` (3 letras) | MongoDB | `{codigo, nombre}` | 404 `NO_ENCONTRADO` | 503/504 | Lectura | 200 con el equipo |
| CU2 | Listar el plantel | App | `codigo`, `posicion?`, `limit`, `offset` | MongoDB | Página de jugadores y total | Equipo inexistente: 404. Sin coincidencias: 200 vacío | 503/504 | Lectura | 200 con `total` consistente |
| CU3 | Ver un partido | App | `id` (`P-NN`) | Neo4j | Fecha, fase, estadio, equipos, resultado simulado | 404 | 503/504 | Lectura | 200 con dos equipos y un estadio |
| CU4 | Ver los eventos de un partido | App | `id`, `limit` | Neo4j | Eventos ordenados por minuto | Partido inexistente: 404. Partido sin eventos: 200 vacío | 503/504 | Lectura | 200 ordenado por minuto |
| CU5 | Leer los comentarios de mi país | Hincha | `id`, `pais`, `ventana`, `limit`, `cursor?` | Cassandra | Página de comentarios (más recientes primero) y `next_cursor` | Partición vacía: 200 vacío | 503/504 | Lectura | 200 con orden `creado_en` descendente |
| CU6 | Comentar un partido | Hincha | `id`, cuerpo, cabecera `Idempotency-Key` | Cassandra + Neo4j | Comentario creado (201) o ya existente (200) | Partido inexistente: 404 | 503/504 | Creación | Un solo registro por clave aunque se reintente |
| CU7 | Consultar mi sesión | App | `usuario` | Redis | Sesión sin datos internos y TTL restante | 404 `SESION_NO_VIGENTE` | 503/504 | Lectura | 200 con TTL > 0 |
| CU8 | Cerrar sesión | App | `usuario` | Redis | 204 | 204 (idempotente) | 503/504 | Invalidación | Clave eliminada |
| CU9 | Ver estadísticas del partido | Analista / app | `id`, `desde`, `hasta`, `equipo?`, `agregacion` | InfluxDB | Puntos agregados o crudos, `truncado` | Sin puntos: 200 vacío | 503/504 | Lectura | 200 dentro de la ventana y del tope de puntos |
| CU10 | Ver el detalle del partido (objetos) | Back-office | `id` | IRIS | Partido con sus eventos hijos | 404 | 503/504 | Lectura | 200 con `estado` y `eventos` |
| CU11 | Avanzar el estado del partido | Operador | `id`, `estado` | IRIS | Partido actualizado | 404 | 503/504 | Actualización | Transición permitida o 409 |
| CU12 | Verificar la salud | Operación | — | Las seis | Estado por fuente | — | 503 con detalle por fuente | Lectura | 200 si todas responden |

## Por qué CU6 usa dos fuentes

Cassandra no puede verificar que el partido exista: su partición `(partido_id, pais, ventana)` acepta cualquier valor. Neo4j es la fuente de los partidos, así que `POST /comentarios` consulta primero Neo4j y recién entonces escribe en Cassandra. Es la única operación que combina fuentes. No se pidió que una request consulte todas las bases, y las demás no combinan ninguna.

## Qué no hace la API

No acepta consultas, colecciones, tablas, keyspaces, Cypher ni comandos enviados por el consumidor. Los textos de consulta son fijos en cada adaptador y el cliente solo aporta valores validados.
