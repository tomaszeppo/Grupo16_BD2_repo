# Modelo de datos

## MongoDB — base `prode2030`

Colecciones, validación e índices se crean en [`seed/cargar_mongo.py`](../seed/cargar_mongo.py).

| Colección | `_id` | Campos | Índices además de `_id` |
|---|---|---|---|
| `usuarios` | `U0000001` | `nombre`, `pais`, `creado_en` | `pais` |
| `prodes` | `PR-` y 8 caracteres | `nombre`, `dueno`, `codigo` (invitación), `integrantes` (hasta 100), `creado_en` | `codigo` único; `integrantes` |
| `pronosticos` | `U0000001:P-07` | `usuario_id`, `partido_id`, `goles_local`, `goles_visitante`, `cargado_en`, `creado_en`; al puntuar: `puntos`, `exacto`, `tiempo_seg`, `anulado` | `usuario_id`; `partido_id` |
| `resultados` | `P-07` | `goles_local`, `goles_visitante`, `clasificado`, `inicio_programado`, `inicio_real`, `cerrado_en`, `puntuacion` | — |
| `puntajes` | `U0000001` | `puntos`, `exactos`, `tiempo_seg`, `aplicados` (partidos ya sumados) | `puntos`, `exactos`, `tiempo_seg` descendentes y `_id` |
| `rankings_historicos` | `P-07` | `generado_en`, `total_usuarios`, `primeros` (100) | — |
| `equipos` | `ARG` | `nombre`, `grupo` | — |
| `jugadores` | `J-ARG-09` | `nombre`, `apellido`, `dorsal`, `posicion`, `equipo` | `equipo`, `posicion` |
| `contadores` | `usuarios` | `valor` (último número de usuario entregado) | — |

`usuarios`, `prodes` y `pronosticos` tienen validación de esquema (`$jsonSchema`).

Un pronóstico ya puntuado (los valores son de ejemplo, para mostrar la forma):

```json
{
  "_id": "U0100001:P-07",
  "usuario_id": "U0100001",
  "partido_id": "P-07",
  "goles_local": 2,
  "goles_visitante": 1,
  "creado_en": "2026-11-17T19:15:41Z",
  "cargado_en": "2026-11-17T19:15:41Z",
  "puntos": 1,
  "exacto": false,
  "tiempo_seg": 172799,
  "anulado": false
}
```

`cargado_en` es la hora de la última corrección; es la que cuenta para el desempate.

El resultado de un partido, con el avance de su puntuación (también de ejemplo):

```json
{
  "_id": "P-07",
  "goles_local": 2,
  "goles_visitante": 0,
  "clasificado": null,
  "inicio_programado": "2026-11-21T18:00:00Z",
  "inicio_real": "2026-11-17T19:18:02Z",
  "cerrado_en": "2026-11-17T19:18:20Z",
  "puntuacion": {
    "estado": "completa",
    "pasos": {"puntuar": 33.8, "sumar": 77.9, "foto": 23.9},
    "pronosticos": 1,
    "iniciada_en": "2026-11-17T19:18:20Z",
    "terminada_en": "2026-11-17T19:18:21Z"
  }
}
```

Los estados de la puntuación son `pendiente`, `en_curso`, `completa` y `fallida`. Los tiempos de `pasos` están en milisegundos.

### Reglas de puntos y desempate

- 3 puntos por el resultado exacto, 1 por acertar el ganador o el empate, 0 si no.
- Orden del ranking: puntos, cantidad de exactos, tiempo acumulado y, a igualdad total, identificador de usuario. El sorteo final queda para el ranking de Redis.
- El tiempo de un pronóstico es cuántos segundos antes del horario programado quedó cargado, con tope de 5 días (432.000 segundos): entero si fue exacto, la mitad si solo acertó el ganador, cero si no acertó.
- Un pronóstico cargado cuando el partido ya había empezado se anula.

## Neo4j

Restricciones, índices y carga en [`seed/cargar_neo4j.py`](../seed/cargar_neo4j.py).

```mermaid
flowchart LR
    J["Jugador<br/>id, nombre, apellido,<br/>dorsal, posicion"]
    E["Equipo<br/>codigo, nombre, grupo"]
    P["Partido<br/>id, fecha_hora, fase, estado,<br/>inicio_real, goles_local,<br/>goles_visitante"]
    S["Estadio<br/>id, nombre, ciudad"]
    V["Evento (jugada)<br/>id, tipo, minuto, orden"]

    J -- PERTENECE_A --> E
    E -- "PARTICIPA_EN<br/>condicion: local | visitante" --> P
    P -- SE_JUEGA_EN --> S
    V -- OCURRE_EN --> P
    J -- PROTAGONIZA --> V
    V -- INFLUYE_EN --> V
    P -- "CLASIFICA_A<br/>como: ganador | perdedor" --> P
```

- Restricción de unicidad sobre `Equipo.codigo`, `Jugador.id`, `Estadio.id`, `Partido.id` y `Evento.id`. Índice sobre `Partido.fecha_hora`.
- `estado` vale `Programado`, `En juego` o `Finalizado`.
- Tipos de jugada: `Inicio`, `Pase`, `Tiro`, `Gol`, `Falta`, `Tarjeta amarilla`, `Tarjeta roja`, `Cambio`, `Final`.
- `INFLUYE_EN` va de la jugada anterior a la que provocó: `(pase)-[:INFLUYE_EN]->(tiro)-[:INFLUYE_EN]->(gol)`.
- `CLASIFICA_A` arma el cuadro: de cada partido de eliminatorias sale una relación al partido siguiente. Las dos semifinales tienen además una relación `perdedor` hacia el partido por el tercer puesto.

La consulta que recorre lo que llevó a una jugada:

```cypher
MATCH (fin:Evento {id: $evento})-[:OCURRE_EN]->(:Partido {id: $partido})
OPTIONAL MATCH (previo:Evento)-[:INFLUYE_EN*1..10]->(fin)
...
```

Todas las consultas están como constantes en [`app/adapters/neo4j.py`](../app/adapters/neo4j.py).

## Datos de laboratorio

Los genera [`seed/datos.py`](../seed/datos.py) con semilla fija: 48 equipos en 12 grupos, 26 jugadores por equipo, 16 estadios y 104 partidos (72 de grupos con sus equipos y 32 de eliminatorias sin equipos, enlazados en el cuadro). Los dos primeros partidos nacen jugados, con sus jugadas y su marcador, para tener cadenas que recorrer desde el arranque.
