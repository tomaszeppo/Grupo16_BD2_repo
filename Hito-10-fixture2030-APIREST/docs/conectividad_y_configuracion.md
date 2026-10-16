# Conectividad y configuración

Todo valor de conexión llega por variables de entorno o por un `.env` local excluido de git. El repositorio solo versiona `.env.example`, sin valores secretos.

## Variables

| Variable | Por defecto | Secreto |
|---|---|---|
| `TIMEOUT_SEGUNDOS` | 3.0 | no |
| `DEADLINE_SEGUNDOS` | 10.0 | no |
| `MONGO_HOST`, `MONGO_PORT`, `MONGO_USER`, `MONGO_DB` | `localhost`, 27017, `admin`, `fixture2030` | no |
| `MONGO_PASSWORD` | — | **sí** |
| `NEO4J_URI`, `NEO4J_USER`, `NEO4J_DB` | `bolt://localhost:7687`, `neo4j`, `neo4j` | no |
| `NEO4J_PASSWORD` | — | **sí** |
| `CASSANDRA_HOST`, `CASSANDRA_PORT`, `CASSANDRA_KEYSPACE` | `localhost`, 9042, `fixture2030` | no |
| `REDIS_HOST`, `REDIS_PORT` | `localhost`, 6379 | no |
| `REDIS_PASSWORD` | — | **sí** |
| `INFLUX_URL`, `INFLUX_DB` | `http://localhost:8181`, `fixture2030_metrics` | no |
| `INFLUX_TOKEN` | lo genera `levantar_servicios.sh` | **sí** |
| `IRIS_HOST`, `IRIS_PORT`, `IRIS_NAMESPACE`, `IRIS_USER` | `localhost`, 1972, `USER`, `fixture` | no |
| `IRIS_PASSWORD` | — | **sí** |
| `*_HOST_PORT` (opcionales) | puerto estándar de cada base | no |

## Notebook frente a Docker

| Componente | Desde el notebook | Desde un contenedor de la red `fixture2030_net` |
|---|---|---|
| MongoDB | `localhost:27017` | `mongodb:27017` |
| Neo4j | `localhost:7687` | `neo4j:7687` |
| Cassandra | `localhost:9042` | `cassandra:9042` |
| Redis | `localhost:6379` | `redis:6379` |
| InfluxDB | `localhost:8181` | `influxdb:8181` |
| IRIS | `localhost:1972` | `iris:1972` |
| API | `localhost:8000` | `api:8000` |

El servicio `api` de Docker Compose sobrescribe los hosts con los nombres de servicio. Para correr la API en el notebook (`scripts/iniciar_api.sh --local`) se usan los valores de `localhost` del `.env`.

### Si un puerto estándar está ocupado

Si ya hay otra base en el puerto estándar (por ejemplo, los contenedores de los Hitos 4, 6 y 7), definir en el `.env` el puerto publicado y el que usa la API del notebook, con el mismo valor:

```
MONGO_HOST_PORT=27117
MONGO_PORT=27117
```

La API en contenedor no se ve afectada: siempre usa el puerto interno estándar.

## Timeouts

| Límite | Valor | Dónde se aplica |
|---|---|---|
| `TIMEOUT_SEGUNDOS` | 3 s | Cada operación de red: `serverSelection`/`connect`/`socket` (pymongo), `connection_timeout` y `unit_of_work(timeout)` (neo4j), `connect_timeout` y `default_timeout` (cassandra), `socket_timeout` y `socket_connect_timeout` (redis), `httpx.Timeout` (InfluxDB), `timeout` de `connect` (IRIS) |
| `DEADLINE_SEGUNDOS` | 10 s | Toda la request: al vencer responde 504 sin esperar al driver |

## Cómo verificar cada dependencia

- `bash scripts/verificar_conectividad.sh`: abre el puerto de cada base desde el notebook y consulta `GET /health`.
- `GET /health`: hace un `ping` acotado por timeout a cada fuente, en paralelo. Responde 200 si todas están bien y 503 con el estado de cada una si alguna falla.

## Orden de arranque y detención

1. `bash scripts/levantar_servicios.sh` (bases, token de InfluxDB, usuario y clases de IRIS, siembra).
2. `bash scripts/iniciar_api.sh`.
3. Detener: `docker compose --profile api stop`. Los datos persisten en los volúmenes nombrados (`fixture2030-api_*`). **No usar `down -v`.**

## Relación con los hitos anteriores

Este compose es independiente de los de los Hitos 4 a 9. Usa su propio nombre de proyecto (`fixture2030-api`), sus propios volúmenes y la red `fixture2030_net`. Solo monta en lectura las clases del Hito 9 (`../Hito-9-fixture2030-iris-objetos/clases`). No modifica ninguna carpeta de otro hito ni los contenedores de esos hitos que estén corriendo. Qué se agregó en cada base está en [cambios_en_las_bases.md](cambios_en_las_bases.md).
