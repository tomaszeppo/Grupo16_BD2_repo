# Modelo clave/valor — Caché de usuarios y sesiones (Hito 7)

## Convención de nombres (RNF5)

`{dominio}:{entidad}[:{id}][:{subcampo}]`, todo en minúscula, separado por `:` (el separador estándar de Redis, que además permite inspeccionar por prefijo con `SCAN MATCH dominio:*`).

| Dominio | Prefijo |
| :--- | :--- |
| Sesiones | `sesion:` |
| Puntero usuario → sesión activa | `usuario:{id}:sesion_activa` |
| Caché de catálogo | `cache:equipo:{codigo}` y `cache:partido:{codigo}:resumen` |
| Ranking público | `ranking:publico` (ZSET) y `ranking:publico:usuario:{id}` (hash) |
| Contador de visitas | `contador:partido:{partido_codigo}:visitas` y `contador:partido:{partido_codigo}:meta` |

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

### `ranking:publico` — Sorted Set, sin TTL

Miembro = `usuario_id`. Score = combinación de puntos y antelación, calculada así:

```
score = puntos + (antelacion_total / 10_000_000)
```

El score se actualiza con `ZINCRBY ranking:publico <puntos + antelacion/10_000_000> <usuario_id>`, que suma el delta de forma atómica. La parte entera del score son los puntos (lo que de verdad importa para ganar); la parte decimal es la antelación normalizada a un número siempre menor a 1, así nunca se mete en el terreno del siguiente punto entero. Con esto, `ZREVRANGE ranking:publico 0 -1` devuelve la tabla ya ordenada de primero a último, desempate incluido, sin ningún paso extra de recálculo. El porqué de este diseño puntual está en `ciclo_de_vida_e_invalidacion.md`.

### `contador:partido:{partido_codigo}:visitas` — string (contador), TTL 1 hora

Cuenta las visitas de un partido. `INCRBY` es atómico: Redis lo ejecuta de una vez aunque lleguen muchos clientes a la vez. Junto a él, `contador:partido:{partido_codigo}:meta` es un hash con la última operación, con el mismo TTL; los dos cambios se hacen juntos dentro de `MULTI/EXEC`.

## Por qué estas estructuras y no otras

- **Hash para la sesión:** es un registro con varios campos relacionados que siempre se leen o escriben juntos; un hash evita tener una clave por campo.
- **String para la caché de equipo y de partido:** es un valor opaco (JSON) que se lee entero o no se lee.
- **Sorted Set para el ranking:** mantiene el orden total actualizado en cada escritura sin trabajo extra en la lectura, que es lo que pide "que el ganador se vea rápido apenas termina el último partido".
- **String con INCRBY para el contador:** `INCRBY` es atómico por diseño; no hace falta un bloque ni una transacción para un contador simple.
