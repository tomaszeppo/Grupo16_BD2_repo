# Modelo documental — Equipos y Jugadores

Dos colecciones, conectadas por referencia (no por embedding). El porque de
esta decision esta en `docs/decisiones-de-diseno.md`; aca solo se describe la
estructura tal como queda validada en `init-scripts/01-create-collections.js`.

## Coleccion `equipos`

| Campo | Tipo | Obligatorio | Descripcion |
| :--- | :--- | :---: | :--- |
| `codigo` | string | Si | Codigo de 3 letras mayusculas segun el estandar FIFA, unico (ej: `ARG`, `GER`). |
| `nombre` | string | Si | Nombre del equipo. |
| `confederacion` | string (enum) | Si | Una de: CONMEBOL, UEFA, CAF, AFC, CONCACAF, OFC. |
| `ranking` | int | Si | Posicion en el ranking. |
| `sedeBase` | string | No | Ciudad de concentracion. |
| `cantidadJugadoresConvocados` | int | No | Dato desnormalizado, calculado a partir de `jugadores`. |

```json
{
  "codigo": "ARG",
  "nombre": "Argentina",
  "confederacion": "CONMEBOL",
  "ranking": 1,
  "sedeBase": "Buenos Aires",
  "cantidadJugadoresConvocados": 24
}
```

## Coleccion `jugadores`

| Campo | Tipo | Obligatorio | Descripcion |
| :--- | :--- | :---: | :--- |
| `codigo` | string | Si | Codigo unico del jugador (ej: `ARG-10`). |
| `equipoCodigo` | string | Si | Referencia al `codigo` del equipo (no hay integridad referencial automatica; la garantiza la aplicacion). |
| `nombre` | string | Si | Nombre de pila. |
| `apellido` | string | Si | Apellido. |
| `posicion` | string (enum) | Si | Una de: Portero, Defensa, Centrocampista, Delantero. |
| `dorsal` | int | No | Numero de camiseta (1 a 26). |
| `fechaNacimiento` | date | No | Fecha de nacimiento. |
| `convocado` | bool | Si | Si integra la lista final. |
| `estadisticas.partidosJugados` | int | No | Se actualiza partido a partido. |
| `estadisticas.goles` | int | No | Se actualiza partido a partido. |
| `estadisticas.tarjetasAmarillas` | int | No | Se actualiza partido a partido. |
| `estadisticas.tarjetasRojas` | int | No | Se actualiza partido a partido. |

```json
{
  "codigo": "ARG-10",
  "equipoCodigo": "ARG",
  "nombre": "Mateo",
  "apellido": "Ramirez",
  "posicion": "Delantero",
  "dorsal": 10,
  "fechaNacimiento": "2004-03-15T00:00:00.000Z",
  "convocado": true,
  "estadisticas": {
    "partidosJugados": 3,
    "goles": 2,
    "tarjetasAmarillas": 1,
    "tarjetasRojas": 0
  }
}
```

## Relacion entre las dos colecciones

`jugadores.equipoCodigo` apunta a `equipos.codigo`. Para traer un equipo con
su plantilla completa hacen falta dos consultas (o un `$lookup`, ver la
segunda agregacion de `queries/01-consultas-recuperacion.js`), a cambio de que
actualizar un jugador nunca toque el documento del equipo.
