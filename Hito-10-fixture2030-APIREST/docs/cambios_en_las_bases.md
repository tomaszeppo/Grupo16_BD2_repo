# Cambios en las bases respecto de los hitos anteriores

Documento para revisión. Registra lo que este hito **agregó o modificó** en cada base frente al esquema de la rama `main` (Hitos 4 a 8). Los esquemas de `main` son la referencia; lo que no figura acá se tomó tal cual.

## Resumen

| Base | Esquema de `main` | Agregado o modificado | Impacto |
|---|---|---|---|
| MongoDB | Colecciones de equipos y jugadores | Colección `partidos` para documentos persistentes, eventos y estado | Medio |
| Neo4j | Sin cambios | Solo datos de ejemplo (ids `P-NN`) | Bajo |
| Cassandra | Las dos tablas del PDF, sin cambios | **Una tabla nueva** (`comentarios_idempotencia`) | **Medio: revisar** |
| Redis | Sin cambios | Contraseña del servidor; datos de ejemplo | Bajo |
| InfluxDB | Sin cambios | Tabla creada por la primera escritura; datos de ejemplo | Bajo |

El proyecto usa cinco bases (proyecto Compose `fixture2030-api`, volúmenes `fixture2030-api_*`, red `fixture2030_net`). Los contenedores de hitos anteriores que estuvieran corriendo no se detienen ni se modifican. Los archivos y registros de hitos previos se conservan como material histórico, pero ya no forman parte del stack de esta API.

## Convención de identificadores

Se unificó el partido como `P-01`…`P-08` en las fuentes que lo referencian. Es un cambio de **valores**, no de esquema:

| Fuente | En `main` | En este hito |
|---|---|---|
| Neo4j `Partido.id` | `P001`…`P032` | `P-01`…`P-08` |
| Neo4j `Evento.id` | `EV-P001-INICIO` | `EV-P-01-INICIO` |
| Cassandra `partido_id` | `ARG-FRA` (ejemplo del PDF) | `P-01` |
| InfluxDB tag `partido_id` | `M001` | `P-01` |
| MongoDB `partidos.codigo` | — | `P-01`…`P-08` |
| Redis | ids de usuario `U001`… (sin partido en las sesiones) | igual |

Los códigos de equipo son los FIFA de tres letras en todas las fuentes, como en `main`.

## MongoDB

- **Esquema:** mantiene `equipos{nombre,codigo}` y `jugadores{nombre,apellido,dorsal,equipo,posicion}` y agrega `partidos{codigo,equipo_local,equipo_visitante,fecha_hora,sede,estado,eventos}`. La nueva colección valida el identificador, los estados admitidos y la forma documental. Índices: único en `equipos.codigo` y `partidos.codigo`; `jugadores.equipo`, `jugadores.apellido`, `jugadores.posicion`.
- **Agregado:** 16 equipos, 80 jugadores sintéticos (5 por equipo) y 8 partidos. La carga de equipos y jugadores es repetible; los partidos se insertan solo si aún no existen para preservar los cambios de estado.
- **Responsabilidad:** guarda el registro documental persistente de los partidos y sus eventos; Neo4j conserva el fixture y las relaciones entre equipos, sedes, partidos y jugadas.
- **Instancia nueva:** `mongo:7.0` con usuario y contraseña propios (`.env`). No se tocó la base del Hito 4.
- **A revisar:** la validación se reescribió siguiendo `validaciones.mongodb.js`; conviene compararla campo por campo si se quiere una réplica exacta.

## Neo4j

- **Esquema:** igual a `main`: `Equipo`, `Partido`, `Estadio`, `Evento`; relaciones `PARTICIPA_EN`, `SE_JUEGA_EN`, `OCURRE_EN`. Las propiedades del resultado simulado conservan los nombres (`equipoGanador`, `equipoPerdedor`, `golesGanador`, `golesPerdedor`, `origenResultado = 'SIMULADO'`).
- **Restricciones de unicidad:** se crean cuatro (`Equipo.codigo`, `Partido.id`, `Estadio.id`, `Evento.id`), un subconjunto de las que define `estructura.cypher`. No se crearon las de `Jugador`, `Usuario`, `Grupo` ni `Prediccion` porque la API no usa esos nodos.
- **Agregado:** 16 equipos, 8 estadios, 8 partidos, 5 eventos y 2 resultados simulados (`P-01` y `P-02`). Se omiten jugadores, usuarios, grupos y predicciones.
- **Diferencia de imagen:** `neo4j:5` en lugar de `neo4j:latest` con los plugins APOC y Graph Data Science, que la API no necesita.
- **A revisar:** los nombres de las restricciones difieren de los del Hito 5 (`equipo_codigo` frente a `equipo_codigo_unico`). Es indiferente si se usa una instancia nueva.

## Cassandra

- **Esquema:** keyspace `fixture2030` (`SimpleStrategy`, factor 1) y las dos tablas del PDF de documentación del Hito 6, con la misma clave de partición: `comentarios_por_partido_pais` `((partido_id, pais, ventana), creado_en, comentario_id)` y `comentarios_por_likes_partido_pais`. En `main` el Hito 6 solo tiene PDF, sin scripts: el esquema se reconstruyó de esa documentación.
- **Tabla nueva (no está en `main`):**

  ```
  comentarios_idempotencia (clave text PRIMARY KEY, partido_id, pais, ventana, creado_en, comentario_id)
  WITH default_time_to_live = 86400
  ```

  **Por qué:** `creado_en` y `ventana` forman parte de la clave primaria. Sin esta tabla, un reintento con la misma `Idempotency-Key` que llegara después de cruzar el borde de la ventana de 30 minutos crearía una fila duplicada. La tabla fija `ventana` y `creado_en` en el primer intento (`INSERT … IF NOT EXISTS`) y las filas expiran a las 24 horas.
- **Comportamiento de escritura:** los `INSERT` en las dos tablas de comentarios usan `IF NOT EXISTS` (transacciones ligeras). Un reintento completa lo que faltó sin duplicar. Cuestan más que un `INSERT` simple.
- **Limitación:** `comentarios_por_likes_partido_pais` guarda `likes` en la clave de clustering. La API inserta con `likes = 0` y no implementa "dar like", que exigiría borrar e insertar la fila. No es un endpoint de la consigna.
- **Agregado:** 5 comentarios sintéticos en la partición `(P-01, ARG, 2030-06-15 18:30)`.
- **A revisar:**
  - Si se prefiere no agregar tablas, la alternativa es documentar que ese caso límite puede duplicar y quitar `comentarios_idempotencia`.
  - Los tipos de columna salen del PDF. El nombre del keyspace no aparece en las capturas del Hito 6; se asumió `fixture2030`.
  - El Hito 6 de la rama `correcciones` define otro esquema (`comentarios_por_partido` con `bucket`). Este hito **no** lo usa.

## Redis

- **Esquema:** igual a `main`: Hash `f2030:sesion:{usuario}` con `session_id`, `usuario_id`, `rol`, `estado_acceso`, `creado_en`, `ultimo_acceso`, `acciones`, `token_ref`; TTL de 1800 s. Mismo `maxmemory 128mb` y política `volatile-lru`, y `appendonly yes`.
- **Agregado:** sesiones `U001` y `U003` activas y `U002` cerrada (como la demostración del Hito 7), y una clave de caché `f2030:cache:partido:P-01:resumen` con TTL de 300 s que la API no usa.
- **Diferencias de configuración:** el servidor exige contraseña (`requirepass`; en `main` no tenía), imagen `redis:7` (no `latest`) y volumen nombrado en lugar de un directorio del equipo.
- **Efecto de las pruebas:** `DELETE /sesiones/U003` elimina esa sesión; `scripts/ejecutar_pruebas.sh integration` la vuelve a sembrar. Las sesiones expiran a los 30 minutos.

## InfluxDB

- **Esquema:** igual a `main`: base `fixture2030_metrics` con retención de 90 días; tabla `estadisticas_partido` con tags `partido_id,equipo_id,sede,fuente,fase` y campos `posesion_pct,pases_completados,tiros,recuperaciones,velocidad_kmh`.
- **Diferencia:** en `main` la tabla se crea explícitamente con `influxdb3 create table --tags …`. Acá la crea la primera escritura (line protocol), que infiere los mismos tags y campos. La tabla `usuarios_conectados` **no** se creó porque la API no la consulta.
- **Agregado:** 4800 puntos (partidos `P-01` y `P-02`, 10 minutos desde `2030-06-15T18:30Z`, 2 equipos × 2 fuentes). Las escrituras repetidas con los mismos timestamps no duplican.
- **Token:** se genera en el primer arranque y se guarda solo en el `.env` local.
- **A revisar:** los datos son de 2030 y la retención es de 90 días contados desde la fecha actual. Las escrituras y las consultas funcionan hoy porque la retención no descarta datos futuros; si se quisiera comprobar el comportamiento de retención, habría que probarlo aparte.

## Infraestructura

- **Compose propio** con las cinco bases, un servicio `api` (perfil `api`) y la red `fixture2030_net`.
- **Puertos:** publicados en `127.0.0.1`. Son parametrizables (`*_HOST_PORT`) porque los puertos estándar pueden estar ocupados por los contenedores de otros hitos. En el equipo donde se desarrolló se usaron 27117 (MongoDB), 6479 (Redis) y 9142 (Cassandra) en el `.env` local, que no se versiona.
- **Imágenes:** `mongo:7.0`, `neo4j:5`, `cassandra:4.1`, `redis:7` e `influxdb:3-core`.
- **Datos:** volúmenes nombrados. `docker compose --profile api stop` los conserva; `down -v` los borra.

## Cómo repetir la revisión

```
docker compose exec cassandra cqlsh -e "DESCRIBE KEYSPACE fixture2030"
docker compose exec mongodb mongosh -u <usuario> -p <contraseña> --authenticationDatabase admin fixture2030 --eval "db.getCollectionInfos().map(c=>c.name)"
docker compose exec neo4j cypher-shell -u neo4j -p <contraseña> "SHOW CONSTRAINTS"
```
