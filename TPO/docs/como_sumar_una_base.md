# Cómo sumar una base al proyecto

La API está armada para que una base se sume sin reescribir lo que hay. Redis (sesiones y partido en vivo), Cassandra, InfluxDB y el monitoreo ya están; lo que queda por enganchar es el **ranking en Redis**. Esta guía dice qué archivos tocar.

## Cómo está organizada la API

```
app/
├── routes/      reciben el pedido y validan el formato
├── services/    el caso de uso: reglas y orden de las operaciones
├── adapters/    un archivo por base; el único lugar donde se usa su driver
├── puertos/     lo que la API espera de una pieza que hoy resuelve una base y mañana otra
└── deps.py      qué implementación se usa para cada cosa
```

Dos reglas que conviene respetar:

1. **El driver de una base se usa solo en su adaptador.** Los servicios no saben qué base hay atrás.
2. **Cada operación contra una base va dentro de `operacion(...)`** ([`app/adapters/base.py`](../app/adapters/base.py)). Con eso queda medida en `/metrics`, se anota en el registro si falla y los errores del driver se traducen a 503 o 504.

## Pasos comunes

1. **Compose.** Agregar el servicio en [`docker-compose.yml`](../docker-compose.yml), en la red `tpo`, con verificación de salud y con `mem_limit` y `cpus`. Los puertos del equipo, solo sobre `127.0.0.1`.
2. **Configuración.** Agregar sus variables en [`app/config/settings.py`](../app/config/settings.py), en el bloque `x-api-entorno` del Compose y en `.env.example`. Las contraseñas van en `.env`, que no se versiona.
3. **Dependencia.** Agregar el driver en `requirements.txt` y reconstruir: `docker compose build`.
4. **Adaptador.** Crear `app/adapters/<base>.py` siguiendo el de MongoDB: conexión al primer uso, una función `_traducir` para los errores del driver, un método por operación y un `ping()`.
5. **Proveedor.** En [`app/deps.py`](../app/deps.py), una función con `@lru_cache` que cree el adaptador una sola vez por proceso, y sumarlo al diccionario de `get_health_service` para que aparezca en `/health/dependencias`.
6. **Pruebas.** Un adaptador falso en [`tests/falsos.py`](../tests/falsos.py) para las pruebas sin bases, y pruebas de integración en `tests/integration/`.

## Redis: lo que ya está

El adaptador es [`app/adapters/redis.py`](../app/adapters/redis.py), con métodos genéricos (guardar, leer, conjuntos ordenados, contadores, publicar) que puede usar cualquier servicio. Las sesiones están en [`app/puertos/sesiones.py`](../app/puertos/sesiones.py) y el partido en vivo en [`app/services/vivo.py`](../app/services/vivo.py). Las claves que ya se usan están en [modelo_de_datos.md](modelo_de_datos.md#redis): conviene que el ranking use un prefijo propio (`ranking:`).

## Redis: ranking en vivo

El TPO incluye `app/adapters/ranking_redis.py`. Compose lo habilita mediante `REDIS_ENABLED=true`; con `false` sigue disponible `RankingMongo`. La inicialización reconstruye el sorted set desde los puntajes de MongoDB por lotes cuando falta la marca de inicialización.

Al iniciar un partido, un hilo prepara los pronósticos en Redis. Al cerrar, se refresca el snapshot y se aplican las reglas del dominio por lotes. Un script Lua actualiza el total, el sorted set y la marca del partido; conserva la base anterior para reintentar una ejecución parcial. Tras la espera configurada se vuelcan los puntos a MongoDB con operaciones idempotentes, se guarda la foto y se limpian los datos temporales del partido. Los pronósticos y el resultado siguen en MongoDB como respaldo.

El ranking acepta lecturas parciales mientras se calcula. La puntuación se puede reintentar por la API si quedó fallida o si vence la reserva tras una interrupción. Redis usa AOF `everysec`; no hay recuperación automática al reinicio, failover ni Redis Cluster. Se asume un único partido puntuándose a la vez. El límite de memoria local es deliberadamente pequeño: hay que dimensionar y medir antes de usar millones de usuarios. Los desempates y la configuración se detallan en el README.

Usa el mismo Redis que las sesiones y el partido en vivo (con su contraseña): `deps._ranking_redis()` le pasa el cliente de `deps._redis()`. Para leer la tabla desde "la otra región" está la réplica `redis_replica` (`REDIS_REPLICA_URL`); cuánto tarda un cambio en llegarle se mide con `python -m scripts.medir_replica_redis` ([arquitectura por regiones](arquitectura_regiones.md)).

Por qué vale la pena está medido: con 100.000 usuarios, saber el puesto de uno leyendo de MongoDB tarda unos 300 ms y con 50 pedidos a la vez empieza a fallar ([rendimiento.md](rendimiento.md#26-saber-el-puesto-de-un-usuario-en-el-ranking)).

## Redis: la copia del calendario (opcional)

Hoy cada proceso de la API guarda su copia del calendario ([`app/services/calendario.py`](../app/services/calendario.py)) y un cambio tarda hasta 30 segundos en llegar a todos. Con la copia en Redis sería una sola para todos los procesos. Los servicios usan dos métodos, `partido(id)` y `listar(fase, fecha, estado)`, más `invalidar()`; una clase con esos métodos puede reemplazarla en `get_calendario`.

## InfluxDB: lo que ya está

[`app/adapters/influx.py`](../app/adapters/influx.py) escribe las estadísticas de la simulación y, desde el cierre de cada minuto ([`app/services/audiencia.py`](../app/services/audiencia.py)), la audiencia y los comentarios por minuto. El análisis está en [`app/routes/analisis.py`](../app/routes/analisis.py). Las medidas, en [modelo_de_datos.md](modelo_de_datos.md#influxdb--tres-bases).

El puerto [`app/puertos/eventos.py`](../app/puertos/eventos.py), para publicar en InfluxDB las jugadas cargadas a mano desde administración, sigue sin implementación: no confundirlo con el flujo de la simulación.

## Cassandra: lo que ya está

Adaptador con una sesión por región ([`app/adapters/cassandra.py`](../app/adapters/cassandra.py)), servicio de comentarios ([`app/services/comentarios.py`](../app/services/comentarios.py)) y rutas ([`app/routes/comentarios.py`](../app/routes/comentarios.py)). Cada región aparece por separado en `/health/dependencias`.

## Prometheus y Grafana: lo que ya está

Están en el Compose, con su configuración en [`monitoreo/`](../monitoreo/). Prometheus recolecta la API (`api:8010`) y los exportadores de Redis y MongoDB; Grafana tiene el tablero `Prode Mundial 2030` en http://127.0.0.1:3001. Una métrica nueva de la API aparece sola en Prometheus; para verla en el tablero hay que agregar el panel en [`monitoreo/grafana/tableros/prode2030.json`](../monitoreo/grafana/tableros/prode2030.json). Las métricas de la API están en [api.md](api.md#métricas).

## Antes de dar por terminado

```powershell
python -m pytest tests/unit -q
docker compose run --rm -e PERMITIR_REINICIO=1 herramientas python -m pytest tests/integration -q
```

Las pruebas de integración borran el grafo de Neo4j y lo vuelven a cargar. Después de correrlas hay que cargar otra vez los datos: `docker compose run --rm herramientas python -m seed.run --reiniciar --dias-hasta-inicio 3`.
