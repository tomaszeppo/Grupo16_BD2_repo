# Modelo tabular — Comentarios masivos (Hito 6)

Sale directo de `patrones_de_acceso.md`. Nada acá se pensó como "traducir" una tabla relacional: cada tabla existe porque resuelve una consulta puntual.

## Keyspace

```
CREATE KEYSPACE fixture2030
WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1};
```

`SimpleStrategy` con factor 1 porque el ambiente de laboratorio es un solo nodo — no hay donde poner una segunda réplica. En un despliegue real, esto pasaría a `NetworkTopologyStrategy` con un factor por datacenter, coherente con el diseño multi-región que ya habíamos definido para Audiencia e interacción en el Hito 3 (ahí prioridad de disponibilidad, consistencia eventual).

## Tabla `comentarios_por_partido`

| Columna | Tipo | Rol |
| :--- | :--- | :--- |
| `partido_codigo` | text | Partición |
| `bucket` | int | Partición |
| `comentario_id` | timeuuid | Clustering (DESC) |
| `usuario_id` | text | Dato |
| `contenido` | text | Dato |
| `creado_en` | timestamp | Dato |
| `estado_moderacion` | text | Dato |
| `likes` | int | Dato |

```
PRIMARY KEY ((partido_codigo, bucket), comentario_id)
WITH CLUSTERING ORDER BY (comentario_id DESC)
```

**Por qué esta clave:** la consulta que más se repite es "los últimos comentarios de este partido, en esta ventana de tiempo" — eso es literalmente `partido_codigo + bucket` como partición. El `comentario_id` (timeuuid, que ya trae el momento de creación codificado) como clustering en orden descendente hace que "los últimos" sea simplemente leer desde el principio de la partición, sin ordenar nada en la aplicación.

## Tabla `comentarios_por_usuario`

| Columna | Tipo | Rol |
| :--- | :--- | :--- |
| `usuario_id` | text | Partición |
| `creado_en` | timestamp | Clustering (DESC) |
| `comentario_id` | timeuuid | Clustering (DESC) |
| `partido_codigo` | text | Dato |
| `contenido` | text | Dato |
| `estado_moderacion` | text | Dato |

```
PRIMARY KEY (usuario_id, creado_en, comentario_id)
WITH CLUSTERING ORDER BY (creado_en DESC, comentario_id DESC)
```

Duplica el contenido del comentario a propósito. Es la estructura de acceso secundaria del módulo (ver `decisiones_de_particionamiento.md` para el porqué de elegir esto y no un índice).

## Tabla `partidos_referencia`

| Columna | Tipo | Rol |
| :--- | :--- | :--- |
| `partido_codigo` | text | Partición (clave simple) |
| `fecha_inicio` | timestamp | Dato |

No es una tabla de comentarios — guarda el horario de inicio de cada partido para poder calcular a qué `bucket` corresponde un comentario nuevo. Usa los mismos 32 códigos de partido (`P-01` a `P-32`) que el módulo de grafos del Hito 5, con las mismas fechas.

## Qué consulta resuelve cada tabla

| Consulta (de `patrones_de_acceso.md`) | Tabla |
| :--- | :--- |
| 1. Feed en vivo de un partido | `comentarios_por_partido` |
| 2. Insertar comentario | `comentarios_por_partido` + `comentarios_por_usuario` (las dos, mismo `comentario_id`) |
| 3. Ventana temporal de un partido | `comentarios_por_partido` (varios `bucket`) |
| 4. Moderar un comentario | `comentarios_por_partido` (y su duplicado en `comentarios_por_usuario`) |
| 5. Borrar un comentario | Igual que moderar |
| 6. Historial de un usuario | `comentarios_por_usuario` |
