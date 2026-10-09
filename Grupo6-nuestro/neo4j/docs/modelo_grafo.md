# Modelo de grafo — Fixture 2030 (Hito 5)

## Nodos

| Etiqueta | Identificador | Propiedades | Por qué esas y no otras |
| :--- | :--- | :--- | :--- |
| `Equipo` | `codigo` (único) | `confederacion`, `ranking` | `confederacion` es candidata a convertirse en su propia relación más adelante (Equipo→Confederación); Se sacaron `nombre` y `sedeBase`: no tocan ninguna relación, viven en el módulo documental (Hito 4). |
| `Jugador` | `codigo` (único, ej. `ARG-10`) | `posicion`, `dorsal` | Ambas se usan para filtrar dentro de un recorrido (por ejemplo, encontrar al delantero de un equipo). Se sacaron `nombre`, `fechaNacimiento` y `convocado`: descriptivas, sin uso relacional. También se sacó `equipoCodigo`: quedaría duplicando lo que ya dice la relación `PERTENECE_A`. |
| `Partido` | `codigo` (único, ej. `P-01`) | `fase`, `fecha`, `equipoGanador`, `equipoPerdedor`, `golesGanador`, `golesPerdedor`, `origenResultado` | `fecha` es la "relación de programación" que pide el hito; `fase` agrupa partidos entre sí y podría derivar en un nodo `Fase` más adelante. |
| `Sede` | `codigo` (único, ej. `EST001`) | `nombre`, `ciudad` | Ambas podrían convertirse en nodos propios (`Sede→Ciudad→País`) si el modelo crece. Se sacó `capacidad`: descriptiva. El resultado del partido es simulado (`origenResultado = 'SIMULADO'`) y no deriva de ninguna predicción. |
| `Evento` | `codigo` (único, ej. `P-01-EV1`) | `tipo`, `minuto` | `tipo` define qué significa la relación con el jugador y el partido; `minuto` da el orden cronológico entre eventos de un mismo partido. |

## Relaciones

| Relación | Dirección | Propiedades | Cardinalidad | Corresponde a |
| :--- | :--- | :--- | :--- | :--- |
| `PERTENECE_A` | `(Jugador)→(Equipo)` | — | N:1 (muchos jugadores, un equipo) | Pertenencia de jugadores a equipos (RF4). |
| `DISPUTA` | `(Partido)→(Equipo)` | `rol` (`local`/`visitante`) | Cada partido tiene exactamente 2; un equipo participa en varios partidos | Participación de equipos en partidos (RF4). Dirección y nombre igual que en la práctica guiada de la Clase 5. |
| `SE_JUEGA_EN` | `(Partido)→(Sede)` | — | N:1 (muchos partidos, una sede) | Programación de partidos en una sede (RF4). |
| `OCURRE_EN` | `(Evento)→(Partido)` | — | N:1 (muchos eventos, un partido) | Vinculación de eventos con su partido (RF4). |
| `PROTAGONISTA_DE` | `(Jugador)→(Evento)` | — | N:1 (un jugador puede protagonizar varios eventos, cada evento tiene un protagonista) | No está en la práctica de la Clase 5 (que no trabaja eventos); es una relación propia para poder recorrer jugador → evento → partido. |

## Restricciones e índices

- Restricción de unicidad en `codigo` para las cinco etiquetas (`equipo_codigo_unico`, etc.), igual que la de la Práctica 5 de la Clase 5 pero aplicada a las cinco entidades del hito, no solo a una de práctica.
- Índice en `Evento.tipo`: para filtrar rápido "todos los goles" o "todas las tarjetas" sin recorrer todos los eventos.
- Índice en `Partido.fecha`: para ordenar o filtrar por fecha sin recorrer todos los partidos.

## Por qué esto se beneficia de ser un grafo

Las preguntas que motivan este módulo (Sección "Problema relacional" de `decisiones.md`) son del tipo "¿quién jugó contra quién?", "¿qué compañeros de plantel hicieron un gol?" o "¿qué dos equipos terminan compartiendo estadio aunque no se enfrenten?". Resolver eso desde documentos aislados (como en Mongo) implica cruzar colecciones a mano cada vez; acá es simplemente recorrer relaciones.
