# Topología y entornos

## Topología de referencia

```text
Postman / curl / navegador
          |
          | HTTP :8000
          v
     API Fixture 2030
     FastAPI / rutas -> servicios -> adaptadores
          |
          | red Docker Compose fixture2030_net
          +---- mongodb:27017   (MongoDB)
          +---- neo4j:7687      (Bolt; Browser HTTP :7474)
          +---- cassandra:9042  (CQL)
          +---- redis:6379      (RESP)
          +---- influxdb:8181   (HTTP / InfluxDB 3)
          +---- iris:1972       (Superserver; portal HTTP :52773)
```

Los nombres y puertos están confirmados contra el `docker-compose.yml` del Hito 10. Docker publica los servicios sobre `127.0.0.1` del host para el trabajo local y usa volúmenes nombrados para persistencia.

## Diferencias importantes

| Origen de la conexión | Host de ejemplo | Puerto | Motivo |
|---|---|---:|---|
| API en notebook | `localhost` | Puerto publicado (`*_HOST_PORT` o el valor correspondiente del `.env`) | El proceso Python corre directamente en el host. |
| API en contenedor Compose | Nombre de servicio, por ejemplo `mongodb` | Puerto interno estándar (`27017`) | El contenedor usa la red interna `fixture2030_net`. |
| Navegador del host a Neo4j Browser | `localhost` | `7474` publicado | Interfaz web para personas; no demuestra que el driver Bolt funcione. |
| Cliente/driver de IRIS desde el host | `localhost` | `1972` publicado | Superserver para el driver; el portal `52773` es otra interfaz. |

Dentro de un contenedor, `localhost` se refiere a ese propio contenedor. Por lo tanto, si la API corre en Docker, `localhost:27017` no apunta automáticamente a MongoDB: se debe usar `mongodb:27017`.

## Comprobación del origen

Desde la raíz del repositorio:

```bash
docker compose ps
docker compose --profile api ps
```

El script `scripts/prueba_tcp.sh` (modo `tcp`) prueba la notebook y, si el servicio `api` está ejecutándose en Compose, prueba además los nombres/puertos internos desde ese contenedor. Si la API se ejecuta localmente, la prueba ejecutada por el proceso local equivale al entorno de origen y queda identificada como `notebook`.

## Configuración de puertos

Los puertos externos publicados pueden personalizarse (`MONGO_HOST_PORT`, `NEO4J_HOST_PORT`, `CASSANDRA_HOST_PORT`, `REDIS_HOST_PORT`, `INFLUX_HOST_PORT`, `IRIS_HOST_PORT`). El servicio `api` en Compose conecta a los puertos internos y no depende del remapeo del host. La API local sí necesita coincidir con el puerto realmente publicado. Ver `../../docs/conectividad_y_configuracion.md` del Hito 10.

## Persistencia y límites

Los productos usan volúmenes nombrados (`mongo_data`, `neo4j_data`, `cassandra_data`, `redis_data`, `influx_data`, `iris_data`). Una prueba de caída debe usar `docker compose stop` y `docker compose start` sobre un servicio; no usar `down -v`, no borrar volúmenes y no limpiar datos. La prueba de conectividad no es una prueba de carga ni de escalabilidad.
