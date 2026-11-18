# La API

Cada endpoint resuelve un caso de uso contra la base que gobierna ese dato. No hay consultas libres: quien llama manda valores, nunca texto de consulta. El contrato completo, con los cuerpos de pedido y respuesta, se ve con la API levantada en http://127.0.0.1:8010/docs.

Todas las respuestas traen un campo `fuente` con la base que respondió.

## Prode (MongoDB)

| Método y ruta | Qué hace | Quién |
|---|---|---|
| `POST /usuarios` | Registra un usuario | Cualquiera |
| `GET /usuarios/{id}` | Datos de un usuario | Cualquiera |
| `PUT /partidos/{id}/pronostico` | Carga o corrige el pronóstico. 201 si es nuevo, 200 si es corrección | Usuario |
| `GET /usuarios/{id}/pronosticos` | Pronósticos del usuario | El propio usuario |
| `POST /prodes` | Crea un prode privado | Usuario |
| `POST /prodes/unirse` | Se une con un código de invitación | Usuario |
| `GET /usuarios/{id}/prodes` | Prodes del usuario | El propio usuario |
| `GET /prodes/{id}/tabla` | Tabla de un prode privado | Sus integrantes |
| `GET /ranking?limit=` | Primeros puestos del prode general | Cualquiera |
| `GET /ranking/usuarios/{id}` | Puesto de un usuario | Cualquiera |
| `GET /ranking/historico/{partido_id}` | El ranking como quedó al cerrar ese partido | Cualquiera |
| `GET /equipos` | Los 48 equipos | Cualquiera |
| `GET /equipos/{codigo}/jugadores?posicion=` | Plantel de un equipo | Cualquiera |

## Fixture y partidos (Neo4j)

| Método y ruta | Qué hace |
|---|---|
| `GET /partidos?fase=&fecha=&estado=` | Fixture. Sale de la copia del calendario; `antiguedad_segundos` dice de cuándo es |
| `GET /partidos/{id}` | Un partido con sus equipos y su estadio |
| `GET /partidos/{id}/eventos` | Jugadas del partido, en orden |
| `GET /partidos/{id}/eventos/{evento_id}/cadena` | Las jugadas que llevaron a esa jugada |
| `GET /equipos/{codigo}/camino` | Partidos del equipo y lo que le queda hasta la final |
| `GET /estadisticas/participacion-en-goles` | Jugadores que más participaron en goles |

## Administración

Para operar partidos en la demostración. Piden el encabezado `X-Admin-Clave`.

| Método y ruta | Qué hace | Base |
|---|---|---|
| `POST /partidos/{id}/estado` | Pone el partido en juego y cierra los pronósticos | Neo4j |
| `POST /partidos/{id}/equipos` | Define los equipos de un partido de eliminatorias | Neo4j |
| `POST /partidos/{id}/eventos` | Carga una jugada. 201 si es nueva, 200 si ya estaba | Neo4j |
| `POST /partidos/{id}/resultado` | Cierra el partido y lanza la puntuación. Responde 202 | MongoDB y Neo4j |
| `GET /partidos/{id}/puntuacion` | Avance de la puntuación | MongoDB |

## Sistema

| Ruta | Qué devuelve |
|---|---|
| `GET /health` | Que la API está viva |
| `GET /health/dependencias` | Estado de MongoDB, de Neo4j y de la copia del calendario. Responde 200 aunque una base esté caída: el cuerpo dice cuál |
| `GET /metrics` | Métricas para Prometheus |
| `GET /demo/` | La interfaz de demostración |

## Quién hace el pedido

El usuario se indica con el encabezado `X-Usuario-Id`. La API solo verifica que exista: es acceso de laboratorio, no autenticación. Cuando Redis tenga las sesiones, esa verificación se reemplaza sin tocar las rutas ([cómo](como_sumar_una_base.md)).

## Errores

Todos los errores tienen la misma forma:

```json
{"error": {"codigo": "CONFLICTO", "mensaje": "El partido ya empezó: no se puede cargar ni corregir el pronóstico.", "request_id": "…"}}
```

| Estado | `codigo` | Cuándo |
|---|---|---|
| 401 | `NO_AUTORIZADO` | Falta el usuario o la clave de administración, o no son válidos |
| 403 | `PROHIBIDO` | Se piden datos de otro usuario o la tabla de un prode ajeno |
| 404 | `NO_ENCONTRADO` | No existe el partido, el usuario, el prode, el equipo o la jugada |
| 409 | `CONFLICTO` | El pedido es válido pero no se puede hacer ahora: pronóstico fuera de horario, prode lleno, marcador que no coincide con los goles cargados |
| 422 | `VALIDACION` | Un dato tiene mal el formato o está fuera de rango. Trae `detalle` con el campo |
| 503 | `DEPENDENCIA_NO_DISPONIBLE` | La base que atiende ese pedido no responde |
| 504 | `DEPENDENCIA_TIMEOUT` | La base tardó más de lo permitido |

Un 503 o un 504 nunca se disfrazan de lista vacía.

## Repetir un pedido

Los pedidos que escriben se pueden repetir sin efectos de más:

- El pronóstico tiene una clave única por usuario y partido: repetirlo lo corrige.
- Unirse dos veces a un prode devuelve `ya_estaba`.
- Poner en juego dos veces no mueve el momento de inicio.
- Una jugada se identifica con el `id` que manda quien la carga: repetirla no la duplica.
- Cerrar un partido dos veces con el mismo marcador no vuelve a sumar puntos.

## Métricas

| Métrica | Etiquetas | Qué mide |
|---|---|---|
| `prode_api_pedidos_total` | `metodo`, `ruta`, `estado` | Pedidos atendidos |
| `prode_api_duracion_segundos` | `metodo`, `ruta` | Tiempo de respuesta (histograma) |
| `prode_base_operaciones_total` | `base`, `operacion`, `resultado` | Operaciones contra cada base |
| `prode_base_duracion_segundos` | `base`, `operacion` | Duración de cada operación (histograma) |
| `prode_puntuacion_duracion_segundos` | `paso` | Duración de cada paso al cerrar un partido |
| `prode_puntuacion_pronosticos_total` | — | Pronósticos puntuados |
| `prode_calendario_antiguedad_segundos` | — | Antigüedad de la copia del calendario |
| `prode_calendario_desactualizado` | — | 1 si la copia no se pudo renovar |

`ruta` es siempre la plantilla (`/partidos/{partido_id}`), nunca la ruta con el identificador. Comparar `prode_api_duracion_segundos` con `prode_base_duracion_segundos` es la forma de saber si un pedido lento se debe a la API o a la base.

Son métricas de aplicación. Las internas de cada base salen de sus exportadores.


## Histórico de una simulación

`GET /partidos/{id}/historico` consulta Neo4j y devuelve estadísticas agregadas por equipo, muestras por minuto y jugadas con sus protagonistas. `GET /partidos/{id}/eventos/{evento_id}/cadena` recorre las jugadas previas. Si falta archivar un partido finalizado, `POST /administracion/simulaciones/{id}/archivar` permite reintentar con `X-Admin-Clave`; no crea duplicados al repetirse. El proceso requiere el guion de MongoDB y las muestras completas de InfluxDB.

Para simulaciones nuevas, `GET /partidos/{id}/estadisticas/jugadores` devuelve los contadores acumulados por jugador, con su equipo y fuente. Antes del archivo consulta InfluxDB; después consulta los resúmenes de Neo4j. Las simulaciones anteriores sin métricas individuales responden 404 en esta ruta. El endpoint de estadísticas por equipo conserva su contrato y agrega los datos individuales para las simulaciones nuevas. La fórmula de posesión y el grano de los puntos están en [diseño por jugador](diseno_estadisticas_jugador.md).

Las simulaciones de versión 3 exponen `GET /partidos/{id}/jugadas/temporales`: eventos de InfluxDB con categoría, jugador, minuto y timestamp de la corrida. Los resúmenes de acciones se calculan a partir de esos eventos; la posesión usa muestras separadas.
