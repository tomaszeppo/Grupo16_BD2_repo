# Modelo multidimensional

## Tabla `estadisticas_partido`

| Elemento | Decisión |
|---|---|
| Tabla | `estadisticas_partido` |
| Tags | `partido_id`, `equipo_id`, `sede`, `fuente`, `fase` |
| Fields | `posesion_pct`, `pases_completados`, `tiros`, `recuperaciones`, `velocidad_kmh` |
| Tiempo | `time`, precisión de segundos |
| Serie | combinación de tabla + los cinco tags |

### Por qué estos tags

`partido_id` y `equipo_id` son filtros centrales. `sede` tiene solo 20 valores en el contexto del grupo. `fuente` está acotada a ocho valores. `fase` también está acotada.

No se agregan como tags medidas (`posesion_pct`, `velocidad_kmh`, etc.), timestamps ni identificadores únicos por punto.

## Tabla `usuarios_conectados`

| Elemento | Decisión |
|---|---|
| Tabla | `usuarios_conectados` |
| Tags | `partido_id`, `region` |
| Field | `usuarios_activos` |
| Tiempo | `time`, segundos |

La serie representa actividad agregada. No identifica a cada usuario individual porque esa dimensión no aporta a las consultas priorizadas y multiplicaría cardinalidad.

## Semántica de fields

- `posesion_pct`: medida de estado/muestra. `AVG` es razonable como resumen de una ventana.
- `pases_completados`: conteo de pases ocurridos durante el intervalo. `SUM` de una ventana es interpretable.
- `tiros`: conteo de tiros del intervalo. `SUM` es interpretable.
- `recuperaciones`: conteo de recuperaciones del intervalo. `SUM` es interpretable.
- `velocidad_kmh`: medida instantánea. `AVG` y `MAX` son interpretables; sumar no tendría sentido.
- `usuarios_activos`: conteo instantáneo. `MAX` responde a la pregunta de pico.
