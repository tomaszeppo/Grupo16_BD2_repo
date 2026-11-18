# Cómo sumar una base al proyecto

La API está armada para que Redis, Cassandra, InfluxDB y el monitoreo se agreguen sin reescribir lo que hay. Esta guía dice qué archivos tocar en cada caso.

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

## Redis: sesiones

Hoy la API confía en el encabezado `X-Usuario-Id`. El punto de enganche es [`app/puertos/sesiones.py`](../app/puertos/sesiones.py):

```python
class SesionesPort(Protocol):
    def usuario_de(self, credencial: str | None) -> str:
        """Devuelve el id del usuario o lanza NoAutorizado."""
```

Qué hacer:

1. Escribir una clase que reciba el identificador de sesión, lo busque en Redis y devuelva el usuario, o lance `NoAutorizado` si no existe o venció.
2. En `deps.py`, hacer que `get_sesiones` devuelva esa clase.
3. Agregar los endpoints para iniciar y cerrar sesión.

Las rutas y los servicios no cambian: siguen recibiendo el usuario de `usuario_actual`. Si el encabezado pasa a llamarse de otra forma, se cambia en `usuario_actual` y en `ui/app.js`.

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

1. Escribir una clase sobre un conjunto ordenado de Redis. El puntaje de cada usuario puede ser un solo número que ya incluya el desempate, como está planteado en `Hito-13-monitoreo/docs/proyecto_final_planteado.md`.
2. En `partido_puntuado(partido_id)`, leer de MongoDB los puntajes de quienes pronosticaron ese partido y escribirlos con `ZADD`. La API llama a este método cuando `puntajes` ya tiene sumado el partido. Conviene escribir el total y no un incremento: así repetir el aviso no cambia nada.
3. En `deps.py`, hacer que `get_ranking` devuelva esa clase.

MongoDB sigue siendo la fuente de verdad. Si Redis se pierde, el ranking se reconstruye recorriendo `puntajes`. La clase actual, `RankingMongo`, sirve además de respaldo si Redis no responde.

Por qué vale la pena está medido: con 100.000 usuarios, saber el puesto de uno leyendo de MongoDB tarda unos 300 ms y con 50 pedidos a la vez empieza a fallar ([rendimiento.md](rendimiento.md#26-saber-el-puesto-de-un-usuario-en-el-ranking)).

## Redis: la copia del calendario (opcional)

Hoy cada proceso de la API guarda su copia del calendario ([`app/services/calendario.py`](../app/services/calendario.py)) y un cambio tarda hasta 30 segundos en llegar a todos. Con la copia en Redis sería una sola para todos los procesos. Los servicios usan dos métodos, `partido(id)` y `listar(fase, fecha, estado)`, más `invalidar()`; una clase con esos métodos puede reemplazarla en `get_calendario`.

## InfluxDB: series de la simulación

El TPO ya incluye InfluxDB 3. [`app/adapters/influx.py`](../app/adapters/influx.py) escribe muestras sintéticas por equipo y minuto; la ruta de estadísticas consulta los agregados durante el vivo. Al terminar, el servicio cruza las muestras con el guion de MongoDB y archiva los resultados y jugadas en Neo4j. Ver [README](../README.md#estadísticas-de-la-simulación-influxdb) y [modelo de datos](modelo_de_datos.md#histórico-de-simulaciones).

El puerto [`app/puertos/eventos.py`](../app/puertos/eventos.py) para publicar jugadas registradas manualmente sigue sin implementación InfluxDB: no confundirlo con el flujo de simulación. Si falla una muestra no hay reintento automático; se marca el histórico incompleto.

## Cassandra: comentarios

El TPO ya incluye Cassandra y su esquema en [`cassandra/esquema.cql`](../cassandra/esquema.cql). Las rutas y la conexión están en [`app/routes/simulaciones.py`](../app/routes/simulaciones.py): `GET /partidos/{id}/comentarios/recientes?pais=ARG` y `POST /partidos/{id}/comentarios`. El POST comprueba el estado en Neo4j y usa el usuario de laboratorio y su país. La tabla particiona por partido, país y ventana de 30 minutos.

Pendientes: separar adaptador, servicio y rutas; definir idempotencia de publicación, retención e historial; e incluir Cassandra en el estado de salud. El TPO no implementa la tabla auxiliar de idempotencia del Hito 10.

## Prometheus y Grafana

La API ya expone `GET /metrics` en el puerto 8010. En el Compose, el servicio se llama `api`, así que el destino para Prometheus es `api:8010`. Los nombres de las métricas están en [api.md](api.md#métricas).

Dos cosas para tener en cuenta:

- Son métricas de aplicación. Para las internas de MongoDB y de Neo4j hacen falta sus exportadores.
- La API corre con varios procesos y `/metrics` ya devuelve la suma de todos.

Paneles que salen directo de lo que hay:

- Pedidos por segundo y errores por ruta: `prode_api_pedidos_total`.
- Latencia por ruta: `prode_api_duracion_segundos`.
- La API contra cada base: `prode_base_duracion_segundos`, separada por `base`.
- Cuánto tarda la tabla en quedar actualizada tras un partido: `prode_puntuacion_duracion_segundos`.
- Si se está pronosticando con un calendario viejo: `prode_calendario_desactualizado`.

## Antes de dar por terminado

```powershell
python -m pytest tests/unit -q
docker compose run --rm -e PERMITIR_REINICIO=1 herramientas python -m pytest tests/integration -q
```

Las pruebas de integración borran el grafo de Neo4j y lo vuelven a cargar. Después de correrlas hay que cargar otra vez los datos: `docker compose run --rm herramientas python -m seed.run --reiniciar --dias-hasta-inicio 3`.
