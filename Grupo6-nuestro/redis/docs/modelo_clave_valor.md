# Modelo clave/valor — Caché de usuarios y sesiones (Hito 7)

## Convención de nombres (RNF5)

`{dominio}:{entidad}[:{id}][:{subcampo}]`, todo en minúscula, separado por `:` (el separador estándar de Redis, que además permite inspeccionar por prefijo con `SCAN MATCH dominio:*`).

| Dominio | Prefijo |
| :--- | :--- |
| Sesiones | `sesion:` |
| Puntero usuario → sesión activa | `usuario:{id}:sesion_activa` |
| Caché de catálogo | `cache:equipo:{codigo}` y `cache:partido:{codigo}:resumen` |
| Ranking público | `ranking:publico` (ZSET) y `ranking:publico:usuario:{id}` (hash) |
| Ranking privado (grupo) | `ranking:privado:{grupo_id}` — mismo patrón que el público, un ZSET por grupo |
| Marcador en vivo | `marcador:{partido_codigo}` |
| Likes de comentarios | `likes:comentario:{comentario_id}` y `likes:pendientes_sync` |
| Límite de comentarios | `ratelimit:comentarios:{usuario_id}` |
| Espectadores en vivo | `espectadores:{partido_codigo}` |

## Claves y estructuras

### `sesion:{sesion_id}` — hash, TTL 30 minutos (ventana deslizante)

| Campo | Tipo | Para qué |
| :--- | :--- | :--- |
| `usuario_id` | string | A quién pertenece la sesión |
| `creado_en` | string (ISO 8601) | Cuándo se inició |
| `ultima_actividad` | string (ISO 8601) | Se actualiza en cada acceso |
| `estado` | string | `activa` |

### `usuario:{usuario_id}:sesion_activa` — string, mismo TTL que la sesión

Guarda el `sesion_id` vigente de ese usuario. Existe para resolver "¿este usuario ya tiene una sesión abierta?" sin tener que buscar por todas las sesiones.

### `cache:equipo:{codigo}` — string (JSON), TTL 5 minutos

Copia de lectura rápida de un documento de la colección `equipos` de Mongo (Hito 4). Se explica el patrón completo de hit/miss/invalidación en `ciclo_de_vida_e_invalidacion.md`.

### `cache:partido:{partido_codigo}:resumen` — string (JSON), TTL 30 segundos

Resumen reconstruible de un partido finalizado, con el campo `revision_fuente` para verificar que tras una invalidación la copia nueva corresponde a la versión actual de Mongo. Misma mecánica que `cache:equipo`, con un TTL más corto.

### `ranking:publico:usuario:{usuario_id}` — hash, sin TTL

| Campo | Tipo | Para qué |
| :--- | :--- | :--- |
| `puntos` | int | Puntaje acumulado del usuario en sus predicciones |
| `antelacion_total` | float | Suma de minutos de anticipación con que cargó cada predicción respecto del partido correspondiente |
| `actualizado_en` | string (ISO 8601) | Última modificación |

### `ranking:publico` — Sorted Set, sin TTL

Miembro = `usuario_id`. Score = combinación de puntos y antelación, calculada así:

```
score = puntos + (antelacion_total / 10_000_000)
```

La parte entera del score son los puntos (lo que de verdad importa para ganar); la parte decimal es la antelación normalizada a un número siempre menor a 1, así nunca se mete en el terreno del siguiente punto entero. Con esto, `ZREVRANGE ranking:publico 0 -1` devuelve la tabla ya ordenada de primero a último, desempate incluido, sin ningún paso extra de recálculo. El porqué de este diseño puntual está en `ciclo_de_vida_e_invalidacion.md`.

## Por qué estas estructuras y no otras

- **Hash para sesión y usuario de ranking:** son registros con varios campos relacionados que siempre se leen o escriben juntos — un hash evita tener una clave por campo.
- **String para la caché de equipo:** es un valor opaco (JSON) que se lee entero o no se lee; no hace falta tocar un campo individual.
- **Sorted Set para el ranking:** es la única estructura de Redis que mantiene un orden total actualizado en cada escritura sin trabajo extra en la lectura — exactamente lo que pide "que el ganador se vea rápido apenas termina el último partido".
- **String con INCR para los likes:** INCR es atómico por diseño en Redis; no hace falta ni un script ni una transacción para un contador simple.

---

## Estructuras agregadas tras la revisión de diseño

### `marcador:{partido_codigo}` — hash, sin TTL (se actualiza por escritura)

| Campo | Tipo | Para qué |
| :--- | :--- | :--- |
| `goles_local` | int | Calculado y escrito en Neo4j al confirmarse un gol |
| `goles_visitante` | int | Idem |
| `minuto` | int | Último minuto conocido |
| `ultimo_evento` | string | Descripción corta, para notificar sin pedir el detalle completo |
| `actualizado_en` | string (ISO 8601) | Para detectar un marcador stale si el productor de eventos se cae |

### `likes:comentario:{comentario_id}` — string (contador), sin TTL hasta sincronizar

`INCR`/`DECR` nativos (atómicos por diseño). Cada `comentario_id` con cambios se agrega a `likes:pendientes_sync` (SET) para que un proceso periódico lea de ahí (nunca con `KEYS`), escriba el valor consolidado en Cassandra, y lo saque del set.

### `ratelimit:comentarios:{usuario_id}` — string (contador), TTL 10 segundos

`INCR` + `EXPIRE ... NX` (el `NX` asegura que el TTL se fija solo en el primer comentario de la ventana, no se reinicia en cada uno). Si el valor supera el límite, la aplicación rechaza el comentario.

### `espectadores:{partido_codigo}` — Sorted Set, TTL de respaldo de 6 horas (además se poda por score)

Miembro = `sesion_id` o `usuario_id`; score = timestamp Unix del último latido. El conteo de gente en vivo es `ZCOUNT` sobre los últimos N segundos, no `ZCARD` del total histórico — así un usuario que se fue sin cerrar sesión deja de contar apenas pasa la ventana, sin necesitar que nadie lo borre explícitamente. Como la clave no tiene otro vencimiento, cada latido renueva con `EXPIRE` un TTL de respaldo de 6 horas (junto con el `ZADD`, dentro de `MULTI/EXEC`): si el partido termina y nadie vuelve a latir, la clave se libera sola en lugar de quedar ocupando memoria.
