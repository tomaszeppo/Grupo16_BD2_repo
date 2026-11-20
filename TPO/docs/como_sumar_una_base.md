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

El punto de enganche es [`app/puertos/ranking.py`](../app/puertos/ranking.py):

```python
class RankingPort(Protocol):
    nombre: str                                              # se informa en "fuente"
    def top(self, limit: int) -> list[dict]: ...             # {puesto, usuario_id, nombre, puntos, exactos, tiempo_seg}
    def posicion(self, usuario_id: str) -> dict | None: ...  # {puesto, puntos, exactos, tiempo_seg, total_usuarios}
    def puntajes_de(self, usuario_ids: list[str]) -> list[dict]: ...
    def partido_puntuado(self, partido_id: str) -> None: ...
```

Qué hacer:

1. Escribir una clase sobre un conjunto ordenado de Redis, usando el adaptador que ya existe (`deps._redis()`). El puntaje de cada usuario puede ser un solo número que ya incluya el desempate, como está planteado en `Hito-13-monitoreo/docs/proyecto_final_planteado.md`.
2. En `partido_puntuado(partido_id)`, leer de MongoDB los puntajes de quienes pronosticaron ese partido y escribirlos con `ZADD`. La API llama a este método cuando `puntajes` ya tiene sumado el partido. Conviene escribir el total y no un incremento: así repetir el aviso no cambia nada.
3. En `deps.py`, hacer que `get_ranking` devuelva esa clase.

Para leer la tabla desde "la otra región" está la réplica `redis_replica`: su dirección llega a la API en `REDIS_REPLICA_URL` (`Settings.redis_replica_url`). Cuánto tarda un cambio en llegarle se mide con `python -m scripts.medir_replica_redis`; es el atraso con que otra región vería la tabla ([arquitectura por regiones](arquitectura_regiones.md)).

MongoDB sigue siendo la fuente de verdad. Si Redis se pierde, el ranking se reconstruye recorriendo `puntajes`. La clase actual, `RankingMongo`, sirve además de respaldo si Redis no responde.

Por qué vale la pena está medido: con 100.000 usuarios, saber el puesto de uno leyendo de MongoDB tarda unos 300 ms y con 50 pedidos a la vez empieza a fallar ([rendimiento.md](rendimiento.md#26-saber-el-puesto-de-un-usuario-en-el-ranking)).

## Redis: la copia del calendario (opcional)

Hoy cada proceso de la API guarda su copia del calendario ([`app/services/calendario.py`](../app/services/calendario.py)) y un cambio tarda hasta 30 segundos en llegar a todos. Con la copia en Redis sería una sola para todos los procesos. Los servicios usan dos métodos, `partido(id)` y `listar(fase, fecha, estado)`, más `invalidar()`; una clase con esos métodos puede reemplazarla en `get_calendario`.

## InfluxDB: lo que ya está

[`app/adapters/influx.py`](../app/adapters/influx.py) escribe las estadísticas de la simulación y, desde el cierre de cada minuto ([`app/services/audiencia.py`](../app/services/audiencia.py)), la audiencia y los comentarios por minuto. El análisis está en [`app/routes/analisis.py`](../app/routes/analisis.py). Las medidas, en [modelo_de_datos.md](modelo_de_datos.md#influxdb--base-fixture2030_metrics).

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
