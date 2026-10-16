# Arquitectura y adaptadores

```
Cliente HTTP
   ↓
routes/      contrato HTTP: rutas, validación de parámetros, códigos de estado
   ↓
services/    reglas del caso de uso (404 vs. vacío, idempotencia, límites)
   ↓
adapters/    único lugar que importa el driver de cada base
   ↓
driver nativo → base NoSQL
```

- **routes** no conoce ninguna base. Declara el contrato (parámetros con regex y rangos, `responses=` con todos los códigos) y delega.
- **services** recibe el adaptador por inyección (`Depends`), por eso las pruebas unitarias lo reemplazan por uno falso sin tocar ninguna base.
- **adapters** crea la conexión de forma perezosa (la API arranca aunque una base esté caída), fija el contexto (base, keyspace, namespace), ejecuta una consulta fija, convierte la respuesta al modelo interno y traduce las excepciones del driver a errores de dominio (`DependenciaNoDisponible`, `DependenciaTimeout`). El mensaje que sale al consumidor nunca incluye el texto de la excepción original.
- **observability** (middleware): asigna o respeta `X-Request-ID` (si el que llega es inválido se reemplaza), registra cada request y aplica un tope duro de duración (`DEADLINE_SEGUNDOS`, 10 s por defecto) que responde 504 sin esperar al driver.

## Adaptadores por producto

| Producto | Driver | Contexto | Conexión y timeout | Errores que traduce |
|---|---|---|---|---|
| MongoDB | `pymongo` | base `fixture2030` | `serverSelection`/`connect`/`socket` = `TIMEOUT_SEGUNDOS` | `NetworkTimeout`→504, resto de `PyMongoError`→503 |
| Neo4j | `neo4j` | base `neo4j` | `connection_timeout` y `unit_of_work(timeout=)` | `Neo4jError`/`DriverError`→503, timeout→504 |
| Cassandra | `cassandra-driver` | keyspace `fixture2030` | `connect_timeout` y `default_timeout` | `OperationTimedOut`/`ReadTimeout`/`WriteTimeout`→504, `NoHostAvailable`→503 |
| Redis | `redis` | claves `f2030:*` | `socket_timeout` y `socket_connect_timeout`, sin reintentos internos | `TimeoutError`→504, `RedisError`→503 |
| InfluxDB 3 | `httpx` (HTTP `/api/v3/query_sql`) | base `fixture2030_metrics` | `httpx.Timeout` | timeout→504, error de conexión o HTTP ≠ 200→503 |
| IRIS | `intersystems-irispython` (DB-API + API nativa de objetos) | namespace `USER` | `timeout` de `iris.connect` | error de comunicación→503 |

## Mapa de endpoints

| Método | Ruta | Fuente | Operación | Caso de uso | Tipo |
|---|---|---|---|---|---|
| GET | `/equipos/{codigo}` | MongoDB | `find_one` por índice único `codigo` | CU1 | lectura |
| GET | `/equipos/{codigo}/jugadores` | MongoDB | `find` + `sort` + `skip`/`limit` sobre índice `equipo` | CU2 | lectura |
| GET | `/partidos/{id}` | Neo4j | Cypher fijo: `PARTICIPA_EN` y `SE_JUEGA_EN` | CU3 | lectura |
| GET | `/partidos/{id}/eventos` | Neo4j | Cypher fijo: `OCURRE_EN` con `LIMIT` | CU4 | lectura |
| GET | `/partidos/{id}/comentarios` | Cassandra | `SELECT` por partición completa | CU5 | lectura |
| POST | `/partidos/{id}/comentarios` | Cassandra (+ Neo4j) | `INSERT … IF NOT EXISTS` (3 tablas) | CU6 | creación |
| GET | `/sesiones/{usuario}` | Redis | `HGETALL` + `TTL` | CU7 | lectura |
| DELETE | `/sesiones/{usuario}` | Redis | `DEL` | CU8 | invalidación |
| GET | `/partidos/{id}/estadisticas` | InfluxDB | SQL fijo acotado por partido, tiempo y límite | CU9 | lectura |
| GET | `/partidos/{id}/detalle` | IRIS | SQL sobre `Fixture.Partido` y `Fixture.Evento` | CU10 | lectura |
| POST | `/partidos/{id}/estado` | IRIS | `CambiarEstado` + `%Save` | CU11 | actualización |
| GET | `/health` | Las seis | `ping` por fuente en paralelo | CU12 | lectura |

## Diseño por acceso

Cada consulta respeta el patrón de acceso de su base, sin escaneos:

- **MongoDB:** filtros por campos indexados (`codigo` único; `equipo`, `apellido`, `posicion`). Paginación con `skip`/`limit` máximo 100 y proyección de solo los campos necesarios (sin `_id`).
- **Neo4j:** se parte siempre de un nodo identificado (`Partido {id}`) y se recorre una o dos relaciones con `LIMIT`. Cypher fijo y parametrizado.
- **Cassandra:** toda lectura conoce `(partido_id, pais, ventana)`. Por eso la ventana de 30 minutos es obligatoria en la ruta: sin ella habría que recorrer particiones. La paginación usa el `paging_state` del driver como cursor opaco.
- **Redis:** acceso por clave exacta; nunca `KEYS` ni `SCAN` desde la API.
- **InfluxDB:** `partido_id` (tag) y un intervalo temporal son obligatorios; ventana máxima de 120 minutos y tope de 500 puntos con la marca `truncado`.
- **IRIS:** acceso por la clave de negocio `Codigo` (índice único) y a los eventos por su relación padre-hijo.

### Neo4j por relación frente a Cassandra por partición

En Neo4j la API navega relaciones desde un nodo (`Evento → Partido ← Equipo`) y el costo depende de cuántas relaciones tenga ese nodo, por eso se limita con `LIMIT`. En Cassandra no se navega nada: se lee una partición entera por su clave completa. El costo depende del tamaño de esa partición, que el Hito 6 acotó con la ventana de 30 minutos. Una consulta de Cassandra que omitiera `pais` o `ventana` sería un escaneo entre particiones.

### Qué podría cachearse y qué riesgo tiene

El detalle de equipos y de partidos cambia poco y podría cachearse en Redis con TTL corto (patrón cache-aside del Hito 7), con invalidación al cambiar el estado de un partido. El riesgo es la frescura: el marcador y el estado de un partido en juego quedarían desactualizados hasta que venza el TTL. Los comentarios, las sesiones y las estadísticas no son buenos candidatos: cambian continuamente o tienen su propio TTL.
